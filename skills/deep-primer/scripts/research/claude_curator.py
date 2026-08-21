"""Real `ClaimGrouper`s — the model half of curation and of R-GROUND-05 corroboration.

Classification: agent-orchestrated (model call — NOT hermetic)
Implements: the proposing half of concept grouping and corroboration; the deciding half stays in
            `grouping.resolve_groups`

Why this exists
---------------
`curate` and `corroborate` both asked "which of these claims say the same thing?" and both answered
it with Jaccard overlap on bag-of-words. Spec-03's first real campaign is the measurement: 271
grounded claims became 249 single-claim concepts, and 0 claims were corroborated. Neither number is
a tuning problem. Independent sources describing one idea reuse each other's vocabulary rarely
enough that a lexical threshold high enough to be precise is too high to find anything, and one low
enough to find things merges unrelated claims that share three common words.

Same division of labour as `claude_claim_extractor.py`
-----------------------------------------------------
The model PROPOSES groups; `resolve_groups` DECIDES. Nothing here is trusted: a claim_id that is not
in the ledger, a claim placed in two groups, a `home_anchor` that restates its own concept — each is
rejected there, not here. So the worst a confabulating model can do is waste a call.

Two strictnesses, one shape
---------------------------
`ClaudeConceptGrouper` groups by TOPIC (one mechanism, however worded) and names what it groups.
`ClaudeCorroborationGrouper` groups by ASSERTION (confirming one would confirm the other) and names
nothing. The second is deliberately much stricter: corroboration that merely means "both mention
reranking" would inflate the evidence base rather than measure it.

Scale
-----
Grouping needs every claim in front of the model at once, which does not survive a large ledger. The
concept grouper batches and then runs ONE merge pass over the resulting labels, because two batches
of the same evidence reliably name the same concept twice. The corroboration grouper blocks first —
lexical overlap at a deliberately permissive threshold narrows which pairs are worth reading — and
then only asks about blocks that actually span two or more sources, since a block from one source
cannot corroborate anything no matter what the model thinks of it.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.discovery import LexicalSimilarity, Similarity  # noqa: E402
from research.grouping import LEXICAL_BLOCK_THRESHOLD, lexical_groups  # noqa: E402
from utils.claude_cli import ClaudeCli, CliUnavailable  # noqa: E402

#: Claims per call. A claim renders to roughly 30 tokens, so this is ~5k tokens of evidence in an
#: instruction — well inside a window, and small enough that the model still attends to the tail.
MAX_CLAIMS_PER_CALL = 150

#: How much longer a retried call may take than the first attempt. A retry is only ever reached
#: after a failure, and the failure this exists for is the clock, so re-running under the ceiling
#: that just expired would mostly re-expire.
RETRY_TIMEOUT_FACTOR = 2

#: Characters of a claim shown to the model. Claims are one sentence by construction (R-GROUND-01);
#: anything past this is a run-on that grouping does not need in full.
CLAIM_CHARS = 240

#: Roughly how many claims should share a concept. Only a hint in the prompt — the gate does not
#: enforce it — but without one the model returns either 3 mega-concepts or one group per claim.
CLAIMS_PER_CONCEPT = 12
MIN_CONCEPTS, MAX_CONCEPTS = 4, 18

_CONCEPT_INSTRUCTION = """\
You are curating the concept map for a technical primer on {target}.
The reader already works in: {home}.

Below are atomic claims extracted from real sources, each with an id. Group the claims that belong
to the SAME CORE CONCEPT — one mechanism, technique, structure, or design constraint — however
differently they are worded. Two claims about different aspects of one technique belong together.
Two claims about different techniques do not, even when they share vocabulary.

CLAIMS:
{claims}

Aim for about {target_groups} groups. A group of one claim is fine only when nothing else in the
list relates to it.

