# Paper Structure Index

**Title**: LLM-Guided Planning for Multi-hop Regulatory Document Exploration
**Venue**: LM4Plan @ ICML 2026 (Deadline: April 24, 2026)
**Status**: All sections in English academic prose. 4 figures inserted. Reviewer v4 feedback addressed.

---

## Core Thesis

Regulatory document review is a planning problem, not a retrieval problem. By constructing documents as text-based environments with defined action interfaces, LLM agents can perform closed-loop online planning that outperforms vector-based RAG systems — and post-retrieval edge inference adds no accuracy benefit.

## Key Numbers

| Metric | Value |
|--------|-------|
| Overall accuracy (planning only) | **81.5%** |
| Best baseline (RAPTOR) | 75.5% |
| PageIndex (same env, no planning) | 43.5% |
| Planning contribution (vs PageIndex) | **+38.0%p** |
| Edge inference effect on accuracy | **0%p** (81.0% → 81.5%) |
| Edge inference cost overhead | **+2.8x** (65% of per-query cost) |
| Faithfulness | 0.93 |
| Context Recall | 0.93 |
| Indexing cost | $4.1, 8–20 min |
| Dynamic termination rate | 33% terminate early (mean 3.4 hops, max 4) |

---

## Section-by-Section Summary

### title_abstract.md — Title & Abstract

- **Title**: LLM-Guided Planning for Multi-hop Regulatory Document Exploration
- **Abstract**: FSAR review as planning under uncertainty → LLM plans over vectorless document tree → 81.5% accuracy vs 4 baselines → edge inference = no accuracy gain, planning = primary driver

### introduction.md — Section 1: Introduction

**Structure**: 7 paragraphs flowing from background → domain problem → our insight → contributions

1. **Background**: LLM agents succeed in general domains (ReAct, Toolformer, Self-RAG). Scientific domain applications emerging (GAIA, VISION, ChemCrow, NukeBERT, NuclearQA).
2. **Domain gap**: Safety-critical domains fundamentally differ. Osprey [Hellert, 2026]: missing transparency. Lee [2025]: LLM black-box vs 10 CFR 50 App B.
3. **FSAR review reality**: NuScale FSAR Ch.01 (352p) + Ch.05 (160p). Core task = multi-hop evidence chains → SATISFIES/VIOLATES judgment. ECCS example. Knowledge in expert practice, not software.
4. **RAG failures**: Chunking destroys cross-references. GraphRAG/LightRAG don't generate judgments. Static indexing incompatible with continuous FSAR revision. 10 CFR 50 App B requires traceable technical basis — embeddings can't provide this.
5. **Key insight**: Regulatory review is a **planning problem** (goal/state/action/goal test). Human review = ReAct-like loop. LLM as agent of planning, not consumer of retrieval.
6. **Our approach**: Document as text-based environment with action interfaces (browse/read/search). Closed-loop online planning with KG state + dynamic termination. Distinct from PageIndex (prompt-based) and BookRAG/DocAgent (query routing). Optional edge inference (SATISFIES/VIOLATES ontology).
7. **Contributions** (4 items):
   1. Document as text-based environment for agentic exploration → 81.5% (vs PageIndex 43.5%, RAPTOR 75.5%)
   2. Vision-augmented multimodal (+18%p on table_only)
   3. 200Q nuclear regulatory benchmark (3-axis orthogonal)
   4. Edge inference cost-accuracy analysis (negative finding)

### related_works.md — Section 2: Related Work

