"""Cross-reference integrity.

Classification: local-deterministic
Implements: R-XREF-02 (xrefs_resolve)

On the IR: every `Figure N` mentioned in prose must have a matching figure caption; every
`[block: id]` pointer must resolve to a real block_id; vague directional pointers ('as shown
below/above', 'see below/above') are phantom references with no resolvable target.

(The nav/TOC==headings clause is an HTML-projection concern — checked in Prompt 4's renderer.)
"""
from __future__ import annotations

import re

from checks._base import LintContext, Violation

_FIG_DEF_RE = re.compile(r"\bFigure\s+(\d+)\b", re.IGNORECASE)
_FIG_REF_RE = re.compile(r"\bFigure\s+(\d+)\b", re.IGNORECASE)
_BLOCK_REF_RE = re.compile(r"\[block:\s*([\w-]+)\]")
_PHANTOM_RE = re.compile(r"\b(?:as shown|see|shown)\s+(?:below|above)\b", re.IGNORECASE)


def xrefs_resolve(ctx: LintContext) -> list[Violation]:
    fig_defs: set[str] = set()
    for b in ctx.ir.flatten_blocks():
        if b.caption:
            fig_defs.update(_FIG_DEF_RE.findall(b.caption))
    all_ids = set(ctx.ir.all_block_ids())

    out: list[Violation] = []
    for b in ctx.ir.flatten_blocks():
        text = b.text or ""
        # caption text also references nothing here; only prose carries refs
        for num in _FIG_REF_RE.findall(text):
            if num not in fig_defs:
                out.append(Violation(b.block_id, f"phantom reference to Figure {num} (no figure caption defines it)"))
        for ref in _BLOCK_REF_RE.findall(text):
            if ref not in all_ids:
                out.append(Violation(b.block_id, f"unresolved cross-reference [block: {ref}] (no such block_id)"))
        for m in _PHANTOM_RE.finditer(text):
            out.append(Violation(b.block_id, f"phantom directional reference {m.group(0)!r} (no resolvable target)"))
    return out
