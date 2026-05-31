"""Prompt 5 tests: six scoped binary passes, binary-only verdicts, test-retest, swap-and-average.

Done-condition: a run produces binary verdicts keyed by rule_id+block_id across all six passes,
with holistic scoring impossible by construction.
"""
import pytest

from critics.run_critics import (
    ModelJudge,
    StubJudge,
    compare_revisions,
    load_passes,
    run_critics,
)
from ir.schema import DocumentIR


def _ir(fixtures):
    return DocumentIR.from_yaml(fixtures / "document-ir.yaml")


# --- structure: six passes, binary verdicts keyed by rule_id+block_id --------

def test_six_passes_with_binary_verdicts(fixtures):
    report = run_critics(_ir(fixtures), StubJudge())
    assert len(report["passes"]) == 6
    pass_names = {p["pass"] for p in report["passes"]}
    assert pass_names == {
        "structure-architecture", "structure-fieldguide", "coherence",
        "expertise-calibration", "evidence-grounding", "figures",
    }
    all_verdicts = [v for p in report["passes"] for v in p["verdicts"]]
    assert all_verdicts, "every pass should yield verdicts on this fixture"
    for v in all_verdicts:
        assert set(v) >= {"rule_id", "block_id", "verdict", "evidence"}
        assert v["verdict"] in {"pass", "fail", "unstable"}  # binary (+ test-retest 'unstable') only


def test_every_pass_has_at_least_one_verdict(fixtures):
    for p in run_critics(_ir(fixtures))["passes"]:
        assert p["verdicts"], f"pass {p['pass']} produced no verdicts"


# --- holistic scoring impossible by construction -----------------------------

def test_non_binary_verdict_rejected_stub(fixtures):
    judge = StubJudge(responder=lambda pass_, rule, block, attempt: ("excellent", "holistic!"))
    with pytest.raises(ValueError, match="non-binary"):
        run_critics(_ir(fixtures), judge)


def test_non_binary_verdict_rejected_model(fixtures):
    judge = ModelJudge(responder=lambda prompt, rule, block: {"verdict": "8/10", "evidence": "score"})
    with pytest.raises(ValueError, match="non-binary"):
        run_critics(_ir(fixtures), judge)


def test_no_score_field_anywhere(fixtures):
    report = run_critics(_ir(fixtures))
    for p in report["passes"]:
        for v in p["verdicts"]:
            assert "score" not in v and "rating" not in v


# --- fail propagation --------------------------------------------------------

def test_fail_verdict_blocks(fixtures):
    def responder(pass_, rule, block, attempt):
        return ("fail", "card reads as a teaser") if rule == "R-CARD-01" else ("pass", "ok")
    report = run_critics(_ir(fixtures), StubJudge(responder=responder))
    card_fails = [v for p in report["passes"] for v in p["verdicts"]
                  if v["rule_id"] == "R-CARD-01" and v["verdict"] == "fail"]
    assert card_fails and report["blocking"] is True


# --- test-retest -------------------------------------------------------------

def test_gating_item_unstable_on_disagreement(fixtures):
    # R-CARD-01 is MUST (gating): flip the verdict between attempts -> 'unstable'
    def responder(pass_, rule, block, attempt):
        if rule == "R-CARD-01":
            return ("pass", "x") if attempt == 1 else ("fail", "y")
        return ("pass", "ok")
    report = run_critics(_ir(fixtures), StubJudge(responder=responder))
    unstable = [u for u in report["unstable_items"] if u["rule_id"] == "R-CARD-01"]
    assert unstable, "a gating rule that disagrees across retest must be 'unstable'"


def test_non_gating_item_not_retested(fixtures):
    # R-SCENT-02 is SHOULD (not gating): only attempt 1 is used, so flipping never yields 'unstable'
    def responder(pass_, rule, block, attempt):
        return ("pass", "x") if attempt == 1 else ("fail", "y")
    report = run_critics(_ir(fixtures), StubJudge(responder=responder))
    scent = [v for p in report["passes"] for v in p["verdicts"] if v["rule_id"] == "R-SCENT-02"]
    assert scent and all(v["verdict"] == "pass" for v in scent)


# --- prompt loading -----------------------------------------------------------

def test_load_passes_extracts_rules():
    passes = load_passes()
    assert len(passes) == 6
    fieldguide = next(rules for name, rules, _ in passes if name == "structure-fieldguide")
    assert "R-CARD-01" in fieldguide and "R-MV-01" in fieldguide


# --- swap-and-average (pairwise only) ----------------------------------------

def test_compare_revisions_cancels_position_bias():
    # a position-biased judge that always prefers whoever is presented first -> swap yields a tie
    def biased(rule, first, second):
        return "A"
    assert compare_revisions("R-X", "alpha", "beta", biased)["winner"] == "tie"


def test_compare_revisions_picks_better_content():
    # a content judge that prefers "good" regardless of order
    def judge(rule, first, second):
        return "A" if first == "good" else "B"
    result = compare_revisions("R-X", "good", "bad", judge)
    assert result["winner"] == "A" and result["score"]["A"] == 1.0
