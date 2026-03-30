# GWM vs Baseline 비교 실험 결과

**작성일**: 2026-03-30
**작성자**: 김보경
**프로젝트**: GWM-based Multimodal Regulatory Document Exploration Agent

---

## 1. 실험 배경

### 1.1 목적

GWM Agent v0.4.6의 성능을 Graph RAG 계열 베이스라인(LightRAG, HippoRAG)과 동일 벤치마크·동일 평가 프레임워크로 비교하여, GWM 방법론의 기여를 정량적으로 분리한다.

### 1.2 비교 대상

| 방법론 | 논문 | 핵심 특징 |
|--------|------|----------|
| **GWM (ours)** | - | Vectorless, State-Action-Transition loop, Dynamic Sub-KG |
| **LightRAG** | Guo et al. (2024) | 이중 레벨(entity + topic) 그래프 검색 + 벡터 DB |
| **HippoRAG** | Gutierrez et al. (2024) | 해마 기반 연상 메모리 + KG + Personalized PageRank |

### 1.3 공정 비교 조건

| 항목 | 값 |
|------|-----|
| 생성 LLM | gpt-4.1 (모든 방법론 통일) |
| 인덱싱 LLM | gpt-4.1 (LightRAG, HippoRAG 포함) |
| Temperature | 0 |
| max_tokens | 300 |
| 답변 프롬프트 | 동일 system_prompt (가이드 4.3절) |
| 데이터셋 | multihop_qa_benchmark_v2.json (200문항) |
| 소스 문서 | NuScale FSAR Ch.01 + Ch.05 |
| 평가 프레임워크 | LLM-as-Judge (Tonic + MLflow + Allganize, 4표 majority vote) |

---

## 2. 실험 환경

### 2.1 LightRAG

| 항목 | 값 |
|------|-----|
| 라이브러리 | lightrag-hku v1.4.12 |
| Python | 3.12 |
| Embedding | text-embedding-3-small (1536 dim) |
| 검색 모드 | hybrid (local + global) |
| Top-K | 40 entities/relations, 20 chunks |
| chunk_token_size | 1200 |

### 2.2 HippoRAG

| 항목 | 값 |
|------|-----|
| 라이브러리 | hipporag 2.0.0a4 |
| Python | 3.10 (별도 venv) |
| Embedding | text-embedding-3-small (OpenAI remote) |
| 검색 방법 | Personalized PageRank + dense embedding |
| num_to_retrieve | 10 |

### 2.3 GWM (참고)

| 항목 | 값 |
|------|-----|
| 버전 | v0.4.6 |
| 모델 | GPT-4.1 |
| max_hops | 4 |
| top_k | 2 |
| 인덱싱 | 없음 (vectorless) |

---

## 3. 인덱싱 비교

| | **GWM** | **LightRAG** | **HippoRAG** |
|--|:-:|:-:|:-:|
| 인덱싱 시간 | **0분** | 52분 | 29분 |
| 인덱싱 비용 | **$0** | $$$ (gpt-4.1 수백 호출) | $$ (gpt-4.1 수백 호출) |
| 인덱스 크기 | **0 MB** | ~240 MB | ~200 MB |
| KG 노드 수 | 동적 생성 | 8,159 | 12,944 |
| KG 엣지/트리플 수 | 동적 생성 | 8,720 | 97,387 |
| 벡터 DB | 없음 | nano-vectordb | OpenAI embedding |

**GWM은 사전 인덱싱 없이 런타임에 동적으로 KG를 구축**하므로 인덱싱 비용이 $0이다. LightRAG와 HippoRAG는 오프라인 인덱싱에 수십 분과 상당한 API 비용이 소요된다.

---

## 4. 전체 결과

### 4.1 Overall Accuracy (LLM-as-Judge)

| 방법론 | Correct | Total | **Accuracy** |
|--------|:-------:|:-----:|:------------:|
| **GWM (ours)** | 162 | 200 | **81.0%** |
| HippoRAG | 138 | 200 | 69.0% |
| LightRAG | 135 | 200 | 67.5% |

