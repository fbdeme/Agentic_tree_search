# RAPTOR Baseline — 구현 가이드

> 논문: Sarthi et al. (2024) "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval"
> 브랜치: `baseline/raptor`

---

## 1. 전체 플로우

```
[PDF 2개]
    │  pdf_extractor.py
    ▼
[Level-0 청크]  100 tokens, 문장 경계 존중, ~3,400개 (Ch.01: ~2,543 / Ch.05: ~879)
    │  embeddings.py  →  text-embedding-3-small
    ▼
[임베딩]  (n, 1536)
    │  clustering.py  →  2단계 UMAP+GMM
    ▼
[클러스터]  Global (n_neighbors=√n) → Local (n_neighbors=10), cosine, GMM threshold=0.1
    │  summarizer.py  →  gpt-4.1 요약
    ▼
[Level-1 요약 노드]
    │  ↑ 위 과정을 최대 3레벨까지 반복
    ▼
[RAPTOR Tree JSON]  baseline_experiment/raptor/index/raptor_tree.json

─────────────── 인덱싱 끝 / 추론 시작 ───────────────

[질문 200개]  multihop_qa_benchmark_v2.json
    │  retriever.py  →  질문 임베딩 + collapse_tree 검색
    ▼
[컨텍스트]  전 레벨 노드 코사인 유사도 정렬 → 2,000 token 예산까지 채움
    │  gpt-4.1  system_prompt (our agent 동일)
    ▼
[pred.json]  baseline_experiment/results/raptor/pred.json

    │  benchmark/llm_judge.py
    ▼
[judge.json]  baseline_experiment/results/raptor/judge.json
```

---

## 2. 파라미터 설정

| 항목 | 값 | 근거 |
|------|----|------|
| Chunk size | **100 tokens** | 논문 §3 원문 |
| Embedding model | text-embedding-3-small | 논문 원본은 SentenceTransformer; OpenAI 통일 |
| UMAP n_components | 10 | 논문 원본 |
| UMAP n_neighbors (global) | `int((n−1)^0.5)` | 논문 `cluster_utils.py` 원본 |
| UMAP n_neighbors (local) | 10 | 논문 원본 고정값 |
| UMAP metric | cosine | 논문 원본 |
| GMM threshold | **0.1** | 논문 `GMM_THRES=0.1` 원본 |
| Tree max levels | 3 | 논문: 수렴까지 재귀 → 실용적 상한 |
| Retrieval mode | **collapse_tree** | 논문 실험에서 tree_traversal보다 우위 |
| Context token budget | **2,000 tokens** | 논문 §4 실험 설정 |
| 생성 LLM | **gpt-4.1** | 가이드 §4.1 필수 통일 항목 |
| Temperature | **0** | 가이드 §4.1 |
| max_tokens | **300** | 가이드 §4.1 |
| System prompt | our agent `generate_answer()`와 동일 | 가이드 §4.3 |

---

## 3. 가이드(baseline_experiment_guide.md) 준수 현황

| 항목 | 준수 | 비고 |
|------|------|------|
| 생성 LLM = gpt-4.1 | ✅ | |
| Temperature = 0 | ✅ | |
| max_tokens = 300 | ✅ | |
| System prompt 동일 | ✅ | |
| 데이터셋 200문항 | ✅ | multihop_qa_benchmark_v2.json |
| 소스 PDF 동일 | ✅ | NuScale FSAR Ch.01 + Ch.05 |
| pred.json 스키마 (§5.1) | ✅ | id, question, expected_answer, generated_answer, reasoning_type, complexity, question_type |
| retrieved_contexts 포함 (§5.3) | ✅ | RAGAs 평가 가능 |
| 브랜치 baseline/raptor (§7.1) | ✅ | |
| 인덱싱 방법 자유 (§4.2) | ✅ | RAPTOR 고유 트리 구조 사용 |
| Embedding model 자유 (§4.2) | ✅ | text-embedding-3-small (note.md 기재) |

---

## 4. 실행 순서

```bash
# 0. 환경
source .venv/bin/activate            # Windows: .venv\Scripts\activate
# .env 파일 필요: OPENAI_API_KEY, ANTHROPIC_API_KEY

# 1. 인덱스 구축  (30~60분, ~$0.7)
python baseline_experiment/scripts/01_build_index.py

# 2. 파일럿 검증 (선택)
python baseline_experiment/scripts/02_run_inference.py --start 1 --end 10

# 3. 전체 추론  (~30분, ~$0.6)
python baseline_experiment/scripts/02_run_inference.py

# 4. LLM-as-Judge 평가  (~100분, ~$13)
python baseline_experiment/scripts/03_run_judge.py

# 5. 결과 확인
python baseline_experiment/scripts/03_run_judge.py --show-results
```

---

## 5. 출력 파일 위치

```
baseline_experiment/results/raptor/
    pred.json       ← 200문항 답변 (실험 중 10문항마다 자동 저장)
    judge.json      ← LLM-as-Judge 평가 결과

benchmark/results/raptor/
    note.md         ← 구현 노트 (실험 후 수치 채워넣기)
```

---

## 6. 논문 대비 의도적 차이

| 항목 | 논문 원본 | 이 구현 | 이유 |
|------|-----------|---------|------|
| Embedding 모델 | multi-qa-mpnet-base-cos-v1 | text-embedding-3-small | OpenAI 생태계 통일 (가이드 §4.2 허용) |
| 생성 LLM | GPT-4 (논문 당시) | gpt-4.1 | 가이드 §4.1 필수 |
| 컨텍스트 길이 | 2,000 tokens | 2,000 tokens | 동일 |
| Tree max levels | 무제한 (수렴까지) | 3 | 실용적 상한, 원 논문도 3레벨 실험 |
