"""Prompt 3 tests: citation recall/precision + deterministic ledger resolution.

Done-condition: on a fixture with one unsupported and one decorative citation, recall/precision
reflect them, and deterministic resolution flags the unledgered marker.
"""
from pathlib import Path

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

SKILL_ROOT = Path(__file__).resolve().parents[1]


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


def test_blocking_on_the_proxy_is_ledger_resolution_only(fixtures):
    """Renamed because it no longer proves what it said. On the lexical proxy the entailment
    thresholds do not gate — word overlap between a <=15-word quote and a required paraphrase is not
    evidence, which is why `propose_thresholds` refuses to fit a floor to it — so what blocks here is
    the unresolved C99 marker, a deterministic R-GROUND-01 MUST that binds on any backend.

    The old name claimed a threshold verdict this fixture never produced, and the assertion passed
    either way."""
    r = _report(fixtures)
    assert r["blocking"] is True
    assert r["resolves_to_ledger"]["ok"] is False

    # strip the one unresolvable marker and the proxy's own low scores block nothing
    ir = DocumentIR.from_yaml(fixtures / "verify-ir.yaml")
    ir.sections[0].blocks = [b for b in ir.sections[0].blocks if b.claim_ids != ["C99"]]
    ledger = SourceLedger.from_yaml(fixtures / "verify-ledger.yaml")
    proxy = evaluate(ir, ledger, backend=LexicalEntailment(), thresholds=load_thresholds())
    assert proxy["verified_recall"] < proxy["thresholds"]["verified_recall"]
    assert proxy["blocking"] is False


def test_a_real_backend_blocks_on_the_settled_thresholds(fixtures):
    """The half the CLI never had: below the verified pair on a backend worth trusting, it blocks.
    It used to block on the LEGACY pair instead — the one eval-rubric.yaml carries as an unfitted
    TODO and load_thresholds() describes as meaningless."""
    ir = DocumentIR.from_yaml(fixtures / "verify-ir.yaml")
    ir.sections[0].blocks = [b for b in ir.sections[0].blocks if b.claim_ids != ["C99"]]
    ledger = SourceLedger.from_yaml(fixtures / "verify-ledger.yaml")
    strict = evaluate(ir, ledger, backend=resolve_backend("claude", judge_fn=lambda _p, _h: False),
                      thresholds=load_thresholds())
    assert strict["resolves_to_ledger"]["ok"] is True
    assert strict["blocking"] is True

    lenient = evaluate(ir, ledger, backend=resolve_backend("claude", judge_fn=lambda _p, _h: True),
                       thresholds=load_thresholds())
    assert lenient["blocking"] is False


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
    # the verified_* pair is what --strict gates on; the legacy pair is kept for the pre-partition
    # report shape and mixes declared synthesis with claimed grounding
    assert th == {"recall": 0.75, "precision": 0.90,
                  "verified_recall": 0.95, "verified_precision": 0.90,
                  "max_inferred_share": 0.60}


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


class _CeilingCli:
    """Stand-in for ClaudeCli whose every entry point has already blown the run's ceiling."""

    model = "haiku"
    calls = 114
    spend_usd = 9.10

    def _boom(self, _instruction):
        from utils.claude_cli import CliBudgetExceeded
        raise CliBudgetExceeded("cost cap hit: $9.10 > $9.00 after 114 calls")

    __call__ = result_text = result_json = _boom


def test_a_judgement_call_carries_no_tool_schemas():
    """Every `claude -p` is a COLD session and re-pays the whole Claude Code preamble — system prompt
    plus every tool schema, MCP servers included — before reading the instruction. Measured on a
    10-token question: ~37,800 preamble tokens with the default tool set, ~15,900 with none. A critic
    run is 113 calls asking for one binary word each, so that is ~2.5M tokens recoverable for free.

    Omitting the flag does NOT mean "no tools"; it means the DEFAULT set. The empty `--tools` is what
    makes it explicit."""
    from utils.claude_cli import ClaudeCli

    argv = ClaudeCli()._argv("judge this")
    assert "--tools" in argv and argv[argv.index("--tools") + 1] == ""
    assert "--allowedTools" not in argv


