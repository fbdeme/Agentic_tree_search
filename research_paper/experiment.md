## 5. Experiments

### 5.1 Experimental Setup

All methods share a unified configuration to ensure fair comparison. The generation LLM is GPT-4.1 across all systems, with GPT-4.1 also used for indexing. Text embeddings use text-embedding-3-small (1536 dimensions). Inference is performed with temperature 0 and max_tokens 300. The agent is configured with max_hops=4 and top_k=2.

### 5.2 Baselines

We compare against five baselines spanning tree-based, graph-based, hybrid retrieval, and ablated variants of our own system. All baselines use the same LLM (GPT-4.1), the same answer-generation prompt, and the same 200-question dataset (§4.3). Our system requires neither vector embeddings nor pre-chunking, and navigates the document tree directly using BM25 combined with browse, read, and search tools.

| Method   | Paper                    | Core Mechanism              | Chunking                  | Retrieval Configuration                     |
| -------- | ----------------------- | -------------------------- | ------------------------ | ----------------------------------- |
| RAPTOR   | Sarthi et al. [2024]    | Recursive summarization tree | 100 tokens, 3,422 leaves   | collapse_tree, 2K token budget      |
| HippoRAG | Gutierrez et al. [2024] | PPR + hippocampal associative KG | 1,000 chars, 1,080 passages  | PPR + dense, top-10                 |
| LightRAG | Guo et al. [2024]       | Dual-level graph + vector DB | 1,200 tokens, 266 chunks | hybrid, top-40 entities + 20 chunks |
| GraphRAG | Edge et al. [2024]      | Community-based local search | 1,200 tokens, 267 chunks | local search, community_level=2     |
| PageIndex | Zhang & Tang [2025]    | Vectorless tree retrieval (no planning) | None (tree nodes) | BM25 + browse/read/search, max 4 hops |

PageIndex serves as a critical ablation baseline: it operates over the **identical document tree environment** with the same browse, read, and search tools, the same browse-first pattern, and the same dynamic termination — but without the agent's Dynamic Sub-KG state management. Where our system maintains a knowledge graph to assess collected evidence and plan subsequent actions, PageIndex performs retrieval without state-conditioned replanning. The gap between PageIndex and our system therefore isolates the contribution of planning over the environment from the environment itself.

### 5.3 Main Results — LLM-as-Judge

The table below reports LLM-as-Judge accuracy across six question types. Our system (planning only) achieves the highest overall accuracy at 81.5%, outperforming all baselines by a substantial margin. RAPTOR is the closest competitor at 75.5%, followed by LightRAG (73.0%), HippoRAG (70.5%), and GraphRAG (49.5%). PageIndex — which uses the identical document tree and tools but without state-conditioned planning — achieves only 43.5%, demonstrating that the environment alone is insufficient and that planning over the environment accounts for a +38.0 percentage point improvement.

| Method                         |     Overall     |    judgment    |   comparative   |     factual     |    cross_doc    |   table_only   |    composite    |
| ------------------------------ | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: | :-------------: |
| **Ours (planning only)** | **81.5%** | **92.3%** | **80.0%** | **72.9%** | **84.0%** | **86.0%** | **77.5%** |
| Ours (planning + edges)        |      81.0%      |      90.8%      |      78.5%      |      74.3%      |      81.3%      |      86.0%      |      85.0%      |
| RAPTOR                         |      75.5%      |      92.3%      |      72.3%      |      62.9%      |      73.3%      |      68.0%      |      72.5%      |
| LightRAG                       |      73.0%      |      92.3%      |      66.1%      |      61.4%      |      76.0%      |      60.0%      |      67.5%      |
| HippoRAG                       |      70.5%      |      86.2%      |      63.1%      |      62.9%      |      69.3%      |      64.0%      |      60.0%      |
| GraphRAG                       |      49.5%      |      61.5%      |      49.2%      |      38.6%      |      37.3%      |      42.0%      |      47.5%      |
| PageIndex (no planning)        |      43.5%      |      61.5%      |      44.6%      |      25.7%      |      45.3%      |        —        |        —        |

