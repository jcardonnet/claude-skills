# Exemplars — contrast pairs

Teaching contrasts for the generator, keyed to `rule_id`. For each rule: the **LLM default** it
counters, a **bad** example with what's wrong, and the repaired **good** version.

**How to use these.** Match the *form*, not the domain. The examples span retrieval, distributed
systems, and general engineering on purpose — the rules are domain-independent; the examples are
illustrative. These are contrasts to learn from, never text to copy. Coverage is deliberately
partial: the mechanical hard-lint rules (block-ids, footnote balance, coverage counts) need no
exemplar because a script enforces them. When a rule's directive changes in the registry, revisit
its exemplar here.

---

## Architecture & openings

### R-ARCH-03 — Answer-first opening (BLUF)
*Open with the thesis/answer, cuttable from the bottom.* **LLM default:** buries the lede behind a generic introduction.
- **Bad:** *"Vector databases have become increasingly important in modern AI. This primer explores their architecture, use cases, and trade-offs, beginning with embeddings."* — A table of contents in prose; states no bottom line; nothing is cuttable because nothing is claimed.
- **Good:** *"For retrieval at scale the index choice is the whole game: HNSW when memory is cheap and the corpus is static, IVF when you'll trade recall for 10× less RAM, brute force only below ~100k vectors. The rest of this primer is why."* — Bottom line first; the body becomes justification you can stop reading at any point.

### R-ARCH-01 — Scope-and-decisions block
*State audience, in/out of scope, and the editorial decisions that shaped the primer.* **LLM default:** dives into content with no scope contract.
- **Bad:** Primer opens directly with *"## What is retrieval-augmented generation?"* — The reader doesn't know who it's for, what it covers, or what was deliberately left out.
- **Good:** *"For backend engineers adding retrieval to an existing product; assumes databases and HTTP services, not ML. In scope: retrieval architecture and the build/buy call. Out of scope: training embedders, and eval methodology (a separate primer). Bias: I weight operational simplicity over marginal recall."* — Audience, scope boundaries, and stance up front.

## Headings

### R-SCENT-01 — Predictive, claim-bearing headings
*Every heading is a complete predictive claim/question.* **LLM default:** generic topic labels (Overview, Background, Conclusion).
- **Bad:** `## Background` · `## Key Concepts` · `## Conclusion` — A reader scanning the headings learns nothing about the argument.
- **Good:** `## Why long context didn't kill chunking` · `## The recall–latency knob every index exposes` · `## When a reranker is dead weight` — The heading skeleton alone conveys the thesis.

### R-SCENT-02 — Parallel sibling headings
*Sibling headings share grammatical form.* **LLM default:** mixes forms (gerund / noun / how-to).
- **Bad:** `## Choosing an index` · `## Rerankers` · `## How to evaluate` — Three grammatical shapes; jarring to scan.
- **Good:** `## Choosing an index` · `## Adding a reranker` · `## Evaluating the pipeline` — Parallel gerund form.

## The card

### R-CARD-01 — Card as advance organizer
*Open each section with the home-domain analogue + anchor concepts, then what's new vs renamed.* **LLM default:** writes the card as a teaser that summarizes the section in its own terms.
- **Bad:** *"Reranking re-scores an initial candidate set to improve the final ordering of results."* — A mini-summary in the section's own vocabulary; activates no prior knowledge.
- **Good:** *"If you've seen a SQL query planner's 'cheap filter, then expensive sort', reranking is that shape: a cheap recall stage hands candidates to an expensive precision stage. New here: the expensive stage is a cross-encoder, and you tune k to trade latency for precision."* — Leads with an anchor the reader owns, then names what's genuinely new.
- **Good (non-software, same form):** *"If you know how a triage nurse sorts an ER waiting room, a load balancer's priority queue is the same move: cheap, fast classification up front so the expensive resource isn't the bottleneck. New here: the 'severity' signal is latency-budget, and the queue can starve low-priority work."* — The rules are domain-independent; only the anchor changes.

