"""Reconciliation deltas: contested role + framings, new ledger/concept-map fields.

Verifies the done-conditions: contested + the four ledger fields exist on the models, and both
renderers accept a contested block (alignment still holds).
"""
from ir.schema import Block, Claim, ConceptMap, Concept, DocumentIR, Framing, Role, Section
from render.check_alignment import check_alignment
from render.render_html import render_html
from render.render_llm_md import render_llm_md


def _contested_ir():
    block = Block(
        block_id="contested-structure", role="contested", provenance="verified",
        framings=[
            Framing(label="by retrieval stage", summary="organize around the retrieval pipeline",
                    applies_when="end-to-end systems", source_ids=["s1"]),
            Framing(label="by index type", summary="organize around the index family", source_ids=["s2"]),
        ],
    )
    ir = DocumentIR(sections=[Section(block_id="sec-c", title="Two ways to carve this", blocks=[block])])
    cm = ConceptMap(concepts=[Concept(concept_id="x", canonical_term="x")], cycle=2, contested=True)
    return ir, cm


# --- schema fields exist ------------------------------------------------------

def test_role_contested_exists():
    assert Role.contested.value == "contested"


def test_ledger_fields_exist_with_defaults():
    c = Claim(claim_id="C1", text="t")
    assert c.corroboration_count is None
    assert c.corroborated_by == []
    assert c.as_of_date is None
    assert c.provenance_origin == "discovered"


def test_conceptmap_cycle_and_contested():
    cm = ConceptMap(cycle=3, contested=True)
    assert cm.cycle == 3 and cm.contested is True
    assert ConceptMap().contested is False  # default


def test_block_accepts_framings():
    _, _ = _contested_ir()  # constructs a Block with framings without raising under extra=forbid


# --- renderers accept contested ----------------------------------------------

def test_render_html_contested_panel_and_banner():
    ir, cm = _contested_ir()
    html = render_html(ir, cm)
    assert 'class="contested"' in html and 'data-block-id="contested-structure"' in html
    assert "by retrieval stage" in html and "by index type" in html
    assert 'aria-label="competing organizing views"' in html  # the per-block panel
    assert "contested-banner" in html                          # concept-map contested:true banner


def test_render_llm_md_keeps_contested_one_per_framing():
    ir, cm = _contested_ir()
    md = render_llm_md(ir, cm)
    # contested is kept (operational), one heading per framing, each with provenance
    assert md.count("## [block: contested-structure]") == 2
    assert "framing: by retrieval stage" in md and "framing: by index type" in md
    assert md.count("provenance: verified") == 2


def test_contested_projections_align():
    ir, cm = _contested_ir()
    report = check_alignment(render_html(ir, cm), render_llm_md(ir, cm))
    assert report["ok"] is True and report["md_only"] == []
