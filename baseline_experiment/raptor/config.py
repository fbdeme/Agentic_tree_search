# -*- coding: utf-8 -*-
"""RAPTOR baseline 설정.

비교 공정성 규칙 (baseline_experiment_guide.md §4):
  - 생성 LLM: gpt-4.1
  - Temperature: 0
  - 답변 길이: max_tokens=300
  - System prompt: GWM과 동일
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent       # Agentic_tree_search/
DATA_DIR = ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
QA_DATASET_PATH = DATA_DIR / "qa_dataset" / "multihop_qa_benchmark_v2.json"

INDEX_DIR = Path(__file__).parent / "index"      # baseline_experiment/raptor/index/
RESULTS_DIR = Path(__file__).parent.parent / "results" / "raptor"  # baseline_experiment/results/raptor/

# Source PDFs (NRC public documents)
PDF_FILES = [
    DOCUMENTS_DIR / "NuScale FSAR Ch.01 (공개본).pdf",
    DOCUMENTS_DIR / "NuScale FSAR Ch.05 (공개본).pdf",
]

# ── Chunking ───────────────────────────────────────────────────
CHUNK_SIZE = 512        # tokens (tiktoken cl100k_base)
CHUNK_OVERLAP = 50      # token overlap between adjacent chunks

# ── Embedding ─────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 100

# ── Clustering (UMAP + GMM) ────────────────────────────────────
UMAP_N_COMPONENTS = 10
UMAP_N_NEIGHBORS = 15
GMM_MAX_CLUSTERS = 50
GMM_THRESHOLD = 0.5     # soft-assignment probability cutoff

# ── Tree building ──────────────────────────────────────────────
MAX_LEVELS = 3           # max recursive levels above leaves
MIN_CLUSTER_SIZE = 2     # min nodes per cluster to produce a summary

# ── Retrieval ─────────────────────────────────────────────────
RETRIEVAL_MODE = "collapse_tree"   # "collapse_tree" | "tree_traversal"
TOP_K = 5                          # chunks / summary nodes returned

# ── Generation (§4.1 — must match GWM settings) ───────────────
GENERATION_MODEL = "gpt-4.1"
TEMPERATURE = 0
MAX_TOKENS = 300

SYSTEM_PROMPT = (
    "You are an expert AI for nuclear regulatory review. "
    "Based on the provided context, answer the user's question. "
    "Answer in 1-2 sentences ONLY. "
    "State the direct answer with specific values, then cite the source. "
    "Do NOT add uncertainty statements, background, or methodology. "
    "Do NOT add information not found in the provided context. "
    "Answer in English."
)
