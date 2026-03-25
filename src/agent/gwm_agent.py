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
        search_log: list[dict] = []  # Agent Memory: tracks past search attempts

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
            tool_actions = self._plan_tool_actions(question, kg, doc_ids, search_log)
            retrieved, hop_searches = self._execute_tools(tool_actions, doc_ids, already_read)

            # Record search attempts in Agent Memory
            if hop_searches:
                search_log.append({"hop": hop, "searches": hop_searches})

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
                        description=rel.get("description", ""),
                        reasoning=rel.get("reasoning", ""),
                    )
                    if kg.add_edge(edge):
                        hop_log.append(f"edge: {relation}")
                        print(f"   🔗 {node_a.node_id[:20]} --{relation}--> {node_b.node_id[:20]}")

            trajectory.append(f"Hop {hop}: " + " | ".join(hop_log) if hop_log else f"Hop {hop}: no new nodes")
            actual_hops = hop

        # ── Collect referenced materials ──────────────────────────
        reference_images = self._collect_reference_images(kg, doc_ids, question=question)
        table_context = self._collect_table_context(kg)

        # ── Generate final answer ─────────────────────────────────
        kg_context = kg.to_context_string()
        if table_context:
            kg_context += "\n\n" + table_context

        print(f"\n{'='*60}")
        print(f"📝 Final answer generation...")
        print(f"   KG: {kg}")
        if reference_images:
            print(f"   📷 Figure images: {len(reference_images)}")
        if table_context:
            print(f"   📊 Table data: {len(table_context)} chars")
        print(f"{'='*60}")

        answer = self.reasoning.generate_answer(
            question=question,
            kg_context=kg_context,
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
                           doc_ids: Optional[list[str]],
                           search_log: list[dict] = None) -> list[dict]:
        """LLM decides which tools to call based on current state + agent memory."""
        system = TOOL_USE_SYSTEM.format(
            tool_descriptions=self.env.get_tool_descriptions()
        )

        explored = list(kg.nodes.keys())
        explored_str = ", ".join(explored) if explored else "(none)"

        # Agent Memory: format search history
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

        # Document structure overview (first hop only — zero LLM cost)
        structure_str = ""
        if not search_log:
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
                       already_read: set[str] = None
                       ) -> tuple[list[dict], list[dict]]:
        """
        Execute tool actions. Returns (retrieved_nodes, search_records).
        search_records feed into Agent Memory to prevent keyword repetition.
        """
        if already_read is None:
            already_read = set()

        retrieved = []
        nodes_to_read = set()
        hop_searches = []

        for action in actions:
            tool = action.get("tool", "")

            if tool == "browse":
                doc_id = action.get("doc_id")
                node_id = action.get("node_id")
                depth = action.get("depth", 1)
                results = self.env.browse(doc_id, node_id, depth=depth)
                if results:
                    print(f"   📂 browse({doc_id}, {node_id}, depth={depth}): {len(results)} items")
                    for r in results[:8]:
                        indent = "  " * r.get("depth", 0)
                        print(f"      {indent}[{r['node_id']}] {r['title'][:50]} ({r['n_children']} children)")

            elif tool == "read":
                doc_id = action.get("doc_id", "")
                node_id = action.get("node_id", "")
                nodes_to_read.add((doc_id, node_id))

            elif tool == "search":
                keyword = action.get("keyword", "")
                results = self.env.search(keyword, doc_ids)
                n_results = len(results) if results else 0

                if results:
                    print(f"   🔎 search(\"{keyword}\"): {n_results} matches")
                    for r in results[:3]:
                        print(f"      [{r['doc_id']}::{r['node_id']}] {r['title'][:40]} (score={r.get('score', '?')})")
                    for r in results[:self.top_k]:
                        nodes_to_read.add((r["doc_id"], r["node_id"]))
                else:
                    print(f"   🔎 search(\"{keyword}\"): 0 matches")

                read_nodes = [f"{r['doc_id']}::{r['node_id']}" for r in (results or [])[:self.top_k]]
                hop_searches.append({
                    "keyword": keyword,
                    "n_results": n_results,
                    "read_nodes": read_nodes,
                })

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

        return retrieved, hop_searches

    # -----------------------------------------------------------
    # Collect structured table data for answer context
    # -----------------------------------------------------------
    def _collect_table_context(self, kg) -> str:
        """
        Collect structured table data from all KG nodes' references.
        Tables are passed as text (not images) since structured data
        is already extracted and more reliable than VLM OCR.
        """
        seen = set()
        sections = []
        for nid, node in kg.nodes.items():
            for ref in node.references:
                if ref.get("type") != "table":
                    continue
                ref_id = ref.get("id", "")
                if ref_id in seen:
                    continue
                seen.add(ref_id)
                structured = ref.get("structured_text", "")
                if structured:
                    caption = ref.get("caption", "")
                    sections.append(f"[{ref_id}: {caption}]\n{structured}")
        if not sections:
            return ""
        return "--- Referenced Tables (structured data) ---\n" + "\n\n".join(sections)

    # -----------------------------------------------------------
    # Collect reference images for VLM (Figures only)
    # -----------------------------------------------------------
    def _collect_reference_images(
        self, kg, doc_ids: list[str] | None, question: str = "",
        max_images: int = 6,
    ) -> list[str]:
        """
        Collect referenced Figure images relevant to the question.
        Tables are handled separately via _collect_table_context() as structured text.
        Uses keyword overlap with question to select most relevant figures.
        """
        # Gather figure references only (tables handled as text)
        all_refs = []
        for nid, node in kg.nodes.items():
            for ref in node.references:
                if ref.get("type") == "table":
                    continue  # Tables passed as structured text, not images
                doc_id = node.source_doc
                page = ref.get("page")
                caption = ref.get("caption", "")
                ref_id = ref.get("id", "")
                if doc_id and page:
                    all_refs.append({
                        "doc_id": doc_id,
                        "page": page,
                        "caption": caption,
                        "ref_id": ref_id,
                    })

        if not all_refs:
            return []

        # Deduplicate by (doc_id, page)
        seen = set()
        unique_refs = []
        for ref in all_refs:
            key = (ref["doc_id"], ref["page"])
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)

        # Rank by relevance to question using simple keyword overlap
        question_terms = set(question.lower().split())
        for ref in unique_refs:
            caption_terms = set(ref["caption"].lower().split())
            ref_id_terms = set(ref["ref_id"].lower().replace("-", " ").split())
            overlap = len(question_terms & (caption_terms | ref_id_terms))
            ref["relevance"] = overlap

        unique_refs.sort(key=lambda r: -r["relevance"])
        selected = unique_refs[:max_images]

        if not selected:
            return []

        from src.utils.vision import render_pdf_pages

        # Group by doc_id for batch rendering
        by_doc: dict[str, list[int]] = {}
        for ref in selected:
            by_doc.setdefault(ref["doc_id"], []).append(ref["page"])

        all_images = []
        for doc_id, pages in by_doc.items():
            pdf_path = self.env.documents.get(doc_id, {}).get("pdf_path", "")
            if not pdf_path or not os.path.isfile(pdf_path):
                continue

            rendered = render_pdf_pages(pdf_path, sorted(pages))
            for r in rendered:
                all_images.append(r["base64"])
                # Find caption for this page
                caption = next(
                    (ref["ref_id"] for ref in selected
                     if ref["doc_id"] == doc_id and ref["page"] == r["page"]),
                    ""
                )
                print(f"   📷 Rendered: {doc_id} p.{r['page']} ({caption})")

        return all_images
