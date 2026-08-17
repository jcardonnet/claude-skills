"""Citation quality: ledger resolution + recall + precision.

Classification: model_verified
Implements: R-GROUND-01 (resolves_to_ledger, deterministic), R-GROUND-02 (recall), R-GROUND-03 (precision)

  - resolves_to_ledger (R-GROUND-01): every claim_id / source_id a block cites exists in the ledger.
    Deterministic, no model. An unresolved marker is the anti-fabrication floor — a MUST failure.
  - recall (R-GROUND-02): a factual statement (a claim-bearing block) is supported if >=1 of its
    cited claim quotes entails it.  recall = supported statements / factual statements.
  - precision (R-GROUND-03): each cited (block, claim) is supporting if its quote entails the block.
    A decorative citation lowers precision.  precision = supporting citations / resolvable citations.

Entailment runs through a pluggable backend (verify/_entailment.py): offline default = lexical
proxy; production = local HF NLI/MiniCheck (GPU) or a scoped Claude call. Thresholds come from
references/eval/eval-rubric.yaml; below threshold is a MUST-level block (priority).

Usage:
    python scripts/verify/citation_quality.py document-ir.yaml --ledger source-ledger.yaml --backend auto
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# scripts/ is the import root (matches registry check.refs); enable standalone execution.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from ir.schema import DocumentIR, SourceLedger  # noqa: E402
from verify._entailment import Entailment, resolve_backend  # noqa: E402

DEFAULT_RUBRIC = Path(__file__).resolve().parents[2] / "references" / "eval" / "eval-rubric.yaml"
_FALLBACK_THRESHOLDS = {"recall": 0.75, "precision": 0.90,
                        "verified_recall": 0.95, "verified_precision": 0.90,
                        "max_inferred_share": 0.60}


def load_thresholds(rubric_path: str | Path = DEFAULT_RUBRIC) -> dict[str, float]:
    try:
        data = yaml.safe_load(Path(rubric_path).read_text(encoding="utf-8")) or {}
        th = (data.get("model_verified") or {}).get("thresholds") or {}
        return {
            "recall": float(th.get("citation_recall", _FALLBACK_THRESHOLDS["recall"])),
            "precision": float(th.get("citation_precision", _FALLBACK_THRESHOLDS["precision"])),
            # what --strict actually gates on; the legacy pair mixes declared synthesis with
            # claimed grounding, so no value of it is meaningful
            "verified_recall": float(th.get("verified_recall",
                                            _FALLBACK_THRESHOLDS["verified_recall"])),
            "verified_precision": float(th.get("verified_precision",
                                               _FALLBACK_THRESHOLDS["verified_precision"])),
            # without this, verified_recall is vacuous for a primer that declares nothing verified
            "max_inferred_share": float(th.get("max_inferred_share",
                                               _FALLBACK_THRESHOLDS["max_inferred_share"])),
        }
    except (OSError, ValueError, TypeError):
        return dict(_FALLBACK_THRESHOLDS)


def resolves_to_ledger(ir: DocumentIR, ledger: SourceLedger) -> list[dict]:
    """R-GROUND-01: every cited claim_id / source_id resolves to the ledger (deterministic)."""
    known_claims = ledger.claim_ids()
    known_sources = ledger.source_ids()
    out: list[dict] = []
    for b in ir.flatten_blocks():
        for cid in b.claim_ids:
            if cid not in known_claims:
                out.append({"block_id": b.block_id, "marker_type": "claim_id", "marker": cid,
                            "detail": f"claim_id {cid!r} does not resolve to the source-ledger"})
        for sid in b.source_ids:
            if sid not in known_sources:
                out.append({"block_id": b.block_id, "marker_type": "source_id", "marker": sid,
                            "detail": f"source_id {sid!r} does not resolve to the source-ledger"})
    return out


def _claim_index(ledger: SourceLedger) -> dict[str, tuple[str, str]]:
    """claim_id -> (supporting_text, source_id). Prefers the short quote; falls back to claim text."""
    idx: dict[str, tuple[str, str]] = {}
    for s in ledger.sources:
        for c in s.claims:
            idx[c.claim_id] = (c.quote or c.text or "", s.source_id)
    return idx


def evaluate(
    ir: DocumentIR,
    ledger: SourceLedger,
    backend: Entailment | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict:
    backend = backend or resolve_backend("auto")
    thresholds = thresholds or dict(_FALLBACK_THRESHOLDS)
    cidx = _claim_index(ledger)

    resolves = resolves_to_ledger(ir, ledger)

    per_statement: list[dict] = []
    per_citation: list[dict] = []
    factual = supported = 0
    cite_total = cite_support = 0

    for b in ir.flatten_blocks():
        if not b.claim_ids:
            continue
        # Per-UNIT, not per-block. A card is seven typed rows against a <=15-word quote cap
        # (R-GROUND-01), so nothing could entail the concatenation and every card failed
        # structurally. `entailment_units` returns the rows that assert something about the world;
        # a citation supports the block when it entails any one of them. Simple blocks yield their
        # prose unchanged, so their scoring is untouched.
        units = b.entailment_units
        statement = b.readable_text
        resolvable = [cid for cid in b.claim_ids if cid in cidx]
        block_supported = False
        for cid in resolvable:
            quote, sid = cidx[cid]
            ok = any(backend.supports(quote, unit) for unit in units)
            cite_total += 1
            cite_support += int(ok)
            block_supported = block_supported or ok
            per_citation.append({
                "block_id": b.block_id, "claim_id": cid, "source_id": sid,
                "supports": ok, "quote": quote, "statement": statement,
                "units": len(units),
            })
        if resolvable:  # a block with no resolvable claim is an R-GROUND-01 failure, not a recall sample
            factual += 1
            supported += int(block_supported)
            per_statement.append({"block_id": b.block_id, "claim_ids": resolvable,
                                  "supported": block_supported,
                                  "provenance": b.provenance.value if b.provenance else None})

    recall = supported / factual if factual else 1.0
    precision = cite_support / cite_total if cite_total else 1.0

    # --- partition by provenance ---------------------------------------------------------------
    # A block marked `inferred` is the author saying "this is my synthesis, not something a source
    # states". Counting it in the same denominator as a `verified` block means a primer that labels
    # its unsupported content HONESTLY scores identically to one that fabricates citations — which
    # deletes the incentive to label honestly, the exact opposite of what R-GROUND-* is for.
    # Measured: spec-02 reads 0.15 overall, and 1/2 on the blocks it actually claims are verified;
    # the other 11 are declared synthesis. Those are two different facts and deserve two numbers.
    #
    # `verified_recall` is where a threshold belongs — a block asserting `verified` whose citation
    # does not entail it is a defect. `inferred_share` is a COMPOSITION signal: a primer that is 85%
    # synthesis may be scrupulously honest and still under-researched, which is a budget question
    # rather than a citation-quality one, and conflating them hides both.
    verified = [s for s in per_statement if s["provenance"] == "verified"]
    inferred = [s for s in per_statement if s["provenance"] == "inferred"]
    verified_ids = {s["block_id"] for s in verified}
    v_supported = sum(1 for s in verified if s["supported"])
    v_cites = [c for c in per_citation if c["block_id"] in verified_ids]
    v_cite_support = sum(1 for c in v_cites if c["supports"])

    verified_recall = v_supported / len(verified) if verified else 1.0
    verified_precision = v_cite_support / len(v_cites) if v_cites else 1.0
    inferred_share = len(inferred) / factual if factual else 0.0

    blocking = bool(resolves) or recall < thresholds["recall"] or precision < thresholds["precision"]

    return {
        "backend": backend.name,
        "resolves_to_ledger": {"ok": not resolves, "violations": resolves},
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "verified_recall": round(verified_recall, 4),
        "verified_precision": round(verified_precision, 4),
        "inferred_share": round(inferred_share, 4),
        "thresholds": thresholds,
        "counts": {"factual_statements": factual, "supported_statements": supported,
                   "citations": cite_total, "supporting_citations": cite_support,
                   "verified_statements": len(verified), "verified_supported": v_supported,
                   "verified_citations": len(v_cites), "verified_supporting": v_cite_support,
                   "inferred_statements": len(inferred)},
        "per_statement": per_statement,
        "per_citation": per_citation,
        "blocking": blocking,
    }


def verify_files(
    ir_path: str | Path,
    ledger_path: str | Path,
    rubric_path: str | Path = DEFAULT_RUBRIC,
    backend_name: str = "auto",
) -> dict:
    return evaluate(
        DocumentIR.from_yaml(ir_path),
        SourceLedger.from_yaml(ledger_path),
        backend=resolve_backend(backend_name),
        thresholds=load_thresholds(rubric_path),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify citation quality (R-GROUND-01/02/03) against the ledger.")
    ap.add_argument("ir")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    ap.add_argument("--backend", default="auto", choices=["auto", "lexical", "nli", "claude"])
    ap.add_argument("--out", default="verify-report.json")
    args = ap.parse_args(argv)

    report = verify_files(args.ir, args.ledger, args.rubric, args.backend)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    r = report
    print(f"{'BLOCKING' if r['blocking'] else 'clean'} — recall={r['recall']} (>= {r['thresholds']['recall']}) "
          f"precision={r['precision']} (>= {r['thresholds']['precision']}) "
          f"unresolved={len(r['resolves_to_ledger']['violations'])} backend={r['backend']} -> {args.out}")
    for v in r["resolves_to_ledger"]["violations"]:
        print(f"  [unresolved] {v['block_id']}: {v['detail']}")
    for c in r["per_citation"]:
        if not c["supports"]:
            print(f"  [non-supporting] {c['block_id']}/{c['claim_id']}: quote does not entail the statement")
    return 1 if r["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
