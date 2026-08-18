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
from checks._base import CheckNotApplicable, LintContext, nlp_available
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


# --- Stage A: the structural checks the flat V1 IR could not express ----------

def _rows(**overrides):
    base = dict(idea="i", home_anchor="h", whats_new_vs_renamed="n", reach_for_when="r",
                skip_when="s", key_exemplar="k", confidence="c")
    base.update(overrides)
    return base


def _items(n, **kw):
    return [{"question": f"q{i}", "answer": f"a{i}", **kw} for i in range(n)]


def sub(block_id, *blocks, title="A subsection claim", concept=None):
    from ir.schema import Subsection
    return Subsection(block_id=block_id, title=title, concept=concept, blocks=list(blocks))


def sec_with_subs(block_id, blocks, subsections, title="A claim-bearing title"):
    return Section(block_id=block_id, title=title, blocks=list(blocks), subsections=list(subsections))


# structure_coverage.params_present (R-PARAM-01)

def test_params_present_pass():
    p = {"home_domain": ["ir"], "target_domain": "rag", "seniority_band": "staff_plus", "length_budget": 4000}
    assert structure_coverage.params_present(ctx(doc(), parameters=p)) == []


def test_params_present_flags_each_missing():
    p = {"home_domain": ["ir"], "target_domain": "rag"}
    out = structure_coverage.params_present(ctx(doc(), parameters=p))
    assert out and "seniority_band" in details(out) and "length_budget" in details(out)


# structure_coverage.card_rows (R-CARD-02)

def test_card_rows_pass():
    d = doc(sec("s1", blk("c", "card", text="x", rows=_rows())))
    assert structure_coverage.card_rows(ctx(d)) == []


def test_card_rows_flags_untyped_card():
    d = doc(sec("s1", blk("c", "card", text="a free-text card")))
    out = structure_coverage.card_rows(ctx(d))
    assert out and out[0].block_id == "c" and "no typed rows" in out[0].detail


def test_card_rows_flags_blank_skip_when():
    d = doc(sec("s1", blk("c", "card", text="x", rows=_rows(skip_when="   "))))
    out = structure_coverage.card_rows(ctx(d))
    assert out and "skip_when" in out[0].detail


# structure_coverage.recall_count (R-RECALL-01)

def test_recall_count_pass_with_three_items():
    d = doc(sec("s1", blk("r", "recall", items=_items(3))))
    assert structure_coverage.recall_count(ctx(d)) == []


def test_recall_count_flags_wrong_number():
    d = doc(sec("s1", blk("r", "recall", items=_items(2))))
    out = structure_coverage.recall_count(ctx(d))
    assert out and "2 recall item" in out[0].detail


def test_recall_count_silent_when_section_has_no_recall_block():
    """A missing recall layer is layer_coverage's finding; recall_count must not double-report."""
    d = doc(sec("s1", blk("l", "lede", text="x")))
    assert structure_coverage.recall_count(ctx(d)) == []


# structure_coverage.operational_artifacts (R-ART-01)

def test_operational_artifacts_pass_with_all_four():
    d = doc(sec("s1", *[blk(f"a{i}", "matrix", artifact_kind=k) for i, k in enumerate(
        ["decision_matrix", "checklist", "failure_catalog", "decision_aid"])]))
    assert structure_coverage.operational_artifacts(ctx(d)) == []


def test_operational_artifacts_flags_collapsed_set():
    d = doc(sec("s1", blk("a0", "matrix", artifact_kind="decision_matrix")))
    out = structure_coverage.operational_artifacts(ctx(d))
    assert out and "checklist" in out[0].detail and "decision_aid" in out[0].detail


# structure_coverage.heading_hierarchy + banned_heading_terms (R-ARCH-05, R-SCENT-01)

