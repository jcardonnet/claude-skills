"""Grounding-loop tests (Prompt 6 / Stage C).

The load-bearing one is the R-DISC-01 firewall: a discovery lead is a pointer, and a claim only
becomes provenance when its quote is found verbatim in a document we actually fetched. Everything
else here — corroboration, recency, coverage, curation — is the deterministic machinery that turns
fetched pages into a ledger the primer can be held to.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

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
from research.grouping import Group, resolve_groups, unnamed_singletons
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


def test_fetch_source_leads_carries_the_lead_type_without_overwriting_a_fetched_one():
    """Discovery's classification survives the fetch, but never overrides what the fetcher derived.

    `claim_extractor` copies `doc.source_type` into `Source.type`, and
    `coverage.vendor_independence` counts sources whose type is not a vendor one. When the lead's
    type was dropped here, every source reached both untyped: the critics lost the signal, and the
    vendor check passed because nothing looked like a vendor.
    """
    leads = DiscoveryLeads(source_leads=[
        SourceLead(id="sl-1", url="https://a.org", type="standard"),
        SourceLead(id="sl-2", url="https://b.org", type="vendor"),
        SourceLead(id="sl-3", url="https://c.org"),
    ])
    fetcher = ReplayFetcher({
        "https://a.org": doc(url="https://a.org"),
        "https://b.org": doc(url="https://b.org", source_type="docs"),
        "https://c.org": doc(url="https://c.org"),
    })
    result = fetch_source_leads(leads, fetcher)
    by_url = {d.url: d.source_type for d in result.documents}
    assert by_url["https://a.org"] == "standard"   # lead type fills the gap
    assert by_url["https://b.org"] == "docs"       # fetcher-derived type wins
    assert by_url["https://c.org"] is None         # neither knew; stays honest


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


# --- the live fetcher (Stage G seam) -----------------------------------------
# Everything here is hermetic. The network path is deliberately NOT tested: a test that depends on
# what a remote host served today is a flake, and the whole reason `freeze_corpus` exists is so the
# network is touched once and replayed thereafter.

def test_html_to_text_strips_chrome_and_keeps_prose():
    from research.http_fetcher import html_to_text
    text = html_to_text(
        "<html><head><title>T</title><style>p{color:red}</style></head>"
        "<body><nav>skip me</nav><p>Chunking bounds recall.</p>"
        "<script>ignored()</script><footer>also skip</footer></body></html>")
    assert "Chunking bounds recall." in text
    assert "ignored()" not in text and "color:red" not in text
    assert "skip me" not in text and "also skip" not in text


def test_fetcher_refuses_non_http_schemes_without_touching_the_network():
    """A lead is an untrusted pointer (R-DISC-01). file:// would read the local disk and present it
    as a fetched source, which is the firewall failing open in the worst possible direction."""
    from research.http_fetcher import HttpFetcher
    fetcher = HttpFetcher()
    assert fetcher("file:///etc/passwd") is None
    assert "unsupported scheme" in fetcher.refused["file:///etc/passwd"]


def test_freeze_corpus_roundtrips_through_replayfetcher(tmp_path):
    """Fetch live once, freeze, replay forever — the property eval's reproducibility rests on.
    source_id and content_hash must survive, since the ledger keys claims by them."""
    from research.http_fetcher import freeze_corpus
    original = Document(url="https://example.org/a/", text="Chunking bounds recall.\nSecond line.",
                        title="A", retrieved_at="2026-01-01")
    replay = ReplayFetcher(corpus_dir=freeze_corpus([original], tmp_path / "corpus"))
    back = replay("https://example.org/a/")
    assert back is not None
    assert back.text == original.text
    assert back.source_id == original.source_id
    assert back.content_hash == original.content_hash


_DETERMINISM_PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
from ir.schema import Claim, Source, SourceLedger
from research import curate

ledger = SourceLedger(sources=[
    Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="chunking bounds achievable retrieval recall", quote="q"),
        Claim(claim_id="C2", text="achievable retrieval recall is bounded by chunking", quote="q"),
    ]),
    Source(source_id="s-b", claims=[
        Claim(claim_id="C3", text="rerankers reorder candidate documents", quote="q",
              contested=True, contradicts=["C1"]),
    ]),
])
cm = curate.curate_concept_map(ledger)
seed = curate.outline_seed(cm, {"user_structure": ["Chunking recall", "Reranking behaviour"]})
print(json.dumps({"concepts": [c.concept_id for c in cm.concepts], "seed": seed}, sort_keys=True))
"""


