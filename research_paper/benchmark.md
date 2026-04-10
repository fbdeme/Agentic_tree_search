## 4. Benchmark: Nuclear Regulatory Multi-hop QA

### 4.1 Motivation

Numerous benchmarks exist for document-based question answering, but none combine the four dimensions required by this work: nuclear regulatory domain, multi-hop reasoning, multimodal evidence (tables and engineering drawings), and regulatory judgment. The table below surveys the most relevant existing benchmarks along these dimensions.

| Benchmark | Document Type | Questions | Multi-hop | Tables | Figures | Cross-doc | Judgment |
|----------|----------|:----:|:------:|:--:|:----:|:-------:|:----:|
| NuclearQA [Acharya et al., 2023] | Nuclear domain knowledge | 100 | -- | -- | -- | -- | -- |
| FDARxBench [2025] | FDA drug labels | 17K | Yes | Yes | Partial | -- | Yes |
| MMLongBench-Doc [2024] | Long PDFs, 7 domains | 1,062 | Yes | Yes | Yes | -- | -- |
| M3DocVQA [2024] | Diverse PDFs | 2,441 | Yes | Yes | Yes | Yes | -- |
| DesignQA [2024] | Engineering docs + CAD | ~hundreds | -- | Yes | Yes | Yes | Partial |
| SEC-QA [2025] | SEC financial reports | 333 | Yes | Yes | -- | Yes | -- |
| TAT-QA [2021] | Financial reports (table+text) | 16K | Yes | Yes | -- | -- | -- |
| **Ours** | **Nuclear FSAR** | **200** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

FDARxBench is the most similar (regulatory documents with multi-hop reasoning and judgment), but covers only single documents without engineering drawings. MMLongBench-Doc and M3DocVQA support multimodal long-document understanding but lack regulatory judgment question types. DesignQA addresses engineering documentation and regulatory compliance but does not support multi-hop reasoning. Our benchmark is the first to combine nuclear regulatory multi-hop cross-document reasoning with multimodal evidence (tables and engineering drawings) and regulatory conformance judgment.

### 4.2 Design Principles

The benchmark is organized around a three-axis orthogonal classification scheme, where every question is tagged along reasoning type, complexity, and question type. Unlike single-dimensional difficulty labels (e.g., "easy/medium/hard"), three independent axes enable precise diagnosis of system weaknesses — for example, identifying a system that fails specifically on "factual x cross_document x table_only" questions.

The three reasoning types mirror the regulatory review process. **Factual** questions require single-fact retrieval (e.g., "What is the RCS operating pressure?"), corresponding to baseline verification in regulatory review. **Comparative** questions require cross-referencing (e.g., "Do the design parameters in Ch.01 Table 1.3-1 match the RCS specifications in Ch.05 Table 5.1-1?"), corresponding to document consistency checks. **Judgment** questions require regulatory conformance determination (e.g., "Does the ECCS design satisfy 10 CFR 50.46(b)?"), corresponding to the core task of regulatory review. The judgment x cross_document cell (35 questions) receives the largest allocation, reflecting the centrality and difficulty of this task in actual review practice.

Four question types capture multimodal evidence diversity: text_only (80 questions) requiring only narrative text, table_only (50) requiring interpretation of specification tables, image_only (30) requiring interpretation of engineering drawings (P&IDs, system diagrams), and composite (40) requiring combined use of text, tables, and drawings. Each question includes ground_truth_evidence annotations specifying the source document, page, source type (text/table/figure), and relevant text — enabling evaluation to distinguish "correct answer from wrong evidence" and "incorrect answer from correct evidence." The benchmark contains 357 total evidence items: 152 text, 125 table, and 80 figure.

### 4.3 Benchmark Composition

The source documents are NuScale FSAR Chapter 01 (352 pages) and Chapter 05 (160 pages), publicly available from the NRC. The 200 questions are distributed across the three axes as follows:

**Reasoning type x complexity:**

|                            | single_evidence | multi_evidence | cross_document |
| -------------------------- | :-------------: | :------------: | :------------: |
| **factual** (70)     |       30       |       25       |       15       |
| **comparative** (65) |       15       |       25       |       25       |
| **judgment** (65)    |        5        |       25       |  **35**  |

> The judgment x cross_document cell (35 questions) is the largest, reflecting the most frequent and challenging task in actual regulatory review.

**Question type distribution:**

| text_only | table_only | image_only | composite |
| :-------: | :--------: | :--------: | :-------: |
|    80    |     50     |     30     |    40    |

Representative examples include: "What is the total electric output of a 12-module NuScale plant?" (factual/single/text), "Compare the operating parameters in Ch.01 Table 1.3-1 with the RCS volumes in Ch.05 Table 5.1-1" (comparative/cross/table), and "Is the integrated SG design described in Ch.01 and Ch.05 adequate for SGTR concerns?" (judgment/cross/composite, Q176).

### 4.4 Dual Evaluation Framework

Recognizing the limitations of any single evaluation approach, we adopt a dual framework combining continuous-scale (RAGAS) and binary (LLM-as-Judge) evaluation.

RAGAS [Es et al., 2024] measures grounding quality — whether the answer is faithful to the retrieved context — across four metrics: Faithfulness (fraction of answer claims supported by context, detecting hallucination), Answer Relevancy (alignment with question intent), Context Recall (fraction of expected answer sentences supported by context, measuring retrieval completeness), and Factual Correctness (factual accuracy against the expected answer, wording-sensitive).

The LLM-as-Judge component employs three independent evaluators with majority voting: Tonic (GPT-4-turbo, 5-point scale, pass at 4+), MLflow (GPT-4o, dual similarity-correctness assessment), and Allganize (Claude Sonnet 4.5, 5-point scale, pass at 4+). A question is judged correct when at least two of three evaluators agree.

The dual approach is empirically motivated: the RAGAS-Judge agreement rate in our experiments is 66.2%, with the 34% disagreement providing complementary information. RAGAS excels at measuring grounding fidelity but underpenalizes correct answers derived from knowledge beyond the retrieved context; the Judge captures practical correctness but may reject answers with valid content expressed differently. Full complementarity analysis is presented in Section 6.4.

![Figure 4: Benchmark design overview. (A) Three-axis orthogonal taxonomy. (B) Reasoning x complexity distribution with judgment x cross_document as the largest cell. (C) Modality distribution and evidence piece counts. (D) Dual evaluation framework with RAGAS and LLM-as-Judge majority vote, showing 66.2% agreement rate.](figures/outputs/run_20260408_190632_ec3d1b/final_output.png)

---
