"""
PageIndexEnvironment: PageIndex 오픈소스를 활용한 문서 탐색 환경
- PDF → 계층적 트리 인덱스 생성 (pageindex_core 사용)
- 트리를 순회하여 관련 노드 탐색
- GWM의 World(Environment) 역할
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# pageindex_core 경로 추가 (프로젝트 루트에서 상대 경로)
PAGEINDEX_PATH = Path(__file__).parent.parent.parent / "pageindex_core"
sys.path.insert(0, str(PAGEINDEX_PATH))


class PageIndexEnvironment:
    """
    PageIndex 기반의 문서 탐색 환경.
    
    GWM의 World에 해당하며, 에이전트의 Action을 받아
    관련 문서 섹션(Observation)을 반환합니다.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.documents: dict[str, dict] = {}  # doc_id -> tree 구조
        self.node_cache: dict[str, dict] = {}  # node_id -> node dict

    # -----------------------------------------------------------
    # 문서 등록
    # -----------------------------------------------------------
    def register_tree(self, doc_id: str, tree: list, doc_name: str = "") -> None:
        """
        이미 생성된 PageIndex 트리를 환경에 등록합니다.
        (JSON 파일로 저장된 트리를 로드할 때 사용)
        """
        self.documents[doc_id] = {
            "tree": tree,
            "name": doc_name or doc_id,
        }
        # 모든 노드를 플랫하게 캐싱
        self._cache_nodes(doc_id, tree)
        print(f"[Environment] 문서 등록됨: {doc_id} ({len(self.node_cache)} 노드 캐싱)")

    def _cache_nodes(self, doc_id: str, nodes: list, depth: int = 0) -> None:
        """트리를 DFS로 순회하며 모든 노드를 캐싱"""
        for node in nodes:
            nid = node.get("node_id", "")
            if nid:
                self.node_cache[f"{doc_id}::{nid}"] = {
                    **node,
                    "doc_id": doc_id,
                    "depth": depth,
                }
            sub = node.get("nodes", [])
            if sub:
                self._cache_nodes(doc_id, sub, depth + 1)

    # -----------------------------------------------------------
    # 트리 요약 (LLM 탐색 계획 수립용)
    # -----------------------------------------------------------
    def get_tree_summary(self, doc_ids: Optional[list[str]] = None) -> str:
        """
        등록된 문서(들)의 트리 구조를 LLM이 읽기 쉬운 텍스트로 변환.
        에이전트가 다음 탐색 계획을 세울 때 사용.
        """
        if doc_ids is None:
            doc_ids = list(self.documents.keys())

        lines = []
        for doc_id in doc_ids:
            if doc_id not in self.documents:
                continue
            doc = self.documents[doc_id]
            lines.append(f"\n📄 문서: {doc['name']} (id={doc_id})")
            lines.append(self._tree_to_text(doc["tree"], indent=0))
        return "\n".join(lines)

    def _tree_to_text(self, nodes: list, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        for node in nodes:
            nid = node.get("node_id", "?")
            title = node.get("title", "Untitled")
            summary = node.get("summary", "")[:100]
            page = node.get("page_index") or node.get("start_index", "?")
            lines.append(f"{prefix}[{nid}] p.{page} {title}")
            if summary:
                lines.append(f"{prefix}    → {summary}")
            sub = node.get("nodes", [])
            if sub:
                lines.append(self._tree_to_text(sub, indent + 1))
        return "\n".join(lines)

    # -----------------------------------------------------------
    # 노드 탐색 (핵심: GWM Action → Observation)
    # -----------------------------------------------------------
    def search_relevant_nodes(
        self,
        query: str,
        doc_ids: Optional[list[str]] = None,
        top_k: int = 3,
    ) -> list[dict]:
        """
        쿼리에 가장 관련도 높은 노드를 트리에서 선택합니다.
        GPT가 트리 구조를 보고 가장 관련있는 node_id를 선택 (Agentic Retrieval).
        
        Returns:
            [{"node_id": "...", "doc_id": "...", "title": "...", "content": "..."}, ...]
        """
        if doc_ids is None:
            doc_ids = list(self.documents.keys())

        tree_summary = self.get_tree_summary(doc_ids)

        prompt = (
            f"다음은 문서의 계층적 트리 구조입니다:\n{tree_summary}\n\n"
            f"검색 쿼리: {query}\n\n"
            f"위 쿼리와 가장 관련성 높은 노드 최대 {top_k}개를 선택하세요.\n"
            f"응답은 반드시 JSON 배열로만 출력하세요:\n"
            f'[{{"doc_id": "...", "node_id": "...", "reason": "선택 이유"}}]'
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "당신은 기술 문서 탐색 전문가입니다. 쿼리와 가장 관련있는 섹션을 정확히 선택하세요.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            selections = json.loads(cleaned)
        except Exception:
            return []

        results = []
        for sel in selections:
            doc_id = sel.get("doc_id", "")
            node_id = sel.get("node_id", "")
            cache_key = f"{doc_id}::{node_id}"
            if cache_key in self.node_cache:
                node = self.node_cache[cache_key]
                results.append(
                    {
                        "doc_id": doc_id,
                        "node_id": node_id,
                        "title": node.get("title", ""),
                        "content": node.get("text", node.get("summary", "")),
                        "page_range": f"{node.get('start_index', node.get('page_index', '?'))}",
                        "reason": sel.get("reason", ""),
                    }
                )
        return results

    def get_node_content(self, doc_id: str, node_id: str) -> Optional[dict]:
        """특정 node_id의 전체 내용 반환"""
        cache_key = f"{doc_id}::{node_id}"
        return self.node_cache.get(cache_key)

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    @property
    def node_count(self) -> int:
        return len(self.node_cache)
