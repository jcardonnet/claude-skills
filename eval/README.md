# eval/ — shared eval runner (repo root)

The cross-skill harness lives here; per-skill **specs + rubric** live inside each skill
(`skills/<skill>/references/eval/`). Each skill exposes `scripts/eval.py` as its entry point.
Keep the runner shared, the specs per-skill (they have different rubrics).
