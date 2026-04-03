"""
Small-scale ablation study: run 10 diverse questions with component-disabled variants.

Variants:
  1. full       — Full system (baseline)
  2. no_vision  — Vision RAG disabled (no images, no structured tables in answer)
  3. no_edges   — Edge inference disabled (nodes collected but no relationships)
  4. no_browse  — Browse-first disabled (no document overview at hop 1)

Usage:
    source .venv/bin/activate
    PYTHONPATH=pageindex_core:$PYTHONPATH python -u experiments/ablation_study.py
"""

import sys
import os
import json
import time
import copy
from pathlib import Path
from functools import wraps

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Token tracking ──────────────────────────────────────────────
_token_log = []

def patch_openai():
    from openai.resources.chat import completions as comp_module
    _orig_create = comp_module.Completions.create

    @wraps(_orig_create)
    def tracked_create(self, *args, **kwargs):
        result = _orig_create(self, *args, **kwargs)
        if hasattr(result, 'usage') and result.usage:
            _token_log.append({
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
            })
        return result

    comp_module.Completions.create = tracked_create

patch_openai()

from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.gwm_agent import GWMAgent
from src.agent.reasoning import ReasoningModule


# ── Ablation Variants ───────────────────────────────────────────

class AblationAgent(GWMAgent):
    """GWM Agent with toggleable components for ablation."""

    def __init__(self, environment, model="gpt-4.1", max_hops=4, top_k=2,
                 enable_vision=True, enable_edges=True, enable_browse_first=True):
        super().__init__(environment, model, max_hops, top_k)
        self.enable_vision = enable_vision
        self.enable_edges = enable_edges
        self.enable_browse_first = enable_browse_first

    def run(self, question, doc_ids=None):
        from src.state.knowledge_graph import DynamicSubKG, KGNode, KGEdge
        import re

        kg = DynamicSubKG(question=question)
        trajectory = []
        actual_hops = 0
        already_read = set()
        search_log = []

        for hop in range(1, self.max_hops + 1):
            kg.current_hop = hop

            # Dynamic termination (hop 2+)
            if hop > 1:
                plan = self.reasoning.plan_next_search(
                    question=question,
                    kg_context=kg.to_context_string(),
                    tree_summary="(use tools to explore)",
                )
                if plan["sufficient"]:
                    trajectory.append(f"Hop {hop}: Early stop")
                    break

            # Action: tool-based exploration
            tool_actions = self._plan_tool_actions_ablation(
                question, kg, doc_ids, search_log)
            retrieved, hop_searches = self._execute_tools(tool_actions, doc_ids, already_read)

            if hop_searches:
                search_log.append({"hop": hop, "searches": hop_searches})

            if not retrieved:
                trajectory.append(f"Hop {hop}: no results")
                continue

            # Transition: add nodes
            hop_log = []
            new_nodes = []
            for r in retrieved:
                node_id = f"{r['doc_id']}_{r['node_id']}"
                if kg.has_node(node_id):
                    continue
                summary = self.reasoning.summarize_node(r["title"], r["content"])
                new_node = KGNode(
                    node_id=node_id, title=r["title"], content=r["content"],
                    summary=summary, source_doc=r["doc_id"],
                    page_range=r["page_range"], references=r.get("references", []),
                )
                if kg.add_node(new_node):
                    new_nodes.append(new_node)
                    hop_log.append(f"node: [{node_id}]")

            # Edge inference (ABLATION: can be disabled)
            if self.enable_edges:
                existing_nodes = [
                    n for nid, n in kg.nodes.items()
                    if nid not in [nn.node_id for nn in new_nodes]
                ]
                pairs = []
                for nn in new_nodes:
                    for en in existing_nodes[:3]:
                        pairs.append((nn, en))
                for i, na in enumerate(new_nodes):
                    for nb in new_nodes[i + 1:]:
                        pairs.append((na, nb))

                for node_a, node_b in pairs:
                    rel = self.reasoning.infer_relation(
                        node_a_title=node_a.title, node_a_content=node_a.content,
                        node_b_title=node_b.title, node_b_content=node_b.content,
                        question=question,
                    )
                    relation = rel.get("relation", "NONE")
                    confidence = rel.get("confidence", 0.5)
                    if relation != "NONE" and confidence >= 0.4:
                        edge = KGEdge(
                            source_id=node_a.node_id, target_id=node_b.node_id,
                            relation=relation, confidence=confidence,
                            description=rel.get("description", ""),
                            reasoning=rel.get("reasoning", ""),
                        )
                        kg.add_edge(edge)
                        hop_log.append(f"edge: {relation}")

            trajectory.append(f"Hop {hop}: " + " | ".join(hop_log) if hop_log else f"Hop {hop}: empty")
            actual_hops = hop

        # Collect references (ABLATION: vision can be disabled)
        if self.enable_vision:
            reference_images = self._collect_reference_images(kg, doc_ids, question=question)
            table_context = self._collect_table_context(kg)
        else:
            reference_images = []
            table_context = ""

        # Generate answer
        kg_context = kg.to_context_string()
        if table_context:
            kg_context += "\n\n" + table_context

        answer = self.reasoning.generate_answer(
            question=question,
            kg_context=kg_context,
            trajectory=trajectory,
            reference_images=reference_images if reference_images else None,
        )

        return {
            "answer": answer, "kg": kg,
            "trajectory": trajectory, "hops_used": actual_hops,
        }

    def _plan_tool_actions_ablation(self, question, kg, doc_ids, search_log):
        """Modified tool planning with browse-first ablation."""
        import re

        system = self.__class__.__mro__[1].__dict__  # skip
        # Just call parent's method but control browse-first
        from src.agent.gwm_agent import TOOL_USE_SYSTEM
        system = TOOL_USE_SYSTEM.format(
            tool_descriptions=self.env.get_tool_descriptions()
        )

        explored = list(kg.nodes.keys())
        explored_str = ", ".join(explored) if explored else "(none)"

        memory_str = ""
        if search_log:
            memory_lines = []
            for entry in search_log:
                searches = ", ".join(
                    f'search("{s["keyword"]}") → {s["n_results"]} results'
                    + (f' → read {", ".join(s["read_nodes"])}' if s.get("read_nodes") else "")
                    for s in entry["searches"]
                )
                memory_lines.append(f'  Hop {entry["hop"]}: {searches}')
            memory_str = (
                "\n\nAgent Memory (previous search attempts):\n"
                + "\n".join(memory_lines)
                + "\n⚠️ Do NOT repeat these keywords. Try different terms, synonyms, "
                "or broader/narrower concepts."
            )

        # ABLATION: browse-first can be disabled
        structure_str = ""
        if self.enable_browse_first and not search_log:
            structure_str = "\n\n" + self.env.get_document_overview(depth=3)

        user = (
            f"Question: {question}\n\n"
            f"Already explored nodes: {explored_str}\n\n"
            f"Current knowledge:\n{kg.to_context_string()}"
            f"{structure_str}"
            f"{memory_str}\n\n"
            f"What tools should I call next to find the answer?"
        )

        response = self.reasoning._call(system, user, max_tokens=512)
        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", response).strip()
            result = json.loads(cleaned)
            return result.get("actions", [])
        except Exception:
            return [{"tool": "search", "keyword": question.split()[0]}]


