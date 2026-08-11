"""Grounding-loop tests (Prompt 6 / Stage C).

The load-bearing one is the R-DISC-01 firewall: a discovery lead is a pointer, and a claim only
becomes provenance when its quote is found verbatim in a document we actually fetched. Everything
else here — corroboration, recency, coverage, curation — is the deterministic machinery that turns
fetched pages into a ledger the primer can be held to.
"""
import pytest

from checks import ledger as ledger_checks
from ir.schema import Claim, DiscoveryLeads, Question, ResearchPlan, Source, SourceLead, SourceLedger
from research import coverage, curate, recency
from research.claim_extractor import (
    MAX_QUOTE_WORDS,
    QuoteScanExtractor,
    anchor_claims,
    build_ledger,
    corroborate,
    mark_conflicts,
    mark_recency,
)
from research.retrieval_loop import Document, ReplayFetcher, fetch_source_leads, retrieve_for_questions

BODY = (
    "Retrieval notes.\n"
    "CLAIM: chunking is the unit of retrieval and bounds achievable recall\n"
    "CLAIM: reranking improves ordering but cannot recover a missed document\n"
)


def doc(url="https://example.org/a", text=BODY, **kw):
    return Document(url=url, text=text, **kw)


# --- the R-DISC-01 firewall ---------------------------------------------------

def test_quote_must_appear_in_the_fetched_body():
    """The anti-fabrication floor: a claim sourced from a discovery report's prose rather than a
    page we fetched cannot reach the ledger."""
    proposals = [{"text": "invented finding", "quote": "a sentence never on the page"}]
    kept, rejected = anchor_claims(proposals, doc())
    assert kept == []
    assert rejected and "not found in the fetched body" in rejected[0]
    assert "R-DISC-01" in rejected[0]


def test_quote_present_in_body_is_kept():
    proposals = [{"text": "chunking bounds recall", "quote": "chunking is the unit of retrieval"}]
    kept, rejected = anchor_claims(proposals, doc())
    assert rejected == [] and len(kept) == 1
    assert kept[0].quote == "chunking is the unit of retrieval"


def test_quote_matching_is_whitespace_insensitive():
    kept, _ = anchor_claims(
        [{"text": "t", "quote": "chunking   is the\nunit of retrieval"}], doc())
    assert len(kept) == 1


def test_overlong_quote_is_rejected():
    """Quotes stay <=15 words: the primer paraphrases, it does not reproduce."""
    long_quote = " ".join(["word"] * (MAX_QUOTE_WORDS + 1))
    kept, rejected = anchor_claims([{"text": "t", "quote": long_quote}], doc(text=long_quote))
    assert kept == [] and "words" in rejected[0]


def test_claim_without_a_quote_is_rejected():
    kept, rejected = anchor_claims([{"text": "believed but unsourced", "quote": ""}], doc())
    assert kept == [] and "R-GROUND-01" in rejected[0]


def test_seed_document_marks_its_claims_as_user_origin():
    kept, _ = anchor_claims([{"text": "t", "quote": "chunking is the unit of retrieval"}],
                            doc(provenance_origin="user"))
    assert kept[0].provenance_origin == "user"


def test_build_ledger_anchors_every_claim_to_a_fetched_source():
    ledger, rejected = build_ledger([doc()], QuoteScanExtractor())
    assert rejected == []
    source = ledger.sources[0]
    assert source.content_hash and source.source_id
    assert all(source_claim.quote for source_claim in source.claims)
    assert len(source.claims) == 2


# --- corroboration + recency (R-GROUND-05) -----------------------------------

def _two_source_ledger(text_a, text_b, type_a="primary_paper", type_b="primary_paper"):
    return SourceLedger(sources=[
        Source(source_id="s-a", url="https://a.org", type=type_a,
               claims=[Claim(claim_id="C1", text=text_a, quote="q")]),
        Source(source_id="s-b", url="https://b.org", type=type_b,
               claims=[Claim(claim_id="C2", text=text_b, quote="q")]),
    ])


