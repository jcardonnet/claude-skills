"""Every prose-reading check must see prose wherever the IR is allowed to put it.

`Block.readable_text` was introduced as the canonical answer to "what does this block say", and its
docstring asks consumers to stop reaching for `.text`. A docstring is not a mechanism: six consumers
reached for `.text` anyway, and each one silently exempted the three composite-content roles —
`card` (typed rows), `recall` (Q&A items) and `contested` (framings), all of which have
`text is None`. Two more iterated `sec.blocks` and so never descended into an h3 subsection at all.

That is the same defect in both directions. A check blind to a placement is a check that CANNOT FAIL
there (a phantom cross-reference in a card row went unreported), and it is also a check that fires
when it should not (a canonical term established in a card read as "never appears").

This module is the mechanism. It plants the SAME offending prose in every placement the IR permits
and asserts each check reports it in all of them. Regressing any consumer to `.text` — or to
`sec.blocks` — turns the matrix red instead of quietly costing coverage.
"""
import pytest

from checks import footnote, multiview_concepts, univocity_terms, xrefs
from checks._base import LintContext
from ir.schema import (
    Block,
    CardRows,
    Concept,
    ConceptMap,
    DocumentIR,
    Framing,
    RecallItem,
    Section,
    Subsection,
)

# --- placement builders ------------------------------------------------------
#
# Each returns a one-section DocumentIR carrying `text` in exactly one place. Filler keeps every
# other row/answer/framing non-empty so a check cannot pass by accident on a degenerate block.

_FILL = "Filler prose that asserts nothing in particular."


def _at_body(text: str) -> DocumentIR:
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw", blocks=[
        Block(block_id="b", role="body", concept="hnsw", text=text)])])


def _at_subsection_body(text: str) -> DocumentIR:
    sub = Subsection(block_id="sub", title="A subsection", concept="hnsw", blocks=[
        Block(block_id="b", role="body", concept="hnsw", text=text)])
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw",
                                        blocks=[], subsections=[sub])])


def _at_card_row(text: str) -> DocumentIR:
    card = Block(block_id="b", role="card", concept="hnsw", rows=CardRows(
        idea=text, home_anchor=_FILL, whats_new_vs_renamed=_FILL, reach_for_when=_FILL,
        skip_when=_FILL, key_exemplar=_FILL, confidence=_FILL))
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw",
                                        blocks=[card])])


def _at_recall_answer(text: str) -> DocumentIR:
    rec = Block(block_id="b", role="recall", concept="hnsw", items=[
        RecallItem(question="A question?", answer=text),
        RecallItem(question="Another?", answer=_FILL),
        RecallItem(question="A third?", answer=_FILL)])
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw",
                                        blocks=[rec])])


def _at_contested_framing(text: str) -> DocumentIR:
    con = Block(block_id="b", role="contested", concept="hnsw", framings=[
        Framing(label="school A", summary=text),
        Framing(label="school B", summary=_FILL)])
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw",
                                        blocks=[con])])


def _at_figure_caption(text: str) -> DocumentIR:
    fig = Block(block_id="b", role="figure", concept="hnsw", caption=text)
    return DocumentIR(sections=[Section(block_id="s", title="A section", concept="hnsw",
                                        blocks=[fig])])


PLACEMENTS = [
    pytest.param(_at_body, id="body-text"),
    pytest.param(_at_subsection_body, id="subsection-body-text"),
    pytest.param(_at_card_row, id="card-row"),
    pytest.param(_at_recall_answer, id="recall-answer"),
    pytest.param(_at_contested_framing, id="contested-framing"),
    pytest.param(_at_figure_caption, id="figure-caption"),
]

_CM = ConceptMap(concepts=[Concept(concept_id="hnsw", canonical_term="HNSW",
                                   aliases=["hierarchical navigable small world"],
                                   home_anchor="skip lists")])


def _ctx(ir: DocumentIR) -> LintContext:
    return LintContext(ir=ir, concept_map=_CM)


# --- the accessor the checks are supposed to share ---------------------------

@pytest.mark.parametrize("build", PLACEMENTS)
def test_prose_segments_finds_the_prose_in_every_placement(build):
    ir = build("The needle sentence.")
    assert any("The needle sentence." in seg
               for b in ir.flatten_blocks() for seg in b.prose_segments)


def test_prose_segments_carries_no_structural_labels():
    """`readable_text` labels its parts (`idea: ...`) so a judge can see which row it reads, and
    `run_critics._ir_digest` hashes that. A prose SCAN must not inherit those labels, or a concept
    canonically termed "confidence" would always appear to be established."""
    card = _at_card_row("The needle sentence.").flatten_blocks()[0]
    joined = " ".join(card.prose_segments)
    for label in ("idea:", "home_anchor:", "whats_new_vs_renamed:", "confidence:"):
        assert label not in joined
    assert "The needle sentence." in joined
    # and every authored row survives — dropping one would re-open the blind spot
    assert len(card.prose_segments) == 7


def test_readable_text_is_unchanged_for_cards_and_recall():
    """The frozen critic report is keyed on a digest of `readable_text`. Changing the card or recall
    rendering silently invalidates a real judged run and drops soft_critic 35 -> 2."""
    card = _at_card_row("The needle sentence.").flatten_blocks()[0]
    assert card.readable_text.startswith("idea: The needle sentence.\nhome_anchor: ")
    rec = _at_recall_answer("The needle sentence.").flatten_blocks()[0]
    assert rec.readable_text.startswith("Q: A question?\nA: The needle sentence.")


