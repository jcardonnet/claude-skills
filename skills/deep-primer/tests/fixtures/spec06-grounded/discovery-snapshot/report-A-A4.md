# source-authority — wave A (brief A-A4)

# Evaluation of Retrieval-Augmented Generation Systems: Authoritative Sources and Methodologies

## Foundational Contributions

Rietrieval-Augmented Generation emerged as a distinct paradigm with **Lewis et al. (2020)**, which introduced RAG models combining pre-trained language models with dense vector retrieval over Wikipedia (arXiv:2005.11401). This foundational work demonstrated that hybrid parametric-nonparametric architectures outperform pure generative approaches on knowledge-intensive tasks. Concurrent architectures—**REALM** (Guu et al., 2020, arXiv:2002.08909), which jointly pre-trains retriever and language model, and **DPR** (Karpukhin et al., 2020, EMNLP 2020, arXiv:2004.04906), which uses dual-encoder dense retrieval—established the technical foundation RAG evaluation still builds on. **Fusion-in-Decoder** (Izacard & Grave, 2020, arXiv:2007.01282) introduced efficient multi-passage fusion through separate passage encoding and decoder-level synthesis. **3+ independent sources** cite these as seminal; no disagreement on their canonical status.

## Evaluation Dimensions and Metrics (2024–2025)

Recent comprehensive surveys establish consensus on three evaluation layers: **(1) Retrieval Quality** (precision, recall, MRR, NDCG), **(2) Generation Quality** (BLEU, ROUGE, BERTScore, faithfulness), and **(3) End-to-End System Performance** (answer accuracy, factual grounding). **2+ major sources** (arxiv:2504.14891 survey and arxiv:2405.07437 survey) align on this decomposition.

Multi-dimensional frameworks dominate current practice. **RAGAS** (Exploding Gradients, 2023, GitHub: vibrantlabsai/ragas) evaluates faithfulness, answer relevancy, context precision, and context recall without requiring ground-truth annotations. **RAGBench/TRACe** (arxiv:2407.11005) formalizes explainable metrics covering Relevance, Utilization, Completeness, and Adherence applicable across domains. **VERA** (arxiv:2409.03759, Sept 2024) adds cross-encoder-based ranking and bootstrap confidence bounds for repository coverage. **RAGCHECKER** (NeurIPS 2024) provides fine-grained diagnostic evaluation. **3–4 independent frameworks** cite these; no methodological disagreement, though metric selection varies by domain.

## Recent Benchmarks and Domain-Specific Work

**CRUD-RAG** (arXiv:2401.17043, v3 July 2024) extends beyond QA to Create/Read/Update/Delete operations for comprehensive Chinese-language evaluation. **MIRAGE-Bench** (arxiv:2410.13716) addresses multilingual scenarios. **TREC 2024 RAG Track** (arxiv:2504.15205) compares LLM judges (GPT-4o) against human annotators for support assessment, finding **56% perfect agreement** on 3-level scales (72% when post-editing), establishing LLM-as-judge viability for at-scale evaluation. **RAG-Zeval** (arxiv:2505.22430, May 2025) targets robust and interpretable end-to-end evaluation through rule-guided reasoning.

## LLM-as-Judge Trends and Concerns

**2 major research directions** dominate: (1) validation of LLM judges against human panels (TREC findings show correlation above independent humans), and (2) mitigation of documented biases—verbosity inflation, self-preference, position effects. The Awesome-LLM-as-a-Judge repository (GitHub: llm-as-a-judge/Awesome-LLM-as-a-judge) aggregates **50+ papers** on this topic. **Disagreement identified**: Traditional metrics remain dominant in published work (arxiv:2504.14891 notes "LLM-based methods have not yet gained widespread acceptance"), while trend analysis shows increasing LLM-judge usage in 2024 H2 and 2025 H1.

## Practitioner Frameworks and Tools

**LangChain** and **LlamaIndex** (both with active 2025 updates) dominate production RAG stacks, with evaluation integrated via RAGAS, LlamaIndex's native faithfulness/relevancy metrics, or custom LLM judges. **AWS Bedrock integration guide** (machine-learning blog) demonstrates production evaluation patterns. Multiple independent 2025 guides (Medium: Meeran Malik, Soni, Mishra) converge on: evaluate at retrieval stage (NDCG, recall), at generation stage (faithfulness vs. context), and end-to-end (answer correctness). **No disagreement on practitioner consensus**, though tool version tracking is fragmented.

## Coverage Gaps and Emerging Areas

**2 major surveys** (arxiv:2504.14891, arxiv:2506.00054) flag: (1) linguistic diversity—most frameworks target English/Chinese only; (2) domain specialization—medical RAG (arxiv:2511.06738 notes systematic evaluation gaps), legal RAG (LRAGE framework, arxiv:2504.01840), and graph-based RAG (arxiv:2503.04338) lack mature evaluation standards; (3) robustness evaluation remains nascent (poisoning attacks, adversarial retrieval). Emerging 2025 work (LiveRAG, arxiv:2511.14531; CiteGuard, arxiv:2510.17853) addresses citation attribution and adversarial resilience, indicating shifts toward production safety.
