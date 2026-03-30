# LightRAG Baseline 구현 노트

## 환경
- LLM: gpt-4.1 (인덱싱 + 생성 모두)
- Embedding: text-embedding-3-small (1536 dim)
- Temperature: 0
- max_tokens: 300
- 라이브러리: lightrag-hku v1.4.12
- Python: 3.12 (.venv)

## 인덱싱
- 방법: PDF → PyMuPDF 텍스트 추출 → LightRAG 그래프 인덱싱 (엔티티/관계 추출 + 벡터 DB)
- 소스: NuScale FSAR Ch.01 (778,239 chars) + Ch.05 (318,787 chars) = 1,097,026 chars
- 청크 수: Ch.01 194개 + Ch.05 72개 = 266개
- 소요 시간: Ch.01 36분 + Ch.05 16분 = **총 52분**
- 인덱스 크기: ~240MB (엔티티 벡터 98MB, 관계 벡터 105MB, KG 그래프 9.8MB 등)
- KG 규모: 8,159 nodes, 8,720 edges

## 검색 설정
- 검색 모드: hybrid (local + global)
- Top-K: 40 entities/relations, 20 chunks
- chunk_token_size: 1200
- chunk_overlap_token_size: 100
- entity_extract_max_gleaning: 1
- llm_model_max_async: 4

## 답변 생성
- system_prompt: 가이드 4.3절 동일
- 검색 → gpt-4.1에 context 전달 → 답변 생성
- 문항당 평균 ~7초

## 결과
- **LLM-as-Judge Accuracy: 67.5% (135/200)**
- factual: 61.4% (43/70)
- comparative: 66.1% (43/65)
- judgment: 75.4% (49/65)
- single_evidence: 72.0% (36/50)
- multi_evidence: 62.7% (47/75)
- cross_document: 69.3% (52/75)
- text_only: 71.2%, table_only: 60.0%, image_only: 73.3%, composite: 65.0%

## 특이사항
- `openai_complete_if_cache()`의 `model` 인자를 `functools.partial`로 positional binding 해야 함 (LightRAG 내부 호출 규약)
- `ainsert()`는 문서를 enqueue만 하고 백그라운드 파이프라인에서 처리 — 스크립트 종료 전 파이프라인 완료 대기 필요
- 엔티티 추출 후 관계 요약(LLMmrg) 단계가 오래 걸림 (엔티티 수천 개)
- 인덱싱에 gpt-4.1 사용 시 비용이 상당 (LightRAG 방법론 특성)

## 스크립트
- `experiments/run_lightrag.py` (인덱싱 + 답변 수집 통합)
