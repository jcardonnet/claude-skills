"""Prompt 4 golden tests: IR -> {HTML, LLM-MD}, block-id alignment, role filter, self-containment.

Done-condition: both projections render, alignment passes, tests green.
"""
import json
import re

from ir.schema import Block, Concept, ConceptMap, DocumentIR, Section, SourceLedger
from render.check_alignment import check_alignment
from render.render_html import render_html
from render.render_llm_md import deanaphorize, render_llm_md
from verify._entailment import LexicalEntailment
from verify.chunk_selfcontained import has_dangling_anaphora, verify


def _fixtures(fixtures):
    ir = DocumentIR.from_yaml(fixtures / "document-ir.yaml")
    cm = ConceptMap.from_yaml(fixtures / "concept-map.yaml")
    return ir, cm


# --- both projections render + align -----------------------------------------

def test_both_projections_render_and_align(fixtures):
    ir, cm = _fixtures(fixtures)
    html = render_html(ir, cm)
    md = render_llm_md(ir, cm)
    report = check_alignment(html, md)
    assert report["ok"] is True
    # the only html-extra ids are the role-filtered recall blocks
    assert set(report["html_only"]) == {"recall-maskfree", "recall-anchor"}
    assert report["md_only"] == []


def test_md_drops_recall_and_svg_keeps_captions(fixtures):
    ir, cm = _fixtures(fixtures)
    md = render_llm_md(ir, cm)
    assert "recall-maskfree" not in md and "recall-anchor" not in md   # R-PROJ-03 drop recall
    assert "<svg" not in md                                            # R-PROJ-06 no svg
    assert "Figure: Figure 1: masks add cost" in md                    # caption kept as text


def test_md_provenance_inline_and_chunk_shape(fixtures):
    ir, cm = _fixtures(fixtures)
    md = render_llm_md(ir, cm)
    assert md.startswith("---")            # front-matter index
    assert "concepts:" in md
    # the artifact-schemas chunk shape: heading w/ provenance, a Claim/Figure line, a Sources line
    assert re.search(r"## \[block: rec-maskfree\].*provenance: verified", md)
    assert "Sources: [s-aaaa]" in md
    assert re.search(r"## \[block: lede-maskfree\].*provenance: inferred\nClaim: ", md)


def test_html_has_instrumentation_and_meta(fixtures):
    ir, cm = _fixtures(fixtures)
    html = render_html(ir, cm)
    for needle in ('data-block-id="lede-maskfree"', 'data-concept="mask-free-linkage"',
                   'data-mode="tradeoff"', 'id="primer-meta"', 'class="prov prov-verified"',
                   'role="img"', "<svg"):
        assert needle in html, needle
    meta_json = re.search(r'id="primer-meta">(.*?)</script>', html, re.S).group(1)
    meta = json.loads(meta_json)
    assert meta["parameters"]["target_domain"] == "bom-linkage"
    assert meta["concept_map"] and meta["concept_map"][0]["concept_id"] == "mask-free-linkage"


def test_alignment_detects_misalignment(fixtures):
    ir, cm = _fixtures(fixtures)
    html = render_html(ir, cm)
    md = render_llm_md(ir, cm) + "\n## [block: ghost-block]\nClaim: not in html\nSources: [none yet — inferred]\n"
    report = check_alignment(html, md)
    assert report["ok"] is False
    assert report["md_only"] == ["ghost-block"]


# --- de-anaphorization producer ----------------------------------------------

def test_deanaphorize_restates_referent_and_strips_crossref():
    assert deanaphorize("This trades recall for speed.", "vector index").startswith("vector index")
    assert "as shown below" not in deanaphorize("Latency dominates, as shown below.", "x")
    assert "(see Figure 3)" not in deanaphorize("Recall saturates (see Figure 3).", "x")


# --- chunk self-containment verifier (R-PROJ-04) ------------------------------

def test_has_dangling_anaphora_detector():
    assert has_dangling_anaphora("This is the fast path") is True
    assert has_dangling_anaphora("Latency dominates, as shown above") is True
    assert has_dangling_anaphora("Vector indexes are fast") is False


def _chunk_ctx(text, quote, *, concept="vector-index"):
    ir = DocumentIR(sections=[Section(block_id="s", title="t", concept=concept, blocks=[
        Block(block_id="b1", role="toulmin", text=text, concept=concept, claim_ids=["C1"], provenance="inferred"),
    ])])
    ledger = SourceLedger(**{"sources": [{"source_id": "s1", "claims": [{"claim_id": "C1", "text": "x", "quote": quote}]}]})
    cm = ConceptMap(concepts=[Concept(concept_id="vector-index", canonical_term="vector index")])
    return ir, ledger, cm


def test_chunk_selfcontained_ok():
    ir, ledger, cm = _chunk_ctx("vector index trades recall for speed", "vector index trades recall for speed")
    report = verify(ir, ledger, cm, backend=LexicalEntailment())
    assert report["ok"] is True and report["verdicts"][0]["entails_claims"] is True


def test_chunk_selfcontained_deanaphorizes_then_passes():
    ir, ledger, cm = _chunk_ctx("This trades recall for speed quickly", "vector index trades recall for speed")
    report = verify(ir, ledger, cm, backend=LexicalEntailment())
    v = report["verdicts"][0]
    assert v["dangling_anaphora"] is False         # producer restated "This" -> "vector index"
    assert v["chunk"].startswith("vector index")
    assert report["ok"] is True


def test_chunk_selfcontained_flags_entailment_failure():
    ir, ledger, cm = _chunk_ctx("completely unrelated remark about weather", "vector index trades recall for speed")
    report = verify(ir, ledger, cm, backend=LexicalEntailment())
    assert report["ok"] is False and report["verdicts"][0]["entails_claims"] is False
