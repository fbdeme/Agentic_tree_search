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
