# -*- coding: utf-8 -*-
"""OpenAI 임베딩 유틸리티.

text-embedding-3-small 기준으로 배치 임베딩을 수행합니다.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from openai import OpenAI

from .config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

logger = logging.getLogger(__name__)


def get_embeddings(texts: List[str], client: OpenAI | None = None) -> np.ndarray:
    """텍스트 리스트를 배치로 임베딩.

    Args:
        texts:  임베딩할 텍스트 목록
        client: OpenAI 클라이언트 (None이면 내부 생성)

    Returns:
        shape (len(texts), dim) float32 ndarray
    """
    if client is None:
        client = OpenAI()

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)
        logger.debug(f"  임베딩 배치 {i // EMBEDDING_BATCH_SIZE + 1}: {len(batch)}개 완료")

    return np.array(all_embeddings, dtype=np.float32)