def _curation_chain_under_hashseed(seed: str) -> str:
    """Run ledger -> concept-map -> outline-seed in a FRESH interpreter at a given PYTHONHASHSEED."""
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    proc = subprocess.run(
        [sys.executable, "-c", _DETERMINISM_PROBE, scripts],
        capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONHASHSEED": seed},
    )
    return proc.stdout.strip()


def test_curation_chain_is_deterministic_across_hash_seeds():
    """Determinism here is load-bearing, not tidiness: R-DISC-04 / R-CONV-02 require the escalate
    loop to terminate reproducibly, so the same ledger must always yield the same outline seed.

    This used to assert `outline_seed(cm, p) == outline_seed(cm, p)` — the same expression on both
    sides. That can only fail if the function mutates global state, and is blind to the failure it
    was written to catch: set/dict iteration order over strings is stable WITHIN a process and
    varies only with PYTHONHASHSEED, so two calls in one interpreter always agree even when the
    chain is order-dependent. Separate interpreters at different seeds are what actually probes it.
    """
    outputs = {_curation_chain_under_hashseed(s) for s in ("0", "1", "524287")}
    assert len(outputs) == 1, "curation chain varied with PYTHONHASHSEED:\n" + "\n".join(sorted(outputs))


def _robots_fetcher(monkeypatch, outcome):
    """An HttpFetcher whose robots.txt request produces `outcome` — an exception, or a body."""
    import urllib.request

    from research.http_fetcher import HttpFetcher

    calls = {}

    class _Response:
        def read(self, _n=None):
            return outcome if isinstance(outcome, bytes) else b""

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def _urlopen(request, timeout=None, **_k):
        calls["timeout"] = timeout
        calls["url"] = getattr(request, "full_url", request)
        if isinstance(outcome, Exception):
            raise outcome
        return _Response()

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    return HttpFetcher(), calls


def _http_error(code, reason):
    import urllib.error

    return urllib.error.HTTPError("https://example.org/robots.txt", code, reason, {}, None)


def test_the_robots_fetch_is_bounded_by_the_same_timeout_as_the_page(monkeypatch):
    """`RobotFileParser.read()` calls urlopen with NO timeout, so `timeout_s` governed the page
    fetch and nothing governed this one — a single unresponsive origin hung the campaign."""
    fetcher, calls = _robots_fetcher(monkeypatch, b"User-agent: *\nAllow: /\n")
    assert fetcher._allowed("https://example.org/page") is True
    assert calls["url"] == "https://example.org/robots.txt"
    assert calls["timeout"] == fetcher.timeout_s


@pytest.mark.parametrize("label,make_outcome,expected", [
    # RFC 9309 §2.3.1: "unavailable" means assume complete disallow. All three read as ALLOW before.
    ("a network failure", lambda: __import__("urllib.error", fromlist=["x"]).URLError("no route"), False),
    ("a server error", lambda: _http_error(503, "Service Unavailable"), False),
    ("an access refusal", lambda: _http_error(403, "Forbidden"), False),
    # ...while a 404 genuinely means no rules were published, so everything is permitted
    ("no robots.txt at all", lambda: _http_error(404, "Not Found"), True),
    ("an explicit allow", lambda: b"User-agent: *\nAllow: /\n", True),
    ("an explicit disallow", lambda: b"User-agent: *\nDisallow: /\n", False),
])
def test_an_undeterminable_robots_txt_denies_rather_than_permits(label, make_outcome, expected,
                                                                 monkeypatch):
    """The check exists to keep the crawler polite, and it resolved every failure — timeout, reset,
    5xx, decode error — to "not a prohibition", then cached that per origin for the whole run."""
    fetcher, _ = _robots_fetcher(monkeypatch, make_outcome())
    assert fetcher._allowed("https://example.org/page") is expected, label


def test_robots_is_rechecked_after_a_redirect(monkeypatch):
    """robots was checked against the URL we ASKED for, but urllib follows redirects silently — so a
    301 onto a disallowed path was fetched and kept. The redirect target is the page actually
    stored, so it is the one the permission has to cover."""
    from research.http_fetcher import HttpFetcher

    fetcher = HttpFetcher()
    allowed_calls = []

    def _allowed(url):
        allowed_calls.append(url)
        return "/private/" not in url

    monkeypatch.setattr(fetcher, "_allowed", _allowed)

    class _Response:
        headers: ClassVar[dict] = {"Content-Type": "text/html"}

        def read(self, _n):
            return b"<html><body><p>secret</p></body></html>"

        def geturl(self):
            return "https://example.org/private/page"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: _Response())

    assert fetcher("https://example.org/public/page") is None
    assert "redirect" in fetcher.refused["https://example.org/public/page"]
    assert allowed_calls == ["https://example.org/public/page", "https://example.org/private/page"]


