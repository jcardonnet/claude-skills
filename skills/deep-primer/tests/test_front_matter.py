"""`DocumentIR.front_matter` — the R-ARCH-01 opening that belongs to no section.

The scope-and-decisions contract precedes the first h2, so it is not section content. Before this
field existed there was NO representable slot for it: `R-CONSIST-01` requires every section to carry
a lede, a card and a recall block, so a seventh "section" could not hold a scope contract, and
`meta` is parameters rather than prose — prose parked there renders to the page while every prose
lint walks `sections` and never sees it. A MUST rule the artifact could not satisfy however it was
written.

Adding a placement is the same hazard `test_block_prose.py` documents, one level up: a consumer that
walks `sections` is now blind to a place the IR permits, and a blind check CANNOT FAIL there. So this
module asserts the new placement is reachable — from `flatten_blocks`, from both projections, from
the lints — and that the four consumers which reason about *placement* rather than content handle it
deliberately rather than by accident.
"""
import re

import pytest

from checks import footnote, recency_versions, structure_coverage, xrefs
from checks._base import LintContext
from critics.claude_judge import _judge_document_view
from critics.run_critics import applicable_blocks
from ir.schema import Block, DocumentIR, Section
from render.check_alignment import check_alignment
from render.render_html import render_html
from render.render_llm_md import kept_blocks, render_llm_md
from verify import chunk_selfcontained

_FM_ID = "scope-and-decisions"


def _with_front_matter(text: str) -> DocumentIR:
    return DocumentIR(
        front_matter=[Block(block_id=_FM_ID, role="body", text=text)],
        sections=[Section(block_id="s", title="A section", concept="hnsw",
                          blocks=[Block(block_id="b", role="body", concept="hnsw",
                                        text="Filler prose that asserts nothing.")])],
    )


def _ctx(ir: DocumentIR) -> LintContext:
    return LintContext(ir=ir)


# --- reachability: the walk every consumer shares ----------------------------

def test_flatten_blocks_yields_front_matter_first():
    """`flatten_blocks()` is what puts the new placement in front of every lint, both renderers and
    the critics without each of them learning about it. Order matters: front matter opens the page."""
    ir = _with_front_matter("The scope contract.")
    assert [b.block_id for b in ir.flatten_blocks()] == [_FM_ID, "b"]


def test_all_block_ids_includes_front_matter():
    """Block-id uniqueness and every id-resolving check (xrefs, alignment) read this."""
    ir = _with_front_matter("The scope contract.")
    assert ir.all_block_ids() == [_FM_ID, "s", "b"]


def test_the_full_fixture_actually_carries_one(fixtures):
    """The reference artifact is what eval scores for R-ARCH-01. If it loses its front matter the
    rule goes back to failing on a real judged run, and this module would otherwise stay green."""
    ir = DocumentIR.from_yaml(fixtures / "document-ir.full.yaml")
    assert [b.block_id for b in ir.front_matter] == [_FM_ID]
    assert ir.front_matter[0].text


# --- placement consumer 1: the HTML projection -------------------------------

def test_html_renders_front_matter_before_the_first_section():
    html = render_html(_with_front_matter("The scope contract."))
    # against the RENDERED section, not `<section`: the template shell has section elements of its
    # own (nav, meta) that precede everything the IR contributes.
    assert html.index(f'id="{_FM_ID}"') < html.index('id="s"')


def test_html_front_matter_is_a_header_not_a_section():
    """A `<section>` would put an empty rung in the nav and the depth-fold: the template builds both
    from `h2`/`h3` inside a `section`, and front matter carries neither heading level."""
    html = render_html(_with_front_matter("The scope contract."))
    header = re.search(r'<header class="front-matter">(.*?)</header>', html, re.DOTALL)
    assert header and _FM_ID in header.group(1)
    assert "<section" not in header.group(1)


# --- placement consumer 2: the LLM-MD projection -----------------------------

