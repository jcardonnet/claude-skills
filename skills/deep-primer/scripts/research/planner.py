"""Discovery-campaign orchestrator + the model-judged research controller.

Classification: agent-orchestrated / model-judged. Deterministic metrics live in
research/discovery.py (R-DISC-04); the backend adapter in research/deep_research.py.

The R-DISC-04 split is load-bearing and runs through this file: the model supplies JUDGMENT
(what a report is pointing at, whether a lead is worth chasing, how aggressive to be), while the
campaign's STRUCTURE and STOPPING DECISION stay deterministic. So `wave_briefs` guarantees the
R-DISC-02 diversity invariant in code and asks the model only to phrase questions; `triage_leads`
lets the model accept/flag/drop but computes support and novelty in discovery.py; and
`front_load_campaign` decides when to stop from the saturation metric, never from a model's
opinion that it has "found enough".

Brief archetypes are the machine-readable half of references/discovery-brief-templates.md; a test
asserts the two stay in lockstep.
Spec: references/artifact-schemas.md (Discovery-campaign artifacts).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import (  # noqa: E402
    Block,
    ConceptMap,
    ConvergenceLog,
    CycleRecord,
    DiscoveryLeads,
    DiscoveryLog,
    Framing,
    Lead,
    ResearchBrief,
    SourceLead,
    TopicLead,
    WaveRecord,
)
from research import convergence, discovery  # noqa: E402
from research.deep_research import Backend, brief_id, run_brief  # noqa: E402

# Standing instructions carried on every brief (discovery-brief-templates.md).
STANDING_INSTRUCTIONS = [
    "prioritize primary / non-vendor sources",
    "report the count of independent supporting sources per key claim, and flag any disagreement",
    "pin the latest version + release date of every named tool",
    "return sources with URLs",
]

# archetype -> (framing, angle, source_class, stance, question template)
BRIEF_ARCHETYPES: dict[str, tuple] = {
    # Wave A - divergent landscape
    "A1": ("structure", "by-method-family", None, None,
           "Map the full landscape of {topic}: subfields, the canonical taxonomy, and how practitioners carve it up."),
    "A2": ("debates", "by-failure-mode", None, None,
           "What are the live controversies and open problems in {topic}? Where is there no consensus?"),
    "A3": ("recency-frontier", None, "latest-release", None,
           "What changed in {topic} in the last 6-12 months - new releases, SOTA shifts, deprecated approaches?"),
    "A4": ("source-authority", None, "primary", None,
           "The most authoritative primary sources, seminal works, key recent papers, and best practitioner writeups on {topic}."),
    "A5": ("adjacent-field", None, None, None,
           "What adjacent fields does {topic} borrow from, resemble, or get confused with? Where are the false friends?"),
    "A6": ("contrarian-seed", None, None, "against-dominant",
           "Make the strongest case against the dominant approach in {topic}. What do skeptics argue, and on what evidence?"),
    # Wave B - convergent targeted dives
    "B-seed": ("source-authority", None, "primary", None,
               "Survey the work of {seed} on {topic}. Summarize key claims and where they sit relative to the consensus."),
    "B-dive": ("theorist", "by-method-family", "primary", None,
               "Deep dive on {concept} within {topic}: mechanism, tradeoffs, when it fails, current best practice, primary sources."),
    "B-conflict": ("debates", "by-failure-mode", None, "against-dominant",
                   "Claim: {claim}. Counter-claim: not-{claim}. Find the deciding evidence and why the two camps disagree."),
    # Wave C - findings audit
    "C-omission": ("practitioner", "by-application", None, None,
                   "A primer on {topic} currently covers: {coverage}. What important aspects are missing?"),
    "C-disconfirm": ("contrarian-seed", "by-failure-mode", None, "against-dominant",
                     "Key claims of a primer on {topic}: {claims}. Find the strongest evidence any are wrong or overstated."),
    "C-source-completeness": ("adjacent-field", None, "primary", None,
                              "Sources a primer on {topic} cites: {sources}. What authoritative sources are NOT in this list?"),
}

# R-DISC-02's framing floor governs the BREADTH wave only (G10, resolved). B and C are deliberately
# narrow follow-ups — pinned to references/discovery-brief-templates.md by
# test_brief_archetypes_match_the_template_document — and forcing five cells onto a targeted wave
# would manufacture the very padding the rule exists to prevent. Every wave still owes DISTINCT
# cells, which `wave_briefs` does guarantee here in code.
WAVE_ARCHETYPES = {
    "A": ["A1", "A2", "A3", "A4", "A5", "A6"],
    "B": ["B-dive", "B-conflict", "B-seed"],
    "C": ["C-omission", "C-disconfirm", "C-source-completeness"],
}

_DIRECT_SEED_KINDS = {"url", "file", "project_ref"}
_DIRECTIVE_SEED_KINDS = {"author", "entity"}


# --- the model-judged seam ---------------------------------------------------

class Judge(Protocol):
    """Every model call the campaign makes. Injecting it keeps the cascade testable offline."""

    def assess_topic(self, topic: str, params: dict) -> dict: ...
    def extract_leads(self, report: str, sources: list[dict], brief: ResearchBrief) -> dict: ...
    def triage(self, clusters: list[list[Lead]], params: dict) -> dict: ...


@dataclass
class StubJudge:
    """Deterministic offline judge — the test/replay default.

    Extracts leads by reading the frozen report's own `- lead:` lines rather than inventing any,
    and accepts everything it is given. It exists so the cascade's control flow can be exercised
    without a model; it is not a substitute for one.
    """

    accept_all: bool = True

    def assess_topic(self, topic: str, params: dict) -> dict:
        return {"front_load_aggressiveness": "standard", "interleave_budget": 0}

    def extract_leads(self, report: str, sources: list[dict], brief: ResearchBrief) -> dict:
        topic_leads, source_leads = [], []
        for i, line in enumerate(report.splitlines()):
            line = line.strip()
            if line.startswith("- lead:"):
                concept = line.removeprefix("- lead:").strip()
                topic_leads.append({"id": f"tl-{brief_id(brief)}-{i}", "concept": concept,
                                    "surfaced_by": [brief.framing]})
        for j, s in enumerate(sources):
            lead = {"id": f"sl-{brief_id(brief)}-{j}", "url": s.get("url", ""),
                    "type": s.get("type"), "surfaced_by": [brief.framing]}
            # Carry the backend's own verdict through. This used to read only url+type, so a lead a
            # verifying backend had already marked `dropped` — a 404, a robots-disallowed host — was
            # rebuilt with the default `accepted` and frozen into the snapshot as a real source. The
            # judge may DOWNGRADE a lead; it must never silently upgrade one the fetcher could not
            # retrieve, which is R-DISC-01's "a lead is a pointer, not evidence" failing at the seam.
            for key in ("status", "provenance_origin", "dropped_reason", "fetched_title",
                        "retrieved_at"):
                if s.get(key):
                    lead[key] = s[key]
            source_leads.append(lead)
        return {"topic_leads": topic_leads, "source_leads": source_leads}

    def triage(self, clusters: list[list[Lead]], params: dict) -> dict:
        return {cluster[0].id: ("accepted" if self.accept_all else "dropped") for cluster in clusters}


# --- deterministic helpers (no model) ----------------------------------------

def route_seeds(seed_sources: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split user seed_sources into (direct_leads, directive_briefs). Deterministic.

    Direct seeds (url/file/project_ref) become accepted source_leads carrying
    provenance_origin=user and exempt from triage-drop; author/entity directives seed a targeted
    brief instead. Seeds are inclusion-authoritative only (R-DISC-06) — still corroboration-graded
    downstream, and the R-DISC-01 firewall still applies: a seed is fetched and grounded, never
    pre-trusted prose.

    NOTE: project_ref resolves only under claude.ai, not from a Claude Code run.
    """
    direct, directives = [], []
    for seed in seed_sources or []:
        kind = seed.get("kind")
        if kind in _DIRECT_SEED_KINDS:
            direct.append({
                "id": f"sl-seed-{len(direct)}",
                "url": seed.get("ref", ""),
                "type": seed.get("type"),
                "status": "accepted",
                "provenance_origin": "user",
                "surfaced_by": ["user-seed"],
            })
        elif kind in _DIRECTIVE_SEED_KINDS:
            directives.append(seed)
    return direct, directives