def test_corroborate_links_independent_sources():
    led = corroborate(_two_source_ledger(
        "chunking bounds achievable retrieval recall",
        "achievable retrieval recall is bounded by chunking"))
    c1 = led.sources[0].claims[0]
    assert c1.corroboration_count == 2 and c1.corroborated_by == ["s-b"]


def test_corroborate_leaves_singletons_alone():
    led = corroborate(_two_source_ledger("chunking bounds recall", "rerankers reorder candidates"))
    assert led.sources[0].claims[0].corroboration_count is None


def test_corroboration_never_counts_a_source_as_its_own_support():
    led = corroborate(SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="chunking bounds retrieval recall", quote="q"),
        Claim(claim_id="C2", text="chunking bounds retrieval recall", quote="q"),
    ])]))
    assert led.sources[0].claims[0].corroboration_count is None


def test_mark_recency_stamps_version_and_sota_claims():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="pgvector 0.7.0 adds HNSW builds", quote="q"),
        Claim(claim_id="C2", text="this is the current state of the art", quote="q"),
        Claim(claim_id="C3", text="chunking bounds recall", quote="q"),
    ])])
    mark_recency(led, as_of="2026-08-11")
    got = {c.claim_id: c.as_of_date for c in led.sources[0].claims}
    assert str(got["C1"]) == "2026-08-11" and str(got["C2"]) == "2026-08-11"
    assert got["C3"] is None


def test_mark_conflicts_is_symmetric():
    """A conflict visible from one side only reads as settled from the other."""
    led = _two_source_ledger("x", "not x")
    mark_conflicts(led, {"C1": ["C2"]})
    c1, c2 = led.sources[0].claims[0], led.sources[1].claims[0]
    assert c1.contested and c2.contested
    assert c1.contradicts == ["C2"] and c2.contradicts == ["C1"]


# --- the ledger lint (R-GROUND-05) -------------------------------------------

def test_ledger_lint_clean_on_a_built_ledger():
    ledger, _ = build_ledger([doc()], QuoteScanExtractor())
    assert ledger_checks.provenance_fields(corroborate(ledger)) == []


def test_ledger_lint_flags_corroboration_without_sources():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="t", quote="q", corroboration_count=3)])])
    assert any("no corroborated_by" in p for p in ledger_checks.provenance_fields(led))


def test_ledger_lint_flags_self_corroboration():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="t", quote="q", corroboration_count=2, corroborated_by=["s-a"])])])
    assert any("its own source" in p for p in ledger_checks.provenance_fields(led))


def test_ledger_lint_flags_version_claim_without_as_of_date():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="pgvector 0.7.0 ships HNSW", quote="q")])])
    assert any("as_of_date" in p for p in ledger_checks.provenance_fields(led))


def test_ledger_lint_flags_asymmetric_conflict():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="t", quote="q", contested=True)])])
    assert any("no contradicting claim" in p for p in ledger_checks.provenance_fields(led))


def test_ledger_lint_flags_overlong_quote():
    led = SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="t", quote=" ".join(["w"] * 20))])])
    assert any("words" in p for p in ledger_checks.provenance_fields(led))


# --- retrieval -----------------------------------------------------------------

def test_fetch_source_leads_skips_dropped_and_carries_seed_origin():
    leads = DiscoveryLeads(source_leads=[
        SourceLead(id="sl-1", url="https://a.org", status="accepted", provenance_origin="user"),
        SourceLead(id="sl-2", url="https://b.org", status="dropped"),
    ])
    fetcher = ReplayFetcher({"https://a.org": doc(url="https://a.org")})
    result = fetch_source_leads(leads, fetcher)
    assert [d.url for d in result.documents] == ["https://a.org"]
    assert result.documents[0].provenance_origin == "user"


