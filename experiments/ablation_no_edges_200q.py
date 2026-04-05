"""
Full 200Q ablation: no_edges variant (verification removed).
Saves full answers, contexts, time, tokens for Judge + RAGAS evaluation.

Usage:
    source .venv/bin/activate
    PYTHONPATH=pageindex_core:$PYTHONPATH python -u experiments/ablation_no_edges_200q.py \
        --start 1 --end 25 --output experiments/results/ablation_no_edges_1.json

    # 8x parallel:
    for i in $(seq 1 8); do
      start=$(( (i-1)*25 + 1 )); end=$(( i*25 ))
      PYTHONPATH=pageindex_core:$PYTHONPATH python -u experiments/ablation_no_edges_200q.py \
        --start $start --end $end \
        --output experiments/results/ablation_no_edges_${i}.json &
    done
    wait
"""

import sys
import os
import json
import time
import argparse
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
from experiments.ablation_study import AblationAgent


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


def extract_contexts_from_kg(kg):
    contexts = [kg.to_context_string()]
    for nid, node in kg.nodes.items():
        if node.content and node.content != node.summary:
            contexts.append(f"[{node.title}] {node.content}")
    return contexts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=200)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    env = load_environment()
    print(f"Environment: {env.doc_count} docs, {env.node_count} nodes")

    with open(ROOT / "data/qa_dataset/multihop_qa_benchmark_v2.json") as f:
        all_questions = json.load(f)["questions"]

    questions = all_questions[args.start - 1 : args.end]
    print(f"Questions: {args.start}–{args.end} ({len(questions)} total)\n")

    results = []
    total_start = time.time()

    for i, q in enumerate(questions):
        qid = q["id"]
        _token_log.clear()

        agent = AblationAgent(
            environment=env, model="gpt-4.1", max_hops=4, top_k=2,
            enable_vision=True, enable_edges=False, enable_browse_first=True,
        )

        doc_ids = list(env.documents.keys())
        start = time.time()
        try:
            result = agent.run(question=q["question"], doc_ids=doc_ids)
            elapsed = time.time() - start
            answer = result["answer"]
            kg = result["kg"]
            hops = result["hops_used"]
            contexts = extract_contexts_from_kg(kg)
        except Exception as e:
            elapsed = time.time() - start
            answer = f"ERROR: {e}"
            kg = None
            hops = 0
            contexts = []

        prompt_tokens = sum(t["prompt_tokens"] for t in _token_log)
        completion_tokens = sum(t["completion_tokens"] for t in _token_log)
        total_tokens = sum(t["total_tokens"] for t in _token_log)
        api_calls = len(_token_log)
        cost = (prompt_tokens * 2 + completion_tokens * 8) / 1_000_000

        entry = {
            "id": qid,
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "generated_answer": answer,
            "reasoning_type": q["reasoning_type"],
            "complexity": q["complexity"],
            "question_type": q["question_type"],
            "retrieved_contexts": contexts,
            "time_sec": round(elapsed, 1),
            "hops_used": hops,
            "kg_nodes": len(kg.nodes) if kg else 0,
            "kg_edges": len(kg.edges) if kg else 0,
            "api_calls": api_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost, 4),
        }
        results.append(entry)

        print(f"[{i+1}/{len(questions)}] {qid} ({q['question_type']}/{q['reasoning_type']}) "
              f"→ {elapsed:.0f}s {hops}hops {len(kg.nodes) if kg else 0}n "
              f"{total_tokens:,}tok ${cost:.3f}")

    total_elapsed = time.time() - total_start

    # Summary
    avg_time = sum(r["time_sec"] for r in results) / len(results)
    avg_tokens = sum(r["total_tokens"] for r in results) / len(results)
    avg_cost = sum(r["cost_usd"] for r in results) / len(results)
    total_cost = sum(r["cost_usd"] for r in results)

    print(f"\n{'='*60}")
    print(f"SUMMARY (no_edges, {len(results)} questions)")
    print(f"{'='*60}")
    print(f"  Avg time: {avg_time:.1f}s")
    print(f"  Avg tokens: {avg_tokens:,.0f}")
    print(f"  Avg cost: ${avg_cost:.4f}")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")

    # Save
    out_path = args.output or str(ROOT / f"experiments/results/ablation_no_edges_{args.start}_{args.end}.json")
    report = {
        "method": "ablation_no_edges",
        "variant": {"enable_vision": True, "enable_edges": False, "enable_browse_first": True},
        "range": {"start": args.start, "end": args.end},
        "summary": {
            "n_questions": len(results),
            "avg_time_sec": round(avg_time, 1),
            "avg_tokens": round(avg_tokens),
            "avg_cost_usd": round(avg_cost, 4),
            "total_cost_usd": round(total_cost, 2),
            "total_time_sec": round(total_elapsed, 1),
        },
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
