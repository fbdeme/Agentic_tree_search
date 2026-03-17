"""
Vision utilities: PDF page rendering for VLM integration.
Renders specific PDF pages as images for GPT-4.1 vision input.
"""

import base64
import os
from pathlib import Path

import fitz  # PyMuPDF


def render_pdf_pages(
    pdf_path: str,
    page_numbers: list[int],
    zoom: float = 2.0,
    output_dir: str | None = None,
) -> list[dict]:
    """
    Render specific PDF pages as JPEG images.

    Args:
        pdf_path: Path to PDF file
        page_numbers: List of 1-indexed page numbers to render
        zoom: Zoom factor for image quality (2.0 = 144 DPI)
        output_dir: Optional directory to save images. If None, only returns base64.

    Returns:
        List of {"page": int, "base64": str, "path": str|None}
    """
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(zoom, zoom)
    results = []

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for page_num in page_numbers:
        if page_num < 1 or page_num > len(doc):
            continue

        page = doc.load_page(page_num - 1)  # fitz uses 0-indexed
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_data).decode("utf-8")

        path = None
        if output_dir:
            path = os.path.join(output_dir, f"page_{page_num}.jpg")
            with open(path, "wb") as f:
                f.write(img_data)

        results.append({"page": page_num, "base64": b64, "path": path})

    doc.close()
    return results


def build_vision_content(prompt: str, image_base64_list: list[str]) -> list[dict]:
    """
    Build OpenAI vision API content array with text + images.

    Args:
        prompt: Text prompt
        image_base64_list: List of base64-encoded JPEG images

    Returns:
        Content array for OpenAI chat API message
    """
    content = [{"type": "text", "text": prompt}]
    for b64 in image_base64_list:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    return content
