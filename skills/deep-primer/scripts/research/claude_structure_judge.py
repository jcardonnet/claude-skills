"""A real `StructureJudge` for the convergence guard — the third and last model seam.

Classification: agent-orchestrated (model call — NOT hermetic)
Implements: the judged half of R-CONV-02; makes R-CONV-01 reachable with a real log

Why this exists
---------------
`run_convergence_loop` has always taken a `StructureJudge`, and the only implementation in the tree
was `ScriptedStructureJudge` — a replay of pre-written findings. So R-CONV-01 ("the drafting loop
reaches a valid terminal state") could only ever be exercised against a judge that was told the
answer in advance. Producing a convergence log that way and calling the rule covered would be the
stub-critic problem again: a green artifact from a judge that never looked.

The division of labour is R-CONV-02, verbatim
---------------------------------------------
"Deciding whether a finding is structural and what concept-map edits it implies is model-judged;
computing structural distance, the tau schedule and convergence classification is deterministic."

So the model does exactly two things, and neither of them is arithmetic:

  - `scan_for_structural` asks whether the map has a STRUCTURAL problem (a concept in the wrong
    place, two concepts that are really one, a missing bridge) as opposed to one that merely wants a
    section deepened. That is a judgement, and it is the one the loop branches on.
  - `implied_edits` asks WHICH edit the finding implies — named as an operation over concept ids,
    never as a rewritten map. The model chooses `merge c1 into c2`; this module applies it. Letting
    a model emit a whole ConceptMap would hand it the deterministic half too, and silently make
    `Delta_struct` a function of how verbose the model felt.

`convergence.py` stays pure and untouched; `checks/conformance.py` enforces that mechanically.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ir.schema import Concept, ConceptMap
from utils.claude_cli import ClaudeCli, CliUnavailable

_SCAN = """\
You are auditing the CONCEPT MAP of a technical primer for STRUCTURAL problems.

A structural finding changes how concepts are organised: two entries that are really one concept,
one entry that is really two, a concept sitting under the wrong parent, or a missing bridge concept
the others depend on. It is NOT a structural finding that a section could be longer, better
explained, better sourced, or have more examples — those are depth findings, and they are out of
scope here.

Target domain: {domain}

CONCEPT MAP ({n} concepts):
{concepts}

Return RAW JSON and nothing else, no markdown fence:
{{"structural": true | false,
  "kind": "merge" | "split" | "rename" | "none",
  "concept_ids": ["<the ids involved, [] if none>"],
  "finding": "<one sentence; empty if structural is false>"}}

Be conservative. Most maps are structurally fine, and a false structural finding costs a whole
re-grounding cycle. If you are not confident, return structural=false.
"""


def _render(cmap: ConceptMap) -> str:
    return "\n".join(
        f"- {c.concept_id}: {c.canonical_term}"
        + (f" (aliases: {', '.join(c.aliases)})" if c.aliases else "")
        + (f" [salience {c.salience:.2f}]" if c.salience is not None else "")
        for c in cmap.concepts) or "(empty)"


def _merge(cmap: ConceptMap, ids: list[str]) -> ConceptMap:
    """Fold later concepts into the first named one. Deterministic: union the evidence, keep the
    survivor's identity, preserve the original ordering of everything untouched."""
    keep, folded = ids[0], set(ids[1:])
    out: list[Concept] = []
    for c in cmap.concepts:
        if c.concept_id in folded:
            continue
        if c.concept_id == keep:
            merged = c.model_copy(deep=True)
            for other in cmap.concepts:
                if other.concept_id in folded:
                    merged.aliases = sorted({*merged.aliases, other.canonical_term, *other.aliases})
                    merged.claim_ids = sorted({*merged.claim_ids, *other.claim_ids})
                    merged.source_ids = sorted({*merged.source_ids, *other.source_ids})
            out.append(merged)
        else:
            out.append(c)
    return ConceptMap(concepts=out)


def _split(cmap: ConceptMap, ids: list[str]) -> ConceptMap:
    """Separate a concept's aliases into a sibling. The model says WHICH concept is overloaded; the
    split itself is mechanical, so Delta_struct stays a function of the map, not of phrasing."""
    out: list[Concept] = []
    for c in cmap.concepts:
        out.append(c)
        if c.concept_id in ids and c.aliases:
            spun = c.model_copy(deep=True)
            spun.concept_id = f"{c.concept_id}-b"
            spun.canonical_term = c.aliases[0]
            spun.aliases = []
            spun.claim_ids = []
            out.append(spun)
    return ConceptMap(concepts=out)


@dataclass
class ClaudeStructureJudge:
    """A `StructureJudge` backed by the local `claude` CLI."""

    params: dict = field(default_factory=dict)
    cli: ClaudeCli | None = None
    model: str = "haiku"
    cost_cap_usd: float = 3.0

    scans: list[dict] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.cli = self.cli or ClaudeCli(model=self.model, cost_cap_usd=self.cost_cap_usd)

    @property
    def calls(self) -> int:
        return self.cli.calls

    @property
    def spend_usd(self) -> float:
        return self.cli.spend_usd

    def scan_for_structural(self, concept_map: ConceptMap, params: dict) -> dict | None:
        domain = (params or self.params).get("target_domain", "the target domain")
        try:
            payload = self.cli.result_json(_SCAN.format(
                domain=domain, n=len(concept_map.concepts), concepts=_render(concept_map)))
        except (CliUnavailable, ValueError) as exc:
            # An unreachable judge means "no structural finding observed", which settles the loop.
            # Inventing one would trigger a re-grounding cycle on the strength of an outage.
            self.scans.append({"error": f"{type(exc).__name__}: {exc}"[:160]})
            return None

        self.scans.append(payload)
        known = {c.concept_id for c in concept_map.concepts}
        ids = [i for i in (payload.get("concept_ids") or []) if i in known]
        kind = str(payload.get("kind") or "none").lower()
        if not payload.get("structural") or kind not in ("merge", "split", "rename") or not ids:
            return None
        if kind == "merge" and len(ids) < 2:
            return None      # a merge naming one concept is not an edit
        return {"kind": kind, "concept_ids": ids, "finding": str(payload.get("finding", ""))[:300]}

    def implied_edits(self, finding: dict, concept_map: ConceptMap) -> ConceptMap:
        kind, ids = finding.get("kind"), finding.get("concept_ids") or []
        if kind == "merge" and len(ids) >= 2:
            return _merge(concept_map, ids)
        if kind == "split" and ids:
            return _split(concept_map, ids)
        if kind == "rename" and ids:
            out = []
            for c in concept_map.concepts:
                if c.concept_id == ids[0]:
                    renamed = c.model_copy(deep=True)
                    renamed.aliases = sorted({*renamed.aliases, renamed.canonical_term})
                    renamed.canonical_term = (finding.get("finding") or renamed.canonical_term)[:60]
                    out.append(renamed)
                else:
                    out.append(c)
            return ConceptMap(concepts=out)
        return concept_map
