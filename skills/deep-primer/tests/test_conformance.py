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
    assert problems and "judge" in problems[0].lower()


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
