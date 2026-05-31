.PHONY: build validate eval bundle test probe
build:                 ## regenerate every skill's lockstep-derived files
	@for s in skills/*/tools/build.sh; do [ -f "$$s" ] && bash "$$s"; done
validate:              ## structural validation of every skill
	python tools/validate_skill.py skills/*
probe:                 ## record optional-dependency availability
	python skills/deep-primer/scripts/probe_env.py
test:
	pytest -q
eval:                  ## run the deep-primer eval harness
	python skills/deep-primer/scripts/eval.py
bundle:                ## emit each skill as a self-contained, deployable folder
	python tools/bundle.py skills/* --out dist/
