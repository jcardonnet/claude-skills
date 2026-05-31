"""Footnote integrity.

Classification: local-deterministic
Implements: R-CONSIST-03 (footnote_balance)

On the IR, footnotes live in block text as Markdown-style references `[^id]` and definitions
`[^id]:` at line start. Every marker needs a matching definition and vice versa.
"""
from __future__ import annotations

import re

from checks._base import LintContext, Violation

_DEF_RE = re.compile(r"(?m)^\s*\[\^([^\]]+)\]:")
_MARKER_RE = re.compile(r"\[\^([^\]]+)\](?!:)")


def footnote_balance(ctx: LintContext) -> list[Violation]:
    text = "\n".join(b.text or "" for b in ctx.ir.flatten_blocks())
    defs = set(_DEF_RE.findall(text))
    markers = set(_MARKER_RE.findall(text))

    out: list[Violation] = []
    for mk in sorted(markers - defs):
        out.append(Violation(None, f"footnote marker [^{mk}] has no matching definition"))
    for d in sorted(defs - markers):
        out.append(Violation(None, f"footnote definition [^{d}] has no matching marker"))
    return out
