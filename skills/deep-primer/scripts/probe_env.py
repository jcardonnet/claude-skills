"""Probe optional deps (spaCy+coref, NLI/MiniCheck, lxml/bs4). Run FIRST; emit
CAPABILITIES.md so lints/verify choose native vs fallback.

Classification: local-deterministic
Implements: -

This is a hermetic, network-free probe. Every optional import is guarded; a
missing dependency is recorded as a fallback, never an error. The output map
tells the linter (`scripts/lint.py`), the coherence check
(`checks/coherence_givennew.py`), and the citation verifier
(`verify/citation_quality.py`) whether their native path is available or they
must degrade.

Usage:
    python skills/deep-primer/scripts/probe_env.py            # writes <repo-root>/CAPABILITIES.md
    python skills/deep-primer/scripts/probe_env.py path.md    # writes to an explicit path
"""
from __future__ import annotations

import importlib.util
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Repo root = .../skills/deep-primer/scripts/probe_env.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Probe:
    """One capability detection result."""

    name: str
    available: bool
    detail: str
    version: str | None = None
    runtime_note: str = ""  # caveats that hold even when `available` is True


@dataclass
class Capabilities:
    probes: dict[str, Probe] = field(default_factory=dict)

    def add(self, p: Probe) -> None:
        self.probes[p.name] = p

    def ok(self, name: str) -> bool:
        p = self.probes.get(name)
        return bool(p and p.available)


# --- low-level helpers -------------------------------------------------------

