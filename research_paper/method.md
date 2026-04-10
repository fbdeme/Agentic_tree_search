## 3. Method

![Figure 1: Overall architecture. The vectorless document tree (left) serves as the environment. The planning loop (center) iterates through state estimation, action planning, execution, and sufficiency checking. Post-retrieval edge inference and vision-augmented answer generation (right) are applied at the output stage.](figures/outputs/run_20260408_190632_a034ed/final_output.png)

### 3.1 Environment: Vector-Free Multimodal Document Tree

While the planning loop described in this section (state estimation, action selection, dynamic termination) is architecturally domain-agnostic — applicable to any hierarchically structured document corpus — regulatory documents such as FSARs present the conditions under which this approach is most advantageous over conventional RAG: deep hierarchical structure that chunking destroys, dense cross-references between sections and figures, multimodal evidence (specification tables, engineering drawings) that co-determines answers, and a review process that inherently requires multi-hop evidence gathering with sufficiency judgment. The domain-specific component is the edge ontology (Section 3.4), which encodes regulatory reasoning relations (SATISFIES, VIOLATES); the rest of the architecture transfers directly to other structured document domains.

The environment is represented as a JSON hierarchical tree organized into chapter → section → paragraph nodes, preserving the native structure of regulatory documents without any chunking or embedding. To support multimodal reasoning, the system parses the LIST OF FIGURES/TABLES and detects in-text references such as "Figure 5.1-1," attaching figure and table metadata to the corresponding nodes via a `references` field. This directly addresses the "figure on different page" problem, wherein the referencing text and the actual diagram reside on different pages of the PDF.

Rather than relying on dense vector retrieval, the system adopts a vector-free design using BM25Okapi [Robertson & Zaragoza, 2009] keyword search over the full document tree. Section titles receive a 3× weight boost, and document-length normalization naturally promotes short, focused leaf nodes to higher rankings. At the scale evaluated in this work, the tree spans Ch.01 with 866 nodes (34 figures, 19 tables) and Ch.05 with 26 nodes (29 figures, 30 tables).

![Figure 2: The FSAR hierarchical document tree environment (left), the three agent tools with their interfaces (right), and the multimodal reference resolution mechanism that links in-text references to actual figures on different pages (bottom).](figures/outputs/run_20260408_190632_f36a5b/final_output.png)

### 3.2 State (Short-Term Memory): Dynamic Sub-KG and Two-Tier Edge Ontology

The agent state at timestep $t$ is defined as a dynamic knowledge graph $G_t = (V_t, E_t)$. The node set $V_t$ comprises document sections (evidence nodes) collected through exploration along with their associated multimodal references. The edge set $E_t$ is governed by a domain-specific two-tier ontology, with edges retained only when confidence is ≥ 0.4.

Tier 1 consists of structural edges that form the backbone of the exploration trajectory:

| Edge | Academic Origin | Domain Application |
| --- | --- | --- |
| REFERENCES | Citation networks [Garfield, 1979] | Section A cross-references Section B |
| SPECIFIES | SysML `<<refine>>` [Friedenthal et al., 2014] | Provides detailed specifications for a higher-level description |

Tier 2 consists of semantic edges that capture regulatory reasoning relationships:

| Edge | Academic Origin | Domain Application |
| --- | --- | --- |
| SATISFIES / VIOLATES | SysML requirements tracing [Friedenthal et al., 2014]; construction regulations [Zhong et al., 2012] | Design outcome node satisfies or violates a regulatory requirement node |
| SUPPORTS / CONTRADICTS | Argumentation mining [Peldszus & Stede, 2013]; textual entailment [Cabrio & Villata, 2012] | Cross-validation of evidence across multiple documents |
| LEADS_TO | Causal KG [Hassanzadeh et al., 2019] | Cause-effect tracing in incident analysis reports |
| IS_PREREQUISITE_OF | Prerequisite relation learning [Pan et al., 2017] | Linking documents that must be reviewed as prior conditions |

Empirically, structural edges (REFERENCES, SPECIFIES) dominate in single-hop factual queries by forming the exploration path, while semantic edges (SATISFIES, SUPPORTS) emerge in composite multi-hop judgment queries to support regulatory compliance synthesis. In correct answers relative to incorrect ones, SUPPORTS appears +6.8 percentage points more frequently and SATISFIES +3.2 percentage points more frequently.

![Figure 3: An example Dynamic Sub-Knowledge Graph showing five evidence nodes connected by structural (Tier 1) and semantic (Tier 2) edges. The edge distribution summary (right) shows the prevalence of each edge type across 7,391 edges from 200 questions.](figures/outputs/run_20260408_190632_afca44/final_output.png)

