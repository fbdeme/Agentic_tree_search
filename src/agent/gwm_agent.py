"""
GWMAgent: Graph World Model based multi-hop document exploration agent.
- State: DynamicSubKG (dynamic knowledge graph)
- Action: Tool-based exploration (browse, read, search)
- Transition: Add nodes/edges to KG + relationship inference
"""

import json
import os
import re
from typing import Optional
from src.state.knowledge_graph import DynamicSubKG, KGNode, KGEdge
from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.reasoning import ReasoningModule


TOOL_USE_SYSTEM = """You are an AI agent exploring regulatory documents to answer a user's question.
You navigate documents like a file system using three tools:

{tool_descriptions}

Respond ONLY in JSON format:
{{
    "thinking": "your reasoning about what to do next",
    "actions": [
        {{"tool": "browse", "doc_id": "...", "node_id": "...or null"}},
        {{"tool": "read", "doc_id": "...", "node_id": "..."}},
        {{"tool": "search", "keyword": "..."}}
    ]
}}

Strategy:
1. FIRST HOP: Always start with search() using key technical terms from the question.
   Try MULTIPLE keyword variants — both the question's phrasing AND likely answer terms.
   Example: for "What is the internal pressure of the CNV?", search both
   "containment pressure" AND "sub-atmospheric" AND "vacuum".
2. Use browse() to explore the tree hierarchy when search isn't finding results.
3. Use read() to get full content of nodes identified by search or browse.
4. Do NOT read large parent nodes (Preface, Chapter overview) — drill down to specific subsections.
5. Do NOT re-read nodes you've already explored.
6. Return 1-3 actions per step."""


