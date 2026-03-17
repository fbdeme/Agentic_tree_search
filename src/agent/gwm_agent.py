"""
GWMAgent: Graph World Model 기반 다중 홉 문서 탐색 에이전트
- State: DynamicSubKG (동적 지식그래프)
- Action: PageIndex 환경에서 관련 노드 탐색
- Transition: KG에 노드/엣지 추가 + 관계 추론
"""

import json
import os
from typing import Optional
from src.state.knowledge_graph import DynamicSubKG, KGNode, KGEdge
from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.reasoning import ReasoningModule


class GWMAgent:
    """
    GWM State-Action-Transition 루프 구현.
    
    에이전트는 빈 그래프 G_0에서 시작하여
    max_hops 번의 탐색을 통해 점진적으로 KG를 구축합니다.
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
    # 메인 루프: run()
    # -----------------------------------------------------------
    def run(self, question: str, doc_ids: Optional[list[str]] = None) -> dict:
        """
        사용자 질의에 대한 GWM 멀티-홉 추론 실행.

        Returns:
            {
                "answer": str,
                "kg": DynamicSubKG,
                "trajectory": list[str],
                "hops_used": int,
            }
        """
        print(f"\n{'='*60}")
        print(f"🤖 GWM Agent 시작")
        print(f"   질의: {question}")
        print(f"   최대 Hop: {self.max_hops}  |  Top-K: {self.top_k}")
        print(f"{'='*60}\n")

        # G_0: 빈 지식그래프 초기화
        kg = DynamicSubKG(question=question)
        trajectory: list[str] = []
        current_query = question

        for hop in range(1, self.max_hops + 1):
            kg.current_hop = hop
            print(f"\n🔍 [Hop {hop}/{self.max_hops}] 탐색 시작")
            print(f"   현재 KG: {kg}")

            # ── Action: 탐색 계획 수립 ──────────────────────────────
            if hop > 1:
                tree_summary = self.env.get_tree_summary(doc_ids)
                current_query = self.reasoning.plan_next_search(
                    question=question,
                    kg_context=kg.to_context_string(max_content_len=400),
                    tree_summary=tree_summary[:2000],
                )
                print(f"   📋 다음 탐색 쿼리: {current_query}")

            # ── Action: PageIndex 환경 탐색 ────────────────────────
            retrieved = self.env.search_relevant_nodes(
                query=current_query,
                doc_ids=doc_ids,
                top_k=self.top_k,
                exclude_node_ids=set(kg.nodes.keys()),
            )
            if not retrieved:
                print(f"   ⚠️  Hop {hop}: 관련 노드를 찾지 못했습니다.")
                trajectory.append(f"Hop {hop}: 관련 섹션 없음 (쿼리: {current_query})")
                continue

            hop_log = []
            new_nodes: list[KGNode] = []

            # ── Transition: KG 노드 추가 ───────────────────────────
            for r in retrieved:
                node_id = f"{r['doc_id']}_{r['node_id']}"
                if kg.has_node(node_id):
                    print(f"   ↩️  이미 탐색된 노드 스킵: [{node_id}]")
                    continue

                # 요약 생성
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
                added = kg.add_node(new_node)
                if added:
                    new_nodes.append(new_node)
                    hop_log.append(f"노드 추가: [{node_id}] {r['title']}")
                    print(f"   ✅ 노드 추가: [{node_id}] {r['title'][:50]}")
                    print(f"      요약: {summary[:100]}")

            # ── Transition: 엣지 생성 (관계 추론) ─────────────────
            # 비교 대상 쌍 수집: (new↔existing) + (new↔new)
            existing_nodes = [
                n for nid, n in kg.nodes.items() if nid not in [nn.node_id for nn in new_nodes]
            ]

            pairs_to_compare = []
            # 1) 새 노드 ↔ 기존 노드 (기존 노드 최대 3개)
            for new_node in new_nodes:
                for existing_node in existing_nodes[:3]:
                    pairs_to_compare.append((new_node, existing_node))
            # 2) 새 노드 ↔ 새 노드 (Hop 1에서도 관계 추론 보장)
            for i, na in enumerate(new_nodes):
                for nb in new_nodes[i + 1:]:
                    pairs_to_compare.append((na, nb))

            for node_a, node_b in pairs_to_compare:
                rel_result = self.reasoning.infer_relation(
                    node_a_title=node_a.title,
                    node_a_content=node_a.content,
                    node_b_title=node_b.title,
                    node_b_content=node_b.content,
                    question=question,
                )
                relation = rel_result.get("relation", "NONE")
                confidence = rel_result.get("confidence", 0.5)
                reasoning_text = rel_result.get("reasoning", "")

                if relation != "NONE" and confidence >= 0.4:
                    edge = KGEdge(
                        source_id=node_a.node_id,
                        target_id=node_b.node_id,
                        relation=relation,
                        confidence=confidence,
                        reasoning=reasoning_text,
                    )
                    if kg.add_edge(edge):
                        hop_log.append(
                            f"edge: [{node_a.node_id}] --{relation}--> [{node_b.node_id}]"
                        )
                        print(
                            f"   🔗 Edge: [{node_a.node_id[:25]}] "
                            f"--{relation}({confidence:.2f})--> [{node_b.node_id[:25]}]"
                        )

            trajectory.append(f"Hop {hop}: " + " | ".join(hop_log) if hop_log else f"Hop {hop}: 신규 노드 없음")

        # ── Collect referenced Figure/Table images ────────────────
        reference_images = self._collect_reference_images(kg, doc_ids)

        # ── Generate final answer ────────────────────────────────
        print(f"\n{'='*60}")
        print(f"📝 Generating final answer...")
        print(f"   Final KG: {kg}")
        if reference_images:
            print(f"   📷 Referenced images: {len(reference_images)}")
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
            "hops_used": self.max_hops,
        }

    def _collect_reference_images(
        self, kg, doc_ids: list[str] | None, max_images: int = 6
    ) -> list[str]:
        """
        Collect unique referenced Figure/Table page images from all KG nodes.
        Returns list of base64-encoded JPEG images.
        """
        # Gather unique (doc_id, page) pairs from references
        ref_pages: dict[str, set[int]] = {}  # doc_id -> set of page numbers
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

        # Render images using PDF paths from environment
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
