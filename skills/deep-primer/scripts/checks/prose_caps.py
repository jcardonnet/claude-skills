"""Prose structural caps + compression gradient.

Classification: local-deterministic
Implements: R-SUMM-03 (compression_gradient), R-PROSE-05 (length_caps), R-PROSE-04 (condition_first)

length_caps / condition_first use spaCy POS+dependency parse when available (per CAPABILITIES.md)
and degrade to regex heuristics otherwise. compression_gradient is pure token counting (always exact).
These are STRUCTURAL checks only — they never inspect vocabulary (R-PROSE-05 is explicit on this).
"""
from __future__ import annotations

import re

from checks._base import (
    CONTENT_ROLES,
    PROSE_ROLES,
    LintContext,
    Violation,
    get_nlp,
    n_words,
    split_sentences,
)

_PROC_CAP = 20       # procedural sentence word cap (R-PROSE-05)
_DESC_CAP = 25       # descriptive sentence word cap
_NOUN_CLUSTER = 3    # max consecutive nouns
_PARA_SENTENCES = 6  # max sentences per paragraph

# fallback imperative openers (no-POS path for condition_first / procedural classification)
_IMPERATIVES = {
    "use", "set", "add", "run", "call", "choose", "prefer", "avoid", "drop", "enable",
    "disable", "configure", "pick", "apply", "remove", "skip", "verify", "ensure", "check",
    "make", "start", "stop", "keep", "store", "index", "batch", "cache", "tune", "scale",
}
_COND_RE = re.compile(r"\b(if|when)\b", re.IGNORECASE)


def compression_gradient(ctx: LintContext) -> list[Violation]:
    """Within a section, a more-abstract layer is never longer than the layer it summarizes.

    Chain (most→least abstract): card.idea < section_summary < section_body (R-SUMM-03).
    Equal length is allowed; only a strictly-longer abstract layer is a violation.
    """
    out: list[Violation] = []
    for sec in ctx.ir.sections:
        layers: list[tuple[str, int]] = []
        for name, roles in (("card", {"card"}), ("summary", {"summary"}), ("body", CONTENT_ROLES)):
            present = [b for b in sec.blocks if b.role.value in roles]
            if present:
                layers.append((name, sum(n_words(b.text) for b in present)))
        for (a_name, a_w), (b_name, b_w) in zip(layers, layers[1:]):
            if a_w > b_w:
                out.append(Violation(
                    sec.block_id,
                    f"compression gradient broken: {a_name} ({a_w}w) longer than {b_name} ({b_w}w)",
                ))
    return out


def _prose_blocks(ctx: LintContext):
    return [b for b in ctx.ir.flatten_blocks() if b.role.value in PROSE_ROLES and b.text]


def length_caps(ctx: LintContext) -> list[Violation]:
    """Flag sentences over the word cap, noun clusters >3, and paragraphs >6 sentences."""
    out: list[Violation] = []
    nlp = get_nlp(ctx)
    for b in _prose_blocks(ctx):
        if nlp is not None:
            doc = nlp(b.text)
            sents = list(doc.sents)
            if len(sents) > _PARA_SENTENCES:
                out.append(Violation(b.block_id, f"paragraph has {len(sents)} sentences (>{_PARA_SENTENCES})"))
            for sent in sents:
                content = [t for t in sent if not t.is_punct and not t.is_space]
                wc = len(content)
                proc = _is_imperative_spacy(sent)
                cap = _PROC_CAP if proc else _DESC_CAP
                if wc > cap:
                    kind = "procedural" if proc else "descriptive"
                    out.append(Violation(b.block_id, f"{kind} sentence is {wc} words (>{cap}): {sent.text.strip()[:60]!r}"))
                run = _max_noun_run(sent)
                if run > _NOUN_CLUSTER:
                    out.append(Violation(b.block_id, f"noun cluster of {run} (>{_NOUN_CLUSTER}) in: {sent.text.strip()[:60]!r}"))
        else:
            sents = split_sentences(b.text)
            if len(sents) > _PARA_SENTENCES:
                out.append(Violation(b.block_id, f"paragraph has {len(sents)} sentences (>{_PARA_SENTENCES}) (no-POS heuristic)"))
            for s in sents:
                wc = n_words(s)
                if wc > _DESC_CAP:  # cannot tell procedural from descriptive without POS
                    out.append(Violation(b.block_id, f"sentence is {wc} words (>{_DESC_CAP}) (no-POS heuristic): {s[:60]!r}"))
    return out


def condition_first(ctx: LintContext) -> list[Violation]:
    """Flag imperative sentences whose if/when condition trails the instruction (R-PROSE-04)."""
    out: list[Violation] = []
    nlp = get_nlp(ctx)
    for b in _prose_blocks(ctx):
        if nlp is not None:
            for sent in nlp(b.text).sents:
                if not _is_imperative_spacy(sent):
                    continue
                cond = next((t for t in sent if t.lower_ in ("if", "when")), None)
                if cond is not None and cond.i > sent.root.i:
                    out.append(Violation(b.block_id, f"condition trails instruction (lead with the condition): {sent.text.strip()[:70]!r}"))
        else:
            for s in split_sentences(b.text):
                toks = s.split()
                if toks and toks[0].lower().strip(",.;:") in _IMPERATIVES:
                    m = _COND_RE.search(s)
                    if m and m.start() > 0:
                        out.append(Violation(b.block_id, f"condition trails instruction (no-POS heuristic): {s[:70]!r}"))
    return out


# --- spaCy helpers -----------------------------------------------------------

def _is_imperative_spacy(sent) -> bool:
    root = sent.root
    # only the ROOT's own subject disqualifies an imperative — a subordinate clause may have one
    root_has_subject = any(t.dep_ in ("nsubj", "nsubjpass", "expl") and t.head == root for t in sent)
    first = next((t for t in sent if not t.is_space), None)
    return root.tag_ == "VB" and not root_has_subject and first is not None and first.pos_ in ("VERB", "AUX")


def _max_noun_run(sent) -> int:
    best = run = 0
    for t in sent:
        if t.pos_ in ("NOUN", "PROPN"):
            run += 1
            best = max(best, run)
        elif not (t.is_punct or t.is_space):
            run = 0
    return best
