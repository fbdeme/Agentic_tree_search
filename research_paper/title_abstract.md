## LLM-Guided Planning for Multi-hop Regulatory Document Exploration

**Target**: LM4Plan @ ICML 2026 (Deadline: April 24, 2026)

---

### Abstract

Reviewing nuclear Final Safety Analysis Reports (FSARs) requires assembling evidence chains across tens of thousands of pages to render regulatory conformance judgments — a process that is fundamentally a planning problem in an uncertain information environment. Existing retrieval-augmented generation (RAG) systems reduce this to passive, single-shot retrieval, failing to handle the multi-hop reasoning, structural complexity, and multimodal evidence that regulatory review demands. We propose an architecture in which an LLM plans information gathering over a vectorless document tree: at each hop, the agent assesses its current knowledge graph state, selects among browse, read, and search tools, and evaluates plan sufficiency — terminating when evidence is sufficient. Both the agent state and environment are represented in text rather than vectors, aligning with the LLM's native modality to enable effective planning. On a 200-question nuclear regulatory benchmark spanning three orthogonal axes (reasoning type, complexity, modality), our system achieves 81.5% accuracy (LLM-as-Judge), outperforming RAPTOR (75.5%), LightRAG (73.0%), HippoRAG (70.5%), and GraphRAG (49.5%), with RAGAS Faithfulness of 0.93 and Context Recall of 0.93. A 200-question ablation reveals that post-retrieval edge inference does not improve accuracy (81.0% vs. 81.5%) while increasing cost by 2.8x, establishing planning — not verification — as the primary driver of performance.

---
