"""Pins on `[tool.ruff]` in the repo-root `pyproject.toml`.

These live at the repo root rather than under `skills/deep-primer/tests/` on purpose: a deployed
skill must be standalone (CLAUDE.md), so nothing bundled into a skill may reach up to a repo-level
file. The lint config is a repo concern, so its pins are repo-level tests.

Both assertions below cover a config bug that was live in this tree and silently did nothing --
which is this repo's signature defect class: a check that could not fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"

# `subprocess.run` with no `check=` -- PLW1510, one of the nine rules the test exemptions name.
# Chosen because it is exempt under `[tool.ruff.lint.per-file-ignores]` and live everywhere else,
# so it reads the boundary rather than the rule.
PROBE = 'import subprocess\nsubprocess.run(["true"])\n'


def _config() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _ruff_codes(as_path: str) -> set[str]:
    """Codes ruff reports for PROBE when it believes the file lives at `as_path`.

    `--stdin-filename` is how ruff resolves per-file-ignores globs, so this asks ruff itself
    rather than re-implementing globset matching in the test.
    """
    proc = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "--no-cache", "--stdin-filename", as_path, "--output-format", "json", "-",
        ],
        cwd=REPO_ROOT,
        input=PROBE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout, f"ruff produced no JSON for {as_path}: {proc.stderr.strip()}"
    return {finding["code"] for finding in json.loads(proc.stdout)}


def test_the_test_exemptions_reach_the_files_the_tests_are_actually_in():
    """`tests/**` matched nothing here; the tests live at `skills/<skill>/tests/**`.

    With the bare key all nine exemptions were inert and the nine rules they name were live on
    every test file. Reverting the key would make this fail rather than quietly re-arm them.
    """
    assert "PLW1510" not in _ruff_codes("skills/deep-primer/tests/test_probe.py")
    assert "PLW1510" in _ruff_codes("skills/deep-primer/scripts/probe.py"), (
        "the exemption is supposed to stop at the tests directory"
    )


def test_ruff_targets_the_python_this_package_declares_support_for():
    """`target-version` must not run ahead of the `requires-python` floor.

    Above the floor ruff offers modernisation rewrites that are syntax errors on the oldest
    supported interpreter -- a lint gate must not be able to suggest code the declared runtime
    cannot parse.
    """
    config = _config()
    floor = config["project"]["requires-python"]
    assert floor.startswith(">="), floor
    major, minor = floor.removeprefix(">=").strip().split(".")[:2]
    assert config["tool"]["ruff"]["target-version"] == f"py{major}{minor}"
