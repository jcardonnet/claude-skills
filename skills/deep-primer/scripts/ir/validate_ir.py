"""Validate a document-ir against the schema + structural invariants.

Classification: local-deterministic
Implements: R-PROJ-01

Invariants enforced (all derive from the canonical-IR contract in artifact-schemas.md):
  1. block_ids are unique across the whole document (section containers + leaf blocks).
  2. every claim_id referenced by a block exists in the source-ledger (R-GROUND-01 substrate).
  3. every `concept` (section or block) exists in the concept-map (so R-MV-01 / R-VOCAB-01 can resolve).
  4. provenance == verified  =>  >= 1 source_id (R-PROJ-05).

Cross-artifact invariants (2, 3) are only enforced when the ledger / concept-map are supplied.

Usage:
    python scripts/ir/validate_ir.py document-ir.yaml --ledger source-ledger.yaml --concept-map concept-map.yaml
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Make `ir.schema` importable whether run as a module or a standalone script (scripts/ is the root).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import ConceptMap, DocumentIR, Provenance, SourceLedger  # noqa: E402


def validate_document(
    ir: DocumentIR,
    ledger: SourceLedger | None = None,
    concept_map: ConceptMap | None = None,
) -> list[str]:
    """Return a list of invariant-violation messages; an empty list means valid."""
    errors: list[str] = []

    # 1. unique block_ids (containers + leaves)
    counts = Counter(ir.all_block_ids())
    for bid, n in sorted(counts.items()):
        if n > 1:
            errors.append(f"duplicate block_id {bid!r} appears {n} times")

    leaves = ir.flatten_blocks()

    # 4. provenance verified => >=1 source_id
    for b in leaves:
        if b.provenance == Provenance.verified and not b.source_ids:
            errors.append(f"{b.block_id}: provenance 'verified' requires >=1 source_id")

    # 2. claim_ids resolve to the ledger
    if ledger is not None:
        known_claims = ledger.claim_ids()
        for b in leaves:
            for cid in b.claim_ids:
                if cid not in known_claims:
                    errors.append(f"{b.block_id}: claim_id {cid!r} not found in source-ledger")

    # 3. concepts resolve to the concept-map (sections and blocks)
    if concept_map is not None:
        known_concepts = concept_map.concept_ids()
        for sec in ir.sections:
            if sec.concept and sec.concept not in known_concepts:
                errors.append(f"{sec.block_id}: concept {sec.concept!r} not found in concept-map")
            for b in sec.blocks:
                if b.concept and b.concept not in known_concepts:
                    errors.append(f"{b.block_id}: concept {b.concept!r} not found in concept-map")

    return errors


def validate_files(
    ir_path: str | Path,
    ledger_path: str | Path | None = None,
    concept_map_path: str | Path | None = None,
) -> list[str]:
    """Load + schema-validate the IR (and optional artifacts), then run invariants.

    Schema-validation failures (bad enum, unknown field, missing required key) are returned as
    `schema:` messages, so a malformed fixture is rejected at either layer.
    """
    from pydantic import ValidationError

    try:
        ir = DocumentIR.from_yaml(ir_path)
    except ValidationError as e:
        return [f"schema: document-ir invalid — {err['loc']}: {err['msg']}" for err in e.errors()]
    except (ValueError, OSError) as e:
        return [f"schema: cannot load document-ir — {e}"]

    ledger = SourceLedger.from_yaml(ledger_path) if ledger_path else None
    concept_map = ConceptMap.from_yaml(concept_map_path) if concept_map_path else None
    return validate_document(ir, ledger, concept_map)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a document-ir.yaml against schema + invariants.")
    ap.add_argument("ir", help="path to document-ir.yaml")
    ap.add_argument("--ledger", help="path to source-ledger.yaml (enables claim_id resolution)")
    ap.add_argument("--concept-map", dest="concept_map", help="path to concept-map.yaml (enables concept resolution)")
    args = ap.parse_args(argv)

    errors = validate_files(args.ir, args.ledger, args.concept_map)
    if errors:
        print(f"INVALID — {len(errors)} problem(s) in {args.ir}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — {args.ir} is a valid document-ir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