def test_the_research_backend_is_the_one_caller_that_gets_tools():
    """A brief cannot be answered without retrieval, and a default-constructed caller has no tools —
    which would leave the backend answering from training data and returning URLs it recalls rather
    than URLs it read. `--permission-mode` matters too: non-interactively there is nobody to ask, so
    without it the CLI searches, cannot fetch, and gives up."""
    from research.claude_backend import ClaudeResearchBackend

    argv = ClaudeResearchBackend(verify_urls=False).cli._argv("run this brief")
    assert argv[argv.index("--allowedTools") + 1:argv.index("--allowedTools") + 3] == \
        ["WebSearch", "WebFetch"]
    assert argv[argv.index("--permission-mode") + 1] == "bypassPermissions"
    assert "--tools" not in argv


def test_a_hit_ceiling_is_not_catchable_as_an_ordinary_outage():
    """`CliBudgetExceeded` used to subclass `CliUnavailable`, so every caller written to absorb a
    per-item outage absorbed the run's ceiling too and the campaign carried on spending. The cap
    aborts only if its type cannot be caught by an `except` clause aimed at transients."""
    from utils.claude_cli import CliBudgetExceeded, CliUnavailable

    assert not issubclass(CliBudgetExceeded, CliUnavailable)
    with pytest.raises(CliBudgetExceeded):
        try:
            raise CliBudgetExceeded("cost cap hit")
        except CliUnavailable:                       # the shape every seam below writes
            pytest.fail("a per-item handler swallowed the run's spend ceiling")


def test_the_entailment_seam_stops_instead_of_scoring_the_rest_unsupported():
    """Absorbing an outage here is deliberate — an unverifiable citation has not been shown
    supported. Absorbing the CEILING means the remaining citations all score `not supported` and
    the primer is blamed for the bill."""
    from utils.claude_cli import CliBudgetExceeded
    from verify.claude_entailment import ClaudeEntailmentJudge

    with pytest.raises(CliBudgetExceeded):
        ClaudeEntailmentJudge(cli=_CeilingCli())("a premise about chunking", "a hypothesis")


def test_the_structure_judge_seam_stops_instead_of_settling_the_loop():
    """The damaging one: `None` from this judge means "no structural finding", which is the answer
    that TERMINATES the convergence loop as `coherent`. On a hit ceiling that is a settled verdict
    from a judge that never answered."""
    from ir.schema import Concept, ConceptMap
    from research.claude_structure_judge import ClaudeStructureJudge
    from utils.claude_cli import CliBudgetExceeded

    cm = ConceptMap(concepts=[Concept(concept_id="c", canonical_term="C", home_anchor="h")])
    with pytest.raises(CliBudgetExceeded):
        ClaudeStructureJudge(cli=_CeilingCli()).scan_for_structural(cm, {"target_domain": "d"})


def test_the_research_backend_seam_stops_instead_of_reporting_an_empty_wave():
    """An empty wave is a real outcome, and it is also what saturation looks like: a ceiling hit
    mid-campaign would otherwise read as "nothing new was found" and freeze the snapshot."""
    from research.claude_backend import ClaudeResearchBackend
    from research.planner import ResearchBrief
    from utils.claude_cli import CliBudgetExceeded

    brief = ResearchBrief(wave="A", framing="structure", questions=["q"], brief_id="A-test")
    backend = ClaudeResearchBackend(cli=_CeilingCli(), verify_urls=False)
    with pytest.raises(CliBudgetExceeded):
        backend(brief)


# --- the provenance partition ------------------------------------------------

def _ir_with(provenances):
    """Two blocks citing the same claim; only their declared provenance differs."""
    from ir.schema import Block, DocumentIR, Section

    return DocumentIR(sections=[Section(block_id="s", title="T", concept="c", blocks=[
        Block(block_id=f"b{i}", role="body", text="chunking bounds recall", concept="c",
              claim_ids=["C1"], provenance=p)
        for i, p in enumerate(provenances)])])


