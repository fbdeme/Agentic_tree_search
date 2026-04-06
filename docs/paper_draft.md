# [초안] 규제 문서 멀티홉 탐색을 위한 LLM 기반 계획

> **상태**: 초안 (개조식 흐름 정리용)  
> **작성일**: 2026-04-03 (최종 수정: 2026-04-06)  
> **타겟**: LM4Plan @ ICML 2026 (마감 4/24)  
> **검증된 인용만 사용** — 미확인 인용은 ⚠️ 표시

---

## 논문 제목 (후보)

- **정식**: *LLM-Guided Planning for Multi-hop Regulatory Document Exploration*
- **대안 1**: *Document Exploration as Planning: LLM-Guided Information Gathering in Vectorless Tree Environments*
- **대안 2**: *Planning with LLMs in Information Environments: Multi-hop Reasoning for Nuclear Regulatory Documents*

---

## Abstract (초안)

- 핵발전소 안전 분석 보고서(FSAR) 심사는 수만 페이지에서 증거를 순차적으로 수집하고 규제 적합성을 판단하는 과정 → 본질적으로 **불확실한 정보 환경에서의 계획 문제(planning under uncertainty)**
- 기존 RAG 기반 시스템은 이 과정을 수동적 1회성 검색으로 환원 → 단일 hop 한계, 구조 파괴, 판단 부재
- **제안**: LLM이 벡터리스 문서 트리 환경에서 **정보 수집을 계획(plan)**하는 아키텍처
  - **Planning loop**: 상태 평가(Dynamic Sub-KG) → 행동 선택(browse/read/search) → 충분성 판단(동적 종료)의 반복
  - **모달리티 정렬**: 상태와 환경을 LLM의 네이티브 모달리티(텍스트)로 구축하여 계획 수립 가능하게 함
  - **Vision**: PDF 원본 도면/표를 GPT-4.1 vision으로 직접 해석
- **결과**: 200문항 멀티홉 벤치마크에서 LLM-as-Judge 81.5% — RAPTOR(75.5%), HippoRAG(69.0%), LightRAG(67.5%), GraphRAG(49.5%) 대비 최고; RAGAS Faithfulness 0.90
- **분석**: 200Q ablation에서 post-retrieval 엣지 추론(verification)은 정확도에 기여하지 않음(81.0%→81.5%) — planning(도구 선택, 동적 종료)이 정확도의 핵심 동인이며, 엣지는 추적 가능성만 제공

---

## 1. Introduction

> **[작성 전략]** LLM 에이전트 범용 성공(planning 포함) → 과학 도메인 적용 시도 → 규제 문서에서 벽 → 도메인 현실(정보 수집 계획 문제) → 요구사항 → 해법(planning in vectorless text environment). Osprey [Hellert et al., 2026] 참고.

### [P1] LLM 에이전트의 범용적 성공과 과학 도메인으로의 확장

- LLM 기반 에이전트는 범용 영역에서 놀라운 진전을 보이고 있음:

  - ReAct [Yao et al., 2023]가 추론(reason)과 행동(act)의 인터리빙을 제안한 이래, 에이전트는 코드 생성, 웹 탐색, 다단계 문제 해결에서 인간 수준에 근접
  - Toolformer [Schick et al., 2024]가 LLM의 자율적 도구 호출 능력을 입증하며 단순 생성기 → 능동적 문제 해결자로 진화
  - 정보 검색에서도 RAG [Lewis et al., 2020]를 넘어 Self-RAG [Asai et al., 2024]⁺, GraphRAG [Edge et al., 2024], LightRAG [Guo et al., 2024] 등 에이전틱 검색이 확산
- 이 범용적 성공에 힘입어, **과학·공학 도메인에서도 LLM 에이전트를 적용하려는 시도**가 활발:

  - GAIA [Mayet, 2024, arXiv:2405.01359]는 DESY 입자 가속기에서 ReAct + 다중 전문가 RAG 기반 운영 보조 에이전트를 구현
  - VISION [Mathur et al., 2025, arXiv:2412.18161]은 X선 산란 빔라인에서 음성 제어 실험 지원 에이전트를 시연
  - 자율 실험실 분야에서는 ChemCrow [Bran et al., 2024, arXiv:2304.05376]가 화학 도구 통합, Boiko et al. [2023]이 자율 화학 연구를 Nature에 발표
  - 핵 도메인에서도 NukeBERT [Jain et al., 2020]을 통한 도메인 특화 언어 모델, NuclearQA [Acharya et al., 2023]를 통한 벤치마크 구축, PACuna [Sulc et al., 2023, arXiv:2310.19106]의 가속기 문서 LoRA 파인튜닝 등 LLM 활용 기반이 형성되고 있음
- **However**, 이러한 시도들은 과학·규제 도메인이 범용 QA나 웹 검색과 **근본적으로 다른 특성**을 가진다는 현실에 직면한다:

  - Osprey [Hellert et al., 2026]는 가속기 제어 시스템에 에이전틱 AI를 배치하면서, 기존 범용 에이전트 프레임워크가 "계획된 행동의 사전 가시성, 프로토콜 인식형 제어 접근, 하드웨어 쓰기 안전장치"를 결여하고 있음을 지적
  - Lee [2025, arXiv:2507.09931]는 원자로 안전 분석에서 LLM의 블랙박스 특성이 10 CFR 50 Appendix B 품질보증 요건과 양립 불가함을 분석, 기계적 해석 가능성(mechanistic interpretability)을 대안으로 제시
  - 핵 규제 문서 검토 — FSAR 심사, 설계 적합성 판단 — 은 이러한 도전이 가장 첨예하게 드러나는 영역임. 그 구체적 원인을 이해하려면 규제 문서라는 세계의 현실을 들여다볼 필요가 있다.

### [P2] 규제 문서라는 세계: 왜 기존 RAG가 실패하는가

- 핵발전소 설계 인허가 과정에서 심사관은 수만 페이지에 달하는 최종안전분석보고서(FSAR)를 검토

  - NuScale FSAR: Ch.01(352p, 설계 개요) + Ch.05(160p, 원자로냉각재계통) — 이것이 전체 17개 장 중 단 2개
  - 각 장 내부는 목차 기반 계층 구조: 장(Chapter) → 절(Section) → 항(Subsection) → 단락으로 구성
  - 텍스트, 규격 표(설계 파라미터, 재료 물성), 공학 도면(P&ID, 계통도)이 한 문서 내에서 유기적으로 얽힘
- 심사관의 핵심 업무는 단순 사실 조회가 아닌 **증거 연쇄를 통한 규제 적합성 판단**

  - 예: "비상노심냉각계통(ECCS) 설계가 10 CFR 50.46(b) 수용 기준을 만족하는가?"
    → Ch.05 §5.4에서 ECCS 설계 사양 확인 → Ch.01 §1.9의 규제 요건 목록과 교차 → 해당 표에서 PCT < 2200°F 확인 → 세 증거를 종합해 만족(SATISFIES) 판단
  - 이 과정은 복수 문서·복수 모달리티를 횡단하는 멀티홉 추론이며, 실수의 결과는 안전에 직결
