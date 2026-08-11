"""Eval-harness tests (Prompt 7 / Stage E).

The harness's job is to be honest about what it measured. Most of these pin that: a spec with no
artifact must not read as a pass, an expected rule that never ran must not read as a pass, and a
threshold must not be proposed from a backend that cannot support one.
"""
from pathlib import Path

import yaml

from eval import (
    _why_unexercised,
    load_specs,
    propose_thresholds,
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
    """Guards against a proxy-derived floor being written into the rubric by accident."""
    rubric = yaml.safe_load((SKILL_ROOT / "references" / "eval" / "eval-rubric.yaml").read_text())
    th = rubric["model_verified"]["thresholds"]
    assert th["citation_recall"] >= 0.7 and th["citation_precision"] >= 0.85


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