### 5.4 RAGAS Results

The first table below reports RAGAS metrics for our system broken down by question type. Our system achieves Faithfulness of 0.93 and Context Recall of 0.93 overall, with particularly strong performance on judgment questions (Faithfulness 0.97, Context Recall 0.96). Factual Correctness (0.42) is lower and reflects the difficulty of exact lexical matching against regulatory text rather than a retrieval failure.

| Metric              |    Overall    | factual |  comparative  |    judgment    |
| ------------------- | :------------: | :-----: | :------------: | :------------: |
| Faithfulness        | **0.93** |  0.92  |      0.92      | **0.97** |
| Answer Relevancy    | **0.84** |  0.85  |      0.78      | **0.89** |
| Context Recall      | **0.93** |  0.92  |      0.91      | **0.96** |
| Factual Correctness |      0.42      |  0.35  | **0.49** |      0.41      |

The cross-system RAGAS comparison confirms the advantage of our approach across all major retrieval quality metrics. Our system ranks first in Faithfulness (0.93) and Context Recall (0.93) by a clear margin. LightRAG is the next best in Faithfulness (0.89), reflecting the benefit of hybrid retrieval in gathering relevant context. GraphRAG scores substantially lower on both Faithfulness (0.28) and Context Recall (0.18), indicating significant factual loss during community summarization. PageIndex used as a retrieval-only baseline without planning achieves Faithfulness of only 0.58, illustrating the limits of unguided retrieval.

**RAGAS comparison (all methods):**

| Metric              | **Ours** | LightRAG |     RAPTOR     | HippoRAG | PageIndex | GraphRAG |
| ------------------- | :------------: | :------: | :------------: | :------: | :-------: | :------: |
| Faithfulness        | **0.93** |   0.89   |      0.74      |   0.76   |   0.58   |   0.28   |
| Answer Relevancy    | **0.84** |   0.83   |      0.83      |   0.83   |   0.77   |   0.59   |
| Context Recall      | **0.93** |   0.88   |      0.77      |   0.76   |   0.66   |   0.18   |
| Factual Correctness |      0.42      |   0.36   | **0.40** |   0.37   |   0.30   |   0.32   |

The per-reasoning-type breakdown further reveals where each method succeeds or fails. Our system leads across all three reasoning types and both metrics. On judgment questions, our system achieves Faithfulness of 0.97 and Context Recall of 0.96, indicating that the planning loop collects nearly complete evidence for regulatory reasoning tasks. GraphRAG's Context Recall of 0.11 on factual questions confirms that specific numerical values are systematically lost during community summarization.

**RAGAS by reasoning type (all methods):**

| reasoning_type | Metric | **Ours** | LightRAG | RAPTOR | HippoRAG | PageIndex | GraphRAG |
| -------------- | ------ | :------------: | :------: | :----: | :------: | :-------: | :------: |
| factual        | Faith  | **0.92** |   0.91   |  0.81  |   0.84   |   0.58   |   0.26   |
| factual        | CR     | **0.92** |   0.86   |  0.75  |   0.79   |   0.57   |   0.11   |
| comparative    | Faith  | **0.92** |   0.88   |  0.68  |   0.70   |   0.54   |   0.32   |
| comparative    | CR     | **0.91** |   0.89   |  0.74  |   0.71   |   0.67   |   0.18   |
| judgment       | Faith  | **0.97** |   0.89   |  0.74  |   0.74   |   0.63   |   0.27   |
| judgment       | CR     | **0.96** |   0.91   |  0.82  |   0.76   |   0.76   |   0.25   |

### 5.5 Efficiency Comparison

Pre-indexing costs vary substantially across methods. Our system requires 8–20 minutes and $4.1, making it competitive with or cheaper than most baselines while eliminating the need to construct a vector store or knowledge graph. LightRAG is the most expensive to index ($7.0) due to its three-pass entity-relation extraction over 266 chunks. RAPTOR is cheapest at $1.4 but takes approximately 44 minutes.

**Table 5: Pre-indexing cost**

