"""Version / recency sweep (R-GROUND-04).

Classification: agent-orchestrated (needs a live version lookup), degrading to flag-only offline.

Extract every named technology from the ledger, pin its current version, and flag anything stale.
Offline — this sandbox, per CAPABILITIES.md — there is no live lookup, so the sweep FLAGS version
tokens for review rather than asserting staleness it cannot verify. Claiming a version is current
without checking would be exactly the false precision R-GROUND-01 forbids.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import SourceLedger  # noqa: E402

# "<name> 1.2.3" / "<name> v1.2" — a named technology carrying a version.
# Names are NOT required to be capitalized: pgvector, numpy, spaCy and kubectl are the norm here,
# and requiring an initial capital silently misses most real version references.
_NAMED_VERSION_RE = re.compile(r"\b([A-Za-z][\w.+-]*)\s+(v)?(\d+(?:\.\d+)+)\b")


def _looks_like_a_technology(name: str, has_v: bool, version: str) -> bool:
    """Filter the bare-number false positives ("recall 0.8", "section 2.1").

    A hit counts when the version is explicitly marked (`v1.2`), has three components (`0.7.0` —
    software versioning, not a measurement), or the name carries an internal capital (spaCy, HNSW).
    """
    return has_v or version.count(".") >= 2 or any(ch.isupper() for ch in name)


@dataclass
class VersionFinding:
    technology: str
    cited_version: str
    current_version: str | None = None
    claim_id: str | None = None
    stale: bool | None = None          # None = unverifiable offline

    def describe(self) -> str:
        if self.current_version is None:
            return (f"{self.technology} {self.cited_version}: freshness unverifiable offline "
                    f"(flag-only, R-GROUND-04)")
        verdict = "STALE" if self.stale else "current"
        return f"{self.technology} {self.cited_version}: {verdict} (latest {self.current_version})"


class VersionLookup(Protocol):
    """Live lookup seam: technology name -> its current version string."""

    def __call__(self, technology: str) -> str | None: ...


def extract_versions(ledger: SourceLedger) -> list[VersionFinding]:
    """Every named technology + version pinned anywhere in the ledger's claims."""
    out: list[VersionFinding] = []
    seen: set[tuple[str, str]] = set()
    for source in ledger.sources:
        for claim in source.claims:
            for tech, v_flag, version in _NAMED_VERSION_RE.findall(claim.text or ""):
                if not _looks_like_a_technology(tech, bool(v_flag), version):
                    continue
                key = (tech.strip(), version)
                if key in seen:
                    continue
                seen.add(key)
                out.append(VersionFinding(technology=tech.strip(), cited_version=version,
                                          claim_id=claim.claim_id))
    return out


def sweep(ledger: SourceLedger, lookup: VersionLookup | None = None) -> list[VersionFinding]:
    """Pin current versions where a lookup is available; otherwise flag for review.

    A finding with `stale is None` is explicitly *unknown*, never silently treated as fresh.
    """
    findings = extract_versions(ledger)
    if lookup is None:
        return findings
    for f in findings:
        current = lookup(f.technology)
        f.current_version = current
        f.stale = None if current is None else (current != f.cited_version)
    return findings


def stale_findings(findings: list[VersionFinding]) -> list[VersionFinding]:
    return [f for f in findings if f.stale]
