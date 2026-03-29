# -*- coding: utf-8 -*-
"""RAPTOR 검색기.

두 가지 검색 모드 (RAPTOR 논문 §3.3):
  collapse_tree   — 모든 레벨 노드를 flat하게 검색 (단순, 빠름)
  tree_traversal  — 루트에서 아래로 내려가며 가장 유사한 경로 탐색 (정밀)

config.py의 RETRIEVAL_MODE로 기본값을 변경할 수 있습니다.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
from openai import OpenAI

from .config import RETRIEVAL_MODE, TOP_K
from .embeddings import get_embeddings
from .tree_builder import RAPTORTree

logger = logging.getLogger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / (denom + 1e-10))


class RAPTORRetriever:
    """RAPTOR 검색기.

    초기화 시 모든 노드 임베딩을 미리 계산합니다.
    대규모 인덱스의 경우 FAISS 등으로 교체할 수 있습니다.
    """

    def __init__(self, tree: RAPTORTree, client: OpenAI | None = None) -> None:
        self.tree = tree
        self.client = client or OpenAI()
        self._emb_cache: Dict[str, np.ndarray] = {}
        self._node_map: Dict[str, Dict] = {n["id"]: n for n in tree.all_nodes}
        self._precompute()

    def _precompute(self) -> None:
        """전체 노드 임베딩 사전 계산."""
        nodes = self.tree.all_nodes
        logger.info(f"임베딩 사전 계산: {len(nodes)}개 노드")
        texts = [n["text"] for n in nodes]
        embs  = get_embeddings(texts, self.client)
        for node, emb in zip(nodes, embs):
            self._emb_cache[node["id"]] = emb
        logger.info("임베딩 사전 계산 완료")

    # ── Public ───────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        mode: str = RETRIEVAL_MODE,
    ) -> List[Dict]:
        """쿼리에 가장 관련 있는 노드를 반환.

        Args:
            query:  검색 쿼리
            top_k:  반환 노드 수
            mode:   "collapse_tree" | "tree_traversal"

        Returns:
            노드 dict 리스트 (score 내림차순)
        """
        q_emb = get_embeddings([query], self.client)[0]

        if mode == "collapse_tree":
            return self._collapse_tree(q_emb, top_k)
        elif mode == "tree_traversal":
            return self._tree_traversal(q_emb, top_k)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")

    # ── Private ──────────────────────────────────────────────────

    def _collapse_tree(self, q_emb: np.ndarray, top_k: int) -> List[Dict]:
        """전체 노드 flat 검색."""
        scored = [
            (_cosine(q_emb, self._emb_cache[n["id"]]), n)
            for n in self.tree.all_nodes
            if n["id"] in self._emb_cache
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]

    def _tree_traversal(self, q_emb: np.ndarray, top_k: int) -> List[Dict]:
        """루트 레벨에서 시작, 유사도 높은 자식으로 내려가며 리프 수집."""
        if not self.tree.all_nodes:
            return []

        max_level = max(n.get("level", 0) for n in self.tree.all_nodes)
        if max_level == 0:
            return self._collapse_tree(q_emb, top_k)

        top_per_level = max(2, top_k // max(1, max_level))

        # 최상위 레벨 노드부터 시작
        current = [n for n in self.tree.all_nodes if n.get("level") == max_level]
        collected_leaf_ids: List[str] = []

        while current:
            scored = [
                (_cosine(q_emb, self._emb_cache[n["id"]]), n)
                for n in current
                if n["id"] in self._emb_cache
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            top_nodes = [n for _, n in scored[:top_per_level]]

            next_level: List[Dict] = []
            for node in top_nodes:
                if node.get("is_leaf"):
                    collected_leaf_ids.append(node["id"])
                else:
                    for child_id in node.get("children", []):
                        if child_id in self._node_map:
                            next_level.append(self._node_map[child_id])

            current = next_level

        # 수집된 리프가 없으면 fallback
        if not collected_leaf_ids:
            return self._collapse_tree(q_emb, top_k)

        candidates = [self._node_map[nid] for nid in collected_leaf_ids if nid in self._node_map]
        scored = [
            (_cosine(q_emb, self._emb_cache[n["id"]]), n)
            for n in candidates
            if n["id"] in self._emb_cache
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]
