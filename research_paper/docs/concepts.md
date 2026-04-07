# Paper Concepts

논문의 핵심 컨셉, 포지셔닝, 메시지를 정의합니다.

---

## 타겟 학회

- **LM4Plan @ ICML 2026** (마감 4/24)
- LLM 기반 계획(planning) 연구를 다루는 워크샵

## 핵심 포지셔닝

- **문서 탐색 = 계획 문제**: 규제 문서 멀티홉 추론을 LLM 기반 planning 문제로 정의
- **Planning이 정확도의 핵심 동인**: 도구 선택, 동적 종료, browse-first 환경 인식만으로 4개 벡터 기반 RAG 시스템 상회
- **엣지 추론 = 정직한 negative finding**: 200Q ablation에서 post-retrieval edge inference는 정확도에 기여하지 않음 (81.0% → 81.5%, 노이즈 범위). 추적 가능성(traceability)만 제공
- **모달리티 정렬 원칙**: 상태(KG)와 환경(트리)을 LLM의 네이티브 모달리티(텍스트)로 구축 → 임베딩/청킹 없이도 경쟁력 있는 성능

## 핵심 메시지 (한 문장)

> LLM 기반 계획만으로 4개 벡터 기반 RAG 시스템을 상회하며, 정보 환경(문서)에서의 planning은 검색(retrieval)을 대체하는 새로운 패러다임이다.

## 포지셔닝 변경 이력

- **Before (~ 2026-04-03)**: Planning + Verification(edge inference)을 동등한 기여로 제시
- **After (2026-04-04~)**: Planning이 core contribution, Verification은 honest negative finding으로 격하
- **근거**: 200Q no_edges ablation에서 엣지 제거 시 정확도 유지 + 비용 65% 절감

## Related Work에서의 차별화

- GWM [Feng et al., 2025]은 임베딩 기반 암묵적 관계 → Ours는 벡터리스 + LLM 추론 기반 명시적 관계
- 기존 RAG(GraphRAG, LightRAG, RAPTOR, HippoRAG)는 수동적 1회성 검색 → Ours는 능동적 multi-hop planning
