# adjacent-field — wave C (brief C-C-source-completeness)

# RAG Evaluation: A Comprehensive Primer

## Landscape Overview

Retrieval-Augmented Generation (RAG) evaluation spans three core dimensions: retrieval quality, generation quality, and integrated system performance. Unlike standalone IR or generation tasks, RAG assessment must measure both components and their interaction—a critical gap filled by recent frameworks.

## Retrieval Evaluation Foundations

Retrieval assessment inherits standard information retrieval metrics from the TREC evaluation tradition (established 1992): Precision@k, Recall@k, and rank-aware metrics including Mean Reciprocal Rank (MRR), Mean Average Precision (MAP), and Normalized Discounted Cumulative Gain (NDCG). These metrics form the baseline for evaluating retrieval subsystems in RAG pipelines.

Key insight: Traditional IR metrics do not account for generation task compatibility. A document ranked highly by IR metrics may not contain information useful for answer generation, motivating context-specific evaluation (2 independent sources).

## Generation and Faithfulness Assessment

Generation quality assessment combines reference-based metrics (ROUGE, BLEU, BERTScore) with reference-free approaches measuring factuality. ROUGE measures n-gram overlap (recall-focused); BLEU emphasizes precision; BERTScore leverages contextual embeddings for better correlation with human judgment (cited by 3+ independent evaluation surveys).

Faithfulness—whether generated text grounded in retrieved context—emerged as critical after discovering that LLMs generate plausible but unsupported claims. FEVER (145K claim-evidence pairs) and HaluEval (10K QA samples) established factuality benchmarking. Recent frameworks incorporate hallucination detection via claim decomposition and entailment checking (2 distinct approaches documented).

## Integrated RAG Frameworks

**RAGAS (2024)** pioneered reference-free RAG evaluation via four metrics: Faithfulness (LLM-based entailment), Answer Relevance (query-response consistency), Context Precision (retrieval ranking quality), and Context Recall (coverage of ground-truth information). Deployed in production systems; open-source implementation available.

**RAGChecker (2024)** decomposes RAG errors into retrieval and generation components using atomic claim extraction and fine-grained entailment evaluation. Meta-evaluation shows 45–85% higher correlation with human judgment than metrics like ROUGE or simple retrieval baselines (verified via NeurIPS benchmarking).

**Comprehensive Surveys (2024–2025)** by Yu et al., Gan et al., and others systematize 50+ evaluation approaches, categorizing metrics by component (retrieval vs. generation), methodology (reference-based vs. reference-free), and dimension (correctness, factuality, efficiency, safety).

## Benchmarks and Datasets

QA task evaluation relies on standardized benchmarks: SQuAD (exact match and F1-score at character level), MRQA (multi-domain generalization via out-of-domain test sets), and specialized medical/legal benchmarks (RAGCare-QA, LongEval-RAG). These datasets enforce reproducibility and enable cross-system comparison.

## Key Gaps in Literature

Three underexplored areas:

1. **Multi-hop reasoning**: Most frameworks evaluate single-step retrieval-generation chains; few address complex reasoning over multiple retrieved documents (1 preliminary study; no consensus framework).

2. **Trade-offs**: Tension between retrieval recall (costly, comprehensive) and generation latency remains largely qualitative; quantitative frameworks for cost-benefit analysis emerging but incomplete.

3. **Robustness**: Limited evaluation of RAG behavior under adversarial inputs, out-of-distribution queries, or malformed retrieval results—a gap highlighted in 2024–2025 surveys as urgent.

## Authoritative Sources Checklist

A complete RAG evaluation primer **must** include:

- Lewis et al. (2020) foundational RAG paper
- TREC evaluation methodology and metrics standards
- Factuality benchmarks (FEVER, FEQA, HaluEval)
- QA evaluation standards (SQuAD, MRQA)
- Reference-based metrics (ROUGE, BLEU, BERTScore)
- RAGAS and RAGChecker frameworks
- Recent comprehensive surveys (2024–2025)
- Domain-specific benchmarks (medical, legal, finance)

Sources NOT commonly cited but essential: TREC evaluation theory; original n-gram overlap metric papers (BLEU, ROUGE); claim-level factuality assessment methods; cost-efficiency frameworks.
