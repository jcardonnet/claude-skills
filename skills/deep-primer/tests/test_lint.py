"""Dispatcher tests (Prompt 2): registry-driven run, blocking-from-priority, degradation, report shape."""
import json

import pytest

from checks._base import LintContext, nlp_available
from ir.schema import Block, Concept, ConceptMap, DocumentIR, Section
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
    # the full set ran: pass, warn, fail, and skip all present
    assert set(report["counts"]) >= {"pass", "warn", "fail", "skip"}


def test_report_record_shape(fixtures):
    report = lint_files(fixtures / "document-ir.yaml", fixtures / "concept-map.yaml")
    for f in report["findings"]:
        assert {"rule_id", "block_id", "status", "detail"} <= set(f)
        assert f["status"] in {"pass", "fail", "warn", "skip"}


def test_unimplemented_refs_are_skipped(fixtures):
    report = lint_files(fixtures / "document-ir.yaml")
    # R-CARD-02 (card_rows) needs richer IR than V1 models -> skip, never crashes
    card = _by_rule(report, "R-CARD-02")
    assert card and card[0]["status"] == "skip"


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


# --- a clean IR passes (no blocking failures) --------------------------------

def _clean_ctx():
    d = DocumentIR(sections=[Section(
        block_id="sec-vi",
        title="A vector index trades recall for speed",
        concept="vector-index",
        blocks=[
            Block(block_id="lede-vi", role="lede", text="A vector index trades recall for query speed.",
                  claim_ids=["C1"], provenance="inferred"),
            Block(block_id="card-vi", role="card", concept="vector-index", mode="mental_model",
                  text="If you know B-trees, this is nearest-not-equal lookup.", claim_ids=["C1"], provenance="inferred"),
            Block(block_id="fig1-vi", role="figure", concept="vector-index", mode="architecture",
                  caption="Figure 1: search descends layers, so latency is logarithmic."),
            Block(block_id="fig2-vi", role="figure", concept="vector-index", mode="benchmark",
                  caption="Figure 2: recall climbs with ef_search at a latency cost."),
            Block(block_id="recall-vi", role="recall", text="When would you skip an ANN index entirely?"),
        ],
    )])
    cm = ConceptMap(concepts=[Concept(concept_id="vector-index", canonical_term="vector index")])
    return LintContext(ir=d, concept_map=cm, parameters={})


def test_clean_ir_is_not_blocking():
    report = run_lint(_clean_ctx())
    fails = [f for f in report["findings"] if f["status"] == "fail"]
    assert report["blocking"] is False
    assert fails == []


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
