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
from checks._base import LintContext  # noqa: E402
from ir.schema import ConceptMap, DocumentIR, SourceLedger  # noqa: E402

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "references" / "rule-registry.yaml"

# check.ref (verbatim from the registry) -> implemented callable. Refs absent here are 'skip'.
CHECKS = {
    "checks/structure_coverage.py::layer_coverage": structure_coverage.layer_coverage,
    "checks/structure_coverage.py::length_budget": structure_coverage.length_budget,
    "checks/prose_caps.py::compression_gradient": prose_caps.compression_gradient,
    "checks/prose_caps.py::length_caps": prose_caps.length_caps,
    "checks/prose_caps.py::condition_first": prose_caps.condition_first,
    "checks/coherence_givennew.py::entity_grid": coherence_givennew.entity_grid,
    "checks/univocity_terms.py::canonical_terms": univocity_terms.canonical_terms,
    "checks/multiview_concepts.py::modes_per_concept": multiview_concepts.modes_per_concept,
    "checks/recency_versions.py::version_freshness": recency_versions.version_freshness,
    "checks/footnote.py::footnote_balance": footnote.footnote_balance,
    "checks/xrefs.py::xrefs_resolve": xrefs.xrefs_resolve,
    "checks/provenance.py::tagged": provenance.tagged,
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
    violations = fn(ctx)
    if not violations:
        return [_record(rule, ref, None, "pass", "ok")]
    return [_record(rule, ref, v.block_id, _status_for(rule, v.force_status), v.detail) for v in violations]


def _refs_for(rule: dict) -> list[str]:
    """A hard_lint rule's own ref, plus any also_hard_lint companion on a soft rule."""
    refs: list[str] = []
    chk = rule.get("check", {})
    if rule.get("enforcement") == "hard_lint" and chk.get("ref"):
        refs.append(chk["ref"])
    if chk.get("also_hard_lint"):
        refs.append(chk["also_hard_lint"])
    return refs


def run_lint(ctx: LintContext, registry_path: str | Path = DEFAULT_REGISTRY) -> dict:
    rules = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")).get("rules", [])
    findings: list[dict] = []
    for rule in rules:
        for ref in _refs_for(rule):
            findings.extend(_run_ref(rule, ref, ctx))

    counts: dict[str, int] = {}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    return {
        "blocking": any(f["status"] == "fail" for f in findings),
        "counts": counts,
        "findings": findings,
    }


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
    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
