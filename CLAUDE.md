# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multimodal regulatory document exploration agent. Combines GPT-4.1 reasoning with PageIndex tree indexing to build dynamic knowledge graphs from NuScale FSAR documents. Uses a State-Action-Transition loop with dynamic termination and Vision-augmented answer generation.

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
├── benchmark/                         # [평가] 평가 스크립트 + 전 모델 결과 (정규 위치)
│   ├── llm_judge.py                   # LLM-as-Judge 평가
│   ├── evaluate_ragas.py              # 베이스라인 RAGAs 평가
│   ├── aggregate_results.py           # 교차 비교 리포트
│   └── results/{method}/              # pred.json, judge.json, ragas.json, note.md
│
├── baseline_experiment/               # [코드] 베이스라인 구현 코드 (결과는 benchmark/results/)
│   ├── graphrag/                      # GraphRAG 실행 스크립트 + 설정
│   ├── hipporag/                      # HippoRAG 실행 스크립트
│   ├── lightrag/                      # LightRAG 실행 스크립트
│   ├── raptor/                        # RAPTOR 알고리즘 구현
│   └── scripts/                       # RAPTOR 실행 스크립트
│
├── data/
│   ├── documents/                     # Source PDFs (gitignored)
│   ├── qa_dataset/                    # 200-question benchmark (multihop_qa_benchmark_v2.json)
│   └── trees/                         # Generated PageIndex trees with references
│
├── pageindex_core/                    # PageIndex library (gitignored, clone: git clone https://github.com/VectifyAI/PageIndex.git pageindex_core)
├── docs/                              # [관리] 프로젝트 관리 문서
│   ├── current_status.md              # 프로젝트 현재 상태 스냅샷
│   ├── issues.md                      # 알려진 문제점과 기술 부채
│   ├── todo.md                        # Prioritized task tracking
│   ├── history.md                     # Development history and design decisions
│   ├── research_proposal.md           # Academic research proposal
│   └── supplementary/                 # 참고/분석 문서
│       ├── baseline_experiment_guide.md
│       ├── baseline_comparison_results.md
│       ├── benchmark_feedback.md
│       └── experiment_analysis.md
│
├── research_paper/                    # [논문] 섹션별 원고 + 작성 관리
│   ├── title_abstract.md, introduction.md, related_works.md, method.md
│   ├── benchmark.md, experiment.md, conclusion.md, references.md
│   └── docs/                          # 논문 작성 관점 관리 문서
│       ├── concepts.md                # 핵심 컨셉, 포지셔닝, 메시지
│       ├── current_status.md          # 섹션별 완성도
│       ├── todo.md, issues.md, history.md
│
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

### Core docs (항상 최신 유지)

- `docs/current_status.md` — 프로젝트 현재 상태 스냅샷. 작업 시작 전/후 업데이트. 포함: 각 컴포넌트 상태, 실험 진행률, 다음 단계.
- `docs/issues.md` — 현재 알려진 문제점과 기술 부채. 발견 즉시 등록, 해결 시 해결일과 방법 기록. 구조: Open / Resolved 섹션.
- `docs/todo.md` — 우선순위별 작업 목록 (High/Medium/Low/Completed). 완료 시 Completed로 이동.
- `docs/history.md` — 버전별 개발 로그. 이슈 발견과 해결 포함. 유의미한 변경 후 업데이트.
- `docs/research_proposal.md` — 학술 연구 제안서. 방법론 변경 시 업데이트.

### Supplementary docs (참고용)

- `docs/supplementary/baseline_experiment_guide.md` — 베이스라인 실험 가이드 (팀원용)
- `docs/supplementary/baseline_comparison_results.md` — 베이스라인 비교 결과 통합
- `docs/supplementary/benchmark_feedback.md` — 벤치마크 피드백
- `docs/supplementary/experiment_analysis.md` — 실험 분석

### Research paper (논문 원고 + 작성 관리)

- `research_paper/` — 섹션별 논문 원고. README.md에 구조 설명.
- `research_paper/docs/` — 논문 작성 관점의 관리 문서. 프로젝트 docs/와 동일한 패턴(concepts, current_status, todo, issues, history) 적용.
  - `concepts.md` — 논문 포지셔닝, 타겟 학회, 핵심 메시지. 방향 변경 시 업데이트.
  - `current_status.md` — 섹션별 완성도, 데이터 현황. 작업 전후 업데이트.
  - `todo.md` — 논문 완성 전 할 일. 완료 시 Completed로 이동.
  - `issues.md` — 약점, 리뷰어 예상 질문. 대응 전략 포함.
  - `history.md` — 포지셔닝 변경, 리비전 등 주요 작성 이력.

### 업데이트 규칙

1. **작업 시작 전**: `current_status.md` 읽고 현재 상태 파악 → 작업 계획 수립
2. **작업 중 이슈 발견**: `issues.md`에 즉시 등록 (제목, 설명, 발견 경위)
3. **작업 완료 후**: `current_status.md` 업데이트, `todo.md`에서 완료 처리, 유의미한 변경이면 `history.md`에 기록
4. **docs 간 참조**: 문서 간 중복 최소화, 상세 내용은 해당 문서에 두고 링크로 연결
