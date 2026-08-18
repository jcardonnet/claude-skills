# GAPS.md — open contract gaps from the dry run

These surfaced when the pipeline was traced against a hard prompt (a practitioner primer on reading callout/leader-line figures and segmenting exploded-view parts catalogues; reference case = a ~80-callout binary exploded view; thesis = anchors seed segmentation, masks may be unnecessary). `spec-02-callout-extraction.yaml` keeps this case live.

Apply any fix via the registry + `bash tools/build.sh` — **never** by hand-editing generated files.

| # | Gap | Status | Action |
|---|-----|--------|--------|
| **G1** | `home ≈ target`: reader already lives in the target domain, so the cross-domain bridge metaphor degenerates. | **RESOLVED** | New `R-XREF-04`: `home_anchor` resolves to the nearest adjacent *technique/sub-field*, with a deterministic companion lint (`home_anchor_distinct`) catching self-restatement; `research-perspectives.md` re-aims bridge-builder at prior-art transfer. |
| **G2** | `R-EXPERT-01` (suppress worked examples) collides with mandatory reference-case grounding. | **RESOLVED** | `R-EXPERT-01` narrowed to *procedural* walkthroughs; new `R-EXPERT-03` (running reference case) plus a `reference_case` parameter make the anchor first-class and explicitly not-suppressed. |
| **G3** | No consumer/dual-purpose knob (human reading vs LLM grounding). | **RESOLVED** | Became the dual-output decision: `outputs` param + `R-PROJ-01..06` (IR-first, two projections). |
| **G4** | Verified-vs-inferred provenance not surfaced. | **RESOLVED** | `R-PROJ-05` — provenance (`verified`/`inferred`/`unverified`) + `source_ids` printed inline in both projections; `provenance` axis added to the IR. |
| **G5** | Competing-school perspective is singular, but the case is a 4-way method bake-off. | **MINOR** | Instantiate the competing-schools perspective per method family in `planner.py` (Prompt 6); no rule change needed. |
| **G6** | User-specified section structure vs the derived outline. | **RESOLVED** | New `R-ARCH-07` + `user_structure` parameter + `Section.maps_to`: the user's structure governs top-level coverage and order, while headings stay predictive claims (the mapping is declared, not inferred, so R-SCENT-01 does not collide). |
| **G7** | `budget_weight` defaults read as prescriptive; this prompt inverts them (historian/bridge-builder high). | **MINOR (wording)** | Document defaults as *re-weightable priors* in `research-perspectives.md`; `planner.py` accepts overrides. |
| **G8** | Phase-1 research is the quality ceiling and the one thing a dry run cannot exercise. | **SCOPE NOTE** | Validate for real in Prompt 6/7 on `spec-01`/`spec-02`; the eval harness is where this gets measured. |
| **G9** | The domain's own figures are copyrighted. | **RESOLVED** | SKILL rendering rule: never fetch source-domain figures; draw synthetic SVG. |
| **G10** | `R-DISC-02` required "**each** discovery wave runs >= MIN_FRAMINGS (5) briefs spanning distinct cells … with >=1 orthogonal framing **per wave**", but `WAVE_ARCHETYPES` gives wave B three archetypes (**two** once `B-seed` skips without a seed) and wave C three — so every campaign ever run violated a MUST. | **RESOLVED** | Scoped to the **breadth wave (A)**. Three artifacts said the floor was about wave A: `MIN_FRAMINGS`' own comment ("Wave A breadth"), `references/discovery-brief-templates.md` (which makes B and C deliberately *narrow* follow-ups, and which `BRIEF_ARCHETYPES` is pinned to), and — decisively — the rule's own `counters`: *"cosmetically-different briefs pay Nx tokens for 1x recall"* is an argument about the broad sweep, where decorrelating the ensemble is the whole job. Forcing five cells onto a targeted follow-up would MANUFACTURE that padding. What every wave still owes is **distinctness** — duplicate cells are cosmetic in any wave — plus a `framing_cells` count matching the manifest. Directive, check, planner comment and test all updated in step; the real spec-02 campaign now passes R-DISC-02 clean. |

