#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 2 — 200문항 답변 수집 (RAPTOR 추론).

트리 인덱스를 로드하고 QA 데이터셋 전체(또는 일부)에 대해
RAPTOR 방식으로 검색 + 생성하여 predictions JSON을 저장합니다.

Usage:
    # 전체 200문항
    python baseline_experiment/scripts/02_run_inference.py

    # 파일럿 (1~10번 문항)
    python baseline_experiment/scripts/02_run_inference.py --start 1 --end 10

    # 분할 실행 (1~50번)
    python baseline_experiment/scripts/02_run_inference.py \\
        --start 1 --end 50 \\
        --output baseline_experiment/results/raptor/pred_1.json

Prerequisites:
    01_build_index.py 실행 완료 (baseline_experiment/raptor/index/raptor_tree.json 존재)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from baseline_experiment.raptor.config import INDEX_DIR, QA_DATASET_PATH, RETRIEVAL_MODE, TOP_K
from baseline_experiment.raptor.tree_builder import RAPTORTree
from baseline_experiment.raptor.pipeline import run_inference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("02_run_inference")

DEFAULT_TREE = INDEX_DIR / "raptor_tree.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAPTOR 200문항 추론",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tree", default=str(DEFAULT_TREE),
        help=f"트리 JSON 경로 (기본: {DEFAULT_TREE})",
    )
    parser.add_argument(
        "--dataset", default=str(QA_DATASET_PATH),
        help="QA 데이터셋 경로",
    )
    parser.add_argument(
        "--output", default=None,
        help="출력 JSON (기본: baseline_experiment/results/raptor/pred.json)",
    )
    parser.add_argument("--start", type=int, default=None, help="시작 문항 번호 (1-based)")
    parser.add_argument("--end",   type=int, default=None, help="종료 문항 번호 (inclusive)")
    args = parser.parse_args()

    if not Path(args.tree).exists():
        logger.error(f"트리 파일 없음: {args.tree}")
        logger.error("먼저 01_build_index.py를 실행하세요.")
        sys.exit(1)

    range_str = ""
    if args.start or args.end:
        range_str = f"  범위: {args.start or 1} ~ {args.end or 200}\n"

    print(f"\n{'='*60}")
    print("RAPTOR 추론")
    print(f"  트리:      {args.tree}")
    print(f"  데이터셋:  {args.dataset}")
    print(f"  검색 모드: {RETRIEVAL_MODE}, top_k={TOP_K}")
    if range_str:
        print(range_str.rstrip())
    print(f"{'='*60}\n")

    logger.info("트리 로드 중...")
    tree = RAPTORTree.load(args.tree)
    logger.info(f"  {len(tree.all_nodes)}개 노드 로드 완료")

    t0 = time.time()
    output_path = run_inference(
        tree=tree,
        dataset_path=args.dataset,
        output_path=args.output,
        start=args.start,
        end=args.end,
    )
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"추론 완료: {output_path}")
    print(f"  소요: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"  다음 단계: 03_run_judge.py --pred {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
