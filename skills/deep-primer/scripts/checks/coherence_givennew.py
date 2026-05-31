"""Given→new coherence (entity grid).

Classification: local-deterministic
Implements: R-PROSE-01 (entity_grid)

NATIVE (spaCy present, per CAPABILITIES.md): build a per-paragraph entity grid from
dependency-parsed subjects + noun lemmas; flag a sentence whose subject was not introduced in
the previous two sentences, and flag a paragraph where every sentence introduces a new subject.
Coreference (fastcoref) is used only when capabilities['use_coref'] is set, because its weights
download on first use — off by default keeps the lint offline-safe.

FALLBACK (no spaCy): a coarse content-word-overlap grid. Because the heuristic is noisy, its
findings are emitted as `force_status="warn"` so a degraded MUST check never hard-blocks delivery
on a guess — this is the 'degrade per CAPABILITIES.md' contract.
"""
from __future__ import annotations

from checks._base import PROSE_ROLES, LintContext, Violation, get_nlp, split_sentences

_WINDOW = 2  # a subject must have appeared within the previous N sentences

_STOP = {
    "the", "a", "an", "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "and", "or", "but", "if", "when", "to", "of", "in", "on", "for", "with", "as", "is", "are",
    "be", "by", "at", "from", "you", "your", "we", "our", "not", "no", "than", "then", "so",
}


def _prose_blocks(ctx: LintContext):
    return [b for b in ctx.ir.flatten_blocks() if b.role.value in PROSE_ROLES and b.text]


def entity_grid(ctx: LintContext) -> list[Violation]:
    nlp = get_nlp(ctx)
    if nlp is not None:
        return _native(ctx, nlp)
    return _fallback(ctx)


# --- native (spaCy) ----------------------------------------------------------

def _native(ctx: LintContext, nlp) -> list[Violation]:
    out: list[Violation] = []
    use_coref = bool(ctx.capabilities.get("use_coref"))
    for b in _prose_blocks(ctx):
        doc = nlp(b.text)
        sents = list(doc.sents)
        if len(sents) < 2:
            continue
        subjects: list[str | None] = []
        entsets: list[set[str]] = []
        for sent in sents:
            subj = _subject_lemma(sent)
            ents = {t.lemma_.lower() for t in sent if t.pos_ in ("NOUN", "PROPN") and t.lemma_}
            subjects.append(subj)
            entsets.append(ents)
        if use_coref:
            _apply_coref(b.text, subjects, entsets)

        new_subject_count = 0
        for i in range(1, len(sents)):
            prior = set().union(*entsets[max(0, i - _WINDOW):i]) if i else set()
            subj = subjects[i]
            if subj and subj not in prior:
                new_subject_count += 1
                out.append(Violation(
                    b.block_id,
                    f"given→new break: subject {subj!r} not introduced in prior {_WINDOW} sentences "
                    f"(sentence {i + 1})",
                ))
        # whole-paragraph choppiness: every sentence after the first introduces a new subject
        if len(sents) >= 3 and new_subject_count == len(sents) - 1:
            out.append(Violation(b.block_id, "choppy paragraph: every sentence introduces a new subject entity"))
    return out


def _subject_lemma(sent) -> str | None:
    for t in sent:
        if t.dep_ in ("nsubj", "nsubjpass"):
            return (t.lemma_ or t.text).lower()
    root = sent.root
    return (root.lemma_ or root.text).lower() if root is not None else None


def _apply_coref(text: str, subjects, entsets) -> None:
    """Best-effort coref enrichment; silently no-ops if weights/model unavailable (offline)."""
    try:
        from fastcoref import FCoref
        model = FCoref()
        pred = model.predict(texts=[text])[0]
        for cluster in pred.get_clusters():
            head = cluster[0].lower()
            for mention in cluster:
                m = mention.lower()
                for s in entsets:
                    if m in s:
                        s.add(head)
    except Exception:
        return


# --- fallback (no spaCy) -----------------------------------------------------

def _content_tokens(sentence: str) -> set[str]:
    return {w for w in (t.strip(".,;:()\"'").lower() for t in sentence.split()) if len(w) >= 4 and w not in _STOP}


def _fallback(ctx: LintContext) -> list[Violation]:
    out: list[Violation] = []
    for b in _prose_blocks(ctx):
        sents = split_sentences(b.text)
        if len(sents) < 2:
            continue
        toks = [_content_tokens(s) for s in sents]
        no_overlap = 0
        for i in range(1, len(sents)):
            prior = set().union(*toks[max(0, i - _WINDOW):i])
            if toks[i] and not (toks[i] & prior):
                no_overlap += 1
                out.append(Violation(
                    b.block_id,
                    f"given→new break (degraded/no-spaCy): sentence {i + 1} shares no content word with prior {_WINDOW}",
                    force_status="warn",
                ))
        if len(sents) >= 3 and no_overlap == len(sents) - 1:
            out.append(Violation(
                b.block_id,
                "choppy paragraph (degraded/no-spaCy): no content-word chaining between sentences",
                force_status="warn",
            ))
    return out
