"""Prompt 1 tests: IR schema, validation invariants, and HTML round-trip.

Done-condition: pytest green AND validate_ir rejects the malformed fixture.
"""
import pytest
from pydantic import ValidationError

from ir.schema import Block, DocumentIR, Mode, Provenance, Role
from ir.validate_ir import main, validate_document, validate_files
from utils.parse_primer import blocks_to_html, parse_primer


# --- schema ------------------------------------------------------------------

def test_loads_valid_ir(fixtures):
    ir = DocumentIR.from_yaml(fixtures / "document-ir.yaml")
    assert len(ir.sections) == 2
    assert len(ir.flatten_blocks()) == 8
    # section containers + leaves are all distinct
    assert len(ir.all_block_ids()) == len(set(ir.all_block_ids())) == 10
    # enums coerced from strings
    fig = next(b for b in ir.flatten_blocks() if b.block_id == "fig-maskfree")
    assert fig.role is Role.figure and fig.mode is Mode.tradeoff
    rec = next(b for b in ir.flatten_blocks() if b.block_id == "rec-maskfree")
    assert rec.provenance is Provenance.verified and rec.source_ids == ["s-aaaa"]


def test_schema_rejects_bad_enum():
    with pytest.raises(ValidationError):
        Block(block_id="x", role="not-a-real-role")


def test_schema_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Block(block_id="x", role="lede", bogus="nope")


# --- invariants --------------------------------------------------------------

def test_valid_ir_passes_all_invariants(fixtures):
    errors = validate_files(
        fixtures / "document-ir.yaml",
        fixtures / "source-ledger.yaml",
        fixtures / "concept-map.yaml",
    )
    assert errors == []


def test_validate_rejects_malformed(fixtures):
    errors = validate_files(
        fixtures / "document-ir.malformed.yaml",
        fixtures / "source-ledger.yaml",
        fixtures / "concept-map.yaml",
    )
    blob = "\n".join(errors)
    assert any("duplicate block_id 'dup'" in e for e in errors), blob
    assert any("C99" in e and "not found in source-ledger" in e for e in errors), blob
    assert any("bogus-concept" in e and "not found in concept-map" in e for e in errors), blob
    assert any("rec-bad" in e and "requires >=1 source_id" in e for e in errors), blob


def test_invariants_skip_cross_artifact_checks_when_absent(fixtures):
    # Without ledger/concept-map, claim/concept resolution is not enforced;
    # the only intrinsic violations of the malformed fixture remain (dup id, verified-no-source).
    errors = validate_document(DocumentIR.from_yaml(fixtures / "document-ir.malformed.yaml"))
    assert any("duplicate block_id" in e for e in errors)
    assert not any("source-ledger" in e for e in errors)


# --- CLI ---------------------------------------------------------------------

def test_cli_exit_codes(fixtures):
    ok = main([str(fixtures / "document-ir.yaml"),
               "--ledger", str(fixtures / "source-ledger.yaml"),
               "--concept-map", str(fixtures / "concept-map.yaml")])
    assert ok == 0
    bad = main([str(fixtures / "document-ir.malformed.yaml"),
                "--ledger", str(fixtures / "source-ledger.yaml"),
                "--concept-map", str(fixtures / "concept-map.yaml")])
    assert bad == 1


# --- round-trip --------------------------------------------------------------

def test_html_roundtrip_preserves_blocks(fixtures):
    ir = DocumentIR.from_yaml(fixtures / "document-ir.yaml")
    blocks = ir.flatten_blocks()
    reparsed = parse_primer(blocks_to_html(blocks))
    assert reparsed == blocks  # full pydantic equality, field-by-field


def test_roundtrip_idempotent_second_pass(fixtures):
    ir = DocumentIR.from_yaml(fixtures / "document-ir.yaml")
    once = parse_primer(blocks_to_html(ir.flatten_blocks()))
    twice = parse_primer(blocks_to_html(once))
    assert once == twice


def test_parser_skips_structural_elements():
    # a <section> carrying data-block-id but no leaf role is not a block
    html = (
        '<section data-block-id="sec-1" data-concept="x">'
        '<div data-block-id="lede-1" data-role="lede">hi</div>'
        '</section>'
    )
    blocks = parse_primer(html)
    assert [b.block_id for b in blocks] == ["lede-1"]
