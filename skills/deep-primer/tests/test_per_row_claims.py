"""Per-row citation attribution — the last approximation left in the citation metric.

`entailment_units` splits a composite block into the rows that assert something, which fixed the
structural failure where a <=15-word quote was asked to entail seven concatenated rows. What it did
NOT fix is ATTRIBUTION: every one of a block's claim_ids was tested against every one of its units,
so a general quote cited for a specific claim could be credited as supporting the block through a
row it has nothing to do with. That is precisely the over-citation eval-rubric.yaml names on
spec-01 — "a general quote attached to a specific claim it does not support" — and the metric could
not see it, because the block-level claim list says WHICH claims are cited and never says WHAT for.

`row_claims` (cards), `RecallItem.claim_ids` and `Framing.claim_ids` let the IR say what for. Where
a block declares nothing the old behaviour is unchanged, so no existing artifact moves.
"""
import pytest
from pydantic import ValidationError

from ir.schema import (
    Block,
    CardRows,
    Claim,
    DocumentIR,
    Framing,
    RecallItem,
    Section,
    Source,
    SourceLedger,
)
from ir.validate_ir import validate_document
from verify._entailment import LexicalEntailment
from verify.citation_quality import evaluate

_ROWS = dict(
    home_anchor="Like a B-tree index, but for nearest rather than equal.",
    whats_new_vs_renamed="Granularity is renamed; the embedding scope is new.",
    reach_for_when="Reach for smaller chunks when queries target specific facts.",
    skip_when="Skip re-chunking when the failure is ordering rather than recall.",
    confidence="settled for the recall bound",
)


def _card(**over) -> Block:
    return Block(block_id="card", role="card", concept="c", provenance="verified", **{
        "claim_ids": ["C-idea", "C-exemplar"],
        "rows": CardRows(idea="Chunking is the retrieval unit and bounds recall.",
                         key_exemplar="A 200-token window over a heading-split corpus.", **_ROWS),
        **over})


def _ledger(**quotes) -> SourceLedger:
    return SourceLedger(sources=[Source(source_id="s1", claims=[
        Claim(claim_id=cid, text=q, quote=q) for cid, q in quotes.items()])])


def _score(block: Block, ledger: SourceLedger) -> dict:
    ir = DocumentIR(sections=[Section(block_id="s", title="T", concept="c", blocks=[block])])
    return evaluate(ir, ledger, backend=LexicalEntailment())


# --- the unit now carries what it is cited FOR --------------------------------

def test_a_unit_reports_the_claims_attached_to_it():
    card = _card(row_claims={"idea": ["C-idea"], "key_exemplar": ["C-exemplar"]})
    units = {u.text: u.claim_ids for u in card.entailment_units}
    assert units == {
        "Chunking is the retrieval unit and bounds recall.": ["C-idea"],
        "A 200-token window over a heading-split corpus.": ["C-exemplar"],
    }


def test_an_undeclared_block_still_yields_bare_units():
    """No `row_claims` means no attribution was authored, and the old every-claim-against-every-unit
    behaviour is what must apply — otherwise adding the field would silently re-score every existing
    artifact."""
    assert [u.claim_ids for u in _card().entailment_units] == [[], []]
    assert [u.text for u in _card().entailment_units] == [
        "Chunking is the retrieval unit and bounds recall.",
        "A 200-token window over a heading-split corpus."]


def test_recall_answers_and_contested_framings_carry_their_own_claims():
    recall = Block(block_id="r", role="recall", claim_ids=["C1", "C2"], items=[
        RecallItem(question="What caps recall?", answer="The chunk boundary does.",
                   claim_ids=["C1"]),
        RecallItem(question="And then?", answer="Reranking cannot recover it.", claim_ids=["C2"])])
    assert [(u.text, u.claim_ids) for u in recall.entailment_units] == [
        ("The chunk boundary does.", ["C1"]),
        ("Reranking cannot recover it.", ["C2"])]

    contested = Block(block_id="con", role="contested", claim_ids=["C3"], framings=[
        Framing(label="school A", summary="Masks are required.", claim_ids=["C3"]),
        Framing(label="school B", summary="Anchors alone suffice.")])
    assert [(u.text, u.claim_ids) for u in contested.entailment_units] == [
        ("Masks are required.", ["C3"]),
        ("Anchors alone suffice.", [])]


