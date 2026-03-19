"""
DynamicSubKG: GWM의 Short-term Memory를 담당하는 동적 지식그래프
- NetworkX DiGraph 기반
- 노드: 탐색된 문서 섹션 (텍스트, 표, 이미지)
- 엣지: 섹션 간의 논리적 관계 (REFERENCES, SUPPORTS, SATISFIES 등)
"""

import json
from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


# 지원하는 엣지 관계 타입
RELATION_TYPES = [
    "REFERENCES",        # A가 B를 인용/참조함
    "SUPPORTS",          # A가 B의 주장을 뒷받침함
    "CONTRADICTS",       # A가 B의 내용과 상충함
    "SATISFIES",         # A (결과)가 B (요건)를 만족함
    "VIOLATES",          # A (결과)가 B (요건)를 위반함
    "IS_PREREQUISITE_OF",# A를 이해해야 B를 이해할 수 있음
    "LEADS_TO",          # A (원인)가 B (결과)로 이어짐
    "SPECIFIES",         # A가 B의 세부 사항을 명시함
]


@dataclass
class KGNode:
    """Knowledge graph node - represents a single explored document section"""
    node_id: str
    title: str
    content: str
    summary: str = ""
    modality: str = "text"        # text | table | image
    source_doc: str = ""
    page_range: str = ""
    hop: int = 0
    references: list = field(default_factory=list)  # [{type, id, page, caption}]

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "summary": self.summary,
            "modality": self.modality,
            "source_doc": self.source_doc,
            "page_range": self.page_range,
            "hop": self.hop,
        }


@dataclass
class KGEdge:
    """Knowledge graph edge — relationship between two nodes.
    description: free-form natural language relationship (primary)
    relation: ontology label mapped from description (secondary)
    """
    source_id: str
    target_id: str
    relation: str = "SEMANTIC"
    confidence: float = 1.0
    description: str = ""     # Free-form relationship description (LightRAG-style)
    reasoning: str = ""       # Backward compat alias for description

    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation,
            "confidence": self.confidence,
            "description": self.description or self.reasoning,
        }


class DynamicSubKG:
    """
    GWM의 State(Short-term Memory)에 해당하는 동적 지식그래프.
    
    에이전트의 탐색(Action)과 추론(Transition)을 통해
    빈 그래프 G_0에서 시작하여 점진적으로 구축됩니다.
    """

    def __init__(self, question: str):
        self.graph = nx.DiGraph()
        self.question = question          # 사용자 질의 (탐색의 목적)
        self.nodes: dict[str, KGNode] = {}
        self.edges: list[KGEdge] = []
        self.current_hop = 0

    # -----------------------------------------------------------
    # 노드 관련
    # -----------------------------------------------------------
    def add_node(self, node: KGNode) -> bool:
        """노드 추가. 이미 존재하면 False 반환"""
        if node.node_id in self.nodes:
            return False
        node.hop = self.current_hop
        self.nodes[node.node_id] = node
        self.graph.add_node(
            node.node_id,
            title=node.title,
            modality=node.modality,
            hop=node.hop,
        )
        return True

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def get_node(self, node_id: str) -> Optional[KGNode]:
        return self.nodes.get(node_id)

    # -----------------------------------------------------------
    # 엣지 관련
    # -----------------------------------------------------------
    def add_edge(self, edge: KGEdge) -> bool:
        """엣지 추가. 두 노드가 모두 존재해야 함"""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            return False
        self.edges.append(edge)
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation=edge.relation,
            confidence=edge.confidence,
        )
        return True

    # -----------------------------------------------------------
    # 컨텍스트 생성 (LLM 프롬프트용)
    # -----------------------------------------------------------
    def to_context_string(self, max_content_len: int = 800) -> str:
        """
        현재 KG 상태를 LLM이 읽을 수 있는 텍스트로 변환.
        최종 답변 생성 및 다음 탐색 계획 수립에 사용.
        """
        lines = [f"=== Knowledge Graph constructed so far (Hop {self.current_hop}) ===\n"]
        lines.append(f"[Query] {self.question}\n")
        lines.append(f"[Nodes] {len(self.nodes)}  [Edges] {len(self.edges)}\n")

        lines.append("\n--- Node List ---")
        for nid, node in self.nodes.items():
            # Prefer summary (concise, contains key facts) over truncated content
            if node.summary:
                display_text = node.summary
            else:
                display_text = node.content[:max_content_len] + "..." \
                    if len(node.content) > max_content_len else node.content
            lines.append(
                f"\n[{nid}] ({node.modality}, Hop {node.hop}) {node.title}\n"
                f"  Source: {node.source_doc} p.{node.page_range}\n"
                f"  Summary: {display_text}"
            )

        lines.append("\n\n--- Relationship (Edge) List ---")
        if self.edges:
            for e in self.edges:
                desc = e.description or e.reasoning
                lines.append(
                    f"  [{e.source_id}] --[{e.relation}]--> [{e.target_id}]"
                    f"  (confidence: {e.confidence:.2f})"
                    + (f"\n    {desc}" if desc else "")
                )
        else:
            lines.append("  (no relationships yet)")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON 직렬화"""
        return {
            "question": self.question,
            "current_hop": self.current_hop,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    def __repr__(self):
        return (
            f"DynamicSubKG(hop={self.current_hop}, "
            f"nodes={len(self.nodes)}, edges={len(self.edges)})"
        )
