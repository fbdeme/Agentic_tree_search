# LM4Plan Reviewer Simulation (v3 — main.md 기반 정밀 리뷰)

**날짜**: 2026-04-07
**기반**: `research_paper/main.md` 인덱스 + 전체 섹션 교차 검증
**외부 조사**: LM4Plan @ ICAPS 2025 accepted papers, APEX-Searcher, PRISM, Game of Thought

---

## Overall Score: 7/10 (Accept — Minor Revision)

v2(6/10)에서 상향. main.md 기반으로 재검토하니, 논문이 생각보다 잘 구성되어 있음:
- Planning 형식화가 P5에서 체계적 (goal/state/action/goal test)
- 벤치마크 한계를 6.5에서 5가지 자진 인정
- 모달리티 정렬 원칙(P6)이 이론적으로 독자적 기여
- VIOLATES case study(6.3)가 도메인 깊이를 보여줌

**다만 아래 2가지가 해결되어야 confident accept:**
1. Related Work에 agentic retrieval 연구 추가 (W2)
2. Planning 기여 분리를 위한 논의 보강 또는 baseline 추가 (W1)

---

## Summary

원자력 규제 문서(NuScale FSAR)의 멀티홉 QA를 **LLM 기반 planning 문제**로 정의하고, 벡터리스 문서 트리 환경에서 browse/read/search 도구를 통해 정보 수집을 계획하는 아키텍처를 제안. Dynamic Sub-KG로 상태를 유지하고 plan sufficiency로 동적 종료를 제어. 200문항 자체 벤치마크에서 4개 RAG 베이스라인을 상회(81.5%). 200Q ablation에서 edge inference가 정확도에 기여하지 않는 negative finding을 보고.

---

## Strengths

### S1. Planning 프레이밍이 LM4Plan에 매우 적합하고 체계적
(근거: introduction.md P5, method.md 3.3)

LM4Plan의 토픽 "Planning directly with LMs", "validation and verification of plans"에 정확히 부합. 특히:
- P5(intro:77)에서 **goal/state/action/goal test**를 형식적으로 정의 — 단순히 "planning"이라 부르는 수준이 아니라 전통 planning 개념과 명시적으로 매핑
- Method 3.3(method:57)에서 plan sufficiency = goal test라고 명확히 연결
- "인간 전문가의 심사 과정이 곧 계획"(intro:87)이라는 동기가 자연스러움
- **정보 환경에서의 planning**이라는 관점은 PDDL/로봇 중심 기존 연구에 새로운 응용 도메인을 제시

