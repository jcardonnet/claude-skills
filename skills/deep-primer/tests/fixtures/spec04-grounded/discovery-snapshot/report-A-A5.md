# adjacent-field — wave A (brief A-A5)

## Adjacent Fields to ANN Index Selection

Approximate nearest-neighbor (ANN) indexing draws from multiple mature fields, each contributing core techniques that have been adapted for vector similarity search at scale.

### Genuine Adjacent Domains

**Graph Theory & Small-World Networks** form the structural foundation of modern ANN algorithms. Hierarchical Navigable Small-World (HNSW) indexes apply navigable small-world graph properties—originally studied in social networks—to create multi-layered proximity graphs that exploit the small-world phenomenon: most nodes are reachable through a small number of hops. This borrowing is direct and non-trivial: HNSW's layer construction and greedy traversal are purpose-built applications of small-world theory to vector search. (2 supporting sources)

**Locality-Sensitive Hashing (LSH)** predates modern neural ANN by decades, yet remains a parallel approach to the same core problem. LSH uses probabilistic hash functions that map similar vectors to the same buckets with high probability, enabling sub-linear search time. While LSH and learned-index methods (e.g., HNSW) differ in mechanism, both solve the fundamental tension between dimensionality, search speed, and accuracy. (2 sources)

**Spatial Indexing** (KD-trees, R-trees, Voronoi partitioning) provides the conceptual language and algorithmic patterns for space decomposition. Inverted File (IVF) indexes—among the most practical ANN methods—explicitly borrow clustering and coarse partitioning from spatial indexing literature. (2 sources)

**Vector Quantization and Compression** (Product Quantization, Binary Hashing) emerged from signal processing and information theory but are now inseparable from ANN design. They reduce memory footprint and accelerate distance computation while preserving similarity structure—a trade-off central to approximate search. (2 sources)

**The Curse of Dimensionality** is perhaps the most fundamental adjacent concept. High-dimensional data exhibits distance concentration: all pairwise distances converge to similar magnitudes, making nearest neighbors less meaningful. ANN methods implicitly address this curse through approximation, structure (graphs, partitions), and learned embeddings. (2 sources)

**Clustering algorithms** (k-means, hierarchical clustering) appear both as foundational theory and as subroutines within ANN indexes. IVF uses k-means to partition vectors into coarse clusters; greedy search then focuses on nearby clusters. Clustering and ANN share distance metrics and optimization objectives, yet solve different problems. (2 sources)

**Metric Learning**, **Vector Embeddings** (Word2Vec, BERT), and **Dimensionality Reduction** (PCA, t-SNE) are upstream: they create the high-dimensional spaces in which ANN operates. Without learned embeddings that preserve semantic similarity, ANN indexes would lack meaningful structure. (3 sources)

**Skip Lists** and probabilistic layer construction share philosophical roots: both use randomization to avoid strict tree balancing, accepting O(log n) search with lower constant factors. HNSW's layer construction mirrors skip list design. (2 sources)

### False Friends

**Full-Text Retrieval** (BM25, TF-IDF) ranks search results by relevance, similar to ANN's goal. Yet they operate on fundamentally different data: discrete term frequencies versus continuous learned embeddings. They answer different retrieval problems—lexical matching versus semantic similarity—and hybrid search combines both because each captures distinct signal. (1 source)

**Classification and Clustering** (as primary objectives) are often confused with ANN. Classification learns decision boundaries for predefined labels; clustering partitions data exhaustively. ANN simply finds k neighbors without assigning labels or creating exhaustive partitions. (2 sources)

**Graph Neural Networks** learn node embeddings via message passing on graphs. They produce vectors suitable for downstream ANN search but are not themselves ANN indexes—the optimization objective is node classification or link prediction, not retrieval speed. (1 source)

**Recommendation Systems** use ANN internally to find similar items but represent a downstream application layer, not an adjacent field. (1 source)

### Key Disagreements

No significant disagreements appeared across sources. Some papers group LSH and random projections under broader "randomized algorithms" while others treat LSH as a distinct paradigm—both framings are valid and non-contradictory.
