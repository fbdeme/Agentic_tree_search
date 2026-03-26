# -*- coding: utf-8 -*-
"""비교 모델 답변 수집기.

벤치마크 데이터셋에 대해 다양한 모델의 답변을 수집하여
llm_judge.py가 소비하는 predictions 포맷으로 저장합니다.

Usage:
    python -m benchmark.run_baseline --method gpt-4o --output benchmark/results/pred_gpt4o.json
    python -m benchmark.run_baseline --method gwm --tree-dir data/trees/ --output benchmark/results/pred_gwm.json
    python -m benchmark.run_baseline --method gpt-4o --start 1 --end 50
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

from tqdm import tqdm

from benchmark.config import ROOT, BENCHMARK_V2_PATH, RESULTS_DIR


# ── Baseline model factories ────────────────────────────────

def make_openai_baseline(model: str) -> Callable[[str], str]:
    """OpenAI API 기반 Vanilla LLM baseline."""
    from openai import OpenAI
    client = OpenAI()

    def answer_fn(question: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "You are a nuclear engineering expert. Answer the question about "
                    "NuScale FSAR (Final Safety Analysis Report) accurately and concisely. "
                    "Provide specific numerical values and technical details when available."
                )},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    return answer_fn


def make_anthropic_baseline(model: str) -> Callable[[str], str]:
    """Anthropic API 기반 Vanilla LLM baseline."""
    from anthropic import Anthropic
    client = Anthropic()

    def answer_fn(question: str) -> str:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0,
            system=(
                "You are a nuclear engineering expert. Answer the question about "
                "NuScale FSAR (Final Safety Analysis Report) accurately and concisely. "
                "Provide specific numerical values and technical details when available."
            ),
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text.strip()

    return answer_fn


def make_gwm_baseline(tree_dir: str, max_hops: int = 4, top_k: int = 2) -> Callable[[str], str]:
    """GWM 에이전트 baseline."""
    sys.path.insert(0, str(ROOT))
    from src.environment.pageindex_env import PageIndexEnvironment
    from src.agent.gwm_agent import GWMAgent

    env = PageIndexEnvironment(model="gpt-4.1")
    tree_files = list(Path(tree_dir).glob("*_structure.json"))
    for tree_file in tree_files:
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        env.register_tree(
            doc_id=data.get("doc_id", tree_file.stem),
            tree=data.get("tree", data.get("structure", [])),
            doc_name=data.get("doc_name", ""),
            pdf_path=data.get("pdf_path", ""),
        )

    doc_id_map = {"Ch.01": "nuscale_ch01", "Ch.05": "nuscale_ch05"}

    def answer_fn(question: str, evidence: list[dict] | None = None) -> str:
        doc_ids = list(env.documents.keys())
        if evidence:
            mapped = set()
            for ev in evidence:
                src = ev.get("source_document", "")
                if src in doc_id_map and doc_id_map[src] in env.documents:
                    mapped.add(doc_id_map[src])
            if mapped:
                doc_ids = list(mapped)

        agent = GWMAgent(
            environment=env, model="gpt-4.1",
            max_hops=max_hops, top_k=top_k,
        )
        result = agent.run(question=question, doc_ids=doc_ids)
        return result["answer"]

    return answer_fn


# ── Model registry ──────────────────────────────────────────

OPENAI_MODELS = {"gpt-4o", "gpt-4-turbo", "gpt-4.1", "gpt-4o-mini"}
ANTHROPIC_MODELS = {"claude-sonnet", "claude-opus"}
ANTHROPIC_MODEL_MAP = {
    "claude-sonnet": "claude-sonnet-4-5-20250929",
    "claude-opus": "claude-opus-4-6-20250610",
}


# ── Main ─────────────────────────────────────────────────────

def collect_answers(
    dataset_path: str,
    method: str,
    output_path: str,
    tree_dir: str | None = None,
    max_hops: int = 4,
    top_k: int = 2,
    start: int | None = None,
    end: int | None = None,
) -> str:
    """답변 수집 실행."""

    # 데이터셋 로드
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions", [])

    # 범위 필터
    if start or end:
        start_idx = (start or 1) - 1
        end_idx = end or len(questions)
        questions = questions[start_idx:end_idx]

    print(f"\n{'='*60}")
    print(f"Baseline 답변 수집: {method}")
    print(f"  데이터셋: {Path(dataset_path).name}")
    print(f"  문항 수: {len(questions)}")
    print(f"{'='*60}\n")

    # 모델 생성
    if method == "gwm":
        if not tree_dir:
            tree_dir = str(ROOT / "data" / "trees")
        answer_fn = make_gwm_baseline(tree_dir, max_hops, top_k)
        is_gwm = True
    elif method in OPENAI_MODELS:
        answer_fn = make_openai_baseline(method)
        is_gwm = False
    elif method in ANTHROPIC_MODELS:
        answer_fn = make_anthropic_baseline(ANTHROPIC_MODEL_MAP[method])
        is_gwm = False
    else:
        raise ValueError(f"지원하지 않는 모델: {method}. "
                         f"지원: {OPENAI_MODELS | ANTHROPIC_MODELS | {'gwm'}}")

    # 답변 수집
    results = []
    errors = 0
    total_start = time.time()

    for i, q in enumerate(tqdm(questions, desc=f"Collecting [{method}]")):
        try:
            if is_gwm:
                answer = answer_fn(q["question"], q.get("ground_truth_evidence"))
            else:
                answer = answer_fn(q["question"])
        except Exception as e:
            print(f"\n  ❌ [{q['id']}] 에러: {e}")
            answer = f"ERROR: {e}"
            errors += 1

        results.append({
            "id": q["id"],
            "question": q["question"],
            "reasoning_type": q.get("reasoning_type"),
            "complexity": q.get("complexity"),
            "question_type": q.get("question_type"),
            "generated_answer": answer,
            "expected_answer": q.get("expected_answer", ""),
        })

        # 10문항마다 중간 저장
        if (i + 1) % 10 == 0:
            _save_output(output_path, method, results)

    elapsed = time.time() - total_start

    # 최종 저장
    _save_output(output_path, method, results)

    print(f"\n{'='*60}")
    print(f"완료: {len(results)}문항, 에러 {errors}건")
    print(f"소요: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"저장: {output_path}")
    return output_path


def _save_output(output_path: str, method: str, results: list[dict]):
    os.makedirs(Path(output_path).parent, exist_ok=True)
    output = {
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GWM Benchmark baseline 답변 수집")
    parser.add_argument(
        "--method", "-m", required=True,
        help=f"모델명: gwm, {', '.join(sorted(OPENAI_MODELS | ANTHROPIC_MODELS))}",
    )
    parser.add_argument(
        "--dataset", default=str(BENCHMARK_V2_PATH),
        help="데이터셋 경로",
    )
    parser.add_argument("--output", "-o", required=True, help="출력 JSON 경로")
    parser.add_argument("--tree-dir", default=None, help="GWM 트리 디렉토리 (gwm 전용)")
    parser.add_argument("--max-hops", type=int, default=4, help="GWM max hops")
    parser.add_argument("--top-k", type=int, default=2, help="GWM top-k")
    parser.add_argument("--start", type=int, default=None, help="시작 문항 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 (inclusive)")
    args = parser.parse_args()

    collect_answers(
        dataset_path=args.dataset,
        method=args.method,
        output_path=args.output,
        tree_dir=args.tree_dir,
        max_hops=args.max_hops,
        top_k=args.top_k,
        start=args.start,
        end=args.end,
    )