def test_unfetchable_lead_is_recorded_not_silently_dropped():
    leads = DiscoveryLeads(source_leads=[SourceLead(id="sl-1", url="https://gone.org")])
    result = fetch_source_leads(leads, ReplayFetcher({}))
    assert result.documents == [] and result.unresolved == ["https://gone.org"]


def test_retrieval_is_bounded_by_max_iterations():
    """A question that will not reach min_sources is left short, not looped on forever."""
    plan = ResearchPlan(topic="t", questions=[Question(id="Q1", text="q")])
    calls = {"n": 0}

    def searcher(query):
        calls["n"] += 1
        return ["https://nowhere.org"]

    result = retrieve_for_questions(plan, ReplayFetcher({}), searcher, max_iterations=3)
    assert calls["n"] == 3 and result.iterations["Q1"] == 3


def test_retrieval_stops_once_min_sources_reached():
    plan = ResearchPlan(topic="t", questions=[Question(id="Q1", text="q")])
    corpus = {f"https://s{i}.org": doc(url=f"https://s{i}.org") for i in range(4)}

    result = retrieve_for_questions(
        plan, ReplayFetcher(corpus), lambda q: list(corpus), max_iterations=6, min_sources=2)
    assert len(result.documents) == 2 and result.iterations["Q1"] == 1
    assert all("Q1" in d.served_questions for d in result.documents)


# --- coverage (R-EVID-03) -----------------------------------------------------

def test_coverage_marks_covered_thin_and_open():
    plan = ResearchPlan(topic="t", questions=[
        Question(id="Q1", text="a"), Question(id="Q2", text="b"), Question(id="Q3", text="c")])
    docs = [doc(url="https://a.org"), doc(url="https://b.org")]
    for d in docs:
        d.served_questions = ["Q1"]
    plan = coverage.update_plan_coverage(plan, docs, iterations={"Q2": 6, "Q3": 1})
    status = {q.id: q.coverage.status.value for q in plan.questions}
    assert status == {"Q1": "covered", "Q2": "thin", "Q3": "open"}
    assert coverage.thin_questions(plan) == ["Q2"]


@pytest.mark.parametrize("text,expected", [
    ("HNSW is 3x faster than IVF", True),
    ("recall climbs to 92%", True),
    ("chunking is the unit of retrieval", False),
])
def test_performance_claim_detection(text, expected):
    assert coverage.is_performance_claim(text) is expected


def test_vendor_only_performance_claim_is_flagged():
    """Repeating a vendor benchmark as established fact is the failure R-EVID-03 counters."""
    led = SourceLedger(sources=[Source(source_id="s-v", type="vendor", claims=[
        Claim(claim_id="C1", text="our index is 5x faster", quote="q")])])
    assert coverage.uncorroborated_performance_claims(led)


def test_independently_corroborated_performance_claim_passes():
    led = _two_source_ledger("index A is 3x faster than B", "index A is 3x faster than B")
    led = corroborate(led)
    assert coverage.uncorroborated_performance_claims(led) == []


def test_coverage_report_exit_condition():
    plan = ResearchPlan(topic="t", questions=[Question(id="Q1", text="a")])
    docs = [doc(url="https://a.org"), doc(url="https://b.org")]
    for d in docs:
        d.served_questions = ["Q1"]
    plan = coverage.update_plan_coverage(plan, docs)
    report = coverage.coverage_report(plan, SourceLedger())
    assert report["exit_ok"] and report["covered"] == ["Q1"]


# --- recency (R-GROUND-04) ----------------------------------------------------

def test_version_sweep_is_flag_only_without_a_lookup():
    led = SourceLedger(sources=[Source(source_id="s", claims=[
        Claim(claim_id="C1", text="pgvector 0.7.0 adds HNSW", quote="q")])])
    findings = recency.sweep(led)
    assert [(f.technology, f.cited_version) for f in findings] == [("pgvector", "0.7.0")]
    assert findings[0].stale is None
    assert "unverifiable offline" in findings[0].describe()


