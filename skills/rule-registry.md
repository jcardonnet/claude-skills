# Deep Primer — Rule Registry (companion)

*Human-readable rendering of `rule-registry.yaml`, generated from it (edit the YAML, regenerate via `tools/build.sh`). The YAML is the source of truth consumed by the generator, the critics, and the linter; this file is for reading and review.*

**Version 0.1.0** · applies to: deep-primer skill, HTML output.

## Legend

**Priority** — `MUST` Non-negotiable. · `SHOULD` Strong default. Deviations require a stated reason in the run log. · `MAY` Apply when it helps; advisory. · `MUST_NOT` Prohibited. Includes anti-rules / do-not-adopt guards.

**Blocking** — Blocking is derived from PRIORITY, not enforcement. A MUST failure blocks delivery; a SHOULD/MAY failure warns and is logged. This holds uniformly across hard_lint, model_verified, and soft_critic.

**Enforcement** — `hard_lint` Deterministically checkable by a local script in scripts/. Runs without consuming generation context. · `model_verified` Script-orchestrated but uses an entailment/judge model (NLI / MiniCheck / a scoped Claude call). Subject to judge-bias caveats; not deterministic. · `soft_critic` Judged by an all-Claude critic against a BINARY rubric question, scoped one category per pass. · `human` Design constraint or judgment the maintainer owns; not auto-checked.

**Evidence grade** — `load_bearing_empirical` Backed by controlled studies / meta-analyses (effect size in EM). · `convergent_craft` Strong practitioner consensus, often corroborated by adjacent evidence; not directly trial-tested. · `engineering` Mechanical/structural correctness; no behavioral claim. · `contested` Weak or disputed evidence; used only as an anti-rule or advisory.

## Per-run parameters

The generalization layer — set once per primer; rules reference these.

- **`home_domain`** (list[str]) — The reader's existing expertise. Fills the card's anchor row; calibrates analogies and assumed vocabulary.
- **`target_domain`** (str) — The primer's subject (the adjacent domain being bridged into).
- **`seniority_band`** (enum) *(values: early_career, mid_senior, staff_plus)* — Scales expertise-reversal suppression. staff_plus = maximal scaffolding suppression; early_career = one opt-in worked example per core concept permitted.
- **`length_budget`** (str|int) — Target length. Drives depth allocation via the ledger-salience proxy (claim-frequency / centrality-in-claims), since V1 has no concept graph.

## Circuit-breaker & calibration defaults

Defaults; tuned in the eval loop.

- `max_retrieval_iterations`: 6
- `min_sources_per_question`: 2
- `min_independent_nonvendor_sources_for_perf_claim`: 2
- `recall_calibration_target`: 0.75
- `critic_human_divergence_recalibrate_threshold`: 0.25
- `max_revise_iterations`: 3
- `per_run_token_cap`: TODO

## Generator core (always resident)

The highest-leverage generation-time MUSTs the generator holds in context. Mechanical hard-lint MUSTs are intentionally excluded here — the linter enforces them after the fact.

- **R-ARCH-03** — Answer-first opening (BLUF)
- **R-SCENT-01** — Predictive, claim-bearing headings
- **R-CARD-01** — Card as advance organizer
- **R-CARD-03** — Skip-it-when is mandatory and specific
- **R-SUMM-01** — Thesis lede, not topic lede
- **R-SUMM-03** — Compression gradient
- **R-SUMM-04** — Fractal coherence (stop-at-any-depth)
- **R-MV-01** — Multi-view per core concept
- **R-PROSE-01** — Given-new information flow
- **R-PROSE-02** — Trade-offs as word-choice
- **R-EXPERT-01** — No worked examples in the primary layer
- **R-VOCAB-01** — Terminology univocity
- **R-RECALL-02** — Generation-based, calibrated recall
- **R-ART-03** — Toulmin recommendation blocks
- **R-EVID-01** — Settled / contested / speculative tags
- **R-GROUND-01** — No fabricated evidence (integrity floor)
- **R-XREF-01** — Cross-domain mapping lives in the card
- **R-FIG-01** — Complete-claim captions

## Rules by category

