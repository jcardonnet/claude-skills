"""Claim grouping: "which of these claims say the same thing?" — proposed, then gated.

Classification: local-deterministic (hermetic; the model half lives in `claude_curator.py`)
Implements: the deciding half of the curate step and of R-GROUND-05 corroboration;
            the mechanical half of R-XREF-04 (an anchor may not restate its own term)

Why one module for two jobs
---------------------------
Concept grouping and corroboration are the SAME question asked at two strictnesses. "Do these
claims belong to one concept?" is topic-level; "do these claims assert one fact?" is
assertion-level. Both were answered by Jaccard overlap on bag-of-words, and both failed in the
first real campaign for the same reason: two sources describing one idea rarely reuse each other's
vocabulary. Spec-03 ground 271 claims and got 249 single-claim "concepts" and ZERO corroborated
claims out of it.

The fix is not a better string metric. It is the pattern `anchor_claims` already establishes: the
MODEL PROPOSES, DETERMINISTIC CODE DECIDES. `resolve_groups` is that gate — pure, testable, and
unable to be talked out of its invariants:

  - a proposed claim_id that is not in the ledger is dropped (the model cannot invent members);
  - a claim lands in AT MOST ONE group, first proposal wins over a fixed order;
  - a claim the model never mentioned becomes its own singleton rather than vanishing;
  - two groups the model gives the same canonical term ARE one group, so R-VOCAB-01's
    uniqueness holds by construction rather than by hoping;
  - a `home_anchor` that restates its own concept is stripped, because a fabricated anchor is
    exactly the "X is like X" failure R-XREF-04 exists to catch.

Every rejection is returned, never swallowed: what the gate threw away is a fact about the run.

R-DISC-04 / R-CONV-02 are unaffected. Both pin `research/discovery.py` and `research/convergence.py`
respectively — clustering *leads*, saturation, and struct_distance stay pure arithmetic. Grouping
grounded CLAIMS is a different operation on a different artifact, and its decisions are still made
here, in code.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.discovery import LexicalSimilarity, Similarity  # noqa: E402

#: Bag-of-words overlap above which two claims are treated as one group by the offline path.
LEXICAL_GROUP_THRESHOLD = 0.5

#: Deliberately permissive, and used only for BLOCKING — narrowing which claim pairs are worth a
#: model's attention before it judges them. Recall matters more than precision at this step: a pair
#: the block never puts together can never be corroborated, while a bad pair inside a block is
#: simply rejected by the model that reads it.
LEXICAL_BLOCK_THRESHOLD = 0.15


@dataclass
class Group:
    """A set of claim_ids the grouper says belong together, plus whatever it could name.

    The naming fields are empty for corroboration (grouping identical assertions needs no label)
    and populated for concept grouping. `curate` treats an empty field as "no answer" and falls
    back to its `Curator` seam rather than inventing one here.
    """

    claim_ids: list[str]
    canonical_term: str = ""
    aliases: list[str] = field(default_factory=list)
    home_anchor: str = ""
    fidelity_boundary: str = ""


class ClaimGrouper(Protocol):
    """The model's contribution: (claim_id, text) pairs in, proposed groups out.

    Each proposal is a dict with at least `claim_ids`; concept groupers add `canonical_term`,
    `aliases`, `home_anchor`, `fidelity_boundary`. Proposals are untrusted — `resolve_groups`
    decides what survives.
    """

    def __call__(self, claims: list[tuple[str, str]], params: dict) -> list[dict]: ...


def anchor_restates_term(anchor: str, terms) -> bool:
    """True when `anchor` is one of `terms`, or contains one, or is contained by one.

    Shared verbatim with `checks/univocity_terms.py::home_anchor_distinct` so the gate that admits
    an anchor and the lint that rejects one cannot drift into disagreeing. Substring either way, not
    equality: "reranking" anchoring "cross-encoder reranking" is the same tautology with more words.
    """
    anchor = (anchor or "").strip().lower()
    if not anchor:
        return False
    for term in terms:
        term = (term or "").strip().lower()
        if term and (anchor == term or anchor in term or term in anchor):
            return True
    return False


def lexical_groups(claims: list[tuple[str, str]], backend: Similarity | None = None,
                   threshold: float = LEXICAL_GROUP_THRESHOLD) -> list[list[str]]:
    """Greedy single-link clustering by lexical overlap. Deterministic over the input order.

    This is the offline path and the blocking primitive, not the production answer: it under-merges
    badly on real prose (see the module docstring). `claims` must already be in a stable order —
    callers sort by claim_id — because single-link greedy clustering is order-dependent.
    """
    backend = backend or LexicalSimilarity()
    clusters: list[list[tuple[str, str]]] = []
    for cid, text in claims:
        for cluster in clusters:
            if any(backend.score(text, other) >= threshold for _, other in cluster):
                cluster.append((cid, text))
                break
        else:
            clusters.append([(cid, text)])
    return [[cid for cid, _ in cluster] for cluster in clusters]


def _admit_members(raw_ids, n: int, known: set[str], assigned: set[str],
                   rejected: list[str]) -> list[str]:
    """The membership half of the gate: a claim must exist, and may join at most one group.

    First proposal wins a contested claim. That is arbitrary but it has to be *something*, and
    "first" is the only tiebreak that stays stable when the model reorders its answer.
    """
    members: list[str] = []
    for cid in raw_ids or []:
        cid = str(cid).strip()
        if cid not in known:
            rejected.append(f"group {n}: claim_id {cid!r} is not in the ledger")
        elif cid in assigned:
            rejected.append(f"group {n}: claim_id {cid!r} was already grouped; a claim "
                            f"belongs to at most one group")
        else:
            members.append(cid)
            assigned.add(cid)
    return members


def resolve_groups(proposals, claims: list[tuple[str, str]]) -> tuple[list[Group], list[str]]:
    """The deterministic gate. Returns (groups, rejection reasons).

    Order is a fact about the input, not about the model's mood: surviving groups keep proposal
    order, and claims nobody claimed are appended as singletons in the order `claims` arrived.
    """
    known = {cid for cid, _ in claims}
    assigned: set[str] = set()
    rejected: list[str] = []
    groups: list[Group] = []
    by_term: dict[str, Group] = {}

    for n, raw in enumerate(proposals, start=1):
        if not isinstance(raw, dict):
            rejected.append(f"group {n}: not an object")
            continue
        members = _admit_members(raw.get("claim_ids"), n, known, assigned, rejected)
        if not members:
            rejected.append(f"group {n}: no usable members")
            continue

        term = str(raw.get("canonical_term") or "").strip()
        aliases = [str(a).strip() for a in (raw.get("aliases") or []) if str(a).strip()]
        anchor = str(raw.get("home_anchor") or "").strip()
        boundary = str(raw.get("fidelity_boundary") or "").strip()
        if anchor and anchor_restates_term(anchor, [term, *aliases]):
            rejected.append(f"group {n}: home_anchor {anchor!r} restates its own term {term!r} "
                            f"(R-XREF-04); dropped rather than shipped as a bridge")
            anchor, boundary = "", ""

        # Same name = same concept. The model naming two groups identically IS the model saying
        # they are one, and merging is what keeps R-VOCAB-01 (A) true by construction.
        prior = by_term.get(term.lower()) if term else None
        if prior is not None:
            rejected.append(f"group {n}: canonical term {term!r} repeats an earlier group; merged")
            prior.claim_ids.extend(members)
            prior.aliases.extend(a for a in aliases if a not in prior.aliases)
            continue

        group = Group(claim_ids=members, canonical_term=term, aliases=aliases,
                      home_anchor=anchor, fidelity_boundary=boundary)
        groups.append(group)
        if term:
            by_term[term.lower()] = group

    # A claim the grouper never mentioned is a claim we still ground. Dropping it would silently
    # shrink the evidence base; making it a singleton says "unmerged", which is the truth.
    orphans = [cid for cid, _ in claims if cid not in assigned]
    if orphans:
        rejected.append(f"{len(orphans)} claim(s) were in no proposed group and became singletons")
    groups.extend(Group(claim_ids=[cid]) for cid in orphans)
    return groups, rejected