def test_heading_hierarchy_pass():
    d = doc(sec_with_subs("s1", [blk("l", "lede", text="x")],
                          [sub("s1a", blk("m", "summary", text="y"),
                               blk("b", "body", text="z", heading="An h4 label"))]))
    assert structure_coverage.heading_hierarchy(ctx(d)) == []


def test_heading_hierarchy_flags_untitled_subsection():
    d = doc(sec_with_subs("s1", [], [sub("s1a", blk("m", "summary", text="y"), title="  ")]))
    out = structure_coverage.heading_hierarchy(ctx(d))
    assert out and out[0].block_id == "s1a"


def test_heading_hierarchy_flags_h4_on_non_body_role():
    d = doc(sec("s1", blk("c", "card", text="x", rows=_rows(), heading="not allowed here")))
    out = structure_coverage.heading_hierarchy(ctx(d))
    assert out and "body blocks only" in out[0].detail


def test_banned_heading_terms_flags_generic_labels():
    d = doc(sec("s1", blk("l", "lede", text="x"), title="Overview"))
    out = structure_coverage.banned_heading_terms(ctx(d))
    assert out and "Overview" in out[0].detail


def test_banned_heading_terms_allows_predictive_heading():
    d = doc(sec("s1", blk("l", "lede", text="x"), title="Why long context did not kill chunking"))
    assert structure_coverage.banned_heading_terms(ctx(d)) == []


# structure_coverage.summary_budgets + the h3:sub-sum 1:1 clause (R-SUMM-02, R-CONSIST-01)

def test_summary_budgets_pass():
    d = doc(sec_with_subs("s1", [blk("m", "summary", text="short")],
                          [sub("s1a", blk("sm", "summary", text="one sub-sum"))]))
    assert structure_coverage.summary_budgets(ctx(d)) == []


def test_summary_budgets_flags_overlong_section_summary():
    d = doc(sec("s1", blk("m", "summary", text=" ".join(["word"] * 501))))
    out = structure_coverage.summary_budgets(ctx(d))
    assert out and "501 words" in out[0].detail


def test_summary_budgets_flags_missing_sub_sum():
    d = doc(sec_with_subs("s1", [], [sub("s1a", blk("b", "body", text="no sub-sum here"))]))
    out = structure_coverage.summary_budgets(ctx(d))
    assert out and "0 sub-sum" in out[0].detail


def test_layer_coverage_flags_duplicate_sub_sum():
    d = doc(sec_with_subs("s1",
                          [blk("l", "lede", text="x"), blk("c", "card", text="y"), blk("r", "recall", text="q")],
                          [sub("s1a", blk("m1", "summary", text="a"), blk("m2", "summary", text="b"))]))
    out = structure_coverage.layer_coverage(ctx(d))
    assert out and "2 sub-sum" in details(out)


# subsection-awareness of the pre-existing checks

def test_flatten_blocks_recurses_into_subsections():
    d = doc(sec_with_subs("s1", [blk("a", "lede", text="x")], [sub("s1a", blk("b", "body", text="y"))]))
    assert [b.block_id for b in d.flatten_blocks()] == ["a", "b"]
    assert d.all_block_ids() == ["s1", "a", "s1a", "b"]


def test_compression_gradient_counts_subsection_body():
    """Body prose living in a subsection still counts as the section's body layer."""
    d = doc(sec_with_subs("s1", [blk("c", "card", text="one two three")],
                          [sub("s1a", blk("b", "body", text=" ".join(["w"] * 20)))]))
    assert prose_caps.compression_gradient(ctx(d)) == []


# --- G1: anchor resolution when home ~= target (R-XREF-04) -------------------

def _cm(**kw):
    return ConceptMap(concepts=[Concept(concept_id="c1", canonical_term="leader anchoring", **kw)])


def test_home_anchor_distinct_passes_on_adjacent_technique():
    out = univocity_terms.home_anchor_distinct(ctx(doc(), _cm(home_anchor="ray casting in graphics")))
    assert out == []


