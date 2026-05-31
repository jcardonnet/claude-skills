"""Convergence guard for the escalate (re-front-load) loop.

Classification: local-deterministic (R-CONV-02). The MODEL parts — scan_for_structural,
implied_edits — live in the orchestrator/judge (planner.py), NOT here. This module is pure:
structural distance, the tau schedule, convergence ratios, and trajectory clustering only.

Governs how a *loose* escalate threshold terminates (auto-tighten + K_MAX) and how a
non-converging trajectory becomes a rendered contested-structure (R-CONV-01).
Spec: references/artifact-schemas.md (Convergence-guard artifacts).
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6b).
"""
from __future__ import annotations

# --- config: the spec's starting defaults; tune against convergence-log over real runs ---
K_MAX = 3                # max re-front-load cycles (hard terminator)
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


def tau(cycle: int) -> float:
    """Escalate threshold at a given cycle (rising). +inf for cycle >= K_MAX."""
    raise NotImplementedError("Prompt 6b: TAU_0 * TAU_GROWTH**cycle, float('inf') if cycle >= K_MAX")


def struct_distance(map_a, map_b) -> float:
    """Weighted concept-map graph-edit distance (EDIT_WEIGHTS). Deterministic.

    Powers Delta_struct (map vs map+implied_edits) and C_k (cycle K-1 vs K)."""
    raise NotImplementedError("Prompt 6b: diff the two concept-maps into weighted edits and sum")


def escalate(delta: float, cycle: int) -> bool:
    """Escalate iff a finding's Delta_struct >= tau(cycle) AND cycle < K_MAX."""
    raise NotImplementedError("Prompt 6b")


def classify_trajectory(maps: list) -> str:
    """Read the regime from the sequence of per-cycle concept-maps.

    Cluster maps by pairwise struct_distance (threshold CLUSTER_DIST):
      1 cluster / C_k -> 0   -> 'converged'  (footnote residual)
      2-3 stable clusters    -> 'contested'  (render the centroids as competing framings)
      >3 / no attractors     -> 'chaotic'    (scope too broad, or campaign diversity miscalibrated)
    Returns one of: 'converged' | 'contested' | 'chaotic'."""
    raise NotImplementedError("Prompt 6b: agglomerative cluster on struct_distance; cluster count -> regime")


def contested_framings(maps: list) -> list:
    """For a 'contested' trajectory, return the cluster centroids as competing framings
    (label, summary, applies_when, source_ids) for the contested-structure block (role: contested)."""
    raise NotImplementedError("Prompt 6b")
