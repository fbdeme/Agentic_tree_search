"""
Baseline RAGAs evaluation script.
Loads pred.json (with retrieved_contexts) and runs RAGAs metrics.

Supports: RAPTOR, GraphRAG (retrieved_contexts already saved in pred.json)

Usage:
    source .venv/bin/activate
    python experiments/evaluate_baseline.py --method raptor
    python experiments/evaluate_baseline.py --method graphrag
    python experiments/evaluate_baseline.py --method raptor --start 1 --end 50
"""

import sys
import os
import json
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
    Faithfulness, AnswerRelevancy, ContextRecall, FactualCorrectness,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory


PRED_PATHS = {
    "raptor":   ROOT / "benchmark/results/raptor/pred.json",
    "graphrag": ROOT / "benchmark/results/graphrag/pred.json",
}


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


async def evaluate_single(question, expected_answer, agent_answer, contexts, metrics):
    answer_for_eval = agent_answer[:2000]
    scores = {}

    try:
        result = await asyncio.wait_for(
            metrics["faithfulness"].ascore(
                user_input=question, response=answer_for_eval,
                retrieved_contexts=contexts,
            ), timeout=120)
        scores["faithfulness"] = round(float(result), 4)
    except Exception as e:
        scores["faithfulness"] = None
        print(f"     [WARN] faithfulness: {str(e)[:80]}")

    try:
        result = await asyncio.wait_for(
            metrics["answer_relevancy"].ascore(
                user_input=question, response=answer_for_eval,
            ), timeout=120)
        scores["answer_relevancy"] = round(float(result), 4)
    except Exception as e:
        scores["answer_relevancy"] = None
        print(f"     [WARN] answer_relevancy: {str(e)[:80]}")

    try:
        result = await asyncio.wait_for(
            metrics["context_recall"].ascore(
                user_input=question, retrieved_contexts=contexts,
                reference=expected_answer,
            ), timeout=120)
        scores["context_recall"] = round(float(result), 4)
    except Exception as e:
        scores["context_recall"] = None
        print(f"     [WARN] context_recall: {str(e)[:80]}")

    try:
        result = await asyncio.wait_for(
            metrics["factual_correctness"].ascore(
                response=answer_for_eval, reference=expected_answer,
            ), timeout=120)
        scores["factual_correctness"] = round(float(result), 4)
    except Exception as e:
        scores["factual_correctness"] = None
        print(f"     [WARN] factual_correctness: {str(e)[:80]}")

    return scores


def safe_avg(entries, key):
    vals = [e[key] for e in entries if e.get(key) is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


async def main():
    parser = argparse.ArgumentParser(description="Baseline RAGAs evaluation")
    parser.add_argument("--method", required=True, choices=list(PRED_PATHS.keys()))
    parser.add_argument("--start", type=int, default=None, help="1-based start index")
    parser.add_argument("--end", type=int, default=None, help="1-based end index (inclusive)")
    args = parser.parse_args()

    pred_path = PRED_PATHS[args.method]
    print(f"\n{'='*60}")
    print(f"Baseline RAGAs Evaluation: {args.method.upper()}")
    print(f"Pred file: {pred_path}")
    print(f"{'='*60}\n")

    with open(pred_path) as f:
        data = json.load(f)
    results_raw = data["results"] if isinstance(data, dict) else data

    # Filter range
    if args.start or args.end:
        start = (args.start or 1) - 1
        end = args.end or len(results_raw)
        results_raw = results_raw[start:end]
        print(f"Range: index {start+1}~{end} -> {len(results_raw)} questions\n")
    else:
        print(f"Total: {len(results_raw)} questions\n")

    # Validate retrieved_contexts
    missing = sum(1 for r in results_raw if not r.get("retrieved_contexts"))
    if missing > 0:
        print(f"[ERROR] {missing}/{len(results_raw)} entries missing retrieved_contexts. Aborting.")
        return

    print("Initializing RAGAs metrics...")
    metrics = init_ragas_metrics()
    print("Ready.\n")

    results = []
    for i, row in enumerate(results_raw):
        qid = row["id"]
        question = row["question"]
        expected = row["expected_answer"]
        generated = row["generated_answer"]
        contexts = row["retrieved_contexts"]
        qtype = row.get("question_type", "unknown")
        reasoning = row.get("reasoning_type", "unknown")
        complexity = row.get("complexity", "unknown")

        print(f"[{i+1}/{len(results_raw)}] {qid} ({qtype})")
        print(f"  Q: {question[:80]}...")
        print(f"  contexts: {len(contexts)}, answer: {len(generated)} chars")

        scores = await evaluate_single(question, expected, generated, contexts, metrics)

        def fmt(v):
            return f"{v:.3f}" if v is not None else "N/A"

        print(f"  Faith={fmt(scores['faithfulness'])}  "
              f"AR={fmt(scores['answer_relevancy'])}  "
              f"CR={fmt(scores['context_recall'])}  "
              f"FC={fmt(scores['factual_correctness'])}")

        results.append({
            "id": qid,
            "question": question,
            "expected_answer": expected,
            "generated_answer": generated,
            "question_type": qtype,
            "reasoning_type": reasoning,
            "complexity": complexity,
            "n_contexts": len(contexts),
            **scores,
        })

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary ({len(results)} questions)")
    print(f"{'='*60}")
    for m in ["faithfulness", "answer_relevancy", "context_recall", "factual_correctness"]:
        avg = safe_avg(results, m)
        n = sum(1 for r in results if r.get(m) is not None)
        print(f"  {m:<25} {avg if avg is not None else 'N/A'}  (n={n})")

    # By question_type
    print(f"\nBy question_type:")
    by_type = {}
    for r in results:
        t = r["question_type"]
        by_type.setdefault(t, []).append(r)
    for t, entries in sorted(by_type.items()):
        avgs = {m: safe_avg(entries, m) for m in ["faithfulness", "context_recall", "factual_correctness"]}
        print(f"  {t:<15} n={len(entries):>3}  "
              f"Faith={fmt(avgs['faithfulness'])}  "
              f"CR={fmt(avgs['context_recall'])}  "
              f"FC={fmt(avgs['factual_correctness'])}")

    # Save
    out_dir = ROOT / "experiments/results/eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"eval_ragas_{args.method}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "method": args.method,
        "evaluation_framework": "RAGAs v0.4",
        "config": {
            "evaluator_model": "gpt-4.1",
            "embedding_model": "text-embedding-3-small",
            "total_questions": len(results),
        },
        "summary": {m: safe_avg(results, m) for m in
                    ["faithfulness", "answer_relevancy", "context_recall", "factual_correctness"]},
        "by_type": {
            t: {m: safe_avg(entries, m) for m in
                ["faithfulness", "answer_relevancy", "context_recall", "factual_correctness"]}
            for t, entries in by_type.items()
        },
        "results": results,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
