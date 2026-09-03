"""Fetched documents -> atomic claims in source-ledger.yaml.

Classification: agent-orchestrated (the extraction step calls a model), with a DETERMINISTIC
anchoring gate around it.
Implements: R-GROUND-01 (never fabricate), R-GROUND-05 (corroboration + recency), R-DISC-01
            (leads are pointers, not provenance)

The model proposes claims; `anchor_claims` decides which survive, and it is pure:

  1. the quote must appear VERBATIM in the fetched body — this is the anti-fabrication floor and
     the R-DISC-01 firewall in one check. A claim sourced from a discovery report's prose rather
     than from a page we actually fetched cannot pass it.
  2. the quote must be <= MAX_QUOTE_WORDS (copyright discipline: the primer paraphrases).
  3. every surviving claim carries its source_id, location, and the document's content hash.

Corroboration and recency (R-GROUND-05) are likewise computed, not asserted: `corroborate` counts
INDEPENDENT sources supporting the same claim, and `mark_recency` stamps as_of_date on the claims
that name a version.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Claim, Source, SourceLedger  # noqa: E402
from research.discovery import LexicalSimilarity, Similarity  # noqa: E402
from research.grouping import ClaimGrouper, resolve_groups  # noqa: E402
from research.retrieval_loop import Document  # noqa: E402

MAX_QUOTE_WORDS = 15                   # SKILL.md: quotes stay short; the primer paraphrases
CLAIM_MATCH_THRESHOLD = 0.6            # two claims count as the same for corroboration
VENDOR_TYPES = {"vendor"}              # excluded from independent corroboration (R-EVID-03)

# a claim is version/SOTA-shaped when it pins a version or asserts currency
_VERSION_RE = re.compile(r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+(?:\.\d+)?\b", re.IGNORECASE)
_SOTA_RE = re.compile(r"\b(state of the art|sota|current|latest|as of|newest|now the default)\b",
                      re.IGNORECASE)


class Extractor(Protocol):
    """The model call: a fetched document -> proposed atomic claims.

    Each proposal is {text, quote, location, confidence}. Proposals are untrusted — `anchor_claims`
    is what decides whether one becomes provenance.
    """

    def __call__(self, document: Document) -> list[dict]: ...


class QuoteScanExtractor:
    """Deterministic offline extractor: lifts sentences the document marks as claim-bearing.

    A stand-in for the model so the anchoring gate and the ledger build are testable without one.
    It can only ever propose text that is literally in the document, which is the point — it
    cannot manufacture the failure mode the gate exists to catch, so tests inject bad proposals
    directly.
    """

    def __call__(self, document: Document) -> list[dict]:
        out: list[dict] = []
        for i, line in enumerate(document.text.splitlines()):
            line = line.strip()
            if not line.startswith("CLAIM:"):
                continue
            body = line.removeprefix("CLAIM:").strip()
            words = body.split()
            out.append({
                "text": body,
                "quote": " ".join(words[:MAX_QUOTE_WORDS]),
                "location": f"line {i + 1}",
                "confidence": "medium",
            })
        return out


def _too_long(quote: str) -> bool:
    return len(quote.split()) > MAX_QUOTE_WORDS


def anchor_claims(proposals: Iterable[dict], document: Document,
                  id_prefix: str | None = None) -> tuple[list[Claim], list[str]]:
    """Keep only proposals genuinely anchored in `document`. Returns (claims, rejection reasons).

    This is the deterministic gate the whole grounding story rests on: a model that invents a
    quote, or paraphrases one it never saw, does not get to write to the ledger.
    """
    kept: list[Claim] = []
    rejected: list[str] = []
    prefix = id_prefix or document.source_id[:8]

    for n, p in enumerate(proposals, start=1):
        quote = (p.get("quote") or "").strip()
        text = (p.get("text") or "").strip()
        if not text:
            rejected.append(f"{prefix}-{n}: no claim text")
            continue
        if not quote:
            rejected.append(f"{prefix}-{n}: no supporting quote (R-GROUND-01)")
            continue
        if _too_long(quote):
            rejected.append(f"{prefix}-{n}: quote is {len(quote.split())} words (> {MAX_QUOTE_WORDS})")
            continue
        if not document.contains(quote):
            rejected.append(
                f"{prefix}-{n}: quote not found in the fetched body of {document.url} — "
                f"a claim must be anchored to a document we fetched, not to a discovery lead (R-DISC-01)")
            continue
        kept.append(Claim(
            claim_id=f"C-{prefix}-{n}",
            text=text,
            quote=quote,
            location=p.get("location"),
            confidence=p.get("confidence") or "medium",
            provenance_origin="user" if document.provenance_origin == "user" else "discovered",
        ))
    return kept, rejected


def build_ledger(documents: Iterable[Document], extractor: Extractor | None = None) -> tuple[SourceLedger, list[str]]:
    """Extract + anchor across every fetched document, producing the ledger. Returns (ledger, rejections)."""
    extractor = extractor or QuoteScanExtractor()
    sources: list[Source] = []
    rejections: list[str] = []

    for doc in documents:
        claims, rejected = anchor_claims(extractor(doc), doc)
        rejections.extend(rejected)
        sources.append(Source(
            source_id=doc.source_id,
            url=doc.url,
            title=doc.title,
            type=doc.source_type,
            retrieved_at=doc.retrieved_at,
            content_hash=doc.content_hash,
            provenance_origin=doc.provenance_origin,
            claims=claims,
        ))
    return SourceLedger(sources=sources), rejections


def corroborate(ledger: SourceLedger, backend: Similarity | None = None,
                threshold: float = CLAIM_MATCH_THRESHOLD,
                grouper: ClaimGrouper | None = None,
                notes: list[str] | None = None) -> SourceLedger:
    """R-GROUND-05: set corroboration_count + corroborated_by on multiply-supported claims.

    Counts INDEPENDENT sources — a claim repeated twice within one document is one source, and
    vendor sources are still counted here but tagged, so coverage.py can apply the stricter
    non-vendor rule to performance claims (R-EVID-03) without losing information.

    Two ways to decide "the same claim", one meaning
    -----------------------------------------------
    Without a `grouper` this is pairwise lexical overlap: for each claim, every OTHER source with a
    claim above `threshold`. That is the offline path, and on real prose it finds almost nothing —
    spec-03's first campaign corroborated 0 of 271 claims, which quietly makes R-GROUND-05 and
    R-EVID-03 unenforceable in exactly the runs that need them.

    With a `grouper` the model proposes sets of claims that assert one fact and `resolve_groups`
    decides; corroboration is then a count over the DISTINCT SOURCES in a surviving group. The
    field means the same thing either way — independent sources supporting one assertion — and the
    group form is strictly better behaved: pairwise similarity is not transitive, so A~B and B~C
    could credit A and C to each other's support without ever being compared.
    """
    if grouper is not None:
        return _corroborate_by_group(ledger, grouper, notes)

    backend = backend or LexicalSimilarity()
    indexed = [(s, c) for s in ledger.sources for c in s.claims]

    for source, claim in indexed:
        supporters = {
            other_source.source_id
            for other_source, other in indexed
            if other_source.source_id != source.source_id
            and backend.score(claim.text, other.text) >= threshold
        }
        if supporters:
            claim.corroborated_by = sorted(supporters)
            claim.corroboration_count = len(supporters) + 1   # this source plus the others
    return ledger


def _corroborate_by_group(ledger: SourceLedger, grouper: ClaimGrouper,
                          notes: list[str] | None = None) -> SourceLedger:
    """Count distinct sources per resolved group. A single-source group corroborates nothing."""
    indexed = {c.claim_id: (s.source_id, c) for s in ledger.sources for c in s.claims}
    claims = sorted(((cid, c.text) for cid, (_, c) in indexed.items()), key=lambda x: x[0])
    # The grouper gets the claim->source map so it can skip work it could never learn from: a
    # candidate set drawn from one source has no corroboration to find, whatever it says.
    params = {"claim_sources": {cid: src for cid, (src, _) in indexed.items()}}
    groups, rejected = resolve_groups(grouper(claims, params), claims)
    if notes is not None:
        notes.extend(rejected)

    for group in groups:
        sources = sorted({indexed[cid][0] for cid in group.claim_ids})
        if len(sources) < 2:
            continue
        for cid in group.claim_ids:
            own, claim = indexed[cid]
            claim.corroborated_by = [s for s in sources if s != own]
            claim.corroboration_count = len(sources)
    return ledger


def mark_recency(ledger: SourceLedger, as_of: str | None = None) -> SourceLedger:
    """R-GROUND-04/05: stamp as_of_date on version/SOTA claims — the ones that go stale.

    `as_of` is passed in rather than read from the clock so a replayed run produces a byte-identical
    ledger.
    """
    for source in ledger.sources:
        for claim in source.claims:
            if _VERSION_RE.search(claim.text) or _SOTA_RE.search(claim.text):
                claim.as_of_date = as_of or source.retrieved_at or None
    return ledger


def mark_conflicts(ledger: SourceLedger, contradictions: dict[str, list[str]]) -> SourceLedger:
    """Record cross-source disagreement as contested + contradicts (R-GROUND-05).

    The judgment "these two claims contradict" is model-supplied; recording it symmetrically is
    deterministic, and symmetry matters — a conflict visible from only one side reads as settled
    from the other.
    """
    by_id = {c.claim_id: c for s in ledger.sources for c in s.claims}
    for claim_id, others in contradictions.items():
        for other_id in others:
            for a, b in ((claim_id, other_id), (other_id, claim_id)):
                claim = by_id.get(a)
                if claim is None or b not in by_id:
                    continue
                claim.contested = True
                if b not in claim.contradicts:
                    claim.contradicts.append(b)
    return ledger
