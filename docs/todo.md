# TODO

Task tracking for the GWM Multimodal Regulatory Document Exploration Agent.

---

## High Priority

### Evaluation
- [ ] Run full 100-question benchmark evaluation
- [ ] Analyze results by question type (text_only, table_only, image_only, composite)
- [ ] Fix Faithfulness metric timeout — consider further context/answer truncation or switching to a lighter evaluator model
- [ ] Validate that Vision RAG improves image_only question scores vs text-only baseline

### Search (Action) Enhancement
- [ ] Fix tree summary truncation (866 nodes exceed 3000 char limit)
  - Option A: Hierarchical drill-down (top-level first → drill into selected subtree)
  - Option B: Paginated tree search (show tree in chunks)
  - Option C: Two-stage search (coarse section selection → fine node selection)
- [ ] Multi-document search reliability — ensure both Ch.01 and Ch.05 trees are visible to LLM
- [ ] Store `end_index` in tree nodes (not just `page_index`) for accurate page range

### Edge Quality
- [ ] Add regulatory compliance judgment questions to QA dataset to trigger SATISFIES/VIOLATES edges
- [ ] Analyze edge type distribution across all 100 questions
- [ ] Validate two-tier edge hierarchy hypothesis: structural edges in single-hop, semantic edges in multi-hop

---

## Medium Priority

### Action Tooling (Search Enhancement v2)
- [ ] Implement multi-tool Action pattern:
  - `tree_search` — current approach (ToC-based reasoning)
  - `text_search` — BM25/keyword search for specific values and terms
  - `graph_query` — Neo4j Cypher queries on already-built KG
  - `follow_ref` — follow node's Figure/Table references
- [ ] Agent selects which tool to use per hop based on query type

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
- [ ] Update CLAUDE.md with current architecture
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
- [x] RAGAs evaluation framework integration
- [x] Exclude already-explored nodes in search
- [x] Unified edge inference (new↔existing + new↔new pairs)
- [x] Two-tier edge ontology (Structural + Semantic)
- [x] GWM Intended/Unintended Action correction in research proposal
- [x] Dynamic termination condition (sufficient evidence → early stop)
- [x] Summary-based KG context (fix content truncation issue)
- [x] Research proposal with updated methodology (docs/research_proposal.md)
