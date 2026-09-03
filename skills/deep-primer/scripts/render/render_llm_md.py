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

    The scope-and-decisions front matter (R-ARCH-01) is yielded first with `sec=None` — it renders
    into the HTML, so omitting it here would break that same alignment.
    """
    for b in ir.front_matter:
        if b.role.value not in DROPPED_ROLES:
            yield None, b
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
        body = "\n".join(f"{label}: {prose}" for label, prose in _framing_md_parts(f, referent))
        srcs = f"Sources: [{', '.join(f.source_ids)}]" if f.source_ids else "Sources: [none yet — inferred]"
        chunks.append(
            f"## [block: {b.block_id}]   framing: {f.label}   provenance: {prov}\n{body}\n{srcs}"
        )
    return "\n\n".join(chunks)


def referent_for(sec, b: Block, referents: dict[str, str]) -> str:
    """The canonical term a bare anaphor in this block resolves to — the block's own concept, else
    its container's, else the section title's head noun. One definition so the verifier resolves the
    same referent the producer used.

    Front matter has no container (`sec is None`) and therefore no fallback referent: it precedes
    every concept the document establishes. `deanaphorize` then leaves a leading anaphor standing
    rather than substituting a wrong one, and verify/chunk_selfcontained.py reports it — the honest
    outcome for prose that opens a document by pointing back at something.
    """
    named = referents.get(b.concept or (sec.concept if sec is not None else None) or "")
    return named or (sec.title.split(",")[0] if sec is not None else "")


def _framing_md_parts(f, referent: str) -> list[tuple[str, str]]:
    """(label, prose) pairs a contested framing contributes. Shared by the renderer and the verifier
    so a change to one cannot leave the other checking something else.

    `applies_when` is here because the projection EMITS it. It used to be interpolated raw — the one
    span in a contested block that never passed through `deanaphorize` — while `distilled_segments`
    excluded it, so R-PROJ-04 could not see the only part of the block that actually leaks a
    dangling reference. Rendered un-repaired and verified not at all.
    """
    parts = [("Framing", deanaphorize(f.summary or "", referent))]
    if (f.applies_when or "").strip():
        parts.append(("Reach-for-it-when", deanaphorize(f.applies_when, referent)))
    return [(label, prose) for label, prose in parts if prose.strip()]


def _card_md_parts(b: Block, referent: str) -> list[tuple[str, str]]:
    """R-PROJ-03: keep the card's information content, drop the advance-organizer *hook*.

    The home-domain analogue is pedagogy for a human reader, so it is demoted rather than kept as
    the opener; what survives is the operational core — the idea, what is genuinely new, and the
    reach-for/skip pair, which is decision content an LLM needs.

    Returned as (label, prose) pairs rather than finished lines so `distilled_segments` can hand the
    verifier the PROSE alone. Checking the labelled blob would defeat the check it feeds: a leading
    anaphor is anchored at `^`, and `Claim: This bounds recall` does not start with `This`.
    """
    r = b.rows
    if r is None:
        return [("Claim", deanaphorize(b.text or "", referent))]
    parts = [("Claim", deanaphorize(r.idea, referent))]
    if (r.whats_new_vs_renamed or "").strip():
        parts.append(("New-vs-renamed", deanaphorize(r.whats_new_vs_renamed, referent)))
    parts.append(("Reach-for-it-when", deanaphorize(r.reach_for_when, referent)))
    parts.append(("Skip-it-when", deanaphorize(r.skip_when, referent)))
    if (r.confidence or "").strip():
        parts.append(("Confidence", r.confidence))
    return parts


def _distill_card(b: Block, referent: str) -> str:
    return "\n".join(f"{label}: {prose}" for label, prose in _card_md_parts(b, referent))


def distilled_segments(sec, b: Block, referents: dict[str, str]) -> list[str]:
    """Each span of prose this projection emits for `b`, de-anaphorized, without its label.

    The single definition of "what the LLM-MD says about this block". `verify/chunk_selfcontained.py`
    reads it rather than re-deriving the answer from `b.text`, which is the mistake that made
    R-PROJ-04 unfalsifiable: a card sets no `text`, so the verifier inspected the empty string —
    finding no dangling anaphora in it (the check could not fail) while asking an entailment judge
    whether "" supports the block's citation (it could not pass).
    """
    referent = referent_for(sec, b, referents)
    role = b.role.value
    if role == "contested":
        return [prose for f in (b.framings or [])
                for _label, prose in _framing_md_parts(f, referent)]
    if role == "figure":
        return [s] if (s := deanaphorize(b.caption or "", referent)) else []
    if role == "card":
        return [prose for _, prose in _card_md_parts(b, referent) if prose.strip()]
    return [s] if (s := deanaphorize(b.text or "", referent)) else []


def _distill(sec, b: Block, referents: dict[str, str]) -> str:
    referent = referent_for(sec, b, referents)
    if b.role.value == "contested":
        return _distill_contested(b, referent)
    sec_concept = sec.concept if sec is not None else None
    head = (f"## [block: {b.block_id}]   concept: {b.concept or sec_concept or '-'}   "
            f"mode: {b.mode.value if b.mode else '-'}   provenance: {b.provenance.value if b.provenance else '-'}")
    if b.artifact_kind:
        head += f"   artifact: {b.artifact_kind.value}"
    if b.role.value == "figure":
        # R-PROJ-06: caption only, SVG dropped. De-anaphorized like every other chunk — a caption
        # opening "This shows the layered graph" is exactly the dangling reference R-PROJ-04 exists
        # to remove, and the verifier was already de-anaphorizing it before comparing.
        body = f"Figure: {deanaphorize(b.caption or '', referent)}".rstrip()
    elif b.role.value == "card":
        body = _distill_card(b, referent)
    else:
        body = f"Claim: {deanaphorize(b.text or '', referent)}"
    return f"{head}\n{body}\n{_sources_line(b)}"


def _yaml_index(ir: DocumentIR, concept_map: ConceptMap | None) -> str:
    """The projection's YAML header (the concept-map as a glossary).

    Named for what it is rather than "front matter": `DocumentIR.front_matter` is the
    scope-and-decisions PROSE (R-ARCH-01), which reaches this projection as ordinary `## [block:]`
    chunks. Two unrelated things under one name is how a renderer starts emitting one for the other.
    """
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
    return _yaml_index(ir, concept_map) + "\n\n" + "\n\n".join(chunks) + "\n"


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
    # Compare against the caption AS PROJECTED, not the raw one. Captions are de-anaphorized like
    # every other chunk — a caption opening "This shows the layered graph" is exactly the dangling
    # reference R-PROJ-04 exists to remove — so a raw-substring test reports "caption dropped" for
    # any caption the repair actually touched: a false failure, and one that would push an author to
    # write captions the repair leaves alone.
    referents = _referent_map(None)
    for sec, b in kept_blocks(ir):
        if b.role.value != "figure" or not b.caption:
            continue
        if not any(seg and seg in md for seg in distilled_segments(sec, b, referents)):
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
