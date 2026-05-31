# Claude Code — Stage 6 prompts (run in order)

Each prompt is self-contained and copy-pasteable. Run them in sequence; review the diff after each.
Two standing rules apply to every prompt (also in `CLAUDE.md`):
- **Lockstep:** never hand-edit `references/rule-registry.md` or `references/critic-prompts/*`. Edit `references/rule-registry.yaml`, then run `bash tools/build.sh`. The YAML is the source of truth.
- **IR-first:** drafting emits the canonical **document IR** (`references/artifact-schemas.md`); HTML and the distilled LLM-MD are projections rendered from it; lints/critics read the IR; both projections share block-ids.

Paths below are relative to `skills/deep-primer/` unless noted.

---

## Prompt 0 — Orient & set up the environment (no feature code yet)
Read `README.md`, `CLAUDE.md`, `skills/deep-primer/SKILL.md`, `skills/deep-primer/references/artifact-schemas.md`, and `skills/deep-primer/references/rule-registry.yaml` (skim `references/evidence-map.md`). Then:
1. Create a venv and `pip install -e .[dev]`. Try the optional extras `[nlp]` (spaCy + a coref model; download a spaCy English model) and the verify option (see Prompt 3) — record what actually installs in this environment.
2. Implement `scripts/probe_env.py` to detect availability of: spaCy + coreference, an NLI/entailment model, lxml/bs4. Write `CAPABILITIES.md` recording which lints and which verifier can run natively vs must fall back.
3. Run `python tools/validate_skill.py skills/*` and `make build`; confirm the lockstep regeneration is idempotent (`git diff` empty after build).

Done when `CAPABILITIES.md` exists, validation + idempotent build pass, and you can state back to me the IR-first contract and the local-deterministic / model_verified / agent-orchestrated script split.

## Prompt 0.5 — Reconcile the contract deltas into your Prompts 1–5 code (apply `RECONCILE.md`)
You implemented Prompts 1–5 before the discovery / convergence / seed-source contracts landed. The *registry and schema* changes are already in the repo (you pulled them); this prompt applies the small **code** touch-ups in `RECONCILE.md` to your implemented files. It is mechanical — review the diff at the end and run nothing else.