def test_kept_blocks_yields_front_matter_with_no_section():
    """`kept_blocks` yields `(section, block)`; front matter has no section, so it yields `None`.
    Every consumer of that generator has to mean it — see the judge test below."""
    ir = _with_front_matter("The scope contract.")
    assert next((sec, b.block_id) for sec, b in kept_blocks(ir)) == (None, _FM_ID)


def test_md_carries_front_matter_and_the_projections_stay_aligned():
    """R-PROJ-02: the two projections share block-ids. Front matter renders into the HTML, so a
    projection that dropped it would report an `html_only` id — a real alignment break."""
    ir = _with_front_matter("The scope contract.")
    report = check_alignment(render_html(ir), render_llm_md(ir))
    assert report["ok"] is True
    assert f"[block: {_FM_ID}]" in render_llm_md(ir)
    assert report["html_only"] == [] and report["md_only"] == []


def test_r_proj_04_reaches_front_matter_and_cannot_repair_its_opening():
    """R-PROJ-04 verifies each distilled chunk stands alone. Front matter is a kept block, so the
    verifier sees it — and the producer's repair does NOT apply: `deanaphorize` replaces a leading
    bare demonstrative with the SECTION's canonical term, and front matter belongs to no section.
    That is a real authoring constraint (the opening must name its subject, not point at it), and it
    is only safe because the verifier can still fail on it. This test is what keeps that true."""
    bad = chunk_selfcontained.verify(_with_front_matter("This primer is for staff-plus engineers."))
    assert [v["block_id"] for v in bad["verdicts"] if v["dangling_anaphora"]] == [_FM_ID]
    good = chunk_selfcontained.verify(_with_front_matter("The primer is for staff-plus engineers."))
    assert not any(v["dangling_anaphora"] for v in good["verdicts"])


def test_md_distills_front_matter_without_a_concept_referent():
    """The de-anaphorization pass resolves referents from the *section's* concept. With `sec=None`
    there is none, and the regression this guards is an AttributeError on `sec.concept`, not a
    wording change."""
    ir = _with_front_matter("It leaves out the index, and that boundary was a decision.")
    assert "boundary was a decision" in render_llm_md(ir)


# --- placement consumer 3: the judge's document view -------------------------

def test_judge_outline_skips_front_matter():
    """The outline numbers SECTION HEADINGS for the structure rules (R-ARCH-*, R-SCENT-01). Front
    matter has no heading; counting it would shift every section's number by one and, with
    `sec=None`, crash on `sec.title` before it got the chance."""
    view = _judge_document_view(_with_front_matter("The scope contract."))
    outline = view.split("BLOCKS")[0]
    assert "1. A section" in outline
    assert "2." not in outline
    # ...but the prose itself still reaches the critic, or R-ARCH-01 could not pass
    assert "The scope contract." in view


def test_a_role_targeted_critic_rule_reaches_front_matter():
    """The judge has two entry points, and the outline test above covers only one.

    `applicable_blocks` walks `flatten_blocks()`, so the four prose rules that target `body`
    (R-PROSE-01/02/03/06) now judge the scope contract as ordinary prose — which is what it is. That
    is the intended reading, but it is a NEW placement for the critics, and an untested one is the
    blind spot this module exists to catch: front matter is the one block a `sections`-only walk
    would have skipped while every count still looked right."""
    ir = _with_front_matter("The scope contract.")
    judged = [b.block_id for b in applicable_blocks("R-PROSE-01", ir)]
    assert _FM_ID in judged, "front-matter prose went unjudged by a prose rule"
    assert judged == [_FM_ID, "b"]


def test_a_document_level_rule_is_unaffected_by_front_matter():
    """The paired negative. R-ARCH-01 is judged against the whole document, not per block; if the
    new placement leaked a block view into a document-level rule, that rule would be answered once
    per block and its verdicts would collide on `block_id`."""
    ir = _with_front_matter("The scope contract.")
    assert [b.block_id for b in applicable_blocks("R-ARCH-01", ir)] == ["document"]


# --- placement consumer 4: the length budget ---------------------------------

