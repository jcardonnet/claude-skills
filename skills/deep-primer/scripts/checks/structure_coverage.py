"""Structural coverage lints on the IR.

Classification: local-deterministic
Implements: R-CONSIST-01 (layer_coverage), R-ARCH-06 (length_budget), R-PARAM-01 (params_present),
            R-ARCH-05 (heading_hierarchy), R-CARD-02 (card_rows), R-SUMM-02 (summary_budgets),
            R-RECALL-01 (recall_count), R-ART-01 (operational_artifacts),
            R-SCENT-01 (banned_heading_terms — the also_hard_lint companion)

All of these read the IR. The subsection level, typed card rows, recall items, and artifact_kind
they depend on are part of the canonical IR (see references/artifact-schemas.md); nothing here
parses HTML.
"""
from __future__ import annotations

import statistics

from checks._base import CONTENT_ROLES, LintContext, Violation, n_words

_SUMMARY_BODY_THRESHOLD = 400  # words; a section past this needs a summary (R-CONSIST-01)
_REQUIRED_LAYERS = ("lede", "card", "recall")
_REQUIRED_PARAMS = ("home_domain", "target_domain", "seniority_band", "length_budget")
_CARD_ROWS = ("idea", "home_anchor", "whats_new_vs_renamed", "reach_for_when",
              "skip_when", "key_exemplar", "confidence")
_RECALL_ITEMS_PER_SECTION = 3          # R-RECALL-01
_SECTION_SUMMARY_WORD_CAP = 500        # R-SUMM-02 ceiling, not a target
_ARTIFACT_KINDS = ("decision_matrix", "checklist", "failure_catalog", "decision_aid")
# R-SCENT-01: generic labels that carry no information scent
_BANNED_HEADINGS = {"overview", "introduction", "key concepts", "background",
                    "conclusion", "miscellaneous"}


def layer_coverage(ctx: LintContext) -> list[Violation]:
    """Every section carries lede + card + recall; every h3 carries exactly one sub-sum; a
    >400-word body requires a section summary (R-CONSIST-01, reconciled with R-DEPTH-03)."""
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        present = {b.role.value for b in sec.blocks}
        for layer in _REQUIRED_LAYERS:
            if layer not in present:
                out.append(Violation(sec.block_id, f"section missing required layer: {layer}"))
        # the h3:sub_sum 1:1 clause — one `summary` block per subsection
        for sub in sec.subsections:
            n_sub_sums = sum(1 for b in sub.blocks if b.role.value == "summary")
            if n_sub_sums != 1:
                out.append(Violation(
                    sub.block_id,
                    f"subsection has {n_sub_sums} sub-sum(s) (a summary block); exactly 1 required",
                ))
        body_words = sum(n_words(b.text) for b in sec.all_blocks() if b.role.value in CONTENT_ROLES)
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
        sum(n_words(b.text) + n_words(b.caption) for b in sec.all_blocks()) for sec in ctx.ir.sections
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


def params_present(ctx: LintContext) -> list[Violation]:
    """R-PARAM-01: the four registry-defined parameters are resolved before generation.

    `outputs` and `seed_sources` are optional (they default to [html] / none), so their absence
    is not a violation.
    """
    missing = [p for p in _REQUIRED_PARAMS if not ctx.parameters.get(p)]
    if missing:
        return [Violation(None, f"parameters unresolved: {', '.join(missing)} (expected in meta.parameters)")]
    return []


def heading_hierarchy(ctx: LintContext) -> list[Violation]:
    """R-ARCH-05: h2 = section, h3 = subsection, h4 = body-block heading (never a container).

    h4 cannot leak into nav/TOC by construction — it is a `heading` attribute on a block rather
    than a container — so this check verifies the remaining half: every container that appears in
    the nav actually carries a title, and only body blocks carry an h4 heading.
    """
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        if not (sec.title or "").strip():
            out.append(Violation(sec.block_id, "section (h2) has no title; nav/TOC entry would be blank"))
        for sub in sec.subsections:
            if not (sub.title or "").strip():
                out.append(Violation(sub.block_id, "subsection (h3) has no title; nav/TOC entry would be blank"))
    for b in ctx.ir.flatten_blocks():
        if b.heading and b.role.value != "body":
            out.append(Violation(
                b.block_id,
                f"h4 heading on role={b.role.value!r}; sub-subsection headings belong on body blocks only",
            ))
    return out


def banned_heading_terms(ctx: LintContext) -> list[Violation]:
    """R-SCENT-01 (also_hard_lint): generic topic labels carry no information scent.

    The mechanical half of R-SCENT-01 — whether a heading is a *predictive claim* stays a critic
    judgment; an exact generic label is deterministically catchable.
    """
    out: list[Violation] = []
    headings: list[tuple[str, str]] = []
    for sec in ctx.ir.sections:
        headings.append((sec.block_id, sec.title))
        headings += [(sub.block_id, sub.title) for sub in sec.subsections]
    headings += [(b.block_id, b.heading) for b in ctx.ir.flatten_blocks() if b.heading]
    for bid, title in headings:
        if (title or "").strip().rstrip(":").lower() in _BANNED_HEADINGS:
            out.append(Violation(bid, f"banned generic heading {title!r}; headings must be predictive claims"))
    return out


