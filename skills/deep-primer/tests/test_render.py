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


# --- Stage A: the extended IR renders into both projections ------------------

def _full(fixtures):
    from ir.schema import ConceptMap, DocumentIR
    return (DocumentIR.from_yaml(fixtures / "document-ir.full.yaml"),
            ConceptMap.from_yaml(fixtures / "concept-map.full.yaml"))


def test_html_renders_subsection_as_h3(fixtures):
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    assert '<h3 data-block-id="sub-chunk-size"' in html


def test_html_renders_card_rows_as_dl_with_anchor_first(fixtures):
    """R-CARD-02 rows become a <dl>; R-XREF-01 puts the home-domain analogue first."""
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    card = html.split('data-block-id="card-chunking"')[1].split("</aside>")[0]
    assert "<dl>" in card
    assert card.index("If you know") < card.index("Idea")
    assert "Skip it when" in card


def test_html_renders_three_recall_items(fixtures):
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    block = html.split('data-block-id="recall-chunking"')[1].split("</div>")[0]
    assert block.count('class="recall-item"') == 3


def test_html_emits_artifact_kind_and_h4(fixtures):
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    assert 'data-artifact-kind="decision_matrix"' in html
    assert 'data-artifact-kind="checklist"' in html
    assert "<h4>Where fixed windows sever context</h4>" in html


def test_template_placeholders_are_substituted_once(fixtures):
    """The template names its placeholders in a header comment. Spelling one with braces made
    str.replace inject a second copy of the whole document into that comment."""
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    assert html.count('data-block-id="recall-chunking"') == 1
    assert html.count('<h3 data-block-id="sub-chunk-size"') == 1
    assert "{{ blocks }}" not in html


def test_llm_md_includes_subsection_blocks(fixtures):
    """A subsection block that renders into HTML but never reaches the MD breaks R-PROJ-02."""
    ir, cm = _full(fixtures)
    md = render_llm_md(ir, cm)
    assert "[block: body-chunk-size]" in md


def test_llm_md_distills_card_rows_and_drops_the_hook(fixtures):
    """R-PROJ-03: keep the card's operational content, demote the advance-organizer hook."""
    ir, cm = _full(fixtures)
    md = render_llm_md(ir, cm)
    card = md.split("[block: card-chunking]")[1].split("## [block:")[0]
    assert "Skip-it-when:" in card and "Reach-for-it-when:" in card
    assert "Like choosing a row-versus-page" not in card   # the hook is demoted


def test_llm_md_surfaces_artifact_kind(fixtures):
    ir, cm = _full(fixtures)
    assert "artifact: decision_matrix" in render_llm_md(ir, cm)


def test_full_fixture_projections_align(fixtures):
    from render.check_alignment import check_alignment
    ir, cm = _full(fixtures)
    report = check_alignment(render_html(ir, cm), render_llm_md(ir, cm))
    assert report["ok"], report
    assert set(report["html_only"]) == {"recall-chunking", "recall-reranking"}


# --- the html-input checks (R-CONSIST-02, R-DEPTH-02, R-FIG-04) --------------

def test_html_checks_pass_on_rendered_output(fixtures):
    from utils.parse_primer import block_ids_and_meta, depth_dial_present, figure_a11y
    ir, cm = _full(fixtures)
    html = render_html(ir, cm)
    assert block_ids_and_meta(html) == []
    assert depth_dial_present(html) == []
    assert figure_a11y(html) == []


def test_figure_a11y_flags_missing_aria_label():
    from utils.parse_primer import figure_a11y
    bad = '<figure data-block-id="f1" role="img"><figcaption>c</figcaption></figure>'
    out = figure_a11y(bad)
    assert out and "aria-label" in out[0]


def test_block_ids_and_meta_flags_duplicate_ids():
    from utils.parse_primer import block_ids_and_meta
    bad = ('<p data-block-id="x"></p><p data-block-id="x"></p>'
           '<script id="primer-meta">{"parameters":{},"ledger_snapshot":[],'
           '"concept_map":[],"generated_at":"t"}</script>')
    out = block_ids_and_meta(bad)
    assert out and "duplicate" in out[0]