def wave_briefs(wave: str, residual: list | None = None, params: dict | None = None,
                judge: Judge | None = None) -> list[ResearchBrief]:
    """Emit a wave's brief ensemble from the archetypes.

    The R-DISC-02 invariant is guaranteed HERE, in code, because it is a MUST lint — a model asked
    to "be diverse" reliably produces cosmetically-different briefs that share a blind spot. The
    model's contribution is wording. Scoped per G10: the BREADTH wave gets >= MIN_FRAMINGS distinct
    cells including >=1 orthogonal; every wave gets DISTINCT cells.
    """
    params = params or {}
    topic = params.get("target_domain", "{topic}")
    names = WAVE_ARCHETYPES.get(wave, [])
    briefs: list[ResearchBrief] = []
    for name in names:
        framing, angle, source_class, stance, template = BRIEF_ARCHETYPES[name]
        if name == "B-seed" and not params.get("seed"):
            continue
        question = (template
                    .replace("{topic}", str(topic))
                    .replace("{seed}", str(params.get("seed", "")))
                    .replace("{concept}", str((residual or ["the residual gap"])[0]))
                    .replace("{claim}", str(params.get("claim", "the dominant claim")))
                    .replace("{coverage}", str(params.get("coverage", "")))
                    .replace("{claims}", str(params.get("claims", "")))
                    .replace("{sources}", str(params.get("sources", ""))))
        briefs.append(ResearchBrief(
            wave=wave, framing=framing, angle=angle, source_class=source_class, stance=stance,
            questions=[question], instructions=list(STANDING_INSTRUCTIONS), brief_id=f"{wave}-{name}",
            seed_ref=params.get("seed") if name == "B-seed" else None,
        ))

    if wave == "A" and discovery.orthogonal_count(briefs) < 1:  # defensive: the archetypes supply A5/A6
        raise ValueError("wave A must carry >=1 orthogonal framing (R-DISC-02)")
    return briefs