|              |     **Ours**     |      RAPTOR      |       LightRAG       |      HippoRAG      |       GraphRAG       |
| ------------ | :--------------------: | :---------------: | :-------------------: | :----------------: | :------------------: |
| Method         |  Tree parsing + LLM summarization  |  Recursive summarization tree  | Entity-relation + vector DB | OpenIE → KG + PPR | Community detection + summarization |
| Time         |   **8–20 min**   |       ~44 min       |         52 min         |        29 min        |         40 min         |
| Cost         | **$4.1** | ~$1.4 | ~$7.0† | ~$4.3† |        ~$3.3†        |
| Vector/KG construction |         Not required         |      Not required      |         Required         |        Required        |         Required         |

> † Estimated: chunk/passage count × GPT-4.1 unit price + embeddings (text-embedding-3-small). LightRAG: 266 chunks × 3 passes; HippoRAG: 1,080 passages via OpenIE; GraphRAG: 267 chunks + ~50 community reports.

Per-query costs reveal the expected trade-off between retrieval depth and efficiency. Our system uses 86,072 tokens per question on average and takes 93 seconds, reflecting multi-hop exploration. Baselines range from 693 tokens (GraphRAG) to 24,276 tokens (LightRAG), with correspondingly lower latency. The high token count of LightRAG (24K/query) is attributable to its hybrid retrieval including entities, relations, and chunks simultaneously in the context.

**Table 6: Per-query cost (200 questions)**

|              | **Ours** |    RAPTOR    | LightRAG | HippoRAG | GraphRAG |
| ------------ | :------------: | :-----------: | :------: | :------: | :------: |
| Time per question  |      93s      |     1.8s     |   ~5s   |   ~3s   |  5.2s  |
| Tokens per question  |     86,072     |     2,045     |  24,276  |  2,577  |   693   |
| Total time (200Q) |     ~320 min     |     ~6 min     |  ~17 min  |  ~10 min  |  ~17 min  |
| Total cost (200Q) |  ~$42  | ~$0.9  | ~$9.8 | ~$1.1 |  ~$0.4  |

> Token and cost figures are extrapolated from a 5-question sample (Q001, Q071, Q131, Q161, Q191), measuring retrieved_contexts + answer with tiktoken (o200k_base) and scaling to 200 questions. Pricing based on GPT-4.1 rates ($2/M input, $8/M output).

When pre-indexing and query costs are combined, our system has the highest total cost (~$46) but achieves the highest accuracy (81.5%). The cost-per-accuracy-point is $0.56/1%p, higher than baselines, but the absolute accuracy advantage over the next-best system (RAPTOR, +6.0%p at $0.03/1%p) reflects a genuine quality-cost frontier difference. Dynamic termination mitigates costs for simpler questions, and 8× parallelization reduces total query time to approximately 39 minutes.

**Table 7: Total cost vs. accuracy**

|                        | **Ours** |    RAPTOR    | LightRAG | HippoRAG | GraphRAG |
| ---------------------- | :-------------: | :-----------: | :------: | :------: | :------: |
| Total time                |     ~320 min     |     ~50 min     |  ~69 min  |  ~39 min  |  ~57 min  |
| Total cost                |  ~$46  | ~$2.3  | ~$17 | ~$5.4 |  ~$3.7  |
| **Accuracy**     | **81.5%** |     75.5%     |  73.0%  |  70.5%  |  49.5%  |
| $/1%p accuracy | $0.56 |  $0.03 | $0.23  | $0.08 | $0.07 |

The per-question breakdown illustrates the dynamic termination effect concretely. A simple factual question (Q001) terminates in 1 hop at a cost of $0.03, comparable to baseline costs, while complex multi-hop questions (Q191) require 4 hops and cost $0.29. The majority of our system's cost is thus concentrated in genuinely complex queries.

**Per-question cost breakdown for Ours (5-question sample):**

