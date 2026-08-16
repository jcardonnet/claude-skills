"""Dispatcher tests (Prompt 2): registry-driven run, blocking-from-priority, degradation, report shape."""
import json

import pytest

from checks._base import LintContext, nlp_available
from ir.schema import Block, ConceptMap, DocumentIR, Section
from lint import lint_files, main, run_lint


def _by_rule(report, rule_id):
    return [f for f in report["findings"] if f["rule_id"] == rule_id]


# --- end-to-end on the Prompt-1 fixture --------------------------------------

def test_full_hard_lint_run_blocks_on_fixture(fixtures):
    report = lint_files(
        fixtures / "document-ir.yaml",
        fixtures / "concept-map.yaml",
        fixtures / "source-ledger.yaml",
    )
    assert report["blocking"] is True
    # R-MV-01 is MUST -> fail (the fixture concepts have <3 modes)
    mv = _by_rule(report, "R-MV-01")
    assert mv and all(f["status"] == "fail" and f["blocking"] for f in mv)
    # R-ARCH-06 is SHOULD -> warn (non-blocking)
    arch = _by_rule(report, "R-ARCH-06")
    assert arch and all(f["status"] == "warn" and not f["blocking"] for f in arch)
    assert set(report["counts"]) >= {"pass", "warn", "fail"}


def test_report_record_shape(fixtures):
    report = lint_files(fixtures / "document-ir.yaml", fixtures / "concept-map.yaml")
    for f in report["findings"]:
        assert {"rule_id", "block_id", "status", "detail"} <= set(f)
        assert f["status"] in {"pass", "fail", "warn", "skip"}


def test_every_dispatched_ir_check_is_implemented(fixtures):
    """The regression guard for the Stage-A gap: an unimplemented check reports 'skip', which is
    non-blocking, so the report reads clean while the rule goes unenforced. Six MUST rules stayed
    dark that way. No IR-targeting check may be unimplemented."""
    report = lint_files(fixtures / "document-ir.yaml")
    assert report["coverage"]["rules_skipped"] == []
    assert report["coverage"]["unenforced_musts"] == []
    assert report["counts"].get("skip", 0) == 0


def test_also_hard_lint_companion_is_dispatched(fixtures):
    """R-SCENT-01 is a soft_critic rule carrying an also_hard_lint companion (banned generic
    headings). Filtering dispatch on enforcement is how that lint went missing."""
    report = lint_files(fixtures / "document-ir.yaml")
    assert _by_rule(report, "R-SCENT-01"), "R-SCENT-01's also_hard_lint companion never ran"


def test_banned_generic_heading_is_caught():
    d = DocumentIR(sections=[Section(
        block_id="s1", title="Background",
        blocks=[Block(block_id="l1", role="lede", text="x")],
    )])
    scent = _by_rule(run_lint(LintContext(ir=d)), "R-SCENT-01")
    assert any(f["status"] == "fail" and "Background" in f["detail"] for f in scent)


def test_cli_main_exit_and_report(fixtures, tmp_path):
    out = tmp_path / "lint-report.json"
    code = main([
        str(fixtures / "document-ir.yaml"),
        "--concept-map", str(fixtures / "concept-map.yaml"),
        "--ledger", str(fixtures / "source-ledger.yaml"),
        "--out", str(out),
    ])
    assert code == 1  # blocking fixture
    data = json.loads(out.read_text())
    assert data["blocking"] is True and data["findings"]


# --- a complete field-guide IR passes (no blocking failures) -----------------

def test_full_fixture_is_not_blocking(fixtures):
    """document-ir.full.yaml exercises the whole structural contract — subsections with one
    sub-sum each, typed card rows, three recall items per section, all four artifacts — and must
    come back clean with nothing skipped."""
    report = lint_files(
        fixtures / "document-ir.full.yaml",
        fixtures / "concept-map.full.yaml",
        fixtures / "source-ledger.full.yaml",
    )
    fails = [f for f in report["findings"] if f["status"] == "fail"]
    assert fails == [], f"unexpected failures: {[(f['rule_id'], f['detail']) for f in fails]}"
    assert report["blocking"] is False
    assert report["counts"].get("skip", 0) == 0


# --- blocking derives from priority ------------------------------------------

