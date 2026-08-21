# practitioner — wave C (brief C-C-omission)

# ANN Index Selection Primers: Critical Gaps for Practitioners

Existing ANN index selection primers—whether academic guides or vendor documentation—typically cover core algorithms (HNSW, IVF, LSH) and high-level trade-offs (recall vs. query latency vs. memory). What remains largely absent are production realities that drive index choice in practice.

## 1. Streaming & Incremental Updates (2–3 independent sources)

Primers treat indexing as a batch operation. Production systems face constant data ingestion. Index selection must account for update cost, not just search performance. HNSW resists updates; IVF requires cluster rebalancing; LSH supports streaming inserts efficiently. Recent systems like FreshDiskANN (graph-based, supports incremental update with 2.47×–6.45× higher throughput than prior work) and SPFresh (cluster-based, LIRE protocol for in-place update) show that update strategy can dominate index choice, yet most primers mention updates as an afterthought.

## 2. Hardware-Specific Optimization (2–3 independent sources)

Index choice differs by hardware. GPU-native CAGRA is state-of-the-art for GPU acceleration; TPU-optimized systems exploit systolic arrays to reduce data movement; CPU+GPU heterogeneous systems require different index strategies entirely (e.g., Ascend-RaBitQ for NPU-CPU acceleration on 1-bit quantization). Primers cover Faiss on CPU and mention GPU acceleration, but lack guidance on when to switch algorithms or quantization strategies based on hardware type.

## 3. Hybrid Dense + Sparse Retrieval (2–3 independent sources)

Modern RAG systems combine ANN (dense) with BM25 (sparse). Primers treat ANN in isolation. Hybrid search reaches 7.4% lift over pure vector search (WANDS benchmark, NDCG 0.7497). Fusion methods (Reciprocal Rank Fusion, score interpolation, learned weighting) are application-specific. No primer addresses when to use hybrid search, score calibration, or the latency-recall curve of combined retrieval.

## 4. Metadata Filtering Trade-offs (2–3 independent sources)

Real queries apply filters: date ranges, user IDs, entity types. Pre-filtering (filter-then-search) is fast if selective but requires per-predicate indexes; post-filtering (search-then-filter) is simple but wastes computation on discarded candidates. Recent work proposes learning-based query planning to dynamically select strategy per query. Primers lack this nuance.

## 5. Distributed Consistency Models (2–3 independent sources)

Multi-node deployments must choose between strong, bound, session, and eventual consistency. Milvus exposes these tunable levels; eventual consistency prioritizes availability but introduces staleness. Index choice interacts with consistency: eventual consistency affects recall guarantees and index freshness. Primers omit this entirely.

## 6. Cost Modeling & SLA Constraints (2–3 independent sources)

Production deploys fix latency SLAs (e.g., p99 ≤ 300 ms time-to-first-token). This determines offered load, GPU count, and total cost per query. Index choice affects cost: HNSW is RAM-heavy; IVF saves memory but increases query compute. Primers mention cost informally but lack models to relate index type to infrastructure spend and per-request latency budget.

## 7. Compression & Quantization Curves (2–3 independent sources)

4× compression with 1% accuracy loss is achievable; Product Quantization can compress 100×. But trade-off curves differ by algorithm and data. Q4_K_M (72% savings, barely perceptible loss) differs from INT4 in gradient degradation. Primers list quantization methods but not production curves or when to apply each method.

## 8. Embedding Drift & Monitoring (2–3 independent sources)

Embedding models change (fine-tuning, model updates). Drift in embedding space originates from input data changes or embedding model instability. Comparison against a reference window (training data or stable period) detects drift; model-based drift detection (tracking per-class distributions) is recommended. Primers don't address index freshness after embedding model updates or drift-driven reindexing decisions.

## 9. Application-Specific Patterns (1–2 independent sources)

E-commerce search (BM25 + dense), recommendation (user embedding → top-k), and graph retrieval have different selectivity profiles and update patterns. Primers treat ANN generically; production often needs hybrid or domain-tuned strategies.

## 10. Workload Asymmetry (1–2 independent sources)

Write-heavy (streaming ingest, frequent updates) vs. read-heavy (batch queries, rare changes) systems warrant different indexes. Primers acknowledge this but don't quantify when workload ratio triggers a switch.

## Tools & Versions (as of August 2026)

- **FAISS** v1.15.0 (Aug 3, 2026) — Multi-algorithm library, GPU support, widely used baseline.
- **Milvus** v2.6.16 (May 13, 2026) / v3.0.0-beta (May 9, 2026) — Multiple index backends, GPU acceleration via CAGRA.
- **Qdrant** v1.19.0 (Aug 4, 2026) — HNSW-focused, introduced TurboQuant (v1.18, May 12, 2026).
- **DiskANN** (Rust rewrite, ongoing) — Real-time updates, cost-effective for disk-based search, multiple distance functions and quantizers.

## Disagreement Note

Benchmark comparisons show algorithm performance is dataset-dependent; no single method dominates. Some sources recommend pgvector as safe starting point; others emphasize Qdrant's tuning sophistication. Guidance varies by corpus size, latency target, and memory budget.
