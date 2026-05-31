"""Shared contract + helpers for the hard_lint checks. Every check operates on the IR.

Classification: local-deterministic

A check is `def check(ctx: LintContext) -> list[Violation]`. It returns the *violations* it
found; the dispatcher (`scripts/lint.py`) maps those to a report status using the rule's
PRIORITY (MUST -> fail/blocking, SHOULD/MAY -> warn). A check that returns `[]` passed.

A `Violation` may set `force_status` to override the priority mapping — used by the coherence
check when it runs in the degraded (no-spaCy) fallback, so a heuristic guess never hard-blocks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ir.schema import ConceptMap, DocumentIR, SourceLedger


@dataclass
class Violation:
    block_id: str | None
    detail: str
    force_status: str | None = None  # e.g. "warn" to downgrade a degraded MUST check


@dataclass
class LintContext:
    """Everything a check may need. Cross-artifact checks no-op when their artifact is absent."""

    ir: DocumentIR
    concept_map: ConceptMap | None = None
    ledger: SourceLedger | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    # capabilities flags: {"force_no_nlp": bool, "use_coref": bool} — drive native/fallback selection
    capabilities: dict[str, Any] = field(default_factory=dict)
    _nlp: Any = None
    _nlp_tried: bool = False

    def length_budget(self) -> int | None:
        return parse_int(self.parameters.get("length_budget"))


# --- text helpers ------------------------------------------------------------

_WORD_RE = re.compile(r"\b[\w'’-]+\b")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'])")
_INT_RE = re.compile(r"\d[\d,]*")


def words(text: str | None) -> list[str]:
    return _WORD_RE.findall(text or "")


def n_words(text: str | None) -> int:
    return len(words(text))


def split_sentences(text: str | None) -> list[str]:
    """Regex sentence split (fallback / non-spaCy path). Crude but deterministic."""
    if not text:
        return []
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def parse_int(value: Any) -> int | None:
    """Pull a leading integer out of an int or a string like '4000' / '4000 words' / '~3k'."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        m = _INT_RE.search(value)
        if m:
            base = int(m.group(0).replace(",", ""))
            tail = value[m.end():m.end() + 1].lower()
            return base * 1000 if tail == "k" else base
    return None


# --- spaCy detection (per CAPABILITIES.md) -----------------------------------

_SPACY_MODELS = ("en_core_web_trf", "en_core_web_lg", "en_core_web_md", "en_core_web_sm")


def get_nlp(ctx: LintContext):
    """Return a loaded spaCy pipeline, or None if unavailable / disabled.

    Mirrors probe_env's detection: a check that gets None must use its entity-overlap /
    regex fallback (this is exactly the 'degrades per CAPABILITIES.md' contract).
    """
    if ctx.capabilities.get("force_no_nlp"):
        return None
    if not ctx._nlp_tried:
        ctx._nlp_tried = True
        try:
            import importlib.util

            import spacy
            for name in _SPACY_MODELS:
                if importlib.util.find_spec(name) is None:
                    continue
                try:
                    ctx._nlp = spacy.load(name, disable=["ner"])  # keep tagger/parser/lemmatizer
                    break
                except Exception:
                    continue
        except Exception:
            ctx._nlp = None
    return ctx._nlp


def nlp_available(ctx: LintContext) -> bool:
    return get_nlp(ctx) is not None


# --- block iteration helpers -------------------------------------------------

CONTENT_ROLES = {"body", "toulmin", "matrix"}
PROSE_ROLES = {"lede", "card", "summary", "body", "toulmin"}


def section_block_words(blocks, roles: set[str]) -> int:
    return sum(n_words(b.text) for b in blocks if b.role.value in roles)
