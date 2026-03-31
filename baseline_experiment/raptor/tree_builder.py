# -*- coding: utf-8 -*-
"""RAPTOR 재귀 트리 구축.

알고리즘 (Sarthi et al. 2024):
  Level 0  — 원본 텍스트 청크 (리프 노드)
  Level L  — Level L-1 노드를 UMAP+GMM으로 클러스터링 → 각 클러스터 요약 → 요약 노드
  반복:      노드 수가 MIN_CLUSTER_SIZE * 2 미만이 되거나 MAX_LEVELS에 도달하면 중단
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

from openai import OpenAI

from .config import MAX_LEVELS, MIN_CLUSTER_SIZE, INDEX_DIR
from .embeddings import get_embeddings
from .clustering import cluster_embeddings
from .summarizer import summarize_cluster

logger = logging.getLogger(__name__)


class RAPTORTree:
    """RAPTOR 다단계 요약 트리.

    Attributes:
        all_nodes:   모든 레벨 노드 (leaf + summary)
        leaf_nodes:  Level 0 원본 청크만
    """

    def __init__(self) -> None:
        self.all_nodes: List[Dict[str, Any]] = []
        self.leaf_nodes: List[Dict[str, Any]] = []

    # ── 구축 ────────────────────────────────────────────────────

    def build(self, leaf_chunks: List[Dict], client: OpenAI | None = None) -> None:
        """리프 청크에서 재귀적으로 트리를 구축합니다.

        Args:
            leaf_chunks: pdf_extractor.extract_chunks_from_pdf() 출력
            client:      OpenAI 클라이언트
        """
        if client is None:
            client = OpenAI()

        self.leaf_nodes = list(leaf_chunks)
        self.all_nodes = list(leaf_chunks)

        current_level_nodes = leaf_chunks

        for level in range(1, MAX_LEVELS + 1):
            n = len(current_level_nodes)
            if n < MIN_CLUSTER_SIZE * 2:
                logger.info(f"Level {level}: 노드 {n}개 < {MIN_CLUSTER_SIZE * 2}, 트리 완성")
                break

            logger.info(f"Level {level}: {n}개 노드 임베딩 + 클러스터링...")
            texts = [node["text"] for node in current_level_nodes]
            embeddings = get_embeddings(texts, client)

            cluster_labels, _ = cluster_embeddings(embeddings)

            # 클러스터 인덱스 → 노드 인덱스 매핑
            cluster_map: Dict[int, List[int]] = {}
            for node_idx, labels in enumerate(cluster_labels):
                for cluster_id in labels:
                    cluster_map.setdefault(cluster_id, []).append(node_idx)

            new_nodes: List[Dict] = []
            for cluster_id, node_indices in sorted(cluster_map.items()):
                if len(node_indices) < MIN_CLUSTER_SIZE:
                    continue

                child_texts = [current_level_nodes[i]["text"] for i in node_indices]
                child_ids   = [current_level_nodes[i]["id"]   for i in node_indices]

                logger.info(f"  Cluster {cluster_id}: {len(node_indices)}개 → 요약 생성")
                summary = summarize_cluster(child_texts, client)

                summary_node: Dict[str, Any] = {
                    "id":       f"summary_L{level}_C{cluster_id:04d}",
                    "text":     summary,
                    "level":    level,
                    "is_leaf":  False,
                    "children": child_ids,
                }
                new_nodes.append(summary_node)

            if not new_nodes:
                logger.info(f"Level {level}: 생성된 요약 노드 없음, 중단")
                break

            self.all_nodes.extend(new_nodes)
            current_level_nodes = new_nodes
            logger.info(f"Level {level} 완성: {len(new_nodes)}개 요약 노드 추가")

        logger.info(
            f"트리 구축 완료 — 전체 {len(self.all_nodes)}개 노드 "
            f"(리프: {len(self.leaf_nodes)}, 요약: {len(self.all_nodes) - len(self.leaf_nodes)})"
        )

    # ── 직렬화 ──────────────────────────────────────────────────

    def save(self, path: str | None = None) -> str:
        """트리를 JSON 파일로 저장."""
        if path is None:
            INDEX_DIR.mkdir(parents=True, exist_ok=True)
            path = str(INDEX_DIR / "raptor_tree.json")

        data = {
            "total_nodes": len(self.all_nodes),
            "leaf_count":  len(self.leaf_nodes),
            "summary_count": len(self.all_nodes) - len(self.leaf_nodes),
            "nodes": self.all_nodes,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, path: str) -> "RAPTORTree":
        """저장된 JSON에서 트리 복원."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tree = cls()
        tree.all_nodes = data["nodes"]
        tree.leaf_nodes = [n for n in tree.all_nodes if n.get("is_leaf", False)]
        return tree
