"""
Measure GWM agent token usage on a small sample (5 questions).
Monkey-patches OpenAI client to intercept usage stats.

Usage:
    source .venv/bin/activate
    PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/measure_token_usage.py
"""

import sys
import os
import json
import time
from pathlib import Path
from functools import wraps

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Token tracking via monkey-patch ─────────────────────────────

_token_log = []

def patch_openai_for_tracking():
    """Monkey-patch openai.resources.chat.completions.Completions.create to log usage."""
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

patch_openai_for_tracking()

from src.environment.pageindex_env import PageIndexEnvironment
from src.agent.gwm_agent import GWMAgent


def load_environment(tree_dir: Path) -> PageIndexEnvironment:
    env = PageIndexEnvironment(model="gpt-4.1")
    for tree_file in tree_dir.glob("*_structure.json"):
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc_id = data.get("doc_id", tree_file.stem)
        doc_name = data.get("doc_name", doc_id)
        tree = data.get("tree", data.get("structure", []))
        pdf_path = data.get("pdf_path", "")
        env.register_tree(doc_id=doc_id, tree=tree, doc_name=doc_name, pdf_path=pdf_path)
    return env


def main():
    # Load environment
    tree_dir = ROOT / "data/trees"
    env = load_environment(tree_dir)
    print(f"Environment: {env.doc_count} docs, {env.node_count} nodes\n")

    # Load dataset - sample 5 questions (diverse types)
    dataset_path = ROOT / "data/qa_dataset/multihop_qa_benchmark_v2.json"
    with open(dataset_path) as f:
        questions = json.load(f)["questions"]

    # Pick 5 diverse questions: 1 factual, 1 comparative, 1 judgment, 1 table, 1 composite
    sample_ids = ["Q001", "Q071", "Q131", "Q161", "Q191"]
    sample = [q for q in questions if q["id"] in sample_ids]
    if len(sample) < 5:
        sample = questions[:5]

    print(f"Sample: {[q['id'] for q in sample]}\n")

    results = []
    for q in sample:
        qid = q["id"]
        _token_log.clear()

        agent = GWMAgent(environment=env, model="gpt-4.1", max_hops=4, top_k=2)

        doc_ids = list(env.documents.keys())
        start = time.time()
        result = agent.run(question=q["question"], doc_ids=doc_ids)
        elapsed = time.time() - start

        total_prompt = sum(t["prompt_tokens"] for t in _token_log)
        total_completion = sum(t["completion_tokens"] for t in _token_log)
        total_tokens = sum(t["total_tokens"] for t in _token_log)
        n_calls = len(_token_log)

        # GPT-4.1 pricing: $2/M input, $8/M output
        cost = (total_prompt * 2 + total_completion * 8) / 1_000_000

        entry = {
            "id": qid,
            "question_type": q["question_type"],
            "reasoning_type": q["reasoning_type"],
            "complexity": q["complexity"],
            "time_sec": round(elapsed, 1),
            "hops_used": result["hops_used"],
            "kg_nodes": len(result["kg"].nodes),
            "kg_edges": len(result["kg"].edges),
            "api_calls": n_calls,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(cost, 4),
        }
        results.append(entry)

        print(f"[{qid}] {q['question_type']}/{q['reasoning_type']}")
        print(f"  time={elapsed:.1f}s  hops={result['hops_used']}  "
              f"nodes={len(result['kg'].nodes)}  edges={len(result['kg'].edges)}")
        print(f"  API calls={n_calls}  tokens={total_tokens:,} "
              f"(prompt={total_prompt:,} + completion={total_completion:,})")
        print(f"  estimated cost=${cost:.4f}")
        print()

    # Summary
    print("=" * 60)
    print(f"SUMMARY ({len(results)} questions)")
    print("=" * 60)
    avg_tokens = sum(r["total_tokens"] for r in results) / len(results)
    avg_cost = sum(r["estimated_cost_usd"] for r in results) / len(results)
    avg_time = sum(r["time_sec"] for r in results) / len(results)
    avg_calls = sum(r["api_calls"] for r in results) / len(results)
    total_cost_200 = avg_cost * 200

    print(f"  Avg tokens/question: {avg_tokens:,.0f}")
    print(f"  Avg API calls/question: {avg_calls:.1f}")
    print(f"  Avg cost/question: ${avg_cost:.4f}")
    print(f"  Avg time/question: {avg_time:.1f}s")
    print(f"  Estimated 200Q total cost: ${total_cost_200:.2f}")
    print(f"  Estimated 200Q total time: {avg_time * 200 / 60:.0f} min")

    # Save
    out_path = ROOT / "experiments/results/token_usage_sample.json"
    with open(out_path, "w") as f:
        json.dump({"results": results, "summary": {
            "n_questions": len(results),
            "avg_tokens_per_question": round(avg_tokens),
            "avg_api_calls_per_question": round(avg_calls, 1),
            "avg_cost_per_question_usd": round(avg_cost, 4),
            "avg_time_per_question_sec": round(avg_time, 1),
            "estimated_200q_total_cost_usd": round(total_cost_200, 2),
            "gpt41_pricing": {"input_per_1M": 2, "output_per_1M": 8},
        }}, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
