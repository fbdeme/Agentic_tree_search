# Baseline Experiments

비교 모델 구현 코드 디렉토리. 각 방법론별 인덱싱/추론 스크립트가 포함되어 있습니다.
결과 파일은 `benchmark/results/{method}/`에 저장합니다 (가이드 Section 5.5 참조).

```
baseline_experiment/
├── graphrag/       # GraphRAG (Edge et al. 2024) — run_graphrag.py, settings.yaml
├── hipporag/       # HippoRAG (Gutierrez et al. 2024) — run_hipporag.py
├── lightrag/       # LightRAG (Guo et al. 2024) — run_lightrag.py
├── raptor/         # RAPTOR (Sarthi et al. 2024) — 알고리즘 구현 코드
└── scripts/        # RAPTOR 실행 스크립트 (01_build_index, 02_run_inference, 03_run_judge)
```

상세 가이드: `docs/baseline_experiment_guide.md`

---

아래는 RAPTOR 관련 상세 설명입니다.

## RAPTOR Baseline

**RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval, Sarthi et al. 2024) baseline for the benchmark comparison.

---

## 개요

NuScale FSAR Ch.01 + Ch.05 PDF를 RAPTOR 트리로 인덱싱한 후,
200문항 QA 벤치마크(`multihop_qa_benchmark_v2.json`)에 대해 답변을 수집합니다.
평가는 기존 `benchmark.llm_judge` 파이프라인을 그대로 사용합니다.

비교 공정성 규칙 (guide §4.1):
| 항목 | 값 |
|------|-----|
| 생성 LLM | `gpt-4.1` |
| Temperature | `0` |
| max_tokens | `300` |
| System prompt | our agent `generate_answer()`와 동일 |

---

## 디렉토리 구조

```
baseline_experiment/
├── raptor/
│   ├── config.py          # 경로·모델·파라미터 설정
│   ├── pdf_extractor.py   # PDF → 토큰 단위 텍스트 청크
│   ├── embeddings.py      # OpenAI 배치 임베딩
│   ├── clustering.py      # UMAP + GMM soft clustering
│   ├── summarizer.py      # 클러스터 요약 (gpt-4.1)
│   ├── tree_builder.py    # 재귀 트리 구축 + 직렬화
│   ├── retriever.py       # collapse_tree / tree_traversal 검색
│   └── pipeline.py        # 엔드투엔드 파이프라인
├── scripts/
│   ├── 01_build_index.py  # Step 1: 트리 인덱스 구축
│   ├── 02_run_inference.py # Step 2: 200문항 추론
│   └── 03_run_judge.py    # Step 3: LLM-as-Judge 평가
├── results/
│   └── raptor/            # pred.json, judge.json 저장 위치
└── requirements.txt
```

---

## 실행 방법

### 0. 환경 준비

```bash
# 프로젝트 루트에서
source .venv/bin/activate
pip install -r baseline_experiment/requirements.txt

# .env 확인 (OPENAI_API_KEY 필수)
cat .env
```

### Step 1 — 트리 인덱스 구축

```bash
python baseline_experiment/scripts/01_build_index.py
```

- PDF: `data/documents/NuScale FSAR Ch.01 (공개본).pdf` + `Ch.05`
- 출력: `baseline_experiment/raptor/index/raptor_tree.json`
- 예상 시간: 30~90분 (청크 수 × 클러스터링 + 요약 API 호출)

```bash
# PDF 위치를 직접 지정하는 경우
python baseline_experiment/scripts/01_build_index.py --pdf-dir /path/to/pdfs
```

### Step 2 — 추론 (200문항 답변 수집)

```bash
# 파일럿 (1~10번, 검증용)
python baseline_experiment/scripts/02_run_inference.py --start 1 --end 10

# 전체 200문항
python baseline_experiment/scripts/02_run_inference.py
```

- 출력: `baseline_experiment/results/raptor/pred.json`
- 10문항마다 자동 중간 저장

분할 실행 (병렬 가능):

```bash
python baseline_experiment/scripts/02_run_inference.py --start 1   --end 50  --output baseline_experiment/results/raptor/pred_1.json
python baseline_experiment/scripts/02_run_inference.py --start 51  --end 100 --output baseline_experiment/results/raptor/pred_2.json
python baseline_experiment/scripts/02_run_inference.py --start 101 --end 150 --output baseline_experiment/results/raptor/pred_3.json
python baseline_experiment/scripts/02_run_inference.py --start 151 --end 200 --output baseline_experiment/results/raptor/pred_4.json
```

### Step 3 — LLM-as-Judge 평가

```bash
python baseline_experiment/scripts/03_run_judge.py
```

- 입력: `baseline_experiment/results/raptor/pred.json`
- 출력: `baseline_experiment/results/raptor/judge.json`
- 예상 시간: ~100분 / 예상 비용: ~$13

