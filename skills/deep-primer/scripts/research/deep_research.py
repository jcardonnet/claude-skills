"""Deep-research backend adapter - runs one research brief, returns (report, sources).

Classification: agent-orchestrated. Invokes the /deep-research workflow (or a local fallback)
for a single research-brief and captures the cited report plus its source list. NOT a pure
function - it calls an external research engine. Output is LEADS material only (R-DISC-01);
the grounding loop (retrieval_loop / claim_extractor) independently re-fetches and quotes.

Preferred backend: /deep-research (Claude Code, Max). Fallback: the local bounded retrieval_loop,
selected by CAPABILITIES.md. Reports are frozen into discovery-snapshot/ (R-DISC-05).

The seam: a backend is any callable taking a ResearchBrief and returning (report_text, sources).
`run_brief` owns the part that must not vary by backend — freezing the report into the snapshot
under a deterministic id — so eval can replay a campaign it did not run.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Callable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import ResearchBrief  # noqa: E402


class Backend(Protocol):
    name: str

    def __call__(self, brief: ResearchBrief) -> tuple[str, list[dict]]: ...


def brief_id(brief: ResearchBrief) -> str:
    """Deterministic id for a brief: its matrix cell + questions. Same brief -> same report file,
    so a replayed campaign resolves to the frozen snapshot rather than re-running research."""
    if brief.brief_id:
        return brief.brief_id
    payload = json.dumps([brief.wave, *brief.cell(), sorted(brief.questions)], sort_keys=True)
    return f"{brief.wave.lower()}-{hashlib.sha1(payload.encode(), usedforsecurity=False).hexdigest()[:8]}"


class ReplayBackend:
    """Reads a previously frozen report instead of running research (R-DISC-05).

    This is what makes the eval harness reproducible: the same snapshot always yields the same
    leads, so a threshold tuned against a campaign stays meaningful.
    """

    name = "replay"

    def __init__(self, snapshot_dir: str | Path) -> None:
        self.root = Path(snapshot_dir)

    def __call__(self, brief: ResearchBrief) -> tuple[str, list[dict]]:
        bid = brief_id(brief)
        report = self.root / f"report-{bid}.md"
        if not report.is_file():
            raise FileNotFoundError(f"no frozen report for brief {bid} in {self.root}")
        sources_file = self.root / f"sources-{bid}.json"
        sources = json.loads(sources_file.read_text(encoding="utf-8")) if sources_file.is_file() else []
        return report.read_text(encoding="utf-8"), sources


class CallableBackend:
    """Production seam. Wrap the /deep-research invocation (or the local retrieval_loop fallback)
    in a callable of this shape; nothing else in the campaign changes."""

    def __init__(self, fn: Callable[[ResearchBrief], tuple[str, list[dict]]], name: str = "deep-research") -> None:
        self._fn = fn
        self.name = name

    def __call__(self, brief: ResearchBrief) -> tuple[str, list[dict]]:
        return self._fn(brief)


def run_brief(brief: ResearchBrief, snapshot_dir: str | Path,
              backend: Backend | None = None) -> tuple[str, list[dict]]:
    """Run one brief through `backend` and freeze the result into snapshot_dir (R-DISC-05).

    With no backend supplied this replays the snapshot — the offline/test default, and the mode
    eval runs in. A live campaign passes a CallableBackend wrapping /deep-research.
    """
    root = Path(snapshot_dir)
    root.mkdir(parents=True, exist_ok=True)
    backend = backend or ReplayBackend(root)

    # A brief already frozen here is a brief already paid for, so don't buy it twice. `brief_id` is
    # content-addressed (wave + cell + questions), so a hit means THIS brief already ran, not merely
    # that some brief did; edit the brief and it gets a new id and runs live.
    #
    # This is the same rule `--from-corpus` applies one level up, for the same reason. Discovery is
    # the expensive, rate-limited half, and it is where campaigns actually die: on 2026-08-21
    # specs 04, 05 and 06 each exhausted the research budget 10-11 briefs in, and every one of those
    # briefs was already on disk. Without this, a retry re-pays for all of them before reaching the
    # brief that failed.
    #
    # Gate on `brief-*.json` and not on the report, because it is written LAST. A run killed
    # mid-freeze can leave a report with no sources file, and ReplayBackend reads that as an empty
    # source list rather than an error -- a brief that found nothing, which is the most reassuring
    # possible reading of a half-written snapshot. Requiring the last file makes presence mean the
    # whole triple landed.
    if not isinstance(backend, ReplayBackend) and (root / f"brief-{brief_id(brief)}.json").is_file():
        return ReplayBackend(root)(brief)

    report, sources = backend(brief)

    # Replay is a READ. Writing back what a ReplayBackend just handed us re-froze the snapshot
    # against whatever parameters the caller happened to use, so simply running `make test` rewrote
    # the committed brief fixtures — the topic string in tests differs from the one they were frozen
    # with. A snapshot that mutates when replayed is not a snapshot, and R-DISC-05's reproducibility
    # guarantee quietly depends on it holding still.
    if isinstance(backend, ReplayBackend):
        return report, sources

    bid = brief_id(brief)
    (root / f"report-{bid}.md").write_text(report, encoding="utf-8")
    (root / f"sources-{bid}.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    (root / f"brief-{bid}.json").write_text(
        json.dumps(brief.model_dump(mode="json"), indent=2), encoding="utf-8")
    return report, sources
