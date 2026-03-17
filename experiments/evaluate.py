"""
QA 벤치마크 기반 GWM 에이전트 성능 평가 스크립트.

연구 계획서 Section 3.2에 따른 RAGAs 프레임워크 기반 평가:
  1. Faithfulness: 답변의 각 claim이 검색된 context에 근거하는 비율 (환각 검출)
  2. Answer Relevancy: 답변이 질문 의도에 부합하는 정도
  3. Context Recall: expected_answer의 각 문장이 검색된 context에 뒷받침되는 비율
  4. Factual Correctness: expected_answer 대비 답변의 사실적 정확도
  + Keyword Hit Rate: 정답 키워드 포함 비율 (보조 지표)

사용법:
    cd /Users/jeonmingyu/workspace_2026/Agentic_tree_search
    source .venv/bin/activate

    # 전체 100문항 평가
    python experiments/evaluate.py

    # 특정 타입만 평가
    python experiments/evaluate.py --question-type text_only

    # 특정 문항 범위만 평가
    python experiments/evaluate.py --start 1 --end 10

    # dry-run (API 호출 없이 설정 확인)
    python experiments/evaluate.py --dry-run
"""

import sys
import os
import json
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.gwm_agent import GWMAgent
from src.utils.visualize import save_kg_json

# RAGAs imports
from openai import AsyncOpenAI
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
    FactualCorrectness,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory


# ── RAGAs 평가기 초기화 ──────────────────────────────────────────

def init_ragas_metrics():
    """RAGAs 메트릭 인스턴스들을 초기화 (AsyncOpenAI 클라이언트 필요)"""
    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    evaluator_llm = llm_factory("gpt-4.1", client=async_client)
    evaluator_embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=async_client
    )

    faithfulness = Faithfulness(llm=evaluator_llm)
    answer_relevancy = AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings)
    context_recall = ContextRecall(llm=evaluator_llm)
    factual_correctness = FactualCorrectness(llm=evaluator_llm)

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_recall": context_recall,
        "factual_correctness": factual_correctness,
    }


async def evaluate_with_ragas(
    question: str,
    agent_answer: str,
    expected_answer: str,
    retrieved_contexts: list[str],
    metrics: dict,
) -> dict:
    """
    RAGAs 메트릭으로 단일 문항 평가.
    각 메트릭마다 요구하는 인자가 다르므로 개별 호출.

    Signatures (ragas v0.4):
        Faithfulness.ascore(user_input, response, retrieved_contexts)
        AnswerRelevancy.ascore(user_input, response, retrieved_contexts)
        ContextRecall.ascore(user_input, retrieved_contexts, reference)
        FactualCorrectness.ascore(response, reference)
    """
    scores = {}

    # Faithfulness: claim이 context에 근거하는 비율
    try:
        result = await asyncio.wait_for(
            metrics["faithfulness"].ascore(
                user_input=question,
                response=agent_answer,
                retrieved_contexts=retrieved_contexts,
            ),
            timeout=120,
        )
        scores["faithfulness"] = round(float(result), 4)
    except asyncio.TimeoutError:
        scores["faithfulness"] = None
        print(f"     ⚠️ RAGAs faithfulness 타임아웃 (120s)")
    except Exception as e:
        scores["faithfulness"] = None
        err_str = str(e)[:80]
        print(f"     ⚠️ RAGAs faithfulness 에러: {err_str}")

    # Answer Relevancy: 답변이 질문 의도에 부합하는 정도
    try:
        result = await asyncio.wait_for(
            metrics["answer_relevancy"].ascore(
                user_input=question,
                response=agent_answer,
            ),
            timeout=120,
        )
        scores["answer_relevancy"] = round(float(result), 4)
    except (asyncio.TimeoutError, Exception) as e:
        scores["answer_relevancy"] = None
        print(f"     ⚠️ RAGAs answer_relevancy 에러: {str(e)[:80]}")

    # Context Recall: expected_answer 문장이 context에 뒷받침되는 비율
    try:
        result = await asyncio.wait_for(
            metrics["context_recall"].ascore(
                user_input=question,
                retrieved_contexts=retrieved_contexts,
                reference=expected_answer,
            ),
            timeout=120,
        )
        scores["context_recall"] = round(float(result), 4)
    except (asyncio.TimeoutError, Exception) as e:
        scores["context_recall"] = None
        print(f"     ⚠️ RAGAs context_recall 에러: {str(e)[:80]}")

    # Factual Correctness: expected_answer 대비 사실 정확도
    try:
        result = await asyncio.wait_for(
            metrics["factual_correctness"].ascore(
                response=agent_answer,
                reference=expected_answer,
            ),
            timeout=120,
        )
        scores["factual_correctness"] = round(float(result), 4)
    except (asyncio.TimeoutError, Exception) as e:
        scores["factual_correctness"] = None
        print(f"     ⚠️ RAGAs factual_correctness 에러: {str(e)[:80]}")

    return scores