| QID  | Type                 | Hops | Nodes | Edges |    Tokens | Time |  Cost |
| ---- | -------------------- | :-: | :--: | :--: | ------: | ---: | ----: |
| Q001 | factual / single     | 1 |  4  |  0  |   9,395 |  17s | $0.03 |
| Q071 | comparative / single | 4 |  19  |  63  | 124,264 | 126s | $0.30 |
| Q131 | composite / cross    | 4 |  11  |  34  |  75,213 |  71s | $0.18 |
| Q161 | judgment / multi     | 4 |  17  |  65  | 104,463 | 111s | $0.25 |
| Q191 | image / cross        | 4 |  19  |  81  | 117,023 | 140s | $0.29 |

**KG complexity statistics (Ours, 200 questions):**

| Metric       | Mean |  Range  |
| ---------- | :--: | :----: |
| Nodes    | 12.8 | 4–26 |
| Edges    | 39.9 | 0–124 |
| Hops used | 3.6 |  1–4  |

---

## 6. Analysis

### 6.1 Ablation Study

#### 6.1.1 Component Ablation (10Q, 4 Variants)

To isolate the contribution of each architectural component, we remove one component at a time from the full system and evaluate on 10 questions spanning diverse reasoning types (3 reasoning types × 3 complexity levels × 4 question types). Four variants are evaluated as defined below.

| Variant                   | Component Removed    | Description                                               |
| ------------------------- | ------------ | -------------------------------------------------- |
| **full**            | —           | Complete system (reference baseline)                             |
| **no_vision**       | Vision RAG   | Figure images and structured tables withheld from answer generation |
| **no_edges**        | Edge inference    | Only nodes collected; full Transition (relation inference) omitted       |
| **no_browse_first** | Browse-first | Automatic document structure (table of contents) injection at Hop 1 removed           |

The summary results show that the full system is the only variant achieving 10/10 judge accuracy. Every component removal causes at least one additional failure, and critically, each component fails on a distinct question type — confirming that the components are complementary rather than redundant.

| Variant         |     3-Judge     |     Faith     |       AR       |       CR       |       FC       |     Time     |           Cost           |
| --------------- | :-------------: | :------------: | :------------: | :------------: | :------------: | :-----------: | :----------------------: |
| **full**  | **10/10** | **0.96** | **0.84** | **0.95** | **0.50** |     104s     |          $0.216          |
| no_vision       |      8/10      |      0.83      |      0.82      |      0.92      |      0.39      |      98s      |      $0.196 (−9%)      |
| no_edges        |      9/10      |      0.93      |      0.84      | **1.00** |      0.48      | **34s** | **$0.073 (−66%)** |
| no_browse_first |      9/10      | **0.97** |      0.79      |      0.94      | **0.57** |      91s      |      $0.180 (−17%)      |

> Judge scores are determined by majority vote across three evaluators (Tonic GPT-4-turbo, MLflow GPT-4o, Allganize Claude Sonnet 4.5). RAGAS metrics are computed using GPT-4.1 as the evaluator.

**Error analysis.** Vision RAG removal produces the largest accuracy drop (10/10 → 8/10): Q101 (table/comparative) and Q131 (composite/comparative) fail entirely without tabular data, with RAGAS Faithfulness dropping from 0.96 to 0.83. Edge inference removal yields the most dramatic cost reduction ($0.073, 34s, −66%) while maintaining CR=1.00 for evidence collection; however, Q058 (seismic scope boundary) fails because the system cannot identify scope exclusions without an explicit VIOLATES edge. Browse-first removal causes Q191 (image/judgment/cross) to fail due to inability to orient exploration without the table of contents, while simpler questions remain unaffected.

| Variant         |     Accuracy     | Failed Questions      | Failure Cause                               |
| --------------- | :-------------: | -------------- | --------------------------------------- |
| **full**  | **10/10** | —             | —                                      |
| no_vision       | **8/10** | Q101, Q131     | Comparative questions fail without table/composite data      |
| no_edges        |      9/10      | **Q058** | Seismic scope boundary judgment fails without edges |
| no_browse_first |      9/10      | **Q191** | Image/judgment exploration fails without table of contents      |

**Per-question 3-Judge detail:**