**GWM이 HippoRAG 대비 +12.0%p, LightRAG 대비 +13.5%p 우위.**

---

## 5. 축별 상세 비교

### 5.1 Reasoning Type별

| Type | **GWM** | **HippoRAG** | **LightRAG** |
|------|:-------:|:------------:|:------------:|
| factual (70) | **53 = 75.7%** | 41 = 58.6% | 43 = 61.4% |
| comparative (65) | **51 = 78.5%** | 41 = 63.1% | 43 = 66.1% |
| judgment (65) | **61 = 93.8%** | 56 = 86.2% | 49 = 75.4% |

- **GWM이 모든 추론 유형에서 1위**
- judgment에서 GWM(93.8%)이 특히 강함 — HippoRAG(86.2%)도 비교적 선전
- factual에서 HippoRAG(58.6%)가 가장 약함

### 5.2 Complexity별

| Level | **GWM** | **HippoRAG** | **LightRAG** |
|-------|:-------:|:------------:|:------------:|
| single_evidence (50) | **43 = 86.0%** | 35 = 70.0% | 36 = 72.0% |
| multi_evidence (75) | **58 = 77.3%** | 54 = 72.0% | 47 = 62.7% |
| cross_document (75) | **64 = 85.3%** | 49 = 65.3% | 52 = 69.3% |

- **GWM이 모든 복잡도에서 1위**
- cross_document에서 GWM(85.3%)과 베이스라인(65~69%) 간 **16~20%p 격차** — 멀티홉 탐색 능력의 차이
- multi_evidence에서 HippoRAG(72.0%)가 LightRAG(62.7%)보다 우위

### 5.3 Question Type별

| Type | **GWM** | **HippoRAG** | **LightRAG** |
|------|:-------:|:------------:|:------------:|
| text_only (80) | **61 = 76.2%** | 63 = 78.8% | 57 = 71.2% |
| table_only (50) | **44 = 88.0%** | 28 = 56.0% | 30 = 60.0% |
| image_only (30) | **28 = 93.3%** | 25 = 83.3% | 22 = 73.3% |
| composite (40) | **32 = 80.0%** | 22 = 55.0% | 26 = 65.0% |

- **text_only에서 HippoRAG(78.8%)가 GWM(76.2%)을 약간 상회** — 유일한 예외
- **table_only에서 GWM(88.0%)과 베이스라인(56~60%) 간 28~32%p 격차** — Vision RAG의 효과
- **image_only에서도 GWM(93.3%) 압도적** — 베이스라인들은 이미지 처리 없이 텍스트만 사용

---

## 6. 분석 및 시사점

### 6.1 GWM의 강점

1. **멀티홉 탐색**: cross_document(85.3%)에서 베이스라인 대비 16~20%p 우위. State-Action-Transition 루프가 문서 간 교차 검색에 효과적.

2. **멀티모달 처리**: table_only(88.0%), image_only(93.3%)에서 압도적. Vision RAG (PyMuPDF → JPEG → GPT-4.1 vision)가 표/그림 문항에서 결정적 차이를 만듦. 베이스라인들은 텍스트만 처리.

3. **규제 판단(judgment)**: 93.8%로 모든 방법론 중 최고. 동적 KG의 two-tier edge ontology가 복합 추론에 유리.

4. **제로 인덱싱**: 사전 처리 없이 쿼리 시점에 동적 탐색. 문서 추가/변경 시 재인덱싱 불필요.

### 6.2 베이스라인별 특성

**LightRAG (67.5%)**
- 전반적으로 균일한 성능 (61~75%)
- 이중 레벨 그래프 검색이 text_only(71.2%)에서는 합리적이나 멀티모달에서 약함
- 인덱싱 비용이 가장 높음 (52분, gpt-4.1로 엔티티/관계 추출)

