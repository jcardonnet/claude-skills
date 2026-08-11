# PLAN.md — implementing the pending deep-primer work

Refines and re-sequences the remainder of `CLAUDE_CODE_PROMPTS.md`. It **inserts a new Stage A
(“Prompt 2b”)** that the original prompt list does not contain, then runs Prompts 6a → 6 → 6b → 7 → 8.
Standing rules still apply: **lockstep** (edit `rule-registry.yaml`, run `bash tools/build.sh`, never
hand-edit generated files) and **IR-first** (lints and critics read the IR; HTML and LLM-MD are
projections). Paths are relative to `skills/deep-primer/` unless noted.

---

## Context — why this plan exists

The repo state is ahead of its own documentation: Prompts 0–5 and most of Prompt 8 are implemented
(81 tests pass, `make build` is idempotent, `bundle.py` is real), while `CLAUDE.md` and `README.md`
still describe `scripts/` as stubs.

More consequentially, **Prompt 2's lint layer is only partly wired.** Running the linter against the
fixture IR shows nine checks reporting `skip` — six of them MUST — plus a tenth that is never
dispatched at all:

```
$ python scripts/lint.py tests/fixtures/document-ir.yaml \
      --concept-map tests/fixtures/concept-map.yaml --ledger tests/fixtures/source-ledger.yaml
BLOCKING — fail=2 warn=3 pass=9 skip=9
```

| Rule | Priority | Check ref | Why it doesn't run |
|---|---|---|---|
| `R-PARAM-01` | MUST | `structure_coverage.py::params_present` | not implemented |
| `R-ARCH-05` | MUST | `structure_coverage.py::heading_hierarchy` | IR has no subsection level |
| `R-CARD-02` | MUST | `structure_coverage.py::card_rows` | card is free text, no typed rows |
| `R-RECALL-01` | MUST | `structure_coverage.py::recall_count` | recall is one block, not three items |
| `R-ART-01` | MUST | `structure_coverage.py::operational_artifacts` | no artifact typing on blocks |
| `R-GROUND-01` | MUST | `citation_quality.py::resolves_to_ledger` | implemented, but not wired into a pass |
| `R-SUMM-02` | SHOULD | `structure_coverage.py::summary_budgets` | needs h3 ↔ sub-sum pairing |
| `R-DEPTH-02` | SHOULD | `parse_primer.py::depth_dial_present` | not implemented; mis-tagged as `input: ir` |
| `R-FIG-04` | SHOULD | `parse_primer.py::figure_a11y` | not implemented; mis-tagged as `input: ir` |
| `R-SCENT-01` | MUST | `structure_coverage.py::banned_heading_terms` | `also_hard_lint` companions are never dispatched |

Two root causes, not ten:

1. **The V1 IR under-models the field-guide layer the registry assumes.** `Section.blocks` is a flat
   list — there is no h3 subsection, no typed card row, no three-item recall, no distinction among the
   four operational artifacts. `structure_coverage.py`'s docstring defers these to "Prompt 4 or a later
   IR extension"; Prompt 4 shipped without picking them up, so the deferral has no owner.
2. **Nothing dispatches non-IR checks.** `lint.py::_ir_hard` correctly scopes the IR pass (per
   `RECONCILE.md`), but the ten rules tagged `input: html | projections | llm_md | ledger |
   discovery-log | convergence-log | snapshot` have no runner, and `also_hard_lint` companions are
   documented in `lint.py`'s docstring but absent from its code.

The failure mode is silent: `skip` is not blocking, so `lint-report.json` reads clean while roughly a
third of the structural contract goes unenforced. Everything downstream — Prompt 7's threshold
calibration, critic-vs-human divergence, the delivered quality card — consumes that report. Calibrating
against it today would calibrate against a hole.

