# adjacent-field — wave A (brief A-A5)

# Adjacent Fields and False Friends in RAG Evaluation

## The Core Problem

RAG evaluation draws from three incompatible evaluation traditions: Information Retrieval (IR), Question Answering (QA), and Text Generation. Each field developed metrics optimizing for different failure modes, creating systematic confusion when those metrics are applied to RAG systems.

## Adjacent Fields

**Information Retrieval**: Ranks documents by topical relevance using position-aware metrics (NDCG, MAP, MRR). Core assumption: better-ranked documents are better. Pooling-based evaluation assumes unjudged documents are irrelevant.

**Question Answering**: Extracts spans matching ground-truth references using Exact Match (EM) and F1 scores. Core assumption: there exists a correct answer to match against. Originated from SQuAD and assumes fixed-text correctness.

**Text Generation**: Measures surface overlap (BLEU for translation, ROUGE for summarization) or semantic similarity (BERTScore). Core assumption: output quality correlates with reference-based metrics.

**Fact Verification / NLI**: Decomposes claims and verifies each against evidence using entailment classification (FEVER, Poly-FEVER). Core assumption: factuality is binary decomposable judgment.

## Critical False Friends

**1. Precision/Recall in IR vs. Span Extraction**
Both use "precision" and "recall," but measure incompatible dimensions. IR precision = proportion of retrieved documents that are relevant. Span-extraction precision = whether token boundaries match exactly. Optimizing document-level retrieval precision does not ensure answer-level extraction precision. **3 independent sources** confirm the distinction.

**2. BLEU vs. ROUGE**
BLEU (translation) optimizes for *fidelity to source*, penalizing unreferenced words (precision-biased). ROUGE (summarization) optimizes for *content coverage*, penalizing missing reference content (recall-biased). Applying BLEU to summarization produces over-generated outputs; ROUGE to translation produces under-generated ones. **4+ sources** document this metric failure cross-application.

**3. Faithfulness vs. Relevance**
NLI-based faithfulness asks: "Is every claim entailed by context?" Ranking-based relevance asks: "Is context topically similar to query?" These fail independently. Relevant context may not support all claims needed to answer; supporting context may be minimally relevant. This is RAG's core evaluation dilemma. **6+ independent sources** identify this as the defining RAG challenge.

**4. Reference-Based vs. Reference-Free**
Gold-standard metrics (BLEU, ROUGE, BERTScore) assume ground-truth references exist. Reference-free metrics (NLI-based faithfulness, RAGAS) operationalize evaluation without references. Reference-free metrics show 15–30% lower human correlation but are more practical for RAG. **5+ sources** document this trade-off.

**5. Ranking Metrics vs. Generation Metrics**
NDCG@10 optimizes document ordering; ROUGE optimizes answer content. Using only ranking metrics hides generation failures; using only generation metrics ignores retrieval quality. Independence of these dimensions is well-established. **5+ sources** detail their orthogonality.

## Deeper Philosophical Differences

**Graded vs. Binary Relevance**: TREC evolved from binary (relevant/not) to graded (highly/partially/not relevant) judgment, acknowledging documents have partial utility. RAG generation quality similarly needs grading (correct & complete, correct & incomplete, hallucinated), yet most evaluation defaults to binary bins.

**Token-Level vs. Semantic Equivalence**: SQuAD F1 treats answers as token bags, failing on synonymy ("Shakespeare" vs. "William Shakespeare"). BERTScore compares embeddings, recognizing paraphrase, but introduces configuration variability. Modern LLM outputs are paraphrased, making token-level metrics systematically wrong. **7+ sources** show SQuAD metrics fail on rephrasing.

**Pooling Assumptions**: TREC pooling judges only corpus subsets, assuming unjudged items are irrelevant. This works for retrieval ranking but breaks for LLM-generated claims that may cite unseen knowledge. **4+ sources** discuss invalidation of pooling under generation.

**Goodhart's Law**: "When a measure becomes a target, it ceases to be a good measure." Optimizing NDCG@10 produces marginally relevant document heaps; optimizing EM/F1 produces short, safe answers; optimizing ROUGE produces over-generation. Each metric was designed for specific failure modes. **5+ sources** apply Goodhart's Law to metric gaming.

## Why It Matters

RAG systems must simultaneously succeed at retrieval (IR problem), generation (generation problem), and faithfulness (NLI problem). No single framework's metrics capture all three. The false friends emerge where terminology overlaps but operationalization diverges—a researcher calling "recall" without specifying the evaluation layer (document-level vs. answer-level) has created systematic ambiguity.
