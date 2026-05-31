"""HTML -> block list, for legacy/round-trip back to the IR (the IR remains canonical).

Classification: local-deterministic
Implements: -

Under IR-first the document-ir.yaml is the source of truth; this module reads a rendered
primer back into the typed `Block` list so the two stay reconcilable. It also exposes
`blocks_to_html`, a *minimal* serializer that is the exact inverse of the parser — the
production renderer is `scripts/render/render_html.py` (Prompt 4), but both honor the same
block-attribute contract:

    data-block-id  data-role  data-concept  data-mode  data-provenance
    data-claim-ids (comma-sep)  data-source-ids (comma-sep)  data-svg-ref
    inner text -> Block.text (non-figure)   <figcaption> -> Block.caption (figure)

An element carrying `data-block-id` but no recognized leaf role (e.g. a <section> container)
is skipped: the parser yields leaf field-guide blocks only.
"""
from __future__ import annotations

import html as _html
import sys
from pathlib import Path

# Make `ir.schema` importable whether run as a module or a standalone script (scripts/ is the root).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import Block, Role  # noqa: E402

_ROLE_VALUES = {r.value for r in Role}


def _make_soup(html: str):
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:  # pragma: no cover - bs4 is a base dependency
        raise ImportError("parse_primer needs beautifulsoup4 (pip install -e .[dev])") from e
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # lxml missing -> stdlib parser
        return BeautifulSoup(html, "html.parser")


def _split_ids(value: str | None) -> list[str]:
    if not value:
        return []
    return [tok.strip() for tok in value.split(",") if tok.strip()]


def parse_primer(html: str) -> list[Block]:
    """Parse rendered primer HTML into the leaf `Block` list, in document order."""
    soup = _make_soup(html)
    blocks: list[Block] = []
    for el in soup.find_all(attrs={"data-block-id": True}):
        role = el.get("data-role") or ("figure" if el.name == "figure" else None)
        if role not in _ROLE_VALUES:
            continue  # structural/wrapper element, not a leaf block

        is_figure = role == Role.figure.value
        caption = None
        text = None
        if is_figure:
            cap = el.find("figcaption")
            if cap is not None:
                caption = cap.get_text().strip() or None
        else:
            t = el.get_text().strip()
            text = t or None

        blocks.append(Block(
            block_id=el["data-block-id"],
            role=role,
            text=text,
            concept=el.get("data-concept") or None,
            mode=el.get("data-mode") or None,
            claim_ids=_split_ids(el.get("data-claim-ids")),
            provenance=el.get("data-provenance") or None,
            source_ids=_split_ids(el.get("data-source-ids")),
            caption=caption,
            svg_ref=el.get("data-svg-ref") or None,
        ))
    return blocks


def _attr(name: str, value: str | None) -> str:
    if not value:
        return ""
    return f' {name}="{_html.escape(value, quote=True)}"'


def block_to_html(b: Block) -> str:
    """Serialize one Block to a single element honoring the block-attribute contract."""
    attrs = (
        _attr("data-block-id", b.block_id)
        + _attr("data-role", b.role.value)
        + _attr("data-concept", b.concept)
        + _attr("data-mode", b.mode.value if b.mode else None)
        + _attr("data-provenance", b.provenance.value if b.provenance else None)
        + _attr("data-claim-ids", ",".join(b.claim_ids) or None)
        + _attr("data-source-ids", ",".join(b.source_ids) or None)
        + _attr("data-svg-ref", b.svg_ref)
    )
    if b.role == Role.figure:
        cap = f"<figcaption>{_html.escape(b.caption)}</figcaption>" if b.caption else ""
        return f"<figure{attrs}>{cap}</figure>"
    body = _html.escape(b.text) if b.text else ""
    return f"<div{attrs}>{body}</div>"


def blocks_to_html(blocks: list[Block]) -> str:
    """Minimal round-trip serializer: `parse_primer(blocks_to_html(bs)) == bs`."""
    inner = "\n".join(block_to_html(b) for b in blocks)
    return f'<main class="primer">\n{inner}\n</main>'


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: parse_primer.py PRIMER.html", file=sys.stderr)
        return 2
    blocks = parse_primer(Path(argv[0]).read_text(encoding="utf-8"))
    print(f"{len(blocks)} block(s):")
    for b in blocks:
        print(f"  {b.block_id:24} role={b.role.value:14} concept={b.concept or '-'} mode={b.mode.value if b.mode else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
