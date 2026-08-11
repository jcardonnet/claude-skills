.PHONY: build validate eval bundle test probe lint help
help:                  ## list targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22
build:                 ## regenerate every skill's lockstep-derived files
	@for s in skills/*/tools/build.sh; do [ -f "$$s" ] && bash "$$s"; done
validate:              ## structural validation + lockstep drift check
	python tools/validate_skill.py --check-build skills/*
probe:                 ## record optional-dependency availability
	python skills/deep-primer/scripts/probe_env.py
test:                  ## unit tests
	python -m pytest -q
lint:                  ## ruff over the skill sources
	python -m ruff check skills/deep-primer/scripts skills/deep-primer/tests
eval:                  ## run the deep-primer eval harness
	python skills/deep-primer/scripts/eval.py
bundle:                ## emit each skill as a self-contained, deployable folder
	python tools/bundle.py skills/* --out dist/