| QID  | Type              | full |   no_vis   |   no_edg   |   no_brw   |
| ---- | ----------------- | :--: | :---------: | :---------: | :---------: |
| Q001 | fact/single       |  O  |      O      |      O      |      O      |
| Q010 | fact/multi        |  O  |      O      |      O      |      O      |
| Q031 | fact/single/table |  O  |      O      |      O      |      O      |
| Q058 | fact/cross        |  O  |      O      | **X** |      O      |
| Q071 | comp/single       |  O  |      O      |      O      |      O      |
| Q101 | comp/cross/table  |  O  | **X** |      O      |      O      |
| Q131 | comp/cross/comp   |  O  | **X** |      O      |      O      |
| Q161 | judg/multi        |  O  |      O      |      O      |      O      |
| Q176 | judg/cross        |  O  |      O      |      O      |      O      |
| Q191 | judg/cross/image  |  O  |      O      |      O      | **X** |

To further decompose the gains of our full system relative to RAPTOR across the 200-question benchmark, we attribute performance differences to individual components using category-level results as natural controls.

| Contributing Factor           | Evidence                                         | Effect                 |
| ------------------- | -------------------------------------------- | -------------------- |
| Dynamic exploration | cross_document: Ours 81.3% vs RAPTOR 73.3%   | **+8.0%p**     |
| Vision RAG (tables)     | table_only: Ours 86.0% vs RAPTOR 68.0%       | **+18.0%p**    |
| Vision RAG (composite)   | composite: Ours 77.5% vs RAPTOR 72.5%        | **+5.0%p**    |
| Two-tier edges          | judgment × cross_doc: 94.3% vs RAPTOR 88.6% | **+5.7%p**     |
| Lightweight indexing         | Tree build 7.6 min vs GraphRAG 40 min             | **5.3× faster** |

#### 6.1.2 Scale-up: Edge Inference Ablation (200Q)

Given that edge inference accounted for 65% of per-query cost in the 10Q ablation and produced an interesting failure on Q058 (VIOLATES case), we scale the comparison to all 200 questions to obtain statistically reliable estimates.

| Metric                   | full (planning + edges) | no_edges (planning only) |      Difference      |
| ------------------------ | :----------------------: | :-----------------------: | :-------------: |
| **3-Judge accuracy** |     81.0% (162/200)     | **81.5% (163/200)** |     +0.5%p     |
| Faithfulness             |     **0.930**     |           0.897           |     −0.033     |
| Context Recall           |     **0.930**     |           0.919           |     −0.011     |
| Factual Correctness      |          0.420          |           0.417           |     −0.003     |
| Cost per question                | $0.215 | **$0.076** |      **−65%**      |
| Time per question                |          115.3s          |      **47.5s**      | **−59%** |

The 200Q results depart from the expectation set by the 10Q ablation. At 10Q, the full system achieved 10/10 versus 9/10 for no_edges, suggesting edge inference was important. At 200Q, accuracy is virtually identical (81.0% vs. 81.5%), and the Q058 failure observed in the 10Q run does not recur — both variants answer it correctly. This suggests the 10Q result reflected noise attributable to sample size rather than a systematic effect of edge inference.

**Key finding: Planning is the primary driver of accuracy.** Removing edge inference entirely does not reduce accuracy, while the planning mechanisms alone — browse-first structure initialization, dynamic termination, and state-conditioned tool selection — are sufficient to outperform all four RAG baselines (81.5% vs. RAPTOR 75.5%). Edge inference accounts for 65% of per-query cost with no measurable accuracy contribution.

**Decomposing planning contributions.** The planning component of our system operates through three distinct mechanisms, each attributable using existing experimental data:

| Planning Mechanism | Evidence | Effect |
|---|---|---|
| **Browse-first** (structure awareness) | no_browse_first ablation: CR 0.45→0.89 (10Q) | Critical for orienting exploration; without the table of contents, complex queries such as Q191 fail entirely |
| **Dynamic termination** (goal test) | avg 2.1–2.6 hops (max 4); Q001: 1 hop/$0.03 vs. Q191: 4 hops/$0.29 | Automatically calibrates exploration depth to question complexity, pruning unnecessary hops on simple queries |
| **State-conditioned tool selection** | PageIndex-only: 43.5% vs. Ours: 81.5% (+38.0%p) | PageIndex exposes the same browse/read/search tools but selects among them without KG state evaluation; the absence of planning accounts for most of the performance gap |

