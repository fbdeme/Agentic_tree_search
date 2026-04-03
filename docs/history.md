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

## v0.3.2 — Image Selection Fix + Caption Indexing (`4d6c7bc`)

**Date**: 2026-03-19

Fixed two critical issues with Vision RAG image delivery.

### Root Cause Analysis

Investigated why image_only FactCorr was 0.13 and Faithfulness failed 80% of the time:

1. **Not a Vision capability problem**: Faithfulness N/A correlated with answer length (2021 chars avg) and KG size (7.8 nodes), not image presence. Composite without images had worse Faithfulness success (9%) than with images (37%).

2. **Image selection was broken**: `_collect_reference_images()` collected ALL reference pages from ALL KG nodes, sorted by page number, took first 6. Result: irrelevant figures filled the quota before the correct figure.
   - Q055: Figure 1.2-6 (p.51) was cut by max_images=6 because p.44-49 filled first.

3. **Reference captions not searchable**: BM25 index only covered title+summary+text. Reference captions (e.g., "NuScale Power Module Major Components") were invisible to search.

### Changes
- **Relevance-based image selection**: Rank references by keyword overlap between question and caption/ref_id. Most relevant figures selected first.
- **Caption indexing**: BM25 index now includes `references[].caption` text, making figure captions searchable.

### Results (Q51-Q55, image_only)
| Question | Correct Figure Delivered? | Before FactCorr | After FactCorr | After KW Hit |
|----------|-------------------------|-----------------|----------------|-------------|
| Q051 | Before: ❌ After: ✅ Figure 5.1-1 (p.16) | 0.00 | 0.00 | 0.83 |
| Q052 | ✅ (was OK) | 0.50 | 0.00 | 1.00 |
| Q053 | Before: ❌ After: ✅ Figure 5.4-1 (p.144) | 0.00 | 0.22 | 0.83 |
| Q054 | Before: ❌ After: ✅ Figure 5.4-10 (p.153) | 0.00 | 0.00 | 0.67 |
| Q055 | Before: ❌ After: ✅ Figure 1.2-6 (p.51) | 0.00 | 0.25 | 0.86 |

### Analysis of 100-question Results
- **Edge distribution**: REFERENCES 54%, SPECIFIES 29%, SUPPORTS 17%. No SATISFIES/VIOLATES/CONTRADICTS/LEADS_TO/IS_PREREQUISITE_OF appeared.
- **Dynamic termination**: 31% stop at hop 1, 56% within 2 hops. Average 2.1-2.6 hops.
- **Faithfulness N/A root cause**: Answer length + KG size, not images. image_only 80% N/A, composite 73% N/A — both due to long context exceeding RAGAs claim extraction token limit.
- **FactCorr 41% zero-score**: composite (53%) and image_only (55%) worst. Mix of search failure + expression mismatch + RAGAs metric limitation.

---

---

## v0.4.0 — Description-first Edge Inference (`TBD`)

**Date**: 2026-03-19

Replaced classification-first edge inference with description-first two-stage approach.

### Root Cause of Edge Type Monotonicity

100-question evaluation showed only 3/8 edge types used (REFERENCES 54%, SPECIFIES 29%, SUPPORTS 17%). Five semantic edge types (SATISFIES, VIOLATES, CONTRADICTS, LEADS_TO, IS_PREREQUISITE_OF) never appeared.

**Root cause**: `infer_relation()` prompt asked LLM to classify first: "Choose one of: REFERENCES, SUPPORTS, ...". Under classification pressure, LLM defaults to safest/most generic label (REFERENCES) when relationship is ambiguous.

### Changes
- **Two-stage edge inference**:
  - Stage 1: LLM describes the relationship in one natural language sentence (no classification pressure)
  - Stage 2: LLM maps description to ontology label (SATISFIES, SUPPORTS, etc.) or SEMANTIC if none fit
- **New edge structure**: `KGEdge.description` stores free-form relationship text (primary), `KGEdge.relation` stores ontology label (secondary interpretation layer)
- **SEMANTIC fallback**: Relationships that don't fit fixed ontology are preserved as SEMANTIC instead of being forced into REFERENCES
- **Academic framing**: "LightRAG-style free-form description with domain-specific ontology label post-mapping. Vectorless alternative to GWM's embedding-based implicit edges."