| Section | Topic | Key References | Our Differentiation |
|---------|-------|---------------|-------------------|
| 2.1 | RAG | GraphRAG, LightRAG, RAPTOR, HippoRAG | All require offline indexing; no judgment generation |
| 2.2 | Agentic IR | Self-RAG, PRISM, Search-o1, APEX-Searcher, Game of Thought | Training-free, domain-specific, vectorless |
| 2.2 (cont.) | Document navigation | ReadAgent, DocAgent, BookRAG, PageIndex | Ours = formal environment + closed-loop planning + KG state + dynamic termination |
| 2.3 | Planning & Agents | ReAct, ToT, Toolformer, GWM | Information environment (not PDDL/robot/web) |
| 2.4 | KG for RAG | Dynamic KG, edge ontology precedents | Query-time KG construction; domain-specific edge types |
| 2.5 | Multimodal RAG | DocVQA, ChartQA | Multi-hop + multimodal (not single-image) |
| 2.6 | Nuclear NLP | NuclearQA, NukeBERT | Multi-hop judgment (not single-hop factual) |
| 2.7 | RAG Evaluation | RAGAS, LLM-as-Judge | Dual framework for complementarity |

### method.md — Section 3: Method

**Figure 1**: Overall pipeline (planning loop)

| Section | Component | Key Details |
|---------|-----------|-------------|
| 3.1 | Environment | JSON hierarchical tree, BM25Okapi (title 3x weight), vectorless. Multimodal reference links (figure-on-different-page solved). Ch.01: 866 nodes, Ch.05: 26 nodes. **Figure 2**: Tree + tools + reference resolution |
| 3.2 | State (Dynamic Sub-KG) | $G_t = (V_t, E_t)$. Tier 1 structural (REFERENCES, SPECIFIES). Tier 2 semantic (SATISFIES/VIOLATES, SUPPORTS/CONTRADICTS, LEADS_TO, IS_PREREQUISITE_OF). Confidence >= 0.4. **Figure 3**: KG example + edge distribution |
| 3.3 | Action Planning | Closed-loop online planning (not offline plan-then-execute). Three tools: browse(ls), read(cat), search(grep). Browse-first at Hop 1 (CR 0.45→0.89). PRF/RM3 query expansion. Agent memory. Dynamic termination (goal test): 33% early termination, mean 3.4 hops |
| 3.4 | Edge Inference (optional) | Does NOT improve accuracy (Section 6.1.2). Stage 1: free-form description. Stage 2: ontology mapping. Interleaved in planning loop. Value = traceability only |
| 3.5 | Vision | Final answer step only. PyMuPDF → JPEG → GPT-4.1 vision. Tables: find_tables() → structured text. table_only 86.0% (+18%p vs RAPTOR) |

**Domain note** (§3.1 opening): Architecture is domain-agnostic. Regulatory documents (FSAR) present strongest case due to deep hierarchy, dense cross-references, multimodal evidence, sufficiency judgment. Only edge ontology (§3.4) is domain-specific.

### benchmark.md — Section 4: Benchmark

- **Source**: NuScale FSAR Ch.01 (352p) + Ch.05 (160p), public NRC documents
- **Size**: 200 questions, 357 ground truth evidence items (text 152, table 125, figure 80)
- **Design**: 3-axis orthogonal (reasoning_type x complexity x question_type)
  - Reasoning: factual (70), comparative (65), judgment (65)
  - Complexity: single (50), multi (75), cross_document (75)
  - Modality: text_only (80), table_only (50), image_only (30), composite (40)
  - Largest cell: judgment x cross_document (35) — mirrors core regulatory review task
- **Evaluation**: Dual framework — RAGAS (continuous, grounding) + LLM-as-Judge (binary, correctness, 3-evaluator majority vote). Agreement 66.2%.
- **Figure 4**: Benchmark taxonomy + evaluation framework
- **Unique**: First benchmark combining nuclear x multi-hop x multimodal x judgment

### experiment.md — Sections 5 & 6: Experiments & Analysis

**§5 Experiments**:

| Section | Content |
|---------|---------|
| 5.1 | Setup: GPT-4.1 unified, temp 0, max_tokens 300, max_hops=4 |
| 5.2 | 5 baselines: RAPTOR, HippoRAG, LightRAG, GraphRAG, **PageIndex** (same env, no planning → 43.5%) |
| 5.3 | Main results (LLM-as-Judge): Ours 81.5% > RAPTOR 75.5% > LightRAG 73.0% > HippoRAG 70.5% > GraphRAG 49.5% > PageIndex 43.5%. Caveat: judgment polarity bias (98% "Yes") |
| 5.4 | RAGAS: Ours Faith 0.93, CR 0.93 (1st). Judgment: Faith 0.97, CR 0.96. PageIndex Faith 0.58 (no planning) |
| 5.5 | Efficiency: Indexing $4.1/8-20min. Query $42/320min (20x RAPTOR). Hop distribution: 67% use full 4 hops, 33% terminate early |

**§6 Analysis**:

| Section | Content | Key Finding |
|---------|---------|-------------|
| 6.1.1 | 10Q component ablation (4 variants) | Full = only 10/10. Each component fails on different question type |
| 6.1.2 | 200Q edge ablation | **Planning is the primary driver**. no_edges 81.5% = full 81.0%. Cost −65%. Planning decomposed: browse-first (CR +0.44), dynamic termination (33% early), state-conditioned selection (PageIndex +38.0%p) |
| 6.2 | Edge distribution (7,391 edges) | SUPPORTS 34.3%, SPECIFIES 31.5%. VIOLATES 0.04% (3 cases) |
| 6.3 | VIOLATES case study | Scope boundary exclusion (not design deficiency). Q058: seismic scope. Q176: SG partial conformance. Domain depth beyond simple RAG |
| 6.4 | Dual evaluation complementarity | RAGAS-Judge agree 66.2%. RAGAS good + Judge X (29): expression mismatch. RAGAS bad + Judge O (38): beyond-context knowledge |
| 6.5 | Limitations | System: text_only −3.8%p vs RAPTOR, $0.21/q (20x), cost justified for regulatory use. Benchmark: FC ceiling 0.42, judgment bias 98% Yes, 66% are 2-hop, Ch.01 coverage 19%, no external validation |

### conclusion.md — Section 7: Conclusion

3 paragraphs:
1. **Main result**: Planning over vectorless document tree → 81.5%, surpassing all RAG baselines. Modality alignment (text-native state + environment) effective.
2. **Edge inference finding**: No accuracy contribution, 65% cost reduction. Value = traceability only, selectable.
3. **LM4Plan implications**: Planning extends to information environments (not just PDDL/robotics). Architecture domain-agnostic (edge ontology = only domain-specific part). Hypothesize similar benefits in FAA, FDA, legal compliance (to be validated).

### references.md — References

- **Total**: 45 references. All verified.
- [2]-[22]: Core methods (RAG, planning, KG, evaluation)
- [23]-[31]: Domain (Osprey, PageIndex, GAIA, VISION, ChemCrow, etc.)
- [32]-[37]: Benchmark comparisons (FDARxBench, MMLongBench-Doc, M3DocRAG, DesignQA, TAT-QA, SEC-QA)
- [38]-[42]: Agentic IR (Self-RAG, PRISM, Search-o1, APEX-Searcher, Game of Thought)
- [43]-[45]: Document navigation (ReadAgent, DocAgent, BookRAG)

---

## Figures

| Figure | Location | Content |
|--------|----------|---------|
| Figure 1 | Method §3 | Overall pipeline: environment → planning loop → output |
| Figure 2 | Method §3.1 | FSAR document tree + agent tools + multimodal reference resolution |
| Figure 3 | Method §3.2 | Dynamic Sub-KG example + edge distribution |
| Figure 4 | Benchmark §4.4 | 3-axis taxonomy + dual evaluation framework |

---

## Reviewer v4 Status (7.5/10, Accept with Minor Revision)

All Major weaknesses from v3 resolved. Remaining items are Minor:
- Generalizability claimed but not cross-domain validated (softened to "hypothesize")
- Cost premium justified with regulatory context argument
- Judgment polarity bias caveat added
- Hop distribution reported (33% early termination, 67% full budget)