Read `RECONCILE.md` and the `R-GROUND-05`, `R-DISC-0*`, `R-CONV-0*` rows of `references/rule-registry.yaml`. Apply exactly these and nothing more:
1. `scripts/ir/schema.py` (+ `validate_ir`): add `contested` to the block `Role` enum; add `cycle: int | None = None` and `contested: bool = False` to `ConceptMap`; add to the ledger-claim model `corroboration_count: int | None = None`, `corroborated_by: list[str] = []`, `as_of_date: date | None = None`, and `provenance_origin: Literal["discovered","user"] = "discovered"`. If `validate_ir` asserts an exhaustive role set, include `contested`. Change no other invariant.
2. `scripts/lint.py`: scope the IR pass to IR-targeting hard_lints — `ir_hard = [r for r in rules if r["enforcement"]=="hard_lint" and r["check"].get("input","ir")=="ir"]` — run `ir_hard` on the IR and leave the render / discovery / convergence / ledger checks to their own passes (those artifacts don't exist during an IR-only lint, and several are unimplemented stubs you must not call here). Scope your lint tests to `ir_hard`.
3. `scripts/render/render_html.py`: add a `contested` role branch — render `block.framings` as a comparison panel (reuse the tradeoff / Toulmin path); when the concept-map has `contested: true`, show a "competing organizing views" banner. `scripts/render/render_llm_md.py`: keep `contested` (emit one `## [block: <id>]` per framing, each with `provenance`). `scripts/render/check_alignment.py`: no change.

Do **not** touch `scripts/verify/*` (Prompt 3) or `scripts/critics/run_critics.py` (Prompt 5) — they are unchanged. Do **not** populate `corroboration_count` / `as_of_date` or implement `checks/ledger.py` here — that is Prompt 6 grounding-loop work; the new fields only need to *exist* on the model now.

Then `bash tools/build.sh`, confirm idempotent (`git diff --exit-code -- references/rule-registry.md references/critic-prompts`), and run pytest (the new enum value + optional fields must not break existing fixtures).

Done when: `contested` plus the four ledger fields exist on the models, `lint.py` runs only the `ir_hard` set on the IR (no stub checks invoked), `render_html` / `render_llm_md` accept a `contested` block, the lockstep build is idempotent, and pytest is green.

## Prompt 1 — Document IR schema + validation (the canonical contract)
Read `references/artifact-schemas.md` (Document IR + all schemas). Then:
1. `scripts/ir/schema.py` — pydantic models: `DocumentIR` (meta + sections of `Block`), `Block(block_id, role, text?, concept?, mode?, claim_ids?, provenance?, source_ids?, caption?, svg_ref?)`, plus `SourceLedger`, `ConceptMap`, `ResearchPlan`, `PrimerMeta`. `role` / `mode` / `provenance` as enums per the schema.
2. `scripts/ir/validate_ir.py` — schema validation + invariants: unique block_ids; every `claim_ids` entry exists in the ledger; every `concept` exists in the concept-map; `provenance: verified` ⇒ ≥1 `source_id`.
3. `scripts/utils/parse_primer.py` — HTML → `Block` list for round-trip (IR stays canonical).
4. Add `tests/` with a small fixture `document-ir.yaml`; round-trip + a malformed-fixture rejection test.

Done when pytest is green and `validate_ir` rejects the malformed fixture.

## Prompt 2 — Local-deterministic lints on the IR
Read the `hard_lint` rows of `rule-registry.yaml`, `artifact-schemas.md`, and `CAPABILITIES.md`. Then:
1. `scripts/lint.py` — load the registry; for each `enforcement: hard_lint` rule dispatch to its `check.ref`; **blocking derives from priority** (MUST blocks, SHOULD/MAY warn); emit `lint-report.json` as `{rule_id, block_id, status, detail}`.
2. `scripts/checks/*.py` — implement each, all operating on the IR/Block list: `structure_coverage` (`layer_coverage`, `length_budget`), `prose_caps` (`compression_gradient`, `length_caps`, `condition_first`), `coherence_givennew` (spaCy+coref if `CAPABILITIES.md` says available, else entity-overlap fallback), `univocity_terms`, `multiview_concepts`, `recency_versions` (flag-only offline), `footnote`, `xrefs`, `provenance`.
3. `tests/` with passing + failing fixtures per check.

Done when `lint.py` runs the full hard_lint set on the fixture IR, MUST failures block and SHOULD/MAY warn, tests are green, and the coherence check degrades per `CAPABILITIES.md`.

## Prompt 3 — model_verified citation quality
Read `R-GROUND-01/02/03` in the registry and the source-ledger schema. Then:
1. `scripts/verify/citation_quality.py`: `resolves_to_ledger` (deterministic, R-GROUND-01), `recall` (R-GROUND-02), `precision` (R-GROUND-03) via an entailment model. Choose per `CAPABILITIES.md`: **MiniCheck** (cheap NLI) if installable, else a **scoped Claude call** (one claim+quote at a time, binary supports/not-supports). Emit `verify-report.json` with per-claim verdicts + aggregate recall/precision.
2. Read the threshold from `references/eval/eval-rubric.yaml`; below threshold is a MUST-level block (priority).

Done when, on a fixture with one unsupported and one decorative citation, recall/precision reflect them and deterministic resolution flags an unledgered marker.

## Prompt 4 — Renderers (IR-first, two projections) + the HTML template
Read `artifact-schemas.md` (Projections), `R-PROJ-*` and `R-FIG-*` in the registry, and `assets/*`. Then:
1. `assets/primer-template.html` — finish the depth-dial shell per its header comment (emit `data-block-id`/`data-concept`/`data-mode` + `primer-meta`; theme-aware SVG; distinctive font pairing; numbered footnotes; provenance inline).
2. `scripts/render/render_html.py` — IR → HTML on the template.
3. `scripts/render/render_llm_md.py` — IR → distilled MD: `role_filter` (R-PROJ-03: drop `recall`, distill cards), de-anaphorize each block to self-contained (R-PROJ-04 producer), provenance inline (R-PROJ-05), drop SVG keep captions (R-PROJ-06), front-matter index + `## [block: id]` headings.
4. `scripts/render/check_alignment.py` — R-PROJ-02 set check (md block-ids ⊆ html; diff == role-filtered roles).
5. `scripts/verify/chunk_selfcontained.py` — R-PROJ-04 verifier (no dangling anaphora + entails claim_ids).
6. Golden-file tests: one fixture IR → both projections; assert block-id alignment, no `role=recall` and no `<svg>` in the MD, provenance present, and the distilled chunk matches the `artifact-schemas.md` shape.

Done when both projections render, alignment passes, and the tests are green.

## Prompt 5 — Critic runner (the six scoped binary passes)
Read `references/critic-prompts/*` and `R-REJECT-05`. Then:
1. `scripts/critics/run_critics.py` — for each of the six passes, feed the critic prompt + the IR block list (filtered to the block types that pass targets) to the model; collect binary `{rule_id, block_id, verdict, evidence}`; test-retest gating items (judge 2×, `unstable` on disagreement); swap-and-average **only** when comparing two candidate revisions. Emit `critic-report.json`.
2. This is agent-orchestrated (calls the model); structure passes to run concurrently later.

Done when a run produces binary verdicts keyed by `rule_id`+`block_id` across all six passes, with holistic scoring impossible by construction.

## Prompt 6a — Discovery campaign (recall augmentation)
Read `references/discovery-brief-templates.md`, the Discovery-campaign artifacts in `references/artifact-schemas.md`, `R-DISC-01..05`, and the stubs `scripts/research/discovery.py`, `scripts/research/deep_research.py`, `scripts/research/planner.py`, `scripts/checks/discovery.py`. Then:
1. `deep_research.py::run_brief` — invoke `/deep-research` for one `research-brief` (you're on Max), capture report + sources, and freeze the report into `discovery-snapshot/`. Provide the local `retrieval_loop` as the fallback backend, selected by `CAPABILITIES.md`.
2. `discovery.py` (deterministic, `R-DISC-04`): `cluster_leads`, `support_count`, `novelty`, `saturation`, `framing_diversity`, using the config constants (`MIN_FRAMINGS`, `SATURATION_THRESHOLD`, `MAX_WAVES`, `FRAMING_AXES`, `ORTHOGONAL_FRAMINGS`).
3. `planner.py` (model-judged): `assess_topic` (→ front-load aggressiveness + interleave budget), `wave_briefs` (emit each wave's diverse ensemble from the templates, ≥`MIN_FRAMINGS` cells incl. ≥1 orthogonal), `extract_leads` (report → `--json-schema` topic/source leads, leads only), `triage_leads` (accept / flag high-salience singletons / drop + salience). Then the cascade `front_load_campaign` (Wave A→B→C to saturation) and `re_front_load` (focused, seeded by an escalation finding) — the entry points the convergence guard (6b) calls. Add `route_seeds` (split `seed_sources` into direct accepted leads vs author/URL directives); `triage_leads` exempts user seeds from drop and marks `provenance_origin=user`; `wave_briefs` emits a seed-anchored brief per directive (`R-DISC-06`).
4. Emit `discovery-leads.yaml` + `discovery-log.yaml`; accepted topic-leads become questions in `research-plan.yaml`, accepted source-leads become fetch candidates for Prompt 6 — never ledger claims (`R-DISC-01`). Route leads surfaced only under contrarian/adjacent framings to the `contested` rendering.
5. `checks/discovery.py`: `framing_diversity` (`R-DISC-02`), `saturation_terminal` (`R-DISC-03`), `snapshot_complete` (`R-DISC-05`) + tests.

Done when a real campaign on `spec-01` saturates (the `discovery-log` shows novel-fraction falling below threshold), produces a triaged `discovery-leads.yaml`, and freezes a `discovery-snapshot/`.

## Prompt 6 — Grounding loop (agent-orchestrated)
Grounds the campaign's accepted leads (Prompt 6a) into the schema-bound ledger. Read the research-plan / source-ledger / concept-map schemas and `R-GROUND-01..04`, `R-EVID-03`. Then:
1. `retrieval_loop.py` — fetch the accepted **source-leads**, and bounded web search → fetch → gap → re-query for accepted **topic-lead** questions not yet covered (`max_retrieval_iterations`).
2. `claim_extractor.py` — atomic claims → `source-ledger.yaml` with independently-fetched ≤15-word quotes, provenance, and confidence. Re-anchor each claim to a fetched source — a discovery lead is a pointer, not provenance (`R-DISC-01`). Set `corroboration_count`/`corroborated_by` from the campaign's per-claim source counts and `as_of_date` on version/SOTA claims, plus `provenance_origin` (user for seed-derived claims) (`R-GROUND-05`/`R-DISC-06`); implement `checks/ledger.py::provenance_fields`.
3. `recency.py` — version sweep (`R-GROUND-04`). `coverage.py` — conflict/coverage vs the plan, mark `thin`, perf claims need `min_independent_nonvendor`. `kb.py` — deferred stub.
4. Curate → `concept-map.yaml` + outline seed — derived from the ledger, never copied from a deep-research report's structure.

Tool-loops, not hermetic functions. Done when a real run on `spec-01` turns the accepted leads into a populated ledger + concept-map with every claim independently grounded.

## Prompt 6b — Convergence guard (the escalate loop)
Read `references/artifact-schemas.md` (Convergence-guard artifacts), `R-CONV-01/02`, and the stubs `scripts/research/convergence.py` + `scripts/checks/convergence.py`. Then:
1. Implement `convergence.py` (deterministic, `R-CONV-02`): `struct_distance` (concept-map graph-edit distance via `EDIT_WEIGHTS`), `tau` (rising schedule, `+inf` past `K_MAX`), `escalate`, `classify_trajectory` (cluster per-cycle maps → `converged` / `contested` / `chaotic`), `contested_framings`.
2. Implement the model-judged side in `planner.py` (or a judge module) — NOT in `convergence.py`: `scan_for_structural` and `implied_edits`. Wire the draft loop: deepen-in-place when `Δ_struct < tau`, escalate (re-front-load, `cycle++`) when `Δ_struct ≥ tau` and `cycle < K_MAX`, else footnote/render per `classify_trajectory`.
3. Emit `concept-map-vK.yaml` per cycle + `convergence-log.yaml`; render the `contested-structure` block (`role: contested`) when the regime is contested, and set the concept-map `contested: true`.
4. Implement `checks/convergence.py::terminal_state` (the `R-CONV-01` lint over the log) + tests: a converging trajectory footnotes; an oscillating one renders a contested-structure; the loop never exceeds `K_MAX`.

Done when the loop provably terminates (≤`K_MAX` escalations), the lint passes, and a synthetic oscillating fixture produces a contested-structure block.

## Prompt 7 — Eval harness + the quantitative loop
Read `references/eval/*` and your existing `skills/skill-creator`. Then:
1. Author 5–8 specs in `references/eval/specs` (vary domain / seniority / length); keep `spec-02` (the home≈target stress).
2. `scripts/eval.py` — load specs + `eval-rubric.yaml`; generate (Phases 0–8) or load primers; score hard lints + model_verified + human overlay; report per-spec.
3. Run against a real generation; record results.
4. Invoke skill-creator to iterate; settle the deferred TODOs (`per_run_token_cap`, citation-recall / recency thresholds) against real numbers.

Done when `eval.py` scores at least `spec-01` end-to-end and you report concrete pass/fail per rule with proposed threshold values.

## Prompt 8 — Repo plumbing (validate, bundle, CI)
1. Extend `tools/validate_skill.py` with a build-idempotence check (run `build.sh`, assert git-clean).
2. Implement `tools/bundle.py` (vendor `shared/` deps into each skill under `dist/`, rewrite imports, validate each bundle).
3. Make the `Makefile` targets real and finish `.github/workflows/ci.yml` with path-filtering (only changed skills) running validate + idempotent build + eval.

Done when `make validate` / `make build` / `make bundle` work, CI is green on a no-op, and a bundled skill under `dist/` is self-contained (no `shared/` imports).

---

## Decisions to surface before Prompts 4/6 (see `GAPS.md`)
Apply via the registry + `build.sh` (never by hand-editing generated files):
- **G2 (recommended: apply)** — narrow `R-EXPERT-01` to *procedural* walkthroughs and add a running-**reference-case** affordance, so "ground every claim against the reference drawing" doesn't get suppressed as a worked example.
- **G1** — when `home_domain ≈ target_domain`, reinterpret `home_anchor` as the nearest adjacent *technique/sub-field* (the bridge-builder perspective becomes prior-art transfer).
- **G6** — an explicit user-specified section structure is authoritative; the derived outline maps onto it (concept-map still drives depth within those sections).
