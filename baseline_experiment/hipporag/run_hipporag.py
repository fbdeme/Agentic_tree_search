# -*- coding: utf-8 -*-
"""HippoRAG baseline: 인덱싱 + 답변 수집.

Usage:
    # Step 1: 인덱싱
    PYTHONPATH=. .venv_hipporag/bin/python experiments/run_hipporag.py --mode index

    # Step 2: 파일럿 (5문항)
    PYTHONPATH=. .venv_hipporag/bin/python experiments/run_hipporag.py --mode query --start 1 --end 5

    # Step 3: 전체 200문항
    PYTHONPATH=. .venv_hipporag/bin/python experiments/run_hipporag.py --mode query

    # Step 4: 한번에
    PYTHONPATH=. .venv_hipporag/bin/python experiments/run_hipporag.py --mode all
"""

import json
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# macOS multiprocessing fix - must be set before any imports that use multiprocessing
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import fitz  # PyMuPDF
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from hipporag import HippoRAG

# ── Config ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
SAVE_DIR = ROOT / "experiments" / "hipporag_index"
DATASET_PATH = ROOT / "data" / "qa_dataset" / "multihop_qa_benchmark_v2.json"
OUTPUT_DIR = ROOT / "benchmark" / "results" / "hipporag"

PDF_FILES = [
    ROOT / "data" / "documents" / "NuScale FSAR Ch.01 (공개본).pdf",
    ROOT / "data" / "documents" / "NuScale FSAR Ch.05 (공개본).pdf",
]

LLM_MODEL = "gpt-4.1"
EMBEDDING_MODEL = "text-embedding-3-small"
TEMPERATURE = 0
MAX_TOKENS = 300

# 가이드 4.3절 system_prompt
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

def extract_passages_from_pdf(pdf_path: Path, chunk_size: int = 1000) -> list[str]:
    """PyMuPDF로 PDF에서 텍스트 추출 → 청크 분할."""
    doc = fitz.open(str(pdf_path))
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            full_text += f"[Page {page_num + 1}] {text}\n"
    doc.close()

    # 단순 문자 수 기반 청크 분할
    passages = []
    words = full_text.split()
    current = []
    current_len = 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            passages.append(" ".join(current))
            current = []
            current_len = 0
    if current:
        passages.append(" ".join(current))

    return passages


# ── HippoRAG 초기화 ─────────────────────────────────────────────

def create_hipporag() -> HippoRAG:
    """HippoRAG 인스턴스 생성. OpenAI API 사용."""
    os.makedirs(SAVE_DIR, exist_ok=True)

    hipporag = HippoRAG(
        save_dir=str(SAVE_DIR),
        llm_model_name=LLM_MODEL,
        embedding_model_name=EMBEDDING_MODEL,
        embedding_base_url="https://api.openai.com/v1",
    )
    return hipporag


# ── 인덱싱 ───────────────────────────────────────────────────────

def run_indexing():
    """PDF 텍스트 추출 + HippoRAG 인덱싱."""
    print("=" * 60)
    print("HippoRAG 인덱싱 시작")
    print(f"  LLM: {LLM_MODEL}")
    print(f"  Embedding: {EMBEDDING_MODEL}")
    print("=" * 60)

    hipporag = create_hipporag()

    total_start = time.time()
    all_passages = []

    for pdf_path in PDF_FILES:
        print(f"\n  {pdf_path.name} 텍스트 추출 중...")
        passages = extract_passages_from_pdf(pdf_path)
        print(f"  추출: {len(passages)} passages")
        all_passages.extend(passages)

    print(f"\n  총 {len(all_passages)} passages 인덱싱 중...")
    hipporag.index(docs=all_passages)

    total_elapsed = time.time() - total_start

    # 인덱싱 결과 기록
    index_report = {
        "timestamp": datetime.now().isoformat(),
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "total_passages": len(all_passages),
        "indexing_time_sec": round(total_elapsed, 1),
        "pdf_files": [p.name for p in PDF_FILES],
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = OUTPUT_DIR / "indexing_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(index_report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"인덱싱 완료!")
    print(f"  총 passages: {len(all_passages)}")
    print(f"  총 소요 시간: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    print(f"  리포트: {report_path}")
    print(f"{'=' * 60}")


# ── 답변 수집 ────────────────────────────────────────────────────

def run_query(start: int | None = None, end: int | None = None):
    """벤치마크 문항에 대해 HippoRAG 검색 + 답변 생성."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"]

    if start or end:
        start_idx = (start or 1) - 1
        end_idx = end or len(questions)
        questions = questions[start_idx:end_idx]

    print(f"\n{'=' * 60}")
    print(f"HippoRAG 답변 수집")
    print(f"  문항 수: {len(questions)}")
    print(f"  LLM: {LLM_MODEL}")
    print(f"{'=' * 60}\n")

    hipporag = create_hipporag()

    from openai import OpenAI
    client = OpenAI()

    results = []
    errors = 0
    total_start = time.time()

    for i, q in enumerate(tqdm(questions, desc="HippoRAG query")):
        try:
            # Step 1: HippoRAG 검색
            retrieval = hipporag.retrieve(
                queries=[q["question"]],
                num_to_retrieve=10,
            )

            # Step 2: 검색 결과에서 context 추출
            if retrieval and len(retrieval) > 0:
                sol = retrieval[0]
                if hasattr(sol, 'retrieved_docs') and sol.retrieved_docs:
                    context = "\n\n".join(sol.retrieved_docs[:10])
                elif hasattr(sol, 'retrieved_passages') and sol.retrieved_passages:
                    context = "\n\n".join(sol.retrieved_passages[:10])
                else:
                    context = str(sol)
            else:
                context = "No context found."

            # Step 3: gpt-4.1로 답변 생성
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Context:\n{context}\n\n"
                        f"Question: {q['question']}"
                    )},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            answer = response.choices[0].message.content.strip()

        except Exception as e:
            print(f"\n  [{q['id']}] 에러: {e}")
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

        if (i + 1) % 10 == 0:
            _save_predictions(results, start, end)

    elapsed = time.time() - total_start
    output_path = _save_predictions(results, start, end)

    print(f"\n{'=' * 60}")
    print(f"완료: {len(results)}문항, 에러 {errors}건")
    print(f"소요: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"저장: {output_path}")
    print(f"{'=' * 60}")


def _save_predictions(results: list[dict], start: int | None, end: int | None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if start or end:
        filename = f"pred_{start or 1}_{end or 'end'}.json"
    else:
        filename = "pred.json"
    output_path = OUTPUT_DIR / filename
    output = {
        "method": "hipporag",
        "model": LLM_MODEL,
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return str(output_path)


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HippoRAG baseline experiment")
    parser.add_argument("--mode", choices=["index", "query", "all"], required=True)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    if args.mode in ("index", "all"):
        run_indexing()
    if args.mode in ("query", "all"):
        run_query(start=args.start, end=args.end)


if __name__ == "__main__":
    main()