# ── 보조 메트릭 ──────────────────────────────────────────────────

def keyword_hit_rate(answer: str, keywords: list[str]) -> float:
    """정답 키워드가 에이전트 답변에 포함된 비율"""
    if not keywords:
        return 0.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / len(keywords)


# ── 메인 평가 루프 ───────────────────────────────────────────────

def load_environment(tree_dir: Path) -> PageIndexEnvironment:
    """트리 JSON들을 로드하여 환경 구성"""
    env = PageIndexEnvironment(model="gpt-4.1")

    tree_files = list(tree_dir.glob("*_structure.json"))
    if not tree_files:
        raise FileNotFoundError(
            f"트리 파일이 없습니다: {tree_dir}\n"
            f"먼저 python experiments/build_trees.py를 실행하세요."
        )

    for tree_file in tree_files:
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc_id = data.get("doc_id", tree_file.stem)
        doc_name = data.get("doc_name", doc_id)
        tree = data.get("tree", data.get("structure", []))

        pdf_path = data.get("pdf_path", "")
        env.register_tree(doc_id=doc_id, tree=tree, doc_name=doc_name, pdf_path=pdf_path)

    return env


def load_qa_dataset(dataset_path: Path) -> list[dict]:
    """QA 데이터셋 로드"""
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]


def map_doc_ids(evidence_list: list[dict], env: PageIndexEnvironment) -> list[str]:
    """ground_truth_evidence의 source_document를 환경의 doc_id로 매핑"""
    doc_id_map = {
        "Ch.01": "nuscale_ch01",
        "Ch.05": "nuscale_ch05",
    }
    doc_ids = set()
    for ev in evidence_list:
        src = ev.get("source_document", "")
        mapped = doc_id_map.get(src, "")
        if mapped and mapped in env.documents:
            doc_ids.add(mapped)

    return list(doc_ids) if doc_ids else list(env.documents.keys())


def extract_contexts_from_kg(kg, max_chars_per_node: int = 800, max_nodes: int = 6) -> list[str]:
    """KG 노드들의 content를 context 리스트로 추출 (토큰 초과 방지를 위해 길이/개수 제한)"""
    contexts = []
    for nid, node in list(kg.nodes.items())[:max_nodes]:
        text = node.content or node.summary
        if text:
            truncated = text[:max_chars_per_node]
            contexts.append(f"[{node.title}] {truncated}")
    return contexts


