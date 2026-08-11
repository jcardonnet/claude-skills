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

**Status:** **G1, G2 and G6 applied** — G2 in Stage A, G1 and G6 as a registry step ahead of Stage C
(see `PLAN.md`). No gap remains OPEN; G5/G7 stay wording/implementation notes handled in `planner.py`
without rule changes, and G8 (Phase-1 research quality) is validated by the eval harness rather than
by a rule.