- 이 지식의 상당 부분은 형식화된 소프트웨어가 아닌 **전문가의 실무 경험**에 의존 — 노동 집약적이고 확장 불가

  - (cf. Osprey [Hellert et al., 2026]가 가속기 운영에서 동일한 문제를 지적: "knowledge resides in expert practice rather than formalized software")
- 이러한 도메인에서 기존 RAG 방법론은 **구조적으로** 부적합하다:

  - **구조가 의미를 담는 문서에서 청킹이 치명적**: "Table 5.1-1 참조"라는 텍스트와 실제 표는 물리적으로 다른 페이지에 위치 — 고정 크기 청킹은 이 참조 관계를 단절시킴 [Gao et al., 2023]
  - **증거 나열과 규제 판단은 다르다**: GraphRAG [Edge et al., 2024]의 커뮤니티 요약이나 LightRAG [Guo et al., 2024]의 엔티티-관계 추출은 관련 텍스트를 수집할 수 있지만, "이 설계가 이 규제 요건을 만족하는가?"라는 SATISFIES/VIOLATES 판단은 생성하지 못함
  - **정적 사전 인덱스는 규제 환경과 양립 불가**: GraphRAG, LightRAG, HippoRAG [Gutierrez et al., 2024] 모두 대규모 사전 인덱싱을 필요로 하나, FSAR는 NRC 심사 과정에서 수시로 개정 — 매번 재인덱싱은 비현실적

### [P3] 안전-임계 도메인의 고유 요건: 투명성과 감사 가능성

- 규제 도메인의 기술적 난제에 더해, **안전-임계 도메인 고유의 품질보증 요건**이 기존 접근법을 더욱 부적합하게 만든다
- 10 CFR 50, Appendix B, Criterion III (Design Control)는 안전 관련 분석이 "독립적 검증이 가능하도록 충분한 상세 수준으로 문서화"될 것을 요구 [10 CFR 50 App B]
  - 이 일반적 품질보증 원칙을 AI 기반 검색 도구에 적용하면, 검색 결과와 안전 결론 사이의 기술적 근거(technical basis)가 추적 가능해야 함
  - 임베딩 유사도 점수만으로는 이 문서화 요건을 충족하기 어려움 — 유사도 점수는 "왜 이 증거가 이 결론을 뒷받침하는가"에 대한 기술적 정당화를 제공하지 않기 때문
  - 반면, "Section 5.4.2가 §5.4.1의 일반 기술을 세부화(SPECIFIES)하며, 이 결과가 10 CFR 50.46(b)(1)의 PCT 한계를 만족(SATISFIES)함"이라는 형태의 **인간 가독 근거 경로**는 독립적 검증이 가능한 기술적 정당화에 해당
  - (참고: NRC는 AI/ML에 특화된 규제를 아직 제정하지 않았으나, 일반 QA 원칙의 적용은 Lee [2025]도 10 CFR 50 Appendix B의 AI 적용 맥락에서 논의)
- 이러한 투명성 문제를 해결하기 위한 선행 연구가 존재:
  - Osprey [Hellert et al., 2026]는 가속기 제어 시스템에서 plan-first 오케스트레이터(실행 전 계획 검토), 컨테이너화된 실행 환경, 하드웨어 쓰기 승인 체계로 투명성과 안전성을 확보 — 제어 시스템 도메인에서의 성공적 사례
  - Lee [2025]는 원자로 안전 분야에서 LoRA 적응 모델의 기계적 해석 가능성(mechanistic interpretability)을 통해 블랙박스 문제에 접근
  - 그러나 **규제 문서 검색**(수만 페이지 FSAR에서 멀티홉 증거를 찾아 규제 판단을 내리는 과정)의 투명성 문제는 아직 해결되지 않았으며, 임베딩 기반 검색의 불투명성은 이 요건과 근본적으로 충돌 — 검색의 패러다임 자체를 재정의해야 함

### [P4] 요구사항 종합

- P1에서 확인한 과학 도메인 적용 시도의 한계, P2의 규제 문서 구조적 난제, P3의 품질보증 요건을 종합하면, 규제 문서 탐색 에이전트는 다음 요건을 동시에 충족해야 함:

  | 요건                  | 근거 (P1~P3)                                     | 기존 접근법의 실패                                            |
  | --------------------- | ------------------------------------------------ | ------------------------------------------------------------- |
  | **멀티홉 추론** | P2: ECCS 적합성 판단은 3개 이상 섹션 횡단 필요   | 단일 hop top-K 반환으로는 증거 연쇄 불가                      |
  | **구조 보존**   | P2: "Table 5.1-1 참조"와 실제 표의 물리적 분리   | 청킹이 계층 구조·교차 참조 관계를 파괴                       |
  | **멀티모달**    | P2: 텍스트·규격 표·공학 도면이 유기적으로 얽힘 | 텍스트 추출만으로 시각 정보(P&ID, 계통도) 손실                |
  | **판단 생성**   | P2: SATISFIES/VIOLATES 판단은 검색이 아닌 추론   | 기존 RAG는 증거를 나열할 뿐 논리 관계 미생성                  |
  | **추적 가능성** | P3: 10 CFR 50 App B — 분석의 독립적 검증 가능성 | 임베딩 유사도 점수는 기술적 정당화 미제공                     |
  | **경량 인덱싱** | P2: FSAR는 심사 중 수시 개정 → 즉시 대응 필요   | GraphRAG/LightRAG 등의 대규모 사전 KG/벡터 DB 재구축 비현실적 |


  - 이 요건들은 핵 규제에 특화되었으나, 항공(FAA), 의약품(FDA), 건설 규제 등 안전-임계 문서 검토 전반에 공통적으로 적용됨 (cf. [Zhong et al., 2012] — 건설 규제 온톨로지)

  > **참고: "인덱싱 무비용"이 아닌 "경량 인덱싱"으로 표현한 이유**: 본 연구의 벡터리스 접근은 임베딩/청킹/KG 사전 구축이 불필요하나, PageIndex 트리 생성 시 LLM 기반 노드 요약이 포함되므로 인덱싱 비용이 완전히 0은 아님. 다만 GraphRAG(엔티티-관계 추출 + 커뮤니티 탐지)나 HippoRAG(OpenIE + PPR)에 비해 트리 구조 파싱 + 노드 요약만으로 구성되어 비용이 크게 절감됨. 정확한 비교는 Section 5.5에서 제시.
  >

### [P5] 우리의 접근: 규제 문서 탐색을 계획 문제로 정의

- **핵심 관찰**: P4의 요구사항을 다시 보면, 규제 문서 심사는 본질적으로 **계획 문제(planning problem)**:
  - **목표(goal)**: 규제 질문에 대한 근거 있는 판단 도출
  - **상태(state)**: 현재까지 수집된 증거와 그 관계
  - **행동(action)**: 문서 트리에서 어떤 섹션을 탐색할지 선택
  - **충분성 판단(goal test)**: 현재 증거로 답변 가능한가?
  - **검증(verification)**: 수집된 증거가 규제 요건을 만족/위반하는가?

