# RAPTOR Baseline 구현 노트

## 환경
- LLM (생성): gpt-4.1
- LLM (요약/인덱싱): gpt-4.1
- 임베딩: text-embedding-3-small
- Chunk size: 512 tokens (tiktoken cl100k_base, overlap=50)

## 인덱싱
- 방법: PDF → 토큰 청크 → UMAP(10d) + GMM soft clustering → 클러스터별 gpt-4.1 요약 → 재귀적 3레벨 트리
- 소요 시간: (기록 예정)
- 인덱스 크기: (기록 예정)
- 총 노드 수: (기록 예정) — 리프: ?, 요약: ?

## 검색 설정
- 검색 모드: collapse_tree  (모든 레벨 flat 검색)
- Top-K: 5
- 임베딩 사전 계산: 인덱스 로드 시 전체 노드 임베딩 캐시

## 결과
- Accuracy: (기록 예정)%
- by reasoning_type:
  - factual:     ?%
  - comparative: ?%
  - judgment:    ?%

## 특이사항
- (실행 후 기록)
