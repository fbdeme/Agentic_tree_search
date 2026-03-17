# Agentic Tree Search

GWM (Graph World Model) based multimodal agent for multi-hop regulatory document exploration.

Implements GWM's State-Action-Transition loop with **PageIndex** as the environment (World), dynamically constructing a knowledge graph from NuScale FSAR documents.

## Architecture

```
[User Query]
      ↓
┌──────────────────────── GWM Agent ────────────────────────────┐
│                                                                │
│  State (Short-term Memory)       Action (Exploration)          │
│  ┌─────────────────────┐         ┌───────────────────────────┐ │
│  │  Dynamic Sub-KG      │ ←───── │  PageIndex Tree Search    │ │
│  │  (NetworkX DiGraph)  │        │  (Agentic Retrieval)      │ │
│  │  + References        │        │  + Dynamic Termination    │ │
│  └─────────────────────┘         └───────────────────────────┘ │
│           ↑                                                    │
│    Transition (GPT-4.1 edge inference)                         │
│    Structural: REFERENCES, SPECIFIES                           │
│    Semantic:   SATISFIES, VIOLATES, SUPPORTS, CONTRADICTS,     │
│                LEADS_TO, IS_PREREQUISITE_OF                    │
└────────────────────────────────────────────────────────────────┘
      ↓ (dynamic termination or max hops)
[Vision-Augmented Answer Generation]
  Text KG context + Referenced Figure/Table images → GPT-4.1 Vision
```

## Quick Start

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Build PageIndex trees from FSAR PDFs (one-time)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/build_trees.py

# 3. Run evaluation (RAGAs framework)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py --start 1 --end 5

# 4. Run predefined experiments (simulated tree)
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/run_experiment.py
```

## Key Features

- **Vectorless Retrieval**: No embeddings or chunking. LLM reasons over PageIndex tree structure (ToC) to select relevant sections.
- **Dynamic Sub-KG**: Knowledge graph built on-the-fly during exploration with domain-specific edges grounded in systems engineering and argumentation theory.
- **Two-Tier Edge Ontology**: Structural edges (REFERENCES, SPECIFIES) form exploration paths; Semantic edges (SATISFIES, SUPPORTS, etc.) capture regulatory judgment.
- **Vision RAG**: Referenced Figures and Tables are rendered from PDF pages and passed to GPT-4.1 vision for multimodal answer generation.
- **Dynamic Termination**: Agent stops exploring when evidence is sufficient (PageIndex-style iterative retrieval).
- **RAGAs Evaluation**: Faithfulness, Answer Relevancy, Context Recall, Factual Correctness on 100-question NuScale FSAR benchmark.

## Project Structure

```
Agentic_tree_search/
├── src/
│   ├── agent/                  # GWM agent + GPT-4.1 reasoning
│   ├── environment/            # PageIndex tree environment
│   ├── state/                  # Dynamic Sub-KG (NetworkX)
│   └── utils/                  # Visualization + Vision (PDF rendering)
├── experiments/
│   ├── build_trees.py          # PDF → tree + Figure/Table metadata
│   ├── evaluate.py             # RAGAs benchmark evaluation
│   └── run_experiment.py       # Predefined experiments
├── data/
│   ├── documents/              # Source PDFs (gitignored)
│   ├── qa_dataset/             # 100-question benchmark
│   └── trees/                  # Generated PageIndex trees
├── docs/
│   ├── research_proposal.md    # Research proposal
│   ├── history.md              # Development history
│   └── todo.md                 # Task tracking
└── pageindex_core/             # PageIndex library (cloned)
```

## Docs

| File | Purpose |
|------|---------|
| `docs/research_proposal.md` | Academic research proposal with methodology, edge ontology, and preliminary results |
| `docs/history.md` | Version-by-version development log — design decisions, issues found, resolutions |
| `docs/todo.md` | Prioritized task tracking — update when starting/completing tasks |

## References

- [Graph World Model (GWM)](https://arxiv.org/abs/2505.xxxxx) — State-Action-Transition framework
- [PageIndex](https://pageindex.ai/) — Vectorless reasoning-based RAG
- [RAGAs](https://docs.ragas.io/) — RAG evaluation framework
- [NuScale FSAR](https://www.nrc.gov/) — Source regulatory documents
