# Claude Code — Stage 6 prompts (run in order)

Each prompt is self-contained and copy-pasteable. Run them in sequence; review the diff after each.
Two standing rules apply to every prompt (also in `CLAUDE.md`):
- **Lockstep:** never hand-edit `references/rule-registry.md` or `references/critic-prompts/*`. Edit `references/rule-registry.yaml`, then run `bash tools/build.sh`. The YAML is the source of truth.
- **IR-first:** drafting emits the canonical **document IR** (`references/artifact-schemas.md`); HTML and the distilled LLM-MD are projections rendered from it; lints/critics read the IR; both projections share block-ids.

Paths below are relative to `skills/deep-primer/` unless noted.

---

## Prompt 0 — Orient & set up the environment (no feature code yet)
Read `README.md`, `CLAUDE.md`, `skills/deep-primer/SKILL.md`, `skills/deep-primer/references/artifact-schemas.md`, and `skills/deep-primer/references/rule-registry.yaml` (skim `references/evidence-map.md`). Then:
1. Create a venv (`uv venv`) and `uv pip install -e .[dev]`. Try the optional extras `[nlp]` (spaCy + a coref model; download a spaCy English model) and the verify option (see Prompt 3) — record what actually installs in this environment.
2. Implement `scripts/probe_env.py` to detect availability of: spaCy + coreference, an NLI/entailment model, lxml/bs4. Write `CAPABILITIES.md` recording which lints and which verifier can run natively vs must fall back.
3. Run `python tools/validate_skill.py skills/*` and `make build`; confirm the lockstep regeneration is idempotent (`git diff` empty after build).

Done when `CAPABILITIES.md` exists, validation + idempotent build pass, and you can state back to me the IR-first contract and the local-deterministic / model_verified / agent-orchestrated script split.

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

## Prompt 6 — Research arc (agent-orchestrated)
Read `references/research-perspectives.md`, the research-plan / source-ledger / concept-map schemas, and `R-EVID-03` / `R-GROUND-04`. Then:
1. `scripts/research/planner.py` — questions × perspectives; **dedup** near-duplicates (`merged_from`); set `budget_weight` per perspective (defaults are re-weightable — a prior-art-mapping request raises historian/bridge-builder); write `research-plan.yaml`.
2. `retrieval_loop.py` — bounded web search → fetch full pages → extract → gap → re-query (`max_retrieval_iterations`).
3. `claim_extractor.py` — atomic claims → `source-ledger.yaml` (≤15-word quotes, provenance, confidence).
4. `recency.py` — version sweep (R-GROUND-04). `coverage.py` — conflict/coverage, mark `thin`, perf claims need `min_independent_nonvendor`. `kb.py` — leave as the deferred stub.
5. Curate → `concept-map.yaml` + outline seed.

These are tool-loops, **not** hermetic functions; keep single-agent now, multi-agent-ready behind the same interfaces. Done when a real run on `spec-01` yields a populated plan + ledger + concept-map with provenance tags.

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
