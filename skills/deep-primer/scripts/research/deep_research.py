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
    return f"{brief.wave.lower()}-{hashlib.sha1(payload.encode()).hexdigest()[:8]}"


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

    report, sources = backend(brief)

    bid = brief_id(brief)
    (root / f"report-{bid}.md").write_text(report, encoding="utf-8")
    (root / f"sources-{bid}.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    (root / f"brief-{bid}.json").write_text(
        json.dumps(brief.model_dump(mode="json"), indent=2), encoding="utf-8")
    return report, sources