# The verbatim body Cloudflare served for `link.springer.com/article/10.1186/s13063-015-0958-9`
# during spec-05's 2026-08-21 campaign. It went into the corpus, an extractor read claims out of it,
# and `fetch_source_leads` stamped it `primary_paper` because that is what the lead had claimed.
WALL = ("Client Challenge\n"
        "A required part of this site couldn\u2019t load. This may be due to a browser extension, "
        "network issues, or browser settings. Please check your connection, disable any ad blockers, "
        "or try using a different browser.")

PAGE = ("Adaptive designs let a trial modify itself while it is running: an interim analysis can "
        "drop an arm, re-estimate the sample size, or stop early for futility, and the design fixes "
        "in advance which of those moves is allowed and on what evidence. The type I error rate is "
        "preserved by spending it across the looks rather than by pretending the looks did not "
        "happen. What the method cannot do is rescue a trial whose endpoint was wrong, and "
        "regulators ask for the adaptation rule before the first patient is enrolled.")


def _page_fetcher(monkeypatch, text, **kwargs):
    """An HttpFetcher that serves `text` as an HTML page, with robots.txt out of the way."""
    from research.http_fetcher import HttpFetcher

    fetcher = HttpFetcher(**kwargs)
    monkeypatch.setattr(fetcher, "_allowed", lambda _url: True)

    class _Response:
        headers: ClassVar[dict] = {"Content-Type": "text/html"}

        def read(self, _n=None):
            return f"<html><body><p>{text}</p></body></html>".encode()

        def geturl(self):
            return "https://example.org/page"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: _Response())
    return fetcher


@pytest.mark.parametrize("label,text,kept", [
    ("a bot wall", WALL, False),
    ("a cookie notice", "Cookies must be enabled. Please enable cookies and reload the page.", False),
    ("a nav-only shell", ("Baggage | OpenTelemetry View Markdown View page source Edit this page "
                          "Was this page helpful? Yes No"), False),
    ("an actual page", PAGE, True),
])
def test_a_body_too_short_to_be_the_document_is_refused_at_the_fetch(label, text, kept, monkeypatch):
    """G17 class 1. Returning bytes is not the same as returning the page that was sought, and by
    the time the difference matters it is gone: `fetch_source_leads` stamps every Document it keeps
    with its lead\u2019s declared type, so a wall enters the ledger wearing whatever credibility tier
    discovery guessed for the paper behind it. spec-05 shipped 15 claims of interstitial
    troubleshooting text that way.

    The threshold is measured, not chosen. Across the 449 documents of the four committed campaign
    corpora the word-count band 62\u201392 is EMPTY \u2014 below it everything is chrome, and the thinnest
    document carrying a real sentence is 93 words long.
    """
    from research.http_fetcher import MIN_CONTENT_WORDS

    fetcher = _page_fetcher(monkeypatch, text)
    got = fetcher("https://example.org/page")
    assert (got is not None) is kept, label
    if kept:
        assert len(text.split()) > MIN_CONTENT_WORDS       # the sample really is over the line
    else:
        assert "below the" in fetcher.refused["https://example.org/page"]


def test_the_length_gate_is_a_dial_and_emptiness_is_refused_underneath_it(monkeypatch):
    """Two separate refusals that would otherwise collapse into one.

    `min_words=0` restores the pre-gate behaviour exactly \u2014 a campaign that wants every byte it can
    get can have it \u2014 but an empty extraction is still not a document, and it keeps its own distinct
    reason so a corpus audit can tell "the server sent chrome" from "the server sent nothing".
    """
    assert _page_fetcher(monkeypatch, WALL, min_words=0)("https://example.org/page") is not None

    empty = _page_fetcher(monkeypatch, "   ", min_words=0)
    assert empty("https://example.org/page") is None
    assert empty.refused["https://example.org/page"] == "fetched but empty after text extraction"


