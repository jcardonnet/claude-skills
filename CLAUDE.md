# CLAUDE.md — orientation for Claude Code

This is a personal **skills monorepo**. The active skill is `skills/deep-primer/` — a registry-driven, multi-pass, source-grounded **primer generator**. Its design contracts are done; **Stage 6 is implementation** (the `scripts/`, `assets/`, and eval harness are stubs that raise `NotImplementedError`). Work through `CLAUDE_CODE_PROMPTS.md` in order.

## Architecture in three lines
- **IR-first:** drafting emits a canonical **document IR** (`skills/deep-primer/references/artifact-schemas.md`). HTML and the distilled LLM-MD are *projections* rendered from it; lints and critics read the IR; both projections share block-ids.
- **Registry-driven:** every rule lives in `references/rule-registry.yaml`. `references/rule-registry.md` and `references/critic-prompts/*` are **generated** from it.
- **Three kinds of enforcement:** local-deterministic lints (`scripts/checks/*`, `scripts/render/*`, `scripts/ir/*`), model_verified checks (`scripts/verify/*`), and agent-orchestrated loops (`scripts/research/*`, `scripts/critics/run_critics.py`).

## Hard conventions (follow these)
1. **Lockstep — never hand-edit generated files.** To change a rule, edit `references/rule-registry.yaml`, then run `bash tools/build.sh`. Do **not** edit `references/rule-registry.md` or `references/critic-prompts/*` directly; they are regenerated. The build is idempotent — a clean `git diff` after running it is the check.
2. **Self-containment.** A deployed skill must be standalone. Do **not** import across skills. Shared code (if any) lives in `/shared` (start empty) and is *vendored into each skill at bundle time* (`tools/bundle.py`). Promote to `/shared` only when a second skill genuinely duplicates the first.
3. **IR-first.** Lints/critics operate on the IR, not parsed HTML. Renderers are pure functions of the IR. The two projections must stay block-id aligned (`R-PROJ-02`).
4. **Script classification — respect it.** Local-deterministic scripts are hermetic Python (unit-testable with fixtures). `verify/*` call an entailment model. `research/*` and `run_critics.py` are **tool-loops** (web/MCP + model) — don't try to make them hermetic; structure them single-agent now, multi-agent-ready behind stable interfaces.
5. **Blocking derives from priority, not enforcement.** MUST rules block; SHOULD/MAY warn. This is independent of whether a rule is lint / model_verified / critic.
6. **Figures & copyright.** Never fetch the source domain's own copyrighted figures; draw synthetic SVG. Quotes from sources stay ≤15 words.

## Commands
- `uv pip install -e .[dev]` (and try `.[nlp]`); `uv run python skills/deep-primer/scripts/probe_env.py` → `CAPABILITIES.md` first.
- `make build` — regenerate lockstep files. `make validate` — structural checks. `make test` — pytest. `make eval` — eval harness. `make bundle` — emit self-contained skills to `dist/`.

## Key files
- Contracts: `skills/deep-primer/SKILL.md`, `references/artifact-schemas.md` (IR + projections), `references/rule-registry.yaml` (67 rules), `references/evidence-map.md` (the "why").
- Generators: `skills/deep-primer/tools/{gen_registry_md.py, gen_critic_prompts.py, build.sh}`.
- Repo tools: `tools/validate_skill.py` (working minimal), `tools/bundle.py` (stub).
- Open design decisions: `GAPS.md` — surface these, don't silently apply them.
