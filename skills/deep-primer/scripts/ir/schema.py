"""Typed models (pydantic) for document-IR, source-ledger, concept-map, research-plan,
primer-meta per references/artifact-schemas.md. The IR is canonical.

Classification: local-deterministic
Implements: R-PROJ-01

The Document IR is the single source of truth (R-PROJ-01): lints, critics, and the
verifier read it; HTML and the distilled LLM-MD are projections rendered from it. These
models pin the on-disk YAML contracts so the Phase-6/7 checks have a stable shape to read.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


# --- enums (per artifact-schemas.md) -----------------------------------------

class Role(str, Enum):
    """Block role. `recall` is pedagogical (dropped in the llm_md projection)."""

    lede = "lede"
    card = "card"
    summary = "summary"
    body = "body"
    toulmin = "toulmin"
    matrix = "matrix"
    figure = "figure"
    recall = "recall"
    glossary = "glossary"
    further_reading = "further_reading"
    contested = "contested"   # 6b convergence loop: a presented-not-asserted structure (carries framings)


class Mode(str, Enum):
    """Representation mode for multi-view coverage (R-MV-01)."""

    architecture = "architecture"
    tradeoff = "tradeoff"
    failure = "failure"
    benchmark = "benchmark"
    cost = "cost"
    code = "code"
    mental_model = "mental_model"
    historical = "historical"


class Provenance(str, Enum):
    """The G4 grounding axis, surfaced inline in both projections (R-PROJ-05)."""

    verified = "verified"
    inferred = "inferred"
    unverified = "unverified"


class SourceType(str, Enum):
    primary_paper = "primary_paper"
    docs = "docs"
    blog = "blog"
    vendor = "vendor"
    standard = "standard"


class Tier(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EpistemicStatus(str, Enum):
    settled = "settled"
    contested = "contested"
    speculative = "speculative"


class ArtifactKind(str, Enum):
    """The four operational artifacts, kept distinct (R-ART-01). Valid only on role=matrix."""

    decision_matrix = "decision_matrix"
    checklist = "checklist"
    failure_catalog = "failure_catalog"
    decision_aid = "decision_aid"


class CoverageStatus(str, Enum):
    open = "open"
    covered = "covered"
    thin = "thin"


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level, got {type(data).__name__}")
    return data


# --- Document IR (canonical) -------------------------------------------------

class Framing(BaseModel):
    """One cluster centroid a contested-structure block oscillated among (artifact-schemas.md)."""

    model_config = ConfigDict(extra="allow")

    label: str
    summary: str | None = None
    applies_when: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class CardRows(BaseModel):
    """The at-a-glance card's required rows (R-CARD-02).

    `home_anchor` leads by contract — the cross-domain mapping belongs in the card's opening,
    not a footnote (R-XREF-01) — and `skip_when` is mandatory alongside `reach_for_when`
    (R-CARD-03). Typing the rows is what makes those rules mechanically checkable; whether a
    row *activates prior knowledge* rather than teasing the section stays a critic judgment
    (R-CARD-01).
    """

    model_config = ConfigDict(extra="allow")

    idea: str
    home_anchor: str
    whats_new_vs_renamed: str
    reach_for_when: str
    skip_when: str
    key_exemplar: str
    confidence: str


class RecallItem(BaseModel):
    """One check-yourself Q&A. A section carries exactly three (R-RECALL-01), at least one of
    which forces a cross-domain mapping (R-RECALL-02, judged by the critic; the flag is a hint)."""

    model_config = ConfigDict(extra="allow")

    question: str
    answer: str
    cross_domain: bool = False


class Block(BaseModel):
    """A leaf field-guide block. `extra=forbid` turns stray/misspelled keys into errors."""

    model_config = ConfigDict(extra="forbid")

    block_id: str
    role: Role
    text: str | None = None
    concept: str | None = None
    mode: Mode | None = None
    claim_ids: list[str] = Field(default_factory=list)
    provenance: Provenance | None = None
    source_ids: list[str] = Field(default_factory=list)
    caption: str | None = None
    svg_ref: str | None = None
    framings: list[Framing] | None = None   # only on role=contested (6b convergence loop)
    # h4 is a block ATTRIBUTE, not a container: R-ARCH-05 requires h4 to stay out of nav/TOC,
    # and modelling it here makes that invariant structural rather than checked.
    heading: str | None = None
    rows: CardRows | None = None                 # only on role=card (R-CARD-02)
    items: list[RecallItem] | None = None        # only on role=recall (R-RECALL-01)
    artifact_kind: ArtifactKind | None = None    # only on role=matrix (R-ART-01)

    @property
    def readable_text(self) -> str:
        """What this block actually SAYS — the canonical answer, so consumers stop re-deriving it.

        A card's content is its typed rows and a recall block's is its three Q&A items; neither sets
        `text`. `text or caption` therefore renders both as EMPTY, and that mistake has now been made
        twice independently: the critic seam failed R-SUMM-04 on a card for "contains no text", and
        `citation_quality` asked an entailment judge whether a quote supports "" — which it correctly
        answered no, silently costing two of spec-01's seven blocks their citation credit.

        Anything needing a block's prose should call this rather than reaching for `.text` — and
        anything SCANNING that prose for a pattern should call `prose_segments`, which is the same
        content without the labels this adds.
        """
        if self.rows is not None:
            rows = self.rows.model_dump(exclude_none=True)
            return "\n".join(f"{k}: {v}" for k, v in rows.items() if v not in ("", [], {}))
        if self.items:
            return "\n".join(f"Q: {i.question}\nA: {i.answer}" for i in self.items)
        if self.framings:
            # The third composite role, and the one that stayed broken: a contested block's content
            # IS its framings and it sets no `text`, so this fell through and returned "". Its
            # citations were therefore unsupportable (`any([])` is False, so every quote scored as
            # non-supporting), and `run_critics._ir_digest` — which hashes this string — could not
            # see the framings change at all, leaving a frozen critic report credited against a
            # document that had been rewritten underneath it.
            return "\n".join(
                f"framing {f.label}: {f.summary or ''}".rstrip()
                + (f"\napplies when: {f.applies_when}" if f.applies_when else "")
                for f in self.framings)
        return self.text or self.caption or ""

    @property
    def prose_segments(self) -> list[str]:
        """Every span of AUTHORED PROSE in this block, without the structural labels.

        The scanning counterpart to `readable_text`, and deliberately not the same string.
        `readable_text` labels its parts (`idea: ...`) so a judge can see which row it is reading,
        and `run_critics._ir_digest` hashes exactly that — so its shape is pinned by a frozen run
        and cannot be bent to suit a scanner. A scanner must not inherit those labels either: a
        concept canonically termed "confidence" would otherwise read as established in every
        document that contains any card at all.

        Checks that search prose for a pattern — a phantom cross-reference, a footnote marker, a
        term's surface form — must iterate this. Reaching for `.text` is what silently exempted all
        three composite roles, none of which set it.
        """
        if self.rows is not None:
            dumped = self.rows.model_dump(exclude_none=True)
            return [s for s in (str(v).strip() for v in dumped.values()) if s]
        if self.items:
            return [s for i in self.items for s in (i.question.strip(), i.answer.strip()) if s]
        if self.framings:
            return [s for f in self.framings
                    for s in ((f.summary or "").strip(), (f.applies_when or "").strip()) if s]
        return [s for s in ((self.text or "").strip(), (self.caption or "").strip()) if s]

    # Rows that assert something about the WORLD, as opposed to authorial framing. A card's other
    # rows are deliberately not here: `home_anchor` is a cross-domain mapping the author constructs
    # for this reader, `whats_new_vs_renamed` is their synthesis, `reach_for_when` / `skip_when` are
    # operational judgement (R-CARD-03 requires them precisely because no source states them), and
    # `confidence` is an epistemic label. Asking a source quote to entail those is a category error.
    _CLAIM_BEARING_ROWS = ("idea", "key_exemplar")

    @property
    def entailment_units(self) -> list[str]:
        """The units a citation may be asked to support — the fix for composite blocks.

        A card is seven typed rows and R-GROUND-01 caps a quote at 15 words, so no single quote can
        entail the concatenation; every card in spec-01 failed for that structural reason rather
        than because its citation was bad. Scoring against the claim-bearing rows separately asks
        the question the citation can actually answer: does this quote support what the block
        ASSERTS? A block is supported when a cited quote entails any one of these.

        Simple blocks return their prose unchanged, so nothing about them changes.
        """
        if self.rows is not None:
            dumped = self.rows.model_dump(exclude_none=True)
            units = [str(dumped[k]).strip() for k in self._CLAIM_BEARING_ROWS
                     if str(dumped.get(k) or "").strip()]
            return units or [self.readable_text]
        if self.items:
            # a recall item's ANSWER is the assertion; the question is a prompt
            return [i.answer.strip() for i in self.items if i.answer.strip()] or [self.readable_text]
        if self.framings:
            # Presented-not-asserted still puts each framing's summary on the page, and `Framing`
            # carries its own `source_ids` precisely so a school of thought can be attributed. The
            # `applies_when` clause is the author's operational judgement, so it stays out for the
            # same reason a card's `reach_for_when` does.
            return [s for f in self.framings if (s := (f.summary or "").strip())]
        return [self.readable_text] if self.readable_text else []


class Subsection(BaseModel):
    """An h3 subsection. Carries exactly one sub-sum — a `summary` block — per R-SUMM-02 /
    R-CONSIST-01; the check lives in checks/structure_coverage.py."""

    model_config = ConfigDict(extra="forbid")

    block_id: str
    title: str
    concept: str | None = None
    blocks: list[Block] = Field(default_factory=list)


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    title: str
    concept: str | None = None
    blocks: list[Block] = Field(default_factory=list)
    subsections: list[Subsection] = Field(default_factory=list)
    # Which entry of a user-supplied structure this section realizes (R-ARCH-07). Declaring the
    # mapping is what lets the heading be a predictive claim (R-SCENT-01) instead of the user's
    # label copied verbatim — the two rules would otherwise collide.
    maps_to: str | None = None

    def all_blocks(self) -> list[Block]:
        """This section's own blocks followed by its subsections', in document order."""
        return [*self.blocks, *(b for sub in self.subsections for b in sub.blocks)]


class IRMeta(BaseModel):
    """The IR meta blob: {parameters, ledger_snapshot, model_versions, generated_at}."""

    model_config = ConfigDict(extra="allow")

    parameters: dict[str, Any] = Field(default_factory=dict)
    ledger_snapshot: list[str] = Field(default_factory=list)
    model_versions: dict[str, Any] = Field(default_factory=dict)
    generated_at: str | None = None


class DocumentIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: IRMeta = Field(default_factory=IRMeta)
    sections: list[Section] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> DocumentIR:
        return cls(**_read_yaml(path))

    def flatten_blocks(self) -> list[Block]:
        """All leaf blocks in document order, recursing into subsections (the round-trip /
        projection unit). Every consumer — lints, both renderers, verify, critics — reads the
        document through this method, so subsection content is visible everywhere by construction."""
        return [b for sec in self.sections for b in sec.all_blocks()]

    def all_block_ids(self) -> list[str]:
        """Every block_id in the document — section and subsection containers *and* leaf blocks."""
        ids: list[str] = []
        for sec in self.sections:
            ids.append(sec.block_id)
            ids.extend(b.block_id for b in sec.blocks)
            for sub in sec.subsections:
                ids.append(sub.block_id)
                ids.extend(b.block_id for b in sub.blocks)
        return ids


# --- source-ledger (the grounding substrate) ---------------------------------

class Claim(BaseModel):
    model_config = ConfigDict(extra="allow")

    claim_id: str
    text: str
    quote: str | None = None
    location: str | None = None
    confidence: Tier | None = None
    contested: bool = False
    contradicts: list[str] = Field(default_factory=list)
    # grounding-loop fields (populated in Prompt 6; only need to exist on the model now)
    corroboration_count: int | None = None
    corroborated_by: list[str] = Field(default_factory=list)   # other source_ids supporting this claim
    as_of_date: date | None = None                             # version/SOTA claims: when verified current
    provenance_origin: Literal["discovered", "user"] = "discovered"  # user = a seed_source (R-DISC-06)


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: str
    url: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    date: str | None = None
    type: SourceType | None = None
    credibility: Tier | None = None
    provenance_origin: Literal["discovered", "user"] = "discovered"  # user = a seed_source (R-DISC-06)
    retrieved_at: str | None = None
    content_hash: str | None = None
    claims: list[Claim] = Field(default_factory=list)


class SourceLedger(BaseModel):
    model_config = ConfigDict(extra="allow")

    sources: list[Source] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> SourceLedger:
        return cls(**_read_yaml(path))

    def claim_ids(self) -> set[str]:
        return {c.claim_id for s in self.sources for c in s.claims}

    def source_ids(self) -> set[str]:
        return {s.source_id for s in self.sources}


# --- concept-map (the coverage substrate) ------------------------------------

class RepresentationMode(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: Mode
    block_ref: str | None = None


class Concept(BaseModel):
    model_config = ConfigDict(extra="allow")

    concept_id: str
    canonical_term: str
    aliases: list[str] = Field(default_factory=list)
    home_anchor: str | None = None
    fidelity_boundary: str | None = None
    epistemic_status: EpistemicStatus | None = None
    salience: float | None = None
    representation_modes: list[RepresentationMode] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class ConceptMap(BaseModel):
    model_config = ConfigDict(extra="allow")

    concepts: list[Concept] = Field(default_factory=list)
    cycle: int | None = None        # concept-map-vK.yaml: the convergence cycle K (R-CONV)
    contested: bool = False         # true when the structure is presented, not asserted (see Role.contested)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ConceptMap:
        return cls(**_read_yaml(path))

    def concept_ids(self) -> set[str]:
        return {c.concept_id for c in self.concepts}


# --- research-plan -----------------------------------------------------------

class Coverage(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: CoverageStatus = CoverageStatus.open
    sources: list[str] = Field(default_factory=list)
    independent_nonvendor: int = 0
    iterations: int = 0


class Question(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    perspective: str | None = None
    text: str
    target_sections: list[str] = Field(default_factory=list)
    serves_rules: list[str] = Field(default_factory=list)
    budget_weight: float = 1.0
    merged_from: list[str] = Field(default_factory=list)
    sub_questions: list[str] = Field(default_factory=list)
    coverage: Coverage = Field(default_factory=Coverage)


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    topic: str
    parameters_ref: str | None = None
    perspectives_used: list[str] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ResearchPlan:
        return cls(**_read_yaml(path))


# --- discovery campaign (Phase 1a — the recall layer) ------------------------
# Discovery output enters the pipeline as LEADS ONLY (R-DISC-01): an accepted topic-lead becomes a
# research-plan question, an accepted source-lead becomes a fetch candidate. Nothing here is
# evidence — the grounding loop re-fetches and quotes independently.

class ResearchBrief(BaseModel):
    """One deep-research run. Its position in the diversity matrix is what R-DISC-02 counts."""

    model_config = ConfigDict(extra="allow")

    wave: str
    framing: str
    angle: str | None = None
    source_class: str | None = None
    stance: str | None = None
    questions: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    brief_id: str | None = None
    seed_ref: str | None = None          # set on a seed-anchored brief (R-DISC-06)

    def cell(self) -> tuple[str, str | None, str | None, str | None]:
        """This brief's cell in the diversity matrix (framing x angle x source_class x stance)."""
        return (self.framing, self.angle, self.source_class, self.stance)


