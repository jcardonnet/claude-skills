"""Discovery-campaign tests (Prompt 6a).

Two things are being pinned. First, the R-DISC-04 split: clustering, support counts, novelty and
saturation are pure functions, so the campaign's stopping decision is reproducible. Second, the
lints that read the campaign's audit trail (R-DISC-02/03/05/06).
"""
import json
from pathlib import Path

import pytest
import yaml

from checks import discovery as disc_checks
from ir.schema import DiscoveryLeads, DiscoveryLog, ResearchBrief, SourceLead, TopicLead
from research import discovery
from research.deep_research import ReplayBackend, brief_id, run_brief
from research.planner import (
    BRIEF_ARCHETYPES,
    WAVE_ARCHETYPES,
    front_load_campaign,
    re_front_load,
    route_seeds,
    triage_leads,
    wave_briefs,
    write_campaign,
)

# cwd-independent: CI runs pytest from the repo root, these tests live under the skill.
_TESTS = Path(__file__).resolve().parent
SKILL_ROOT = _TESTS.parent
SNAPSHOT = _TESTS / "fixtures" / "discovery-snapshot"


def tl(i, concept, **kw):
    return TopicLead(id=i, concept=concept, **kw)


def sl(i, url, **kw):
    return SourceLead(id=i, url=url, **kw)


def brief(wave="A", framing="structure", angle=None, sc=None, stance=None, bid=None):
    return ResearchBrief(wave=wave, framing=framing, angle=angle, source_class=sc,
                         stance=stance, brief_id=bid)


# --- deterministic metrics (R-DISC-04) ---------------------------------------

def test_cluster_merges_rephrased_topic_leads():
    leads = [tl("tl-1", "chunking bounds retrieval recall"),
             tl("tl-2", "retrieval recall is bounded by chunking")]
    assert len(discovery.cluster_leads(leads)) == 1


def test_cluster_keeps_distinct_urls_apart():
    """Two papers on one host share most URL tokens; fuzzy-matching them would collapse the
    source set, understate novelty, and stop the campaign early."""
    leads = [sl("sl-1", "https://example.org/papers/chunking-2024"),
             sl("sl-2", "https://example.org/papers/reranking-2024")]
    assert len(discovery.cluster_leads(leads)) == 2


def test_cluster_merges_urls_differing_only_cosmetically():
    leads = [sl("sl-1", "https://example.org/a"), sl("sl-2", "http://www.example.org/a/")]
    assert len(discovery.cluster_leads(leads)) == 1


def test_cluster_never_merges_across_lead_kinds():
    leads = [tl("tl-1", "example org chunking"), sl("sl-1", "https://example.org/chunking")]
    assert len(discovery.cluster_leads(leads)) == 2


def test_cluster_is_order_independent():
    leads = [tl("tl-3", "alpha beta gamma"), tl("tl-1", "delta epsilon zeta"),
             tl("tl-2", "alpha beta gamma delta")]
    a = [[x.id for x in c] for c in discovery.cluster_leads(leads)]
    b = [[x.id for x in c] for c in discovery.cluster_leads(list(reversed(leads)))]
    assert a == b


def test_support_count_counts_distinct_framings_not_mentions():
    """Five briefs sharing one framing are one blind spot, not five confirmations."""
    cluster = [tl("tl-1", "x", surfaced_by=["structure"]), tl("tl-2", "x", surfaced_by=["structure"]),
               tl("tl-3", "x", surfaced_by=["contrarian-seed"])]
    assert discovery.support_count(cluster) == 2


def test_support_count_resolves_brief_ids_to_framings():
    cluster = [tl("tl-1", "x", surfaced_by=["A-A1", "A-A6"])]
    briefs = [brief(bid="A-A1", framing="structure"), brief(bid="A-A6", framing="contrarian-seed")]
    assert discovery.support_count(cluster, briefs) == 2


