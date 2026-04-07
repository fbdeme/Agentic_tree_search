# Paper TODO

마감: **2026-04-24 (17일 남음)**

---

## Critical — 이것 없으면 reject

### 1. Planning 기여 분리 (PISS-010)
- [ ] BM25-only baseline 구현: planning 없이 단순 top-k retrieval → generate
- [ ] 결과를 experiment.md Table에 추가
- [ ] "Planning 기여 = Ours - BM25-only" 정량화

### 2. Planning 형식화 (PISS-013)
- [ ] Method에 형식적 정의 추가: State S, Action A, Transition T, Goal G
- [ ] Online planning / reactive planning 으로 정직하게 위치
- [ ] 전통 planning과의 관계 논의 (1-2 paragraphs)

### 3. 최신 관련 연구 추가 (PISS-012)
- [ ] APEX-Searcher, PRISM, Self-RAG 조사 및 Related Work에 추가
- [ ] "Agentic Retrieval" 소절 신설
- [ ] Ours와의 차별화 논의

## High — accept 확률 크게 높임

### 4. 벤치마크 신뢰도 (PISS-011)
- [ ] Limitation에서 자체 벤치마크 한계 명시적 인정
- [ ] 벤치마크 설계 원칙을 contribution으로 강조
- [ ] (시간 여유 시) HotpotQA 소규모 실험 추가

### 5. 논문체 변환 (PISS-006)
- [ ] Introduction 논문체
- [ ] Method 논문체
- [ ] Experiment 논문체
- [ ] Related Work 논문체
- [ ] Conclusion 논문체

### 6. Figure 제작
- [ ] Figure 1: Overall pipeline (planning loop)
- [ ] Figure 2: Document tree + tool interaction
- [ ] Figure 3: Dynamic Sub-KG with edge ontology
- [ ] Figure 4: Benchmark 3-axis design

## Medium

- [ ] 비용 정당화 강화: 오답 사례 위험도 분석 1-2건 (PISS-002)
- [ ] References [32]-[37] 정밀 검증
- [ ] 제목 최종 선택

## Completed

- [x] RAPTOR, GraphRAG RAGAs 결과 추가
- [x] 토큰 비용 실측
- [x] 트리 빌드 시간/비용 실측
- [x] 10Q Ablation (4 variants)
- [x] 200Q no_edges ablation
- [x] 논문 리포지셔닝: Planning 중심으로 전환
- [x] HippoRAG, LightRAG RAGAs 완전 비교 (2026-04-07)
- [x] 리뷰어 시뮬레이션 + 약점 분석 (2026-04-07)
