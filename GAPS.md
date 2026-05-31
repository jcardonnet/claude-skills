# GAPS.md — open contract gaps from the dry run

These surfaced when the pipeline was traced against a hard prompt (a practitioner primer on reading callout/leader-line figures and segmenting exploded-view parts catalogues; reference case = a ~80-callout binary exploded view; thesis = anchors seed segmentation, masks may be unnecessary). `spec-02-callout-extraction.yaml` keeps this case live.

Apply any fix via the registry + `bash tools/build.sh` — **never** by hand-editing generated files.

| # | Gap | Status | Action |
|---|-----|--------|--------|
| **G1** | `home ≈ target`: reader already lives in the target domain, so the cross-domain bridge metaphor degenerates. | **OPEN** | Reinterpret `home_anchor` as the nearest adjacent *technique/sub-field*; the bridge-builder perspective becomes prior-art transfer. Decide before Prompt 6. |
| **G2** | `R-EXPERT-01` (suppress worked examples) collides with mandatory reference-case grounding. | **OPEN — recommend APPLY** | Narrow `R-EXPERT-01` to *procedural* walkthroughs; add a running **reference-case** affordance so "ground every claim against the reference drawing" is not suppressed. |
| **G3** | No consumer/dual-purpose knob (human reading vs LLM grounding). | **RESOLVED** | Became the dual-output decision: `outputs` param + `R-PROJ-01..06` (IR-first, two projections). |
| **G4** | Verified-vs-inferred provenance not surfaced. | **RESOLVED** | `R-PROJ-05` — provenance (`verified`/`inferred`/`unverified`) + `source_ids` printed inline in both projections; `provenance` axis added to the IR. |
| **G5** | Competing-school perspective is singular, but the case is a 4-way method bake-off. | **MINOR** | Instantiate the competing-schools perspective per method family in `planner.py` (Prompt 6); no rule change needed. |
| **G6** | User-specified section structure vs the derived outline. | **OPEN** | Make an explicit user structure authoritative; the derived outline maps onto it (concept-map still drives within-section depth). Decide before Prompt 4/6. |
| **G7** | `budget_weight` defaults read as prescriptive; this prompt inverts them (historian/bridge-builder high). | **MINOR (wording)** | Document defaults as *re-weightable priors* in `research-perspectives.md`; `planner.py` accepts overrides. |
| **G8** | Phase-1 research is the quality ceiling and the one thing a dry run cannot exercise. | **SCOPE NOTE** | Validate for real in Prompt 6/7 on `spec-01`/`spec-02`; the eval harness is where this gets measured. |
| **G9** | The domain's own figures are copyrighted. | **RESOLVED** | SKILL rendering rule: never fetch source-domain figures; draw synthetic SVG. |

**Recommended now:** apply **G2**. Defer G1/G6 to an explicit decision at Prompt 4/6 (both are small registry edits). G5/G7 are handled in `planner.py` without rule changes.