# --- what the attribution buys: precision stops crediting the wrong row --------

def test_a_quote_is_only_asked_about_the_row_it_was_cited_for():
    """The defect. `C-exemplar` cites a quote about window sizes; without attribution it is tested
    against the `idea` row too, entails THAT, and is scored as a supporting citation — so a citation
    that supports nothing it was attached to still raises precision."""
    ledger = _ledger(**{
        "C-idea": "chunking is the retrieval unit and bounds recall",
        # cited for the exemplar, but its words are the idea's
        "C-exemplar": "chunking is the retrieval unit and bounds recall",
    })

    loose = _score(_card(), ledger)
    assert loose["precision"] == 1.0, "both citations credited — via the same row"

    exact = _score(_card(row_claims={"idea": ["C-idea"], "key_exemplar": ["C-exemplar"]}), ledger)
    assert exact["precision"] == 0.5
    supports = {c["claim_id"]: c["supports"] for c in exact["per_citation"]}
    assert supports == {"C-idea": True, "C-exemplar": False}


def test_a_correctly_attributed_pair_still_scores_clean():
    """The paired positive — attribution must not simply make everything fail."""
    ledger = _ledger(**{
        "C-idea": "chunking is the retrieval unit and bounds recall",
        "C-exemplar": "a 200-token window over a heading-split corpus",
    })
    exact = _score(_card(row_claims={"idea": ["C-idea"], "key_exemplar": ["C-exemplar"]}), ledger)
    assert exact["precision"] == 1.0 and exact["recall"] == 1.0


def test_a_claim_attached_to_no_row_is_decorative():
    """A block-level claim_id the author never attributed supports nothing in particular, which is
    what a decorative citation IS."""
    card = _card(claim_ids=["C-idea", "C-exemplar", "C-loose"],
                 row_claims={"idea": ["C-idea"], "key_exemplar": ["C-exemplar"]})
    ledger = _ledger(**{
        "C-idea": "chunking is the retrieval unit and bounds recall",
        "C-exemplar": "a 200-token window over a heading-split corpus",
        "C-loose": "chunking is the retrieval unit and bounds recall",
    })
    r = _score(card, ledger)
    assert {c["claim_id"]: c["supports"] for c in r["per_citation"]}["C-loose"] is False
    assert r["precision"] == pytest.approx(2 / 3, abs=1e-3)   # reported rounded to 4dp


# --- the IR contract ----------------------------------------------------------

def test_row_claims_must_name_a_real_row():
    card = _card(row_claims={"not_a_row": ["C-idea"]})
    ir = DocumentIR(sections=[Section(block_id="s", title="T", blocks=[card])])
    assert any("not_a_row" in e for e in validate_document(ir))


def test_row_claims_must_be_a_subset_of_the_block_s_citations():
    """The block-level list stays the authoritative "what this block cites" — it is what the HTML
    projection prints and what R-GROUND-01 resolves. A row citing outside it would be a marker no
    ledger check ever sees."""
    card = _card(row_claims={"idea": ["C-nowhere"]})
    ir = DocumentIR(sections=[Section(block_id="s", title="T", blocks=[card])])
    errors = validate_document(ir)
    assert any("C-nowhere" in e and "claim_ids" in e for e in errors)


def test_row_claims_is_rejected_on_a_block_that_has_no_rows():
    body = Block(block_id="b", role="body", text="x", claim_ids=["C1"],
                 row_claims={"idea": ["C1"]})
    ir = DocumentIR(sections=[Section(block_id="s", title="T", blocks=[body])])
    assert any("row_claims" in e for e in validate_document(ir))


def test_per_item_claims_resolve_to_the_ledger():
    recall = Block(block_id="r", role="recall", claim_ids=["C1"], items=[
        RecallItem(question="q?", answer="a.", claim_ids=["C-nowhere"])])
    ir = DocumentIR(sections=[Section(block_id="s", title="T", blocks=[recall])])
    assert any("C-nowhere" in e for e in validate_document(ir))


def test_the_schema_still_forbids_stray_keys():
    with pytest.raises(ValidationError):
        Block(block_id="b", role="body", rowclaims={"idea": ["C1"]})
