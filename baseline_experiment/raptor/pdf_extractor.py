# -*- coding: utf-8 -*-
"""PDF → 토큰 단위 텍스트 청크 추출.

PyMuPDF(fitz)로 페이지별 텍스트를 추출한 뒤
tiktoken cl100k_base 인코더로 CHUNK_SIZE 토큰 단위로 분할합니다.
페이지 경계를 최대한 보존하며, CHUNK_OVERLAP 만큼 앞 청크와 겹칩니다.
"""

from __future__ import annotations

import logging
from typing import List, Dict

import fitz  # PyMuPDF
import tiktoken

from .config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def extract_chunks_from_pdf(pdf_path: str, doc_id: str) -> List[Dict]:
    """PDF 파일을 청크 리스트로 변환.

    Args:
        pdf_path: PDF 파일 경로
        doc_id:   문서 식별자 (예: "nuscale_ch01")

    Returns:
        List of chunk dicts::

            {
                "id":      "nuscale_ch01_chunk_0000",
                "doc_id":  "nuscale_ch01",
                "text":    "...",
                "pages":   [1, 2],
                "level":   0,        # 0 = leaf (원본 청크)
                "is_leaf": True,
            }
    """
    enc = tiktoken.get_encoding("cl100k_base")

    doc = fitz.open(pdf_path)
    pages_text = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if text:
            pages_text.append({"page": page_num, "text": text})
    doc.close()
    logger.info(f"  [{doc_id}] {len(pages_text)} 페이지 텍스트 추출 완료")

    chunks: List[Dict] = []
    chunk_id = 0

    buffer_tokens: List[int] = []
    current_pages: List[int] = []

    for page_info in pages_text:
        page_tokens = enc.encode(page_info["text"])

        if len(buffer_tokens) + len(page_tokens) <= CHUNK_SIZE:
            buffer_tokens.extend(page_tokens)
            current_pages.append(page_info["page"])
        else:
            # 현재 버퍼 → 청크 저장
            if buffer_tokens:
                chunks.append(_make_chunk(enc, buffer_tokens, current_pages, doc_id, chunk_id))
                chunk_id += 1

            # 오버랩: 이전 청크의 마지막 CHUNK_OVERLAP 토큰 유지
            overlap = buffer_tokens[-CHUNK_OVERLAP:] if len(buffer_tokens) > CHUNK_OVERLAP else list(buffer_tokens)
            buffer_tokens = overlap + page_tokens
            current_pages = [page_info["page"]]

            # 버퍼가 여전히 CHUNK_SIZE 초과인 경우 강제 분할
            while len(buffer_tokens) > CHUNK_SIZE:
                chunk_tokens = buffer_tokens[:CHUNK_SIZE]
                chunks.append(_make_chunk(enc, chunk_tokens, current_pages, doc_id, chunk_id))
                chunk_id += 1
                overlap = buffer_tokens[CHUNK_SIZE - CHUNK_OVERLAP:CHUNK_SIZE]
                buffer_tokens = overlap + buffer_tokens[CHUNK_SIZE:]

    # 남은 버퍼
    if buffer_tokens:
        chunks.append(_make_chunk(enc, buffer_tokens, current_pages, doc_id, chunk_id))

    logger.info(f"  [{doc_id}] {len(chunks)} 청크 생성 완료")
    return chunks


def _make_chunk(enc, tokens: List[int], pages: List[int], doc_id: str, chunk_id: int) -> Dict:
    return {
        "id": f"{doc_id}_chunk_{chunk_id:04d}",
        "doc_id": doc_id,
        "text": enc.decode(tokens),
        "pages": list(pages),
        "level": 0,
        "is_leaf": True,
    }
