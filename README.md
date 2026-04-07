# Agentic Tree Search

Multimodal agent for multi-hop regulatory document exploration.

Implements a State-Action-Transition loop with **PageIndex** as the environment (World), dynamically constructing a knowledge graph from NuScale FSAR documents.

## Results

### Ours (v0.4.6)

| Metric | Value |
|--------|-------|
| LLM-as-Judge Accuracy | **81.0%** (162/200) |
| RAGAs Faithfulness | **0.93** |
| RAGAs Context Recall | **0.93** |
| Judgment Accuracy | **90.8%** |
| Cross-document Accuracy | **81.3%** |

### Baseline Comparison — LLM-as-Judge (200Q, NuScale FSAR Ch.01 + Ch.05)

| Method | Overall | judgment | comparative | factual | cross_document | table_only | composite |
|--------|:-------:|:--------:|:-----------:|:-------:|:--------------:|:----------:|:---------:|
| **Ours** | **81.0%** (162/200) | 90.8% | **78.5%** | **74.3%** | **81.3%** | **86.0%** | **85.0%** |
| RAPTOR (Sarthi et al. 2024) | 75.5% (151/200) | **92.3%** | 72.3% | 62.9% | 73.3% | 68.0% | 72.5% |
| HippoRAG (Gutierrez et al. 2024) | 69.0% (138/200) | 86.2% | 63.1% | 58.6% | 65.3% | 56.0% | 55.0% |
| LightRAG (Guo et al. 2024) | 67.5% (135/200) | 75.4% | 66.2% | 61.4% | 69.3% | 60.0% | 65.0% |
| GraphRAG (Edge et al. 2024) | 49.5% (99/200) | 61.5% | 49.2% | 38.6% | 37.3% | 42.0% | 47.5% |

> Evaluator: 3-way majority vote — Tonic (GPT-4-turbo) · MLflow (GPT-4o) · Allganize (Claude Sonnet 4.5)
> Full breakdown → [`docs/supplementary/baseline_comparison_results.md`](docs/supplementary/baseline_comparison_results.md)

## Architecture

```
[User Query]
      ↓
┌──────────────────────── Our Agent ────────────────────────────┐
│                                                                │
│  State (Short-term Memory)       Action (Exploration)          │
│  ┌─────────────────────┐         ┌───────────────────────────┐ │
│  │  Dynamic Sub-KG      │ ←───── │  Tool-based Navigation    │ │
│  │  (NetworkX DiGraph)  │        │  browse / read / search   │ │
│  │  + Agent Memory      │        │  + BM25 + PRF (RM3)       │ │
│  └─────────────────────┘         └───────────────────────────┘ │
│           ↑                                                    │
│    Transition (Two-stage edge inference)                       │
│    Structural: REFERENCES, SPECIFIES                           │
│    Semantic:   SATISFIES, VIOLATES, SUPPORTS, CONTRADICTS,     │
│                LEADS_TO, IS_PREREQUISITE_OF, SEMANTIC           │
└────────────────────────────────────────────────────────────────┘
      ↓ (dynamic termination or max hops)
[Vision-Augmented Answer Generation]
  KG context + Structured Tables + Figure Images → GPT-4.1 Vision
```

## Key Features

- **Vectorless Retrieval**: No embeddings or chunking. BM25 + PRF query expansion with tool-based navigation (browse/read/search).
- **Browse-first Exploration**: Document structure auto-injected at first hop. Agent sees table of contents before searching.
- **Two-stage Edge Inference**: Description-first (LightRAG-style free-form), then ontology label mapping. All 9 edge types emerge naturally.
- **Vision RAG**: Figures as VLM images, Tables as structured text (PyMuPDF `find_tables()`).
- **Agent Memory**: Search history prevents keyword repetition across hops.
- **Dynamic Termination**: Agent stops when evidence is sufficient.
- **Dual Evaluation**: RAGAs (Faithfulness, AR, CR, FC) + LLM-as-Judge (3 evaluator majority vote).

## Project Structure

```
Agentic_tree_search/
├── src/                           # Core agent implementation
│   ├── agent/
│   │   ├── gwm_agent.py           # State-Action-Transition loop
│   │   └── reasoning.py           # GPT-4.1 reasoning (plan, infer, answer)
│   ├── environment/
│   │   └── pageindex_env.py       # browse/read/search tools + BM25 + PRF
│   ├── state/
│   │   └── knowledge_graph.py     # DynamicSubKG, KGNode, KGEdge
│   └── utils/
│       ├── vision.py              # PDF page rendering (PyMuPDF → JPEG)
│       └── visualize.py           # KG visualization
│
├── experiments/                   # RAGAs evaluation pipeline
│   ├── build_trees.py             # PDF → PageIndex tree + Figure/Table metadata
│   ├── evaluate.py                # RAGAs evaluation (Faithfulness, AR, CR, FC)
│   ├── re_evaluate.py             # Re-evaluate saved results without agent re-run
│   └── results/eval/              # RAGAs results + KG JSONs
│
├── benchmark/                     # LLM-as-Judge evaluation pipeline
│   ├── config.py                  # Evaluator models, taxonomy, paths
│   ├── run_baseline.py            # Answer collection (our agent or vanilla LLM)
│   ├── llm_judge.py               # 3-evaluator majority vote (MAM-RAG Table 8)
│   ├── aggregate_results.py       # Cross-model comparison tables
│   ├── validate_dataset.py        # Dataset schema validation
│   └── results/                   # Predictions + Judge results
│
├── data/
│   ├── documents/                 # Source PDFs (gitignored)
│   ├── qa_dataset/                # Benchmark datasets
│   │   ├── multihop_qa_benchmark_v2.json  # 200-question multihop benchmark
│   │   └── nuclear_qa_dataset_en.json     # Original 100-question dataset
│   └── trees/                     # Generated PageIndex trees with references
│
├── docs/
│   ├── research_proposal.md       # Research proposal
│   ├── experiment_analysis.md     # 3-axis experiment analysis
│   ├── benchmark_feedback.md      # Benchmark improvement proposals
│   ├── history.md                 # Development history
│   └── todo.md                    # Task tracking
│
└── pageindex_core/                # PageIndex library (cloned)
```

