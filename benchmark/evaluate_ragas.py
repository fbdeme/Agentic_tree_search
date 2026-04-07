# -*- coding: utf-8 -*-
"""
베이스라인 모델 RAGAs 평가 스크립트.

이미 생성된 pred.json (generated_answer + retrieved_contexts)을 입력받아
RAGAs 4개 메트릭을 측정합니다.

Usage:
    cd /home/user/workspace_2026/Agentic_tree_search
    source .venv/bin/activate

    # 단일 모델 평가
    python -m benchmark.evaluate_ragas benchmark/results/graphrag/pred.json

    # 여러 모델 동시 평가
    python -m benchmark.evaluate_ragas \
        benchmark/results/graphrag/pred.json \
        benchmark/results/raptor/pred.json

    # 병렬도 조절 (기본 4)
    python -m benchmark.evaluate_ragas pred.json --concurrency 8

    # 특정 범위만
    python -m benchmark.evaluate_ragas pred.json --start 1 --end 10
"""

import sys
import os
import json
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from openai import AsyncOpenAI
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
    FactualCorrectness,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory

from benchmark.config import REASONING_TYPES, COMPLEXITY_LEVELS, QUESTION_TYPES


# ── RAGAs 메트릭 초기화 ──────────────────────────────────────────

def init_ragas_metrics():
    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    evaluator_llm = llm_factory("gpt-4.1", client=async_client, max_tokens=4096)
    evaluator_embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=async_client
    )
    return {
        "faithfulness": Faithfulness(llm=evaluator_llm),
        "answer_relevancy": AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        "context_recall": ContextRecall(llm=evaluator_llm),
        "factual_correctness": FactualCorrectness(llm=evaluator_llm),
    }


# ── 단일 문항 RAGAs 평가 ─────────────────────────────────────────

METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_recall", "factual_correctness"]

async def evaluate_single(
    qid: str,
    question: str,
    answer: str,
    expected_answer: str,
    retrieved_contexts: list[str],
    metrics: dict,
) -> dict:
    """단일 문항에 대해 RAGAs 4개 메트릭 측정."""
    answer_for_eval = answer[:2000] if len(answer) > 2000 else answer
    scores = {}

    # Faithfulness
    try:
        result = await asyncio.wait_for(
            metrics["faithfulness"].ascore(
                user_input=question,
                response=answer_for_eval,
                retrieved_contexts=retrieved_contexts,
            ),
            timeout=120,
        )
        scores["faithfulness"] = round(float(result), 4)
    except Exception as e:
        scores["faithfulness"] = None
        print(f"     ⚠️ {qid} faithfulness: {str(e)[:80]}")

    # Answer Relevancy
    try:
        result = await asyncio.wait_for(
            metrics["answer_relevancy"].ascore(
                user_input=question,
                response=answer_for_eval,
            ),
            timeout=120,
        )
        scores["answer_relevancy"] = round(float(result), 4)
    except Exception as e:
        scores["answer_relevancy"] = None
        print(f"     ⚠️ {qid} answer_relevancy: {str(e)[:80]}")

    # Context Recall
    try:
        result = await asyncio.wait_for(
            metrics["context_recall"].ascore(
                user_input=question,
                retrieved_contexts=retrieved_contexts,
                reference=expected_answer,
            ),
            timeout=120,
        )
        scores["context_recall"] = round(float(result), 4)
    except Exception as e:
        scores["context_recall"] = None
        print(f"     ⚠️ {qid} context_recall: {str(e)[:80]}")

    # Factual Correctness
    try:
        result = await asyncio.wait_for(
            metrics["factual_correctness"].ascore(
                response=answer_for_eval,
                reference=expected_answer,
            ),
            timeout=120,
        )
        scores["factual_correctness"] = round(float(result), 4)
    except Exception as e:
        scores["factual_correctness"] = None
        print(f"     ⚠️ {qid} factual_correctness: {str(e)[:80]}")

    return scores


# ── 병렬 평가 워커 ────────────────────────────────────────────────

async def worker(
    sem: asyncio.Semaphore,
    item: dict,
    metrics: dict,
    progress: dict,
) -> dict:
    """세마포어로 병렬도를 제한하며 단일 문항 평가."""
    async with sem:
        qid = item["id"]
        progress["done"] += 1
        n = progress["done"]
        total = progress["total"]
        print(f"  [{n}/{total}] {qid} ({item.get('reasoning_type', '?')}/{item.get('complexity', '?')})")

        retrieved_contexts = item.get("retrieved_contexts", [])
        if not retrieved_contexts:
            print(f"     ⚠️ {qid}: retrieved_contexts 비어있음 → 스킵")
            return {
                "id": qid,
                "faithfulness": None,
                "answer_relevancy": None,
                "context_recall": None,
                "factual_correctness": None,
                "skipped": True,
            }

        scores = await evaluate_single(
            qid=qid,
            question=item["question"],
            answer=item["generated_answer"],
            expected_answer=item["expected_answer"],
            retrieved_contexts=retrieved_contexts,
            metrics=metrics,
        )

        def fmt(v):
            return f"{v:.2f}" if v is not None else "N/A"
        print(f"     Faith:{fmt(scores.get('faithfulness'))}  "
              f"AR:{fmt(scores.get('answer_relevancy'))}  "
              f"CR:{fmt(scores.get('context_recall'))}  "
              f"FC:{fmt(scores.get('factual_correctness'))}")

        return {"id": qid, **scores}


# ── 메인 평가 루프 ────────────────────────────────────────────────

def safe_avg(entries: list[dict], key: str) -> float | None:
    vals = [e[key] for e in entries if e.get(key) is not None]
    return sum(vals) / len(vals) if vals else None


