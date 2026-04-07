# -*- coding: utf-8 -*-
"""비교 모델 답변 수집기.

벤치마크 데이터셋에 대해 다양한 모델의 답변을 수집하여
llm_judge.py가 소비하는 predictions 포맷으로 저장합니다.

Usage:
    python -m benchmark.run_baseline --method gpt-4o --output benchmark/results/pred_gpt4o.json
    python -m benchmark.run_baseline --method gwm --tree-dir data/trees/ --output benchmark/results/pred_gwm.json
    python -m benchmark.run_baseline --method gpt-4o --start 1 --end 50
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

from tqdm import tqdm

from benchmark.config import ROOT, BENCHMARK_V2_PATH, RESULTS_DIR


# ── Baseline model factories ────────────────────────────────

def make_openai_baseline(model: str) -> Callable[[str], str]:
    """OpenAI API 기반 Vanilla LLM baseline."""
    from openai import OpenAI
    client = OpenAI()

    def answer_fn(question: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "You are a nuclear engineering expert. Answer the question about "
                    "NuScale FSAR (Final Safety Analysis Report) accurately and concisely. "
                    "Provide specific numerical values and technical details when available."
                )},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    return answer_fn


def make_anthropic_baseline(model: str) -> Callable[[str], str]:
    """Anthropic API 기반 Vanilla LLM baseline."""
    from anthropic import Anthropic
    client = Anthropic()

    def answer_fn(question: str) -> str:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0,
            system=(
                "You are a nuclear engineering expert. Answer the question about "
                "NuScale FSAR (Final Safety Analysis Report) accurately and concisely. "
                "Provide specific numerical values and technical details when available."
            ),
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text.strip()

    return answer_fn


def make_pageindex_without_kg_baseline(
    tree_dir: str, max_hops: int = 4, top_k: int = 2
) -> Callable[[str], dict]:
    """PageIndex without KG: retrieval-only baseline.

    Uses the same PageIndex tree + BM25 browse/read/search tools as GWM,
    but with NO DynamicSubKG, NO relation inference, and NO KG-based context.
    Retrieved node texts are concatenated directly as plain context for answer generation.
    """
    import re as _re
    sys.path.insert(0, str(ROOT))
    from openai import OpenAI as _OpenAI
    from src.environment.pageindex_env import PageIndexEnvironment

    client = _OpenAI()
    env = PageIndexEnvironment(model="gpt-4.1")
    tree_files = list(Path(tree_dir).glob("*_structure.json"))
    for tree_file in tree_files:
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        env.register_tree(
            doc_id=data.get("doc_id", tree_file.stem),
            tree=data.get("tree", data.get("structure", [])),
            doc_name=data.get("doc_name", ""),
            pdf_path=data.get("pdf_path", ""),
        )

    _ANSWER_SYSTEM = (
        "You are an expert AI for nuclear regulatory review. "
        "Based on the provided context, answer the user's question. "
        "Answer in 1-2 sentences ONLY. "
        "State the direct answer with specific values, then cite the source. "
        "Do NOT add uncertainty statements, background, or methodology. "
        "Do NOT add information not found in the provided context. "
        "Answer in English."
    )

    _TOOL_SYSTEM = (
        "You are an AI agent exploring regulatory documents to answer a user's question.\n"
        "You navigate documents like a file system using three tools:\n\n"
        "{tool_descriptions}\n\n"
        "Respond ONLY in JSON format:\n"
        '{{\n'
        '    "thinking": "your reasoning about what to do next",\n'
        '    "actions": [\n'
        '        {{"tool": "browse", "doc_id": "...", "node_id": "...or null"}},\n'
        '        {{"tool": "read", "doc_id": "...", "node_id": "..."}},\n'
        '        {{"tool": "search", "keyword": "..."}}\n'
        '    ]\n'
        '}}\n\n'
        "Return 1-3 actions per step."
    )

    def answer_fn(question: str) -> dict:
        doc_ids = list(env.documents.keys())
        retrieved_nodes: dict[str, dict] = {}   # key -> node_data (plain dict)
        already_read: set[str] = set()
        retrieval_start = time.time()

        for hop in range(1, max_hops + 1):

            # Sufficiency check (hop 2+) using plain accumulated context, no KG
            if hop > 1 and retrieved_nodes:
                context_text = "\n\n".join(
                    f"[{n['title']}]\n{n['content'][:600]}"
                    for n in retrieved_nodes.values()
                )
                try:
                    suf_resp = client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {"role": "system", "content": (
                                "You are a document retrieval assistant. "
                                "Judge if the retrieved context is sufficient to fully answer "
                                "the question with specific values and source references. "
                                'Respond ONLY in JSON: {"sufficient": true/false, '
                                '"next_keyword": "keyword or empty string"}'
                            )},
                            {"role": "user", "content": (
                                f"Question: {question}\n\n"
                                f"Retrieved context so far:\n{context_text[:2000]}"
                            )},
                        ],
                        max_tokens=128,
                        temperature=0.1,
                    )
                    suf_raw = suf_resp.choices[0].message.content.strip()
                    suf = json.loads(_re.sub(r"```json\s*|\s*```", "", suf_raw).strip())
                    if suf.get("sufficient"):
                        break
                except Exception:
                    pass

            # Plan tool actions (plain context, no KG)
            context_for_planning = "\n\n".join(
                f"[{n['title']}]\n{n['content'][:400]}"
                for n in retrieved_nodes.values()
            ) if retrieved_nodes else "(none yet)"

            structure_str = ""
            if hop == 1:
                structure_str = "\n\n" + env.get_document_overview(depth=3)

            try:
                tool_resp = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": _TOOL_SYSTEM.format(
                            tool_descriptions=env.get_tool_descriptions()
                        )},
                        {"role": "user", "content": (
                            f"Question: {question}\n\n"
                            f"Already explored nodes: {', '.join(already_read) or '(none)'}\n\n"
                            f"Retrieved context so far:\n{context_for_planning}"
                            f"{structure_str}\n\n"
                            f"What tools should I call next to find the answer?"
                        )},
                    ],
                    max_tokens=512,
                    temperature=0.1,
                )
                tool_raw = tool_resp.choices[0].message.content.strip()
                actions = json.loads(
                    _re.sub(r"```json\s*|\s*```", "", tool_raw).strip()
                ).get("actions", [])
            except Exception:
                actions = [{"tool": "search", "keyword": question.split()[0]}]

            # Execute tools
            nodes_to_read: set[tuple[str, str]] = set()
            for action in actions:
                tool = action.get("tool", "")
                if tool == "search":
                    keyword = action.get("keyword", "")
                    results = env.search(keyword, doc_ids)
                    for r in (results or [])[:top_k]:
                        nodes_to_read.add((r["doc_id"], r["node_id"]))
                elif tool == "read":
                    nodes_to_read.add((action.get("doc_id", ""), action.get("node_id", "")))
                # browse: informational only, no reads queued

            for doc_id, node_id in nodes_to_read:
                key = f"{doc_id}_{node_id}"
                if key in already_read:
                    continue
                already_read.add(key)
                node_data = env.read(doc_id, node_id)
                if node_data and node_data.get("content"):
                    retrieved_nodes[key] = node_data

        retrieval_time = time.time() - retrieval_start

        # Build plain context (no KG, no relation labels, no trajectory)
        context_parts = [
            f"[Source: {n['doc_id']} - {n['title']}]\n{n['content']}"
            for n in retrieved_nodes.values()
        ]
        plain_context = "\n\n---\n\n".join(context_parts)

        # Generate answer from plain context
        gen_start = time.time()
        gen_resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": _ANSWER_SYSTEM},
                {"role": "user", "content": (
                    f"Question: {question}\n\nContext:\n{plain_context}"
                )},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        gen_time = time.time() - gen_start

        return {
            "answer": gen_resp.choices[0].message.content.strip(),
            "retrieved_contexts": [n["content"] for n in retrieved_nodes.values()],
            "n_chunks_retrieved": len(retrieved_nodes),
            "retrieval_time_sec": round(retrieval_time, 2),
            "generation_time_sec": round(gen_time, 2),
        }

    return answer_fn


def make_pageindex_baseline(
    tree_dir: str, max_hops: int = 4, top_k: int = 2
) -> Callable[[str], dict]:
    """PageIndex + KG baseline.

    Identical retrieval path to pageindex_without_kg (same hop loop, same budget).
    After retrieval, builds a DynamicSubKG and runs relation inference.
    Generates the final answer from KG context — no trajectory, no vision,
    no GWMAgent loop, no agentic planning.
    """
    import re as _re
    sys.path.insert(0, str(ROOT))
    from openai import OpenAI as _OpenAI
    from src.environment.pageindex_env import PageIndexEnvironment
    from src.state.knowledge_graph import DynamicSubKG, KGNode, KGEdge
    from src.agent.reasoning import ReasoningModule

    client = _OpenAI()
    env = PageIndexEnvironment(model="gpt-4.1")
    tree_files = list(Path(tree_dir).glob("*_structure.json"))
    for tree_file in tree_files:
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        env.register_tree(
            doc_id=data.get("doc_id", tree_file.stem),
            tree=data.get("tree", data.get("structure", [])),
            doc_name=data.get("doc_name", ""),
            pdf_path=data.get("pdf_path", ""),
        )

    reasoning = ReasoningModule(model="gpt-4.1")

    _TOOL_SYSTEM = (
        "You are an AI agent exploring regulatory documents to answer a user's question.\n"
        "You navigate documents like a file system using three tools:\n\n"
        "{tool_descriptions}\n\n"
        "Respond ONLY in JSON format:\n"
        '{{\n'
        '    "thinking": "your reasoning about what to do next",\n'
        '    "actions": [\n'
        '        {{"tool": "browse", "doc_id": "...", "node_id": "...or null"}},\n'
        '        {{"tool": "read", "doc_id": "...", "node_id": "..."}},\n'
        '        {{"tool": "search", "keyword": "..."}}\n'
        '    ]\n'
        '}}\n\n'
        "Return 1-3 actions per step."
    )

    def answer_fn(question: str) -> dict:
        doc_ids = list(env.documents.keys())
        retrieved_nodes: dict[str, dict] = {}
        already_read: set[str] = set()
        retrieval_start = time.time()

        # ── Retrieval loop (identical to pageindex_without_kg) ──────────
        for hop in range(1, max_hops + 1):

            if hop > 1 and retrieved_nodes:
                context_text = "\n\n".join(
                    f"[{n['title']}]\n{n['content'][:600]}"
                    for n in retrieved_nodes.values()
                )
                try:
                    suf_resp = client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {"role": "system", "content": (
                                "You are a document retrieval assistant. "
                                "Judge if the retrieved context is sufficient to fully answer "
                                "the question with specific values and source references. "
                                'Respond ONLY in JSON: {"sufficient": true/false, '
                                '"next_keyword": "keyword or empty string"}'
                            )},
                            {"role": "user", "content": (
                                f"Question: {question}\n\n"
                                f"Retrieved context so far:\n{context_text[:2000]}"
                            )},
                        ],
                        max_tokens=128,
                        temperature=0.1,
                    )
                    suf_raw = suf_resp.choices[0].message.content.strip()
                    suf = json.loads(_re.sub(r"```json\s*|\s*```", "", suf_raw).strip())
                    if suf.get("sufficient"):
                        break
                except Exception:
                    pass

            context_for_planning = "\n\n".join(
                f"[{n['title']}]\n{n['content'][:400]}"
                for n in retrieved_nodes.values()
            ) if retrieved_nodes else "(none yet)"

            structure_str = ""
            if hop == 1:
                structure_str = "\n\n" + env.get_document_overview(depth=3)

            try:
                tool_resp = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": _TOOL_SYSTEM.format(
                            tool_descriptions=env.get_tool_descriptions()
                        )},
                        {"role": "user", "content": (
                            f"Question: {question}\n\n"
                            f"Already explored nodes: {', '.join(already_read) or '(none)'}\n\n"
                            f"Retrieved context so far:\n{context_for_planning}"
                            f"{structure_str}\n\n"
                            f"What tools should I call next to find the answer?"
                        )},
                    ],
                    max_tokens=512,
                    temperature=0.1,
                )
                tool_raw = tool_resp.choices[0].message.content.strip()
                actions = json.loads(
                    _re.sub(r"```json\s*|\s*```", "", tool_raw).strip()
                ).get("actions", [])
            except Exception:
                actions = [{"tool": "search", "keyword": question.split()[0]}]

            nodes_to_read: set[tuple[str, str]] = set()
            for action in actions:
                tool = action.get("tool", "")
                if tool == "search":
                    keyword = action.get("keyword", "")
                    results = env.search(keyword, doc_ids)
                    for r in (results or [])[:top_k]:
                        nodes_to_read.add((r["doc_id"], r["node_id"]))
                elif tool == "read":
                    nodes_to_read.add((action.get("doc_id", ""), action.get("node_id", "")))

            for doc_id, node_id in nodes_to_read:
                key = f"{doc_id}_{node_id}"
                if key in already_read:
                    continue
                already_read.add(key)
                node_data = env.read(doc_id, node_id)
                if node_data and node_data.get("content"):
                    retrieved_nodes[key] = node_data

        retrieval_time = time.time() - retrieval_start

        # ── KG construction (post-retrieval, all at once) ────────────────
        kg = DynamicSubKG(question=question)
        node_keys = list(retrieved_nodes.keys())

        for key in node_keys:
            n = retrieved_nodes[key]
            summary = reasoning.summarize_node(
                title=n.get("title", key),
                content=n.get("content", ""),
            )
            kg.add_node(KGNode(
                node_id=key,
                title=n.get("title", key),
                content=n.get("content", ""),
                summary=summary,
                source_doc=n.get("doc_id", ""),
                page_range=str(n.get("page_range", "")),
            ))

        for i, key_a in enumerate(node_keys):
            for key_b in node_keys[i + 1:]:
                na = retrieved_nodes[key_a]
                nb = retrieved_nodes[key_b]
                rel = reasoning.infer_relation(
                    node_a_title=na.get("title", key_a),
                    node_a_content=na.get("content", ""),
                    node_b_title=nb.get("title", key_b),
                    node_b_content=nb.get("content", ""),
                    question=question,
                )
                if rel["relation"] != "NONE" and rel["confidence"] >= 0.4:
                    kg.add_edge(KGEdge(
                        source_id=key_a,
                        target_id=key_b,
                        relation=rel["relation"],
                        confidence=rel["confidence"],
                        description=rel.get("description", ""),
                    ))

        # ── Answer from KG context (no trajectory, no vision) ───────────
        gen_start = time.time()
        answer = reasoning.generate_answer(
            question=question,
            kg_context=kg.to_context_string(),
            trajectory=[],
            reference_images=None,
        )
        gen_time = time.time() - gen_start

        return {
            "answer": answer,
            "retrieved_contexts": [n["content"] for n in retrieved_nodes.values()],
            "n_chunks_retrieved": len(retrieved_nodes),
            "n_kg_nodes": len(kg.nodes),
            "n_kg_edges": len(kg.edges),
            "retrieval_time_sec": round(retrieval_time, 2),
            "generation_time_sec": round(gen_time, 2),
        }

    return answer_fn


def make_gwm_baseline(tree_dir: str, max_hops: int = 4, top_k: int = 2) -> Callable[[str], str]:
    """GWM 에이전트 baseline."""
    sys.path.insert(0, str(ROOT))
    from src.environment.pageindex_env import PageIndexEnvironment
    from src.agent.gwm_agent import GWMAgent

    env = PageIndexEnvironment(model="gpt-4.1")
    tree_files = list(Path(tree_dir).glob("*_structure.json"))
    for tree_file in tree_files:
        with open(tree_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        env.register_tree(
            doc_id=data.get("doc_id", tree_file.stem),
            tree=data.get("tree", data.get("structure", [])),
            doc_name=data.get("doc_name", ""),
            pdf_path=data.get("pdf_path", ""),
        )

    doc_id_map = {"Ch.01": "nuscale_ch01", "Ch.05": "nuscale_ch05"}

    def answer_fn(question: str, evidence: list[dict] | None = None) -> str:
        doc_ids = list(env.documents.keys())
        if evidence:
            mapped = set()
            for ev in evidence:
                src = ev.get("source_document", "")
                if src in doc_id_map and doc_id_map[src] in env.documents:
                    mapped.add(doc_id_map[src])
            if mapped:
                doc_ids = list(mapped)

        agent = GWMAgent(
            environment=env, model="gpt-4.1",
            max_hops=max_hops, top_k=top_k,
        )
        result = agent.run(question=question, doc_ids=doc_ids)
        return result["answer"]

    return answer_fn


# ── Model registry ──────────────────────────────────────────

OPENAI_MODELS = {"gpt-4o", "gpt-4-turbo", "gpt-4.1", "gpt-4o-mini"}
ANTHROPIC_MODELS = {"claude-sonnet", "claude-opus"}
ANTHROPIC_MODEL_MAP = {
    "claude-sonnet": "claude-sonnet-4-5-20250929",
    "claude-opus": "claude-opus-4-6-20250610",
}


# ── Main ─────────────────────────────────────────────────────

def collect_answers(
    dataset_path: str,
    method: str,
    output_path: str,
    tree_dir: str | None = None,
    max_hops: int = 4,
    top_k: int = 2,
    start: int | None = None,
    end: int | None = None,
) -> str:
    """답변 수집 실행."""

    # 데이터셋 로드
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions", [])

    # 범위 필터
    if start or end:
        start_idx = (start or 1) - 1
        end_idx = end or len(questions)
        questions = questions[start_idx:end_idx]

    print(f"\n{'='*60}")
    print(f"Baseline 답변 수집: {method}")
    print(f"  데이터셋: {Path(dataset_path).name}")
    print(f"  문항 수: {len(questions)}")
    print(f"{'='*60}\n")

    # 모델 생성
    is_gwm = False
    is_pageindex_without_kg = False
    if method == "gwm":
        if not tree_dir:
            tree_dir = str(ROOT / "data" / "trees")
        answer_fn = make_gwm_baseline(tree_dir, max_hops, top_k)
        is_gwm = True
    elif method == "pageindex":
        if not tree_dir:
            tree_dir = str(ROOT / "data" / "trees")
        answer_fn = make_pageindex_baseline(tree_dir, max_hops, top_k)
        is_pageindex_without_kg = True
    elif method == "pageindex_without_kg":
        if not tree_dir:
            tree_dir = str(ROOT / "data" / "trees")
        answer_fn = make_pageindex_without_kg_baseline(tree_dir, max_hops, top_k)
        is_pageindex_without_kg = True
    elif method in OPENAI_MODELS:
        answer_fn = make_openai_baseline(method)
    elif method in ANTHROPIC_MODELS:
        answer_fn = make_anthropic_baseline(ANTHROPIC_MODEL_MAP[method])
    else:
        raise ValueError(f"지원하지 않는 모델: {method}. "
                         f"지원: gwm, pageindex, pageindex_without_kg, "
                         f"{', '.join(sorted(OPENAI_MODELS | ANTHROPIC_MODELS))}")

    # 답변 수집
    results = []
    errors = 0
    total_start = time.time()

    for i, q in enumerate(tqdm(questions, desc=f"Collecting [{method}]")):
        extra_fields: dict = {}
        try:
            if is_gwm:
                answer = answer_fn(q["question"], q.get("ground_truth_evidence"))
            elif is_pageindex_without_kg:
                result_dict = answer_fn(q["question"])
                answer = result_dict.pop("answer")
                extra_fields = result_dict
            else:
                answer = answer_fn(q["question"])
        except Exception as e:
            print(f"\n  ❌ [{q['id']}] 에러: {e}")
            answer = f"ERROR: {e}"
            extra_fields = {"error": str(e)}
            errors += 1

        results.append({
            "id": q["id"],
            "question": q["question"],
            "reasoning_type": q.get("reasoning_type"),
            "complexity": q.get("complexity"),
            "question_type": q.get("question_type"),
            "generated_answer": answer,
            "expected_answer": q.get("expected_answer", ""),
            **extra_fields,
        })

        # 10문항마다 중간 저장
        if (i + 1) % 10 == 0:
            _save_output(output_path, method, results)

    elapsed = time.time() - total_start

    # 최종 저장
    _save_output(output_path, method, results)

    print(f"\n{'='*60}")
    print(f"완료: {len(results)}문항, 에러 {errors}건")
    print(f"소요: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"저장: {output_path}")
    return output_path


def _save_output(output_path: str, method: str, results: list[dict]):
    os.makedirs(Path(output_path).parent, exist_ok=True)
    output = {
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GWM Benchmark baseline 답변 수집")
    parser.add_argument(
        "--method", "-m", required=True,
        help=(
            f"모델명: gwm, pageindex, pageindex_without_kg, "
            f"{', '.join(sorted(OPENAI_MODELS | ANTHROPIC_MODELS))}"
        ),
    )
    parser.add_argument(
        "--dataset", default=str(BENCHMARK_V2_PATH),
        help="데이터셋 경로",
    )
    parser.add_argument("--output", "-o", required=True, help="출력 JSON 경로")
    parser.add_argument("--tree-dir", default=None, help="GWM 트리 디렉토리 (gwm 전용)")
    parser.add_argument("--max-hops", type=int, default=4, help="GWM max hops")
    parser.add_argument("--top-k", type=int, default=2, help="GWM top-k")
    parser.add_argument("--start", type=int, default=None, help="시작 문항 (1-based)")
    parser.add_argument("--end", type=int, default=None, help="종료 문항 (inclusive)")
    args = parser.parse_args()

    collect_answers(
        dataset_path=args.dataset,
        method=args.method,
        output_path=args.output,
        tree_dir=args.tree_dir,
        max_hops=args.max_hops,
        top_k=args.top_k,
        start=args.start,
        end=args.end,
    )
