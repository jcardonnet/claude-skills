"""Ledger -> concept-map + outline seed (Phase 1, step 7).

Classification: local-deterministic core with a model-judged naming/anchoring seam.
Implements: the curate step; R-XREF-04 (adjacent anchor when home ~= target),
            R-ARCH-07 (a user structure governs the outline)

The concept-map is derived FROM THE LEDGER — from claims we actually grounded — never copied from
a deep-research report's structure. That is the R-DISC-01 firewall applied to shape as well as to
evidence: a discovery report's own taxonomy is a lead about how the field is organized, not a
finding about it.

Deterministic here: clustering claims into concepts, salience (claim-frequency centrality),
epistemic status from the contested flags, and the outline's order/mapping. Model-judged behind
the `Curator` seam: what to CALL a concept, and which adjacent technique anchors it.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Concept, ConceptMap, EpistemicStatus, SourceLedger  # noqa: E402
from research.discovery import LexicalSimilarity, Similarity  # noqa: E402

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
            counts.update(_tokens(t))
        # Explicit alphabetical tiebreak, NOT Counter.most_common. `_tokens` returns a frozenset, so
        # keys land in the Counter in hash order; short claims make nearly every count a tie, and
        # most_common resolves ties by insertion order — which varies with PYTHONHASHSEED. That
        # leaked into canonical_term and therefore concept_id, so one ledger produced different
        # concept-maps in different processes, breaking the reproducibility R-DISC-04 / R-CONV-02
        # rest on. Same (-count, key) idiom as assign_section below and outline_seed.
        top = [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:2]]
        return (" ".join(top) or "concept"), []

    def home_anchor(self, canonical_term: str, claim_texts: list[str], params: dict) -> tuple[str, str]:
        return "", ""

    def assign_section(self, canonical_term: str, user_structure: list[str]) -> str:
        scored = [(self.backend.score(canonical_term, entry), i, entry)
                  for i, entry in enumerate(user_structure)]
        # ties resolve to the earliest entry, so the assignment is order-stable
        return max(scored, key=lambda s: (s[0], -s[1]))[2]


def cluster_claims(ledger: SourceLedger, backend: Similarity | None = None,
                   threshold: float = CONCEPT_MATCH_THRESHOLD) -> list[list[tuple[str, str]]]:
    """Group ledger claims into concept clusters. Deterministic (claims sorted by id first).

    Returns clusters of (claim_id, claim_text).
    """
    backend = backend or LexicalSimilarity()
    claims = sorted(((c.claim_id, c.text) for s in ledger.sources for c in s.claims),
                    key=lambda x: x[0])
    clusters: list[list[tuple[str, str]]] = []
    for cid, text in claims:
        for cluster in clusters:
            if any(backend.score(text, other) >= threshold for _, other in cluster):
                cluster.append((cid, text))
                break
        else:
            clusters.append([(cid, text)])
    return clusters


def curate_concept_map(ledger: SourceLedger, params: dict | None = None,
                       curator: Curator | None = None,
                       backend: Similarity | None = None) -> ConceptMap:
    """Build the concept-map from grounded claims.

    `salience` is the claim-frequency centrality proxy the depth allocator uses (R-ARCH-06): a
    concept's share of claims relative to the largest cluster. V1 has no concept graph, so
    frequency stands in for centrality.
    """
    params = params or {}
    curator = curator or StubCurator(backend)
    clusters = cluster_claims(ledger, backend)
    if not clusters:
        return ConceptMap()

    claim_source = {c.claim_id: s.source_id for s in ledger.sources for c in s.claims}
    contested_ids = {c.claim_id for s in ledger.sources for c in s.claims if c.contested}
    biggest = max(len(c) for c in clusters)

    concepts: list[Concept] = []
    for n, cluster in enumerate(clusters, start=1):
        claim_ids = [cid for cid, _ in cluster]
        texts = [t for _, t in cluster]
        term, aliases = curator.name_concept(texts)
        anchor, boundary = curator.home_anchor(term, texts, params)
        concepts.append(Concept(
            concept_id=f"c{n}-{term.replace(' ', '-')[:40]}",
            canonical_term=term,
            aliases=aliases,
            home_anchor=anchor or None,
            fidelity_boundary=boundary or None,
            epistemic_status=(EpistemicStatus.contested
                              if any(cid in contested_ids for cid in claim_ids)
                              else EpistemicStatus.settled),
            salience=round(len(cluster) / biggest, 4),
            source_ids=sorted({claim_source[cid] for cid in claim_ids if cid in claim_source}),
            claim_ids=claim_ids,
        ))
    return ConceptMap(concepts=concepts)


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