def test_a_contested_block_says_something():
    """Regression: `readable_text` handled `rows` and `items` and fell through to `text or caption`,
    so a contested block — whose content is its framings — read as the EMPTY STRING everywhere. That
    made its citations unsupportable (`any([])` is False), and made the digest blind to a rewrite of
    the framings themselves."""
    con = _at_contested_framing("Masks are required for reliable linkage.").flatten_blocks()[0]
    assert con.readable_text != ""
    assert "Masks are required for reliable linkage." in con.readable_text
    assert "school A" in con.readable_text
    assert con.entailment_units, "a contested block's framings are what it puts on the page"
    assert any("Masks are required" in u.text for u in con.entailment_units)


# --- R-XREF-02: phantom cross-references ------------------------------------

@pytest.mark.parametrize("build", PLACEMENTS)
def test_phantom_crossref_is_caught_in_every_placement(build):
    ir = build("As shown above, the traversal descends layers.")
    violations = xrefs.xrefs_resolve(_ctx(ir))
    assert violations, "a phantom directional reference went unreported"
    assert any("as shown above" in v.detail.lower() for v in violations)


@pytest.mark.parametrize("build", PLACEMENTS)
def test_unresolved_block_pointer_is_caught_in_every_placement(build):
    ir = build("The detail lives in [block: does-not-exist].")
    assert any("does-not-exist" in v.detail for v in xrefs.xrefs_resolve(_ctx(ir)))


@pytest.mark.parametrize("build", PLACEMENTS)
def test_a_resolvable_document_stays_clean_in_every_placement(build):
    """The other half: the check must not fire on prose it newly became able to read."""
    ir = build("The traversal descends layers, which is the whole trick.")
    assert xrefs.xrefs_resolve(_ctx(ir)) == []


# --- R-CONSIST-03: footnote balance -----------------------------------------

@pytest.mark.parametrize("build", PLACEMENTS)
def test_unmatched_footnote_marker_is_caught_in_every_placement(build):
    ir = build("Recall is bounded by the split[^undefined].")
    assert any("undefined" in v.detail for v in footnote.footnote_balance(_ctx(ir)))


# --- R-VOCAB-01: terminology univocity --------------------------------------

@pytest.mark.parametrize("build", PLACEMENTS)
def test_alias_without_canonical_is_caught_in_every_placement(build):
    """False-negative direction: an alias used where the canonical term is never established."""
    ir = build("A hierarchical navigable small world graph descends layers.")
    violations = univocity_terms.canonical_terms(_ctx(ir))
    assert any("hierarchical navigable small world" in v.detail for v in violations)


@pytest.mark.parametrize("build", PLACEMENTS)
def test_canonical_term_established_anywhere_silences_the_alias_rule(build):
    """False-positive direction, and the more damaging one: the canonical term IS established, just
    not in a `.text` field, so the check reported a violation the document does not commit."""
    ir = build("HNSW is the layered-graph index.")
    # the alias appears in an ordinary body block elsewhere in the same section
    ir.sections[0].blocks.append(Block(block_id="alias-user", role="body", concept="hnsw",
                                       text="A hierarchical navigable small world graph is used."))
    assert univocity_terms.canonical_terms(_ctx(ir)) == []


# --- R-MV-01: multi-view coverage (a block ATTRIBUTE, not prose) -------------

def test_modes_realized_in_a_subsection_count_toward_coverage():
    """R-MV-01 counted `sec.blocks` only, so a document realizing three modes was reported as
    realizing one whenever two of them lived in an h3. That is a MUST-level false positive."""
    mk = lambda i, m: Block(block_id=f"b{i}", role="body", concept="hnsw", mode=m, text=_FILL)
    ir = DocumentIR(sections=[Section(
        block_id="s", title="A section", concept="hnsw",
        blocks=[mk(1, "architecture")],
        subsections=[Subsection(block_id="sub", title="Detail",
                                blocks=[mk(2, "tradeoff"), mk(3, "failure")])])])
    modes = {b.mode.value for b in ir.flatten_blocks() if b.mode}
    assert len(modes) == 3
    assert multiview_concepts.modes_per_concept(_ctx(ir)) == []


def test_mv01_still_fails_when_the_modes_are_genuinely_absent():
    """The paired negative: widening the walk must not make the rule unfailable."""
    ir = DocumentIR(sections=[Section(
        block_id="s", title="A section", concept="hnsw",
        blocks=[Block(block_id="b1", role="body", concept="hnsw", mode="architecture", text=_FILL)],
        subsections=[Subsection(block_id="sub", title="Detail", blocks=[
            Block(block_id="b2", role="body", concept="hnsw", mode="architecture", text=_FILL)])])])
    assert any("hnsw" in v.detail for v in multiview_concepts.modes_per_concept(_ctx(ir)))


# --- R-GROUND-04: version tokens (the seventh consumer) -----------------------

@pytest.mark.parametrize("build", PLACEMENTS)
def test_a_version_token_is_flagged_in_every_placement(build):
    """`version_freshness` read `b.text`/`b.caption`, so a version token written into a card row —
    "reach for it on 2.4+" is exactly the kind of thing a card row says — could not be flagged. The
    same family as the six consumers already moved off `.text`, found one review later."""
    from checks import recency_versions

    ir = build("Use the v2.4 collector, which changed the default sampler.")
    violations = recency_versions.version_freshness(_ctx(ir))
    assert any("v2.4" in v.detail for v in violations), "version token went unflagged"


@pytest.mark.parametrize("build", PLACEMENTS)
def test_prose_without_a_version_token_stays_quiet(build):
    from checks import recency_versions

    ir = build("The collector changed its default sampler, which surprised everyone.")
    assert recency_versions.version_freshness(_ctx(ir)) == []
