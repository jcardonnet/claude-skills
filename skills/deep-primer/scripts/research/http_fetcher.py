"""Live `Fetcher`: turn a URL into a Document the ledger may anchor claims to.

Classification: tool-loop (network I/O — NOT hermetic, not unit-tested against the live web)
Implements: the production half of the R-DISC-01 firewall (HANDOFF §5 step 2)

Why this matters more than "download a page"
--------------------------------------------
R-DISC-01 says a discovery lead is a POINTER, and a claim only becomes provenance once its quote is
found verbatim in a document actually fetched. Offline that firewall is enforced against
`ReplayFetcher`'s frozen corpus, which proves the mechanism but can never prove the claim — the
corpus was written by us. Only a real fetch closes it.

`ReplayFetcher` stays the default everywhere else on purpose: eval must score the same ledger every
time, not whatever the live web served that morning. The intended workflow is fetch live ONCE,
freeze via `freeze_corpus`, then replay forever.

Deliberate constraints
----------------------
  - robots.txt is honored. A primer generator is an automated crawler and should behave like one;
    a disallowed URL returns None and is reported as unresolved rather than silently fetched.
  - Body text only, capped. Figures are never pulled: the skill's copyright rule draws synthetic
    SVG rather than lifting a source domain's artwork, so there is nothing here that fetches images.
  - Failures return None instead of raising. `retrieve_for_questions` already treats an unfetchable
    URL as `unresolved`, which is the honest outcome — a lead that would not load is not evidence.
  - A body that is too short to be the document is refused too (`MIN_CONTENT_WORDS`). Returning
    bytes is not the same as returning the page that was sought, and the difference is invisible
    downstream: `fetch_source_leads` stamps every document it keeps with its lead's declared type,
    so a bot wall enters the ledger wearing whatever credibility tier discovery guessed for the
    paper behind it. spec-05's campaign put 15 claims of interstitial troubleshooting text into the
    ledger that way, attributed to `trialsjournal.biomedcentral.com` and typed `primary_paper`.
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import UTC, datetime
from pathlib import Path

from research.retrieval_loop import Document, canonical_url

USER_AGENT = "deep-primer/1.0 (+research primer generator; respects robots.txt)"
MAX_BYTES = 4_000_000
TIMEOUT_S = 20

#: Below this many words a fetch is refused as chrome rather than kept as a document (G17 class 1).
#: Measured, not guessed. Across the 449 documents of the four committed campaign corpora the
#: word-count band 62-92 is EMPTY: everything below it is a bot wall (Cloudflare "Client Challenge"
#: at 37 words), a cookie notice (PubMed at 15), or a navigation-only shell (a Jaeger docs index at
#: 61, the OpenTelemetry Baggage spec page at 51 -- all 51 of them "View page source / Was this page
#: helpful?"), and the thinnest document carrying a real sentence is 93. 80 sits inside that gap.
#: It is deliberately NOT set high enough to reach the landing-page class (222-262 words), which is
#: genuinely about the topic and cannot be told from a document by length -- see GAPS.md G17.
MIN_CONTENT_WORDS = 80
_TEXTUAL = ("text/html", "text/plain", "application/xhtml+xml", "application/xml", "text/xml")


def html_to_text(html: str) -> str:
    """Readable body text. Uses lxml when present (already a declared dependency), else the stdlib
    parser — both ship with beautifulsoup4, so this adds no new requirement."""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001 — parser availability, not a logic error; html.parser always works
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "form"]):
        tag.decompose()
    return "\n".join(line for line in
                     (ln.strip() for ln in soup.get_text("\n").splitlines()) if line)


class HttpFetcher:
    """Fetch over HTTP(S), honoring robots.txt. Satisfies `retrieval_loop.Fetcher`."""

    name = "http"

    def __init__(self, *, timeout_s: int = TIMEOUT_S, max_bytes: int = MAX_BYTES,
                 user_agent: str = USER_AGENT, obey_robots: bool = True,
                 min_words: int = MIN_CONTENT_WORDS) -> None:
        self.timeout_s = timeout_s
        self.max_bytes = max_bytes
        self.user_agent = user_agent
        self.obey_robots = obey_robots
        self.min_words = min_words
        self.fetched: list[str] = []
        self.refused: dict[str, str] = {}          # url -> why it produced no Document
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _read_robots(self, origin: str) -> urllib.robotparser.RobotFileParser | None:
        """Fetch and parse an origin's robots.txt. `None` means "could not determine" — deny.

        Not `RobotFileParser.read()`, which is what this used. That method calls `urlopen` with no
        timeout argument, so `timeout_s` governed the page fetch and nothing at all governed the
        robots fetch: a single unresponsive origin hung the campaign indefinitely.

        Outcomes follow RFC 9309 §2.3.1 instead of collapsing to "allow". A 4xx means no rules were
        published, so everything is permitted; 401/403 means access is refused, which is itself a
        prohibition; 5xx or an unreachable host means UNAVAILABLE, which the RFC says to treat as
        complete disallow. The old handler mapped every one of those — a timeout, a connection
        reset, a decode error — to "not a prohibition", cached it per origin for the rest of the
        run, and fetched away. Failing open on the check that exists to keep the crawler polite is
        the wrong direction, and `refused[url]` records the reason either way.
        """
        parser = urllib.robotparser.RobotFileParser()
        robots_url = f"{origin}/robots.txt"
        parser.set_url(robots_url)
        request = urllib.request.Request(robots_url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:  # noqa: S310
                body = response.read(self.max_bytes)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                parser.disallow_all = True
                return parser
            if 400 <= exc.code < 500:
                parser.allow_all = True          # nothing published => no restrictions
                return parser
            return None                          # 5xx: unavailable => complete disallow
        except (urllib.error.URLError, OSError, ValueError):
            return None                          # unreachable => unavailable => complete disallow
        parser.parse(body.decode("utf-8", errors="replace").splitlines())
        return parser

    def _allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        parts = urllib.parse.urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._read_robots(origin)
        parser = self._robots[origin]
        return False if parser is None else parser.can_fetch(self.user_agent, url)

    def __call__(self, url: str) -> Document | None:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            self.refused[url] = f"unsupported scheme {parts.scheme!r}"
            return None
        if not self._allowed(url):
            self.refused[url] = "disallowed by robots.txt"
            return None

        request = urllib.request.Request(url, headers={  # noqa: S310 — scheme checked above
            "User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml,text/plain",
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:  # noqa: S310
                content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()
                if content_type and content_type not in _TEXTUAL:
                    self.refused[url] = f"non-textual content-type {content_type!r}"
                    return None
                raw = response.read(self.max_bytes + 1)
                final_url = response.geturl()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            self.refused[url] = f"{type(exc).__name__}: {exc}"
            return None

        if len(raw) > self.max_bytes:
            self.refused[url] = f"body exceeded {self.max_bytes} bytes"
            return None

        # robots was checked against the URL we ASKED for; urllib follows redirects silently, so a
        # 301 to a disallowed path would otherwise be fetched and kept. The redirect target is the
        # page actually retrieved and stored, so it is the one the permission has to cover.
        if final_url != url and not self._allowed(final_url):
            self.refused[url] = f"redirected to {final_url}, disallowed by robots.txt"
            return None

        body = raw.decode("utf-8", errors="replace")
        text = html_to_text(body) if "html" in (content_type or "html") else body
        if not text.strip():
            self.refused[url] = "fetched but empty after text extraction"
            return None

        # Too short to be the document that was asked for. Refusing here rather than downstream is
        # the point: every later stage sees a Document and has no way back to "was this a page?".
        words = len(text.split())
        if words < self.min_words:
            self.refused[url] = (f"body is {words} words, below the {self.min_words}-word minimum "
                                 f"— a bot wall, cookie notice or nav-only shell, not a document")
            return None

        self.fetched.append(final_url)
        return Document(
            url=final_url,
            text=text,
            title=_title(body),
            retrieved_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        )


def _title(html: str) -> str | None:
    from bs4 import BeautifulSoup
    tag = BeautifulSoup(html, "html.parser").find("title")
    return tag.get_text(strip=True) if tag else None


def freeze_corpus(documents: list[Document], out_dir: str | Path) -> Path:
    """Write documents in the layout `ReplayFetcher(corpus_dir=...)` reads.

    This is the point of fetching live: run the network ONCE, freeze, then let eval replay it
    forever. Without this step a live grounding run is unreproducible and the numbers it produces
    cannot support a threshold — the same reason the discovery campaign freezes its snapshot.
    """
    import json
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    for doc in documents:
        stem = canonical_url(doc.url).replace("/", "_").replace(":", "_")[:120] or "doc"
        (root / f"{stem}.txt").write_text(doc.text, encoding="utf-8")
        (root / f"{stem}.json").write_text(json.dumps({
            "url": doc.url, "title": doc.title, "source_type": doc.source_type,
            "retrieved_at": doc.retrieved_at, "provenance_origin": doc.provenance_origin,
        }, indent=2), encoding="utf-8")
    return root
