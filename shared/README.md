# shared/ — DEV-ONLY cross-skill code

Start **empty**. Promote code here only when a *second* skill genuinely duplicates the first — premature
sharing is how monorepos calcify. Anything placed here is **vendored into each skill at bundle time**
(`tools/bundle.py`) so shipped skills stay self-contained. Candidates if/when reuse appears: an HTML/SVG
rendering lib, a registry->generated-files generator, the eval runner.
