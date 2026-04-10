# Paper Issues

논문의 약점, 리뷰어 예상 질문, 미해결 사항을 추적합니다.
리뷰 시뮬레이션 원본: `docs/supplementary/evaluation_lm4plan_review.md`

---

## Open — Minor

### PISS-001: text_only에서 RAPTOR보다 낮음
- **예상 질문**: text_only에서 왜 RAPTOR(80.0%)보다 Ours(76.2%)가 낮은가?
- **대응**: 재귀적 요약이 텍스트 전용 문항에서 효과적. 나머지 3개 modality에서 Ours 우위.

### PISS-002: 비용 정당화 부족 (W5)
- **예상 질문**: Ours $46 vs RAPTOR $2.3 → 20배, +6%p
- **대응**: 동적 종료로 단순 질문 $0.03. Safety-critical 도메인 논거.

### PISS-003: Factual Correctness 0.42
- **대응**: FC 구조적 한계 (다른 증거 노드 → 다른 표현). LLM-as-Judge가 보완.

### PISS-005: 엣지 존재 이유
- **대응**: 정직한 negative finding. 추적 가능성 필요 시 선택적 활용.

### PISS-011: 자체 벤치마크만 사용
- **심각도**: Minor (Section 6.5에서 5가지 한계를 이미 상세히 인정)
- **대응**: (B) Limitation 명시 + (C) 벤치마크 자체를 contribution으로 포지셔닝

---

## Resolved

### PISS-010: Planning 기여 분리 불명확 (W1) — 해결 (2026-04-10)
- PageIndex baseline(43.5%) 추가로 planning 기여 +38.0%p 분리
- experiment.md §5.2-5.3에 PageIndex 행 추가, §6.1.2에 planning 분리 테이블

### PISS-012: 최신 agentic retrieval 연구 누락 (W2) — 해결 (2026-04-09)
- Section 2.2에 Self-RAG, PRISM, Search-o1, APEX-Searcher, Game of Thought 5편
- ReadAgent, DocAgent, BookRAG 3편 (document navigation 선행연구)
- references.md [38]-[45] 추가

### PISS-013: Planning 용어 정밀화 (W3) — 해결 (2026-04-09)
- Method 3.3에 closed-loop online planning 명시

### PISS-006: 논문 완성도 (W4) — 해결 (2026-04-10)
- 전 섹션 English academic prose 변환 완료
- Title/Abstract 확정
- Figure 4개 삽입 (submodule), hop 분포 추가, 비용 정당화 추가
