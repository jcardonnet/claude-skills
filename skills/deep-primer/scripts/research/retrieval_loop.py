"""Bounded retrieval: accepted leads -> fetched documents.

Classification: agent-orchestrated (web tools + model), NOT a hermetic function.
Implements: the fetch half of R-GROUND-01..04; the R-DISC-01 firewall's enforcement point.

Per question x perspective: search -> fetch full pages (not snippets) -> extract -> identify gaps
-> re-query, bounded by `max_retrieval_iterations`. Search and fetch sit behind protocols so the
loop's CONTROL FLOW is testable offline while the I/O stays pluggable.

The firewall (R-DISC-01) is enforced here by construction: discovery hands over URLs, and nothing
downstream can mint a claim without a `Document` produced by this module — a fetched body with a
content hash. A lead is a pointer, never provenance.
"""
from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import DiscoveryLeads, ResearchPlan  # noqa: E402

MAX_RETRIEVAL_ITERATIONS = 6      # registry budget
MIN_SOURCES_PER_QUESTION = 2      # registry budget

_WS_RE = re.compile(r"\s+")


def canonical_url(url: str) -> str:
    u = (url or "").strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    return u.removeprefix("www.").rstrip("/")


def source_id_for(url: str) -> str:
    """sha1 of the canonical url — the ledger's source_id (artifact-schemas.md).

    `usedforsecurity=False` states the obvious for scanners (Sonar S4790 / bandit B324): this is
    content addressing, not a security primitive. It does NOT change the digest, so every
    source_id already written into a frozen fixture or discovery snapshot stays byte-identical.
    """
    return hashlib.sha1(canonical_url(url).encode(), usedforsecurity=False).hexdigest()


def normalize(text: str | None) -> str:
    """Whitespace-collapsed lowercase, for substring checks against a fetched body."""
    return _WS_RE.sub(" ", (text or "")).strip().lower()


@dataclass
class Document:
    """A page actually fetched. The only thing a ledger claim may be anchored to."""

    url: str
    text: str
    title: str | None = None
    source_type: str | None = None        # primary_paper | docs | blog | vendor | standard
    retrieved_at: str | None = None
    provenance_origin: str = "discovered"  # 'user' when it came from a seed_source (R-DISC-06)
    served_questions: list[str] = field(default_factory=list)

    @property
    def source_id(self) -> str:
        return source_id_for(self.url)

    @property
    def content_hash(self) -> str:
        return hashlib.sha1(self.text.encode(), usedforsecurity=False).hexdigest()

    def contains(self, quote: str) -> bool:
        """Whether `quote` appears verbatim in the fetched body (whitespace-insensitive)."""
        return bool(quote) and normalize(quote) in normalize(self.text)


class Fetcher(Protocol):
    name: str

    def __call__(self, url: str) -> Document | None: ...


class Searcher(Protocol):
    def __call__(self, query: str) -> list[str]: ...


class ReplayFetcher:
    """Offline default: serves documents from a frozen corpus keyed by canonical URL.

    Same role as the discovery snapshot — it makes a grounding run replayable, so eval scores the
    same ledger every time instead of whatever the live web returned that day.
    """

    name = "replay"

    def __init__(self, corpus: dict[str, Document] | None = None, corpus_dir: str | Path | None = None) -> None:
        self.corpus: dict[str, Document] = {}
        for url, doc in (corpus or {}).items():
            self.corpus[canonical_url(url)] = doc
        if corpus_dir:
            self._load_dir(Path(corpus_dir))

    def _load_dir(self, root: Path) -> None:
        import json
        for meta_path in sorted(root.glob("*.json")):
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            body = (root / f"{meta_path.stem}.txt")
            doc = Document(
                url=meta["url"], text=body.read_text(encoding="utf-8") if body.is_file() else "",
                title=meta.get("title"), source_type=meta.get("source_type"),
                retrieved_at=meta.get("retrieved_at"),
                provenance_origin=meta.get("provenance_origin", "discovered"),
            )
            self.corpus[canonical_url(doc.url)] = doc

    def __call__(self, url: str) -> Document | None:
        return self.corpus.get(canonical_url(url))


@dataclass
class RetrievalResult:
    documents: list[Document] = field(default_factory=list)
    iterations: dict[str, int] = field(default_factory=dict)     # question_id -> loops spent
    unresolved: list[str] = field(default_factory=list)          # urls that would not fetch

    def by_source_id(self) -> dict[str, Document]:
        return {d.source_id: d for d in self.documents}


def fetch_source_leads(leads: DiscoveryLeads, fetcher: Fetcher) -> RetrievalResult:
    """Fetch every ACCEPTED source-lead. A dropped lead is not fetched; a flagged one is.

    Seed-derived leads carry provenance_origin=user through to the document, so the ledger can
    record where a claim came from without treating the seed as pre-trusted (R-DISC-06).

    A lead's `type` is carried across too, and the fetcher wins when it managed to derive one.
    Discovery classifies a source (docs / standard / vendor / blog / primary_paper) from context the
    fetched body no longer has, and two consumers need that classification: `claim_extractor` writes
    it to `Source.type` for the source-quality critics, and `coverage.vendor_independence` counts
    non-vendor sources per question. Losing it here silently reported every source as untyped, which
    made that coverage check pass for the wrong reason.
    """
    result = RetrievalResult()
    for lead in leads.source_leads:
        if lead.status == "dropped":
            continue
        doc = fetcher(lead.url)
        if doc is None:
            result.unresolved.append(lead.url)
            continue
        doc.provenance_origin = lead.provenance_origin
        doc.source_type = doc.source_type or lead.type
        doc.served_questions = list(lead.supports)
        result.documents.append(doc)
    return result


def retrieve_for_questions(plan: ResearchPlan, fetcher: Fetcher, searcher: Searcher,
                           max_iterations: int = MAX_RETRIEVAL_ITERATIONS,
                           min_sources: int = MIN_SOURCES_PER_QUESTION,
                           seen: Iterable[str] = ()) -> RetrievalResult:
    """Bounded search -> fetch -> gap -> re-query per open question.

    The bound is the point: a question that will not reach `min_sources` in `max_iterations` is
    left short and marked thin by coverage.py, rather than looping until something is found. An
    under-supported area the primer can flag beats one it fabricates into.
    """
    result = RetrievalResult()
    already = {canonical_url(u) for u in seen}

    for q in plan.questions:
        if q.coverage.status == "covered":
            continue
        found: list[Document] = []
        iterations = 0
        while len(found) < min_sources and iterations < max_iterations:
            iterations += 1
            # the follow-up: later loops re-query with the sub-questions, STORM-style
            extra = q.sub_questions[iterations - 2] if 1 < iterations <= len(q.sub_questions) + 1 else ""
            for url in searcher(f"{q.text} {extra}".strip()):
                if canonical_url(url) in already:
                    continue
                doc = fetcher(url)
                already.add(canonical_url(url))
                if doc is None:
                    result.unresolved.append(url)
                    continue
                doc.served_questions.append(q.id)
                found.append(doc)
                if len(found) >= min_sources:
                    break
        result.iterations[q.id] = iterations
        result.documents.extend(found)
    return result