| **G11** | **`eval.py --strict` is RED.** The gate only ever consulted `expect.must_pass` — a spec's curated list of rules it wants exercised, six for spec-01 — never the registry's MUST set, so a critic MUST failure outside that list was invisible to every gate. Wiring it surfaced two on the reference artifact, both judged by **sonnet** on the gating tier and therefore not haiku variance: **R-ARCH-01** (the primer opens on a claim; there is no scope-and-decisions block) and **R-EVID-01** (`aid-reranking` and `fig-reranking` state precise thresholds — recall@k 0.8, 100 candidates — as flat fact under `Sources: [none yet — inferred]`, with no epistemic tag). | **OPEN — needs a spend decision** | Both are real, and both are fixable in the artifact, which is what `eval-rubric.yaml` instructs: *"fix the artifacts, do not lower the bar"*. The catch is circular — editing the IR moves its digest and stales `critic-report.full.json`, dropping `soft_critic` 35 → 2 and failing the coverage ratchet — so the artifact fix and a re-judge (`run_critics.py <ir> --judge claude --gating-model sonnet`, ~113 calls, ~$18-equivalent, ~50 min — subscription quota, not a bill) have to land together. Per-row `row_claims` attribution for spec-01's two cards belongs in the same pass, for the same reason. The gate is deliberately left red rather than widened. A haiku-only report reports `must_failed` and does **not** block, on the same principle that keeps the lexical proxy out of the citation gate: only gate on a measurement worth trusting. |

| **G12** | **The frozen critic report is STALE, and the 79/79 coverage figure rested on it.** `critic-report.full.json` was judged against `document-ir.full.yaml` as of `49764e0` — identified by matching its original byte-stamp `e114186cc80d`. `f80ff65` then relabelled `matrix-chunking`, `body-chunk-size` and `toulmin-reranking` from `verified` to `inferred`, and kept the report credited by making the staleness digest blind to provenance, on the stated grounds that this was "a grounding correction the critics cannot see". **They can see it**: `_judge_document_view` builds the document unit from `render_llm_md`, which prints `provenance:` into every block heading, so three lines of the surface every document-level critic reads are different — and provenance is exactly what R-EVID-01 judges. With the digest keyed on the real judged surface and stamped to the document actually judged, the guard reports `stale`: **soft_critic 2/35, total coverage 46/79.** | **OPEN — same remedy as G11** | Not fixable by re-stamping; that is what produced the problem, twice. It needs a re-judge, which is the same ~113-call run G11 already requires — so the artifact fix (R-ARCH-01, R-EVID-01), the `row_claims` attribution, and this all land in ONE pass and one digest move. The `coverage_floor` stays at 35: lowering it to match a stale report is precisely the silent erosion the ratchet exists to catch. Until then `soft_critic` is short by 33 and the gate is red, which is the honest reading — those 33 rules were being credited from a judged run of a different document. |

**Status:** **G1, G2 and G6 applied** — G2 in Stage A, G1 and G6 as a registry step ahead of Stage C
(see `PLAN.md`). **G10 is RESOLVED** (opened when the discovery checks were first dispatched, closed by
scoping the framing floor to the breadth wave — see §8 of `HANDOFF.md`). **G11 and G12 are the OPEN gaps**, and they are
one spend decision, not two engineering problems — a single re-judge clears both. G5/G7 stay wording/implementation notes
handled in `planner.py` without rule changes, and G8 (Phase-1 research quality) is validated by the
eval harness rather than by a rule.

> **Note on the cost figure — a correction.** An earlier revision of this note claimed the committed
> report's `calls: 113, spend_usd: 17.85` was double the truth. **It is not.** That report was
> produced at `97ab26e`, where each `ClaudeCliJudge` owned an independent `ClaudeCli` carrying its
> own `spend_usd`/`calls`, so summing the two was correct then. The shared `Budget` arrived four
> commits later at `976db04`. The stamp is a true total, and `113` being ODD settles it on its own —
> a double count is `n + n`, always even.
>
> The double-count window was `976db04..abf363c` and no report was generated inside it. The code fix
> at `run_critics.main` (read the shared `Budget` once instead of summing both judges) is correct
> and stays; only the claim about the committed report was wrong.
>
> **The re-judge is ~$18-equivalent, not ~$9.** On a Claude MAX subscription that is not a bill —
> `claude -p` authenticates by OAuth and draws on subscription quota, and `total_cost_usd` is a
> notional API-equivalent. The binding constraint is rate limit, not money, which is why the
> per-call preamble saving below matters more than the dollar figure.
