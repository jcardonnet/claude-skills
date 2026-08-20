"""Orchestrate the six scoped binary critic passes against the IR block list.

Classification: agent-orchestrated (calls the model — NOT a hermetic function)
Implements: R-REJECT-05 + the soft_critic rules

For each pass (references/critic-prompts/*.md) this feeds the pass prompt + the applicable IR
blocks to a judge and collects BINARY verdicts keyed by rule_id + block_id. Discipline (R-REJECT-05):

  - Verdicts are strictly {pass, fail}. There is no numeric/holistic score anywhere, and
    `_validate_verdict` rejects anything else — holistic "is this good/thorough?" scoring is
    impossible by construction.
  - Gating items (MUST-priority rules) are still judged TWICE, but the FIRST verdict decides and
    the second is only recorded (`retest`, `flipped`). See `run_pass`.
  - Swap-and-average is implemented ONLY in `compare_revisions` (a pairwise call), never pointwise.

The judge is pluggable: the offline/test default is a deterministic stub; production wires a scoped
Claude call behind the same `Judge` protocol. Passes are independent -> structured to run
concurrently later.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from critics._errors import JudgeUnavailable  # noqa: E402
from ir.schema import Block, DocumentIR  # noqa: E402

CRITIC_DIR = Path(__file__).resolve().parents[2] / "references" / "critic-prompts"
DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "references" / "rule-registry.yaml"

_VALID_VERDICTS = {"pass", "fail"}  # the only two outcomes anywhere — see `run_pass` on retest
_RULE_HEADING_RE = re.compile(r"^####\s+(R-[A-Z]+-\d+)\b", re.MULTILINE)

DOCUMENT = "document"

# rule -> the block roles it targets; None means a document-level judgment (block_id == "document")
_ROLE_TARGETS: dict[str, set[str] | None] = {
    "R-CARD-01": {"card"}, "R-CARD-03": {"card"},
    "R-SUMM-01": {"lede"}, "R-SUMM-04": {"lede", "card", "summary"},
    "R-RECALL-02": {"recall"},
    "R-ART-03": {"toulmin"},
    "R-PROSE-01": {"lede", "card", "summary", "body", "toulmin"},
    "R-PROSE-02": {"lede", "card", "summary", "body", "toulmin"},
    "R-PROSE-03": {"lede", "card", "summary", "body", "toulmin"},
    "R-PROSE-06": {"lede", "card", "summary", "body", "toulmin"},
    "R-FIG-01": {"figure"}, "R-FIG-02": {"figure"}, "R-FIG-03": {"figure"}, "R-FIG-05": {"figure"},
}


def _targets(rule_id: str) -> set[str] | None:
    if rule_id in _ROLE_TARGETS:
        return _ROLE_TARGETS[rule_id]
    return None  # document-level by default (architecture, scent, mv, vocab, evid, depth, xref, ...)


@dataclass
class BlockView:
    """The slice of a block a critic sees (the 'parsed AST block list' the prompt references)."""

    block_id: str
    role: str
    concept: str | None = None
    mode: str | None = None
    text: str | None = None


def _view(b: Block) -> BlockView:
    return BlockView(b.block_id, b.role.value, b.concept, b.mode.value if b.mode else None,
                     b.readable_text)


_DOC_VIEW = BlockView(DOCUMENT, DOCUMENT)


def applicable_blocks(rule_id: str, ir: DocumentIR) -> list[BlockView]:
    roles = _targets(rule_id)
    if roles is None:
        return [_DOC_VIEW]
    return [_view(b) for b in ir.flatten_blocks() if b.role.value in roles]


@dataclass
class JudgeResult:
    verdict: str
    evidence: str = ""
    span: str | None = None


class Judge(Protocol):
    def __call__(self, pass_name: str, prompt: str, rule_id: str, block: BlockView, attempt: int) -> JudgeResult: ...


def _validate_verdict(v: str) -> str:
    if v not in _VALID_VERDICTS:
        raise ValueError(f"non-binary verdict {v!r}: critics return only {sorted(_VALID_VERDICTS)} (R-REJECT-05)")
    return v


@dataclass
class StubJudge:
    """Deterministic offline judge. `responder(pass, rule, block, attempt) -> (verdict, evidence)`;
    defaults to a uniform 'pass'. Used for tests and dry runs — never holistic, always per-rule."""

    responder: Callable[[str, str, BlockView, int], tuple[str, str]] | None = None

    def __call__(self, pass_name, prompt, rule_id, block, attempt) -> JudgeResult:
        if self.responder is None:
            return JudgeResult("pass", "stub: no responder")
        verdict, evidence = self.responder(pass_name, rule_id, block, attempt)
        return JudgeResult(_validate_verdict(verdict), evidence)


@dataclass
class ModelJudge:
    """Production seam: wraps a scoped model call returning a binary verdict for ONE (rule, block).
    `responder(prompt, rule_id, block) -> dict|str` must yield a binary verdict; non-binary raises."""

    responder: Callable[[str, str, BlockView], dict]

    def __call__(self, pass_name, prompt, rule_id, block, attempt) -> JudgeResult:
        raw = self.responder(prompt, rule_id, block)
        if isinstance(raw, str):
            raw = json.loads(raw)
        return JudgeResult(_validate_verdict(str(raw.get("verdict")).lower()),
                           raw.get("evidence", ""), raw.get("span"))


def load_passes(critic_dir: Path = CRITIC_DIR) -> list[tuple[str, list[str], str]]:
    out = []
    for path in sorted(critic_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        rule_ids = _RULE_HEADING_RE.findall(text)
        out.append((path.stem, rule_ids, text))
    return out


def _ir_digest(ir_path: Path) -> str:
    """Digest of what the CRITICS SEE in an IR — content addressing, never security.

    Not the raw file. Hashing bytes conflated "the document changed" with "the file changed":
    relabelling three blocks `verified` -> `inferred` invalidated a $17 run and dropped the
    soft_critic tier from 35 to 2, a false staleness report and exactly the kind of thing that
    teaches people to delete the guard. A comment edit would have done the same.

    And not a hand-written summary of the judged surface either, which is what replaced it. That
    version recorded `[block_id, role, concept, mode, readable_text]` plus section titles and
    asserted in its own docstring that the judge sees no provenance or source_ids — while
    `claude_judge._judge_document_view` builds the document unit out of `render_llm_md`, which
    prints `provenance:` into every block heading and a `Sources: [...]` line beneath it. Summary
    and surface had already drifted, so the very relabelling described above changed what every
    document-level critic read and moved this digest not at all: the guard was blind in exactly the
    direction it had been re-tuned to be blind in, and now sensitive nowhere it needed to be.

    `judged_surface` IS the surface, assembled by the helpers the judge itself calls. Imported
    lazily because claude_judge imports this module.
    """
    import hashlib
    import json as _json

    from critics.claude_judge import judged_surface
    from ir.schema import DocumentIR

    payload = _json.dumps(judged_surface(DocumentIR.from_yaml(ir_path)),
                          sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload, usedforsecurity=False).hexdigest()


def _gating_rules(registry_path: Path = DEFAULT_REGISTRY) -> set[str]:
    rules = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")).get("rules", [])
    return {r["id"] for r in rules if r.get("priority") == "MUST"}


def _retest(pass_name: str, prompt: str, rid: str, bv: BlockView, judge: Judge, gating: set[str],
            gating_judge: Judge | None, first: str) -> dict:
    """Ask a gating item a second time and RECORD the answer. It does not change the verdict.

    Test-retest used to collapse a disagreement into 'unstable', which sounds prudent and is not:
    the item then blocks nothing and clears nothing, so the rule silently stops gating for exactly
    the documents it is least sure about. Worse, the control was within-run only. Two judged runs
    over a byte-identical block — hence a byte-identical prompt, asserted by
    `test_a_block_scoped_judgement_cannot_see_the_rest_of_the_document` — returned opposite verdicts
    on R-SUMM-01, each internally retest-AGREEING. A control that cannot see the drift it exists to
    catch is not measuring stability; it is sampling it once and calling that a decision.

    So the first verdict gates, always, and the second becomes a measurement: `flake_rate` over a
    run says how much any single verdict is worth. Spend is unchanged — the same two calls — but a
    number that accumulates across runs replaces a veto that fired on n=2.
    """
    try:
        active = gating_judge if (gating_judge and rid in gating) else judge
        second = active(pass_name, prompt, rid, bv, 2).verdict
    except (JudgeUnavailable, OSError, TimeoutError) as exc:
        # The probe failing costs the measurement, not the verdict — that one is already in hand.
        return {"retest": None, "flipped": None, "retest_error": f"{type(exc).__name__}: {exc}"[:200]}
    return {"retest": second, "flipped": second != first}


def run_pass(pass_name: str, rule_ids: list[str], prompt: str, ir: DocumentIR, judge: Judge,
             gating: set[str], gating_judge: Judge | None = None) -> list[dict]:
    verdicts: list[dict] = []
    for rid in rule_ids:
        for bv in applicable_blocks(rid, ir):
            item = {"rule_id": rid, "block_id": bv.block_id}
            try:
                # Gating (MUST) rules go to `gating_judge` when one is supplied. Measured on this
                # fixture, haiku disagreed with itself on 6/21 gating items (29% — a coin flip on
                # rules that BLOCK) against sonnet's 1/21, and haiku also hard-FAILED two items
                # sonnet passed. Spending the better model exactly where items block is the cheap
                # half of the fix, and it is why the second call is still worth making.
                active = gating_judge if (gating_judge and rid in gating) else judge
                r1 = active(pass_name, prompt, rid, bv, 1)
                item.update(verdict=r1.verdict, evidence=r1.evidence, span=r1.span)
            except (JudgeUnavailable, OSError, TimeoutError) as exc:
                # An unreachable judge must not discard every judgement already made — the first
                # live run lost ~100 of them to one timeout. The item is recorded as 'error', never
                # coerced to 'pass': a judge that failed to answer has not cleared the rule. Note
                # the narrow catch — a non-binary verdict (ValueError) still propagates.
                item.update(verdict="error", evidence=f"{type(exc).__name__}: {exc}"[:300], span=None)
            if rid in gating and item["verdict"] != "error":
                item.update(_retest(pass_name, prompt, rid, bv, judge, gating, gating_judge,
                                    item["verdict"]))
            verdicts.append(item)
    return verdicts


def run_critics(ir: DocumentIR, judge: Judge | None = None, critic_dir: Path = CRITIC_DIR,
                registry_path: Path = DEFAULT_REGISTRY, only: set[str] | None = None,
                gating_judge: Judge | None = None) -> dict:
    judge = judge or StubJudge()
    gating = _gating_rules(registry_path)
    passes_out = []
    counts = {"pass": 0, "fail": 0, "error": 0}
    for pass_name, all_rule_ids, prompt in load_passes(critic_dir):
        # `only` narrows the run to specific rules. The pass PROMPT is still sent whole — a rule's
        # verdict depends on the calibration notes and sibling rules around it, so trimming the
        # prompt to match would change what is being measured. This is for re-judging a handful of
        # rules (a calibration sweep, a flaky item) without paying for all 114 calls.
        rule_ids = [r for r in all_rule_ids if only is None or r in only]
        if not rule_ids:
            continue
        verdicts = run_pass(pass_name, rule_ids, prompt, ir, judge, gating, gating_judge)
        for v in verdicts:
            counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
        passes_out.append({"pass": pass_name, "rules": rule_ids, "verdicts": verdicts})
    # Blocking derives from PRIORITY, not from enforcement or from the mere existence of a failure.
    # MUST blocks; SHOULD and MAY warn. This read `any fail`, so a MAY-priority critic rule — an
    # advisory judgement, on a tier the registry deliberately calls soft — exited the pass non-zero
    # and would fail CI. `gating` is already the MUST set; it was computed for test-retest and not
    # consulted here.
    blocking_failures = [{"pass": p["pass"], **v} for p in passes_out for v in p["verdicts"]
                         if v["verdict"] == "fail" and v["rule_id"] in gating]
    return {
        "passes": passes_out,
        "counts": counts,
        "blocking": bool(blocking_failures),
        "blocking_failures": blocking_failures,
        "advisory_failures": [{"pass": p["pass"], **v} for p in passes_out for v in p["verdicts"]
                              if v["verdict"] == "fail" and v["rule_id"] not in gating],
        "errored_items": [{"pass": p["pass"], **v} for p in passes_out for v in p["verdicts"]
                          if v["verdict"] == "error"],
        **_flake(passes_out),
    }


def _flake(passes_out: list[dict]) -> dict:
    """How often a gating verdict would have come out the other way, had we asked once more.

    Reported with its denominator, not as a bare ratio: at n=1 retested item a "100% flake rate" and
    a "1 in 1" are the same number and only one of them is honest about the sample. `retested` counts
    gating items whose probe actually answered, so a run where the probe kept timing out reads as a
    small sample rather than a stable one.
    """
    flagged = [{"pass": p["pass"], **v} for p in passes_out for v in p["verdicts"] if v.get("flipped")]
    retested = sum(1 for p in passes_out for v in p["verdicts"] if v.get("flipped") is not None)
    return {
        "flake": {"retested": retested, "flipped": len(flagged),
                  "flake_rate": round(len(flagged) / retested, 4) if retested else None},
        "flaky_items": flagged,
    }


def compare_revisions(rule_id: str, block_a: str, block_b: str,
                      pairwise_judge: Callable[[str, str, str], str]) -> dict:
    """Swap-and-average — the ONLY place it is allowed (a pairwise revision comparison, R-REJECT-05).

    `pairwise_judge(rule_id, first, second) -> 'A'|'B'|'tie'` is called in BOTH orders to cancel
    position bias; the averaged preference is returned.
    """
    forward = pairwise_judge(rule_id, block_a, block_b)        # A first
    reverse = pairwise_judge(rule_id, block_b, block_a)        # B first
    score = {"A": 0.0, "B": 0.0}
    for pref, first, second in ((forward, "A", "B"), (reverse, "B", "A")):
        if pref == "A":
            score[first] += 0.5
        elif pref == "B":
            score[second] += 0.5
        else:
            score["A"] += 0.25
            score["B"] += 0.25
    winner = "A" if score["A"] > score["B"] else "B" if score["B"] > score["A"] else "tie"
    return {"rule_id": rule_id, "winner": winner, "score": score, "orders": [forward, reverse]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the six scoped binary critic passes against a document-ir.yaml.")
    ap.add_argument("ir")
    ap.add_argument("--critic-dir", default=str(CRITIC_DIR))
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--out", default="critic-report.json")
    ap.add_argument("--judge", choices=("stub", "claude"), default="stub",
                    help="'stub' is a structural dry run (no model). 'claude' runs the real scoped "
                         "binary judge via the local claude CLI — one call per (rule, block).")
    ap.add_argument("--model", default="haiku", help="model for --judge claude (a binary verdict "
                                                     "does not need a frontier model)")
    ap.add_argument("--cost-cap", type=float, default=5.0,
                    help="abort once cumulative spend passes this many USD")
    ap.add_argument("--gating-model", help="model for MUST-priority (gating) rules; defaults to "
                                           "--model. Measured on the reference fixture, haiku "
                                           "disagreed with itself on 6/21 gating items vs sonnet's "
                                           "1/21 — a coin flip on the rules that actually block.")
    ap.add_argument("--rules", help="comma-separated rule ids to judge (default: all). The pass "
                                    "prompt is still sent whole, so a narrowed run measures the "
                                    "same thing a full one does — for calibration sweeps.")
    args = ap.parse_args(argv)

    ir = DocumentIR.from_yaml(args.ir)
    cli_judge = gating_cli_judge = None
    if args.judge == "claude":
        from critics.claude_judge import ClaudeCliJudge
        from utils.claude_cli import Budget
        # ONE budget across both judges: --cost-cap is a ceiling on the run, not on each model
        budget = Budget(cost_cap_usd=args.cost_cap)
        cli_judge = ClaudeCliJudge(ir, model=args.model, budget=budget)
        if args.gating_model and args.gating_model != args.model:
            gating_cli_judge = ClaudeCliJudge(ir, model=args.gating_model, budget=budget)
    judge: Judge = cli_judge or StubJudge()

    only = {r.strip() for r in args.rules.split(",") if r.strip()} if args.rules else None
    report = run_critics(ir, judge, Path(args.critic_dir), Path(args.registry), only,
                         gating_cli_judge)
    # A stub run exercises the dispatch wiring and NOTHING else. Stamp which judge produced this, or
    # the artifact is indistinguishable from a real run that happened to find nothing — which is the
    # silent-skip failure the whole registry is built to avoid.
    # Stamp WHAT was judged. A frozen critic report is replayed as coverage by eval, and an IR that
    # has changed since means those verdicts describe a different document — silently. Editing two
    # sentences of the reference fixture was enough to make a $18 report stale with nothing to show
    # it. The digest lets eval detect that instead of crediting judgements of prose that is gone.
    report["ir_sha256"] = _ir_digest(Path(args.ir))
    if cli_judge is None:
        report["judge"] = {"kind": "stub", "exercised_rules": False}
    else:
        # Read the shared Budget ONCE. Both judges are constructed against the same `budget` object
        # — that is what makes --cost-cap a ceiling on the run rather than on each model — and
        # `ClaudeCli.calls` / `.spend_usd` are properties reading straight through to it, so adding
        # them together reports exactly double.
        #
        # This does NOT mean the committed critic-report.full.json is doubled; an earlier version of
        # this comment claimed it was, and that was wrong. That report predates the shared Budget
        # (it was judged at 97ab26e; Budget arrived at 976db04), so its two judges had independent
        # counters and summing them was correct. Its `calls: 113` is odd, which settles it — a
        # double count is n + n. The bug's window was 976db04..abf363c, and no report was made in it.
        calls, spend = cli_judge.calls, cli_judge.spend_usd
        report["judge"] = {"kind": "claude", "model": args.model, "calls": calls,
                           "spend_usd": round(spend, 4), "exercised_rules": True}
        # Which model judged the GATING (MUST) items — always recorded, whether or not a second
        # judge was built. `--gating-model sonnet --model sonnet` builds no second judge (they are
        # the same model), and stamping only in that branch left the STRONGEST configuration
        # unstamped, so a consumer keying on the field read "everything on sonnet" as less
        # trustworthy than "haiku with sonnet gating".
        report["judge"]["gating_model"] = args.gating_model or args.model
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    c = report["counts"]
    f_ = report["flake"]
    print(f"{len(report['passes'])} passes — pass={c['pass']} fail={c['fail']} "
          f"error={c.get('error', 0)} -> {args.out}")
    print(f"flake: {f_['flipped']}/{f_['retested']} gating verdicts flipped on retest "
          f"(recorded, not gating)")
    if cli_judge is not None:
        stamp = report["judge"]
        gating_note = f" (gating: {args.gating_model})" if gating_cli_judge else ""
        print(f"judge: {args.model}{gating_note}, {stamp['calls']} calls, ${stamp['spend_usd']:.2f}")
    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
