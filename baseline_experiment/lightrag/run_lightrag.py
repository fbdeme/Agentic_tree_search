# -*- coding: utf-8 -*-
"""LightRAG baseline: 인덱싱 + 답변 수집.

Usage:
    # Step 1: 인덱싱
    PYTHONPATH=. python experiments/run_lightrag.py --mode index

    # Step 2: 파일럿 (5문항)
    PYTHONPATH=. python experiments/run_lightrag.py --mode query --start 1 --end 5

    # Step 3: 전체 200문항
    PYTHONPATH=. python experiments/run_lightrag.py --mode query

    # Step 4: 인덱싱 + 쿼리 한번에
    PYTHONPATH=. python experiments/run_lightrag.py --mode all
"""

import asyncio
import json
import os
import sys
import time
import argparse
from functools import partial
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

# ── Config ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
WORKING_DIR = ROOT / "experiments" / "lightrag_index"
DATASET_PATH = ROOT / "data" / "qa_dataset" / "multihop_qa_benchmark_v2.json"
OUTPUT_DIR = ROOT / "benchmark" / "results" / "lightrag"

PDF_FILES = [
    ROOT / "data" / "documents" / "NuScale FSAR Ch.01 (공개본).pdf",
    ROOT / "data" / "documents" / "NuScale FSAR Ch.05 (공개본).pdf",
]

LLM_MODEL = "gpt-4.1"
EMBEDDING_MODEL = "text-embedding-3-small"
TEMPERATURE = 0
MAX_TOKENS = 300

# 가이드 4.3절 system_prompt (답변 생성용)
SYSTEM_PROMPT = (
    "You are an expert AI for nuclear regulatory review. "
    "Based on the provided context, answer the user's question. "
    "Answer in 1-2 sentences ONLY. "
    "State the direct answer with specific values, then cite the source. "
    "Do NOT add uncertainty statements, background, or methodology. "
    "Do NOT add information not found in the provided context. "
    "Answer in English."
)


# ── PDF 텍스트 추출 ─────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """PyMuPDF로 PDF에서 텍스트 추출."""
    doc = fitz.open(str(pdf_path))
    texts = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            texts.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(texts)


# ── LightRAG 초기화 ─────────────────────────────────────────────

def create_rag() -> LightRAG:
    """LightRAG 인스턴스 생성. LLM은 gpt-4.1 통일."""
    os.makedirs(WORKING_DIR, exist_ok=True)

    embedding_func = EmbeddingFunc(
        func=openai_embed,
        model_name=EMBEDDING_MODEL,
        embedding_dim=1536,
        max_token_size=8192,
    )

    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        llm_model_func=partial(openai_complete_if_cache, LLM_MODEL),
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={"temperature": TEMPERATURE},
        embedding_func=embedding_func,
        # 인덱싱 설정
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        entity_extract_max_gleaning=1,
        llm_model_max_async=4,
        embedding_batch_num=10,
        embedding_func_max_async=8,
        # 검색 설정
        top_k=40,
        chunk_top_k=20,
        addon_params={"language": "English"},
    )
    return rag


# ── 인덱싱 ───────────────────────────────────────────────────────

