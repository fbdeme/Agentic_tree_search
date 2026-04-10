# Main — Paper Structure Index

논문 전체 구조를 한 눈에 파악하기 위한 인덱스.
각 섹션의 핵심 주장, 주요 수치, 리뷰어 대응 포인트를 기록.

---

## title_abstract.md (30 lines)

**제목 후보** (line 10):
- 정식: *LLM-Guided Planning for Multi-hop Regulatory Document Exploration*
- 대안 1: *Document Exploration as Planning: ...*
- 대안 2: *Planning with LLMs in Information Environments: ...*

**Abstract 핵심** (line 20-27):
- 문제: FSAR 심사 = planning under uncertainty
- 제안: LLM planning loop in vectorless document tree
- 결과: **81.5%** (vs RAPTOR 75.5%, HippoRAG 69.0%, LightRAG 67.5%, GraphRAG 49.5%)
- 발견: edge inference는 정확도 기여 없음 → planning이 핵심 동인

---

## introduction.md (157 lines)

### P1 (line 5): LLM 에이전트 성공 + 과학 도메인 확장
- ReAct, Toolformer, Self-RAG 인용
- 과학 도메인: GAIA(가속기), VISION(빔라인), ChemCrow(화학), NukeBERT/NuclearQA(핵)
- Osprey [Hellert, 2026]: safety-critical 에이전트의 투명성 문제 지적

### P2 (line 24): 규제 문서의 구조적 특성 — 기존 RAG 실패 이유
- NuScale FSAR: Ch.01(352p) + Ch.05(160p) = 17개 장 중 2개
- 심사관 업무 = 멀티홉 증거 연쇄 → 규제 적합성 판단 (ECCS 예시)
- RAG 실패 3가지: 청킹 파괴, 판단 미생성, 정적 인덱싱

### P3 (line 45): 안전-임계 도메인 요건 — 투명성/감사
- **10 CFR 50 Appendix B, Criterion III**: 독립적 검증 가능한 문서화 요구
- 임베딩 유사도 → 기술적 정당화 미제공 vs 텍스트 기반 근거 경로 → 검증 가능
- ⚠️ 리뷰어 대응: NRC는 AI 특화 규제 미제정, 일반 QA 원칙의 적용 논의 (line 52)

### P4 (line 58): 요구사항 종합 테이블
- 6개 요건: 멀티홉, 구조보존, 멀티모달, 판단생성, 추적가능성, 경량인덱싱
- ⚠️ "인덱싱 무비용"이 아닌 "경량 인덱싱" ($4.06) — 주석에서 명시 (line 74)

### P5 (line 77): ★ Planning 형식 정의
- **goal**: 근거 있는 판단 도출
- **state**: 수집된 증거 + 관계 (Dynamic Sub-KG)
- **action**: browse/read/search 도구 선택
- **goal test**: plan sufficiency (동적 종료, avg 2.1–2.6 hops)
- **verification**: SATISFIES/VIOLATES 판단 (선택적)
- Planning loop 테이블 (line 93): State estimation → Action planning → Execution → Sufficiency
- 비용 변동: Q001 1hop $0.03 vs Q191 4hops $0.29
- ★ edge inference = 정확도 기여 없음 (81.0%→81.5%), 비용 2.8× (line 105)

### P6 (line 109): 모달리티 정렬 원칙 (벡터리스 근거)
- 설계 원칙: State & Environment를 LLM 네이티브 모달리티(텍스트)에 정렬
- 비교 테이블 (line 119): 벡터 표현 ❌ vs 텍스트 표현 ✅ (4가지)
- "벡터 검색 tool 추가하면?" → architecture와 orthogonal (line 130)
- PageIndex 트리: $4.06 / 7.6–19.8분, 5–7× 빠름

### P7 (line 143): 기여 5가지
1. Planning 문제 정의 → 81.5% (4개 RAG 상회)
2. 모달리티 정렬 벡터리스 설계
3. Vision-augmented 멀티모달 (table_only +18%p)
4. 200Q 3축 벤치마크 (최초 nuclear × multi-hop × multimodal × judgment)
5. Edge inference 비용 대비 효과 분석 (negative finding)

---

## related_works.md (60 lines)

### 2.1 RAG (line 3): GraphRAG, LightRAG, RAPTOR, HippoRAG
- LightRAG → Ours Stage 1 영감 (free-form relation extraction)
- RAPTOR → PageIndex와 구조 유사하나 사전 인덱싱/동적 탐색 없음

