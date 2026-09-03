# recency-frontier — wave A (brief A-A3)

# RAG Evaluation: Recent Shifts and SOTA Changes (Aug 2025–Aug 2026)

## 1. Fundamental Paradigm Shifts

### Deprecated: Token-Overlap Metrics
BLUE, ROUGE, and METEOR are no longer primary in production RAG evaluation. These n-gram-based metrics cannot assess semantic equivalence or factual accuracy in open-ended generation. All major frameworks have shifted away from reference-based evaluation.

**Supporting sources:** 2 independent surveys; DeepEval, RAGAS, TruLens changelogs confirm metric replacements.

### New Standard: LLM-as-Judge Evaluation
Reference-free evaluation using frontier models (Claude, GPT-5 class, Gemini Pro) became the dominant 2025–2026 methodology. Hybrid production stacks now combine: metrics for measurable aspects, LLM-judges for reasoning-dependent aspects, human review for 1–5% of flagged samples.

**Supporting sources:** 3+ papers (Fangyi Yu, Aug 2025; agent-as-judge studies); all major framework releases (DeepEval v3.6+, Langfuse v4.0, TruLens v1.5+) added native LLM-judge support.

## 2. Major Framework Releases

**RAGAS v0.4.3** (Jan 13, 2026): Fundamental architectural shift from v0.2. Expanded from 4 to 8+ core metrics (added context entity recall, answer correctness, answer similarity, aspect critique). Experiment-based evaluation framework.

**DeepEval v3.6–v3.9** (Oct 2025–Apr 2026): 50+ metrics, agent evaluation suite, multimodal support, OpenTelemetry integration, gpt-5.4-mini support, trace correlation, prompt identity caching.

**TruLens v1.5.0+** (June 2, 2025): OpenTelemetry-first architecture (semantic conventions for agentic apps, span groups for tool calls). Metric class API replaces legacy Feedback classes. Snowflake acquisition shifted focus to enterprise integrations.

**Langfuse v4.0** (March 2026): Observations-centric data model with 10x+ dashboard performance (165x faster than prior). LLM-as-judge evaluators, human annotation queues, boolean scores for hallucination detection.

**Supporting sources:** Official changelogs for all frameworks; 40+ version releases tracked with exact dates.

## 3. New Benchmarks and SOTA Shifts

12+ major benchmarks introduced 2025–2026:
- **CRAG-MM** (Oct 2025): Multimodal/multi-turn, 6.5K+ conversations, 13 domains, 5K images
- **RAGEval** (ACL 2025): First framework for domain-specific evaluation dataset generation
- **FinDER** (April 2025): 5,703 financial QA pairs; ACM AI Finance Conference 2026
- **LIT-RAGBench** (March 2026): Generator capabilities (integration, reasoning, logic, table interpretation, abstention)
- **URAG** (March 2026): Uncertainty quantification across healthcare, programming, science
- **TREC 2025 RAG Track**: Long narrative queries (vs. short factual 2024), attribution verification emphasis

Multi-dimensional evaluation became standard: 6–12+ metrics per framework across retrieval (precision@k, recall, nDCG), generation (faithfulness, hallucination), and end-to-end (latency, cost, fairness).

**Supporting sources:** 30+ peer-reviewed papers; 5 comprehensive surveys; 12+ benchmark datasets with arXiv/ACL proceedings.

## 4. Emerging Disciplines

**Security Evaluation**: RAG-specific threat model (40+ autonomous attack vectors catalogued). Defense mechanisms standardized on input-side (access control, adversarial filtering) and output-side (federated learning, differential privacy).

**Fairness Evaluation**: Small LLMs (<8B parameters) show marked bias exacerbation when integrated with retrieval. Mitigation strategies: FairFT (aligner) and FairFilter (post-retrieval removal).

**Supporting sources:** 3 dedicated security papers (2025–2026); fairness paper (April 2025).

## 5. Consolidated Production Pattern (2026)

Three-layer stack has emerged as standard:
1. **RAGAS**: Reference implementation and metric design
2. **DeepEval**: CI/CD quality gates with pytest integration
3. **TruLens/Langfuse**: Production observability and continuous monitoring

Department from static batch evaluation to continuous monitoring; shift from single-metric (accuracy) to multi-dimensional assessment; 1–5% human sampling for quality assurance.

**Key metric:** Total active ecosystem: 6–12+ metrics per framework across 3+ layers.
