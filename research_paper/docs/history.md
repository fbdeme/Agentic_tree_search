# Paper History

논문 작성 과정의 주요 변경 이력을 기록합니다.

---

## 2026-04-07 — 구조 정리 + RAGAs 완료

- `docs/paper_draft.md` → `research_paper/` 섹션별 분리
- `research_paper/docs/` 관리 문서 체계 도입 (concepts, current_status, todo, issues, history)
- 전 모델 RAGAs 평가 완료 (6개): GraphRAG, RAPTOR, HippoRAG, LightRAG, PageIndex, Ours
- GWM → Ours 표기 변경 (논문 리포지셔닝 반영)

## 2026-04-04~06 — 논문 리포지셔닝

- 200Q no_edges ablation 결과: 엣지 추론 제거 시 정확도 유지 (81.0% → 81.5%), 비용 65% 절감
- **포지셔닝 전환**: Planning + Verification 동등 기여 → Planning이 core, Verification은 negative finding
- 구체적 조치:
  - 제목에서 Verification 제거 또는 격하
  - Abstract: Planning이 core, edges는 analysis result로 보고
  - Section 6 ablation을 주요 근거로 승격
  - Conclusion: "Planning drives accuracy; Verification provides traceability but NOT accuracy"

## 2026-04-03 — 초안 작성

- `docs/paper_draft.md` 첫 초안 작성 (개조식)
- 타겟: LM4Plan @ ICML 2026 (마감 4/24)
- Section 1-7 + References + 작성 메모 포함
- 벤치마크 비교 (Section 4.1), 인용 검증, 효율성 실측 포함

## 2026-03-31 — 베이스라인 비교 완료

- 4개 베이스라인 LLM-as-Judge 결과 수집 완료
- `docs/baseline_comparison_results.md` 통합 문서 작성
- `docs/baseline_experiment_guide.md` v2 작성
