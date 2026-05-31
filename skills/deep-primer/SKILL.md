---
name: deep-primer
description: >
  Generates a research-grade technical primer on a topic for an EXPERT reader, delivered as a
  depth-dialed, self-contained HTML artifact with a per-section field-guide layer, multi-view
  concept coverage, and source-grounded citations. Use this skill whenever the user
  asks to "get up to speed on", "give me a primer on", "deep dive into", "I need to understand",
  "teach me about", "what's the state of the art in", "break down X for me", or otherwise signals
  they want a thorough, structured, decision-ready understanding of a domain — especially when
  bridging from one technical domain into an adjacent one. Also trigger on "primer", "landscape
  overview", "technical briefing", "field guide", or "lay of the land", and on substantive
  upskilling or synthesis requests even when the user never says the word "primer".
  Do NOT trigger for simple factual questions, code generation, debugging, or file manipulation.
---

# Deep Primer

Generate a research-grade primer for a senior practitioner moving into an adjacent domain — the
working map you'd build after reading a dozen papers, watching conference talks, and talking to
practitioners — delivered as one self-contained, depth-dialed HTML artifact.

This skill is governed by a **rule registry** (`references/rule-registry.yaml`, 61 rules). The
18 highest-leverage generation-time rules are inlined below as the **CORE**; hold them throughout.
The rest are enforced *after* generation by deterministic lints (`scripts/`), a model-verified
citation check (Phase 6), and scoped binary critics (`references/critic-prompts/`) — you needn't
recite them, but never contradict them.
Rationale and effect sizes for every rule are in `references/evidence-map.md`. Cite a rule by ID
(e.g. `R-CARD-01`) in any note you write to disk.

## The one test
A competent reader in the domain can stop at **any** depth — only the ledes, only the cards, only
the summaries, or the full prose — and come away with a coherent, correctly-scoped mental model at
that depth. Every rule serves this test.

## Parameters — resolve first
Set four parameters before anything else (`R-PARAM-01`). If the request is bare, infer from memory
and past chats (`conversation_search`, `recent_chats`); if still unknown, ask **one** compact
question. Write `parameters.yaml`.

- **home_domain** (list) — the reader's existing expertise; fills the card's anchor row, calibrates analogies and assumed vocabulary.
- **target_domain** — the primer's subject (the domain being bridged into).
- **seniority_band** — `early_career | mid_senior | staff_plus`; scales scaffolding suppression (`R-PARAM-02`, `R-EXPERT-01`). Default `mid_senior` if unknown.
- **length_budget** — drives depth allocation via the ledger-salience proxy (claim frequency / centrality), since V1 has no concept graph. Total length tracks the budget; allocate by salience rather than padding uniformly (`R-ARCH-06`), and scale the apparatus to each section's substance (`R-DEPTH-03`).
- **outputs** — which projections to render from the IR: `html` (human) and/or `llm_md` (operationally-distilled, block-id-aligned, provenance-tagged). Default `[html]`; add `llm_md` when the primer will also ground an LLM (`R-PROJ-01..06`).
- **seed_sources** — optional user-provided sources to consult ("check the work of John Doe and <URL>"): `url` / `file` / `project_ref` (direct — fetched, grounded, never dropped) and `author`/entity directives (seed a targeted brief). Treated as leads worth looking at, not gospel — still corroboration-graded and surfaced as contested where the consensus disagrees (`R-DISC-06`). `project_ref` resolves only in claude.ai.