def _ledger_supporting(text="chunking bounds recall"):
    from ir.schema import Claim, Source, SourceLedger

    return SourceLedger(sources=[Source(source_id="s1", claims=[
        Claim(claim_id="C1", text=text, quote=text)])])


def test_labelling_everything_unverified_does_not_clear_the_gate():
    """`verified | inferred` is not exhaustive — `Provenance` also has `unverified`, and a block may
    carry claim_ids with no tag at all. Both fell between the buckets every threshold reads, so a
    primer could clear all three at once by grounding nothing and admitting it."""
    from verify._entailment import LexicalEntailment
    from verify.citation_quality import evaluate

    for label in ("unverified", None):
        r = evaluate(_ir_with([label, label]), _ledger_supporting(), backend=LexicalEntailment())
        # the vacuous readings are still reported, and still vacuous
        assert r["verified_recall"] == 1.0 and r["verified_precision"] == 1.0
        assert r["inferred_share"] == 0.0
        # ...but composition now measures the whole population, so nothing is hidden
        assert r["ungrounded_share"] == 1.0
        assert r["counts"]["untagged_or_unverified_statements"] == 2


def test_a_primer_that_cites_nothing_is_unscoreable_not_clean():
    """With no claim-bearing block every ratio reports its PASSING value by vacuous truth, so an
    empty artifact cleared R-GROUND-02/03 outright."""
    from ir.schema import Block, DocumentIR, Section
    from verify._entailment import LexicalEntailment
    from verify.citation_quality import evaluate

    ir = DocumentIR(sections=[Section(block_id="s", title="T", blocks=[
        Block(block_id="b", role="body", text="a sentence citing nothing")])])
    r = evaluate(ir, _ledger_supporting(), backend=LexicalEntailment())
    assert r["recall"] == 1.0 and r["precision"] == 1.0 and r["verified_recall"] == 1.0
    assert r["scoreable"] is False
    assert r["counts"]["factual_statements"] == 0


def test_the_two_citation_gates_are_one_function():
    """`score_spec` checked recall+precision on ANY backend and dropped `meets_composition` — the
    guard that exists because the other two are vacuous — while `_spec_strict_failures` twenty lines
    away checked all three and only on a real backend. Two judgements, already disagreeing."""
    from eval import _citation_shortfall

    ok = {"status": "scored", "backend": "lexical", "meets_recall": True,
          "meets_precision": True, "meets_composition": True}
    assert _citation_shortfall(ok) is None

    # the ENTAILMENT pair is what the proxy cannot speak to, and only that pair
    proxy = {**ok, "meets_recall": False, "meets_precision": False}
    assert _citation_shortfall(proxy) is None, "proxy entailment numbers gate nothing"
    assert _citation_shortfall({**proxy, "backend": "nli"}), "a real backend gates them"


def test_composition_gates_on_every_backend_because_no_backend_computes_it():
    """The split is by what the measurement DEPENDS ON, not by which function asks.
    `ungrounded_share` and `scoreable` come from provenance tags and claim counts — no
    `backend.supports()` call is involved — so they mean the same thing everywhere.

    The first version of this gate put them behind the proxy bypass, which made the guard
    unreachable in the only configuration that runs offline and in CI. That is where it was needed:
    spec-02 is 13 claim-bearing blocks, ALL `inferred`, ungrounded_share 1.00 against a 0.60 cap
    eval-rubric.yaml says exists to "fail a primer that is entirely synthesis" — and it passed."""
    from eval import _citation_shortfall

    for backend in ("lexical", "nli", "claude"):
        mv = {"status": "scored", "backend": backend, "meets_recall": True,
              "meets_precision": True, "meets_composition": False, "ungrounded_share": 1.0,
              "scoreable": True, "thresholds": {"max_inferred_share": 0.6}}
        shortfall = _citation_shortfall(mv)
        assert shortfall and "composition" in shortfall, f"{backend} let composition through"
        assert "1.0" in shortfall


