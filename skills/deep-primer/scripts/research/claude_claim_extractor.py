"""A real `Extractor` for the grounding loop — the model half of `claim_extractor.build_ledger`.

Classification: agent-orchestrated (model call — NOT hermetic)
Implements: the proposing half of R-GROUND-01; the deciding half stays in `anchor_claims`

Why this exists
---------------
`build_ledger` has always taken an `Extractor`, and the only implementation in the tree was
`QuoteScanExtractor` — a scanner for `CLAIM:` lines that no real web page contains. So every ledger
the project could build offline was either hand-authored or empty, and specs 03-06 shipped
hand-built ledgers full of `example.org`. This is what a ledger built from pages we actually
fetched needs.

The division of labour is the same one the module docstring already states
--------------------------------------------------------------------------
The model PROPOSES {text, quote}; `anchor_claims` DECIDES. Nothing here is trusted:

  - a quote that is not verbatim in the fetched body is rejected there, not here;
  - a quote over `MAX_QUOTE_WORDS` is rejected there, not here;
  - so the worst a confabulating model can do is waste a call.

That is why this module does not verify anything and must not start: two gates that can disagree is
worse than one gate that cannot.

`location` is computed, not asked for
-------------------------------------
A model asked "where in the document is this?" answers with a plausible line number. The quote's
actual offset is a fact about the fetched text, so it is measured here — and measured on the
NORMALIZED text, the same whitespace-insensitive form `Document.contains` matches on, so a location
is never reported for a quote the gate will go on to reject.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from research.claim_extractor import MAX_QUOTE_WORDS
from research.retrieval_loop import Document, normalize
from utils.claude_cli import ClaudeCli, CliUnavailable

#: Characters of document body per call. Web pages routinely exceed any single instruction, and a
#: truncated page silently grounds a primer in its navigation chrome. Chunking is bounded rather
#: than exhaustive: `MAX_CHUNKS` calls per document, front-loaded, because a page's substance is
#: near its top and the tail is references and footers.
CHUNK_CHARS = 12_000
MAX_CHUNKS = 3
MAX_CLAIMS_PER_CHUNK = 8

_INSTRUCTION = """\
You are building the evidence ledger for a technical primer. Extract ATOMIC, CHECKABLE claims from
the document excerpt below.

An atomic claim states ONE fact that could be shown wrong: a mechanism, a tradeoff, a measured
number, a version, a design constraint. Skip marketing copy, navigation text, author bios,
tables of contents, and anything that is only true of this website.

Document title: {title}
Source URL: {url}

EXCERPT:
---
{excerpt}
---

For each claim, give the claim in your own words AND a supporting quote copied EXACTLY, character
for character, from the excerpt above. The quote must be at most {max_words} words. Do not
paraphrase inside the quote, do not fix its typos, do not join text across an ellipsis: a quote
that is not found verbatim in the excerpt is discarded and the claim with it.

Return at most {max_claims} claims. Fewer is fine; an excerpt with nothing checkable in it should
return an empty list.

Return RAW JSON and nothing else, no markdown fence:
{{"claims": [{{"text": "<the claim, one sentence>",
              "quote": "<verbatim, <= {max_words} words>",
              "confidence": "high|medium|low"}}]}}
"""


def _chunks(text: str, size: int = CHUNK_CHARS, limit: int = MAX_CHUNKS) -> list[str]:
    """Split on paragraph boundaries where possible, never mid-sentence, no overlap.

    No overlap is deliberate: an overlapping window re-proposes the same claim from the same
    source, and `corroborate` counts INDEPENDENT sources, so a within-source duplicate cannot
    inflate corroboration — it just doubles the claim count a concept's salience is computed from.
    """
    out: list[str] = []
    rest = text
    while rest and len(out) < limit:
        if len(rest) <= size:
            out.append(rest)
            break
        cut = rest.rfind("\n\n", 0, size)
        if cut < size // 2:
            cut = rest.rfind(" ", 0, size)
        if cut <= 0:
            cut = size
        out.append(rest[:cut])
        rest = rest[cut:].lstrip()
    return [c for c in out if c.strip()]


def _locate(quote: str, document: Document) -> str | None:
    """Where the quote sits in the fetched body, measured on the normalized text.

    Returns None when it is not there at all — which is exactly the case `anchor_claims` is about
    to reject, so a location is never attached to a claim that will not survive.
    """
    haystack, needle = normalize(document.text), normalize(quote)
    if not needle or needle not in haystack:
        return None
    at = haystack.index(needle)
    return f"char {at} of {len(haystack)} (normalized)"


@dataclass
class ClaudeClaimExtractor:
    """An `Extractor` backed by the local `claude` CLI.

    Runs with NO tools: the document body is handed over inline, so a fetch tool here would only
    invite the model to read something other than the page the ledger will anchor against.
    """

    cli: ClaudeCli | None = None
    model: str = "haiku"
    cost_cap_usd: float = 5.0
    max_chunks: int = MAX_CHUNKS

    errors: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.cli = self.cli or ClaudeCli(model=self.model, cost_cap_usd=self.cost_cap_usd)

    def __call__(self, document: Document) -> list[dict]:
        proposals: list[dict] = []
        for excerpt in _chunks(document.text, limit=self.max_chunks):
            instruction = _INSTRUCTION.format(
                title=document.title or "(untitled)", url=document.url, excerpt=excerpt,
                max_words=MAX_QUOTE_WORDS, max_claims=MAX_CLAIMS_PER_CHUNK,
            )
            try:
                payload = self.cli.result_json(instruction)
            except (CliUnavailable, json.JSONDecodeError) as exc:
                # A failed extraction is a document with no claims, not a run that dies. The count
                # of these is a fact about the campaign, so it is recorded rather than swallowed.
                self.errors.append(f"{document.url}: {type(exc).__name__}: {exc}")
                continue
            for raw in (payload.get("claims") or [])[:MAX_CLAIMS_PER_CHUNK]:
                if not isinstance(raw, dict):
                    continue
                quote = str(raw.get("quote") or "").strip()
                proposals.append({
                    "text": str(raw.get("text") or "").strip(),
                    "quote": quote,
                    "location": _locate(quote, document),
                    "confidence": raw.get("confidence") or "medium",
                })
        return proposals