def _to_leads(payload: dict, report_id: str) -> tuple[list[TopicLead], list[SourceLead]]:
    topic = [TopicLead(**{**t, "report_ids": [report_id]}) for t in payload.get("topic_leads", [])]
    source = [SourceLead(**{**s, "report_ids": [report_id]}) for s in payload.get("source_leads", [])]
    return topic, source


def triage_leads(clustered: list[list[Lead]], params: dict | None = None,
                 judge: Judge | None = None, briefs: list[ResearchBrief] | None = None) -> list[Lead]:
    """Model-judged accept/flag/drop, with the deterministic metrics attached first.

    Order matters: support_count and novelty are computed in discovery.py BEFORE the judge sees a
    cluster, so its decision is informed by reproducible numbers rather than producing them. User
    seeds are exempt from drop (R-DISC-06), and a high-salience singleton is flagged rather than
    dropped — the rare-gem-vs-noise call is not one to make silently.
    """
    judge = judge or StubJudge()
    params = params or {}
    verdicts = judge.triage(clustered, params)

    out: list[Lead] = []
    for cluster in clustered:
        head = cluster[0]
        head.support_count = discovery.support_count(cluster, briefs or [])
        head.surfaced_by = sorted({f for m in cluster for f in m.surfaced_by})
        head.report_ids = sorted({r for m in cluster for r in m.report_ids})
        status = verdicts.get(head.id, "accepted")
        # A lead the FETCHER could not retrieve is a fact, not a judgement, and the judge must not
        # overturn it. Without this a 404 or robots-disallowed URL was re-promoted to `accepted` and
        # frozen into the snapshot as a real source — R-DISC-01's "a lead is a pointer, not
        # evidence" failing one seam further in than extract_leads. Checked BEFORE the user-seed
        # exemption on purpose: a seed that will not load is still not evidence, and R-DISC-06 asks
        # for seeds to be consulted and grounded, not asserted past what they can support.
        if head.status == "dropped" and getattr(head, "dropped_reason", None):
            head.status = "dropped"
            out.append(head)
            continue
        if head.provenance_origin == "user":
            status = "accepted"                                  # R-DISC-06: exempt from drop
        elif (discovery.SINGLETON_FLAG and head.support_count <= 1
              and head.salience == "high" and status == "dropped"):
            status = "flagged"                                   # rare gem vs noise -> human/judge
        head.status = status
        out.append(head)
    return out


