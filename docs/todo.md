# TODO

Task tracking for the GWM Multimodal Regulatory Document Exploration Agent.

---

## High Priority

### Evaluation
- [x] ~~Run full 100-question benchmark evaluation~~ → Completed (v0.3.1), 99/100 success
- [x] ~~Analyze results by question type~~ → See history.md v0.3.1 for full breakdown
- [ ] Fix Faithfulness metric timeout — only 54/99 scored (45% failure rate). Consider lighter evaluator model or shorter context.
- [ ] Investigate image_only low Factual Correctness (0.13) — is Vision RAG extracting useful info from diagrams?
- [ ] Address Factual Correctness structural limitation — agent's detailed answers penalized vs terse expected answers

### Search (Action) Enhancement
- [x] ~~Fix tree summary truncation~~ → Replaced with tool-based exploration (v0.3.0)
- [x] ~~Multi-document search reliability~~ → search() spans all documents (v0.3.0)
- [x] ~~BM25 search ranking~~ → Replaces naive keyword match, specific nodes rank higher (v0.3.1)
- [ ] Improve search keyword strategy — agent searches question terms but key info uses different vocabulary
- [ ] Encourage browse tool usage — agent defaults to search-only, rarely does hierarchical drill-down
- [ ] Store `end_index` in tree nodes (not just `page_index`) for accurate page range

### Data Quality
- [ ] Review QA dataset for factual errors — **Q004 confirmed**: expected answer says SG "outside RPV" but actually inside

### Edge Quality
- [ ] Add regulatory compliance judgment questions to QA dataset to trigger SATISFIES/VIOLATES edges
- [ ] Analyze edge type distribution across all 100 questions
- [ ] Validate two-tier edge hierarchy hypothesis: structural edges in single-hop, semantic edges in multi-hop

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
