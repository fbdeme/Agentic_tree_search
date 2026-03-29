# RAPTOR Baseline Experiment

**RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval, Sarthi et al. 2024) baseline for the GWM benchmark comparison.

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
| System prompt | GWM `generate_answer()`와 동일 |

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

## RAPTOR 파라미터 조정

[raptor/config.py](raptor/config.py) 에서 조정:

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `CHUNK_SIZE` | 512 | 청크 토큰 크기 |
| `CHUNK_OVERLAP` | 50 | 청크 간 오버랩 토큰 |
| `EMBEDDING_MODEL` | text-embedding-3-small | 임베딩 모델 |
| `UMAP_N_COMPONENTS` | 10 | UMAP 목표 차원 |
| `GMM_MAX_CLUSTERS` | 50 | BIC 탐색 최대 k |
| `GMM_THRESHOLD` | 0.5 | Soft assignment 확률 임계값 |
| `MAX_LEVELS` | 3 | 트리 최대 레벨 |
| `RETRIEVAL_MODE` | collapse_tree | 검색 모드 |
| `TOP_K` | 5 | 검색 반환 노드 수 |

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