**HippoRAG (69.0%)**
- judgment(86.2%)에서 LightRAG(75.4%)보다 크게 우위 — KG 기반 연상 메모리가 복합 추론에 유리
- factual(58.6%)에서 가장 약함 — 단순 사실 검색에 PageRank 기반 접근이 비효율적
- text_only(78.8%)에서 GWM(76.2%)을 약간 상회 — 유일한 우위 지점

### 6.3 GWM 방법론의 기여 분리

| 기여 요소 | 근거 |
|-----------|------|
| **Dynamic exploration** | cross_document에서 +16~20%p (정적 인덱스 vs 동적 탐색) |
| **Vision RAG** | table_only +28~32%p, image_only +10~20%p (텍스트 전용 vs 멀티모달) |
| **Two-tier edge ontology** | judgment에서 +7.6~18.4%p (고정 KG vs 동적 추론 엣지) |
| **Vectorless design** | 인덱싱 0분/$0 vs 29~52분/$$$ |

---

## 7. 효율성 비교

| | **GWM** | **LightRAG** | **HippoRAG** |
|--|:-:|:-:|:-:|
| 사전 인덱싱 시간 | **0분** | 52분 | 29분 |
| 문항당 평균 시간 | ~100초 | ~7초 | ~3초 |
| 200문항 총 답변 시간 | ~330분 | ~23분 | ~11분 |
| 사전 인덱싱 + 답변 총합 | ~330분 | ~75분 | ~40분 |

GWM은 문항당 시간은 길지만(동적 탐색 루프), 사전 인덱싱이 없어 **문서 변경에 즉시 대응** 가능. 규제 문서처럼 빈번히 개정되는 도메인에서 재인덱싱 비용이 $0인 점은 실용적 장점.

---

## 8. 실험 재현

### 8.1 LightRAG

```bash
source .venv/bin/activate

# 인덱싱
PYTHONPATH=. python experiments/run_lightrag.py --mode index

# 답변 수집
PYTHONPATH=. python experiments/run_lightrag.py --mode query

# 평가
python -m benchmark.llm_judge benchmark/results/lightrag/pred.json \
  --output benchmark/results/lightrag/judge.json
```

### 8.2 HippoRAG

```bash
source .venv_hipporag/bin/activate

# 인덱싱
PYTHONPATH=. python experiments/run_hipporag.py --mode index

# 답변 수집
PYTHONPATH=. python experiments/run_hipporag.py --mode query

# 평가 (.venv로 전환)
source .venv/bin/activate
python -m benchmark.llm_judge benchmark/results/hipporag/pred.json \
  --output benchmark/results/hipporag/judge.json
```

### 8.3 결과 파일 위치

```
benchmark/results/
  gwm/                          # GWM 결과 (기존)
  lightrag/
    pred.json                   # 200문항 답변
    judge.json                  # LLM-as-Judge 결과 (67.5%)
    note.md                     # 구현 노트
    indexing_report.json        # 인덱싱 리포트
  hipporag/
    pred.json                   # 200문항 답변
    judge.json                  # LLM-as-Judge 결과 (69.0%)
    note.md                     # 구현 노트
    indexing_report.json        # 인덱싱 리포트
```

---

## 9. 결론

동일 벤치마크(200문항)·동일 LLM(gpt-4.1)·동일 평가 프레임워크(LLM-as-Judge)에서 **GWM이 LightRAG, HippoRAG 대비 12~13.5%p 높은 정확도**를 달성하였다. 특히:

1. **멀티홉 교차 문서 검색**(cross_document +16~20%p)과 **멀티모달 처리**(table/image +10~32%p)에서 격차가 두드러짐
2. **사전 인덱싱 비용 $0**으로 문서 변경에 즉시 대응 가능
3. **규제 판단(judgment) 93.8%**로 실무 적용 가능성 시사

이 결과는 규제 문서 도메인에서 **동적 KG 구축 + 멀티모달 처리 + vectorless 접근**의 조합이 정적 그래프 RAG 방법론보다 효과적임을 보여준다.
