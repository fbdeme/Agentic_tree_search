# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GWM (Graph World Model) based multimodal regulatory document exploration agent. Combines GPT-4.1 reasoning with PageIndex tree indexing to build dynamic knowledge graphs from NuScale FSAR documents. Uses a State-Action-Transition loop with dynamic termination and Vision-augmented answer generation.

## Commands

```bash
source .venv/bin/activate

# Build PageIndex trees from actual FSAR PDFs (includes Figure/Table metadata)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/build_trees.py

# Run evaluation (RAGAs framework)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py                    # full 100 questions
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py --start 1 --end 5  # subset
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py --question-type composite
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py --dry-run           # config check only

# Run predefined experiments (simulated tree)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/run_experiment.py
```

**Note**: `PYTHONPATH=pageindex_core:$PYTHONPATH` is required for PageIndex imports.

**Environment**: Requires `OPENAI_API_KEY` in `.env` file.

## Project Structure

```
Agentic_tree_search/
├── src/
│   ├── agent/
│   │   ├── gwm_agent.py              # GWM State-Action-Transition loop + dynamic termination
│   │   └── reasoning.py              # GPT-4.1 reasoning (plan, infer, summarize, generate)
│   ├── environment/
│   │   └── pageindex_env.py           # PageIndex tree environment (search, references)
│   ├── state/
│   │   └── knowledge_graph.py         # DynamicSubKG (NetworkX DiGraph, KGNode, KGEdge)
│   └── utils/
│       ├── visualize.py               # KG visualization (matplotlib)
│       └── vision.py                  # PDF page rendering for VLM (PyMuPDF → JPEG → base64)
│
├── experiments/
│   ├── build_trees.py                 # PDF → PageIndex tree + Figure/Table metadata
│   ├── evaluate.py                    # RAGAs evaluation framework (async)
│   ├── run_experiment.py              # Predefined experiments (simulated tree)
│   ├── sample_fsar_tree.json          # Simulated FSAR tree
│   └── results/                       # Output (PNG, JSON, eval reports)
│       └── eval/                      # RAGAs evaluation results
│
├── data/
│   ├── documents/                     # Source PDFs (gitignored)
│   ├── qa_dataset/                    # 100-question benchmark (EN + KR)
│   └── trees/                         # Generated PageIndex trees with references
│
├── pageindex_core/                    # PageIndex open-source library (cloned)
├── docs/
│   ├── research_proposal.md           # Research proposal (updated methodology)
│   ├── history.md                     # Development history and design decisions
│   └── todo.md                        # Prioritized task tracking
└── notebooks/                         # Jupyter notebooks
```

## Architecture

```
User Query → GWMAgent (dynamic multi-hop loop, max 4)
  ├── State:       DynamicSubKG (NetworkX DiGraph) — short-term memory
  ├── Action:      PageIndexEnvironment — agentic retrieval (Intended Action)
  │                + dynamic termination (LLM judges sufficiency)
  ├── Transition:  ReasoningModule — infer two-tier edges
  │                Structural: REFERENCES, SPECIFIES
  │                Semantic:   SATISFIES, VIOLATES, SUPPORTS, CONTRADICTS,
  │                            LEADS_TO, IS_PREREQUISITE_OF
  └── Vision:      Collect referenced Figure/Table pages → render JPEG
                   → GPT-4.1 vision API (final answer only)
→ Final Answer + KG (JSON) + Trajectory
```

### Key Design Decisions

- **Dynamic termination**: `plan_next_search()` returns `{sufficient, next_search_query}`. Agent stops when evidence is sufficient. No extra LLM call (integrated into planning).
- **Summary-based KG context**: `to_context_string()` uses node summaries (not truncated content) to preserve key facts in LLM prompts.
- **Vision at answer step only**: Multimodal processing applied only to `generate_answer()` (1 call/query) for cost efficiency. All intermediate steps are text-only.
- **Reference linking**: Figure/Table metadata parsed from PDF and attached to tree nodes via `references` field. Solves the "figure on different page" problem.
- **Two-tier edge ontology**: Structural edges (REFERENCES, SPECIFIES) form exploration backbone; Semantic edges emerge in composite multi-hop queries.
- **Exclude explored nodes**: `exclude_node_ids` prevents re-selection of already-visited nodes.

### Key Patterns

- All LLM responses parsed as JSON with `re.sub(r"```json\s*|\s*```", "", response)` cleanup
- Node IDs: `"{doc_id}_{node_id}"` (e.g., `nuscale_ch01_0006`)
- Node cache keys: `"{doc_id}::{node_id}"` in PageIndexEnvironment
- Edge confidence threshold: ≥ 0.4
- All prompts and output in English
- Evaluation via RAGAs framework (Faithfulness, Answer Relevancy, Context Recall, Factual Correctness)

### Dependencies

Core: `openai`, `networkx`, `matplotlib`, `python-dotenv`, `ragas`, `langchain-openai`.
PageIndex: `PyMuPDF` (fitz), `PyPDF2`, `tiktoken`, `pyyaml`.

## Docs Convention

- `docs/history.md` — Version-by-version development log with issues found and resolutions. Update after each significant change.
- `docs/todo.md` — Prioritized task list (High/Medium/Low/Completed). Move items to Completed when done.
- `docs/research_proposal.md` — Academic research proposal. Update when methodology changes.
