"""One scoped `claude -p` call, with cost accounting. Shared by the model-backed seams.

Classification: tool-loop (model call — NOT hermetic)

Both places the skill needs a model are the same shape: send one self-contained instruction, get one
small structured answer back, pay for it. `critics/claude_judge.py` (binary rule verdicts) and
`verify/claude_entailment.py` (binary supports/not-supports) both sit on this rather than keeping
two copies of subprocess handling, JSON-envelope parsing, and spend tracking that can drift apart.

The cost cap is not decoration. A citation run is one call per (citation, claim) pair and a critic
run is one per (rule, block); either can quietly become hundreds of calls on a larger artifact, so
the ceiling is explicit and aborts rather than discovering the bill afterwards.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


class CliUnavailable(RuntimeError):
    """The CLI could not be run, timed out, or returned something unusable."""


class CliBudgetExceeded(CliUnavailable):
    """The accumulated spend passed the declared cap; the run stops rather than continuing."""


def strip_fence(text: str) -> str:
    """Drop a ```json fence. The CLI adds one often enough that not stripping it would turn every
    well-formed answer into a parse error."""
    out = text.strip()
    if out.startswith("```"):
        out = _FENCE_RE.sub("", out)
    return out.strip()


def extract_json(text: str) -> dict:
    """Parse the first complete JSON object in `text`, tolerating packaging around it.

    Models wrap JSON in fences, precede it with "Here is the result:", and occasionally append a
    closing remark. None of that changes the answer, so none of it should discard the answer — but
    a bare `json.loads` treats all three as fatal. Scans for the first balanced `{...}`, respecting
    string literals and escapes so a brace inside a value does not end the scan early.
    """
    stripped = strip_fence(text)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    start = stripped.find("{")
    if start == -1:
        raise CliUnavailable(f"no JSON object in response: {stripped[:200]!r}")
    depth, in_string, escaped = 0, False, False
    for i, ch in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(stripped[start:i + 1])
                except json.JSONDecodeError as exc:
                    raise CliUnavailable(f"malformed JSON object: {exc}") from exc
    raise CliUnavailable(f"unterminated JSON object in response: {stripped[:200]!r}")


@dataclass
class Budget:
    """A spend ceiling shared by several callers.

    Needed because `--gating-model` builds TWO CLI callers (one per model) and giving each the full
    `--cost-cap` meant a declared $9 ceiling could spend $18. A cap the user sets once is a cap on
    the RUN, not on each participant that happens to exist inside it.
    """

    cost_cap_usd: float = 5.0
    spend_usd: float = 0.0
    calls: int = 0

    def charge(self, usd: float) -> None:
        self.spend_usd += usd
        self.calls += 1
        if self.spend_usd > self.cost_cap_usd:
            raise CliBudgetExceeded(
                f"cost cap hit: ${self.spend_usd:.2f} > ${self.cost_cap_usd:.2f} after "
                f"{self.calls} calls — raise the cap to continue")


@dataclass
class ClaudeCli:
    """A cost-capped `claude -p` caller.

    `model` defaults to haiku: every current caller wants a BINARY answer, which does not need a
    frontier model, and the difference is roughly an order of magnitude per call.
    """

    model: str = "haiku"
    # 180s was not enough in practice — instructions that embed a whole rendered document are slow,
    # and one call exceeding the ceiling used to abort an otherwise-complete 45-minute run.
    timeout_s: int = 420
    cost_cap_usd: float = 5.0
    # Pass a shared Budget when several callers must respect ONE ceiling (see --gating-model).
    budget: Budget | None = None

    def __post_init__(self) -> None:
        self.budget = self.budget or Budget(cost_cap_usd=self.cost_cap_usd)

    @property
    def spend_usd(self) -> float:
        return self.budget.spend_usd

    @property
    def calls(self) -> int:
        return self.budget.calls

    def __call__(self, instruction: str) -> dict:
        """Run one call and return the parsed CLI envelope. Raises CliUnavailable on any failure."""
        try:
            # A neutral cwd: run from inside the repo and the CLI loads CLAUDE.md and project
            # context into every call — irrelevant to the judgement, and paid for each time.
            with tempfile.TemporaryDirectory() as neutral_cwd:
                proc = subprocess.run(
                    ["claude", "-p", instruction, "--model", self.model,
                     "--output-format", "json"],
                    capture_output=True, text=True, timeout=self.timeout_s, cwd=neutral_cwd,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            raise CliUnavailable(f"claude CLI exceeded {self.timeout_s}s") from exc
        except OSError as exc:
            raise CliUnavailable(f"claude CLI could not be started: {exc}") from exc

        if proc.returncode != 0:
            raise CliUnavailable(f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[:300]}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise CliUnavailable(f"CLI envelope was not JSON: {proc.stdout[:200]}") from exc

        self.budget.charge(float(envelope.get("total_cost_usd") or 0.0))
        if envelope.get("is_error"):
            raise CliUnavailable(f"CLI reported an error: {str(envelope.get('result'))[:200]}")
        return envelope

    def result_text(self, instruction: str) -> str:
        """The model's answer, fence-stripped."""
        return strip_fence(str(self(instruction).get("result", "")))

    def result_json(self, instruction: str) -> dict:
        """The model's answer parsed as a JSON object.

        Uses `extract_json`, not a bare `json.loads`. Three separate runs in this project died on
        output-shape assumptions — a ```json fence, a pass-level wrapper, an empty result — and each
        time a correct answer was discarded over packaging. Parse leniently, validate strictly:
        the CONTENT still has to satisfy the caller's contract.
        """
        return extract_json(self.result_text(instruction))