async def evaluate_pred_file(
    pred_path: str,
    metrics: dict,
    concurrency: int = 4,
    start: int | None = None,
    end: int | None = None,
):
    """pred.json 하나를 RAGAs 평가."""
    pred_path = Path(pred_path)
    with open(pred_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    method = pred_path.parent.name
    items = data["results"]

    # 범위 필터
    if start or end:
        s = (start or 1) - 1
        e = end or len(items)
        items = items[s:e]

    print(f"\n{'='*60}")
    print(f"📐 RAGAs 평가: {method} ({len(items)}문항, 병렬도 {concurrency})")
    print(f"   소스: {pred_path}")
    print(f"{'='*60}\n")

    sem = asyncio.Semaphore(concurrency)
    progress = {"done": 0, "total": len(items)}
    t0 = time.time()

    tasks = [worker(sem, item, metrics, progress) for item in items]
    eval_results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0

    # ID로 원본 데이터 매핑
    orig_map = {item["id"]: item for item in items}

    # 결과 병합
    merged = []
    for er in eval_results:
        qid = er["id"]
        orig = orig_map[qid]
        merged.append({
            "id": qid,
            "reasoning_type": orig.get("reasoning_type", ""),
            "complexity": orig.get("complexity", ""),
            "question_type": orig.get("question_type", ""),
            "question": orig["question"],
            "generated_answer": orig["generated_answer"],
            "expected_answer": orig["expected_answer"],
            "faithfulness": er.get("faithfulness"),
            "answer_relevancy": er.get("answer_relevancy"),
            "context_recall": er.get("context_recall"),
            "factual_correctness": er.get("factual_correctness"),
            "skipped": er.get("skipped", False),
        })

    # 집계
    valid = [r for r in merged if not r.get("skipped")]
    summary = {}
    for m in METRIC_NAMES:
        summary[m] = round(safe_avg(valid, m), 4) if safe_avg(valid, m) is not None else None

    # 타입별 집계
    by_reasoning = {}
    for rt in REASONING_TYPES:
        subset = [r for r in valid if r["reasoning_type"] == rt]
        if subset:
            by_reasoning[rt] = {
                "count": len(subset),
                **{m: round(safe_avg(subset, m), 4) if safe_avg(subset, m) is not None else None for m in METRIC_NAMES},
            }

    by_complexity = {}
    for cx in COMPLEXITY_LEVELS:
        subset = [r for r in valid if r["complexity"] == cx]
        if subset:
            by_complexity[cx] = {
                "count": len(subset),
                **{m: round(safe_avg(subset, m), 4) if safe_avg(subset, m) is not None else None for m in METRIC_NAMES},
            }

    by_question_type = {}
    for qt in QUESTION_TYPES:
        subset = [r for r in valid if r["question_type"] == qt]
        if subset:
            by_question_type[qt] = {
                "count": len(subset),
                **{m: round(safe_avg(subset, m), 4) if safe_avg(subset, m) is not None else None for m in METRIC_NAMES},
            }

    # 리포트 출력
    print(f"\n{'='*60}")
    print(f"📊 RAGAs 결과: {method}")
    print(f"{'='*60}")
    print(f"\n전체 평균 ({len(valid)}문항 평가, {len(merged)-len(valid)}건 스킵):")
    for m in METRIC_NAMES:
        v = summary[m]
        print(f"   {m:<25} {v:.4f}" if v is not None else f"   {m:<25} N/A")

    print(f"\nreasoning_type별:")
    for rt, stats in by_reasoning.items():
        vals = "  ".join(f"{m[:5]}:{stats[m]:.2f}" if stats[m] is not None else f"{m[:5]}:N/A" for m in METRIC_NAMES)
        print(f"   {rt:<15} (n={stats['count']})  {vals}")

    print(f"\ncomplexity별:")
    for cx, stats in by_complexity.items():
        vals = "  ".join(f"{m[:5]}:{stats[m]:.2f}" if stats[m] is not None else f"{m[:5]}:N/A" for m in METRIC_NAMES)
        print(f"   {cx:<18} (n={stats['count']})  {vals}")

    print(f"\n⏱️  소요 시간: {elapsed:.0f}초 ({elapsed/60:.1f}분)")

    # 저장
    output_dir = pred_path.parent
    report = {
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "evaluation_framework": "RAGAs v0.4",
        "config": {
            "evaluator_model": "gpt-4.1",
            "embedding_model": "text-embedding-3-small",
            "max_tokens": 4096,
            "concurrency": concurrency,
            "total_questions": len(merged),
            "evaluated": len(valid),
            "skipped": len(merged) - len(valid),
        },
        "summary": summary,
        "by_reasoning_type": by_reasoning,
        "by_complexity": by_complexity,
        "by_question_type": by_question_type,
        "results": merged,
    }

    out_path = output_dir / "ragas.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n💾 저장: {out_path}")

    return report


async def main(args):
    print("📐 RAGAs 메트릭 초기화 중...")
    metrics = init_ragas_metrics()
    print(f"   메트릭: {', '.join(metrics.keys())}\n")

    for pred_path in args.pred_files:
        await evaluate_pred_file(
            pred_path=pred_path,
            metrics=metrics,
            concurrency=args.concurrency,
            start=args.start,
            end=args.end,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="베이스라인 RAGAs 평가")
    parser.add_argument("pred_files", nargs="+", help="pred.json 파일 경로(들)")
    parser.add_argument("--concurrency", type=int, default=4, help="병렬 평가 수 (default: 4)")
    parser.add_argument("--start", type=int, default=None, help="시작 문항 번호 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 번호 (inclusive)")
    args = parser.parse_args()

    asyncio.run(main(args))