- **인간 전문가의 심사 과정이 곧 계획**:
  - 목차로 탐색 범위 파악 (환경 인식) → 관련 섹션 드릴다운 (행동 선택) → 교차 참조 추적 (계획 수정) → 증거 충분성 평가 (goal test) → 규제 적합성 판단 (검증)
  - 이 과정은 ReAct [Yao et al., 2023]의 Reason-Act 인터리빙과 일치하며, 기존 RAG의 수동적 1회성 검색과 근본적으로 다름
  - 기존 RAG에서 LLM은 검색 결과의 **소비자** — 본 연구에서 LLM은 계획의 **주체**

- **제안 아키텍처: Planning loop**

  | Planning 단계 | 역할 | 구현 |
  |--------------|------|------|
  | **State estimation** | 현재 수집된 증거를 구조적으로 평가 | Dynamic Sub-KG (NetworkX DiGraph) |
  | **Action planning** | 다음에 어떤 문서 섹션을 탐색할지 결정 | LLM이 `browse`/`read`/`search` tool 선택 |
  | **Plan execution** | 선택된 행동 실행, 새 증거 수집 | BM25 기반 검색 + 노드 읽기 |
  | **Plan sufficiency** | 현재 증거로 답변 가능한지 판단 | LLM 기반 동적 종료 (avg 2.1–2.6 홉) |

  - 에이전트는 매 홉마다 현재 KG 상태를 기반으로 다음 탐색을 계획하는 반복적 루프로 작동
  - 동적 종료가 문항 복잡도에 따라 계획 깊이를 자동 조절 (Q001: 1홉 $0.03 vs Q191: 4홉 $0.29)

- **선택적 컴포넌트: Post-retrieval edge inference (Verification)**
  - 수집된 증거 간 관계를 2단계 엣지 추론(자유형 기술 → SATISFIES/VIOLATES 온톨로지 매핑)으로 명시화
  - 200Q ablation 결과, 이 컴포넌트는 **정확도에 기여하지 않음** (81.0% vs 81.5%) — 비용만 2.8× 증가
  - 가치는 추적 가능성(인간 가독 근거 경로)과 Faithfulness 소폭 개선(+0.033)에 한정
  - **핵심 발견: planning(도구 선택, 동적 종료)이 정확도의 핵심 동인이며, post-retrieval verification은 선택적**

### [P6] 왜 벡터리스인가: Planning Agent의 모달리티 정렬 원칙

- **설계 원칙: 상태와 환경을 에이전트의 네이티브 모달리티에 정렬**
  - LLM 기반 planning agent의 네이티브 모달리티는 **텍스트**
  - 에이전트가 효과적으로 계획을 수립하려면, 자신의 상태(State)와 환경(Environment)을 **직접 읽고 추론**할 수 있어야 함
  - 임베딩/벡터 표현은 LLM에게 불투명 — "유사도 0.87"로는 "다음에 뭘 탐색해야 하는가?"를 추론할 수 없음
  - 반면 텍스트 기반 표현은 LLM이 직접 해석 가능 — "현재 ECCS 설계 사양은 확보했으나 수용 기준이 미확인" → "규제 요건 테이블을 검색해야겠다"

- **이 원칙이 KG(State)와 Environment 설계에 미치는 영향**:

  | 요소 | 벡터 기반 표현 | 텍스트 기반 (ours) | LLM 계획 수립 가능? |
  |------|--------------|-------------------|:------------------:|
  | **KG 엣지** | 코사인 유사도 0.87 | "Section A SATISFIES Regulation B" | ❌ vs ✅ |
  | **검색 결과** | [chunk_42, score=0.91] | [§5.4 ECCS Design, 키워드 매칭: "ECCS"] | ❌ vs ✅ |
  | **환경 구조** | 평탄화된 청크 목록 | 계층 트리 (Ch.05 → §5.4 → §5.4.1) | ❌ vs ✅ |
  | **현재 상태 평가** | 임베딩 벡터 집합 | "3개 노드, SPECIFIES 2개, SATISFIES 1개" | ❌ vs ✅ |

  - **KG 엣지를 자연어로 기술**하는 이유: LLM이 현재 상태를 읽고 "어떤 관계가 부족한가"를 판단하기 위함 (cf. LightRAG [Guo et al., 2024]의 free-form 관계 추출도 동일 발상)
  - **환경을 계층 트리로 구성**하는 이유: LLM이 목차를 읽고 "어디를 탐색할지" 계획하기 위함 — 벡터 DB에서는 불가능한 `browse`(구조 탐색) 행동이 가능

- **"벡터 검색을 tool로 추가하면 안 되나?"에 대한 답변**:
  - 본 연구의 핵심 주장은 "BM25가 벡터 검색보다 우월하다"가 아님
  - 핵심은 **State(KG)와 Environment(트리)를 텍스트 기반으로 구축하여 LLM이 계획을 수립할 수 있게 한 아키텍처** — search tool의 구현(BM25/벡터)은 이 아키텍처와 직교적(orthogonal)
  - 경험적으로 BM25 기반 현재 구현이 4개 벡터 기반 베이스라인(GraphRAG, LightRAG, HippoRAG, RAPTOR)을 상회 → 현재 선택의 타당성 뒷받침
  - 벡터 검색 tool 추가 비교는 향후 연구로 남김

- **벡터리스 문서 트리 구현**:
  - 문서의 원본 계층 구조(목차)를 그대로 보존한 JSON 트리 인덱스 [Zhang & Tang, 2025, PageIndex]
  - 각 트리 노드 = 문서의 한 섹션 (제목, 전문, LLM 요약, 하위 노드 목록)
  - 멀티모달 참조 링크: LIST OF FIGURES/TABLES 파싱 → `references` 필드로 도면/표 메타데이터 첨부
  - 경량 인덱싱: $4.06 / 7.6–19.8분 (기존 대비 5–7× 빠름)

  > **⚠️ 인용 참고**: PageIndex는 학술 논문이 아닌 오픈소스 프레임워크. 벡터리스 RAG 개념에 대한 독립적 학술 분석으로는 Lumer et al. [2025, arXiv:2511.18177] 참조.

### [P7] 본 연구의 기여

- 위 요구사항(P4)을 충족하기 위해, 규제 문서 탐색을 **LLM 기반 계획 문제**로 정의하고, 상태와 환경을 LLM의 네이티브 모달리티(텍스트)에 정렬한 아키텍처를 제안
- 핵심 기여:

