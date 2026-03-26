# -*- coding: utf-8 -*-
"""GWM Benchmark 평가 설정 (MAM-RAG 논문 Table 8 기준)"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Taxonomy axes ──────────────────────────────────────────────
REASONING_TYPES = ["factual", "comparative", "judgment"]
COMPLEXITY_LEVELS = ["single_evidence", "multi_evidence", "cross_document"]
QUESTION_TYPES = ["text_only", "table_only", "image_only", "composite"]

# 9-cell matrix (reasoning_type × complexity)
MATRIX_CELLS = [(r, c) for r in REASONING_TYPES for c in COMPLEXITY_LEVELS]

# ── LLM-as-Judge 모델 (논문 Table 8) ──────────────────────────
TONIC_MODEL = "gpt-4-turbo"                     # Similarity 0-5, ≥4 → O
MLFLOW_MODEL = "openai:/gpt-4o"                  # Similarity+Correctness 1-5, both≥4 → O
ALLGANIZE_MODEL = "claude-sonnet-4-5-20250929"   # Correctness 0/1, =1 → O

VOTE_THRESHOLD = 4  # Tonic, MLflow 기준

# ── Dataset paths ──────────────────────────────────────────────
BENCHMARK_V2_PATH = ROOT / "data" / "qa_dataset" / "multihop_qa_benchmark_v2.json"
RESULTS_DIR = ROOT / "benchmark" / "results"

# ── Required schema fields ─────────────────────────────────────
REQUIRED_FIELDS = [
    "id", "question", "reasoning_type", "complexity",
    "question_type", "expected_answer", "answer_keywords",
    "ground_truth_evidence",
]

EVIDENCE_REQUIRED_FIELDS = [
    "source_document", "source_type", "page_number", "relevant_text",
]
