# TODO

Task tracking for the GWM Multimodal Regulatory Document Exploration Agent.

---

## High Priority

### Evaluation
- [x] ~~Run full 100-question benchmark evaluation~~ → Completed (v0.3.1), 99/100 success
- [x] ~~Analyze results by question type~~ → See history.md v0.3.1 for full breakdown
- [x] ~~Run multihop benchmark (200q)~~ → 200/200 success, judgment CR=0.82, SATISFIES 659 instances
- [x] ~~Fix Faithfulness measurement rate~~ → Root cause: RAGAs default max_tokens=1024. Fixed to 4096. Now 200/200 (100%) measured. (v0.4.3)
- [x] ~~Improve single_evidence CR (0.45)~~ → Browse-first fixed: CR 0.45→0.89, only 4% CR=0 (v0.4.5)
- [x] ~~Address FC~~ → Reduced answer length (2213→324 chars), FC improved 0.39→0.58. Remaining gap is structural (different evidence nodes → different wording). (v0.4.4)

### Search (Action) Enhancement
- [x] ~~Fix tree summary truncation~~ → Replaced with tool-based exploration (v0.3.0)
- [x] ~~Multi-document search reliability~~ → search() spans all documents (v0.3.0)
- [x] ~~BM25 search ranking~~ → Replaces naive keyword match, specific nodes rank higher (v0.3.1)
- [x] ~~Action history / search memory~~ → Agent Memory implemented (v0.4.2). Search log prevents keyword repetition.
- [x] ~~Browse-first pattern~~ → Document structure auto-injected in Hop 1, browse(depth) added (v0.4.5)
- [x] ~~Query expansion~~ → PRF (RM3) implemented. Auto-expands queries from top-3 results. Q051 CR 0.50→1.00 (v0.4.6)
- [ ] **Follow-reference tool**: When node mentions "see Table 5.1-1", follow that reference directly.
- [ ] Store `end_index` in tree nodes (not just `page_index`) for accurate page range

### Data Quality
- [ ] Review QA dataset for factual errors — **Q004 confirmed**: expected answer says SG "outside RPV" but actually inside

### Edge Quality
- [x] ~~SATISFIES/VIOLATES never appeared~~ → Fixed by description-first edge inference (v0.4.0). CONTRADICTS (3), SATISFIES (1), SEMANTIC (1) emerged in pilot.
- [x] ~~Full edge distribution analysis~~ → 8/9 types emerged, SATISFIES 584 (8.1%) across 200q (v0.4.5)
- [ ] Address edge explosion (judgment avg 48.7 edges) — consider selective pairing or max edge limits

### Benchmark Improvement
- [ ] Request benchmark v3 with improvements (see docs/benchmark_feedback.md):
  - Comprehensive expected_answers (multiple valid perspectives)
  - Source-pinned questions (reduce ambiguity)
  - 30%+ "No" judgment questions (test violation detection)
  - 3-4 evidence chain questions (deeper multi-hop)
  - Broader document coverage (Section 1.9 regulatory tables)

---

## Medium Priority

### Action Tooling (Search Enhancement v2)
- [x] ~~Implement multi-tool Action pattern~~ → browse/read/search implemented (v0.3.0)
- [ ] Add `follow_ref` tool — follow node's Figure/Table references as navigation
- [ ] Add `graph_query` tool — query already-built KG relationships
- [ ] Add few-shot examples to tool-use prompt for browse-based hierarchical exploration

### Vision Pipeline
- [ ] Benchmark Vision vs text-only on image_only questions (Q051-Q070)
- [ ] Optimize image count per query (currently max 6) — test impact on quality vs cost
- [ ] Add image analysis to `summarize_node()` for figure-heavy nodes (cost-benefit analysis needed)

### Ablation Study
- [ ] Implement baseline comparisons:
  - [ ] Vanilla RAG (vector DB + chunking)
  - [ ] GraphRAG baseline
  - [ ] LightRAG baseline
  - [ ] PageIndex without KG (retrieval only, no edge inference)
- [ ] Compare cost (API calls, tokens, time) across methods

---

## Low Priority