1. **문서 탐색의 계획 문제 정의**: 규제 문서 멀티홉 추론을 정보 수집 계획 문제로 모델링 — 상태 평가, 행동 선택, 충분성 판단, 동적 종료의 planning loop 구현. 이것만으로 4개 RAG 베이스라인 상회 (81.5%)
2. **모달리티 정렬 원칙에 기반한 벡터리스 설계**: LLM이 상태(KG)와 환경(문서 트리)을 직접 읽고 추론할 수 있도록 텍스트 기반으로 구축 — 임베딩 불투명성 제거, 계획 수립 가능하게 함
3. **Vision-Augmented 멀티모달 처리**: PDF 원본 도면/표를 GPT-4.1 vision으로 해석 (table_only +18%p vs. RAPTOR)
4. **200Q 핵 규제 멀티홉 벤치마크**: 3축 직교 분류(reasoning × complexity × modality), 기존 벤치마크에 없는 judgment + cross_document + multimodal 조합

- 분석적 기여:
5. **Post-retrieval edge inference의 비용 대비 효과 분석**: 200Q ablation에서 엣지 추론이 정확도에 기여하지 않음을 발견 (81.0% vs 81.5%, 비용 2.8× 증가). Planning이 정확도의 핵심 동인이며, 엣지의 가치는 추적 가능성에 한정됨

---

## 2. Related Work

### 2.1 Retrieval-Augmented Generation (RAG)

- **기본 RAG**: 쿼리 → 벡터 유사도 검색 → LLM 생성 [Lewis et al., 2020]⁺
  - 한계: 단일 hop, 청킹 경계에서 문맥 단절
- **GraphRAG** [Edge et al., 2024, arXiv:2404.16130]: 커뮤니티 기반 글로벌/로컬 검색
- **LightRAG** [Guo et al., 2024, arXiv:2410.05779]: free-form 관계 추출 후 이중 레벨 그래프 검색
  - 본 연구의 2단계 엣지 추론 Stage 1이 LightRAG 관계 추출 방식에서 영감
- **RAPTOR** [Sarthi et al., 2024, arXiv:2401.18059]: 재귀 요약 트리 (ICLR 2024)
  - 본 연구의 PageIndex 트리와 구조적으로 유사하나 사전 인덱싱 필요, 동적 탐색 없음
- **HippoRAG** [Gutierrez et al., 2024, arXiv:2405.14831]: 해마 기반 PPR 검색 (NeurIPS 2024)

### 2.2 LLM-based Planning & Agent Frameworks

- **LLM for Planning**: LLM을 계획 생성·평가에 활용하는 연구가 활발
  - ReAct [Yao et al., 2023]: 추론(reason)과 행동(act) 인터리빙 — 본 연구의 planning loop과 개념적으로 일치
  - Tree-of-Thought [Yao et al., 2024]⁺: 탐색 트리 기반 다단계 추론 — 본 연구의 문서 트리 탐색과 구조적 유사
  - Toolformer [Schick et al., 2024]: LLM 자율적 도구 호출 — 본 연구의 browse/read/search 행동 선택 기반
  - 본 연구의 차별점: 기존 LLM planning 연구가 PDDL/로봇/웹 환경에 집중하는 반면, **정보 환경(규제 문서)**에서의 계획 문제를 다룸

- **World Models & State Representation**:
  - Ha & Schmidhuber [2018]: 에이전트가 환경의 내부 표현을 유지하며 행동 계획
  - GWM [Feng et al., 2025, ICML 2025]: 그래프 구조 상태 표현 + 메시지 패싱 기반 액션
  - 본 연구는 Dynamic Sub-KG를 계획 과정의 내부 상태로 사용하되, 임베딩 대신 LLM 추론 기반 명시적 관계(SATISFIES, VIOLATES)를 생성하는 벡터리스 접근

- **Verification with LLMs**: LLM을 계획/정책 검증에 사용
  - 본 연구의 2단계 엣지 추론이 이 범주에 해당 — 수집된 증거가 규제 요건을 만족하는지 LLM이 검증

### 2.3 Knowledge Graph for RAG

- **KG 기반 RAG**: 명시적 트리플로 멀티홉 추론 강화 [Pan et al., 2024]⁺
- **동적 KG**: 쿼리별 실시간 KG 생성 — 사전 KG 구축 비용 없음
  - 본 연구의 Dynamic Sub-KG가 이 범주에 해당
- **엣지 온톨로지 선례**:
  - SysML 요구사항 추적 [Friedenthal et al., 2014]: SATISFIES/REFINES 관계
  - 건설 규제 온톨로지 [Zhong et al., 2012]⁺: 규정 준수 자동 검사 — 규제 도메인 적용 선례
  - 논증 마이닝 [Peldszus & Stede, 2013]: SUPPORTS/CONTRADICTS 관계 기원
  - 텍스트 함의 + 논증 [Cabrio & Villata, 2012, ACL]: 온라인 토론 지원에 ATTACKS/SUPPORTS 적용
  - 전제 관계 학습 [Pan et al., 2017, ACL]: IS_PREREQUISITE_OF 관계 기원
  - 인과 KG [Hassanzadeh et al., 2019, IJCAI]: LEADS_TO 관계 기원

### 2.4 Multimodal RAG

- **DocVQA, ChartQA**: 단일 이미지 Q&A → 본 연구는 multi-hop + 멀티모달 복합 처리

### 2.5 Nuclear Domain NLP

- **NuclearQA** [Acharya et al., 2023, arXiv:2310.10920]: 핵 도메인 언어 모델 벤치마크
  - 단일 hop 사실 추출 위주 → 멀티홉 판단 평가 불가, 본 벤치마크 설계 동기
- **NukeBERT** [Jain et al., 2020, arXiv:2003.13821]: 핵 도메인 사전 학습 언어 모델

### 2.6 RAG Evaluation

- **RAGAS** [Es et al., 2024, arXiv:2309.15217, EACL 2024]: RAG 자동 평가 프레임워크
  - Faithfulness, Answer Relevancy, Context Recall, Factual Correctness
- **LLM-as-Judge**: GPT-4 기반 자동 평가 [Zheng et al., 2023]⁺ — 3-평가자 다수결 투표

---

## 3. Method

> **전체 파이프라인**: User Query → Planning Loop (State estimation → Action planning → Execution → Verification, max 4 hops) → Vision-Augmented Answer

### 3.1 Environment: 벡터리스 멀티모달 문서 트리

- **표현**: JSON 계층 트리 — 장(chapter) → 절(section) → 단락(paragraph) 노드
- **멀티모달 참조 링크**: 목록(LIST OF FIGURES/TABLES) 파싱 → 노드 텍스트 내 "Figure 5.1-1" 참조 탐지 → `references` 필드로 메타데이터 첨부
  - 해결 문제: "figure on different page" — 참조 텍스트와 실제 도면이 다른 페이지에 위치하는 포맷 문제
- **벡터리스 설계**: 임베딩/청킹 없음 → BM25Okapi [Robertson & Zaragoza, 2009] 기반 키워드 검색
  - title 가중치 3×, 문서 길이 정규화 → 짧고 집중된 리프 노드가 자연스럽게 상위 랭크
- **스케일**: Ch.01 866 노드(34 figures, 19 tables), Ch.05 26 노드(29 figures, 30 tables)

