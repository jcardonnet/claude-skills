"""Structural coverage lints on the IR.

Classification: local-deterministic
Implements: R-CONSIST-01 (layer_coverage), R-ARCH-06 (length_budget)

Other structure_coverage check.refs in the registry (params_present, heading_hierarchy,
banned_heading_terms, card_rows, summary_budgets, operational_artifacts, recall_count) target
HTML/subsection structure the V1 IR does not yet model; lint.py marks them skip. They are owned
by Prompt 4 (HTML round-trip) or a later IR extension, not Prompt 2.
"""
from __future__ import annotations

import statistics

from checks._base import CONTENT_ROLES, LintContext, Violation, n_words

_SUMMARY_BODY_THRESHOLD = 400  # words; a section past this needs a summary (R-CONSIST-01)
_REQUIRED_LAYERS = ("lede", "card", "recall")


def layer_coverage(ctx: LintContext) -> list[Violation]:
    """Every section carries lede + card + recall; a >400-word body requires a summary.

    (The h3:sub_sum 1:1 clause needs subsection structure the flat V1 IR lacks — deferred.)
    """
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        present = {b.role.value for b in sec.blocks}
        for layer in _REQUIRED_LAYERS:
            if layer not in present:
                out.append(Violation(sec.block_id, f"section missing required layer: {layer}"))
        body_words = sum(n_words(b.text) for b in sec.blocks if b.role.value in CONTENT_ROLES)
        if body_words > _SUMMARY_BODY_THRESHOLD and "summary" not in present:
            out.append(Violation(
                sec.block_id,
                f"section body is {body_words} words (>{_SUMMARY_BODY_THRESHOLD}) but has no summary layer",
            ))
    return out


def length_budget(ctx: LintContext) -> list[Violation]:
    """Total length tracks length_budget; flag near-uniform section lengths (salience-blind padding)."""
    out: list[Violation] = []
    section_words = [
        sum(n_words(b.text) + n_words(b.caption) for b in sec.blocks) for sec in ctx.ir.sections
    ]
    total = sum(section_words)

    budget = ctx.length_budget()
    if budget:
        lo, hi = int(0.6 * budget), int(1.4 * budget)
        if not (lo <= total <= hi):
            out.append(Violation(
                None,
                f"total {total} words outside budget band [{lo}, {hi}] (length_budget={budget})",
            ))

    # uniform-depth heuristic: many sections of near-identical length => padded, not salience-allocated
    if len(section_words) >= 3 and total > 0:
        mean = statistics.mean(section_words)
        if mean > 0:
            cv = statistics.pstdev(section_words) / mean
            if cv < 0.15:
                out.append(Violation(
                    None,
                    f"section lengths near-uniform (cv={cv:.2f}); allocate depth by salience, not uniform padding",
                ))
    return out