## Reproducing Experiments

### Prerequisites

```bash
# 1. Python environment
source .venv/bin/activate

# 2. Install dependencies
pip install openai networkx matplotlib python-dotenv ragas langchain-openai \
            langchain-anthropic mlflow pandas tqdm seaborn rank-bm25 PyMuPDF

# 3. API keys in .env
OPENAI_API_KEY=sk-...          # GPT-4.1 (agent) + GPT-4-turbo/4o (evaluators)
ANTHROPIC_API_KEY=sk-ant-...   # Claude Sonnet 4.5 (Allganize evaluator)

# 4. Source PDFs (place in data/documents/)
# NuScale FSAR Ch.01 and Ch.05 (publicly available from NRC)
```

### Step 1: Build PageIndex Trees (one-time)

```bash
PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/build_trees.py
# Output: data/trees/nuscale_ch01_structure.json (866 nodes, 34 figures, 19 tables)
#         data/trees/nuscale_ch05_structure.json (26 nodes, 29 figures, 30 tables)
```

### Step 2: Collect Agent Answers

```bash
# 8x parallel (25 questions each, ~40 min total)
for i in $(seq 1 8); do
  start=$(( (i-1)*25 + 1 ))
  end=$(( i*25 ))
  PYTHONPATH=pageindex_core:$PYTHONPATH python -m benchmark.run_baseline \
    --method gwm --tree-dir data/trees/ \
    --output benchmark/results/pred_gwm_${i}.json \
    --start $start --end $end &
done
wait
```

### Step 3A: RAGAs Evaluation

```bash
DATASET="data/qa_dataset/multihop_qa_benchmark_v2.json"

# 8x parallel
for i in $(seq 1 8); do
  start=$(( (i-1)*25 + 1 ))
  end=$(( i*25 ))
  PYTHONPATH=pageindex_core:$PYTHONPATH python experiments/evaluate.py \
    --dataset $DATASET --start $start --end $end &
done
wait
# Output: experiments/results/eval/eval_ragas_*.json + kg_Q*.json
```

### Step 3B: LLM-as-Judge Evaluation

```bash
# Requires OPENAI_API_KEY (GPT-4-turbo, GPT-4o) + ANTHROPIC_API_KEY (Claude Sonnet)
for i in $(seq 1 8); do
  python -m benchmark.llm_judge \
    benchmark/results/pred_gwm_${i}.json \
    --output benchmark/results/judge_gwm_${i}.json &
done
wait
# Output: benchmark/results/judge_gwm_*.json
```

### Step 4: Analyze Results

```bash
# RAGAs summary
python3 -c "
import json, glob
files = sorted(glob.glob('experiments/results/eval/eval_ragas_*.json'))
results = []
for f in files:
    with open(f) as fh:
        results.extend(json.load(fh)['results'])
valid = [r for r in results if 'error' not in r]
for m in ['faithfulness','answer_relevancy','context_recall','factual_correctness']:
    vals = [r[m] for r in valid if r.get(m) is not None]
    print(f'{m}: {sum(vals)/len(vals):.4f} (n={len(vals)})')
"

# LLM-as-Judge summary
python3 -c "
import json, glob
files = sorted(glob.glob('benchmark/results/judge_gwm_*.json'))
results = []
for f in files:
    with open(f) as fh:
        results.extend(json.load(fh)['results'])
correct = sum(1 for r in results if r.get('final_vote') == 'O')
print(f'Accuracy: {correct}/{len(results)} = {correct/len(results)*100:.1f}%')
"
```

## Docs

| File | Purpose |
|------|---------|
| `docs/supplementary/experiment_analysis.md` | 3-axis analysis: benchmark types × evaluation frameworks × KG edges |
| `docs/research_proposal.md` | Academic research proposal with methodology and results |
| `docs/supplementary/benchmark_feedback.md` | Benchmark improvement proposals based on evaluation findings |
| `docs/history.md` | Version-by-version development log |
| `docs/todo.md` | Prioritized task tracking |

## References

- State-Action-Transition framework for agentic document exploration
- [PageIndex](https://pageindex.ai/) — Vectorless reasoning-based RAG
- [RAGAs](https://docs.ragas.io/) — RAG evaluation framework
- [MAM-RAG](https://arxiv.org/) — LLM-as-Judge evaluation methodology
- [NuScale FSAR](https://www.nrc.gov/) — Source regulatory documents
