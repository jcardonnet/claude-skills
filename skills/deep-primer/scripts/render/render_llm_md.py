"""IR -> operationally-distilled Markdown projection.

Classification: local-deterministic
Implements: R-PROJ-03 (role_filter), R-PROJ-04 (de-anaphorize producer), R-PROJ-05 (provenance
            inline), R-PROJ-06 (drop SVG, keep captions)

A projection of the canonical IR, not a second document. Keeps the operational core and drops the
only pedagogical role (recall) — so the block-id set is the HTML's minus the recall blocks, which
is exactly what check_alignment expects. Each kept block is rewritten self-contained
(de-anaphorized) and carries its provenance + sources inline. Output: a YAML front-matter index
(the concept-map as glossary) then one `## [block: <id>]` section per kept block.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Block, ConceptMap, DocumentIR  # noqa: E402

DROPPED_ROLES = {"recall"}  # the only role removed by the filter -> the alignment diff (R-PROJ-02/03)

_ANAPHOR_LEAD = re.compile(r"^(This|That|These|Those|It|They|Such)\b", re.IGNORECASE)
_CROSSREF = re.compile(
    r"\((?:see|cf\.?)[^)]*\)"
    r"|\bas (?:shown|seen|noted|described|discussed|mentioned) (?:above|below|earlier|later|previously)\b"
    r"|\bsee (?:above|below|figure\s+\d+|section\s+[\w.]+)\b",
    re.IGNORECASE,
)


def deanaphorize(text: str, referent: str | None) -> str:
    """R-PROJ-04 producer: strip cross-block references and restate a leading bare anaphor.

    Best-effort and deterministic — the verifier (verify/chunk_selfcontained.py) checks the result.
    """
    if not text:
        return ""
    out = _CROSSREF.sub("", text)
    if referent:
        out = _ANAPHOR_LEAD.sub(referent, out, count=1)
    out = re.sub(r"\s{2,}", " ", out).replace(" ,", ",").replace(" .", ".").strip()
    return out


def kept_blocks(ir: DocumentIR):
    """Yield (section, block) for every block the role filter keeps (everything but recall)."""
    for sec in ir.sections:
        for b in sec.blocks:
            if b.role.value not in DROPPED_ROLES:
                yield sec, b


def _referent_map(concept_map: ConceptMap | None) -> dict[str, str]:
    return {c.concept_id: c.canonical_term for c in concept_map.concepts} if concept_map else {}


def _sources_line(b: Block) -> str:
    if b.source_ids:
        return f"Sources: [{', '.join(b.source_ids)}]"
    if b.provenance and b.provenance.value == "unverified":
        return "Sources: [unverified]"
    return "Sources: [none yet — inferred]"


def _distill(sec, b: Block, referents: dict[str, str]) -> str:
    referent = referents.get(b.concept or sec.concept or "", None) or sec.title.split(",")[0]
    head = (f"## [block: {b.block_id}]   concept: {b.concept or sec.concept or '-'}   "
            f"mode: {b.mode.value if b.mode else '-'}   provenance: {b.provenance.value if b.provenance else '-'}")
    if b.role.value == "figure":
        body = f"Figure: {b.caption or ''}".rstrip()          # R-PROJ-06: caption only, SVG dropped
    else:
        body = f"Claim: {deanaphorize(b.text or '', referent)}"
    return f"{head}\n{body}\n{_sources_line(b)}"


def _front_matter(ir: DocumentIR, concept_map: ConceptMap | None) -> str:
    if concept_map:
        concepts = [{"id": c.concept_id, "canonical_term": c.canonical_term, "aliases": c.aliases,
                     "home_anchor": c.home_anchor, "fidelity_boundary": c.fidelity_boundary}
                    for c in concept_map.concepts]
    else:
        seen, concepts = set(), []
        for _, b in kept_blocks(ir):
            if b.concept and b.concept not in seen:
                seen.add(b.concept)
                concepts.append({"id": b.concept, "canonical_term": b.concept})
    fm = {
        "title": ir.sections[0].title if ir.sections else "Primer",
        "generated_at": ir.meta.generated_at,
        "concepts": concepts,
    }
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip() + "\n---"


def render_llm_md(ir: DocumentIR, concept_map: ConceptMap | None = None) -> str:
    referents = _referent_map(concept_map)
    chunks = [_distill(sec, b, referents) for sec, b in kept_blocks(ir)]
    return _front_matter(ir, concept_map) + "\n\n" + "\n\n".join(chunks) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render a document-ir.yaml to the distilled LLM-MD projection.")
    ap.add_argument("ir")
    ap.add_argument("--concept-map", dest="concept_map")
    ap.add_argument("--out", default="primer.llm.md")
    args = ap.parse_args(argv)
    ir = DocumentIR.from_yaml(args.ir)
    cm = ConceptMap.from_yaml(args.concept_map) if args.concept_map else None
    Path(args.out).write_text(render_llm_md(ir, cm), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
