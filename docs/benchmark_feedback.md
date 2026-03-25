# Benchmark Improvement Feedback

Based on v0.4.5 evaluation of 200 questions from `multihop_qa_benchmark_v2.json`, this document summarizes identified limitations and proposed improvements for the next benchmark version.

## Current Benchmark Summary

- 200 questions, 3 reasoning types × 3 complexity levels × 4 modalities
- Source: NuScale FSAR Chapter 01 (352p) + Chapter 05 (160p)
- Evaluated with RAGAs (Faithfulness, Answer Relevancy, Context Recall, Factual Correctness)

## v0.4.5 Results (Baseline for Feedback)

| Metric | Overall | factual | comparative | judgment |
|--------|---------|---------|-------------|----------|
| Faithfulness | 0.93 | 0.91 | 0.92 | 0.95 |
| Answer Relevancy | 0.84 | 0.85 | 0.78 | 0.89 |
| Context Recall | 0.93 | 0.92 | 0.91 | 0.97 |
| Factual Correctness | 0.42 | 0.40 | 0.43 | 0.44 |

---

## Issue 1: Factual Correctness Ceiling (~0.5)

### Problem

FC averages 0.42 despite high Faithfulness (0.93) and Context Recall (0.93). 36 questions (18%) score FC=0 even when agent answers are factually correct.

### Root Cause

RAGAs FC compares agent answer claims against expected answer claims. When agent uses **different evidence nodes** or **different wording**, claims don't match even though both answers are correct.

### Evidence

```
Q003 (FC=0.0):
  Expected: "helical coil steam generators integrated within the RPV"
  Agent:    "vertical helical once-through steam generator with 1,380 tubes"
  → Both correct. Different aspects of the same component.

Q136 (FC=0.33):
  Expected: "587 kg/s flow" + "lower power density" (from Table 5.1-2)
  Agent:    "420°F within 36 hours" (from Figure 5.4-13)
  → Same conclusion ("adequate"), different supporting evidence.

Q138 (FC=0.5):
  Expected: "maximum RTPTS 120.4°F" (32 EFPY row)
  Agent:    "125.9°F" (57 EFPY row)
  → Same table, different row. Question didn't specify which condition.
```

### Proposed Improvements

**1. Comprehensive expected_answer**: Include key facts from ALL valid evidence sources, not just one.

```json
// Before
"expected_answer": "NuScale uses helical coil steam generators integrated within the RPV."

// After
"expected_answer": "NuScale uses helical coil steam generators (also described as vertical, once-through, with 1,380 helical tubes per module) integrated within the reactor pressure vessel."
```

**2. Broader answer_keywords**: Include keywords from all valid perspectives.

```json
// Before
"answer_keywords": ["helical", "coil", "integrated", "RPV"]

// After
"answer_keywords": ["helical", "coil", "integrated", "RPV", "1380", "once-through", "vertical", "tubes"]
```

**3. Source-pinned questions**: When a specific evidence source is intended, reference it in the question.

```json
// Before
"question": "Is the natural circulation design adequate for core heat removal?"

// After
"question": "Based on Table 5.1-2 flow rate data, is the natural circulation design adequate for core heat removal?"
```

**4. Condition-specific questions**: When multiple valid answers exist (different table rows, time periods), specify the condition.

```json
// Before
"question": "What is the maximum RTPTS value for RPV materials?"

// After
"question": "What is the maximum RTPTS value at 57 EFPY according to Table 5.3-8?"
```

---

## Issue 2: Judgment Answer Polarity Bias

### Problem

64/65 judgment questions (98%) have "Yes" as the expected answer. An agent that always outputs "Yes" would score 98% on judgment polarity.

### Root Cause

NuScale FSAR is a **design certification document** — all designs are presented as meeting regulatory requirements. Genuine violations don't exist in the source material.

### Proposed Improvements

**Add hypothetical violation scenarios** (30%+ "No" answers):

```json
{
  "question": "If the NuScale RPV cladding thickness were reduced to 0.10 inches instead of 0.25 inches, would it still satisfy the ASME BPVC requirements for corrosion protection?",
  "expected_answer": "No. The current 0.25-inch cladding provides adequate corrosion protection per ASME standards. Reducing to 0.10 inches would likely be insufficient.",
  "reasoning_type": "judgment"
}
```

This tests whether the agent can **distinguish compliant from non-compliant** conditions, not just confirm compliance.

---

## Issue 3: Evidence Depth — Most Questions Are 2-hop

### Problem

```
1 evidence piece: 57 questions (28%)
2 evidence pieces: 131 questions (66%)
3+ evidence pieces: 12 questions (6%)
```

"Multi-hop" benchmark but only 6% require 3+ evidence pieces.

### Proposed Improvement

Add questions requiring **3-4 evidence chain reasoning**:

```json
{
  "question": "Trace the complete heat removal path from reactor core to ultimate heat sink during a station blackout, identifying all intermediate systems and their design parameters.",
  "ground_truth_evidence": [
    {"source": "Ch.05 p.10", "text": "Core generates 160 MWt..."},
    {"source": "Ch.05 p.12", "text": "Natural circulation transfers heat to SG..."},
    {"source": "Ch.05 p.106", "text": "DHRS removes decay heat via pool..."},
    {"source": "Ch.01 p.15", "text": "No AC/DC power required for 72 hours..."}
  ],
  "complexity": "cross_document",
  "reasoning_type": "factual"
}
```

---

## Issue 4: Document Coverage Imbalance

### Problem

```
Ch.01: evidence from pages 15-81 only (out of 352 pages)
Ch.05: evidence from pages 10-100 (out of 160 pages)
```

Ch.01's Section 1.9 (Conformance with Regulatory Criteria, pages 82-352) contains 727 regulatory compliance items but has almost no questions.

### Proposed Improvement

Add questions from Section 1.9's regulatory compliance tables:

```json
{
  "question": "According to Table 1.9-2, does the NuScale design conform to Regulatory Guide 1.29 for seismic design classification?",
  "ground_truth_evidence": [
    {"source": "Ch.01 p.135", "source_type": "table", "text": "RG 1.29: Conforms..."}
  ]
}
```

---

## Issue 5: Keyword Hit vs FC Tradeoff

### Problem

Concise answers (1-2 sentences, ~386 chars) improve Faith/CR but reduce Keyword Hit (0.65→0.53). Short answers naturally omit secondary keywords.

### Proposed Improvement

Separate **core keywords** (must be present) from **secondary keywords** (nice to have):

```json
{
  "answer_keywords_core": ["570", "MWe"],
  "answer_keywords_secondary": ["12", "modules", "net", "electrical"]
}
```

Evaluation can then report core keyword hit rate separately.

---

## Summary: Priority Ranking

| Priority | Improvement | Impact on FC | Effort |
|----------|-------------|-------------|--------|
| **1** | Comprehensive expected_answer + broader keywords | High (+0.1~0.15 FC estimated) | Medium — rewrite 200 answers |
| **2** | Source-pinned + condition-specific questions | High — reduces ambiguity | Medium — rewrite ~50 questions |
| **3** | Add "No" judgment questions (30%+) | Medium — validates judgment ability | High — requires counterfactual scenarios |
| **4** | Add 3-4 evidence chain questions | Low on FC, high on multi-hop validation | High — new question design |
| **5** | Document coverage expansion (Section 1.9) | Low on FC, broadens evaluation | Medium — new questions from existing content |
