# Known Issues

현재 알려진 문제점과 기술 부채를 추적합니다.

---

## Open

### ISS-004: baseline_comparison_results.md 데이터 구버전
- **발견일**: 2026-04-07
- **설명**: `docs/supplementary/baseline_comparison_results.md`의 HippoRAG(69.0%), LightRAG(67.5%)가 v1 결과. v2에서 HippoRAG 70.5%, LightRAG 73.0%로 변경됨. RAGAs 결과도 미반영.
- **영향**: supplementary 문서와 논문 간 수치 불일치 가능
- **해결 방안**: v2 결과 + 전체 RAGAs 결과로 업데이트 필요 (우선순위 낮음, 논문 기준은 research_paper/)

---

## Resolved

### ISS-001: 결과 파일 위치 불일치 — 해결 (2026-04-07)
- GraphRAG/RAPTOR ragas 결과를 `benchmark/results/{method}/ragas.json`으로 복사
- `benchmark/evaluate_ragas.py` 출력 경로를 `{method}/ragas.json`으로 수정

### ISS-002: 브랜치 데이터 main 미머지 — 해결 (2026-04-07)
- `baseline/lightrag`, `baseline/pageindex` 브랜치를 main에 머지 완료

### ISS-003: 효율성 데이터 누락 — 해결 (2026-04-07)
- pred.json의 retrieved_contexts를 tiktoken으로 측정하여 5문항 샘플 기반 추정
- 인덱싱 비용은 청크 수 × GPT-4.1 단가로 추정
- 전 모델 효율성 테이블 완성 (research_paper/experiment.md Table 5-7)

### ISS-005: PageIndex baseline에 note.md 없음 — 해결 (2026-04-07)
- `benchmark/results/pageindex/note.md` 생성 (환경, 설정, 결과, 특이사항)

### ISS-006: 디렉토리 역할 혼재 — 해결 (2026-04-07)
- 베이스라인 코드 `baseline_experiment/{method}/`로 통일
- 결과는 `benchmark/results/{method}/`로 통일
- CLAUDE.md에 디렉토리 역할 정의 추가
- `docs/supplementary/baseline_experiment_guide.md`에 코드 위치 규칙(Section 8.0) 추가
