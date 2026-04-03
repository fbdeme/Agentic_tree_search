"""
Re-run ablation with full answer + contexts saved, then evaluate with LLM-as-Judge and RAGAS.

Usage:
    source .venv/bin/activate
    PYTHONPATH=pageindex_core:$PYTHONPATH python -u experiments/ablation_evaluate.py
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from functools import wraps

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Token tracking ──────────────────────────────────────────────
_token_log = []

def patch_openai():
    from openai.resources.chat import completions as comp_module
    _orig_create = comp_module.Completions.create

    @wraps(_orig_create)
    def tracked_create(self, *args, **kwargs):
        result = _orig_create(self, *args, **kwargs)
        if hasattr(result, 'usage') and result.usage:
            _token_log.append({
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
            })
        return result
    comp_module.Completions.create = tracked_create

patch_openai()

from src.environment.pageindex_env import PageIndexEnvironment
from experiments.ablation_study import AblationAgent, VARIANTS, SAMPLE_IDS, load_environment

# ── RAGAS ────────────────────────────────────────────────────────
from openai import AsyncOpenAI
from ragas.metrics.collections import (
    Faithfulness, AnswerRelevancy, ContextRecall, FactualCorrectness,
)
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory


def init_ragas():
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    llm = llm_factory("gpt-4.1", client=client, max_tokens=4096)
    emb = embedding_factory("openai", model="text-embedding-3-small", client=client)
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=emb),
        "context_recall": ContextRecall(llm=llm),
        "factual_correctness": FactualCorrectness(llm=llm),
    }


async def ragas_score(question, answer, expected, contexts, metrics):
    scores = {}
    answer = answer[:2000]
    for name, metric in metrics.items():
        try:
            if name == "faithfulness":
                r = await asyncio.wait_for(metric.ascore(
                    user_input=question, response=answer, retrieved_contexts=contexts), 120)
            elif name == "answer_relevancy":
                r = await asyncio.wait_for(metric.ascore(
                    user_input=question, response=answer), 120)
            elif name == "context_recall":
                r = await asyncio.wait_for(metric.ascore(
                    user_input=question, retrieved_contexts=contexts, reference=expected), 120)
            elif name == "factual_correctness":
                r = await asyncio.wait_for(metric.ascore(
                    response=answer, reference=expected), 120)
            scores[name] = round(float(r), 4)
        except Exception as e:
            scores[name] = None
    return scores


# ── LLM-as-Judge (simplified inline) ────────────────────────────
from openai import OpenAI

def judge_single(question, generated, expected, client, model="gpt-4.1"):
    """Single-model judge: score 1-5, >=4 is O."""
    prompt = f"""Evaluate whether the generated answer correctly addresses the question compared to the expected answer.

Question: {question}

Expected Answer: {expected}

Generated Answer: {generated}

Score on a scale of 1-5:
1: Completely wrong or irrelevant
2: Partially relevant but major errors
3: Somewhat correct but missing key information
4: Mostly correct with minor issues
5: Fully correct and comprehensive

