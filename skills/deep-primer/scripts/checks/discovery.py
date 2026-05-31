"""Discovery-campaign lints (deterministic).

Classification: local-deterministic
Implements: R-DISC-02 (framing_diversity), R-DISC-03 (saturation_terminal), R-DISC-05 (snapshot_complete)
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6a).
"""
from __future__ import annotations


def seed_handling(discovery_leads: dict, seed_sources: list) -> list[str]:
    """R-DISC-06: every seed_source appears in discovery-leads as status=accepted with
    provenance_origin=user; seed-only claims carry corroboration_count (not promoted past evidence). [] if ok."""
    raise NotImplementedError("Prompt 6a")


def framing_diversity(discovery_log: dict, briefs: list) -> list[str]:
    """R-DISC-02: each wave covers >= MIN_FRAMINGS matrix cells incl. >=1 orthogonal. [] if ok."""
    raise NotImplementedError("Prompt 6a")


def saturation_terminal(discovery_log: dict) -> list[str]:
    """R-DISC-03: waves <= MAX_WAVES, per-wave novel_fraction recorded, terminal valid. [] if ok."""
    raise NotImplementedError("Prompt 6a")


def snapshot_complete(discovery_leads: dict, snapshot_dir: str) -> list[str]:
    """R-DISC-05: every report referenced by an accepted lead exists in the snapshot. [] if ok."""
    raise NotImplementedError("Prompt 6a")
