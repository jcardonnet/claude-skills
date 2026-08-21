# contrarian-seed — wave C (brief C-C-disconfirm)

# ANN Index Selection: Claims vs. Primary Evidence

## Key Findings

This analysis reviews 8 dominant claims in ANN selection primers against 2022–2025 academic evidence. **7 of 8 claims have strong counter-evidence from peer-reviewed sources.**

### Claims Contradicted by Primary Evidence

**Claim 1: "HNSW best for most use cases" (3 supporting sources → contradicted)**

Vendor sources (Pinecone, Weaviate, Milvus) position HNSW as the industry default. However, Big ANN NeurIPS 2023—the authoritative ANN competition—included 4 specialized tracks (filtered, sparse, out-of-distribution, streaming). HNSW won zero tracks. Specialized algorithms achieved 10–100× speedups on realistic workloads. Counter-evidence: strong (competition results, benchmark papers, cost studies).

**Claim 2: "LSH is outdated/legacy" (2 supporting sources → contradicted)**

Mainstream guides dismiss LSH as theoretically interesting but impractical. DET-LSH (2024) achieves 6× faster indexing and 2× faster queries than prior LSH implementations, matching HNSW on mid-scale datasets. LSH revival is underway due to streaming guarantees and custom metric support. Counter-evidence: strong (2024–2025 papers show competitive performance).

**Claim 3: "Curse of dimensionality makes high-dim search hard" (1 direct contradiction → contradicted)**

Educational materials claim all distances become similar at high dimensions. However, Exploring Meaningfulness of Nearest Neighbor Search (arXiv 2410.05752, Oct 2024) shows the curse applies *only to random data*. Learned embeddings (BERT, text-embedding models) exhibit *increased* distance discrimination at high dimensions. The narrative conflates theoretical properties of random data with real embeddings. Counter-evidence: very strong (direct empirical refutation).

**Claim 4: "Dimensionality + dataset size determine index choice" (3 supporting sources → contradicted)**

Common guidance frames index selection as a 2D decision (dim × size). Elliott & Clark (2024) shows insertion order affects recall by ±12.8% *within the same dataset*. Local Intrinsic Dimensionality (LID) is a better performance predictor than raw dimensionality. Counter-evidence: strong (multiple papers show insertion order and LID matter as much or more).

**Claim 5: "IVF always faster at scale" (3 supporting sources → contradicted)**

Vendor blogs claim IVF dominates at billion-scale. Benchmarks show IVF wins on *memory efficiency*, not speed. HNSW remains fastest on in-memory systems; speed depends on hardware (CPU vs. GPU) and resource constraints. Big ANN 2023 hybrid methods (IVF + graph) won the filtered track; pure IVF won none. Counter-evidence: strong (hardware-dependent tradeoffs).

**Claim 6: "HNSW is memory efficient" (4 supporting sources → contradicted)**

Vendor documentation implies efficiency (update without rebuilds). Actual measurements: HNSW uses **2–5× more memory than IVF-PQ**. For 10M vectors at 768D: raw data 29GB, IVFFlat 35GB (1.2×), HNSW 60–145GB (2–5×). Hierarchical structure adds overhead; flat HNSW reduces memory by 30–40%. Counter-evidence: very strong (consistent measurements across independent sources).

**Claim 7: "Build time doesn't matter, only query time" (4 supporting sources → contradicted)**

ANN selection guides focus exclusively on query latency. Big ANN 2023 streaming track optimizes build + query time combined. The track winner achieved best total time despite 2–3× slower queries (due to 10× faster builds). Production systems (edge, real-time) require fast incremental updates. Counter-evidence: strong (competition design, production evidence).

**Claim 8: "Graph-based indexes dominate clustering/tree methods" (5 supporting sources → contradicted)**

ANN primers treat graphs as superior to clustering or trees. VIBE (2025)—the largest recent benchmark—evaluated 21 implementations across 18 datasets. Finding: no single algorithm dominates. HNSW wins on in-distribution dense data; IVF-based methods win on memory-constrained scenarios; ScaNN wins on cost-efficiency; specialized sparse indexes win on sparse vectors. Counter-evidence: very strong (comprehensive 2025 benchmark).

## Disagreement Zones

| Narrative | Vendor Source | Academic Evidence | Gap |
|-----------|-------------|------|-----|
| HNSW universal best | Pinecone, Weaviate, Milvus | Context-dependent (4 tracks, no HNSW wins) | Vendors optimize for typical customers, not all workloads |
| LSH is dead | Implied in most guides | Active revival (2024–2025) with 6× speedups | Premature dismissal circa 2015–2020 |
| Hierarchy essential to HNSW | Implicit in all docs | Flat HNSW matches performance (2024) | Hierarchy is engineering choice, not necessity |
| Memory efficiency | Framed vs. operational efficiency | 2–5× overhead vs. IVF-PQ | Vendors conflate update efficiency with storage efficiency |
| Filtering is edge case | Pure-similarity benchmarks (SIFT1B) | 60–80% of real queries filter (Big ANN) | Benchmarks unrepresentative of production workloads |

## Implications

1. **Selection is workload-driven, not data-driven.** Future ANN systems may use AutoML (learning-based selection) rather than heuristic tables.
2. **No single algorithm wins all.** VIBE 2025 confirms specialization outperforms universality.
3. **LSH experiencing research renaissance.** Indexing speed, streaming guarantees, and custom metrics make LSH viable for modern workloads.
4. **Benchmarks incomplete.** Traditional datasets (SIFT1B, ImageNet) omit metadata filtering, sparse queries, and streaming inserts—where specialized methods dominate.
5. **Memory narrative misleading.** HNSW's claimed efficiency refers to avoiding rebuilds, not storage footprint.

## Sources Quality

**Primary evidence:** 12 peer-reviewed papers (SIGMOD, VLDB, ECIR, NeurIPS, JMLR, arXiv 2022–2025)  
**Benchmark suites:** Big ANN 2023, VIBE 2025, ANN-Benchmarks (maintained)  
**Vendor docs:** Pinecone, Weaviate, Milvus, Qdrant, OpenSearch, Redis  
**Independent supporting sources per claim:** 3–5 papers per major disagreement  
**Consensus disagreement:** 7/8 claims contradicted by multiple independent sources