Respond with ONLY a JSON: {{"score": <int>, "reasoning": "<brief>"}}"""

    response = client.chat.completions.create(
        model=model, temperature=0, max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    import re
    text = response.choices[0].message.content.strip()
    text = re.sub(r"```json\s*|\s*```", "", text)
    try:
        result = json.loads(text)
        return result.get("score", 0)
    except:
        return 0


def extract_contexts_from_kg(kg):
    """Same as evaluate.py: KG context + node contents."""
    contexts = [kg.to_context_string()]
    for nid, node in kg.nodes.items():
        if node.content and node.content != node.summary:
            contexts.append(f"[{node.title}] {node.content}")
    return contexts


# ── Main ─────────────────────────────────────────────────────────

async def main():
    env = load_environment()
    print(f"Environment: {env.doc_count} docs, {env.node_count} nodes\n")

    with open(ROOT / "data/qa_dataset/multihop_qa_benchmark_v2.json") as f:
        all_questions = json.load(f)["questions"]
    qa_map = {q["id"]: q for q in all_questions}
    sample = [qa_map[qid] for qid in SAMPLE_IDS if qid in qa_map]

    print("Initializing RAGAS metrics...")
    ragas_metrics = init_ragas()
    judge_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("Ready.\n")

    all_results = {}

    for variant_name, config in VARIANTS.items():
        print(f"\n{'='*60}")
        print(f"VARIANT: {variant_name} {config}")
        print(f"{'='*60}\n")

        variant_results = []

        for q in sample:
            qid = q["id"]
            _token_log.clear()

            agent = AblationAgent(
                environment=env, model="gpt-4.1", max_hops=4, top_k=2, **config)
            doc_ids = list(env.documents.keys())

            start = time.time()
            try:
                result = agent.run(question=q["question"], doc_ids=doc_ids)
                elapsed = time.time() - start
                answer = result["answer"]
                kg = result["kg"]
                hops = result["hops_used"]
                contexts = extract_contexts_from_kg(kg)
            except Exception as e:
                elapsed = time.time() - start
                answer = f"ERROR: {e}"
                kg = None
                hops = 0
                contexts = []

            total_tokens = sum(t["total_tokens"] for t in _token_log)
            cost = (sum(t["prompt_tokens"] for t in _token_log) * 2 +
                    sum(t["completion_tokens"] for t in _token_log) * 8) / 1_000_000

            # LLM-as-Judge (single model for speed)
            judge_score = judge_single(q["question"], answer, q["expected_answer"], judge_client)
            judge_vote = "O" if judge_score >= 4 else "X"

            # RAGAS
            ragas = await ragas_score(
                q["question"], answer, q["expected_answer"], contexts, ragas_metrics)

            entry = {
                "id": qid,
                "variant": variant_name,
                "question_type": q["question_type"],
                "reasoning_type": q["reasoning_type"],
                "complexity": q["complexity"],
                "time_sec": round(elapsed, 1),
                "hops_used": hops,
                "kg_nodes": len(kg.nodes) if kg else 0,
                "kg_edges": len(kg.edges) if kg else 0,
                "total_tokens": total_tokens,
                "cost_usd": round(cost, 4),
                "judge_score": judge_score,
                "judge_vote": judge_vote,
                "faithfulness": ragas.get("faithfulness"),
                "answer_relevancy": ragas.get("answer_relevancy"),
                "context_recall": ragas.get("context_recall"),
                "factual_correctness": ragas.get("factual_correctness"),
                "answer": answer,
                "n_contexts": len(contexts),
            }
            variant_results.append(entry)

            f_s = f"{ragas.get('faithfulness', 0):.2f}" if ragas.get('faithfulness') is not None else "N/A"
            cr_s = f"{ragas.get('context_recall', 0):.2f}" if ragas.get('context_recall') is not None else "N/A"
            print(f"  [{qid}] Judge={judge_vote}({judge_score}) Faith={f_s} CR={cr_s} "
                  f"| {elapsed:.0f}s {hops}hops {len(kg.nodes) if kg else 0}n {len(kg.edges) if kg else 0}e ${cost:.3f}")

        all_results[variant_name] = variant_results

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print("ABLATION EVALUATION SUMMARY")
    print(f"{'='*60}\n")

    def safe_avg(items, key):
        vals = [r[key] for r in items if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    header = f"{'Variant':<18} {'Judge':>6} {'Faith':>6} {'AR':>6} {'CR':>6} {'FC':>6} {'Time':>6} {'Cost':>7}"
    print(header)
    print("-" * len(header))

    for vname, results in all_results.items():
        correct = sum(1 for r in results if r["judge_vote"] == "O")
        n = len(results)
        faith = safe_avg(results, "faithfulness")
        ar = safe_avg(results, "answer_relevancy")
        cr = safe_avg(results, "context_recall")
        fc = safe_avg(results, "factual_correctness")
        avg_time = sum(r["time_sec"] for r in results) / n
        avg_cost = sum(r["cost_usd"] for r in results) / n

        def fmt(v): return f"{v:.3f}" if v is not None else "N/A"

        print(f"{vname:<18} {correct}/{n}   {fmt(faith)} {fmt(ar)} {fmt(cr)} {fmt(fc)} {avg_time:>5.0f}s ${avg_cost:.3f}")

    # Save
    out_path = ROOT / "experiments/results/ablation_evaluated.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
