"""Coverage + conflict analysis against the research plan.

Classification: local-deterministic
Implements: R-EVID-03 (independent non-vendor corroboration for performance claims),
            the coverage half of the Phase-1 exit condition

Coverage is a model self-assessment in the abstract; here it is paired with a hard source count so
a question cannot be declared covered on judgment alone (research-perspectives.md step 6). A
question that runs out of iterations is marked `thin` rather than covered — an under-supported area
the primer can flag beats one it fabricates into.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ir.schema import CoverageStatus, ResearchPlan, SourceLedger  # noqa: E402
from research.retrieval_loop import Document  # noqa: E402

MIN_SOURCES_PER_QUESTION = 2
MIN_INDEPENDENT_NONVENDOR_FOR_PERF = 2
MAX_RETRIEVAL_ITERATIONS = 6
VENDOR_TYPES = {"vendor"}

# performance-shaped claims: a number attached to a speed/quality/cost assertion
_PERF_RE = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:%|x|ms|s|qps|gb|mb)|faster|slower|outperform\w*|beats|"
    r"speedup|latency|throughput|recall|precision|accuracy|cheaper)\b",
    re.IGNORECASE,
)


def is_performance_claim(text: str) -> bool:
    """Whether a claim asserts comparative performance (the R-EVID-03 trigger)."""
    return bool(_PERF_RE.search(text or ""))


def update_plan_coverage(plan: ResearchPlan, documents: list[Document],
                         iterations: dict[str, int] | None = None,
                         min_sources: int = MIN_SOURCES_PER_QUESTION,
                         max_iterations: int = MAX_RETRIEVAL_ITERATIONS) -> ResearchPlan:
    """Fill each question's `coverage` from what was actually fetched.

    covered  <- enough distinct sources
    thin     <- the iteration cap was hit first
    open     <- neither (still has budget)
    """
    iterations = iterations or {}
    for q in plan.questions:
        serving = [d for d in documents if q.id in d.served_questions]
        source_ids = sorted({d.source_id for d in serving})
        q.coverage.sources = source_ids
        q.coverage.independent_nonvendor = len(
            {d.source_id for d in serving if (d.source_type or "") not in VENDOR_TYPES})
        q.coverage.iterations = iterations.get(q.id, q.coverage.iterations)

        if len(source_ids) >= min_sources:
            q.coverage.status = CoverageStatus.covered
        elif q.coverage.iterations >= max_iterations:
            q.coverage.status = CoverageStatus.thin
        else:
            q.coverage.status = CoverageStatus.open
    return plan


def thin_questions(plan: ResearchPlan) -> list[str]:
    """Questions the primer must flag as under-supported rather than write over."""
    return [q.id for q in plan.questions if q.coverage.status == CoverageStatus.thin]


def uncorroborated_performance_claims(
        ledger: SourceLedger,
        min_independent: int = MIN_INDEPENDENT_NONVENDOR_FOR_PERF) -> list[str]:
    """R-EVID-03: a performance claim needs >= min_independent non-vendor sources.

    Vendor benchmarks repeated as established fact are the specific failure this counters, so the
    vendor's own source never counts toward its claim's corroboration.
    """
    by_source = {s.source_id: s for s in ledger.sources}
    problems: list[str] = []

    for source in ledger.sources:
        for claim in source.claims:
            if not is_performance_claim(claim.text):
                continue
            supporters = {sid for sid in claim.corroborated_by
                          if (by_source.get(sid) and (by_source[sid].type.value if by_source[sid].type else "")
                              not in VENDOR_TYPES)}
            if (source.type.value if source.type else "") not in VENDOR_TYPES:
                supporters.add(source.source_id)
            if len(supporters) < min_independent:
                problems.append(
                    f"{claim.claim_id}: performance claim with {len(supporters)} independent "
                    f"non-vendor source(s) (< {min_independent}) — tag contested or drop the number")
    return problems


def coverage_report(plan: ResearchPlan, ledger: SourceLedger) -> dict:
    """The Phase-1 exit check, as data: is every question covered, and every perf claim corroborated?"""
    thin = thin_questions(plan)
    open_qs = [q.id for q in plan.questions if q.coverage.status == CoverageStatus.open]
    perf = uncorroborated_performance_claims(ledger)
    return {
        "covered": [q.id for q in plan.questions if q.coverage.status == CoverageStatus.covered],
        "thin": thin,
        "open": open_qs,
        "uncorroborated_performance_claims": perf,
        # the exit condition: nothing still open, and no perf claim resting on a lone vendor
        "exit_ok": not open_qs and not perf,
    }
