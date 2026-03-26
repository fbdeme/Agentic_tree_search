# Experiment Analysis: 3-Axis Evaluation

**Date**: 2026-03-26
**Version**: v0.4.6
**Benchmark**: GWM Benchmark v2 (200 questions)

---

## Overview

| Metric | Value |
|--------|-------|
| LLM-as-Judge Accuracy | **81.0%** (162/200) |
| RAGAs Faithfulness | **0.93** (200/200 measured) |
| RAGAs Context Recall | **0.93** |
| RAGAs Answer Relevancy | **0.84** |
| RAGAs Factual Correctness | 0.42 |
| Total KG Edges | 7,391 (9 types) |

---

## Axis 1: Benchmark Type Analysis

### 9-Cell Matrix — LLM-as-Judge Accuracy

|  | single_evidence | multi_evidence | cross_document |
|--|:-:|:-:|:-:|
| **factual** | 77% (30) | 72% (25) | 73% (15) |
| **comparative** | **100%** (15) | 76% (25) | 68% (25) |
| **judgment** | 80% (5) | 88% (25) | **94%** (35) |

### By Question Type (Modality)

| Type | Accuracy | Faithfulness | AR | CR | FC |
|------|:--------:|:-----------:|:--:|:--:|:--:|
| text_only | 76.2% | 0.911 | 0.891 | 0.924 | 0.373 |
| **table_only** | **86.0%** | **0.969** | 0.844 | 0.900 | **0.508** |
| image_only | 80.0% | 0.950 | 0.773 | **0.967** | 0.361 |
| composite | 85.0% | 0.928 | 0.799 | 0.959 | 0.423 |

**Key Findings:**
- **judgment + cross_document = 94%**: Strongest on regulatory compliance questions requiring evidence from both chapters
- **comparative + single_evidence = 100%**: Perfect on single-source comparison questions
- **table_only = 86%**: Structured table extraction enables accurate numerical retrieval
- **image_only CR = 0.967**: Vision RAG effectively retrieves figure context

---

## Axis 2: Evaluation Framework Cross-Comparison

### RAGAs vs LLM-as-Judge Agreement Matrix

|  | Judge O | Judge X | Total |
|--|:-:|:-:|:-:|
| **RAGAs Good** (Faith≥0.8, CR≥0.8) | 122 | 29 | 151 |
| **RAGAs Bad** | 38 | 9 | 47 |
| Total | 160 | 38 | 198 |

**Agreement rate: 66.2%** (131/198)

### Disagreement Analysis

**RAGAs Good + Judge X (29 cases):**
Agent found correct evidence (Faith=1.0, CR=1.0) but answer wording differed from expected answer. MLflow evaluator is particularly strict on exact phrasing.

Example — Q019:
```
Expected: "the pressurizer volume is 578 ft³"
Agent:    "the pressurizer region volume is 578 ft³ and the cylindrical section is 487 ft³"
RAGAs: Faith=1.00, CR=1.00 (evidence fully grounded)
Judge: tonic=4(O), allganize=1(O), mlflow_sim=2(X), mlflow_corr=3(X) → X
→ MLflow penalizes additional detail ("region", "cylindrical section 487 ft³")
```

**RAGAs Bad + Judge O (38 cases):**
Answer was judged correct by evaluators despite RAGAs showing low context matching. Agent answered correctly from knowledge not captured in KG summary context.

**Interpretation:**
- RAGAs measures **grounding** (is the answer supported by retrieved context?)
- LLM-as-Judge measures **correctness** (does the answer match the expected answer?)
- These are complementary, not redundant. A complete evaluation needs both.

---

## Axis 3: KG Edge Analysis

### Edge Distribution by Reasoning Type

| Type | Avg Edges | SUPPORTS | SPECIFIES | SATISFIES | IS_PREREQ | LEADS_TO | CONTRADICTS |
|------|:---------:|:--------:|:---------:|:---------:|:---------:|:--------:|:-----------:|
| factual | 28 | 31.8% | 34.9% | 6.0% | 6.4% | 0.6% | 0.4% |
| comparative | 35 | 27.6% | 40.0% | 7.4% | 9.8% | 2.0% | 0.3% |
| **judgment** | **48** | **40.7%** | 23.3% | **10.6%** | **11.2%** | 0.3% | 0.3% |

**Key Finding:** judgment questions produce the largest KGs (avg 48 edges) with the highest proportion of SATISFIES (10.6%) and SUPPORTS (40.7%). These semantic edges drive regulatory compliance reasoning.

