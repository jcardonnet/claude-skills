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

import re

from checks._base import PROSE_ROLES, LintContext, Violation, get_nlp, split_sentences

_WINDOW = 2  # a subject must have appeared within the previous N sentences

# Subjects that are ANAPHORIC by nature: they point back, so they are the 'given' half of given→new
# and can never be an unintroduced entity. Kept alongside the POS check because the parser tags
# relative 'which'/'that' inconsistently depending on clause structure.
_ANAPHORIC = {
    "it", "its", "this", "that", "these", "those", "they", "them", "their", "which", "who",
    "whom", "whose", "he", "she", "we", "you", "i", "one", "both", "either", "neither",
}

_STOP = {
    "the", "a", "an", "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "and", "or", "but", "if", "when", "to", "of", "in", "on", "for", "with", "as", "is", "are",
    "be", "by", "at", "from", "you", "your", "we", "our", "not", "no", "than", "then", "so",
}


def _prose_blocks(ctx: LintContext):
    return [b for b in ctx.ir.flatten_blocks() if b.role.value in PROSE_ROLES and b.text]


# A leading structural label on a sentence — "Qualifier:", "Rebuttal:", "Warrant:". Toulmin blocks
# are REQUIRED to carry these, and they wreck the dependency parse: in "Qualifier: the gain shrinks
# as retrieval precision rises" spaCy tags `shrinks` as a NOUN subject, and in "Rebuttal: on
# high-QPS paths ..." the label itself becomes the subject. Both then read as unintroduced entities,
# so R-PROSE-01 failed a correctly-shaped Toulmin block for having the shape the schema mandates.
_LABEL_RE = re.compile(r"(?:(?<=^)|(?<=[.!?]\s))([A-Z][A-Za-z-]{2,14}):\s+")


def _strip_labels(text: str) -> str:
    """Drop structural sentence labels before parsing, RE-CAPITALISING what follows.

    The capitalisation is not cosmetic. Removing "Qualifier: " leaves "the gain shrinks as
    retrieval precision rises", and spaCy then tags `shrinks` as a NOUN subject purely because the
    sentence opens lowercase — swapping one parse artifact for another. Restoring the capital
    yields the real subject, `gain`.

    Offsets are not reused downstream — only lemma sets and subjects are — so rewriting is safe.
    """
    pieces: list[str] = []
    last = 0
    for m in _LABEL_RE.finditer(text):
        pieces.append(text[last:m.start()])
        following = text[m.end():m.end() + 1]
        pieces.append(following.upper())
        last = m.end() + len(following)
    pieces.append(text[last:])
    return "".join(pieces)


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
        doc = nlp(_strip_labels(b.text))
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
    """The subject ENTITY this sentence is about, or None when there is nothing to check.

    Two cases deliberately return None. Both produced false given→new breaks on well-formed prose
    the moment spaCy was actually installed — this check had never run its native path anywhere,
    CI included, so the errors were invisible:

      - A PRONOMINAL subject ('which', 'it', 'they'). An anaphor is *given* by construction: it can
        only mean anything if its referent already appeared. Flagging one as "not introduced in the
        prior 2 sentences" inverts the rule — the sentence is doing exactly what R-PROSE-01 asks.
      - A sentence with no nominal subject. The old fallback returned `sent.root`, which for an
        imperative or fragment is a VERB ('shrink'), then compared it against a set of noun lemmas
        it could never appear in. That break was guaranteed regardless of the prose.
    """
    for t in sent:
        if t.dep_ in ("nsubj", "nsubjpass"):
            if t.pos_ == "PRON" or (t.lemma_ or t.text).lower() in _ANAPHORIC:
                return None
            return (t.lemma_ or t.text).lower()
    return None


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
