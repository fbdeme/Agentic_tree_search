# -*- coding: utf-8 -*-
"""RAPTOR 검색기.

두 가지 검색 모드 (RAPTOR 논문 §3.3):
  collapse_tree   — 모든 레벨 노드를 flat하게 검색. 실험적으로 더 나은 성능.
                    cosine similarity 기준으로 정렬 후 CONTEXT_TOKEN_BUDGET 내에서 선택.
  tree_traversal  — 루트부터 아래로 내려가며 경로 탐색.

컨텍스트 조합 방식 (원논문):
  - 유사도 내림차순으로 노드 추가
  - 누적 토큰 수가 CONTEXT_TOKEN_BUDGET(=2000)에 도달하면 중단
  - 이 방식이 TOP_K 고정보다 더 faithful한 구현
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np
import tiktoken
from openai import OpenAI

from .config import CONTEXT_TOKEN_BUDGET, RETRIEVAL_MODE, TOP_K
from .embeddings import get_embeddings
from .tree_builder import RAPTORTree

logger = logging.getLogger(__name__)

_enc = tiktoken.get_encoding("cl100k_base")


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / (denom + 1e-10))


class RAPTORRetriever:
    """RAPTOR 검색기.

    초기화 시 모든 노드 임베딩을 미리 계산합니다.
    """

    def __init__(self, tree: RAPTORTree, client: OpenAI | None = None) -> None:
        self.tree   = tree
        self.client = client or OpenAI()
        self._emb_cache: Dict[str, np.ndarray] = {}
        self._node_map:  Dict[str, Dict]        = {n["id"]: n for n in tree.all_nodes}
        self._precompute()

    def _precompute(self) -> None:
        """전체 노드 임베딩 사전 계산 (인덱스 로드 직후 1회 실행)."""
        nodes = self.tree.all_nodes
        logger.info(f"임베딩 사전 계산: {len(nodes)}개 노드...")
        texts = [n["text"] for n in nodes]
        embs  = get_embeddings(texts, self.client)
        for node, emb in zip(nodes, embs):
            self._emb_cache[node["id"]] = emb
        logger.info("임베딩 사전 계산 완료")

    # ── Public ───────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        mode: str = RETRIEVAL_MODE,
        token_budget: int = CONTEXT_TOKEN_BUDGET,
    ) -> Tuple[List[Dict], str]:
        """쿼리에 가장 관련 있는 노드를 반환하고 컨텍스트 문자열을 구성.

        Args:
            query:        검색 쿼리
            mode:         "collapse_tree" | "tree_traversal"
            token_budget: 컨텍스트 최대 토큰 수 (원논문 기준 2000)

        Returns:
            (nodes, context_text)  — 선택된 노드 목록 + 조합된 컨텍스트 문자열
        """
        q_emb = get_embeddings([query], self.client)[0]

        if mode == "collapse_tree":
            ranked = self._collapse_tree_ranked(q_emb)
        elif mode == "tree_traversal":
            ranked = self._tree_traversal_ranked(q_emb)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")

        # 토큰 예산 내에서 노드 선택
        selected, context = self._budget_select(ranked, token_budget)
        return selected, context

    # ── Private ──────────────────────────────────────────────────

    def _collapse_tree_ranked(self, q_emb: np.ndarray) -> List[Tuple[float, Dict]]:
        """전체 노드 flat 검색 → (score, node) 내림차순 정렬."""
        scored = [
            (_cosine(q_emb, self._emb_cache[n["id"]]), n)
            for n in self.tree.all_nodes
            if n["id"] in self._emb_cache
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _tree_traversal_ranked(self, q_emb: np.ndarray) -> List[Tuple[float, Dict]]:
        """루트 레벨에서 시작, 유사도 높은 자식으로 내려가며 리프 수집."""
        if not self.tree.all_nodes:
            return []

        max_level = max(n.get("level", 0) for n in self.tree.all_nodes)
        if max_level == 0:
            return self._collapse_tree_ranked(q_emb)

        top_per_level = max(2, TOP_K // max(1, max_level))
        current = [n for n in self.tree.all_nodes if n.get("level") == max_level]
        collected: List[str] = []

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
                    collected.append(node["id"])
                else:
                    for child_id in node.get("children", []):
                        if child_id in self._node_map:
                            next_level.append(self._node_map[child_id])
            current = next_level

        if not collected:
            return self._collapse_tree_ranked(q_emb)

        candidates = [self._node_map[nid] for nid in collected if nid in self._node_map]
        scored = [
            (_cosine(q_emb, self._emb_cache[n["id"]]), n)
            for n in candidates
            if n["id"] in self._emb_cache
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _budget_select(
        self, ranked: List[Tuple[float, Dict]], budget: int
    ) -> Tuple[List[Dict], str]:
        """유사도 순으로 노드를 추가하되 토큰 예산 초과 시 중단.

        원논문: "top nodes are selected until we have reached the
                 set maximum number of tokens" (~2000)

        Returns:
            (selected_nodes, context_string)
        """
        selected: List[Dict] = []
        total_tokens = 0
        parts: List[str] = []

        for _, node in ranked:
            t = len(_enc.encode(node["text"]))
            if total_tokens + t > budget and selected:
                break
            selected.append(node)
            total_tokens += t
            parts.append(node["text"])

        # 최소 1개는 보장
        if not selected and ranked:
            selected = [ranked[0][1]]
            parts    = [ranked[0][1]["text"]]

        context = "\n\n---\n\n".join(parts)
        return selected, context