결과 확인:

```bash
python baseline_experiment/scripts/03_run_judge.py --show-results
```

---

## RAPTOR 파라미터

[raptor/config.py](raptor/config.py) 에서 조정:

| 파라미터 | 값 | 근거 |
|----------|----|------|
| `CHUNK_SIZE` | **100** tokens | 논문 §3 원문 |
| `EMBEDDING_MODEL` | text-embedding-3-small | 논문 원본은 SentenceTransformer; OpenAI 통일 |
| `UMAP_N_COMPONENTS` | 10 | 논문 원본 |
| `UMAP_N_NEIGHBORS` (global) | `int((n−1)^0.5)` | 논문 `cluster_utils.py` 원본 |
| `UMAP_N_NEIGHBORS` (local) | 10 | 논문 원본 고정값 |
| `GMM_THRESHOLD` | **0.1** | 논문 `GMM_THRES=0.1` 원본 |
| `MAX_LEVELS` | 3 | 논문: 수렴까지 재귀 → 실용적 상한 |
| `RETRIEVAL_MODE` | collapse_tree | 논문 실험에서 tree_traversal보다 우위 |
| `CONTEXT_TOKEN_BUDGET` | **2,000** tokens | 논문 §4 실험 설정 |

---

## 실험 결과

> 실험일: 2026-03-30 · 브랜치: `baseline/raptor`

### 비용/효율 지표 (guide §9)

| 지표 | 값 |
|------|-----|
| 사전 인덱싱 시간 | **43.5분** (2,612초) |
| 사전 인덱싱 LLM 호출 | ~624회 (클러스터 요약, GPT-4.1) |
| 사전 인덱싱 비용 | **~$1.4** |
| 문항당 평균 시간 | **~2초** (402초 / 200문항) |
| 문항당 평균 LLM 호출 | **1회** (생성 1회, 검색은 embedding만) |
| 200문항 총 비용 | **~$0.6** |

---

### 전체 Accuracy

| Method | Accuracy | n |
|--------|:--------:|:-:|
| **Ours** (비교) | **81.0%** | 200 |
| **RAPTOR** | **75.5%** | 200 |
| Δ | −5.5%p | |

### Reasoning Type별

| reasoning_type | RAPTOR | Ours |
|----------------|:------:|:----------:|
| factual | 62.9% (44/70) | — |
| comparative | 72.3% (47/65) | — |
| **judgment** | **92.3%** (60/65) | **90.8%** |

### Complexity별

| complexity | RAPTOR | Ours |
|------------|:------:|:----------:|
| single_evidence | 74.0% (37/50) | — |
| multi_evidence | 78.7% (59/75) | — |
| cross_document | 73.3% (55/75) | **81.3%** |

### Question Type별

| question_type | RAPTOR | n |
|---------------|:------:|:-:|
| text_only | **80.0%** | 80 |
| image_only | **80.0%** | 30 |
| composite | 72.5% | 40 |
| table_only | 68.0% | 50 |

### 9-Cell Matrix (reasoning × complexity)

| | single_evidence | multi_evidence | cross_document |
|---|:---:|:---:|:---:|
| **factual** | 60.0% (18/30) | 72.0% (18/25) | 53.3% (8/15) |
| **comparative** | **93.3%** (14/15) | 68.0% (17/25) | 64.0% (16/25) |
| **judgment** | **100.0%** (5/5) | **96.0%** (24/25) | 88.6% (31/35) |

### Evaluator 세부

| Evaluator | 모델 | O 판정 | 기준 |
|-----------|------|:------:|------|
| Tonic | GPT-4-turbo | 176/200 | similarity ≥ 4 (0–5 scale) |
| MLflow similarity | GPT-4o | 148/200 | similarity ≥ 4 (1–5 scale) |
| MLflow correctness | GPT-4o | 144/200 | correctness ≥ 4 (1–5 scale) |
| Allganize | Claude Sonnet 4.5 | 158/200 | binary == 1 |

> Final vote: 4표 중 다수결 (동률 시 X 우선)
> 세부 결과: [`results/raptor/judge.json`](results/raptor/judge.json) · [`benchmark/results/raptor/note.md`](../benchmark/results/raptor/note.md)

---

## 결과 저장 위치

```
baseline_experiment/results/raptor/
    pred.json     ← 답변 파일 (필수)
    judge.json    ← 평가 결과 (필수)

benchmark/results/raptor/
    pred.json     ← benchmark 비교용 복사본
    judge.json
    note.md       ← 구현 노트
```

---

## 참고

- RAPTOR 논문: Sarthi et al. (2024) "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval"
- 원 구현: https://github.com/parthsarthi03/raptor
- 비교 가이드: `docs/baseline_experiment_guide.md`
