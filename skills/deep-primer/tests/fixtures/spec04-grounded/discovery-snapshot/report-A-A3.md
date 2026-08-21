# recency-frontier — wave A (brief A-A3)

# ANN Index Selection: 6-12 Month Frontier Report

## State-of-the-Art Shifts (2025-2026)

Graph-based indices remain dominant, but the landscape is consolidating around three production archetypes:

**In-memory (< ~100M vectors):** HNSW delivers sub-millisecond latency, achieving ~0.42ms p95 query time on 10M 768-dim vectors (May 2025 benchmark) versus IVFFlat's 0.83ms, though requiring 3× the RAM. HNSW implementations now feature persistent-memory variants (P-HNSW) and GPU acceleration (NVIDIA GTC 2025).

**Disk-resident (100M–1B+ vectors):** DiskANN has solidified as the reference design, adopted by Milvus, Azure Database, Timescale, and GaussDB. December 2025 marked a turning point: pgvectorscale added **StreamingDiskANN** as a third option alongside existing IVFFlat/HNSW, making disk-based indexing accessible to PostgreSQL users.

**Quantization + Graph fusion:** SymphonyQG (SIGMOD 2025) represents the emerging consensus: integrating product quantization with graph construction for recall-efficient indexing. Complementary 2025 work (CS-PQ) achieves cache-friendly SIMD product quantization for large-scale index building.

## New Releases & Version Pins

- **pgvector:** 0.8.0 released; pgvectorscale 0.9.0 (March 2026 tested with PostgreSQL 18)
- **DiskANN:** Rust rewrite (since 2023); active development through April 2026; v0.6.x introduces breaking changes in index metadata
- **HNSW:** No single "canonical" version—reference implementation (hnswlib C++), Facebook FAISS variant, Milvus optimized build, Redis 8 (66K insertions/sec at 95% precision)

## Deprecated Patterns

Flat/exhaustive search and simple IVF (inverted file) approaches are increasingly marginal except for exploratory <1M vector workloads. IVFFlat persists in production as a cost-conscious fallback with faster build times (2.3× faster than HNSW) and lower RAM footprint, but is rarely the default choice for new systems targeting >10M vectors.

## 2025–2026 Research Consensus

SIGMOD 2025 and concurrent venues (VLDB, ICDE, KDD) converge on graph-based efficiency breakthroughs:
- **DGAI** (decoupled on-disk graph indexing) and **NAVIS** (concurrent search/update on SSD) address operational challenges
- **LEANN** and **HRNN** extend graphs to low-storage and reverse-KNN scenarios
- **BatANN** pushes distributed disk-based search throughput; **HAKARI-Bench** provides unified benchmarking methodology

Benchmarks show pgvectorscale at 471 QPS (99% recall, 50M vectors), Redis sustaining 66K insertions/sec, and Milvus maintaining sub-50ms latency at 100M+ scale—no single library dominates all dimensions.

## Supporting Evidence Counts

**Graph-based superiority (3 sources):** ACM SIGMOD 2025 accepted papers, arxiv 2025 quantization fusion papers, PostgreSQL extension adoption
**HNSW latency (2 sources):** Benchmark blog (May 2025), Couchbase DiskANN comparison
**DiskANN disk-efficiency (2 sources):** Microsoft Research publication, Azure/Timescale adoption claims
**pgvectorscale December 2025 launch (1 source):** DBI Services blog; no conflict detected

No major disagreements surfaced; SOTA consensus favors graph indices with quantization integration for new systems post-June 2025.
