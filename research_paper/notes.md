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
- [x] ~~HippoRAG, LightRAG retrieved_contexts 재수집 → RAGAS 완전 비교~~ (2026-04-07, 6개 모델 전체 RAGAs 완료)
- [ ] 효율성 비교 (Section 5.5): HippoRAG/LightRAG 쿼리 비용 데이터 보완
- [ ] LightRAG v2(73.0%), HippoRAG v2(70.5%) 결과로 Section 5.3 세부 축별 테이블 업데이트
