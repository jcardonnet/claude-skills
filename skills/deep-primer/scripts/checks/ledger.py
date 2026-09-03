"""Source-ledger provenance lint (deterministic).

Classification: local-deterministic
Implements: R-GROUND-05

The campaign and the grounding loop produce corroboration, conflict, and recency signal; this
checks that the ledger actually RECORDS it. Without these fields provenance collapses to a bare
source id, and everything downstream — the contested rendering, the non-vendor rule for
performance claims, the staleness sweep — loses the input it needs.

Reads the ledger, so it runs in its own pass (`input: ledger`), not the IR lint.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import SourceLedger  # noqa: E402

_VERSION_RE = re.compile(r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+(?:\.\d+)?\b", re.IGNORECASE)
_SOTA_RE = re.compile(r"\b(state of the art|sota|current|latest|as of|newest|now the default)\b",
                      re.IGNORECASE)
MAX_QUOTE_WORDS = 15


def provenance_fields(source_ledger: SourceLedger | dict) -> list[str]:
    """Return [] if the ledger satisfies R-GROUND-05, else a list of violation strings."""
    ledger = SourceLedger(**source_ledger) if isinstance(source_ledger, dict) else source_ledger
    problems: list[str] = []
    known_claims = ledger.claim_ids()
    known_sources = ledger.source_ids()

    for source in ledger.sources:
        for claim in source.claims:
            cid = claim.claim_id

            # corroboration: the two fields travel together or not at all
            if claim.corroborated_by and claim.corroboration_count is None:
                problems.append(f"{cid}: corroborated_by is set but corroboration_count is not")
            if claim.corroboration_count and claim.corroboration_count > 1 and not claim.corroborated_by:
                problems.append(
                    f"{cid}: corroboration_count {claim.corroboration_count} but no corroborated_by "
                    f"source ids — the supporting sources are unrecoverable")
            for sid in claim.corroborated_by:
                if sid not in known_sources:
                    problems.append(f"{cid}: corroborated_by {sid!r} is not a source in this ledger")
                if sid == source.source_id:
                    problems.append(f"{cid}: corroborated_by lists its own source; corroboration must be independent")

            # recency: a version/SOTA claim without as_of_date cannot be checked for staleness
            if (_VERSION_RE.search(claim.text or "") or _SOTA_RE.search(claim.text or "")) \
                    and claim.as_of_date is None:
                problems.append(f"{cid}: version/SOTA claim carries no as_of_date (R-GROUND-04/05)")

            # conflict: contested and contradicts travel together, and must resolve
            if claim.contested and not claim.contradicts:
                problems.append(f"{cid}: contested but lists no contradicting claim")
            if claim.contradicts and not claim.contested:
                problems.append(f"{cid}: lists contradicts but is not marked contested")
            for other in claim.contradicts:
                if other not in known_claims:
                    problems.append(f"{cid}: contradicts {other!r}, which is not a claim in this ledger")

            # the grounding floor: a claim without a short verbatim quote is not provenance
            if not (claim.quote or "").strip():
                problems.append(f"{cid}: no supporting quote (R-GROUND-01)")
            elif len(claim.quote.split()) > MAX_QUOTE_WORDS:
                problems.append(
                    f"{cid}: quote is {len(claim.quote.split())} words (> {MAX_QUOTE_WORDS})")
    return problems
