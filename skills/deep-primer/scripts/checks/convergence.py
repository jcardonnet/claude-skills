"""Validate a convergence-log against R-CONV-01 (deterministic lint).

Classification: local-deterministic
Implements: R-CONV-01
Checks: <= K_MAX cycles; exactly one valid terminal_regime in
{converged, contested, chaotic, coherent}; no escalate decision after K_MAX;
if terminal_regime == contested, a contested-structure block (role: contested) exists.

The failure this guards is a loose escalate threshold that oscillates: each redraft surfaces a new
structural wrinkle, the loop never terminates, and the run burns its budget without converging.
The log is the evidence that it did terminate, and in a state the renderer knows how to express.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import ConvergenceLog, DocumentIR  # noqa: E402
from research.convergence import K_MAX  # noqa: E402

_VALID_REGIMES = {"converged", "contested", "chaotic", "coherent"}
_REGIME_DECISION = {
    "converged": "footnote-residual",
    "contested": "render-contested",
    "chaotic": "flag-scope",
    "coherent": "draft",
}


def terminal_state(convergence_log: ConvergenceLog | dict, ir: DocumentIR | None = None) -> list[str]:
    """Return [] if the run satisfies R-CONV-01, else a list of violation strings."""
    log = ConvergenceLog(**convergence_log) if isinstance(convergence_log, dict) else convergence_log
    problems: list[str] = []
    cap = log.k_max or K_MAX

    cycles = [c.cycle for c in log.cycles]
    if cycles and max(cycles) > cap:
        problems.append(f"reached cycle {max(cycles)}, cap is {cap}")

    escalations = [c for c in log.cycles if c.decision == "escalate"]
    if len(escalations) > cap:
        problems.append(f"{len(escalations)} escalations, cap is {cap}")
    for c in escalations:
        if c.cycle > cap:
            problems.append(f"escalate decision recorded at cycle {c.cycle} (> K_MAX {cap})")

    if log.terminal_regime not in _VALID_REGIMES:
        problems.append(f"terminal_regime {log.terminal_regime!r} is not one of {sorted(_VALID_REGIMES)}")
    else:
        expected = _REGIME_DECISION[log.terminal_regime]
        if log.terminal_decision != expected:
            problems.append(
                f"terminal_regime {log.terminal_regime!r} implies decision {expected!r}, "
                f"got {log.terminal_decision!r}")

    if not log.cycles:
        problems.append("convergence-log records no cycles")
    elif log.cycles[-1].decision != "stop":
        problems.append(f"final cycle decision is {log.cycles[-1].decision!r}, expected 'stop'")

    # A `coherent` terminal means the judge looked and found nothing. It is ALSO what the loop
    # records when the judge could not answer at all: `scan_for_structural` returns None on an
    # outage, deliberately, because inventing a finding would trigger a re-grounding cycle on the
    # strength of a timeout. Two opposite facts producing one log entry — so the log now carries the
    # errors, and the rule refuses to credit a termination resting on them.
    if log.terminal_regime == "coherent" and getattr(log, "judge_errors", None):
        problems.append(
            f"terminal_regime 'coherent' but the structure judge failed {len(log.judge_errors)} "
            f"scan(s): {log.judge_errors[0][:120]} — a judge that did not answer has not found "
            f"the map coherent")

    # a contested trajectory must actually be RENDERED, not just recorded
    if log.terminal_regime == "contested" and ir is not None:
        has_block = any(b.role.value == "contested" for b in ir.flatten_blocks())
        if not has_block:
            problems.append(
                "terminal_regime is 'contested' but the IR carries no role=contested block; "
                "the competing framings would be silently dropped")
    return problems
