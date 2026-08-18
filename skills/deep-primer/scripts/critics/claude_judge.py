"""Judge backend: the local `claude` CLI as the scoped binary judge for the critic passes.

Classification: agent-orchestrated (calls a model — NOT hermetic, never unit-tested live)
Implements: the judge seam `run_critics.Judge` declares but never had a production implementation

Why this exists
---------------
All 35 soft_critic rules were dispatched by the six generated critic prompts, so the tier was fully
wired — and 33 of them had still never executed once, because the only judge in the tree was
`StubJudge` and `run_critics.main` hardcoded it. The tier that carries the primer's actual quality
thesis (depth, prose, evidence, figures, expertise) was structurally complete and empirically dark.

Discipline preserved from run_critics (R-REJECT-05)
--------------------------------------------------
  - ONE call per (rule, block). Never batched, never holistic — batching rules into a single call is
    exactly the "score this document out of 10" failure the binary contract exists to forbid.
  - The model returns only {pass, fail}. Anything else raises rather than being coerced: a judge
    that silently degrades to "probably fine" is the soft version of a skipped check.
  - Test-retest for gating rules is driven by run_critics, not here. The two calls deliberately send
    an IDENTICAL instruction — varying it would test two different things instead of measuring the
    judge's own stability. Independence comes from sampling: prompt caching reuses prefix
    computation, it does not pin the output, so a genuinely borderline call can still flip.

Cost
----
A binary verdict does not need a frontier model, and the default is `haiku` for that reason. Runs
carry a hard USD cap and abort rather than silently overspending — `--cost-cap`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from critics._errors import JudgeUnavailable
from critics.run_critics import DOCUMENT, BlockView, JudgeResult, _validate_verdict, _view
from ir.schema import DocumentIR
from utils.claude_cli import ClaudeCli, CliUnavailable, strip_fence

_INSTRUCTION = """\
You are a scoped binary critic. Judge ONE rule against ONE unit of text. Nothing else.

{prompt}

--- THE ONLY RULE YOU ARE JUDGING NOW ---
{rule_id}

--- THE UNIT UNDER JUDGEMENT ---
block_id: {block_id}
role: {role}
concept: {concept}
mode: {mode}

{text}

--- OUTPUT CONTRACT ---
Return RAW JSON and nothing else. No prose, no markdown fence:
{{"verdict": "pass" | "fail", "evidence": "<= 25 words quoting or citing what decided it", "span": "<the exact substring that decided it, or null>"}}

