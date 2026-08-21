# debates — wave A (brief A-A2)

# ANN Index Selection: Live Controversies and Open Problems

## Failure Mode 1: Recall Consistency & Measurement Issues

The field's primary metric—mean Recall@k across query sets—systematically hides performance variance. Two systems with identical average recall can deliver noticeably different answer quality: one consistent across queries, the other excelling on most while failing catastrophically on hard queries. **Sources: 3** (*ANN Search: Recall What Matters* [arxiv], *Benchmarking Filtered Approximate Nearest Neighbor Search* [ETH], *The Achilles Heel of Vector Search: Filters* [blog]). Systems rank inconsistently depending on whether recall is averaged or counted, making cross-benchmark generalization unreliable.

## Failure Mode 2: Scalability Collapse at 100M+ Vectors

HNSW—the benchmark winner for small datasets—catastrophically degrades past 100M vectors. Production systems with 120M vectors (1536 dims) saw index size explode from 30 GB to 890 GB, P50 latency spike to 4.7s, P99 to 23s, and recall plummet to 73%. **Sources: 3** (*The Vector Database Performance Lie: HNSW vs IVF When You Have 100M+ Embeddings* [Medium 2025], *HNSW Vector Search Recall Failures in Production* [blog], AWS GPU acceleration announcement [2025]). Index construction times for billion-scale datasets require days of compute. The algorithm's O(n) memory footprint and sequential construction process inherently limit horizontal scaling. No consensus exists on whether optimized HNSW variants (P-HNSW, GPU-accelerated), hierarchical approaches (DiskANN, SPANN), or algorithm replacement (IVF, LSH variants) should be the default for large corpora.

## Failure Mode 3: Filter Integration—Post-Filter Recall Loss

Filtered ANN search fundamentally breaks when engines rely on post-filtering: they waste work retrieving and ranking vectors outside the filter, then discard them, causing recall to plummet. Engines with in-algorithm filtering preserve recall and run faster, but parameter tuning alone cannot fix high-selectivity filter failure in HNSW. **Sources: 3** (*The Achilles Heel of Vector Search: Filters* [blog 2025], *Benchmarking Filtered Approximate Nearest Neighbor Search* [ETH paper], *PipeANN-Filter* [arxiv]). Recent solutions (ACORN, Milvus Cardinal) exist but lack production maturity or vendor consensus on which to standardize.

## Failure Mode 4: Incremental Update Overhead

Traditional ANN indexes were designed for static corpora. Adding incremental inserts and deletes forces expensive reindexing: HNSW must rebuild after significant churn, IVF must rebalance partitions, and maintaining index invariants under streaming updates remains an open, expensive problem. **Sources: 2** (*Quantization for Vector Search under Streaming Updates* [arxiv 2512], *LSM-VEC: A Large-Scale Disk-Based System for Dynamic Vector Search* [arxiv 2505]). No production system has solved this efficiently; research remains exploratory.

## Failure Mode 5: Distance Metric Sensitivity & Dimensionality Curse

Index performance is highly sensitive to distance metric choice (Euclidean vs. cosine vs. fractional Lk norms) and embedding dimensionality. High-dimensional spaces cause distance metric discrimination to collapse: all points become approximately equidistant. Rank-based similarity measures outperform primary distance measures in high dimensions, but algorithm selection is ad-hoc and data-dependent. **Sources: 3** (*What is the curse of dimensionality and how does it affect vector search* [Milvus], *Quantixar* [arxiv 2403], *Can Shared-Neighbor Distances Defeat the Curse of Dimensionality* [Springer]). Quantization strategies (product quantization in FAISS) partially mitigate but introduce additional hyperparameters and tradeoffs without clear selection rules.

## Failure Mode 6: Benchmark-to-Reality Gap (Index-Access Pattern Mismatch)

Algorithm rankings on ann-benchmarks.com do not transfer to real workloads: the single-threaded CPU winner may fail on your specific query distribution, hardware (GPU vs. CPU), corpus size, or update pattern. HNSW beats IVF on in-memory latency benchmarks but loses under billion-scale disk residency. LSH wins on theoretical guarantees but loses in practice. **Sources: 2** (*HNSW vs IVF-PQ vs LSH: Approximate Nearest Neighbor Algorithms Compared* [Abhik Sarkar], *HNSW vs LSH: how Elasticsearch hits 0.99 recall@10 at 15,000 QPS* [Elastic blog]). No principled method exists to predict which algorithm suits a given scenario without empirical testing.

## Conclusion

ANN index selection remains fundamentally unsolved at scale. Benchmarks optimize for orthogonal concerns (single-threaded latency, in-memory operation), metrics hide tail behavior, algorithms fail at scale, and workload-specific parameters (filters, updates, dimensionality) shift the optimal choice unpredictably. The field has divided into specialized solutions (HNSW for small warm caches, IVF for billion-scale, LSH for streaming) but lacks integrated theory or practical selection guidance.
