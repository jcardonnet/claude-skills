# Artifact schemas

The data contracts the pipeline produces and consumes. Pinning these is what lets the Phase-6/7
checks run: the grounding check reads `source-ledger`, the multi-view and univocity lints read
`concept-map` plus the block attributes below. All are YAML on disk (files are canonical); the
persistent source store is indexed in Mixedbread for retrieval/dedup.

---

## `research-plan.yaml` (Phase 1, step 1)
The planner emits this; the retrieval loop fills `coverage`. Feeds `source-ledger` and `concept-map`.

```yaml
topic: "<the primer topic>"
parameters_ref: parameters.yaml
perspectives_used: [bridge-builder, practitioner, skeptic, historian, competing-school, forecaster]
questions:
  - id: Q1
    perspective: bridge-builder
    text: "What is <concept> in <target_domain>, and its closest analogue in <home_domain>?"
    target_sections: [foundations, cross-domain]
    serves_rules: [R-CARD-01, R-XREF-01]
    budget_weight: 1.0          # per-perspective retrieval weight (see research-perspectives.md)
    merged_from: []             # ids of duplicate questions folded into this one (dedup)
    sub_questions:
      - "Where does the analogy break (fidelity boundary)?"
    coverage:
      status: open              # open | covered | thin
      sources: []               # source_ids from the ledger
      independent_nonvendor: 0
      iterations: 0
```
`covered` when the perspective's coverage signal is met **and** `len(sources) >= min_sources_per_question`
(`independent_nonvendor >= min_independent_nonvendor` for any performance claim); `thin` if
`iterations >= max_retrieval_iterations` first.

---

## `source-ledger.yaml` (Phase 1, step 4 — the grounding substrate)
Atomic claims with provenance. Every empirical statement in the primer must resolve to a `claim_id`
here (`R-GROUND-01`). New sources are also upserted into the Mixedbread store (dedup by
normalized-URL hash + embedding similarity). A per-primer **frozen snapshot** of the entries used is
embedded in `primer-meta` for reproducibility.

```yaml
sources:
  - source_id: "<sha1 of canonical url>"
    url: "https://..."
    title: "..."
    authors: ["..."]
    venue: "..."                       # journal / conference / org / site
    date: "YYYY-MM-DD"                  # publication date
    type: primary_paper                # primary_paper | docs | blog | vendor | standard
    credibility: high                  # high | medium | low
    retrieved_at: "2026-05-28T00:00:00Z"
    content_hash: "<sha1 of fetched body>"
    claims:
      - claim_id: "C1"
        text: "<atomic claim, paraphrased>"
        quote: "<=15-word supporting quote"   # short, for copyright
        location: "p.5 / §3.2 / para 4"
        confidence: high                       # high | medium | low
        contested: false                       # true if another source contradicts it
        contradicts: []                        # claim_ids this conflicts with
```

---

## `concept-map.yaml` (Phase 1, step 7 — the coverage substrate)
Core concepts with canonical terms, anchors, and the representation modes each will receive. Drives
the multi-view lint (`R-MV-01`), univocity lint (`R-VOCAB-01`), the glossary, and depth allocation
via `salience`.

```yaml
concepts:
  - concept_id: "hnsw"
    canonical_term: "HNSW"
    aliases: ["hierarchical navigable small world"]   # only these surface forms allowed (univocity)
    home_anchor: "<the home-domain analogue>"
    fidelity_boundary: "<where the analogy breaks>"
    epistemic_status: settled                          # settled | contested | speculative
    salience: 0.82                                     # centrality-in-claims proxy; drives depth
    representation_modes:                              # planned at outline, block_ref filled when drafted
      - {mode: architecture, block_ref: "fig-3"}
      - {mode: tradeoff,     block_ref: "sec-4-matrix"}
      - {mode: failure,      block_ref: "sec-6-b"}
    source_ids: ["<...>"]
    claim_ids: ["C1", "C7"]
```
`mode ∈ {architecture, tradeoff, failure, benchmark, cost, code, mental_model, historical}`.
R-MV-01 passes when `len(distinct realized modes) >= 3` per concept.

---

## `primer-meta` + block-attribute contract (Phase 3 rendering)
The rendered HTML is self-describing. **This instrumentation is what makes R-MV-01 and R-VOCAB-01
mechanically checkable** — without it, the lints have nothing to count.

Every section / subsection / card / figure carries a stable `data-block-id`. A block that *realizes a
concept in a mode* additionally carries `data-concept` and `data-mode`:

```html
<section data-block-id="sec-4" data-concept="hnsw">
  ...
  <figure data-block-id="fig-3" data-concept="hnsw" data-mode="architecture"
          role="img" aria-label="HNSW layered-graph search">
    <figcaption>Figure 3: search descends layers, so latency is logarithmic in corpus size.</figcaption>
  </figure>
</section>
```

Embedded once per document:

```html
<script type="application/json" id="primer-meta">
{
  "parameters": { "...": "from parameters.yaml" },
  "ledger_snapshot": ["<source_id>", "..."],
  "concept_map": [ { "concept_id": "hnsw", "...": "..." } ],
  "lint_report": { "...": "filled in Phase 7" },
  "model_versions": { "generator": "...", "verifier": "..." },
  "generated_at": "2026-05-28T00:00:00Z"
}
</script>
```

`parse_primer.py` reads HTML back into the typed block list `(id, type, concept, mode)` for legacy/round-trip — but under IR-first (below) the **IR is authoritative** and HTML is one rendering of it, not the source.

---

## Document IR (canonical) — the source of truth
Under IR-first, Phase 3 emits a structured **document IR**, not HTML. Lints, critics, and verification read the IR; the HTML and the distilled LLM-MD are both *rendered from* it (`R-PROJ-01`).

```yaml
# document-ir.yaml (canonical)
meta: {parameters, ledger_snapshot, model_versions, generated_at}
sections:
  - block_id: sec-maskfree
    title: "Pixel masks are usually wasted work for BOM linkage"
    concept: mask-free-linkage
    blocks:
      - {block_id: lede-maskfree,   role: lede,    text: "...", claim_ids: [C1], provenance: inferred}
      - {block_id: card-maskfree,   role: card,    text: "...", concept: mask-free-linkage, mode: mental_model, claim_ids: [C1]}
      - {block_id: rec-maskfree,    role: toulmin, text: "...", claim_ids: [C1,C7], provenance: verified, source_ids: ["<...>"]}
      - {block_id: fig-maskfree,    role: figure,  mode: tradeoff, caption: "Figure 3: ...", svg_ref: "assets/..."}
      - {block_id: recall-maskfree, role: recall,  text: "..."}        # pedagogical → dropped in llm_md
```
`role ∈ {lede, card, summary, body, toulmin, matrix, figure, recall, glossary, further_reading}`;
`provenance ∈ {verified, inferred, unverified}` (the G4 axis; surfaced inline in both projections, `R-PROJ-05`).
Lints run on this structure — no brittle HTML parsing.

## Projections — one IR, two renderings
Both artifacts are pure functions of the IR and **share block_ids** (`R-PROJ-02`), so a claim cited as `[block: rec-maskfree]` resolves in either.

**HTML (human)** — `render/render_html.py`. Full apparatus; depth-dial L1–L5; given→new prose; SVG figures; embeds `primer-meta`. Optimizes linear reading.

**LLM-MD (operationally distilled)** — `render/render_llm_md.py`. A *projection*, not a second document:
- **Role filter** (`R-PROJ-03`): keep `{lede→claim, card→distilled, toulmin, matrix, figure→caption-only, glossary, further_reading→annotated}`; **drop** `{recall}`; demote the advance-organizer hook (keep the anchor only where it carries information).
- **De-anaphorize** (`R-PROJ-04`): rewrite each block self-contained — restate referents, no "as above"; suspend *cross-chunk* minimalism, keep *within-chunk* minimalism. Verify each rewritten block still entails its `claim_ids`.
- **Provenance inline** (`R-PROJ-05`): every claim block prints `provenance` + `source_ids`.
- **SVG→caption** (`R-PROJ-06`): drop SVG markup, keep the complete-claim caption as text.
- **Format**: YAML front-matter index (the concept-map as a glossary/map) + one `##` section per block, heading `[block: <block_id>]` (== the HTML block-id) so a coding agent can grep/jump and a human can cross-reference.

Emitted LLM-MD block shape:
```markdown
## [block: rec-maskfree]   concept: mask-free-linkage   mode: tradeoff   provenance: inferred
Claim: (callout value + bbox + leader anchor) is sufficient for BOM attribution; pixel masks not required.
Holds-when: downstream needs only attribution.
Rebuttal: masks required when downstream needs per-part crops, area, or occlusion.
Sources: [none yet — inferred]
```

Consumption (v1, no index): whole-context attach, or file-in-repo for a Claude Code assistant (grep by block-id). Mixedbread indexing is deferred but a no-op import later, because each block is already a self-contained, metadata-tagged record.