def card_rows(ctx: LintContext) -> list[Violation]:
    """R-CARD-02: every card carries the seven required rows, none of them blank."""
    out: list[Violation] = []
    for b in ctx.ir.flatten_blocks():
        if b.role.value != "card":
            continue
        if b.rows is None:
            out.append(Violation(b.block_id, "card has no typed rows (R-CARD-02 requires all seven)"))
            continue
        blank = [r for r in _CARD_ROWS if not (getattr(b.rows, r, "") or "").strip()]
        if blank:
            out.append(Violation(b.block_id, f"card rows missing or blank: {', '.join(blank)}"))
    return out


def recall_count(ctx: LintContext) -> list[Violation]:
    """R-RECALL-01: exactly three check-yourself Q&As per section.

    Counts items across the section's recall blocks. A section with no recall block at all is
    R-CONSIST-01's finding (layer_coverage), not double-reported here.
    """
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        recalls = [b for b in sec.all_blocks() if b.role.value == "recall"]
        if not recalls:
            continue
        n = sum(len(b.items or []) for b in recalls)
        if n != _RECALL_ITEMS_PER_SECTION:
            out.append(Violation(
                sec.block_id,
                f"section has {n} recall item(s); exactly {_RECALL_ITEMS_PER_SECTION} required",
            ))
    return out


def summary_budgets(ctx: LintContext) -> list[Violation]:
    """R-SUMM-02: a section summary is <=500 words, and each h3 has exactly one sub-sum.

    The 1:1 clause is shared with R-CONSIST-01 (layer_coverage); it is restated here because the
    two rules are separately reportable and a reader of either finding needs the whole story.
    """
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        for b in sec.blocks:
            if b.role.value == "summary":
                words = n_words(b.text)
                if words > _SECTION_SUMMARY_WORD_CAP:
                    out.append(Violation(
                        b.block_id,
                        f"section summary is {words} words (>{_SECTION_SUMMARY_WORD_CAP} ceiling)",
                    ))
        for sub in sec.subsections:
            n_sub_sums = sum(1 for b in sub.blocks if b.role.value == "summary")
            if n_sub_sums != 1:
                out.append(Violation(sub.block_id, f"subsection has {n_sub_sums} sub-sum(s); exactly 1 required"))
    return out


def user_structure_respected(ctx: LintContext) -> list[Violation]:
    """R-ARCH-07: an explicit user structure governs the top-level outline.

    Checks the *mapping*, not the heading strings: each section declares the entry it realizes via
    `maps_to`, so a heading can still be a predictive claim (R-SCENT-01) rather than the user's
    label copied verbatim. No user_structure parameter means nothing to enforce.
    """
    wanted = ctx.parameters.get("user_structure")
    if not wanted:
        return []

    out: list[Violation] = []
    claimed: dict[str, list[str]] = {}
    for sec in ctx.ir.sections:
        if sec.maps_to is None:
            out.append(Violation(sec.block_id, "section declares no maps_to; a user structure is in force"))
        else:
            claimed.setdefault(sec.maps_to, []).append(sec.block_id)

    for entry in wanted:
        holders = claimed.get(entry, [])
        if not holders:
            out.append(Violation(None, f"user-structure entry {entry!r} is not realized by any section"))
        elif len(holders) > 1:
            out.append(Violation(None, f"user-structure entry {entry!r} claimed by {len(holders)} sections: {holders}"))

    for entry, holders in claimed.items():
        if entry not in wanted:
            out.append(Violation(holders[0], f"maps_to {entry!r} is not an entry of the user structure"))

    # order: the realized sequence must follow the user's, ignoring unmapped/extra sections
    realized = [s.maps_to for s in ctx.ir.sections if s.maps_to in wanted]
    expected = [e for e in wanted if e in realized]
    if realized != expected:
        out.append(Violation(None, f"section order {realized} does not follow the user structure {expected}"))
    return out


def operational_artifacts(ctx: LintContext) -> list[Violation]:
    """R-ART-01: all four operational artifacts present and distinct.

    Distinctness is structural: four blocks carrying four different `artifact_kind` values. Two
    artifacts collapsed into one table shows up as a missing kind.
    """
    kinds = [b.artifact_kind.value for b in ctx.ir.flatten_blocks() if b.artifact_kind is not None]
    missing = [k for k in _ARTIFACT_KINDS if k not in kinds]
    if missing:
        return [Violation(None, f"operational artifacts missing or collapsed: {', '.join(missing)}")]
    return []
