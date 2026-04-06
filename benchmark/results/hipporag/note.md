# HippoRAG Baseline 구현 노트

## 환경
- LLM: gpt-4.1 (OpenIE + 생성)
- Embedding: text-embedding-3-small (OpenAI remote, embedding_base_url)
- Temperature: 0
- max_tokens: 300
- 라이브러리: hipporag 2.0.0a4
- Python: 3.10 (.venv_hipporag, 별도 가상환경)

## 인덱싱
- 방법: PDF → PyMuPDF 텍스트 추출 → 1000자 단위 청크 → HippoRAG 인덱싱 (OpenIE → KG 구축 + Personalized PageRank)
- 소스: NuScale FSAR Ch.01 (765 passages) + Ch.05 (315 passages) = 1,080 passages
- 소요 시간: **29.1분**
- KG 규모: 12,944 nodes (11,864 phrase + 1,080 passage), 97,387 triples
- 추출 트리플: 12,456개
- 동의어 트리플: 67,218개

## 검색 설정
- 검색 방법: Personalized PageRank over KG + dense embedding similarity
- num_to_retrieve: 10
- 문항당 평균 ~3초 (LightRAG보다 빠름)

## 답변 생성
- system_prompt: 가이드 4.3절 동일
- HippoRAG retrieve → context 추출 → gpt-4.1 답변 생성

## 결과 (재실험, retrieved_contexts 포함)
- **LLM-as-Judge Accuracy: 70.5% (141/200)**
- factual: 62.9% (44/70)
- comparative: 63.1% (41/65)
- judgment: 86.2% (56/65)
- single_evidence: 74.0% (37/50)
- multi_evidence: 69.3% (52/75)
- cross_document: 69.3% (52/75)
- text_only: 78.8%, table_only: 64.0%, image_only: 73.3%, composite: 60.0%

### 이전 결과 (v1, retrieved_contexts 미포함)
- LLM-as-Judge Accuracy: 69.0% (138/200)

## 변경사항 (재실험)
- `sol.docs`로 개별 passage 10개를 `retrieved_contexts`에 리스트로 저장
- 이전에는 `str(sol)` fallback으로 전체를 하나의 문자열로 저장했음
- retrieved_contexts 저장으로 RAGAs 평가 가능

## 특이사항
- vllm 의존성: Mac(no CUDA)에서 설치 불가 → stub 모듈로 우회 (OpenAI API만 사용하므로 문제 없음)
- multiprocessing.Manager() macOS 이슈: EmbeddingCache 클래스에서 클래스 레벨 Manager() 호출 → 일반 dict로 패치
- Python 3.10 필요 (기존 프로젝트 3.12와 호환 안 됨) → 별도 venv 생성
- openai 핀 버전(1.91.1) 충돌 방지를 위해 --no-deps 설치 + 수동 의존성 관리
- judgment 유형에서 86.2%로 가장 높은 성능 (KG 기반 연상 메모리가 복합 추론에 유리)
- factual 유형에서 62.9%로 가장 낮음 (단순 사실 검색에 약함)

## 스크립트
- `experiments/run_hipporag.py` (인덱싱 + 답변 수집 통합)
