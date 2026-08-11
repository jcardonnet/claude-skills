"""Convergence guard for the escalate (re-front-load) loop.

Classification: local-deterministic (R-CONV-02). The MODEL parts — scan_for_structural,
implied_edits — live in the orchestrator/judge (planner.py), NOT here. This module is pure:
structural distance, the tau schedule, convergence ratios, and trajectory clustering only.

Why the split is absolute: the loop's TERMINATION must be reproducible. If struct_distance or the
regime were an LLM call, the same draft could escalate on one run and settle on the next, and no
eval could replay either. Deciding whether a finding is structural is judgment; measuring how far
the structure moved is arithmetic.

Governs how a *loose* escalate threshold terminates (auto-tighten + K_MAX) and how a
non-converging trajectory becomes a rendered contested-structure (R-CONV-01).
Spec: references/artifact-schemas.md (Convergence-guard artifacts).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import ConceptMap  # noqa: E402

# --- config: the spec's starting defaults; tune against convergence-log over real runs ---
K_MAX = 3                # max re-front-load cycles (hard terminator)
MAX_DIVES = 3            # deepen-in-place bound per draft; without it a loop of sub-tau findings
                         # never escalates and never ends (R-CONV-01)
TAU_0 = 4.0              # loose: escalate on split/merge/reorder/home-anchor-level or bigger
TAU_GROWTH = 1.5         # tau(k) = TAU_0 * TAU_GROWTH**k   (auto-tighten)
RHO_CONVERGED = 0.5      # rho < this  => converging
RHO_CONTESTED = 0.7      # rho >= this (sustained) => contested
CLUSTER_DIST = TAU_0     # trajectory clustering distance threshold

# concept-map graph-edit weights (structural distance)
EDIT_WEIGHTS = {
    "leaf_add_remove": 1,
    "edge_add_remove": 2,
    "concept_split_merge": 4,
    "section_add_remove_reorder": 4,
    "home_anchor_or_framing": 6,
    "alias_rename": 0,            # cosmetic; univocity (R-VOCAB-01) handles it
}

MATCH_THRESHOLD = 0.3    # claim-set overlap at which two concepts are "the same" across cycles


def tau(cycle: int) -> float:
    """Escalate threshold at a given cycle (rising). +inf for cycle >= K_MAX.

    The schedule is the whole termination argument: the threshold starts loose so a genuine
    structural finding can escalate early, then auto-tightens, so each further cycle must clear a
    higher bar. At K_MAX it becomes unreachable and the loop cannot escalate again.
    """
    if cycle >= K_MAX:
        return float("inf")
    return TAU_0 * (TAU_GROWTH ** cycle)


def _claims(concept) -> frozenset[str]:
    return frozenset(concept.claim_ids)


def _overlap(a, b) -> float:
    ca, cb = _claims(a), _claims(b)
    if not ca or not cb:
        return 0.0
    return len(ca & cb) / len(ca | cb)


def match_concepts(map_a: ConceptMap, map_b: ConceptMap) -> tuple[list[tuple], list, list]:
    """Pair concepts across two maps by claim-set overlap. Deterministic.

    Matching on claims rather than on concept_id or term is deliberate: curation regenerates ids
    and may rename a concept, and a rename is cosmetic (weight 0) while a claim regrouping is
    structural. Identity has to follow the evidence, not the label.

    Returns (pairs, only_in_a, only_in_b).
    """
    unmatched_b = sorted(map_b.concepts, key=lambda c: c.concept_id)
    pairs: list[tuple] = []
    only_a = []

    for ca in sorted(map_a.concepts, key=lambda c: c.concept_id):
        best, best_score = None, 0.0
        for cb in unmatched_b:
            score = _overlap(ca, cb)
            if score > best_score:
                best, best_score = cb, score
        if best is not None and best_score >= MATCH_THRESHOLD:
            pairs.append((ca, best))
            unmatched_b.remove(best)
        else:
            only_a.append(ca)
    return pairs, only_a, unmatched_b


def _matched_order(cmap: ConceptMap, identity: dict[str, int]) -> list[int]:
    """Salience order of a map's concepts, expressed as matched-pair ids.

    Identity comes from the cross-map match, never from the term — otherwise a pure rename reads
    as a reorder and gets charged 4, which is precisely the cosmetic-vs-structural confusion
    `alias_rename: 0` exists to prevent. Unmatched concepts are excluded: their arrival or
    departure is already priced as a split/merge, and counting them here too would double-charge.
    """
    ordered = sorted(cmap.concepts, key=lambda c: (-(c.salience or 0), c.concept_id))
    return [identity[c.concept_id] for c in ordered if c.concept_id in identity]


def struct_distance(map_a: ConceptMap, map_b: ConceptMap) -> float:
    """Weighted concept-map graph-edit distance (EDIT_WEIGHTS). Deterministic.

    The registry fixes the weights; this fixes what they apply to, since the V1 concept-map has no
    explicit relation graph:

      concept_split_merge (4)      a concept present in one map with no counterpart in the other
      edge_add_remove (2)          a claim that moved between two matched concepts
      leaf_add_remove (1)          a claim that entered or left the map entirely
      home_anchor_or_framing (6)   a matched concept whose anchor or epistemic status changed
      section_add_remove_reorder (4)  the salience ordering of the concepts changed
      alias_rename (0)             term/alias changes on an otherwise identical concept

    Powers Delta_struct (map vs map+implied_edits) and C_k (cycle K-1 vs K).
    """
    pairs, only_a, only_b = match_concepts(map_a, map_b)
    total = 0.0

    total += EDIT_WEIGHTS["concept_split_merge"] * (len(only_a) + len(only_b))

    claims_a = {cid for c in map_a.concepts for cid in c.claim_ids}
    claims_b = {cid for c in map_b.concepts for cid in c.claim_ids}
    total += EDIT_WEIGHTS["leaf_add_remove"] * len(claims_a ^ claims_b)

    shared = claims_a & claims_b
    id_a: dict[str, int] = {}
    id_b: dict[str, int] = {}
    for n, (ca, cb) in enumerate(pairs):
        id_a[ca.concept_id] = n
        id_b[cb.concept_id] = n
        moved = (_claims(ca) ^ _claims(cb)) & shared     # present in both maps, but regrouped
        total += EDIT_WEIGHTS["edge_add_remove"] * len(moved)
        if (ca.home_anchor or "") != (cb.home_anchor or ""):
            total += EDIT_WEIGHTS["home_anchor_or_framing"]
        if (ca.epistemic_status or None) != (cb.epistemic_status or None):
            total += EDIT_WEIGHTS["home_anchor_or_framing"]
        # canonical_term / aliases deliberately contribute nothing (alias_rename == 0)

    if _matched_order(map_a, id_a) != _matched_order(map_b, id_b):
        total += EDIT_WEIGHTS["section_add_remove_reorder"]
    return float(total)


def escalate(delta: float, cycle: int) -> bool:
    """Escalate iff a finding's Delta_struct >= tau(cycle) AND cycle < K_MAX.

    Both conditions are stated even though tau(>=K_MAX) is already +inf — the cap is the
    termination guarantee and should not depend on a float comparison against infinity.
    """
    return cycle < K_MAX and delta >= tau(cycle)


def rho(c_k: float, c_prev: float | None) -> float | None:
    """Convergence ratio C_k / C_(k-1): how much of the previous cycle's movement remains."""
    if not c_prev:
        return None
    return round(c_k / c_prev, 4)


