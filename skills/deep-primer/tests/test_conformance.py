"""Conformance-check tests — and above all, proof that each check CAN fail.

The nine rules these cover were unexercised, filed under `human` as "maintainer judgment, never
auto-checked". They are not that: every one is an assertion about this codebase, so every one is
mechanically checkable.

Which creates the obvious hazard. A conformance suite that reports 9/9 conformant on a clean tree
looks identical to nine tautologies that can never fail — and this project has now been bitten by
exactly that twice (a rule dispatching to nothing, an assertion comparing a value to itself). So the
load-bearing tests here are the NEGATIVE ones: each check is fed a deliberately violating tree and
must catch it. Without those, the coverage this module adds would be a lie.
"""

from pathlib import Path

import pytest

from checks.conformance import (
    critics_are_binary_only,
    deterministic_modules_stay_pure,
    ir_is_the_only_canonical_source,
    leads_are_never_evidence,
    no_rejected_techniques_are_implemented,
    run_conformance_pass,
    swap_and_average_is_pairwise_only,
)


# --- the real tree is conformant ---------------------------------------------

def test_the_repo_is_conformant_today():
    report = run_conformance_pass()
    failures = [f for f in report["findings"] if f["status"] == "fail"]
    assert not failures, failures
    assert report["counts"]["pass"] == 9
    assert not report["blocking"]


def test_every_conformance_rule_is_reported_exactly_once():
    ids = [f["rule_id"] for f in run_conformance_pass()["findings"]]
    assert sorted(ids) == sorted(set(ids))
    assert set(ids) == {"R-REJECT-01", "R-REJECT-02", "R-REJECT-03", "R-REJECT-04", "R-REJECT-05",
                        "R-PROJ-01", "R-CONV-02", "R-DISC-01", "R-DISC-04"}


# --- each check must be able to FAIL -----------------------------------------

def test_purity_check_catches_a_clock_and_a_random_source(tmp_path):
    impure = tmp_path / "impure.py"
    impure.write_text("import random\n"
                      "from datetime import datetime\n"
                      "def f():\n"
                      "    return random.choice([1, 2]), datetime.now()\n", encoding="utf-8")
    problems = deterministic_modules_stay_pure({"R-CONV-02": impure})
    assert problems
    assert any("random" in p for p in problems)
    assert any("now()" in p for p in problems)


def test_purity_check_catches_a_judge_import(tmp_path):
    """The split R-CONV-02 protects: the metric half is deterministic, the judged half lives in
    planner.py. A judge imported into the pure module collapses that distinction."""
    impure = tmp_path / "impure.py"
    impure.write_text("from critics.run_critics import StubJudge\n", encoding="utf-8")
    problems = deterministic_modules_stay_pure({"R-DISC-04": impure})
    assert problems and "critics.run_critics" in problems[0]


@pytest.mark.parametrize("label,source", [
    # The one that mattered: nothing in the old denylist named a module that calls a model, so a
    # live `claude -p` inside a "pure" function passed the guard 9/9 clean.
    ("a model call", "from utils.claude_cli import ClaudeCli\n"
                     "def tau():\n    return ClaudeCli()('judge this')\n"),
    # Aliasing walked straight through a denylist keyed on the imported NAME.
    ("an aliased clock", "import time as t\ndef tau():\n    return t.time()\n"),
    ("an aliased datetime", "from datetime import datetime as dt\ndef tau():\n    return dt.now()\n"),
    # An environment read makes the same input produce different output on another machine.
    ("an environment read", "import os\ndef tau():\n    return os.environ.get('SEED')\n"),
    # A lazy import inside a function body is still an import.
    ("a function-local import", "def tau():\n    import random\n    return random.random()\n"),
    # The exact class this repo already shipped once, in `concept_id`: builtin hash() is salted per
    # process, so the same corpus clusters differently between runs.
    ("builtin hash()", "def concept_id(term):\n    return hash(term) % 97\n"),
    ("a subprocess", "import subprocess\ndef tau():\n    return subprocess.run(['ls'])\n"),
])
def test_purity_check_catches_every_impurity_this_repo_can_actually_produce(label, source, tmp_path):
    """The denylist this replaces was {random, secrets, uuid} plus a handful of method names, and it
    could not detect ANY of these — least of all the model call, which is what R-CONV-02 and
    R-DISC-04 are principally about."""
    impure = tmp_path / "impure.py"
    impure.write_text(source, encoding="utf-8")
    assert deterministic_modules_stay_pure({"R-DISC-04": impure}), f"{label} went undetected"


def test_the_purity_allowlist_still_admits_what_the_pure_modules_need():
    """The paired positive: an allowlist that rejected everything would be a check that always
    fails, which is no more useful than one that never does. Asserted against the REAL modules, so
    a legitimate new import has to be added to the allowlist deliberately."""
    assert deterministic_modules_stay_pure() == []


def test_a_holistic_instruction_is_not_excused_by_an_unrelated_negation():
    """The exemption exists because every generated prompt QUOTES the prohibition. It used to skip
    any line containing `not `, which is common enough in English that a real holistic instruction
    sharing a line with an unrelated negation was waved through — the detector disabled on exactly
    the phrasing it was aimed at."""
    from checks.conformance import _asks_holistically

    assert _asks_holistically("Judge the overall quality of the block, but do not quote the source.")
    assert _asks_holistically("Rate the section out of 10; the block does not need a figure.")
    assert _asks_holistically("Say how good the argument is, if the claim is not cited.")

    # ...while the quotation each generated prompt carries stays exempt
    assert not _asks_holistically(
        '- Return a **binary** verdict — `pass` or `fail`. **Never** score holistic "quality", '
        '"thoroughness", or "how good"; holistic scoring is prohibited (`R-REJECT-05`).')
    assert not _asks_holistically("Do not rate the block out of 10.")
    assert not _asks_holistically("Avoid asking on a scale of 1-5.")