# --- the model half of the grounding loop (ClaudeClaimExtractor) -------------
# Hermetic: the CLI is stubbed. What is pinned here is the division of labour — the extractor
# PROPOSES and never verifies, so the gate stays the single place a quote is checked. Until this
# module existed the only Extractor in the tree scanned for `CLAIM:` lines, which no fetched page
# contains, so every offline ledger was hand-authored or empty.

def _stub_extractor(payloads):
    from research.claude_claim_extractor import ClaudeClaimExtractor

    class _Cli:
        calls = 0
        spend_usd = 0.0

        def __init__(self):
            self.seen = []

        def result_json(self, instruction):
            self.seen.append(instruction)
            return payloads[min(len(self.seen) - 1, len(payloads) - 1)]

    return ClaudeClaimExtractor(cli=_Cli())


def test_extractor_proposes_without_verifying_so_the_gate_stays_the_only_check():
    """A fabricated quote must reach `anchor_claims` and die there, not be filtered upstream.

    Two gates that can disagree is worse than one gate that cannot: if the extractor also checked,
    a bug in either check would be invisible from the other side.
    """
    doc = Document(url="https://example.org/a", text="Spans carry a start and an end timestamp.")
    extractor = _stub_extractor([{"claims": [
        {"text": "real", "quote": "Spans carry a start", "confidence": "high"},
        {"text": "invented", "quote": "spans are free", "confidence": "high"},
    ]}])

    proposals = extractor(doc)
    assert len(proposals) == 2                      # the extractor passed BOTH through

    kept, rejected = anchor_claims(proposals, doc)
    assert [c.text for c in kept] == ["real"]
    assert "quote not found" in rejected[0]


def test_location_is_measured_not_asked_for():
    """A model asked where a quote sits answers plausibly. The offset is a fact about the text."""
    doc = Document(url="https://example.org/a", text="Alpha beta.\n\nGamma delta epsilon.")
    extractor = _stub_extractor([{"claims": [
        {"text": "found", "quote": "Gamma delta", "location": "line 500"},
        {"text": "absent", "quote": "not present here", "location": "line 1"},
    ]}])

    by_text = {p["text"]: p["location"] for p in extractor(doc)}
    assert by_text["found"] == "char 12 of 32 (normalized)"   # normalized: the blank line is one space
    # None, not a guess: the gate is about to reject this one, and a location on a rejected claim
    # would be a coordinate into a document that does not contain it.
    assert by_text["absent"] is None


def test_a_long_document_is_chunked_and_the_chunking_is_bounded():
    from research.claude_claim_extractor import CHUNK_CHARS, MAX_CHUNKS, _chunks

    body = "\n\n".join(["paragraph " + "x" * 500] * 200)
    chunks = _chunks(body)
    assert len(chunks) == MAX_CHUNKS                       # bounded, not exhaustive
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert "".join(c.replace(" ", "") for c in chunks).count("paragraph") == sum(
        c.count("paragraph") for c in chunks)              # no overlap: no claim counted twice


def test_an_extraction_failure_is_a_document_with_no_claims_not_a_dead_run():
    from research.claude_claim_extractor import ClaudeClaimExtractor
    from utils.claude_cli import CliUnavailable

    class _DeadCli:
        calls = 0
        spend_usd = 0.0

        def result_json(self, _instruction):
            raise CliUnavailable("simulated outage")

    extractor = ClaudeClaimExtractor(cli=_DeadCli())
    doc = Document(url="https://example.org/a", text="Spans carry a timestamp.")
    assert extractor(doc) == []
    assert "simulated outage" in extractor.errors[0]       # recorded, not swallowed


# --- the grouping gate (research/grouping.py) --------------------------------
# Concept grouping and corroboration ask one question — "which of these claims say the same
# thing?" — and both used to answer it with word overlap. Spec-03's first real campaign is the
# measurement: 271 grounded claims became 249 single-claim concepts, 0 of them corroborated. The
# model proposes now. What is pinned below is that it still does not DECIDE: every property here
# holds no matter what the model returns, which is the only reason a model is allowed near the
# evidence base at all.

GATE_CLAIMS = [("C1", "chunking bounds recall"),
               ("C2", "recall is bounded by chunking"),
               ("C3", "rerankers reorder candidates")]


def test_the_gate_drops_a_claim_id_that_is_not_in_the_ledger():
    """A confabulated id would otherwise invent provenance out of nothing."""
    groups, rejected = resolve_groups(
        [{"claim_ids": ["C1", "C99"], "canonical_term": "chunking"}], GATE_CLAIMS)
    assert groups[0].claim_ids == ["C1"]
    assert "C99" in rejected[0] and "not in the ledger" in rejected[0]


