"""Prompt 5 tests: six scoped binary passes, binary-only verdicts, test-retest, swap-and-average.

Done-condition: a run produces binary verdicts keyed by rule_id+block_id across all six passes,
with holistic scoring impossible by construction.
"""
import pytest

from critics.run_critics import (
    ModelJudge,
    StubJudge,
    applicable_blocks,
    compare_revisions,
    load_passes,
    run_critics,
)
from ir.schema import DocumentIR


def _ir(fixtures):
    return DocumentIR.from_yaml(fixtures / "document-ir.yaml")


def test_judge_failures_are_contained_but_contract_breaches_are_not(fixtures):
    """Two failures that must NOT be treated alike.

    An unreachable judge is operational — the first live run lost ~100 completed judgements to one
    timeout, so it is now recorded as 'error' per item and the run continues. A non-binary verdict
    is a breach of R-REJECT-05 and must still stop the run, or "holistic scoring is impossible by
    construction" quietly becomes false. 'error' is never coerced to 'pass': a judge that did not
    answer has not cleared the rule.
    """
    from critics.run_critics import JudgeResult, JudgeUnavailable, _validate_verdict

    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")

    def unreachable(*_args, **_kwargs):
        raise JudgeUnavailable("simulated timeout")

    report = run_critics(ir, unreachable)
    assert len(report["passes"]) == 6, "a failing judge must not abort the run"
    assert report["counts"]["pass"] == 0
    assert report["counts"]["error"] == len(report["errored_items"]) > 0

    def non_binary(*_args, **_kwargs):
        return JudgeResult(_validate_verdict("excellent"))

    with pytest.raises(ValueError, match="R-REJECT-05"):
        run_critics(ir, non_binary)


def test_claude_judge_errors_are_containable_and_strip_fences():
    """The CLI wraps JSON in ```json fences often enough that not stripping them would turn every
    verdict into an unparseable-output error."""
    from critics.claude_judge import JudgeError, JudgeTransient, _strip_fence
    from critics.run_critics import JudgeUnavailable

    assert issubclass(JudgeError, JudgeUnavailable)      # so run_pass contains it
    assert issubclass(JudgeTransient, JudgeError)
    assert _strip_fence('```json\n{"verdict":"pass"}\n```') == '{"verdict":"pass"}'
    assert _strip_fence('{"verdict":"fail"}') == '{"verdict":"fail"}'


def test_a_missing_verdict_field_is_malformed_output_not_a_contract_breach():
    """A response with no `verdict` key did not follow the output contract — retryable and
    containable. Only a verdict the model ASSERTED ("excellent") is the R-REJECT-05 breach that must
    stop the run. Conflating them killed a 45-minute run over a formatting slip."""
    from critics.claude_judge import ClaudeCliJudge
    from critics.run_critics import BlockView, JudgeUnavailable

    judge = ClaudeCliJudge.__new__(ClaudeCliJudge)     # no CLI, no IR render
    judge.max_attempts, judge._document_text = 1, ""
    judge._invoke = lambda _instruction: {"result": '{"evidence": "no verdict key"}'}

    # JudgeUnavailable is the property that matters: run_pass contains it, so the run survives
    with pytest.raises(JudgeUnavailable, match="no verdict"):
        judge("coherence", "prompt", "R-PROSE-02", BlockView("b1", "body", text="x"), 1)

    judge._invoke = lambda _instruction: {"result": '{"verdict": "excellent"}'}
    with pytest.raises(ValueError, match="R-REJECT-05"):
        judge("coherence", "prompt", "R-PROSE-02", BlockView("b1", "body", text="x"), 1)


def test_judge_unavailable_is_one_class_across_both_import_paths():
    """run_critics.py runs as a script, so it exists twice — as `__main__` and as
    `critics.run_critics`. An exception class defined there would be TWO classes, and the `except`
    in `__main__` would not catch the one `claude_judge` raised. That killed a completed 45-minute
    run whose containment logic was otherwise correct. Both must resolve to the same object."""
    import critics._errors
    import critics.run_critics
    from critics.claude_judge import JudgeError

    assert critics.run_critics.JudgeUnavailable is critics._errors.JudgeUnavailable
    assert issubclass(JudgeError, critics._errors.JudgeUnavailable)


