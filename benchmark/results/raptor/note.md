# RAPTOR Baseline 구현 노트

실험일: 2026-03-30
브랜치: `baseline/raptor`

---

## 환경

| 항목 | 값 |
|------|----|
| 생성 LLM | gpt-4.1 |
| 요약 LLM (인덱싱) | gpt-4.1 |
| 임베딩 | text-embedding-3-small (1536d) |
| Chunk size | 100 tokens (tiktoken cl100k_base, 문장 경계 존중) |
| Temperature | 0 |
| max_tokens (생성) | 300 |

> 원논문은 SentenceTransformer(multi-qa-mpnet-base-cos-v1) 사용.
> 이 실험은 OpenAI 생태계 통일 목적으로 text-embedding-3-small 사용.

---

## 인덱싱

| 항목 | 값 |
|------|----|
| 소스 PDF | NuScale FSAR Ch.01 (352p) + Ch.05 (160p) |
| 리프 청크 수 | 3,422개 (Ch.01: 2,543 / Ch.05: 879) |
| 요약 노드 수 | 624개 (Level1: ~587, Level2: ~37 수준) |
| 전체 트리 노드 | 4,046개 |
| 클러스터링 방식 | UMAP(cosine, n_comp=10) + GMM(BIC 최적 k, threshold=0.1) 2단계 |
| 인덱싱 소요 시간 | **43.5분** (2612초) |
| 인덱스 파일 | baseline_experiment/raptor/index/raptor_tree.json |

---

## 검색 설정

| 항목 | 값 |
|------|----|
| 검색 모드 | collapse_tree (전 레벨 flat 검색) |
| Context token budget | 2,000 tokens |
| 임베딩 사전 계산 | 인덱스 로드 시 4,046개 전체 |

---

## 추론

| 항목 | 값 |
|------|----|
| 문항 수 | 200개 (multihop_qa_benchmark_v2.json) |
| 에러 | 0건 |
| 소요 시간 | **6.7분** (402초) |

---

## 평가 결과 (LLM-as-Judge)

### 전체 Accuracy

| 지표 | 값 |
|------|----|
| **Accuracy** | **69.0%** (138/200) |
| GWM v0.4.6 (비교) | 81.0% (162/200) |
| 차이 | -12.0%p |

### Reasoning Type별

| reasoning_type | Accuracy | n |
|---------------|----------|---|
| factual | 55.7% | 70 |
| comparative | 69.2% | 65 |
| judgment | **83.1%** | 65 |

### Complexity별

| complexity | Accuracy | n |
|-----------|----------|---|
| single_evidence | 68.0% | 50 |
| multi_evidence | **72.0%** | 75 |
| cross_document | 66.7% | 75 |

### Question Type별

| question_type | Accuracy | n |
|--------------|----------|---|
| text_only | **73.8%** | 80 |
| table_only | 66.0% | 50 |
| image_only | 66.7% | 30 |
| composite | 65.0% | 40 |

### 9-Cell Matrix (reasoning × complexity)

| | single_evidence | multi_evidence | cross_document |
|---|---|---|---|
| **factual** | 53.3% | 64.0% | 46.7% |
| **comparative** | 93.3% | 64.0% | 60.0% |
| **judgment** | 80.0% | 88.0% | 80.0% |

### Evaluator 세부

| Evaluator | ≥threshold | 비고 |
|-----------|-----------|------|
| Tonic (GPT-4-turbo, sim≥4) | 177/200 | |
| MLflow sim (GPT-4o, ≥4) | 152/200 | |
| MLflow corr (GPT-4o, ≥4) | 143/200 | |
| Allganize (Claude Sonnet 4.5) | N/A | ANTHROPIC_API_KEY 미제공 → 전 문항 -1(X) 처리 |

> Allganize 전 문항 X로 처리됨 — 최종 Accuracy는 실제보다 낮을 수 있음.
> Tonic+MLflow 3표만으로 과반 충족 시 O, 동률 시 X 우선 정책 적용.

---

## 특이사항

- **factual 정확도(55.7%) 낮음**: RAPTOR 요약 트리는 추상적 요약 위주로 구축되어 구체적 수치(사실) 검색에 불리함. GWM의 vectorless BM25+LLM 탐색 대비 정밀도 낮음.
- **judgment 정확도(83.1%) 높음**: 고레벨 요약 노드가 판단형 질문에 적합한 맥락을 잘 포착함.
- **Allganize 미평가**: ANTHROPIC_API_KEY 없이 실행 — 재평가 시 실제 Accuracy 상승 예상.
- 인덱싱 비용: ~$0.7 (임베딩) + ~$0.7 (요약 gpt-4.1 ~624회) ≈ **$1.4**
- 추론 비용: ~$0.6 (gpt-4.1 200회)
- Judge 비용: ~$8 (Tonic GPT-4-turbo + MLflow GPT-4o 각 200회)
