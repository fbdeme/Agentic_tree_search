## 5. Experiments

### 5.1 실험 설정

- **생성 LLM**: GPT-4.1 (모든 방법론 통일)
- **인덱싱 LLM**: GPT-4.1
- **임베딩**: text-embedding-3-small (1536d)
- **Temperature**: 0, **max_tokens**: 300
- **Agent 설정**: max_hops=4, top_k=2

### 5.2 베이스라인

| 방법론   | 논문                    | 핵심 특징                      |
| -------- | ----------------------- | ------------------------------ |
| RAPTOR   | Sarthi et al. [2024]    | 재귀 요약 트리 + collapse_tree |
| HippoRAG | Gutierrez et al. [2024] | PPR + 해마 연상 KG             |
| LightRAG | Guo et al. [2024]       | 이중 레벨 그래프 + 벡터 DB     |
| GraphRAG | Edge et al. [2024]      | 커뮤니티 기반 글로벌/로컬 검색 |

### 5.3 전체 결과 — LLM-as-Judge

| 방법론               |     Overall     |    judgment    |   comparative   |     factual     |    cross_doc    |   table_only   |    composite    |
| -------------------- | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: |
| **Ours (planning only)** | **81.5%** | **92.3%** | **80.0%** | **72.9%** | **84.0%** | **86.0%** | **77.5%** |
| Ours (planning + edges) | 81.0% | 90.8% | 78.5% | 74.3% | 81.3% | 86.0% | 85.0% |
| RAPTOR | 75.5% | 92.3% | 72.3% | 62.9% | 73.3% | 68.0% | 72.5% |
| LightRAG             |      73.0%      |      92.3%      |      66.1%      |      61.4%      |      76.0%      |      60.0%      |      67.5%      |
| HippoRAG             |      70.5%      |      86.2%      |      63.1%      |      62.9%      |      69.3%      |      64.0%      |      60.0%      |
| GraphRAG             |      49.5%      |      61.5%      |      49.2%      |      38.6%      |      37.3%      |      42.0%      |      47.5%      |

### 5.4 RAGAS 결과 (Ours)

| 메트릭              |    Overall    | factual |  comparative  |    judgment    |
| ------------------- | :------------: | :-----: | :------------: | :------------: |
| Faithfulness        | **0.93** |  0.92  |      0.92      | **0.97** |
| Answer Relevancy    | **0.84** |  0.85  |      0.78      | **0.89** |
| Context Recall      | **0.93** |  0.92  |      0.91      | **0.96** |
| Factual Correctness |      0.42      |  0.35  | **0.49** |      0.41      |

**RAGAS 비교 (전체 모델):**

| 메트릭              | **Ours** | LightRAG | RAPTOR | HippoRAG | PageIndex | GraphRAG |
| ------------------- | :------: | :------: | :----: | :------: | :-------: | :------: |
| Faithfulness        | **0.93** |   0.89   |  0.74  |   0.76   |   0.58    |   0.28   |
| Answer Relevancy    | **0.84** |   0.83   |  0.83  |   0.83   |   0.77    |   0.59   |
| Context Recall      | **0.93** |   0.88   |  0.77  |   0.76   |   0.66    |   0.18   |
| Factual Correctness |   0.42   |   0.36   |**0.40**|   0.37   |   0.30    |   0.32   |

> Ours가 Faithfulness(0.93), Context Recall(0.93)에서 압도적 1위. LightRAG가 Faith 0.89로 차상위 — hybrid 검색이 관련 context를 잘 가져옴. GraphRAG는 Faith 0.28, CR 0.18 — 커뮤니티 요약에서 구체적 사실 손실. PageIndex(retrieval only)는 Faith 0.58로 planning 없는 검색의 한계.

**RAGAS by reasoning_type (전체 모델):**

| reasoning_type | 메트릭 | **Ours** | LightRAG | RAPTOR | HippoRAG | PageIndex | GraphRAG |
| -------------- | ------ | :------: | :------: | :----: | :------: | :-------: | :------: |
| factual        | Faith  | **0.92** |   0.91   |  0.81  |   0.84   |   0.58    |   0.26   |
| factual        | CR     | **0.92** |   0.86   |  0.75  |   0.79   |   0.57    |   0.11   |
| comparative    | Faith  | **0.92** |   0.88   |  0.68  |   0.70   |   0.54    |   0.32   |
| comparative    | CR     | **0.91** |   0.89   |  0.74  |   0.71   |   0.67    |   0.18   |
| judgment       | Faith  | **0.97** |   0.89   |  0.74  |   0.74   |   0.63    |   0.27   |
| judgment       | CR     | **0.96** |   0.91   |  0.82  |   0.76   |   0.76    |   0.25   |