### Results (Q1-Q3 pilot)
| Edge Type | Before (100q) | After (3q only!) |
|-----------|--------------|-----------------|
| REFERENCES | 280 | ✅ present |
| SPECIFIES | 150 | ✅ present |
| SUPPORTS | 87 | ✅ dominant |
| **CONTRADICTS** | **0** | **✅ 3 instances** |
| **SATISFIES** | **0** | **✅ 1 instance** |
| **SEMANTIC** | N/A | **✅ 1 instance** |

Q003 alone produced 45 edges including CONTRADICTS and SATISFIES — types that never appeared in 100 questions with the old prompt.

---

---

## v0.4.1 — Structured Table Extraction + Table/Figure Split (`4f35255`)

**Date**: 2026-03-19

### Root Cause: Table Data Unreachable

table_only Q031-Q035 all scored AR=0.0, FC=0.0. Investigation revealed:

1. **PDF text extraction corrupts table cells**: PyMuPDF `get_text()` merges adjacent cells — "635Cold Leg" instead of "635 | Cold Leg". BM25 tokenizer (`text.split()`) creates token "635cold", making `search("635")` return 0 results.

2. **PageIndex doesn't handle tables specially**: `add_node_text()` simply concatenates page text. No table detection or structuring.

3. **PyMuPDF `find_tables()` exists**: Extracts clean structured rows/columns as DataFrames.

### Changes
- **Structured table extraction** in `build_trees.py`: `find_tables()` + `to_pandas()` → pipe-delimited text stored as `structured_text` in table references
- **BM25 index includes structured_text**: `search("635")` now finds results
- **`read()` appends structured tables**: Node content includes clean table data
- **`generate_answer()` receives table context**: `_collect_table_context()` passes deduplicated structured tables directly in KG context
- **Figure/Table split for VLM**: `_collect_reference_images()` excludes table pages (tables passed as text), giving more image slots to figures

### Results (Q31-Q35, table_only)

| Question | Before (v0.4.0) | After |
|----------|-----------------|-------|
| Q031 (Hot Leg 635) | AR=0.0 FC=0.0 | **AR=0.85 FC=0.50** |
| Q032 (Cold Leg 578) | AR=0.0 FC=0.0 | **AR=0.81 FC=0.50** |
| Q033 (Core 89) | AR=0.0 FC=0.0 | **AR=0.79 FC=0.40** |
| Q034 (SG 621) | AR=0.0 FC=0.0 | **AR=0.84 FC=0.50** |
| Q035 (PZR 578) | AR=0.0 FC=0.0 | AR=0.0 FC=0.0 (search keyword repetition) |

### Q035 Failure Analysis
Agent searched "pressurizer volume" / "PZR volume" across all 4 hops but never tried "RCS volumes" (which returns System Evaluation node with Table 5.1-1 at score=15.21). Root cause: **agent repeats same search keywords because it has no memory of previous search attempts.**

### Full 100-Question Results (v0.4.1)

| Metric | v0.4.0 | v0.4.1 | Change |
|--------|--------|--------|--------|
| Faithfulness | 0.77 | 0.73 | -0.04 |
| Answer Relevancy | 0.70 | **0.74** | **+0.04** |
| Context Recall | 0.59 | 0.56 | -0.03 |
| Factual Correctness | 0.20 | **0.24** | **+0.04** |
| Keyword Hit | 0.63 | **0.66** | **+0.03** |

By type — key improvements:

| Type | v0.4.0 AR/FC | v0.4.1 AR/FC | Change |
|------|-------------|-------------|--------|
| text_only | 0.78/0.24 | **0.81/0.32** | +0.03/+0.08 |
| **table_only** | **0.50/0.26** | **0.67/0.41** | **+0.17/+0.15** |
| image_only | 0.76/0.18 | 0.75/0.11 | -0.01/-0.07 |
| composite | 0.70/0.13 | 0.72/0.14 | +0.02/+0.01 |

Edge distribution (1,328 total): SPECIFIES 525 (39.5%), SUPPORTS 442 (33.3%), REFERENCES 137 (10.3%), IS_PREREQUISITE_OF 87 (6.6%), SATISFIES 77 (5.8%), SEMANTIC 47 (3.5%), LEADS_TO 8 (0.6%), CONTRADICTS 5 (0.4%).

