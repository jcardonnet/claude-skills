"""Registry-driven hard_lint dispatcher.

Classification: local-deterministic
Implements: all hard_lint

Loads rule-registry.yaml; for every `enforcement: hard_lint` rule (and any `also_hard_lint`
companion) it dispatches the rule's `check.ref` to an implemented callable and records the
outcome. BLOCKING DERIVES FROM PRIORITY, not enforcement: a MUST violation -> status 'fail'
(blocking); SHOULD/MAY -> 'warn'. A Violation may set force_status to override (the coherence
check uses this to downgrade its degraded/no-spaCy findings to 'warn'). Refs not implemented in
this stage are 'skip' (never imported, so stub modules that raise on import are not touched).

Emits lint-report.json: {blocking, counts, findings:[{rule_id, block_id, status, detail, ...}]}.

Usage:
    python scripts/lint.py document-ir.yaml --concept-map concept-map.yaml --ledger source-ledger.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# scripts/ is the import root (matches registry check.refs); enable standalone execution.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from checks import (  # noqa: E402
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
from checks import convergence as convergence_checks  # noqa: E402
from checks import discovery as discovery_checks  # noqa: E402
from checks import ledger as ledger_checks  # noqa: E402
from checks._base import CheckNotApplicable, LintContext, Violation  # noqa: E402
from ir.schema import ConceptMap, DocumentIR, SourceLedger  # noqa: E402
from render import render_llm_md as md_checks  # noqa: E402
from utils import parse_primer  # noqa: E402
from verify import citation_quality  # noqa: E402


def _resolves_to_ledger(ctx: LintContext) -> list[Violation]:
    """R-GROUND-01 adapter. The deterministic half of citation quality lives under verify/ next
    to the model_verified halves, but it reads the IR + ledger with no model in the loop and the
    registry marks it hard_lint — so it runs in this pass.

    No ledger supplied means the check did not run. It used to return [] — indistinguishable in the
    report from "every marker resolved" — so an IR-only lint reported this MUST rule as satisfied
    and credited it as coverage."""
    if ctx.ledger is None:
        raise CheckNotApplicable("R-GROUND-01 needs a source-ledger; none was supplied")
    return [Violation(v["block_id"], v["detail"])
            for v in citation_quality.resolves_to_ledger(ctx.ir, ctx.ledger)]

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "references" / "rule-registry.yaml"

# check.ref (verbatim from the registry) -> implemented callable. Refs absent here are 'skip'.
CHECKS = {
    "checks/structure_coverage.py::layer_coverage": structure_coverage.layer_coverage,
    "checks/structure_coverage.py::length_budget": structure_coverage.length_budget,
    "checks/structure_coverage.py::params_present": structure_coverage.params_present,
    "checks/structure_coverage.py::heading_hierarchy": structure_coverage.heading_hierarchy,
    "checks/structure_coverage.py::banned_heading_terms": structure_coverage.banned_heading_terms,
    "checks/structure_coverage.py::card_rows": structure_coverage.card_rows,
    "checks/structure_coverage.py::recall_count": structure_coverage.recall_count,
    "checks/structure_coverage.py::summary_budgets": structure_coverage.summary_budgets,
    "checks/structure_coverage.py::operational_artifacts": structure_coverage.operational_artifacts,
    "checks/structure_coverage.py::user_structure_respected": structure_coverage.user_structure_respected,
    "checks/univocity_terms.py::home_anchor_distinct": univocity_terms.home_anchor_distinct,
    "checks/prose_caps.py::compression_gradient": prose_caps.compression_gradient,
    "checks/prose_caps.py::length_caps": prose_caps.length_caps,
    "checks/prose_caps.py::condition_first": prose_caps.condition_first,
    "checks/coherence_givennew.py::entity_grid": coherence_givennew.entity_grid,
    "checks/univocity_terms.py::canonical_terms": univocity_terms.canonical_terms,
    "checks/multiview_concepts.py::modes_per_concept": multiview_concepts.modes_per_concept,
    "checks/recency_versions.py::version_freshness": recency_versions.version_freshness,
    # the registry names these two under structure_coverage.py; the impls live in their own modules
    "checks/structure_coverage.py::footnote_balance": footnote.footnote_balance,
    "checks/structure_coverage.py::xrefs_resolve": xrefs.xrefs_resolve,
    "checks/provenance.py::tagged": provenance.tagged,
    "verify/citation_quality.py::resolves_to_ledger": _resolves_to_ledger,
}

# The `html` pass: checks that read the RENDERED artifact rather than the IR. They take the html
# string and return violation strings. Every other structural rule reads the IR.
HTML_CHECKS = {
    "utils/parse_primer.py::block_ids_and_meta": parse_primer.block_ids_and_meta,
    "utils/parse_primer.py::depth_dial_present": parse_primer.depth_dial_present,
    "utils/parse_primer.py::figure_a11y": parse_primer.figure_a11y,
}

# The `ledger` pass: reads source-ledger.yaml at the end of Phase 1, before any drafting exists.
LEDGER_CHECKS = {
    "checks/ledger.py::provenance_fields": ledger_checks.provenance_fields,
}

# The `convergence-log` pass: run after the drafting<->structure loop terminates (R-CONV-01).
# Takes a PAIR, like llm_md. R-CONV-01's contested clause — "a contested trajectory must actually
# be RENDERED, not just recorded" — reads the IR, and `terminal_state`'s `ir` parameter defaulted to
# None on the only dispatched path, so that half of the rule was unreachable from every caller.
CONVERGENCE_CHECKS = {
    "checks/convergence.py::terminal_state": lambda p: convergence_checks.terminal_state(*p),
}

# The `llm_md` pass. Artifact is the tuple (markdown, DocumentIR) — the roles a block-id belongs
# to live in the IR, so these need both halves.
LLM_MD_CHECKS = {
    "render/render_llm_md.py::role_filter": md_checks.role_filter,
    "render/render_llm_md.py::no_svg": md_checks.no_svg,
}

# The discovery passes. These checks have existed in checks/discovery.py since Stage B and were
# never reachable: with no entry here `run_artifact_pass` finds no function, records `skip`, and
# skip is NON-BLOCKING — four MUST rules (R-DISC-02/03/05/06) dark in exactly the way Stage A
# existed to stop, one layer further out than Stage A looked. Each takes a PAIR, like llm_md:
# a lead set means nothing without the briefs, snapshot, or seeds it is judged against.
DISCOVERY_LOG_CHECKS = {
    "checks/discovery.py::framing_diversity": lambda p: discovery_checks.framing_diversity(*p),
    "checks/discovery.py::saturation_terminal": lambda p: discovery_checks.saturation_terminal(p[0]),
}
DISCOVERY_LEADS_CHECKS = {
    "checks/discovery.py::seed_handling": lambda p: discovery_checks.seed_handling(*p),
}
SNAPSHOT_CHECKS = {
    "checks/discovery.py::snapshot_complete": lambda p: discovery_checks.snapshot_complete(*p),
}


def _record(rule: dict, ref: str, block_id: str | None, status: str, detail: str) -> dict:
    return {
        "rule_id": rule["id"],
        "block_id": block_id,
        "status": status,            # pass | fail | warn | skip
        "detail": detail,
        "priority": rule["priority"],
        "ref": ref,
        "blocking": status == "fail",
    }


def _status_for(rule: dict, force: str | None) -> str:
    if force:
        return force
    return "fail" if rule["priority"] == "MUST" else "warn"


def _run_ref(rule: dict, ref: str, ctx: LintContext) -> list[dict]:
    fn = CHECKS.get(ref)
    if fn is None:
        return [_record(rule, ref, None, "skip", "not implemented in this stage (IR/HTML or later prompt)")]
    try:
        violations = fn(ctx)
    except CheckNotApplicable as exc:
        # "I was handed nothing to check" is a SKIP, not a pass. Returning [] here made an IR-only
        # lint report four MUST rules as satisfied: R-GROUND-01, R-VOCAB-01, R-XREF-04, R-MV-01.
        return [_record(rule, ref, None, "skip", str(exc))]
    if not violations:
        return [_record(rule, ref, None, "pass", "ok")]
    return [_record(rule, ref, v.block_id, _status_for(rule, v.force_status), v.detail) for v in violations]


def _ir_hard(rules: list[dict]) -> list[tuple[dict, str]]:
    """(rule, ref) pairs targeting the IR. Convention: absent check.input => 'ir'. The render /
    discovery / convergence / ledger checks run in their own passes — their artifacts don't
    exist during an IR-only lint, and several are unimplemented stubs we must not call here.

    `also_hard_lint` companions are dispatched too, and deliberately WITHOUT filtering on the
    parent rule's enforcement: R-SCENT-01 is a soft_critic rule whose mechanical half (the banned
    generic-heading list) is deterministically checkable, and skipping it because its parent is
    soft is exactly how that lint went missing.
    """
    pairs: list[tuple[dict, str]] = []
    for r in rules:
        check = r.get("check", {})
        if check.get("input", "ir") != "ir":
            continue
        if r["enforcement"] == "hard_lint" and check.get("ref"):
            pairs.append((r, check["ref"]))
        if check.get("also_hard_lint"):
            pairs.append((r, check["also_hard_lint"]))
    return pairs


def run_lint(ctx: LintContext, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    rules = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")).get("rules", [])
    pairs = _ir_hard(rules)
    findings: list[dict] = []
    for rule, ref in pairs:
        findings.extend(_run_ref(rule, ref, ctx))

    counts: dict[str, int] = {}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    skipped = sorted({f["rule_id"] for f in findings if f["status"] == "skip"})
    unenforced_musts = sorted({f["rule_id"] for f in findings
                               if f["status"] == "skip" and f["priority"] == "MUST"})
    return {
        "blocking": any(f["status"] == "fail" for f in findings),
        "counts": counts,
        # coverage answers "what was actually enforced?" — a report with silent skips reads clean
        # while the contract goes unchecked, which is how six MUST rules stayed dark.
        "coverage": {
            "checks_dispatched": len(pairs),
            "rules_skipped": skipped,
            "unenforced_musts": unenforced_musts,
        },
        "findings": findings,
    }


_ARTIFACT_CHECKS = {"html": HTML_CHECKS, "ledger": LEDGER_CHECKS,
                    "convergence-log": CONVERGENCE_CHECKS, "llm_md": LLM_MD_CHECKS,
                    "discovery-log": DISCOVERY_LOG_CHECKS,
                    "discovery-leads": DISCOVERY_LEADS_CHECKS,
                    "snapshot": SNAPSHOT_CHECKS}


def run_artifact_pass(artifact, input_tag: str, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """Dispatch the hard_lints tagged `input: <input_tag>` against a non-IR artifact.

    Each pass runs when its artifact exists — `ledger` at the end of Phase 1, `html` after Phase 8
    rendering — which is why they cannot ride along with the IR lint.
    """
    rules = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")).get("rules", [])
    table = _ARTIFACT_CHECKS.get(input_tag, {})
    findings: list[dict] = []
    dispatched = 0
    for rule in rules:
        check = rule.get("check", {})
        if rule["enforcement"] != "hard_lint" or check.get("input") != input_tag:
            continue
        ref = check.get("ref")
        fn = table.get(ref)
        dispatched += 1
        if fn is None:
            findings.append(_record(rule, ref, None, "skip", "not implemented"))
            continue
        try:
            problems = fn(artifact)
        except CheckNotApplicable as exc:
            findings.append(_record(rule, ref, None, "skip", str(exc)))
            continue
        if not problems:
            findings.append(_record(rule, ref, None, "pass", "ok"))
        else:
            findings.extend(_record(rule, ref, None, _status_for(rule, None), p) for p in problems)

    counts: dict[str, int] = {}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    return {
        "blocking": any(f["status"] == "fail" for f in findings),
        "counts": counts,
        "coverage": {
            "checks_dispatched": dispatched,
            "rules_skipped": sorted({f["rule_id"] for f in findings if f["status"] == "skip"}),
            "unenforced_musts": sorted({f["rule_id"] for f in findings
                                        if f["status"] == "skip" and f["priority"] == "MUST"}),
        },
        "findings": findings,
    }


def run_html_pass(html: str, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `html` pass (R-CONSIST-02, R-DEPTH-02, R-FIG-04)."""
    return run_artifact_pass(html, "html", registry_path)


