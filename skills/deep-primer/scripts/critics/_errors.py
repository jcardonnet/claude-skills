"""Judge failure types, in their own module for a load-bearing reason.

`run_critics.py` is executed as a script, so it is imported twice under two names: as `__main__`
and as `critics.run_critics`. An exception class defined there is therefore TWO distinct classes,
and `except JudgeUnavailable` in `__main__` does not catch the `critics.run_critics` one that
`claude_judge` raised. That is not hypothetical — it killed a completed 45-minute run whose
containment logic was otherwise correct. Defining these here gives both importers the same object.
"""
from __future__ import annotations


class JudgeUnavailable(RuntimeError):
    """The judge could not be reached, timed out, or emitted unusable output.

    OPERATIONAL, and contained per-item so one bad call cannot discard a whole run. A non-binary
    *verdict* is emphatically NOT this: that is a breach of R-REJECT-05 and must still raise and
    stop the run, or "holistic scoring is impossible by construction" stops being true.
    """
