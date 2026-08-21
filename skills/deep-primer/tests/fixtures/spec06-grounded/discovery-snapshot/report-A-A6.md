# contrarian-seed — wave A (brief A-A6)

# Against the Dominant Paradigm: RAG Evaluation's Critical Blindspots

The field of retrieval-augmented generation has converged on a cluster of evaluation practices—synthetic benchmarks, LLM-as-judge metrics, and vector-based retrieval assessment—that skeptics argue systematically misrepresent system performance. The case against this orthodoxy rests on mounting evidence of systematic bias, mathematical limits, and disconnect between metrics and production reality.

## Synthetic Benchmarks Systematically Overestimate

Vendors widely adopt synthetic datasets for RAG evaluation by generating questions and answers from their own documents. These benchmarks are "easier to score but systematically overestimate real-world performance" compared to messy production queries. Research demonstrates data leakage: LLMs generating synthetic evaluation data inadvertently incorporate knowledge from their training corpora, creating artificial overlaps that inflate metrics. LegalBench-RAG (2024) found weak correlation between performance on different legal datasets—strong results on one document type don't transfer—yet vendors publish single-benchmark claims as universal. The evidence is stark: systems showing 84% Recall@64 achieve only 14% Precision@1 on identical tasks, and 70% of RAG systems still lack any systematic evaluation framework.

## LLM Judges Don't Align with Human Assessment

Automatic LLM-as-judge evaluation, popularized through frameworks like RAGAS, faces fundamental alignment problems. Empirical validation shows RAGAS metrics correlate with human judgment at a harmonic mean of only 0.55—far below reliability thresholds. The CALM framework documents 12 distinct biases in LLM judges: position bias, verbosity bias, self-enhancement bias, and authority bias. TREC 2024 RAG Track data reveals agreement fractions of 0.30–0.34 between automated and human assessments on relevance—suggesting limited agreement relative to human assessors. Prometheus demonstrated that even fine-tuned open-source LLMs require structured rubrics to approach GPT-4 correlation (>0.79 with rubrics), but most production systems lack such calibration. The core problem: misaligned judges optimize systems toward what the metric measures, not what users need.

## Vector Embeddings Hit a Hard Mathematical Ceiling

Single-vector retrieval faces a fundamental geometric constraint: for any embedding dimension, there exists a hard cap on the number and complexity of query-document relationships representable. Research connecting retrieval capacity to sign-rank from communication complexity proves this limit follows a third-degree polynomial curve—increasing dimension helps, but cannot overcome the combinatorial problem. The LIMIT benchmark exposed this by testing every possible pair combination from a document set. Results were severe: Gemini Embeddings achieved <20% recall@100 on complex tasks, while BM25—a 20+ year old lexical method—substantially outperformed modern embeddings. Fine-tuning provided negligible gains, proving the limitation stems from the single-vector architecture itself, not domain knowledge gaps. Vector search excels at conceptual recall but struggles with precision, forcing re-ranking post-retrieval, which adds latency and reintroduces the retrieval-generation coupling problem.

## Metrics Don't Capture Real-World Complexity

Vendors conflate measurement dimensions without clarification. "Precision@1 and Precision@64 are completely different numbers," yet are presented interchangeably in benchmarking claims. The absence of cost-latency reporting with accuracy metrics obscures efficiency trade-offs. Real user queries are "messier, more conversational, and often ambiguous" than clean benchmark questions. Systems optimized for synthetic judges risk overfitting to artifacts of the generator, not to actual retrieval needs. Without human feedback loops, automated metrics guide optimization toward metric maximization, not user value—a classic goodharts-law failure in production deployments.

## The Consensus Breaks Down Under Production Pressure

When skeptics stress-test dominant practices, cracks emerge: benchmarks don't predict deployment success, LLM judges diverge from human assessment, vector retrieval fails on adversarial inputs, and metrics decompose under domain shift. The field's consensus on how to evaluate RAG systems appears optimized for publication clarity and vendor marketing, not for predicting production outcomes. This explains why strong benchmark results often fail to translate to user satisfaction and why enterprises must validate with human review to prevent systems from learning synthetic artifacts.