"verdict" MUST be exactly "pass" or "fail". Do not hedge, do not score, do not return any other
value. If the rule does not apply to this unit, that is a "pass".
"""


def _unwrap(payload: dict, rule_id: str, block_id: str) -> dict:
    """Accept either output shape the judge can plausibly produce.

    The instruction embeds the whole generated pass prompt, which ends with its own `## Output`
    section specifying `{"pass": ..., "verdicts": [...]}` for the entire pass. Appending a
    single-verdict contract after it leaves two conflicting instructions in one message, and the
    model sometimes follows the first. Rejecting that as malformed threw away a correct judgement
    over formatting — so take the matching entry when the pass-level shape comes back.
    """
    verdicts = payload.get("verdicts")
    if not isinstance(verdicts, list):
        return payload
    for entry in verdicts:
        if isinstance(entry, dict) and entry.get("rule_id") == rule_id \
                and entry.get("block_id") == block_id:
            return entry
    return verdicts[0] if verdicts and isinstance(verdicts[0], dict) else payload


def _judge_document_view(ir: DocumentIR) -> str:
    """The document as a document-level critic must see it — section titles included.

    NOT the raw LLM-MD projection. That projection is deliberately a flat, block-addressable
    retrieval surface: its own docstring says it emits one `## [block: <id>]` heading per kept block
    and no section titles at all. Handing it to a critic made `R-SCENT-01` — "headings are
    predictive claims, not topic labels" — fail against a primer whose section titles are exactly
    that ("Chunking caps recall before the embedder ever runs"). The rule was being judged on a
    surface engineered to omit the thing it checks, which is a guaranteed false FAIL and would have
    been read as a defect in the primer.

    Structure rules also need the shape: R-ARCH-*, R-XREF-03 and R-SCENT-01 are all about how
    sections relate, which a flat block list cannot show.
    """
    from render.render_llm_md import kept_blocks, render_llm_md

    seen: list[str] = []
    outline: list[str] = []
    for sec, _block in kept_blocks(ir):
        if sec.title not in seen:
            seen.append(sec.title)
            outline.append(f"{len(seen)}. {sec.title}")
    return ("SECTION HEADINGS, in document order:\n" + "\n".join(outline)
            + "\n\nBLOCKS (the distilled projection):\n" + render_llm_md(ir))


_NO_TEXT = "(this block carries no text)"


def unit_text(block: BlockView, document_text: str) -> str:
    """The text a critic is shown for one unit."""
    return document_text if block.block_id == DOCUMENT else (block.text or _NO_TEXT)


def judged_surface(ir: DocumentIR) -> list[list[str]]:
    """Everything a critic can be shown for this IR — identity fields and text, per unit.

    `run_critics._ir_digest` hashes THIS rather than reconstructing an approximation of it, which is
    what it used to do. The reconstruction and the real surface had already drifted: it recorded
    `[block_id, role, concept, mode, readable_text]` plus section titles and its docstring asserted
    the judge sees no provenance or source_ids — but the document view is built from
    `render_llm_md`, which prints `provenance:` into every block heading and a `Sources: [...]` line
    under it. Relabelling a block verified -> inferred therefore changed what every document-level
    critic read and left the digest unmoved, so a frozen report stayed "fresh" for a document it no
    longer described. Deriving the digest from the surface makes that impossible rather than
    documented.
    """
    doc = _judge_document_view(ir)
    units = [[DOCUMENT, DOCUMENT, "-", "-", doc]]
    for b in ir.flatten_blocks():
        bv = _view(b)
        units.append([bv.block_id, bv.role, bv.concept or "-", bv.mode or "-",
                      unit_text(bv, doc)])
    return units


class JudgeError(JudgeUnavailable):
    """The CLI failed or could not be parsed, and retrying will not help.

    Subclasses `run_critics.JudgeUnavailable` so `run_pass` contains it per-item. A NON-BINARY
    verdict deliberately does not come through here — `_validate_verdict` raises ValueError, which
    propagates and stops the run, because R-REJECT-05 is a contract, not a transport hiccup.
    """


class JudgeTransient(JudgeError):
    """A timeout or transport hiccup — worth one more attempt.

    Kept distinct because the first full run died here: a single call exceeding the timeout raised
    `subprocess.TimeoutExpired`, which nothing caught, and ~100 completed judgements went with it.
    A 45-minute tool-loop must not be one slow response away from losing everything.
    """


_strip_fence = strip_fence  # kept as a local name: the fence-stripping tests import it from here


@dataclass
class ClaudeCliJudge:
    """One scoped `claude -p` call per (rule, block), behind run_critics' Judge protocol.

    `ir` is required because `applicable_blocks` hands document-level rules a placeholder BlockView
    carrying no text at all (`_DOC_VIEW`). Judging "does this document have a coherent architecture"
    against an empty string would produce a confident, meaningless verdict — the exact failure this
    whole tier is meant to catch — so the document's rendered projection is substituted instead.
    """

    ir: DocumentIR
    model: str = "haiku"
    # 180s was not enough: the document-level rules ship the whole rendered projection, and one call
    # in the first full run exceeded it. Timeouts are retried now, but the ceiling was simply low.
    timeout_s: int = 420
    cost_cap_usd: float = 5.0
    max_attempts: int = 2
    budget: object | None = None

    _cli: ClaudeCli = field(init=False)
    _document_text: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self._cli = ClaudeCli(model=self.model, timeout_s=self.timeout_s,
                              cost_cap_usd=self.cost_cap_usd, budget=self.budget)
        self._document_text = _judge_document_view(self.ir)

    @property
    def calls(self) -> int:
        return self._cli.calls

    @property
    def spend_usd(self) -> float:
        return self._cli.spend_usd

    def _unit_text(self, block: BlockView) -> str:
        return unit_text(block, self._document_text)

    def _invoke(self, instruction: str) -> dict:
        """Delegate to the shared CLI caller, re-raising in this module's taxonomy.

        The split matters: a blown budget must NOT be retried (retrying is what blows it further),
        while a timeout or transport hiccup should be.

        `CliBudgetExceeded` is deliberately NOT translated. It used to become a `JudgeError`, which
        subclasses `JudgeUnavailable`, which `run_pass` catches per item and records as verdict
        "error" before moving to the next (rule, block) — so the run carried on calling and paying,
        and every remaining item was stamped as a judge failure. Making `CliBudgetExceeded` a
        sibling of `CliUnavailable` fixed the research, entailment and structure-judge seams; this
        one re-created the swallow by hand one layer up.

        A blown ceiling is a RUN-level abort. Only per-item failures belong in this taxonomy.
        """
        try:
            return self._cli(instruction)
        except CliUnavailable as exc:
            raise JudgeTransient(str(exc)) from exc

    def __call__(self, pass_name: str, prompt: str, rule_id: str,
                 block: BlockView, attempt: int) -> JudgeResult:
        instruction = _INSTRUCTION.format(
            prompt=prompt, rule_id=rule_id, block_id=block.block_id, role=block.role,
            concept=block.concept or "-", mode=block.mode or "-", text=self._unit_text(block),
        )
        last: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                envelope = self._invoke(instruction)
                payload = _unwrap(json.loads(_strip_fence(str(envelope.get("result", "")))),
                                  rule_id, block.block_id)
                raw_verdict = str(payload.get("verdict") or "").strip().lower()
                if not raw_verdict:
                    # MISSING is not the same as NON-BINARY. A response with no `verdict` key simply
                    # did not follow the output contract — malformed, retryable, and containable.
                    # Only a verdict the model actually asserted ("excellent", "7/10") is the
                    # R-REJECT-05 breach that must stop the run. Defaulting the absent key to "" and
                    # handing it to _validate_verdict conflated the two, and killed a 45-minute run
                    # by reporting a formatting slip as a holistic-scoring violation.
                    raise JudgeTransient(  # noqa: TRY301 — the raise IS the branch; hiding it in a
                        # helper would separate this distinction from the comment explaining it
                        f"response carried no verdict field: {str(payload)[:120]}")
                return JudgeResult(
                    _validate_verdict(raw_verdict),
                    str(payload.get("evidence", ""))[:300],
                    payload.get("span"),
                )
            except JudgeTransient as exc:
                last = exc                      # a timeout is worth one more try
            except JudgeError:
                raise                           # cost cap / hard CLI failure: retrying won't help
            except json.JSONDecodeError as exc:
                last = exc                      # unparseable output: one more attempt
        raise JudgeError(f"{rule_id}/{block.block_id}: no usable response after "
                         f"{self.max_attempts} attempts ({last})")
