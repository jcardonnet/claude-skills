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


def test_an_advisory_failure_does_not_block(fixtures):
    """Blocking derives from PRIORITY, not from the existence of a failure. R-SCENT-02 is SHOULD, so
    it warns; this read `any fail` and exited a critic pass non-zero — failing CI — on an advisory
    judgement from the tier the registry deliberately calls soft."""
    def responder(pass_, rule, block, attempt):
        return ("fail", "heading is a topic label") if rule == "R-SCENT-02" else ("pass", "ok")

    report = run_critics(_ir(fixtures), StubJudge(responder=responder))
    assert report["counts"]["fail"] > 0, "the fixture must actually produce the failure"
    assert report["blocking"] is False
    assert {f["rule_id"] for f in report["advisory_failures"]} == {"R-SCENT-02"}
    assert report["blocking_failures"] == []

    # ...and the MUST half still blocks, so this is not a blanket downgrade
    def must_fail(pass_, rule, block, attempt):
        return ("fail", "card reads as a teaser") if rule == "R-CARD-01" else ("pass", "ok")

    strict = run_critics(_ir(fixtures), StubJudge(responder=must_fail))
    assert strict["blocking"] is True
    assert {f["rule_id"] for f in strict["blocking_failures"]} == {"R-CARD-01"}


def test_a_hit_ceiling_stops_the_critic_run_rather_than_erroring_every_item(fixtures):
    """`run_pass` contains `JudgeUnavailable` per item ON PURPOSE — one bad call must not discard a
    45-minute run. `claude_judge._invoke` used to translate `CliBudgetExceeded` into `JudgeError`,
    which subclasses it, so the ceiling landed in exactly that containment: the run kept calling,
    kept paying, and stamped every remaining (rule, block) as verdict "error".

    Making `CliBudgetExceeded` a sibling of `CliUnavailable` fixed the research, entailment and
    structure-judge seams. This one had re-created the swallow by hand, one layer up."""
    from utils.claude_cli import CliBudgetExceeded

    class _CeilingJudge:
        calls = 0

        def __call__(self, pass_name, prompt, rule_id, block, attempt):
            type(self).calls += 1
            raise CliBudgetExceeded("cost cap hit: $9.10 > $9.00 after 114 calls")

    judge = _CeilingJudge()
    with pytest.raises(CliBudgetExceeded):
        run_critics(_ir(fixtures), judge)
    assert judge.calls == 1, "the run must stop on the first refusal, not walk the whole registry"


def test_an_ordinary_judge_outage_is_still_contained_per_item(fixtures):
    """The other half — without it the fix above would just be "abort on anything"."""
    from critics._errors import JudgeUnavailable

    class _Flaky:
        def __call__(self, pass_name, prompt, rule_id, block, attempt):
            raise JudgeUnavailable("simulated per-item outage")

    report = run_critics(_ir(fixtures), _Flaky())
    assert report["counts"]["error"] > 1, "a per-item outage must not stop the run"


def test_a_shared_budget_is_not_counted_once_per_judge():
    """`--gating-model` builds two judges against ONE Budget — that is what makes --cost-cap a
    ceiling on the run — and `calls`/`spend_usd` read straight through to it. Summing the two
    reported exactly double, so every cost figure quoted from a gated run was 2x."""
    from utils.claude_cli import Budget, ClaudeCli

    shared = Budget(cost_cap_usd=100.0)
    fast, strong = ClaudeCli(model="haiku", budget=shared), ClaudeCli(model="sonnet", budget=shared)
    shared.charge(3.0)
    shared.charge(6.0)

    assert fast.calls == strong.calls == shared.calls == 2
    assert fast.spend_usd == strong.spend_usd == shared.spend_usd == 9.0
    assert fast.calls + strong.calls != shared.calls, "the doubling this guards against"


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


def test_a_block_scoped_judgement_cannot_see_the_rest_of_the_document(fixtures, tmp_path):
    """GAPS G14's load-bearing fact. `R-SUMM-01 [lede-reranking]` passed in one judged run and
    failed in the next with that block's text byte-identical between them, and the diagnosis —
    judge drift, not an artifact defect — rests entirely on the two PROMPTS having been identical
    too. That is a property of the code, so it is asserted here rather than asserted in prose.

    A block-scoped rule's instruction is built from `block_id/role/concept/mode` and the block's own
    `readable_text`. Nothing else in the IR reaches it, so editing any other block leaves it byte
    for byte the same. The mutation used is the one that actually staled the last report (a
    `verified` -> `inferred` relabel plus a text change), and it lands on the SIBLING lede so the
    unchanged neighbour is as close as the document allows.

    The document-scoped half is what stops this from being un-failable: `_DOC_VIEW` carries no text,
    so the judge substitutes the whole rendered projection, and there the same edit MUST show up.
    Without that assertion a `_unit_text` that returned "" for everything would pass the first half.
    """
    import yaml
    from critics.claude_judge import ClaudeCliJudge

    def _instruction_for(ir_path, rule_id, block_id):
        ir = DocumentIR.from_yaml(ir_path)
        judge = ClaudeCliJudge(ir)
        seen = []
        judge._cli = lambda text: (seen.append(text),
                                   {"result": '{"verdict": "pass", "evidence": "-"}'})[1]
        block = next(b for b in applicable_blocks(rule_id, ir) if b.block_id == block_id)
        judge("summary", "<pass prompt>", rule_id, block, 1)
        return seen[0]

    original = fixtures / "document-ir.full.yaml"
    raw = yaml.safe_load(original.read_text(encoding="utf-8"))
    edited = [b for s in raw["sections"] for b in s["blocks"] if b["block_id"] == "lede-chunking"]
    assert len(edited) == 1, "fixture drifted: the sibling lede this test mutates is gone"
    edited[0]["text"] = "Chunking decides what retrieval can ever return."
    edited[0]["provenance"] = "inferred"
    mutated = tmp_path / "document-ir.mutated.yaml"
    mutated.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    assert (_instruction_for(original, "R-SUMM-01", "lede-reranking")
            == _instruction_for(mutated, "R-SUMM-01", "lede-reranking"))
    assert (_instruction_for(original, "R-ARCH-01", "document")
            != _instruction_for(mutated, "R-ARCH-01", "document"))
