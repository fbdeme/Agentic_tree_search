# -*- coding: utf-8 -*-
"""GraphRAG로 벤치마크 200문항 답변 수집.

로컬 검색(local_search)과 글로벌 검색(global_search) 중
기본값으로 local_search를 사용합니다. 멀티홉 질의에는 local이 더 적합합니다.

Usage:
    # 전체 200문항
    python graphrag/run_graphrag.py

    # 범위 지정
    python graphrag/run_graphrag.py --start 1 --end 10

    # 글로벌 검색
    python graphrag/run_graphrag.py --search-type global

    # 건식 실행 (설정 확인만)
    python graphrag/run_graphrag.py --dry-run
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import tiktoken

_enc = tiktoken.get_encoding("o200k_base")

def count_tokens(text: str) -> int:
    return len(_enc.encode(str(text)))

from dotenv import load_dotenv
from tqdm import tqdm

# graphrag/.env 로드 (GRAPHRAG_API_KEY)
load_dotenv(Path(__file__).parent / ".env")
# 프로젝트 루트 .env 로드 (OPENAI_API_KEY fallback)
load_dotenv(Path(__file__).parent.parent / ".env")

# GRAPHRAG_API_KEY가 없으면 OPENAI_API_KEY로 채움
if not os.getenv("GRAPHRAG_API_KEY") or os.getenv("GRAPHRAG_API_KEY") == "<API_KEY>":
    openai_key = os.getenv("OPENAI_API_KEY", "")
    os.environ["GRAPHRAG_API_KEY"] = openai_key

ROOT = Path(__file__).parent.parent
GRAPHRAG_ROOT = Path(__file__).parent
BENCHMARK_PATH = ROOT / "data" / "qa_dataset" / "multihop_qa_benchmark_v2.json"
RESULTS_DIR = ROOT / "benchmark" / "results" / "graphrag"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "You are an expert AI for nuclear regulatory review. "
    "Based on the provided context, answer the user's question. "
    "Answer in 1-2 sentences ONLY. "
    "State the direct answer with specific values, then cite the source. "
    "Do NOT add uncertainty statements, background, or methodology. "
    "Do NOT add information not found in the provided context. "
    "Answer in English."
)


def load_index():
    """GraphRAG 인덱스 파라콘텍스트 로드."""
    import graphrag.api as api
    from graphrag.config.load_config import load_config

    config = load_config(GRAPHRAG_ROOT)
    return config


async def run_local_search(question: str, config) -> tuple[str, list[str], dict]:
    """Local search로 답변 생성."""
    import graphrag.api as api
    import pandas as pd

    output_dir = GRAPHRAG_ROOT / "output"

    # 인덱스 데이터 로드
    entities = pd.read_parquet(output_dir / "entities.parquet")
    relationships = pd.read_parquet(output_dir / "relationships.parquet")
    communities = pd.read_parquet(output_dir / "communities.parquet")
    community_reports = pd.read_parquet(output_dir / "community_reports.parquet")
    text_units = pd.read_parquet(output_dir / "text_units.parquet")
    covariates = None  # extract_claims 비활성화

    # 임베딩 로드
    try:
        entity_embeddings = pd.read_parquet(
            output_dir / "embeddings.entity.description.parquet"
        )
    except FileNotFoundError:
        entity_embeddings = None

    response, context = await api.local_search(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        text_units=text_units,
        relationships=relationships,
        covariates=covariates,
        community_level=2,
        response_type="Single Paragraph",
        query=question,
    )

    contexts = []
    context_text = ""
    if isinstance(context, dict):
        sources = context.get("sources")
        if sources is not None and hasattr(sources, "itertuples"):
            for row in sources.head(5).itertuples():
                text = getattr(row, "text", "") or ""
                contexts.append(str(text)[:500])
                context_text += str(text)

    response_str = str(response)
    tokens = {
        "prompt_tokens": count_tokens(question) + count_tokens(context_text),
        "completion_tokens": count_tokens(response_str),
    }
    tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]

    return response_str, contexts, tokens


async def run_global_search(question: str, config) -> tuple[str, list[str], dict]:
    """Global search로 답변 생성."""
    import graphrag.api as api
    import pandas as pd

    output_dir = GRAPHRAG_ROOT / "output"

    entities = pd.read_parquet(output_dir / "entities.parquet")
    communities = pd.read_parquet(output_dir / "communities.parquet")
    community_reports = pd.read_parquet(output_dir / "community_reports.parquet")

    response, context = await api.global_search(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        community_level=2,
        dynamic_community_selection=False,
        response_type="Single Paragraph",
        query=question,
    )

    contexts = []
    context_text = ""
    if isinstance(context, dict):
        sources = context.get("sources")
        if sources is not None and hasattr(sources, "itertuples"):
            for row in sources.head(5).itertuples():
                text = getattr(row, "text", "") or ""
                contexts.append(str(text)[:500])
                context_text += str(text)

    response_str = str(response)
    tokens = {
        "prompt_tokens": count_tokens(question) + count_tokens(context_text),
        "completion_tokens": count_tokens(response_str),
    }
    tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]

    return response_str, contexts, tokens


def collect_answers(
    search_type: str = "local",
    start: int | None = None,
    end: int | None = None,
    output_path: Path | None = None,
    dry_run: bool = False,
):
    # 데이터셋 로드
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"]

    start_idx = (start or 1) - 1
    end_idx = end or len(questions)
    questions = questions[start_idx:end_idx]

    if output_path is None:
        output_path = RESULTS_DIR / "pred.json"
    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"\n{'='*60}")
    print(f"GraphRAG 답변 수집 ({search_type} search)")
    print(f"  문항 수: {len(questions)} ({start_idx+1}~{end_idx})")
    print(f"  출력: {output_path}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] 설정 확인만 실행합니다.")
        print(f"  GRAPHRAG_API_KEY: {'설정됨' if os.getenv('GRAPHRAG_API_KEY') else '없음'}")
        output_dir = GRAPHRAG_ROOT / "output"
        print(f"  인덱스 디렉토리: {'존재' if output_dir.exists() else '없음 - graphrag index 먼저 실행 필요'}")
        return

    # 인덱스 확인
    output_dir = GRAPHRAG_ROOT / "output"
    if not output_dir.exists():
        print("ERROR: graphrag/output/ 없음. 먼저 인덱싱을 실행하세요:")
        print("  source graphrag/.venv/bin/activate")
        print("  graphrag index --root ./graphrag")
        sys.exit(1)

    config = load_index()

    results = []
    errors = 0
    total_start = time.time()

    for i, q in enumerate(tqdm(questions, desc=f"GraphRAG [{search_type}]")):
        t0 = time.time()
        try:
            if search_type == "global":
                answer, contexts, tokens = asyncio.run(run_global_search(q["question"], config))
            else:
                answer, contexts, tokens = asyncio.run(run_local_search(q["question"], config))
            elapsed = time.time() - t0
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected_answer": q.get("expected_answer", ""),
                "generated_answer": answer,
                "reasoning_type": q.get("reasoning_type"),
                "complexity": q.get("complexity"),
                "question_type": q.get("question_type"),
                "retrieved_contexts": contexts,
                "retrieval_time_sec": round(elapsed, 2),
                "prompt_tokens": tokens["prompt_tokens"],
                "completion_tokens": tokens["completion_tokens"],
                "total_tokens": tokens["total_tokens"],
                "search_type": search_type,
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"\n  ERROR [{q['id']}]: {e}")
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected_answer": q.get("expected_answer", ""),
                "generated_answer": f"ERROR: {e}",
                "reasoning_type": q.get("reasoning_type"),
                "complexity": q.get("complexity"),
                "question_type": q.get("question_type"),
                "error": str(e),
                "retrieval_time_sec": round(elapsed, 2),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "search_type": search_type,
            })
            errors += 1

        # 10문항마다 중간 저장
        if (i + 1) % 10 == 0:
            _save(output_path, search_type, results)

    elapsed_total = time.time() - total_start
    _save(output_path, search_type, results)

    print(f"\n{'='*60}")
    print(f"완료: {len(results)}문항, 에러 {errors}건")
    print(f"소요: {elapsed_total:.0f}s ({elapsed_total/60:.1f}min)")
    print(f"저장: {output_path}")


def _save(output_path: Path, search_type: str, results: list):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    valid = [r for r in results if not r.get("error")]
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    avg_time = sum(r.get("retrieval_time_sec", 0) for r in results) / len(results) if results else 0
    output = {
        "method": f"graphrag_{search_type}",
        "model": "gpt-4.1",
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "stats": {
            "total_tokens": total_tokens,
            "avg_tokens_per_question": round(total_tokens / len(results), 1) if results else 0,
            "avg_retrieval_time_sec": round(avg_time, 2),
            "errors": len(results) - len(valid),
        },
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GraphRAG 벤치마크 답변 수집")
    parser.add_argument(
        "--search-type", choices=["local", "global"], default="local",
        help="검색 타입 (기본: local)",
    )
    parser.add_argument("--start", type=int, default=None, help="시작 문항 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 (inclusive)")
    parser.add_argument("--output", type=Path, default=None, help="출력 JSON 경로")
    parser.add_argument("--dry-run", action="store_true", help="설정 확인만")
    args = parser.parse_args()

    collect_answers(
        search_type=args.search_type,
        start=args.start,
        end=args.end,
        output_path=args.output,
        dry_run=args.dry_run,
    )
