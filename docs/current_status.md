# Current Status

**최종 갱신**: 2026-04-07

---

## Our Agent (v0.4.6) — 완료

| 지표 | 값 |
|------|-----|
| LLM-as-Judge | **81.0%** (162/200) |
| RAGAs Faithfulness | 0.93 |
| RAGAs Context Recall | 0.93 |
| RAGAs Factual Correctness | 0.42 |

- 코드 구현 완료, 논문 작성 단계

---

## Baseline 실험 현황 — 전체 완료

### 결과 파일 (가이드 기준: `benchmark/results/{method}/`)

> 브랜치 통합 완료 (2026-04-07): baseline/lightrag, baseline/pageindex → main 머지

| 방법론 | pred.json | judge.json | ragas.json | note.md |
|--------|:-:|:-:|:-:|:-:|
| **GraphRAG** | O | O | O | O |
| **RAPTOR** | O | O | O | O |
| **HippoRAG** | O (v2) | O (v2) | O | O |
| **LightRAG** | O (v2) | O (v2) | O | O |
| **PageIndex** | O | O | O | O |

### LLM-as-Judge 결과

| 방법론 | Accuracy |
|--------|:--------:|
| **Ours** | **81.0%** |
| RAPTOR | 75.5% |
| LightRAG | 73.0% |
| HippoRAG | 70.5% |
| GraphRAG | 49.5% |
| PageIndex only | 43.5% |

### RAGAs 결과 — 전체 완료

| 방법론 | Faithfulness | AR | CR | FC |
|--------|:-:|:-:|:-:|:-:|
| Ours | **0.93** | **0.84** | **0.93** | **0.42** |
| LightRAG | 0.89 | 0.83 | 0.88 | 0.36 |
| RAPTOR | 0.74 | 0.83 | 0.77 | 0.40 |
| HippoRAG | 0.76 | 0.83 | 0.76 | 0.37 |
| PageIndex | 0.58 | 0.77 | 0.66 | 0.30 |
| GraphRAG | 0.28 | 0.59 | 0.18 | 0.32 |

### 효율성 비교 — 완료 (추정 포함)

| 방법론 | 총 시간 | 총 비용 | Accuracy |
|--------|:-------:|:-------:|:--------:|
| Ours | ~320분 | ~$46 | **81.5%** |
| RAPTOR | ~50분 | ~$2.3 | 75.5% |
| LightRAG | ~69분 | ~$17 | 73.0% |
| HippoRAG | ~39분 | ~$5.4 | 70.5% |
| GraphRAG | ~57분 | ~$3.7 | 49.5% |

---

## 논문 (research_paper/) 진행 상태

| 섹션 | 파일 | 상태 |
|------|------|:----:|
| Title + Abstract | title_abstract.md | 초안 완료 |
| Introduction | introduction.md | 초안 완료 |
| Related Works | related_works.md | 초안 완료 |
| Method | method.md | 초안 완료 |
| Benchmark | benchmark.md | 초안 완료 |
| Experiment (5+6) | experiment.md | **RAGAs + 효율성 업데이트 완료** |
| Conclusion | conclusion.md | 초안 완료 |
| References | references.md | 초안 완료 |
| Notes | notes.md | 작성 메모 |

**타겟**: LM4Plan @ ICML 2026 (마감 4/24)

---

## 다음 단계

1. **Paper figures**: Figure 1~4 디자인 (design/figures/)
2. **논문 리뷰/다듬기**: 초안 → 최종 원고
3. **docs/supplementary/baseline_comparison_results.md 업데이트**: v2 결과 + RAGAs 반영

---

## 알려진 문제 → `docs/issues.md` 참조
