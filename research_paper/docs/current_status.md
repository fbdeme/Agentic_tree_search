# Paper Current Status

**최종 갱신**: 2026-04-10

---

## 섹션별 완성도

| 섹션 | 파일 | 상태 | 비고 |
|------|------|:----:|------|
| Title + Abstract | title_abstract.md | **논문체 완료** | 제목 확정, Abstract 수치 검증 완료 |
| 1. Introduction | introduction.md | **논문체 완료** | English prose, contribution 4개 (document-as-environment 중심) |
| 2. Related Work | related_works.md | **논문체 완료** | 2.1-2.7, Agentic IR + document navigation 선행연구 (ReadAgent, DocAgent, BookRAG) |
| 3. Method | method.md | **논문체 완료** | 3.1-3.5, online planning, 도메인 범용성 포지셔닝 추가 |
| 4. Benchmark | benchmark.md | **논문체 완료** | English prose, 4.1-4.4 |
| 5-6. Experiments + Analysis | experiment.md | **논문체 완료** | PageIndex baseline 추가 (§5.2-5.3), planning 분리 테이블 |
| 7. Conclusion | conclusion.md | **논문체 완료** | 도메인 범용성 + FAA/FDA 확장 가능성 추가 |
| References | references.md | **검증 완료** | [32]-[37] 수정, [38]-[42] agentic IR, [43]-[45] doc navigation 추가 |

## 데이터 완료 현황

| 데이터 | 상태 |
|--------|:----:|
| LLM-as-Judge 전 모델 (6개 + PageIndex) | 완료 |
| RAGAs 전 모델 (6개 + PageIndex) | 완료 |
| 10Q Component Ablation | 완료 |
| 200Q no_edges Ablation | 완료 |
| 효율성 비교 | 완료 (일부 추정값 포함) |

## v3 리뷰어 약점 대응 현황

| 약점 | 심각도 | 상태 |
|------|:------:|:----:|
| W1. Planning 기여 분리 | Major | **해결** — PageIndex baseline(43.5% vs 81.5%) + planning 분리 테이블 |
| W2. Agentic retrieval 누락 | Major | **해결** — 5편 + document navigation 3편 추가 |
| W3. Online planning 명시 | Minor | **해결** — closed-loop online planning 명시 |
| W4. 논문 완성도 | Minor | **해결** — 전 섹션 논문체 + Figure 4개 삽입 (submodule) |

## 다음 작업

1. (선택) 리뷰어 시뮬레이션 v5 — v4 수정 반영 후 재평가
2. (선택) Cross-domain pilot (새 실험)