async def run_indexing():
    """PDF 텍스트 추출 + LightRAG 인덱싱."""
    print("=" * 60)
    print("LightRAG 인덱싱 시작")
    print(f"  LLM: {LLM_MODEL}")
    print(f"  Embedding: {EMBEDDING_MODEL}")
    print("=" * 60)

    rag = create_rag()
    await rag.initialize_storages()

    total_start = time.time()
    total_chars = 0

    for pdf_path in PDF_FILES:
        print(f"\n  {pdf_path.name} 텍스트 추출 중...")
        text = extract_text_from_pdf(pdf_path)
        total_chars += len(text)
        print(f"  추출: {len(text):,} chars")

        print(f"  LightRAG 인덱싱 중...")
        insert_start = time.time()
        await rag.ainsert(
            input=text,
            ids=pdf_path.stem,
            file_paths=str(pdf_path),
        )
        insert_elapsed = time.time() - insert_start
        print(f"  인덱싱 완료: {insert_elapsed:.1f}s")

    total_elapsed = time.time() - total_start
    await rag.finalize_storages()

    # 인덱싱 결과 기록
    index_report = {
        "timestamp": datetime.now().isoformat(),
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "total_chars": total_chars,
        "indexing_time_sec": round(total_elapsed, 1),
        "pdf_files": [p.name for p in PDF_FILES],
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = OUTPUT_DIR / "indexing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(index_report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"인덱싱 완료!")
    print(f"  총 문자 수: {total_chars:,}")
    print(f"  총 소요 시간: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    print(f"  리포트: {report_path}")
    print(f"{'=' * 60}")


# ── 답변 수집 ────────────────────────────────────────────────────

async def run_query(start: int | None = None, end: int | None = None):
    """벤치마크 문항에 대해 LightRAG 검색 + 답변 생성."""
    # 데이터셋 로드
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"]

    # 범위 필터
    if start or end:
        start_idx = (start or 1) - 1
        end_idx = end or len(questions)
        questions = questions[start_idx:end_idx]

    print(f"\n{'=' * 60}")
    print(f"LightRAG 답변 수집")
    print(f"  문항 수: {len(questions)}")
    print(f"  LLM: {LLM_MODEL}")
    print(f"  검색 모드: hybrid")
    print(f"{'=' * 60}\n")

    rag = create_rag()
    await rag.initialize_storages()

    from openai import OpenAI
    client = OpenAI()

    results = []
    errors = 0
    total_start = time.time()

    for i, q in enumerate(tqdm(questions, desc="LightRAG query")):
        try:
            # Step 1: LightRAG 검색 (context 수집)
            retrieved = await rag.aquery(
                query=q["question"],
                param=QueryParam(mode="hybrid"),
            )

            # Step 2: 검색 결과를 context로 gpt-4.1에 답변 생성
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Context:\n{retrieved}\n\n"
                        f"Question: {q['question']}"
                    )},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            answer = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"\n  ❌ [{q['id']}] 에러: {e}")
            answer = f"ERROR: {e}"
            errors += 1

        results.append({
            "id": q["id"],
            "question": q["question"],
            "expected_answer": q.get("expected_answer", ""),
            "generated_answer": answer,
            "reasoning_type": q.get("reasoning_type"),
            "complexity": q.get("complexity"),
            "question_type": q.get("question_type"),
        })

        # 10문항마다 중간 저장
        if (i + 1) % 10 == 0:
            _save_predictions(results, start, end)

    elapsed = time.time() - total_start

    # 최종 저장
    output_path = _save_predictions(results, start, end)

    print(f"\n{'=' * 60}")
    print(f"완료: {len(results)}문항, 에러 {errors}건")
    print(f"소요: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"저장: {output_path}")
    print(f"{'=' * 60}")


def _save_predictions(results: list[dict], start: int | None, end: int | None) -> str:
    """predictions JSON 저장."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if start or end:
        filename = f"pred_{start or 1}_{end or 'end'}.json"
    else:
        filename = "pred.json"

    output_path = OUTPUT_DIR / filename
    output = {
        "method": "lightrag",
        "model": LLM_MODEL,
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return str(output_path)


# ── Main ──────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="LightRAG baseline experiment")
    parser.add_argument("--mode", choices=["index", "query", "all"], required=True,
                        help="index: 인덱싱만, query: 답변 수집만, all: 둘 다")
    parser.add_argument("--start", type=int, default=None, help="시작 문항 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 (inclusive)")
    args = parser.parse_args()

    if args.mode in ("index", "all"):
        await run_indexing()

    if args.mode in ("query", "all"):
        await run_query(start=args.start, end=args.end)


if __name__ == "__main__":
    asyncio.run(main())
