"""Block-id alignment across the two projections.

Classification: local-deterministic
Implements: R-PROJ-02

The MD block-ids must be a subset of the HTML block-ids, and the difference must be exactly the
role-filtered blocks (recall). Uses parse_primer to read leaf block-ids+roles back from the HTML
(section containers carry data-block-id but no leaf role, so they are not counted).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from render.render_llm_md import DROPPED_ROLES  # noqa: E402
from utils.parse_primer import parse_primer  # noqa: E402

_MD_BLOCK_RE = re.compile(r"^##\s*\[block:\s*([\w-]+)\]", re.MULTILINE)


def check_alignment(html: str, md: str) -> dict:
    html_blocks = parse_primer(html)
    html_ids = {b.block_id for b in html_blocks}
    md_ids = set(_MD_BLOCK_RE.findall(md))

    dropped_ids = {b.block_id for b in html_blocks if b.role.value in DROPPED_ROLES}
    diff = html_ids - md_ids

    md_subset = md_ids <= html_ids
    diff_is_dropped = diff == dropped_ids
    return {
        "ok": md_subset and diff_is_dropped,
        "md_subset_of_html": md_subset,
        "diff_equals_role_filtered": diff_is_dropped,
        "html_only": sorted(diff),
        "md_only": sorted(md_ids - html_ids),
        "dropped_roles": sorted(DROPPED_ROLES),
        "expected_dropped": sorted(dropped_ids),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check block-id alignment between the HTML and LLM-MD projections.")
    ap.add_argument("html")
    ap.add_argument("md")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report = check_alignment(Path(args.html).read_text(encoding="utf-8"), Path(args.md).read_text(encoding="utf-8"))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    status = "ALIGNED" if report["ok"] else "MISALIGNED"
    print(f"{status} — md⊆html={report['md_subset_of_html']} diff==role-filtered={report['diff_equals_role_filtered']} "
          f"(html-only={report['html_only']}, md-only={report['md_only']})")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
