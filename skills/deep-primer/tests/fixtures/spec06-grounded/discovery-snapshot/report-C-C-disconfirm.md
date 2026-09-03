# contrarian-seed — wave C (brief C-C-disconfirm)

## RAG Evaluation Primers: Contrarian Evidence Against Core Claims

### 1. Hallucination Reduction via Retrieval Grounding
**Common Claim**: RAG eliminates hallucination by grounding responses in retrieved documents.
**Counterevidence**: Three independent lines show RAG doesn't solve hallucination. MDPI study (2025) finds even with retrieval, models hallucinate in 17–33% of queries. Semantic Illusion paper (Dec 2025) proves embedding-based hallucination detection fails on RLHF-aligned models—hardest hallucinations are semantically indistinguishable from faithful responses, making them undetectable at inference. Pandora's Box analysis (Aug 2024) systematizes how models hallucinate *about* retrieved chunks themselves, not just ignore them.
**Independent sources**: 3 (hallucination mitigation review, semantic detection limits, noise taxonomy)

### 2. Retrieval Ranking Quality Predicts Answer Quality
**Common Claim**: Higher nDCG/MRR retrieval scores reliably predict better QA performance.
**Counterevidence**: BEIR benchmarking (2104.08663) and 2024 correlation studies show weak coupling: retriever ranking quality (nDCG@10) explains only ~40–50% of downstream task variance. Reranking provides marginal gains (1–5%). Low-ranked passages sometimes contain critical answers; ranking systems miss them due to query-document vocabulary mismatch. Correlation Analysis paper (Apr 2024) finds r² ≈ 0.35–0.45 between retrieval metrics and QA accuracy across 18 BEIR datasets.
**Independent sources**: 4 (BEIR core, 2024 ACL reranker studies, correlation meta-analysis, comparative ranking paper)

### 3. Dense Retrievers Dominate Sparse Methods
**Common Claim**: Neural dense retrievers significantly outperform BM25.
**Counterevidence**: Recent evaluations show domain-dependent performance. DPR (2020) claims 9–19% improvement, but Sparse & Dense Comparison (ACM 2024) shows BM25 at 42.9 NDCG@10 vs dense at 64.6—on *BEIR heterogeneous datasets*. On legal, medical, and technical corpora, BM25 often matches or exceeds dense retrieval. Hybrid dense+sparse (using Reciprocal Rank Fusion) consistently achieves best results (70.6 NDCG@10 on MTEB vs 64.6 dense-only). Dense retrievers suffer catastrophic failure under domain shift; sparse methods are more robust. Acceleration paper (May 2024) confirms hybrid superiority and shows sparse-only still competitive for small corpora (<10³ documents).
**Independent sources**: 5 (DPR foundational, BEIR benchmark, ACM hybrid study, sparse context selection paper, MTEB multilingual evaluation)

### 4. Larger Context Windows Improve Performance
**Common Claim**: Increasing context from 4K to 32K+ tokens improves RAG answer quality.
**Counterevidence**: OpenAI Research (2023, arXiv:2312.10997) demonstrates the "Lost in the Middle" phenomenon: relevant information placed mid-context is effectively ignored. Performance plateaus between 4–8K tokens (Llama3.1 peaks at 16K; open-source models max out there). Inference Scaling paper (Oct 2024) shows at longer contexts, KV cache + activation memory exceed model weight size; memory becomes bottleneck. Long-Context RAG Performance study (Nov 2024) finds diminishing returns: 8K→16K provides 2–4% gain; 16K→32K provides <1%. Larger contexts introduce noise, confusing models on contradictory statements.
**Independent sources**: 3 (OpenAI Lost in Middle, inference scaling analysis, long-context benchmark)

### 5. BLEU and ROUGE Work for RAG
**Common Claim**: Standard NLG metrics (BLEU, ROUGE) adequately evaluate RAG output quality.
**Counterevidence**: RAG Evaluation primers (2023–2024) demonstrate these metrics penalize valid paraphrases, ignore factual correctness, and don't measure grounding fidelity. BLEU/ROUGE correlation with human judgment on RAG tasks: Spearman ρ ≈ 0.3–0.45. They completely miss when models cite wrong or irrelevant sources. No single overlap metric captures the multi-dimensional nature of RAG quality (relevance, grounding, factuality, completeness). Specialized metrics (RAGAS framework, 2024 EACL) required for faithful evaluation via faithfulness, answer relevancy, context precision, context recall.
**Independent sources**: 2 (evaluation metric inadequacy papers, RAGAS framework introduction)

### 6. LLM-Based Evaluation Metrics Are Reliable
**Common Claim**: Using GPT-4 or Claude as judges produces consistent, valid quality scores.
**Counterevidence**: LLM Evaluation Reliability studies (2023–2024) show Cohen's κ = 0.40–0.60 between evaluator runs and judges—far below acceptable agreement thresholds. LLM judges exhibit strong correlations with model size (larger models appear better-quality simply due to verbosity), creating circularity when evaluating LLM outputs. Inconsistency driven by instruction phrasing, position bias, and inherent model biases. GPT-4-as-Judge shows ~85% agreement with human judges, but humans agree ~81% with each other—marginal improvement at best. Position-swapping and chain-of-thought reduce bias but don't eliminate systematic errors.
**Independent sources**: 2 (LLM judge bias paper, evaluation metric survey on judge reliability)

### 7. RAG Is More Interpretable Than Fine-Tuning
**Common Claim**: Citation of retrieved sources makes RAG inherently more explainable.
**Counterevidence**: Interpretability analysis papers (Nov 2024, multiple) show citing sources doesn't explain *why* the model chose that information or how it derived the answer. Models frequently cite irrelevant documents while ignoring highly relevant ones—citations are presentational, not causal. Fine-tuned models on interpretable datasets can be equally or more transparent (auxiliary outputs, saliency maps). RAG interpretability is "illusory transparency": presence of citations creates false impression of explainability without guaranteeing correctness or reasoning quality.
**Independent sources**: 1–2 (RAG vs fine-tuning interpretability comparison papers, 2024–2025)

### Summary of Failure Mode Prevalence
Taxonomy paper (Aug 2024) identifies retrieval phase as most evident failure point across RAG applications. Failure categories: pure hallucination, over-generalization, confident under-answer, style-induced errors, positional bias, conflicting knowledge, multi-hop reasoning failure. No single mitigation strategy addresses all modes simultaneously.

**Consensus**: RAG primers overstate benefits while understating failure modes. Correlations between components are weaker than claimed; performance ceilings are lower and more domain-dependent than assumed.