def test_a_claim_joins_at_most_one_group_however_often_it_is_proposed():
    """Salience is claims-per-concept over the largest concept. A claim counted twice inflates both
    ends of that ratio, and R-ARCH-06 spends depth on the result."""
    groups, rejected = resolve_groups(
        [{"claim_ids": ["C1", "C2"], "canonical_term": "chunking"},
         {"claim_ids": ["C2", "C3"], "canonical_term": "reranking"}], GATE_CLAIMS)
    assert [g.claim_ids for g in groups] == [["C1", "C2"], ["C3"]]
    assert sum(len(g.claim_ids) for g in groups) == len(GATE_CLAIMS)
    assert any("already grouped" in r for r in rejected)


def test_two_groups_with_one_name_are_one_concept():
    """R-VOCAB-01 (A) wants canonical terms unique across concepts. Naming two groups identically
    IS the model saying they are one, so merging makes the rule true by construction rather than
    leaving a lint to report it after the map is built."""
    groups, rejected = resolve_groups(
        [{"claim_ids": ["C1"], "canonical_term": "chunking", "aliases": ["segmentation"]},
         {"claim_ids": ["C2"], "canonical_term": "Chunking", "aliases": ["windowing"]},
         {"claim_ids": ["C3"], "canonical_term": "reranking"}], GATE_CLAIMS)
    assert [g.canonical_term for g in groups] == ["chunking", "reranking"]
    assert groups[0].claim_ids == ["C1", "C2"]
    assert groups[0].aliases == ["segmentation", "windowing"]
    assert any("repeats an earlier group" in r for r in rejected)


def test_a_claim_nobody_grouped_becomes_a_singleton_not_a_deletion():
    """Silently dropping unmentioned claims would shrink the evidence base every time the model
    got lazy, and shrink it invisibly. An unmerged claim is a fact about the grouping, not a
    reason to stop grounding it."""
    groups, rejected = resolve_groups(
        [{"claim_ids": ["C1"], "canonical_term": "chunking"}], GATE_CLAIMS)
    assert [g.claim_ids for g in groups] == [["C1"], ["C2"], ["C3"]]
    assert "2 claim(s)" in rejected[0]


def test_a_singleton_is_named_from_meaning_not_from_a_digit_that_sorts_first():
    """The companion to the test above: keeping an unmerged claim is only honest if the concept it
    becomes is *named* honestly.

    Both strings are verbatim from the 2026-08-20 spec-03 ledger, and both really did produce the
    concepts "000 application" and "600 built-in". "10,000" tokenizes to "10" and "000"; "10" is
    below the length floor and "000" is not, and with a single claim every count ties at 1, so the
    alphabetical tiebreak handed the concept its name from the inside of a number. canonical_term
    is not cosmetic — it seeds concept_id, it is what R-VOCAB-01 checks for uniqueness, and
    assign_section scores it against the user's structure, so a nonsense name mis-files the concept
    as well as mis-labelling it.
    """
    name = curate.StubCurator().name_concept
    assert name([("A microservices application handling 10,000 requests per second generates "
                  "hundreds of thousands of spans per second.")])[0] == "microservices application"
    assert name([("Datadog has 600 or more built-in integrations for services and "
                  "platforms.")])[0] == "integrations platforms"


def test_the_singleton_the_grouper_could_not_name_is_the_one_worth_looking_at():
    """G17 class 1, read off the grouping instead of off the page.

    A grouper that saw every claim in the corpus, put THIS one with nothing, and could not say what
    it was about either has answered a question: the claim shares no subject with the rest of the
    evidence. `resolve_groups` was computing that and `curate_concept_map` was discarding it \u2014 by
    the time the artifact exists the tell is gone, because StubCurator's word-frequency fallback has
    already supplied a name ("settings browser", "requires content") that only LOOKS like an answer.

    The empty term is the signal; the salad is the symptom. So the test is structural: a singleton
    the grouper named is not flagged, and a group of two is not a singleton however it was named.
    """
    groups = [Group(claim_ids=["C1", "C2"]),                          # corroboration: no name wanted
              Group(claim_ids=["C3"], canonical_term="reranking"),    # named \u2014 the grouper had an answer
              Group(claim_ids=["C4"])]                                # orphaned AND unnameable
    assert unnamed_singletons(groups) == ["C4"]
    assert unnamed_singletons([]) == []


