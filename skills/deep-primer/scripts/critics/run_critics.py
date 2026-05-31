"""Orchestrate the six scoped binary critic passes against the IR block list.

Classification: agent-orchestrated (calls the model — NOT a hermetic function)
Implements: R-REJECT-05 + the soft_critic rules

For each pass (references/critic-prompts/*.md) this feeds the pass prompt + the applicable IR
blocks to a judge and collects BINARY verdicts keyed by rule_id + block_id. Discipline (R-REJECT-05):

  - Verdicts are strictly {pass, fail, unstable}. There is no numeric/holistic score anywhere, and
    `_validate_verdict` rejects anything else — holistic "is this good/thorough?" scoring is
    impossible by construction.
  - Gating items (MUST-priority rules) are judged TWICE (test-retest); disagreement -> 'unstable'.
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

from ir.schema import Block, DocumentIR  # noqa: E402

CRITIC_DIR = Path(__file__).resolve().parents[2] / "references" / "critic-prompts"
DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "references" / "rule-registry.yaml"

_VALID_VERDICTS = {"pass", "fail"}  # what a judge may return; 'unstable' is assigned by test-retest
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
    return BlockView(b.block_id, b.role.value, b.concept, b.mode.value if b.mode else None, b.text or b.caption)


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


def _gating_rules(registry_path: Path = DEFAULT_REGISTRY) -> set[str]:
    rules = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")).get("rules", [])
    return {r["id"] for r in rules if r.get("priority") == "MUST"}


def run_pass(pass_name: str, rule_ids: list[str], prompt: str, ir: DocumentIR, judge: Judge,
             gating: set[str]) -> list[dict]:
    verdicts: list[dict] = []
    for rid in rule_ids:
        for bv in applicable_blocks(rid, ir):
            r1 = judge(pass_name, prompt, rid, bv, 1)
            verdict = r1.verdict
            if rid in gating:  # test-retest gating items
                r2 = judge(pass_name, prompt, rid, bv, 2)
                if r2.verdict != r1.verdict:
                    verdict = "unstable"
            verdicts.append({"rule_id": rid, "block_id": bv.block_id, "verdict": verdict,
                             "evidence": r1.evidence, "span": r1.span})
    return verdicts


def run_critics(ir: DocumentIR, judge: Judge | None = None, critic_dir: Path = CRITIC_DIR,
                registry_path: Path = DEFAULT_REGISTRY) -> dict:
    judge = judge or StubJudge()
    gating = _gating_rules(registry_path)
    passes_out = []
    counts = {"pass": 0, "fail": 0, "unstable": 0}
    for pass_name, rule_ids, prompt in load_passes(critic_dir):
        verdicts = run_pass(pass_name, rule_ids, prompt, ir, judge, gating)
        for v in verdicts:
            counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
        passes_out.append({"pass": pass_name, "rules": rule_ids, "verdicts": verdicts})
    return {
        "passes": passes_out,
        "counts": counts,
        "blocking": counts.get("fail", 0) > 0,
        "unstable_items": [{"pass": p["pass"], **v} for p in passes_out for v in p["verdicts"]
                           if v["verdict"] == "unstable"],
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
    args = ap.parse_args(argv)
    # No model is wired at the CLI (agent-orchestrated): the stub judge produces a structural dry run.
    report = run_critics(DocumentIR.from_yaml(args.ir), StubJudge(), Path(args.critic_dir), Path(args.registry))
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    c = report["counts"]
    print(f"{len(report['passes'])} passes — pass={c['pass']} fail={c['fail']} unstable={c['unstable']} -> {args.out}")
    return 1 if report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
