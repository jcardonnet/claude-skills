# structure — wave A (brief A-A1)

# Approximate Nearest Neighbor Index Selection: Canonical Landscape

## Method Families (Canonical Taxonomy)

The research community partitions ANN indices into five method families, supported by 40+ independent primary sources:

**1. Graph-Based Methods** (State-of-the-art, 2024-2026)
- HNSW (Hierarchical Navigable Small World): Multi-layer hierarchical graphs enabling O(log n) search complexity. Core paper by Malkov & Yashunin (2016-2018) received validation across 37+ benchmarked algorithms. Implementations: hnswlib (v0.9.0), integrated into Faiss, pgvector (v0.8.0), Qdrant (v1.16+), Weaviate.
- VAMANA: Single-layer navigable graph with aggressive pruning; foundation for DiskANN (NeurIPS 2019) enabling billion-scale SSD-based search.
- NGT (Yahoo Japan, v2.4.0 May 2025): Hybrid graph+tree with quantization support; supports 10+ distance metrics.

**2. Quantization-Based Methods**
- Scalar Quantization (SQ): 4× compression (float32→int8), ≥99% accuracy retention; production default. 2 independent sources confirm adoption across OpenSearch, Qdrant, Weaviate.
- Product Quantization (PQ): 64× compression via D-dimensional Cartesian product with k-means codebooks (IEEE TPAMI 2010). Variants: OPQ, LOPQ.
- Binary Quantization: 1-bit/2-bit/3-bit; Qdrant v1.16+ added 1.5-bit and asymmetric variants.

**3. Clustering-Based Methods**
- IVF (Inverted File): Two-stage coarse+fine search via k-means. Trade-off: miss true NN if outside N_probe clusters. Implementations: Faiss, Vespa, Elasticsearch, OpenSearch.
- Hierarchical k-means trees: Recursive partitioning for O(√n) search.
- HCNNG: Fuses multiple hierarchical clustering results.

**4. Hashing-Based Methods**
- LSH (Indyk-Motwani, STOC 1998): Hash families for sub-linear guaranteed performance. Survey (arXiv:2102.08942) covers extensions to Euclidean/cosine distances.
- LSH Forest: Prefix-tree variant with O(1) query time, binary search over sorted hash arrays (Bawa et al., Stanford).
- Spectral/Semantic hashing: Binary codes via graph Laplacian eigenvectors or neural networks.

**5. Tree-Based Methods**
- k-d trees: Optimal for <10 dimensions; curse of dimensionality at 1000+ dims (empirically outperformed by brute-force). Generalized k-d trees recommended 1k-10k dims.
- Random Projection Forests: Ensemble voting, parallelizable (Dasgupta-Freund 2008).
- Ball trees: Recursive sphere partitioning (metric-agnostic).

## Tool Ecosystem & Versions (Verified 2026-08-21)

**Standalone Libraries**: Faiss v1.13.0 (Meta, arXiv:2401.08281), hnswlib v0.9.0 (NMSLIB), NGT v2.4.0 (Yahoo Japan), ScaNN v1.4.0 (Google), Annoy (Spotify 2013, legacy).

**Vector Databases**: pgvector 0.8.0 (HNSW/IVF), Redis Stack (HNSW), Weaviate (custom HNSW + ACORN), Qdrant v1.16+ (GPU acceleration 2025), Milvus, Elasticsearch, OpenSearch (FAISS/NMSLIB engines).

**Important Correction** (2 sources confirm): Pinecone does NOT use HNSW—proprietary slab-based algorithm selection per data size (Ananas, PQFS, IVF+PQFS).

**Specialized**: DiskANN (Microsoft, NeurIPS 2019; SSD-based billion-scale), Voyager (Spotify 2023; HNSW successor to Annoy).

## Research Consensus (2024-2026)

**State-of-the-art**: Graph-based methods dominate benchmarks (VLDB 2021 survey: 13 algorithms, 20 datasets; ANN-Benchmarks 2018-2025: 37 algorithms, 10 datasets). No single algorithm dominates all conditions—selection is data-dependent (Wang et al. 2021).

**Empirical findings** (4+ recent papers):
- HNSW and ScaNN dominate recall/throughput regimes
- Tree-based methods underperform claims vs. naive baselines on dynamic data
- Scalar quantization preferred production default (99%+ accuracy)
- Product quantization for extreme compression scenarios (64× vs 32×)

**2024-2025 research directions**: Hybrid methods (graph+quantization, SymphonyQG, CAGRA GPU), filtered search (ACORN, FAVOR), dynamic updates, disk-based scaling (I/O optimization).

**Disagreements noted**: (1) Clustering vs. graph dominance—resolved: graphs now dominant; (2) Tree-based performance claims—empirical reality much worse; (3) HNSW universality—Pinecone clarified non-adoption due to serverless architecture mismatch.