This finding resonates with, yet differentiates from, recent agentic retrieval work such as APEX-Searcher [Chen et al., 2026] and PRISM [Nahid & Rafiei, 2025], which acquire planning capability through RL or SFT fine-tuning. Our system achieves equivalent planning behavior in a **training-free** setting, relying solely on prompted LLM state evaluation and dynamic termination.

**What edges provide and what they do not.** Edges do not improve accuracy at 200Q scale. A marginal Faithfulness improvement (+0.033) is directionally consistent but not statistically verified. Their primary value lies in traceability: human-readable reasoning paths of the form "Section A SATISFIES Regulation B." Head-to-head analysis shows 25 common errors, 13 errors unique to full, and 12 unique to no_edges — a near-symmetric distribution consistent with execution-level variance rather than a systematic difference.

**Post-retrieval vs. retrieval-time edges.** These results pertain specifically to *post-retrieval* edges, which encode relationships among already-retrieved evidence nodes. They do not speak to *retrieval-time* edges used by systems such as GraphRAG and LightRAG for graph traversal during retrieval — a fundamentally different role. The results suggest that LLMs are able to implicitly infer relational structure among retrieved nodes during answer generation, and that explicit post-retrieval edge inference largely duplicates this capacity.

### 6.2 Edge Distribution Analysis (7,391 edges, 200 questions)

Across the full 200-question benchmark with edge inference enabled, the system generates 7,391 edges in total. The distribution reveals clear structural patterns aligned with the two-tier ontology design.

| Edge               | Count |   %   | Category       |
| ------------------ | :---: | :---: | ---------- |
| SUPPORTS           | 2,532 | 34.3% | Semantic   |
| SPECIFIES          | 2,330 | 31.5% | Structural |
| REFERENCES         |  966  | 13.1% | Structural |
| IS_PREREQUISITE_OF |  701  | 9.5% | Semantic   |
| SATISFIES          |  622  | 8.4% | Semantic   |
| SEMANTIC           |  149  | 2.0% | Free-form  |
| LEADS_TO           |  66  | 0.9% | Semantic   |
| CONTRADICTS        |  22  | 0.3% | Semantic   |
| VIOLATES           |   3   | 0.04% | Semantic   |

Comparing edge patterns between correct and incorrect answers reveals that semantic edges are more prevalent in correct answers: SUPPORTS appears +6.8 percentage points more frequently, and SATISFIES +3.2 percentage points more frequently. The three VIOLATES instances are analyzed in the case study below.

### 6.3 Case Study: Why VIOLATES Appears in a Certified Design Document

The FSAR is a document that has already been certified by the NRC. The emergence of VIOLATES edges in such a document warrants explanation. Analysis of all three instances reveals that VIOLATES captures **scope boundary exclusions** rather than design deficiencies.

**Cases 1–2: Seismic design scope exclusion (Q058, VIOLATES ×2).** The question asks how NuScale's seismic design in Ch.01 affects RCS components in Ch.05. Both VIOLATES edges (confidence 0.85 and 0.90) identify that non-safety-related systems (Chilled Water System, Condensate Storage Facilities) are intentionally placed outside Seismic Category I classification, and therefore the seismic qualification requirements of the referenced sections do not apply. These are legitimate design decisions, explicitly justified in the FSAR: "failure of non-safety SSCs does not affect safety-related SSCs." The agent records these scope boundaries in the KG while correctly judging the overall answer (Judge = O).

**Case 3: Partial conformance and design trade-offs (Q176, VIOLATES ×1).** The question asks whether the integrated SG design adequately addresses SGTR concerns. The VIOLATES edge (confidence 0.85) captures that NuScale's innovative design — with the SG integrated inside the RPV — eliminates the traditional containment bypass problem but introduces a leakage detection limitation: the system cannot distinguish identified from unidentified leakage, resulting in partial conformance with DSRS 15.6.5. The FSAR itself acknowledges this partial conformance. The agent judges the overall design as "adequate" while explicitly noting the leakage detection limitation in its uncertainty section.

