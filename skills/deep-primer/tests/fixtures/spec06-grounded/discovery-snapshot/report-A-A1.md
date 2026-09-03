# structure — wave A (brief A-A1)

# RAG Evaluation Landscape: Structure & Method Families

## Canonical Taxonomy (5 Dimensions)

Retrieval-augmented generation evaluation organizes across five orthogonal dimensions: **scope** (component vs. end-to-end), **aspect** (retrieval, generation, factuality), **method** (automatic metrics, LLM judges, human annotation), **granularity** (token/claim/passage/answer level), and **ground truth** (unsupervised to fully annotated). The field consensus (6+ 2024-2025 sources) has shifted toward **hybrid multi-dimensional assessment**: component diagnostics for root-cause analysis plus end-to-end health checks for go/no-go decisions.

## Subfield 1: Retrieval Evaluation (IR-Standard Methods)

**Canonical metrics** (TREC 2024, CRAG, BEIR consensus): nDCG@K (position-weighted relevance, 0–1), Mean Reciprocal Rank (first relevant result position), MAP (mean average precision). **Context Precision** and **Context Recall** assess chunk ranking and coverage. nDCG@20 and nDCG@100 are production-standard thresholds. Three independent sources validate nDCG as retrieval gold standard.

## Subfield 2: Generation Evaluation (NLG Methods)

**Text overlap metrics** (ROUGE-1/2/L, BLEU, METEOR) measure n-gram coverage; sufficient for summarization but insufficient for semantic variation. **BERTScore** and contextual embeddings provide semantic similarity (active in 2024-2025 production systems). **LLM judges** using chain-of-thought prompting or rule-based criteria dominate recent evaluations, though **disagreement exists**: RAGBench 2024 finds 400M fine-tuned DeBERTa outperforms larger LLM judges on hallucination detection, while RAGAS reports 0.95 human agreement on faithfulness via careful prompt design.

## Subfield 3: RAG-Specific Metrics (Domain Innovations)

**Faithfulness/Groundedness** (5+ papers, unsolved problem) measures contradictions between generated text and retrieved context via NLI pipelines and claim-level decomposition. **Answer Relevance** evaluates query-response alignment. **Context Recall** fraction of available relevant context retrieved. **Utilization** (TRACe framework) tracks how well generation leverages retrieved context. **Key Point Recall** assesses information coverage from context.

## Subfield 4: Factuality & Hallucination (Critical Emerging Field)

**Citation accuracy** (support assessment, TREC 2024 standard) penalizes overcitation and rewards complete citation coverage. **Atomic claim detection** (AutoNuggetizer, TREC 2024) decomposes answers into verifiable facts. **Hallucination detection** combines NLI, token-level tracing (TRACe), and claim decomposition. No consensus solution yet; 7+ papers flag this as critical and unresolved.

## Practitioner Taxonomy: Production Workflow

**TREC 2024 RAG Track** (NIST-endorsed standard) formalizes production evaluation:
- **Tier 1**: End-to-end metrics (go/no-go gates; e.g., Faithfulness >0.85)
- **Tier 2**: Component diagnostics (Context Precision, nDCG@K, Answer Relevance)
- **Tier 3**: Generation fidelity (Faithfulness, Completeness)
- **Tier 4**: Citation/support accuracy (weighted precision/recall)

Evaluation axes: nugget assessment (atomic facts), support assessment (citation correctness), fluency, and retrieval ranking. Scale: 0–4 relevance (NIST standard); human-LLM agreement: 56% perfect match, 72% post-editing.

## Tools & Frameworks (Version Status, 2024-2025)

**RAGAS** (v0.3.4+, integrated LlamaIndex/LangChain): Minimizes ground truth; Faithfulness (0.95 human agreement), Context Precision/Recall, Answer Relevance. **DeepEval** (v2024+, Confident AI): 50+ metrics including Hallucination; reimplemented RAGAS suite early 2024. **ARES** (NAACL 2024): Lightweight LM judges via prediction-powered inference; 8-task validation. **TruLens** (acquired Snowflake May 2024): Real-time monitoring, OpenTelemetry, custom feedback functions. **Haystack** (v2.x): Transparent pipelines, audit trails for regulated industries. **TrecEval / pytrec_eval**: NIST official IR metrics tool.

**Specialized tools**: RAGChecker (claim decomposition), AutoNuggetizer (TREC 2024 nugget standard), RAGXplain (explainability), BERTScore (contextual embeddings).

## Benchmarks & Standardization

**Large-scale benchmark consensus**: CRAG (Meta, 4,409 QA, 5 domains, 8 question types), RAGBench (100k industry docs), CRUD-RAG (functional taxonomy: Create/Read/Update/Delete), BEIR (15+ heterogeneous IR datasets), MTEB v2.0 (1000+ languages, long-document embeddings), SQuAD (100k QA, standard EM/F1 metrics). **Emerging (2024-2025)**: mmRAG (multimodal), MEMERAG (multilingual meta-evaluation), FinDER (financial domain), FAB-Bench (semiconductor).

## Current Tensions & Consensus

**Unresolved**: LLM judge reliability (RAGAS 0.95 vs. RAGBench fine-tuned models superiority); metric-based vs. LLM-based trade-offs; ground truth necessity spectrum.

**Emerging consensus (6+ sources)**: (1) Component + end-to-end hybrid required; (2) multi-dimensional evaluation mandatory; (3) human validation of automated evaluators essential; (4) nDCG@K is retrieval standard; (5) factuality/hallucination remains unsolved; (6) production monitoring over one-time evaluation.
