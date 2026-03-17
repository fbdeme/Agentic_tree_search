# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agentic Tree Search implements a Graph World Model (GWM) for multi-hop regulatory document exploration. It combines GPT-4.1 reasoning with the PageIndex library to build dynamic knowledge graphs from hierarchical document structures (e.g., nuclear facility FSARs). The system iteratively searches, synthesizes, and infers relationships between document sections through a State-Action-Transition loop.

## Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run experiments with simulated FSAR tree
python experiments/run_experiment.py

# Generate document tree from PDF via PageIndex
cd pageindex_core && python run_pageindex.py --pdf_path /path/to/fsar.pdf --model gpt-4.1
```

Results are saved to `experiments/results/` (PNG visualizations + JSON KGs).

**Environment**: Requires `OPENAI_API_KEY` in `.env` file.

## Data Layout

```
data/
├── documents/          # Source PDF documents (gitignored)
│   ├── NuScale FSAR Ch.01 (공개본).pdf
│   └── NuScale FSAR Ch.05 (공개본).pdf
└── qa_dataset/         # Evaluation QA datasets
    ├── nuclear_qa_dataset.json      # Korean
    └── nuclear_qa_dataset_en.json   # English
```

## Architecture

```
User Query → GWMAgent (4-hop loop)
  ├── State:       DynamicSubKG (NetworkX DiGraph) — short-term memory
  ├── Action:      PageIndexEnvironment — agentic retrieval from document tree
  └── Transition:  ReasoningModule (GPT-4.1) — infer relationships → add edges
→ Final Answer + KG Visualization
```

### Core Modules

- **`src/agent/gwm_agent.py`** — Orchestrates the State-Action-Transition loop. Runs `max_hops` iterations (default 4), each retrieving `top_k` nodes, adding them to the KG, and inferring edges.
- **`src/agent/reasoning.py`** — All GPT-4.1 calls: `plan_next_search()`, `infer_relation()`, `summarize_node()`, `generate_answer()`. Uses temperature 0.1 and expects JSON structured output.
- **`src/environment/pageindex_env.py`** — Loads PageIndex JSON trees, caches nodes via DFS flattening (key format: `"{doc_id}::{node_id}"`), and uses LLM to select relevant nodes from tree structure.
- **`src/state/knowledge_graph.py`** — `DynamicSubKG` wrapping `nx.DiGraph()`. `KGNode` represents document sections; `KGEdge` represents one of 8 relationship types (REFERENCES, SUPPORTS, CONTRADICTS, SATISFIES, VIOLATES, IS_PREREQUISITE_OF, LEADS_TO, SPECIFIES). Edges require confidence ≥ 0.4.
- **`src/utils/visualize.py`** — KG visualization with NetworkX spring layout + matplotlib dark theme. Nodes colored by discovery hop, edges by relationship type.
- **`experiments/run_experiment.py`** — Runs predefined experiments against `sample_fsar_tree.json`.

### Key Patterns

- All LLM responses are parsed as JSON with `re.sub(r"```json\s*|\s*```", "", response)` cleanup
- Node IDs follow format `"{doc_id}_{node_id}"`
- Prompts, comments, and output are in Korean
- No test suite currently exists

### Dependencies

Core: `openai`, `networkx`, `matplotlib`, `python-dotenv`. PageIndex: `PyMuPDF`, `PyPDF2`, `tiktoken`, `pyyaml`.
