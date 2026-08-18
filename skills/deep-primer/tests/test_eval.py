"""Eval-harness tests (Prompt 7 / Stage E).

The harness's job is to be honest about what it measured. Most of these pin that: a spec with no
artifact must not read as a pass, an expected rule that never ran must not read as a pass, and a
threshold must not be proposed from a backend that cannot support one.
"""
import json
from pathlib import Path

import yaml

from eval import (
    _spec_strict_failures,
    _tier_soft_critic,
    _why_unexercised,
    coverage_gate,
    load_specs,
    propose_thresholds,
    registry_rule_ids,
    registry_rules,
    resolve_artifacts,
    run_eval,
    score_spec,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = SKILL_ROOT / "references" / "eval" / "specs"


def test_every_shipped_spec_parses_and_declares_parameters():
    specs = load_specs(SPEC_DIR)
    assert len(specs) >= 5, "Prompt 7 asks for 5-8 specs"
    for s in specs:
        assert s["id"] and s["parameters"]
        for key in ("home_domain", "target_domain", "seniority_band", "length_budget"):
            assert key in s["parameters"], f"{s['id']} missing {key}"


def test_specs_span_seniority_bands_and_budgets():
    """A single-band spec set would never exercise the expertise-reversal scaling."""
    specs = load_specs(SPEC_DIR)
    bands = {s["parameters"]["seniority_band"] for s in specs}
    budgets = {s["parameters"]["length_budget"] for s in specs}
    assert len(bands) >= 2 and len(budgets) >= 4


def test_spec_without_an_artifact_is_not_generated_not_passed():
    """An eval that silently scores nothing reads as a green run — the failure this prevents."""
    result = score_spec({"id": "spec-x", "parameters": {}})
    assert result["status"] == "not_generated"
    assert not result.get("passed")


def test_missing_artifact_paths_are_dropped_rather_than_crashing():
    spec = {"id": "spec-x", "artifact": {"ir": "tests/fixtures/does-not-exist.yaml"}}
    assert resolve_artifacts(spec, SKILL_ROOT) == {}


def test_reference_spec_scores_all_deterministic_tiers():
    report = run_eval(SPEC_DIR, SKILL_ROOT, only="spec-01-rag-chunking")
    result = report["results"][0]
    assert result["status"] == "scored"
    hard = result["hard_lints"]
    assert hard["counts"].get("fail", 0) == 0
    assert hard["coverage"]["unenforced_musts"] == []
    # every deterministic pass ran against the reference artifact
    for pass_name in ("ledger_pass", "html_pass", "projections_pass", "llm_md_pass"):
        assert pass_name in hard, f"{pass_name} did not run"
    assert hard["projections_pass"]["ok"]


def test_expected_rule_that_never_ran_is_not_counted_as_passing():
    spec = {
        "id": "spec-probe",
        "artifact": {"ir": "tests/fixtures/document-ir.full.yaml",
                     "concept_map": "tests/fixtures/concept-map.full.yaml",
                     "ledger": "tests/fixtures/source-ledger.full.yaml"},
        "expect": {"must_pass": ["R-DISC-02"]},   # needs a discovery artifact this spec lacks
    }
    result = score_spec(spec, SKILL_ROOT)
    assert "R-DISC-02" in result["expected_must_pass_report"]["not_exercised"]
    assert result["passed"] is False


def test_unexercised_reasons_distinguish_a_judge_gap_from_a_silent_skip():
    """Collapsing the two hides the second, which is the whole Stage A finding."""
    assert "soft_critic" in _why_unexercised("R-CARD-01")
    assert "human" in _why_unexercised("R-REJECT-01")
    assert "discovery" in _why_unexercised("R-DISC-02")


def test_enforcement_coverage_is_reported_per_tier():
    report = run_eval(SPEC_DIR, SKILL_ROOT, only="spec-01-rag-chunking")
    cov = report["enforcement_coverage"]
    assert cov["rules_total"] > 0
    by = cov["by_enforcement"]
    assert set(by) >= {"hard_lint", "soft_critic", "model_verified", "human"}
    # the deterministic tier is the one this harness can actually score
    assert by["hard_lint"]["fraction"] > 0.5
    assert by["model_verified"]["exercised"] >= 2


def test_thresholds_are_refused_when_only_the_lexical_proxy_scored():
    """The proxy measures overlap between a <=15-word quote and a paraphrased block; a floor
    derived from it would silently disable the citation check."""
    report = run_eval(SPEC_DIR, SKILL_ROOT, only="spec-01-rag-chunking")
    proposal = propose_thresholds(report)
    assert proposal["status"] == "refused"
    assert "lexical" in proposal["reason"] or "lexical" in str(proposal["observed"])
    assert "citation_recall" not in proposal


def test_thresholds_are_proposed_from_a_real_backend():
    fake = {"results": [{"model_verified": {"status": "scored", "backend": "nli",
                                            "recall": 0.9, "precision": 0.95}}]}
    proposal = propose_thresholds(fake)
    assert proposal["status"] == "proposed"
    assert proposal["citation_recall"] == 0.85 and proposal["citation_precision"] == 0.9


def test_rubric_thresholds_are_still_the_documented_todos():
    """Guards against a floor derived from too little evidence being written into the rubric.

    A real backend now exists (`verify/claude_entailment.py`), and scoring spec-01 with it gives
    recall 0.5714 / precision 0.5 — roughly 4x what the lexical proxy reports (0.1429 / 0.125),
    which is the proxy understating a compliant paraphrasing primer exactly as designed.
    `propose_thresholds()` accordingly stops refusing and proposes 0.52 / 0.45.

    Those are deliberately NOT adopted. The denominators are 7 factual statements and 8 citations,
    on a hand-built reference fixture rather than a real generation — a project-wide quality floor
    set from that would be calibration theatre, and `propose_thresholds` says so itself in its
    caveat. Settle them in Stage G, against real runs and more than one spec.
    """
    rubric = yaml.safe_load((SKILL_ROOT / "references" / "eval" / "eval-rubric.yaml").read_text())
    th = rubric["model_verified"]["thresholds"]
    assert th["citation_recall"] >= 0.7 and th["citation_precision"] >= 0.85


# --- the coverage gate -------------------------------------------------------
# `enforcement_coverage` was reported from Prompt 7 onward but nothing ever failed on it. These pin
# the gate that closed that: coverage is now a ratchet, not a readout.

def test_coverage_gate_passes_on_the_shipped_artifacts():
    report = run_eval(SPEC_DIR, SKILL_ROOT, only="spec-01-rag-chunking")
    gate = report["coverage_gate"]
    assert gate["passed"], gate
    assert not gate["silent_skips"] and not gate["shortfalls"] and not gate["spec_failures"]


def test_coverage_gate_fails_when_a_tier_regresses():
    """The ratchet's whole job: dropping a rule below the declared floor must fail, not just print.

    Baselines against the FULL spec set, not a narrowed run — a floor counts rules exercised across
    every spec, and no single spec reaches it (spec-01 has no campaign artifacts, spec-02 has no
    critic report). Narrowing here is what made this test fail when the hard_lint floor rose.
    """
    report = run_eval(SPEC_DIR, SKILL_ROOT)
    exercised = set(registry_rule_ids()) - set(report["enforcement_coverage"]["unexercised"])
    assert coverage_gate(exercised, [])["passed"], "baseline must be green before thinning it"

    hard_lint_ids = {r["id"] for r in registry_rules() if r["enforcement"] == "hard_lint"}
    thinned = exercised - {min(exercised & hard_lint_ids)}
    gate = coverage_gate(thinned, [])
    assert not gate["passed"]
    assert any(s["tier"] == "hard_lint" for s in gate["shortfalls"])


def test_r_proj_04_is_actually_exercised():
    """It is model_verified/MUST and the verifier was unit-tested from Stage A, but eval never
    called it — so it read as unexercised forever while looking identical to a passing rule."""
    report = run_eval(SPEC_DIR, SKILL_ROOT, only="spec-01-rag-chunking")
    assert "R-PROJ-04" not in report["enforcement_coverage"]["unexercised"]
    mv = report["results"][0]["model_verified"]
    assert mv["chunk_selfcontained"]["blocks"] > 0


def _critic_report(path: Path, *, exercised: bool, verdict: str) -> Path:
    path.write_text(json.dumps({
        "judge": {"kind": "claude" if exercised else "stub", "exercised_rules": exercised},
        "counts": {"pass": 1, "fail": 1 if verdict == "fail" else 0, "unstable": 0},
        "passes": [{"pass": "coherence", "rules": ["R-PROSE-02"], "verdicts": [
            {"rule_id": "R-PROSE-02", "block_id": "b1", "verdict": verdict, "evidence": ""}]}],
    }), encoding="utf-8")
    return path


def test_a_stub_critic_report_is_never_counted_as_coverage(tmp_path):
    """StubJudge returns 'pass' for every (rule, block) without consulting anything. Crediting its
    report would manufacture a green 35/35 soft_critic tier out of a judge that never read a word —
    Stage A's silent-skip failure with the sign flipped, and flattering enough to survive review."""
    stub = _critic_report(tmp_path / "stub.json", exercised=False, verdict="pass")
    tier = _tier_soft_critic({"critic_report": stub})
    assert tier["status"] == "stub_only"
    assert tier["rules_exercised"] == []


def test_a_real_critic_report_scores_and_credits_the_tier(tmp_path):
    real = _critic_report(tmp_path / "real.json", exercised=True, verdict="fail")
    tier = _tier_soft_critic({"critic_report": real})
    assert tier["status"] == "scored"
    assert tier["rules_exercised"] == ["R-PROSE-02"]
    assert tier["failed"] == ["R-PROSE-02"]


def test_lexical_backend_does_not_trip_the_citation_gate():
    """propose_thresholds() refuses to derive a floor from the lexical proxy because its numbers are
    meaningless for a paraphrasing primer. Failing --strict on those same numbers would be
    incoherent, and would leave the gate permanently red offline."""
    results = [{
        "id": "spec-x", "status": "scored",
        "hard_lints": {"blocking": False},
        "model_verified": {"status": "scored", "backend": "lexical", "recall": 0.1,
                           "precision": 0.1, "meets_recall": False, "meets_precision": False},
        "expected_must_pass_report": {"failed": [], "not_exercised": []},
    }]
    assert _spec_strict_failures(results, registry_rules()) == []

    results[0]["model_verified"]["backend"] = "nli"
    failures = _spec_strict_failures(results, registry_rules())
    assert len(failures) == 1 and "citation quality" in failures[0]["reasons"][0]


# --- the two verdicts that were computed and read by no gate ------------------

def _scored(**tiers) -> list[dict]:
    """A minimal `scored` result with every gate quiet, so each test turns exactly one knob."""
    base = {
        "id": "spec-x", "status": "scored",
        "hard_lints": {"blocking": False, "unenforced_musts": []},
        "model_verified": {"status": "scored", "backend": "lexical",
                           "chunk_selfcontained": {"ok": True, "backend": "lexical",
                                                   "failures": [], "dangling_failures": []}},
        "expected_must_pass_report": {"failed": [], "not_exercised": []},
    }
    for tier, patch in tiers.items():
        base[tier] = {**base[tier], **patch}
    return [base]


def test_the_baseline_scored_result_trips_no_gate():
    """Guards the three tests below: if this ever fails they stop proving what they claim."""
    assert _spec_strict_failures(_scored(), registry_rules()) == []


def test_a_must_rule_that_dispatches_to_nothing_fails_the_strict_gate():
    """`run_artifact_pass` has computed `unenforced_musts` since Stage A and only `lint.py --strict`
    ever read it — for the IR pass alone. A MUST rule in one of the six non-IR passes pointing at a
    check that does not exist scored 100% coverage and exited 0."""
    failures = _spec_strict_failures(
        _scored(hard_lints={"unenforced_musts": ["R-FAKE-99"]}), registry_rules())
    assert len(failures) == 1
    assert "R-FAKE-99" in failures[0]["reasons"][0]
    assert "dispatched to no implementation" in failures[0]["reasons"][0]


def test_a_dangling_anaphora_in_a_projected_chunk_fails_the_strict_gate():
    """R-PROJ-04 is MUST. Its verdict was written into the report and read by no gate, so the rule
    was credited 3/3 model_verified coverage while failing. The dangling-anaphora half is a
    deterministic regex verdict, so unlike the entailment numbers it gates on any backend."""
    failures = _spec_strict_failures(
        _scored(model_verified={"chunk_selfcontained": {
            "ok": False, "backend": "lexical",
            "failures": ["card-x"], "dangling_failures": ["card-x"]}}),
        registry_rules())
    assert len(failures) == 1 and "R-PROJ-04" in failures[0]["reasons"][0]


def test_the_lexical_proxy_never_gates_the_entailment_half_of_r_proj_04():
    """Same reasoning as the citation thresholds: word overlap against a required paraphrase is not
    evidence, so gating on it would leave --strict permanently red offline."""
    quiet = _spec_strict_failures(
        _scored(model_verified={"chunk_selfcontained": {
            "ok": False, "backend": "lexical",
            "failures": ["body-x"], "dangling_failures": []}}),
        registry_rules())
    assert quiet == []

    loud = _spec_strict_failures(
        _scored(model_verified={"chunk_selfcontained": {
            "ok": False, "backend": "nli",
            "failures": ["body-x"], "dangling_failures": []}}),
        registry_rules())
    assert len(loud) == 1 and "chunk self-containment" in loud[0]["reasons"][0]


def test_a_skip_is_not_credited_as_coverage(tmp_path):
    """The mechanism under the gate: a registry rule whose `check.ref` names no implementation must
    not appear in `rules_exercised`. It used to, which is how the ratchet came to be blind to the
    one defect class it exists to detect."""
    from eval import _exercised, _unenforced
    from ir.schema import SourceLedger
    from lint import run_ledger_pass

    registry = yaml.safe_load((SKILL_ROOT / "references" / "rule-registry.yaml").read_text())
    registry["rules"].append({
        "id": "R-FAKE-99", "namespace": "GROUND", "priority": "MUST", "enforcement": "hard_lint",
        "directive": "a rule nobody implemented", "rationale": "-", "counters": "-",
        "check": {"ref": "checks/nonexistent.py::never_written", "input": "ledger",
                  "detail": "never implemented"},
    })
    path = tmp_path / "rule-registry.yaml"
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    ledger = SourceLedger.from_yaml(SKILL_ROOT / "tests" / "fixtures" / "source-ledger.full.yaml")
    report = run_ledger_pass(ledger, registry_path=path)

    assert report["counts"].get("skip") == 1
    assert "R-FAKE-99" not in _exercised(report["findings"])
    assert _unenforced(report) == ["R-FAKE-99"]
    # the rules that DO dispatch are still credited — the filter is not a blanket refusal
    assert _exercised(report["findings"])


# --- the run manifest (Stage F) ----------------------------------------------

def test_manifest_resumes_at_the_first_incomplete_phase():
    """Not the phase after the last complete one: phase 8 consumes what phase 3 produced, so a
    gap must be re-run rather than skipped."""
    from run_manifest import PHASES, RunManifest
    m = RunManifest(run_id="r1")
    for p in PHASES[:3]:
        m.complete(p)
    m.complete(PHASES[5])          # a stray later completion
    assert m.resume_from() == PHASES[3]


def test_manifest_round_trips(tmp_path):
    from run_manifest import RunManifest
    m = RunManifest(run_id="r1", topic="rag")
    m.start("0-parameters", at="t0").complete("0-parameters", ["parameters.yaml"], at="t1")
    path = m.save(tmp_path / "run-manifest.json")
    back = RunManifest.load(path)
    assert back.run_id == "r1" and back.topic == "rag"
    assert back.is_complete("0-parameters")
    assert back.phases["0-parameters"].artifacts == ["parameters.yaml"]


def test_manifest_is_stable_across_saves(tmp_path):
    """Timestamps are injected, never read from the clock — the eval harness replays runs."""
    from run_manifest import RunManifest
    a = RunManifest(run_id="r1").complete("0-parameters", at="t1").save(tmp_path / "a.json")
    b = RunManifest(run_id="r1").complete("0-parameters", at="t1").save(tmp_path / "b.json")
    assert a.read_text() == b.read_text()


def test_manifest_rejects_an_unknown_phase():
    from run_manifest import RunManifest
    try:
        RunManifest(run_id="r1").complete("9-nonexistent")
    except KeyError as e:
        assert "unknown phase" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_failed_phase_blocks_resume_past_it():
    from run_manifest import RunManifest
    m = RunManifest(run_id="r1").complete("0-parameters").fail("1a-discovery", "backend timeout")
    assert m.resume_from() == "1a-discovery"
    assert m.completed_phases() == ["0-parameters"]


def test_narrowed_runs_do_not_trip_the_coverage_floors():
    """A floor counts rules exercised across EVERY spec, so comparing it against one spec's coverage
    fails for the wrong reason — and a gate that cries wolf on a routine `--spec` run is a gate
    someone switches off. Floors suspend; silent-skips and real spec failures stay armed, because
    those are local facts that remain true when only one spec ran."""
    thin = {"R-GROUND-01"}
    full = coverage_gate(thin, [], partial=False)
    assert not full["passed"] and full["shortfalls"] and full["floors_enforced"]

    partial = coverage_gate(thin, [], partial=True)
    assert partial["shortfalls"] == []
    assert partial["scope"] == "partial" and partial["floors_enforced"] is False

    # ...but a genuine spec failure is NOT excused by narrowing
    failing = [{"id": "spec-x", "status": "scored", "hard_lints": {"blocking": True},
                "model_verified": {"status": "skipped"},
                "expected_must_pass_report": {"failed": [], "not_exercised": []}}]
    assert coverage_gate(thin, failing, partial=True)["passed"] is False


def test_a_stale_critic_report_is_not_counted_as_coverage(tmp_path):
    """A frozen report judged one specific IR. If that IR has changed, the verdicts describe a
    document that no longer exists — crediting them is coverage for judging something else, the
    same class of lie as counting a stub but much harder to notice. Editing two sentences of the
    reference fixture was enough to invalidate an $18 report with nothing to show it."""
    ir = tmp_path / "ir.yaml"
    ir.write_text("sections: []\n", encoding="utf-8")
    stale = tmp_path / "critic.json"
    stale.write_text(json.dumps({
        "judge": {"kind": "claude", "exercised_rules": True},
        "ir_sha256": "0" * 64,
        "passes": [{"pass": "coherence", "verdicts": [
            {"rule_id": "R-PROSE-02", "block_id": "b1", "verdict": "pass"}]}],
    }), encoding="utf-8")

    tier = _tier_soft_critic({"critic_report": stale, "ir": ir})
    assert tier["status"] == "stale"
    assert tier["rules_exercised"] == []

    # matching digest -> credited normally
    from eval import _ir_digest
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps({
        "judge": {"kind": "claude", "exercised_rules": True},
        "ir_sha256": _ir_digest(ir),
        "passes": [{"pass": "coherence", "verdicts": [
            {"rule_id": "R-PROSE-02", "block_id": "b1", "verdict": "pass"}]}],
    }), encoding="utf-8")
    assert _tier_soft_critic({"critic_report": fresh, "ir": ir})["rules_exercised"] == ["R-PROSE-02"]


