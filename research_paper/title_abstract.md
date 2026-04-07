# [초안] 규제 문서 멀티홉 탐색을 위한 LLM 기반 계획

> **상태**: 초안 (개조식 흐름 정리용)  
> **작성일**: 2026-04-03 (최종 수정: 2026-04-06)  
> **타겟**: LM4Plan @ ICML 2026 (마감 4/24)  
> **검증된 인용만 사용** — 미확인 인용은 ⚠️ 표시

---

## 논문 제목 (후보)

- **정식**: *LLM-Guided Planning for Multi-hop Regulatory Document Exploration*
- **대안 1**: *Document Exploration as Planning: LLM-Guided Information Gathering in Vectorless Tree Environments*
- **대안 2**: *Planning with LLMs in Information Environments: Multi-hop Reasoning for Nuclear Regulatory Documents*

---

## Abstract (초안)

- 핵발전소 안전 분석 보고서(FSAR) 심사는 수만 페이지에서 증거를 순차적으로 수집하고 규제 적합성을 판단하는 과정 → 본질적으로 **불확실한 정보 환경에서의 계획 문제(planning under uncertainty)**
- 기존 RAG 기반 시스템은 이 과정을 수동적 1회성 검색으로 환원 → 단일 hop 한계, 구조 파괴, 판단 부재
- **제안**: LLM이 벡터리스 문서 트리 환경에서 **정보 수집을 계획(plan)**하는 아키텍처
  - **Planning loop**: 상태 평가(Dynamic Sub-KG) → 행동 선택(browse/read/search) → 충분성 판단(동적 종료)의 반복
  - **모달리티 정렬**: 상태와 환경을 LLM의 네이티브 모달리티(텍스트)로 구축하여 계획 수립 가능하게 함
  - **Vision**: PDF 원본 도면/표를 GPT-4.1 vision으로 직접 해석
- **결과**: 200문항 멀티홉 벤치마크에서 LLM-as-Judge 81.5% — RAPTOR(75.5%), HippoRAG(69.0%), LightRAG(67.5%), GraphRAG(49.5%) 대비 최고; RAGAS Faithfulness 0.90
- **분석**: 200Q ablation에서 post-retrieval 엣지 추론(verification)은 정확도에 기여하지 않음(81.0%→81.5%) — planning(도구 선택, 동적 종료)이 정확도의 핵심 동인이며, 엣지는 추적 가능성만 제공

---
