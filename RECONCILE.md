# RECONCILE.md — apply to your Prompts 1–5 working copy

**Do not overwrite your tree with the zip** — it carries stubs where you have implementations. Apply these deltas on top of your code. The *contract* changes (registry / schema) are already in the repo: pull those files and run `bash tools/build.sh` after the registry edit (lockstep — regenerate the `.md`/critics, don't hand-copy them). The *code* touch-ups below you apply to your implemented files.

Net effect: one enum value + three optional ledger fields (Prompt 1), one dispatcher filter (Prompt 2), one renderer branch (Prompt 4). **Prompts 3 and 5 are unchanged.**

## Contract changes already in the repo (pull these)
- `references/rule-registry.yaml` — every non-IR script check now carries an `input:` tag; added `R-GROUND-05`. Run `bash tools/build.sh`.
- `references/artifact-schemas.md` — the ledger claim gains `corroboration_count`, `corroborated_by`, `as_of_date`. (`source_type` and a `conflicts[]` block were **not** added — they're already covered by the ledger's existing `type`/`credibility` and `contested`/`contradicts`.)
- `scripts/checks/ledger.py` — new stub, implemented in Prompt 6.

## Prompt 1 — `scripts/ir/schema.py` (+ `validate_ir`)
1. Role enum: add `contested`.
   ```python
   Role = Literal["lede","card","summary","body","toulmin","matrix",
                  "figure","recall","glossary","further_reading","contested"]
   ```
2. `ConceptMap`: add `cycle: int | None = None` and `contested: bool = False`.
3. Ledger claim model: add
   ```python
   corroboration_count: int | None = None
   corroborated_by: list[str] = []     # other source_ids supporting this claim
   as_of_date: date | None = None      # version/SOTA claims: when verified current
   provenance_origin: Literal["discovered","user"] = "discovered"  # user = a seed_source (R-DISC-06)
   ```
4. `validate_ir`: if you assert an exhaustive role set, include `contested`. No other invariant changes.

## Prompt 2 — `scripts/lint.py` (the only real one)
The registry now tags every non-IR script check with `input` (`html` / `projections` / `llm_md` / `convergence-log` / `discovery-log` / `snapshot` / `ledger`). **Convention: absent `input` ⇒ `ir`.** Scope the IR pass to IR-targeting checks:
```python
ir_hard = [r for r in rules
           if r["enforcement"] == "hard_lint"
           and r["check"].get("input", "ir") == "ir"]
```
Run `ir_hard` on the IR; route the rest to their own passes (render checks after rendering; discovery/convergence/ledger checks at their phases — those artifacts don't exist during an IR-only lint, and their checks are unimplemented stubs you must not call here). Scope your lint tests to `ir_hard`.

The four that were breaking your dispatcher are `convergence::terminal_state`, `discovery::{framing_diversity,saturation_terminal}`, `discovery::snapshot_complete`; the rest (`check_alignment`→projections, `render_llm_md::{role_filter,no_svg}`→llm_md, `chunk_selfcontained`→llm_md, `parse_primer::block_ids_and_meta`→html, `ledger::provenance_fields`→ledger) are tagged for consistency and run in your render / phase passes as before.

## Prompt 4 — renderers
Teach the `contested` role (only emitted by the 6b loop, but don't choke on it):
- `render_html.py` — render `block.framings` as a comparison panel (reuse your tradeoff/Toulmin path); when the concept-map has `contested: true`, show a "competing organizing views" banner.
- `render_llm_md.py` — **keep** `contested` (operational, not pedagogy): one `## [block: <id>]` per framing with `provenance`.
- `check_alignment.py` — no change (contested blocks carry block-ids).

## Prompt 6 (ahead of you — not a 1–5 touch-up)
`checks/ledger.py::provenance_fields` (`R-GROUND-05`) and populating `corroboration_count`/`corroborated_by`/`as_of_date` in `claim_extractor.py` are grounding-loop work; they land when you do Prompt 6.
