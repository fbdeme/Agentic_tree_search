# -*- coding: utf-8 -*-
"""RAPTOR 엔드투엔드 파이프라인.

두 단계로 구성됩니다:
  1. build_index()   — PDF → RAPTOR 트리 인덱스 구축 + 저장
  2. run_inference() — 트리 + QA 데이터셋 → predictions JSON 생성

출력 형식은 baseline_experiment_guide.md §5를 따릅니다.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from .config import (
    GENERATION_MODEL,
    MAX_TOKENS,
    QA_DATASET_PATH,
    RESULTS_DIR,
    RETRIEVAL_MODE,
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_K,
)
from .pdf_extractor import extract_chunks_from_pdf
from .retriever import RAPTORRetriever
from .tree_builder import RAPTORTree

logger = logging.getLogger(__name__)


# ── Step 1: 인덱스 구축 ─────────────────────────────────────────

def build_index(
    pdf_paths: Dict[str, str],
    save_path: Optional[str] = None,
) -> RAPTORTree:
    """PDF 딕셔너리 → RAPTOR 트리 구축 + 저장.

    Args:
        pdf_paths: {doc_id: pdf_file_path} 딕셔너리
        save_path: 저장 경로 (None이면 기본 위치)

    Returns:
        구축된 RAPTORTree 객체
    """
    client = OpenAI()
    all_chunks: List[Dict] = []

    for doc_id, pdf_path in pdf_paths.items():
        logger.info(f"PDF 추출: {pdf_path}")
        chunks = extract_chunks_from_pdf(pdf_path, doc_id)
        all_chunks.extend(chunks)

    logger.info(f"총 {len(all_chunks)}개 청크로 트리 구축 시작")
    tree = RAPTORTree()
    tree.build(all_chunks, client)

    saved = tree.save(save_path)
    logger.info(f"트리 저장 완료: {saved}")
    return tree


# ── Step 2: 추론 ────────────────────────────────────────────────

def run_inference(
    tree: RAPTORTree,
    dataset_path: Optional[str] = None,
    output_path: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> str:
    """QA 데이터셋 전체 추론 → predictions JSON 저장.

    Args:
        tree:         로드된 RAPTORTree
        dataset_path: QA 데이터셋 경로 (None이면 config 기본값)
        output_path:  출력 JSON 경로 (None이면 results/raptor/pred.json)
        start:        시작 문항 번호 (1-based, None이면 처음부터)
        end:          종료 문항 번호 (inclusive, None이면 끝까지)

    Returns:
        저장된 파일 경로
    """
    client = OpenAI()
    retriever = RAPTORRetriever(tree, client)

    # 데이터셋 로드
    dataset_path = dataset_path or str(QA_DATASET_PATH)
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions: List[Dict] = data.get("questions", [])

    # 범위 필터
    if start or end:
        s = (start or 1) - 1
        e = end or len(questions)
        questions = questions[s:e]

    logger.info(f"추론 시작: {len(questions)}문항 (mode={RETRIEVAL_MODE}, top_k={TOP_K})")
    results: List[Dict] = []
    errors = 0

    for i, q in enumerate(questions):
        q_id = q.get("id", f"Q{i+1:03d}")
        try:
            t_ret = time.time()
            nodes = retriever.retrieve(q["question"], top_k=TOP_K, mode=RETRIEVAL_MODE)
            retrieval_time = time.time() - t_ret

            context = "\n\n---\n\n".join(n["text"] for n in nodes)

            t_gen = time.time()
            response = client.chat.completions.create(
                model=GENERATION_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q['question']}"},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            answer = response.choices[0].message.content.strip()
            generation_time = time.time() - t_gen

            results.append({
                "id":                q_id,
                "question":          q["question"],
                "expected_answer":   q.get("expected_answer", ""),
                "generated_answer":  answer,
                "reasoning_type":    q.get("reasoning_type"),
                "complexity":        q.get("complexity"),
                "question_type":     q.get("question_type"),
                # 선택 필드 (§5.3)
                "retrieved_contexts":   [n["text"] for n in nodes],
                "n_chunks_retrieved":   len(nodes),
                "retrieval_time_sec":   round(retrieval_time, 2),
                "generation_time_sec":  round(generation_time, 2),
            })

        except Exception as exc:
            logger.error(f"[{q_id}] 에러: {exc}")
            results.append({
                "id":               q_id,
                "question":         q.get("question", ""),
                "expected_answer":  q.get("expected_answer", ""),
                "generated_answer": f"ERROR: {exc}",
                "reasoning_type":   q.get("reasoning_type"),
                "complexity":       q.get("complexity"),
                "question_type":    q.get("question_type"),
                "error":            str(exc),
            })
            errors += 1

        # 10문항마다 중간 저장
        if (i + 1) % 10 == 0:
            _save_predictions(results, output_path)
            logger.info(f"  중간 저장 ({i + 1}/{len(questions)}, 에러 {errors}건)")

    saved = _save_predictions(results, output_path)
    logger.info(f"추론 완료: {len(results)}문항, 에러 {errors}건 → {saved}")
    return saved


# ── 내부 유틸 ────────────────────────────────────────────────────

def _save_predictions(results: List[Dict], output_path: Optional[str]) -> str:
    if output_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(RESULTS_DIR / "pred.json")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    output = {
        "method":    "raptor",
        "model":     GENERATION_MODEL,
        "timestamp": datetime.now().isoformat(),
        "total":     len(results),
        "results":   results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return output_path