### 3.2 State (단기 기억): Dynamic Sub-KG와 2티어 엣지 온톨로지

- **정의**: 시각 $t$의 에이전트 상태 $s_t$ = 동적 지식 그래프 $G_t = (V_t, E_t)$

  - 노드 $V_t$: 탐색으로 수집된 문서 섹션(증거) + 연관 멀티모달 참조
  - 엣지 $E_t$: 2티어 도메인 특화 온톨로지 (신뢰도 ≥ 0.4 필터링)
- **Tier 1 — 구조 엣지** (탐색 경로 backbone):

  | 엣지       | 학술적 기원                                     | 도메인 적용                 |
  | ---------- | ----------------------------------------------- | --------------------------- |
  | REFERENCES | 인용 네트워크 [Garfield, 1979]                  | 섹션 A가 섹션 B를 교차 참조 |
  | SPECIFIES  | SysML `<<refine>>` [Friedenthal et al., 2014] | 상위 기술의 세부 사양 제공  |
- **Tier 2 — 의미 엣지** (규제 판단 관계):

  | 엣지                   | 학술적 기원                                                                    | 도메인 적용                                 |
  | ---------------------- | ------------------------------------------------------------------------------ | ------------------------------------------- |
  | SATISFIES / VIOLATES   | SysML 요구사항 추적 [Friedenthal et al., 2014]; 건설 규제 [Zhong et al., 2012] | 설계 결과 노드가 규제 요건 노드를 만족/위반 |
  | SUPPORTS / CONTRADICTS | 논증 마이닝 [Peldszus & Stede, 2013]; 텍스트 함의 [Cabrio & Villata, 2012]     | 복수 문서 증거 상호 검증                    |
  | LEADS_TO               | 인과 KG [Hassanzadeh et al., 2019]                                             | 사고 분석 보고서의 원인-결과 추적           |
  | IS_PREREQUISITE_OF     | 전제 관계 학습 [Pan et al., 2017]                                              | 선결 검토 조건 문서 연결                    |
- **경험적 근거**:

  - 단일 홉 사실 질문: 구조 엣지(REFERENCES, SPECIFIES) 지배 → 탐색 경로 형성
  - 복합 멀티홉 판단 질문: 의미 엣지(SATISFIES, SUPPORTS) 출현 → 규제 준수 합성
  - 정답(O) vs 오답(X): SUPPORTS +6.8%p, SATISFIES +3.2%p in correct answers

### 3.3 Action Planning: LLM 기반 도구 선택

- **기존 RAG와의 차이**: 임베딩 유사도 기반 수동 검색이 아닌, LLM이 현재 상태를 평가하고 다음 행동을 **계획**

  | Tool                        | 유추     | 기능                                   |
  | --------------------------- | -------- | -------------------------------------- |
  | `browse(doc_id, node_id)` | `ls`   | 트리 노드 자식 목록 — 계층적 드릴다운 |
  | `read(doc_id, node_id)`   | `cat`  | 특정 노드 전체 내용 추출               |
  | `search(keyword)`         | `grep` | BM25 랭킹 키워드 검색 (전문서)         |
- **Browse-first 패턴**: Hop 1에서 문서 구조(목차)를 자동 주입 → 에이전트가 검색 전 전체 지도 파악

  - 효과: single_evidence CR 0.45 → 0.89 (v0.4.5)
- **PRF (Pseudo-Relevance Feedback, RM3)**: 상위 3개 검색 결과에서 쿼리 자동 확장

  - 어휘 불일치(vocabulary mismatch) 해결, LLM 비용 0
- **에이전트 메모리**: 검색 히스토리로 키워드 중복 방지 — 계획의 반복 회피
- **Plan sufficiency (동적 종료)**: Hop 2부터 매 홉 전 LLM이 "현재 KG로 답변 가능한가?"를 판단 → 충분하면 조기 종료
  - 이는 planning에서의 **goal test**에 해당 — 문항 복잡도에 따라 계획 깊이를 자동 조절
  - 단순 factual (Q001): 1홉 17초 $0.03 / 복잡한 judgment (Q191): 4홉 140초 $0.29
  - 평균 실제 홉 수: 2.1–2.6 (최대 4) — 불필요한 탐색을 자동으로 가지치기

### 3.4 Post-retrieval Edge Inference (선택적 컴포넌트)

- **역할**: 수집된 증거 간 관계를 명시화 — 상태 전이 $f_{tr}(s_t, a_t) \rightarrow s_{t+1}$와 동시에 수행
- **참고**: 200Q ablation 결과, 이 컴포넌트는 정확도에 기여하지 않음 (Section 6.1 참조). 추적 가능성이 필요한 경우 선택적으로 활용
- **Stage 1 — 자유형 기술 (Description)**: LLM이 두 노드 간 관계를 자연어 1문장으로 기술 (분류 압력 없음)
  - LightRAG [Guo et al., 2024]의 free-form 관계 추출 방식 채택
  - 예: "ECCS의 3 RVV + 2 RRV 설계는 10 CFR 50.46의 수용 기준을 충족하도록 구성됨"
- **Stage 2 — 레이블 (Ontology Mapping)**: Stage 1 기술을 규제 도메인 온톨로지(SATISFIES, VIOLATES 등)로 매핑
  - 매핑 불가 시 SEMANTIC으로 보존 → 관계 손실 없음
- **Planning과의 관계**: Verification은 planning과 분리된 후처리가 아니라, **매 홉마다 planning loop 내에서 인터리빙** — 새 증거 수집(planning) 직후 관계 추론(verification) 수행, 그 결과가 다음 홉의 plan sufficiency 판단에 반영
- **기존 접근과의 차이**: 임베딩 기반 암묵적 관계(GraphRAG, GWM) 대신 LLM 추론 기반 명시적 자연어 기술 → 검증 결과가 인간이 검사 가능

### 3.5 Vision-Augmented 최종 답변 생성

- **비용 효율 설계**: 멀티모달 처리는 최종 답변 생성 1회에만 적용
  - 중간 탐색(search, plan, infer) 전부 텍스트 전용
- **구현**:
  1. KG 전체 노드의 Figure/Table references 수집
  2. PyMuPDF로 해당 PDF 페이지 → JPEG 렌더링
  3. 텍스트 KG 문맥 + 이미지 → GPT-4.1 vision API
- **표 처리**: PyMuPDF `find_tables()`로 행/열 구조 추출 → 구조화 텍스트로 직접 전달 (VLM 이미지 불필요)
  - 결과: table_only 86.0% (vs RAPTOR 68.0%, +18%p)

---

## 4. Benchmark: Nuclear Regulatory Multi-hop QA

### 4.1 기존 벤치마크의 한계와 새 벤치마크의 필요성

