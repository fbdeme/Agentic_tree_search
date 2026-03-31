# -*- coding: utf-8 -*-
"""LLM-as-Judge 평가 스크립트 (MAM-RAG 논문 Table 8 기준).

3 evaluators (Tonic AI, MLflow, Allganize) + majority vote로 Accuracy를 산출합니다.

Usage:
    python -m benchmark.llm_judge benchmark/results/pred_gpt4o.json
    python -m benchmark.llm_judge benchmark/results/pred_gwm.json --output benchmark/results/judge_gwm.json
    python -m benchmark.llm_judge predictions.json --filter reasoning_type=judgment
"""

import json
import os
import sys
import re
import time
import logging
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import pandas as pd
from tqdm import tqdm
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import mlflow

from benchmark.config import (
    ROOT,
    RESULTS_DIR,
    REASONING_TYPES,
    COMPLEXITY_LEVELS,
    QUESTION_TYPES,
    TONIC_MODEL,
    MLFLOW_MODEL,
    ALLGANIZE_MODEL,
    VOTE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ── Prompt templates (MAM-RAG 원본) ──────────────────────────

TONIC_ANSWER_SIMILARITY_PROMPT = (
    "Considering the reference answer and the new answer to the following question, "
    "on a scale of 0 to 5, where 5 means the same and 0 means not at all similar, "
    "how similar in meaning is the new answer to the reference answer? Respond with just "
    "a number and no additional text.\nQUESTION: {question}\nREFERENCE ANSWER: {"
    "reference_answer}\nNEW ANSWER: {llm_answer}\n"
)

ALLGANIZE_ANSWER_CORRECTNESS_PROMPT = """
question = \"\"\"
{question}
\"\"\"

target_answer = \"\"\"
{reference_answer}
\"\"\"

generated_answer = \"\"\"
{llm_answer}
\"\"\"

Check if target_answer and generated_answer match by referring to question.
If target_answer and generated_answer match 1, answer 0 if they do not match.
Only 1 or 0 must be created.
"""


# ── Answer cleaning ──────────────────────────────────────────

def extract_final_answer(text: str) -> str:
    if "Final answer:" in text:
        return text.split("Final answer:")[-1].strip()
    elif "final answer:" in text.lower():
        idx = text.lower().find("final answer:")
        return text[idx + len("final answer:"):].strip()
    return text


def remove_citations(text: str) -> str:
    # MAM-RAG 인용 패턴
    text = re.sub(r"\[Text\s*-[^\]]*\]", "", text)
    text = re.sub(r"\[Table\s*-[^\]]*\]", "", text)
    text = re.sub(r"\[Figure\s*-[^\]]*\]", "", text)
    text = re.sub(r"\[Source[^\]]*\]", "", text)
    # GWM 에이전트 인용 패턴
    text = re.sub(r"\[nuscale_ch\d+_\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Evaluators (MAM-RAG 원본 포팅) ──────────────────────────

def tonic_validate(
    questions: list, generated_answers: list, target_answers: list, model: str = TONIC_MODEL
) -> list[int]:
    """Tonic AI Similarity: 0-5 scale."""
    llm = ChatOpenAI(model_name=model, temperature=0)
    prompt = PromptTemplate(
        input_variables=["question", "reference_answer", "llm_answer"],
        template=TONIC_ANSWER_SIMILARITY_PROMPT,
    )
    chain = prompt | llm | StrOutputParser()

    results = []
    for question, target, generated in tqdm(
        zip(questions, target_answers, generated_answers),
        total=len(questions), desc="TONIC Similarity",
    ):
        try:
            raw = chain.invoke({
                "question": question,
                "reference_answer": target,
                "llm_answer": generated,
            })
            results.append(int(raw.strip()))
        except Exception as e:
            logger.warning(f"tonic_validate exception: {e}")
            results.append(-1)
    return results


def mlflow_eval(
    question_list: list, answer_list: list, ground_truth_list: list, model: str = MLFLOW_MODEL
) -> tuple[list, list]:
    """MLflow answer_similarity + answer_correctness: 1-5 scale each."""
    mlflow.set_tracking_uri((RESULTS_DIR / "mlruns").as_uri())

    eval_data = pd.DataFrame({
        "inputs": question_list,
        "predictions": answer_list,
        "ground_truth": ground_truth_list,
    })

    with mlflow.start_run():
        results = mlflow.evaluate(
            data=eval_data,
            targets="ground_truth",
            predictions="predictions",
            extra_metrics=[
                mlflow.metrics.genai.answer_similarity(model=model),
                mlflow.metrics.genai.answer_correctness(model=model),
            ],
            evaluators="default",
        )
        eval_table = results.tables["eval_results_table"]
        similarity = eval_table["answer_similarity/v1/score"].tolist()
        correctness = eval_table["answer_correctness/v1/score"].tolist()

    return similarity, correctness


def allganize_eval(
    questions: list, generated_answers: list, target_answers: list, model: str = ALLGANIZE_MODEL
) -> list[int]:
    """Allganize Correctness: binary 0/1."""
    llm = ChatAnthropic(model=model, temperature=0)
    prompt = PromptTemplate(
        input_variables=["question", "reference_answer", "llm_answer"],
        template=ALLGANIZE_ANSWER_CORRECTNESS_PROMPT,
    )
    chain = prompt | llm | StrOutputParser()

    _MAX_RETRIES = 5
    _RETRY_BASE = 2.0  # seconds (exponential: 2, 4, 8, 16, 32)

    results = []
    for question, target, generated in tqdm(
        zip(questions, target_answers, generated_answers),
        total=len(questions), desc="ALLGANIZE Correctness",
    ):
        raw = None
        for attempt in range(_MAX_RETRIES):
            try:
                raw = chain.invoke({
                    "question": question,
                    "reference_answer": target,
                    "llm_answer": generated,
                })
                break  # 성공 시 재시도 루프 탈출
            except Exception as e:
                err_str = str(e)
                is_overload = "overloaded_error" in err_str or "529" in err_str
                if is_overload and attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BASE ** (attempt + 1)
                    logger.warning(f"Anthropic overloaded (attempt {attempt+1}/{_MAX_RETRIES}), retrying in {wait:.0f}s...")
                    time.sleep(wait)
                else:
                    logger.warning(f"allganize_eval exception: {e}")
                    break

        if raw is None:
            results.append(-1)
            continue

        try:
            m = re.search(r'[01]', raw)
            if m is None:
                raise ValueError(f"No 0/1 found in response: {raw[:50]!r}")
            results.append(int(m.group()))
        except Exception as e:
            logger.warning(f"allganize_eval parse exception: {e}")
            results.append(-1)
    return results


# ── Voting (MAM-RAG 원본) ───────────────────────────────────

def get_evaluation_result(score: int) -> str:
    """score >= VOTE_THRESHOLD → O, else X"""
    return "O" if score >= VOTE_THRESHOLD else "X"


def most_frequent_element(result: list) -> str:
    """다수결, 동률시 X 우선 (보수적)"""
    count = Counter(result)
    most_common = count.most_common()
    for element in ["X", "O"]:
        if element in count and count[element] == most_common[0][1]:
            return element
    return most_common[0][0] if most_common else "X"


def eval_vote(
    tonic_similarity: list,
    mlflow_similarity: list,
    mlflow_correctness: list,
    allganize_correctness: list,
) -> list[str]:
    """4표 majority vote → final O/X per question."""
    results = []
    for i in range(len(tonic_similarity)):
        tonic_ox = get_evaluation_result(tonic_similarity[i])
        mlflow_sim_ox = get_evaluation_result(mlflow_similarity[i])
        mlflow_corr_ox = get_evaluation_result(mlflow_correctness[i])
        allganize_ox = "O" if allganize_correctness[i] == 1 else "X"

        results.append(most_frequent_element([
            tonic_ox, mlflow_sim_ox, mlflow_corr_ox, allganize_ox,
        ]))
    return results


# ── Aggregation (3축 확장) ───────────────────────────────────

def _aggregate(results: list[dict], key: str) -> dict:
    """단일 축 기준 O/X 집계"""
    stats = {}
    for r in results:
        val = r.get(key, "unknown")
        if val not in stats:
            stats[val] = {"total": 0, "O": 0, "X": 0}
        stats[val]["total"] += 1
        stats[val][r["final_vote"]] += 1
    for v in stats.values():
        v["accuracy"] = round(v["O"] / v["total"], 4) if v["total"] else 0
    return stats


def aggregate_by_matrix(results: list[dict]) -> dict:
    """9-cell matrix (reasoning_type × complexity)"""
    stats = {}
    for r in results:
        key = f"{r.get('reasoning_type', 'unknown')}_{r.get('complexity', 'unknown')}"
        if key not in stats:
            stats[key] = {"total": 0, "O": 0, "X": 0}
        stats[key]["total"] += 1
        stats[key][r["final_vote"]] += 1
    for v in stats.values():
        v["accuracy"] = round(v["O"] / v["total"], 4) if v["total"] else 0
    return stats


# ── Main ─────────────────────────────────────────────────────

def load_predictions(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    raise ValueError(f"지원하지 않는 데이터 형식: {type(data)}")


def save_partial(path: str, data: dict):
    partial_path = path.replace(".json", "_partial.json")
    with open(partial_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_llm_judge(
    predictions_path: str,
    output_path: str | None = None,
    clean_answers: bool = True,
    filters: dict | None = None,
) -> dict:
    """LLM-as-Judge 평가 메인 실행."""

    predictions = load_predictions(predictions_path)

    # 필터 적용
    if filters:
        for key, val in filters.items():
            predictions = [p for p in predictions if p.get(key) == val]

    print(f"\n{'='*60}")
    print(f"LLM-as-Judge 평가 (MAM-RAG 논문 Table 8)")
    print(f"{'='*60}")
    print(f"입력: {Path(predictions_path).name}")
    print(f"문항 수: {len(predictions)}")
    if filters:
        print(f"필터: {filters}")
    print(f"{'='*60}\n")

    # 데이터 추출
    ids = [p["id"] for p in predictions]
    questions = [p["question"] for p in predictions]
    generated_answers = [p["generated_answer"] for p in predictions]
    expected_answers = [p["expected_answer"] for p in predictions]

    # 답변 정제
    if clean_answers:
        print("답변 정제 중 (Final answer 추출, 인용 제거)...")
        generated_answers = [remove_citations(extract_final_answer(a)) for a in generated_answers]

    # Step 1: Tonic
    print(f"\n[1/3] Tonic AI Similarity ({TONIC_MODEL})...")
    tonic_scores = tonic_validate(questions, generated_answers, expected_answers)
    save_partial(output_path or "benchmark/results/judge_output.json", {"tonic": tonic_scores})

    # Step 2: MLflow
    print(f"\n[2/3] MLflow Evaluation ({MLFLOW_MODEL})...")
    mlflow_sim, mlflow_corr = mlflow_eval(questions, generated_answers, expected_answers)
    save_partial(output_path or "benchmark/results/judge_output.json", {
        "tonic": tonic_scores, "mlflow_sim": mlflow_sim, "mlflow_corr": mlflow_corr,
    })

    # Step 3: Allganize
    print(f"\n[3/3] Allganize Correctness ({ALLGANIZE_MODEL})...")
    allganize_scores = allganize_eval(questions, generated_answers, expected_answers)

    # Step 4: Voting
    print("\n[Vote] Majority voting...")
    final_votes = eval_vote(tonic_scores, mlflow_sim, mlflow_corr, allganize_scores)

    # 결과 조합
    results = []
    for i in range(len(predictions)):
        results.append({
            "id": ids[i],
            "reasoning_type": predictions[i].get("reasoning_type"),
            "complexity": predictions[i].get("complexity"),
            "question_type": predictions[i].get("question_type"),
            "tonic_similarity": tonic_scores[i],
            "mlflow_similarity": mlflow_sim[i],
            "mlflow_correctness": mlflow_corr[i],
            "allganize_correctness": allganize_scores[i],
            "final_vote": final_votes[i],
            "question": questions[i],
            "generated_answer": generated_answers[i],
            "expected_answer": expected_answers[i],
        })

    # 집계
    o_count = sum(1 for r in results if r["final_vote"] == "O")
    total = len(results)
    accuracy = o_count / total if total else 0

    output = {
        "timestamp": datetime.now().isoformat(),
        "source": Path(predictions_path).name,
        "filters": filters,
        "evaluators": {
            "tonic": {"model": TONIC_MODEL, "criteria": "similarity", "scale": "0-5", "threshold": VOTE_THRESHOLD},
            "mlflow": {"model": MLFLOW_MODEL, "criteria": "similarity+correctness", "scale": "1-5", "threshold": VOTE_THRESHOLD},
            "allganize": {"model": ALLGANIZE_MODEL, "criteria": "correctness", "scale": "0/1", "threshold": 1},
        },
        "summary": {
            "total": total,
            "correct": o_count,
            "incorrect": total - o_count,
            "accuracy": round(accuracy, 4),
        },
        "by_question_type": _aggregate(results, "question_type"),
        "by_reasoning_type": _aggregate(results, "reasoning_type"),
        "by_complexity": _aggregate(results, "complexity"),
        "matrix_9cell": aggregate_by_matrix(results),
        "results": results,
    }

    # 출력
    print(f"\n{'='*60}")
    print(f"전체 결과: {o_count}/{total} = Accuracy {accuracy*100:.1f}%")
    print(f"\n타입별:")
    for qt, stats in output["by_question_type"].items():
        print(f"  [{qt}] {stats['O']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")
    print(f"\n추론 유형별:")
    for rt, stats in output["by_reasoning_type"].items():
        print(f"  [{rt}] {stats['O']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")
    print(f"\n복잡도별:")
    for cx, stats in output["by_complexity"].items():
        print(f"  [{cx}] {stats['O']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")

    # 저장
    if output_path is None:
        output_path = predictions_path.replace(".json", "_llm_judge_results.json")
    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")

    # partial 파일 삭제
    partial = output_path.replace(".json", "_partial.json")
    if os.path.exists(partial):
        os.remove(partial)

    return output


def parse_filters(filter_args: list[str] | None) -> dict | None:
    if not filter_args:
        return None
    filters = {}
    for f in filter_args:
        key, val = f.split("=", 1)
        filters[key] = val
    return filters


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM-as-Judge 평가 (MAM-RAG Table 8)")
    parser.add_argument("predictions", help="predictions JSON 파일 경로")
    parser.add_argument("--output", "-o", default=None, help="결과 저장 경로")
    parser.add_argument("--filter", action="append", help="필터 (예: reasoning_type=judgment)")
    parser.add_argument("--no-clean", action="store_true", help="답변 정제 비활성화")
    args = parser.parse_args()

    run_llm_judge(
        predictions_path=args.predictions,
        output_path=args.output,
        clean_answers=not args.no_clean,
        filters=parse_filters(args.filter),
    )