def _installed(module: str) -> bool:
    """True if `module` can be found without importing it (cheap, side-effect-free)."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _version(module: str) -> str | None:
    try:
        mod = __import__(module)
        return getattr(mod, "__version__", None)
    except Exception:
        return None


# --- individual probes -------------------------------------------------------

def probe_lxml() -> Probe:
    if _installed("lxml"):
        return Probe("lxml", True, "lxml installed (fast HTML/XML parser backend)", _version("lxml"))
    return Probe("lxml", False, "lxml not installed; bs4 can fall back to the stdlib 'html.parser'")


def probe_bs4() -> Probe:
    if _installed("bs4"):
        ver = _version("bs4")
        return Probe("beautifulsoup4", True, "bs4 installed (HTML -> Block round-trip parsing)", ver)
    return Probe("beautifulsoup4", False, "bs4 not installed; HTML round-trip (parse_primer) unavailable")


def probe_spacy() -> Probe:
    if not _installed("spacy"):
        return Probe("spacy", False, "spaCy not installed")
    return Probe("spacy", True, "spaCy library installed (POS/dep parse for prose + entity-grid lints)", _version("spacy"))


def probe_spacy_model() -> Probe:
    """Detect a loadable English model. Loading is the only honest test of availability."""
    if not _installed("spacy"):
        return Probe("spacy_model", False, "spaCy not installed, so no English model")
    candidates = ["en_core_web_trf", "en_core_web_lg", "en_core_web_md", "en_core_web_sm"]
    try:
        import spacy
    except Exception as e:  # pragma: no cover - defensive
        return Probe("spacy_model", False, f"spaCy import failed: {e!r}")
    for name in candidates:
        if importlib.util.find_spec(name) is None:
            continue
        try:
            spacy.load(name)
            return Probe("spacy_model", True, f"English model '{name}' loads", name)
        except Exception as e:
            return Probe("spacy_model", False, f"model '{name}' present but failed to load: {e!r}")
    return Probe(
        "spacy_model", False,
        "no en_core_web_* model installed (run: python -m spacy download en_core_web_sm)",
    )


def probe_coref() -> Probe:
    """Coreference resolver for cross-sentence entity chaining (R-PROSE-01 native path)."""
    for mod, label in (("fastcoref", "fastcoref"), ("crosslingual_coreference", "crosslingual_coreference")):
        if _installed(mod):
            return Probe(
                "coref", True,
                f"{label} installed (coreference for given->new entity chaining)",
                _version(mod),
                runtime_note="model weights download from HuggingFace on first use (needs network once).",
            )
    return Probe("coref", False, "no coref resolver (fastcoref) installed; entity-grid uses surface-string chaining only")


def probe_nli() -> Probe:
    """Entailment model for citation recall/precision (R-GROUND-02/03) and chunk self-containment (R-PROJ-04)."""
    if _installed("minicheck"):
        return Probe("nli", True, "MiniCheck installed (purpose-built cheap fact-verification NLI)", _version("minicheck"))
    has_tf = _installed("transformers")
    has_torch = _installed("torch")
    if has_tf and has_torch:
        return Probe(
            "nli", True,
            "transformers + torch installed (local NLI substrate; MiniCheck absent from PyPI)",
            f"transformers {_version('transformers')} / torch {_version('torch')}",
            runtime_note=(
                "no purpose-built MiniCheck package; instantiate a HF NLI model "
                "(e.g. a MiniCheck/RoBERTa-MNLI checkpoint) which downloads weights on first use."
            ),
        )
    missing = [m for m, present in (("transformers", has_tf), ("torch", has_torch)) if not present]
    return Probe("nli", False, f"no local entailment substrate (missing: {', '.join(missing)})")


def probe_cuda() -> Probe:
    """Detect a CUDA GPU usable by torch (accelerates the local NLI verifier + transformer coref)."""
    if not _installed("torch"):
        return Probe("cuda", False, "torch not installed; CPU only")
    try:
        import torch

        if torch.cuda.is_available():
            n = torch.cuda.device_count()
            names = ", ".join(torch.cuda.get_device_name(i) for i in range(n))
            return Probe(
                "cuda", True, f"{n}× CUDA GPU ({names})",
                f"torch CUDA {getattr(torch.version, 'cuda', '?')}",
                runtime_note="local NLI verifier + transformer/coref models run GPU-accelerated.",
            )
        return Probe(
            "cuda", False,
            "torch present but torch.cuda.is_available() is False (CPU only)",
            getattr(torch.version, "cuda", None),
        )
    except Exception as e:  # pragma: no cover - defensive
        return Probe("cuda", False, f"torch CUDA probe failed: {e!r}")


# --- capability -> check/verifier mapping ------------------------------------

def lint_matrix(c: Capabilities) -> list[dict]:
    """How each enforcement check runs given the detected capabilities.

    mode: 'native' (full implementation) | 'degraded' (heuristic fallback) | 'flag-only'.
    """
    spacy_ok = c.ok("spacy")
    model_ok = c.ok("spacy_model")
    coref_ok = c.ok("coref")
    given_new_native = spacy_ok and model_ok  # coref strengthens but is not required
    html_ok = c.ok("beautifulsoup4")

    rows: list[dict] = []

    def row(check, rules, enf, native_when, mode, note):
        rows.append({
            "check": check, "rules": rules, "enforcement": enf,
            "native_when": native_when, "mode": mode, "note": note,
        })

    # Pure-Python deterministic lints — always native (pyyaml + stdlib only).
    always = [
        ("checks/structure_coverage.py", "R-PARAM-01, R-ARCH-05, R-CARD-02, R-SUMM-02, R-RECALL-01, R-ART-01, R-ARCH-06, R-XREF-02, R-CONSIST-01/03, R-SCENT-01(banned terms)"),
        ("checks/multiview_concepts.py", "R-MV-01"),
        ("checks/univocity_terms.py", "R-VOCAB-01"),
        ("checks/footnote.py", "R-CONSIST-03"),
        ("checks/xrefs.py", "R-XREF-02"),
        ("checks/provenance.py", "R-PROJ-05"),
        ("render/check_alignment.py", "R-PROJ-02"),
    ]
    for check, rules in always:
        row(check, rules, "hard_lint", "always (operates on the IR with pyyaml + stdlib)", "native",
            "IR-first: reads document-ir.yaml, no HTML parsing or NLP needed.")

    # prose_caps — regex/token heuristics natively; spaCy sharpens noun-cluster + condition-first.
    row("checks/prose_caps.py", "R-SUMM-03, R-PROSE-04, R-PROSE-05", "hard_lint",
        "core caps always; spaCy improves noun-cluster (R-PROSE-05) + condition-first (R-PROSE-04)",
        "native" if spacy_ok and model_ok else "degraded",
        "compression_gradient = token counts (always exact); length/noun-cluster/condition-first use POS when spaCy present, else regex heuristics.")

    # coherence given->new — the headline NLP-dependent lint.
    row("checks/coherence_givennew.py", "R-PROSE-01", "hard_lint",
        "spaCy + English model (coref optional but recommended)",
        "native" if given_new_native else "degraded",
        ("entity grid via dependency-parsed subjects"
         + (" + coreference chaining" if coref_ok else " (NO coref: pronoun chains under-counted)")
         if given_new_native
         else "FALLBACK: surface-string / noun-overlap entity grid (per Prompt 2) — flags only the coarsest given->new breaks."))

    # recency — needs the live web; offline it can only flag.
    row("checks/recency_versions.py", "R-GROUND-04", "hard_lint",
        "live web access (version lookup)", "flag-only",
        "offline sandbox: extracts named tech and flags un-pinned/possibly-stale versions; cannot confirm latest without network.")

    # HTML round-trip — legacy under IR-first; needs bs4/lxml.
    row("utils/parse_primer.py", "R-DEPTH-02, R-FIG-04, R-CONSIST-02 (round-trip)", "hard_lint",
        "beautifulsoup4 (+ lxml backend)", "native" if html_ok else "degraded",
        "IR is canonical; this is for HTML->Block round-trip only. " + ("bs4+lxml present." if html_ok else "bs4 absent: round-trip disabled, lints read the IR directly."))

    return rows


def verifier_matrix(c: Capabilities) -> list[dict]:
    nli_ok = c.ok("nli")
    minicheck = c.ok("nli") and _installed("minicheck")
    accel = f"GPU-accelerated ({c.probes['cuda'].detail})" if c.ok("cuda") else "CPU"
    if minicheck:
        path, mode = "MiniCheck (native)", "native"
        note = f"Cheap purpose-built NLI, {accel}; run one claim+quote per call."
    elif nli_ok:
        path, mode = "local HF NLI model (native substrate)", "native"
        note = (f"transformers+torch present, {accel}; load an NLI checkpoint (downloads weights once) "
                "OR fall back to scoped Claude.")
    else:
        path, mode, note = "scoped Claude call (fallback)", "fallback", "No local NLI; one binary supports/not-supports Claude call per (claim, quote)."

    det = "always (deterministic marker -> ledger source_id resolution; no model)"
    return [
        {"check": "verify/citation_quality.py::resolves_to_ledger", "rules": "R-GROUND-01",
         "enforcement": "hard_lint", "path": "pure Python", "mode": "native", "note": det},
        {"check": "verify/citation_quality.py::recall", "rules": "R-GROUND-02",
         "enforcement": "model_verified", "path": path, "mode": mode, "note": note},
        {"check": "verify/citation_quality.py::precision", "rules": "R-GROUND-03",
         "enforcement": "model_verified", "path": path, "mode": mode, "note": note},
        {"check": "verify/chunk_selfcontained.py::entailment", "rules": "R-PROJ-04",
         "enforcement": "model_verified", "path": path, "mode": mode,
         "note": "Same entailment substrate: each de-anaphorized LLM-MD chunk must still entail its claim_ids."},
    ]


# --- rendering ---------------------------------------------------------------

_MODE_MARK = {"native": "✅ native", "degraded": "⚠️ degraded", "flag-only": "⚠️ flag-only", "fallback": "⚠️ fallback"}


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    return "\n".join(out)


def render(c: Capabilities) -> str:
    L: list[str] = []
    w = L.append
    w("# CAPABILITIES.md")
    w("")
    w("Environment capability record for **deep-primer**. Generated by "
      "`skills/deep-primer/scripts/probe_env.py` (local-deterministic, network-free). "
      "Regenerate after changing the venv: `make probe`. This file is git-ignored — it "
      "describes *this* machine, not the skill.")
    w("")
    w(f"- **Python:** {platform.python_version()} ({sys.implementation.name}) — `{sys.executable}`")
    w(f"- **Platform:** {platform.platform()}")
    cuda = c.probes["cuda"]
    compute = f"GPU — {cuda.detail} ({cuda.version})" if cuda.available else f"CPU only — {cuda.detail}"
    w(f"- **Compute:** {compute}")
    w("")

    w("## Detected capabilities")
    w("")
    rows = []
    for key in ("lxml", "beautifulsoup4", "spacy", "spacy_model", "coref", "nli"):
        p = c.probes[key]
        status = "✅ available" if p.available else "❌ absent"
        ver = p.version or "—"
        detail = p.detail + (f" _{p.runtime_note}_" if p.runtime_note else "")
        rows.append([p.name, status, ver, detail])
    w(_table(["Capability", "Status", "Version", "Detail"], rows))
    w("")

    w("## Lints — native vs fallback")
    w("")
    w("Deterministic lints operate on the **document IR** (canonical), so most need only "
      "`pyyaml` + the stdlib and are always native. The NLP-dependent and network-dependent "
      "ones degrade as noted.")
    w("")
    rows = []
    for r in lint_matrix(c):
        rows.append([r["check"], r["rules"], r["enforcement"], _MODE_MARK[r["mode"]], r["native_when"], r["note"]])
    w(_table(["Script::check", "Rule(s)", "Enforcement", "Mode here", "Native when", "Behavior in this env"], rows))
    w("")

    w("## Verifier (Phase 6 / Phase 8 entailment) — native vs fallback")
    w("")
    w("Citation recall/precision (`R-GROUND-02/03`) and LLM-MD chunk self-containment "
      "(`R-PROJ-04`) are **model_verified**: an entailment model judges whether a quote "
      "supports a claim. Fabrication resolution (`R-GROUND-01`) is deterministic and always native.")
    w("")
    rows = []
    for r in verifier_matrix(c):
        rows.append([r["check"], r["rules"], r["enforcement"], _MODE_MARK[r["mode"]], r["path"], r["note"]])
    w(_table(["Script::check", "Rule(s)", "Enforcement", "Mode here", "Path", "Notes"], rows))
    w("")

    # Headline summary
    given_new = "native" if (c.ok("spacy") and c.ok("spacy_model")) else "degraded (entity-overlap)"
    coref = "with coref" if c.ok("coref") else "no coref"
    verifier = (
        "MiniCheck" if (c.ok("nli") and _installed("minicheck"))
        else "local HF NLI substrate (transformers+torch)" if c.ok("nli")
        else "scoped-Claude fallback"
    )
    if c.ok("nli") and c.ok("cuda"):
        verifier += " — GPU-accelerated"
    w("## Bottom line")
    w("")
    w("- **Deterministic IR lints:** native (pyyaml + stdlib).")
    w(f"- **Given→new coherence (R-PROSE-01):** {given_new}, {coref}.")
    w(f"- **HTML round-trip (parse_primer):** {'native (bs4+lxml)' if c.ok('beautifulsoup4') else 'disabled — IR read directly'}.")
    w(f"- **Citation entailment verifier (R-GROUND-02/03, R-PROJ-04):** {verifier}.")
    w("- **Recency/version sweep (R-GROUND-04):** flag-only offline (needs live web).")
    w("")
    return "\n".join(L)


def build_capabilities() -> Capabilities:
    c = Capabilities()
    for p in (probe_lxml(), probe_bs4(), probe_spacy(), probe_spacy_model(),
              probe_coref(), probe_nli(), probe_cuda()):
        c.add(p)
    return c


def main(argv: list[str]) -> int:
    c = build_capabilities()
    out_path = Path(argv[0]).resolve() if argv else (REPO_ROOT / "CAPABILITIES.md")
    out_path.write_text(render(c), encoding="utf-8")

    # Concise stdout summary.
    print(f"wrote {out_path}")
    for key in ("lxml", "beautifulsoup4", "spacy", "spacy_model", "coref", "nli"):
        p = c.probes[key]
        print(f"  [{'OK ' if p.available else '-- '}] {p.name:16} {p.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
