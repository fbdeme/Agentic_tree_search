# -*- coding: utf-8 -*-
"""PDF → 문장 경계를 존중하는 100-token 텍스트 청크 추출.

RAPTOR 원논문(Sarthi et al. 2024, §3):
  "We first segment each document into chunks of 100 tokens,
   making sure to not cut any sentences in half."

구현 전략:
  1. PyMuPDF로 페이지별 텍스트 추출
  2. 간단한 문장 분리 (마침표/줄바꿈 기준)
  3. 문장 단위로 100-token 버킷에 채움 — 문장을 자르지 않음
  4. 어떤 단일 문장이 100 토큰을 넘으면 그 문장 전체를 하나의 청크로 사용
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict

import fitz  # PyMuPDF
import tiktoken

from .config import CHUNK_SIZE

logger = logging.getLogger(__name__)

_SENT_RE = re.compile(r'(?<=[.!?])\s+')   # 문장 경계 분리 패턴


def extract_chunks_from_pdf(pdf_path: str, doc_id: str) -> List[Dict]:
    """PDF 파일을 RAPTOR 스타일 청크 리스트로 변환.

    Args:
        pdf_path: PDF 파일 경로
        doc_id:   문서 식별자 (예: "nuscale_ch01")

    Returns:
        List of chunk dicts::

            {
                "id":      "nuscale_ch01_chunk_0000",
                "doc_id":  "nuscale_ch01",
                "text":    "...",
                "pages":   [3, 4],
                "level":   0,
                "is_leaf": True,
            }
    """
    enc = tiktoken.get_encoding("cl100k_base")

    doc = fitz.open(pdf_path)
    # 페이지별 텍스트 + 페이지 번호 수집
    page_sentences: List[Dict] = []   # {"sentences": [...], "page": N}
    for page_num, page in enumerate(doc, start=1):
        raw = page.get_text().strip()
        if not raw:
            continue
        # 문장 분리
        sents = [s.strip() for s in _SENT_RE.split(raw) if s.strip()]
        if sents:
            page_sentences.append({"sentences": sents, "page": page_num})
    doc.close()
    logger.info(f"  [{doc_id}] {len(page_sentences)} 페이지 추출 완료")

    # ── 100-token 버킷 채우기 ──────────────────────────────────
    chunks: List[Dict] = []
    chunk_id = 0

    buffer_tokens: List[int] = []
    buffer_pages:  List[int] = []

    for page_info in page_sentences:
        for sent in page_info["sentences"]:
            sent_tokens = enc.encode(sent)

            # 단일 문장이 CHUNK_SIZE 초과 → 그 자체로 하나의 청크
            if len(sent_tokens) > CHUNK_SIZE:
                # 버퍼 비우기
                if buffer_tokens:
                    chunks.append(_make_chunk(enc, buffer_tokens, buffer_pages, doc_id, chunk_id))
                    chunk_id += 1
                    buffer_tokens = []
                    buffer_pages  = []
                # 긴 문장 청크
                chunks.append(_make_chunk(enc, sent_tokens, [page_info["page"]], doc_id, chunk_id))
                chunk_id += 1
                continue

            # 버퍼에 넣으면 초과 → 현재 버퍼를 청크로 저장 후 새 버퍼
            if len(buffer_tokens) + len(sent_tokens) > CHUNK_SIZE and buffer_tokens:
                chunks.append(_make_chunk(enc, buffer_tokens, buffer_pages, doc_id, chunk_id))
                chunk_id += 1
                buffer_tokens = []
                buffer_pages  = []

            buffer_tokens.extend(sent_tokens)
            if page_info["page"] not in buffer_pages:
                buffer_pages.append(page_info["page"])

    # 남은 버퍼
    if buffer_tokens:
        chunks.append(_make_chunk(enc, buffer_tokens, buffer_pages, doc_id, chunk_id))

    logger.info(f"  [{doc_id}] {len(chunks)} 청크 생성 (CHUNK_SIZE={CHUNK_SIZE} tokens)")
    return chunks


def _make_chunk(enc, tokens: List[int], pages: List[int], doc_id: str, chunk_id: int) -> Dict:
    return {
        "id":      f"{doc_id}_chunk_{chunk_id:04d}",
        "doc_id":  doc_id,
        "text":    enc.decode(tokens),
        "pages":   list(pages),
        "level":   0,
        "is_leaf": True,
    }
