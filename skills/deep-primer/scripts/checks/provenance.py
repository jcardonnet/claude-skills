"""Provenance tagging on claim-bearing blocks.

Classification: local-deterministic
Implements: R-PROJ-05 (tagged)

Every block carrying claim_ids must have a provenance tag, and provenance: verified implies at
least one source_id. (validate_ir enforces the verified⇒source_id invariant as a hard schema
gate; here it is a SHOULD lint so the report surfaces untagged claim blocks as warnings.)
"""
from __future__ import annotations

from checks._base import LintContext, Violation


def tagged(ctx: LintContext) -> list[Violation]:
    out: list[Violation] = []
    for b in ctx.ir.flatten_blocks():
        if not b.claim_ids:
            continue
        if b.provenance is None:
            out.append(Violation(b.block_id, f"block carries claim_ids {b.claim_ids} but has no provenance tag"))
        elif b.provenance.value == "verified" and not b.source_ids:
            out.append(Violation(b.block_id, "provenance 'verified' but no source_ids"))
    return out
