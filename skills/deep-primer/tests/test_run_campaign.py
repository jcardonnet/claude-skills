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
                 backend=_Backend(), extractor=_Extractor(), judge=_NoFinding())

    for name in ("discovery-leads.yaml", "discovery-log.yaml", "source-ledger.yaml",
                 "concept-map.yaml", "convergence-log.yaml", "campaign-run.json"):
        assert (out / name).is_file(), name
    assert report["topic"] == "distributed tracing"
    assert report["retrieval"]["documents_fetched"] == 3


def test_the_gate_still_runs_inside_the_composition(tmp_path):
    """A fabricated quote does not become provenance just because a driver assembled the call."""
    out = tmp_path / "out"
    report = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 backend=_Backend(), extractor=_Extractor(), judge=_NoFinding())

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
                backend=_Backend(), extractor=_Extractor(), judge=_NoFinding())
    frozen = (out / "source-ledger.yaml").read_text(encoding="utf-8")

    # --from-corpus: no backend at all, and the same bytes come back out.
    second = run(_spec(tmp_path), out, as_of="2026-08-20", waves=("A",),
                 from_corpus=out / "corpus", extractor=_Extractor(), judge=_NoFinding())
    assert (out / "source-ledger.yaml").read_text(encoding="utf-8") == frozen
    assert second["retrieval"]["documents_extracted"] == first["retrieval"]["documents_extracted"]
    assert second["retrieval"]["documents_fetched"] == 0   # the resume path touched no network