# --- the cascade -------------------------------------------------------------

@dataclass
class CampaignResult:
    leads: DiscoveryLeads
    log: DiscoveryLog
    briefs: list[ResearchBrief] = field(default_factory=list)


def front_load_campaign(topic: str, params: dict | None = None, snapshot_dir: str | Path = "discovery-snapshot",
                        backend: Backend | None = None, judge: Judge | None = None,
                        waves: tuple[str, ...] = ("A", "B", "C")) -> CampaignResult:
    """Run Wave A->B->C to saturation; return the triaged leads plus the audit log.

    Stopping is deterministic (R-DISC-03/04): a wave's novel_fraction against the accepted set
    decides whether another runs, bounded by MAX_WAVES. Called at cycle 0 and, via re_front_load,
    on escalation by the convergence guard.
    """
    params = dict(params or {})
    params.setdefault("target_domain", topic)
    judge = judge or StubJudge()

    accepted: list[Lead] = []
    all_briefs: list[ResearchBrief] = []
    records: list[WaveRecord] = []
    terminal = "max_waves"

    seed_direct, _ = route_seeds(params.get("seed_sources", []))
    accepted.extend(SourceLead(**s) for s in seed_direct)

    for wave in waves[:discovery.MAX_WAVES]:
        briefs = wave_briefs(wave, residual=params.get("residual"), params=params, judge=judge)
        all_briefs.extend(briefs)

        fresh: list[Lead] = []
        for brief in briefs:
            report, sources = run_brief(brief, snapshot_dir, backend)
            topic_leads, source_leads = _to_leads(
                judge.extract_leads(report, sources, brief), brief_id(brief))
            fresh.extend([*topic_leads, *source_leads])

        novel = discovery.novel_leads(fresh, accepted)
        novel_fraction = len(novel) / len(fresh) if fresh else 0.0
        clusters = discovery.cluster_leads([*accepted, *fresh])
        accepted = triage_leads(clusters, params, judge, all_briefs)

        saturated = novel_fraction < discovery.SATURATION_THRESHOLD
        records.append(WaveRecord(
            wave=wave, briefs=len(briefs), framing_cells=discovery.framing_diversity(briefs),
            leads_total=len(fresh), leads_new=len(novel),
            novel_fraction=round(novel_fraction, 4),
            decision="stop" if saturated else "continue",
        ))
        if saturated:
            terminal = "saturated"
            break

    if records and records[-1].decision != "stop":
        records[-1].decision = "stop"   # the cap stopped it; the log must say so

    leads = DiscoveryLeads(
        topic_leads=[lead for lead in accepted if isinstance(lead, TopicLead)],
        source_leads=[lead for lead in accepted if isinstance(lead, SourceLead)],
    )
    # The cap this campaign actually ran under, not the global ceiling. `waves` is configurable and
    # defaults to three, so recording MAX_WAVES=4 made every unsaturated run report terminal
    # 'max_waves' after 3 of 4 — a label describing a cap that was never reached. R-DISC-03 checks
    # exactly that correspondence, and the check had no dispatch entry to catch it with.
    log = DiscoveryLog(max_waves=min(len(waves), discovery.MAX_WAVES),
                       saturation_threshold=discovery.SATURATION_THRESHOLD,
                       waves=records, terminal=terminal)
    return CampaignResult(leads=leads, log=log, briefs=all_briefs)


