"""Eval harness: score generated primers against the registry, per spec.

Classification: local-deterministic
Implements: the quantitative loop (Prompt 7)

Loads `references/eval/specs/*.yaml` plus `eval-rubric.yaml` and scores whatever artifacts a spec
points at, across the three enforcement tiers the registry defines:

  hard_lints      scripts/lint.py over the IR (+ the html / ledger / convergence passes)
  model_verified  scripts/verify/* — citation recall + precision, chunk self-containment
  human_overlay   spot-check labels, when a spec supplies them

Two deliberate properties:

  - a spec with NO artifact reports `not_generated` rather than passing. An eval that silently
    scores nothing is worse than one that reports zero coverage, because it reads as a green run.
  - the report carries `enforcement_coverage` — how many registry rules were actually exercised.
    Stage A's whole finding was that unenforced rules look identical to passing ones unless the
    report says otherwise.

Usage:
    python scripts/eval.py                       # score every spec
    python scripts/eval.py --spec spec-01-rag-chunking --out eval-report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from ir.schema import ConceptMap, ConvergenceLog, DocumentIR, SourceLedger  # noqa: E402
from lint import (  # noqa: E402
    lint_files,
    run_convergence_pass,
    run_html_pass,
    run_ledger_pass,
    run_llm_md_pass,
)
from verify._entailment import resolve_backend  # noqa: E402
from verify.citation_quality import evaluate as verify_citations  # noqa: E402
from verify.citation_quality import load_thresholds  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = SKILL_ROOT / "references" / "eval" / "specs"
RUBRIC = SKILL_ROOT / "references" / "eval" / "eval-rubric.yaml"

_ARTIFACT_FILES = {
    "ir": "document-ir.yaml",
    "concept_map": "concept-map.yaml",
    "ledger": "source-ledger.yaml",
    "convergence_log": "convergence-log.yaml",
    "critic_report": "critic-report.json",
}


def load_specs(spec_dir: Path = SPEC_DIR) -> list[dict]:
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(spec_dir.glob("*.yaml"))]


def resolve_artifacts(spec: dict, root: Path = SKILL_ROOT) -> dict[str, Path]:
    """Where a spec's generated artifacts live.

    `artifact` may name a directory (conventional filenames inside) or map roles to explicit paths,
    so a spec can point at a hand-built reference artifact before a real generation exists.
    """
    ref = spec.get("artifact")
    if not ref:
        return {}
    if isinstance(ref, dict):
        # existence-checked: a bundled skill drops tests/, and a spec pointing at a missing file
        # should report `not_generated` rather than crash the whole eval run
        return {k: (root / v) for k, v in ref.items() if (root / v).is_file()}
    d = root / ref
    return {k: d / name for k, name in _ARTIFACT_FILES.items() if (d / name).is_file()}


def _tier_hard_lints(paths: dict[str, Path]) -> dict:
    report = lint_files(paths["ir"], paths.get("concept_map"), paths.get("ledger"))
    out = {
        "blocking": report["blocking"],
        "counts": report["counts"],
        "coverage": report["coverage"],
        "failures": [{"rule_id": f["rule_id"], "detail": f["detail"]}
                     for f in report["findings"] if f["status"] == "fail"],
        "warnings": sorted({f["rule_id"] for f in report["findings"] if f["status"] == "warn"}),
        "rules_exercised": sorted({f["rule_id"] for f in report["findings"]}),
    }

    # the artifact passes, each only when its artifact exists
    if paths.get("ledger"):
        led = run_ledger_pass(SourceLedger.from_yaml(paths["ledger"]))
        out["ledger_pass"] = {"counts": led["counts"],
                              "failures": [f["detail"] for f in led["findings"] if f["status"] == "fail"]}
        out["rules_exercised"] += [f["rule_id"] for f in led["findings"]]
    if paths.get("convergence_log"):
        conv = run_convergence_pass(ConvergenceLog.from_yaml(paths["convergence_log"]))
        out["convergence_pass"] = {"counts": conv["counts"],
                                   "failures": [f["detail"] for f in conv["findings"] if f["status"] == "fail"]}
        out["rules_exercised"] += [f["rule_id"] for f in conv["findings"]]

    if paths.get("ir"):
        from render.check_alignment import check_alignment
        from render.render_html import render_html
        from render.render_llm_md import render_llm_md

        ir = DocumentIR.from_yaml(paths["ir"])
        cm = ConceptMap.from_yaml(paths["concept_map"]) if paths.get("concept_map") else None
        html = render_html(ir, cm)
        htm = run_html_pass(html)
        out["html_pass"] = {"counts": htm["counts"],
                            "failures": [f["detail"] for f in htm["findings"] if f["status"] == "fail"]}
        out["rules_exercised"] += [f["rule_id"] for f in htm["findings"]]

        # R-PROJ-02 is deterministic (a set comparison over block-ids), so eval can exercise it
        # for real rather than leaving it to a critic
        md = render_llm_md(ir, cm)
        align = check_alignment(html, md)
        out["projections_pass"] = {"ok": align["ok"], "html_only": align["html_only"],
                                   "md_only": align["md_only"]}
        out["rules_exercised"].append("R-PROJ-02")

        mdp = run_llm_md_pass(md, ir)
        out["llm_md_pass"] = {"counts": mdp["counts"],
                              "failures": [f["detail"] for f in mdp["findings"] if f["status"] == "fail"]}
        out["rules_exercised"] += [f["rule_id"] for f in mdp["findings"]]
        if not align["ok"]:
            out["failures"].append({"rule_id": "R-PROJ-02",
                                    "detail": f"projection block-ids misaligned: {align}"})
            out["blocking"] = True

    out["rules_exercised"] = sorted(set(out["rules_exercised"]))
    return out


def _tier_model_verified(paths: dict[str, Path], rubric_path: Path,
                         backend: object | None = None) -> dict:
    if not paths.get("ledger"):
        return {"status": "skipped", "reason": "no source-ledger artifact"}
    thresholds = load_thresholds(rubric_path)
    ir = DocumentIR.from_yaml(paths["ir"])
    ledger = SourceLedger.from_yaml(paths["ledger"])
    report = verify_citations(ir, ledger, backend=backend, thresholds=thresholds)
    out = {
        "status": "scored",
        "backend": report["backend"],
        "recall": report["recall"],
        "precision": report["precision"],
        "thresholds": thresholds,
        "meets_recall": report["recall"] >= thresholds["recall"],
        "meets_precision": report["precision"] >= thresholds["precision"],
        "unresolved_citations": len(report["resolves_to_ledger"]["violations"]),
        "counts": report["counts"],
    }

    # R-PROJ-04 (chunk self-containment) is model_verified and MUST, and the verifier for it has
    # existed and been unit-tested since Stage A — the eval harness simply never called it, so the
    # rule read as "unexercised" forever while looking no different from a passing one. That is the
    # silent-skip class, and the coverage gate is what surfaced it.
    from verify.chunk_selfcontained import verify as verify_chunks
    cm = ConceptMap.from_yaml(paths["concept_map"]) if paths.get("concept_map") else None
    chunks = verify_chunks(ir, ledger, cm, backend=backend)
    out["chunk_selfcontained"] = {
        "ok": chunks["ok"],
        "backend": chunks["backend"],
        "blocks": len(chunks["verdicts"]),
        "failures": chunks["failures"],
    }
    return out


def _tier_soft_critic(paths: dict[str, Path]) -> dict:
    """Score the critic tier from a run_critics report, if the spec's artifacts include one.

    The safety property here is the whole point: a report produced by `StubJudge` is stamped
    `exercised_rules: false` and is NOT credited as coverage. A stub run returns 'pass' for every
    (rule, block) pair without consulting anything, so counting it would manufacture a green
    35/35 soft_critic tier out of a judge that never read a word — Stage A's silent-skip failure
    with the sign flipped, and far more flattering, which is what would make it stick.
    """
    path = paths.get("critic_report")
    if not path:
        return {"status": "not_run",
                "reason": "no critic-report.json — scripts/critics/run_critics.py --judge claude"}
    report = json.loads(path.read_text(encoding="utf-8"))
    judge = report.get("judge") or {}

    # A frozen report judged a specific IR. If that IR has since changed, these verdicts describe a
    # document that no longer exists, and crediting them is coverage for judging something else —
    # the same class of lie as counting a stub, just harder to notice.
    stamped, actual = report.get("ir_sha256"), _ir_digest(paths.get("ir"))
    if stamped and actual and stamped != actual:
        return {"status": "stale", "judge": judge, "rules_exercised": [],
                "reason": f"critic report was judged against a different IR "
                          f"({stamped[:12]}… vs {actual[:12]}…) — re-run run_critics"}
    verdicts = [v for p in report.get("passes", []) for v in p.get("verdicts", [])]
    if not judge.get("exercised_rules"):
        return {"status": "stub_only", "judge": judge, "rules_exercised": [],
                "reason": "critic report came from the stub judge; not counted as coverage"}
    return {
        "status": "scored",
        "judge": judge,
        # 'error' means the judge never answered for that (rule, block). A rule whose every verdict
        # errored was attempted, not exercised — crediting it would be the same lie as counting a
        # stub. A rule with at least one real verdict did run, so it counts.
        "rules_exercised": sorted({v["rule_id"] for v in verdicts if v["verdict"] != "error"}),
        "counts": report.get("counts", {}),
        "failed": sorted({v["rule_id"] for v in verdicts if v["verdict"] == "fail"}),
        "unstable": sorted({v["rule_id"] for v in verdicts if v["verdict"] == "unstable"}),
        "errored": sorted({v["rule_id"] for v in verdicts if v["verdict"] == "error"}),
    }


def _tier_human(spec: dict) -> dict:
    labels = spec.get("human_labels")
    if not labels:
        return {"status": "no_labels"}
    return {"status": "scored", "labels": labels}


_ARTIFACT_TIERS = {"discovery-log": "needs a discovery campaign artifact",
                   "discovery-leads": "needs a discovery campaign artifact",
                   "snapshot": "needs a frozen discovery snapshot",
                   "convergence-log": "needs a convergence-log artifact"}


def _ir_digest(ir_path: Path | None) -> str | None:
    """Digest of an IR file — content addressing, never security. Mirrors run_critics._ir_digest."""
    import hashlib
    if not ir_path or not Path(ir_path).is_file():
        return None
    return hashlib.sha256(Path(ir_path).read_bytes(), usedforsecurity=False).hexdigest()


SILENT_SKIP = "DETERMINISTIC RULE NOT EXERCISED — investigate (silent-skip class)"


def _why_unexercised(rule_id: str, rules: list[dict] | None = None) -> str:
    """Classify why a rule never ran — a judge gap, a missing artifact, or a real hole.

    `rules` lets a caller hand the registry in once. Classifying all 79 rules for the coverage gate
    would otherwise re-read and re-parse rule-registry.yaml once per rule.
    """
    for rule in (registry_rules() if rules is None else rules):
        if rule["id"] != rule_id:
            continue
        enforcement = rule["enforcement"]
        if enforcement == "soft_critic":
            return "soft_critic — needs a judge model (not run offline)"
        if enforcement == "human":
            return "human — maintainer judgment, never auto-checked"
        artifact = (rule.get("check") or {}).get("input")
        if artifact in _ARTIFACT_TIERS:
            return _ARTIFACT_TIERS[artifact]
        return SILENT_SKIP
    return "unknown rule id"


def score_spec(spec: dict, root: Path = SKILL_ROOT, rubric_path: Path = RUBRIC,
               backend: object | None = None) -> dict:
    paths = resolve_artifacts(spec, root)
    result = {
        "id": spec["id"],
        "parameters": spec.get("parameters", {}),
        "expected_must_pass": (spec.get("expect") or {}).get("must_pass", []),
    }
    if not paths.get("ir"):
        # not a pass: an eval that silently scores nothing reads as a green run
        result["status"] = "not_generated"
        result["detail"] = "no artifact — run the pipeline for this spec, or point `artifact:` at one"
        return result

    hard = _tier_hard_lints(paths)
    model = _tier_model_verified(paths, rubric_path, backend)
    critics = _tier_soft_critic(paths)
    human = _tier_human(spec)

    # The union across ALL tiers, kept beside them rather than folded back into `hard_lints`.
    # It used to be written back onto hard_lints["rules_exercised"], so the lint tier's own report
    # claimed credit for rules the linter never touched — harmless while it was two citation rules,
    # actively misleading once the critic tier can contribute 35 more.
    exercised = set(hard["rules_exercised"])
    if model.get("status") == "scored":
        # recall/precision genuinely ran; attribute them or the tier reads as 0% exercised
        exercised |= {"R-GROUND-02", "R-GROUND-03"}
        if "chunk_selfcontained" in model:
            exercised.add("R-PROJ-04")
    exercised |= set(critics.get("rules_exercised") or [])
    expected = result["expected_must_pass"]
    unexercised = [r for r in expected if r not in exercised]
    # a critic FAIL on an expected rule is a real failure, exactly like a lint fail. 'unstable' is
    # not folded in: test-retest disagreement means the judge could not decide, which is a signal
    # about the judge, and silently scoring it as a failure would blame the primer for that.
    failed_expected = sorted({f["rule_id"] for f in hard["failures"] if f["rule_id"] in expected}
                             | {r for r in (critics.get("failed") or []) if r in expected})

    result.update({
        "status": "scored",
        "rules_exercised": sorted(exercised),
        "hard_lints": hard,
        "model_verified": model,
        "soft_critic": critics,
        "human_overlay": human,
        "expected_must_pass_report": {
            "failed": failed_expected,
            # a rule the spec expects but the run never exercised is NOT a pass
            "not_exercised": unexercised,
            # ...but WHY it didn't run matters: a soft_critic rule needs a judge model and is
            # expected to be unexercised offline, while an unexercised deterministic rule is the
            # silent-skip bug Stage A existed to fix. Collapsing the two hides the second.
            "not_exercised_reason": {r: _why_unexercised(r) for r in unexercised},
        },
    })

    # a spec passes only if nothing blocked, no expected rule failed, every expected rule actually
    # ran, and — when it could be scored — citation quality cleared both thresholds
    model_ok = model.get("status") != "scored" or (model.get("meets_recall") and model.get("meets_precision"))
    result["passed"] = bool(
        not hard["blocking"] and not failed_expected and not unexercised and model_ok)
    return result


def registry_rules(registry_path: Path | None = None) -> list[dict]:
    path = registry_path or (SKILL_ROOT / "references" / "rule-registry.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]


def registry_rule_ids(registry_path: Path | None = None) -> list[str]:
    return [r["id"] for r in registry_rules(registry_path)]


def _coverage_by_enforcement(exercised: set[str]) -> dict:
    """Coverage split by enforcement tier.

    A bare fraction misleads here: the deterministic tier is the only one this harness can score
    offline, so 33% overall is mostly "critics need a judge model", not "two-thirds unenforced".
    Reporting it per tier keeps the genuinely-unenforced deterministic rules visible — which is the
    failure mode Stage A existed to fix.
    """
    out: dict[str, dict] = {}
    for rule in registry_rules():
        tier = rule["enforcement"]
        bucket = out.setdefault(tier, {"total": 0, "exercised": 0, "unexercised": []})
        bucket["total"] += 1
        if rule["id"] in exercised:
            bucket["exercised"] += 1
        else:
            bucket["unexercised"].append(rule["id"])
    for bucket in out.values():
        bucket["fraction"] = round(bucket["exercised"] / bucket["total"], 4) if bucket["total"] else 0.0
    return out


def _spec_strict_failures(results: list[dict], rules: list[dict]) -> list[dict]:
    """Spec failures a strict run must not tolerate.

    A spec fails for two very different reasons and only one of them is a defect:

      - it FAILED a rule, or missed a citation threshold  -> a real failure
      - a rule it expects never ran, because this environment has no judge model and no generated
        artifact                                          -> the documented offline state

    Collapsing the two would make --strict useless: spec-01 fails on exactly the second kind today,
    so a gate keyed on `passed` would be red on every offline run and get switched off. Keying on
    the classification instead means the gate is quiet about the known gaps and loud about defects.
    """
    out = []
    for r in results:
        if r["status"] != "scored":
            continue
        hard, mv, expected = r["hard_lints"], r["model_verified"], r["expected_must_pass_report"]
        reasons = []
        if hard["blocking"]:
            reasons.append("blocking lint failure")
        if expected["failed"]:
            reasons.append(f"expected rule(s) FAILED: {', '.join(expected['failed'])}")
        # Only gate citation quality on a backend whose numbers mean something. The lexical proxy
        # scores word overlap between a <=15-word quote and a block R-GROUND-01 requires to be a
        # PARAPHRASE, so a low score there is compliance, not a defect — which is exactly why
        # propose_thresholds() refuses to derive a floor from it. Failing on the same numbers it
        # refuses to trust would be incoherent, and would make --strict permanently red offline.
        if (mv.get("status") == "scored" and mv.get("backend") != "lexical"
                and not (mv.get("meets_recall") and mv.get("meets_precision"))):
            reasons.append(f"citation quality below threshold "
                           f"(recall={mv['recall']} precision={mv['precision']}, "
                           f"backend={mv.get('backend')})")
        silent = [rid for rid in expected["not_exercised"]
                  if _why_unexercised(rid, rules) == SILENT_SKIP]
        if silent:
            reasons.append(f"expected but silently unexercised: {', '.join(silent)}")
        if reasons:
            out.append({"spec": r["id"], "reasons": reasons})
    return out


def coverage_gate(exercised: set[str], results: list[dict], rubric_path: Path = RUBRIC,
                  partial: bool = False) -> dict:
    """The ratchet `--strict` enforces — see the `coverage_floor` note in eval-rubric.yaml.

    Three ways to fail: a tier drops below its declared floor, a deterministic rule goes dark with
    no attributable reason, or a spec fails for a reason that is not the documented offline gap.

    `partial` (a `--spec`-narrowed run) suspends the FLOORS only. A floor counts rules exercised
    across every spec, so comparing it against one spec's coverage would fail for the wrong reason —
    and a gate that cries wolf on a routine single-spec run is a gate someone switches off. The
    other two checks stay armed: a silent skip and a real spec failure are local facts, still true
    when only one spec ran.
    """
    rules = registry_rules()
    rubric = yaml.safe_load(rubric_path.read_text(encoding="utf-8")) or {}
    floors = {tier: int(n) for tier, n in (rubric.get("coverage_floor") or {}).items()}
    by_tier = _coverage_by_enforcement(exercised)

    shortfalls = [] if partial else [
        {"tier": tier, "floor": floor, "exercised": by_tier.get(tier, {}).get("exercised", 0)}
        for tier, floor in sorted(floors.items())
        if by_tier.get(tier, {}).get("exercised", 0) < floor]
    silent = sorted(r["id"] for r in rules
                    if r["id"] not in exercised and _why_unexercised(r["id"], rules) == SILENT_SKIP)
    spec_failures = _spec_strict_failures(results, rules)
    return {
        "scope": "partial" if partial else "full",
        "floors": floors,
        "floors_enforced": not partial,
        "shortfalls": shortfalls,
        "silent_skips": silent,
        "spec_failures": spec_failures,
        "passed": not shortfalls and not silent and not spec_failures,
    }


def run_eval(spec_dir: Path = SPEC_DIR, root: Path = SKILL_ROOT, rubric_path: Path = RUBRIC,
             only: str | None = None, backend: object | None = None) -> dict:
    specs = [s for s in load_specs(spec_dir) if only is None or s["id"] == only]
    results = [score_spec(s, root, rubric_path, backend) for s in specs]

    exercised: set[str] = set()
    for r in results:
        if r["status"] == "scored":
            exercised |= set(r["rules_exercised"])
    all_rules = registry_rule_ids()

    return {
        "specs_total": len(results),
        "specs_scored": sum(1 for r in results if r["status"] == "scored"),
        "specs_not_generated": sorted(r["id"] for r in results if r["status"] == "not_generated"),
        "specs_passed": sorted(r["id"] for r in results if r.get("passed")),
        "enforcement_coverage": {
            "rules_total": len(all_rules),
            "rules_exercised": len(exercised),
            "fraction": round(len(exercised) / len(all_rules), 4) if all_rules else 0.0,
            "by_enforcement": _coverage_by_enforcement(exercised),
            "unexercised": sorted(set(all_rules) - exercised),
        },
        "coverage_gate": coverage_gate(exercised, results, rubric_path, partial=only is not None),
        "results": results,
    }


def propose_thresholds(report: dict) -> dict:
    """Suggest citation thresholds from what was actually observed — or refuse, with the reason.

    It REFUSES on the offline lexical backend, and that refusal is the point. The proxy scores
    token overlap between a <=15-word quote and a full block, while R-GROUND-01 requires the primer
    to PARAPHRASE rather than reproduce. Low overlap is therefore the designed behaviour of a
    compliant primer, not evidence of bad citations — so a floor derived from it would be
    meaningless, and writing it into eval-rubric.yaml would silently disable the check.
    """
    recalls, precisions, backends = [], [], set()
    for r in report["results"]:
        mv = r.get("model_verified") or {}
        if mv.get("status") == "scored":
            recalls.append(mv["recall"])
            precisions.append(mv["precision"])
            backends.add(mv.get("backend"))
    if not recalls:
        return {"status": "insufficient_data", "scored_specs": 0}

    observed = {"recall_min": min(recalls), "precision_min": min(precisions),
                "backends": sorted(b for b in backends if b)}
    if backends <= {"lexical"}:
        return {
            "status": "refused",
            "scored_specs": len(recalls),
            "observed": observed,
            "reason": ("scored only with the offline lexical proxy, which measures word overlap "
                       "between a short quote and a paraphrased block — low scores are what a "
                       "COMPLIANT primer produces. Re-run with --backend nli or claude before "
                       "setting citation_recall / citation_precision."),
        }
    return {
        "status": "proposed",
        "scored_specs": len(recalls),
        "observed": observed,
        "citation_recall": max(0.0, round(min(recalls) - 0.05, 2)),
        "citation_precision": max(0.0, round(min(precisions) - 0.05, 2)),
        "caveat": "a floor from the artifacts present; re-calibrate against real generations (Stage G)",
    }


def _print_gate(gate: dict) -> None:
    for s in gate["shortfalls"]:
        print(f"  coverage REGRESSED: {s['tier']} exercised {s['exercised']}, floor is {s['floor']}")
    for rule in gate["silent_skips"]:
        print(f"  silent skip: {rule} — {SILENT_SKIP}")
    for sf in gate["spec_failures"]:
        print(f"  {sf['spec']} failed strictly: {'; '.join(sf['reasons'])}")
    if not gate["floors_enforced"]:
        print("  coverage floors NOT enforced: --spec narrowed the run, and a floor counts rules "
              "across every spec")
    print(f"coverage gate: {'PASS' if gate['passed'] else 'FAIL'}"
          + ("" if gate["passed"] else " (use --strict to make this exit non-zero)"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score deep-primer eval specs against the registry.")
    ap.add_argument("--spec", help="score only this spec id")
    ap.add_argument("--specs-dir", default=str(SPEC_DIR))
    ap.add_argument("--root", default=str(SKILL_ROOT), help="root that spec `artifact:` paths resolve against")
    ap.add_argument("--rubric", default=str(RUBRIC))
    ap.add_argument("--out", default="eval-report.json")
    ap.add_argument("--backend", default="auto", choices=("auto", "lexical", "nli", "claude"),
                    help="entailment backend for the model_verified tier. 'auto'/'lexical' is the "
                         "offline word-overlap proxy, whose scores cannot support a threshold — "
                         "'nli' or 'claude' is required before citation_recall/precision mean "
                         "anything (see propose_thresholds)")
    ap.add_argument("--entailment-cost-cap", type=float, default=5.0,
                    help="USD ceiling for --backend claude; the run aborts rather than overspending")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if coverage regressed below the rubric's coverage_floor, a "
                         "deterministic rule went dark unattributed, or a spec failed for any "
                         "reason other than the documented offline judge/artifact gap")
    args = ap.parse_args(argv)

    judge = None
    if args.backend == "claude":
        from verify.claude_entailment import ClaudeEntailmentJudge
        judge = ClaudeEntailmentJudge(cost_cap_usd=args.entailment_cost_cap)
    backend = resolve_backend(args.backend, judge_fn=judge)

    report = run_eval(Path(args.specs_dir), Path(args.root), Path(args.rubric), args.spec, backend)
    if judge is not None:
        report["entailment_judge"] = {"calls": judge.calls, "spend_usd": round(judge.spend_usd, 4),
                                      "unresolved": judge.unresolved[:20]}
    report["proposed_thresholds"] = propose_thresholds(report)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    cov = report["enforcement_coverage"]
    print(f"specs: {report['specs_scored']}/{report['specs_total']} scored "
          f"({len(report['specs_not_generated'])} not generated)")
    print(f"enforcement coverage: {cov['rules_exercised']}/{cov['rules_total']} rules exercised "
          f"({cov['fraction']:.0%})")
    for tier, b in sorted(cov["by_enforcement"].items()):
        print(f"    {tier:16} {b['exercised']:>2}/{b['total']:<3} ({b['fraction']:.0%})")
    for r in report["results"]:
        if r["status"] != "scored":
            print(f"  [{'skip':7}] {r['id']}: {r['detail']}")
            continue
        hard, mv = r["hard_lints"], r["model_verified"]
        verdict = "PASS" if r["passed"] else "FAIL"
        print(f"  [{verdict:7}] {r['id']}: "
              f"lint fail={hard['counts'].get('fail', 0)} warn={hard['counts'].get('warn', 0)}"
              + (f" | recall={mv['recall']} precision={mv['precision']}"
                 if mv.get("status") == "scored" else " | model_verified skipped"))
        for f in hard["failures"]:
            print(f"            - {f['rule_id']}: {f['detail']}")
        for rule in r["expected_must_pass_report"]["not_exercised"]:
            print(f"            - {rule}: expected by the spec but never exercised")
    pt = report["proposed_thresholds"]
    if pt["status"] == "proposed":
        print(f"proposed thresholds: citation_recall={pt['citation_recall']} "
              f"citation_precision={pt['citation_precision']} (from {pt['scored_specs']} scored spec(s))")
    elif pt["status"] == "refused":
        print(f"thresholds NOT proposed: {pt['reason']}")
        print(f"  observed (proxy only): {pt['observed']}")

    _print_gate(report["coverage_gate"])
    print(f"-> {args.out}")
    return 1 if (args.strict and not report["coverage_gate"]["passed"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
