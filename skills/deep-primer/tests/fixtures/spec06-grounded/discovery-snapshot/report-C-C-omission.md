# practitioner — wave C (brief C-C-omission)

# RAG Evaluation Primers: Critical Missing Aspects

## Current State
Established RAG evaluation primers cover core retrieval metrics (context relevance, nDCG@K, recall), generation quality (faithfulness, answer relevancy), hallucination detection basics, and benchmarks like CRAG and KILT. This foundation is solid for academic research.

## Eight Critical Gaps (By-Application Perspective)

### 1. **Production Readiness Metrics** (5 sources)
Primers focus on accuracy but omit operational constraints: latency decomposition (time to first token, component-level latency), per-query cost modeling, resource consumption, and cost-latency-quality (CLQ) tradeoff analysis. Production teams must build this framework independently.

### 2. **Domain-Specific Evaluation Protocols** (4 sources)
No primers differentiate evaluation by application domain despite fundamental differences:
- **Legal**: Precedent identification accuracy, statutory interpretation, stare decisis (case hierarchy)—addressed by LRAGE framework but absent from generalist primers
- **Financial**: Risk assessment, regulatory compliance, historical accuracy across market cycles
- **Healthcare**: Evidence hierarchy (clinical trial > observational study > opinion), clinician review requirements, safety-critical hallucination thresholds
- **Customer Support**: User satisfaction correlation, helpfulness-accuracy tradeoffs, tone/professionalism
- **Manufacturing**: Specification retrieval accuracy, process parameter correctness, safety compliance

### 3. **User Experience & Fairness** (3 sources)
Metrics miss subjective quality: tone appropriateness, demographic bias assessment, long-tail entity accuracy, user satisfaction correlation, explainability quality. Fairness testing across demographic groups remains almost absent from primer guidance.

### 4. **Temporal Dynamics** (3 sources)
No protocols for knowledge drift assessment. CRAG addresses temporal dynamism (years to seconds), but most frameworks ignore knowledge base staleness, recency requirements by domain, and continuous re-evaluation patterns—critical for news, markets, research domains.

### 5. **Diagnostic Error Attribution** (3 sources)
Aggregated scores hide component failures. Primers lack fine-grained attribution: Is error from retrieval, reranking, comprehension, reasoning, or generation? RAGVue (2025) proposes this as a novel contribution, confirming widespread gap.

### 6. **Hallucination Detection Taxonomy** (6+ sources)
Recent advances (TPA, SURE-RAG, HART, 2024-2025) address claim-level verification, hallucination types, and source attribution quality—yet remain fragmented and absent from unified primers. Distinction between grounding-faithful-but-incorrect and unsupported-but-correct remains underspecified.

### 7. **Reranker & Intermediate Step Evaluation** (3 sources)
Retrieval quality is assessed end-to-end; intermediate steps (reranking, hybrid search, metadata filtering, K-truncation optimization) lack standardized evaluation. RAGRouter-Bench and cost-latency papers identify this as key control point for constrained optimization.

### 8. **Practitioner Workflow Guidance** (3 sources)
Tools exist (RAGAS, DeepEval, UpTrain, TruLens) with distinct tradeoffs, but primers omit: when to use human vs. LLM judges (TREC 2024 shows 56% LLM-human agreement), cost-benefit analysis by method, tool selection matrix by domain, CI/CD patterns, sample sizing. Teams operate without synthesis.

## Source Count & Disagreement

- **Claims with 5+ supporting sources**: Production metrics, domain-specific protocols
- **Claims with 3-4 sources**: Temporal dynamics, error attribution, hallucination, reranker evaluation, practitioner workflows
- **No claim with single source** (all gaps independently supported)
- **Minimal disagreement**: TREC 2024 vs. 2025 differ on temporal focus; academic primers rarely mention production metrics but industry surveys emphasize them

## Implications

Current primers successfully teach evaluation *mechanics* but fail to map those mechanics to *operational reality*. A team deploying customer support RAG needs different evaluation than a legal research system, yet primers conflate these. Production teams must independently build cost models, domain frameworks, fairness protocols, and diagnostic tools—reinventing wheels at scale.
