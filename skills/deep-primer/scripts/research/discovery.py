"""Discovery-campaign engine - deterministic metrics (R-DISC-04).

Classification: local-deterministic. The MODEL parts - extract_leads (report -> structured leads),
triage_leads (accept/flag/drop + salience), assess_topic, wave_briefs - live in planner.py, NOT here.
This module is pure: lead clustering, cross-run support counts, novelty diff, the saturation metric,
and the framing-diversity helper.

The convergence guard's front_load_campaign / re_front_load (planner.py) run this cascade.
Spec: references/artifact-schemas.md (Discovery-campaign artifacts);
brief archetypes: references/discovery-brief-templates.md.
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6a).
"""
from __future__ import annotations

# --- config: starting defaults; tune against discovery-log over real runs ---
MIN_FRAMINGS = 5              # Wave A breadth (distinct diversity-matrix cells)
SATURATION_THRESHOLD = 0.15   # stop a campaign when novel_fraction < this
MAX_WAVES = 4                 # hard cap on waves
SINGLETON_FLAG = True         # high-salience + support_count==1 -> flag for human/judge (gem vs noise)

# the diversity matrix axes; vary briefs across these, >=1 orthogonal framing per wave
FRAMING_AXES = {
    "framing":      ["structure", "debates", "recency-frontier", "source-authority",
                     "adjacent-field", "contrarian-seed", "practitioner", "theorist"],
    "angle":        ["by-method-family", "by-failure-mode", "by-application", "by-chronology"],
    "source_class": ["primary", "industry", "latest-release"],
    "stance":       ["dominant", "against-dominant"],
}
ORTHOGONAL_FRAMINGS = {"contrarian-seed", "adjacent-field"}  # keep >=1 live per wave (R-DISC-02)


def cluster_leads(leads: list) -> list:
    """Embed + agglomerative-cluster near-duplicate leads across runs. Deterministic.
    A cluster's spread across distinct framings is its support_count."""
    raise NotImplementedError("Prompt 6a")


def support_count(cluster, briefs) -> int:
    """Number of DISTINCT framings whose run surfaced this lead (cross-run corroboration)."""
    raise NotImplementedError("Prompt 6a")


def novelty(leads: list, accepted: list) -> float:
    """Fraction of leads not already in the accepted set (a wave's novel_fraction)."""
    raise NotImplementedError("Prompt 6a")


def saturation(discovery_log: dict) -> bool:
    """True when the latest wave's novel_fraction < SATURATION_THRESHOLD (campaign may stop)."""
    raise NotImplementedError("Prompt 6a")


def framing_diversity(briefs: list) -> int:
    """Count distinct diversity-matrix cells covered by a wave's brief set (for R-DISC-02)."""
    raise NotImplementedError("Prompt 6a")
