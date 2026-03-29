# -*- coding: utf-8 -*-
"""UMAP 차원 축소 + GMM 클러스터링.

RAPTOR 논문(Sarthi et al. 2024)의 클러스터링 방식을 따릅니다:
  1. UMAP으로 고차원 임베딩 → 저차원 축소
  2. BIC 기준으로 최적 k 탐색
  3. GMM soft assignment — probability ≥ GMM_THRESHOLD 클러스터 모두 배정
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np
from sklearn.mixture import GaussianMixture
import umap

from .config import UMAP_N_COMPONENTS, UMAP_N_NEIGHBORS, GMM_MAX_CLUSTERS, GMM_THRESHOLD

logger = logging.getLogger(__name__)


def cluster_embeddings(
    embeddings: np.ndarray,
    n_clusters: int | None = None,
) -> Tuple[List[List[int]], np.ndarray]:
    """임베딩을 클러스터링하여 각 샘플의 소속 클러스터 목록 반환.

    Args:
        embeddings:  shape (n, dim)
        n_clusters:  강제 지정 시 BIC 탐색 생략

    Returns:
        labels:  List[List[int]] — 각 샘플이 속하는 클러스터 인덱스 목록 (soft)
        reduced: UMAP 축소 결과 (n, n_components)
    """
    n_samples = len(embeddings)

    if n_samples < 3:
        return [[0]] * n_samples, embeddings

    # ── UMAP ────────────────────────────────────────────────────
    n_comp = min(UMAP_N_COMPONENTS, n_samples - 1)
    n_neighbors = min(UMAP_N_NEIGHBORS, n_samples - 1)
    logger.debug(f"  UMAP: {n_samples} samples → {n_comp}d (neighbors={n_neighbors})")

    reducer = umap.UMAP(
        n_components=n_comp,
        n_neighbors=n_neighbors,
        random_state=42,
        low_memory=True,
    )
    reduced = reducer.fit_transform(embeddings)

    # ── BIC로 최적 k 탐색 ────────────────────────────────────────
    if n_clusters is None:
        max_k = min(GMM_MAX_CLUSTERS, n_samples // 2)
        max_k = max(max_k, 2)
        best_k, best_bic = 2, float("inf")

        for k in range(2, max_k + 1):
            gmm = GaussianMixture(n_components=k, random_state=42, max_iter=200)
            try:
                gmm.fit(reduced)
                bic = gmm.bic(reduced)
                if bic < best_bic:
                    best_bic, best_k = bic, k
            except Exception:
                break

        n_clusters = best_k
        logger.debug(f"  BIC 최적 k={n_clusters}")

    # ── GMM soft assignment ──────────────────────────────────────
    gmm = GaussianMixture(n_components=n_clusters, random_state=42, max_iter=300)
    gmm.fit(reduced)
    probs = gmm.predict_proba(reduced)  # (n, k)

    labels: List[List[int]] = []
    for prob in probs:
        assigned = [c for c, p in enumerate(prob) if p >= GMM_THRESHOLD]
        if not assigned:
            assigned = [int(np.argmax(prob))]
        labels.append(assigned)

    return labels, reduced