**Intended outcome.** Every registry rule either runs or is *visibly* unenforceable; the research arc
(the primer's quality ceiling, never yet exercised) is implemented and testable offline; the eval
harness scores a spec end-to-end with real numbers behind the TODO thresholds; and CI cannot let this
class of silent gap recur.

## Decisions taken

| Decision | Choice |
|---|---|
| Structural lint gap | **Extend the IR** — keeps IR-first intact; lints never parse HTML |
| Open GAPS.md items | **Apply G2 only** (reference-case affordance). G1 and G6 stay open |
| Live research runs | **Build against frozen fixtures**; the live spec-01 campaign is Stage G, triggered separately |
| Scope | **Everything remaining, dependency-ordered** |

---

## Stage A — Prompt 2b: close the IR ↔ registry structural gap

The prerequisite for every later stage, because Prompt 7 calibrates against the lint report.

### A1 · Extend the IR (`scripts/ir/schema.py`)

```python
class CardRows(BaseModel):            # R-CARD-02's seven required rows
    idea: str
    home_anchor: str                  # R-XREF-01 — the analogue leads
    whats_new_vs_renamed: str
    reach_for_when: str
    skip_when: str                    # R-CARD-03
    key_exemplar: str
    confidence: str

class RecallItem(BaseModel):
    question: str
    answer: str
    cross_domain: bool = False        # R-RECALL-02 wants >= 1 per section

ArtifactKind = Literal["decision_matrix", "checklist", "failure_catalog", "decision_aid"]

class Subsection(BaseModel):          # h3
    block_id: str
    title: str
    concept: str | None = None
    blocks: list[Block] = []

# Block gains: rows (role=card) · items (role=recall) · artifact_kind (role=matrix)
#              heading (an h4 label on a body block)
# Section gains: subsections: list[Subsection] = []
```

Two deliberate modelling calls:

- **h4 is a `Block.heading` attribute, not a container.** `R-ARCH-05` requires h4 to be absent from
  nav/TOC; modelling it as a block attribute makes that invariant structural rather than checked.
- **Recall is one block carrying three `items`,** not three blocks — block-ids stay stable and the
  `llm_md` role filter still drops the whole thing in one move.

`flatten_blocks()` and `all_block_ids()` must recurse into subsections. **This is the widest blast
radius in the plan** — lints, both renderers, `check_alignment`, `verify/*`, and `run_critics` all call
them. Keep the method signatures and return contracts identical so no caller changes.

New `validate_ir` invariants: `role=card ⇒ rows`; `role=recall ⇒ len(items) == 3`; `artifact_kind` only
on `role=matrix`; block-id uniqueness across the nested tree.

### A2 · Renderers follow the IR

- `render/render_html.py` — emit `<h3>` per subsection; `<dl>` card rows (finishes the
  `assets/card-template.html` stub); three `<details>` from `items`; `data-artifact-kind`. Nav/TOC
  builds from h2 + h3 only.
- `render/render_llm_md.py` — card distillation reads `rows` (drop the advance-organizer hook per
  `R-PROJ-03`, keep the anchor where it carries information); recall still dropped whole;
  `artifact_kind` surfaces in the block header.
- `utils/parse_primer.py` — read nested block-ids back; add `depth_dial_present` and `figure_a11y`.
- Update the golden-file tests and `tests/fixtures/document-ir.yaml`.

### A3 · Implement the missing checks

In `checks/structure_coverage.py`: `params_present`, `heading_hierarchy`, `card_rows`,
`summary_budgets`, `recall_count`, `operational_artifacts`, `banned_heading_terms`; and extend
`layer_coverage` to enforce the h3 ↔ sub-sum 1:1 clause it currently defers. A `summary` block *inside*
a `Subsection` is the sub-sum, which unifies the `R-SUMM-02` and `R-CONSIST-01` clauses into one check.

Registry edits (then `build.sh`): retag `R-DEPTH-02` and `R-FIG-04` as `input: html`.

### A4 · Registry-driven pass runner + strict mode

New `scripts/run_checks.py` (or `lint.py --pass`), dispatching by `check.input`: `ir`, `html`,
`projections`, `llm_md`, `ledger`, `discovery-log`, `convergence-log`, `snapshot`. It also dispatches
`also_hard_lint` companions **regardless of the parent rule's enforcement** (`R-SCENT-01` is
`soft_critic`, which is why its companion is invisible today).

Add a `coverage` block to `lint-report.json` — `rules_total / ran / skipped` — and a **`--strict` mode
where a `skip` on a MUST rule is an error**. Wire `--strict` into CI. This is the regression guard for
exactly the bug this stage fixes.

### A5 · Apply G2 (registry + lockstep)

Narrow `R-EXPERT-01` to *procedural* walkthroughs and add the running **reference-case** affordance, so
"ground every claim against the reference drawing" is not suppressed as a worked example. Add
`reference_case` to the registry `parameters` block — `spec-02` already carries the key. Regenerate via
`build.sh`, confirm idempotent, mark G2 **RESOLVED** in `GAPS.md`.

### A6 · Fix the documentation drift

Rule count is **76**, not 61 (`SKILL.md`) or 67 (`CLAUDE.md`, `README.md`). Refresh `README.md`'s Status
section and `SKILL.md`'s `[Claude Code phase]` markers. `SKILL.md` says "four parameters" but lists six
— `params_present` requires the four registry-defined ones and treats `outputs` / `seed_sources` as
optional.

**Verify A:** `pytest` green · `scripts/lint.py <fixture> --strict` reports zero MUST skips ·
`make build` idempotent · `validate_skill.py` clean · render goldens + `check_alignment` pass.

---

## Stage B — Prompt 6a: discovery campaign

Reuse the **Protocol + deterministic stub** pattern already proven in `critics/run_critics.py` and
`verify/_entailment.py`: pure code is hermetic and unit-tested; every model/tool call sits behind an
injectable seam with an offline default.