def test_blocking_derives_from_priority():
    # MUST violation (layer_coverage: no card/recall) + SHOULD violation (provenance: claim w/o tag)
    d = DocumentIR(sections=[Section(
        block_id="s1", title="t",
        blocks=[Block(block_id="l1", role="lede", text="x", claim_ids=["C1"])],
    )])
    report = run_lint(LintContext(ir=d))
    consist = _by_rule(report, "R-CONSIST-01")
    proj = _by_rule(report, "R-PROJ-05")
    assert any(f["status"] == "fail" and f["priority"] == "MUST" for f in consist)
    assert any(f["status"] == "warn" and f["priority"] == "SHOULD" for f in proj)
    assert report["blocking"] is True  # the MUST failure blocks


# --- coherence degrades per CAPABILITIES.md ----------------------------------

_CHOPPY = "HNSW builds a graph. A shard splits the corpus. Quantization shrinks the vectors."


def _choppy_ctx(caps):
    d = DocumentIR(sections=[Section(block_id="s1", title="t",
                                     blocks=[Block(block_id="b1", role="body", text=_CHOPPY)])])
    return LintContext(ir=d, capabilities=caps)


def test_coherence_native_is_blocking():
    if not nlp_available(LintContext(ir=DocumentIR())):
        pytest.skip("spaCy model unavailable")
    prose = _by_rule(run_lint(_choppy_ctx({})), "R-PROSE-01")
    assert prose and any(f["status"] == "fail" and f["blocking"] for f in prose)


def test_coherence_degraded_is_warn_not_fail():
    prose = _by_rule(run_lint(_choppy_ctx({"force_no_nlp": True})), "R-PROSE-01")
    assert prose, "fallback should still produce R-PROSE-01 findings"
    assert all(f["status"] == "warn" and not f["blocking"] for f in prose)


# --- the html pass (input: html rules) ---------------------------------------

def test_html_pass_dispatches_and_passes_on_rendered_output(fixtures):
    from lint import run_html_pass
    from render.render_html import render_html

    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")
    cm = ConceptMap.from_yaml(fixtures / "concept-map.full.yaml")
    report = run_html_pass(render_html(ir, cm))
    assert report["coverage"]["checks_dispatched"] == 3
    assert report["coverage"]["rules_skipped"] == []
    assert report["blocking"] is False


def test_html_pass_blocks_on_missing_primer_meta():
    from lint import run_html_pass
    report = run_html_pass('<p data-block-id="x" data-tierlevel="1"></p><body data-depth="1"></body>')
    consist = [f for f in report["findings"] if f["rule_id"] == "R-CONSIST-02"]
    assert any(f["status"] == "fail" for f in consist)   # MUST -> blocking
    assert report["blocking"] is True


def test_spec02_primer_is_lint_clean_and_honestly_grounded(fixtures):
    """spec-02's artifact is the first primer here built from a REAL grounding run: sources found by
    web search, fetched over the network, every ledger quote verified verbatim at <=15 words.

    It also pins the honesty correction that run produced. Scored with the real entailment backend
    the primer came back at recall 0.15 — because four abstracts about line-segment detection and
    promptable segmentation cannot support claims about callouts, exploded views or seated parts.
    Those blocks are synthesis from adjacent evidence, so they carry `provenance: inferred`, not
    `verified`. Structural compliance is not grounding, and the provenance axis is where the
    difference is recorded rather than smoothed over.
    """
    from ir.schema import DocumentIR

    spec02 = fixtures / "spec02"
    report = lint_files(spec02 / "document-ir.yaml", spec02 / "concept-map.yaml",
                        spec02 / "source-ledger.yaml")
    fails = [f for f in report["findings"] if f["status"] == "fail"]
    assert fails == [], f"unexpected failures: {[(f['rule_id'], f['detail']) for f in fails]}"
    assert report["coverage"]["unenforced_musts"] == []

    ir = DocumentIR.from_yaml(spec02 / "document-ir.yaml")
    provenances = {b.provenance.value for b in ir.flatten_blocks() if b.provenance}
    assert "inferred" in provenances, "the synthesis blocks must not claim to be verified"
    assert "verified" in provenances, "the directly-quoted blocks should still say so"