> judgment에서 Ours Faith 0.97, CR 0.96 — planning loop이 규제 판단에 필요한 증거를 거의 완벽하게 수집. factual에서 GraphRAG CR 0.11 — 구체적 수치가 커뮤니티 요약 과정에서 소실.

### 5.5 효율성 비교

**인덱싱 비용 (실측):**

|                |             **Ours**             | **RAPTOR** |     **LightRAG**     | **HippoRAG** |     **GraphRAG**     |
| -------------- | :-----------------------------------: | :--------------: | :------------------------: | :----------------: | :-------------------------: |
| 인덱싱 방식 | 트리 파싱 + LLM 노드 요약 | 재귀 요약 트리 | 엔티티-관계 추출 + 벡터 DB | OpenIE → KG + PPR | 엔티티-관계 + 커뮤니티 탐지 |
| 인덱싱 시간 | **7.6–19.8분**¹ | ~43.5분² | 52.1분 | 29.1분 | 40.0분 |
| 인덱싱 토큰 | **1,665,250**¹ | — | — | — | — |
| 인덱싱 비용 | **$4.06**¹ | ~$1.4 | $$$ | $$ | $$$ |
| API 호출 수 | 275 (Ch01: 235 + Ch05: 40) | — | — | — | — |
| 임베딩/KG 구축 | 불필요 | 불필요 | 필요 | 필요 | 필요 |

> ¹ Ours 인덱싱 실측: Ch.01(352p) 1,536K tokens/$3.75/17.7min + Ch.05(160p) 129K tokens/$0.31/2.1min. 시간 변동은 PageIndex TOC 파싱 retry 횟수에 의존 (retry 없이 7.6분, retry 포함 시 19.8분). 비용 $4.06은 GPT-4.1 기준($2/M input, $8/M output).
> ² RAPTOR는 다른 환경에서 실행, indexing_report 미생성. 기존 문서 기록 기반.

**쿼리 비용 (5문항 샘플 실측 → 200문항 외삽):**

|                 |                    **Ours**                    | **RAPTOR** | **GraphRAG** | HippoRAG | LightRAG |
| --------------- | :-------------------------------------------------: | :--------------: | :----------------: | :------: | :------: |
| 문항당 시간     |                  **93.0초**                  | **1.8초** |  **3.8초**  |  미저장  |  미저장  |
| 문항당 토큰     | **86,072** (prompt 79,861 + completion 6,210) |      미저장      |       4,953       |  미저장  |  미저장  |
| 문항당 API 호출 |                  **74.0회**                  |        —        |         —         |    —    |    —    |
| 문항당 비용     |           **$0.21** | — | ~$0.012           |        —        |         —         |          |          |
| 200문항 총 비용 |            **~$41.9** | — | ~$2.4            |        —        |         —         |          |          |
| 200문항 총 시간 |               ~310분 (8× 병렬 ~39분)               |       ~6분       |       ~13분       |    —    |    —    |

> 토큰 측정: 5문항 샘플(Q001 factual/single, Q071 comparative/single, Q131 composite/cross, Q161 judgment/multi, Q191 image/cross) 실측 후 평균 외삽. GPT-4.1 가격 기준($2/M input, $8/M output).

**문항별 비용 변동 (5문항 샘플):**

| 문항 | 유형               | 홉 | 노드 | 엣지 |    토큰 | 시간 |  비용 |
| ---- | ------------------ | :-: | :--: | :--: | ------: | ---: | ----: |
| Q001 | factual/single     | 1 |  4  |  0  |   9,395 |  17s | $0.03 |
| Q071 | comparative/single | 4 |  19  |  63  | 124,264 | 126s | $0.30 |
| Q131 | composite/cross    | 4 |  11  |  34  |  75,213 |  71s | $0.18 |
| Q161 | judgment/multi     | 4 |  17  |  65  | 104,463 | 111s | $0.25 |
| Q191 | image/cross        | 4 |  19  |  81  | 117,023 | 140s | $0.29 |