### 2.2 Agentic Information Retrieval (line 14): ★ 신규 추가
- Self-RAG [38]: 토큰 단위 반응적 검색, 명시적 계획 없음
- PRISM [39]: 3-에이전트, precision/recall 분리, 반복 수렴 종료
- Search-o1 [40]: 추론 중간 동적 웹 검색, EMNLP 2025
- APEX-Searcher [41]: RL+SFT 하이브리드, 가장 직접적 경쟁 연구
- Game of Thought [42]: 게임 이론 기반 정보 탐색, LM4Plan @ ICAPS 2025
- ★ 차별점: training-free + 도메인 특화 + 벡터리스 + edge ontology + vision
- ReadAgent [43]: 페이지 gist + lookup, 계층 구조/KG 없음
- DocAgent [44]: XML outline 탐색, KG state/동적 종료 없음
- BookRAG [45]: 계층 인덱스 + 쿼리 라우팅, planning loop 없음
- PageIndex: 프롬프트 기반 단일 패스 트리 탐색 vs Ours: 환경으로서의 트리 + 에이전트 루프

### 2.3 Planning & Agent (line 25): ReAct, Tree-of-Thought, Toolformer, GWM
- ★ 차별점: 기존은 PDDL/로봇/웹 → Ours는 **정보 환경**(규제 문서)

### 2.4 KG for RAG: 동적 KG, 엣지 온톨로지 학술적 기원 6개
### 2.5 Multimodal RAG: DocVQA/ChartQA (단일 이미지) vs Ours (multi-hop+multimodal)
### 2.6 Nuclear NLP: NuclearQA, NukeBERT
### 2.7 RAG Evaluation: RAGAS, LLM-as-Judge

---

## method.md (84 lines)

### 3.1 Environment (line 5): 벡터리스 문서 트리
- JSON 계층 트리, BM25Okapi, title 가중치 3×
- 멀티모달 참조 링크 (figure/table on different page 해결)
- 스케일: Ch.01 866 nodes, Ch.05 26 nodes

### 3.2 State (line 14): Dynamic Sub-KG + 2티어 엣지
- $s_t = G_t = (V_t, E_t)$, 신뢰도 ≥ 0.4
- Tier 1 구조: REFERENCES, SPECIFIES
- Tier 2 의미: SATISFIES/VIOLATES, SUPPORTS/CONTRADICTS, LEADS_TO, IS_PREREQUISITE_OF
- 경험적: 정답에서 SUPPORTS +6.8%p, SATISFIES +3.2%p (상관, 인과 아님)

### 3.3 Action Planning (line 40): ★ LLM 도구 선택
- 3가지 tool: browse(ls), read(cat), search(grep)
- Browse-first: Hop 1에서 TOC 자동 주입 → CR 0.45→0.89
- PRF (RM3): 쿼리 자동 확장, LLM 비용 0
- Agent memory: 키워드 중복 방지
- ★ Plan sufficiency = **goal test** (line 57): 매 홉 충분성 판단 → 동적 종료
  - avg 2.1–2.6 hops, 불필요한 탐색 자동 가지치기

### 3.4 Edge Inference (line 61): 선택적 컴포넌트
- ★ "200Q ablation에서 정확도 기여 없음" 명시 (line 64)
- Stage 1: 자유형 기술 (LightRAG 방식)
- Stage 2: 온톨로지 매핑 (SATISFIES 등), 불가 시 SEMANTIC 보존
- Planning loop 내 인터리빙 (후처리 아님)

### 3.5 Vision (line 73): 최종 답변 1회만 멀티모달
- PyMuPDF → JPEG → GPT-4.1 vision
- 표: find_tables() → 구조화 텍스트 (VLM 불필요) → table_only 86.0% (+18%p)

---

## benchmark.md (99 lines)

### 4.1 기존 벤치마크 한계 (line 3): 7개 벤치마크 비교 테이블
- ★ 기존에 nuclear × multi-hop × multimodal × judgment 조합 없음
- NuclearQA: nuclear but ❌ multi-hop/judgment
- FDARxBench: regulatory + judgment but ❌ multimodal

### 4.2 설계 원칙 (line 23): 3축 직교 분류
- reasoning × complexity × modality = 독립 3차원
- judgment × cross_doc = 35문항 (실제 심사 핵심)
- Ground truth: 357 evidence items (text 152, table 125, figure 80)

### 4.3 상세 구성 (line 46): 200문항 분포
- factual 70, comparative 65, judgment 65
- text_only 80, table_only 50, image_only 30, composite 40

### 4.4 이중 평가 (line 76): RAGAS + LLM-as-Judge
- RAGAS-Judge 일치율 66.2% → 34% 불일치가 상호 보완적
- 3-평가자: Tonic(GPT-4-turbo), MLflow(GPT-4o), Allganize(Claude Sonnet 4.5)

