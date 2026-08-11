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

# The projection's block heading. Defined here because this module owns the MD format;
# check_alignment imports it rather than keeping a second copy that can drift.
MD_BLOCK_RE = re.compile(r"^##\s*\[block:\s*([\w-]+)\]", re.MULTILINE)

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
    """Yield (section, block) for every block the role filter keeps (everything but recall).

    Recurses into subsections via Section.all_blocks(): a subsection block that rendered into the
    HTML but never reached the MD would break block-id alignment (R-PROJ-02).
    """
    for sec in ir.sections:
        for b in sec.all_blocks():
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


def _distill_contested(b: Block, referent: str) -> str:
    """A contested-structure block is operational (kept): one `## [block: <id>]` per framing,
    each carrying provenance (R-PROJ-05). All share the block-id so they resolve in the HTML."""
    prov = b.provenance.value if b.provenance else "-"
    chunks = []
    for f in b.framings or []:
        applies = f"\nReach-for-it-when: {f.applies_when}" if f.applies_when else ""
        srcs = f"Sources: [{', '.join(f.source_ids)}]" if f.source_ids else "Sources: [none yet — inferred]"
        chunks.append(
            f"## [block: {b.block_id}]   framing: {f.label}   provenance: {prov}\n"
            f"Framing: {deanaphorize(f.summary or '', referent)}{applies}\n{srcs}"
        )
    return "\n\n".join(chunks)


def _distill_card(b: Block, referent: str) -> str:
    """R-PROJ-03: keep the card's information content, drop the advance-organizer *hook*.

    The home-domain analogue is pedagogy for a human reader, so it is demoted rather than kept as
    the opener; what survives is the operational core — the idea, what is genuinely new, and the
    reach-for/skip pair, which is decision content an LLM needs.
    """
    r = b.rows
    if r is None:
        return f"Claim: {deanaphorize(b.text or '', referent)}"
    lines = [f"Claim: {deanaphorize(r.idea, referent)}"]
    if (r.whats_new_vs_renamed or "").strip():
        lines.append(f"New-vs-renamed: {deanaphorize(r.whats_new_vs_renamed, referent)}")
    lines.append(f"Reach-for-it-when: {deanaphorize(r.reach_for_when, referent)}")
    lines.append(f"Skip-it-when: {deanaphorize(r.skip_when, referent)}")
    if (r.confidence or "").strip():
        lines.append(f"Confidence: {r.confidence}")
    return "\n".join(lines)


def _distill(sec, b: Block, referents: dict[str, str]) -> str:
    referent = referents.get(b.concept or sec.concept or "", None) or sec.title.split(",")[0]
    if b.role.value == "contested":
        return _distill_contested(b, referent)
    head = (f"## [block: {b.block_id}]   concept: {b.concept or sec.concept or '-'}   "
            f"mode: {b.mode.value if b.mode else '-'}   provenance: {b.provenance.value if b.provenance else '-'}")
    if b.artifact_kind:
        head += f"   artifact: {b.artifact_kind.value}"
    if b.role.value == "figure":
        body = f"Figure: {b.caption or ''}".rstrip()          # R-PROJ-06: caption only, SVG dropped
    elif b.role.value == "card":
        body = _distill_card(b, referent)
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


# --- the `llm_md` pass: deterministic checks over the rendered projection -----
# Artifact shape is (markdown, DocumentIR): the roles a block-id belongs to live in the IR, so a
# projection check needs both halves to say anything stronger than "grep for <svg>".

def role_filter(artifact) -> list[str]:
    """R-PROJ-03: the distilled projection drops pedagogy and keeps the operational core."""
    md, ir = artifact
    problems: list[str] = []
    present = set(MD_BLOCK_RE.findall(md))

    leaked = sorted({b.block_id for b in ir.flatten_blocks()
                     if b.role.value in DROPPED_ROLES} & present)
    for bid in leaked:
        problems.append(f"{bid}: role={'/'.join(sorted(DROPPED_ROLES))} block survived the filter")

    # cards must arrive distilled to their information content, not copied verbatim
    for b in ir.flatten_blocks():
        if b.role.value != "card" or b.block_id not in present:
            continue
        chunk = md.split(f"[block: {b.block_id}]", 1)[1].split("## [block:", 1)[0]
        if "Skip-it-when:" not in chunk and b.rows is not None:
            problems.append(f"{b.block_id}: card kept in the md without its distilled decision content")
    return problems


def no_svg(artifact) -> list[str]:
    """R-PROJ-06: SVG markup is dropped, the complete-claim caption is kept as text."""
    md, ir = artifact
    problems: list[str] = []
    if "<svg" in md.lower():
        problems.append("SVG markup present in the llm_md projection (token noise, R-PROJ-06)")
    for b in ir.flatten_blocks():
        if b.role.value == "figure" and b.caption and b.caption not in md:
            problems.append(f"{b.block_id}: figure caption dropped from the md projection")
    return problems


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
