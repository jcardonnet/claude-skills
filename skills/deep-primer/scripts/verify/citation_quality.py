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
                        "max_inferred_share": 0.60,
                        # no per-type table reachable -> no spine gate, rather than a floor
                        # invented here that the rubric never agreed to
                        "min_spine_grounded": 0.0,
                        "primer_type": None,
                        "primer_type_recognised": True}

# The blocks a primer's grounded SPINE is made of. eval-rubric.yaml has justified
# `max_inferred_share` by the spine since it was written ("a primer needs a grounded SPINE ...
# spec-01 keeps its ledes and cards verified") without ever measuring one; this is that sentence
# turned into a population.
SPINE_ROLES = ("lede", "card")


def _resolve_composition(th: dict, primer_type: str | None) -> tuple[float, float, str | None, bool]:
    """(max_ungrounded, min_spine, resolved_type, recognised) for a declared primer type.

    An UNRECOGNISED type resolves to the STRICTEST entry in the table, never the default. A typo
    in a spec must not be able to LOOSEN a gate — that is the silent-erosion shape this file's
    other comments keep describing, and here it would be a one-character edit away.
    """
    table = th.get("composition_by_primer_type") or {}
    if not isinstance(table, dict) or not table:
        return (float(th.get("max_inferred_share", _FALLBACK_THRESHOLDS["max_inferred_share"])),
                0.0, primer_type, True)
    default = th.get("default_primer_type")
    if primer_type and primer_type in table:
        entry, resolved, known = table[primer_type], primer_type, True
    elif primer_type:
        resolved, known = primer_type, False
        entry = min(table.values(), key=lambda e: (float(e.get("max_ungrounded_share", 1.0)),
                                                   -float(e.get("min_spine_grounded", 0.0))))
    elif default in table:
        entry, resolved, known = table[default], default, True
    else:
        entry = min(table.values(), key=lambda e: float(e.get("max_ungrounded_share", 1.0)))
        resolved, known = None, True
    return (float(entry.get("max_ungrounded_share",
                            th.get("max_inferred_share",
                                   _FALLBACK_THRESHOLDS["max_inferred_share"]))),
            float(entry.get("min_spine_grounded", 0.0)),
            resolved, known)


