# source-authority — wave A (brief A-A4)

## Approximate Nearest-Neighbor Index Selection: Authoritative Sources & Key Findings

### Seminal Algorithmic Work

Three core algorithmic families dominate ANN index selection, established through foundational research:

**HNSW (Hierarchical Navigable Small World)** — Malkov & Yashunin's 2018 paper "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs" (IEEE TPAMI 42(4), 824–836) introduced hierarchical graph-based indexing with logarithmic search complexity. HNSW trades memory overhead for strong recall and has become the default choice for moderate-scale deployments (supporting ~4 independent sources: arxiv, GitHub implementations, benchmark tools, Faiss integration).

**IVF + Product Quantization (PQ)** — Jégou, Douze, and Schmid's 2011 paper "Product Quantization for Nearest Neighbor Search" (IEEE TPAMI 33(1), 117–128) established the most memory-efficient approach for billion-scale datasets. IVF partitions space via k-means; PQ decomposes vectors into quantized subspaces. This two-tier structure enables sub-millisecond search on massive corpora but at the cost of recall accuracy (3 independent supporting sources: academic papers, Faiss integration, practitioner guides).

**Locality-Sensitive Hashing (LSH)** — Andoni & Indyk's research (FOCS 2006, Communications of the ACM 2008) formalized LSH for high-dimensional spaces. LSH provides theoretical guarantees but has largely been superseded in practice by HNSW and IVF for dense embeddings, though remains valuable for sparse or streaming scenarios (2 independent sources: theoretical papers, algorithmic surveys).

### Recent Advances (2024–2025)

**ScaNN (Google, 2020)** — "Accelerating Large-Scale Inference with Anisotropic Vector Quantization" (ICML 2020) combines anisotropic quantization with search space pruning, reporting 3× speedup over HNSW on GloVe. ScaNN is available open-source on Google Research GitHub and integrated into Faiss, making it a practical production option (2 supporting sources: Google Research, Faiss documentation).

**Learned Index Structures** — Recent work (2022–2025, Springer/arXiv) applies neural networks to learn index shape and search strategies. The HKC+-index achieves up to 7× speedup over tree indexes while maintaining recall. However, adoption remains limited; these remain research contributions rather than production standard (1–2 supporting sources: academic papers only, no widespread deployment).

**VIBE Benchmark (2025)** — The first comprehensive benchmark using modern embedding datasets (Jääsaari et al., arXiv:2505.17810). VIBE evaluates 21 implementations on 12 in-distribution and 6 out-of-distribution datasets, showing that index selection is sensitive to embedding distribution and workload characteristics. This is the most current empirical foundation for selection decisions (1 primary source: VIBE paper + website).

### Practical Selection Framework

Contemporary practitioner guidance (Oracle, Databricks, Microsoft SQL Server 2025 docs, BigQuery guides) converges on a size-based heuristic with recall-latency tradeoffs:

- **Small corpora (<10M vectors)**: HNSW or exact search (FLAT) when recall requirements are high and memory is available.
- **Medium scale (10–100M)**: IVF with PQ, balancing memory efficiency and acceptable recall (~95% top-10) via tuning the probe parameter.
- **Large scale (>100M)**: Hybrid approaches combining IVF with scalar or product quantization, or HNSW with compressed storage.
- **Specialized**: ScaNN for inner-product search; LSH for streaming or approximate filtering.

Key disagreement exists on memory overhead: HNSW advocates accept 10–20× index size overhead for latency gains, while IVF+PQ users prioritize sub-GB footprints for billion-vector deployments. Consensus: there is no universal winner; selection depends on corpus size, available memory, latency SLA, and acceptable recall threshold.

### Tool Ecosystem & Versions

**Faiss** (Facebook/Meta, v1.12.0, released Aug 12, 2025) — Most widely used ANN library, supporting HNSW, IVF, ScaNN, and quantization variants with Python/C++ APIs. Integrated into production systems at hyperscale (3+ supporting sources: engineering blog, GitHub, documentation).

**Annoy** (Spotify, latest via GitHub releases) — Memory-efficient forest-of-trees implementation, superseded by Voyager (2023) for HNSW but still used in legacy systems.

**Milvus** (open-source, 2025 releases) — Supports HNSW, IVF, ScaNN, and GPU acceleration; enables index selection via configuration.

**Weaviate, Pinecone, Qdrant** — Commercial/managed services with opinionated defaults (Weaviate uses HNSW+inverted indexes for hybrid search; Pinecone abstracts index tuning) (2 supporting sources: comparison guides, vendor documentation).

### Supporting Infrastructure

Benchmarking consensus anchored by three independent projects:
- **ANN-Benchmarks** (GitHub, erikbern/ann-benchmarks) — Long-running evaluation of 30+ libraries on SIFT, GIST, GloVe since 2017.
- **VIBE** (2025) — Updated with modern embeddings and out-of-distribution testing.
- Vendor-specific benchmarks (Milvus, Weaviate, Faiss performance blogs).

No significant disagreement exists on benchmarking results; variation reflects tuning choices and hardware. The core tradeoff—recall vs. latency vs. memory—remains unavoidable.

### Consensus & Open Questions

All authoritative sources agree: index selection is fundamentally a tradeoff tuning problem requiring empirical validation on representative data. No single index dominates across all scenarios. Learned index structures show promise but lack production validation. Quantization techniques (PQ, OPQ, SQ) remain essential for scale beyond 100M vectors but are underexplored for modern dense embeddings (VIBE addresses this gap).