- `research/discovery.py` (pure, `R-DISC-04`) — `cluster_leads`, `support_count`, `novelty`,
  `saturation`, `framing_diversity`. No embeddings offline: cluster on normalized-token Jaccard, with an
  embedding backend behind a `resolve_backend`-style seam. Must be seed-free so eval replays reproduce.
- `research/planner.py` (model-judged) — `route_seeds`, `assess_topic`, `wave_briefs`, `extract_leads`,
  `triage_leads`, then the cascade `front_load_campaign` (Wave A→B→C) and `re_front_load`.
- `research/deep_research.py::run_brief` — backend adapter; `/deep-research` preferred, local
  `retrieval_loop` fallback, selected per `CAPABILITIES.md`; freezes `discovery-snapshot/report-<id>.md`.
- `checks/discovery.py` — `framing_diversity`, `saturation_terminal`, `snapshot_complete`,
  `seed_handling`. **Registry fix:** `R-DISC-06`'s `seed_handling` is tagged `input: discovery-log` but
  its detail and signature read `discovery-leads`; retag.
- Fixtures: `discovery-log.yaml`, `discovery-leads.yaml`, a minimal `discovery-snapshot/`.

**Verify B:** a synthetic three-wave campaign saturates (novel-fraction falls below threshold), triage
honours the `R-DISC-06` seed exemption, and the three lints pass on good fixtures / fail on bad ones.

## Stage C — Prompt 6: grounding loop

- `retrieval_loop.py`, `claim_extractor.py`, `recency.py`, `coverage.py` — tool-loops behind the same
  seam. `kb.py` stays a documented V2 deferral.
- `checks/ledger.py::provenance_fields` (`R-GROUND-05`) — pure and testable now.
- Populate `corroboration_count` / `corroborated_by` / `as_of_date` / `provenance_origin` (the fields
  `RECONCILE.md` added to the model but deliberately left unpopulated).
- **Assert the `R-DISC-01` firewall in tests:** a discovery lead is a pointer, never provenance — every
  ledger claim requires an independent fetch and its own ≤15-word quote.

**Verify C:** a recorded-fixture run turns accepted leads into a populated ledger + concept-map; the
ledger lint catches a claim with two sources and no `corroboration_count`.

## Stage D — Prompt 6b: convergence guard

Entirely pure, so it is the most testable stage: `tau`, `struct_distance` (via the given `EDIT_WEIGHTS`),
`escalate`, `classify_trajectory`, `contested_framings`, plus `checks/convergence.py::terminal_state`.
The model-judged `scan_for_structural` / `implied_edits` go in `planner.py`, never in `convergence.py`
(`R-CONV-02`).

**Verify D:** a converging trajectory footnotes; a synthetic oscillating one emits a `role: contested`
block and sets `concept_map.contested = true`; a property test proves the loop never exceeds `K_MAX`.

## Stage E — Prompt 7: eval harness

Author 5–8 specs spanning domain / seniority / length (keep `spec-01` and `spec-02`; add one with
`seed_sources` and one non-software topic). Implement `scripts/eval.py` over the specs +
`eval-rubric.yaml`, scoring all three tiers per-spec. Then settle the deferred TODOs against real
numbers: `per_run_token_cap`, `citation_recall`, `citation_precision`, recency thresholds.

**Verify E:** `make eval` scores `spec-01` end-to-end and reports concrete pass/fail per rule with
proposed threshold values.

## Stage F — Prompt 8: remaining plumbing

Add the build-idempotence check to `tools/validate_skill.py`; add `dorny/paths-filter` so CI runs only
changed skills and add the eval step; make `make eval` real; implement the `run-manifest.json` phase
ledger `SKILL.md` promises but nothing writes.

## Stage G — the live run (trigger separately)

A real `/deep-research` campaign + grounding run on `spec-01`, producing a genuine
`discovery-snapshot/` and populated ledger — the prompts' stated done-criteria for 6a/6. Held out of the
main sequence so the build stays deterministic and CI-safe; run it when you want to spend the tokens.

---

## Risks and open items

- **`flatten_blocks()` recursion is the one change that can break everything quietly.** Land A1 with the
  full test suite green before touching renderers, and add a test asserting nested block-ids appear in
  both projections.
- **G1 and G6 remain open** (`GAPS.md`). G1 (home ≈ target) bites in Stage C's `planner.py` — `spec-02`
  exercises it. G6 (user-specified structure is authoritative) bites when the outline maps onto a
  user-supplied skeleton. Both are small registry edits; decide before Stage C.
- **Offline lead clustering trades quality for determinism.** Jaccard will over-split near-duplicate
  leads that embeddings would merge. Acceptable for tests; note it as a Stage G calibration item.
- **`CAPABILITIES.md` is gitignored and absent in a fresh container** — run `make probe` first, or the
  NLP-dependent lints silently take their fallback path.
- **Google-Fonts links in `primer-template.html`** sit oddly with "self-contained HTML artifact."
  Not in scope here; worth a later decision.