@pytest.mark.parametrize("text,expected", [
    ("pgvector 0.7.0 adds HNSW", [("pgvector", "0.7.0")]),      # lowercase names are the norm
    ("numpy v2.1 changed the API", [("numpy", "2.1")]),          # explicit v marker
    ("spaCy 3.7 ships a new parser", [("spaCy", "3.7")]),        # internal capital
    ("recall reached 0.8 on the eval", []),                       # a measurement, not a version
    ("see section 2.1 for details", []),
])
def test_version_extraction_distinguishes_versions_from_measurements(text, expected):
    led = SourceLedger(sources=[Source(source_id="s", claims=[
        Claim(claim_id="C1", text=text, quote="q")])])
    assert [(f.technology, f.cited_version) for f in recency.extract_versions(led)] == expected


def test_version_sweep_detects_staleness_with_a_lookup():
    led = SourceLedger(sources=[Source(source_id="s", claims=[
        Claim(claim_id="C1", text="Pgvector 0.5.0 is current", quote="q")])])
    findings = recency.sweep(led, lambda tech: "0.8.0")
    assert findings[0].stale is True and recency.stale_findings(findings)


# --- curation (G1 / G6 land here) ---------------------------------------------

def _curation_ledger():
    return SourceLedger(sources=[
        Source(source_id="s-a", claims=[
            Claim(claim_id="C1", text="chunking bounds achievable retrieval recall", quote="q"),
            Claim(claim_id="C2", text="achievable retrieval recall is bounded by chunking", quote="q"),
        ]),
        Source(source_id="s-b", claims=[
            Claim(claim_id="C3", text="rerankers reorder candidate documents", quote="q", contested=True,
                  contradicts=["C1"]),
        ]),
    ])


def test_concept_map_is_derived_from_the_ledger():
    cm = curate.curate_concept_map(_curation_ledger())
    assert len(cm.concepts) == 2
    assert {cid for c in cm.concepts for cid in c.claim_ids} == {"C1", "C2", "C3"}


def test_salience_tracks_claim_frequency():
    cm = curate.curate_concept_map(_curation_ledger())
    by_size = sorted(cm.concepts, key=lambda c: -len(c.claim_ids))
    assert by_size[0].salience == 1.0 and by_size[1].salience < 1.0


def test_contested_claims_make_their_concept_contested():
    cm = curate.curate_concept_map(_curation_ledger())
    contested = [c for c in cm.concepts if "C3" in c.claim_ids]
    assert contested[0].epistemic_status.value == "contested"


def test_stub_curator_leaves_the_anchor_empty_rather_than_inventing_one():
    """A fabricated anchor would pass the R-XREF-04 tautology lint while being the exact failure
    that rule exists to catch."""
    cm = curate.curate_concept_map(_curation_ledger())
    assert all(c.home_anchor is None for c in cm.concepts)


def test_outline_seed_orders_by_salience_without_a_user_structure():
    seed = curate.outline_seed(curate.curate_concept_map(_curation_ledger()))
    assert [s["salience"] for s in seed] == sorted((s["salience"] for s in seed), reverse=True)
    assert all(s["maps_to"] is None for s in seed)


def test_outline_seed_honors_user_structure_in_order():
    """G6: the user's entries ARE the sections, in their order, each carrying maps_to."""
    cm = curate.curate_concept_map(_curation_ledger())
    seed = curate.outline_seed(cm, {"user_structure": ["Reranking behaviour", "Chunking recall"]})
    assert [s["maps_to"] for s in seed] == ["Reranking behaviour", "Chunking recall"]
    assert sum(len(s["concepts"]) for s in seed) == len(cm.concepts)


def test_outline_seed_assignment_is_deterministic():
    cm = curate.curate_concept_map(_curation_ledger())
    params = {"user_structure": ["Chunking recall", "Reranking behaviour"]}
    assert curate.outline_seed(cm, params) == curate.outline_seed(cm, params)
