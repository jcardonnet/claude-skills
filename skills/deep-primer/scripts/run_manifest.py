"""Phase ledger: record what a run completed so it can resume after interruption.

Classification: local-deterministic
Implements: the run-manifest contract in SKILL.md ("Write a run-manifest.json recording phase
completion so a run can resume after interruption")

The pipeline's expensive phases — the discovery campaign, the grounding loop — are exactly the ones
you do not want to repeat because Phase 7 crashed. The manifest records, per phase, whether it
completed and which artifacts it produced, so a resumed run can skip forward instead of re-spending
the research budget.

Timestamps are INJECTED rather than read from the clock: a manifest that changes on every load
would make golden-file comparison impossible, and the eval harness replays runs.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# the pipeline's phases, in order (SKILL.md)
PHASES = [
    "0-parameters",
    "1a-discovery",
    "1-research",
    "2-outline",
    "3-draft-ir",
    "4-coherence",
    "5-recall-figures",
    "6-verification",
    "7-critique",
    "8-delivery",
]


@dataclass
class PhaseRecord:
    status: str = "pending"          # pending | running | complete | failed
    artifacts: list[str] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    detail: str | None = None


@dataclass
class RunManifest:
    run_id: str
    topic: str | None = None
    phases: dict[str, PhaseRecord] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in PHASES:
            self.phases.setdefault(name, PhaseRecord())

    # --- transitions ---------------------------------------------------------

    def start(self, phase: str, at: str | None = None) -> RunManifest:
        self._require(phase)
        rec = self.phases[phase]
        rec.status = "running"
        rec.started_at = at
        return self

    def complete(self, phase: str, artifacts: list[str] | None = None, at: str | None = None) -> RunManifest:
        self._require(phase)
        rec = self.phases[phase]
        rec.status = "complete"
        rec.artifacts = sorted(artifacts or [])
        rec.completed_at = at
        return self

    def fail(self, phase: str, detail: str, at: str | None = None) -> RunManifest:
        self._require(phase)
        rec = self.phases[phase]
        rec.status = "failed"
        rec.detail = detail
        rec.completed_at = at
        return self

    # --- resume --------------------------------------------------------------

    def is_complete(self, phase: str) -> bool:
        self._require(phase)
        return self.phases[phase].status == "complete"

    def resume_from(self) -> str | None:
        """The first phase not yet complete — where a resumed run picks up.

        Returns the earliest incomplete phase in pipeline order, NOT the one after the last
        complete one: a run that completed phases 0-2 and 5 (say, from a manual re-run) must still
        resume at 3, because 8 consumes what 3 produced.
        """
        for name in PHASES:
            if self.phases[name].status != "complete":
                return name
        return None

    def completed_phases(self) -> list[str]:
        return [p for p in PHASES if self.phases[p].status == "complete"]

    def _require(self, phase: str) -> None:
        if phase not in self.phases:
            raise KeyError(f"unknown phase {phase!r}; expected one of {PHASES}")

    # --- persistence ---------------------------------------------------------

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "topic": self.topic,
                "phases": {k: asdict(v) for k, v in self.phases.items()},
                "resume_from": self.resume_from()}

    def save(self, path: str | Path = "run-manifest.json") -> Path:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: str | Path = "run-manifest.json") -> RunManifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        phases = {k: PhaseRecord(**{f: v.get(f) if f != "artifacts" else (v.get("artifacts") or [])
                                    for f in ("status", "artifacts", "started_at", "completed_at", "detail")})
                  for k, v in (data.get("phases") or {}).items()}
        return cls(run_id=data["run_id"], topic=data.get("topic"), phases=phases)
