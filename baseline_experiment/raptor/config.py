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
# RAPTOR 원논문: 100 tokens, 문장 경계 존중 (Sarthi et al. 2024, §3)
CHUNK_SIZE = 100        # tokens (tiktoken cl100k_base)

# ── Embedding ─────────────────────────────────────────────────
# 원논문: multi-qa-mpnet-base-cos-v1 (SentenceTransformer)
# OpenAI 생태계 통일을 위해 text-embedding-3-small 사용 (note.md에 기록)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 100

# ── Clustering (UMAP + GMM) ────────────────────────────────────
# 원논문 cluster_utils.py 기준
UMAP_N_COMPONENTS = 10          # 기본 목표 차원
UMAP_METRIC = "cosine"          # 원논문 명시 metric
# n_neighbors: Global = int((n-1)**0.5), Local = 10  (dynamic, see clustering.py)
GMM_MAX_CLUSTERS = 50           # BIC 탐색 최대 k
GMM_THRESHOLD = 0.1             # soft-assignment 확률 임계값 (원논문 GMM_THRES=0.1)

# ── Tree building ──────────────────────────────────────────────
MAX_LEVELS = 3           # 재귀 레벨 상한 (원논문: 수렴될 때까지 → 실용적 상한 적용)
MIN_CLUSTER_SIZE = 2     # 요약 생성을 위한 클러스터 최소 노드 수

# ── Retrieval ─────────────────────────────────────────────────
# 원논문 실험 결과: collapse_tree가 tree_traversal보다 성능 우위
RETRIEVAL_MODE = "collapse_tree"   # "collapse_tree" | "tree_traversal"
CONTEXT_TOKEN_BUDGET = 2000        # 검색 컨텍스트 최대 토큰 수 (원논문 기준)
TOP_K = 10                         # collapse_tree fallback: 최대 노드 수

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
