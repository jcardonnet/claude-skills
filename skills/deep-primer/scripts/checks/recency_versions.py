"""Recency / version freshness (flag-only offline).

Classification: local-deterministic (web-assisted in production)
Implements: R-GROUND-04 (version_freshness)

Offline (this sandbox, per CAPABILITIES.md) there is no live version lookup, so this is FLAG-ONLY:
it surfaces version tokens for human/agent review rather than confirming staleness. R-GROUND-04 is
SHOULD, so these are warnings. The version pattern requires a 'v' prefix or a 3-part number to
avoid matching section refs like '§3.2'.
"""
from __future__ import annotations

import re

from checks._base import LintContext, Violation

_VER_RE = re.compile(r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+\.\d+\b", re.IGNORECASE)


def version_freshness(ctx: LintContext) -> list[Violation]:
    out: list[Violation] = []
    for b in ctx.ir.flatten_blocks():
        for field in (b.text, b.caption):
            if not field:
                continue
            for tok in sorted({m.group(0) for m in _VER_RE.finditer(field)}):
                out.append(Violation(
                    b.block_id,
                    f"version token {tok!r} present — freshness unverifiable offline (flag-only, R-GROUND-04)",
                ))
    return out
