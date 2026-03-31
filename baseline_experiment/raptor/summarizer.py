# -*- coding: utf-8 -*-
"""클러스터 텍스트 요약 (gpt-4.1).

RAPTOR 트리 구축 시 각 클러스터의 텍스트를 요약하여 상위 노드를 생성합니다.
생성 모델은 비교 공정성을 위해 GENERATION_MODEL (gpt-4.1)로 고정합니다.
"""

from __future__ import annotations

import logging
from typing import List

from openai import OpenAI

from .config import GENERATION_MODEL, TEMPERATURE

logger = logging.getLogger(__name__)

SUMMARIZE_SYSTEM = (
    "You are an expert technical summarizer for nuclear engineering documents. "
    "Summarize the provided text passages into a concise, comprehensive paragraph. "
    "Preserve all technical details, numerical values, component names, and key facts. "
    "Do NOT add information not present in the passages. "
    "Write in English."
)

# 클러스터당 최대 사용 청크 수 (프롬프트 길이 제한)
MAX_CHUNKS_PER_SUMMARY = 10
SUMMARY_MAX_TOKENS = 600


def summarize_cluster(texts: List[str], client: OpenAI | None = None) -> str:
    """청크 텍스트 목록 → 요약 문자열.

    Args:
        texts:  클러스터에 속한 텍스트 리스트
        client: OpenAI 클라이언트

    Returns:
        요약 텍스트
    """
    if client is None:
        client = OpenAI()

    combined = "\n\n---\n\n".join(texts[:MAX_CHUNKS_PER_SUMMARY])

    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM},
            {"role": "user", "content": f"Summarize these passages:\n\n{combined}"},
        ],
        temperature=TEMPERATURE,
        max_tokens=SUMMARY_MAX_TOKENS,
    )
    return response.choices[0].message.content.strip()
