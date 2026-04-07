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
