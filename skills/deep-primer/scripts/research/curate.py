"""Ledger -> concept-map + outline seed (Phase 1, step 7).

Classification: local-deterministic core with a model-judged naming/anchoring seam.
Implements: the curate step; R-XREF-04 (adjacent anchor when home ~= target),
            R-ARCH-07 (a user structure governs the outline)

The concept-map is derived FROM THE LEDGER — from claims we actually grounded — never copied from
a deep-research report's structure. That is the R-DISC-01 firewall applied to shape as well as to
evidence: a discovery report's own taxonomy is a lead about how the field is organized, not a
finding about it.

Deterministic here: salience (claim-frequency centrality), epistemic status from the contested
flags, the outline's order/mapping — and the GATE on grouping. Model-judged behind two seams: which
claims belong together (`ClaimGrouper`, see `research/grouping.py`), and what to CALL the result
(`Curator`).

Grouping moved behind a seam because the offline lexical path could not do the job. On spec-03's
real ledger it turned 271 grounded claims into 249 single-claim "concepts": two sources describing
one idea seldom reuse each other's words, so bag-of-words overlap under-merges by construction, and
a concept-map of singletons makes salience meaningless and depth allocation (R-ARCH-06) arbitrary.
What stayed deterministic is every DECISION — `resolve_groups` admits a grouping, `curate` derives
salience, status, and source_ids from the ledger. `LexicalGrouper` remains the default so an
offline run still produces a concept-map without a model.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Concept, ConceptMap, EpistemicStatus, SourceLedger  # noqa: E402
from research.discovery import LexicalSimilarity, Similarity  # noqa: E402
from research.grouping import ClaimGrouper, Group, lexical_groups, resolve_groups  # noqa: E402

CONCEPT_MATCH_THRESHOLD = 0.5     # claims this similar cluster into one concept


class Curator(Protocol):
    """The model's contribution to curation: naming and anchoring."""

    def name_concept(self, claim_texts: list[str]) -> tuple[str, list[str]]: ...
    def home_anchor(self, canonical_term: str, claim_texts: list[str], params: dict) -> tuple[str, str]: ...
    def assign_section(self, canonical_term: str, user_structure: list[str]) -> str: ...


class StubCurator:
    """Deterministic offline curator.

    Names a concept from the most frequent content words of its claims, and picks a section by
    lexical similarity to the user's entry. It deliberately returns an EMPTY home_anchor rather
    than inventing one: a fabricated anchor would pass R-XREF-04's tautology lint while being
    exactly the "X is like X" failure that rule exists to catch, and an absent anchor is honest.
    """

    def __init__(self, backend: Similarity | None = None) -> None:
        self.backend = backend or LexicalSimilarity()

    def name_concept(self, claim_texts: list[str]) -> tuple[str, list[str]]:
        from collections import Counter
        from research.discovery import _tokens
        counts: Counter = Counter()
        for t in claim_texts:
            # A bare number is never a concept name. `_WORD_RE` splits "10,000" into "10" and "000";
            # "10" dies on the length filter but "000" survives, and being all-digits it sorts ahead
            # of every word. A one-claim group has no frequency signal to outvote it, which is how a
            # real run produced the concepts "000 application" and "600 built-in".
            counts.update(w for w in _tokens(t) if not w.isdigit())
        # Explicit deterministic tiebreak, NOT Counter.most_common. `_tokens` returns a frozenset, so
        # keys land in the Counter in hash order; short claims make nearly every count a tie, and
        # most_common resolves ties by insertion order — which varies with PYTHONHASHSEED. That
        # leaked into canonical_term and therefore concept_id, so one ledger produced different
        # concept-maps in different processes, breaking the reproducibility R-DISC-04 / R-CONV-02
        # rest on. Length precedes the alphabetical key because among equally-frequent words the
        # longer one carries more meaning ("microservices" over "and"-adjacent filler); `w` last
        # keeps the order total, which is the property the reproducibility rules actually need.
        top = [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[:2]]
        return (" ".join(top) or "concept"), []

    def home_anchor(self, canonical_term: str, claim_texts: list[str], params: dict) -> tuple[str, str]:
        return "", ""

    def assign_section(self, canonical_term: str, user_structure: list[str]) -> str:
        scored = [(self.backend.score(canonical_term, entry), i, entry)
                  for i, entry in enumerate(user_structure)]
        # ties resolve to the earliest entry, so the assignment is order-stable
        return max(scored, key=lambda s: (s[0], -s[1]))[2]


def ledger_claims(ledger: SourceLedger) -> list[tuple[str, str]]:
    """Every grounded claim as (claim_id, text), sorted by id — the stable order groupers need."""
    return sorted(((c.claim_id, c.text) for s in ledger.sources for c in s.claims),
                  key=lambda x: x[0])


def cluster_claims(ledger: SourceLedger, backend: Similarity | None = None,
                   threshold: float = CONCEPT_MATCH_THRESHOLD) -> list[list[tuple[str, str]]]:
    """Group ledger claims into concept clusters by lexical overlap, as (claim_id, text) pairs.

    Kept as the offline path; the clustering itself now lives in `grouping.lexical_groups` so the
    same primitive can also block candidate pairs for corroboration.
    """
    claims = ledger_claims(ledger)
    text_of = dict(claims)
    return [[(cid, text_of[cid]) for cid in ids]
            for ids in lexical_groups(claims, backend, threshold)]


