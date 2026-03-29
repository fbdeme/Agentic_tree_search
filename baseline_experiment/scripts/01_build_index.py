#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step 1 — RAPTOR 트리 인덱스 구축.

NuScale FSAR PDF 파일을 읽어 RAPTOR 재귀 요약 트리를 구축하고
baseline_experiment/raptor/index/raptor_tree.json 에 저장합니다.

Usage:
    # 기본 (data/documents/ 아래 PDF 자동 탐색)
    python baseline_experiment/scripts/01_build_index.py

    # PDF 디렉토리 명시
    python baseline_experiment/scripts/01_build_index.py --pdf-dir data/documents

    # 저장 경로 지정
    python baseline_experiment/scripts/01_build_index.py \\
        --output baseline_experiment/raptor/index/raptor_tree.json

Prerequisites:
    pip install umap-learn scikit-learn tiktoken PyMuPDF openai numpy python-dotenv
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from baseline_experiment.raptor.config import PDF_FILES, INDEX_DIR
from baseline_experiment.raptor.pipeline import build_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("01_build_index")


def _resolve_pdf_paths(pdf_dir: str | None) -> dict[str, str]:
    """PDF 경로 딕셔너리 반환. doc_id는 파일명에서 자동 추론."""
    if pdf_dir:
        pdf_files = sorted(Path(pdf_dir).glob("*.pdf"))
    else:
        pdf_files = [p for p in PDF_FILES if p.exists()]

    if not pdf_files:
        return {}

    result = {}
    for p in pdf_files:
        name = p.stem.lower()
        if "ch.01" in name or "ch01" in name or "chapter_1" in name:
            doc_id = "nuscale_ch01"
        elif "ch.05" in name or "ch05" in name or "chapter_5" in name:
            doc_id = "nuscale_ch05"
        else:
            doc_id = p.stem.replace(" ", "_").lower()
        result[doc_id] = str(p)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAPTOR 트리 인덱스 구축",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf-dir", default=None,
        help="PDF 디렉토리 (기본: data/documents/)",
    )
    parser.add_argument(
        "--output", default=None,
        help=f"트리 저장 경로 (기본: {INDEX_DIR / 'raptor_tree.json'})",
    )
    args = parser.parse_args()

    pdf_paths = _resolve_pdf_paths(args.pdf_dir)

    if not pdf_paths:
        logger.error("PDF 파일을 찾을 수 없습니다.")
        logger.error(f"  기본 위치: {[str(p) for p in PDF_FILES]}")
        logger.error("  --pdf-dir 옵션으로 디렉토리를 지정하세요.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("RAPTOR 트리 인덱스 구축")
    print(f"  PDF: {len(pdf_paths)}개")
    for doc_id, path in pdf_paths.items():
        print(f"    [{doc_id}] {path}")
    save_target = args.output or str(INDEX_DIR / "raptor_tree.json")
    print(f"  저장: {save_target}")
    print(f"{'='*60}\n")

    t0 = time.time()
    tree = build_index(pdf_paths, save_path=args.output)
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print("인덱싱 완료!")
    print(f"  전체 노드:  {len(tree.all_nodes)}")
    print(f"  리프 노드:  {len(tree.leaf_nodes)}")
    print(f"  요약 노드:  {len(tree.all_nodes) - len(tree.leaf_nodes)}")
    print(f"  소요 시간:  {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