---

---

## v0.4.2 — Agent Memory + Multihop Benchmark (`TBD`)

**Date**: 2026-03-20 ~ 2026-03-24

### Agent Memory
Search history tracked per hop and passed in `_plan_tool_actions` prompt. Prevents keyword repetition. Q035 fix confirmed: agent tries different terms each hop, finds answer at hop 4 via `search("RCS volume")`.

### Multihop Benchmark (200 questions)

New benchmark from `github.com/kimmbk/GWM_Benchmark`:
- 200 questions, 3 reasoning types (factual/comparative/judgment), 3 complexity levels (single/multi/cross_document)
- Designed specifically for multi-evidence, multi-hop evaluation

**Full Results:**

| Metric | Overall | factual (70) | comparative (65) | judgment (65) |
|--------|---------|-------------|------------------|--------------|
| Faithfulness | 0.56 (n=39) | 0.43 | **0.86** | **0.82** |
| Answer Relevancy | **0.81** | 0.80 | 0.77 | **0.85** |
| Context Recall | **0.68** | 0.54 | 0.70 | **0.82** |
| Factual Correctness | **0.38** | 0.35 | **0.46** | 0.34 |
| Keyword Hit | 0.65 | **0.71** | 0.65 | 0.60 |

**By Complexity (Context Recall):**

|  | single_evidence | multi_evidence | cross_document |
|--|-----------------|----------------|----------------|
| factual | 0.33 | 0.60 | 0.88 |
| comparative | 0.64 | 0.52 | 0.91 |
| judgment | 0.60 | 0.70 | **0.94** |

**Edge Distribution (8,069 total):**
SUPPORTS 33%, SPECIFIES 31%, REFERENCES 14%, IS_PREREQUISITE_OF 10%, **SATISFIES 8.2% (659)**, SEMANTIC 2%, LEADS_TO 1%, CONTRADICTS 0.6%, VIOLATES 0.02%

**Key Findings:**
1. judgment CR=0.82: Regulatory judgment questions trigger broadest exploration, finding evidence from both design specs and requirements.
2. cross_document CR=0.92: Counterintuitively highest — Agent Memory drives diverse search across both chapters.
3. SATISFIES 659 instances (judgment alone: 359) — validates the core thesis that regulatory judgment edges emerge in multi-hop queries.
4. comparative FC=0.46 (highest): Comparison answers naturally produce claim-by-claim structure that matches RAGAs evaluation well.
5. single_evidence CR=0.45 (lowest): Paradoxically hardest — finding one specific node requires exact BM25 match.
6. VIOLATES only 2 instances: Not an agent limitation — FSAR is a certification document where all designs pass requirements.
7. Faithfulness measured only 19.5% (39/200): KG avg 52 edges for judgment → token overflow in RAGAs claim extraction.
8. 200/200 questions succeeded, 0 errors.

**KG Stats:**
| Type | Avg Nodes | Avg Edges | Avg Hops |
|------|-----------|-----------|----------|
| factual | 10.8 | 29.2 | 3.4 |
| comparative | 12.9 | 40.5 | 3.6 |
| judgment | 15.0 | 52.3 | 3.8 |

---

---

## v0.4.3 — Faithfulness Fix: RAGAs max_tokens 1024→4096 (`TBD`)

**Date**: 2026-03-24

### Root Cause

Faithfulness measured only 39/200 (19.5%). Investigation revealed the failure was NOT caused by context size or answer length — it was RAGAs internal LLM `max_tokens=1024` (default). Faithfulness claim extraction outputs a JSON list of all claims in the answer. When answer has >15 claims, the JSON exceeds 1024 output tokens and gets truncated → parse failure.

### Fix

One line: `llm_factory("gpt-4.1", client=async_client, max_tokens=4096)`

### Results (re-evaluation of same 200 answers, no agent re-run)

| Metric | Before (max_tokens=1024) | After (max_tokens=4096) |
|--------|-------------------------|------------------------|
| Faithfulness | 0.56 (n=39/200, 19.5%) | **0.71 (n=200/200, 100%)** |
| Answer Relevancy | 0.81 | 0.81 |
| Context Recall | 0.68 | **0.69** |
| Factual Correctness | 0.38 | **0.39** |

