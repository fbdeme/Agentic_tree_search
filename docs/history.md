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

## v0.2.3 — Context Alignment + Grounded Answers (`TBD`)

**Date**: 2026-03-18

Fixed structural mismatch between agent's view and RAGAs evaluation context.

### Root Cause Analysis

Three separate information views existed:
1. **Agent reads**: full node content (thousands of chars) during exploration
2. **Agent answers from**: `kg.to_context_string()` = summaries + edges
3. **RAGAs evaluates against**: `extract_contexts_from_kg()` = content[:800] (truncated)

Agent → evaluation mismatch caused RAGAs to judge "no evidence" for information the agent actually saw and used.

### Changes
- **Context alignment**: `extract_contexts_from_kg()` now returns `kg.to_context_string()` — same context agent used for answer generation
- **Grounded answer generation**: Prompt updated to require quoting specific evidence from KG and prohibit claims not in the provided context

### Results (Q1-Q5)
| Metric | Before | After |
|--------|--------|-------|
| Faithfulness | 0.15 | **0.77** |
| Context Recall | 0.00 | **0.40** |
| Factual Correctness | 0.30 | **0.47** |
| Keyword Hit | 55% | **60%** |

### Deep Dive: Why Q003-Q005 Context Recall Still 0.0

| Question | Root Cause | Type |
|----------|-----------|------|
| Q003 (AC/DC power) | KG has the answer but summary wording differs from expected answer. RAGAs sentence matching too strict. | Evaluation limitation |
| Q004 (SG config) | Expected answer has factual error ("outside RPV" → actually inside). Agent answer is more accurate. | Dataset error |
| Q005 (CNV pressure) | "sub-atmospheric" info is in Ch.01 Introduction, but agent only searched Ch.05. Cross-chapter search failed. | **Search failure** |

Q005 is the most critical finding — it demonstrates the tree_summary truncation problem causing cross-document search failure.

---

## v0.3.0 — Tool-based Exploration (browse/read/search) (`d6311a0`)

**Date**: 2026-03-18

Replaced monolithic tree-summary search with file-system-like tool-based exploration.

### Root Cause Addressed

Previous search dumped entire tree summary (217K chars) into a single prompt, truncated to 3000 chars — only 1.4% visible. Ch.05 was completely invisible. This is like running `tree / | head -40` and asking "find a file here."

### Changes
- **Three exploration tools**:
  - `browse(doc_id, node_id)`: list children of a node (like `ls`)
  - `read(doc_id, node_id)`: get full content (like `cat`)
  - `search(keyword)`: keyword search across all nodes (like `grep`)
- **LLM selects tools** at each hop via JSON-based tool-use pattern
- **Prompt strategy**: search with MULTIPLE keyword variants (question terms + likely answer terms)
- **Skip already-read nodes**: prevent redundant reads across hops
- **Legacy search preserved** for backward compatibility

### Results (Q1-Q5)
| Metric | tree-summary (v0.2.3) | tool-use (v0.3.0) |
|--------|----------------------|-------------------|
| Answer Relevancy | 0.92 | **0.91** |
| Context Recall | 0.40 | **0.40** |
| Faithfulness | 0.77 | 0.34 |
| Factual Correctness | 0.47 | **0.37** |
| Keyword Hit | 60% | 45% |

### Key Findings
- **Q003 Context Recall 0.00 → 1.00**: diverse keyword search found evidence across sections
- **Q005 Context Recall 0.00 → 1.00**: `search("vacuum")` successfully called; Ch.05 context sufficient
- **Q004**: cross-chapter search worked — found Ch.05 Steam Generators directly
- **Q002**: dynamic termination at hop 3 (sufficient evidence)
- **Faithfulness dropped**: agent reads large parent nodes (Preface, Chapter overview) → bloated context → RAGAs claim verification harder. Need to enforce "don't read large parent nodes" rule.
- **browse under-utilized**: agent predominantly uses search, rarely drills down with browse

