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
| 요약 노드 수 | 624개 |
| 전체 트리 노드 | 4,046개 |
| 클러스터링 | UMAP(cosine, n_comp=10) + GMM(BIC, threshold=0.1), Global+Local 2단계 |
| 소요 시간 | **43.5분** (2,612초) |
| 인덱스 파일 | baseline_experiment/raptor/index/raptor_tree.json |

---

## 검색 설정

| 항목 | 값 |
|------|----|
| 검색 모드 | collapse_tree |
| Context token budget | 2,000 tokens |

---

## 추론

| 항목 | 값 |
|------|----|
| 문항 수 | 200개 |
| 에러 | 0건 |
| 소요 시간 | **6.7분** (402초) |

---

## 평가 결과 (LLM-as-Judge, 3 evaluator 전체)

### 전체 Accuracy

| 지표 | 값 |
|------|----|
| **RAPTOR Accuracy** | **75.5%** (151/200) |
| Ours (비교) | 81.0% (162/200) |
| 차이 | **-5.5%p** |

### Reasoning Type별

| reasoning_type | Accuracy | n |
|----------------|----------|---|
| factual | 62.9% | 70 |
| comparative | 72.3% | 65 |
| **judgment** | **92.3%** | 65 |

### Complexity별

| complexity | Accuracy | n |
|------------|----------|---|
| single_evidence | 74.0% | 50 |
| multi_evidence | **78.7%** | 75 |
| cross_document | 73.3% | 75 |

### Question Type별

| question_type | Accuracy | n |
|---------------|----------|---|
| **text_only** | **80.0%** | 80 |
| image_only | **80.0%** | 30 |
| composite | 72.5% | 40 |
| table_only | 68.0% | 50 |

### 9-Cell Matrix (reasoning x complexity)

| | single_evidence | multi_evidence | cross_document |
|---|---|---|---|
| **factual** | 60.0% | 72.0% | 53.3% |
| **comparative** | **93.3%** | 68.0% | 64.0% |
| **judgment** | **100.0%** | **96.0%** | **88.6%** |

### Evaluator 세부

| Evaluator | O 판정 수 | 비고 |
|-----------|-----------|------|
| Tonic (GPT-4-turbo, sim>=4) | 176/200 | |
| MLflow sim (GPT-4o, >=4) | 148/200 | |
| MLflow corr (GPT-4o, >=4) | 144/200 | |
| Allganize (Claude Sonnet 4.5, ==1) | 158/200 | 파싱 실패 0건 (지수 백오프 재시도 적용) |

---

## 특이사항

- **judgment 92.3%**: 고레벨 요약 노드가 규제 판단형 질문의 맥락을 잘 포착
- **factual 62.9%**: 요약 과정에서 구체적 수치·단위가 손실되는 구조적 약점
- **table_only 68.0%**: 표 내 수치가 요약 시 누락되는 경향
- Allganize 평가 에러 0건: 파싱 오류(`re.search` 적용) + 과부하 재시도(지수 백오프, 최대 5회) 적용
- 인덱싱 비용: ~$1.4 / 추론 비용: ~$0.6 / Judge 비용: ~$10
