"""
Build PageIndex trees from actual NuScale FSAR PDFs.
Includes Figure/Table metadata extraction and reference linking.

Usage:
    cd /Users/jeonmingyu/workspace_2026/Agentic_tree_search
    source .venv/bin/activate
    python experiments/build_trees.py

Output:
    data/trees/nuscale_ch01_structure.json
    data/trees/nuscale_ch05_structure.json
"""

import sys
import os
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "pageindex_core"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from pageindex import config, page_index_main


# ── Config ────────────────────────────────────────────────────────
PDF_CONFIGS = [
    {
        "pdf_path": ROOT / "data/documents/NuScale FSAR Ch.01 (공개본).pdf",
        "doc_id": "nuscale_ch01",
        "doc_name": "NuScale FSAR Chapter 01 - Introduction and General Description",
    },
    {
        "pdf_path": ROOT / "data/documents/NuScale FSAR Ch.05 (공개본).pdf",
        "doc_id": "nuscale_ch05",
        "doc_name": "NuScale FSAR Chapter 05 - Reactor Coolant System",
    },
]

OUTPUT_DIR = ROOT / "data/trees"


# ── Figure/Table metadata extraction ─────────────────────────────

def extract_figure_table_metadata(pdf_path: str) -> tuple[dict, dict]:
    """
    Scan all PDF pages to find Figure and Table captions.
    Returns (figures_dict, tables_dict) with page numbers and captions.

    Strategy: Find all pages containing "Figure X.Y-Z:" or "Table X.Y-Z:" captions.
    Take the LAST occurrence of each ID as the actual location (first occurrence is
    in the LIST OF FIGURES/TABLES in the front matter).
    """
    doc = fitz.open(pdf_path)

    # Collect ALL occurrences, keep last one per ID
    figures = {}
    tables = {}

    fig_pattern = re.compile(r'(Figure\s+\d+\.\d+-\d+)\s*:\s*(.+?)(?:\n|$)')
    tbl_pattern = re.compile(r'(Table\s+\d+\.\d+-\d+)\s*:\s*(.+?)(?:\n|$)')

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        for match in fig_pattern.finditer(text):
            fig_id = match.group(1).strip()
            caption = match.group(2).strip()
            # Remove trailing dots and page numbers from LIST entries
            caption = re.sub(r'\s*\.{3,}.*$', '', caption).strip()
            figures[fig_id] = {
                "page": page_num + 1,  # 1-indexed
                "caption": caption,
            }

        for match in tbl_pattern.finditer(text):
            tbl_id = match.group(1).strip()
            caption = match.group(2).strip()
            caption = re.sub(r'\s*\.{3,}.*$', '', caption).strip()
            tables[tbl_id] = {
                "page": page_num + 1,
                "caption": caption,
            }

    doc.close()
    return figures, tables


def add_references_to_nodes(nodes: list, figures: dict, tables: dict) -> int:
    """
    Walk tree nodes and add 'references' field by matching
    "Figure X.Y-Z" and "Table X.Y-Z" patterns in node text.
    Returns total number of references added.
    """
    ref_pattern = re.compile(r'((?:Figure|Table)\s+\d+\.\d+-\d+)')
    total_refs = 0

    for node in nodes:
        text = node.get("text", "") + " " + node.get("summary", "")
        matches = set(ref_pattern.findall(text))

        references = []
        for ref_id in sorted(matches):
            if ref_id in figures:
                references.append({
                    "type": "figure",
                    "id": ref_id,
                    "page": figures[ref_id]["page"],
                    "caption": figures[ref_id]["caption"],
                })
            elif ref_id in tables:
                references.append({
                    "type": "table",
                    "id": ref_id,
                    "page": tables[ref_id]["page"],
                    "caption": tables[ref_id]["caption"],
                })

        if references:
            node["references"] = references
            total_refs += len(references)

        # Recurse into children
        children = node.get("nodes", [])
        if children:
            total_refs += add_references_to_nodes(children, figures, tables)

    return total_refs


# ── Tree building ─────────────────────────────────────────────────

def build_tree(pdf_path: str, doc_id: str, doc_name: str) -> dict:
    """PDF → PageIndex tree → convert format → enrich with references"""
    print(f"\n{'='*60}")
    print(f"📄 Tree generation: {doc_name}")
    print(f"   PDF: {pdf_path}")
    print(f"{'='*60}")

    opt = config(
        model="gpt-4.1",
        toc_check_page_num=20,
        max_page_num_each_node=10,
        max_token_num_each_node=20000,
        if_add_node_id="yes",
        if_add_node_summary="yes",
        if_add_doc_description="no",
        if_add_node_text="yes",
    )

    raw_tree = page_index_main(str(pdf_path), opt)
    print(f"✅ PageIndex parsing complete")

    # Convert format
    structure = raw_tree.get("structure", raw_tree.get("tree", []))
    converted_tree = convert_nodes(structure)

    # Extract figure/table metadata
    print(f"🔍 Extracting Figure/Table metadata...")
    figures, tables = extract_figure_table_metadata(str(pdf_path))
    print(f"   Found {len(figures)} figures, {len(tables)} tables")

    # Add references to nodes
    total_refs = add_references_to_nodes(converted_tree, figures, tables)
    print(f"   Linked {total_refs} references to tree nodes")

    result = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "pdf_path": str(pdf_path),
        "figures": figures,
        "tables": tables,
        "tree": converted_tree,
    }

    return result


def convert_nodes(nodes: list) -> list:
    """Convert PageIndex output nodes to environment-compatible format."""
    converted = []
    for node in nodes:
        new_node = {
            "title": node.get("title", "Untitled"),
            "node_id": node.get("node_id", ""),
            "page_index": node.get("start_index", node.get("page_index", 0)),
            "summary": node.get("summary", ""),
            "text": node.get("text", node.get("summary", "")),
        }
        children = node.get("nodes", [])
        new_node["nodes"] = convert_nodes(children) if children else []
        converted.append(new_node)
    return converted


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for cfg in PDF_CONFIGS:
        pdf_path = cfg["pdf_path"]
        if not os.path.isfile(pdf_path):
            print(f"⚠️  PDF not found, skipping: {pdf_path}")
            continue

        tree_data = build_tree(
            pdf_path=str(pdf_path),
            doc_id=cfg["doc_id"],
            doc_name=cfg["doc_name"],
        )

        output_path = OUTPUT_DIR / f"{cfg['doc_id']}_structure.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tree_data, f, indent=2, ensure_ascii=False)

        def count_nodes(nodes):
            total = len(nodes)
            for n in nodes:
                total += count_nodes(n.get("nodes", []))
            return total

        n_nodes = count_nodes(tree_data["tree"])
        n_figs = len(tree_data["figures"])
        n_tbls = len(tree_data["tables"])
        print(f"💾 Saved: {output_path} ({n_nodes} nodes, {n_figs} figures, {n_tbls} tables)")

    print(f"\n{'='*60}")
    print(f"✅ All trees generated: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
