"""Repo-conformance checks: the nine rules the registry files under `human`.

Classification: local-deterministic
Implements: R-REJECT-01..05, R-PROJ-01, R-CONV-02, R-DISC-01, R-DISC-04

Why these are checkable at all
------------------------------
All nine were unexercised, classified as "maintainer judgment, never auto-checked". Reading them
together shows that is not what they are. Not one of them is about a generated primer, which is what
a human overlay would review. Every one is an assertion about THIS CODEBASE:

  - R-REJECT-01..05 are prohibitions on the pipeline's own design — do not impose E-Prime, do not
    optimise surprisal, do not gate on MECE, do not auto-restructure from RST, never let a critic
    score holistic quality. "Absence of a misfeature" is awkward to test but not subjective.
  - R-PROJ-01, R-CONV-02, R-DISC-01 and R-DISC-04 are architecture invariants — the IR is canonical,
    and specific halves of the discovery/convergence loops are deterministic while others are
    model-judged. Purity is exactly what a parser can confirm.

So these are conformance lints against the source tree, and a rule nobody can check is a rule that
does not bind. R-REJECT-05 makes the point: its directive calls itself "the primary guard", and it
was already enforced in code by `_validate_verdict` — the registry just never said so.

The registry still classifies them `human`; changing that is the maintainer's call, and this module
deliberately does not depend on it. It reports findings keyed by rule_id, so the rules are exercised
either way. `run_conformance_pass` does not go through `run_artifact_pass`, which filters to
`hard_lint`.

Each function returns [] when clean, else a list of violation strings.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRIPTS = Path(__file__).resolve().parents[1]
SKILL_ROOT = SCRIPTS.parent

# Modules the registry declares PURE. A model call, a clock or a random source in any of them breaks
# reproducibility, which is what R-CONV-02 and R-DISC-04 exist to protect.
_PURE_MODULES = {
    "R-CONV-02": SCRIPTS / "research" / "convergence.py",
    "R-DISC-04": SCRIPTS / "research" / "discovery.py",
}
_IMPURE_CALLS = {"now", "today", "utcnow", "random", "randint", "shuffle", "choice", "uuid4", "time"}
_IMPURE_IMPORTS = {"random", "secrets", "uuid"}


def deterministic_modules_stay_pure(modules: dict | None = None) -> list[str]:
    """R-CONV-02 / R-DISC-04: the metric halves are deterministic; only the judged halves may call
    a model. Eval replays campaigns, and the escalate loop's termination must be reproducible — if
    either module gained a clock, a random source or a model call, the same draft could escalate on
    one run and settle on the next."""
    problems: list[str] = []
    for rule_id, path in (modules or _PURE_MODULES).items():
        if not path.is_file():
            problems.append(f"{rule_id}: {path.name} is missing; the purity claim cannot be checked")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in _IMPURE_IMPORTS:
                        problems.append(f"{rule_id}: {path.name} imports {alias.name!r}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in _IMPURE_IMPORTS:
                    problems.append(f"{rule_id}: {path.name} imports from {node.module!r}")
                if "judge" in node.module.lower() or root == "critics":
                    problems.append(f"{rule_id}: {path.name} imports a judge ({node.module!r}); "
                                    f"the model-judged half belongs in planner.py")
            elif isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name in _IMPURE_CALLS:
                    problems.append(f"{rule_id}: {path.name} calls {name}() — non-deterministic")
    return problems


def critics_are_binary_only(prompt_dir: Path | None = None) -> list[str]:
    """R-REJECT-05: critic prompts ask binary single-criterion questions; never 'is this good?'.

    Three things have to hold together, and the rule is only as strong as the weakest: the verdict
    vocabulary is binary, a non-binary verdict RAISES rather than being coerced, and no generated
    critic prompt asks a holistic question.
    """
    problems: list[str] = []
    from critics.run_critics import _VALID_VERDICTS, _validate_verdict

    if _VALID_VERDICTS != {"pass", "fail"}:
        problems.append(f"R-REJECT-05: verdict vocabulary is {sorted(_VALID_VERDICTS)}, not binary")
    try:
        _validate_verdict("excellent")
        problems.append("R-REJECT-05: a non-binary verdict was accepted rather than raising")
    except ValueError:
        pass

    holistic = re.compile(r"\b(how good|is this good|overall quality|score .*\b(1|0)-\s*\d|"
                          r"rate .* out of|thoroughness|on a scale)\b", re.IGNORECASE)
    for prompt in sorted((prompt_dir or SKILL_ROOT / "references" / "critic-prompts").glob("*.md")):
        for n, line in enumerate(prompt.read_text(encoding="utf-8").splitlines(), start=1):
            # the prohibition itself is quoted in every prompt's discipline block; skip those
            if "never" in line.lower() or "prohibited" in line.lower() or "not " in line.lower():
                continue
            if holistic.search(line):
                problems.append(f"R-REJECT-05: {prompt.name}:{n} asks a holistic question: "
                                f"{line.strip()[:80]}")
    return problems


def swap_and_average_is_pairwise_only() -> list[str]:
    """R-REJECT-05 (second half): swap-and-average is legitimate for a PAIRWISE revision comparison
    and nowhere else. Applied pointwise it reintroduces the holistic score through the back door."""
    from critics import run_critics

    source = Path(run_critics.__file__).read_text(encoding="utf-8")
    body = source[source.index("def run_pass("):source.index("def compare_revisions(")]
    if "0.5" in body or "swap" in body.lower():
        return ["R-REJECT-05: run_pass appears to average or swap; pointwise verdicts must be binary"]
    return []


def no_rejected_techniques_are_implemented(check_dir: Path | None = None) -> list[str]:
    """R-REJECT-01..04: four techniques the design deliberately refuses.

    E-Prime as a writing constraint, surprisal smoothing as an EDITING TARGET, strict MECE as a
    quality GATE, and auto-restructuring from RST parser output. Each is checked as "no check module
    blocks on it", not "the words never appear" — the evidence map discusses all four at length, and
    a check that fired on discussion would be unfixable noise.
    """
    banned = {
        "R-REJECT-01": (re.compile(r"\be-?prime\b", re.IGNORECASE), "E-Prime writing constraint"),
        "R-REJECT-02": (re.compile(r"\bsurprisal\b", re.IGNORECASE), "surprisal as an editing target"),
        "R-REJECT-03": (re.compile(r"\bmece\b", re.IGNORECASE), "strict MECE gate"),
        "R-REJECT-04": (re.compile(r"\brst\b(?!\s*=)", re.IGNORECASE), "RST auto-restructuring"),
    }
    problems: list[str] = []
    check_dir = check_dir or SCRIPTS / "checks"
    for rule_id, (pattern, label) in banned.items():
        for path in sorted(check_dir.glob("*.py")):
            if path.name == "conformance.py":       # this module names all four to forbid them
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#") or not pattern.search(line):
                    continue
                problems.append(f"{rule_id}: {path.name}:{n} implements {label} as a check — "
                                f"the design rejects it: {stripped[:70]}")
    return problems


def ir_is_the_only_canonical_source(render_dir: Path | None = None) -> list[str]:
    """R-PROJ-01: drafting emits the IR; HTML and LLM-MD are rendered FROM it and never hand-edited.

    Checked structurally: every renderer takes the IR as its first parameter, so neither projection
    can be authored independently. A renderer that read a projection back in would make the IR one
    source among several, which is precisely what this forbids.
    """
    problems: list[str] = []
    render_dir = render_dir or SCRIPTS / "render"
    for name in ("render_html.py", "render_llm_md.py"):
        path = render_dir / name
        if not path.is_file():
            problems.append(f"R-PROJ-01: {name} is missing")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        entry = next((n for n in tree.body
                      if isinstance(n, ast.FunctionDef) and n.name == path.stem), None)
        if entry is None:
            problems.append(f"R-PROJ-01: {name} has no {path.stem}() entry point")
            continue
        first = entry.args.args[0].arg if entry.args.args else None
        if first != "ir":
            problems.append(f"R-PROJ-01: {path.stem}() takes {first!r} first, not the IR — "
                            f"a projection that is not a function of the IR is a second source")
    return problems


def leads_are_never_evidence() -> list[str]:
    """R-DISC-01: a discovery lead is a POINTER. A claim becomes provenance only when its quote is
    found verbatim in a document actually fetched.

    Behavioural, not structural — the gate is asserted by exercising it, because "the function
    exists" is exactly the kind of evidence this project has been burned by. A quote absent from the
    fetched body must be rejected, a present one kept, and the rejection must name the rule.
    """
    from research.claim_extractor import anchor_claims
    from research.retrieval_loop import Document

    doc = Document(url="https://example.org/a", text="chunking is the unit of retrieval")
    problems: list[str] = []

    kept, rejected = anchor_claims([{"text": "invented", "quote": "never on this page"}], doc)
    if kept:
        problems.append("R-DISC-01: a quote absent from the fetched body was accepted as provenance")
    if not any("R-DISC-01" in r for r in rejected):
        problems.append("R-DISC-01: the rejection does not cite the rule it enforces")

    kept, _ = anchor_claims([{"text": "t", "quote": "chunking is the unit of retrieval"}], doc)
    if len(kept) != 1:
        problems.append("R-DISC-01: a quote present verbatim in the fetched body was NOT accepted — "
                        "the firewall has become a blanket refusal, which fails open on coverage")
    return problems


CONFORMANCE_CHECKS = {
    "R-CONV-02": deterministic_modules_stay_pure,
    "R-DISC-04": deterministic_modules_stay_pure,
    "R-REJECT-05": critics_are_binary_only,
    "R-REJECT-01": no_rejected_techniques_are_implemented,
    "R-REJECT-02": no_rejected_techniques_are_implemented,
    "R-REJECT-03": no_rejected_techniques_are_implemented,
    "R-REJECT-04": no_rejected_techniques_are_implemented,
    "R-PROJ-01": ir_is_the_only_canonical_source,
    "R-DISC-01": leads_are_never_evidence,
}


def run_conformance_pass() -> dict:
    """Run every conformance check and report findings keyed by rule_id.

    Deliberately NOT routed through `run_artifact_pass`, which filters to `hard_lint` — the registry
    still files these nine under `human`, and whether to reclassify them is the maintainer's call.
    This reports on them either way, so the rules bind now rather than after that decision.
    """
    findings: list[dict] = []
    cache: dict = {}
    for rule_id, fn in sorted(CONFORMANCE_CHECKS.items()):
        if fn not in cache:
            cache[fn] = fn()
        # every violation string is prefixed with the rule it belongs to, so a check shared by
        # several rules (purity covers two, the rejected-technique sweep covers four) attributes
        # cleanly instead of failing all of them together
        mine = [p for p in cache[fn] if p.startswith(rule_id)]
        findings.append({
            "rule_id": rule_id,
            "status": "fail" if mine else "pass",
            "detail": "; ".join(mine) if mine else "conformant",
        })
    counts = {"pass": sum(1 for f in findings if f["status"] == "pass"),
              "fail": sum(1 for f in findings if f["status"] == "fail")}
    return {"findings": findings, "counts": counts, "blocking": counts["fail"] > 0}
