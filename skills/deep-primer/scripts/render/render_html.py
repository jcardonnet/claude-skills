"""IR -> HTML projection.

Classification: local-deterministic
Implements: R-PROJ-01 (HTML is a rendering of the canonical IR), R-PROJ-05 (provenance inline),
            R-FIG-04 (figure a11y), R-CONSIST-02 (block ids + primer-meta)

Renders the IR onto assets/primer-template.html: every block carries data-block-id / -role /
-concept / -mode / -tierlevel; claim blocks show provenance inline; source citations become
numbered footnotes -> a References section; #primer-meta carries the reproducibility snapshot.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Block, ConceptMap, DocumentIR, Section  # noqa: E402

TEMPLATE = Path(__file__).resolve().parents[2] / "assets" / "primer-template.html"

# block role -> depth tier (1 = shallowest/always-on; 5 = deepest)
_TIER = {"lede": 1, "card": 1, "summary": 2, "toulmin": 2, "matrix": 2,
         "body": 3, "figure": 3, "glossary": 4, "further_reading": 4, "recall": 4}


def _esc(s: str | None) -> str:
    return html.escape(s or "")


def _data_attrs(b: Block) -> str:
    a = [f'data-block-id="{_esc(b.block_id)}"', f'data-role="{b.role.value}"',
         f'data-tierlevel="{_TIER.get(b.role.value, 3)}"']
    if b.concept:
        a.append(f'data-concept="{_esc(b.concept)}"')
    if b.mode:
        a.append(f'data-mode="{b.mode.value}"')
    if b.provenance:
        a.append(f'data-provenance="{b.provenance.value}"')
    if b.claim_ids:
        a.append(f'data-claim-ids="{_esc(",".join(b.claim_ids))}"')
    if b.source_ids:
        a.append(f'data-source-ids="{_esc(",".join(b.source_ids))}"')
    if b.svg_ref:
        a.append(f'data-svg-ref="{_esc(b.svg_ref)}"')
    return " ".join(a)


def _prov_span(b: Block) -> str:
    if not b.provenance:
        return ""
    return f'<span class="prov prov-{b.provenance.value}">{b.provenance.value}</span>'


def _placeholder_svg() -> str:
    # theme-aware (CSS vars survive dark mode); decorative — the <figure> carries role=img + aria-label
    return ('<svg viewBox="0 0 320 120" aria-hidden="true">'
            '<rect class="fill" x="12" y="24" width="120" height="64" rx="6"/>'
            '<line class="accent" x1="132" y1="56" x2="300" y2="56"/>'
            '<text x="24" y="60">schematic</text></svg>')


def _footnote_sup_ids(source_ids, fn_index: dict[str, int]) -> str:
    sups = []
    for sid in source_ids:
        n = fn_index.setdefault(sid, len(fn_index) + 1)
        sups.append(f'<sup class="fn">[{n}]</sup>')
    return "".join(sups)


def _footnote_sup(b: Block, fn_index: dict[str, int]) -> str:
    return _footnote_sup_ids(b.source_ids, fn_index)


def _contested_html(b: Block, attrs: str, fn_index: dict[str, int]) -> str:
    """Render a contested-structure block: each framing as a comparison panel (reuses the
    tradeoff/Toulmin path). The competing-views banner is document-level (see render_html)."""
    panels = []
    for f in b.framings or []:
        applies = f'<p class="applies-when">Reach for it when: {_esc(f.applies_when)}</p>' if f.applies_when else ""
        panels.append(
            f'<div class="toulmin framing"><strong>{_esc(f.label)}</strong>'
            f'<p>{_esc(f.summary)}</p>{applies}{_footnote_sup_ids(f.source_ids, fn_index)}</div>'
        )
    return (f'<div class="contested" {attrs} role="group" aria-label="competing organizing views">'
            f'<p class="contested-note">Competing organizing views — presented, not asserted.{_prov_span(b)}</p>'
            f'{"".join(panels)}</div>')


def _block_html(b: Block, fn_index: dict[str, int]) -> str:
    attrs = _data_attrs(b)
    if b.role.value == "figure":
        svg = _placeholder_svg()
        cap = f'<figcaption>{_esc(b.caption)}{_prov_span(b)}</figcaption>' if b.caption else ""
        return f'<figure {attrs} role="img" aria-label="{_esc(b.caption or "")}">{svg}{cap}</figure>'
    if b.role.value == "contested":
        return _contested_html(b, attrs, fn_index)
    text = _esc(b.text)
    tail = _prov_span(b) + _footnote_sup(b, fn_index)
    if b.role.value == "lede":
        return f'<p class="lede" {attrs}>{text}{tail}</p>'
    if b.role.value == "card":
        return f'<aside class="card" {attrs}>{text}{tail}</aside>'
    if b.role.value == "toulmin":
        return f'<div class="toulmin" {attrs}>{text}{tail}</div>'
    if b.role.value == "recall":
        return f'<details class="recall" {attrs}><summary>Check yourself</summary>{text}</details>'
    return f'<div class="{b.role.value}" {attrs}>{text}{tail}</div>'


def _section_html(sec: Section, fn_index: dict[str, int]) -> str:
    attrs = [f'data-block-id="{_esc(sec.block_id)}"']
    if sec.concept:
        attrs.append(f'data-concept="{_esc(sec.concept)}"')
    inner = "\n".join(_block_html(b, fn_index) for b in sec.blocks)
    return f'<section {" ".join(attrs)}><h2>{_esc(sec.title)}</h2>\n{inner}\n</section>'


def _references_html(fn_index: dict[str, int], ledger=None) -> str:
    if not fn_index:
        return ""
    title = {}
    if ledger is not None:
        title = {s.source_id: (s.title or s.source_id) for s in ledger.sources}
    items = sorted(fn_index.items(), key=lambda kv: kv[1])
    lis = "".join(f'<li id="ref-{n}">{_esc(title.get(sid, sid))} <code>{_esc(sid)}</code></li>' for sid, n in items)
    return f'<section class="refs"><h2>References</h2><ol>{lis}</ol></section>'


def _primer_meta(ir: DocumentIR, concept_map: ConceptMap | None, lint_report: dict | None) -> str:
    meta = {
        "parameters": ir.meta.parameters,
        "ledger_snapshot": ir.meta.ledger_snapshot,
        "concept_map": [c.model_dump(mode="json") for c in concept_map.concepts] if concept_map else [],
        "lint_report": lint_report or {},
        "model_versions": ir.meta.model_versions,
        "generated_at": ir.meta.generated_at,
    }
    return json.dumps(meta, indent=2)


def render_html(
    ir: DocumentIR,
    concept_map: ConceptMap | None = None,
    lint_report: dict | None = None,
    title: str | None = None,
) -> str:
    fn_index: dict[str, int] = {}
    banner = ""
    if concept_map is not None and concept_map.contested:
        banner = ('<aside class="contested-banner" role="note">Competing organizing views: this '
                  'primer presents its structure as contested, not asserted.</aside>\n')
    sections_html = banner + "\n".join(_section_html(sec, fn_index) for sec in ir.sections)
    refs_html = _references_html(fn_index)
    doc_title = title or (ir.sections[0].title if ir.sections else "Primer")

    tpl = TEMPLATE.read_text(encoding="utf-8")
    return (tpl
            .replace("{{ title }}", _esc(doc_title))
            .replace("{{ blocks }}", sections_html)
            .replace("{{ footnotes }}", refs_html)
            .replace("{{ primer_meta }}", _primer_meta(ir, concept_map, lint_report)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render a document-ir.yaml to the HTML projection.")
    ap.add_argument("ir")
    ap.add_argument("--concept-map", dest="concept_map")
    ap.add_argument("--out", default="primer.html")
    args = ap.parse_args(argv)
    ir = DocumentIR.from_yaml(args.ir)
    cm = ConceptMap.from_yaml(args.concept_map) if args.concept_map else None
    Path(args.out).write_text(render_html(ir, cm), encoding="utf-8")
    print(f"wrote {args.out} ({len(ir.sections)} sections)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
