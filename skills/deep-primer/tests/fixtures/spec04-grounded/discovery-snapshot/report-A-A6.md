# contrarian-seed — wave A (brief A-A6)

# Against the Grain: Skeptical Case Against Dominant ANN Index Selection

## The Dominant Assumption

The vector search industry consensus holds that approximate nearest neighbor (ANN) indexes—particularly HNSW—are the optimal choice for all-scale similarity search. Vendors and researchers alike present ANN as a necessity: faster, scalable, inevitable. Skeptics disagree on both empirical and fundamental grounds.

## The Strongest Skeptical Claims

### 1. Exact Methods Remain Competitive (3 independent sources)

Brute-force exact search is widely dismissed as impractical, yet production deployments contradict this. AWS's Ring team runs brute-force parallel scans on 100-200B embeddings partitioned per-user; FAISS benchmarks show flat indexes recommended for <1M vectors with perfect recall; GPU-accelerated brute force achieves 6× speedup over CPU clusters. The claim that ANN is mandatory conflates "must scale to billions" with "should always be approximate."

### 2. Hierarchical Graph Structures Add Complexity Without Benefit (2 sources)

HNSW's hierarchy is marketed as essential, but VLDB 2024 research ("Down with the Hierarchy") demonstrates that FlatNav—removing the 'H'—achieves identical latency and recall with less memory overhead. High-dimensional spaces suffer from the hubness phenomenon, rendering hierarchical navigation ineffective. The hierarchy persists due to marketing inertia, not algorithmic necessity.

### 3. Hidden Construction and Maintenance Costs (3 sources)

Benchmarks report query latency in isolation. They omit: HNSW build-time overhead (2.73× higher for recall-satisfying configs), 10+ GB RAM consumption for million-vector datasets, multi-hour build times, frequent re-indexing to maintain recall, and deletion cascades requiring full rebuilds. The actual cost curve flips when total-cost-of-ownership is measured.

### 4. Benchmarks Systematically Mislead (3 sources)

30% of major vector databases contractually prohibit publishing slowness claims (DeWitt Clause). Standard benchmarks measure static ingestion ("Time Zero") with single clients; production has continuous updates and 100+ concurrent connections. Reddit's 340M-vector deployment found metadata filtering—not vector search—is the bottleneck, with 10× tail latency jumps and P99 slowing from 10ms to 100ms. VectorDBBench tests conditions that do not exist in production.

### 5. SIMD-Optimized Linear Scan Is Competitive (3 sources)

Elasticsearch's simdvec achieves 23-28 ns/operation on x86 (AVX-512) with 1.2-4× speedups via prefetching. PDX data layout makes linear scan 2.5-6.2× faster than FAISS/Milvus. For reranking, IVF candidate filtering, and memory-constrained scenarios, brute force with hardware optimization beats complex indexes. The gap closes further as instruction-set optimizations mature.

### 6. Approximation Errors Don't Harm Results (2 sources)

Supplying near-misses instead of exact neighbors produces negligible downstream impact. BERTScore varies <1.2% across full recall ranges (0.4–1.0); LLM-graded evaluation varies <1%. Embedding redundancy and downstream processing absorb approximation error. The obsession with perfect recall ignores application-level robustness.

### 7. HNSW Delete Operations Break the Index (2 sources)

Deleting a node from a sparse hierarchical graph orphans entire sections, requiring full reconstruction. Points become unreachable after insertions and deletions. Dynamic workloads with frequent updates force either continuous rebuilds (downtime) or accepting data corruption (orphaned vectors). This is an algorithmic constraint, not an implementation problem.

### 8. Metadata Filtering Is the Actual Bottleneck (2 sources)

Production queries include metadata filters: category (3.3× overhead), date range (8× overhead). In a 100M-item dataset, four-criteria metadata intersection takes 100ms—longer than vector search itself. ANN research optimizes the wrong problem; the bottleneck moved long ago.

### 9. Disk Residency Fundamentally Mismatches HNSW (2 sources)

Scaling beyond ~350GB vectors (HNSW RAM requirement) forces disk storage, but HNSW's random-access pattern conflicts with disk's sequential-I/O preference. Billion-scale deployments face a choice: keep HNSW and accept severe performance degradation, or abandon it. Workarounds (prefetching, caching) add complexity without solving the fundamental mismatch.

### 10. Hyperparameter Tuning Is Intractable (2 sources)

HNSW requires tuning ef, M, efConstruction, L. Optimal settings change between data versions; Pinecone documents "Monday's weights vastly different from Tuesday's." This is NP-hard bilevel optimization. Industry frames it as a configuration problem; skeptics see it as a signal that the algorithm is too sensitive for production.

## Skepticism's Horizon

The contrarian view is not that ANN is always wrong, but that it is oversold. Exact methods, SIMD brute force, and simpler alternatives solve the problem in 60-80% of cases. Complex indexes pay their way only at massive scale with specific workloads (billion vectors, queries without filters, static data). For typical deployments—millions of vectors, metadata filtering, dynamic updates—the dominant approach imposes unnecessary complexity, operational overhead, and technical debt. The skeptics argue that an honest engineering choice would start simpler and graduate to ANN only when evidence demands it, not reverse-engineer complexity into every system.