By reasoning type (all n=full):
| Type | Faithfulness | AR | CR | FC |
|------|-------------|-----|-----|-----|
| factual (70) | 0.59 | 0.80 | 0.54 | 0.35 |
| comparative (65) | **0.77** | 0.77 | 0.70 | **0.45** |
| judgment (65) | **0.78** | **0.85** | **0.85** | 0.36 |

By complexity:
| Complexity | Faithfulness | CR |
|-----------|-------------|-----|
| single_evidence (50) | 0.56 | 0.45 |
| multi_evidence (75) | 0.64 | 0.64 |
| cross_document (75) | **0.88** | **0.91** |

Key insight: Previous Faithfulness 0.56 was selection bias — only 39 "easy" questions (small KGs) were measured. Full measurement reveals actual Faithfulness is 0.71, with cross_document reaching 0.88.

---

---

## v0.4.4 — Concise Answer Generation (`TBD`)

**Date**: 2026-03-25

### Meeting Feedback Addressed
- 답변 출력이 너무 길다 → 2,213 chars → **324 chars** (-85%)
- 사실 기반 노드 정확도 낮다 → FC 0.39 → **0.58** (+0.19)

### Changes
- `generate_answer()` prompt: "300 words" → **"1-2 sentences ONLY"**
- max_tokens: 800 → **300**
- Removed: "No uncertainty" boilerplate, background explanations, methodology
- Kept: source citations (node IDs) — removing them didn't improve FC

### Results (9q pilot: factual Q1-3, comparative Q71-73, judgment Q136-138)

| Metric | v0.4.2 (200q) | v0.4.4 (9q pilot) |
|--------|--------------|-------------------|
| Answer length | 2,213 chars | **324 chars** |
| Faithfulness | 0.71 | **0.95** |
| Answer Relevancy | 0.81 | **0.97** |
| Context Recall | 0.69 | **0.94** |
| Factual Correctness | 0.39 | **0.58** |

### FC Analysis
FC upper bound is ~0.6 due to structural limitation:
- **CITATION_EXTRA**: Agent cites node IDs not in expected answer → extra claim penalty. But removing citations didn't help (FC dropped).
- **WORDING_MISMATCH**: Agent finds different evidence nodes → uses different values/expressions than expected answer. Same conclusion, different supporting data. Cannot fix with prompting.
- **KW_MISSING**: Shorter answers omit secondary keywords from expected answer.

---

---

## v0.4.5 — Concise Answers + Browse-first (`82c23e4`)

**Date**: 2026-03-25

### Changes
- **Answer generation**: "300 words" → "1-2 sentences ONLY" + max_tokens 800→300
- **Browse-first**: `get_document_overview(depth=3)` auto-injected in first hop prompt
- **browse(depth)**: depth parameter for tree-view browsing
- **RAGAs max_tokens**: 1024→4096 (100% Faithfulness measurement)

### Full 200-Question Results (Multihop Benchmark)

| Metric | v0.4.2 | v0.4.5 | Change |
|--------|--------|--------|--------|
| Faithfulness | 0.71 (n=200) | **0.93** | **+0.22** |
| Answer Relevancy | 0.81 | **0.84** | +0.03 |
| Context Recall | 0.69 | **0.93** | **+0.24** |
| Factual Correctness | 0.39 | **0.42** | +0.03 |
| Answer length | 2,213 chars | **386 chars** | -83% |

By reasoning type:
| Type | Faith | AR | CR | FC |
|------|-------|-----|-----|-----|
| factual | 0.91 | 0.85 | 0.92 | 0.40 |
| comparative | 0.92 | 0.78 | 0.91 | 0.43 |
| judgment | **0.95** | **0.89** | **0.97** | **0.44** |

Key improvements:
- single_evidence CR: 0.45→**0.89** (CR=0 cases: 42%→4%)
- judgment FC=0 cases: **0/65 (0%)** — no judgment question gets zero FC
- Browse usage: agent uses document structure in Hop 1, then targeted search

### FC Ceiling Analysis
FC ~0.42 is structural: agent uses different evidence nodes than expected answer author → different wording for same conclusion. Detailed analysis in `docs/benchmark_feedback.md`.

