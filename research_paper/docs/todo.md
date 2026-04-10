# Paper TODO

마감: **2026-04-24 (14일 남음)**
리뷰 시뮬레이션 v3 기준 (7/10, Accept with Minor Revision)

---

## 남은 작업

- [ ] Figure 1: Overall pipeline (planning loop) — 팀원(kimmbk) 진행 중
- [ ] Figure 2: 최소 1개 추가 (tree/KG/benchmark 중 택1) — 팀원 진행 중
- [ ] (선택) 리뷰어 시뮬레이션 v4 재평가

---

## Completed

### Phase 1: 내용 보강 (2026-04-09)
- [x] Related Work에 agentic retrieval 추가 (W2): Self-RAG, PRISM, Search-o1, APEX-Searcher, Game of Thought
- [x] Online planning 명시 (W3): Method 3.3에 closed-loop online planning
- [x] Planning 기여 논의 강화 (W1): planning 분리 테이블 + agentic retrieval 비교

### Phase 2: 논문체 변환 (2026-04-09)
- [x] Introduction, Method, Experiment, Related Work, Conclusion → English academic prose

### Phase 3: Introduction 재구성 (2026-04-10)
- [x] Introduction 테이블/이모지 제거 → 순수 prose 스타일
- [x] Contribution 재구성: "Document as text-based environment for agentic exploration" 중심

### Phase 4: 마무리 (2026-04-10)
- [x] Benchmark (Section 4) 논문체 변환
- [x] 제목 확정: "LLM-Guided Planning for Multi-hop Regulatory Document Exploration"
- [x] Abstract 수치 검증 (HippoRAG 70.5%, LightRAG 73.0%, Faith 0.93)
- [x] References [32]-[37] 검증 및 수정 (4건 저자/제목 오류)
- [x] 전체 통독 교정 (9건 수치/cross-ref/인용 형식 수정)
- [x] References 한국어/이모지 제거

### Phase 5: 기여 포인트 정립 + 선행연구 보강 (2026-04-10)
- [x] Document-as-environment 선행연구 검증 (PageIndex, DocAgent, ReadAgent, BookRAG)
- [x] Related Work §2.2에 ReadAgent [43], DocAgent [44], BookRAG [45] 추가
- [x] PageIndex와의 차별점 명시 (프롬프트 기반 단일패스 vs 환경 + 에이전트 루프)
- [x] Contribution 1 재정의: document as scalable text-based environment + agentic online planning
- [x] 도메인 범용성 포지셔닝 (Method §3.1 + Conclusion)
- [x] PageIndex baseline을 §5.2-5.3에 추가 (43.5% → planning 기여 +38.0%p 분리)
