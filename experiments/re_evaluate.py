"""
Re-evaluate existing agent answers with updated RAGAs metrics.
Loads saved KG JSONs + agent answers from previous eval reports,
runs only the RAGAs evaluation step (no agent execution).

Usage:
    PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/re_evaluate.py \
        --eval-dir experiments/results/eval \
        --dataset data/qa_dataset/multihop_qa_benchmark_v2.json \
        --reports eval_ragas_20260324_104413.json eval_ragas_20260324_105021.json ...
"""

import sys
import os
import json
import asyncio
import argparse
import glob
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.state.knowledge_graph import DynamicSubKG, KGNode, KGEdge

# RAGAs imports
from openai import AsyncOpenAI
from ragas.metrics.collections import (
    Faithfulness, AnswerRelevancy, ContextRecall, FactualCorrectness,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory


def init_ragas_metrics():
    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    evaluator_llm = llm_factory("gpt-4.1", client=async_client, max_tokens=4096)
    evaluator_embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=async_client
    )
    return {
        "faithfulness": Faithfulness(llm=evaluator_llm),
        "answer_relevancy": AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        "context_recall": ContextRecall(llm=evaluator_llm),
        "factual_correctness": FactualCorrectness(llm=evaluator_llm),
    }


def rebuild_contexts_from_kg(kg_path: str) -> list[str]:
    """Rebuild full KG context string from saved KG JSON — same as agent saw."""
    with open(kg_path) as f:
        kg_data = json.load(f)

    # Rebuild to_context_string() equivalent
    lines = [f"=== Knowledge Graph ===\n"]
    lines.append(f"[Query] {kg_data.get('question', '')}\n")
    nodes = kg_data.get("nodes", {})
    edges = kg_data.get("edges", [])
    lines.append(f"[Nodes] {len(nodes)}  [Edges] {len(edges)}\n")

    lines.append("\n--- Node List ---")
    for nid, node in nodes.items():
        summary = node.get("summary", "")
        if summary:
            lines.append(
                f"\n[{nid}] ({node.get('modality','text')}, Hop {node.get('hop',0)}) {node.get('title','')}\n"
                f"  Source: {node.get('source_doc','')} p.{node.get('page_range','')}\n"
                f"  Summary: {summary}"
            )

    lines.append("\n\n--- Relationship (Edge) List ---")
    for e in edges:
        desc = e.get("description", e.get("reasoning", ""))
        lines.append(
            f"  [{e['source']}] --[{e.get('relation','')}]--> [{e['target']}]"
            f"  (confidence: {e.get('confidence',0):.2f})"
            + (f"\n    {desc}" if desc else "")
        )

    return ["\n".join(lines)]


async def evaluate_single(qid, question, expected_answer, agent_answer,
                          contexts, metrics):
    answer_for_eval = agent_answer[:2000]
    scores = {}

    # Faithfulness
    try:
        result = await asyncio.wait_for(
            metrics["faithfulness"].ascore(
                user_input=question, response=answer_for_eval,
                retrieved_contexts=contexts,
            ), timeout=120)
        scores["faithfulness"] = round(float(result), 4)
    except:
        scores["faithfulness"] = None

    # Answer Relevancy
    try:
        result = await asyncio.wait_for(
            metrics["answer_relevancy"].ascore(
                user_input=question, response=answer_for_eval,
            ), timeout=120)
        scores["answer_relevancy"] = round(float(result), 4)
    except:
        scores["answer_relevancy"] = None

    # Context Recall
    try:
        result = await asyncio.wait_for(
            metrics["context_recall"].ascore(
                user_input=question, retrieved_contexts=contexts,
                reference=expected_answer,
            ), timeout=120)
        scores["context_recall"] = round(float(result), 4)
    except:
        scores["context_recall"] = None

    # Factual Correctness
    try:
        result = await asyncio.wait_for(
            metrics["factual_correctness"].ascore(
                response=answer_for_eval, reference=expected_answer,
            ), timeout=120)
        scores["factual_correctness"] = round(float(result), 4)
    except:
        scores["factual_correctness"] = None

    return scores


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", default=str(ROOT / "experiments/results/eval"))
    parser.add_argument("--dataset", default=str(ROOT / "data/qa_dataset/multihop_qa_benchmark_v2.json"))
    parser.add_argument("--reports", nargs="+", required=True)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    # Load previous results
    all_prev = []
    for report_name in args.reports:
        path = os.path.join(args.eval_dir, report_name)
        with open(path) as f:
            data = json.load(f)
        all_prev.extend(data["results"])
    print(f"Loaded {len(all_prev)} previous results")

    # Filter
    if args.start or args.end:
        start = (args.start or 1) - 1
        end = args.end or len(all_prev)
        all_prev = all_prev[start:end]
        print(f"Filtered to {len(all_prev)} results")

    # Load dataset for expected answers
    with open(args.dataset) as f:
        qa = json.load(f)
    qa_map = {q["id"]: q for q in qa["questions"]}

    # Init RAGAs
    print("Initializing RAGAs metrics...")
    metrics = init_ragas_metrics()

    results = []
    for i, prev in enumerate(all_prev):
        qid = prev["id"]
        if "error" in prev:
            results.append(prev)
            continue

        q = qa_map.get(qid, {})
        question = prev.get("question", q.get("question", ""))
        expected = prev.get("expected_answer", q.get("expected_answer", ""))
        agent_answer = prev.get("agent_answer", "")

        # Load KG and rebuild contexts
        kg_path = os.path.join(args.eval_dir, f"kg_{qid}.json")
        if os.path.exists(kg_path):
            contexts = rebuild_contexts_from_kg(kg_path)
        else:
            contexts = ["(no context available)"]

        print(f"[{i+1}/{len(all_prev)}] {qid}: {len(contexts)} contexts, {len(agent_answer)} chars answer")

        scores = await evaluate_single(qid, question, expected, agent_answer, contexts, metrics)

        entry = {**prev, **scores}
        results.append(entry)

        f_s = f"{scores['faithfulness']:.2f}" if scores['faithfulness'] is not None else "N/A"
        print(f"  Faith={f_s} AR={scores.get('answer_relevancy','N/A')} "
              f"CR={scores.get('context_recall','N/A')} FC={scores.get('factual_correctness','N/A')}")

    # Save
    report_path = os.path.join(args.eval_dir,
                               f"reeval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    report = {
        "timestamp": datetime.now().isoformat(),
        "note": "Re-evaluation with node-level contexts (no edges)",
        "total": len(results),
        "results": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