def test_novelty_is_zero_when_everything_is_known():
    accepted = [tl("tl-1", "chunking bounds retrieval recall")]
    assert discovery.novelty([tl("tl-9", "chunking bounds retrieval recall")], accepted) == 0.0


def test_novelty_dedupes_within_the_wave():
    """Six briefs surfacing one idea is one new lead; counting it six times would keep
    novel_fraction high and run the campaign past saturation."""
    fresh = [tl(f"tl-{i}", "late interaction reranking helps") for i in range(6)]
    assert discovery.novelty(fresh, []) == pytest.approx(1 / 6)


def test_novelty_does_not_depend_on_the_order_the_briefs_returned():
    """The dedup is greedy and thresholded similarity is not transitive, so with A~B, B~C and A!~C
    the walk order changed the answer: [A,B,C] kept two leads, [B,A,C] kept one. A 2x swing in
    `novelty`, which is compared against SATURATION_THRESHOLD to decide whether the campaign stops —
    and `fresh` arrives in whatever order the briefs happened to come back in. R-DISC-04 is the
    claim that this decision is reproducible."""
    import itertools

    sim = discovery.resolve_similarity()
    a = tl("A", "leader line tracing for callouts")
    b = tl("B", "leader line tracing")
    c = tl("C", "line tracing")
    assert discovery.same_lead(a, b, sim) and discovery.same_lead(b, c, sim)
    assert not discovery.same_lead(a, c, sim), "this trio must be non-transitive to prove anything"

    answers = {len(discovery.novel_leads(perm, [])) for perm in itertools.permutations([a, b, c])}
    assert len(answers) == 1, f"input order changed the novelty count: {answers}"


def test_a_wave_that_returned_nothing_is_not_saturation():
    """`novel_fraction` is 0/0 for an empty wave, and reporting it as 0.0 put it below any threshold
    — so a dead research backend stopped the campaign on wave A, froze an empty snapshot, and wrote
    the most reassuring word available into the log."""
    log = DiscoveryLog(max_waves=3, saturation_threshold=0.15, terminal="saturated", waves=[
        {"wave": "A", "briefs": 5, "framing_cells": 5, "leads_total": 0, "leads_new": 0,
         "novel_fraction": 0.0, "decision": "stop"}])
    assert any("no leads at all" in p for p in disc_checks.saturation_terminal(log))

    log.terminal = "no_leads"
    assert disc_checks.saturation_terminal(log) == []

    # ...and the new label is not a free pass either: a wave that DID retrieve cannot claim it
    log.waves[-1].leads_total = 4
    assert any("returned 4 lead(s)" in p for p in disc_checks.saturation_terminal(log))


def test_saturation_reads_the_latest_wave():
    log = {"saturation_threshold": 0.15,
           "waves": [{"novel_fraction": 0.9}, {"novel_fraction": 0.1}]}
    assert discovery.saturation(log) is True
    log["waves"][-1]["novel_fraction"] = 0.4
    assert discovery.saturation(log) is False


def test_framing_diversity_counts_matrix_cells_not_briefs():
    same = [brief(framing="structure", angle="by-method-family") for _ in range(4)]
    assert discovery.framing_diversity(same) == 1
    varied = [brief(framing="structure"), brief(framing="debates"), brief(framing="adjacent-field")]
    assert discovery.framing_diversity(varied) == 3


def test_orthogonal_count():
    briefs = [brief(framing="structure"), brief(framing="contrarian-seed"), brief(framing="adjacent-field")]
    assert discovery.orthogonal_count(briefs) == 2


# --- seeds (R-DISC-06) --------------------------------------------------------

def test_route_seeds_splits_direct_from_directive():
    direct, directives = route_seeds([
        {"kind": "url", "ref": "https://example.org/x"},
        {"kind": "file", "ref": "uploads/spec.pdf"},
        {"kind": "author", "ref": "J. Doe"},
    ])
    assert [d["url"] for d in direct] == ["https://example.org/x", "uploads/spec.pdf"]
    assert all(d["provenance_origin"] == "user" for d in direct)
    assert [d["ref"] for d in directives] == ["J. Doe"]


