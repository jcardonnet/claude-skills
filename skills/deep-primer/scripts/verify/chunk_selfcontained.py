"""LLM-MD chunk self-containment verifier.

Classification: model_verified
Implements: R-PROJ-04

For each kept block, verify the de-anaphorized chunk (produced by render_llm_md.deanaphorize):
  1. no dangling anaphora — it must not open with a bare demonstrative/pronoun and must carry no
     cross-block reference ("as above", "see Figure 3");
  2. it still entails its source claim_ids — the chunk (premise) supports each cited claim
     (hypothesis), via the pluggable entailment backend (offline default = lexical proxy).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import ConceptMap, DocumentIR, SourceLedger  # noqa: E402
from render.render_llm_md import (  # noqa: E402
    _ANAPHOR_LEAD,
    _CROSSREF,
    _referent_map,
    distilled_segments,
    kept_blocks,
)
from verify._entailment import Entailment, resolve_backend  # noqa: E402


def has_dangling_anaphora(text: str) -> bool:
    """The producer's own patterns, imported rather than restated.

    This module used to keep a `_LEAD_ANAPHOR` / `_CROSSREF` pair of its own, written to match
    `render_llm_md`'s. A verifier that re-declares the producer's definition stops verifying it the
    moment either side is edited, and R-PROJ-04 is precisely the claim that `deanaphorize` left
    nothing dangling — which requires both to agree on what dangling means.
    """
    return bool(_ANAPHOR_LEAD.match(text.strip())) or bool(_CROSSREF.search(text))


def _claim_text(ledger: SourceLedger | None) -> dict[str, str]:
    if ledger is None:
        return {}
    return {c.claim_id: (c.quote or c.text or "") for s in ledger.sources for c in s.claims}


def verify(
    ir: DocumentIR,
    ledger: SourceLedger | None = None,
    concept_map: ConceptMap | None = None,
    backend: Entailment | None = None,
) -> dict:
    backend = backend or resolve_backend("auto")
    referents = _referent_map(concept_map)
    claims = _claim_text(ledger)

    verdicts: list[dict] = []
    for sec, b in kept_blocks(ir):
        # What the projection ACTUALLY emits for this block, from the projection itself. Re-deriving
        # it here as `b.text or ""` verified a string render_llm_md never produced: empty for every
        # card and contested block, and un-de-anaphorized for figures.
        segments = distilled_segments(sec, b, referents)
        chunk = "\n".join(segments)
        # Per segment, not on the join: `_ANAPHOR_LEAD` is anchored at `^`, so a card whose `idea`
        # opens "This bounds recall" hides behind the `Claim:` label of the line before it.
        dangling = any(has_dangling_anaphora(s) for s in segments)
        resolvable = [cid for cid in b.claim_ids if cid in claims]
        entails = all(backend.supports(chunk, claims[cid]) for cid in resolvable) if resolvable else True
        verdicts.append({
            "block_id": b.block_id,
            "chunk": chunk,
            "dangling_anaphora": dangling,
            "entails_claims": entails,
            "unresolved_claims": [cid for cid in b.claim_ids if cid not in claims],
            "ok": (not dangling) and entails,
        })

    bad = [v for v in verdicts if not v["ok"]]
    return {
        "backend": backend.name,
        "ok": not bad,
        "blocking": bool(bad),
        "verdicts": verdicts,
        "failures": [v["block_id"] for v in bad],
        # Reported separately because the two halves have different standing. Dangling anaphora is a
        # deterministic regex verdict and means the same thing on every backend; entailment is only
        # meaningful on a real one, since the lexical proxy scores word overlap against a paraphrase.
        # A caller that gates on the whole verdict either gates on the proxy or gates on nothing.
        "dangling_failures": [v["block_id"] for v in verdicts if v["dangling_anaphora"]],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify LLM-MD chunk self-containment (R-PROJ-04).")
    ap.add_argument("ir")
    ap.add_argument("--ledger")
    ap.add_argument("--concept-map", dest="concept_map")
    ap.add_argument("--backend", default="auto", choices=["auto", "lexical", "nli", "claude"])
    ap.add_argument("--out", default="chunk-selfcontained-report.json")
    args = ap.parse_args(argv)
    report = verify(
        DocumentIR.from_yaml(args.ir),
        SourceLedger.from_yaml(args.ledger) if args.ledger else None,
        ConceptMap.from_yaml(args.concept_map) if args.concept_map else None,
        resolve_backend(args.backend),
    )
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{'OK' if report['ok'] else 'FAIL'} — {len(report['verdicts'])} chunks, failures={report['failures']}")
    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
