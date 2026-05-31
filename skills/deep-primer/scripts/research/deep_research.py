"""Deep-research backend adapter - runs one research brief, returns (report, sources).

Classification: agent-orchestrated. Invokes the /deep-research workflow (or a local fallback)
for a single research-brief and captures the cited report plus its source list. NOT a pure
function - it calls an external research engine. Output is LEADS material only (R-DISC-01);
the grounding loop (retrieval_loop / claim_extractor) independently re-fetches and quotes.

Preferred backend: /deep-research (Claude Code, Max). Fallback: the local bounded retrieval_loop,
selected by CAPABILITIES.md. Reports are frozen into discovery-snapshot/ (R-DISC-05).
Stage 6 - implement per ../../CLAUDE_CODE_PROMPTS.md (Prompt 6a).
NOTE: agent-orchestrated - invokes /deep-research (or the local fallback), not a hermetic function.
"""
from __future__ import annotations


def run_brief(brief: dict, snapshot_dir: str) -> tuple:
    """Run a deep-research brief; return (report_text, sources). Freeze the report into snapshot_dir."""
    raise NotImplementedError("deep-primer Stage 6 stub: research/deep_research.py::run_brief (Prompt 6a)")