def test_user_seed_is_exempt_from_triage_drop():
    class DropEverything:
        def assess_topic(self, topic, params): return {}
        def extract_leads(self, report, sources, brief): return {}
        def triage(self, clusters, params): return {c[0].id: "dropped" for c in clusters}

    seed = sl("sl-seed-0", "https://example.org/seed", provenance_origin="user")
    other = sl("sl-1", "https://example.org/other")
    out = triage_leads(discovery.cluster_leads([seed, other]), {}, DropEverything())
    by_id = {lead.id: lead for lead in out}
    assert by_id["sl-seed-0"].status == "accepted"     # R-DISC-06
    assert by_id["sl-1"].status == "dropped"


def test_high_salience_singleton_is_flagged_not_dropped():
    class DropEverything:
        def assess_topic(self, topic, params): return {}
        def extract_leads(self, report, sources, brief): return {}
        def triage(self, clusters, params): return {c[0].id: "dropped" for c in clusters}

    gem = tl("tl-1", "a rare finding", salience="high", surfaced_by=["contrarian-seed"])
    out = triage_leads(discovery.cluster_leads([gem]), {}, DropEverything())
    assert out[0].status == "flagged"


# --- the cascade --------------------------------------------------------------

def test_campaign_saturates_and_logs_its_trail():
    result = front_load_campaign("retrieval-augmented generation",
                                 {"target_domain": "retrieval-augmented generation", "seed": "J. Doe"},
                                 snapshot_dir=SNAPSHOT)
    assert result.log.terminal == "saturated"
    assert [w.decision for w in result.log.waves][-1] == "stop"
    fractions = [w.novel_fraction for w in result.log.waves]
    assert fractions == sorted(fractions, reverse=True), "novelty must fall as the campaign converges"
    assert fractions[-1] < discovery.SATURATION_THRESHOLD


def test_campaign_is_reproducible():
    """Same snapshot -> same leads and same stopping wave. Without this the eval cannot replay."""
    kw = dict(params={"target_domain": "retrieval-augmented generation", "seed": "J. Doe"},
              snapshot_dir=SNAPSHOT)
    a = front_load_campaign("rag", **kw)
    b = front_load_campaign("rag", **kw)
    assert [w.model_dump() for w in a.log.waves] == [w.model_dump() for w in b.log.waves]
    assert [lead.id for lead in a.leads.accepted()] == [lead.id for lead in b.leads.accepted()]


def test_campaign_never_exceeds_max_waves():
    result = front_load_campaign("rag", {"target_domain": "rag"}, snapshot_dir=SNAPSHOT)
    assert len(result.log.waves) <= discovery.MAX_WAVES


def test_re_front_load_skips_wave_a():
    """Re-sweeping the landscape is how an escalate loop burns budget without new information."""
    result = re_front_load("rag", {"concept": "late-interaction reranking"},
                           {"target_domain": "rag"}, snapshot_dir=SNAPSHOT)
    assert {w.wave for w in result.log.waves} <= {"B", "C"}


def test_wave_a_always_carries_an_orthogonal_framing():
    briefs = wave_briefs("A", params={"target_domain": "rag"})
    assert discovery.framing_diversity(briefs) >= discovery.MIN_FRAMINGS
    assert discovery.orthogonal_count(briefs) >= 1


def test_seed_brief_only_emitted_when_a_seed_exists():
    assert not any(b.seed_ref for b in wave_briefs("B", params={"target_domain": "rag"}))
    assert any(b.seed_ref == "J. Doe" for b in wave_briefs("B", params={"target_domain": "rag", "seed": "J. Doe"}))


def test_brief_id_is_stable_for_the_same_brief():
    b1 = ResearchBrief(wave="A", framing="structure", questions=["q"])
    b2 = ResearchBrief(wave="A", framing="structure", questions=["q"])
    assert brief_id(b1) == brief_id(b2)


