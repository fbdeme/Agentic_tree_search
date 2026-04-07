# Ours vs Baseline 비교 실험 결과 (통합)

**최종 갱신**: 2026-03-31
**원본 작성**: 김보경 (LightRAG, HippoRAG), RAPTOR/GraphRAG 브랜치 추가
**프로젝트**: Multimodal Regulatory Document Exploration Agent

---

## 1. 실험 배경

### 1.1 목적

Our agent v0.4.6의 성능을 4개 베이스라인(RAPTOR, HippoRAG, LightRAG, GraphRAG)과 동일 벤치마크·동일 평가 프레임워크로 비교하여, our method의 기여를 정량적으로 분리한다.

### 1.2 비교 대상

| 방법론 | 논문 | 핵심 특징 |
|--------|------|----------|
| **Ours** | — | Vectorless, State-Action-Transition loop, Dynamic Sub-KG, Vision RAG |
| **RAPTOR** | Sarthi et al. (2024) | 재귀적 요약 트리 + collapse_tree 검색 |
| **HippoRAG** | Gutierrez et al. (2024) | 해마 기반 연상 메모리 + KG + Personalized PageRank |
| **LightRAG** | Guo et al. (2024) | 이중 레벨(entity + topic) 그래프 검색 + 벡터 DB |
| **GraphRAG** | Edge et al. (2024) | 커뮤니티 기반 글로벌/로컬 검색 (Microsoft) |

### 1.3 공정 비교 조건

| 항목 | 값 |
|------|-----|
| 생성 LLM | gpt-4.1 (모든 방법론 통일) |
| 인덱싱 LLM | gpt-4.1 |
| Embedding | text-embedding-3-small (1536d) |
| Temperature | 0 |
| max_tokens | 300 |
| 답변 프롬프트 | 동일 system_prompt (가이드 4.3절) |
| 데이터셋 | multihop_qa_benchmark_v2.json (200문항) |
| 소스 문서 | NuScale FSAR Ch.01 + Ch.05 |
| 평가 프레임워크 | LLM-as-Judge (Tonic + MLflow + Allganize, majority vote) |

---

## 2. 실험 환경

| 항목 | Ours | RAPTOR | LightRAG | HippoRAG | GraphRAG |
|------|-----|--------|----------|----------|----------|
| 라이브러리 | (자체 구현) | 공식 레포 기반 | lightrag-hku v1.4.12 | hipporag 2.0.0a4 | graphrag 3.0.8 |
| Python | 3.12 | 3.12 | 3.12 | 3.10 (별도 venv) | 3.13 (별도 venv) |
| 검색 방법 | BM25+PRF tool-based | collapse_tree (2K tokens) | hybrid (local+global) | PPR + dense embedding | Local Search (community_level=2) |
| 인덱싱 | 없음 (vectorless) | 재귀 요약 트리 | 엔티티/관계 추출 + 벡터 DB | OpenIE → KG + PPR | 엔티티/관계 추출 → 커뮤니티 탐지 → 요약 |

---

## 3. 인덱싱 비용 비교

| | **Ours** | **RAPTOR** | **LightRAG** | **HippoRAG** | **GraphRAG** |
|--|:-:|:-:|:-:|:-:|:-:|
| 인덱싱 시간 | **0분** | 43.5분 | 52분 | 29분 | ~40분 |
| 인덱싱 비용 | **$0** | ~$1.4 | $$$ | $$ | $$$ |
| 인덱스 크기 | **0 MB** | — | ~240 MB | ~200 MB | lancedb |
| KG/트리 노드 수 | 동적 생성 | 4,046 | 8,159 | 12,944 | — |
| 엣지/트리플 수 | 동적 생성 | — | 8,720 | 97,387 | — |

---

## 4. 전체 결과

### 4.1 Overall Accuracy (LLM-as-Judge)

| 방법론 | Correct | Total | **Accuracy** | Δ vs Ours |
|--------|:-------:|:-----:|:------------:|:--------:|
| **Ours** | **162** | 200 | **81.0%** | — |
| RAPTOR | 151 | 200 | 75.5% | −5.5%p |
| HippoRAG | 138 | 200 | 69.0% | −12.0%p |
| LightRAG | 135 | 200 | 67.5% | −13.5%p |
| GraphRAG | 99 | 200 | 49.5% | −31.5%p |

---

## 5. 축별 상세 비교

### 5.1 Reasoning Type별

| Type (n) | **Ours** | **RAPTOR** | **HippoRAG** | **LightRAG** | **GraphRAG** |
|----------|:-------:|:----------:|:------------:|:------------:|:------------:|
| factual (70) | **74.3%** | 62.9% | 58.6% | 61.4% | 38.6% |
| comparative (65) | **78.5%** | 72.3% | 63.1% | 66.2% | 49.2% |
| judgment (65) | 90.8% | **92.3%** | 86.2% | 75.4% | 61.5% |