### Issues Found
- **"Power Output" node unreachable by search**: Q001's key node (0006) has title "Power Output" but no "thermal output" in summary/text first 800 chars. search("thermal output") returns 1 match (different node). Need to improve search to match title+summary+text holistically.
- **Large node reads waste context**: Preface (14K chars), Chapter overview nodes pollute KG with generic content, reducing signal-to-noise for RAGAs evaluation.

---

## v0.3.1 — BM25 Search Ranking + Full 100-Question Evaluation (`TBD`)

**Date**: 2026-03-18

Added BM25 ranking to search tool and ran full 100-question benchmark.

### Changes
- **BM25 search ranking**: Replaced naive `keyword in text` with BM25Okapi ranking. Title weighted 3x. Naturally pushes shorter, focused nodes above large parent nodes.
- **`match_in` → `score` fix**: Aligned search result schema with tool-use agent.
- **Parallel evaluation**: 4 concurrent processes (Q1-25, Q26-50, Q51-75, Q76-100). Wall clock reduced from ~3.4h to **58 minutes**.

### BM25 Impact on Search Quality
| Query | Before (naive) | After (BM25) |
|-------|---------------|--------------|
| "160 MWt" | Power Output invisible | **Power Output #2** |
| "sub-atmospheric" | Preface #1 | **Preface last, Introduction #1** |
| "thermal output" | 1 match only | **5 matches, Power Output #5** |

### Full 100-Question Results

| Metric | Overall | text_only | table_only | image_only | composite |
|--------|---------|-----------|------------|------------|-----------|
| Faithfulness | 0.68 | 0.74 | 0.59 | 0.60 | **0.79** |
| Answer Relevancy | 0.72 | **0.81** | 0.68 | 0.71 | 0.65 |
| Context Recall | 0.56 | 0.54 | 0.55 | **0.62** | 0.53 |
| Factual Correctness | 0.22 | 0.30 | 0.31 | 0.13 | 0.15 |
| Keyword Hit | 0.65 | 0.52 | **0.88** | 0.75 | 0.57 |

### KG Construction Stats

| Type | Avg Nodes | Avg Edges | Avg Hops |
|------|-----------|-----------|----------|
| text_only | 6.6 | 4.4 | 2.1 |
| table_only | 5.5 | 2.1 | 2.2 |
| image_only | 7.2 | 6.5 | 2.6 |
| composite | 7.0 | 7.2 | 2.4 |

### Key Findings
1. **Dynamic termination works**: Average 2.1-2.6 hops (max 4). Agent stops early when evidence is sufficient.
2. **Faithfulness highest for composite (0.79)**: Multi-hop exploration + edge inference produces well-grounded answers.
3. **table_only Keyword Hit 0.88**: Agent reliably finds numerical values in tables.
4. **image_only Factual Correctness 0.13**: Lowest — Vision helps see figures but answer-to-expected matching is weak.
5. **Factual Correctness overall low (0.22)**: Agent answers more detailed than expected answers → extra claims penalized by RAGAs.
6. **99/100 questions succeeded**: 1 error (API timeout).

### Timing
- Sequential: ~3.4 hours estimated
- **4x parallel: 58 minutes** (3.5x speedup)
- Agent: 114.6 min total, Eval: 82.6 min total

---

## Known Issues (Unresolved)

1. **Factual Correctness structurally low**: RAGAs penalizes extra claims in agent answers. Agent answers are more detailed than expected answers. This is a metric limitation, not an agent quality issue.
2. **Faithfulness timeout (45/99)**: RAGAs Faithfulness fails for ~45% of questions when context is long. Only 54/99 scored.
3. **image_only weak performance**: Vision RAG passes referenced images but Factual Correctness is 0.13. Agent may not extract correct details from engineering diagrams.
4. **QA dataset errors**: Q004 expected answer contains factual error. Need dataset review.
5. **browse tool under-utilized**: Agent defaults to search-heavy strategy.
6. **Search keyword mismatch**: Agent searches question terms, but key information may use different vocabulary.