def re_front_load(topic: str, finding: dict, params: dict | None = None,
                  snapshot_dir: str | Path = "discovery-snapshot",
                  backend: Backend | None = None, judge: Judge | None = None) -> CampaignResult:
    """A focused campaign seeded by an escalation finding (the convergence guard's entry point).

    Narrower than the initial front-load by design: Wave B dives on the specific structural
    wrinkle that escalated, then a Wave C audit. Wave A is not re-run — the landscape was already
    swept, and re-sweeping it is how an escalate loop burns its budget without new information.
    """
    params = dict(params or {})
    params["residual"] = [finding.get("concept") or finding.get("finding", "the escalation finding")]
    params["claim"] = finding.get("claim", params.get("claim", "the dominant claim"))
    return front_load_campaign(topic, params, snapshot_dir, backend, judge, waves=("B", "C"))


def write_campaign(result: CampaignResult, out_dir: str | Path = ".") -> dict[str, Path]:
    """Persist discovery-leads.yaml + discovery-log.yaml (the artifacts the lints read)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "leads": out / "discovery-leads.yaml",
        "log": out / "discovery-log.yaml",
    }
    paths["leads"].write_text(
        yaml.safe_dump(result.leads.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    paths["log"].write_text(
        yaml.safe_dump(result.log.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    return paths


# --- the convergence guard's model-judged side + the draft loop (R-CONV-02) ---
# convergence.py stays pure; the judgment calls live here, next to the campaign they re-trigger.

class StructureJudge(Protocol):
    """The two model calls the convergence guard makes. Everything else about it is arithmetic."""

    def scan_for_structural(self, concept_map: ConceptMap, params: dict) -> dict | None:
        """Is there a finding that changes the STRUCTURE (vs one that just deepens a section)?"""

    def implied_edits(self, finding: dict, concept_map: ConceptMap) -> ConceptMap:
        """The concept-map that finding implies. Its distance from the current map is Delta_struct."""


@dataclass
class ScriptedStructureJudge:
    """Deterministic offline structure judge: replays a scripted list of findings.

    Each entry is (finding, next_map). Exhausting the script means "no further structural
    finding", which is how a converging trajectory terminates.
    """

    script: list[tuple[dict, ConceptMap]] = field(default_factory=list)
    _i: int = 0

    def scan_for_structural(self, concept_map: ConceptMap, params: dict) -> dict | None:
        return self.script[self._i][0] if self._i < len(self.script) else None

    def implied_edits(self, finding: dict, concept_map: ConceptMap) -> ConceptMap:
        proposed = self.script[self._i][1]
        self._i += 1
        return proposed


@dataclass
class ConvergenceRun:
    log: ConvergenceLog
    cycle_maps: list[ConceptMap]
    contested_block: Block | None = None

    @property
    def regime(self) -> str | None:
        return self.log.terminal_regime


_TERMINAL_DECISION = {
    "converged": "footnote-residual",
    "contested": "render-contested",
    "chaotic": "flag-scope",
    "coherent": "draft",
}


def run_convergence_loop(initial_map: ConceptMap, judge: StructureJudge,
                         params: dict | None = None,
                         recurate=None) -> ConvergenceRun:
    """Drive the drafting<->structure loop to a valid terminal state (R-CONV-01).

    Three exits, and the loop provably reaches one of them:
      - no further structural finding            -> converged / coherent (footnote the residual)
      - Delta_struct >= tau(cycle), cycle < K_MAX -> escalate: re-front-load, cycle++
      - neither                                   -> deepen in place, bounded by MAX_DIVES

    Termination: `cycle` only ever increments on an escalate, escalation requires cycle < K_MAX,
    and the deepen path is separately capped — so neither branch can spin.

    `recurate(finding, current_map) -> ConceptMap` is the escalation seam: in production it runs
    re_front_load, re-grounds, and re-curates. Offline it defaults to the judge's proposed map, so
    the control flow is exercisable without a campaign.
    """
    params = params or {}
    cycle = 0
    dives = 0
    current = initial_map
    cycle_maps = [initial_map]
    records = [CycleRecord(cycle=0, c_k=None, rho=None, tau=convergence.tau(0),
                           finding="initial", decision="draft")]
    prev_c: float | None = None

    while True:
        finding = judge.scan_for_structural(current, params)
        if finding is None:
            regime = "coherent" if len(cycle_maps) == 1 else convergence.classify_trajectory(cycle_maps)
            break

        proposed = judge.implied_edits(finding, current)
        delta = convergence.struct_distance(current, proposed)
        label = str(finding.get("finding") or finding.get("concept") or "structural finding")

        if convergence.escalate(delta, cycle):
            cycle += 1
            current = (recurate(finding, current) if recurate else proposed)
            c_k = convergence.struct_distance(cycle_maps[-1], current)
            cycle_maps.append(current)
            records.append(CycleRecord(cycle=cycle, c_k=c_k, rho=convergence.rho(c_k, prev_c),
                                       tau=convergence.tau(cycle), finding=label,
                                       decision="escalate"))
            prev_c = c_k
            dives = 0
            continue

        dives += 1
        if dives > convergence.MAX_DIVES:
            records.append(CycleRecord(cycle=cycle, c_k=None, rho=None, tau=convergence.tau(cycle),
                                       finding=f"{label} (dive cap reached)", decision="stop"))
            regime = convergence.classify_trajectory(cycle_maps) if len(cycle_maps) > 1 else "coherent"
            break
        current = proposed
        records.append(CycleRecord(cycle=cycle, c_k=None, rho=None, tau=convergence.tau(cycle),
                                   finding=label, decision="deepen"))

    if records[-1].decision not in ("stop",):
        records.append(CycleRecord(cycle=cycle, c_k=None, rho=None, tau=convergence.tau(cycle),
                                   finding="terminal", decision="stop"))

    log = ConvergenceLog(k_max=convergence.K_MAX, cycles=records, terminal_regime=regime,
                         terminal_decision=_TERMINAL_DECISION[regime])

    block = None
    if regime == "contested":
        block = build_contested_block(cycle_maps)
        for cmap in cycle_maps:
            cmap.contested = True
    return ConvergenceRun(log=log, cycle_maps=cycle_maps, contested_block=block)


def build_contested_block(cycle_maps: list[ConceptMap], block_id: str = "contested-structure") -> Block:
    """The `role: contested` IR block: the framings the trajectory oscillated among.

    Emitting this is the point of the whole guard — when the structure will not settle, the primer
    presents the competing organizations rather than asserting one and hiding the disagreement.
    """
    framings = [Framing(label=f["label"], summary=f["summary"], applies_when=f["applies_when"],
                        source_ids=f["source_ids"])
                for f in convergence.contested_framings(cycle_maps)]
    return Block(block_id=block_id, role="contested", framings=framings, provenance="verified",
                 source_ids=sorted({sid for f in framings for sid in f.source_ids}))


def write_convergence(run: ConvergenceRun, out_dir: str | Path = ".") -> dict[str, Path]:
    """Persist concept-map-vK.yaml per cycle + convergence-log.yaml."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for k, cmap in enumerate(run.cycle_maps):
        cmap.cycle = k
        p = out / f"concept-map-v{k}.yaml"
        p.write_text(yaml.safe_dump(cmap.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
                     encoding="utf-8")
        paths[f"map_v{k}"] = p
    log_path = out / "convergence-log.yaml"
    log_path.write_text(yaml.safe_dump(run.log.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
                        encoding="utf-8")
    paths["log"] = log_path
    return paths