**핵심 발견:**
- **factual에서 Ours가 유일하게 70%+ 달성** — 동적 탐색이 구체적 수치/사실 검색에 효과적
- **judgment에서 RAPTOR(92.3%)가 Ours(90.8%)를 근소하게 상회** — 재귀적 요약이 고수준 판단에 유리
- **GraphRAG는 factual(38.6%)에서 최저** — 커뮤니티 요약 과정에서 구체적 수치가 손실

### 5.2 Complexity별

| Level (n) | **Ours** | **RAPTOR** | **HippoRAG** | **LightRAG** | **GraphRAG** |
|-----------|:-------:|:----------:|:------------:|:------------:|:------------:|
| single_evidence (50) | **84.0%** | 74.0% | 70.0% | 72.0% | 50.0% |
| multi_evidence (75) | **78.7%** | **78.7%** | 72.0% | 62.7% | 61.3% |
| cross_document (75) | **81.3%** | 73.3% | 65.3% | 69.3% | 37.3% |

**핵심 발견:**
- **multi_evidence에서 Ours와 RAPTOR 동률(78.7%)**, GraphRAG(61.3%)도 선방
- **cross_document에서 GraphRAG(37.3%) 최저** — 커뮤니티 기반 검색이 문서 간 연결 추론에 취약
- **Ours(81.3%)가 cross_document에서 차상위(RAPTOR 73.3%) 대비 +8.0%p**

### 5.3 Question Type별

| Type (n) | **Ours** | **RAPTOR** | **HippoRAG** | **LightRAG** | **GraphRAG** |
|----------|:-------:|:----------:|:------------:|:------------:|:------------:|
| text_only (80) | 76.2% | **80.0%** | 78.8% | 71.2% | 63.7% |
| table_only (50) | **86.0%** | 68.0% | 56.0% | 60.0% | 42.0% |
| image_only (30) | 80.0% | 80.0% | **83.3%** | 73.3% | 26.7% |
| composite (40) | **85.0%** | 72.5% | 55.0% | 65.0% | 47.5% |

**핵심 발견:**
- **text_only에서 RAPTOR(80.0%) 1위** — 재귀 요약이 텍스트 전용 문항에서 유리
- **table_only에서 Ours(86.0%) 압도적** — Vision RAG 효과 (+18~44%p vs 나머지)
- **image_only에서 GraphRAG(26.7%) 최저** — 텍스트 추출 기반이라 이미지 정보 완전 손실
- **composite에서 Ours(85.0%) 압도적** — 멀티모달 + 멀티홉 조합에서 구조적 우위

---

## 6. 9-Cell Matrix (reasoning_type × complexity)

### Ours

| | single_evidence | multi_evidence | cross_document |
|---|:-:|:-:|:-:|
| **factual** | 76.7% | 72.0% | 73.3% |
| **comparative** | **100.0%** | 76.0% | 68.0% |
| **judgment** | 80.0% | 88.0% | **94.3%** |

### RAPTOR

| | single_evidence | multi_evidence | cross_document |
|---|:-:|:-:|:-:|
| **factual** | 60.0% | 72.0% | 53.3% |
| **comparative** | 93.3% | 68.0% | 64.0% |
| **judgment** | **100.0%** | **96.0%** | 88.6% |

### HippoRAG

| | single_evidence | multi_evidence | cross_document |
|---|:-:|:-:|:-:|
| **factual** | 63.3% | 64.0% | 40.0% |
| **comparative** | 73.3% | 64.0% | 56.0% |
| **judgment** | **100.0%** | 88.0% | 82.9% |

### LightRAG

| | single_evidence | multi_evidence | cross_document |
|---|:-:|:-:|:-:|
| **factual** | 63.3% | 64.0% | 53.3% |
| **comparative** | 86.7% | 68.0% | 52.0% |
| **judgment** | 80.0% | 56.0% | 88.6% |

### GraphRAG

| | single_evidence | multi_evidence | cross_document |
|---|:-:|:-:|:-:|
| **factual** | 36.7% | 48.0% | 26.7% |
| **comparative** | 53.3% | 60.0% | 36.0% |
| **judgment** | 80.0% | 76.0% | 48.6% |

**9-Cell 핵심 발견:**
- **Ours의 comparative × single_evidence = 100%** — 단일 증거 비교 문항 완벽 해결
- **Ours의 judgment × cross_document = 94.3%** — 문서 간 교차 판단에서 압도적
- **RAPTOR의 judgment × multi_evidence = 96.0%** — 재귀 요약이 다중 증거 판단에 매우 효과적
- **GraphRAG의 factual × cross_document = 26.7%** — 5개 방법론 중 최저 셀
- **factual × cross_document**: 모든 방법론이 약점 (Ours 73.3% → GraphRAG 26.7%)

---

## 7. 문항별 교차 분석

### 7.1 난이도 분포 (5개 방법론 정답 수 기준)

| 정답 수 | 문항 수 | 해석 |
|:-------:|:-------:|------|
| 5/5 | 59 | 쉬운 문항 (모든 방법론 정답) |
| 4/5 | 56 | 약간 어려운 문항 |
| 3/5 | 36 | 중간 난이도 |
| 2/5 | 24 | 어려운 문항 |
| 1/5 | 10 | 매우 어려운 문항 |
| 0/5 | 15 | 최고 난이도 (모든 방법론 오답) |