### R-XREF-01 — Cross-domain mapping lives in the card
*The home-domain analogue is the card's opening sentence, not a footnote.* **LLM default:** demotes the highest-yield analogy to an aside.
- **Bad:** *"…(for readers from a databases background, this is loosely analogous to a query planner; see footnote 7)."* — The analogy that does the most work is hidden where a scanning reader misses it.
- **Good:** The analogue is the first sentence of the card (as in R-CARD-01's good example). — The mapping does its work at L1, where it's actually read.

### R-CARD-03 — Skip-it-when is mandatory and specific
*Every technique states when to reach for it AND a specific when-to-skip.* **LLM default:** gives a use-condition, never a skip-condition.
- **Bad:** *"Use a reranker to improve retrieval precision."* — Only tells you when to use it.
- **Good:** *"Reach for a reranker when top-k precision beats tail latency. Skip it under ~100ms p99, when QPS is high enough that per-pair cost dominates, or when your real failure is recall, not ordering."* — Specific skip-conditions, not platitudes.

## Summaries & layering

### R-SUMM-01 — Thesis lede, not topic lede
*The lede states a complete claim, not the topic.* **LLM default:** announces what the section "covers."
- **Bad:** *"This section discusses approaches to chunking documents for retrieval."* — A topic label.
- **Good:** *"Chunking isn't preprocessing you skip with a long-context model — it's the unit of retrieval, and getting it wrong caps your recall ceiling no matter how good the embedder."* — A defensible claim the section then defends.

### R-SUMM-03 — Compression gradient
*Each layer is materially shorter and more abstract than the one below; a sub-sum never longer than its source.* **LLM default:** makes every layer the same length, collapsing the fractal into paraphrases.
- **Bad:** A four-paragraph subsection on index families, followed by a sub-sum that restates it in four paragraphs. — Same length, no compression; the layer earns nothing for a skimming reader.
- **Good:** The same subsection, sub-summed to one line: *"Three index families trade memory for recall: brute-force (exact, tiny corpora), IVF (cheap, approximate), HNSW (fast, memory-hungry)."* — Shorter and more abstract; stands alone at summary depth.

### R-SUMM-04 — Fractal coherence (stop at any depth)
*Each layer is self-contained; never assumes a deeper one was read.* **LLM default:** references content that only exists deeper.
- **Bad (a card line):** *"As shown in the ablation below, the third variant wins."* — A reader who stops at the card is stranded; the claim depends on a layer they haven't read.
- **Good:** *"The third variant wins; the ablation later in this section shows why."* — Self-contained here, with an optional pointer down rather than a dependency.

## Coverage & flow

### R-MV-01 — Multi-view per core concept
*Each core concept appears in ≥3 distinct representation modes across the document.* **LLM default:** gives one definition and stops.
- **Bad:** *"HNSW is a graph-based ANN index with logarithmic search."* — One mode (definitional); the reader gets a definition and nothing to reason with.
- **Good:** HNSW appears as **architecture** (the layered-graph diagram), as a **trade-off** (the memory-vs-recall row in the decision matrix), and as a **failure mode** (the "updates are costly — deletes force partial rebuilds" pitfall). — The same concept as structure, as a trade-off, and as a failure; that's cognitive flexibility, not repetition.

### R-PROSE-01 — Given→new information flow
*Sentences open with given/linking material and end with the new; chain subject entities.* **LLM default:** every sentence introduces a new subject — disconnected facts.
- **Bad:** *"Embeddings encode meaning. Latency is a production concern. Cross-encoders are slow."* — Three sentences, three new subjects, no thread.
- **Good:** *"Embeddings encode meaning as vectors; comparing those vectors is fast, which is why bi-encoders scale — but a cross-encoder, which scores a query–document *pair* directly, is slower for the same reason it's more accurate."* — Each clause picks up the prior one's terminal idea.

## Tone & stance

### R-PROSE-02 — Trade-offs as word-choice
*Never "X is good"; always what X buys and at what cost.* **LLM default:** unqualified praise or neutral "balanced" coverage.
- **Bad:** *"Microservices are a great architecture for scalability."* — Praise with no cost named.
- **Good:** *"Microservices buy independent deploy and scale at the cost of network latency, distributed-failure modes, and operational overhead a monolith never had."* — Merit paired with its price.

### R-PROSE-06 — Opinionated, asymmetric
*Take leverage-weighted positions; don't force pro/con parity.* **LLM default:** forced symmetry and hedging.
- **Bad:** *"There are pros and cons to both. A has three advantages and three disadvantages; B likewise."* — Takes no position; manufactures parity.
- **Good:** *"Default to A. Its one real weakness — cold-start latency — matters only if you restart often, which most services don't. B wins in exactly one case: hard real-time, where A's GC pauses are disqualifying."* — A weighted call; the trade-off is asymmetric and named.

## Vocabulary

### R-VOCAB-01 — Terminology univocity
*One canonical term per concept; aliases declared, not improvised.* **LLM default:** renames the same concept several ways.
- **Bad:** *"…the retriever… the recall stage… the candidate generator… the first-pass search…"* — Four names for one component; the reader can't tell they're the same thing.
- **Good:** Pick one — *"the retriever"* — and use it throughout, declaring any alias once. — One concept, one name.

### R-VOCAB-02 — Name and reuse handles
*Give recurring failure modes/patterns memorable names and reuse them.* **LLM default:** re-describes the same idea each time.
- **Bad:** *"…the problem where retrieval returns plausible-but-wrong passages… that issue where the retriever fetches something that looks right but isn't…"* — An unnamed recurring concept, re-explained, costing the reader memory.
- **Good:** *"Call this **confident-irrelevance**."* then reuse the handle. — A name that turns a recurring idea into a reusable token.

## Pedagogy

### R-EXPERT-01 — No worked examples in the primary layer
*Above early_career, teach by contrast; worked examples only behind opt-in deeper layers.* **LLM default:** tutorial scaffolding (its training distribution).
- **Bad:** *"Let's walk through it. First, install the client. Second, create a collection. Third, insert your vectors. Fourth, run a query…"* — An expert reads past all of it.
- **Good:** *"The API is the same three calls as any datastore — create, write, query; the only non-obvious part is that 'query' takes a vector and a k and returns *approximate* neighbors, so unlike SQL the results can shift when you rebuild the index."* — Teaches by contrast with what the expert already knows.

### R-EXPERT-02 — Scaffolding behind explicit gates
*Novice scaffolding lives behind an "if you don't have X, read Y" gate, not on the primary surface.* **LLM default:** inline remedial explanation.
- **Bad:** *"In case you're not familiar, an embedding is a list of numbers that represents meaning…"* — On the primary surface, where the expert must read past it.
- **Good:** *"(New to embeddings? Read the Foundations primer first.)"* — A one-line gate; the scaffolding is off the primary surface.

## Recall

### R-RECALL-02 — Generation-based, calibrated recall
*Questions require generation (not recognition), ≥1 cross-domain, answerable from an attentive L1 read.* **LLM default:** definitional/recognition trivia.
- **Bad:** *"Q: What does HNSW stand for? A: Hierarchical Navigable Small World."* — Recognition trivia; tests nothing usable.
- **Good:** *"Q: You're at 200ms p99 and need to halve it; the index is HNSW on a static 2M-vector corpus. First knob, and its cost? A: Lower efSearch — fewer graph hops — trading recall for latency; if that's not enough, drop embedding dimension or move to a coarser IVF."* — Requires generation and transfer.

## Operational artifacts

### R-ART-03 — Toulmin recommendation blocks
*Every recommendation carries a qualifier (conditions) and rebuttal (when it fails).* **LLM default:** bare, unqualified recommendations.
- **Bad:** *"Use hybrid search (BM25 + vectors) for better results."* — No conditions, no failure mode.
- **Good:** *"Use hybrid BM25+vector when queries mix exact-match terms (codes, names) with semantic intent — the lexical channel catches what embeddings blur. **Qualifier:** the gain shrinks as queries become purely conceptual. **Rebuttal:** on short, code-like corpora BM25 alone often beats hybrid, and fusion adds latency plus a tuning knob (the RRF constant) you now own."* — Claim, qualifier, and rebuttal all present.

### R-ART-04 — Decision matrix is decisive
*Named criteria, a named baseline, a named recommendation; no undisambiguated "it depends".* **LLM default:** a grid of vague ratings with no interpretation.
- **Bad:** A table of *Medium / High / Low* cells, no baseline, final row "it depends." — The reader leaves with no decision.
- **Good:** Same table with a named baseline (*"start with pgvector"*), a recommendation per column, and every "it depends" replaced by a rule (*"corpus < 1M → pgvector; > 10M → dedicated store"*). — Decidable.

### R-ART-02 — Checklist killer-item discipline
*≤9 action-verb items per pause; only high-frequency-consequential failures; not a glossary.* **LLM default:** exhaustive lists nobody runs.
- **Bad:** A 30-item "RAG checklist" enumerating every conceivable consideration. — Reads as a glossary; never gets run.
- **Good:** A 6-item pre-ship list, action-first: *"Confirm recall@k on real queries · Verify no PII in the index · Check the rebuild path exists · …"* — Short, action-verb-first, high-consequence only.

## Evidence & honesty

### R-EVID-01 — Settled / contested / speculative tags
*Tag epistemic status; contested claims name a dissenting view; speculation isn't grammatically a fact.* **LLM default:** smuggles speculation as settled fact.
- **Bad:** *"Reranking improves RAG accuracy by 20%."* — A precise number, no source, no hedge — speculation wearing the grammar of fact.
- **Good:** *"Rerankers reliably improve ordering when recall is already high (settled); the end-task gain is contested and dataset-dependent — some report double-digit gains, others near-zero on already-precise retrievers."* — Settled vs contested marked; magnitude not overstated.

### R-EVID-02 — Honest-limits section
*Audit where the primer's own thesis breaks down.* **LLM default:** never says where its framework is wrong.
- **Bad:** Primer ends on "where it's heading" with no acknowledgment of its own blind spots.
- **Good:** *"Where this primer is weakest: it treats retrieval and generation as separable, which breaks for end-to-end-trained systems; and its cost figures assume cloud GPU pricing, which won't hold on-prem."* — Names its own failure boundary.

## Grounding

### R-GROUND-01 — No fabricated evidence
*Every number/citation/effect size resolves to the ledger; unsourced claims are marked "unverified", never given false precision.* **LLM default:** invents authoritative-looking statistics and citations.
- **Bad:** *"Studies show a 0.84 correlation between chunk size and retrieval quality (Chen et al., 2023)."* — A precise statistic and a citation with no ledger entry — fabricated authority.
- **Good:** *"Chunk size materially affects retrieval quality, though the optimum is corpus-specific; I don't have a single authoritative effect size and have marked this unverified rather than invent one."* — Claims only what's grounded; marks the gap.

### R-GROUND-03 — Citation precision (the Phase-6 signature failure)
*The cited source must actually support the statement it's attached to.* **LLM default:** attaches a real, ledger-present source that is merely topical, not supporting.
- **Bad:** *"Rerankers cut hallucination rates by half [Lewis et al. 2020]."* — Lewis et al. (the RAG paper) is real and in the ledger, but it doesn't establish that hallucination claim — a precision failure, not a fabrication.
- **Good:** *"Reranking improves retrieval ordering [Lewis et al. 2020]; its effect on downstream hallucination is not established by that work and I haven't found a source that measures it directly."* — The citation supports exactly what it's attached to, and the unsupported leap is named, not smuggled.

## Figures

### R-FIG-01 — Complete-claim captions
*Every caption states the figure's conclusion, not a label.* **LLM default:** writes a label.
- **Bad:** *"Figure 4: The ingestion pipeline."* — States no conclusion.
- **Good:** *"Figure 4: Ingestion is embarrassingly parallel up to the embed step, which is the throughput bottleneck — everything downstream waits on the GPU."* — States what the figure proves.