def cluster_maps(maps: list[ConceptMap], threshold: float = CLUSTER_DIST) -> list[list[int]]:
    """Agglomerative (single-linkage) clustering of per-cycle maps by struct_distance."""
    clusters: list[list[int]] = []
    for i, m in enumerate(maps):
        for cluster in clusters:
            if any(struct_distance(m, maps[j]) <= threshold for j in cluster):
                cluster.append(i)
                break
        else:
            clusters.append([i])
    return clusters


def classify_trajectory(maps: list[ConceptMap], threshold: float = CLUSTER_DIST) -> str:
    """Read the regime from the sequence of per-cycle concept-maps.

      1 cluster           -> 'converged'  (footnote residual)
      2-3 stable clusters -> 'contested'  (render the centroids as competing framings)
      >3 / no attractors  -> 'chaotic'    (scope too broad, or campaign diversity miscalibrated)

    The distinction that matters: oscillating between two coherent structures is a fact about the
    FIELD and gets rendered; wandering among many is a fact about this RUN and gets flagged.
    """
    if not maps:
        return "coherent"
    n = len(cluster_maps(maps, threshold))
    if n <= 1:
        return "converged"
    if n <= 3:
        return "contested"
    return "chaotic"


def _centroid(maps: list[ConceptMap], cluster: list[int]) -> int:
    """The cluster member minimizing total distance to the rest (ties -> lowest index)."""
    return min(cluster, key=lambda i: (sum(struct_distance(maps[i], maps[j])
                                           for j in cluster if j != i), i))


def contested_framings(maps: list[ConceptMap], threshold: float = CLUSTER_DIST) -> list[dict]:
    """For a 'contested' trajectory, the cluster centroids as competing framings.

    Each framing is the shape the structure kept returning to, labelled by its highest-salience
    concepts — the primer then presents the disagreement instead of silently picking a side.
    """
    out: list[dict] = []
    for cluster in cluster_maps(maps, threshold):
        cmap = maps[_centroid(maps, cluster)]
        top = sorted(cmap.concepts, key=lambda c: (-(c.salience or 0), c.concept_id))[:3]
        terms = [c.canonical_term for c in top]
        out.append({
            "label": f"by {terms[0]}" if terms else "unlabelled framing",
            "summary": "Organizes the material around " + ", ".join(terms) + "." if terms else "",
            "applies_when": f"the reader's question is framed in terms of {terms[0]}." if terms else None,
            "source_ids": sorted({sid for c in cmap.concepts for sid in c.source_ids}),
            "cycles": sorted(cluster),
        })
    return out