def test_run_brief_freezes_a_live_result(tmp_path):
    """A LIVE backend's result is frozen: report, sources and the brief that produced them."""
    from research.deep_research import CallableBackend

    b = ResearchBrief(wave="A", framing="structure", questions=["q"], brief_id="A-test")
    snap = tmp_path / "snap"
    live = CallableBackend(lambda _b: ("# fresh\n- lead: something\n", [{"url": "https://e.org/1"}]))
    report, sources = run_brief(b, snap, live)

    assert "fresh" in report and sources[0]["url"] == "https://e.org/1"
    for name in ("report-A-test.md", "sources-A-test.json", "brief-A-test.json"):
        assert (snap / name).is_file(), f"{name} was not frozen"


def test_replaying_a_snapshot_does_not_rewrite_it(tmp_path):
    """Replay is a READ. Writing back what ReplayBackend just returned re-froze the snapshot against
    whatever parameters the caller used, so running `make test` rewrote the committed brief fixtures
    (the topic string in tests differs from the one they were frozen with). A snapshot that mutates
    when replayed is not a snapshot, and R-DISC-05's reproducibility guarantee rests on it holding
    still."""
    b = ResearchBrief(wave="A", framing="structure", questions=["q"], brief_id="A-test")
    src = tmp_path / "snap"
    src.mkdir()
    (src / "report-A-test.md").write_text("# frozen\n- lead: something\n", encoding="utf-8")
    (src / "sources-A-test.json").write_text(json.dumps([{"url": "https://e.org/1"}]), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in src.iterdir()}

    report, sources = run_brief(b, src, ReplayBackend(src))

    assert "frozen" in report and sources[0]["url"] == "https://e.org/1"
    assert {p.name: p.read_bytes() for p in src.iterdir()} == before, "replay mutated the snapshot"


def test_write_campaign_emits_both_artifacts(tmp_path):
    result = front_load_campaign("rag", {"target_domain": "rag"}, snapshot_dir=SNAPSHOT)
    paths = write_campaign(result, tmp_path)
    assert DiscoveryLog(**yaml.safe_load(paths["log"].read_text())).terminal in {"saturated", "max_waves"}
    assert DiscoveryLeads(**yaml.safe_load(paths["leads"].read_text())).accepted()


def test_brief_archetypes_match_the_template_document():
    """BRIEF_ARCHETYPES is the machine-readable half of discovery-brief-templates.md; drift
    between them means the campaign stops running the briefs the doc says it runs."""
    import re
    doc = (SKILL_ROOT / "references" / "discovery-brief-templates.md").read_text(encoding="utf-8")
    # the doc writes the id at the head of a bold run: **A1 structure**, **B-seed**, **C-omission**
    documented = set(re.findall(r"\*\*(A\d|B-[a-z]+|C-[a-z-]+?)(?:\s[^*]*)?\*\*", doc))
    assert documented == set(BRIEF_ARCHETYPES), documented ^ set(BRIEF_ARCHETYPES)
    assert set(sum(WAVE_ARCHETYPES.values(), [])) == set(BRIEF_ARCHETYPES)


# --- the lints (R-DISC-02/03/05/06) ------------------------------------------

def _log(**kw):
    base = dict(max_waves=4, saturation_threshold=0.15, terminal="saturated",
                waves=[{"wave": "A", "briefs": 6, "framing_cells": 6, "leads_total": 41,
                        "leads_new": 41, "novel_fraction": 0.1, "decision": "stop"}])
    base.update(kw)
    return DiscoveryLog(**base)


def test_framing_diversity_lint_flags_thin_wave():
    briefs = [brief(framing="structure") for _ in range(6)]
    out = disc_checks.framing_diversity(_log(), briefs)
    assert any("framing cell" in p for p in out)
    assert any("orthogonal" in p for p in out)


def test_framing_diversity_lint_passes_on_a_real_wave():
    briefs = wave_briefs("A", params={"target_domain": "rag"})
    log = _log(waves=[{"wave": "A", "briefs": len(briefs), "framing_cells": discovery.framing_diversity(briefs),
                       "leads_total": 10, "leads_new": 1, "novel_fraction": 0.1, "decision": "stop"}])
    assert disc_checks.framing_diversity(log, briefs) == []