def test_a_source_stranded_in_every_claim_is_reported_and_a_mostly_stranded_one_is_not():
    """The cut is "all of them", and it has no threshold to tune because that is where spec-05's
    real campaign separates: the five sources at 100% are the five bot walls, and the worst GENUINE
    source \u2014 a Bayesian dose-finding paper full of one-off specifics \u2014 sits at 9 of 20.

    `w-*` below is a wall's whole contribution; `p-*` is that paper, shrunk to the same ratio. Any
    threshold loose enough to catch a chatty wall would take the paper with it, so the roll-up
    refuses to be a percentage.
    """
    groups = [Group(claim_ids=["w1"]), Group(claim_ids=["w2"]),
              Group(claim_ids=["p1"]), Group(claim_ids=["p2"]),
              Group(claim_ids=["p3", "p4"], canonical_term="dose escalation")]
    claim_source = {"w1": "s-wall", "w2": "s-wall",
                    "p1": "s-paper", "p2": "s-paper", "p3": "s-paper", "p4": "s-paper"}
    assert curate.ungrouped_sources(groups, claim_source) == [
        {"source_id": "s-wall", "claims": 2, "claim_ids": ["w1", "w2"]}]


def test_stranded_sources_reach_the_campaign_report_only_when_a_caller_asks_for_them():
    """Advisory, never a gate \u2014 the claims stay in the ledger and the concept-map is unchanged.

    It cannot be a gate for a structural reason worth pinning: `LexicalGrouper`, the default offline
    path, names nothing at all, so on `--lexical-grouping` every singleton is flagged and the signal
    means nothing. Only a naming grouper makes the empty term informative, which is why the stub
    below supplies one and why the parameter is opt-in rather than always-on.
    """
    def grouper(_claims, _params):
        return [{"claim_ids": ["C1", "C2"], "canonical_term": "chunking recall"}]

    stranded: list[dict] = []
    cm = curate.curate_concept_map(_curation_ledger(), grouper=grouper, stranded=stranded)
    assert stranded == [{"source_id": "s-b", "claims": 1, "claim_ids": ["C3"]}]
    assert {cid for c in cm.concepts for cid in c.claim_ids} == {"C1", "C2", "C3"}

    assert curate.curate_concept_map(_curation_ledger(), grouper=grouper).concepts == cm.concepts


def test_a_home_anchor_that_restates_its_own_concept_never_reaches_the_concept_map():
    """R-XREF-04, enforced where the anchor is admitted rather than only where it is audited.

    The last assertion is the point: the gate and `home_anchor_distinct` share one predicate, so an
    anchor the gate lets through cannot be one the lint later rejects. Two copies of "does this
    restate itself" would drift, and the drift strands a finished concept-map.
    """
    from checks._base import LintContext
    from checks.univocity_terms import home_anchor_distinct
    from ir.schema import DocumentIR

    def _tautology(claims, _params):
        return [{"claim_ids": [cid for cid, _ in claims],
                 "canonical_term": "cross-encoder reranking",
                 "home_anchor": "reranking", "fidelity_boundary": "the cost model differs"}]

    notes: list[str] = []
    cm = curate.curate_concept_map(_curation_ledger(), grouper=_tautology, notes=notes)
    assert not cm.concepts[0].home_anchor          # stripped, not shipped as a bridge
    assert not cm.concepts[0].fidelity_boundary    # a boundary with no bridge is orphaned prose
    assert any("R-XREF-04" in n for n in notes)
    assert home_anchor_distinct(LintContext(ir=DocumentIR(sections=[]), concept_map=cm)) == []


# --- group-based corroboration (R-GROUND-05) ---------------------------------

def _three_claim_ledger():
    return SourceLedger(sources=[
        Source(source_id="s-a", claims=[Claim(claim_id="C1", text="alpha", quote="q"),
                                        Claim(claim_id="C2", text="beta", quote="q")]),
        Source(source_id="s-b", claims=[Claim(claim_id="C3", text="gamma", quote="q")]),
    ])


def test_group_corroboration_counts_distinct_sources_not_claims():
    """Three claims, two sources, one asserted fact — the support is 2. Counting claims would let a
    single wordy source corroborate itself, which is exactly what R-GROUND-05 exists to prevent."""
    assert corroborate(_three_claim_ledger()).sources[0].claims[0].corroboration_count is None
    led = corroborate(_three_claim_ledger(),
                      grouper=lambda claims, _p: [{"claim_ids": [c for c, _ in claims]}])
    c1, c2 = led.sources[0].claims
    assert c1.corroboration_count == 2 and c1.corroborated_by == ["s-b"]
    assert c2.corroborated_by == ["s-b"]
    assert led.sources[1].claims[0].corroborated_by == ["s-a"]


