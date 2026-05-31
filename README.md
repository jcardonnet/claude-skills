# skills-monorepo

A personal monorepo of Claude skills. One repo, many skills; shared tooling at the root; each skill bundled **self-contained** for deployment. The dev workspace is this repo (consumed directly by Claude Code); claude.ai gets published bundles.

The active skill, **`deep-primer`**, is a registry-driven, multi-pass, source-grounded *primer generator*: it researches a topic, drafts a canonical document IR, runs deterministic lints + model-verified citation checks + scoped critics against it, and renders two projections — an HTML primer for humans and an operationally-distilled, block-id-aligned Markdown file for grounding an LLM.

## Layout
```
skills/
  deep-primer/            ← active: design DONE, Stage 6 = implement scripts/assets/eval
    SKILL.md
    references/           rule-registry.yaml (source of truth) + generated md/critics,
                          artifact-schemas.md (IR + projections), evidence-map.md, exemplars.md,
                          research-perspectives.md, eval/ (specs + rubric)
    scripts/              Stage-6 stubs (checks/ verify/ render/ ir/ critics/ research/ utils/)
    assets/               primer-template.html, card-template.html, llm_md_template.md (stubs)
    tools/                gen_registry_md.py, gen_critic_prompts.py, build.sh  (lockstep)
  arch-design-doc-obsidian/   placeholder — drop your existing skill here
  skill-creator/              placeholder — drop your existing skill here
shared/                   DEV-ONLY cross-skill code (start empty; vendored at bundle time)
tools/                    validate_skill.py (working), bundle.py (stub)
eval/                     shared eval runner (specs live per-skill)
.github/workflows/ci.yml  validate + idempotent build + eval (path-filtered — Prompt 8)
pyproject.toml  Makefile  CLAUDE.md  CLAUDE_CODE_PROMPTS.md  GAPS.md
```

## Conventions
- **Lockstep:** edit `references/rule-registry.yaml`, then `bash tools/build.sh`. Never hand-edit `rule-registry.md` or `critic-prompts/*` — they're generated, and the build is idempotent.
- **IR-first:** the document IR is canonical; HTML + LLM-MD are projections that share block-ids.
- **Self-containment:** skills never import across each other; shared code is vendored at bundle time so a shipped skill is standalone.
- **`shared/` starts empty:** promote code only when a second skill duplicates it.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]            # optionally: pip install -e .[nlp]
python skills/deep-primer/scripts/probe_env.py   # writes CAPABILITIES.md
make validate                    # structural checks (working today)
make build                       # regenerate lockstep files (idempotent)
```
Then open **`CLAUDE_CODE_PROMPTS.md`** and run Prompt 0 → Prompt 8. `CLAUDE.md` is the standing orientation for the coding agent; `GAPS.md` holds the open design decisions to settle along the way.

## Status
Design + contracts shipped (registry at 67 rules incl. the `R-PROJ-*` projection rules; IR + projections schema; SKILL pipeline). Everything under `scripts/`, `assets/`, and the eval harness is a documented stub awaiting Stage 6.