def test_saturation_lint_flags_wave_cap_breach():
    waves = [{"wave": w, "briefs": 1, "framing_cells": 1, "leads_total": 1, "leads_new": 0,
              "novel_fraction": 0.1, "decision": "stop"} for w in "ABCDE"]
    assert any("cap" in p for p in disc_checks.saturation_terminal(_log(waves=waves)))


def test_saturation_lint_flags_mislabelled_terminal():
    log = _log(waves=[{"wave": "A", "briefs": 1, "framing_cells": 1, "leads_total": 1, "leads_new": 1,
                       "novel_fraction": 0.9, "decision": "stop"}])
    assert any("saturated" in p for p in disc_checks.saturation_terminal(log))


def test_saturation_lint_clean_on_a_real_campaign():
    result = front_load_campaign("rag", {"target_domain": "rag"}, snapshot_dir=SNAPSHOT)
    assert disc_checks.saturation_terminal(result.log) == []


def test_snapshot_lint_flags_missing_report(tmp_path):
    leads = DiscoveryLeads(topic_leads=[tl("tl-1", "x", report_ids=["a-missing"])])
    (tmp_path / "report-other.md").write_text("x", encoding="utf-8")
    out = disc_checks.snapshot_complete(leads, tmp_path)
    assert out and "missing" in out[0]


def test_snapshot_lint_flags_lead_without_report_id(tmp_path):
    leads = DiscoveryLeads(topic_leads=[tl("tl-1", "x")])
    assert any("no report id" in p for p in disc_checks.snapshot_complete(leads, tmp_path))


def test_snapshot_lint_clean_on_the_frozen_campaign():
    result = front_load_campaign("rag", {"target_domain": "rag"}, snapshot_dir=SNAPSHOT)
    assert disc_checks.snapshot_complete(result.leads, SNAPSHOT) == []


def test_seed_lint_flags_dropped_seed():
    leads = DiscoveryLeads(source_leads=[
        sl("sl-1", "https://example.org/seed", status="dropped", provenance_origin="user")])
    out = disc_checks.seed_handling(leads, [{"kind": "url", "ref": "https://example.org/seed"}])
    assert any("exempt from drop" in p for p in out)


def test_seed_lint_flags_missing_seed():
    out = disc_checks.seed_handling(DiscoveryLeads(), [{"kind": "url", "ref": "https://example.org/seed"}])
    assert any("never appears" in p for p in out)


def test_seed_lint_flags_seed_promoted_past_its_evidence():
    """Seeds are authoritative for inclusion, not for truth (R-DISC-06)."""
    leads = DiscoveryLeads(source_leads=[
        sl("sl-1", "https://example.org/seed", provenance_origin="user", salience="high", support_count=0)])
    out = disc_checks.seed_handling(leads, [{"kind": "url", "ref": "https://example.org/seed"}])
    assert any("not for truth" in p for p in out)


def test_seed_lint_ignores_directive_seeds():
    assert disc_checks.seed_handling(DiscoveryLeads(), [{"kind": "author", "ref": "J. Doe"}]) == []


# --- the live campaign backend (Stage G seam) --------------------------------
# Hermetic: the CLI and the network are both stubbed. The point being pinned is that a lead the
# backend could not FETCH never enters a snapshot as accepted — `run_brief` freezes what a backend
# returns, so a confabulated URL written there becomes a fabrication replayed as fact forever.
# This is not hypothetical: probed against this CLI, `claude -p` reported `web_search_requests: 0`
# while claiming it had searched, and one of the three URLs it produced did not resolve.

