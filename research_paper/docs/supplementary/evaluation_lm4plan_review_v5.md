# LM4Plan Reviewer Simulation (v5 — v4 피드백 반영 후)

**날짜**: 2026-04-10
**기반**: commit da23c85 (Figure 삽입 + v4 피드백 8건 수정 + main.md 재작성)
**변경점 vs v4**: Figure 4개 삽입(submodule), PageIndex 행동 차이 명시, judgment polarity caveat, hop 분포 실측(mean 3.4, 33% early), 범용성 완화, 비용 정당화, hop count 통일

---

## Overall Score: 8/10 (Accept)

v4(7.5/10)에서 상향. Figure 추가 + hop 분포 정직 보고 + PageIndex 행동 차이 명시가 완성도를 높임.

---

## v4 → v5 변경 근거

| v4 약점 | 심각도 | v5 상태 | 점수 영향 |
|---------|:------:|:-------:|:---------:|
| W1 범용성 미검증 | Medium | **완화됨** — "we hypothesize" + "to be validated" | Minor로 하향 |
| W2 PageIndex 행동 차이 | Medium | **해결** — §5.2에 구체적 의사결정 차이 3문장 | 해소 |
| W3 비용 정당화 | Medium | **해결** — §6.5에 human reviewer 대비 논거 | 해소 |
| W4 Judgment polarity | Minor | **해결** — §5.3에 caveat 추가 | 해소 |
| W5 Hop 분포 | Minor | **해결** — §5.5에 분포 테이블 + 33%/67% 보고 | 해소 |
| W6 Figure 없음 | Minor | **해결** — Figure 4개 삽입 (submodule) | 해소 |

---

## Strengths (v5)

### S1. PageIndex ablation으로 planning 기여 깔끔하게 분리 (강화)
동일 환경 + 도구에서 +38.0%p. §5.2의 행동 차이 설명이 메커니즘을 명확히 함.

### S2. LM4Plan 정합성 + document-as-environment novelty (유지)
Planning 형식화 + 8편 선행연구 대비 차별화 (특히 PageIndex/DocAgent/BookRAG/ReadAgent).

### S3. 투명하고 자기 비판적 평가 (강화)
- Hop 분포 정직 보고 (67% full budget)
- Judgment polarity caveat
- §6.5 벤치마크 한계 5가지
- 비용 20x premium 숨기지 않음 + 도메인 맥락 정당화

### S4. Negative finding (유지)
Edge inference ablation + post-retrieval vs retrieval-time 구분.

### S5. VIOLATES case study (유지)
도메인 깊이 증명.

### S6. 시각적 소통 (신규)
Figure 4개가 아키텍처, 환경, 상태, 벤치마크를 효과적으로 전달.

---

## Weaknesses (v5 — 신규 평가)

### W1. (Medium) 범용성 = 가설
"we hypothesize"로 적절히 완화됨. 그러나 Method §3.1에서 "architecturally domain-agnostic"은 여전히 강한 표현. 새 도메인 실험 없이는 검증 불가.
- **대응**: 이미 최선으로 완화됨. 추가 실험 없이는 더 이상 대응 불가. **수정 불요**

### W2. (Medium) max_hops=4 ceiling 논의 부재
67% full budget → ceiling이 낮은 건지, 4 hops가 충분한 건지 논의 없음.
- **대응**: §6.5에 1-2문장 추가. **지금 가능**

### W3. (Minor) Per-question cost table 출처
Q071 nodes=19/edges=63이 200Q KG 파일(nodes=11/edges=30)과 불일치. 별도 5문항 sample run 출처임.
- **대응**: §5.5에 1문장 provenance 명시. **지금 가능**

### W4. (Minor) Composite 기여 분리 불완전
Vision RAG composite +5.0%p가 planning+vision 혼합. no_vision composite 별도 수치 필요.
- **대응**: 10Q ablation no_vision 데이터 확인 후 가능할 수 있음. **확인 필요**

### Minor Issues

| 위치 | 문제 | 대응 |
|------|------|------|
| §3.3 | Q001 1-hop 문장 중복 | 삭제. **지금 가능** |
| §5.5 | Node/edge 수치 출처 불일치 | Provenance 명시 (W3과 동일) |
| 전체 | 인용 형식 혼재 (author-year vs [Author, Year]) | 통일. **지금 가능** |

---

## 즉시 수정 가능한 항목 (4건)

1. **W2**: max_hops=4 ceiling 논의 (§6.5, 1-2문장)
2. **W3**: Per-question table provenance (§5.5, 1문장)
3. **§3.3 중복 문장** 삭제
4. **인용 형식 통일** (§3, §6에서 [Author, Year] → author-year 또는 역방향)

## 확인 후 가능 (1건)

5. **W4**: 10Q ablation no_vision composite 수치 확인

## 수정 불가 (1건)

6. **W1**: Cross-domain pilot (새 실험 필요, 이미 "hypothesize"로 완화)

---

## Accept 조건 (v5 기준)

### Camera-ready 전 권장:
1. max_hops ceiling 논의 1-2문장 (W2)
2. Per-question table provenance (W3)
3. §3.3 중복 문장 삭제
4. 인용 형식 통일

### 선택적:
5. no_vision composite 수치 추가 (W4)

---

## 전체 점수 추이

| 버전 | 점수 | 주요 변화 |
|:----:|:----:|----------|
| v3 | 7/10 | 초안. Major 2건 (planning 분리, agentic IR 누락) |
| v4 | 7.5/10 | 논문체 + contribution 재구성 + 8편 추가 + PageIndex baseline |
| v5 | **8/10** | Figure 4개 + hop 실측 + 행동 차이 명시 + 비용 정당화. Major 0건 |
