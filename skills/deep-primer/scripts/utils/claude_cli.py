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
    """The CLI could not be run, timed out, or returned something unusable.

    A PER-ITEM failure. Callers legitimately absorb it: an unreachable model on one brief is a
    reportable empty result, not a reason to discard the other twenty.
    """


class CliBudgetExceeded(RuntimeError):
    """The accumulated spend passed the declared cap; the run stops rather than continuing.

    Deliberately NOT a subclass of `CliUnavailable`, which it used to be. Every caller that wrote
    `except CliUnavailable` to absorb a per-item outage was silently absorbing this too — so a run
    that hit its ceiling did not stop. It kept calling, kept paying, and scored each further call as
    a failure, which is worse than stopping because the damage is rule-shaped and looks like a
    finding: an exhausted budget scores every remaining citation "not supported"
    (verify/claude_entailment.py), and terminates the convergence loop as `coherent` on a judge that
    never answered (research/claude_structure_judge.py).

    This module's docstring already promised the ceiling "aborts rather than discovering the bill
    afterwards". Not inheriting from `CliUnavailable` is what makes that true rather than merely
    stated — a sibling type cannot be caught by an `except` clause aimed at ordinary transients.
    """


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

    # Which Claude Code tools this caller may use. `()` — the default — means NONE, and that is a
    # cost decision, not a safety one.
    #
    # Every `claude -p` is a COLD session: it re-pays the whole Claude Code preamble (system prompt
    # plus every tool schema, including any MCP servers configured on the machine) before it reads a
    # word of the instruction. Measured on a 10-token question: ~37,800 preamble tokens with the
    # default tool set, ~15,900 with none — a ~58% saving on EVERY call. A critic run is 113 calls
    # asking for one binary word each, so the preamble, not the judgement, is the bill: ~4M input
    # tokens of boilerplate either way, and half of it recoverable for free.
    #
    # A caller that genuinely needs tools says so — see `research/claude_backend.py`, which needs
    # WebSearch and WebFetch to retrieve anything at all.
    allowed_tools: tuple[str, ...] = ()
    # `bypassPermissions` is required for a non-interactive run to actually USE a tool it is given;
    # without it the CLI has no one to ask. Only meaningful when `allowed_tools` is non-empty.
    permission_mode: str | None = None

    def __post_init__(self) -> None:
        self.budget = self.budget or Budget(cost_cap_usd=self.cost_cap_usd)

    def _argv(self, instruction: str) -> list[str]:
        argv = ["claude", "-p", instruction, "--model", self.model, "--output-format", "json"]
        if self.allowed_tools:
            argv += ["--allowedTools", *self.allowed_tools]
            argv += ["--permission-mode", self.permission_mode or "bypassPermissions"]
        else:
            # An explicit empty tool set. Omitting the flag does NOT mean "no tools" — it means the
            # default set, schemas and all.
            argv += ["--tools", ""]
        return argv

    @property
    def spend_usd(self) -> float:
        return self.budget.spend_usd

    @property
    def calls(self) -> int:
        return self.budget.calls

    def __call__(self, instruction: str, *, timeout_s: int | None = None) -> dict:
        """Run one call and return the parsed CLI envelope. Raises CliUnavailable on any failure.

        `timeout_s` overrides the ceiling for THIS call only. It exists for retries: a caller that
        just lost a call to the clock has evidence it is near the ceiling, and re-running it under
        the same ceiling mostly re-loses it (see `claude_curator._ask`).
        """
        ceiling = timeout_s or self.timeout_s
        try:
            # A neutral cwd: run from inside the repo and the CLI loads CLAUDE.md and project
            # context into every call — irrelevant to the judgement, and paid for each time.
            with tempfile.TemporaryDirectory() as neutral_cwd:
                proc = subprocess.run(
                    self._argv(instruction),
                    capture_output=True, text=True, timeout=ceiling, cwd=neutral_cwd,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            raise CliUnavailable(f"claude CLI exceeded {ceiling}s") from exc
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

    def result_text(self, instruction: str, *, timeout_s: int | None = None) -> str:
        """The model's answer, fence-stripped."""
        return strip_fence(str(self(instruction, timeout_s=timeout_s).get("result", "")))

    def result_json(self, instruction: str, *, timeout_s: int | None = None) -> dict:
        """The model's answer parsed as a JSON object.

        Uses `extract_json`, not a bare `json.loads`. Three separate runs in this project died on
        output-shape assumptions — a ```json fence, a pass-level wrapper, an empty result — and each
        time a correct answer was discarded over packaging. Parse leniently, validate strictly:
        the CONTENT still has to satisfy the caller's contract.
        """
        return extract_json(self.result_text(instruction, timeout_s=timeout_s))
