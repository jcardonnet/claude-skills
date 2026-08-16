"""Prompt 3 tests: citation recall/precision + deterministic ledger resolution.

Done-condition: on a fixture with one unsupported and one decorative citation, recall/precision
reflect them, and deterministic resolution flags the unledgered marker.
"""
import pytest

from ir.schema import DocumentIR, SourceLedger
from verify.citation_quality import (
    evaluate,
    load_thresholds,
    main,
    resolves_to_ledger,
    verify_files,
)
from verify._entailment import LexicalEntailment, resolve_backend


def _report(fixtures):
    return verify_files(fixtures / "verify-ir.yaml", fixtures / "verify-ledger.yaml", backend_name="lexical")


def test_recall_precision_reflect_planted_cases(fixtures):
    r = _report(fixtures)
    # B is unsupported -> recall = 2/3
    assert r["recall"] == pytest.approx(2 / 3, abs=1e-3)
    assert r["recall"] < r["thresholds"]["recall"]
    # B's C2 (unsupported) and C's C4 (decorative) are non-supporting -> precision = 2/4
    assert r["precision"] == pytest.approx(0.5, abs=1e-9)
    assert r["precision"] < r["thresholds"]["precision"]


def test_decorative_and_unsupported_citations_marked(fixtures):
    r = _report(fixtures)
    supports = {(c["block_id"], c["claim_id"]): c["supports"] for c in r["per_citation"]}
    assert supports[("A", "C1")] is True
    assert supports[("B", "C2")] is False   # unsupported
    assert supports[("C", "C3")] is True
    assert supports[("C", "C4")] is False   # decorative


def test_deterministic_resolution_flags_unledgered_marker(fixtures):
    r = _report(fixtures)
    assert r["resolves_to_ledger"]["ok"] is False
    markers = {v["marker"] for v in r["resolves_to_ledger"]["violations"]}
    assert "C99" in markers


def test_blocking_when_below_threshold(fixtures):
    assert _report(fixtures)["blocking"] is True


def test_resolves_to_ledger_unit(fixtures):
    ir = DocumentIR.from_yaml(fixtures / "verify-ir.yaml")
    ledger = SourceLedger.from_yaml(fixtures / "verify-ledger.yaml")
    viols = resolves_to_ledger(ir, ledger)
    assert [v["marker"] for v in viols] == ["C99"]
    assert viols[0]["marker_type"] == "claim_id"


def test_resolves_to_ledger_flags_unledgered_source_id():
    ir = DocumentIR(**{"sections": [{"block_id": "s", "title": "t", "blocks": [
        {"block_id": "b1", "role": "toulmin", "text": "alpha beta gamma", "claim_ids": ["K1"],
         "provenance": "verified", "source_ids": ["s1", "ghost-src"]}]}]})
    ledger = SourceLedger(**{"sources": [{"source_id": "s1",
        "claims": [{"claim_id": "K1", "text": "x", "quote": "alpha beta gamma delta"}]}]})
    viols = resolves_to_ledger(ir, ledger)
    assert [(v["marker_type"], v["marker"]) for v in viols] == [("source_id", "ghost-src")]
    report = evaluate(ir, ledger, backend=LexicalEntailment())
    assert report["blocking"] is True and report["resolves_to_ledger"]["ok"] is False


def test_thresholds_loaded_from_rubric():
    th = load_thresholds()
    assert th == {"recall": 0.75, "precision": 0.90}


def test_clean_primer_passes():
    """All citations supported, all resolvable -> recall=precision=1, not blocking."""
    ir = DocumentIR(**{
        "sections": [{
            "block_id": "s", "title": "t",
            "blocks": [{"block_id": "b1", "role": "toulmin", "text": "alpha beta gamma",
                        "claim_ids": ["K1"], "provenance": "verified", "source_ids": ["s1"]}],
        }],
    })
    ledger = SourceLedger(**{
        "sources": [{"source_id": "s1", "claims": [{"claim_id": "K1", "text": "x", "quote": "alpha beta gamma delta"}]}],
    })
    r = evaluate(ir, ledger, backend=LexicalEntailment())
    assert r["recall"] == 1.0 and r["precision"] == 1.0 and r["blocking"] is False
    assert r["resolves_to_ledger"]["ok"] is True


