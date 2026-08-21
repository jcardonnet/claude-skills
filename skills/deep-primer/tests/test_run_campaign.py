"""The campaign driver: the eight-phase pipeline's first two phases, written down.

The skill is the driver — an agent runs the phases and calls `research/*` as engines. That is why
spec-02's campaign could not be re-run: the sequence only ever existed in a transcript. These tests
pin the composition, not the engines (each of those is covered where it lives), and they run with
all three model seams stubbed, which is the property that made writing the sequence down worth it.
"""
from pathlib import Path

import yaml

from research.retrieval_loop import Document
from research.run_campaign import run

# Grouping is a model seam like the other three, and these tests stay offline, so every call below
# either injects a stub grouper or passes `lexical_grouping=True`. The default is deliberately the
# model path — word-overlap grouping is what turned spec-03's 271 claims into 249 concepts — so a
# test that forgets to say so would reach the network, which is the failure mode worth spelling out.
OFFLINE = {"lexical_grouping": True}

BODY = (
    "Distributed tracing propagates a trace context across service boundaries.\n\n"
    "A span is the unit of work in a trace and carries a start and an end timestamp.\n\n"
    "Tail-based sampling defers the keep decision until the trace is complete.\n"
)

SPEC = {
    "id": "spec-test",
    "parameters": {"target_domain": "distributed tracing", "home_domain": ["backend services"],
                   "seniority_band": "mid_senior", "length_budget": 2500},
}


class _Backend:
    """Stands in for `ClaudeResearchBackend`: returns leads and the documents it fetched."""

    name = "stub"

    def __init__(self, n=3):
        self.documents = [Document(url=f"https://ex{i}.test/p", text=BODY, title=f"Doc {i}",
                                   source_type="docs", retrieved_at="2026-08-20")
                          for i in range(n)]
        self.dropped = []

    def __call__(self, _brief):
        return "# report\n\n- lead: tracing\n", [
            {"id": f"s{i}", "url": d.url, "type": "docs", "status": "accepted",
             "provenance_origin": "discovered"}
            for i, d in enumerate(self.documents)]


class _Extractor:
    errors: list = []

    def __call__(self, _doc):
        return [
            {"text": "A span is the unit of work in a trace.",
             "quote": "A span is the unit of work in a trace", "confidence": "high"},
            {"text": "fabricated", "quote": "no such sentence anywhere", "confidence": "high"},
        ]


class _NoFinding:
    def scan_for_structural(self, _cmap, _params):
        return None

    def implied_edits(self, _finding, cmap):
        return cmap


def _spec(tmp_path: Path) -> Path:
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.safe_dump(SPEC), encoding="utf-8")
    return p


def test_the_driver_produces_every_artifact_the_lints_read(tmp_path):
    out = tmp_path / "out"
    report = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 backend=_Backend(), extractor=_Extractor(), judge=_NoFinding(), **OFFLINE)

    for name in ("discovery-leads.yaml", "discovery-log.yaml", "source-ledger.yaml",
                 "concept-map.yaml", "convergence-log.yaml", "campaign-run.json"):
        assert (out / name).is_file(), name
    assert report["topic"] == "distributed tracing"
    assert report["retrieval"]["documents_fetched"] == 3


def test_the_gate_still_runs_inside_the_composition(tmp_path):
    """A fabricated quote does not become provenance just because a driver assembled the call."""
    out = tmp_path / "out"
    report = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 backend=_Backend(), extractor=_Extractor(), judge=_NoFinding(), **OFFLINE)

    assert report["grounding"]["claims_kept"] == 3        # one survivor per document
    assert report["grounding"]["claims_rejected"] == 3
    ledger = yaml.safe_load((out / "source-ledger.yaml").read_text(encoding="utf-8"))
    texts = {c["text"] for s in ledger["sources"] for c in s["claims"]}
    assert "fabricated" not in texts


def test_the_ledger_is_built_by_replaying_the_frozen_corpus(tmp_path):
    """The network runs once. Everything downstream reads what was frozen, so the grounding half
    re-runs offline to a byte-identical ledger — the property a threshold can be fitted against."""
    out = tmp_path / "out"
    first = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                backend=_Backend(), extractor=_Extractor(), judge=_NoFinding(), **OFFLINE)
    frozen = (out / "source-ledger.yaml").read_text(encoding="utf-8")

    # --from-corpus: no backend at all, and the same bytes come back out.
    second = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 from_corpus=out / "corpus", extractor=_Extractor(), judge=_NoFinding(), **OFFLINE)
    assert (out / "source-ledger.yaml").read_text(encoding="utf-8") == frozen
    assert second["retrieval"]["documents_extracted"] == first["retrieval"]["documents_extracted"]
    assert second["retrieval"]["documents_fetched"] == 0   # the resume path touched no network


def test_a_campaign_that_resolves_no_documents_fails_instead_of_reporting_zero(tmp_path):
    """Total retrieval failure is silent unless something refuses it.

    Every stage after retrieval is a clean no-op on an empty document list: no claims are anchored,
    there is nothing to group, and the driver writes a full report and exits 0. The only symptom is
    `concepts: 0` in a file nobody reads on a green run. That is how the 2026-08-21 spec-04 retry
    reported success on 155 source leads with every one of them unresolved.
    """
    import pytest

    class _Empty(_Backend):
        def __init__(self):
            super().__init__()
            self.documents = []          # leads still surface; nothing behind them fetched

        def __call__(self, _brief):
            return "# report\n\n- lead: tracing\n", [
                {"id": "s0", "url": "https://ex0.test/p", "type": "docs", "status": "accepted",
                 "provenance_origin": "discovered"}]

    with pytest.raises(RuntimeError, match="resolved 0 documents"):
        run(_spec(tmp_path), tmp_path / "out", as_of="2026-08-20", waves=("A",),
            backend=_Empty(), extractor=_Extractor(), judge=_NoFinding(), **OFFLINE)


def test_the_grouping_seams_are_wired_and_what_they_reject_is_reported(tmp_path):
    """Grouping is where the last campaign quietly failed: 271 claims became 249 concepts and 0
    corroborations, and `campaign-run.json` had no field that would have said so.

    An injected grouper wins over `lexical_grouping`, so a test never has to opt out twice.
    """
    out = tmp_path / "out"

    class _Grouper:
        notes = ["stub grouper ran"]
        errors: list = []

        def __call__(self, claims, params):
            assert params["target_domain"] == "distributed tracing"   # params reach the seam
            return [{"claim_ids": [cid for cid, _ in claims] + ["C-invented"],
                     "canonical_term": "span", "home_anchor": "a request log line"}]

    report = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 backend=_Backend(), extractor=_Extractor(), judge=_NoFinding(),
                 grouper=_Grouper(), corroboration_grouper=lambda claims, _p: [
                     {"claim_ids": [cid for cid, _ in claims]}])

    assert report["concepts"] == 1                       # one concept, not one per claim
    assert report["grounding"]["corroborated"] == 3      # three documents, three sources, one fact
    assert any("C-invented" in n for n in report["grouping"]["gate_rejections"])
    assert "stub grouper ran" in report["grouping"]["grouper_notes"]
    assert report["calls"]["group"] == 0                 # stubs carry no cli; the field still exists