def test_a_group_drawn_from_one_source_corroborates_nothing():
    led = corroborate(SourceLedger(sources=[Source(source_id="s-a", claims=[
        Claim(claim_id="C1", text="alpha", quote="q"),
        Claim(claim_id="C2", text="beta", quote="q")])]),
        grouper=lambda claims, _p: [{"claim_ids": [c for c, _ in claims]}])
    assert all(c.corroboration_count is None for c in led.sources[0].claims)


def test_the_corroboration_grouper_is_told_which_source_each_claim_came_from():
    """So it can skip candidate sets it could never learn anything from — see the blocking test."""
    seen: dict = {}

    def _grouper(_claims, params):
        seen.update(params.get("claim_sources") or {})
        return []

    corroborate(_curation_ledger(), grouper=_grouper)
    assert seen == {"C1": "s-a", "C2": "s-a", "C3": "s-b"}


# --- the model half (research/claude_curator.py) -----------------------------
# Hermetic: the CLI is stubbed. These pin the plumbing — batching, reconciliation, blocking, and
# what an outage costs — not the model's judgement, which is not testable here and is not trusted.

def _stub_cli(payloads):
    class _Cli:
        calls = 0
        spend_usd = 0.0
        timeout_s = 420

        def __init__(self):
            self.seen = []

        def result_json(self, instruction, **_):
            self.seen.append(instruction)
            return payloads[min(len(self.seen) - 1, len(payloads) - 1)]

    return _Cli()


def test_the_concept_grouper_names_but_the_gate_still_decides():
    from research.claude_curator import ClaudeConceptGrouper

    grouper = ClaudeConceptGrouper(cli=_stub_cli([{"groups": [
        {"claim_ids": ["C1", "C2", "C404"], "canonical_term": "chunk granularity",
         "aliases": ["chunking"], "home_anchor": "record blocking",
         "fidelity_boundary": "no join key survives the split"}]}]))
    notes: list[str] = []
    cm = curate.curate_concept_map(
        _curation_ledger(), {"target_domain": "RAG", "home_domain": ["classical IR"]},
        grouper=grouper, notes=notes)

    first = cm.concepts[0]
    assert first.canonical_term == "chunk granularity" and first.claim_ids == ["C1", "C2"]
    assert first.home_anchor == "record blocking"          # distinct, so it survives the gate
    assert {cid for c in cm.concepts for cid in c.claim_ids} == {"C1", "C2", "C3"}
    assert any("C404" in n for n in notes)                 # invented id rejected, run continues
    assert "RAG" in grouper.cli.seen[0] and "classical IR" in grouper.cli.seen[0]


def test_batched_grouping_is_reconciled_by_one_merge_pass():
    """Two batches of one evidence base name one concept twice. Without the merge pass the
    duplicate survives to R-VOCAB-01 as two near-identical terms competing for the same claims."""
    from research.claude_curator import ClaudeConceptGrouper

    grouper = ClaudeConceptGrouper(max_claims_per_call=1, cli=_stub_cli([
        {"groups": [{"claim_ids": ["C1"], "canonical_term": "chunk granularity"}]},
        {"groups": [{"claim_ids": ["C2"], "canonical_term": "chunk sizing"}]},
        {"merge": [[1, 2]]},
    ]))
    proposals = grouper([("C1", "a"), ("C2", "b")], {})
    assert len(grouper.cli.seen) == 3                       # two batches + one reconciliation
    assert proposals == [{"claim_ids": ["C1", "C2"], "canonical_term": "chunk granularity",
                          "aliases": ["chunk sizing"]}]     # the absorbed name becomes an alias
    assert any("merge pass" in n for n in grouper.notes)