def load_thresholds(rubric_path: str | Path = DEFAULT_RUBRIC,
                    primer_type: str | None = None) -> dict[str, float]:
    """Citation thresholds, with composition resolved for `primer_type` (G13).

    `max_inferred_share` keeps its name and its place in the report — only its VALUE now depends
    on the declared type, so every existing consumer, message and pin reads the same shape.
    """
    try:
        data = yaml.safe_load(Path(rubric_path).read_text(encoding="utf-8")) or {}
        th = (data.get("model_verified") or {}).get("thresholds") or {}
        max_ungrounded, min_spine, resolved, known = _resolve_composition(th, primer_type)
        return {
            "recall": float(th.get("citation_recall", _FALLBACK_THRESHOLDS["recall"])),
            "precision": float(th.get("citation_precision", _FALLBACK_THRESHOLDS["precision"])),
            # what --strict actually gates on; the legacy pair mixes declared synthesis with
            # claimed grounding, so no value of it is meaningful
            "verified_recall": float(th.get("verified_recall",
                                            _FALLBACK_THRESHOLDS["verified_recall"])),
            "verified_precision": float(th.get("verified_precision",
                                               _FALLBACK_THRESHOLDS["verified_precision"])),
            # without this, verified_recall is vacuous for a primer that declares nothing
            # verified. Per-primer-type since G13 — see the derivation in eval-rubric.yaml.
            "max_inferred_share": max_ungrounded,
            # the spine floor its justification always implied but never measured
            "min_spine_grounded": min_spine,
            "primer_type": resolved,
            "primer_type_recognised": known,
        }
    except (OSError, ValueError, TypeError):
        out = dict(_FALLBACK_THRESHOLDS)
        out["primer_type"] = primer_type
        return out


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
        undeclared = [u for u in units if not u.claim_ids]
        block_supported = False
        for cid in resolvable:
            quote, sid = cidx[cid]
            # Only the units this claim was actually cited FOR. Testing every claim against every
            # unit is what let a general quote be credited through a row it has nothing to do with
            # — the over-citation eval-rubric.yaml records on spec-01, invisible to the metric that
            # was supposed to catch it, because `claim_ids` says what a block cites and never what
            # for. A block with no declared attribution falls back to all of its units, which is
            # every artifact written before `row_claims` existed.
            targets = [u for u in units if cid in u.claim_ids] or undeclared
            ok = any(backend.supports(quote, u.text) for u in targets)
            cite_total += 1
            cite_support += int(ok)
            block_supported = block_supported or ok
            per_citation.append({
                "block_id": b.block_id, "claim_id": cid, "source_id": sid,
                "supports": ok, "quote": quote, "statement": statement,
                "units": len(units), "units_cited_for": [u.text for u in targets],
            })
        if resolvable:  # a block with no resolvable claim is an R-GROUND-01 failure, not a recall sample
            factual += 1
            supported += int(block_supported)
            per_statement.append({"block_id": b.block_id, "claim_ids": resolvable,
                                  "supported": block_supported,
                                  "role": b.role.value if b.role else None,
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

    # `verified | inferred` is NOT an exhaustive partition. `Provenance` also has `unverified`, and
    # a block may carry claim_ids with no provenance tag at all — both fall between the two buckets,
    # and all three settled thresholds are keyed on one of them. A primer that labels every
    # claim-bearing block `unverified` therefore scores verified_recall 1.0 (vacuous — nothing
    # claims grounding, so nothing can fail), verified_precision 1.0 and inferred_share 0.00,
    # clearing the whole gate while grounding nothing. `max_inferred_share` exists to stop exactly
    # that, so it has to be measured against the WHOLE population rather than one bucket of it.
    #
    # On both shipped artifacts every claim-bearing block is verified or inferred, so this is
    # numerically identical to inferred_share today (spec-01 0.43, spec-02 0.85) and the calibrated
    # threshold keeps its meaning. `inferred_share` stays in the report: "declared synthesis" and
    # "not grounded" are different facts and the rubric's reasoning is about the first.
    # Composition's denominator is `factual` — blocks with a RESOLVABLE citation — which by itself
    # rewards deleting citations: strip the claim_ids off a weak block and it leaves the denominator
    # entirely, improving the score. Blocks that DECLARE a grounding status and cite nothing close
    # that: they assert something about their own groundedness, so they belong in the population the
    # composition threshold is about.
    #
    # Deliberately NOT every uncited block. spec-01's uncited blocks are figures, checklists,
    # decision aids, recall Q&A and sub-sums — apparatus, not sourced claims — and counting those
    # would fail the artifact eval-rubric.yaml holds up as "what a compliant primer looks like".
    # Neither shipped artifact has an uncited block carrying provenance, so this is a no-op on both
    # and the calibrated 0.60 keeps its meaning.
    declared_uncited = [b for b in ir.flatten_blocks()
                        if b.provenance and b.entailment_units
                        and not any(c in cidx for c in b.claim_ids)]
    composition_total = factual + len(declared_uncited)
    ungrounded_share = ((composition_total - len(verified)) / composition_total
                        if composition_total else 0.0)

    # --- the SPINE ------------------------------------------------------------------------------
    # `ungrounded_share` alone turned out to measure APPARATUS DENSITY as much as grounding.
    # Measured across the six eval specs: spec-05 scores worst of the compliant five (0.57) while
    # having the most complete spine of any of them — every lede, card and summary verified — purely
    # because it carries more matrix, figure and body blocks, all legitimately synthesis. A primer is
    # penalised for being thorough, so no scalar cap can be tightened without failing a
    # correctly-composed artifact.
    #
    # The spine is the other half. eval-rubric.yaml has justified the composition cap by it since it
    # was written — "a primer needs a grounded SPINE ... spec-01 keeps its ledes and cards verified
    # while its matrix, body elaboration and Toulmin argumentation are synthesis" — without ever
    # measuring one. Across the five compliant specs the spine is 26/26 verified; spec-02's is 0/4.
    # That is not the top of a continuum, it is a different kind of document, and it is the
    # distinction a cap on the total could only ever see as a bigger number.
    #
    # Counted over EVERY lede and card in the document, not over the composition population. Scoping
    # it to the composition population would leave the strip-the-tags escape open in the one place
    # that matters: delete a lede's claim_ids and its provenance and the block drops out of both the
    # numerator and the denominator, so an author could empty their whole spine and read a vacuous
    # 1.0. Structurally, a lede is a lede whether or not it admits to being ungrounded.
    #
    # Grounded means `verified` AND carrying a resolvable citation. Declaring `verified` and citing
    # nothing is the evasion this guard exists to stop, not a way to satisfy it. Measured identical
    # to the composition-scoped reading on all six specs today (4/4, 0/4, 6/6, 6/6, 6/6, 8/8), so
    # the wider population costs nothing and closes the hole.
    spine_blocks = [b for b in ir.flatten_blocks()
                    if (b.role.value if b.role else "") in SPINE_ROLES]
    spine_verified = [b for b in spine_blocks
                      if b.provenance and b.provenance.value == "verified"
                      and any(c in cidx for c in b.claim_ids)]
    spine_total = len(spine_blocks)
    # A document with no lede and no card is not an ungrounded primer, it is an R-ARCH-06 failure —
    # `checks/structure_coverage.py::layer_coverage` is the deterministic MUST that requires the
    # layers to EXIST, and it gates on every backend already. Reporting a structural absence here as
    # a grounding shortfall would send an author to the wrong fix and would make this verifier
    # unusable on any document it was not asked a structural question about. Vacuous, and SAID to be
    # vacuous, rather than silently either way.
    spine_scoreable = spine_total > 0
    spine_grounded = len(spine_verified) / spine_total if spine_scoreable else 1.0

    # With nothing to score, every ratio above reports its PASSING value by vacuous truth, so a
    # primer that cites nothing at all clears R-GROUND-02/03 outright. That is not a clean primer,
    # it is an unscoreable one, and a gate has to be able to tell the two apart.
    scoreable = composition_total > 0

    # R-GROUND-01 is deterministic and MUST — an unresolved marker is the anti-fabrication floor and
    # blocks on any backend. The entailment-derived thresholds are a different matter twice over.
    #
    # They used to be the LEGACY `recall`/`precision` pair, which this file's own threshold loader
    # describes as mixing declared synthesis with claimed grounding so that "no value of it is
    # meaningful", and which eval-rubric.yaml carries as an unfitted TODO. The standalone CLI was
    # the only consumer still blocking on it, and it blocked on ANY backend — including the lexical
    # proxy, whose low scores are what a COMPLIANT primer produces.
    # Split by what the measurement DEPENDS ON, not by which function is asking.
    #
    # `resolves`, `scoreable` and `ungrounded_share` are computed from provenance tags and resolvable
    # claim_ids. No `backend.supports()` call is involved, so they mean exactly the same thing on
    # every backend and gate unconditionally. Only `verified_recall` / `verified_precision` are
    # entailment-derived, and only those are meaningless on the lexical proxy — it scores word
    # overlap between a <=15-word quote and a block R-GROUND-01 requires to be a PARAPHRASE.
    #
    # Putting composition behind the proxy bypass made the guard unreachable in the one configuration
    # this repo actually runs offline and in CI, which is where it was needed: spec-02 is 13
    # claim-bearing blocks, ALL `inferred`, ungrounded_share 1.00 against a 0.60 cap that
    # eval-rubric.yaml says exists precisely to "fail a primer that is entirely synthesis" — and it
    # passed clean. The same batch got this right for R-PROJ-04, whose deterministic
    # dangling-anaphora half gates on any backend while its entailment half waits for a real one.
    #
    # The spine floor rides along: it is computed from provenance tags and claim resolution too, so
    # it means the same thing on every backend.
    blocking = (bool(resolves) or not scoreable
                or ungrounded_share > thresholds["max_inferred_share"]
                or (spine_scoreable
                    and spine_grounded < thresholds.get("min_spine_grounded", 0.0)))
    if backend.name != "lexical":
        blocking = blocking \
            or verified_recall < thresholds["verified_recall"] \
            or verified_precision < thresholds["verified_precision"]

    return {
        "backend": backend.name,
        # How many (premise, hypothesis) pairs the judge could not answer. Every one of them scored
        # as NOT SUPPORTED, so without this number a total judge outage is indistinguishable from a
        # primer whose every citation is decorative — and the second reading is the one that gets
        # written into a threshold.
        "backend_unresolved": len(list(getattr(backend, "unresolved", []) or [])),
        "resolves_to_ledger": {"ok": not resolves, "violations": resolves},
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "verified_recall": round(verified_recall, 4),
        "verified_precision": round(verified_precision, 4),
        "inferred_share": round(inferred_share, 4),
        "ungrounded_share": round(ungrounded_share, 4),
        "spine_grounded": round(spine_grounded, 4),
        "spine_scoreable": spine_scoreable,
        "primer_type": thresholds.get("primer_type"),
        "primer_type_recognised": thresholds.get("primer_type_recognised", True),
        "scoreable": scoreable,
        "thresholds": thresholds,
        "counts": {"factual_statements": factual, "supported_statements": supported,
                   "citations": cite_total, "supporting_citations": cite_support,
                   "verified_statements": len(verified), "verified_supported": v_supported,
                   "verified_citations": len(v_cites), "verified_supporting": v_cite_support,
                   "inferred_statements": len(inferred),
                   "spine_blocks": spine_total,
                   "spine_grounded_blocks": len(spine_verified),
                   "untagged_or_unverified_statements": factual - len(verified) - len(inferred)},
        "per_statement": per_statement,
        "per_citation": per_citation,
        "blocking": blocking,
    }


def verify_files(
    ir_path: str | Path,
    ledger_path: str | Path,
    rubric_path: str | Path = DEFAULT_RUBRIC,
    backend_name: str = "auto",
    primer_type: str | None = None,
) -> dict:
    return evaluate(
        DocumentIR.from_yaml(ir_path),
        SourceLedger.from_yaml(ledger_path),
        backend=resolve_backend(backend_name),
        thresholds=load_thresholds(rubric_path, primer_type),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify citation quality (R-GROUND-01/02/03) against the ledger.")
    ap.add_argument("ir")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    ap.add_argument("--backend", default="auto", choices=["auto", "lexical", "nli", "claude"])
    # Free-text on purpose: an unknown type resolves to the STRICTEST row of the rubric table rather
    # than erroring, so a typo costs a confusing failure instead of a silently loosened gate.
    ap.add_argument("--primer-type", default=None,
                    help="primer type selecting the composition row in eval-rubric.yaml")
    ap.add_argument("--out", default="verify-report.json")
    args = ap.parse_args(argv)

    report = verify_files(args.ir, args.ledger, args.rubric, args.backend, args.primer_type)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    r = report
    th = r["thresholds"]
    print(f"{'BLOCKING' if r['blocking'] else 'clean'} — "
          f"verified_recall={r['verified_recall']} (>= {th['verified_recall']}) "
          f"verified_precision={r['verified_precision']} (>= {th['verified_precision']}) "
          f"ungrounded_share={r['ungrounded_share']} (<= {th['max_inferred_share']}) "
          f"spine_grounded={r['spine_grounded']}{'' if r['spine_scoreable'] else ' (vacuous — no lede or card block; R-ARCH-06 is what requires them)'} "
          f"(>= {th.get('min_spine_grounded', 0.0)}) "
          f"primer_type={r['primer_type']} "
          f"scoreable={r['scoreable']} "
          f"unresolved={len(r['resolves_to_ledger']['violations'])} backend={r['backend']} -> {args.out}")
    if not r["primer_type_recognised"]:
        print(f"  (primer_type {r['primer_type']!r} is not in the rubric's composition table — "
              f"resolved to the STRICTEST row so a typo cannot loosen the gate)")
    if r["backend"] == "lexical":
        print("  (lexical proxy: entailment thresholds are NOT gated — word overlap against a "
              "required paraphrase is not evidence; only ledger resolution blocks here)")
    for v in r["resolves_to_ledger"]["violations"]:
        print(f"  [unresolved] {v['block_id']}: {v['detail']}")
    for c in r["per_citation"]:
        if not c["supports"]:
            print(f"  [non-supporting] {c['block_id']}/{c['claim_id']}: quote does not entail the statement")
    return 1 if r["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
