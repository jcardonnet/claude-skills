# Research Perspectives — Phase 1 companion

The companion to the Phase 1 research arc in `SKILL.md`. Research quality is the primer's quality
ceiling, and the way to research well is **perspective-guided question asking with iterative
follow-ups** (the STORM result, specialized here for expert technical primers).

## The principle
Perspectives are not arbitrary personas — they are **the lenses the primer must fill anyway**. Each
perspective feeds specific sections and operational artifacts, so research coverage maps one-to-one
onto section coverage. Research a topic by instantiating each perspective's seed questions against
the topic's concepts, then deepening with follow-ups until the coverage signal is met.

A perspective **earns its place by feeding a section or artifact.** Drop one whose section the topic
doesn't need (e.g. standards/compliance for a topic with no regulatory dimension); add a
domain-specific one only when the topic demands a lens these six don't cover.

---

## How the planner uses this
1. **Select** the relevant perspectives for the topic (all six core ones by default; the conditional one only when applicable).
2. **Instantiate** each perspective's seed questions with the topic's concepts → write `research-plan.yaml` (schema in `artifact-schemas.md`).
3. **Deduplicate before retrieving.** Skeptic and practitioner (and others) will generate near-identical sub-questions; merge them into one question (record the folded ids in `merged_from`) so the retrieval loop doesn't search the same thing twice — this is the single biggest source of wasted retrieval.
4. **Weight the budget by perspective.** Perspectives are not equal-yield: bridge-builder and practitioner usually repay more retrieval than historian or forecaster on fast-moving topics. Set `budget_weight` per question accordingly; spend `max_retrieval_iterations` proportionally rather than uniformly.
5. **Retrieve iteratively** per question. Follow-ups arise from answers: when an answer reveals a new sub-question or a gap, add it — STORM's simulated-conversation mechanism — bounded by `max_retrieval_iterations`.
6. **Track coverage** per question against its coverage signal and the budgets (`min_sources_per_question`; `min_independent_nonvendor_sources_for_perf_claim` for any performance claim). Coverage is a model self-assessment, so keep it paired with the hard source count rather than trusting the judgment alone.
7. **Stop** a question when its coverage signal is met or the iteration cap is hit; if the cap is hit first, mark it `thin` so the primer can flag that area as under-supported rather than fabricate to fill it.

All question text uses placeholders the planner fills: `{target_domain}`, `{home_domain}`,
`{concept}`, `{approach}`, `{rival}`, `{task}`.

---

## The perspectives

### bridge-builder — map the target back to what the reader knows
- **Feeds:** conceptual foundations; cross-domain connections; every card's anchor row.
- **Serves:** `R-CARD-01`, `R-XREF-01`, `R-MV-01` (the home-domain-analogue representation mode).
- **Seed questions:**
  - What is `{concept}` in `{target_domain}`, and what is its closest precise analogue in `{home_domain}`?
  - Which `{home_domain}` intuitions transfer to `{concept}`, and at exactly what point does the analogy break (the **fidelity boundary**)?
  - What in `{target_domain}` is genuinely new versus merely a renamed `{home_domain}` idea?
  - Which `{home_domain}` tools/techniques have direct counterparts here, and which have none?
- **Coverage signal:** every core concept has a stated home-domain anchor **and** a stated fidelity boundary.
- **Where to look:** foundational papers for the precise definition; canonical `{home_domain}` references to anchor the analogy accurately — never invent the mapping.

### practitioner — what teams actually do, and what breaks
- **Feeds:** current landscape; decision matrix; decision aid; cost discussion.
- **Serves:** `R-ART-01`, `R-ART-04`, `R-PROSE-02` (cost-named trade-offs), `R-EVID-03`.
- **Seed questions:**
  - What do production teams actually use for `{task}` today, and what is the de facto default?
  - What breaks when `{approach}` is taken to scale / sustained load / long-running operation?
  - What are the real operational costs — latency, dollars, infra, ops burden, failure recovery?
  - When do practitioners deviate from the default, and what triggers the switch?
  - Where does the paper/benchmark result diverge from production behavior?
- **Coverage signal:** a named default + named deviation-triggers + ≥1 production-cost dimension per major option.
- **Where to look:** engineering blogs from teams who built it, postmortems, conference talks; treat vendor benchmarks skeptically (`R-EVID-03`).