## CORE — hold these throughout (the resident `must_core`)
1. **R-ARCH-03** Open with the thesis/answer (BLUF/SCQA), cuttable from the bottom; no throat-clearing intro.
2. **R-SCENT-01** Every heading is a complete predictive claim/question; banned generic labels: Overview, Introduction, Key Concepts, Background, Conclusion, Miscellaneous.
3. **R-CARD-01** Each section opens with an at-a-glance card that *activates prior knowledge*: lead with the home_domain analogue + 3–5 anchor concepts, then what's new vs renamed. Not a teaser/summary.  *(why: advance organizers fire only if they activate prior knowledge)*
4. **R-CARD-03** Every technique states when to reach for it **and** a specific when-to-skip.
5. **R-SUMM-01** The lede states a complete claim, not the topic.
6. **R-SUMM-03** Compression gradient: each layer is materially shorter and more abstract than the one below; a sub-sum is never longer than its source.  *(why: minimalism, d≈1.12 — compress, don't repeat)*
7. **R-SUMM-04** Each layer is self-contained; never assumes a deeper layer was read.
8. **R-MV-01** Each core concept appears in ≥3 distinct representation modes across the document (architecture / tradeoff-table / failure-taxonomy / benchmark / cost-model / code / mental-model / historical).
9. **R-PROSE-01** Given→new flow: sentences open with given/linking material and end with the new; chain subject entities across sentences; each section opening restates the prior section's terminal entity.  *(why: given→new is how prose coheres, not a style preference)*
10. **R-PROSE-02** Trade-offs as word-choice: never "X is good" — always "X buys A at the cost of B".
11. **R-EXPERT-01** No step-by-step worked examples in the primary layer above `early_career`; teach by contrastive comparison; worked examples only behind opt-in deeper layers.  *(why: expertise reversal — scaffolding that helps novices hurts experts)*
12. **R-VOCAB-01** One canonical term per concept; define only topic-specific terms-of-art; assume in-domain vocabulary per home_domain.
13. **R-RECALL-02** 3 generation (not recognition) questions per section, ≥1 forcing a cross-domain mapping, answerable from an attentive L1 read.  *(why: testing effect — generation beats recognition)*
14. **R-ART-03** Every recommendation/trade-off/superiority claim is a Toulmin block — Claim / Data / Warrant / Backing / Qualifier / Rebuttal — with the **Qualifier** (conditions/strength) and **Rebuttal** (when it fails) always present.
15. **R-EVID-01** Tag claims settled / contested / speculative; contested claims name ≥1 dissenting view; speculation never wears the grammar of fact.
16. **R-GROUND-01** Every number, citation, or effect size resolves to a source-ledger entry. **Never fabricate** a citation, statistic, or effect size; a believed-but-unsourced claim is marked "unverified", never given false precision.  *(why: the integrity floor — never traded off)*
17. **R-XREF-01** The home-domain mapping lives in the card's opening sentence, not a footnote.
18. **R-FIG-01** Every figure caption states the figure's conclusion (a claim), not a label.

## Anti-rules — never do (the `MUST_NOT` tier)
- **R-REJECT-01** No E-Prime constraint. **R-REJECT-02** Surprisal/UID is a diagnostic heuristic only, never an editing target. **R-REJECT-03** No strict-MECE quality gate. **R-REJECT-04** No content restructuring driven by an RST parse (soft signal only). **R-REJECT-05** Critic prompts ask **binary single-criterion** questions only — never "is this good/thorough?" — and use swap-and-average on any pairwise call; this is the guard against verbosity and self-preference bias in an all-Claude judge.

---

## The pipeline
Eight phases. Each declares inputs → outputs and an exit condition; the synthesizer reads its
**file artifacts** (external memory), never an in-context dump of everything, so the research phase
parallelizes later without rework. Write a `run-manifest.json` recording phase completion so a run
can resume after interruption.
**IR-first:** Phase 3 emits a canonical **document IR** (`references/artifact-schemas.md`), not HTML;
Phases 4–7 read the IR; Phase 8 renders it into the requested `outputs` (HTML and/or the distilled
LLM-MD), which share block-ids (`R-PROJ-01..06`).
**Discovery (Phase 1a):** before retrieval, a saturating cascade of parallel deep-research ensembles (`references/discovery-brief-templates.md`) augments recall, feeding leads — not evidence — into the grounding loop (`R-DISC-01..05`; deterministic engine `scripts/research/discovery.py`).
**Convergence guard:** the drafting↔structure loop is bounded by `R-CONV-01..02` — a loose escalate (re-front-load) threshold that auto-tightens to a hard `K_MAX`, and renders a `contested-structure` block when the structure won't settle (`scripts/research/convergence.py`).

### Circuit breakers (from registry `budgets`; tune in eval)
`max_retrieval_iterations: 6` · `min_sources_per_question: 2` · `min_independent_nonvendor_sources_for_perf_claim: 2` · `recall_calibration_target: 0.75` · `critic_human_divergence_recalibrate_threshold: 0.25` · `max_revise_iterations: 3` · `per_run_token_cap: TODO`. A loop that hits a cap halts and surfaces state rather than spending more.

### Phase 0 — Parameters
in: request, memory/past-chats → out: `parameters.yaml`. Exit: all four parameters resolved. (`R-PARAM-01/02`)

### Phase 1 — Research arc (single-agent, circuit-broken) — *detail below*
in: `parameters.yaml`, persistent KB (files + Mixedbread) → out: `research-plan.yaml`, `source-ledger.yaml` (+ KB upsert), `concept-map.yaml`, outline seed.
Exit: every research-plan question has ≥`min_sources_per_question` grounded claims (≥`min_independent_nonvendor` for any performance claim); coverage gaps closed or explicitly flagged. (`R-EVID-03`, `R-GROUND-04`)

### Phase 2 — Outline (lint-gated)
in: `concept-map.yaml`, `parameters.yaml` → out: `outline.yaml`.
Active: operational artifacts planned (`R-ART-01`), honest-limits section (`R-EVID-02`), multi-view coverage at outline level (`R-MV-01`), predictive headings (`R-SCENT-01`), L1 actionable (`R-DEPTH-01`).
**Scope control (broad topics):** a single artifact cannot hold an unbounded topic at depth — pick the 3–5 highest-leverage sub-areas to cover fully and treat the rest at a higher level with pointers; this is an editorial decision stated in the scope block, not collapsible-section hiding. Match the apparatus to substance — a thin section need not carry the full layer set (`R-DEPTH-03`).
Exit: outline lint passes.

### Phase 3 — Per-section drafting (the field-guide layer)
in: `outline.yaml`, `concept-map.yaml`, `source-ledger.yaml` → out: **document IR** (`document-ir.yaml`: sections→blocks with `role`/`concept`/`mode`/`claim_ids`/`provenance`, + meta). HTML is rendered later (Phase 8), not here.
Per section, in order: lede (`R-SUMM-01`) → card (`R-CARD-01/02/03`, `R-XREF-01`) → section summary ≤500w (`R-SUMM-02`) → subsections, each opening with one sub-sum → recall placeholder. Apply prose rules (`R-PROSE-*`), expertise rules (`R-EXPERT-01/02`), univocity (`R-VOCAB-01`) throughout.
Exit: per-section structural lints pass before moving to the next section.

### Phase 4 — Coherence + multi-view passes
in: draft + sidecars → out: revised draft. Checks: given-new entity grid (`R-PROSE-01`), representation modes per concept (`R-MV-01`). Exit: both clear.

### Phase 5 — Recall + figures
in: draft + `concept-map.yaml` → out: recall blocks (`R-RECALL-01/02`) and figures with complete-claim captions, one emphasis each, accessible (`R-FIG-01..05`). Exit: recall-count and figure checks clear.

### Phase 6 — Verification (citation recall / precision) — *model_verified, not a deterministic lint*
in: draft + `source-ledger.yaml` → out: `verify-report.json`. Checks: no fabrication (`R-GROUND-01`, deterministic — every marker resolves to a ledger source_id), citation recall (`R-GROUND-02`) and citation precision (`R-GROUND-03`), both **model_verified** via an entailment check (NLI / MiniCheck or a scoped Claude call) that the cited quote actually supports the claim. Source or mark-unverified any uncited factual statement. Exit: zero unresolved citations and recall/precision ≥ eval thresholds.

### Phase 7 — Critique + bounded revise loop — *detail below*
in: draft + all sidecars + reports → out: `lint-report.json`, `critic-report.json`, `revision-log.md`, revised primer.
Exit: zero MUST violations, or `max_revise_iterations` reached → surface persistent violations to the user.

### Phase 8 — Delivery (render projections from the IR)
in: validated IR → out: the requested `outputs` rendered from the IR — `primer.html` (human) and/or `primer.llm.md` (operationally distilled), sharing block-ids (`R-PROJ-02`) — plus `quality-card.md` (what passed, what was waived, known limits) + 2–3 concrete follow-up offers (an interactive drill-down on one section, a cheat-sheet / quick-reference card, an annotated bibliography). Present the artifact(s); keep the post-amble short.

---

## Phase 1 in detail — the research arc
The quality ceiling of the primer is the quality of this phase. Run it as a structured, multistep
arc, not one batch of searches. Perspective question-templates live in
`references/research-perspectives.md`.

1. **Plan into questions × perspectives.** Decompose the topic into key questions and sub-questions, each tagged with a perspective. Derive the perspectives from the primer's own structure — they are the lenses you must fill anyway: bridge-builder (home→target mapping), production practitioner (what breaks at scale), skeptic (failure modes, overclaims), historian (lineage, what was tried before), competing-school adherent (the rival approach's case), and a standards/compliance lens where relevant. Write `research-plan.yaml`.
2. **Consult the persistent KB first.** `search_store` (Mixedbread) for prior sources relevant to each question; reuse fresh hits, flag stale ones for re-fetch. Only then go to the web for gaps.
3. **Iterative, perspective-scoped retrieval.** For each question × perspective: search → fetch full pages (not snippets) → extract → identify gaps → re-query, bounded by `max_retrieval_iterations` and the coverage rule. Favor primary sources; tag every source's type (primary-paper / docs / blog / vendor) and a credibility tier.
4. **Claim-level extraction → ledger.** As you read, extract atomic claims with provenance: claim text, `source_id`, a **short** supporting quote (≤15 words) with location, source-type, recency stamp, confidence. Write `source-ledger.yaml`; upsert new sources into the KB (dedup by normalized-URL hash + embedding similarity). Keep quotes short — the primer paraphrases, never reproduces.
5. **Recency / version sweep.** Extract every named technology/library/model; search current versions and release notes; pin them; flag anything stale (`R-GROUND-04`).
6. **Conflict + coverage analysis.** Tag contradictions as contested with both sides cited; check coverage against the plan; gaps loop back to step 3 (bounded). Performance claims need ≥`min_independent_nonvendor` corroboration (`R-EVID-03`).
7. **Curate → concept map + outline seed.** Cluster claims into core concepts with canonical terms, home-domain anchors, and the representation modes each will get; emit `concept-map.yaml` and the outline seed.

