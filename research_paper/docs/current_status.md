# Paper Current Status

**최종 갱신**: 2026-04-07

---

## 섹션별 완성도

| 섹션 | 파일 | 상태 | 비고 |
|------|------|:----:|------|
| Title + Abstract | title_abstract.md | 초안 완료 | 제목 후보 3개, 최종 선택 필요 |
| 1. Introduction | introduction.md | 초안 완료 | P1-P7 개조식 흐름 |
| 2. Related Work | related_works.md | 초안 완료 | 2.1-2.6, 인용 검증 완료 |
| 3. Method | method.md | 초안 완료 | 3.1-3.5, 엣지를 선택적 컴포넌트로 재정의 |
| 4. Benchmark | benchmark.md | 초안 완료 | 4.1-4.4, 3축 직교 설계 |
| 5-6. Experiments + Analysis | experiment.md | **데이터 보완 필요** | RAGAs 전 모델 완료, 효율성 비교 일부 누락 |
| 7. Conclusion | conclusion.md | 초안 완료 | Planning 중심 결론 |
| References | references.md | 검증 중 | [32]-[37] 정밀 검증 필요 |

## 데이터 완료 현황

| 데이터 | 상태 |
|--------|:----:|
| LLM-as-Judge 전 모델 (6개) | 완료 |
| RAGAs 전 모델 (6개) | 완료 (2026-04-07) |
| 10Q Component Ablation | 완료 |
| 200Q no_edges Ablation | 완료 |
| 효율성 비교 (Ours) | 완료 (5문항 샘플 실측) |
| 효율성 비교 (베이스라인) | **일부 추정값** (HippoRAG ~3초, LightRAG ~5초는 note.md 기반) |
| LightRAG/HippoRAG v2 축별 테이블 | 반영 완료 (2026-04-07 확인) |

## 다음 작업

1. experiment.md Section 5.5 효율성 비교 데이터 보완
2. experiment.md Section 5.3 LightRAG v2(73.0%), HippoRAG v2(70.5%) 결과 반영
3. references.md [32]-[37] 정밀 검증
4. 제목 최종 선택
5. 전체 흐름 검토 (개조식 → 논문체 변환)