For each group return:
  "claim_ids": the ids in that group. Every id above must appear in EXACTLY ONE group.
  "canonical_term": the one name this primer will use for the concept — 2-4 words, the field's own
      vocabulary, a noun phrase and not a description.
  "aliases": other names the sources use for the same thing. [] if there are none.
  "home_anchor": the nearest ADJACENT technique from the reader's home domain ({home}) that this
      concept can be explained against. NAME THE HOME TECHNIQUE AND NOTHING ELSE — 2 to 6 words, a
      noun phrase, no verb, no "like ...", no comparison. It is the far end of the bridge, not the
      bridge: the primer writes the comparison later, from this plus fidelity_boundary.
      GOOD: "index cardinality on composite keys".  BAD: "Like relational databases managing key
      combinations as index entries, Prometheus stores each metric-label pair as a time series".
      It must contain NO word from {target} and no product or tool name from it — an anchor that
      mentions the concept, its aliases, or any target-domain product is describing the target
      instead of anchoring it, and will be rejected.
      It must not restate the concept: "reranking" is not an anchor for "cross-encoder reranking".
      Use "" when no honest adjacent anchor exists — an empty anchor is better than a circular one.
  "fidelity_boundary": one clause naming where that analogy stops being true. "" if home_anchor is "".

Return RAW JSON and nothing else, no markdown fence:
{{"groups": [{{"claim_ids": ["..."], "canonical_term": "...", "aliases": [],
              "home_anchor": "...", "fidelity_boundary": "..."}}]}}
"""

_MERGE_INSTRUCTION = """\
These concept labels were produced independently from different batches of the SAME evidence about
{target}, so some of them name the same concept twice under different words.

LABELS:
{labels}

Return the sets of numbers that name ONE concept and should be merged. Merge only genuine
duplicates — two labels for different aspects of a shared topic are two concepts, not one.

Return RAW JSON and nothing else, no markdown fence:
{{"merge": [[1, 4], [2, 7]]}}
Return {{"merge": []}} if every label is distinct.
"""

_CORROBORATION_INSTRUCTION = """\
Below are claims extracted from DIFFERENT sources about {target}. Find the sets that assert THE SAME
FACT — the same measurement, mechanism, threshold, or constraint — such that confirming one would
confirm the others. This is how independent corroboration gets counted, so precision matters more
than coverage.

Be strict. Two claims on one topic are NOT the same fact: "reranking improves precision" and
"reranking adds latency" describe one technique and assert different things. Different numbers for
the same quantity are not the same fact either — they are a disagreement.

CLAIMS:
{claims}

Leave out any claim that asserts something no other claim in the list asserts. Most claims will be
left out; that is the expected result, not a failure.

