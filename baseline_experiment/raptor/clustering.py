# -*- coding: utf-8 -*-
"""UMAP 차원 축소 + GMM 클러스터링 (2단계).

RAPTOR 원논문(Sarthi et al. 2024) cluster_utils.py 구현을 따릅니다:

  Global clustering:
    - UMAP n_neighbors = int((n - 1) ** 0.5)   ← 논문 원본
    - UMAP n_components = 10, metric = "cosine"
    - GMM + BIC로 최적 k 탐색
    - Soft assignment: prob ≥ GMM_THRESHOLD (=0.1)

  Local clustering (각 global cluster 내부):
    - UMAP n_neighbors = 10                     ← 논문 원본
    - 동일 metric / n_components
    - 동일 GMM 방식

  결합: 각 노드는 (global_id, local_id) 쌍의 고유 cluster_id에 배정됩니다.
  cluster_id는 트리 구축 시 요약 노드 식별에 사용됩니다.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict

import numpy as np
from sklearn.mixture import GaussianMixture
import umap

from .config import UMAP_N_COMPONENTS, UMAP_METRIC, GMM_MAX_CLUSTERS, GMM_THRESHOLD

logger = logging.getLogger(__name__)


# ── 저수준 유틸 ──────────────────────────────────────────────────

def _reduce_umap(embeddings: np.ndarray, n_neighbors: int) -> np.ndarray:
    """UMAP 차원 축소. 충분한 샘플이 없으면 원본 반환."""
    n = len(embeddings)
    if n < 3:
        return embeddings

    n_comp = min(UMAP_N_COMPONENTS, n - 2)
    n_nb   = min(n_neighbors, n - 2)

    reducer = umap.UMAP(
        n_components=n_comp,
        n_neighbors=n_nb,
        metric=UMAP_METRIC,
        random_state=42,
        low_memory=True,
    )
    return reducer.fit_transform(embeddings)


def _gmm_soft_labels(reduced: np.ndarray) -> List[List[int]]:
    """BIC 최적 k를 찾아 GMM soft assignment 수행.

    Returns:
        labels[i] = 샘플 i가 속하는 클러스터 인덱스 목록
    """
    n = len(reduced)
    if n < 2:
        return [[0]] * n

    max_k = max(2, min(GMM_MAX_CLUSTERS, n // 2))
    best_k, best_bic = 2, float("inf")

    for k in range(2, max_k + 1):
        gmm = GaussianMixture(n_components=k, random_state=42, max_iter=300)
        try:
            gmm.fit(reduced)
            bic = gmm.bic(reduced)
            if bic < best_bic:
                best_bic, best_k = bic, k
        except Exception:
            break

    logger.debug(f"  BIC 최적 k={best_k}")
    gmm = GaussianMixture(n_components=best_k, random_state=42, max_iter=300)
    gmm.fit(reduced)
    probs = gmm.predict_proba(reduced)   # (n, best_k)

    labels: List[List[int]] = []
    for prob in probs:
        assigned = [c for c, p in enumerate(prob) if p >= GMM_THRESHOLD]
        if not assigned:
            assigned = [int(np.argmax(prob))]
        labels.append(assigned)

    return labels


# ── 공개 API ─────────────────────────────────────────────────────

def cluster_embeddings(embeddings: np.ndarray) -> Tuple[List[List[int]], np.ndarray]:
    """Global + Local 2단계 UMAP+GMM 클러스터링.

    Args:
        embeddings: shape (n, dim)

    Returns:
        labels:  List[List[int]] — 각 샘플의 최종 클러스터 ID 목록 (복수 가능)
        reduced: Global UMAP 축소 결과 (디버깅·시각화용)
    """
    n = len(embeddings)

    if n < 4:
        # 샘플이 너무 적으면 단일 클러스터
        return [list(range(n))] * n, embeddings.copy()

    # ── Step 1: Global clustering ────────────────────────────────
    global_n_neighbors = max(2, int((n - 1) ** 0.5))
    logger.debug(f"  Global UMAP: {n} samples, n_neighbors={global_n_neighbors}")

    global_reduced = _reduce_umap(embeddings, n_neighbors=global_n_neighbors)
    global_labels  = _gmm_soft_labels(global_reduced)

    # global cluster → 소속 인덱스 매핑
    global_map: Dict[int, List[int]] = {}
    for idx, glabels in enumerate(global_labels):
        for g in glabels:
            global_map.setdefault(g, []).append(idx)

    # ── Step 2: Local clustering within each global cluster ──────
    # 각 global cluster 내부에서 local UMAP+GMM 수행
    # 결합 cluster_id = global_id * 1000 + local_id (충돌 방지용 상수)
    final_labels: List[List[int]] = [[] for _ in range(n)]
    cluster_offset = 0

    for g_id, g_indices in sorted(global_map.items()):
        g_embs = embeddings[g_indices]

        if len(g_indices) < 4:
            # 너무 작은 global cluster: local clustering 생략, 단일 클러스터
            for idx in g_indices:
                final_labels[idx].append(cluster_offset)
            cluster_offset += 1
            continue

        local_n_neighbors = 10   # 원논문 고정값
        logger.debug(f"  Local UMAP: global_cluster={g_id}, {len(g_indices)} samples")

        local_reduced = _reduce_umap(g_embs, n_neighbors=local_n_neighbors)
        local_labels  = _gmm_soft_labels(local_reduced)

        # local cluster_id를 전역 고유 ID로 변환
        local_ids_seen: Dict[int, int] = {}
        for pos, llabels in enumerate(local_labels):
            orig_idx = g_indices[pos]
            for l_id in llabels:
                if l_id not in local_ids_seen:
                    local_ids_seen[l_id] = cluster_offset
                    cluster_offset += 1
                final_labels[orig_idx].append(local_ids_seen[l_id])

    # 한 번도 배정되지 않은 샘플 처리 (방어 코드)
    for i, fl in enumerate(final_labels):
        if not fl:
            final_labels[i] = [cluster_offset]
            cluster_offset += 1

    logger.info(
        f"  클러스터링 완료: {n}개 노드 → {cluster_offset}개 클러스터 "
        f"(global={len(global_map)})"
    )
    return final_labels, global_reduced