---

## experiment.md (367 lines)

### 5.1 설정 (line 1): GPT-4.1, temp 0, max_tokens 300
### 5.2 베이스라인 (line 8): RAPTOR, HippoRAG, LightRAG, GraphRAG 상세

### 5.3 LLM-as-Judge 결과 (line 16): ★ 핵심 테이블
- **Ours (planning only) 81.5%** > RAPTOR 75.5% > LightRAG 73.0% > HippoRAG 70.5% > GraphRAG 49.5%
- judgment: Ours 92.3% = RAPTOR 92.3% (동률)
- table_only: Ours **86.0%** vs RAPTOR 68.0% (+18%p)
- cross_doc: Ours **84.0%** vs RAPTOR 73.3% (+10.7%p)

### 5.4 RAGAs (line 31): 전 모델 비교
- Ours: Faith 0.93, CR 0.93 (압도적 1위)
- GraphRAG: Faith 0.28, CR 0.18 (최저)
- reasoning_type별 상세 (line 53): judgment Faith **0.97**, CR **0.96**

### 5.5 효율성 (line 66): Tables 5-7
- 인덱싱: Ours **$4.1, 8-20분** vs GraphRAG $3.3/40분, LightRAG $7.0/52분
- 쿼리: Ours **$42/310분** vs RAPTOR $0.9/6분 (20배 비쌈)
- $/1%p accuracy: Ours $0.56 vs RAPTOR $0.03
- 문항별 변동 (line 101): Q001 $0.03 (1hop) vs Q191 $0.29 (4hops)

### 6.1 Ablation (line 125): ★ 핵심 발견
- **10Q 4-variant** (line 127): full 10/10, no_vision 8/10, no_edges 9/10, no_browse_first 9/10
  - no_edges: 비용 −66%, 시간 −67%
- **200Q planning vs planning+edges** (line 200):
  - ★ no_edges **81.5%** vs full 81.0% → **엣지 제거 시 정확도 유지/소폭 상승**
  - 비용 $0.076 vs $0.215 (−65%)
  - ★ "Planning이 정확도의 핵심 동인"

### 6.2 엣지 분포 (line 238): 7,391 edges
- SUPPORTS 34.3%, SPECIFIES 31.5%, REFERENCES 13.1%
- VIOLATES 0.04% (3건) — 인증 문서이므로 정상

### 6.3 Case Study (line 255): VIOLATES 3건 분석
- VIOLATES = 위반이 아닌 **scope boundary exclusion** (설계 의도적 제외)
- Q058: 비안전등급 설비의 내진 scope 제외 (정상 설계)
- Q176: NuScale 일체형 SG의 부분 적합성 (혁신 설계 trade-off)
- ★ 이 분석은 단순 RAG에서 불가능한 nuance

### 6.4 이중 평가 보완성 (line 320): RAGAS-Judge 일치 66.2%
- RAGAS good + Judge X (29건): 정확한 증거, 표현 불일치
- RAGAS bad + Judge O (38건): context 밖 지식으로 정답

### 6.5 한계 (line 330): ★ 이미 상세히 인정
- **시스템 한계**: text_only −3.8%p vs RAPTOR, 문항당 $0.21, follow_ref 미구현
- **벤치마크 한계 5가지** (line 340):
  1. FC 상한 ~0.42 (expected_answer 단일 관점)
  2. Judgment 극성 편향 (98% "Yes")
  3. 증거 깊이 부족 (66%가 2-hop)
  4. 문서 커버리지 불균형 (Ch.01 19%)
  5. ★ **외부 검증 부재** — 편향 가능성 명시 + 완화 요인 설명 (line 362)

---

## conclusion.md (17 lines)

1. Planning = accuracy driver (81.5%, 4개 RAG 상회)
2. 모달리티 정렬 원칙 유효 (벡터리스 경쟁력)
3. Edge inference = 선택적 (accuracy 0%, cost −65%)
4. 경량 인덱싱 ($4.06, 5-7× fast)
- LM4Plan 시사점: 정보 환경에서의 planning 유효, retrieval 대체 패러다임

---

## references.md (47 lines)

- 총 37개 인용, ✅ 대부분 검증됨
- ⚠️ PageIndex [24]: 오픈소스, 학술 논문 없음
- ⚠️ [32]-[37]: 벤치마크 비교 인용, 정밀 검증 필요
- ⚠️ **누락**: APEX-Searcher, PRISM, Self-RAG (→ Related Work에 추가 필요)
