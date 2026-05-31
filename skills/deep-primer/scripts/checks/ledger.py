"""Source-ledger provenance lint (deterministic).

Classification: local-deterministic
Implements: R-GROUND-05
Checks: claims with >1 supporting source set corroboration_count + corroborated_by;
version/SOTA claims set as_of_date; contested claims list contradicts (each referencing >=1 claim).
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6).
"""
from __future__ import annotations


def provenance_fields(source_ledger: dict) -> list[str]:
    """Return [] if the ledger satisfies R-GROUND-05, else a list of violation strings."""
    raise NotImplementedError("deep-primer Stage 6 stub: checks/ledger.py::provenance_fields (Prompt 6)")