def test_backend_selection():
    assert resolve_backend("auto").name == "lexical"
    assert resolve_backend("lexical").name == "lexical"
    with pytest.raises(ValueError):
        resolve_backend("claude")  # needs an injected judge_fn
    assert resolve_backend("claude", judge_fn=lambda p, h: True).name == "claude"


def test_cli_exit_code(fixtures, tmp_path):
    out = tmp_path / "verify-report.json"
    code = main([str(fixtures / "verify-ir.yaml"), "--ledger", str(fixtures / "verify-ledger.yaml"),
                 "--backend", "lexical", "--out", str(out)])
    assert code == 1
    assert out.exists()


# --- the Claude entailment backend (the production judge_fn) ------------------
# resolve_backend("claude") has always raised without a judge_fn, and nothing supplied one — so
# every citation number the harness ever produced came from the lexical proxy. These pin the
# behaviour of the judge that closes that; the live model path is deliberately not tested.

def test_resolve_backend_claude_requires_and_uses_a_judge_fn():
    with pytest.raises(ValueError, match="judge_fn"):
        resolve_backend("claude")
    backend = resolve_backend("claude", judge_fn=lambda _p, _h: True)
    assert backend.name == "claude"
    assert backend.supports("anything", "anything") is True


def test_claude_entailment_treats_every_failure_as_not_supported():
    """A citation the verifier could not check has NOT been shown to be supported. Resolving the
    ambiguity the other way would let an outage, a malformed reply, or a hedge quietly RAISE the
    citation score — inflating the exact number the tier exists to police."""
    from utils.claude_cli import CliUnavailable
    from verify.claude_entailment import ClaudeEntailmentJudge

    judge = ClaudeEntailmentJudge()

    judge.cli.result_text = lambda _instruction: '{"supports": true, "why": "ok"}'
    assert judge("evidence", "statement") is True

    judge.cli.result_text = lambda _instruction: '{"supports": "probably", "why": "hedged"}'
    assert judge("evidence", "statement") is False

    judge.cli.result_text = lambda _instruction: "not json at all"
    assert judge("evidence", "statement") is False

    def _boom(_instruction):
        raise CliUnavailable("simulated outage")

    judge.cli.result_text = _boom
    assert judge("evidence", "statement") is False

    # every non-support above is recorded, never silently swallowed
    assert len(judge.unresolved) == 3


def test_claude_entailment_skips_empty_pairs_without_spending():
    from verify.claude_entailment import ClaudeEntailmentJudge

    judge = ClaudeEntailmentJudge()
    assert judge("", "statement") is False
    assert judge("evidence", "   ") is False
    assert judge.calls == 0


def test_extract_json_tolerates_packaging_but_not_absence():
    """Three separate runs in this project died on packaging — a ```json fence, a pass-level
    wrapper, an empty result — each discarding a correct answer over how it was wrapped. Parse
    leniently; the CONTENT is still validated strictly by the caller."""
    from utils.claude_cli import CliUnavailable, extract_json

    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here is the result:\n{"a": 1}\nHope that helps!') == {"a": 1}
    # a brace inside a string value must not end the scan early
    assert extract_json('{"a": "} not the end", "b": 2}') == {"a": "} not the end", "b": 2}
    assert extract_json('{"outer": {"inner": 1}}') == {"outer": {"inner": 1}}

    for bad in ("", "no json here at all", '{"unterminated": '):
        with pytest.raises(CliUnavailable):
            extract_json(bad)


def test_a_shared_budget_caps_the_run_not_each_caller():
    """`--gating-model` builds TWO CLI callers, one per model. Giving each the full --cost-cap meant
    a declared $9 ceiling could spend $18: a cap the user sets once is a cap on the RUN."""
    from utils.claude_cli import Budget, ClaudeCli, CliBudgetExceeded

    shared = Budget(cost_cap_usd=1.0)
    fast, strong = ClaudeCli(model="haiku", budget=shared), ClaudeCli(model="sonnet", budget=shared)

    shared.charge(0.6)
    with pytest.raises(CliBudgetExceeded, match=r"\$1\.20"):
        shared.charge(0.6)
    assert fast.spend_usd == strong.spend_usd == 1.2
    assert fast.calls == strong.calls == 2

    # and an unshared caller still gets its own ceiling
    solo = ClaudeCli(cost_cap_usd=1.0)
    assert solo.spend_usd == 0.0 and solo.budget is not shared