- [PARAM — Parameters & calibration](#param) (2)
- [ARCH — Document architecture](#arch) (5)
- [SCENT — Headings as information scent](#scent) (2)
- [CARD — The at-a-glance card](#card) (3)
- [SUMM — Fractal summary discipline](#summ) (4)
- [DEPTH — Progressive disclosure](#depth) (3)
- [MV — Multi-view (cognitive flexibility)](#mv) (1)
- [PROSE — Prose & tone](#prose) (6)
- [VOCAB — Vocabulary & univocity](#vocab) (2)
- [EXPERT — Expertise reversal](#expert) (2)
- [RECALL — Retrieval practice](#recall) (2)
- [ART — Operational artifacts](#art) (6)
- [EVID — Empirical claims & epistemic honesty](#evid) (3)
- [GROUND — Anti-hallucination / citation grounding](#ground) (4)
- [FIG — Figures & diagrams](#fig) (5)
- [XREF — Cross-domain mapping & cross-referencing](#xref) (3)
- [PROJ — IR-first & projections](#proj) (6)
- [CONSIST — Consistency & build invariants](#consist) (3)
- [REJECT — Anti-rules / do-not-adopt](#reject) (5)

<a id='param'></a>

### PARAM — Parameters & calibration

#### R-PARAM-01 — Parameters set before generation
`MUST` · `hard_lint` · *convergent_craft*  
Resolve home_domain, target_domain, seniority_band, and length_budget before any generation; if the request is bare, run the parameter interview first.  
- **Check (hard lint):** `checks/structure_coverage.py::params_present` — parameters.yaml exists with all four required fields
- **Counters:** LLM assumes a generic audience and writes an uncalibrated primer.
- **Phase:** 0 · **Evidence:** EM Part I §1 (advance organizers contingent on reader prior knowledge)

#### R-PARAM-02 — Calibrate scaffolding to seniority
`MUST` · `soft_critic` · *load_bearing_empirical*  
Scale scaffolding suppression to seniority_band: staff_plus gets pure contrast and no worked examples; mid_senior gets worked examples only behind deep layers; early_career may have one opt-in worked example per core concept.  
- **Check (critic · expertise-calibration pass):** “Is the scaffolding density consistent with seniority_band (no primary-layer worked examples above early_career)? y/n”
- **Counters:** One-size-fits-all pedagogy that over-scaffolds experts.
- **Phase:** 3,4,7 · **Evidence:** EM Part I §5, flag 2; Kalyuga/Sweller 2003 expertise reversal
- **Params:** seniority_band

<a id='arch'></a>

### ARCH — Document architecture

#### R-ARCH-01 — Scope-and-decisions block
`MUST` · `soft_critic` · *convergent_craft*  
Open the primer with a scope-and-decisions block: intended reader, what is in/out of scope, and the 2-3 editorial decisions that shaped it.  
- **Check (critic · structure pass):** “Does the front matter state audience, scope boundaries, and key editorial decisions before content begins? y/n”
- **Counters:** LLM dives into content with no scope contract.
- **Phase:** 2,3 · **Evidence:** styleguide §1; EM Part I §1

#### R-ARCH-03 — Answer-first opening (BLUF)
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
The opening states the thesis/answer first (SCQA then answer; bottom-line-up-front) and is cuttable from the bottom; no throat-clearing introduction.  
- **Check (critic · structure pass):** “Does the first paragraph state the primer's central claim/answer (not merely the topic), such that later paragraphs could be cut without losing the bottom line? y/n”
- **Counters:** LLM buries the lede behind generic introduction.
- **Phase:** 3 · **Evidence:** EM Part I §1 (inverted pyramid/BLUF), Part II §2 (Minto)

#### R-ARCH-04 — Goal-tuned reading paths
`SHOULD` · `soft_critic` · *convergent_craft*  
Include 2-3 goal-tuned reading paths (e.g., architect-a-system / audit-an-existing-one / research-the-space), each with a one-line who-this-is-for.  
- **Check (critic · structure pass):** “Are there >=2 goal-tuned reading paths with audience notes? y/n”
- **Counters:** LLM assumes a single linear read.
- **Phase:** 2,3 · **Evidence:** styleguide §1

#### R-ARCH-05 — Heading hierarchy contract
`MUST` · `hard_lint` · *engineering*  
h2 = section (full field-guide layer); h3 = subsection (sub-sum + nav + TOC entry); h4 = sub-subsection (body only, NOT in nav/TOC).  
- **Check (hard lint):** `checks/structure_coverage.py::heading_hierarchy` — h4 absent from nav/TOC; every h3 in TOC
- **Counters:** LLM puts everything at one level or floods nav with h4s.
- **Phase:** 3,7 · **Evidence:** styleguide §1

#### R-ARCH-06 — Output length tracks the budget
`SHOULD` · `hard_lint` · *engineering*  
Total length stays within length_budget; allocate depth by ledger-salience — high-centrality concepts get full field-guide treatment, low-salience ones get a mention — rather than padding every section uniformly.  
- **Check (hard lint):** `checks/structure_coverage.py::length_budget` — total words within the budget band; flag uniform-depth padding via per-section length variance
- **Counters:** LLM ignores the length budget and pads every section to similar length regardless of salience.
- **Phase:** 2,3,7 · **Evidence:** styleguide §6; EM Part I §2 (minimalism)
- **Params:** length_budget

<a id='scent'></a>

### SCENT — Headings as information scent

#### R-SCENT-01 — Predictive, claim-bearing headings
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
Every heading is a complete, predictive claim or question; a reader who reads only the headings can reconstruct the section's gist. Banned generic labels: Overview, Introduction, Key Concepts, Background, Conclusion, Miscellaneous.  
- **Check (critic · structure pass):** “Could a reader reconstruct the gist from headings alone, AND are all generic-label headings eliminated? y/n”
- **PASS looks like:** Headings read as 'Why long context did not kill chunking' / 'When a reranker is dead weight' — claims, not 'Background'/'Overview'.
- **Also (hard):** `checks/structure_coverage.py::banned_heading_terms`
- **Counters:** LLM defaults to generic topic-label headings, forcing F-pattern scanning.
- **Phase:** 2,3 · **Evidence:** EM Part I §3 (information foraging; F-pattern vs layer-cake)

#### R-SCENT-02 — Parallel sibling headings
`SHOULD` · `soft_critic` · *convergent_craft*  
Sibling headings share grammatical form.  
- **Check (critic · structure pass):** “Are sibling headings grammatically parallel? y/n”
- **Counters:** Mixed heading forms degrade scannability.
- **Phase:** 3 · **Evidence:** EM Part I §3

<a id='card'></a>

### CARD — The at-a-glance card

#### R-CARD-01 — Card as advance organizer
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
Each section opens with an at-a-glance card that ACTIVATES prior knowledge: it leads with the home_domain anchor analogy and the 3-5 anchor concepts the reader already knows, then states what is genuinely new vs merely renamed. It is not a teaser or a summary in the section's own terminology.  
- **Check (critic · structure pass):** “Does the card open with a home-domain analogue + anchor concepts (an advance organizer), rather than restating the section's content in its own terms? y/n”
- **PASS looks like:** If you know SQL query planners, reranking is the same cheap-filter-then-expensive-sort shape; new is the cross-encoder and the k knob.
- **Counters:** LLM writes the card as a mini-summary (teaser), so the advance-organizer effect never fires.
- **Phase:** 3 · **Evidence:** EM Part I §1 + flag 1; Ausubel; Luiten et al. 1980
- **Params:** home_domain

#### R-CARD-02 — Card required rows
`MUST` · `hard_lint` · *convergent_craft*  
The card contains the required rows: idea, home-domain anchor, what's-new-vs-renamed, reach-for-it-when, skip-it-when, key-exemplar, confidence/maturity.  
- **Check (hard lint):** `checks/structure_coverage.py::card_rows` — all required <dl> rows present per section card
- **Counters:** LLM drops the harder rows (skip-it-when, what's-new).
- **Phase:** 3,7 · **Evidence:** styleguide §3

#### R-CARD-03 — Skip-it-when is mandatory and specific
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Every technique/approach states both when to reach for it and when to SKIP it; skip-conditions are specific, not platitudes.  
- **Check (critic · structure pass):** “Does every technique presented carry a specific skip-condition (not just a use-condition)? y/n”
- **PASS looks like:** Reach for a reranker when top-k precision beats tail latency; skip it under ~100ms p99 or when recall, not ordering, is the failure.
- **Counters:** LLM lists when to use something but never when not to.
- **Phase:** 3,4 · **Evidence:** styleguide §0, §3 (every concept paired with triggers)

<a id='summ'></a>

### SUMM — Fractal summary discipline

#### R-SUMM-01 — Thesis lede, not topic lede
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Each section's lede states its thesis as a complete claim (cuttable from the bottom), not the section's topic.  
- **Check (critic · structure pass):** “Is the lede a complete claim defending a position, rather than a topic announcement? y/n”
- **PASS looks like:** 'Chunking is the unit of retrieval, and getting it wrong caps recall no matter the embedder' — a claim, not 'This section covers chunking.'
- **Counters:** Topic-label ledes ('This section covers X').
- **Phase:** 3 · **Evidence:** styleguide §2,§4

#### R-SUMM-02 — Summary budgets and 1:1 sub-sum
`SHOULD` · `hard_lint` · *convergent_craft*  
Section summary <= 500 words (ceiling, not target); each h3 has exactly one sub-sum.  
- **Check (hard lint):** `checks/structure_coverage.py::summary_budgets` — section_summary_words<=500; count(h3)==count(sub_sum)
- **Counters:** Runaway summaries; missing or duplicate sub-sums.
- **Phase:** 3,7 · **Evidence:** styleguide §4

#### R-SUMM-03 — Compression gradient
`MUST` · `hard_lint` · *load_bearing_empirical* · **CORE**  
Each layer is materially shorter and more abstract than the one below it; a sub-sum never exceeds the length of the subsection it summarizes.  
- **Check (hard lint):** `checks/prose_caps.py::compression_gradient` — len(sub_sum) < len(source); card.idea < section_summary < section_body (token ratios)
- **Counters:** LLM makes every layer roughly the same length, collapsing the fractal into three paraphrases.
- **Phase:** 3,4,7 · **Evidence:** EM Part I §2; Carroll 1990 minimalism; Ginns, Hollender & Reimann 2006 (minimalist-training meta-analysis) d≈1.12 (slash-the-verbiage d≈0.89)

#### R-SUMM-04 — Fractal coherence (stop-at-any-depth)
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Each layer is coherent on its own; no layer assumes the reader has read a deeper layer.  
- **Check (critic · coherence pass):** “Reading only this layer (lede / card / summary), is it self-contained without requiring a deeper layer? y/n”
- **PASS looks like:** A card that names the analogue, anchors, and what's-new stands alone; a reader who stops there is not told to 'see the ablation below'.
- **Counters:** Layers that reference content only defined deeper, breaking the depth dial.
- **Phase:** 4,7 · **Evidence:** EM Part I §1 (Reigeluth epitome); styleguide §4

<a id='depth'></a>

### DEPTH — Progressive disclosure

#### R-DEPTH-01 — L1 is actionable for a senior reader
`MUST` · `soft_critic` · *convergent_craft*  
Everything a senior practitioner frequently needs to ACT is present at L1 (ledes + cards); decision-critical material is never hidden in deep layers only.  
- **Check (critic · structure pass):** “Could a senior reader make the primer's routine decisions from L1 alone, without descending? y/n”
- **Counters:** Hiding frequently-needed information behind progressive disclosure.
- **Phase:** 2,3 · **Evidence:** EM Part I §3 (Nielsen progressive-disclosure caveat)

#### R-DEPTH-02 — Depth-dial mechanics
`SHOULD` · `hard_lint` · *engineering*  
Emit the L1-L5 depth-dial controls and ensure each depth tier renders coherently.  
- **Check (hard lint):** `utils/parse_primer.py::depth_dial_present` — depth toggles + tier classes present
- **Counters:** Static document with no disclosure control.
- **Phase:** 3,7 · **Evidence:** styleguide §6

#### R-DEPTH-03 — Scale the apparatus to substance
`SHOULD` · `soft_critic` · *convergent_craft*  
Match the field-guide apparatus to each section's substance: a thin section may carry a lede and a brief card without the heavier artifacts; never manufacture cards, recall questions, or artifacts to fill a quota where they add nothing.  
- **Check (critic · expertise-calibration pass):** “Is the apparatus proportionate to each section's substance, with no padded or quota-filling cards/recall/artifacts? y/n”
- **PASS looks like:** A two-paragraph section carries a lede and a one-line card and stops; it does not invent a decision matrix or three recall questions to look complete.
- **Counters:** LLM applies the full heavy apparatus uniformly, padding thin sections and fighting minimalism.
- **Phase:** 2,3,7 · **Evidence:** EM Part I §2 (minimalism); EM Part I §3 (progressive disclosure)

<a id='mv'></a>

### MV — Multi-view (cognitive flexibility)

#### R-MV-01 — Multi-view per core concept
`MUST` · `hard_lint` · *load_bearing_empirical* · **CORE**  
Each core concept (from the concept-map) is presented in >=3 distinct representation modes across the document (from: architecture, tradeoff-table, failure-taxonomy, benchmark, cost-model, code-example, mental-model, historical-analogue).  
- **Check (hard lint):** `checks/multiview_concepts.py::modes_per_concept` — count(distinct representation_modes per concept_id) >= 3
- **Also (soft):** Are the multiple representations genuinely different lenses, not restatements? (multiview pass)
- **Counters:** LLM gives one definition of a concept and stops.
- **Phase:** 2,4,7 · **Evidence:** EM Part II §7; Spiro CFT; Jacobson & Spiro 1995

<a id='prose'></a>

### PROSE — Prose & tone

#### R-PROSE-01 — Given-new information flow
`MUST` · `hard_lint` · *load_bearing_empirical* · **CORE**  
Each sentence opens with given/linking material and ends with the new; subject entities chain across sentences; each section opening restates the prior section's terminal entity.  
- **Check (hard lint):** `checks/coherence_givennew.py::entity_grid` — flag sentences whose subject entity is absent from the previous 2 sentences; flag paragraphs where every sentence introduces a new subject entity
- **Also (soft):** Does the prose chain given->new rather than introducing a new subject each sentence? (coherence pass)
- **Counters:** LLM writes choppy prose where every sentence introduces a new subject entity.
- **Phase:** 4,7 · **Evidence:** EM Part II §4; Haviland & Clark 1974; Barzilay & Lapata 2008

#### R-PROSE-02 — Trade-offs as word-choice
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Never assert 'X is good'; always state what X buys and at what cost ('X reduces A at the cost of B').  
- **Check (critic · expertise-calibration pass):** “Are claims of merit framed as trade-offs (cost named), not as unqualified praise? y/n”
- **PASS looks like:** 'HNSW buys sub-linear latency at the cost of high memory and slow builds' — cost named, not 'HNSW is great.'
- **Counters:** LLM gives neutral 'balanced' coverage or unqualified endorsements.
- **Phase:** 3,4 · **Evidence:** styleguide §0,§8

#### R-PROSE-03 — Prose-first
`SHOULD` · `soft_critic` · *convergent_craft*  
Prose is the default carrier; use lists/tables/figures only where they are the clearest form; do not bullet-dump reasoning.  
- **Check (critic · structure pass):** “Is reasoning carried in prose rather than fragmented into bullets where prose would be clearer? y/n”
- **Counters:** LLM bullets everything.
- **Phase:** 3,4 · **Evidence:** styleguide §8

#### R-PROSE-04 — Condition before instruction
`SHOULD` · `hard_lint` · *convergent_craft*  
In procedural sentences, state the circumstance/goal before the instruction ('To X, do Y'), so a reader can skip inapplicable steps.  
- **Check (hard lint):** `checks/prose_caps.py::condition_first` — heuristic: imperative-led sentences with a trailing 'if/when' clause flagged
- **Counters:** LLM puts the instruction first, the condition last.
- **Phase:** 3,4 · **Evidence:** EM Part II §9 (Google condition-first; working memory)

#### R-PROSE-05 — Structural length caps (not vocabulary restriction)
`MAY` · `hard_lint` · *convergent_craft*  
Apply soft caps: procedural sentence <=20 words, descriptive <=25, noun-cluster <=3, paragraph <=6 sentences. These are STRUCTURAL only; do NOT restrict vocabulary or flatten technical nuance.  
- **Check (hard lint):** `checks/prose_caps.py::length_caps` — flag cap exceedances; never check vocabulary
- **Counters:** Runaway sentences and deep noun stacks.
- **Phase:** 3,4 · **Evidence:** EM Part II §3 (STE structural subset; expertise-reversal caveat on vocabulary)

#### R-PROSE-06 — Opinionated, asymmetric
`SHOULD` · `soft_critic` · *convergent_craft*  
Take positions weighted by leverage; allow asymmetric trade-off analysis (do not force pro/con parity or triadic lists).  
- **Check (critic · expertise-calibration pass):** “Does the text take a leverage-weighted position rather than over-symmetrizing or hedging? y/n”
- **PASS looks like:** 'Default to A; its one weakness, cold-start, matters only if you restart often' — a weighted call, not forced 3-pro/3-con parity.
- **Counters:** LLM over-symmetrizes (forced 3 pros / 3 cons) and hedges.
- **Phase:** 3,4 · **Evidence:** styleguide §8

<a id='vocab'></a>

### VOCAB — Vocabulary & univocity

#### R-VOCAB-01 — Terminology univocity
`MUST` · `hard_lint` · *convergent_craft* · **CORE**  
One canonical term per concept (from the concept-map); variant surface forms only as declared aliases. Define only topic-specific terms-of-art on first use; assume in-domain vocabulary per home_domain.  
- **Check (hard lint):** `checks/univocity_terms.py::canonical_terms` — flag concept references not matching canonical_term or declared aliases; flag definitions of assumed in-domain terms
- **Counters:** LLM renames the same concept three ways and over-defines basics.
- **Phase:** 4,7 · **Evidence:** EM Part II §3 (ISO 704 univocity); styleguide §9
- **Params:** home_domain

#### R-VOCAB-02 — Name and reuse handles
`SHOULD` · `soft_critic` · *convergent_craft*  
Give failure modes, patterns, and tiers short evocative names and reuse them as handles throughout.  
- **Check (critic · structure pass):** “Are recurring failure modes/patterns/tiers named and reused as consistent handles? y/n”
- **Counters:** Unnamed concepts re-explained each time.
- **Phase:** 3,4 · **Evidence:** styleguide §9,§13

<a id='expert'></a>

### EXPERT — Expertise reversal

#### R-EXPERT-01 — No worked examples in the primary layer
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
For mid_senior/staff_plus readers, the primary layer teaches by CONTRASTIVE COMPARISON (this-vs-that, home-vs-target), not step-by-step worked examples; worked examples appear only behind opt-in deeper layers, scaled by seniority_band.  
- **Check (critic · expertise-calibration pass):** “Is the primary layer free of step-by-step worked examples (above early_career), using contrast instead? y/n”
- **PASS looks like:** The API is the same three calls as any datastore; the only new part is query-by-vector — taught by contrast, no install-step walkthrough.
- **Counters:** LLM defaults to tutorial-style scaffolding (its training distribution).
- **Phase:** 3,4,7 · **Evidence:** EM Part I §5 + flag 2; Kalyuga et al. 2001b/2003
- **Params:** seniority_band

#### R-EXPERT-02 — Scaffolding behind explicit gates
`SHOULD` · `soft_critic` · *load_bearing_empirical*  
Any novice scaffolding lives behind an explicit 'if you don't have X, read Y first' gate, never on the primary surface.  
- **Check (critic · expertise-calibration pass):** “Is novice scaffolding gated behind an explicit prerequisite pointer rather than inline on the primary surface? y/n”
- **Counters:** Inline remedial explanation that experts must read past.
- **Phase:** 3,4 · **Evidence:** EM Part I §5

<a id='recall'></a>

### RECALL — Retrieval practice

#### R-RECALL-01 — Three check-yourself Q&As per section
`MUST` · `hard_lint` · *convergent_craft*  
Each section ends with exactly 3 check-yourself Q&As rendered as show-answer.  
- **Check (hard lint):** `checks/structure_coverage.py::recall_count` — exactly 3 <details> recall items per section
- **Counters:** LLM writes 0, 1, or 7 questions inconsistently.
- **Phase:** 5,7 · **Evidence:** styleguide §5; testing effect

#### R-RECALL-02 — Generation-based, calibrated recall
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
Recall questions require generation (not recognition/definition trivia), are calibrated so an attentive L1 reader answers >=2/3, and at least one forces a cross-domain mapping.  
- **Check (critic · structure pass):** “Do the 3 questions require generation (not recognition), with >=1 cross-domain-mapping question, answerable from an attentive L1 read? y/n”
- **PASS looks like:** 'At 200ms p99 on a static 2M-vector HNSW index, what is the first knob and its cost?' — generation + transfer, not 'What does HNSW stand for?'
- **Counters:** LLM writes definitional or recognition-style trivia.
- **Phase:** 5,7 · **Evidence:** EM Part I §4; Rowland 2014 g=0.50; Roediger & Karpicke 2006 d=0.83

<a id='art'></a>

### ART — Operational artifacts

#### R-ART-01 — Four operational artifacts present and distinct
`MUST` · `hard_lint` · *convergent_craft*  
Include all four, kept distinct: decision matrix, diagnostic checklist, failure-modes catalog, decision aid.  
- **Check (hard lint):** `checks/structure_coverage.py::operational_artifacts` — all four artifact types detectable and non-collapsed
- **Counters:** LLM omits some or collapses them into one table.
- **Phase:** 2,3,7 · **Evidence:** styleguide §7; EM Part I §4

#### R-ART-02 — Checklist killer-item discipline
`SHOULD` · `soft_critic` · *load_bearing_empirical*  
The diagnostic checklist holds <=9 items per pause, action-verb-first, only high-frequency-consequential failures; it is not a glossary.  
- **Check (critic · structure pass):** “Is the checklist <=9 action-verb items of high-frequency failures (not a glossary)? y/n”
- **PASS looks like:** A 6-item action-first pre-ship list of high-frequency failures, not a 30-item glossary of every consideration.
- **Counters:** Exhaustive checklists that nobody runs.
- **Phase:** 3 · **Evidence:** EM Part I §4; Gawande/WHO (36%/47% reductions)

#### R-ART-03 — Toulmin recommendation blocks
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Every recommendation, design trade-off, or superiority claim is structured as Claim / Data / Warrant / Backing / Qualifier / Rebuttal, with the Qualifier (strength/conditions) and Rebuttal (failure modes) always present.  
- **Check (critic · evidence-grounding pass):** “Does each recommendation carry an explicit qualifier (conditions/strength) and rebuttal (when it fails)? y/n”
- **PASS looks like:** 'Use hybrid when queries mix exact + semantic (qualifier); on code-like corpora BM25 alone often wins (rebuttal)' — both present.
- **Counters:** LLM gives unqualified recommendations with no failure conditions.
- **Phase:** 3,4,7 · **Evidence:** EM Part II §6; Toulmin 1958

#### R-ART-04 — Decision matrix is decisive
`SHOULD` · `soft_critic` · *convergent_craft*  
The decision matrix has named criteria, a named baseline, and a named recommendation; no 'it depends' cell without an accompanying disambiguating rule.  
- **Check (critic · structure pass):** “Does the matrix name criteria + baseline + recommendation, with every 'it depends' disambiguated? y/n”
- **PASS looks like:** Matrix names a baseline ('start with pgvector'), a recommendation per column, and replaces every 'it depends' with a rule.
- **Counters:** A grid of vague ratings with no interpretation.
- **Phase:** 3 · **Evidence:** styleguide §7

#### R-ART-05 — Uniform mechanism-survey shape
`SHOULD` · `soft_critic` · *convergent_craft*  
When surveying a family of mechanisms/algorithms, give each the same shape: input -> mechanism -> the one assumption that bites -> when to reach for it.  
- **Check (critic · structure pass):** “Do mechanism surveys follow the uniform input/mechanism/assumption/when shape? y/n”
- **Counters:** Inconsistent, non-comparable mechanism descriptions.
- **Phase:** 3,4 · **Evidence:** EM Part I §5; styleguide §10

#### R-ART-06 — Annotated further-reading
`SHOULD` · `soft_critic` · *convergent_craft*  
End with a curated further-reading list; each entry carries a one-line note on what it offers and who it is for — never a bare link dump.  
- **Check (critic · structure pass):** “Does each further-reading entry carry a one-line what-it-offers / who-it's-for note rather than a bare link? y/n”
- **PASS looks like:** 'Lewis et al. 2020 — the original RAG paper; read for the retriever-generator split, skip if you only need the production view.'
- **Counters:** LLM dumps a bare list of links with no annotation.
- **Phase:** 3 · **Evidence:** styleguide §further-reading; deep-primer Phase 5

<a id='evid'></a>

### EVID — Empirical claims & epistemic honesty

#### R-EVID-01 — Settled / contested / speculative tags
`MUST` · `soft_critic` · *convergent_craft* · **CORE**  
Tag claims by epistemic status; contested claims name >=1 dissenting view; speculation never wears the grammar of fact.  
- **Check (critic · evidence-grounding pass):** “Are non-settled claims tagged, with contested ones naming a dissenting view and speculation marked as such? y/n”
- **PASS looks like:** 'Rerankers reliably improve ordering (settled); the end-task gain is contested and dataset-dependent' — status tagged.
- **Counters:** LLM smuggles speculation as settled fact.
- **Phase:** 3,4,7 · **Evidence:** EM Part I §5 (hedging/GRADE); styleguide §10

#### R-EVID-02 — Honest-limits section
`SHOULD` · `soft_critic` · *convergent_craft*  
Include a section auditing where the primer's own thesis/framework breaks down.  
- **Check (critic · structure pass):** “Is there an honest-limits section where the thesis is shown to break down? y/n”
- **PASS looks like:** 'Where this primer is weakest: it treats retrieval and generation as separable, which breaks for end-to-end systems.'
- **Counters:** A primer that never says where it is wrong.
- **Phase:** 2,3 · **Evidence:** styleguide §10

#### R-EVID-03 — Independent corroboration over seniority
`SHOULD` · `soft_critic` · *convergent_craft*  
Weight replicated/independent findings over authority; performance claims require independent (non-vendor) corroboration.  
- **Check (critic · evidence-grounding pass):** “Are performance claims corroborated by >=1 independent non-vendor source, not just the vendor? y/n”
- **Counters:** LLM repeats vendor benchmarks as established fact.
- **Phase:** 1,6 · **Evidence:** styleguide §10; user vendor-skepticism

<a id='ground'></a>

### GROUND — Anti-hallucination / citation grounding

#### R-GROUND-01 — No fabricated evidence (integrity floor)
`MUST` · `hard_lint` · *load_bearing_empirical* · **CORE**  
Every empirical claim, number, citation, or effect size MUST resolve to a source-ledger entry. Never fabricate a citation, statistic, or effect size. A believed-but-unsourced claim is marked 'unverified', never given false precision.  
- **Check (hard lint):** `verify/citation_quality.py::resolves_to_ledger` — every citation marker maps to a ledger source_id; unresolved numeric/cited claims fail
- **Counters:** LLM invents 'd=0.84 (Smith 2019)' from nothing.
- **Phase:** 6 · **Evidence:** EM Addendum §A (ALCE); Part II §8 (misattribution debunk)

#### R-GROUND-02 — Citation recall
`MUST` · `model_verified` · *load_bearing_empirical*  
Every factual statement has at least one supporting citation into the ledger (ALCE citation recall).  
- **Check (model-verified):** `verify/citation_quality.py::recall` — model identifies factual statements, then checks each has >=1 supporting citation; threshold set in eval
- **Counters:** Unsupported assertions presented as fact.
- **Phase:** 6 · **Evidence:** EM Addendum §A (ALCE; Gao et al. 2023)

#### R-GROUND-03 — Citation precision
`MUST` · `model_verified` · *load_bearing_empirical*  
Each cited source actually supports the statement it is attached to; remove irrelevant or non-supporting citations (ALCE citation precision).  
- **Check (model-verified):** `verify/citation_quality.py::precision` — entailment check (NLI/MiniCheck or scoped Claude) that the cited quote supports the claim
- **Counters:** Decorative citations that don't support the claim.
- **Phase:** 6 · **Evidence:** EM Addendum §A (ALCE)

#### R-GROUND-04 — Recency / version freshness
`SHOULD` · `hard_lint` · *engineering*  
Named technologies/libraries/models carry current versions; flag any version reference older than its freshness TTL.  
- **Check (hard lint):** `checks/recency_versions.py::version_freshness` — extract named tech -> compare to live version -> flag stale
- **Counters:** Stale version references (recurring failure).
- **Phase:** 1,6 · **Evidence:** research phase 1e

<a id='fig'></a>

### FIG — Figures & diagrams

#### R-FIG-01 — Complete-claim captions
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
Every figure caption states the figure's conclusion as a complete sentence, not a label.  
- **Check (critic · figures pass):** “Does each caption state the figure's conclusion (a claim), not just name it? y/n”
- **PASS looks like:** 'Figure 4: ingestion is parallel up to the embed step, the throughput bottleneck' — a conclusion, not 'Figure 4: the pipeline.'
- **Counters:** LLM writes 'Figure 3: architecture'.
- **Phase:** 5,7 · **Evidence:** EM Part I §3,§5 (Schriver: captions read first)

#### R-FIG-02 — One emphasis, shared vocabulary
`SHOULD` · `soft_critic` · *convergent_craft*  
Each figure emphasizes exactly one component (the most important / safety-critical) and reuses a shared visual vocabulary (outlined / light-filled / solid-filled boxes; solid / dashed arrows).  
- **Check (critic · figures pass):** “Is exactly one element emphasized, using the shared box/arrow vocabulary? y/n”
- **PASS looks like:** One box outlined as the safety-critical component, shared box/arrow vocabulary across figures — not every node bolded.
- **Counters:** Everything emphasized (so nothing is); ad hoc visual style per figure.
- **Phase:** 5 · **Evidence:** styleguide §12; Tufte

#### R-FIG-03 — Spatial contiguity
`SHOULD` · `soft_critic` · *load_bearing_empirical*  
Place each label adjacent to the graphic element it describes; if separation is unavoidable, replicate the key label inline. No split attention.  
- **Check (critic · figures pass):** “Are labels adjacent to their referents (no split attention)? y/n”
- **Counters:** Legend-far-from-data layouts.
- **Phase:** 5 · **Evidence:** EM Part I §5 / Part III §D; Ginns 2006 spatial-contiguity meta-analysis d≈0.72 (combined ~0.85); Schroeder & Cenkci 2018 g≈0.63; up to d≈1.10 in Mayer's lab on complex materials

#### R-FIG-04 — Figure accessibility
`SHOULD` · `hard_lint` · *engineering*  
Every figure carries aria-label + role=img + a standalone figcaption.  
- **Check (hard lint):** `utils/parse_primer.py::figure_a11y` — each <svg>/figure has aria-label, role=img, figcaption
- **Counters:** Inaccessible figures with no text alternative.
- **Phase:** 5,7 · **Evidence:** styleguide §12

#### R-FIG-05 — Small multiples for comparison
`MAY` · `soft_critic` · *convergent_craft*  
Render comparisons as small-multiple tables/charts sharing one structure, not a single composite figure.  
- **Check (critic · figures pass):** “Are comparisons shown as small multiples rather than one overloaded composite? y/n”
- **Counters:** Overloaded composite comparison figures.
- **Phase:** 5 · **Evidence:** EM Part I §5; Tufte

<a id='xref'></a>

### XREF — Cross-domain mapping & cross-referencing

#### R-XREF-01 — Cross-domain mapping lives in the card
`MUST` · `soft_critic` · *load_bearing_empirical* · **CORE**  
Where a home-domain analogue exists, it appears in the L1 card's opening sentence, not buried in a footnote or aside.  
- **Check (critic · structure pass):** “Is the home-domain mapping in the card's opening (L1), not below it? y/n”
- **PASS looks like:** The home-domain analogue is the card's first sentence, not a 'see footnote 7' aside.
- **Counters:** LLM relegates the highest-yield analogy to a 'see also'.
- **Phase:** 3,4 · **Evidence:** EM Part I §5 + flag 3; Gentner; fuzzy-trace; advance organizer
- **Params:** home_domain

#### R-XREF-02 — References resolve; nav/TOC in sync
`MUST` · `hard_lint` · *engineering*  
Every internal cross-reference resolves; nav and TOC are in sync with headings; no phantom references to figures/tables ('as shown below').  
- **Check (hard lint):** `checks/xrefs.py::xrefs_resolve` — all anchors resolve; nav/TOC == headings; no phantom figure/table refs
- **Counters:** LLM emits broken refs and phantom 'see Figure X' pointers.
- **Phase:** 7 · **Evidence:** styleguide §11,§14; deep-primer Phase 4 self-check

#### R-XREF-03 — Edges realized as cross-references
`SHOULD` · `soft_critic` · *convergent_craft*  
Important concept-map relations are realized as cross-references in prose, so the document reads as a navigable web.  
- **Check (critic · structure pass):** “Are the key concept relationships surfaced as cross-references rather than left implicit? y/n”
- **Counters:** Linear document that ignores conceptual dependencies.
- **Phase:** 4 · **Evidence:** styleguide §11

<a id='proj'></a>

### PROJ — IR-first & projections

#### R-PROJ-01 — IR is canonical
`MUST` · `human` · *engineering*  
Drafting emits the structured document IR; the HTML and the distilled LLM-MD are both rendered FROM it and are never hand-edited. The IR is the single source of truth; lints and critics read the IR.  
- **Check (human):** both projections are render outputs of the same document-ir; no manual edits to rendered artifacts
- **Counters:** Editing the HTML directly, so the two artifacts and the IR drift.
- **Phase:** 3,8 · **Evidence:** artifact-schemas.md (Document IR); design decision (IR-first)

#### R-PROJ-02 — Block-id alignment across projections
`MUST` · `hard_lint` · *engineering*  
Every block_id emitted in the LLM-MD exists in the HTML and vice versa, except blocks intentionally removed by the role filter; a citation by block_id resolves in either artifact.  
- **Check (hard lint):** `render/check_alignment.py::check_alignment` — set(md block_ids) subset of set(html block_ids); the diff is exactly the role-filtered roles
- **Counters:** Renderers assign different ids, breaking cross-artifact traceability.
- **Phase:** 8 · **Evidence:** artifact-schemas.md (Projections); design decision (align by block-id)

#### R-PROJ-03 — LLM-MD is operationally distilled
`SHOULD` · `hard_lint` · *convergent_craft*  
The LLM-MD keeps the operational core (claims, Toulmin recommendations, decision matrix, figure captions, glossary, annotated further-reading) and drops pedagogical apparatus (recall questions; the advance-organizer hook framing of cards).  
- **Check (hard lint):** `render/render_llm_md.py::role_filter` — no role=recall blocks in md; cards reduced to their information content
- **Counters:** Shipping the human pedagogy verbatim as the LLM context source.
- **Phase:** 8 · **Evidence:** design decision (operationally distilled); EM Part I §2 (minimalism)

#### R-PROJ-04 — LLM-MD chunks are self-contained
`MUST` · `model_verified` · *convergent_craft*  
Each LLM-MD block stands alone when retrieved: referents restated, no cross-block anaphora ('as above'); cross-chunk minimalism is suspended while within-chunk minimalism is kept. Each rewritten block must still entail its source claim_ids.  
- **Check (model-verified):** `verify/chunk_selfcontained.py::entailment` — no dangling anaphora; rewritten block entails its claim_ids (NLI/MiniCheck or scoped Claude)
- **Counters:** Given->new flow (R-PROSE-01) leaves a chunk leaning on its neighbors, useless when retrieved alone.
- **Phase:** 8 · **Evidence:** EM Addendum §A (attributable generation); artifact-schemas.md (Projections)

#### R-PROJ-05 — Provenance surfaced inline
`SHOULD` · `hard_lint` · *convergent_craft*  
Every claim block carries a provenance tag (verified | inferred | unverified) and its source_ids, surfaced inline in BOTH projections; version/SOTA claims are flagged verified-against-source vs inferred.  
- **Check (hard lint):** `checks/provenance.py::tagged` — every block with claim_ids has a provenance value; verified implies >=1 source_id
- **Counters:** The reader/LLM cannot tell a web-verified claim from a training-recalled one (dry-run gap G4).
- **Phase:** 6,8 · **Evidence:** dry-run finding G4; EM Addendum §A

#### R-PROJ-06 — LLM-MD drops SVG, keeps captions
`SHOULD` · `hard_lint` · *engineering*  
The LLM-MD omits SVG/figure markup and keeps each figure's complete-claim caption as text.  
- **Check (hard lint):** `render/render_llm_md.py::no_svg` — no <svg> in md; each figure's figcaption present as text
- **Counters:** SVG XML as token-noise in an LLM context source.
- **Phase:** 8 · **Evidence:** design decision (modality); R-FIG-01 (captions are complete claims)

<a id='consist'></a>

### CONSIST — Consistency & build invariants

#### R-CONSIST-01 — 1:1 field-guide coverage
`MUST` · `hard_lint` · *engineering*  
Every section has lede + card + recall, and every h3 has exactly one sub-sum; a section summary is required only when the section body exceeds the length threshold (~400 words), so thin sections stay lean (see R-DEPTH-03).  
- **Check (hard lint):** `checks/structure_coverage.py::layer_coverage` — per-section lede+card+recall present; h3:sub_sum == 1:1; section_summary present iff body_words > 400
- **Counters:** Sections missing a required layer; or a full summary manufactured for a thin section (padding).
- **Phase:** 7 · **Evidence:** styleguide §14; reconciled with R-DEPTH-03

#### R-CONSIST-02 — Stable block IDs + embedded metadata
`MUST` · `hard_lint` · *engineering*  
Every section/subsection/card/figure carries a stable data-block-id; the HTML embeds a primer-meta JSON (parameters, frozen ledger snapshot, concept-map, lint report).  
- **Check (hard lint):** `utils/parse_primer.py::block_ids_and_meta` — block_ids present and unique; primer-meta JSON parseable and complete
- **Counters:** Whole-document regeneration on revision (no targetable blocks); non-reproducible output.
- **Phase:** 3,7 · **Evidence:** V1 plan (block-scoped revision; reproducibility snapshot)

#### R-CONSIST-03 — Footnotes balanced
`SHOULD` · `hard_lint` · *engineering*  
Every footnote marker has a matching definition and vice versa.  
- **Check (hard lint):** `checks/footnote.py::footnote_balance` — markers == definitions
- **Counters:** Dangling or orphaned footnotes.
- **Phase:** 7 · **Evidence:** styleguide §14

<a id='reject'></a>

### REJECT — Anti-rules / do-not-adopt

#### R-REJECT-01 — Do not adopt E-Prime
`MUST_NOT` · `human` · *contested*  
Do not impose E-Prime (elimination of 'to be') as a writing constraint.  
- **Check (human):** no E-Prime constraint in generator/critic prompts
- **Counters:** Importing an over-extended general-semantics rule with no comprehension evidence.
- **Phase:** — · **Evidence:** EM Part II §8 (no evidence; '4-16x compression' is a misattribution)

#### R-REJECT-02 — UID is diagnostic only
`MUST_NOT` · `human` · *contested*  
Do not use language-model surprisal smoothing as an editing target; surprisal spikes are a diagnostic heuristic for human review only.  
- **Check (human):** no surprisal-smoothing rewrite step in the pipeline
- **Counters:** Mistaking a production-side psycholinguistic theory for a reading intervention.
- **Phase:** — · **Evidence:** EM Part II §5

#### R-REJECT-03 — No strict MECE gate
`MUST_NOT` · `human` · *contested*  
Do not enforce strict MECE partitioning as a quality gate; use it only as a framing heuristic.  
- **Check (human):** no MECE-partition gate in lints/critics
- **Counters:** Forcing artificial non-overlap on conceptual material.
- **Phase:** — · **Evidence:** EM Part II §2

#### R-REJECT-04 — No RST auto-rendering
`MUST_NOT` · `human` · *contested*  
Do not auto-collapse or restructure content from RST parser output; RST is a soft signal only (parser accuracy ~= human agreement floor).  
- **Check (human):** no rendering decision gated on an RST parse
- **Counters:** Driving deterministic UI from an unreliable discourse parse.
- **Phase:** — · **Evidence:** EM Part II §1 (SOTA ~57 F1 vs ~55 F1 human IAA)

#### R-REJECT-05 — Critics never score holistic quality
`MUST_NOT` · `human` · *load_bearing_empirical*  
Critic prompts MUST ask binary single-criterion compliance questions only; never 'is this good / thorough / high-quality?'. This is the primary guard against verbosity and self-preference (family) bias in an all-Claude judge.  
- **Check (human):** every critic-prompt question is binary and single-criterion; swap-and-average on any pairwise call; gating calls run >=2x
- **Counters:** Holistic LLM-judge scoring rewards length (verbosity bias) and Claude-judging-Claude self-preference, undermining minimalism.
- **Phase:** 7 · **Evidence:** EM Addendum §D (LLM-as-judge bias: position/verbosity/family; swap-and-average; >25% divergence -> recalibrate)