def test_the_composition_guard_binds_the_shipped_artifacts_on_the_offline_backend():
    """End-to-end on the real fixtures, since the unit test above could pass on a mock alone.
    spec-01 is 4/7 verified and clears the cap; spec-02 grounds nothing and must not."""
    from ir.schema import DocumentIR, SourceLedger
    from verify.citation_quality import evaluate, load_thresholds

    root = SKILL_ROOT / "tests" / "fixtures"
    one = evaluate(DocumentIR.from_yaml(root / "document-ir.full.yaml"),
                   SourceLedger.from_yaml(root / "source-ledger.full.yaml"),
                   backend=LexicalEntailment(), thresholds=load_thresholds())
    assert one["ungrounded_share"] == pytest.approx(3 / 7, abs=1e-3)
    assert one["blocking"] is False, "a primer with a grounded spine must still pass offline"

    two = evaluate(DocumentIR.from_yaml(root / "spec02" / "document-ir.yaml"),
                   SourceLedger.from_yaml(root / "spec02" / "source-ledger.yaml"),
                   backend=LexicalEntailment(), thresholds=load_thresholds())
    assert two["counts"]["verified_statements"] == 0
    assert two["ungrounded_share"] == 1.0
    assert two["blocking"] is True, "an artifact that grounds nothing must not read as clean"


def test_inferred_blocks_are_scored_separately_from_verified_ones():
    """A block marked `inferred` is the author saying "this is my synthesis". Counting it in the
    same denominator as a `verified` block means a primer that labels its unsupported content
    HONESTLY scores identically to one that fabricates citations — which deletes the incentive to
    label honestly, the opposite of what R-GROUND-* is for. Measured on spec-02: 0.15 overall,
    1/2 on the blocks it actually claims are verified, and 11 declared synthesis."""
    from verify._entailment import LexicalEntailment
    from verify.citation_quality import evaluate

    ir = _ir_with(["verified", "inferred", "inferred"])
    report = evaluate(ir, _ledger_supporting(), backend=LexicalEntailment())

    assert report["counts"]["factual_statements"] == 3
    assert report["counts"]["verified_statements"] == 1
    assert report["counts"]["inferred_statements"] == 2
    assert report["inferred_share"] == round(2 / 3, 4)
    # every block cites a supporting quote here, so both views are clean...
    assert report["verified_recall"] == 1.0


def test_honest_labelling_is_not_punished_like_fabrication():
    """The property that matters. Two primers cite the SAME unsupported claim; one declares the
    blocks inferred, the other asserts they are verified. Overall recall cannot tell them apart —
    verified_recall must."""
    from verify._entailment import LexicalEntailment
    from verify.citation_quality import evaluate

    unsupported = _ledger_supporting("something else entirely unrelated to the block")
    honest = evaluate(_ir_with(["inferred", "inferred"]), unsupported, backend=LexicalEntailment())
    asserted = evaluate(_ir_with(["verified", "verified"]), unsupported, backend=LexicalEntailment())

    assert honest["recall"] == asserted["recall"], "overall recall is blind to the difference"
    assert honest["verified_recall"] == 1.0, "no verified claims to fail"
    assert asserted["verified_recall"] == 0.0, "asserting verified and failing entailment IS a defect"
    assert honest["inferred_share"] == 1.0 and asserted["inferred_share"] == 0.0


def test_entailment_votes_take_a_majority_and_record_the_splits():
    """Two runs over identical artifacts gave spec-01 4/7 then 3/7. A threshold fitted to a judge
    that moves like that measures the judge, so calibration runs vote — and a split ballot is
    recorded rather than smoothed away, because it is the number that says whether a threshold is
    fittable yet."""
    from verify.claude_entailment import ClaudeEntailmentJudge

    judge = ClaudeEntailmentJudge.__new__(ClaudeEntailmentJudge)
    judge.unresolved, judge.flipped, judge.votes = [], [], 3
    ballots = iter([True, False, True])
    judge.cli = type("_Cli", (), {
        "result_json": staticmethod(lambda _i: {"supports": next(ballots)})})()

    assert judge("evidence", "statement") is True          # 2 of 3
    assert judge.flipped and judge.flipped[0].startswith("2/3")