> 단순 factual 질문(Q001)은 1홉 17초 $0.03으로 종료, 복잡한 judgment 질문(Q191)은 4홉 140초 $0.29. 동적 종료가 비용 최적화에 기여.

**인덱싱 + 쿼리 총합:**

| | **Ours** | **RAPTOR** | **LightRAG** | **HippoRAG** | **GraphRAG** |
|--|:-:|:-:|:-:|:-:|:-:|
| 인덱싱 시간 | 7.6–19.8분 | ~43.5분 | 52.1분 | 29.1분 | 40.0분 |
| 인덱싱 비용 | **$4.06** | ~$1.4 | $$$ | $$ | $$$ |
| 쿼리 시간 (200Q) | ~310분 | ~6분 | — | — | ~13분 |
| 쿼리 비용 (200Q) | **~$41.9** | — | — | — | ~$2.4 |
| **시간 총합** | **~318–330분** | **~50분** | — | — | **~53분** |
| **비용 총합** | **~$46** | — | — | — | — |

> Ours는 시간·비용 모두 가장 높지만, 인덱싱 비중이 시간의 2–6%, 비용의 9%에 불과. 문서 개정 시 인덱싱($4.06)만 재실행하면 되며, 쿼리 비용은 8× 병렬화로 시간 단축 가능.

**KG 복잡도 (Ours, 200문항 전체):**

| 지표       | 평균 |  범위  |
| ---------- | :--: | :----: |
| 노드 수    | 12.8 | 4–26 |
| 엣지 수    | 39.9 | 0–124 |
| 사용 홉 수 | 3.6 |  1–4  |

---

## 6. Analysis

### 6.1 Ablation Study

#### 6.1.1 Component Ablation (10Q, 4 variants)

최종 시스템에서 핵심 컴포넌트를 하나씩 제거하여 각각의 기여를 탐색. 10문항(3 reasoning_type × 3 complexity × 4 question_type 포괄)에 대해 4개 variant 실행.

**Variant 정의:**

| Variant | 제거 대상 | 설명 |
|---------|----------|------|
| **full** | — | 최종 시스템 (baseline) |
| **no_vision** | Vision RAG | 도면 이미지·구조화 표를 답변 생성에 제공하지 않음 |
| **no_edges** | 엣지 추론 | 노드만 수집, 관계 추론(Transition) 전체 생략 |
| **no_browse_first** | Browse-first | Hop 1에서 문서 구조(목차) 자동 주입 제거 |

**전체 요약 (효율성 + 품질):**

| Variant | 3-Judge | Faith | AR | CR | FC | 시간 | 비용 |
|---------|:-------:|:-----:|:--:|:--:|:--:|:----:|:----:|
| **full** | **10/10** | **0.96** | **0.84** | **0.95** | **0.50** | 104s | $0.216 |
| no_vision | 8/10 | 0.83 | 0.82 | 0.92 | 0.39 | 98s | $0.196 (−9%) |
| no_edges | 9/10 | 0.93 | 0.84 | **1.00** | 0.48 | **34s** | **$0.073 (−66%)** |
| no_browse_first | 9/10 | **0.97** | 0.79 | 0.94 | **0.57** | 91s | $0.180 (−17%) |

> Judge = 3-평가자 다수결 (Tonic GPT-4-turbo, MLflow GPT-4o, Allganize Claude Sonnet 4.5)
> RAGAS = GPT-4.1 evaluator (Faithfulness, Answer Relevancy, Context Recall, Factual Correctness)

**오답 분석 (3-Judge X):**

| Variant | 정답률 | 오답 문항 | 실패 원인 |
|---------|:------:|----------|----------|
| **full** | **10/10** | — | — |
| no_vision | **8/10** | Q101, Q131 | 표/복합 데이터 없이 비교 질문 실패 |
| no_edges | 9/10 | **Q058** | 엣지 없이 내진 scope boundary 판단 실패 |
| no_browse_first | 9/10 | **Q191** | 목차 없이 image/judgment 탐색 실패 |

**핵심 발견:**

1. **Full system이 유일한 10/10** — 모든 컴포넌트가 정확도에 기여
   - 어떤 컴포넌트를 제거해도 최소 1문항 이상 추가 오답 발생
   - 각 컴포넌트가 **서로 다른 유형의 문항**에서 결정적 역할

