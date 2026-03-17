# Development History

This document tracks the development history of the GWM-based Multimodal Regulatory Document Exploration Agent, including design decisions, issues found, and resolutions.

---

## v0.1.0 — Initial PoC (`75f92d5`)

**Date**: 2026-03-10

Initial prototype with simulated FSAR tree data.

- GWM State-Action-Transition loop implemented (`gwm_agent.py`)
- DynamicSubKG with NetworkX DiGraph (`knowledge_graph.py`)
- PageIndex environment wrapper (`pageindex_env.py`)
- GPT-4o-mini based reasoning module (`reasoning.py`)
- KG visualization with matplotlib (`visualize.py`)
- Two predefined experiments (RCP trip PCT, LOCA 3-criteria)
- Simulated FSAR tree (`sample_fsar_tree.json`)

---

## v0.2.0 — Multimodal Pipeline + RAGAs Evaluation (`263f92f`)

**Date**: 2026-03-16

Major overhaul: real PDF data, Vision RAG, RAGAs evaluation framework.

### Changes
- **Model upgrade**: gpt-4o-mini → gpt-4.1 (all prompts)
- **Language**: All prompts switched from Korean to English
- **Data reorganization**: `data/documents/`, `data/qa_dataset/`, `data/trees/`
- **Real PDF tree generation**: `build_trees.py` using PageIndex on actual NuScale FSAR Ch.01 (352p, 866 nodes) and Ch.05 (160p, 26 nodes)
- **Figure/Table reference linking**: Parse LIST OF FIGURES/TABLES from PDF, attach `references` field to tree nodes matching "Figure X.Y" / "Table X.Y" patterns in text
- **Vision-augmented answer generation**: Render referenced PDF pages as JPEG via PyMuPDF, pass to GPT-4.1 vision API at final answer step only
- **RAGAs evaluation framework**: Faithfulness, Answer Relevancy, Context Recall, Factual Correctness
- **Exclude already-explored nodes**: `exclude_node_ids` parameter prevents repeated node selection
- **Unified edge inference**: Both new↔existing and new↔new node pairs are compared

### Issues Found
- **Faithfulness metric timeout**: RAGAs Faithfulness fails when agent answer or context is too long (>3072 output tokens). Mitigated by truncating answer to 2000 chars and context to 6 nodes × 800 chars.
- **Context Recall 0.0 on text_only**: Expected answer sentences don't match truncated context well. Partially addressed by using node summaries.
- **Hop 2-4 node stagnation**: Without `exclude_node_ids`, agent kept selecting same nodes. Fixed.
- **Edge 0 on simple questions**: Single-hop factual queries (Q001, Q002) produce no edges because all retrieved sections are from the same topic area with no meaningful regulatory relationships. This is expected behavior.

### Pilot Results
| Config | Answer Relevancy | Context Recall | Factual Correctness |
|--------|-----------------|----------------|-------------------|
| text_only Q1-Q5 | 0.92 | 0.20 | 0.40 |
| composite+Vision Q71-Q73 | 0.83 | 0.67 | 0.36 |

---

## v0.2.1 — Two-Tier Edge Ontology + GWM Action Correction (`e309a89`)

**Date**: 2026-03-17

Research proposal update based on external review (Manus verification).

### Changes
- **Two-tier edge ontology**:
  - Structural: REFERENCES (citation networks [17]), SPECIFIES (SysML `<<refine>>` [7])
  - Semantic: SATISFIES/VIOLATES, SUPPORTS/CONTRADICTS, LEADS_TO, IS_PREREQUISITE_OF
- **GWM Action classification fix**: Our tree-based navigation is an *Intended Action* (direct structural reference), not *Unintended Action* (embedding similarity RAG) as previously stated
- **Citation corrections**: Hassanzadeh (IJCAI 2019), Pan (ACL 2017) — verified titles/venues

### Issues Found
- **SATISFIES/VIOLATES edges never appear**: Current QA dataset questions are descriptive ("What is...") rather than compliance-judgment ("Does X satisfy requirement Y?"). Need regulatory compliance questions to trigger semantic edges.
- **REFERENCES/SPECIFIES dominate**: In pilot experiments, only structural edges appear. Semantic edges (SUPPORTS) emerge only in composite questions.

---

## v0.2.2 — Dynamic Termination + Summary-based Context (`3640d00`)

**Date**: 2026-03-17

Added dynamic termination condition and fixed KG context truncation.

### Changes
- **Dynamic termination**: `plan_next_search()` now returns `{sufficient, next_search_query, reasoning}`. Agent stops early when LLM judges evidence is sufficient. No extra LLM call (integrated into existing planning step).
- **Summary-based KG context**: `to_context_string()` now uses node summaries instead of truncated content. Summaries contain key facts (e.g., "160 MWt") that were being cut off at 800 chars.
- **Increased context limits**: `max_content_len` 400→800, `tree_summary` 2000→3000 chars.
- **`hops_used` reflects actual hops** (not always max_hops).

### Issues Found
- **KG context truncation caused false negatives**: With `max_content_len=400`, key numerical values (e.g., "160 MWt" at position 1526 in node text) were cut off, making LLM always judge "insufficient". Fixed by using summaries.
- **Early termination works for simple questions**: Q001 ("thermal output") stops at Hop 2 after finding the answer. Complex questions (Q003, "AC/DC power") correctly continue to Hop 4.
- **tree_summary truncation at 3000 chars**: With 866 nodes in Ch.01, the tree summary far exceeds 3000 chars. Later sections of the tree may be invisible to the LLM during search planning.

### Results After Fix
| Metric | Before (content truncated) | After (summary-based) |
|--------|---------------------------|----------------------|
| Answer Relevancy | 0.92 | 0.92 |
| Factual Correctness | 0.30 | 0.33 |
| Keyword Hit | 55% | 70% |
| Early termination | 0/5 | 1/5 (Q001 at Hop 2) |
| Time | 11 min | 8.7 min (-21%) |

---

## Known Issues (Unresolved)

1. **Tree summary truncation**: 866 nodes → text summary far exceeds context limit. LLM only sees first portion of document tree. Need hierarchical drill-down or paginated tree search.
2. **Faithfulness metric instability**: RAGAs Faithfulness frequently times out or fails due to long context. Need further optimization of context passed to evaluator.
3. **Single-document tree search bottleneck**: When multiple documents are registered, their combined tree summaries may exceed limits, making cross-document search unreliable.
4. **No semantic edge emergence in text_only questions**: SATISFIES/VIOLATES edges require regulatory compliance judgment questions, which are underrepresented in current QA dataset.
5. **PageIndex node page ranges**: Only `page_index` (start) is stored, not `end_index`. This limits accurate page range rendering for Vision RAG.