def test_backend_drops_urls_that_do_not_fetch(tmp_path):
    from types import SimpleNamespace

    from ir.schema import ResearchBrief
    from research.claude_backend import ClaudeResearchBackend

    class _Cli:
        calls = 0
        spend_usd = 0.0

        def result_json(self, _instruction):
            return {"report": "body", "sources": [
                {"url": "https://real.example/a", "type": "docs", "why": "x"},
                {"url": "https://fake.example/b", "type": "blog", "why": "y"},
            ]}

    class _Fetcher:
        name = "stub"
        refused = {"https://fake.example/b": "HTTPError: 404"}

        def __call__(self, url):
            if url == "https://real.example/a":
                return SimpleNamespace(url=url, title="A", retrieved_at="2026-01-01", text="body")
            return None

    backend = ClaudeResearchBackend(cli=_Cli(), fetcher=_Fetcher())
    report, leads = backend(ResearchBrief(wave="A", framing="mechanism", questions=["q?"]))

    assert "mechanism" in report
    by_status = {lead["url"]: lead["status"] for lead in leads}
    assert by_status["https://real.example/a"] == "accepted"
    assert by_status["https://fake.example/b"] == "dropped"
    # dropped, not deleted: what a wave proposed vs what survived is a signal about the backend
    assert len(leads) == 2
    assert backend.dropped[0]["dropped_reason"].startswith("HTTPError")


def test_a_redirected_lead_points_at_the_url_the_corpus_is_keyed_by():
    """`Document.url` is the POST-redirect URL — the page actually fetched, and the key the frozen
    corpus is written under — while the lead kept the URL we asked for. So a source verified live
    resolved to nothing on replay: the campaign passes, and re-running it offline cannot find the
    evidence it just proved."""
    from types import SimpleNamespace

    from ir.schema import ResearchBrief
    from research.claude_backend import ClaudeResearchBackend

    class _Cli:
        calls = 0
        spend_usd = 0.0

        def result_json(self, _instruction):
            return {"report": "body", "sources": [
                {"url": "http://old.example/a", "type": "docs", "why": "x"}]}

    class _Fetcher:
        name = "stub"
        refused: dict = {}

        def __call__(self, _url):
            return SimpleNamespace(url="https://new.example/a", title="A",
                                   retrieved_at="2026-01-01", text="body")

    backend = ClaudeResearchBackend(cli=_Cli(), fetcher=_Fetcher())
    _report, leads = backend(ResearchBrief(wave="A", framing="mechanism", questions=["q?"]))

    assert leads[0]["url"] == "https://new.example/a" == backend.documents[0].url
    assert leads[0]["requested_url"] == "http://old.example/a"   # kept for the audit trail


def test_backend_returns_an_empty_wave_rather_than_inventing_one():
    from ir.schema import ResearchBrief
    from research.claude_backend import ClaudeResearchBackend
    from utils.claude_cli import CliUnavailable

    class _DeadCli:
        calls = 0
        spend_usd = 0.0

        def result_json(self, _instruction):
            raise CliUnavailable("simulated outage")

    backend = ClaudeResearchBackend(cli=_DeadCli())
    report, leads = backend(ResearchBrief(wave="A", framing="mechanism", questions=["q?"]))
    assert leads == []
    assert "No report" in report


