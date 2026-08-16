"""A scoped Claude entailment judge — the production `judge_fn` for `CallableEntailment`.

Classification: model_verified (substrate, model-backed — NOT hermetic)
Implements: the missing half of `_entailment.resolve_backend("claude", judge_fn=...)`

Why this closes a real gap
--------------------------
`resolve_backend("claude")` has always raised without a `judge_fn`, and nothing in the tree ever
supplied one — so every citation score the harness has ever produced came from `LexicalEntailment`,
a word-overlap proxy. That proxy is why `propose_thresholds()` REFUSES: it measures token overlap
between a <=15-word quote and a block `R-GROUND-01` requires to be a PARAPHRASE, so a compliant
primer scores near zero. `citation_recall: 0.75` / `citation_precision: 0.90` in eval-rubric.yaml
have therefore never been measurements — they are placeholders that nothing could validate.

Entailment is exactly the question the proxy cannot answer: does this quote SUPPORT this statement,
even when they share almost no words? That is a judgement, not a string comparison.

Discipline
----------
  - One premise/hypothesis pair per call. Never batched — a batched call invites the model to score
    the set holistically, which is the failure `R-REJECT-05` forbids for critics and which would be
    just as wrong here.
  - Binary only. A hedged answer is treated as NOT supported: an entailment verifier that resolves
    ambiguity in the primer's favour would inflate exactly the number it exists to police.
"""
from __future__ import annotations

import json

from utils.claude_cli import ClaudeCli, CliUnavailable

_PROMPT = """\
Does the EVIDENCE support the STATEMENT?

Answer only about support, not about whether the statement is true in general, and not about style.
The statement is expected to PARAPHRASE rather than quote the evidence, so wording will differ —
judge meaning, not overlap. Support means: an attentive reader of the evidence alone would accept
the statement as backed by it.

--- EVIDENCE ---
{premise}

--- STATEMENT ---
{hypothesis}

--- OUTPUT CONTRACT ---
Return RAW JSON and nothing else, no markdown fence:
{{"supports": true | false, "why": "<= 20 words"}}
"""


class ClaudeEntailmentJudge:
    """Callable of the shape `CallableEntailment` wants: `(premise, hypothesis) -> bool`.

    Failures resolve to False rather than raising. A citation the verifier could not check has not
    been shown to be supported, and counting it as supported would let an outage quietly raise the
    score — the same silent-pass failure the registry is built around.
    """

    def __init__(self, cli: ClaudeCli | None = None, *, model: str = "haiku",
                 cost_cap_usd: float = 5.0) -> None:
        self.cli = cli or ClaudeCli(model=model, cost_cap_usd=cost_cap_usd)
        self.unresolved: list[str] = []

    @property
    def calls(self) -> int:
        return self.cli.calls

    @property
    def spend_usd(self) -> float:
        return self.cli.spend_usd

    def __call__(self, premise: str, hypothesis: str) -> bool:
        if not (premise or "").strip() or not (hypothesis or "").strip():
            return False
        try:
            payload = self.cli.result_json(_PROMPT.format(premise=premise, hypothesis=hypothesis))
        except (CliUnavailable, json.JSONDecodeError) as exc:
            self.unresolved.append(f"{type(exc).__name__}: {exc}"[:200])
            return False
        value = payload.get("supports")
        if isinstance(value, bool):
            return value
        # a hedged or missing answer is not support
        self.unresolved.append(f"non-boolean supports={value!r}")
        return False