---

---

## v0.4.6 — Pseudo-Relevance Feedback (PRF/RM3) (`TBD`)

**Date**: 2026-03-25

### Change
Added PRF (RM3) to BM25 search: initial search → extract top terms from top-3 results → expand query → re-score. Zero LLM cost, pure lexical operation. α=0.4, 5 expansion terms.

### Pilot Results (3 questions that previously failed)

| Question | CR Before | CR After | FC Before | FC After |
|----------|----------|----------|----------|----------|
| Q051 (composite) | 0.50 | **1.00** | 0.17 | **0.67** |
| Q095 (comparative) | 0.33 | **1.00** | 0.20 | 0.20 |
| Q136 (judgment) | 0.67 | **1.00** | 0.29 | **0.50** |

PRF helped all 3 reach CR=1.0 by expanding queries with related terms from top initial results. Expected overall impact: +0.02~0.03 CR on full 200q (already at 0.93).

### Search Enhancement Evaluation (from meeting feedback)

Three traditional IR methods were evaluated:
- **BM25F**: Theoretically correct field weighting, but CR=0.93 makes practical impact minimal. High implementation cost.
- **SDM**: Phrase recognition. Not our failure mode — failures are vocabulary mismatch, not word order.
- **PRF (RM3)**: Directly addresses vocabulary mismatch. Implemented. Low cost, proven effective on failure cases.

---

---

## v0.4.6 Final — Dual Evaluation (RAGAs + LLM-as-Judge) (`2b76a1b`)

**Date**: 2026-03-26

### Full Pipeline: Answer Collection → RAGAs + LLM-as-Judge

200 questions evaluated with both frameworks simultaneously.

### LLM-as-Judge Results (MAM-RAG Table 8 methodology)

**Overall: 162/200 = 81.0%**

| Reasoning | Accuracy | | Complexity | Accuracy | | Modality | Accuracy |
|-----------|:--------:|-|------------|:--------:|-|----------|:--------:|
| factual | 74.3% | | single_evidence | 84.0% | | text_only | 76.2% |
| comparative | 78.5% | | multi_evidence | 78.7% | | table_only | **86.0%** |
| **judgment** | **90.8%** | | cross_document | 81.3% | | image_only | 80.0% |
| | | | | | | composite | 85.0% |

### RAGAs Results

| Metric | Overall | factual | comparative | judgment |
|--------|:-------:|:-------:|:-----------:|:--------:|
| Faithfulness | 0.93 | 0.92 | 0.92 | **0.97** |
| Answer Relevancy | 0.84 | 0.85 | 0.78 | **0.89** |
| Context Recall | 0.93 | 0.92 | 0.91 | **0.96** |
| Factual Correctness | 0.42 | 0.35 | **0.49** | 0.41 |

### 3-Axis Analysis (see docs/experiment_analysis.md)

1. **Benchmark Types**: judgment/cross_document 94% highest; factual/single 77% lowest
2. **Evaluation Frameworks**: RAGAs vs Judge 66.2% agreement — complementary, not redundant
3. **KG Edges**: Correct answers have +6.8%p SUPPORTS, +3.2%p SATISFIES vs incorrect

### Case Studies
- VIOLATES in certified document: scope exclusion + partial conformance
- SATISFIES driving judgment: Q184 with 34 SATISFIES edges → correct regulatory determination
- LEADS_TO causal chain: Q112 tracing power output → decay heat → pool temperature
- Cross-document SATISFIES: Q178 connecting Ch.01 Rankine cycle → Ch.05 SG compliance
- RAGAs vs Judge disagreement: Q019 Faith=1.0 but Judge=X (MLflow strict on additional detail)

---

## Baseline RAGAs Evaluation & Paper Draft — 2026-04-03

### Baseline RAGAs 평가 실행

RAPTOR, GraphRAG의 pred.json에 `retrieved_contexts`가 포함되어 있어 RAGAs 평가 실행.
`experiments/evaluate_baseline.py` 신규 작성.

