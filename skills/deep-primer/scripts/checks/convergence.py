"""Validate a convergence-log against R-CONV-01 (deterministic lint).

Classification: local-deterministic
Implements: R-CONV-01
Checks: <= K_MAX cycles; exactly one valid terminal_regime in
{converged, contested, chaotic, coherent}; no escalate decision after K_MAX;
if terminal_regime == contested, a contested-structure block (role: contested) exists.
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6b).
"""
from __future__ import annotations


def terminal_state(convergence_log: dict, ir=None) -> list[str]:
    """Return [] if the run satisfies R-CONV-01, else a list of violation strings."""
    raise NotImplementedError("deep-primer Stage 6 stub: checks/convergence.py::terminal_state (Prompt 6b)")