- **59문항(29.5%)만 5/5 전원 정답** — GraphRAG 추가로 "쉬운 문항" 비율이 47.5%→29.5%로 하락
- **15문항(7.5%)은 0/5 전원 오답** — 현재 RAG 기술의 공통 한계
- 4/5 이상 = 115문항(57.5%) — 과반은 대부분의 방법론이 해결 가능

### 7.2 Ours vs RAPTOR Head-to-Head

| | 문항 수 |
|--|:------:|
| Ours 정답, RAPTOR 오답 | **25** |
| RAPTOR 정답, Ours 오답 | 14 |
| 동일 결과 | 161 |

→ Ours가 RAPTOR보다 **net +11 문항 우위**

---

## 8. 효율성 비교

| | **Ours** | **RAPTOR** | **LightRAG** | **HippoRAG** | **GraphRAG** |
|--|:-:|:-:|:-:|:-:|:-:|
| 사전 인덱싱 시간 | **0분** | 43.5분 | 52분 | 29분 | ~40분 |
| 문항당 평균 시간 | ~100초 | ~2초 | ~7초 | ~3초 | ~5초 |
| 200문항 총 답변 시간 | ~330분 | ~6.7분 | ~23분 | ~11분 | ~17분 |
| **인덱싱 + 답변 총합** | **~330분** | ~50분 | ~75분 | ~40분 | ~57분 |
| 인덱싱 비용 | $0 | ~$1.4 | $$$ | $$ | $$$ |
| 쿼리 비용 | ~$25 | — | — | — | ~$2.4 |

Ours는 문항당 시간이 가장 길지만(동적 멀티홉 탐색), 사전 인덱싱이 없어 **문서 변경에 즉시 대응 가능**.

---

## 9. RAGAs 평가 현황

| 방법론 | retrieved_contexts | RAGAs 실행 | Faithfulness | Context Recall |
|--------|:--:|:--:|:--:|:--:|
| **Ours** | KG 기반 | 완료 | **0.93** | **0.93** |
| **RAPTOR** | 200/200 저장됨 | **실행 가능** | — | — |
| **GraphRAG** | 200/200 저장됨 | **실행 가능** | — | — |
| HippoRAG | 미저장 | 재실행 필요 | — | — |
| LightRAG | 미저장 | 재실행 필요 | — | — |

> RAPTOR, GraphRAG는 `retrieved_contexts`가 pred.json에 포함되어 있어 RAGAs 평가 즉시 실행 가능.
> HippoRAG, LightRAG는 `retrieved_contexts`를 저장하지 않아 답변 재수집 필요.

---

## 10. Our method의 기여 분리

| 기여 요소 | 근거 | 효과 |
|-----------|------|------|
| **Dynamic exploration** | cross_document: Ours 81.3% vs 차상위(RAPTOR) 73.3% | +8.0%p |
| **Vision RAG (Table)** | table_only: Ours 86.0% vs 차상위(RAPTOR) 68.0% | +18.0%p |
| **Vision RAG (Composite)** | composite: Ours 85.0% vs 차상위(RAPTOR) 72.5% | +12.5%p |
| **Two-tier edge ontology** | judgment × cross_document: Ours 94.3% vs RAPTOR 88.6% | +5.7%p |
| **Vectorless design** | 인덱싱 0분/$0 vs 29~52분/$$$ | 운영 비용 절감 |

> text_only에서 RAPTOR(80.0%)가 Ours(76.2%)를 +3.8%p 상회 — Ours의 개선 여지.

---

## 11. 결론

동일 벤치마크(200문항)·동일 LLM(gpt-4.1)·동일 평가 프레임워크(LLM-as-Judge)에서:

| 순위 | 방법론 | Accuracy |
|:----:|--------|:--------:|
| 1 | **Ours** | **81.0%** |
| 2 | RAPTOR | 75.5% |
| 3 | HippoRAG | 69.0% |
| 4 | LightRAG | 67.5% |
| 5 | GraphRAG | 49.5% |

**Ours가 차상위(RAPTOR) 대비 +5.5%p, 최하위(GraphRAG) 대비 +31.5%p 우위.**

핵심 기여:
1. **멀티홉 교차 문서 검색**(cross_document +8.0%p vs RAPTOR) — State-Action-Transition 루프
2. **멀티모달 처리**(table_only +18.0%p, composite +12.5%p vs RAPTOR) — Vision RAG
3. **규제 판단 × 교차 문서**(judgment × cross_document 94.3%) — 동적 KG + edge ontology
4. **제로 인덱싱**: 문서 변경에 즉시 대응 가능

**남은 과제:**
- text_only 문항에서 RAPTOR 대비 열위(−3.8%p) → 요약 기반 검색 보완 검토
- RAPTOR, GraphRAG RAGAs 평가 실행 (retrieved_contexts 이미 저장됨)
- HippoRAG, LightRAG retrieved_contexts 포함 재수집 → RAGAs 평가
- GPT-4.1 vanilla baseline (fair model comparison)
