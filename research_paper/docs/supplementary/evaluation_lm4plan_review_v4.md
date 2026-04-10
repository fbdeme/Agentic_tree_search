# LM4Plan Reviewer Simulation (v4 — 논문체 변환 + 기여 재구성 후)

**날짜**: 2026-04-10
**기반**: 전 섹션 English prose 변환 완료본 (commit f2007b0)
**변경점 vs v3**: 전 섹션 논문체 변환, Contribution 재구성 (document-as-environment), Related Work 8편 추가 (agentic IR 5 + doc navigation 3), PageIndex baseline 추가, 도메인 범용성 포지셔닝, References 검증

---

## Overall Score: 7.5/10 (Accept — Minor Revision)

v3(7/10)에서 상향. 논문체 변환 + 기여 재구성 + 선행연구 보강이 완성도를 높임.

---

## v3 약점 대응 현황

| v3 약점 | 심각도 | v4 상태 | 대응 내용 |
|---------|:------:|:-------:|----------|
| W1. Planning 기여 분리 | Major | **해결** | PageIndex baseline(43.5%) 추가 → 동일 환경+도구에서 +38.0%p planning 기여 분리. §6.1.2에 3-mechanism 분리 테이블 |
| W2. Agentic retrieval 누락 | Major | **해결** | §2.2에 Self-RAG, PRISM, Search-o1, APEX-Searcher, Game of Thought + ReadAgent, DocAgent, BookRAG 8편 추가 |
| W3. Online planning 명시 | Minor | **해결** | Method §3.3에 closed-loop online planning 명시 |
| W4. 논문 완성도 | Minor | **대부분 해결** | 전 섹션 English prose. Figure 미완 (팀원 진행 중) |

---

## Strengths

### S1. LM4Plan 정합성 — 정보 환경에서의 planning (유지)
Planning 형식화(goal/state/action/goal test)가 체계적. Game of Thought과 같은 워크숍 시리즈 인식.

### S2. PageIndex ablation이 planning 기여를 깔끔하게 분리 (신규)
동일 환경 + 동일 도구에서 KG state management 유무만으로 43.5% → 81.5% (+38.0%p). 가장 설득력 있는 실험 근거.

### S3. 정직한 negative finding (유지)
200Q edge ablation. Post-retrieval vs retrieval-time edge 구분이 리뷰어 예상 반론 사전 차단.

### S4. 충실한 평가 + 자기 비판 (유지)
200Q × 6 methods × 2 frameworks. §6.5 벤치마크 한계 5가지 자진 인정.

### S5. VIOLATES case study (유지)
Scope boundary exclusion 분석. 도메인 깊이 증명.

### S6. 선행연구 포지셔닝 (강화)
Agentic IR 5편 + document navigation 3편. PageIndex와의 차별점 (프롬프트 기반 vs 환경) 명확화. Contribution 1이 "document as text-based environment for agentic exploration"으로 재구성되어 novelty가 더 명확.

---

## Weaknesses (신규 평가)

### W1. (Major) 범용성 주장은 있으나 검증 없음
Method §3.1과 Conclusion에서 "domain-agnostic", FAA/FDA 확장 가능성을 언급하나 단일 도메인 평가. Cross-domain pilot 없음.
- **대응**: 표현 완화 ("we expect" → "we hypothesize") — 텍스트 수정으로 즉시 가능

### W2. (Medium) PageIndex baseline 행동 차이가 구체적이지 않음
§5.2에서 "without the agent's Dynamic Sub-KG state management"라고만 설명. 구체적으로 어떤 프롬프트/의사결정 차이인지 불명확.
- **대응**: 2-3문장 추가로 즉시 가능

### W3. (Medium) 비용 정당화 부족
$46 vs RAPTOR $2.3 (20x). Safety-critical 도메인 논거가 있으나 구체적 cost-benefit 부재.
- **대응**: 규제 도메인 맥락의 비용 논거 2-3문장 추가로 즉시 가능

### W4. (Minor) Judgment polarity bias의 결과 해석 영향 미언급
98% "Yes" 편향을 §6.5에서 인정하나, §5.3 결과 해석에서 이 caveat 없음. RAPTOR도 judgment 92.3% 동률.
- **대응**: §5.3에 1문장 caveat 추가로 즉시 가능

### W5. (Minor) Dynamic termination 서사 vs 실제 hop 분포
Mean 3.6 hops (max 4) → 대부분 거의 전체 예산 사용. "동적 종료" 기여가 과장될 수 있음.
- **대응**: pred.json에서 hop 분포 추출하여 보고 — 데이터 확인 후 가능

### W6. (Minor) Figure 없음
Pipeline diagram, KG 예시 등 없음. 이해도 저하.
- **대응**: 팀원 진행 중

---

## Minor Issues

| 위치 | 문제 | 대응 |
|------|------|------|
| §5.3 PageIndex row | table_only, composite = "—" | 데이터 없는 이유 명시 필요 |
| §6.1.2 planning table | "avg 2.1-2.6 hops" vs §5.5 "mean 3.6" | 수치 출처 명확화 or 통일 |
| Method §3 서두 | `> **Overall pipeline**` 내부 메모 잔존 | 제거 또는 Figure로 대체 |
| 전체 | 인용 형식 혼재 (author-year vs [38]-[45]) | 통일 필요 |

---

## 즉시 수정 가능한 항목 (7건)

1. **W2**: PageIndex 행동 차이 명시 (§5.2, 2-3문장)
2. **W4**: Judgment polarity bias caveat (§5.3, 1문장)
3. **Hop count 불일치**: 2.1-2.6 vs 3.6 정리
4. **W1**: 범용성 표현 완화 (Conclusion)
5. **W3**: 비용 정당화 (§5.5 or §6.5, 2-3문장)
6. **PageIndex "—"**: 설명 추가 (§5.3, 1문장)
7. **Pipeline overview**: Method §3 내부 메모 제거

## 데이터 확인 후 가능 (1건)

8. **W5**: Hop 분포 보고 (pred.json 분석)

## 팀원/시간 필요 (2건)

9. Figure 제작 (팀원 진행 중)
10. Cross-domain pilot (새 실험, 선택적)

---

## v3 → v4 점수 변동 근거

| 항목 | v3 | v4 | 이유 |
|------|:--:|:--:|------|
| Overall | 7/10 | **7.5/10** | v3 Major 2건(W1, W2) 모두 해결. 논문체 완성. Contribution 재구성으로 novelty 명확화 |
| W1 Planning 분리 | Major | **해결** | PageIndex 43.5% → +38.0%p 분리 |
| W2 관련 연구 | Major | **해결** | 8편 추가 |
| 논문 완성도 | Minor | **대부분 해결** | Figure만 남음 |
| 신규 W1 범용성 | — | **Medium** | 주장만 있고 검증 없음 (표현 완화로 대응 가능) |
| 신규 W2 PageIndex 설명 | — | **Medium** | 행동 차이 구체화 필요 |

---

## Accept 조건 (v4 기준)

### Must fix:
1. PageIndex 행동 차이 명시 (W2)
2. Judgment polarity caveat (W4)
3. Hop count 불일치 해소
4. Figure 최소 1개

### Strongly recommended:
5. 범용성 표현 완화 (W1)
6. 비용 정당화 (W3)
7. Hop 분포 보고 (W5)