## Phase 7 in detail — critique, bounded loop, block-scoped revision
- **Hard lints first** (deterministic, free of context): run `scripts/lint.py`, which loads the registry and dispatches every `hard_lint` check; plus the Phase 6 verification report.
- **Then scoped binary critics** — the **six** prompts in `references/critic-prompts/` (architecture, field-guide, coherence, expertise-calibration, evidence-grounding, figures), each reading only its slice of the registry and answering binary rubric questions against the parsed block list. Never ask a critic for holistic quality (`R-REJECT-05`). Run gating judgments ≥2× (test-retest) and flag unstable verdicts for human review; swap-and-average applies only when comparing two candidate revisions, not to pointwise verdicts.
- **Revise block-scoped.** Each violation points at a `data-block-id`; revise that block and its immediate neighbors only — never regenerate the whole document. Track which violations were fixed, which persisted, which appeared new, in `revision-log.md`.
- **Bounded.** Stop at zero MUST violations or `max_revise_iterations`; surface any persistent violations in the quality card rather than papering over them.
- **Calibration (maintenance, not per-run):** spot-check critic verdicts against the human-labeled eval set; divergence above `critic_human_divergence_recalibrate_threshold` means the rubric needs recalibration.

## Rendering (projections from the IR)
Both artifacts are rendered from the canonical IR (`R-PROJ-01`) and share block-ids (`R-PROJ-02`).
**HTML** (`render/render_html.py`): build on `assets/primer-template.html`, which provides the depth-dial shell (L1–L5 toggles),
dark/light mode, a floating font-size control, `data-block-id`/`data-concept`/`data-mode` on blocks,
and the embedded `primer-meta` JSON. Carry over the proven aesthetic: a distinctive readable font pairing (avoid Inter/Roboto/Arial);
no hard max-width on the content container; SVG diagrams that use CSS theme variables (no hardcoded
strokes that vanish in dark mode); numbered footnotes linking to a references section. Use `image_search` only for a real photograph SVG cannot convey; never fetch the domain's own copyrighted figures — draw a synthetic schematic instead.
**LLM-MD** (`render/render_llm_md.py`, emitted when `outputs` includes `llm_md`): the operationally-distilled projection — role-filtered (`R-PROJ-03`), de-anaphorized to self-contained chunks (`R-PROJ-04`), provenance-tagged inline (`R-PROJ-05`), SVG dropped but captions kept (`R-PROJ-06`); front-matter index + one `##` block per heading `[block: <id>]`. See `references/artifact-schemas.md`.

