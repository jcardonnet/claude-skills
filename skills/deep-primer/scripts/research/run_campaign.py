"""Drive one real grounding campaign end to end, from a spec's parameters to its artifacts.

Classification: agent-orchestrated (network + model — NOT hermetic)
Implements: SKILL.md Phase 1 (research arc) and Phase 1a (discovery), composed

Why this exists
---------------
The skill itself is the driver: an agent executes the eight phases and calls `research/*` as
engines. That works, and it is also why nobody could re-run spec-02's campaign — the sequence
lived in a transcript. This script is that sequence, written down. It adds NO logic of its own:
every step below is an existing function, and the only decisions here are which one to call next
and where to put the result.

What it does NOT do
-------------------
It stops at the artifacts (ledger, concept-map, convergence log). Drafting a primer from them is
Phases 2-8 and stays the agent's job — a script that also drafted would be a second, divergent
implementation of the pipeline the skill already specifies.

Reproducibility
---------------
The network runs ONCE. `freeze_corpus` writes what was actually fetched and the ledger is built by
replaying that frozen corpus, so re-running the grounding half offline produces a byte-identical
ledger. `--as-of` is passed in rather than read from the clock for the same reason.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import DiscoveryLeads, DiscoveryLog, SourceLedger
from research import planner
from research.claim_extractor import build_ledger, corroborate, mark_recency
from research.claude_backend import ClaudeResearchBackend
from research.claude_claim_extractor import ClaudeClaimExtractor
from research.claude_curator import ClaudeConceptGrouper, ClaudeCorroborationGrouper
from research.claude_structure_judge import ClaudeStructureJudge
from research.curate import curate_concept_map
from research.http_fetcher import freeze_corpus
from research.retrieval_loop import ReplayFetcher, RetrievalResult, fetch_source_leads


def _calls(seam) -> int:
    return getattr(getattr(seam, "cli", None), "calls", 0)


def _spend(seam) -> float:
    return round(getattr(getattr(seam, "cli", None), "spend_usd", 0.0), 4)


def _dump(model, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False,
                                   allow_unicode=True), encoding="utf-8")
    return path


def _spec_params(spec_path: Path) -> dict:
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    params = dict(spec.get("parameters") or {})
    if not params.get("target_domain"):
        raise SystemExit(f"{spec_path} has no parameters.target_domain")
    return params


def run(spec_path: Path, out_dir: Path, *, as_of: str, waves: tuple[str, ...],
        research_model: str = "haiku", extract_model: str = "haiku", cost_cap: float = 5.0,
        max_docs: int | None = None, skip_convergence: bool = False,
        lexical_grouping: bool = False, from_corpus: Path | None = None,
        from_ledger: bool = False,
        backend=None, extractor=None, judge=None,
        grouper=None, corroboration_grouper=None) -> dict:
    """Every model seam is injectable for the same reason they are everywhere else here: the
    composition is what this file is for, and it has to be exercisable without the network.

    `lexical_grouping` is the offline escape hatch, not a mode anyone should prefer — it restores
    the word-overlap grouping that produced 249 concepts from 271 claims. An explicitly injected
    grouper wins over it, so a test can pass a stub without also having to opt out.
    """
    params = _spec_params(spec_path)
    topic = params["target_domain"]
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    # --- Phase 1a: discovery campaign. The backend verifies every URL it returns, so what lands
    # in `backend.documents` is the set of pages that genuinely fetched (R-DISC-01).
    #
    # `--from-corpus` skips it and replays a corpus a previous run froze. Discovery is the
    # expensive, rate-limited half and it is written to disk BEFORE extraction begins, so a run
    # that dies in grounding has already banked the part worth keeping — resume it, don't repeat it.
    if from_corpus or from_ledger:
        campaign = planner.CampaignResult(
            leads=DiscoveryLeads(**yaml.safe_load(
                (out_dir / "discovery-leads.yaml").read_text(encoding="utf-8"))),
            log=DiscoveryLog(**yaml.safe_load(
                (out_dir / "discovery-log.yaml").read_text(encoding="utf-8"))),
            briefs=[])
        corpus_dir = Path(from_corpus) if from_corpus else out_dir / "corpus"
    else:
        backend = backend or ClaudeResearchBackend(model=research_model, cost_cap_usd=cost_cap)
        campaign = planner.front_load_campaign(
            topic, params, snapshot_dir=str(out_dir / "discovery-snapshot"),
            backend=backend, waves=waves)
        planner.write_campaign(campaign, out_dir)
        # --- Freeze, then replay. Everything downstream reads the frozen corpus, not the live web.
        corpus_dir = freeze_corpus(list(getattr(backend, "documents", [])), out_dir / "corpus")
    notes: list[str] = []
    corroborator = corroboration_grouper
    if from_ledger:
        # `--from-ledger` resumes at grouping. The ledger on disk is already corroborated and
        # recency-marked -- those steps ran before it was written -- so re-deriving it would not
        # produce the same file: extraction is a model call, and a second pass over the same corpus
        # yields a DIFFERENT set of claims. Grouping is 3 calls; extraction was 51. Re-running a
        # grouping that failed should not mean discarding a grounding that succeeded.
        retrieval = RetrievalResult()
        documents, rejections = [], []
        ledger = SourceLedger.from_yaml(out_dir / "source-ledger.yaml")
    else:
        retrieval = fetch_source_leads(campaign.leads, ReplayFetcher(corpus_dir=corpus_dir))
        # A campaign that resolved nothing must not report success. Every stage below is a clean
        # no-op on an empty document list: build_ledger anchors no claims, grouping has nothing to
        # group, and the run exits 0 having written a report whose only symptom is `concepts: 0`.
        # That is the most reassuring possible reading of a total retrieval failure -- and it is
        # what the 2026-08-21 spec-04 retry produced, 155 source leads, every one unresolved, exit 0.
        if campaign.leads.source_leads and not retrieval.documents:
            raise RuntimeError(
                f"retrieval resolved 0 documents from {len(campaign.leads.source_leads)} source "
                f"leads (corpus: {corpus_dir}) -- every stage downstream would be vacuous")
        documents = retrieval.documents[:max_docs] if max_docs else retrieval.documents

        # --- Phase 1: grounding. The model proposes claims; `anchor_claims` inside build_ledger
        # keeps only the ones whose quote is verbatim in the fetched body.
        extractor = extractor or ClaudeClaimExtractor(model=extract_model, cost_cap_usd=cost_cap)
        ledger, rejections = build_ledger(documents, extractor)

        # --- Corroboration. Both this and grouping below ask "which of these claims say the same
        # thing?", and both used to answer it with word overlap: spec-03's first campaign turned 271
        # claims into 249 single-claim concepts and corroborated 0 of them. The model proposes now;
        # `resolve_groups` still decides, and `--lexical-grouping` restores the offline answer.
        if corroborator is None and not lexical_grouping:
            corroborator = ClaudeCorroborationGrouper(model=extract_model, cost_cap_usd=cost_cap)
        ledger = mark_recency(corroborate(ledger, grouper=corroborator, notes=notes), as_of=as_of)
        _dump(ledger, out_dir / "source-ledger.yaml")

    if grouper is None and not lexical_grouping:
        grouper = ClaudeConceptGrouper(model=extract_model, cost_cap_usd=cost_cap)
    concept_map = curate_concept_map(ledger, params, grouper=grouper, notes=notes)
    # A grouping that lost a whole batch must not be written as a campaign. `_ask` already retries,
    # and a batch that answers nothing even then leaves every one of its claims a singleton concept
    # -- which reads, in the artifact, exactly like a claim the model found genuinely unique. That
    # is what the 2026-08-21 spec-04 run shipped: 333 claims, one lost batch of 150, 215 "concepts",
    # exit 0. The ledger above is already on disk, so `--from-ledger` resumes this for 3 calls.
    lost = getattr(grouper, "lost_claims", 0)
    if lost:
        raise RuntimeError(
            f"concept grouping lost {lost} of {sum(len(s.claims) for s in ledger.sources)} claims "
            f"to a batch that proposed nothing: {getattr(grouper, 'errors', [])} -- the concept map "
            f"would be mostly singletons. Re-run with --from-ledger to retry grouping only")
    _dump(concept_map, out_dir / "concept-map.yaml")

    convergence_paths: dict = {}
    if not skip_convergence and concept_map.concepts:
        run_ = planner.run_convergence_loop(
            concept_map, judge or ClaudeStructureJudge(params=params, cost_cap_usd=cost_cap),
            params)
        convergence_paths = planner.write_convergence(run_, out_dir)

    claims = [c for s in ledger.sources for c in s.claims]
    report = {
        "spec": spec_path.name,
        "topic": topic,
        "as_of": as_of,
        "wall_clock_s": round(time.monotonic() - started, 1),
        # Which phase this run actually started at. Named for the same reason `max_docs` is: a
        # resumed run's zeroes ("documents_resolved: 0") are otherwise indistinguishable from a
        # run that fetched nothing.
        "resumed_from": "ledger" if from_ledger else ("corpus" if from_corpus else None),
        "discovery": {
            "waves": [w.model_dump(mode="json") for w in campaign.log.waves],
            "terminal": campaign.log.terminal,
            "briefs": len(campaign.briefs),
            "source_leads": len(campaign.leads.source_leads),
            "dropped_by_backend": len(getattr(backend, "dropped", [])),
        },
        "retrieval": {
            "documents_fetched": len(getattr(backend, "documents", [])),
            "documents_resolved": len(retrieval.documents),
            "documents_extracted": len(documents),
            # The cap that made resolved != extracted, so the gap reads as a setting rather than a
            # failure. Without it the 2026-08-20 spec-03 run looked like retrieval had lost 90 of
            # its 120 documents; it had not, it was told to stop at 30. A bound on coverage that
            # the report does not name is indistinguishable from having covered everything.
            "max_docs": max_docs,
            "unresolved": retrieval.unresolved,
        },
        "grounding": {
            "claims_kept": len(claims),
            "claims_rejected": len(rejections),
            "corroborated": sum(1 for c in claims if (c.corroboration_count or 0) > 1),
            "extractor_errors": list(getattr(extractor, "errors", [])),
            "rejections": rejections,
        },
        "concepts": len(concept_map.concepts),
        # What the gate threw away and what the groupers had to do to fit. Reported rather than
        # logged because a silently-capped grouping run looks exactly like a well-grouped one.
        "grouping": {
            "gate_rejections": notes,
            "grouper_notes": list(getattr(grouper, "notes", []))
                             + list(getattr(corroborator, "notes", [])),
            "grouper_errors": list(getattr(grouper, "errors", []))
                              + list(getattr(corroborator, "errors", [])),
        },
        "convergence": {k: str(v) for k, v in convergence_paths.items()},
        # Notional API-equivalent under the subscription, not a bill. Recorded because the binding
        # constraint on a campaign is the rate limit, and calls are what track against it.
        "calls": {"research": _calls(backend), "extract": _calls(extractor),
                  "group": _calls(grouper) + _calls(corroborator)},
        "spend_usd": {"research": _spend(backend), "extract": _spend(extractor),
                      "group": round(_spend(grouper) + _spend(corroborator), 4)},
    }
    (out_dir / "campaign-run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="path to an eval spec YAML (its parameters drive the campaign)")
    ap.add_argument("--out", required=True, help="directory to write artifacts into")
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD stamped on version/SOTA claims")
    ap.add_argument("--waves", default="A,B,C")
    ap.add_argument("--research-model", default="haiku")
    ap.add_argument("--extract-model", default="haiku")
    ap.add_argument("--cost-cap", type=float, default=5.0, help="per-caller notional USD ceiling")
    ap.add_argument("--max-docs", type=int, default=None, help="cap documents sent to extraction")
    ap.add_argument("--skip-convergence", action="store_true")
    ap.add_argument("--lexical-grouping", action="store_true",
                    help="group concepts and corroboration by word overlap instead of by model "
                         "(free and offline, but it under-merges badly — see claude_curator.py)")
    ap.add_argument("--from-corpus", default=None,
                    help="skip discovery; replay this frozen corpus (resumes a died-in-grounding run)")
    ap.add_argument("--from-ledger", action="store_true",
                    help="skip discovery AND grounding; re-group the source-ledger.yaml already in "
                         "--out (resumes a run whose grouping failed, for the cost of grouping)")
    args = ap.parse_args(argv)

    report = run(Path(args.spec), Path(args.out), as_of=args.as_of,
                 waves=tuple(w.strip() for w in args.waves.split(",") if w.strip()),
                 research_model=args.research_model, extract_model=args.extract_model,
                 cost_cap=args.cost_cap, max_docs=args.max_docs,
                 skip_convergence=args.skip_convergence,
                 lexical_grouping=args.lexical_grouping,
                 from_corpus=Path(args.from_corpus) if args.from_corpus else None,
                 from_ledger=args.from_ledger)
    print(json.dumps({k: v for k, v in report.items() if k != "grounding"}, indent=2))
    g = report["grounding"]
    print(f"claims kept {g['claims_kept']} · rejected {g['claims_rejected']} · "
          f"corroborated {g['corroborated']} · concepts {report['concepts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