### Code Quality
- [ ] Add unit tests for core modules (knowledge_graph, reasoning, pageindex_env)
- [ ] Add error handling for API rate limits
- [ ] Track token usage per query for cost analysis
- [ ] Cache LLM inference results to avoid redundant API calls

### Documentation
- [x] ~~Update CLAUDE.md with current architecture~~ (done v0.2.2)
- [ ] Add architecture diagram reflecting Vision RAG + reference linking
- [ ] Document evaluation setup and reproduction steps

### Future Extensions
- [ ] Multi-document cross-referencing (e.g., Ch.01 references Ch.05 sections)
- [ ] Streaming answers during agent exploration
- [ ] User feedback loop for edge correction
- [ ] Web interface (Flask/FastAPI) for interactive exploration
- [ ] Support additional document formats (Markdown, Word)

---

## Completed

- [x] Initial PoC with simulated FSAR tree (v0.1.0)
- [x] Real PDF → PageIndex tree generation (Ch.01: 866 nodes, Ch.05: 26 nodes)
- [x] Model upgrade gpt-4o-mini → gpt-4.1
- [x] All prompts switched to English
- [x] Figure/Table metadata extraction + reference linking to tree nodes
- [x] Vision-augmented answer generation (GPT-4.1 vision)
- [x] Context alignment: RAGAs evaluation uses same context as agent (v0.2.3)
- [x] Grounded answer generation: agent quotes evidence from KG (v0.2.3)
- [x] Root cause analysis of Context Recall / Factual Correctness issues (v0.2.3)
- [x] Tool-based exploration: browse/read/search replacing tree-summary search (v0.3.0)
- [x] Verified Figure/Table references present in both Ch.01 (829 nodes) and Ch.05 (21 nodes)
- [x] RAGAs evaluation framework integration
- [x] Exclude already-explored nodes in search
- [x] Unified edge inference (new↔existing + new↔new pairs)
- [x] Two-tier edge ontology (Structural + Semantic)
- [x] GWM Intended/Unintended Action correction in research proposal
- [x] Dynamic termination condition (sufficient evidence → early stop)
- [x] Summary-based KG context (fix content truncation issue)
- [x] Research proposal with updated methodology (docs/research_proposal.md)
- [x] BM25 search ranking replacing naive keyword match (v0.3.1)
- [x] Full 100-question benchmark: 58 min (4x parallel), 99/100 success (v0.3.1)
- [x] Agent Memory: search history prevents keyword repetition (v0.4.2)
- [x] Multihop benchmark (200q): 100 min (8x parallel), 200/200 success, SATISFIES 659 instances (v0.4.2)
- [x] Faithfulness 100% measurement: RAGAs max_tokens 1024→4096 (v0.4.3)
- [x] Concise answers (2213→324 chars): Faith 0.71→0.95, FC 0.39→0.58 (v0.4.4)
- [x] Browse-first + concise answers (200q): Faith 0.93, CR 0.93, FC 0.42 (v0.4.5)
- [x] Benchmark feedback document: FC ceiling analysis + 5 improvement proposals (v0.4.5)
- [x] PRF (RM3) query expansion: zero LLM cost, fixes vocabulary mismatch (v0.4.6)
- [x] LLM-as-Judge pipeline integration: 3 evaluators + majority vote, 81.0% accuracy (v0.4.6)
- [x] Dual evaluation (RAGAs + LLM-as-Judge) on 200q multihop benchmark (v0.4.6)
- [x] 3-axis experiment analysis: benchmark types × evaluation frameworks × KG edges (v0.4.6)
- [x] Case studies: VIOLATES, SATISFIES, LEADS_TO, cross-doc, RAGAs-Judge disagreement (v0.4.6)
- [x] Relevance-based image selection: question keywords vs caption overlap (v0.3.2)
- [x] BM25 caption indexing: reference captions now searchable (v0.3.2)
- [x] Root cause analysis: Faithfulness N/A = answer length + KG size, not images (v0.3.2)
- [x] Description-first two-stage edge inference — CONTRADICTS/SATISFIES/SEMANTIC now emerge (v0.4.0)
- [x] Structured table extraction via PyMuPDF find_tables() (v0.4.1)
- [x] Table data passed directly in answer context (not via VLM image) (v0.4.1)
- [x] Figure/Table split: tables as text, figures as VLM images (v0.4.1)
