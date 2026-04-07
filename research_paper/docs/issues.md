# Paper Issues

논문의 약점, 리뷰어 예상 질문, 미해결 사항을 추적합니다.
리뷰 시뮬레이션 원본: `docs/supplementary/evaluation_lm4plan_review.md`

---

## Open — Critical

### PISS-010: Planning 기여 분리 불명확 (W1)
- **심각도**: Critical
- **문제**: "Planning이 핵심"이라고 주장하지만, planning vs multi-hop retrieval vs GPT-4.1 reasoning 기여가 분리 안 됨
- **현재 상태**: PageIndex baseline(43.5%)이 있지만 이것도 browse/read/search 도구 사용 → planning 포함
- **필요 조치**: BM25-only baseline 추가 (planning 없이 단순 top-k retrieval → generate)
- **난이도**: 중 (run_baseline.py에 BM25-only 모드 추가)

### PISS-011: 자체 벤치마크만 사용 (W2)
- **심각도**: Critical
- **문제**: 200문항 직접 제작/평가 → 편향 가능성. 공인 벤치마크(HotpotQA, MuSiQue) 결과 없음
- **대응 옵션**:
  - (A) HotpotQA에서 실험 추가 — 시간 소요 큼
  - (B) Limitation에서 명시적으로 인정 + 도메인 특수성 강조
  - (C) 벤치마크 자체를 contribution으로 포지셔닝 (설계 원칙 상세 기술)
- **권장**: 마감 고려 시 (B)+(C) 조합

## Open — Major

### PISS-012: 최신 agentic retrieval 연구 누락 (W3)
- **심각도**: Major
- **누락 연구**:
  - APEX-Searcher (arXiv:2603.13853) — RL 기반 agentic planning + retrieval
  - PRISM (arXiv:2510.14278) — precision/recall 분리 agentic retrieval
  - Search-o1 — agentic search + reasoning
  - Self-RAG (arXiv:2310.11511) — 자기 반성 기반 적응적 검색
- **필요 조치**: Related Work Section 2.1에 "Agentic Retrieval" 소절 추가, 차별화 논의
- **난이도**: 하 (문헌 조사 + 2-3 paragraphs)

### PISS-013: Planning 형식화 부재 (W4)
- **심각도**: Major
- **문제**: state/action/goal 형식적 정의 없음. 현재 시스템은 reactive agent에 가까움 (매 스텝 1-step 결정)
- **LM4Plan 커뮤니티 우려**: "이게 정말 planning인가?"
- **대응 옵션**:
  - (A) Method에 형식적 정의 추가 (S, A, T, G 정의)
  - (B) "Planning as information gathering"이라는 관점에서 전통 planning과의 관계 논의
  - (C) Reactive planning / online planning으로 재포지셔닝
- **권장**: (A)+(C) — 형식적 정의를 제시하되, online planning으로 정직하게 위치

## Open — Minor

### PISS-001: text_only에서 RAPTOR보다 낮음
- **예상 질문**: text_only에서 왜 RAPTOR(80.0%)보다 Ours(76.2%)가 낮은가?
- **대응**: 재귀적 요약이 텍스트 전용 문항에서 효과적. 나머지 3개 modality에서 Ours 우위.

### PISS-002: 비용 정당화 부족 (W5)
- **예상 질문**: Ours $46 vs RAPTOR $2.3 → 20배, +6%p
- **대응**: 동적 종료로 단순 질문 $0.03. Safety-critical 도메인 논거. 오답 사례 위험도 분석 1-2건 추가하면 강화됨.

### PISS-003: Factual Correctness 0.42
- **대응**: FC 구조적 한계 (다른 증거 노드 → 다른 표현). LLM-as-Judge가 보완.

### PISS-004: 벤치마크 편향 → PISS-011로 통합

### PISS-005: 엣지 존재 이유
- **대응**: 정직한 negative finding. 추적 가능성 필요 시 선택적 활용.

### PISS-006: 논문 완성도 (W6)
- 개조식 → 논문체 변환 필요
- Figure 1-4 제작 필요

---

## Resolved

(아직 없음)