def test_votes_are_forced_odd_so_a_ballot_cannot_tie():
    from verify.claude_entailment import ClaudeEntailmentJudge

    assert ClaudeEntailmentJudge(votes=2).votes == 3
    assert ClaudeEntailmentJudge(votes=4).votes == 5
    assert ClaudeEntailmentJudge(votes=1).votes == 1


# --- per-unit entailment for composite blocks --------------------------------

def test_a_card_is_entailed_per_row_not_as_one_blob():
    """A card is seven typed rows and R-GROUND-01 caps a quote at 15 words, so no quote can entail
    the concatenation — every card in spec-01 failed for that structural reason rather than because
    its citation was bad. A citation supports the block when it entails what the block ASSERTS."""
    from ir.schema import Block, CardRows

    card = Block(block_id="c", role="card", claim_ids=["C1"], rows=CardRows(
        idea="Chunking is the retrieval unit and bounds recall.",
        home_anchor="Like a B-tree index, but for nearest rather than equal.",
        whats_new_vs_renamed="Granularity is renamed; the embedding scope is new.",
        reach_for_when="Reach for smaller chunks when queries target specific facts.",
        skip_when="Skip re-chunking when the failure is ordering rather than recall.",
        key_exemplar="A 200-token window over a heading-split corpus.",
        confidence="settled for the recall bound"))

    units = [u.text for u in card.entailment_units]
    assert units == ["Chunking is the retrieval unit and bounds recall.",
                     "A 200-token window over a heading-split corpus."]
    # the framing rows are deliberately absent — no source states an author's skip-condition
    joined = " ".join(units)
    for framing in ("B-tree", "Skip re-chunking", "Granularity is renamed", "settled"):
        assert framing not in joined


def test_a_simple_block_is_unchanged_by_the_unit_split():
    from ir.schema import Block

    b = Block(block_id="b", role="body", text="Chunking bounds recall.", claim_ids=["C1"])
    assert [u.text for u in b.entailment_units] == ["Chunking bounds recall."]


def test_a_recall_block_is_entailed_on_its_answers():
    from ir.schema import Block, RecallItem

    b = Block(block_id="r", role="recall", claim_ids=["C1"], items=[
        RecallItem(question="What caps recall?", answer="The chunk boundary does."),
        RecallItem(question="And then?", answer="Reranking cannot recover it.")])
    assert [u.text for u in b.entailment_units] == ["The chunk boundary does.",
                                                    "Reranking cannot recover it."]


def test_per_unit_scoring_rescues_a_card_a_blob_comparison_would_fail():
    """The regression this fixes: the quote entails the card's `idea` exactly, but is swamped when
    compared against all seven rows joined."""
    from ir.schema import Block, CardRows, Claim, DocumentIR, Section, Source, SourceLedger
    from verify._entailment import LexicalEntailment
    from verify.citation_quality import evaluate

    quote = "chunking is the retrieval unit and bounds recall"
    card = Block(block_id="card", role="card", concept="c", claim_ids=["C1"], provenance="verified",
                 rows=CardRows(
                     idea="Chunking is the retrieval unit and bounds recall.",
                     home_anchor="Like a SQL B-tree index but for nearest instead of equal, "
                                 "which is a different traversal entirely.",
                     whats_new_vs_renamed="Granularity is renamed rather than new here.",
                     reach_for_when="Reach for smaller chunks when queries target specific facts.",
                     skip_when="Skip re-chunking when the failure is ordering rather than recall.",
                     key_exemplar="A 200-token window.",
                     confidence="settled"))
    ir = DocumentIR(sections=[Section(block_id="s", title="T", concept="c", blocks=[card])])
    ledger = SourceLedger(sources=[Source(source_id="s1", claims=[
        Claim(claim_id="C1", text=quote, quote=quote)])])

    report = evaluate(ir, ledger, backend=LexicalEntailment())
    assert report["verified_recall"] == 1.0, "the quote entails the card's idea row exactly"