class Lead(BaseModel):
    """Fields shared by topic- and source-leads."""

    model_config = ConfigDict(extra="allow")

    id: str
    support_count: int = 0               # DISTINCT framings that surfaced it (cross-run corroboration)
    novelty: float | None = None
    salience: str | None = None          # model-judged (R-DISC-04)
    status: Literal["accepted", "flagged", "dropped"] = "accepted"
    provenance_origin: Literal["discovered", "user"] = "discovered"
    surfaced_by: list[str] = Field(default_factory=list)   # framings / brief ids
    report_ids: list[str] = Field(default_factory=list)    # snapshot linkage (R-DISC-05)


class TopicLead(Lead):
    concept: str
    why: str | None = None


class SourceLead(Lead):
    url: str
    type: str | None = None
    supports: list[str] = Field(default_factory=list)      # topic-lead ids this source serves


class DiscoveryLeads(BaseModel):
    model_config = ConfigDict(extra="allow")

    topic_leads: list[TopicLead] = Field(default_factory=list)
    source_leads: list[SourceLead] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> DiscoveryLeads:
        return cls(**_read_yaml(path))

    def all_leads(self) -> list[Lead]:
        return [*self.topic_leads, *self.source_leads]

    def accepted(self) -> list[Lead]:
        return [lead for lead in self.all_leads() if lead.status == "accepted"]


class WaveRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    wave: str
    briefs: int
    framing_cells: int
    leads_total: int
    leads_new: int
    novel_fraction: float
    decision: Literal["continue", "stop"]


class DiscoveryLog(BaseModel):
    """Per-wave audit + saturation trail — the evidence R-DISC-03's lint reads."""

    model_config = ConfigDict(extra="allow")

    max_waves: int
    saturation_threshold: float
    waves: list[WaveRecord] = Field(default_factory=list)
    # `no_leads` is a THIRD outcome, not a flavour of saturation. A wave returning nothing makes
    # novel_fraction a 0/0 that used to be reported as 0.0 — below any threshold — so a dead
    # research backend stopped the campaign on wave A, froze an empty snapshot, and labelled it
    # `saturated`: the most reassuring possible word for a total retrieval outage.
    terminal: Literal["saturated", "max_waves", "no_leads"] | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> DiscoveryLog:
        return cls(**_read_yaml(path))


# --- convergence guard (the escalate loop) -----------------------------------

class CycleRecord(BaseModel):
    """One cycle of the drafting<->structure loop. `c_k` is the structural distance from the
    previous cycle's map, `rho` the ratio c_k / c_(k-1), `tau` the threshold in force."""

    model_config = ConfigDict(extra="allow")

    cycle: int
    c_k: float | None = None
    rho: float | None = None
    tau: float
    finding: str
    decision: Literal["draft", "deepen", "escalate", "stop"]


class ConvergenceLog(BaseModel):
    """The audit trail R-CONV-01's lint reads: did the loop terminate, and in what regime."""

    model_config = ConfigDict(extra="allow")

    k_max: int
    cycles: list[CycleRecord] = Field(default_factory=list)
    terminal_regime: Literal["converged", "contested", "chaotic", "coherent"] | None = None
    terminal_decision: str | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> ConvergenceLog:
        return cls(**_read_yaml(path))


# --- primer-meta (the HTML-embedded JSON, Phase 3 rendering) -----------------

class PrimerMeta(BaseModel):
    """The `<script id="primer-meta">` blob embedded in the rendered HTML."""

    model_config = ConfigDict(extra="allow")

    parameters: dict[str, Any] = Field(default_factory=dict)
    ledger_snapshot: list[str] = Field(default_factory=list)
    concept_map: list[dict[str, Any]] = Field(default_factory=list)
    lint_report: dict[str, Any] = Field(default_factory=dict)
    model_versions: dict[str, Any] = Field(default_factory=dict)
    generated_at: str | None = None
