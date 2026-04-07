# LM4Plan Reviewer Simulation

**날짜**: 2026-04-07
**시뮬레이션**: LM4Plan @ ICML 2026 리뷰어 관점에서 자체 평가

---

## Overall Score: 5/10 (Borderline)

---

## Summary

규제 문서(NuScale FSAR)에서 멀티홉 질의응답을 LLM 기반 planning loop으로 해결하는 시스템을 제안. 벡터리스 트리 환경에서 browse/read/search 도구를 선택하고, 동적 종료 조건으로 탐색을 제어. 200문항 자체 벤치마크에서 4개 RAG 베이스라인 대비 우위를 보이며, ablation으로 edge inference가 정확도에 기여하지 않음을 발견.

---

## Strengths

### S1. Planning 프레이밍이 워크샵 토픽에 적합
LM4Plan이 명시한 "Planning directly with LMs", "validation and verification of plans"에 정확히 부합. 정보 수집을 planning 문제로 재정의한 관점은 PDDL/로봇 중심의 기존 연구에 신선한 도메인 확장.

### S2. 실험 규모와 비교의 성실함
200문항 × 6개 모델 × 2개 평가 프레임워크(LLM-as-Judge + RAGAs)는 워크샵 논문 치고 상당히 충실. 특히 전 모델 RAGAs를 맞추려고 재실험까지 한 점은 공정 비교에 대한 의지가 보임.

### S3. Ablation의 정직한 negative finding
Edge inference가 정확도에 기여하지 않는다는 발견을 숨기지 않고 핵심 결과로 제시한 것은 학술적으로 가치 있음. "Planning drives accuracy, edges provide only traceability"는 명확한 takeaway.

### S4. 도메인 특수성
원자력 규제 문서라는 safety-critical 도메인은 LLM planning의 실용적 적용 사례로서 의미 있음.

---

## Weaknesses

### W1. (Critical) Planning 기여의 분리가 불명확 — 개선 필요
"Planning이 핵심"이라고 주장하지만, planning의 어떤 요소가 기여하는지 분리되지 않음.

- Ours(81.5%) vs RAPTOR(75.5%)의 +6%p가 planning 때문인지, multi-hop retrieval 때문인지, GPT-4.1 reasoning 때문인지 구분 불가
- PageIndex baseline(43.5%)도 browse/read/search 도구를 사용 → planning 요소 이미 포함
- **필요한 ablation**: (1) planning 없이 단순 BM25 top-k → generate, (2) planning은 있되 도구가 search만, (3) 현재 시스템

**개선 상태**: [ ] 미착수

### W2. (Critical) 자체 벤치마크 + 자체 평가 = 신뢰도 문제 — 개선 필요
- 200문항 직접 제작, 직접 평가 → 편향 가능성
- HotpotQA, MuSiQue, 2WikiMultiHopQA 같은 공인 벤치마크 결과가 전혀 없음
- APEX-Searcher, PRISM 등 최신 연구는 모두 공인 벤치마크 사용
- 최소 1-2개 공인 벤치마크에서의 generalizability 검증이 없으면 일반적 주장 불가

**개선 상태**: [ ] 미착수

### W3. (Major) 최신 관련 연구 누락 — 개선 필요
누락된 직접적 경쟁 연구:
- **APEX-Searcher** (arXiv:2603.13853, 2025): RL 기반 agentic planning + multi-hop retrieval
- **PRISM** (arXiv:2510.14278, 2024): agentic retrieval, precision/recall 분리 설계
- **Search-o1** (2025): agentic search + reasoning
- **Self-RAG** (arXiv:2310.11511, 2024): 자기 반성 기반 적응적 검색

RAPTOR/GraphRAG/LightRAG/HippoRAG만 비교하는 것은 "RAG vs Ours"이지 "agentic planning vs Ours"가 아님.

**개선 상태**: [ ] 미착수

### W4. (Major) Planning 형식화(formalization)의 부재 — 개선 필요
LM4Plan 커뮤니티의 핵심 관심사는 planning의 형식적 특성:
- State space 정의, action space 정의, goal 조건, plan의 soundness/completeness
- 현재 시스템: state=KG(비형식적), action=tool selection(프롬프트), termination="sufficient"(LLM 주관적)
- 매 스텝 현재 상태만 보고 다음 행동 결정 → **reactive agent에 가까움, plan 생성 없음**
- "이게 planning인가?"라는 근본적 질문이 제기될 수 있음

**개선 상태**: [ ] 미착수

### W5. (Minor) 비용 정당화 부족
- Ours $46 vs RAPTOR $2.3 → 20배 비용, +6%p 향상
- Safety-critical 주장은 이해하지만 정량적 근거(오답 위험도 분석 등) 없음

**개선 상태**: [ ] 미착수

### W6. (Minor) 논문 완성도
- 전체가 개조식 메모 상태 → 논문체 변환 필요
- Figure 전혀 없음

**개선 상태**: [ ] 미착수

---

## Reviewer Questions

1. browse/read/search 도구 선택 없이 단순 BM25 retrieval → answer generation만 했을 때 성능은?
2. HotpotQA나 MuSiQue에서 이 시스템을 돌릴 계획이 있나요?
3. plan_next_search()가 여러 스텝을 미리 계획하나요, 아니면 다음 1스텝만 결정하나요?

---

## 개선 우선순위

| 순위 | Weakness | 난이도 | 영향 | 제안 |
|:----:|----------|:------:|:----:|------|
| 1 | W1: Planning 분리 | 중 | Critical | BM25-only baseline 추가 실험 |
| 2 | W4: Planning 형식화 | 중 | Major | Method에 형식적 정의 추가, reactive vs deliberative 논의 |
| 3 | W3: 관련 연구 | 하 | Major | APEX-Searcher, PRISM 등 Related Work에 추가 |
| 4 | W2: 공인 벤치마크 | 상 | Critical | HotpotQA 실험 추가 (시간 제약 시 limitation으로 인정) |
| 5 | W6: 논문 완성도 | 중 | Minor | 개조식 → 논문체, Figure 제작 |
| 6 | W5: 비용 정당화 | 하 | Minor | 오답 사례 위험도 분석 1-2건 추가 |

---

## References

- [LM4Plan @ ICML 2026](https://llmforplanning.github.io/ICML26/)
- [LM4Plan @ ICAPS 2025](https://llmforplanning.github.io/)
- [APEX-Searcher (arXiv:2603.13853)](https://arxiv.org/abs/2603.13853)
- [PRISM (arXiv:2510.14278)](https://arxiv.org/abs/2510.14278)
- [PlanGenLLMs Survey (arXiv:2502.11221)](https://arxiv.org/abs/2502.11221)
- [Self-RAG (arXiv:2310.11511)](https://arxiv.org/abs/2310.11511)