def test_home_anchor_distinct_flags_self_restatement():
    """home ~= target degenerates the bridge into 'X is like X'."""
    out = univocity_terms.home_anchor_distinct(ctx(doc(), _cm(home_anchor="leader anchoring")))
    assert out and "restates its own term" in out[0].detail


def test_home_anchor_distinct_flags_substring_restatement():
    out = univocity_terms.home_anchor_distinct(ctx(doc(), _cm(home_anchor="anchoring")))
    assert out


def test_home_anchor_distinct_flags_alias_restatement():
    out = univocity_terms.home_anchor_distinct(
        ctx(doc(), _cm(home_anchor="leader following", aliases=["leader following"])))
    assert out


def test_concept_map_checks_declare_they_did_not_run_rather_than_passing():
    """These used to return `[]` with no concept-map, and the dispatcher records `[]` as a PASS — so
    an IR-only lint reported three MUST rules (R-VOCAB-01, R-XREF-04, R-MV-01) as satisfied and
    credited them as coverage. `[]` has to keep meaning "I looked and found nothing"."""
    for check in (univocity_terms.home_anchor_distinct, univocity_terms.canonical_terms,
                  multiview_concepts.modes_per_concept):
        with pytest.raises(CheckNotApplicable):
            check(ctx(doc()))


# --- G6: user-specified structure is authoritative (R-ARCH-07) ---------------

def _sec_mapped(bid, maps_to, title="A predictive claim about it"):
    return Section(block_id=bid, title=title, maps_to=maps_to)


def test_user_structure_not_enforced_when_absent():
    d = DocumentIR(sections=[Section(block_id="s1", title="t")])
    assert structure_coverage.user_structure_respected(ctx(d)) == []


def test_user_structure_pass_with_rewritten_headings():
    """The heading is a predictive claim (R-SCENT-01); maps_to carries the user's entry."""
    d = DocumentIR(sections=[_sec_mapped("s1", "Background"), _sec_mapped("s2", "Tradeoffs")])
    p = {"user_structure": ["Background", "Tradeoffs"]}
    assert structure_coverage.user_structure_respected(ctx(d, parameters=p)) == []


def test_user_structure_flags_missing_entry():
    d = DocumentIR(sections=[_sec_mapped("s1", "Background")])
    p = {"user_structure": ["Background", "Tradeoffs"]}
    out = structure_coverage.user_structure_respected(ctx(d, parameters=p))
    assert any("'Tradeoffs' is not realized" in v.detail for v in out)


def test_user_structure_flags_unmapped_section():
    d = DocumentIR(sections=[_sec_mapped("s1", "Background"), Section(block_id="s2", title="invented")])
    p = {"user_structure": ["Background"]}
    out = structure_coverage.user_structure_respected(ctx(d, parameters=p))
    assert any("declares no maps_to" in v.detail for v in out)


def test_user_structure_flags_duplicate_claim():
    d = DocumentIR(sections=[_sec_mapped("s1", "Background"), _sec_mapped("s2", "Background")])
    p = {"user_structure": ["Background"]}
    out = structure_coverage.user_structure_respected(ctx(d, parameters=p))
    assert any("claimed by 2 sections" in v.detail for v in out)


def test_user_structure_flags_foreign_maps_to():
    d = DocumentIR(sections=[_sec_mapped("s1", "Nowhere")])
    p = {"user_structure": ["Background"]}
    out = structure_coverage.user_structure_respected(ctx(d, parameters=p))
    assert any("not an entry of the user structure" in v.detail for v in out)


def test_user_structure_flags_reordering():
    d = DocumentIR(sections=[_sec_mapped("s1", "Tradeoffs"), _sec_mapped("s2", "Background")])
    p = {"user_structure": ["Background", "Tradeoffs"]}
    out = structure_coverage.user_structure_respected(ctx(d, parameters=p))
    assert any("does not follow the user structure" in v.detail for v in out)