## Files (progressive disclosure — when to load each)
- `references/rule-registry.yaml` / `.md` — source of truth + readable companion. Consult when a rule's exact wording/enforcement matters. **[built]**
- `references/evidence-map.md` — rationale and effect sizes. Load only when a rule's rationale is in question. **[built]**
- `references/research-perspectives.md` — perspective question-templates. Load at **Phase 1**. **[built]**
- `references/artifact-schemas.md` — schemas for `research-plan` / `source-ledger` / `concept-map` / `primer-meta` + the block-attribute contract. Load at **Phase 1** (and Phase 3 for the block attributes). **[built]**
- `references/exemplars.md` — contrast pairs keyed by rule_id. Load during **Phase 3** drafting. **[built]**
- `references/critic-prompts/{structure-architecture,structure-fieldguide,coherence,expertise-calibration,evidence-grounding,figures}.md` — scoped binary critic prompts. Load the matching one **during its Phase-7 pass**. **[built]**
- `tools/{gen_registry_md,gen_critic_prompts}.py` + `build.sh` — regenerate the lockstep-derived files after editing the registry. **[built]**
- `scripts/lint.py` + `scripts/checks/*` — `hard_lint` implementations. **[Claude Code phase]**
- `scripts/research/*` — planner, retrieval loop, claim extractor, recency, coverage, KB (files + Mixedbread). **[Claude Code phase]**
- `scripts/verify/citation_quality.py` — `model_verified` recall/precision + ledger resolution. **[Claude Code phase]**
- `scripts/utils/parse_primer.py` — HTML → typed AST + block list (id/type/concept/mode); figure a11y; meta. **[Claude Code phase]**
- `scripts/eval.py` + `references/eval/` — held-out test specs + rubric. **[Claude Code phase]**
- `assets/primer-template.html`, `assets/card-template.html` — the rendering shells. **[Claude Code phase]**

## Surfaces (V1)
Single-agent throughout. The research phase is *structured* into questions × perspectives and the
synthesizer consumes the ledger as external memory, so multi-agent fan-out is a V2 drop-in behind
unchanged interfaces. The "scripts" are two kinds: **local-deterministic** (parse_primer, the
structural/prose lints) and **agent-orchestrated** (research needs web tools, verification needs an
entailment model, the KB is a Mixedbread MCP tool) — the latter are agent tool-loops, not hermetic
Python. The sandbox has no network and no runtime package installs, so verify package availability
before relying on heavier lints (e.g. spaCy/coref for given-new); structural and length checks
degrade gracefully, while the entity-grid coherence check and the recency sweep need their tooling
or web access. Subagent research, a concept *graph*, and a vector-DB-backed KB are explicitly V2.