class GWMAgent:
    """
    GWM State-Action-Transition loop with tool-based exploration.

    The agent starts with an empty graph G_0 and progressively builds a KG
    through multi-hop exploration using browse/read/search tools.
    """

    def __init__(
        self,
        environment: PageIndexEnvironment,
        model: str = "gpt-4.1",
        max_hops: int = 4,
        top_k: int = 2,
    ):
        self.env = environment
        self.model = model
        self.max_hops = max_hops
        self.top_k = top_k
        self.reasoning = ReasoningModule(model=model)

    # -----------------------------------------------------------
    # Main loop: run()
    # -----------------------------------------------------------
    def run(self, question: str, doc_ids: Optional[list[str]] = None) -> dict:
        print(f"\n{'='*60}")
        print(f"🤖 GWM Agent (tool-use)")
        print(f"   Query: {question}")
        print(f"   Max hops: {self.max_hops}")
        print(f"{'='*60}\n")

        kg = DynamicSubKG(question=question)
        trajectory: list[str] = []
        actual_hops = 0
        already_read: set[str] = set()

        for hop in range(1, self.max_hops + 1):
            kg.current_hop = hop
            print(f"\n🔍 [Hop {hop}/{self.max_hops}]")
            print(f"   KG: {kg}")

            # ── Check sufficiency (hop 2+) ────────────────────────
            if hop > 1:
                plan = self.reasoning.plan_next_search(
                    question=question,
                    kg_context=kg.to_context_string(),
                    tree_summary="(use tools to explore)",
                )
                if plan["sufficient"]:
                    print(f"   ✅ Evidence sufficient — stopping at hop {hop}")
                    trajectory.append(f"Hop {hop}: Early stop — evidence sufficient")
                    break

            # ── Action: Tool-based exploration ────────────────────
            tool_actions = self._plan_tool_actions(question, kg, doc_ids)
            retrieved = self._execute_tools(tool_actions, doc_ids, already_read)

            if not retrieved:
                print(f"   ⚠️  No new nodes found")
                trajectory.append(f"Hop {hop}: no results")
                continue

            # ── Transition: Add nodes + infer edges ───────────────
            hop_log = []
            new_nodes: list[KGNode] = []

            for r in retrieved:
                node_id = f"{r['doc_id']}_{r['node_id']}"
                if kg.has_node(node_id):
                    continue

                summary = self.reasoning.summarize_node(r["title"], r["content"])
                new_node = KGNode(
                    node_id=node_id,
                    title=r["title"],
                    content=r["content"],
                    summary=summary,
                    source_doc=r["doc_id"],
                    page_range=r["page_range"],
                    references=r.get("references", []),
                )
                if kg.add_node(new_node):
                    new_nodes.append(new_node)
                    hop_log.append(f"node: [{node_id}] {r['title'][:40]}")
                    print(f"   ✅ Node: [{node_id}] {r['title'][:50]}")

            # Edge inference: new↔existing + new↔new
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
                    node_a_title=node_a.title,
                    node_a_content=node_a.content,
                    node_b_title=node_b.title,
                    node_b_content=node_b.content,
                    question=question,
                )
                relation = rel.get("relation", "NONE")
                confidence = rel.get("confidence", 0.5)
                if relation != "NONE" and confidence >= 0.4:
                    edge = KGEdge(
                        source_id=node_a.node_id,
                        target_id=node_b.node_id,
                        relation=relation,
                        confidence=confidence,
                        reasoning=rel.get("reasoning", ""),
                    )
                    if kg.add_edge(edge):
                        hop_log.append(f"edge: {relation}")
                        print(f"   🔗 {node_a.node_id[:20]} --{relation}--> {node_b.node_id[:20]}")

            trajectory.append(f"Hop {hop}: " + " | ".join(hop_log) if hop_log else f"Hop {hop}: no new nodes")
            actual_hops = hop

        # ── Collect reference images ──────────────────────────────
        reference_images = self._collect_reference_images(kg, doc_ids)

        # ── Generate final answer ─────────────────────────────────
        print(f"\n{'='*60}")
        print(f"📝 Final answer generation...")
        print(f"   KG: {kg}")
        if reference_images:
            print(f"   📷 Images: {len(reference_images)}")
        print(f"{'='*60}")

        answer = self.reasoning.generate_answer(
            question=question,
            kg_context=kg.to_context_string(),
            trajectory=trajectory,
            reference_images=reference_images if reference_images else None,
        )

        return {
            "answer": answer,
            "kg": kg,
            "trajectory": trajectory,
            "hops_used": actual_hops,
        }

    # -----------------------------------------------------------
    # Tool-based action planning
    # -----------------------------------------------------------
    def _plan_tool_actions(self, question: str, kg: DynamicSubKG,
                           doc_ids: Optional[list[str]]) -> list[dict]:
        """LLM decides which tools to call based on current state."""
        system = TOOL_USE_SYSTEM.format(
            tool_descriptions=self.env.get_tool_descriptions()
        )

        explored = list(kg.nodes.keys())
        explored_str = ", ".join(explored) if explored else "(none)"

        user = (
            f"Question: {question}\n\n"
            f"Already explored nodes: {explored_str}\n\n"
            f"Current knowledge:\n{kg.to_context_string()}\n\n"
            f"What tools should I call next to find the answer?"
        )

        response = self.reasoning._call(system, user, max_tokens=512)

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", response).strip()
            result = json.loads(cleaned)
            actions = result.get("actions", [])
            thinking = result.get("thinking", "")
            if thinking:
                print(f"   💭 {thinking[:100]}")
            return actions
        except Exception:
            # Fallback: search with the question
            return [{"tool": "search", "keyword": question.split()[0]}]

    def _execute_tools(self, actions: list[dict],
                       doc_ids: Optional[list[str]],
                       already_read: set[str] = None) -> list[dict]:
        """Execute tool actions and return retrieved nodes to add to KG."""
        if already_read is None:
            already_read = set()

        retrieved = []
        nodes_to_read = set()

        for action in actions:
            tool = action.get("tool", "")

            if tool == "browse":
                doc_id = action.get("doc_id")
                node_id = action.get("node_id")
                results = self.env.browse(doc_id, node_id)
                if results:
                    print(f"   📂 browse({doc_id}, {node_id}): {len(results)} items")
                    for r in results[:5]:
                        print(f"      [{r['node_id']}] {r['title'][:50]} ({r['n_children']} children)")

            elif tool == "read":
                doc_id = action.get("doc_id", "")
                node_id = action.get("node_id", "")
                nodes_to_read.add((doc_id, node_id))

            elif tool == "search":
                keyword = action.get("keyword", "")
                results = self.env.search(keyword, doc_ids)
                if results:
                    print(f"   🔎 search(\"{keyword}\"): {len(results)} matches")
                    for r in results[:3]:
                        print(f"      [{r['doc_id']}::{r['node_id']}] {r['title'][:40]} (in {r['match_in']})")
                    for r in results[:self.top_k]:
                        nodes_to_read.add((r["doc_id"], r["node_id"]))

        # Read queued nodes (skip already read)
        for doc_id, node_id in nodes_to_read:
            key = f"{doc_id}_{node_id}"
            if key in already_read:
                continue
            already_read.add(key)

            node_data = self.env.read(doc_id, node_id)
            if node_data and node_data.get("content"):
                retrieved.append(node_data)
                print(f"   📖 read({doc_id}, {node_id}): {node_data['title'][:50]}")

        return retrieved

    # -----------------------------------------------------------
    # Collect reference images for VLM
    # -----------------------------------------------------------
    def _collect_reference_images(
        self, kg, doc_ids: list[str] | None, max_images: int = 6
    ) -> list[str]:
        ref_pages: dict[str, set[int]] = {}
        for nid, node in kg.nodes.items():
            for ref in node.references:
                doc_id = node.source_doc
                page = ref.get("page")
                if doc_id and page:
                    if doc_id not in ref_pages:
                        ref_pages[doc_id] = set()
                    ref_pages[doc_id].add(page)

        if not ref_pages:
            return []

        from src.utils.vision import render_pdf_pages

        all_images = []
        for doc_id, pages in ref_pages.items():
            pdf_path = self.env.documents.get(doc_id, {}).get("pdf_path", "")
            if not pdf_path or not os.path.isfile(pdf_path):
                continue

            sorted_pages = sorted(pages)[:max_images - len(all_images)]
            if not sorted_pages:
                break

            rendered = render_pdf_pages(pdf_path, sorted_pages)
            for r in rendered:
                all_images.append(r["base64"])
                print(f"   📷 Rendered: {doc_id} p.{r['page']}")

            if len(all_images) >= max_images:
                break

        return all_images