- 규제·기술 문서 QA 벤치마크는 다수 존재하나, 본 연구가 요구하는 **핵 규제 × 멀티홉 × 멀티모달 × 판단** 조합을 동시에 갖춘 벤치마크는 없음:

  | 벤치마크 | 문서 유형 | 문항 | 멀티홉 | 표 | 도면 | 교차문서 | 판단 |
  |----------|----------|:----:|:------:|:--:|:----:|:-------:|:----:|
  | NuclearQA [Acharya et al., 2023] | 핵 도메인 지식 | 100 | ❌ | ❌ | ❌ | ❌ | ❌ |
  | FDARxBench [2025, arXiv:2603.19539]⁺ | FDA 의약품 라벨 | 17K | ✅ | ✅ | △ | ❌ | ✅ |
  | MMLongBench-Doc [2024, arXiv:2407.01523]⁺ | 장문 PDF 7개 도메인 | 1,062 | ✅ | ✅ | ✅ | ❌ | ❌ |
  | M3DocVQA [2024, arXiv:2411.04952]⁺ | 다양한 PDF | 2,441 | ✅ | ✅ | ✅ | ✅ | ❌ |
  | DesignQA [2024, arXiv:2404.07917]⁺ | 공학 문서 + CAD | ~수백 | ❌ | ✅ | ✅ | ✅ | △ |
  | SEC-QA [2025, arXiv:2406.14394]⁺ | SEC 재무 보고서 | 333 | ✅ | ✅ | ❌ | ✅ | ❌ |
  | TAT-QA [2021, arXiv:2105.07624] | 재무 보고서 (표+텍스트) | 16K | ✅ | ✅ | ❌ | ❌ | ❌ |
  | **Ours** | **핵 FSAR** | **200** | **✅** | **✅** | **✅** | **✅** | **✅** |

  - FDARxBench가 가장 유사 (규제 문서 + 멀티홉 + 판단)하나, 단일 문서·도면 없음
  - MMLongBench-Doc, M3DocVQA가 멀티모달 장문서에 강하나, 규제 판단(judgment) 문항 유형 없음
  - DesignQA가 공학 문서 + 규정 준수에 유사하나, 멀티홉 추론 미지원
  - **본 벤치마크의 고유 기여**: 핵 규제 도메인에서 멀티홉 교차 문서 추론 + 멀티모달(표·도면) + 규제 적합성 판단(judgment)을 결합한 **최초의 벤치마크**

### 4.2 설계 원칙

- **3축 직교 분류 체계**: 모든 문항이 reasoning_type × complexity × question_type 3축에 태깅

  - 단일 차원 분류(예: "easy/medium/hard")가 아닌 독립 3축 → 특정 약점을 정밀 진단 가능
  - 예: "factual × cross_document × table_only"에서만 약한 시스템 식별 가능
- **규제 심사 과정 모방**:

  - **factual**: 단일 사실 조회 — "RCS 운전 압력은?" (심사 기초 확인)
  - **comparative**: 교차 비교 — "Ch.01의 설계 개요와 Ch.05의 상세 사양이 일치하는가?" (문서 간 일관성 검증)
  - **judgment**: 규제 적합성 판단 — "ECCS 설계가 10 CFR 50.46(b) 요건을 만족하는가?" (심사의 핵심)
  - judgment × cross_document(35문항)에 가장 큰 비중 — 실제 심사의 핵심 업무를 반영
- **멀티모달 증거 다양성**:

  - text_only(80): 서술 텍스트만으로 답변 가능
  - table_only(50): 규격 표(설계 파라미터, 재료 물성) 해석 필요
  - image_only(30): 공학 도면(P&ID, 계통도) 해석 필요
  - composite(40): 텍스트 + 표 + 도면 복합 활용 필요
- **ground_truth_evidence 표기**: 각 문항에 정답 근거의 소스 문서, 페이지, 소스 타입(text/table/figure), 관련 텍스트를 명시

  - 평가 시 "맞혔지만 틀린 근거"와 "틀렸지만 맞는 근거"를 구분 가능
  - 총 357개 증거 조각: text 152, table 125, figure 80

### 4.3 벤치마크 상세 구성

- **소스 문서**: NuScale FSAR Ch.01 (352p) + Ch.05 (160p) — NRC 공개 자료
- **총 200문항**, 3축 교차 분포:

  **reasoning_type × complexity:**

  |                            | single_evidence | multi_evidence | cross_document |
  | -------------------------- | :-------------: | :------------: | :------------: |
  | **factual** (70)     |       30       |       25       |       15       |
  | **comparative** (65) |       15       |       25       |       25       |
  | **judgment** (65)    |        5        |       25       |  **35**  |


  > judgment × cross_document(35문항)가 최대 셀 — 실제 규제 심사에서 가장 빈번하고 어려운 작업
  >

  **question_type 분포:**

  | text_only | table_only | image_only | composite |
  | :-------: | :--------: | :--------: | :-------: |
  |    80    |     50     |     30     |    40    |
- **문항 예시**:

  | 유형                         | 예시                                                                      |
  | ---------------------------- | ------------------------------------------------------------------------- |
  | factual / single / text      | "NuScale 원전 12모듈 기준 총 전기 출력은?"                                |
  | comparative / cross / table  | "Ch.01 Table 1.3-1 운전 파라미터와 Ch.05 Table 5.1-1 RCS 체적을 비교하라" |
  | judgment / cross / composite | "Ch.01과 Ch.05에 기술된 일체형 SG 설계가 SGTR 우려에 적절한가?" (Q176)    |

### 4.4 이중 평가 프레임워크

- 단일 평가 프레임워크의 한계를 인식, **연속형(RAGAS) + 이진형(LLM-as-Judge)** 이중 평가 채택

  | 프레임워크                        | 측정 대상                                   | 스케일    | 장점                            | 한계                                     |
  | --------------------------------- | ------------------------------------------- | --------- | ------------------------------- | ---------------------------------------- |
  | **RAGAS** [Es et al., 2024] | Grounding (답변이 검색된 문맥에 근거하는가) | 연속 0–1 | 세밀한 품질 측정, 메트릭별 진단 | 검색 문맥 밖 지식으로 맞힌 경우 과소평가 |
  | **LLM-as-Judge**            | Correctness (답변이 기대 답변과 일치하는가) | 이진 O/X  | 실질적 정확도, 해석 용이        | 표현 불일치 시 과소평가                  |
- **RAGAS 4개 메트릭**:

  - Faithfulness: 답변의 각 claim이 검색 문맥에 근거하는 비율 → 환각 탐지
  - Answer Relevancy: 답변이 질문 의도에 부합하는 정도
  - Context Recall: 기대 답변의 각 문장이 검색 문맥에 뒷받침되는 비율 → 검색 완전성
  - Factual Correctness: 기대 답변 대비 사실적 정확도 → wording-sensitive
- **LLM-as-Judge 3-평가자 다수결**:

  - Tonic (GPT-4-turbo): 5점 척도, ≥4점 → O
  - MLflow (GPT-4o): 유사도 + 정확도 이중 판정
  - Allganize (Claude Sonnet 4.5): 5점 척도, ≥4점 → O
  - 3인 중 2인 이상 O → 최종 O (다수결)