### 3.3 Action Planning: LLM-Based Tool Selection

Rather than precomputing a full retrieval plan offline, the system performs closed-loop online planning. At each hop, the agent observes the current KG state $s_t$ and decides the next action $a_{t+1}$, with environment feedback (retrieved results) immediately incorporated into the subsequent plan. This constitutes a state-based iterative decision-making structure, distinct from the plan-then-execute separation of APEX-Searcher [Chen et al., 2026] and the token-level reactive retrieval of Self-RAG [Asai et al., 2024]. Unlike passive embedding-similarity retrieval in conventional RAG, the LLM actively evaluates the current state and plans the next action.

The agent has access to three tools that mirror familiar filesystem operations:

| Tool | Analogy | Function |
| --- | --- | --- |
| `browse(doc_id, node_id)` | `ls` | List child nodes of a tree node — hierarchical drill-down |
| `read(doc_id, node_id)` | `cat` | Extract the full content of a specific node |
| `search(keyword)` | `grep` | BM25-ranked keyword search across all documents |

A browse-first pattern is enforced at Hop 1, where the document structure (table of contents) is automatically injected so that the agent obtains a global map before searching. This intervention improved single-evidence Context Recall from 0.45 to 0.89. To address vocabulary mismatch, Pseudo-Relevance Feedback (PRF, RM3) automatically expands queries using the top-3 retrieved results at zero additional LLM cost. The agent also maintains a search history to prevent duplicate keyword queries across hops.

Dynamic termination is implemented as a plan sufficiency check beginning at Hop 2: before each hop, the LLM judges whether the current KG already contains sufficient evidence to answer the query. If so, the agent terminates early. This functions as a goal test within the planning loop, automatically calibrating exploration depth to query complexity. Across 200 questions, 33% of queries terminate early at 1–3 hops (mean 3.4, maximum 4). The remaining 67% use the full 4-hop budget, reflecting the multi-hop complexity of regulatory reasoning. Simple factual queries (e.g., Q001) complete in 1 hop (17 s, $0.03), while complex cross-document judgment queries (e.g., Q191) consistently require the full budget (140 s, $0.29).

### 3.4 Post-Retrieval Edge Inference (Optional Component)

Edge inference makes explicit the relationships among collected evidence nodes and is performed concurrently with the state transition $f_{tr}(s_t, a_t) \rightarrow s_{t+1}$. It is worth noting that ablation experiments on the 200-question benchmark found this component does not contribute to answer accuracy (see Section 6.1.2); it is therefore offered as an optional module for use cases requiring traceability.

Inference proceeds in two stages. In Stage 1 (Description), the LLM produces a single natural-language sentence describing the relationship between two nodes, without imposing any classification pressure. This follows the free-form relation extraction approach of LightRAG [Guo et al., 2024]; for example: "The ECCS design of 3 RVV + 2 RRV is configured to meet the acceptance criteria of 10 CFR 50.46." In Stage 2 (Ontology Mapping), the free-form description is mapped onto the regulatory domain ontology (SATISFIES, VIOLATES, etc.). When no mapping is applicable, the relationship is preserved as SEMANTIC, ensuring no relational information is discarded.

Crucially, verification is not a post-processing step separated from planning. Instead, it is interleaved within the planning loop at every hop: immediately after new evidence is retrieved (planning), relationship inference is performed (verification), and the resulting enriched KG state informs the plan sufficiency judgment for the subsequent hop. This design differs from embedding-based implicit relations used in GraphRAG and GWM; by grounding relationships in explicit LLM-generated natural-language descriptions, the inference results remain human-inspectable.

### 3.5 Vision-Augmented Final Answer Generation

Multimodal processing is applied exclusively at the final answer generation step, with all intermediate operations (search, plan, infer) remaining text-only. This cost-efficient design avoids the expense of vision API calls during iterative exploration while still enabling visually grounded final answers.

The implementation proceeds in three steps: (1) all Figure/Table references across KG nodes are collected; (2) the corresponding PDF pages are rendered to JPEG using PyMuPDF; and (3) the full text KG context together with the rendered images is passed to the GPT-4.1 vision API. For tables specifically, PyMuPDF's `find_tables()` function extracts row and column structure directly as structured text, making VLM image processing unnecessary. This approach achieves 86.0% accuracy on table-only questions, compared to 68.0% for RAPTOR (+18 percentage points).

---