def test_the_framing_floor_governs_the_breadth_wave_and_later_waves_stay_distinct():
    """G10, resolved. R-DISC-02 used to demand the floor of EVERY wave, which no campaign could
    satisfy: WAVE_ARCHETYPES gives B three archetypes (two once B-seed skips) and C three.

    Scoped to the breadth wave, because three artifacts said so — MIN_FRAMINGS' own comment ("Wave A
    breadth"), discovery-brief-templates.md (B and C are deliberately narrow, and that document is
    pinned by a test), and the rule's own `counters`: "cosmetically-different briefs pay Nx tokens
    for 1x recall" is an argument about the broad sweep. Forcing five cells onto a targeted
    follow-up would manufacture precisely that padding.

    What every wave still owes is DISTINCTNESS — duplicate cells are cosmetic in any wave.
    """
    from research import discovery as disc
    from research.planner import WAVE_ARCHETYPES, StubJudge, wave_briefs

    params = {"target_domain": "T"}
    briefs = {w: wave_briefs(w, residual=None, params=params, judge=StubJudge())
              for w in WAVE_ARCHETYPES}

    # the breadth wave carries the floor and the orthogonal framing
    assert disc.BREADTH_WAVE == "A"
    assert disc.framing_diversity(briefs["A"]) >= disc.MIN_FRAMINGS
    assert disc.orthogonal_count(briefs["A"]) >= 1

    # later waves are narrower BY DESIGN, but never duplicate a cell
    for wave in ("B", "C"):
        assert disc.framing_diversity(briefs[wave]) < disc.MIN_FRAMINGS, (
            f"wave {wave} now meets the breadth floor — if that was intentional, the templates "
            f"document and this test both need updating")
        assert disc.framing_diversity(briefs[wave]) == len(briefs[wave]), (
            f"wave {wave} has duplicate framing cells")


def test_campaign_log_records_the_cap_it_actually_ran_under():
    """`waves` is configurable and defaults to three, but the log recorded MAX_WAVES=4 — so every
    unsaturated run reported terminal 'max_waves' after 3 of 4, describing a cap never reached.
    R-DISC-03 checks exactly that correspondence, and had no dispatch entry to catch it with."""
    from checks.discovery import saturation_terminal
    from research.planner import front_load_campaign

    result = front_load_campaign(
        "retrieval-augmented generation",
        {"target_domain": "retrieval-augmented generation", "seed": "J. Doe"},
        snapshot_dir=SNAPSHOT)
    assert result.log.max_waves == min(3, discovery.MAX_WAVES)
    assert "terminal 'max_waves'" not in " ".join(saturation_terminal(result.log))


def test_backend_verdicts_survive_lead_extraction():
    """A verifying backend marks a lead it could not FETCH as `dropped`. extract_leads used to
    rebuild source leads from url+type alone, so that verdict vanished and the lead was frozen into
    the snapshot as `accepted` — a 404 laundered into a real source. Measured on a live campaign:
    124 leads, every one 'accepted', none with a fetched title. The judge may downgrade a lead; it
    must never upgrade one the fetcher already rejected (R-DISC-01: a lead is a pointer)."""
    from research.planner import StubJudge

    sources = [
        {"url": "https://real.example/a", "type": "docs", "status": "accepted",
         "fetched_title": "A", "retrieved_at": "2026-01-01"},
        {"url": "https://fake.example/b", "type": "blog", "status": "dropped",
         "dropped_reason": "HTTPError: 404"},
    ]
    payload = StubJudge().extract_leads("report body", sources, brief(wave="A"))
    by_url = {s["url"]: s for s in payload["source_leads"]}
    assert by_url["https://real.example/a"]["status"] == "accepted"
    assert by_url["https://fake.example/b"]["status"] == "dropped"
    assert by_url["https://fake.example/b"]["dropped_reason"].startswith("HTTPError")
    assert by_url["https://real.example/a"]["fetched_title"] == "A"


def test_a_dropped_lead_is_not_resurrected_by_triage():
    """Triage runs after extraction; a lead the fetcher rejected must not come back accepted."""
    from research.planner import StubJudge, triage_leads

    def _status(lead):
        return [x.status for x in triage_leads(discovery.cluster_leads([lead]), {}, StubJudge())]

    assert _status(sl("sl-1", "https://fake.example/b", status="dropped",
                      dropped_reason="HTTPError: 404")) == ["dropped"]

    # a user seed that will not load is still not evidence — R-DISC-06 asks for seeds to be
    # consulted and grounded, not asserted past what they can support
    assert _status(sl("sl-2", "https://fake.example/seed", status="dropped",
                      dropped_reason="HTTPError: 404", provenance_origin="user")) == ["dropped"]

    # a lead the JUDGE dropped (no fetch verdict) still follows the normal triage path
    assert _status(sl("sl-3", "https://real.example/c", status="dropped")) == ["accepted"]
