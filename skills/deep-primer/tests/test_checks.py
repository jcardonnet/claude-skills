"""Per-check pass + fail tests (Prompt 2). Each check is exercised on small inline IRs.

Coherence is tested in both native (spaCy) and forced-fallback modes to prove it degrades per
CAPABILITIES.md: native findings are blocking-eligible (force_status None), fallback findings are
downgraded to warn.
"""
import pytest

from checks import (
    coherence_givennew,
    footnote,
    multiview_concepts,
    prose_caps,
    provenance,
    recency_versions,
    structure_coverage,
    univocity_terms,
    xrefs,
)
from checks._base import LintContext, nlp_available
from ir.schema import Block, Concept, ConceptMap, DocumentIR, Section


# --- builders ----------------------------------------------------------------

def blk(block_id, role, **kw):
    return Block(block_id=block_id, role=role, **kw)


def sec(block_id, *blocks, title="A claim-bearing title", concept=None):
    return Section(block_id=block_id, title=title, concept=concept, blocks=list(blocks))


def doc(*sections):
    return DocumentIR(sections=list(sections))


def ctx(document, concept_map=None, parameters=None, caps=None):
    return LintContext(ir=document, concept_map=concept_map, parameters=parameters or {}, capabilities=caps or {})


def details(violations):
    return " | ".join(v.detail for v in violations)


# --- structure_coverage.layer_coverage ---------------------------------------

def test_layer_coverage_pass():
    d = doc(sec("s1", blk("l", "lede", text="x"), blk("c", "card", text="y"), blk("r", "recall", text="q")))
    assert structure_coverage.layer_coverage(ctx(d)) == []


def test_layer_coverage_fail_missing_card_and_summary():
    long_body = "word " * 450
    d = doc(sec("s1", blk("l", "lede", text="x"), blk("r", "recall", text="q"), blk("b", "body", text=long_body)))
    viols = structure_coverage.layer_coverage(ctx(d))
    blob = details(viols)
    assert "missing required layer: card" in blob
    assert "no summary layer" in blob


# --- structure_coverage.length_budget ----------------------------------------

def test_length_budget_within_band_passes():
    body = "word " * 100
    d = doc(sec("s1", blk("b", "body", text=body)))
    assert structure_coverage.length_budget(ctx(d, parameters={"length_budget": 100})) == []


def test_length_budget_outside_band_warns():
    d = doc(sec("s1", blk("b", "body", text="three little words")))
    viols = structure_coverage.length_budget(ctx(d, parameters={"length_budget": 4000}))
    assert any("outside budget band" in v.detail for v in viols)


def test_length_budget_uniform_sections_flagged():
    body = "word " * 50
    d = doc(*[sec(f"s{i}", blk(f"b{i}", "body", text=body)) for i in range(4)])
    viols = structure_coverage.length_budget(ctx(d))
    assert any("near-uniform" in v.detail for v in viols)


# --- prose_caps.compression_gradient -----------------------------------------

def test_compression_gradient_pass():
    d = doc(sec("s1", blk("c", "card", text="short idea"), blk("b", "body", text="word " * 30)))
    assert prose_caps.compression_gradient(ctx(d)) == []


def test_compression_gradient_fail_card_longer_than_body():
    d = doc(sec("s1", blk("c", "card", text="word " * 30), blk("b", "body", text="tiny body")))
    viols = prose_caps.compression_gradient(ctx(d))
    assert any("compression gradient broken" in v.detail for v in viols)


# --- prose_caps.length_caps / condition_first (spaCy native) ------------------

def _require_spacy():
    if not nlp_available(ctx(doc())):
        pytest.skip("spaCy model unavailable in this environment")


def test_length_caps_flags_overlong_sentence():
    _require_spacy()
    long_sentence = "The retrieval subsystem " + "and the embedding pipeline " * 6 + "matter."
    d = doc(sec("s1", blk("b", "body", text=long_sentence)))
    assert any("words" in v.detail for v in prose_caps.length_caps(ctx(d)))


def test_length_caps_passes_short_sentences():
    d = doc(sec("s1", blk("b", "body", text="This is short. So is this.")))
    assert prose_caps.length_caps(ctx(d)) == []


def test_condition_first_flags_trailing_condition():
    _require_spacy()
    d = doc(sec("s1", blk("b", "body", text="Use a reranker if top-k precision dominates latency.")))
    assert any("condition trails instruction" in v.detail for v in prose_caps.condition_first(ctx(d)))


def test_condition_first_clean_when_condition_leads():
    _require_spacy()
    d = doc(sec("s1", blk("b", "body", text="When top-k precision dominates latency, add a reranker.")))
    assert prose_caps.condition_first(ctx(d)) == []


# --- coherence_givennew (native + fallback) -----------------------------------

_CHOPPY = "HNSW builds a graph. A shard splits the corpus. Quantization shrinks the vectors."
_COHERENT = "Retrieval fetches passages. The passages add latency. That latency is the budget a reranker spends."


def test_entity_grid_native_flags_choppy_and_is_blocking_eligible():
    _require_spacy()
    d = doc(sec("s1", blk("b", "body", text=_CHOPPY)))
    viols = coherence_givennew.entity_grid(ctx(d))
    assert viols, "native entity grid should flag the choppy paragraph"
    assert all(v.force_status is None for v in viols), "native findings must be blocking-eligible (MUST)"


def test_entity_grid_native_passes_coherent():
    _require_spacy()
    d = doc(sec("s1", blk("b", "body", text=_COHERENT)))
    assert coherence_givennew.entity_grid(ctx(d)) == []