def _budget_ctx(front_words: int, section_words: list[int]) -> LintContext:
    word = "word "
    ir = DocumentIR(
        front_matter=[Block(block_id=_FM_ID, role="body", text=(word * front_words).strip())]
        if front_words else [],
        sections=[Section(block_id=f"s{i}", title=f"S{i}", concept="hnsw",
                          blocks=[Block(block_id=f"b{i}", role="body", text=(word * n).strip())])
                  for i, n in enumerate(section_words)],
    )
    return LintContext(ir=ir, parameters={"length_budget": 100})


def test_front_matter_words_are_spent_against_the_budget():
    """It is prose on the page. Excluding it would let a document blow its budget in a place the
    check could not see — the same could-not-fail shape this field otherwise fixes."""
    # sections alone sit inside [60, 140]; the front matter pushes the total past the ceiling
    assert structure_coverage.length_budget(_budget_ctx(0, [60, 60])) == []
    violations = structure_coverage.length_budget(_budget_ctx(40, [60, 60]))
    assert any("outside budget band" in v.detail for v in violations)


def test_front_matter_stays_out_of_the_uniformity_statistic():
    """The paired half. Three equal sections are near-uniform whatever the opening does; a scope
    contract is *expected* to be shorter than a section, so folding it in would drag the CV up and
    read as salience the document does not have."""
    detail = "near-uniform"
    uniform = _budget_ctx(20, [30, 30, 30])
    assert any(detail in v.detail for v in structure_coverage.length_budget(uniform))
    varied = _budget_ctx(20, [10, 30, 60])
    assert not any(detail in v.detail for v in structure_coverage.length_budget(varied))


# --- the lints reach it ------------------------------------------------------
#
# Same matrix as test_block_prose.py, one placement further out: a check blind to front matter is a
# check that cannot fail there, and front matter is authored prose like any other.

@pytest.mark.parametrize("check,text,needle,anchor", [
    pytest.param(xrefs.xrefs_resolve, "As shown above, the split caps recall.",
                 "as shown above", _FM_ID, id="R-XREF-02-phantom-reference"),
    pytest.param(xrefs.xrefs_resolve, "The detail lives in [block: does-not-exist].",
                 "does-not-exist", _FM_ID, id="R-XREF-02-unresolved-pointer"),
    # footnote_balance is document-level by construction — it diffs marker and definition SETS over
    # the whole document, so there is no one block to blame and it reports `block_id=None`.
    pytest.param(footnote.footnote_balance, "Recall is bounded by the split[^undefined].",
                 "undefined", None, id="R-CONSIST-03-footnote"),
    pytest.param(recency_versions.version_freshness, "Use the v2.4 collector, which changed things.",
                 "v2.4", _FM_ID, id="R-GROUND-04-version-token"),
])
def test_a_lint_reaches_prose_written_in_front_matter(check, text, needle, anchor):
    violations = check(_ctx(_with_front_matter(text)))
    assert any(needle in v.detail.lower() for v in violations), \
        "front matter is a blind spot for this check"
    assert any(v.block_id == anchor for v in violations), "reported against the wrong block"


def test_the_same_lints_stay_quiet_on_clean_front_matter():
    """The other direction: becoming able to read a placement must not make the checks fire in it."""
    ir = _with_front_matter("The primer covers two stages, which is the whole scope.")
    ctx = _ctx(ir)
    assert xrefs.xrefs_resolve(ctx) == []
    assert footnote.footnote_balance(ctx) == []
    assert recency_versions.version_freshness(ctx) == []


# --- back-compatibility ------------------------------------------------------

def test_a_document_without_front_matter_is_unchanged(fixtures):
    """Every artifact authored before the field exists must load and render exactly as it did."""
    ir = DocumentIR.from_yaml(fixtures / "document-ir.yaml")
    assert ir.front_matter == []
    html = render_html(ir)
    assert 'class="front-matter"' not in html
    assert check_alignment(html, render_llm_md(ir))["md_only"] == []
