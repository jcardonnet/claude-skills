# debates — wave A (brief A-A2)

# Live Controversies in RAG Evaluation: A Framing by Failure Mode

Retrieval-augmented generation evaluation is fracturing across multiple fault lines, with no emerging consensus on metrics, methodology, or failure attribution. The field is divided not by implementation differences, but by fundamental disagreements about what evaluation should measure.

## Metric Reliability Crisis

The industry's most widely adopted evaluation framework, RAGAS, exhibits critical precision failures: RAGAS-Fact achieved only 19% precision (92% recall), SelfCheck 15% precision (50% recall), and LLM-as-judge error classification reaches only 57.8% agreement with human experts on error stage, 40.3% on error type (arXiv:2510.13975). Correlation between any reference-based metric and human judgment peaks at r=0.477—explaining <23% of variance—creating a reliability ceiling far below practical thresholds (Deepchecks 2026, GRAMMAR arXiv:2404.19232). Yet RAGAS remains dominant across LangChain, LlamaIndex, and Haystack despite these known limitations.

## The Oracle Paradox

Systems receiving perfect context achieve 94–99% accuracy; real RAG with imperfect retrieval reaches only 64–74% on the largest models—a 20–30 percentage point gap that *widens* with model size (M4-RAG arXiv:2512.05959, T²-RAGBench arXiv:2506.12071). This violates intuition: larger models should recover signal from noisy input better than smaller ones. The gap is unexplained by current literature and suggests fundamental limits in how LLMs process imperfect context—a failure mode without proposed consensus solutions.

## Semantic Collapse in Metric Design

Frameworks conflate "faithfulness" (answers follow from context) and "groundedness" (sources justify answers), yet these are distinct phenomena requiring separate optimization (Openlayer 2026, arXiv:2506.00054). A retriever can score high on context precision while failing context recall. Different evaluation systems *reverse their rankings* across task domains—a system optimized for high precision in one domain may hallucinate off-topic in another with ambiguous queries (arXiv:2506.00054). Vendors cannot guarantee optimization of one metric improves real-world performance.

## Positional Bias Beyond Consensus

The "lost in the middle" effect—30% accuracy degradation when relevant chunks move from first/last to center positions—extends beyond middle placement (ECIR 2025 arXiv:2502.08662 "Lost but Not Only in the Middle"). Performance instability intensifies with larger context windows, yet standard TREC metrics assume position-independence (U-NIAH arXiv:2503.00353). No consensus metric exists for "effective reranking quality," leaving reordering mitigations unvalidated.

## Preprocessing Blindness

Semantic entanglement—when source documents conflate multiple topics in contiguous text—causes retrieval accuracy to collapse from 82% to 32% without preprocessing (arXiv:2604.17677 Semantic Entanglement in Vector-Based Retrieval). Standard evaluation frameworks (RAGAS, ARES, DeepEval, TruLens) do not measure or flag this failure mode because they assume input quality. A system with high faithfulness and context-precision scores can silently suffer 50-point retrieval loss.

## Theory-Practice Chasm on Token-Level Evaluation

A 2024 preprint (arXiv:2406.00944 "A Theory for Token-Level Harmonization") argues that token-level evaluation (measuring LLM benefit/detriment per generation step) is fundamentally superior to passage-level metrics yet shows no training or module dependencies. The claim directly critiques Self-RAG, CRAG, RetRobust, and standard passage-level approaches as theoretically misspecified. Yet production systems universally use passage-level metrics. This represents an unresolved research-to-practice gap with no vendor adoption of the proposed theory.

## Benchmark-Production Collapse

Industry surveys converge on 70–85% of agentic RAG systems failing in production (Atlan 2025, Medium: "10 RAG Failure Modes at Scale"), while academic benchmarks show no predictive power. Production failure modes—drift, stale indexes, context overflow truncation, silent failures—are not systematically tested by TREC or MS MARCO (A Systematic Taxonomy of Failure Modes arXiv:2026.trustnlp-main.27 / ACL 2026). Lab rankings do not transfer to operations.

## Human vs. LLM Judge Disagreement

TREC 2024 RAG Track results: 44% of GPT-4o assessments differ from human judgment on 3-level scale (56% agreement, 72% with post-editing). Laura Dietz's "Principles and Guidelines for the Use of LLM Judges" (2025) acknowledges systematic bias in LLM-based evaluation, yet some vendors reinterpret TREC data to claim LLM judges are "reliable alternatives." No consensus on when LLM judges suffice versus requiring human review.

## Ground Truth Construction Ambiguity

No consensus exists on synthetic vs. human reference answers. Synthetic question-answer pairs introduce systematic bias and reduce benchmark coverage, particularly in domain-specific RAG (legal, medical, financial). Yet most commercial platforms do not disclose whether benchmarks use human-curated or synthetic ground truth, making it impossible to compare across vendors (IBM Think 2026, Red Hat 2026, LRAGE arXiv:2504.01840).

## Methodological Divide

The field is split on retrieval evaluation philosophy: classical IR approach (evaluate precision/recall/MRR independently via relevance labels) versus task-aware approach (eRAG: assess documents by downstream RAG performance). Different evaluation paradigms produce incompatible rankings. A document TREC labels "marginal" may be high-value for a particular LLM; a "perfectly relevant" document may confuse due to position or semantic overlap with prompt. These two frameworks are not reconciled in literature.