def test_entity_grid_fallback_degrades_to_warn():
    d = doc(sec("s1", blk("b", "body", text=_CHOPPY)))
    viols = coherence_givennew.entity_grid(ctx(d, caps={"force_no_nlp": True}))
    assert viols, "fallback should still flag the choppy paragraph"
    assert all(v.force_status == "warn" for v in viols), "degraded findings must be downgraded to warn"


def test_entity_grid_fallback_passes_coherent():
    d = doc(sec("s1", blk("b", "body", text=_COHERENT)))
    assert coherence_givennew.entity_grid(ctx(d, caps={"force_no_nlp": True})) == []


# --- univocity_terms ----------------------------------------------------------

def test_univocity_duplicate_canonical_flagged():
    cm = ConceptMap(concepts=[
        Concept(concept_id="a", canonical_term="reranker"),
        Concept(concept_id="b", canonical_term="Reranker"),
    ])
    viols = univocity_terms.canonical_terms(ctx(doc(), concept_map=cm))
    assert any("reused" in v.detail for v in viols)


def test_univocity_alias_without_canonical_flagged():
    cm = ConceptMap(concepts=[Concept(concept_id="h", canonical_term="HNSW", aliases=["hierarchical navigable small world"])])
    d = doc(sec("s1", blk("b", "body", text="The hierarchical navigable small world index is fast.")))
    viols = univocity_terms.canonical_terms(ctx(d, concept_map=cm))
    assert any("never appears" in v.detail for v in viols)


def test_univocity_clean():
    cm = ConceptMap(concepts=[Concept(concept_id="h", canonical_term="HNSW", aliases=["hnsw graph"])])
    d = doc(sec("s1", blk("b", "body", text="HNSW indexes vectors.")))
    assert univocity_terms.canonical_terms(ctx(d, concept_map=cm)) == []


# --- multiview_concepts -------------------------------------------------------

def test_modes_per_concept_pass_with_three():
    cm = ConceptMap(concepts=[Concept(concept_id="v", canonical_term="vec")])
    d = doc(sec("s1",
                blk("c", "card", concept="v", mode="mental_model"),
                blk("f1", "figure", concept="v", mode="architecture"),
                blk("f2", "figure", concept="v", mode="benchmark")))
    assert multiview_concepts.modes_per_concept(ctx(d, concept_map=cm)) == []


def test_modes_per_concept_fail_with_two():
    cm = ConceptMap(concepts=[Concept(concept_id="v", canonical_term="vec")])
    d = doc(sec("s1", blk("c", "card", concept="v", mode="mental_model"), blk("f1", "figure", concept="v", mode="architecture")))
    viols = multiview_concepts.modes_per_concept(ctx(d, concept_map=cm))
    assert any("(<3)" in v.detail for v in viols)


def test_modes_uses_section_concept_fallback():
    cm = ConceptMap(concepts=[Concept(concept_id="v", canonical_term="vec")])
    d = doc(sec("s1",
                blk("c", "card", mode="mental_model"),
                blk("f1", "figure", mode="architecture"),
                blk("f2", "figure", mode="benchmark"),
                concept="v"))
    assert multiview_concepts.modes_per_concept(ctx(d, concept_map=cm)) == []


# --- recency_versions ---------------------------------------------------------

def test_recency_flags_version_token():
    d = doc(sec("s1", blk("b", "body", text="Pin HNSW to v1.2.3 in production.")))
    assert any("v1.2.3" in v.detail for v in recency_versions.version_freshness(ctx(d)))


def test_recency_ignores_section_refs():
    d = doc(sec("s1", blk("b", "body", text="See section 3.2 for details.")))
    assert recency_versions.version_freshness(ctx(d)) == []


# --- footnote -----------------------------------------------------------------

def test_footnote_unmatched_marker():
    d = doc(sec("s1", blk("b", "body", text="A claim with a note.[^1]")))
    assert any("no matching definition" in v.detail for v in footnote.footnote_balance(ctx(d)))


def test_footnote_balanced():
    d = doc(sec("s1", blk("b", "body", text="A claim.[^1]\n[^1]: the source.")))
    assert footnote.footnote_balance(ctx(d)) == []


# --- xrefs --------------------------------------------------------------------

def test_xrefs_phantom_figure():
    d = doc(sec("s1", blk("b", "body", text="As established in Figure 9, latency dominates.")))
    assert any("Figure 9" in v.detail for v in xrefs.xrefs_resolve(ctx(d)))


def test_xrefs_unresolved_block_ref_and_directional():
    d = doc(sec("s1", blk("b", "body", text="See [block: nope] and the diagram as shown below.")))
    blob = details(xrefs.xrefs_resolve(ctx(d)))
    assert "[block: nope]" in blob and "phantom directional" in blob


def test_xrefs_resolved_figure_ok():
    d = doc(sec("s1",
                blk("f1", "figure", caption="Figure 1: latency dominates."),
                blk("b", "body", text="Figure 1 shows latency dominating.")))
    assert xrefs.xrefs_resolve(ctx(d)) == []


# --- provenance ---------------------------------------------------------------

def test_provenance_missing_tag():
    d = doc(sec("s1", blk("b", "body", text="x", claim_ids=["C1"])))
    assert any("no provenance tag" in v.detail for v in provenance.tagged(ctx(d)))


def test_provenance_verified_without_source():
    d = doc(sec("s1", blk("b", "toulmin", text="x", claim_ids=["C1"], provenance="verified")))
    assert any("no source_ids" in v.detail for v in provenance.tagged(ctx(d)))


def test_provenance_ok():
    d = doc(sec("s1", blk("b", "toulmin", text="x", claim_ids=["C1"], provenance="verified", source_ids=["s1"])))
    assert provenance.tagged(ctx(d)) == []
