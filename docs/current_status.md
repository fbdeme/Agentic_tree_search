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

## Baseline 실험 현황

### 결과 파일 상태 (가이드 기준: `benchmark/results/{method}/`)

> 브랜치 통합 완료 (2026-04-07): baseline/lightrag, baseline/pageindex → main 머지

| 방법론 | pred.json | judge.json | ragas.json | note.md |
|--------|:-:|:-:|:-:|:-:|
| **GraphRAG** | O | O | O | O |
| **RAPTOR** | O | O | O | O |
| **HippoRAG** | O (v2) | O (v2) | O | O |
| **LightRAG** | O (v2) | O (v2) | O | O |
| **PageIndex** | O | O | O | O |

### LLM-as-Judge 결과 비교

| 방법론 | Accuracy | 데이터 버전 |
|--------|:--------:|------------|
| **Ours** | **81.0%** | main |
| RAPTOR | 75.5% | main |
| HippoRAG | 70.5% | v2 (baseline/lightrag 브랜치) |
| LightRAG | 73.0% | v2 (baseline/lightrag 브랜치) |
| GraphRAG | 49.5% | main |
| PageIndex only | 43.5% | baseline/pageindex 브랜치 |

> Note: HippoRAG/LightRAG v2는 retrieved_contexts 포함 재실험. LightRAG는 aquery→aquery_data 변경으로 67.5%→73.0% 개선.

### RAGAs 결과

| 방법론 | Faithfulness | AR | CR | FC | 상태 |
|--------|:-:|:-:|:-:|:-:|:---:|
| Ours | 0.93 | — | 0.93 | 0.42 | 완료 |
| GraphRAG | 0.28 | 0.59 | 0.18 | 0.32 | 완료 |
| RAPTOR | 0.74 | 0.83 | 0.77 | 0.40 | 완료 |
| HippoRAG | 0.76 | 0.83 | 0.76 | 0.37 | 완료 |
| LightRAG | 0.89 | — | 0.76 | 0.37 | 완료 |
| PageIndex | 0.58 | — | 0.44 | 0.28 | 완료 |

---

## 다음 단계 (우선순위 순)

1. **[진행 중] RAGAs 평가 실행**: HippoRAG, LightRAG, PageIndex (스크립트: `benchmark/evaluate_ragas.py`)
2. **[진행 중] 결과 파일 정리**: 가이드(`docs/baseline_experiment_guide.md` Section 5.5)대로 `benchmark/results/{method}/ragas.json`에 통일
3. **[대기] 효율성 비교**: 5문항 샘플 실측 → 문항당 시간/토큰/비용 측정 (베이스라인별)
4. **[대기] 논문 업데이트**: Section 5.5 효율성 비교 테이블 채우기
5. **[대기] Paper figures**: Figure 1~4 디자인 (design/figures/)

---

## 알려진 문제 → `docs/issues.md` 참조
