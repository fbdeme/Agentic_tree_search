"""
GWMAgent: Graph World Model 기반 다중 홉 문서 탐색 에이전트
- State: DynamicSubKG (동적 지식그래프)
- Action: PageIndex 환경에서 관련 노드 탐색
- Transition: KG에 노드/엣지 추가 + 관계 추론
"""

import json
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
        model: str = "gpt-4o-mini",
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
                )
                added = kg.add_node(new_node)
                if added:
                    new_nodes.append(new_node)
                    hop_log.append(f"노드 추가: [{node_id}] {r['title']}")
                    print(f"   ✅ 노드 추가: [{node_id}] {r['title'][:50]}")
                    print(f"      요약: {summary[:100]}")

            # ── Transition: 엣지 생성 (관계 추론) ─────────────────
            existing_nodes = [
                n for nid, n in kg.nodes.items() if nid not in [nn.node_id for nn in new_nodes]
            ]

            for new_node in new_nodes:
                for existing_node in existing_nodes[:3]:  # 최대 3개와 비교
                    rel_result = self.reasoning.infer_relation(
                        node_a_title=new_node.title,
                        node_a_content=new_node.content,
                        node_b_title=existing_node.title,
                        node_b_content=existing_node.content,
                        question=question,
                    )
                    relation = rel_result.get("relation", "NONE")
                    confidence = rel_result.get("confidence", 0.5)
                    reasoning_text = rel_result.get("reasoning", "")

                    if relation != "NONE" and confidence >= 0.4:
                        edge = KGEdge(
                            source_id=new_node.node_id,
                            target_id=existing_node.node_id,
                            relation=relation,
                            confidence=confidence,
                            reasoning=reasoning_text,
                        )
                        if kg.add_edge(edge):
                            hop_log.append(
                                f"엣지: [{new_node.node_id}] --{relation}--> [{existing_node.node_id}]"
                            )
                            print(
                                f"   🔗 관계 추론: [{new_node.node_id[:20]}] "
                                f"--{relation}({confidence:.2f})--> [{existing_node.node_id[:20]}]"
                            )
                            print(f"      근거: {reasoning_text[:100]}")

            # 기존 노드에도 추가: 새 노드들 끼리 관계 추론
            if len(new_nodes) > 1:
                for i, na in enumerate(new_nodes):
                    for nb in new_nodes[i + 1:]:
                        rel_result = self.reasoning.infer_relation(
                            node_a_title=na.title,
                            node_a_content=na.content,
                            node_b_title=nb.title,
                            node_b_content=nb.content,
                            question=question,
                        )
                        relation = rel_result.get("relation", "NONE")
                        confidence = rel_result.get("confidence", 0.5)
                        if relation != "NONE" and confidence >= 0.4:
                            edge = KGEdge(
                                source_id=na.node_id,
                                target_id=nb.node_id,
                                relation=relation,
                                confidence=rel_result.get("confidence", 0.5),
                                reasoning=rel_result.get("reasoning", ""),
                            )
                            kg.add_edge(edge)

            trajectory.append(f"Hop {hop}: " + " | ".join(hop_log) if hop_log else f"Hop {hop}: 신규 노드 없음")

        # ── 최종 답변 생성 ────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"📝 최종 답변 생성 중...")
        print(f"   최종 KG: {kg}")
        print(f"{'='*60}")

        answer = self.reasoning.generate_answer(
            question=question,
            kg_context=kg.to_context_string(),
            trajectory=trajectory,
        )

        return {
            "answer": answer,
            "kg": kg,
            "trajectory": trajectory,
            "hops_used": self.max_hops,
        }
