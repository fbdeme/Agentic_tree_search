# -*- coding: utf-8 -*-
"""교차 비교 리포트 생성기.

여러 모델의 LLM-as-Judge 결과를 로드하여 비교 테이블 및 히트맵을 생성합니다.

Usage:
    python -m benchmark.aggregate_results benchmark/results/judge_*.json --output benchmark/results/comparison/
"""

import json
import os
import argparse
from pathlib import Path

import pandas as pd

from benchmark.config import REASONING_TYPES, COMPLEXITY_LEVELS, QUESTION_TYPES


def load_judge_results(paths: list[str]) -> dict[str, dict]:
    """여러 결과 파일 로드, method명으로 key."""
    results = {}
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        method = data.get("source", Path(p).stem).replace("pred_", "").replace("_llm_judge_results", "")
        results[method] = data
    return results


def build_comparison_table(results: dict[str, dict]) -> pd.DataFrame:
    """비교 테이블: rows=methods, columns=accuracy by axis."""
    rows = []
    for method, data in results.items():
        summary = data.get("summary", {})
        row = {
            "method": method,
            "total": summary.get("total", 0),
            "accuracy": summary.get("accuracy", 0),
        }

        # question_type별
        for qt in QUESTION_TYPES:
            stats = data.get("by_question_type", {}).get(qt, {})
            row[f"qt_{qt}"] = stats.get("accuracy", 0)

        # reasoning_type별
        for rt in REASONING_TYPES:
            stats = data.get("by_reasoning_type", {}).get(rt, {})
            row[f"rt_{rt}"] = stats.get("accuracy", 0)

        # complexity별
        for cx in COMPLEXITY_LEVELS:
            stats = data.get("by_complexity", {}).get(cx, {})
            row[f"cx_{cx}"] = stats.get("accuracy", 0)

        rows.append(row)

    return pd.DataFrame(rows).set_index("method")


def build_matrix_heatmap(data: dict, method: str, output_dir: str):
    """9셀 히트맵 (reasoning_type × complexity) 생성."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("  ⚠️ matplotlib/seaborn 미설치, 히트맵 건너뜀")
        return

    matrix = data.get("matrix_9cell", {})
    grid = []
    for rt in REASONING_TYPES:
        row = []
        for cx in COMPLEXITY_LEVELS:
            key = f"{rt}_{cx}"
            stats = matrix.get(key, {})
            row.append(stats.get("accuracy", 0))
        grid.append(row)

    df = pd.DataFrame(grid, index=REASONING_TYPES, columns=COMPLEXITY_LEVELS)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        df, annot=True, fmt=".1%", cmap="YlGnBu",
        vmin=0, vmax=1, ax=ax,
        linewidths=0.5, linecolor="white",
    )
    ax.set_title(f"Accuracy Matrix: {method}")
    ax.set_ylabel("Reasoning Type")
    ax.set_xlabel("Complexity")
    plt.tight_layout()

    out = Path(output_dir) / f"heatmap_{method}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  히트맵 저장: {out}")


def run_aggregation(result_paths: list[str], output_dir: str):
    """메인: 로드 → 비교 → 저장."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"교차 비교 리포트 생성")
    print(f"  입력: {len(result_paths)}개 파일")
    print(f"  출력: {output_dir}")
    print(f"{'='*60}\n")

    results = load_judge_results(result_paths)

    # 비교 테이블
    df = build_comparison_table(results)
    csv_path = Path(output_dir) / "comparison_table.csv"
    df.to_csv(csv_path)
    print(f"비교 테이블 저장: {csv_path}")
    print(f"\n{df.to_string()}\n")

    # 히트맵
    for method, data in results.items():
        build_matrix_heatmap(data, method, output_dir)

    # JSON 요약
    summary = {}
    for method, data in results.items():
        summary[method] = {
            "accuracy": data.get("summary", {}).get("accuracy", 0),
            "by_question_type": {
                qt: data.get("by_question_type", {}).get(qt, {}).get("accuracy", 0)
                for qt in QUESTION_TYPES
            },
            "by_reasoning_type": {
                rt: data.get("by_reasoning_type", {}).get(rt, {}).get("accuracy", 0)
                for rt in REASONING_TYPES
            },
            "by_complexity": {
                cx: data.get("by_complexity", {}).get(cx, {}).get("accuracy", 0)
                for cx in COMPLEXITY_LEVELS
            },
        }

    json_path = Path(output_dir) / "comparison_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"JSON 요약 저장: {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="교차 비교 리포트 생성")
    parser.add_argument("results", nargs="+", help="LLM-as-Judge 결과 JSON 파일들")
    parser.add_argument("--output", "-o", default="benchmark/results/comparison/", help="출력 디렉토리")
    args = parser.parse_args()

    run_aggregation(args.results, args.output)