def test_a_narrowed_run_cannot_fabricate_a_silent_skip():
    """`_why_unexercised` classifies by rule KIND, not by whether this run could reach the rule, so
    a deterministic rule that spec-01 exercises and spec-02 does not would be reported as a silent
    skip under `--spec spec-02` — a defect invented by narrowing. It does not fire today only
    because the two specs happen to exercise identical hard_lint sets, which is luck, not design."""
    hard_lint = [r["id"] for r in registry_rules() if r["enforcement"] == "hard_lint"]
    exercised = set(registry_rule_ids()) - {hard_lint[0]}      # one deterministic rule goes dark

    full = coverage_gate(exercised, [], partial=False)
    assert full["silent_skips"] == [hard_lint[0]], "a full run must still catch a dark rule"

    narrowed = coverage_gate(exercised, [], partial=True)
    assert narrowed["silent_skips"] == []
    assert narrowed["passed"], "a narrowed run must not invent a silent skip"


def test_a_narrowed_run_still_reports_real_spec_failures():
    """Suspending the coverage checks must not disarm the gate entirely: a rule that FAILED is a
    local fact, true no matter which specs ran."""
    results = [{
        "id": "spec-x", "status": "scored",
        "hard_lints": {"blocking": True},
        "model_verified": {"status": "skipped"},
        "expected_must_pass_report": {"failed": ["R-GROUND-01"], "not_exercised": []},
    }]
    gate = coverage_gate(set(registry_rule_ids()), results, partial=True)
    assert not gate["passed"]
    assert gate["spec_failures"] and gate["spec_failures"][0]["spec"] == "spec-x"