Return RAW JSON and nothing else, no markdown fence:
{{"groups": [{{"claim_ids": ["...", "..."]}}]}}
"""


def _render(claims: list[tuple[str, str]]) -> str:
    return "\n".join(f"{cid}: {text.strip()[:CLAIM_CHARS]}" for cid, text in claims)


def _batches(claims: list[tuple[str, str]], size: int) -> list[list[tuple[str, str]]]:
    return [claims[i:i + size] for i in range(0, len(claims), size)] or []


def _union_find(pairs, n: int) -> list[int]:
    """Resolve model-proposed merge sets into one representative index per group.

    Out-of-range and non-numeric entries are ignored rather than rejected loudly: a merge pass is an
    optimisation over naming, so a malformed suggestion should cost a missed merge, not a run.
    """
    parent = list(range(n))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for pair in pairs or []:
        if not isinstance(pair, (list, tuple)):
            continue
        idx = sorted({int(x) - 1 for x in pair
                      if isinstance(x, (int, float)) and 1 <= int(x) <= n})
        for other in idx[1:]:
            parent[root(other)] = root(idx[0])
    return [root(i) for i in range(n)]


@dataclass
class _ClaudeGrouper:
    """Shared plumbing: a cost-capped CLI, an error log, and a structural-decision log.

    Runs with NO tools — every claim it judges is handed over inline, and a fetch tool here would
    only invite the model to group against something other than the ledger.
    """

    cli: ClaudeCli | None = None
    model: str = "haiku"
    cost_cap_usd: float = 5.0

    errors: list[str] = field(default_factory=list, init=False)
    notes: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.cli = self.cli or ClaudeCli(model=self.model, cost_cap_usd=self.cost_cap_usd)

    def _ask(self, instruction: str, what: str) -> dict:
        """One call, retried once. A failure that survives the retry is an empty answer for THIS
        step, recorded, not a dead run.

        The retry is there because of one measured failure. Spec-04's 2026-08-21 campaign lost
        concept batch 2 of 3 to `claude CLI exceeded 420s` — and batch 1, the same 150 claims'
        worth of instruction, had just succeeded under the same ceiling. That is latency variance,
        not a question the model could not answer, and treating it as final cost 196 claims their
        grouping. The second attempt gets a longer ceiling: the evidence that we are near one is
        that we just hit it.

        `CliBudgetExceeded` is deliberately not caught: it is not a subclass of `CliUnavailable`,
        and a run that has hit its ceiling must stop rather than quietly group nothing. That also
        bounds the retry — it cannot spend a run past its cap.
        """
        try:
            return self.cli.result_json(instruction)
        except (CliUnavailable, json.JSONDecodeError) as first:
            self.notes.append(f"{what}: retrying once after {type(first).__name__}: {first}")
        try:
            return self.cli.result_json(
                instruction, timeout_s=self.cli.timeout_s * RETRY_TIMEOUT_FACTOR)
        except (CliUnavailable, json.JSONDecodeError) as exc:
            self.errors.append(f"{what}: {type(exc).__name__}: {exc} (after one retry)")
            return {}


@dataclass
class ClaudeConceptGrouper(_ClaudeGrouper):
    """Groups claims into concepts AND names them, in one call per batch plus a merge pass."""

    max_claims_per_call: int = MAX_CLAIMS_PER_CALL

    #: Claims whose batch came back with no groups at all. A batch that answers nothing is not a
    #: grouping this run can stand behind: every one of its claims falls through to a singleton
    #: concept, which is indistinguishable in the artifact from a claim the model genuinely found
    #: unique. Counted rather than raised here because degrading gracefully is still the right
    #: behaviour for a GROUPER — it is the driver that has to refuse to call the result a campaign
    #: (see `run_campaign.run`). Covers both halves of the failure: a call that died, and a call
    #: that returned `{"groups": []}` for 150 claims.
    lost_claims: int = field(default=0, init=False)

    def __call__(self, claims: list[tuple[str, str]], params: dict) -> list[dict]:
        if not claims:
            return []
        target = params.get("target_domain") or "the target domain"
        home = params.get("home_domain") or []
        home = ", ".join(home) if isinstance(home, list) else str(home)

        batches = _batches(claims, self.max_claims_per_call)
        if len(batches) > 1:
            self.notes.append(
                f"{len(claims)} claims exceeded {self.max_claims_per_call} per call; grouped in "
                f"{len(batches)} batches and reconciled by one merge pass")

        groups: list[dict] = []
        for i, batch in enumerate(batches, start=1):
            n = max(MIN_CONCEPTS, min(MAX_CONCEPTS, round(len(batch) / CLAIMS_PER_CONCEPT)))
            payload = self._ask(_CONCEPT_INSTRUCTION.format(
                target=target, home=home or "(not stated)", claims=_render(batch),
                target_groups=n), f"concept batch {i}/{len(batches)}")
            proposed = [g for g in (payload.get("groups") or []) if isinstance(g, dict)]
            if not proposed:
                self.lost_claims += len(batch)
                self.errors.append(
                    f"concept batch {i}/{len(batches)}: no groups proposed for {len(batch)} "
                    f"claim(s); every one of them would become a singleton")
            groups.extend(proposed)

        return self._merge(groups, claims, target) if len(batches) > 1 else groups

    def _merge(self, groups: list[dict], claims: list[tuple[str, str]], target: str) -> list[dict]:
        """One reconciliation call over the LABELS, not the claims — cheap, and the only cross-batch
        view there is. Identical names are already merged downstream by `resolve_groups`; this is
        for the near-misses ("chunk sizing" / "chunk granularity") it cannot see."""
        if len(groups) < 2:
            return groups
        text_of = dict(claims)
        lines = []
        for i, g in enumerate(groups, start=1):
            first = next((text_of[str(c)] for c in (g.get("claim_ids") or [])
                          if str(c) in text_of), "")
            lines.append(f"{i}. {g.get('canonical_term') or '(unnamed)'} — e.g. {first[:140]}")
        payload = self._ask(_MERGE_INSTRUCTION.format(target=target, labels="\n".join(lines)),
                            "concept merge pass")

        head_of = _union_find(payload.get("merge"), len(groups))

        merged: dict[int, dict] = {}
        for i, g in enumerate(groups):
            head = head_of[i]
            if head == i:
                merged[i] = {**g, "claim_ids": list(g.get("claim_ids") or []),
                             "aliases": list(g.get("aliases") or [])}
                continue
            into = merged[head]
            into["claim_ids"].extend(g.get("claim_ids") or [])
            # The absorbed label is an alias for the surviving one — that is what "same concept,
            # different words" means, and R-VOCAB-01 (B) is about exactly those surface forms.
            for alias in [g.get("canonical_term"), *(g.get("aliases") or [])]:
                if alias and alias not in into["aliases"] and alias != into.get("canonical_term"):
                    into["aliases"].append(alias)
        if len(merged) < len(groups):
            self.notes.append(f"merge pass reconciled {len(groups)} batch groups into {len(merged)}")
        return [merged[i] for i in sorted(merged)]


@dataclass
class ClaudeCorroborationGrouper(_ClaudeGrouper):
    """Groups claims that assert the SAME FACT, for R-GROUND-05 corroboration counting.

    Blocks first, then judges. `params["claim_sources"]` (supplied by `_corroborate_by_group`) lets
    a block that draws on only one source be skipped without a call: corroboration counts INDEPENDENT
    sources, so such a block has no possible verdict worth paying for.
    """

    backend: Similarity | None = None
    block_threshold: float = LEXICAL_BLOCK_THRESHOLD
    max_claims_per_call: int = MAX_CLAIMS_PER_CALL

    def __call__(self, claims: list[tuple[str, str]], params: dict) -> list[dict]:
        if not claims:
            return []
        target = params.get("target_domain") or "the topic"
        sources = params.get("claim_sources") or {}
        text_of = dict(claims)

        blocks = lexical_groups(claims, self.backend or LexicalSimilarity(), self.block_threshold)
        candidates: list[list[tuple[str, str]]] = []
        skipped_single_source = 0
        for ids in blocks:
            if len(ids) < 2:
                continue
            if sources and len({sources.get(cid) for cid in ids}) < 2:
                skipped_single_source += 1
                continue
            block = [(cid, text_of[cid]) for cid in ids]
            if len(block) > self.max_claims_per_call:
                self.notes.append(
                    f"block of {len(block)} claims split into "
                    f"{-(-len(block) // self.max_claims_per_call)} calls; pairs separated by the "
                    f"split cannot be corroborated")
            candidates.extend(_batches(block, self.max_claims_per_call))

        if skipped_single_source:
            self.notes.append(f"{skipped_single_source} block(s) drew on one source only and were "
                              f"not sent for judgement")
        self.notes.append(f"{len(blocks)} lexical blocks at threshold {self.block_threshold} -> "
                          f"{len(candidates)} judgement call(s)")

        groups: list[dict] = []
        for i, block in enumerate(candidates, start=1):
            payload = self._ask(
                _CORROBORATION_INSTRUCTION.format(target=target, claims=_render(block)),
                f"corroboration block {i}/{len(candidates)}")
            groups.extend({"claim_ids": g["claim_ids"]} for g in payload.get("groups") or []
                          if isinstance(g, dict) and len(g.get("claim_ids") or []) > 1)
        return groups