def test_pass_level_output_shape_is_accepted():
    """The embedded pass prompt specifies `{"pass":..., "verdicts":[...]}`; the appended contract
    specifies a single verdict. Two instructions, one message — the model follows either. Rejecting
    the first shape discards a correct judgement over formatting."""
    from critics.claude_judge import _unwrap

    pass_shaped = {"pass": "structure-fieldguide", "verdicts": [
        {"rule_id": "R-OTHER-01", "block_id": "document", "verdict": "fail"},
        {"rule_id": "R-MV-01", "block_id": "document", "verdict": "pass", "evidence": "ok"},
    ]}
    assert _unwrap(pass_shaped, "R-MV-01", "document")["verdict"] == "pass"
    single = {"verdict": "fail", "evidence": "x"}
    assert _unwrap(single, "R-MV-01", "document") == single


def test_document_level_critics_can_see_section_headings(fixtures):
    """R-SCENT-01 judges whether headings are predictive claims. The LLM-MD projection is by design
    a flat block-addressable surface with NO section titles, so judging that rule against it failed
    a primer whose headings are exactly right — a false FAIL that reads as a defect in the primer.
    """
    from critics.claude_judge import _judge_document_view

    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")
    view = _judge_document_view(ir)
    for section in ir.sections:
        assert section.title in view, f"critic cannot see the heading {section.title!r}"


def test_structured_blocks_are_not_presented_empty_to_a_critic(fixtures):
    """A card's content IS its typed rows and a recall block's IS its Q&A items — neither sets
    `text`. The view handed judges `text or caption`, so both roles arrived EMPTY, and the first
    live judge run duly failed R-SUMM-04 on a card with "Card block contains no text" — a defect
    this seam manufactured rather than found. Four soft_critic rules target exactly these roles.
    """
    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")
    for rule_id in ("R-CARD-01", "R-CARD-03", "R-RECALL-02"):
        views = applicable_blocks(rule_id, ir)
        assert views, f"{rule_id} targets a role the fixture does not contain"
        for v in views:
            assert (v.text or "").strip(), f"{rule_id}/{v.block_id} reads as empty to a critic"


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


def test_gating_rules_route_to_the_gating_judge(fixtures):
    """MUST-priority rules are the ones that BLOCK, and are already judged twice for reliability.
    Measured on the reference fixture, haiku returned 6/21 unstable verdicts on gating items — a
    coin flip — against sonnet's 1/21, and hard-FAILED two items sonnet passed. Spending the better
    model exactly on the gating tier is the cheap half of that fix, so the routing must be exact."""
    from critics.run_critics import JudgeResult, _gating_rules, applicable_blocks, load_passes

    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")
    seen = {"main": 0, "gating": 0}

    def _judge(tag):
        def _call(_pass, _prompt, _rule, _block, _attempt):
            seen[tag] += 1
            return JudgeResult("pass", tag)
        return _call

    report = run_critics(ir, _judge("main"), gating_judge=_judge("gating"))

    gating = _gating_rules()
    expected_gating = sum(2 * len(applicable_blocks(r, ir))
                          for _n, ids, _p in load_passes() for r in ids if r in gating)
    expected_main = sum(len(applicable_blocks(r, ir))
                        for _n, ids, _p in load_passes() for r in ids if r not in gating)
    assert seen["gating"] == expected_gating
    assert seen["main"] == expected_main
    assert seen["gating"] > 0 and seen["main"] > 0

    # and with no gating judge supplied, everything goes to the single judge
    seen["main"] = seen["gating"] = 0
    run_critics(ir, _judge("main"))
    assert seen["gating"] == 0 and seen["main"] > 0
    assert report["counts"]["error"] == 0