def test_the_rejected_technique_scan_reaches_past_the_checks_directory(tmp_path):
    """R-REJECT-01..04 forbid four techniques in the PIPELINE. Scanning `checks/` alone said nothing
    about the other five directories: surprisal as an editing target would land in render/ or
    critics/, an MECE gate in verify/, and neither was ever looked at."""
    from checks.conformance import REJECT_SCAN_DIRS

    assert set(REJECT_SCAN_DIRS) >= {"checks", "verify", "critics", "render"}

    root = tmp_path / "verify"
    root.mkdir()
    (root / "sneaky.py").write_text(
        'def gate(x):\n    raise ValueError("MECE partition required")\n', encoding="utf-8")
    assert no_rejected_techniques_are_implemented(root)


def test_purity_check_reports_a_missing_module_rather_than_passing(tmp_path):
    """A module that vanished must not read as pure — absence of evidence is the failure mode this
    whole registry exists to prevent."""
    problems = deterministic_modules_stay_pure({"R-CONV-02": tmp_path / "gone.py"})
    assert problems and "missing" in problems[0]


def test_holistic_prompt_is_caught(tmp_path):
    (tmp_path / "bad.md").write_text(
        "#### R-X-01 — something\n"
        "Rate the section out of 10 for overall quality.\n", encoding="utf-8")
    problems = critics_are_binary_only(tmp_path)
    assert problems and "holistic" in problems[0]


def test_a_clean_prompt_dir_passes(tmp_path):
    (tmp_path / "ok.md").write_text(
        "#### R-X-01 — something\n**Verdict question (binary):** Does the card open with an "
        "analogue? y/n\n", encoding="utf-8")
    assert critics_are_binary_only(tmp_path) == []


def test_rejected_techniques_are_caught_per_rule(tmp_path):
    (tmp_path / "mece_gate.py").write_text(
        "def check(ir):\n    return [] if is_mece(ir) else ['not MECE']\n", encoding="utf-8")
    problems = no_rejected_techniques_are_implemented(tmp_path)
    assert problems
    assert all(p.startswith("R-REJECT-03") for p in problems), problems


def test_a_rejected_technique_in_a_COMMENT_is_not_a_violation(tmp_path):
    """The evidence map discusses all four at length. A check that fired on discussion would be
    unfixable noise, so only executable lines count."""
    (tmp_path / "fine.py").write_text(
        "# we deliberately do NOT enforce MECE or E-Prime here\n"
        "def check(ir):\n    return []\n", encoding="utf-8")
    assert no_rejected_techniques_are_implemented(tmp_path) == []


def test_ir_canonical_check_catches_a_renderer_not_driven_by_the_ir(tmp_path):
    (tmp_path / "render_html.py").write_text(
        "def render_html(html_string, cm=None):\n    return html_string\n", encoding="utf-8")
    (tmp_path / "render_llm_md.py").write_text(
        "def render_llm_md(ir, cm=None):\n    return ''\n", encoding="utf-8")
    problems = ir_is_the_only_canonical_source(tmp_path)
    assert problems
    assert "render_html" in problems[0] and "second source" in problems[0]


def test_ir_canonical_check_catches_a_missing_renderer(tmp_path):
    (tmp_path / "render_llm_md.py").write_text("def render_llm_md(ir):\n    return ''\n",
                                               encoding="utf-8")
    problems = ir_is_the_only_canonical_source(tmp_path)
    assert any("render_html.py is missing" in p for p in problems)


def test_the_firewall_check_actually_exercises_the_firewall():
    """R-DISC-01 is asserted by RUNNING anchor_claims, not by observing that it exists. It must
    reject an absent quote, cite the rule when it does, and still accept a present one — a blanket
    refusal would pass a naive check while destroying every citation."""
    assert leads_are_never_evidence() == []


def test_swap_and_average_stays_out_of_the_pointwise_path():
    assert swap_and_average_is_pairwise_only() == []


# --- the stub inventory ------------------------------------------------------
#
# Not a registry rule; a claim CLAUDE.md makes about this tree. It used to say the scripts and the
# eval harness "are stubs that raise NotImplementedError", which stopped being true stages ago and
# stayed on the page — orientation a fresh agent reads first, describing a repo that no longer
# exists. Correcting the sentence is not enough on its own: the same drift can happen in the other
# direction, where a module is quietly reduced to a stub and nothing says so. So the inventory is
# pinned. `kb.py` is the one deliberate deferral (V2 Mixedbread source KB); anything else raising
# NotImplementedError at import is either a regression or a decision that belongs in the docs.

_ALLOWED_STUBS = {"scripts/research/kb.py"}


def test_the_only_deliberate_stub_is_the_deferred_source_kb():
    root = Path(__file__).resolve().parents[1]
    found = {
        str(p.relative_to(root)).replace("\\", "/")
        for p in (root / "scripts").rglob("*.py")
        if "NotImplementedError" in p.read_text(encoding="utf-8")
    }
    assert found == _ALLOWED_STUBS, (
        "the stub inventory moved — update CLAUDE.md and this set together, or restore the module"
    )
