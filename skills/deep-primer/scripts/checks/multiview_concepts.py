"""Multi-view coverage per core concept.

Classification: local-deterministic
Implements: R-MV-01 (modes_per_concept)

A concept passes when >=3 distinct representation modes are *realized* across IR blocks. A block
realizes a concept-in-a-mode when it carries data-mode and either its own data-concept or (when it
has none) its section's concept.
"""
from __future__ import annotations

from checks._base import LintContext, Violation

_MIN_MODES = 3


def modes_per_concept(ctx: LintContext) -> list[Violation]:
    cm = ctx.concept_map
    if cm is None:
        return []

    realized: dict[str, set[str]] = {}
    for sec in ctx.ir.sections:
        for b in sec.blocks:
            if b.mode is None:
                continue
            cid = b.concept or sec.concept
            if cid:
                realized.setdefault(cid, set()).add(b.mode.value)

    out: list[Violation] = []
    for c in cm.concepts:
        modes = realized.get(c.concept_id, set())
        if len(modes) < _MIN_MODES:
            out.append(Violation(
                None,
                f"concept '{c.concept_id}' realized in {len(modes)} mode(s) {sorted(modes)} (<{_MIN_MODES})",
            ))
    return out