- **이중 평가의 근거**: 본 연구 결과에서 RAGAS-Judge 일치율 66.2% — 34%의 불일치가 상호 보완적 정보 제공 (6.4절 상세 분석)

---

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
| HippoRAG             |      69.0%      |      86.2%      |      63.1%      |      58.6%      |      65.3%      |      56.0%      |      55.0%      |
| LightRAG             |      67.5%      |      75.4%      |      66.2%      |      61.4%      |      69.3%      |      60.0%      |      65.0%      |
| GraphRAG             |      49.5%      |      61.5%      |      49.2%      |      38.6%      |      37.3%      |      42.0%      |      47.5%      |

### 5.4 RAGAS 결과 (Ours)

| 메트릭              |    Overall    | factual |  comparative  |    judgment    |
| ------------------- | :------------: | :-----: | :------------: | :------------: |
| Faithfulness        | **0.93** |  0.92  |      0.92      | **0.97** |
| Answer Relevancy    | **0.84** |  0.85  |      0.78      | **0.89** |
| Context Recall      | **0.93** |  0.92  |      0.91      | **0.96** |
| Factual Correctness |      0.42      |  0.35  | **0.49** |      0.41      |

**RAGAS 비교 (Ours vs RAPTOR vs GraphRAG):**

| 메트릭              | **Ours** | RAPTOR | GraphRAG |
| ------------------- | :------------------: | :----: | :------: |
| Faithfulness        |    **0.93**    |  0.74  |   0.28   |
| Answer Relevancy    |    **0.84**    |  0.83  |   0.59   |
| Context Recall      |    **0.93**    |  0.77  |   0.18   |
| Factual Correctness |    **0.42**    |  0.40  |   0.32   |

> Ours가 모든 RAGAS 메트릭에서 최고 성능. GraphRAG는 Faithfulness 0.28, Context Recall 0.18 — 커뮤니티 요약에서 구체적 사실이 손실되는 구조적 문제.

**RAGAS by question_type (RAPTOR / GraphRAG):**

| Type       | RAPTOR Faith | RAPTOR CR | GraphRAG Faith | GraphRAG CR |
| ---------- | :----------: | :-------: | :------------: | :---------: |
| text_only  |     0.79     |   0.79   |      0.16      |    0.19    |
| table_only |     0.77     |   0.66   |      0.38      |    0.09    |
| image_only |     0.63     |   0.86   |      0.32      |    0.25    |
| composite  |     0.71     |   0.79   |      0.36      |    0.20    |

> RAPTOR image_only CR 0.86 (재귀 요약이 이미지 설명 포착). GraphRAG table_only CR **0.09** — 사실상 표 정보 검색 불가.

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

## 7. Conclusion

- 규제 문서 멀티홉 추론을 **LLM 기반 계획 문제**로 정의하고, 벡터리스 문서 트리 환경에서 이를 해결하는 아키텍처를 제안

- **핵심 발견**:
  1. **Planning이 정확도의 핵심 동인**: LLM의 도구 선택, 동적 종료(plan sufficiency), browse-first 환경 인식만으로 81.5% 달성 — 4개 벡터 기반 RAG 베이스라인 상회
  2. **모달리티 정렬 원칙의 유효성**: 상태(KG)와 환경(트리)을 LLM의 네이티브 모달리티(텍스트)로 구축 → 임베딩/청킹 없이도 경쟁력 있는 성능
  3. **Post-retrieval edge inference는 정확도에 기여하지 않음**: 200Q ablation에서 엣지 추론 제거 시 정확도 유지(81.0%→81.5%), 비용 65% 절감. 엣지의 가치는 추적 가능성에 한정
  4. **경량 인덱싱**: 벡터리스 트리 구축 $4.06, 기존 대비 5–7× 빠름

- **LM4Plan 관점에서의 시사점**:
  - LLM 기반 계획은 PDDL/로봇 환경뿐 아니라 **정보 환경(규제 문서)**에서도 유효
  - 정보 환경에서의 planning은 검색(retrieval)을 대체하는 패러다임이 될 수 있음
  - Post-retrieval verification(엣지 추론)은 정확도가 아닌 추적 가능성이 필요한 도메인에서 선택적으로 활용

---

## References

> 검증 상태: ✅ 확인됨 / ⚠️ 미확인 또는 미출판

| #    | 인용                                                                                                                                                                                                       | 상태             |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| [2]  | Feng, T., Wu, Y., Lin, G., & You, J. (2025).*Graph World Model*. ICML 2025. arXiv:2507.10539                                                                                                             | ✅               |
| [3]  | Edge, D., Trinh, H., Cheng, N., et al. (2024).*From Local to Global: A Graph RAG Approach to Query-Focused Summarization*. arXiv:2404.16130                                                              | ✅               |
| [4]  | Guo, Z., Xia, L., Yu, Y., Ao, T., & Huang, C. (2024).*LightRAG: Simple and Fast Retrieval-Augmented Generation*. arXiv:2410.05779                                                                        | ✅               |
| [5]  | Sarthi, P., Abdullah, S., Goldie, A., et al. (2024).*RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval*. ICLR 2024. arXiv:2401.18059                                                 | ✅               |
| [6]  | Gutierrez, B.J., Shu, Y., Gu, Y., Yasunaga, M., & Su, Y. (2024).*HippoRAG: Neurologically Inspired Long-Term Memory for Large Language Models*. NeurIPS 2024. arXiv:2405.14831                           | ✅               |
| [7]  | Es, S., James, J., Espinosa Anke, L., & Schockaert, S. (2024).*RAGAS: Automated Evaluation of Retrieval Augmented Generation*. EACL 2024. arXiv:2309.15217                                               | ✅               |
| [8]  | Acharya, A., et al. (2023).*NuclearQA: A Human-Made Benchmark for Language Models for the Nuclear Domain*. arXiv:2310.10920                                                                              | ✅               |
| [9]  | Friedenthal, S., Moore, A., & Steiner, R. (2014).*A Practical Guide to SysML: The Systems Modeling Language* (3rd ed.). Morgan Kaufmann.                                                                 | ✅               |
| [10] | Peldszus, A., & Stede, M. (2013). From argument diagrams to argumentation mining in texts: A survey.*IJCINI*, 7(1), 1–31.                                                                               | ✅               |
| [11] | Cabrio, E., & Villata, S. (2012). Combining textual entailment and argumentation theory for supporting online debates interactions.*ACL 2012*.                                                           | ✅               |
| [12] | Pan, L., Li, C., Li, J., & Tang, J. (2017). Prerequisite relation learning for concepts in MOOCs.*ACL 2017*.                                                                                             | ✅               |
| [13] | Hassanzadeh, O., et al. (2019). Answering binary causal questions through large-scale text mining: An evaluation using cause-effect pairs from human expert consensus.*IJCAI 2019*.                      | ✅               |
| [14] | Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.*Foundations and Trends in Information Retrieval*, 3(4), 333–389.                                          | ✅               |
| [15] | Zhong, B., et al. (2012). Ontology-based semantic modeling of knowledge of construction regulations for regulatory compliance checking of construction designs.*Automation in Construction*, 28, 58–70. | ✅ (제목 수정됨) |
| [16] | Garfield, E. (1979).*Citation Indexing: Its Theory and Application in Science, Technology, and Humanities*. Wiley.                                                                                       | ✅               |
| [17] | Jain, A., Meenachi, N.M., & Venkatraman, B. (2020). NukeBERT: A pre-trained language model for low resource nuclear domain. arXiv:2003.13821                                                               | ✅               |
| [18] | Ha, D., & Schmidhuber, J. (2018). Recurrent world models facilitate policy evolution.*NeurIPS 2018*. arXiv:1803.10122                                                                                    | ✅               |
| [19] | Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks.*NeurIPS 2020*. arXiv:2005.11401                                                       | ✅               |
| [20] | Yao, S., Zhao, J., Yu, D., et al. (2023). ReAct: Synergizing reasoning and acting in language models.*ICLR 2023*. arXiv:2210.03629                                                                       | ✅               |
| [21] | Gao, Y., Xiong, Y., Gao, X., et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv:2312.10997                                                                           | ✅               |
| [22] | Schick, T., Dwivedi-Yu, J., Dessì, R., et al. (2024). Toolformer: Language models can teach themselves to use tools.*NeurIPS 2023*. arXiv:2302.04761                                                    | ✅               |

