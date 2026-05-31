"""Typed models (pydantic) for document-IR, source-ledger, concept-map, research-plan,
primer-meta per references/artifact-schemas.md. The IR is canonical.

Classification: local-deterministic
Implements: R-PROJ-01

The Document IR is the single source of truth (R-PROJ-01): lints, critics, and the
verifier read it; HTML and the distilled LLM-MD are projections rendered from it. These
models pin the on-disk YAML contracts so the Phase-6/7 checks have a stable shape to read.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

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


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    title: str
    concept: str | None = None
    blocks: list[Block] = Field(default_factory=list)


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
        """All leaf blocks in document order (the round-trip / projection unit)."""
        return [b for sec in self.sections for b in sec.blocks]

    def all_block_ids(self) -> list[str]:
        """Every block_id in the document — section containers *and* leaf blocks."""
        ids: list[str] = []
        for sec in self.sections:
            ids.append(sec.block_id)
            ids.extend(b.block_id for b in sec.blocks)
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