# ── Main ────────────────────────────────────────────────────────

VARIANTS = {
    "full":            {"enable_vision": True,  "enable_edges": True,  "enable_browse_first": True},
    "no_vision":       {"enable_vision": False, "enable_edges": True,  "enable_browse_first": True},
    "no_edges":        {"enable_vision": True,  "enable_edges": False, "enable_browse_first": True},
    "no_browse_first": {"enable_vision": True,  "enable_edges": True,  "enable_browse_first": False},
}

# 10 diverse questions spanning all types
SAMPLE_IDS = [
    "Q001",  # factual / single / text
    "Q010",  # factual / multi / text
    "Q031",  # factual / single / table
    "Q058",  # factual / cross / text (VIOLATES case)
    "Q071",  # comparative / single / text
    "Q101",  # comparative / cross / text
    "Q131",  # comparative / cross / composite
    "Q161",  # judgment / multi / composite
    "Q176",  # judgment / cross / composite (VIOLATES case)
    "Q191",  # judgment / cross / image
]


def load_environment():
    env = PageIndexEnvironment(model="gpt-4.1")
    tree_dir = ROOT / "data/trees"
    for tree_file in tree_dir.glob("*_structure.json"):
        with open(tree_file) as f:
            data = json.load(f)
        env.register_tree(
            doc_id=data.get("doc_id", tree_file.stem),
            tree=data.get("tree", data.get("structure", [])),
            doc_name=data.get("doc_name", ""),
            pdf_path=data.get("pdf_path", ""),
        )
    return env