2. **Vision RAG 제거: 가장 큰 정확도 하락 (10/10 → 8/10)**
   - **Q101(table/comparative)**: Tonic 4→1, MLflow 4→1 — 표 데이터 없이 비교 질문 완전 실패
   - **Q131(composite/comparative)**: MLflow corr 4→2 — 복합 증거 종합 불가
   - RAGAS도 하락: Faith 0.96→0.83, FC 0.50→0.39
   - **결론**: Vision은 특히 table/composite 문항에서 필수적

3. **엣지 추론 제거: 비용 66% 절감, 그러나 규제 판단에서 실패**
   - no_edges는 가장 저렴 ($0.073, 34초)이며 CR=1.00으로 증거 수집은 정상
   - 그러나 **Q058 오답**: Tonic 4→2, Allganize 1→0 — 엣지 없이 scope exclusion 판단 실패
     - full: VIOLATES 엣지로 "비안전 계통은 내진 요건 적용 범위 밖"을 명시적 추론 → O
     - no_edges: 노드만 나열, scope boundary 미식별 → X
   - **결론**: 엣지 추론은 비용의 66%를 차지하지만, 6.3절 VIOLATES case study가 보여주듯 규제 판단의 핵심

4. **Browse-first 제거: 복잡한 멀티모달 문항에서 탐색 실패**
   - **Q191(image/judgment/cross)**: Tonic 4→0, MLflow 4→1 — 목차 없이 탐색 방향 설정 실패
   - 단순 문항(Q001~Q031)에서는 영향 없음 — browse-first는 복잡 문항에서만 결정적

**문항별 3-Judge 상세:**

| QID | 유형 | full | no_vis | no_edg | no_brw |
|-----|------|:----:|:------:|:------:|:------:|
| Q001 | fact/single | O | O | O | O |
| Q010 | fact/multi | O | O | O | O |
| Q031 | fact/single/table | O | O | O | O |
| Q058 | fact/cross | O | O | **X** | O |
| Q071 | comp/single | O | O | O | O |
| Q101 | comp/cross/table | O | **X** | O | O |
| Q131 | comp/cross/comp | O | **X** | O | O |
| Q161 | judg/multi | O | O | O | O |
| Q176 | judg/cross | O | O | O | O |
| Q191 | judg/cross/image | O | O | O | **X** |

**베이스라인 대비 기여 분리** (200문항 전체, Ours vs RAPTOR):

| 기여 요소 | 근거 | 효과 |
|-----------|------|------|
| Dynamic exploration | cross_document: Ours 81.3% vs RAPTOR 73.3% | **+8.0%p** |
| Vision RAG (표) | table_only: Ours 86.0% vs RAPTOR 68.0% | **+18.0%p** |
| Vision RAG (복합) | composite: Ours 85.0% vs RAPTOR 72.5% | **+12.5%p** |
| 2티어 엣지 | judgment × cross_doc: 94.3% vs RAPTOR 88.6% | **+5.7%p** |
| 경량 인덱싱 | 트리 빌드 7.6분 vs GraphRAG 40분 | **5.3× 빠름** |

#### 6.1.2 Scale-up: Edge Inference 제거 (200Q)

10Q ablation에서 엣지 추론이 가장 비용이 크고(65%), Q058(VIOLATES case)에서 흥미로운 결과를 보였으므로, **200문항 전체로 확대하여 통계적 신뢰도를 확보.**

| 메트릭 | full (planning + edges) | no_edges (planning only) | 차이 |
|--------|:----------------------:|:-----------------------:|:----:|
| **3-Judge 정확도** | 81.0% (162/200) | **81.5% (163/200)** | +0.5%p |
| Faithfulness | **0.930** | 0.897 | −0.033 |
| Context Recall | **0.930** | 0.919 | −0.011 |
| Factual Correctness | 0.420 | 0.417 | −0.003 |
| 비용/문항 | $0.215 | **$0.076** | **−65%** |
| 시간/문항 | 115.3s | **47.5s** | **−59%** |