| [23] | Hellert, T., Montenegro, J., & Sulc, A. (2026). Osprey: Production-ready agentic AI for safety-critical control systems. *APL Machine Learning*, 4(1), 016103. arXiv:2508.15066 | ✅ |
| [24] | Zhang, M. & Tang, Y. (2025). *PageIndex: Next-Generation Vectorless, Reasoning-based RAG*. pageindex.ai | ⚠️ 오픈소스, 학술 논문 없음 |
| [25] | Lumer, E., et al. (2025). Rethinking Retrieval: From Traditional RAG to Agentic and Non-Vector Reasoning Systems in the Financial Domain. arXiv:2511.18177 | ✅ |
| [26] | Mayet, F. (2024). GAIA: A General AI Assistant for Intelligent Accelerator Operations. arXiv:2405.01359 | ✅ |
| [27] | Mathur, S., van der Vleuten, N., Yager, K., & Tsai, E. (2025). VISION: A Modular AI Assistant for Natural Human-Instrument Interaction at Scientific User Facilities. arXiv:2412.18161 | ✅ |
| [28] | Bran, A.M., et al. (2024). ChemCrow: Augmenting Large-Language Models with Chemistry Tools. arXiv:2304.05376 | ✅ |
| [29] | Boiko, D., et al. (2023). Autonomous chemical research with large language models. *Nature* | ✅ |
| [30] | Lee, Y.P. (2025). Mechanistic Interpretability of LoRA-Adapted Language Models for Nuclear Reactor Safety Applications. arXiv:2507.09931 | ✅ |
| [31] | Sulc, A., et al. (2023). PACuna: Automated Fine-Tuning of Language Models for Particle Accelerators. arXiv:2310.19106 | ✅ |
| [32] | FDARxBench (2025). arXiv:2603.19539 — FDA 의약품 라벨 규제 문서 QA 벤치마크 (17K 문항, 멀티홉) | ✅⁺ |
| [33] | Ma, Y., et al. (2024). MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations. arXiv:2407.01523 | ✅⁺ |
| [34] | Huang, J., et al. (2024). M3DocVQA / M3DocRAG: Multi-modal Multi-page Multi-document RAG. arXiv:2411.04952 | ✅⁺ |
| [35] | Doris, Y., et al. (2024). DesignQA: A Multimodal Benchmark for Evaluating LLMs' Understanding of Engineering Documentation. arXiv:2404.07917 | ✅⁺ |
| [36] | Zhu, F., et al. (2021). TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance. arXiv:2105.07624 | ✅ |
| [37] | Loukas, L., et al. (2025). SEC-QA: A Systematic Evaluation Corpus for Financial QA. arXiv:2406.14394 | ✅⁺ |

> ⁺ 추가 검증 권장: Zheng et al. 2023 LLM-as-Judge (arXiv:2306.05685), Asai et al. 2024 Self-RAG (arXiv:2310.11511)
> ⁺ [32]~[37]은 벤치마크 비교 목적으로 인용, 저자/제목 정밀 검증 필요

---

## 작성 메모

### 논문 포지셔닝

- **Planning 중심 프레이밍**: 문서 탐색을 계획 문제로 정의, planning이 정확도의 핵심 동인
- 엣지 추론(verification)은 정직한 negative finding으로 보고 — 정확도 기여 없음, 추적 가능성만 제공
- GWM은 Related Work에서 비교 대상으로 인용 (임베딩 기반 vs 벡터리스)
- 핵심 메시지: "LLM 기반 계획만으로 4개 벡터 기반 RAG 시스템을 상회하며, 정보 환경(문서)에서의 planning은 검색을 대체하는 새로운 패러다임"

### 현재 논문의 약점 (리뷰어 예상 질문)

1. **Q. text_only에서 왜 RAPTOR보다 낮은가?** → 답: 요약 기반 검색이 텍스트 전용에서 효과적, 향후 요약 노드 추가 검토
2. **Q. 문항당 48초/$0.08(no_edges)은 여전히 비싸다** → 답: 동적 종료로 단순 질문 $0.03(1홉), 8× 병렬 ~20분/200Q, +6%p 정확도 향상(vs RAPTOR)의 trade-off
3. **Q. Factual Correctness 0.42가 낮다** → 답: FC의 구조적 한계(예상 답변 표현 다양성), RAGAS 논문도 인정
4. **Q. benchmark 자체 제작이라 편향** → 답: 3축 직교 설계, 3인 다수결, 7개 기존 벤치마크 대비 고유성 주장, 외부 검증은 향후
5. **Q. 엣지가 의미 없으면 왜 넣었나?** → 답: 200Q ablation에서 발견한 정직한 결과. post-retrieval edge가 정확도에 기여하지 않는다는 것 자체가 발견. 추적 가능성이 필요한 도메인에서는 선택적 활용

### TODO (논문 완성 전)

- [x] ~~RAPTOR, GraphRAG RAGAS 결과 추가~~
- [x] ~~토큰 비용 실측~~
- [x] ~~트리 빌드 시간/비용 실측~~
- [x] ~~인덱싱 무비용 수정~~
- [x] ~~NRC 투명성 주장 검증~~
- [x] ~~MAM-RAG 제거~~
- [x] ~~10Q Ablation (4 variants)~~
- [x] ~~200Q no_edges ablation~~ → Planning이 핵심, 엣지 정확도 기여 없음
- [x] ~~트리 빌드 토큰 비용 측정~~
- [x] ~~논문 리포지셔닝: Planning 중심으로 전환~~
- [ ] HippoRAG, LightRAG retrieved_contexts 재수집 → RAGAS 완전 비교
