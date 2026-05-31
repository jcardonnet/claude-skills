"""Terminology univocity.

Classification: local-deterministic
Implements: R-VOCAB-01 (canonical_terms)

Two deterministic, concept-map-grounded checks:
  (A) no two concepts share a canonical term;
  (B) a concept whose canonical term never appears in the prose, yet is referenced by one of its
      declared aliases, is using a variant surface form without establishing the canonical one.

The directive's other half — flagging over-definition of assumed in-domain terms — needs a
home_domain term list the IR does not carry, so it is left to the expertise-calibration critic.
"""
from __future__ import annotations

import re

from checks._base import LintContext, Violation


def _doc_text(ctx: LintContext) -> str:
    parts: list[str] = []
    for sec in ctx.ir.sections:
        parts.append(sec.title or "")
        for b in sec.blocks:
            parts.append(b.text or "")
            parts.append(b.caption or "")
    return "\n".join(parts)


def _contains_phrase(text_lower: str, phrase: str) -> bool:
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    return re.search(rf"\b{re.escape(phrase)}\b", text_lower) is not None


def canonical_terms(ctx: LintContext) -> list[Violation]:
    cm = ctx.concept_map
    if cm is None:
        return []
    out: list[Violation] = []

    # (A) canonical terms unique across concepts
    seen: dict[str, str] = {}
    for c in cm.concepts:
        key = c.canonical_term.strip().lower()
        if key in seen:
            out.append(Violation(None, f"canonical term {c.canonical_term!r} reused by '{seen[key]}' and '{c.concept_id}'"))
        else:
            seen[key] = c.concept_id

    # (B) alias used while canonical term never appears
    text_lower = _doc_text(ctx).lower()
    for c in cm.concepts:
        if _contains_phrase(text_lower, c.canonical_term):
            continue
        for alias in c.aliases:
            if _contains_phrase(text_lower, alias):
                out.append(Violation(
                    None,
                    f"concept '{c.concept_id}' referenced by alias {alias!r} but canonical term "
                    f"{c.canonical_term!r} never appears",
                ))
                break
    return out
