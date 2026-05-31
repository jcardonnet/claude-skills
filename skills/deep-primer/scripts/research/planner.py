"""Discovery-campaign orchestrator + the model-judged research controller.

Classification: agent-orchestrated / model-judged. Deterministic metrics live in
research/discovery.py (R-DISC-04); the backend adapter in research/deep_research.py.

Holds: assess_topic (maturity/breadth/contestedness -> front-load aggressiveness + interleave budget),
wave_briefs (emit the diverse brief ensemble per wave from discovery-brief-templates.md + the
perspectives registry), extract_leads (report -> structured leads via --json-schema, leads only),
triage_leads (accept/flag/drop + salience: the model-judged gate), and the cascade entry points the
convergence guard calls - front_load_campaign and re_front_load.
Spec: references/artifact-schemas.md (Discovery-campaign artifacts).
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6a).
NOTE: agent-orchestrated - tool-loops using /deep-research + the model, NOT hermetic functions.
"""
from __future__ import annotations


def route_seeds(seed_sources: list) -> tuple:
    """Split user seed_sources into (direct_leads, directive_briefs). Direct seeds (url/file/project_ref)
    -> accepted source_leads with provenance_origin=user, exempt from triage-drop; author/entity ->
    a seed-anchored brief. Seeds are inclusion-authoritative only (R-DISC-06): still corroboration-graded.
    NOTE: project_ref resolves only under claude.ai (not reachable from a Claude Code run)."""
    raise NotImplementedError("Prompt 6a")


def assess_topic(topic: str, params: dict) -> dict:
    """Model-judged: maturity / breadth / contestedness -> {front_load_aggressiveness, interleave_budget}."""
    raise NotImplementedError("Prompt 6a")


def wave_briefs(wave: str, residual: list, params: dict) -> list:
    """Emit a wave's diverse brief ensemble (>= MIN_FRAMINGS cells, >=1 orthogonal) from the templates."""
    raise NotImplementedError("Prompt 6a")


def extract_leads(report: str, sources: list) -> dict:
    """Model (--json-schema): report+sources -> topic_leads + source_leads (no claims; leads only)."""
    raise NotImplementedError("Prompt 6a")


def triage_leads(clustered: list, params: dict) -> dict:
    """Model-judged gate: accept / flag (high-salience singleton) / drop, salience vs audience+budget.
    User seeds (provenance_origin=user) are exempt from drop (R-DISC-06)."""
    raise NotImplementedError("Prompt 6a")


def front_load_campaign(topic: str, params: dict) -> dict:
    """Run Wave A->B->C to saturation; return accepted discovery-leads + write discovery-snapshot/.
    Called at cycle 0 and (via re_front_load) on escalation by the convergence guard."""
    raise NotImplementedError("Prompt 6a")


def re_front_load(topic: str, finding: dict) -> dict:
    """Re-run a focused campaign seeded by an escalation finding; return a new curated concept-map."""
    raise NotImplementedError("Prompt 6a")