### Correct (O) vs Incorrect (X) Edge Patterns

| Edge | Correct (O) | Incorrect (X) | Difference |
|------|:-----------:|:-------------:|:----------:|
| **SUPPORTS** | **35.5%** | 28.7% | **+6.8%p** |
| **SATISFIES** | **9.0%** | 5.8% | **+3.2%p** |
| SPECIFIES | 30.0% | **38.4%** | -8.4%p |
| IS_PREREQUISITE_OF | 9.2% | 10.8% | -1.6%p |

**Key Finding:** Correct answers have higher SUPPORTS and SATISFIES proportions, while incorrect answers are dominated by SPECIFIES (structural edges). This confirms that **semantic edges (evidence-based judgment) directly correlate with answer quality**, while structural edges alone are insufficient.

### SATISFIES Count vs Accuracy

| SATISFIES Count | Accuracy | Questions |
|:-:|:-:|:-:|
| 0 | 80.0% | 70 |
| 1-3 | 76.4% | 72 |
| **4-8** | **88.6%** | 35 |
| **9+** | **87.0%** | 23 |

Questions with 4+ SATISFIES edges achieve ~88% accuracy vs ~78% for questions with 0-3. The presence of multiple regulatory compliance judgments in the KG correlates with higher answer quality.

---

## Case Studies

### Case 1: VIOLATES in a Certified Document

**Q058** (factual/cross_document) — 2 VIOLATES edges

The agent identifies that seismic design requirements (GDC 2) apply to safety-related systems but **explicitly do not apply** to non-safety systems (e.g., condensate storage) located outside the Seismic Category I building. This is not a design failure but a **scope exclusion** — the agent correctly captures that regulatory criteria A does not govern system B.

**Q176** (judgment/cross_document) — 1 VIOLATES edge

The agent detects that NuScale's innovative integral SG design creates a **partial conformance** situation: the RCPB leakage detection system doesn't use traditional designed leakage rate components, which impacts full satisfaction of LOCA/SGTR regulatory requirements under DSRS 15.6.5.

**Significance:** VIOLATES edges in a certified document represent scope exclusions and partial conformance — not failures, but nuanced regulatory relationships that simple RAG systems cannot capture.

### Case 2: SATISFIES Driving Judgment Accuracy

**Q184** (judgment/cross_document) — 34 SATISFIES edges, 105 total

Question asks whether eliminated safety systems (Table 1.3-2) are adequately replaced by NuScale's DHRS/ECCS design (Table 5.4-1). The agent builds a KG connecting:
- Ch.01 eliminated systems (AFW, RHR, SIS) → Ch.05 DHRS design parameters
- SATISFIES edges: "DHRS design achieves safe shutdown capability, replacing the function of eliminated AFW system"

The dense SATISFIES network enables a well-grounded "Yes" judgment with specific cross-chapter evidence.

### Case 3: LEADS_TO Causal Chain

**Q112** (comparative/cross_document) — 16 LEADS_TO edges

Question compares electrical output with reactor pool temperature implications. LEADS_TO edges trace:
- Electrical output parameters → DHRS heat removal capacity → reactor pool temperature limits
- Establishing the causal chain: higher power → more decay heat → higher pool temperature demand

### Case 4: Cross-Document SATISFIES

**Q178** (judgment/cross_document) — 14 cross-chapter SATISFIES edges

Question asks if the Rankine cycle (Ch.01) matches SG secondary conditions (Ch.05). Cross-chapter SATISFIES edges connect:
- Ch.01 regulatory requirements for water quality → Ch.05 SG design compliance
- Ch.05 SG tube materials → Ch.01 conformance criteria

### Case 5: RAGAs vs Judge Disagreement

**Q019** — RAGAs Faith=1.0, CR=1.0 but Judge=X

Agent answered "578 ft³" correctly with full evidence grounding, but added "and the cylindrical section is 487 ft³". MLflow evaluator scored similarity=2/5 due to the additional detail. This demonstrates that **RAGAs and LLM-as-Judge measure fundamentally different qualities**: grounding vs. exact-match correctness.

---

## Summary

| Axis | Key Insight |
|------|-------------|
| **Benchmark Types** | System excels at judgment (90.8%) and cross-document (81.3%) — its designed purpose |
| **Evaluation Frameworks** | RAGAs and Judge agree 66.2% — complementary, not redundant |
| **KG Edges** | SUPPORTS/SATISFIES correlate with correctness; SPECIFIES-dominated KGs are less accurate |