def run_ledger_pass(ledger, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `ledger` pass (R-GROUND-05), run at the end of Phase 1."""
    return run_artifact_pass(ledger, "ledger", registry_path)


def run_convergence_pass(log, ir=None, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `convergence-log` pass (R-CONV-01), run once the escalate loop terminates.

    Takes the IR as well: a `contested` terminal regime has to be RENDERED, not merely recorded, and
    that clause cannot be checked from the log alone.
    """
    return run_artifact_pass((log, ir), "convergence-log", registry_path)


def run_llm_md_pass(md: str, ir, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `llm_md` pass (R-PROJ-03, R-PROJ-06) over the distilled projection."""
    return run_artifact_pass((md, ir), "llm_md", registry_path)


def run_discovery_log_pass(log, briefs, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `discovery-log` pass (R-DISC-02 framing diversity, R-DISC-03 saturation)."""
    return run_artifact_pass((log, briefs), "discovery-log", registry_path)


def run_discovery_leads_pass(leads, seed_sources, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `discovery-leads` pass (R-DISC-06 seed handling)."""
    return run_artifact_pass((leads, seed_sources or []), "discovery-leads", registry_path)


def run_snapshot_pass(leads, snapshot_dir, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    """The `snapshot` pass (R-DISC-05: every cited report is actually frozen)."""
    return run_artifact_pass((leads, snapshot_dir), "snapshot", registry_path)


def lint_files(
    ir_path: str | Path,
    concept_map_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
    parameters: dict | None = None,
    capabilities: dict | None = None,
    registry_path: str | Path = DEFAULT_REGISTRY,
) -> dict:
    ir = DocumentIR.from_yaml(ir_path)
    ctx = LintContext(
        ir=ir,
        concept_map=ConceptMap.from_yaml(concept_map_path) if concept_map_path else None,
        ledger=SourceLedger.from_yaml(ledger_path) if ledger_path else None,
        parameters=parameters if parameters is not None else dict(ir.meta.parameters),
        capabilities=capabilities or {},
    )
    return run_lint(ctx, registry_path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the hard_lint set against a document-ir.yaml.")
    ap.add_argument("ir", help="path to document-ir.yaml")
    ap.add_argument("--concept-map", dest="concept_map")
    ap.add_argument("--ledger")
    ap.add_argument("--length-budget", type=int, dest="length_budget")
    ap.add_argument("--no-nlp", action="store_true", help="force the entity-overlap fallback (skip spaCy)")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--out", default="lint-report.json")
    ap.add_argument("--strict", action="store_true",
                    help="treat an unenforced MUST rule (status 'skip') as an error")
    args = ap.parse_args(argv)

    ir = DocumentIR.from_yaml(args.ir)
    parameters = dict(ir.meta.parameters)
    if args.length_budget is not None:
        parameters["length_budget"] = args.length_budget
    ctx = LintContext(
        ir=ir,
        concept_map=ConceptMap.from_yaml(args.concept_map) if args.concept_map else None,
        ledger=SourceLedger.from_yaml(args.ledger) if args.ledger else None,
        parameters=parameters,
        capabilities={"force_no_nlp": args.no_nlp},
    )
    report = run_lint(ctx, args.registry)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    c = report["counts"]
    print(f"{'BLOCKING' if report['blocking'] else 'clean'} — "
          f"fail={c.get('fail', 0)} warn={c.get('warn', 0)} pass={c.get('pass', 0)} skip={c.get('skip', 0)} "
          f"-> {args.out}")
    for f in report["findings"]:
        if f["status"] in ("fail", "warn"):
            print(f"  [{f['status']:4}] {f['rule_id']:12} {f['block_id'] or '-':24} {f['detail']}")

    unenforced = report["coverage"]["unenforced_musts"]
    if unenforced:
        print(f"  [{'ERROR' if args.strict else 'note ':5}] {len(unenforced)} MUST rule(s) unenforced "
              f"(no implementation dispatched): {', '.join(unenforced)}")
    if args.strict and unenforced:
        return 1
    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
