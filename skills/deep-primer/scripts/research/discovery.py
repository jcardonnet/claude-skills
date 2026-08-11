"""Discovery-campaign engine - deterministic metrics (R-DISC-04).

Classification: local-deterministic. The MODEL parts - extract_leads (report -> structured leads),
triage_leads (accept/flag/drop + salience), assess_topic, wave_briefs - live in planner.py, NOT here.
This module is pure: lead clustering, cross-run support counts, novelty diff, the saturation metric,
and the framing-diversity helper.

R-DISC-04 exists because the campaign's STOPPING DECISION must be reproducible: if clustering or
saturation were an LLM call, two runs of the same campaign could terminate at different waves and
the eval could never replay a snapshot. Everything here is therefore a pure function of its inputs,
free of wall-clock, randomness, and iteration-order effects (leads are sorted by id before
clustering, so the result does not depend on the order reports came back).

The convergence guard's front_load_campaign / re_front_load (planner.py) run this cascade.
Spec: references/artifact-schemas.md (Discovery-campaign artifacts);
brief archetypes: references/discovery-brief-templates.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable, Iterable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Lead, ResearchBrief  # noqa: E402

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

SIMILARITY_THRESHOLD = 0.6    # >= this counts as the same lead across runs

_WORD_RE = re.compile(r"\b[\w'-]+\b")
_STOP = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "to", "with", "as", "by", "at",
    "from", "is", "are", "be", "this", "that", "it", "its", "how", "what", "why", "when",
}


def _tokens(text: str | None) -> frozenset[str]:
    return frozenset(w for w in (t.lower() for t in _WORD_RE.findall(text or ""))
                     if len(w) >= 3 and w not in _STOP)


def lead_text(lead: Lead) -> str:
    """The text a lead is compared on: its concept/url plus its rationale."""
    parts = [getattr(lead, "concept", None), getattr(lead, "url", None),
             getattr(lead, "why", None)]
    return " ".join(p for p in parts if p)


class Similarity(Protocol):
    name: str

    def score(self, a: str, b: str) -> float: ...


class LexicalSimilarity:
    """Deterministic offline default: Jaccard over content tokens.

    Under-merges relative to embeddings (two phrasings of one idea can fall below threshold), which
    costs recall in clustering but never reproducibility. The embedding backend is the production
    upgrade; it plugs in here without touching callers.
    """

    name = "lexical"

    def score(self, a: str, b: str) -> float:
        ta, tb = _tokens(a), _tokens(b)
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)


class CallableSimilarity:
    """Production seam for an embedding-backed scorer (injected, so this module stays pure)."""

    name = "embedding"

    def __init__(self, score_fn: Callable[[str, str], float]) -> None:
        self._fn = score_fn

    def score(self, a: str, b: str) -> float:
        return float(self._fn(a, b))


def resolve_similarity(name: str = "auto", score_fn: Callable[[str, str], float] | None = None) -> Similarity:
    if name in ("auto", "lexical"):
        return LexicalSimilarity()
    if name == "embedding":
        if score_fn is None:
            raise ValueError("the 'embedding' backend needs score_fn")
        return CallableSimilarity(score_fn)
    raise ValueError(f"unknown similarity backend: {name!r}")


def normalize_url(url: str | None) -> str:
    """Canonical form for source identity: scheme-less, lowercased, no trailing slash."""
    u = (url or "").strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    return u.removeprefix("www.").rstrip("/")


def same_lead(a: Lead, b: Lead, backend: Similarity, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    """Whether two leads denote the same thing.

    Source leads are identified by normalized URL, NOT by text similarity: two distinct papers on
    one site share most of their URL tokens, and fuzzy-matching them silently collapses the source
    set — which would understate novelty and stop the campaign early. Topic leads, which are
    free-text concepts, use the similarity backend.
    """
    if type(a) is not type(b):
        return False
    ua, ub = getattr(a, "url", None), getattr(b, "url", None)
    if ua is not None and ub is not None:
        return normalize_url(ua) == normalize_url(ub)
    return backend.score(lead_text(a), lead_text(b)) >= threshold


def cluster_leads(leads: Iterable[Lead], backend: Similarity | None = None,
                  threshold: float = SIMILARITY_THRESHOLD) -> list[list[Lead]]:
    """Group near-duplicate leads surfaced by different runs. Deterministic.

    Single-linkage greedy assignment over leads sorted by id: a lead joins the first cluster
    holding a member it matches, else it starts one. Sorting first is what makes the output
    independent of the order reports arrived in.
    """
    backend = backend or resolve_similarity()
    clusters: list[list[Lead]] = []
    for lead in sorted(leads, key=lambda x: x.id):
        for cluster in clusters:
            if any(same_lead(lead, m, backend, threshold) for m in cluster):
                cluster.append(lead)
                break
        else:
            clusters.append([lead])
    return clusters


def support_count(cluster: list[Lead], briefs: Iterable[ResearchBrief] = ()) -> int:
    """Number of DISTINCT framings whose run surfaced this lead (cross-run corroboration).

    Counts framings, not mentions: five briefs sharing one framing are one blind spot, not five
    independent confirmations, so they must not inflate a lead's support.
    """
    by_id = {b.brief_id: b.framing for b in briefs if b.brief_id}
    framings = {by_id.get(origin, origin) for lead in cluster for origin in lead.surfaced_by}
    return len(framings - {None})


def novel_leads(leads: Iterable[Lead], accepted: Iterable[Lead], backend: Similarity | None = None,
                threshold: float = SIMILARITY_THRESHOLD) -> list[Lead]:
    """The subset of `leads` matching nothing already accepted — deduped against each other too.

    Deduping within the wave matters: six briefs surfacing one idea is one new lead, and counting
    it six times would keep novel_fraction high and the campaign running past saturation.
    """
    backend = backend or resolve_similarity()
    known = list(accepted)
    out: list[Lead] = []
    for lead in leads:
        if not any(same_lead(lead, k, backend, threshold) for k in [*known, *out]):
            out.append(lead)
    return out


def novelty(leads: Iterable[Lead], accepted: Iterable[Lead], backend: Similarity | None = None,
            threshold: float = SIMILARITY_THRESHOLD) -> float:
    """A wave's novel_fraction: the share of `leads` that do not match anything already accepted.

    Diversity-aware by construction — matching runs through the same backend as clustering, so a
    rephrased duplicate does not read as novel. Returns 0.0 for an empty wave (nothing new was
    found, which is the saturating direction).
    """
    leads = list(leads)
    if not leads:
        return 0.0
    return len(novel_leads(leads, accepted, backend, threshold)) / len(leads)


def saturation(discovery_log: dict | object) -> bool:
    """True when the latest wave's novel_fraction fell below SATURATION_THRESHOLD.

    Accepts a DiscoveryLog or the raw dict its YAML parses to.
    """
    waves = discovery_log.get("waves", []) if isinstance(discovery_log, dict) else discovery_log.waves
    if not waves:
        return False
    last = waves[-1]
    threshold = (discovery_log.get("saturation_threshold", SATURATION_THRESHOLD)
                 if isinstance(discovery_log, dict) else discovery_log.saturation_threshold)
    fraction = last["novel_fraction"] if isinstance(last, dict) else last.novel_fraction
    return fraction < threshold


def framing_diversity(briefs: Iterable[ResearchBrief]) -> int:
    """Distinct diversity-matrix cells covered by a wave's brief set (for R-DISC-02)."""
    return len({b.cell() for b in briefs})


def orthogonal_count(briefs: Iterable[ResearchBrief]) -> int:
    """Briefs deliberately framed against the grain (contrarian / adjacent-field).

    R-DISC-02 keeps >=1 live per wave: an ensemble that agrees with itself pays N times for 1x
    recall, and the orthogonal cell is what decorrelates the blind spots.
    """
    return sum(1 for b in briefs if b.framing in ORTHOGONAL_FRAMINGS)