### skeptic — failure modes, overclaims, limits
- **Feeds:** pitfalls / anti-patterns; failure-modes catalog; honest-limits section; epistemic tags.
- **Serves:** `R-ART-02`, `R-EVID-01`, `R-EVID-02`, `R-GROUND-01..03`.
- **Seed questions:**
  - What are the documented failure modes of `{approach}`, and how frequently / consequentially do they bite?
  - What looks good in demos but breaks in practice?
  - Which widely-repeated claims about `{concept}` are unreplicated, vendor-sourced, or overstated?
  - Where does the dominant approach's own thesis break down — what can it not do?
  - What is the strongest published critique of `{approach}`?
- **Coverage signal:** ≥N named failure modes with frequency/consequence; ≥1 explicit limit of the dominant thesis; every "X is better" claim either independently corroborated or tagged contested.
- **Where to look:** critique papers, ablation studies, incident reports; favor reproductions over single results.

### historian — lineage and what was tried before
- **Feeds:** historical arc; the rediscovered-ideas thread.
- **Serves:** `R-MV-01` (historical-analogue mode); the cross-domain narrative.
- **Seed questions:**
  - What problem drove the emergence of `{approach}`, and what did it replace?
  - What was tried before `{approach}` and abandoned — and why (what changed to make the new thing work)?
  - Which older ideas in this lineage are being rediscovered or re-applied now?
  - What is the citation lineage of `{concept}` back to its origin?
- **Coverage signal:** a narrative (not a timeline dump) explaining *why* each major shift happened; ≥1 older/rediscovered idea surfaced.
- **Where to look:** seminal/origin papers, retrospectives, survey "related work" sections, citation chains.

### competing-school — the rival case and genuine disagreement
- **Feeds:** trade-offs / decision framework; contested tags; decision matrix.
- **Serves:** `R-EVID-01`, `R-PROSE-06` (leverage-weighted positions), `R-PROSE-02`.
- **Seed questions:**
  - What would a proponent of `{rival}` argue against `{approach}`, in its strongest form?
  - Where is there genuine, unresolved disagreement among experts about `{concept}`?
  - What does each camp optimize for, and what does each sacrifice?
  - On what does the disagreement turn — different benchmarks, definitions, or contexts?
- **Coverage signal:** each major contested point has both sides stated at their strongest, with the basis of disagreement named.
- **Where to look:** position papers from each camp, comparative studies, debate among credible practitioners. Steelman, never strawman.

### forecaster — where the field is heading
- **Feeds:** where-the-field-is-heading; open problems.
- **Serves:** `R-EVID-01` (separate trajectory from speculation); the recency sweep.
- **Seed questions:**
  - What is the credible near-term trajectory for `{target_domain}` (next 6–18 months)?
  - What are the salient open problems / unsolved bottlenecks?
  - Which emerging directions have real traction (adoption, results) versus hype?
  - What work from the last 60 days signals a shift?
- **Coverage signal:** near-term trajectory separated from speculative bets, each tagged; recency sweep satisfied.
- **Where to look:** recent preprints, roadmaps, well-reasoned forward-looking pieces; mark speculation as speculation (`R-EVID-01`).

### standards / compliance — *conditional*
Include **only** where `{target_domain}` has a regulatory, standards, or safety-critical dimension.
- **Feeds:** a constraints/compliance treatment; safety gates in the decision aid.
- **Serves:** domain-specific safety/constraint rules.
- **Seed questions:**
  - What standards/regulations govern `{target_domain}`, and which are mandatory versus advisory?
  - What are the safety-critical constraints, and what are the consequences of violating them?
  - What does compliant practice require that naive practice misses?
- **Coverage signal:** governing standards named with mandatory/advisory status; safety-critical constraints enumerated.
- **Where to look:** standards bodies, regulatory texts, official compliance guidance — primary sources only.

---

## Cross-cutting passes (part of Phase 1, not perspectives)
- **Recency / version sweep** (`R-GROUND-04`): for every named technology/library/model, pin the current version; covered when no stale reference remains.
- **Conflict detection:** contradictions across sources become a `contested` tag carrying both positions and the basis of disagreement (`R-EVID-01`).
- **Fidelity-boundary discipline:** every cross-domain analogy must state where it breaks. The bridge-builder owns this, but it is a global requirement — an analogy with no stated boundary is an incomplete claim.

---

## Output contract
The planner emits **`research-plan.yaml`**; the retrieval loop fills `coverage`; downstream it feeds
`source-ledger.yaml` (atomic claims) and `concept-map.yaml` (concept clusters). The schema for all
three — plus `primer-meta` and the block-attribute contract — lives in **`artifact-schemas.md`**
(single source, so it can't drift from this file). The `research-plan.yaml` schema there now carries
`budget_weight` and `merged_from` for the weighting and dedup steps above.