def main():
    env = load_environment()
    print(f"Environment: {env.doc_count} docs, {env.node_count} nodes\n")

    with open(ROOT / "data/qa_dataset/multihop_qa_benchmark_v2.json") as f:
        all_questions = json.load(f)["questions"]
    qa_map = {q["id"]: q for q in all_questions}
    sample = [qa_map[qid] for qid in SAMPLE_IDS if qid in qa_map]
    print(f"Sample: {[q['id'] for q in sample]} ({len(sample)} questions)\n")

    # Load judge results for correctness check
    import glob
    judge_map = {}
    for f_path in glob.glob(str(ROOT / "benchmark/results/gwm/judge_gwm_v046_*.json")):
        with open(f_path) as f:
            d = json.load(f)
        for r in d["results"]:
            judge_map[r["id"]] = r.get("final_vote", "?")

    all_results = {}

    for variant_name, config in VARIANTS.items():
        print(f"\n{'='*60}")
        print(f"VARIANT: {variant_name}")
        print(f"  Config: {config}")
        print(f"{'='*60}\n")

        variant_results = []

        for q in sample:
            qid = q["id"]
            _token_log.clear()

            agent = AblationAgent(
                environment=env, model="gpt-4.1", max_hops=4, top_k=2,
                **config
            )

            doc_ids = list(env.documents.keys())
            start = time.time()
            try:
                result = agent.run(question=q["question"], doc_ids=doc_ids)
                elapsed = time.time() - start
                answer = result["answer"]
                kg = result["kg"]
                hops = result["hops_used"]
            except Exception as e:
                elapsed = time.time() - start
                answer = f"ERROR: {e}"
                kg = None
                hops = 0

            total_tokens = sum(t["total_tokens"] for t in _token_log)
            prompt_tokens = sum(t["prompt_tokens"] for t in _token_log)
            completion_tokens = sum(t["completion_tokens"] for t in _token_log)
            cost = (prompt_tokens * 2 + completion_tokens * 8) / 1_000_000

            entry = {
                "id": qid,
                "question_type": q["question_type"],
                "reasoning_type": q["reasoning_type"],
                "complexity": q["complexity"],
                "time_sec": round(elapsed, 1),
                "hops_used": hops,
                "kg_nodes": len(kg.nodes) if kg else 0,
                "kg_edges": len(kg.edges) if kg else 0,
                "total_tokens": total_tokens,
                "cost_usd": round(cost, 4),
                "answer_len": len(answer),
                "answer_preview": answer[:200],
                "full_judge": judge_map.get(qid, "?"),
            }
            variant_results.append(entry)

            print(f"  [{qid}] {q['question_type']}/{q['reasoning_type']} "
                  f"→ {elapsed:.0f}s, {hops}hops, {len(kg.nodes) if kg else 0}nodes, "
                  f"{len(kg.edges) if kg else 0}edges, {total_tokens:,}tok, ${cost:.3f}")

        all_results[variant_name] = variant_results

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print("ABLATION SUMMARY")
    print(f"{'='*60}\n")

    header = f"{'Variant':<18} {'Time':>6} {'Hops':>5} {'Nodes':>6} {'Edges':>6} {'Tokens':>9} {'Cost':>7}"
    print(header)
    print("-" * len(header))

    for variant_name, results in all_results.items():
        avg_time = sum(r["time_sec"] for r in results) / len(results)
        avg_hops = sum(r["hops_used"] for r in results) / len(results)
        avg_nodes = sum(r["kg_nodes"] for r in results) / len(results)
        avg_edges = sum(r["kg_edges"] for r in results) / len(results)
        avg_tokens = sum(r["total_tokens"] for r in results) / len(results)
        avg_cost = sum(r["cost_usd"] for r in results) / len(results)
        print(f"{variant_name:<18} {avg_time:>5.1f}s {avg_hops:>5.1f} {avg_nodes:>6.1f} "
              f"{avg_edges:>6.1f} {avg_tokens:>8,.0f} ${avg_cost:>.4f}")

    # Save
    out_path = ROOT / "experiments/results/ablation_study.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
