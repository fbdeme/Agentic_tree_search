# Paper TODO

마감: **2026-04-24 (17일 남음)**
리뷰 시뮬레이션 v3 기준 (7/10, Accept with Minor Revision)

---

## 필수 (Minor Revision — 이것 없으면 reject 위험)

### 1. Related Work에 agentic retrieval 추가 (W2)
- [ ] APEX-Searcher (arXiv:2603.13853) 조사 + 차별화
- [ ] PRISM (arXiv:2510.14278) 조사 + 차별화
- [ ] Game of Thought (arXiv:2602.01708) — LM4Plan @ ICAPS 2025 accepted
- [ ] Related Work 2.2에 "Agentic Information Retrieval" 소절 추가 (2-3 paragraphs)
- [ ] 차별점: Ours = 도메인 특화 + 벡터리스 + edge ontology + vision vs 이들 = 범용 + RL/SFT

### 2. Online planning 명시 (W3)
- [ ] Method에 1-2문장 추가: online planning / closed-loop 임을 명시

## 강력 권장 (accept 확률 높임)

### 3. Planning 기여 논의 강화 (W1)
- [ ] 기존 데이터로 planning contribution 분리 서술:
  - browse-first: CR 0.45 → 0.89 (+0.44) — method.md:51
  - 동적 종료: avg 2.1-2.6 hops (max 4) — method.md:58
  - 10Q no_browse_first: 9/10 (Q191 실패) — experiment.md:127
  - PageIndex only (43.5%): planning 도구는 있으나 KG 상태 평가 없음
- [ ] (선택) BM25-only baseline 추가 실험

### 4. 논문체 변환 + Figure (W4)
- [ ] Introduction → 논문체
- [ ] Method → 논문체
- [ ] Experiment → 논문체
- [ ] Related Work → 논문체
- [ ] Conclusion → 논문체
- [ ] Figure 1: Overall pipeline (planning loop)
- [ ] Figure 2: 최소 1개 추가 (tree/KG/benchmark 중 택1)

## Medium

- [ ] 제목 최종 선택
- [ ] References [32]-[37] 정밀 검증
- [ ] Abstract의 81.5% → HippoRAG v2(70.5%), LightRAG v2(73.0%) 반영 확인

## Completed

- [x] RAGAs 전 모델 완료 (2026-04-07)
- [x] 논문 리포지셔닝: Planning 중심 (2026-04-04)
- [x] 리뷰어 시뮬레이션 v1→v2→v3 (2026-04-07)
- [x] main.md 논문 구조 인덱스 작성 (2026-04-07)
- [x] 벤치마크 한계 인정 → 6.5에서 5가지 (이미 완료)
