"""Pluggable entailment backends for the model_verified tier (R-GROUND-02/03, R-PROJ-04).

Classification: model_verified (substrate)

Per CAPABILITIES.md: MiniCheck is not on PyPI; the production options are a local HF NLI/MiniCheck
checkpoint (transformers + torch — GPU-accelerated here) or a scoped Claude call (one premise+
hypothesis at a time, binary supports/not-supports). The OFFLINE/TEST default is a deterministic
lexical-overlap proxy so the pipeline and CI run hermetically — no network, no model weights.

`supports(premise, hypothesis)` answers: does the evidence (a source quote, or a claim's grounding
text) support the hypothesis (the primer statement / rewritten chunk)?
"""
from __future__ import annotations

import re
from typing import Callable, Protocol

_WORD_RE = re.compile(r"\b[\w'-]+\b")
_STOP = {
    "the", "a", "an", "this", "that", "these", "those", "it", "its", "is", "are", "be", "was",
    "were", "and", "or", "but", "to", "of", "in", "on", "for", "with", "as", "by", "at", "from",
    "not", "no", "than", "then", "so", "into", "over", "per", "via", "you", "your", "we", "our",
}


def _content(text: str | None) -> set[str]:
    return {w for w in (t.lower() for t in _WORD_RE.findall(text or "")) if len(w) >= 3 and w not in _STOP}


class Entailment(Protocol):
    name: str

    def supports(self, premise: str, hypothesis: str) -> bool: ...


class LexicalEntailment:
    """Deterministic offline proxy: premise supports hypothesis if it covers >= `threshold` of the
    hypothesis's content tokens. Cheap, network-free, and good enough to distinguish a supporting
    quote from a decorative/irrelevant one in tests."""

    name = "lexical"

    def __init__(self, threshold: float = 0.4) -> None:
        self.threshold = threshold

    def supports(self, premise: str, hypothesis: str) -> bool:
        h = _content(hypothesis)
        if not h:
            return False
        overlap = len(h & _content(premise)) / len(h)
        return overlap >= self.threshold


class NLIEntailment:
    """Local HF NLI / MiniCheck-style backend (transformers + torch). Lazy-loaded; weights download
    on first use, so it is not exercised by the offline test suite. GPU-accelerated when available."""

    name = "nli"

    def __init__(self, model_name: str = "tals/albert-base-vitaminc-mnli", entail_labels=("entailment", "supported", "label_1")) -> None:
        self.model_name = model_name
        self._entail = {lbl.lower() for lbl in entail_labels}
        self._pipe = None

    def _ensure(self):
        if self._pipe is None:
            from transformers import pipeline  # heavy import, deferred
            self._pipe = pipeline("text-classification", model=self.model_name, top_k=None)
        return self._pipe

    def supports(self, premise: str, hypothesis: str) -> bool:
        pipe = self._ensure()
        scores = pipe({"text": premise, "text_pair": hypothesis})
        if isinstance(scores, list) and scores and isinstance(scores[0], list):
            scores = scores[0]
        best = max(scores, key=lambda s: s["score"])
        return best["label"].lower() in self._entail


class CallableEntailment:
    """Wraps an injected judge — the production seam for the scoped Claude call (one pair at a time)."""

    name = "claude"

    def __init__(self, judge_fn: Callable[[str, str], bool]) -> None:
        self._fn = judge_fn

    def supports(self, premise: str, hypothesis: str) -> bool:
        return bool(self._fn(premise, hypothesis))


def resolve_backend(name: str = "auto", judge_fn: Callable[[str, str], bool] | None = None) -> Entailment:
    """Select a backend per CAPABILITIES.md. 'auto' resolves to the offline lexical proxy."""
    if name in ("auto", "lexical"):
        return LexicalEntailment()
    if name == "nli":
        return NLIEntailment()
    if name == "claude":
        if judge_fn is None:
            raise ValueError("the 'claude' backend needs judge_fn (a scoped supports/not-supports call)")
        return CallableEntailment(judge_fn)
    raise ValueError(f"unknown entailment backend: {name!r}")
