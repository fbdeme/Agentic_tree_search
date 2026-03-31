# -*- coding: utf-8 -*-
"""PDF → GraphRAG input 텍스트 추출.

NuScale FSAR PDF 2개를 graphrag/input/ 에 텍스트 파일로 저장합니다.

Usage:
    python graphrag/extract_text.py
"""

import fitz  # PyMuPDF
from pathlib import Path

DOCUMENTS = [
    ("NuScale FSAR Ch.01 (공개본).pdf", "nuscale_ch01.txt"),
    ("NuScale FSAR Ch.05 (공개본).pdf", "nuscale_ch05.txt"),
]

DOC_DIR = Path(__file__).parent.parent / "data" / "documents"
INPUT_DIR = Path(__file__).parent / "input"
INPUT_DIR.mkdir(exist_ok=True)


def extract(pdf_path: Path, out_path: Path):
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(f"[Page {page.number + 1}]\n{text.strip()}")
    doc.close()
    out_path.write_text("\n\n".join(pages), encoding="utf-8")
    print(f"  {pdf_path.name} → {out_path.name} ({len(pages)} pages)")


if __name__ == "__main__":
    print("PDF 텍스트 추출 시작...")
    for pdf_name, txt_name in DOCUMENTS:
        pdf_path = DOC_DIR / pdf_name
        out_path = INPUT_DIR / txt_name
        if not pdf_path.exists():
            print(f"  [SKIP] {pdf_name} not found")
            continue
        extract(pdf_path, out_path)
    print("완료. graphrag/input/ 확인하세요.")
