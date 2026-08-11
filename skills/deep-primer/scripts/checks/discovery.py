"""Discovery-campaign lints (deterministic).

Classification: local-deterministic
Implements: R-DISC-02 (framing_diversity), R-DISC-03 (saturation_terminal),
            R-DISC-05 (snapshot_complete), R-DISC-06 (seed_handling)

These read the campaign's own audit trail — discovery-log.yaml, discovery-leads.yaml, and the
frozen discovery-snapshot/ — not the IR, so they run in their own pass at Phase 1 rather than in
the IR lint. Each returns [] when clean, else a list of violation strings.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import DiscoveryLeads, DiscoveryLog, ResearchBrief  # noqa: E402
from research.discovery import (  # noqa: E402
    MAX_WAVES,
    MIN_FRAMINGS,
    framing_diversity as _cells,
    orthogonal_count,
)

_VALID_TERMINALS = {"saturated", "max_waves"}


def framing_diversity(discovery_log: DiscoveryLog, briefs: list[ResearchBrief]) -> list[str]:
    """R-DISC-02: each wave spans >= MIN_FRAMINGS distinct matrix cells, >=1 of them orthogonal."""
    problems: list[str] = []
    by_wave: dict[str, list[ResearchBrief]] = {}
    for b in briefs:
        by_wave.setdefault(b.wave, []).append(b)

    for record in discovery_log.waves:
        wave_briefs = by_wave.get(record.wave, [])
        if not wave_briefs:
            problems.append(f"wave {record.wave}: discovery-log records {record.briefs} brief(s) "
                            f"but no brief manifest was supplied")
            continue
        cells = _cells(wave_briefs)
        if cells < MIN_FRAMINGS:
            problems.append(f"wave {record.wave}: {cells} distinct framing cell(s) (< {MIN_FRAMINGS}); "
                            f"cosmetically-different briefs pay Nx tokens for 1x recall")
        if record.framing_cells != cells:
            problems.append(f"wave {record.wave}: discovery-log claims {record.framing_cells} "
                            f"framing cells, the brief manifest has {cells}")
        if orthogonal_count(wave_briefs) < 1:
            problems.append(f"wave {record.wave}: no orthogonal framing (contrarian / adjacent-field); "
                            f"the ensemble's blind spots stay correlated")
    return problems


def saturation_terminal(discovery_log: DiscoveryLog) -> list[str]:
    """R-DISC-03: waves <= MAX_WAVES, every wave records novel_fraction, terminal state valid."""
    problems: list[str] = []
    cap = discovery_log.max_waves or MAX_WAVES
    if len(discovery_log.waves) > cap:
        problems.append(f"{len(discovery_log.waves)} waves run, cap is {cap}")
    if discovery_log.terminal not in _VALID_TERMINALS:
        problems.append(f"terminal is {discovery_log.terminal!r}; expected one of {sorted(_VALID_TERMINALS)}")

    for record in discovery_log.waves:
        if not 0.0 <= record.novel_fraction <= 1.0:
            problems.append(f"wave {record.wave}: novel_fraction {record.novel_fraction} outside [0,1]")

    if discovery_log.waves:
        last = discovery_log.waves[-1]
        if last.decision != "stop":
            problems.append(f"wave {last.wave} is the final wave but its decision is {last.decision!r}")
        # the terminal label must match why the campaign actually stopped
        below = last.novel_fraction < discovery_log.saturation_threshold
        if discovery_log.terminal == "saturated" and not below:
            problems.append(
                f"terminal 'saturated' but the final wave's novel_fraction {last.novel_fraction} "
                f">= threshold {discovery_log.saturation_threshold}")
        if discovery_log.terminal == "max_waves" and len(discovery_log.waves) < cap:
            problems.append(f"terminal 'max_waves' but only {len(discovery_log.waves)} of {cap} waves ran")
    return problems


def snapshot_complete(discovery_leads: DiscoveryLeads, snapshot_dir: str | Path) -> list[str]:
    """R-DISC-05: every report an accepted lead cites exists in discovery-snapshot/.

    Eval replays the snapshot instead of re-running the campaign, so a missing report makes a run
    unreproducible even though the lead set looks intact.
    """
    problems: list[str] = []
    root = Path(snapshot_dir)
    if not root.is_dir():
        return [f"snapshot dir {root} does not exist"]
    present = {p.name for p in root.glob("report-*.md")}
    for lead in discovery_leads.accepted():
        if not lead.report_ids:
            problems.append(f"{lead.id}: accepted lead carries no report id")
            continue
        for rid in lead.report_ids:
            name = rid if rid.endswith(".md") else f"report-{rid}.md"
            if name not in present:
                problems.append(f"{lead.id}: report {name!r} missing from {root}")
    return problems


def seed_handling(discovery_leads: DiscoveryLeads, seed_sources: list[dict]) -> list[str]:
    """R-DISC-06: user seeds are consulted and grounded, but never promoted past their evidence.

    Two failure directions, both checked: a seed silently dropped by the salience gate (seeds are
    inclusion-authoritative), and a seed-only claim laundered into an asserted one (a seed with no
    corroboration must still carry its support_count, which is what keeps it corroboration-graded).
    """
    problems: list[str] = []
    directives = {"author", "entity"}
    by_ref: dict[str, list] = {}
    for lead in discovery_leads.all_leads():
        ref = getattr(lead, "url", None) or getattr(lead, "concept", None)
        if ref:
            by_ref.setdefault(ref, []).append(lead)

    for seed in seed_sources:
        kind, ref = seed.get("kind"), seed.get("ref")
        if kind in directives:
            continue  # a directive seeds a brief, not a lead — nothing to resolve here
        matches = by_ref.get(ref, [])
        if not matches:
            problems.append(f"seed {ref!r} ({kind}) never appears in discovery-leads")
            continue
        for lead in matches:
            if lead.status != "accepted":
                problems.append(f"seed {ref!r} has status {lead.status!r}; user seeds are exempt from drop")
            if lead.provenance_origin != "user":
                problems.append(f"seed {ref!r} has provenance_origin {lead.provenance_origin!r}, expected 'user'")

    # a seed accepted on its own authority must still show what corroborates it
    for lead in discovery_leads.accepted():
        if lead.provenance_origin == "user" and lead.support_count == 0 and lead.salience == "high":
            problems.append(
                f"{lead.id}: user seed marked high salience with support_count 0 and no corroboration "
                f"recorded; seeds are authoritative for inclusion, not for truth")
    return problems