참고: LM4Plan @ ICAPS 2025에서도 [Game of Thought (Cui et al., 2025)](https://arxiv.org/abs/2602.01708)가 "information seeking as strategic planning"을 다뤘으므로, 이 워크샵이 information environment에서의 planning에 열린 태도를 가지고 있음.

### S2. 모달리티 정렬 원칙 (P6)이 이론적으로 독자적 기여
(근거: introduction.md P6:109-133)

- "LLM이 계획을 수립하려면 상태와 환경이 LLM의 네이티브 모달리티(텍스트)여야 한다"는 설계 원칙이 논문의 벡터리스 설계를 단순 엔지니어링 선택이 아닌 **원칙 기반 설계**로 격상시킴
- P6의 비교 테이블(intro:119-124)이 4가지 차원에서 벡터 vs 텍스트를 대조 — 매우 직관적
- "벡터 검색을 tool로 추가하면?"에 대한 사전 대응(intro:130): "architecture와 orthogonal" — 리뷰어의 예상 반론을 차단
- 이 원칙은 이 논문의 도메인을 넘어 **LLM planning 일반에 적용 가능한 인사이트**

### S3. 실험 규모 + 투명한 보고 + 자기 비판적 한계 인정
(근거: experiment.md 전체, 특히 6.5:330-367)

- 200문항 × 6모델 × 2 평가 프레임워크는 워크샵 치고 매우 충실
- 효율성(5.5)에서 Ours가 20배 비싼 것을 숨기지 않고 $/1%p accuracy까지 계산
- **6.5 벤치마크 한계 5가지**(experiment:340-365)가 특히 인상적:
  - judgment 극성 편향(98% "Yes"), 증거 깊이 부족(66%가 2-hop), 외부 검증 부재 등을 자진 인정
  - 단순 인정이 아니라 각 한계의 **원인 분석 + 개선 방향**까지 제시
  - 이 수준의 자기 비판은 학술적 성실성을 보여줌

### S4. Ablation의 정직한 negative finding + VIOLATES case study
(근거: experiment.md 6.1:200-237, 6.3:255-310)

- Edge inference가 정확도에 기여하지 않는다는 200Q ablation 결과를 **핵심 발견**으로 제시 (81.0%→81.5%, 비용 −65%)
- "Planning이 정확도의 핵심 동인"이라는 결론이 데이터로 뒷받침됨
- VIOLATES case study(6.3)는 도메인 깊이를 보여줌:
  - VIOLATES 3건이 "위반"이 아닌 **scope boundary exclusion**(설계 의도적 제외)이라는 분석
  - Q176 NuScale 일체형 SG의 부분 적합성 분석 — 이 수준의 도메인 해석은 단순 RAG 논문에서는 불가능

### S5. 벤치마크 설계가 독자적 기여
(근거: benchmark.md 4.1-4.3)

- 7개 기존 벤치마크와의 체계적 비교(benchmark:5-16)에서 nuclear × multi-hop × multimodal × judgment 조합의 유일성을 입증
- 3축 직교 분류(reasoning × complexity × modality)로 정밀 진단 가능 — "factual × cross_doc × table_only"처럼 약점을 정확히 찝어냄
- 357개 ground truth evidence items (text 152, table 125, figure 80) — 단순 Q&A가 아닌 증거 추적 가능한 설계
- 이중 평가(RAGAS + LLM-as-Judge) 선택의 근거가 명확: 66.2% 일치 → 34% 상호 보완(benchmark:96)

---

## Weaknesses

### W1. (Major) Planning 기여의 실험적 분리가 추가로 필요
(근거: experiment.md 5.3:16-29, 6.1:200-237)

P5에서 planning을 형식적으로 정의하고, ablation에서 edge 제거의 효과를 보여줬지만:

- 현재 비교 구도는 **"Ours (planning agent) vs RAG systems (non-planning)"** — 이 차이가 planning 때문인지, multi-hop retrieval 자체의 효과인지, GPT-4.1의 reasoning 때문인지 불명확
- PageIndex baseline(43.5%)은 browse/read/search 도구를 사용하므로 planning 요소 포함 → "planning 없는" 순수 비교가 아님
- **제안**: 아래 중 하나로 해결 가능:
  - (A) BM25 top-k → generate (planning 없이 단순 검색) baseline 추가
  - (B) 현재 데이터로 "why the gap is due to planning" 논의 강화 — 예: 동적 종료로 avg 2.1-2.6 hops vs 고정 1-hop RAG, browse-first의 CR 0.45→0.89 효과(method:51) 등을 planning contribution으로 명시적 분리 서술

### W2. (Major) 최신 agentic retrieval 연구 누락
(근거: related_works.md 2.2:14-26)

Related Work 2.2가 ReAct, Tree-of-Thought, Toolformer을 다루지만 **직접적 경쟁 연구**가 빠져있음:

- **[APEX-Searcher](https://arxiv.org/abs/2603.13853)** (2025): "Agentic Planning and Execution for search" — RL 기반 plan 생성 + iterative retrieval. HotpotQA, MuSiQue, 2WikiMultiHopQA에서 검증. 이름부터 직접 경쟁.
- **[PRISM](https://arxiv.org/abs/2510.14278)** (2024): precision/recall 분리 에이전틱 retrieval. MuSiQue 등에서 SOTA.
- **[Game of Thought](https://arxiv.org/abs/2602.01708)** (2025): 정보 탐색을 game-theoretic planning으로 정의 — LM4Plan @ ICAPS 2025 accepted paper. **같은 워크샵 시리즈에 제출하면서 이걸 모르면 인상이 좋지 않음.**

**차별화 포인트는 명확**: Ours는 도메인 특화(규제 문서), 벡터리스, edge ontology, vision 포함. APEX-Searcher/PRISM은 범용 벤치마크 + RL/SFT 기반. 이 차별화를 Related Work에 2-3 paragraphs로 추가하면 됨.

### W3. (Minor) Online planning 성격 명시 부족
(근거: introduction.md P5:93-101, method.md 3.3:56-59)

- P5에서 planning loop를 정의했지만, 이것이 **매 스텝 1-step 결정**(online/reactive planning)이라는 점을 명시하지 않음
- plan_next_search()는 다음 1스텝만 결정 — multi-step plan을 미리 생성하지 않음
- LM4Plan 커뮤니티에서 "이것은 classical planning이 아니라 online planning"이라는 질문이 나올 수 있음
- **해결**: Method에 1-2문장 추가: "Our planning loop operates as online planning (closed-loop), where the agent re-plans at each hop based on updated state rather than committing to a fixed multi-step plan. This is appropriate for information environments where the observation space is too large for offline plan enumeration."

### W4. (Minor) 논문 완성도
- 전체가 개조식 메모 상태 → 논문체 변환 필요
- Figure 전혀 없음 — pipeline diagram, tree visualization 등은 이해도를 크게 높일 것

---

## Reviewer Questions

1. **Planning 분리**: browse-first의 CR 0.45→0.89 효과(method:51)와 동적 종료의 hop 절감 효과(method:58)를 planning의 기여로 정량화할 수 있는가? 이 두 가지가 planning의 핵심이라면, 각각을 제거했을 때의 성능이 planning contribution의 upper/lower bound가 될 수 있지 않은가?

2. **APEX-Searcher/PRISM과의 차별화**: 이들은 공인 벤치마크(HotpotQA, MuSiQue)에서 검증됨. Ours의 접근이 이들 벤치마크에서도 동작할 것으로 예상하는가? 만약 도메인 특화만의 가치를 주장한다면, 그 근거는?

3. **Edge inference의 Faithfulness +0.033**: 200Q ablation에서 edge가 정확도에 기여하지 않지만 Faithfulness는 소폭 개선. 이것은 edge가 "답변의 근거성(grounding)"에는 기여한다는 의미인가? 그렇다면 safety-critical 도메인에서 이 0.033의 가치를 어떻게 평가하는가?

---

## 기존 리뷰 대비 수정 사항

| 항목 | v2 | v3 | 이유 |
|------|:--:|:--:|------|
| Overall | 6/10 | **7/10** | main.md로 전체 재확인: P6 원칙, 6.5 한계 인정, VIOLATES case study 가치 재평가 |
| W1 Planning 분리 | Major | **Major** | 유지. 다만 해결 방안 (B) 추가: 기존 데이터로 논의 강화도 가능 |
| W2 관련 연구 | Major | **Major** | 유지 + Game of Thought 추가 (같은 워크샵 시리즈) |
| W3 벤치마크 | Major | **삭제** | 6.5에서 이미 5가지 한계 자진 인정 → 문제 없음 |
| W4 형식화 | Minor | **Minor** (W3으로 재번호) | P5에서 형식 정의 있으나 online planning 명시 필요 |
| 비용 정당화 | Minor | **삭제** | 6.5에서 시스템 한계로 인정 + 동적 종료 효과 제시 |
| S2 모달리티 정렬 | 인정 | **강화** | P6의 비교 테이블과 사전 반론 대응이 독자적 이론 기여 |
| S5 벤치마크 | 미언급 | **신규** | 4.1의 7개 벤치마크 비교 + 3축 설계가 독자적 contribution |

---

## Accept 조건

### 필수 (Minor Revision):
1. **W2**: APEX-Searcher, PRISM, Game of Thought를 Related Work 2.2에 추가 + 차별화 논의 (2-3 paragraphs)
2. **W3**: Method에 "online planning" 1-2문장 추가

### 강력 권장:
3. **W1**: Planning 기여를 기존 데이터로 논의 강화 (browse-first CR +0.44, 동적 종료 hop 절감, 10Q ablation no_browse_first 결과 활용) — 또는 BM25-only baseline 추가
4. **W4**: 개조식 → 논문체 변환, Figure 최소 1-2개

---

## References

- [LM4Plan @ ICML 2026](https://llmforplanning.github.io/ICML26/)
- [LM4Plan @ ICAPS 2025](https://llmforplanning.github.io/)
- [APEX-Searcher (arXiv:2603.13853)](https://arxiv.org/abs/2603.13853)
- [PRISM (arXiv:2510.14278)](https://arxiv.org/abs/2510.14278)
- [Game of Thought (arXiv:2602.01708)](https://arxiv.org/abs/2602.01708)
- [PlanGenLLMs Survey (arXiv:2502.11221)](https://arxiv.org/abs/2502.11221)