async def run_evaluation_async(args):
    """메인 평가 실행 (async)"""
    print(f"\n{'='*70}")
    print(f"🔬 GWM 에이전트 성능 평가 (RAGAs 프레임워크)")
    print(f"   트리 디렉토리: {args.tree_dir}")
    print(f"   QA 데이터셋: {args.dataset}")
    print(f"   Max hops: {args.max_hops}  |  Top-K: {args.top_k}")
    print(f"{'='*70}\n")

    # 환경 로드
    env = load_environment(Path(args.tree_dir))
    print(f"✅ 환경 로드 완료: {env.doc_count}개 문서, {env.node_count}개 노드\n")

    # QA 데이터셋 로드
    questions = load_qa_dataset(Path(args.dataset))
    print(f"✅ QA 데이터셋 로드: {len(questions)}개 문항\n")

    # 필터링
    if args.question_type:
        questions = [q for q in questions if q["question_type"] == args.question_type]
        print(f"   필터: {args.question_type} → {len(questions)}개 문항")
    if args.start or args.end:
        start_idx = (args.start or 1) - 1
        end_idx = args.end or len(questions)
        questions = questions[start_idx:end_idx]
        print(f"   범위: Q{start_idx+1}~Q{end_idx} → {len(questions)}개 문항")

    if args.dry_run:
        print(f"\n🏁 Dry-run 완료. {len(questions)}개 문항 평가 예정.")
        return

    # RAGAs 메트릭 초기화
    print("📐 RAGAs 메트릭 초기화 중...")
    ragas_metrics = init_ragas_metrics()
    print(f"   메트릭: {', '.join(ragas_metrics.keys())}\n")

    # 결과 저장
    results = []
    metrics_by_type = {}

    results_dir = ROOT / "experiments/results/eval"
    os.makedirs(results_dir, exist_ok=True)

    total_start = time.time()

    for i, q in enumerate(questions):
        qid = q["id"]
        qtype = q["question_type"]
        print(f"\n{'─'*60}")
        print(f"[{i+1}/{len(questions)}] {qid} ({qtype})")
        print(f"  Q: {q['question'][:80]}...")

        # 관련 문서 매핑
        doc_ids = map_doc_ids(q.get("ground_truth_evidence", []), env)

        # 에이전트 실행
        agent = GWMAgent(
            environment=env,
            model="gpt-4.1",
            max_hops=args.max_hops,
            top_k=args.top_k,
        )

        q_start = time.time()
        try:
            result = agent.run(question=q["question"], doc_ids=doc_ids)
            answer = result["answer"]
            kg = result["kg"]
            trajectory = result["trajectory"]
            agent_elapsed = time.time() - q_start
        except Exception as e:
            print(f"  ❌ 에이전트 에러: {e}")
            results.append({
                "id": qid, "type": qtype, "error": str(e),
                "keyword_hit": 0,
                "faithfulness": None, "answer_relevancy": None,
                "context_recall": None, "factual_correctness": None,
            })
            continue

        # KG에서 context 추출
        retrieved_contexts = extract_contexts_from_kg(kg)

        # RAGAs 평가 (답변이 너무 길면 claim 추출에서 토큰 초과 → 2000자로 제한)
        answer_for_eval = answer[:2000] if len(answer) > 2000 else answer

        eval_start = time.time()
        ragas_scores = await evaluate_with_ragas(
            question=q["question"],
            agent_answer=answer_for_eval,
            expected_answer=q["expected_answer"],
            retrieved_contexts=retrieved_contexts,
            metrics=ragas_metrics,
        )
        eval_elapsed = time.time() - eval_start

        # 보조 메트릭
        kw_hit = keyword_hit_rate(answer, q.get("answer_keywords", []))

        total_elapsed_q = time.time() - q_start

        # 결과 기록
        entry = {
            "id": qid,
            "type": qtype,
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "agent_answer": answer,
            # RAGAs 메트릭 (0~1 스케일)
            "faithfulness": ragas_scores.get("faithfulness"),
            "answer_relevancy": ragas_scores.get("answer_relevancy"),
            "context_recall": ragas_scores.get("context_recall"),
            "factual_correctness": ragas_scores.get("factual_correctness"),
            # 보조 메트릭
            "keyword_hit": round(kw_hit, 3),
            # KG 정보
            "kg_nodes": len(kg.nodes),
            "kg_edges": len(kg.edges),
            "hops_used": result["hops_used"],
            "retrieved_contexts_count": len(retrieved_contexts),
            # 시간
            "agent_sec": round(agent_elapsed, 1),
            "eval_sec": round(eval_elapsed, 1),
            "total_sec": round(total_elapsed_q, 1),
            "trajectory": trajectory,
        }
        results.append(entry)

        # 타입별 집계
        if qtype not in metrics_by_type:
            metrics_by_type[qtype] = []
        metrics_by_type[qtype].append(entry)

        # 결과 출력
        f_score = ragas_scores.get("faithfulness")
        r_score = ragas_scores.get("answer_relevancy")
        cr_score = ragas_scores.get("context_recall")
        fc_score = ragas_scores.get("factual_correctness")

        def fmt(v):
            return f"{v:.2f}" if v is not None else "N/A"

        print(f"  ✅ KW Hit: {kw_hit:.1%}  |  KG: {len(kg.nodes)}nodes, {len(kg.edges)}edges")
        print(f"     Faith: {fmt(f_score)}  AnswerRel: {fmt(r_score)}  "
              f"CtxRecall: {fmt(cr_score)}  FactCorr: {fmt(fc_score)}")
        print(f"     Agent: {agent_elapsed:.1f}s  Eval: {eval_elapsed:.1f}s")

        # KG 저장
        kg_path = results_dir / f"kg_{qid}.json"
        save_kg_json(kg, str(kg_path))

    total_elapsed = time.time() - total_start

    # ── 종합 리포트 ──────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print(f"📊 RAGAs 평가 결과 종합 리포트")
    print(f"{'='*70}")

    valid = [r for r in results if "error" not in r]
    metric_names = ["faithfulness", "answer_relevancy", "context_recall", "factual_correctness", "keyword_hit"]

    def safe_avg(entries, key):
        vals = [e[key] for e in entries if e.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    if valid:
        print(f"\n📈 전체 평균 ({len(valid)}문항, 에러 {len(results)-len(valid)}건 제외)")
        summary = {}
        for m in metric_names:
            avg = safe_avg(valid, m)
            summary[m] = round(avg, 4) if avg is not None else None
            label = m.replace("_", " ").title()
            if avg is not None:
                print(f"   {label:<25} {avg:.4f}")
            else:
                print(f"   {label:<25} N/A")

        print(f"\n📊 타입별 성능:")
        header = f"   {'Type':<15} {'N':>3}"
        for m in metric_names:
            short = m[:8]
            header += f" {short:>8}"
        print(header)
        print(f"   {'─'*75}")

        by_type_summary = {}
        for qtype, entries in sorted(metrics_by_type.items()):
            row = f"   {qtype:<15} {len(entries):>3}"
            type_summary = {"count": len(entries)}
            for m in metric_names:
                avg = safe_avg(entries, m)
                type_summary[m] = round(avg, 4) if avg is not None else None
                row += f" {avg:>8.4f}" if avg is not None else f" {'N/A':>8}"
            by_type_summary[qtype] = type_summary
            print(row)
    else:
        summary = {m: None for m in metric_names}
        by_type_summary = {}

    print(f"\n⏱️  총 소요 시간: {total_elapsed:.0f}초 ({total_elapsed/60:.1f}분)")

    # 결과 저장
    report = {
        "timestamp": datetime.now().isoformat(),
        "evaluation_framework": "RAGAs v0.4",
        "config": {
            "model": "gpt-4.1",
            "evaluator_model": "gpt-4.1",
            "embedding_model": "text-embedding-3-small",
            "max_hops": args.max_hops,
            "top_k": args.top_k,
            "question_type_filter": args.question_type,
            "total_questions": len(results),
            "errors": len(results) - len(valid),
        },
        "metrics_description": {
            "faithfulness": "Fraction of claims in the answer that are supported by the retrieved context (0-1)",
            "answer_relevancy": "How relevant the answer is to the question, measured by reverse question generation (0-1)",
            "context_recall": "Fraction of expected answer sentences supported by retrieved context (0-1)",
            "factual_correctness": "Factual overlap between agent answer and expected answer (0-1)",
            "keyword_hit": "Fraction of expected keywords present in the agent answer (0-1)",
        },
        "summary": summary,
        "by_type": by_type_summary,
        "results": results,
    }

    report_path = results_dir / f"eval_ragas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 리포트 저장: {report_path}")
    print(f"✅ 평가 완료!")


def run_evaluation(args):
    """sync wrapper"""
    asyncio.run(run_evaluation_async(args))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GWM 에이전트 QA 벤치마크 평가 (RAGAs)")
    parser.add_argument(
        "--tree-dir", default=str(ROOT / "data/trees"),
        help="PageIndex 트리 JSON 디렉토리 (default: data/trees/)"
    )
    parser.add_argument(
        "--dataset", default=str(ROOT / "data/qa_dataset/nuclear_qa_dataset_en.json"),
        help="QA 데이터셋 경로"
    )
    parser.add_argument("--max-hops", type=int, default=4, help="최대 홉 수 (default: 4)")
    parser.add_argument("--top-k", type=int, default=2, help="홉당 검색 노드 수 (default: 2)")
    parser.add_argument("--question-type", type=str, default=None,
                        choices=["text_only", "table_only", "image_only", "composite"],
                        help="특정 문항 타입만 평가")
    parser.add_argument("--start", type=int, default=None, help="시작 문항 번호 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 번호 (inclusive)")
    parser.add_argument("--dry-run", action="store_true", help="설정 확인만 (API 호출 없음)")

    run_evaluation(parser.parse_args())
