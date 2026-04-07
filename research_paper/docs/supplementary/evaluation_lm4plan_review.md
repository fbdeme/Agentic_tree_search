# LM4Plan Reviewer Simulation (v2)

**날짜**: 2026-04-07
**시뮬레이션**: LM4Plan @ ICML 2026 리뷰어 관점에서 자체 평가
**v2 변경**: 전체 섹션(Intro P1-P7, Method 3.1-3.5, Related Work 2.1-2.6, Benchmark, Experiment, Conclusion) 정밀 재검토 반영

---

## Overall Score: 6/10 (Weak Accept — 조건부)

v1에서 5/10으로 평가했으나, Introduction P5의 planning formalization과 Method 3.3의 plan sufficiency/goal test 등을 재확인하여 상향. 다만 여전히 아래 약점들이 해결되어야 accept.

---

## Summary

원자력 규제 문서(NuScale FSAR)의 멀티홉 질의응답을 LLM 기반 planning 문제로 정의. 벡터리스 문서 트리 환경에서 browse/read/search 도구를 통해 정보 수집을 계획하고, Dynamic Sub-KG로 상태를 유지하며, 동적 종료로 탐색 깊이를 조절. 200문항 자체 벤치마크에서 4개 RAG 베이스라인을 상회하며, ablation에서 edge inference가 정확도에 기여하지 않는 negative finding을 보고.

---

## Strengths

### S1. Planning 프레이밍이 워크샵에 매우 적합
- LM4Plan의 "Planning directly with LMs", "validation and verification of plans"에 정확히 부합
- **정보 환경에서의 planning**이라는 관점은 PDDL/로봇 중심 기존 연구에 신선한 도메인 확장
- Introduction P5에서 goal/state/action/goal test를 명시적으로 정의하고, "인간 전문가의 심사 과정이 곧 계획"이라는 동기가 설득력 있음

### S2. 모달리티 정렬 원칙 (P6)이 이론적으로 흥미
- "LLM이 계획을 수립하려면 상태와 환경이 LLM의 네이티브 모달리티(텍스트)여야 한다"는 설계 원칙이 명확
- P6의 비교 테이블(벡터 vs 텍스트 표현)이 직관적으로 설득력 있음
- "벡터 검색을 tool로 추가하면?"에 대한 사전 대응이 있음 (architecture와 orthogonal)
- 이 원칙은 정보 검색 분야에서의 planning 연구에 일반적으로 적용 가능한 인사이트

### S3. 실험 규모와 비교의 성실함
- 200문항 × 6개 모델 × 2개 평가 프레임워크(LLM-as-Judge + RAGAs)는 워크샵 치고 충실
- 전 모델 RAGAs를 맞추려고 재실험까지 한 점, 공정 비교 조건(동일 LLM, 동일 프롬프트) 명시
- Section 5.5 효율성 비교에서 불리한 비용(Ours $46 vs RAPTOR $2.3)까지 투명하게 보고

### S4. Ablation의 정직한 negative finding
- Edge inference가 정확도에 기여하지 않는다는 발견을 핵심 결과로 제시
- "Planning drives accuracy, edges provide only traceability"는 명확한 takeaway
- 이 발견은 LM4Plan 커뮤니티에서 "verification의 실제 가치는 무엇인가?"라는 유의미한 논의를 촉발할 수 있음

### S5. 도메인 동기와 요구사항 분석이 체계적
- P2(규제 문서 현실) → P3(안전-임계 요건) → P4(요구사항 종합 테이블)의 흐름이 논리적
- 10 CFR 50 Appendix B 인용, Osprey/Lee 선행 연구와의 연결이 구체적
- P4의 6개 요구사항이 설계 결정과 직접 연결됨

---

## Weaknesses

### W1. (Major) Planning 기여의 정량적 분리가 불완전
**수정된 평가**: P5에서 planning을 형식적으로 정의하고, Method 3.3에서 plan sufficiency = goal test라고 명시한 점은 인정. 그러나:

- Ours(81.5%) vs 베이스라인들의 차이가 **planning 때문인지, multi-hop retrieval 자체 때문인지, GPT-4.1의 reasoning 능력 때문인지** 실험적으로 분리되지 않음
- PageIndex baseline(43.5%)은 browse/read/search 도구를 사용 → planning 요소 이미 포함. 이것은 "planning 없는" baseline이 아님
- **필요**: planning 없이 단순 BM25 top-k retrieval → generate 하는 순수 retrieval baseline
- 이것이 있으면 "Planning contribution = Ours(81.5%) - BM25-only(?%)" 으로 정량화 가능
- 현재는 4개 RAG 시스템이 이미 나름의 retrieval strategy를 갖고 있어서, 차이가 planning인지 retrieval quality인지 구분 어려움

