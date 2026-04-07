# Known Issues

현재 알려진 문제점과 기술 부채를 추적합니다.

---

## Open

### ISS-001: 결과 파일 위치 불일치
- **발견일**: 2026-04-07
- **설명**: `baseline_experiment_guide.md`에서는 `benchmark/results/{method}/ragas.json`에 저장하도록 정의했으나, 실제 GraphRAG/RAPTOR RAGAs 결과는 `experiments/results/eval/eval_ragas_{method}_*.json`에 타임스탬프 이름으로 저장됨
- **영향**: 결과 파일 탐색이 어렵고, 자동화 스크립트가 결과를 못 찾음
- **해결 방안**: 기존 결과를 가이드 위치로 복사/이동, 평가 스크립트 출력 경로를 `benchmark/results/{method}/ragas.json`으로 변경



### ISS-003: 효율성 데이터 누락
- **발견일**: 2026-04-07
- **설명**: HippoRAG/LightRAG pred.json에 `retrieval_time_sec`, `generation_time_sec`, 토큰 필드 없음. 논문 Section 5.5 효율성 비교 테이블 대부분 공란
- **영향**: 논문 효율성 비교 불완전
- **해결 방안**: 5문항 샘플 실측으로 추정값 산출

### ISS-004: baseline_comparison_results.md 데이터 구버전
- **발견일**: 2026-04-07
- **설명**: `docs/baseline_comparison_results.md`의 HippoRAG(69.0%), LightRAG(67.5%)가 v1 결과. v2에서 HippoRAG 70.5%, LightRAG 73.0%로 변경됨. RAGAs Section 9도 미완료 상태 그대로
- **영향**: 논문에 구버전 수치 사용 위험

### ISS-005: PageIndex baseline에 note.md 없음
- **발견일**: 2026-04-07
- **설명**: PageIndex only baseline에 구현 노트가 없음. 실험 환경, 설정, 특이사항 미기록
- **영향**: 재현성 부족

### ISS-006: baseline_experiment / benchmark / experiments 디렉토리 역할 혼재
- **발견일**: 2026-04-07
- **설명**: 베이스라인 관련 파일이 3곳에 분산되어 있음
  - `baseline_experiment/` — RAPTOR 코드 + 스크립트 + 결과 (RAPTOR 전용)
  - `benchmark/` — 평가 스크립트 + 전 모델 결과 (가이드 기준 정규 위치)
  - `experiments/` — GWM 전용 실행/평가 + GraphRAG/RAPTOR RAGAs 결과가 여기에도 있음
- **영향**: 결과 파일 찾기 어려움, 가이드와 실제 구조 불일치
- **해결 방안**: 
  - 결과는 `benchmark/results/{method}/`로 통일 (가이드 기준)
  - `baseline_experiment/`는 RAPTOR 코드 전용으로 유지, 결과는 `benchmark/results/raptor/`만 참조
  - `experiments/results/eval/`의 베이스라인 ragas 결과는 `benchmark/results/`로 이동 완료 (ISS-001)
  - 장기적으로 CLAUDE.md에 디렉토리 역할 정의 추가 필요

---

## Resolved

### ISS-001: 결과 파일 위치 불일치 — 해결 (2026-04-07)
- GraphRAG/RAPTOR ragas 결과를 `benchmark/results/{method}/ragas.json`으로 복사
- `benchmark/evaluate_ragas.py` 출력 경로를 `{method}/ragas.json`으로 수정
- PageIndex pred 파일명 `pred_q200.json` → `pred.json` 복사

### ISS-002: 브랜치 데이터 main 미머지 — 해결 (2026-04-07)
- `baseline/lightrag`, `baseline/pageindex` 브랜치를 main에 머지 완료
- HippoRAG/LightRAG v2 pred+judge, PageIndex pred+judge+run_baseline.py 통합됨