def test_the_corroboration_grouper_does_not_pay_to_judge_a_single_source_block():
    """Corroboration counts INDEPENDENT sources, so a candidate set from one source has no verdict
    worth buying. Blocking is what makes this affordable at 271 claims; this is what makes it cheap
    at the ones that block together but cannot corroborate."""
    from research.claude_curator import ClaudeCorroborationGrouper

    claims = [("C1", "chunking bounds achievable retrieval recall"),
              ("C2", "achievable retrieval recall is bounded by chunking"),
              ("C3", "rerankers reorder candidate documents")]
    same = ClaudeCorroborationGrouper(cli=_stub_cli([{"groups": [{"claim_ids": ["C1", "C2"]}]}]))
    assert same(claims, {"claim_sources": {"C1": "s-a", "C2": "s-a", "C3": "s-b"}}) == []
    assert same.cli.seen == []
    assert any("one source only" in n for n in same.notes)

    split = ClaudeCorroborationGrouper(cli=_stub_cli([{"groups": [{"claim_ids": ["C1", "C2"]}]}]))
    assert split(claims, {"claim_sources": {"C1": "s-a", "C2": "s-b", "C3": "s-b"}}) == [
        {"claim_ids": ["C1", "C2"]}]
    assert len(split.cli.seen) == 1        # C3 blocked alone and was never sent


def test_a_grouping_outage_leaves_honest_singletons_not_a_dead_run():
    from research.claude_curator import ClaudeConceptGrouper
    from utils.claude_cli import CliUnavailable

    class _DeadCli:
        calls = 0
        spend_usd = 0.0
        timeout_s = 420                                    # `_ask` doubles it on the retry

        def result_json(self, _instruction, **_):
            raise CliUnavailable("simulated outage")

    grouper = ClaudeConceptGrouper(cli=_DeadCli())
    cm = curate.curate_concept_map(_curation_ledger(), grouper=grouper)
    assert len(cm.concepts) == 3                           # ungrouped, but every claim still there
    assert "simulated outage" in grouper.errors[0]         # recorded, not swallowed


def test_a_grouping_call_lost_to_the_clock_is_retried_before_it_is_believed():
    """One slow call must not cost a whole batch its grouping.

    Spec-04's 2026-08-21 campaign is the measurement: concept batch 2 of 3 died on `claude CLI
    exceeded 420s`, batch 1 — an instruction built from the same 150 claims — had just succeeded,
    and the run still exited 0 with 215 "concepts" from 333 claims. Nothing about that batch was
    unanswerable; the clock ran out. The retry gets a longer ceiling because the evidence that we
    are near one is that we just hit it, and the first failure is recorded either way — a retry
    that rescues a run silently is a run whose latency is drifting invisibly.
    """
    from research.claude_curator import RETRY_TIMEOUT_FACTOR, ClaudeConceptGrouper
    from utils.claude_cli import CliUnavailable

    class _SlowOnceCli:
        calls = 0
        spend_usd = 0.0
        timeout_s = 420

        def __init__(self):
            self.ceilings: list = []

        def result_json(self, _instruction, *, timeout_s=None):
            self.ceilings.append(timeout_s)
            if len(self.ceilings) == 1:
                raise CliUnavailable("claude CLI exceeded 420s")
            return {"groups": [{"claim_ids": ["C1", "C2", "C3"], "canonical_term": "chunking",
                                "home_anchor": "a page of a book"}]}

    grouper = ClaudeConceptGrouper(cli=_SlowOnceCli())
    cm = curate.curate_concept_map(_curation_ledger(), grouper=grouper)

    assert len(cm.concepts) == 1                           # the retry's answer was used
    assert grouper.errors == []                            # a rescued call is not a failure
    assert any("retrying once" in n for n in grouper.notes)
    assert grouper.lost_claims == 0
    assert grouper.cli.ceilings == [None, 420 * RETRY_TIMEOUT_FACTOR]


def test_a_batch_that_proposes_nothing_is_counted_not_quietly_absorbed():
    """A silent batch and a batch of genuinely unique claims produce the SAME artifact.

    Either way every claim falls through `resolve_groups` to a singleton concept, and the concept
    map cannot tell the two apart afterwards. So the grouper counts the claims it lost at the point
    where it still knows — the driver is what refuses to write the result (see test_run_campaign).
    An empty `groups` list is counted alongside the outage because a call that answers nothing
    costs exactly as much as a call that never returned.
    """
    from research.claude_curator import ClaudeConceptGrouper

    grouper = ClaudeConceptGrouper(cli=_stub_cli([{"groups": []}]))
    cm = curate.curate_concept_map(_curation_ledger(), grouper=grouper)

    assert len(cm.concepts) == 3                           # indistinguishable from three uniques
    assert grouper.lost_claims == 3                        # which is why the count exists
    assert "no groups proposed" in grouper.errors[0]