### W2. (Major) 최신 agentic retrieval 연구 누락
Related Work 2.1-2.2가 기존 RAG + planning 프레임워크를 다루지만, **직접적 경쟁 연구**가 빠져 있음:

- **APEX-Searcher** (arXiv:2603.13853, 2025): "Agentic Planning and Execution for search" — 이름부터 직접적 경쟁. RL 기반 plan 생성 + multi-hop retrieval. 공인 벤치마크(HotpotQA, MuSiQue)에서 검증
- **PRISM** (arXiv:2510.14278, 2024): agentic retrieval로 multi-hop QA — precision/recall 분리 에이전트 설계. MuSiQue 등에서 SOTA
- 이들은 "planning for information retrieval"을 이미 다루고 있으며, Ours와의 차별화(도메인 특수성, 벡터리스, edge ontology)를 논의해야 함
- Section 2.2에 "Agentic Information Retrieval" 소절 추가 필요

### W3. (Major) 자체 벤치마크만의 평가
- 200문항 직접 제작/평가 → 편향 가능성을 완전히 배제할 수 없음
- APEX-Searcher, PRISM은 HotpotQA, MuSiQue, 2WikiMultiHopQA 등 공인 벤치마크 사용
- 도메인 특수성은 이해하지만:
  - (a) 벤치마크 설계 원칙(3축 직교, Section 4)을 더 강조하여 contribution으로 포지셔닝하거나
  - (b) Limitation에서 명시적으로 인정하거나
  - (c) 시간 여유 시 HotpotQA 소규모 실험 추가
- 현재 Section 4가 상당히 상세하므로 (a)가 가장 현실적

### W4. (Minor) Planning 형식화 — 부분적으로 해결됨
**v1에서 Critical로 평가했으나 Major→Minor로 하향**:
- P5에서 goal/state/action/goal test를 정의하고, Method 3.3에서 plan sufficiency를 goal test로 연결
- 다만 "매 스텝 1-step 결정"이므로 전통적 planning(multi-step plan 생성)보다는 **online planning / closed-loop planning**에 가까움
- 이를 논문에서 명시적으로 인정하고, 전통 planning과의 관계를 1-2문장으로 논의하면 충분

### W5. (Minor) 비용 정당화
- $/1%p accuracy 테이블이 오히려 불리하게 작용 (Ours $0.56 vs RAPTOR $0.03)
- Safety-critical 도메인 논거가 있으나, 오답의 구체적 위험도 분석이 있으면 더 설득적

---

## Reviewer Questions

1. BM25 top-k retrieval만으로(planning 없이) 답변 생성했을 때 성능은? 이 데이터가 있어야 planning의 기여가 분리됩니다.
2. APEX-Searcher, PRISM과의 차별점은? 이들도 planning + multi-hop retrieval을 다룹니다.
3. plan_next_search()가 다음 1스텝만 결정하는 것이라면, 이것이 전통적 의미의 "planning"인지? online planning으로 포지셔닝하는 것이 더 정확하지 않은지?

---

## 개선 우선순위 (수정)

| 순위 | Weakness | 난이도 | 영향 | 제안 |
|:----:|----------|:------:|:----:|------|
| 1 | W1: Planning 분리 | 중 | Major | BM25-only baseline 추가 |
| 2 | W2: 관련 연구 | 하 | Major | APEX-Searcher, PRISM 추가 + 차별화 논의 |
| 3 | W3: 벤치마크 | 하 | Major | Section 4를 contribution으로 강조 + Limitation 인정 |
| 4 | W4: Planning 용어 | 하 | Minor | "online planning" 1-2문장 추가 |
| 5 | W5: 비용 | 하 | Minor | 오답 위험도 사례 1건 추가 |

---

## Accept 조건

1. W1(BM25 baseline) 또는 최소한 "왜 이 비교가 planning 기여를 보여주는지"에 대한 추가 논의
2. W2(APEX-Searcher, PRISM) Related Work 추가
3. W3에 대한 명시적 대응 (Limitation 또는 벤치마크 contribution 강화)

위 3가지가 해결되면 **7/10 (Accept)** 가능.

---

## References

- [LM4Plan @ ICML 2026](https://llmforplanning.github.io/ICML26/)
- [LM4Plan @ ICAPS 2025](https://llmforplanning.github.io/)
- [APEX-Searcher (arXiv:2603.13853)](https://arxiv.org/abs/2603.13853)
- [PRISM (arXiv:2510.14278)](https://arxiv.org/abs/2510.14278)
- [PlanGenLLMs Survey (arXiv:2502.11221)](https://arxiv.org/abs/2502.11221)
- [Self-RAG (arXiv:2310.11511)](https://arxiv.org/abs/2310.11511)
