"""A live campaign `Backend` on the local `claude` CLI, with every returned URL verified.

Classification: agent-orchestrated (model + network — NOT hermetic)
Implements: the production half of `deep_research.CallableBackend` (HANDOFF §5 step 1)

The measurement that shaped this
--------------------------------
Probed here, `claude -p` in this environment does **not** actually search the web:
`usage.server_tool_use.web_search_requests` came back `0` even with `--tools WebSearch,WebFetch
--permission-mode bypassPermissions`. The model answered from training data, returned plausible
URLs, and — asked directly — reported `"searched": true`. Two of three URLs happened to resolve; one
did not, and the version number it "found" differed between two runs of the same question.

So a research backend must never trust a model's self-reported sourcing. That is not a quirk of this
CLI, it is the assumption R-DISC-01 already encodes: **a lead is a pointer, not evidence.** This
backend therefore fetches every URL it is handed before letting it into a snapshot, because
`run_brief` FREEZES what it returns — a confabulated URL written into the snapshot is a fabrication
with a permanent home, replayed as fact by every eval run afterwards.

Unfetchable leads are marked `status: "dropped"` with a reason rather than quietly removed. The
count of what a wave proposed versus what survived is itself a signal about the backend, and
deleting the evidence would hide it.

Nothing here promotes a lead to provenance. That still requires the grounding loop finding the quote
verbatim in a fetched document (`claim_extractor.anchor_claims`). This only ensures the pointers are
real pointers.
"""
from __future__ import annotations

import json

from research.deep_research import brief_id
from research.http_fetcher import HttpFetcher
from utils.claude_cli import ClaudeCli, CliUnavailable

_INSTRUCTION = """\
You are running one research brief for a technical primer. Cover the questions from the angle given.

Wave: {wave}
Framing: {framing}
Angle: {angle}
Preferred source class: {source_class}
Stance to take: {stance}

QUESTIONS:
{questions}

ADDITIONAL INSTRUCTIONS:
{instructions}

Write a compact markdown report answering the questions from this framing. Then list the sources you
are drawing on. Only list a URL you are confident exists — every one will be fetched and checked,
and a URL that does not resolve is discarded and counted against this brief.

Return RAW JSON and nothing else, no markdown fence:
{{"report": "<markdown, <= 800 words>",
  "sources": [{{"url": "<https url>", "type": "primary_paper|docs|blog|vendor|standard",
               "why": "<= 15 words on what it supports"}}]}}
"""


class ClaudeResearchBackend:
    """Satisfies `deep_research.Backend`: `(brief) -> (report_markdown, source_dicts)`."""

    name = "claude-cli"

    def __init__(self, cli: ClaudeCli | None = None, fetcher: HttpFetcher | None = None, *,
                 model: str = "haiku", cost_cap_usd: float = 5.0, verify_urls: bool = True) -> None:
        self.cli = cli or ClaudeCli(model=model, cost_cap_usd=cost_cap_usd)
        self.fetcher = fetcher or HttpFetcher()
        self.verify_urls = verify_urls
        self.documents: list = []       # what actually fetched — hand to freeze_corpus()
        self.dropped: list[dict] = []

    def _instruction(self, brief) -> str:
        return _INSTRUCTION.format(
            wave=brief.wave, framing=brief.framing, angle=brief.angle or "-",
            source_class=brief.source_class or "-", stance=brief.stance or "-",
            questions="\n".join(f"- {q}" for q in brief.questions) or "- (none given)",
            instructions="\n".join(f"- {i}" for i in brief.instructions) or "- (none)",
        )

    def __call__(self, brief) -> tuple[str, list[dict]]:
        bid = brief_id(brief)
        try:
            payload = self.cli.result_json(self._instruction(brief))
        except (CliUnavailable, json.JSONDecodeError) as exc:
            # An empty wave is a real, reportable outcome; inventing one would be worse.
            return (f"# {brief.framing} (brief {bid})\n\nNo report: {type(exc).__name__}: {exc}\n",
                    [])

        report = str(payload.get("report") or "").strip()
        leads: list[dict] = []
        for n, raw in enumerate(payload.get("sources") or [], start=1):
            if not isinstance(raw, dict) or not raw.get("url"):
                continue
            lead = {
                "id": f"{bid}-s{n}",
                "url": str(raw["url"]),
                "type": raw.get("type"),
                "status": "accepted",
                "provenance_origin": "discovered",
                "surfaced_by": [brief.framing],
                "report_ids": [bid],
                "why": str(raw.get("why") or "")[:120],
            }
            if self.verify_urls:
                doc = self.fetcher(lead["url"])
                if doc is None:
                    lead["status"] = "dropped"
                    lead["dropped_reason"] = self.fetcher.refused.get(lead["url"], "did not fetch")
                    self.dropped.append(lead)
                else:
                    self.documents.append(doc)
                    lead["fetched_title"] = doc.title
                    lead["retrieved_at"] = doc.retrieved_at
            leads.append(lead)

        header = f"# {brief.framing} — wave {brief.wave} (brief {bid})\n\n"
        return header + (report or "_(no report body returned)_") + "\n", leads