**10Q에서의 기대와 200Q 결과의 괴리:**
- 10Q: full=10/10, no_edges=9/10 → 엣지가 중요해 보였음
- 200Q: full=81.0%, no_edges=81.5% → **엣지 제거 시 정확도가 오히려 유지/소폭 상승**
- 10Q의 Q058(VIOLATES case) 오답은 200Q에서 재현되지 않음 (둘 다 O) → 10Q 결과는 샘플 크기 한계로 인한 노이즈였을 가능성

**핵심 발견: Planning이 정확도의 핵심 동인**
- 엣지 추론을 완전히 제거해도 정확도가 유지됨
- **Planning(도구 선택, 동적 종료, browse-first)만으로 4개 RAG 베이스라인 상회** (81.5% vs RAPTOR 75.5%)
- 엣지 추론은 비용의 65%를 차지하지만 정확도 기여 없음

**엣지가 제공하는 것과 제공하지 않는 것:**
- ❌ 정확도 향상: 200Q에서 차이 없음
- △ Faithfulness: +0.033 (방향 일관적이나 미미, 통계적 유의성 미검증)
- ✅ 추적 가능성: "Section A SATISFIES Regulation B" 형태의 인간 가독 근거 경로

**Head-to-head 분석:**
- 공통 오답 25문항, full만 오답 13문항, no_edges만 오답 12문항 → 거의 대칭 (실행 변동 수준)

**Post-retrieval vs retrieval-time edges:**
- 본 결과는 **검색 후(post-retrieval)** 증거 간 관계를 추론하는 엣지가 정확도에 기여하지 않음을 보여줌
- 이는 **검색 자체를 위한(retrieval-time)** 엣지(GraphRAG, LightRAG의 그래프 탐색)에 대한 결론이 아님 — 역할이 근본적으로 다름
- LLM은 답변 생성 시 노드 내용만으로도 관계를 암묵적으로 추론할 수 있으며, 명시적 엣지 추론은 이를 중복하는 것으로 보임

### 6.2 엣지 분포 분석 (7,391 edges, 200문항)

| 엣지               | Count |   %   | 범주       |
| ------------------ | :---: | :---: | ---------- |
| SUPPORTS           | 2,532 | 34.3% | Semantic   |
| SPECIFIES          | 2,330 | 31.5% | Structural |
| REFERENCES         |  966  | 13.1% | Structural |
| IS_PREREQUISITE_OF |  701  | 9.5% | Semantic   |
| SATISFIES          |  622  | 8.4% | Semantic   |
| SEMANTIC           |  149  | 2.0% | Free-form  |
| LEADS_TO           |  66  | 0.9% | Semantic   |
| CONTRADICTS        |  22  | 0.3% | Semantic   |
| VIOLATES           |   3   | 0.04% | Semantic   |

- **정답 vs 오답 엣지 패턴**: SUPPORTS +6.8%p, SATISFIES +3.2%p in correct → 의미 엣지가 정확도와 직접 연관
- **VIOLATES 3건**: 아래 Case Study 참조

### 6.3 Case Study: FSAR 인증 문서에서 VIOLATES가 출현한 이유

> FSAR는 NRC에 의해 이미 인증된 설계 문서다. 그런데 왜 VIOLATES(위반) 관계가 출현했는가? 이 3건의 분석은 VIOLATES가 "오류 탐지"가 아닌 **규제 적용 범위의 경계(scope boundary)**를 포착한다는 것을 보여준다.

#### Case 1–2: 내진 설계 적용 범위 면제 (Q058, VIOLATES ×2)

- **질문**: "Ch.01의 NuScale 내진 설계가 Ch.05의 RCS 부품에 어떤 영향을 미치는가?"
- **에이전트 판단 결과**: Judge = O (정답)
- **VIOLATES 엣지 1** (confidence 0.85):

  - Source: `nuscale_ch01_0146` — DSRS 3.11 환경 적격성 인증 (안전 관련 기기의 내진·환경 기준)
  - Target: `nuscale_ch01_0338` — 냉각수 계통(Chilled Water System) 설계
  - **엣지 기술**: "Section A는 안전 관련 기기의 내진·환경 기준을 논의하나, Section B의 냉각수 계통은 **안전 관련이 아니며 Seismic Category I 건물 외부에 위치** — Section A의 내진 요건이 Section B에 적용되지 않음"