| 메트릭 | **GWM** | RAPTOR | GraphRAG |
|--------|:-------:|:------:|:--------:|
| Faithfulness | **0.93** | 0.74 | 0.28 |
| Answer Relevancy | **0.84** | 0.83 | 0.59 |
| Context Recall | **0.93** | 0.77 | 0.18 |
| Factual Correctness | **0.42** | 0.40 | 0.32 |

- HippoRAG, LightRAG는 `retrieved_contexts` 미저장으로 RAGAs 실행 불가 (재수집 필요)
- GraphRAG CR=0.18, Faith=0.28 — 커뮤니티 요약에서 구체적 사실 손실 확인

### 논문 초안 작성 (`docs/paper_draft.md`)

- 개조식 형태 논문 흐름 초안 작성
- 인용 25개 검증 완료 (GWM arXiv:2507.10539 ICML 2025 확인, MAM-RAG 미출판)
- Introduction: Osprey [Hellert et al., 2026] 스타일 Domain-first 서사 구조 채택
- PageIndex: 학술 논문 없음 확인 → 오픈소스 프레임워크로 정직하게 표기, Lumer et al. [2025] 인용 추가

### 비용 데이터 현황 및 한계

논문 Section 5.5 (인덱싱 효율성) 작성 중 비용/시간 데이터의 불완전성 확인:

**보유 데이터:**
- GWM: `agent_sec` (avg 115.3s/문항), `kg_nodes`, `kg_edges`, `hops_used` — RAGAs eval에서 저장됨
- RAPTOR: `retrieval_time_sec` (avg 0.19s), `generation_time_sec` (avg 1.63s)
- GraphRAG: `retrieval_time_sec` (avg 3.78s), `total_tokens` (avg 4,953/문항, 총 990K)
- 인덱싱: GraphRAG 2,400s, HippoRAG 1,745s, LightRAG 3,123s (`indexing_report.json`)

**미보유 데이터:**
- GWM 토큰 사용량: `gwm_agent.py`에 토큰 카운팅 미구현 → 200문항 전체 재실행 시 ~$25 + 6시간 소요로 비현실적
- GWM 인덱싱 시간(PageIndex 트리 빌드): 측정 이력 없음
- RAPTOR 인덱싱 시간: `indexing_report.json` 미생성
- HippoRAG/LightRAG 문항당 시간: pred.json에 미저장 (다른 분이 실험)

**실측 결과 (2026-04-03):**

1. **GWM 토큰 사용량 (5문항 샘플 실측)**:
   - 측정 스크립트: `experiments/measure_token_usage.py` (OpenAI API monkey-patch로 usage 수집)
   - 샘플: Q001(factual/single), Q071(comparative/single), Q131(composite/cross), Q161(judgment/multi), Q191(image/cross)
   - 결과: 평균 86,072 tokens/문항, 74.0 API calls/문항, $0.21/문항
   - 200문항 외삽: ~$41.9 (기존 추정 $25보다 높음 — 추정치는 과소평가였음)
   - Q001(1홉, $0.03) vs Q191(4홉, $0.29) — 동적 종료가 비용 최적화에 기여

2. **PageIndex 트리 빌드 시간 (실측)**:
   - Ch.01 (352p, 866 nodes): **332.1초 (5.5분)**
   - Ch.05 (160p, 26 nodes): **122.6초 (2.0분)**
   - 합계: **454.7초 (7.6분)** — 기존 대비 5.7×–6.9× 빠름
   - 비용: LLM 노드 요약 포함하나 정확한 토큰 수는 미측정

3. 결과 저장: `experiments/results/token_usage_sample.json`

**"인덱싱 무비용" 주장 수정:**
PageIndex 트리 생성에 `model="gpt-4.1"` + `if_add_node_summary="yes"` 사용 확인 → LLM 비용 발생. "인덱싱 무비용"은 부정확하며 "경량 인덱싱"으로 수정. 임베딩/KG 사전 구축은 불필요하나, 노드 요약 생성 비용은 존재함을 논문에 명시.

---

## Known Issues (Unresolved)

1. **FC structural ceiling ~0.5**: Agent uses different evidence nodes → different wording.
2. **Keyword Hit dropped**: 0.65→0.53 due to shorter answers.
3. **VIOLATES rare (3/7391)**: FSAR is a compliance document.
4. **RAGAs-Judge 33.8% disagreement**: Different aspects measured (grounding vs correctness).
