.PHONY: build validate eval bundle test probe lint help

# `python` on PATH is not necessarily this project's interpreter. Under a system or conda
# python the suite still COLLECTS, then ~31 tests fail on missing optional deps (bs4 and
# friends) — which reads as 31 regressions and is not one. Prefer the repo venv when it
# exists; override with `make test PY=...` if you mean a different interpreter.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)
help:                  ## list targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22
build:                 ## regenerate every skill's lockstep-derived files
	@for s in skills/*/tools/build.sh; do [ -f "$$s" ] && bash "$$s"; done
validate:              ## structural validation + lockstep drift check
	$(PY) tools/validate_skill.py --check-build skills/*
probe:                 ## record optional-dependency availability
	$(PY) skills/deep-primer/scripts/probe_env.py
test:                  ## unit tests
	$(PY) -m pytest -q
lint:                  ## ruff over the skill sources and the repo-level tests
# `tools/` is deliberately absent: validate_skill.py is the working-minimal version and
# bundle.py is still a stub, and between them they carry 16 findings that are noise until
# Stage 6 rewrites both. Add them here once they are real.
	$(PY) -m ruff check skills/deep-primer/scripts skills/deep-primer/tests tests
eval:                  ## run the deep-primer eval harness
	$(PY) skills/deep-primer/scripts/eval.py
bundle:                ## emit each skill as a self-contained, deployable folder
	$(PY) tools/bundle.py skills/* --out dist/