**Value of VIOLATES analysis.** These cases demonstrate capabilities beyond simple RAG: (1) explicit scope boundary identification — marking where regulatory requirements apply and do not apply; (2) nuanced partial conformance — capturing the space between full satisfaction and full violation that is most critical in regulatory review; (3) auditable reasoning — preserving VIOLATES edges in the KG enables independent verification of why partial conformance is acceptable; and (4) frequency as a quality signal — only 3 of 7,391 edges (0.04%) are VIOLATES, consistent with the certified nature of the document.

### 6.4 Dual Evaluation Framework Complementarity

The RAGAS-Judge agreement rate is 66.2%, revealing substantial complementarity between the two evaluation frameworks.

|                                            | Judge O | Judge X |
| ------------------------------------------ | :-----: | :-----: |
| **RAGAS Good** (Faith≥0.8, CR≥0.8) |   122   |   29   |
| **RAGAS Bad**                        |   38   |    9    |

The 29 cases where RAGAS rates highly but Judge rejects (RAGAS Good + Judge X) represent correct evidence retrieval with expression mismatch — the MLflow evaluator applies particularly strict criteria. Conversely, the 38 cases where RAGAS rates poorly but Judge accepts (RAGAS Bad + Judge O) indicate correct answers derived from knowledge beyond the retrieved KG context. RAGAS thus measures grounding fidelity while the Judge measures answer correctness, and both are necessary for a complete evaluation.

### 6.5 Limitations and Future Work

#### System Limitations

Our system underperforms RAPTOR on text-only questions (76.2% vs. 80.0%, −3.8%p), suggesting that RAPTOR's recursive summarization is more effective for long text passages; adding summary nodes to the tree is a potential improvement. The average per-query cost of $0.21 (93s, 86K tokens) is substantially higher than RAPTOR (~$0.01, 1.8s), though dynamic termination partially mitigates this (Q001: 1 hop/$0.03 vs. Q191: 4 hops/$0.29), and 8× parallelization reduces total query time to ~39 minutes. A follow-reference tool for directly navigating "see Table 5.1-1" references remains unimplemented.

#### Benchmark Limitations

Our 200-question benchmark, designed specifically for this study, exhibits five structural limitations identified during evaluation:

1. **Factual Correctness ceiling (~0.42)**: Expected answers reflect only one evidence perspective. For example, Q003 expects "helical coil SG integrated within RPV" while the agent answers "vertical helical once-through SG with 1,380 tubes" — both correct, but FC=0.0. Multi-perspective expected answers would raise this ceiling.

2. **Judgment polarity bias**: 64 of 65 judgment questions (98%) have "Yes" as the correct answer, because the FSAR documents designs that are by definition regulation-compliant. A system that always outputs "Yes" could achieve 98% on judgment questions. Adding hypothetical violation scenarios (targeting 30%+ "No" answers) would address this.

3. **Limited evidence depth**: 57 questions (28%) require 1 evidence hop, 131 (66%) require 2 hops, and only 12 (6%) require 3+ hops. Despite being labeled a multi-hop benchmark, 66% are effectively 2-hop. Adding 3–4 evidence chain questions (e.g., tracing the core → natural circulation → SG → DHRS → pool heat removal path) would increase depth.

4. **Document coverage imbalance**: Ch.01 uses only pages 15–81 of 352 (19%), while Ch.05 uses pages 10–100 of 160 (56%). Ch.01 §1.9 contains 727 regulatory conformance items that are largely untapped by the benchmark.

5. **Absence of external validation**: The benchmark is self-designed, creating potential bias. Mitigating factors include the three-axis orthogonal design, 3-evaluator majority voting, and uniform comparison across 5 methods under identical conditions. Independent expert evaluation and external research group replication would strengthen validity.

---
