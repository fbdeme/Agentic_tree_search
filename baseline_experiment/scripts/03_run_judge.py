#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 3 — LLM-as-Judge 평가 실행.

기존 benchmark.llm_judge 모듈을 그대로 사용합니다.
3개 evaluator(Tonic / MLflow / Allganize) 순차 실행 → 4표 majority vote → Accuracy.

예상 소요: ~100분 (200문항 × ~30초)
예상 비용: ~$13 (GPT-4-turbo + GPT-4o + Claude Sonnet 4.5)

Usage:
    # 기본 (pred.json → judge.json)
    python baseline_experiment/scripts/03_run_judge.py

    # 경로 지정
    python baseline_experiment/scripts/03_run_judge.py \\
        --pred baseline_experiment/results/raptor/pred.json \\
        --output baseline_experiment/results/raptor/judge.json

    # 결과 확인
    python baseline_experiment/scripts/03_run_judge.py --show-results
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "baseline_experiment" / "results" / "raptor"
DEFAULT_PRED = RESULTS_DIR / "pred.json"
DEFAULT_JUDGE = RESULTS_DIR / "judge.json"


def show_results(judge_path: str) -> None:
    """judge.json 결과 요약 출력."""
    with open(judge_path, encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    print(f"\n{'='*60}")
    print("RAPTOR Baseline — LLM-as-Judge 결과")
    print(f"  전체 Accuracy: {summary.get('accuracy', 0) * 100:.1f}%  "
          f"({summary.get('correct', '?')}/{summary.get('total', '?')})")
    print()

    for axis, key in [("reasoning_type", "by_reasoning_type"), ("complexity", "by_complexity")]:
        section = data.get(key, {})
        if section:
            print(f"  {axis}:")
            for label, stats in section.items():
                acc = stats.get("accuracy", 0) * 100
                n   = stats.get("total", "?")
                print(f"    {label:20s}: {acc:.1f}% (n={n})")
            print()
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-as-Judge 평가 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pred", default=str(DEFAULT_PRED),
        help=f"predictions JSON (기본: {DEFAULT_PRED})",
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_JUDGE),
        help=f"judge 결과 경로 (기본: {DEFAULT_JUDGE})",
    )
    parser.add_argument(
        "--show-results", action="store_true",
        help="judge.json 결과만 출력하고 종료",
    )
    args = parser.parse_args()

    if args.show_results:
        if not Path(args.output).exists():
            print(f"ERROR: judge 파일 없음: {args.output}")
            sys.exit(1)
        show_results(args.output)
        return

    if not Path(args.pred).exists():
        print(f"ERROR: pred 파일 없음: {args.pred}")
        print("먼저 02_run_inference.py를 실행하세요.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("LLM-as-Judge 평가 시작")
    print(f"  입력:      {args.pred}")
    print(f"  출력:      {args.output}")
    print(f"  예상 시간: ~100분 (200문항 × ~30초)")
    print(f"  예상 비용: ~$13 (GPT-4-turbo + GPT-4o + Claude Sonnet 4.5)")
    print(f"{'='*60}\n")

    # benchmark.llm_judge 실행
    cmd = [
        sys.executable, "-m", "benchmark.llm_judge",
        args.pred,
        "--output", args.output,
    ]
    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode == 0:
        print(f"\n평가 완료: {args.output}")
        print("결과 확인: python baseline_experiment/scripts/03_run_judge.py --show-results")
    else:
        print(f"\nERROR: 평가 실패 (returncode={result.returncode})")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