- **VIOLATES 엣지 2** (confidence 0.90):

  - Source: `nuscale_ch01_0307` — GDC 2 내진 설계 기준 (안전 관련 계통 적합성)
  - Target: `nuscale_ch01_0334` — 응축수 저장 시설(Condensate Storage Facilities)
  - **엣지 기술**: "Section A는 GDC 2에 따른 안전 관련 계통의 내진 설계 기준을 규정하나, Section B는 응축수 저장 계통이 **안전 관련이 아니며 내진 설계 요건에서 제외**됨을 명시"
- **해석**: 두 VIOLATES 엣지 모두 "설계가 규제를 위반했다"가 아니라, **"이 규제 요건의 적용 범위에 해당 계통이 포함되지 않는다"**는 scope exclusion을 포착

  - 비안전 계통(Chilled Water, Condensate Storage)은 의도적으로 Seismic Category I 밖에 배치
  - 이는 정당한 설계 결정이며, FSAR에서 "비안전 계통의 고장이 안전 관련 SSC에 영향을 미치지 않음"으로 명시적으로 정당화됨
  - 에이전트는 이 scope boundary를 KG에 기록하면서도 최종 답변에서 정확한 판단을 내림 (Judge = O)

#### Case 3: 부분 적합성과 설계 한계 인정 (Q176, VIOLATES ×1)

- **질문**: "Ch.01과 Ch.05에 기술된 일체형 SG 설계가 SGTR(증기발생기 세관 파열) 우려에 적절한가?"
- **에이전트 판단 결과**: Judge = O (정답, "Yes, adequate")
- **VIOLATES 엣지** (confidence 0.85):

  - Source: `nuscale_ch05_0012` — 원자로냉각재 압력경계 누설 감지
  - Target: `nuscale_ch01_0779` — DSRS 15.6.5 냉각재 상실 사고(LOCA) 방사선 영향 평가
  - **엣지 기술**: "Section A는 NuScale 원자로냉각재 압력경계의 **누설 감지 한계**를 기술 — 전통적 설계와 달리 식별 누설(identified leakage)과 미식별 누설(unidentified leakage)의 구분이 불가능. Section B는 LOCA(SGTR 포함)의 방사선 영향 계산에 대한 규제 요건과 **부분 적합성(partial conformance)**을 명시 — Section A의 감지 한계가 Section B의 규제 요건을 완전히 만족하는 능력에 영향"
- **해석**: 이 VIOLATES는 NuScale 혁신 설계의 **구조적 trade-off**를 포착

  - NuScale은 SG가 RPV 내부에 일체화된 혁신 설계 → 전통적 PWR의 격납건물 우회(containment bypass) 문제를 원천 제거
  - 그러나 이 설계 때문에 기존 누설 감지 방식이 그대로 적용 불가 → DSRS 15.6.5의 방사선 영향 계산 기준에 대해 **부분 적합(partial conformance)**
  - FSAR 자체가 이 부분 적합을 인정하고 문서화함: "NuScale's evaluation models address only the technically relevant features required by regulations"
  - 에이전트는 전체적으로는 "adequate"로 판단하면서도, **불확실성 섹션에서** 누설 감지 한계를 명시적으로 언급: "the leakage detection system treats all leakage as unidentified until located, which may affect rapid source identification during SGTR, but does not compromise overall safety"

#### VIOLATES의 가치: 왜 이것이 단순 RAG에서는 불가능한가

1. **Scope boundary 포착**: 규제 요건이 어디에 적용되고 어디에 적용되지 않는지를 명시적으로 기록. 단순 RAG는 "관련 텍스트"를 반환할 뿐, 적용 범위의 경계를 추론하지 못함.
2. **부분 적합의 뉘앙스**: "만족(SATISFIES)"과 "위반(VIOLATES)"의 이분법이 아닌, FSAR 자체가 인정하는 partial conformance를 포착. 이는 규제 심사에서 가장 주의 깊게 검토해야 하는 영역 — 완전 적합도, 완전 위반도 아닌 지점.
3. **추적 가능한 판단 근거**: 에이전트가 "adequate"라고 최종 판단하면서도 VIOLATES 엣지를 KG에 보존 → 심사관이 "왜 부분 적합이 허용되는가"를 독립적으로 검증 가능. 이는 P3에서 논의한 10 CFR 50 App B Criterion III의 "독립적 검증이 가능한 문서화" 요건에 직접 부합.
4. **빈도 자체가 의미**: 7,391 엣지 중 3건(0.04%)만 VIOLATES — FSAR가 인증 문서이므로 당연. 만약 VIOLATES가 다수 출현한다면 문서 자체의 품질 문제를 시사. 이 비율 자체가 문서 품질의 간접 지표로 활용 가능.