class LexicalGrouper:
    """The offline `ClaimGrouper`: lexical overlap, no naming. Under-merges — see the module docstring."""

    def __init__(self, backend: Similarity | None = None,
                 threshold: float = CONCEPT_MATCH_THRESHOLD) -> None:
        self.backend = backend or LexicalSimilarity()
        self.threshold = threshold

    def __call__(self, claims: list[tuple[str, str]], params: dict) -> list[dict]:
        return [{"claim_ids": ids}
                for ids in lexical_groups(claims, self.backend, self.threshold)]


def curate_concept_map(ledger: SourceLedger, params: dict | None = None,
                       curator: Curator | None = None,
                       backend: Similarity | None = None,
                       grouper: ClaimGrouper | None = None,
                       notes: list[str] | None = None) -> ConceptMap:
    """Build the concept-map from grounded claims.

    `grouper` proposes which claims belong together; `resolve_groups` decides. A grouper that also
    names its groups (the model path) supplies canonical_term / aliases / home_anchor directly; the
    `Curator` seam fills in only what the grouper left blank, so the offline path is unchanged.

    `salience` is the claim-frequency centrality proxy the depth allocator uses (R-ARCH-06): a
    concept's share of claims relative to the largest cluster. V1 has no concept graph, so
    frequency stands in for centrality.

    `notes` collects what the gate rejected. It is a sink rather than a second return value because
    every existing caller wants the concept-map; a run that cares what was thrown away passes a list.
    """
    params = params or {}
    curator = curator or StubCurator(backend)
    claims = ledger_claims(ledger)
    if not claims:
        return ConceptMap()

    grouper = grouper or LexicalGrouper(backend)
    groups, rejected = resolve_groups(grouper(claims, params), claims)
    if notes is not None:
        notes.extend(rejected)
    if not groups:
        return ConceptMap()

    text_of = dict(claims)
    claim_source = {c.claim_id: s.source_id for s in ledger.sources for c in s.claims}
    contested_ids = {c.claim_id for s in ledger.sources for c in s.claims if c.contested}
    biggest = max(len(g.claim_ids) for g in groups)

    concepts: list[Concept] = []
    for n, group in enumerate(groups, start=1):
        claim_ids = group.claim_ids
        texts = [text_of[cid] for cid in claim_ids]
        term, aliases = _name(group, texts, curator)
        anchor, boundary = _anchor(group, term, texts, params, curator)
        concepts.append(Concept(
            concept_id=f"c{n}-{term.replace(' ', '-')[:40]}",
            canonical_term=term,
            aliases=aliases,
            home_anchor=anchor or None,
            fidelity_boundary=boundary or None,
            epistemic_status=(EpistemicStatus.contested
                              if any(cid in contested_ids for cid in claim_ids)
                              else EpistemicStatus.settled),
            salience=round(len(claim_ids) / biggest, 4),
            source_ids=sorted({claim_source[cid] for cid in claim_ids if cid in claim_source}),
            claim_ids=claim_ids,
        ))
    return ConceptMap(concepts=concepts)


def _name(group: Group, texts: list[str], curator: Curator) -> tuple[str, list[str]]:
    """The grouper's own name if it gave one, else the curator's. Never both."""
    if group.canonical_term:
        return group.canonical_term, list(group.aliases)
    return curator.name_concept(texts)


def _anchor(group: Group, term: str, texts: list[str], params: dict,
            curator: Curator) -> tuple[str, str]:
    """Ditto for the R-XREF-04 bridge. `resolve_groups` has already stripped a tautological one,
    so an empty `home_anchor` here means "the grouper had no answer", not "the answer was bad"."""
    if group.home_anchor:
        return group.home_anchor, group.fidelity_boundary
    return curator.home_anchor(term, texts, params)


def outline_seed(concept_map: ConceptMap, params: dict | None = None,
                 curator: Curator | None = None) -> list[dict]:
    """The outline seed: ordered sections, each carrying the concepts it must cover.

    With `user_structure` set (R-ARCH-07) the user's entries ARE the sections, in their order, each
    emitted with `maps_to` so the drafted heading can still be a predictive claim (R-SCENT-01)
    while the structure stays provably honored. Without one, sections follow salience descending,
    which is what makes depth track the budget rather than uniform padding (R-ARCH-06).
    """
    params = params or {}
    curator = curator or StubCurator()
    user_structure = params.get("user_structure")

    if user_structure:
        buckets: dict[str, list[Concept]] = {entry: [] for entry in user_structure}
        for concept in concept_map.concepts:
            buckets[curator.assign_section(concept.canonical_term, user_structure)].append(concept)
        return [
            {
                "maps_to": entry,
                "concepts": [c.concept_id for c in sorted(buckets[entry],
                                                          key=lambda c: (-(c.salience or 0), c.concept_id))],
                "salience": round(max((c.salience or 0) for c in buckets[entry]), 4) if buckets[entry] else 0.0,
            }
            for entry in user_structure
        ]

    return [
        {"maps_to": None, "concepts": [c.concept_id], "salience": c.salience or 0.0}
        for c in sorted(concept_map.concepts, key=lambda c: (-(c.salience or 0), c.concept_id))
    ]
