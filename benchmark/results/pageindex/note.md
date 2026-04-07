# PageIndex (without KG) Baseline 구현 노트

## 환경
- LLM: gpt-4.1 (생성)
- 라이브러리: 자체 구현 (src/agent, src/environment 기반)
- Python: 3.12
- 검색: BM25 + PRF, tool-based exploration (browse/read/search)

## 방법
- Our agent와 동일한 PageIndex 탐색을 수행하되, **KG edge 추론(Transition) 단계를 완전 생략**
- 노드 수집만 수행, 관계 추론 없음 → Pure retrieval baseline
- `benchmark/run_baseline.py --method pageindex` 로 실행

## 인덱싱
- Ours와 동일: PageIndex 트리 사용 (사전 구축 완료)
- 별도 인덱싱 불필요

## 검색 설정
- max_hops: 4
- top_k: 2
- 동적 종료 (sufficient 판단)
- browse-first 패턴 적용

## 결과
- **LLM-as-Judge Accuracy: 43.5% (87/200)**
- factual: 25.7% (18/70)
- comparative: 44.6% (29/65)
- judgment: 61.5% (40/65)
- single_evidence: 40.0% (20/50)
- multi_evidence: 44.0% (33/75)
- cross_document: 45.3% (34/75)

## 효율성
- 문항당 평균 시간: 13.3초
- 200문항 총 시간: 44.2분
- retrieval: 11.6초/문항, generation: 1.7초/문항

## 특이사항
- KG 없이 retrieval만으로는 43.5%에 그침 → Ours(81.0%)와의 차이(37.5%p)는 agentic planning + edge inference 기여
- judgment 유형에서 상대적으로 높은 성능(61.5%) — 문서 구조 탐색만으로도 판단형 질문에 일정 수준 대응 가능
- 18건의 문항에서 retrieved_contexts가 비어있음 (검색 실패)

## 스크립트
- `benchmark/run_baseline.py` (`--method pageindex`)