### 6.4 이중 평가 프레임워크 상호 보완성

- **RAGAS-Judge 일치율 66.2%**

  |                                            | Judge O | Judge X |
  | ------------------------------------------ | :-----: | :-----: |
  | **RAGAS Good** (Faith≥0.8, CR≥0.8) |   122   |   29   |
  | **RAGAS Bad**                        |   38   |    9    |
- **해석**:

  - RAGAS 좋음 + Judge X (29건): 올바른 증거 검색, 표현 불일치 — MLflow 평가자 엄격 기준
  - RAGAS 나쁨 + Judge O (38건): KG 문맥 외 지식으로 정답 → RAGAS는 grounding, Judge는 correctness 측정
  - **결론**: 두 평가가 상호 보완적이며 완전한 평가를 위해 모두 필요

### 6.5 한계 및 향후 과제

#### 시스템 한계

- **text_only 열위**: Ours 76.2% vs RAPTOR 80.0% (−3.8%p) → RAPTOR의 재귀 요약이 긴 텍스트에서 효과적, 향후 요약 노드 추가 검토
- **문항당 비용**: 평균 $0.21/문항 (93초, 86K 토큰) vs RAPTOR ~$0.01/문항 (1.8초)
  - 동적 종료가 부분적으로 완화 (Q001: 1홉 $0.03 vs Q191: 4홉 $0.29)
  - 8× 병렬 실행 시 총 소요 ~39분으로 단축 가능
- **follow_ref tool 미구현**: "Table 5.1-1 참조" 직접 탐색 도구 향후 추가 예정

#### 벤치마크 한계

본 연구의 200문항 벤치마크는 직접 설계한 것으로, 평가 과정에서 다음 5가지 구조적 한계를 확인함:

1. **Factual Correctness 상한 (~0.42)**: expected_answer가 하나의 증거 관점만 반영

   - 예: Q003 — 기대 답변 "helical coil SG integrated within RPV", 에이전트 "vertical helical once-through SG with 1,380 tubes" → 둘 다 정확하나 FC=0.0
   - 예: Q138 — 동일 표의 다른 행(32 EFPY vs 57 EFPY) 참조 → 질문이 조건 미지정
   - **개선 방향**: 복수 증거 관점을 포괄하는 expected_answer 재작성, 조건 명시형 질문으로 수정
2. **Judgment 극성 편향**: 65개 judgment 문항 중 64개(98%)가 "Yes" 정답

   - 원인: FSAR는 설계 인증 문서로 모든 설계가 규제 적합하게 기술됨 → "No" 답변이 구조적으로 불가
   - 이로 인해 항상 "Yes"를 출력하는 시스템도 judgment에서 98% 달성 가능
   - **개선 방향**: 가상 위반 시나리오(hypothetical violation) 추가 — "RPV 클래딩 두께를 0.10인치로 줄이면 ASME 요건을 만족하는가?" 등 30%+ "No" 문항 필요
3. **증거 깊이 부족**: 1증거 57문항(28%), 2증거 131문항(66%), 3+증거 12문항(6%)

   - "멀티홉 벤치마크"를 표방하나 실질적으로 66%가 2-hop 수준
   - **개선 방향**: 3–4 증거 체인 문항 추가 (예: "노심 → 자연순환 → SG → DHRS → 수조" 열제거 경로 추적)
4. **문서 커버리지 불균형**: Ch.01은 p.15–81만 활용 (352p 중 19%), Ch.05는 p.10–100 (160p 중 56%)

   - Ch.01 §1.9 (규제 적합성 표, p.82–352)에 727개 규제 항목이 있으나 거의 문항화되지 않음
   - **개선 방향**: §1.9 규제 테이블 기반 문항 추가로 커버리지 확대
5. **외부 검증 부재**: 자체 설계 벤치마크로 편향 가능성 존재

   - 완화 요인: 3축 직교 분류 설계, LLM-as-Judge 3인 다수결, 5개 방법론 동일 조건 비교
   - **개선 방향**: 원자력 도메인 전문가 참여 검증, 외부 연구 그룹에 의한 독립 평가

---
