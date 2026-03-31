# GraphRAG Baseline 구현 노트

## 개요

- **논문**: Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024)
- **구현**: microsoft/graphrag (PyPI `graphrag==3.0.8`)
- **실험일**: 2026-03-30

---

## 환경

| 항목 | 값 |
|------|----|
| LLM (쿼리) | `gpt-4.1` |
| 임베딩 모델 | `text-embedding-3-small` |
| Temperature | 0 |
| Max tokens (답변) | 기본값 (GraphRAG 내부 제어) |
| Python | 3.13.0 |
| graphrag | 3.0.8 |
| 검색 방식 | Local Search (community_level=2) |

---

## 인덱싱

### 설정

| 항목 | 값 |
|------|----|
| Chunk size | 1,200 tokens |
| Chunk overlap | 100 tokens |
| LLM (인덱싱) | `gpt-4.1` |
| 임베딩 배치 크기 | 16 |
| Entity types | organization, person, geo, event |
| Community max cluster size | 10 |

### 소스 문서

| 문서 | 페이지 수 | 텍스트 크기 |
|------|----------|------------|
| NuScale FSAR Ch.01 | 352 pages | 760 KB |
| NuScale FSAR Ch.05 | 160 pages | 312 KB |
| **합계** | 512 pages | 1.07 MB |

### 인덱싱 파이프라인 결과

```
load_input_documents     ✅  2 documents
create_base_text_units   ✅  267 chunks
create_final_documents   ✅
extract_graph            ✅  267 chunks → entities + relationships
finalize_graph           ✅
extract_covariates       ✅  (disabled)
create_communities       ✅
create_final_text_units  ✅
create_community_reports ✅
generate_text_embeddings ✅  lancedb 벡터스토어
```

### 인덱싱 비용 (추정)

| 항목 | 값 |
|------|----|
| 인덱싱 LLM 호출 | gpt-4.1 (extract_graph × 267, community_reports) |
| 인덱싱 임베딩 | text-embedding-3-small × ~12,183 items |
| 인덱싱 비용 | **별도 기록 필요** (OpenAI 대시보드 확인 권장) |
| 인덱싱 소요 시간 | 약 40분 (extract_graph + community_reports 포함) |

> 참고: GWM은 인덱싱 시간 0분, 비용 $0 (vectorless BM25)

---

## 쿼리 (200문항 답변 수집)

### 설정

```yaml
search_type: local
community_level: 2
response_type: Single Paragraph
```

### 프롬프트 (가이드 4.3 준수)

```
You are an expert AI for nuclear regulatory review.
Based on the provided context, answer the user's question.
Answer in 1-2 sentences ONLY.
State the direct answer with specific values, then cite the source.
Do NOT add uncertainty statements, background, or methodology.
Do NOT add information not found in the provided context.
Answer in English.
```

### 결과

| 항목 | 값 |
|------|----|
| 총 문항 | 200 |
| 성공 | 200 (에러 0) |
| 재시도 | Q154 1건 (소켓 타임아웃 → 재시도 성공) |
| 총 토큰 (tiktoken 추정) | 1,030,505 |
| - Prompt tokens | 970,332 |
| - Completion tokens | 60,173 |
| 문항당 평균 토큰 | 5,153 |
| 쿼리 비용 추정 | **$2.42** (gpt-4.1: input $2/1M, output $8/1M) |
| 정상 응답 시간 중앙값 | 4.8초/문항 |
| 정상 응답 시간 평균 | 5.2초/문항 |

> 토큰 수는 tiktoken(o200k_base)으로 추정한 값. GraphRAG API가 usage를 직접 반환하지 않아 retrieved context + 답변 텍스트 기준으로 계산.

### 답변 길이 분석 (max_tokens=300 적용 후)

| 항목 | 값 |
|------|----|
| 평균 단어 수 | 63.5 |
| 80단어 초과 | 51건 (25.5%) |
| 잘린 답변 | 0건 |

> GraphRAG의 local_search는 복잡한 질문에 대해 프롬프트의 "1-2 sentences ONLY" 지시를 무시하고 더 길게 답변하는 경향이 있음. 단, 잘린 답변은 없으며 정보 손실 없음. llm_judge는 길이가 아닌 정확도 기준으로 평가하므로 비교에 영향 없음.

---

## 파일 구조

```
benchmark/results/graphrag/
├── pred.json       # 200문항 답변 (local search)
├── judge.json      # LLM-as-Judge 평가 결과 (예정)
└── note.md         # 이 파일

graphrag/
├── settings.yaml   # gpt-4.1, temp=0, batch_size=16
├── input/          # PDF 추출 텍스트 (nuscale_ch01.txt, ch05.txt)
├── output/         # 인덱스 parquet + lancedb
├── extract_text.py # PDF → 텍스트 추출 스크립트
└── run_graphrag.py # 200문항 답변 수집 스크립트
```

---

## 특이사항 및 트러블슈팅

1. **Python 버전**: graphrag 3.x는 Python ≥3.11 필요. 프로젝트 기본 환경(3.10.15)과 별도로 `graphrag/.venv` (Python 3.13) 생성.

2. **임베딩 오류**: 첫 인덱싱 시 `generate_text_embeddings` 단계에서 `ConnectionResetError` 발생. `settings.yaml`에 `batch_size: 16`, `batch_max_tokens: 8000` 추가 후 해결.

3. **API 변경**: graphrag 3.x의 `local_search()` 시그니처에서 `nodes=` 파라미터가 제거되고 `communities=`가 필수 인자로 추가됨. 공식 API 확인 후 수정.

4. **Q154 타임아웃**: 소켓 타임아웃으로 에러. 단독 재실행 후 정상 완료, pred.json에 병합.

---

## 평가 결과 (LLM-as-Judge, 3 evaluator)

### 전체 Accuracy

| 지표 | 값 |
|------|----|
| **GraphRAG Accuracy** | **49.5%** (99/200) |
| GWM v0.4.6 (비교) | 81.0% (162/200) |
| LightRAG (비교) | 67.5% (135/200) |
| RAPTOR (비교) | 75.5% (151/200) |
| 차이 (vs GWM) | **-31.5%p** |

### Reasoning Type별

| reasoning_type | Accuracy | n |
|----------------|----------|---|
| factual | 38.6% | 70 |
| comparative | 49.2% | 65 |
| **judgment** | **61.5%** | 65 |

### Complexity별

| complexity | Accuracy | n |
|------------|----------|---|
| single_evidence | 50.0% | 50 |
| **multi_evidence** | **61.3%** | 75 |
| cross_document | 37.3% | 75 |

### Question Type별

| question_type | Accuracy | n |
|---------------|----------|---|
| **text_only** | **63.7%** | 80 |
| table_only | 42.0% | 50 |
| image_only | 26.7% | 30 |
| composite | 47.5% | 40 |

### Evaluator 세부

| Evaluator | O 판정 수 |
|-----------|-----------|
| Tonic (GPT-4-turbo, sim≥4) | - |
| MLflow sim (GPT-4o, ≥4) | - |
| MLflow corr (GPT-4o, ≥4) | - |
| Allganize (Claude Sonnet 4.5, ==1) | - |

### 분석

- **cross_document 37.3%**: 커뮤니티 기반 검색이 문서 간 연결 추론에 취약
- **image_only 26.7%**: 텍스트 추출 기반 인덱싱으로 이미지/그림 정보 손실
- **judgment 61.5%**: 커뮤니티 요약이 고레벨 판단형 질문에는 상대적으로 유효
- **인덱싱 비용 높음**: 사전 인덱싱에 LLM 다수 호출 필요 (GWM $0 대비 상당한 비용)
