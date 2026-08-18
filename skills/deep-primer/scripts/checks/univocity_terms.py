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

from checks._base import CheckNotApplicable, LintContext, Violation


def _doc_text(ctx: LintContext) -> str:
    """Every surface form the document actually puts in front of a reader.

    Two blind spots used to live here and both bit in the damaging direction. Walking `sec.blocks`
    never descended into an h3, so an alias used in a subsection went unreported; and reading
    `b.text`/`b.caption` skipped the three composite roles, so a canonical term ESTABLISHED in a
    card read as "never appears" and (B) reported a violation the document does not commit.
    `flatten_blocks` + `prose_segments` is what "the prose" means (R-PROJ-01).
    """
    parts: list[str] = []
    for sec in ctx.ir.sections:
        parts.append(sec.title or "")
        parts.extend(sub.title or "" for sub in sec.subsections)
    parts.extend(seg for b in ctx.ir.flatten_blocks() for seg in b.prose_segments)
    return "\n".join(parts)


def _contains_phrase(text_lower: str, phrase: str) -> bool:
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    return re.search(rf"\b{re.escape(phrase)}\b", text_lower) is not None


def canonical_terms(ctx: LintContext) -> list[Violation]:
    cm = ctx.concept_map
    if cm is None:
        raise CheckNotApplicable("R-VOCAB-01 needs a concept-map; none was supplied")
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


def home_anchor_distinct(ctx: LintContext) -> list[Violation]:
    """R-XREF-04 (also_hard_lint): a home_anchor must not restate its own concept.

    The mechanical half of the home ~= target gap. When the reader already lives in the target
    domain, the bridge degenerates into "X is like X" and the advance organizer never fires; an
    anchor equal to (or contained in) the concept's own canonical term or aliases is that failure
    in its detectable form. Whether a distinct anchor is genuinely ADJACENT stays a critic call.
    """
    cm = ctx.concept_map
    if cm is None:
        raise CheckNotApplicable("R-XREF-04 needs a concept-map; none was supplied")

    out: list[Violation] = []
    for c in cm.concepts:
        anchor = (c.home_anchor or "").strip().lower()
        if not anchor:
            continue
        own = {(c.canonical_term or "").strip().lower(), *(a.strip().lower() for a in c.aliases)}
        own.discard("")
        for term in own:
            if anchor == term or anchor in term or term in anchor:
                out.append(Violation(
                    None,
                    f"concept '{c.concept_id}': home_anchor {c.home_anchor!r} restates its own term "
                    f"{term!r}; resolve it to the nearest ADJACENT technique (R-XREF-04)",
                ))
                break
    return out
