# HANDOFF — resuming deep-primer work in a local session

Written at the end of a Claude Code **web** session that implemented `PLAN.md` Stages A–F.
Branch **`claude/deep-primer-skill-review-n3egin`**, PR **#1** (draft), 8 commits, tree clean,
everything pushed. Read `PLAN.md` for the full stage-by-stage rationale; this file is the
what-you-need-to-start.

---

## 1. First five minutes

```bash
git fetch origin && git checkout claude/deep-primer-skill-review-n3egin
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'            # optionally: pip install -e '.[nlp]'
make probe                          # writes CAPABILITIES.md (gitignored, absent on a fresh clone)
make test && make validate && make eval
```

**Use `python -m pytest`, not bare `pytest`.** In the web container the bare entrypoint resolved to
a different interpreter and failed on a missing `yaml`. The Makefile and CI already use `python -m`.

Expected on a clean checkout (measured at handoff):

| Command | Expected |
|---|---|
| `make test` | `256 passed, 6 skipped` — all 6 skips are "spaCy model unavailable" |
| `make validate` | `OK — 1 skill(s) valid (lockstep in sync), 2 skipped` |
| `make lint` | `All checks passed!` |
| `make eval` | 1/6 specs scored, enforcement coverage 31/79, thresholds **refused** (see §4) |
| `make bundle` | `bundled 1/1 skill(s)` |
| strict lint (below) | `clean — fail=0 warn=0 pass=22 skip=0` |

```bash
python skills/deep-primer/scripts/lint.py \
  skills/deep-primer/tests/fixtures/document-ir.full.yaml \
  --concept-map skills/deep-primer/tests/fixtures/concept-map.full.yaml \
  --ledger skills/deep-primer/tests/fixtures/source-ledger.full.yaml --strict
```

If `make test` shows a different count, or the strict lint reports any `skip`, something regressed —
see §3 for why that matters more than it looks.

---

## 2. Where things stand

Registry: **79 rules** — 32 `hard_lint`, 35 `soft_critic`, 3 `model_verified`, 9 `human`.

| Stage | Status | What landed |
|---|---|---|
| A (new, "Prompt 2b") | done | IR extension (subsections, typed card rows, 3-item recall, artifact typing) + the 7 missing structural checks + registry-driven pass runner with `--strict` |
| B (Prompt 6a) | done | Discovery campaign: pure metrics, model-judged seams, `ReplayBackend` |
| G1 + G6 | done | `R-XREF-04` (adjacent anchor) and `R-ARCH-07` (`user_structure` + `Section.maps_to`) |
| C (Prompt 6) | done | Grounding loop; the R-DISC-01 firewall is now a mechanical gate |
| D (Prompt 6b) | done | Convergence guard; termination is provable |
| E (Prompt 7) | done | 6 eval specs + `eval.py` scoring all deterministic tiers |
| F (Prompt 8) | done | `--check-build`, CI path-filtering + gates, `run_manifest.py` |
| **G (live run)** | **not started — blocked in cloud** | See §5 |

`GAPS.md` has **no OPEN gap**. The only remaining `NotImplementedError` in the tree is
`scripts/research/kb.py` — a deliberate V2 deferral (Mixedbread-backed source KB).

---

## 3. The three ideas to hold before changing anything

**(a) A `skip` is not a pass.** The whole reason Stage A exists: a registry rule with no dispatched
implementation reports `status: skip`, which is non-blocking — so `lint-report.json` reads clean
while the rule goes unenforced. Six MUST rules were dark that way. Guards now in place, all of which
you should keep: `lint.py --strict` (a MUST skip is an error, wired into CI), the `coverage` block in
every lint report, `test_every_dispatched_ir_check_is_implemented`, and eval's per-tier coverage.

**(b) Determinism is load-bearing, not tidiness.** `research/discovery.py` and
`research/convergence.py` must stay pure — no clock, no randomness, no model calls, no
iteration-order dependence. Eval replays campaigns and the escalate loop's termination must be
reproducible; if either became a model call, the same draft could escalate on one run and settle on
the next. That's `R-DISC-04` / `R-CONV-02`, and the model-judged halves deliberately live in
`planner.py` instead.

**(c) Lockstep.** Never hand-edit `references/rule-registry.md` or `references/critic-prompts/*`.
Edit `references/rule-registry.yaml`, then `bash skills/deep-primer/tools/build.sh`.
`make validate` now regenerates into a temp copy and diffs, so drift fails the build.

---

## 4. Live landmines / non-obvious decisions

- **`make eval` reports FAIL for spec-01, and that is correct.** Two expected `soft_critic` rules
  (`R-ARCH-03`, `R-CARD-01`) need a judge model, so they are *not exercised*, and an unexercised
  expected rule is deliberately not a pass. The report classifies why (judge gap vs missing artifact
  vs a real silent skip) — check `not_exercised_reason` before assuming a bug.
- **Citation thresholds are deliberately still TODO.** Scored with the offline lexical backend,
  spec-01 shows recall 0.14 / precision 0.13 — those are what a *compliant* primer produces, because
  the proxy measures word overlap between a ≤15-word quote and a block `R-GROUND-01` requires to be a
  paraphrase. `propose_thresholds()` therefore **refuses** on the lexical backend. Do not write those
  numbers into `eval-rubric.yaml`; `test_rubric_thresholds_are_still_the_documented_todos` guards it.
- **spec-01 points `artifact:` at `tests/fixtures/*.full.yaml`.** That is the reference artifact until
  a real generation exists. `bundle.py` drops `tests/`, so a bundled skill reports `not_generated`
  rather than crashing (paths are existence-checked).
- **`assets/primer-template.html` must not spell its own placeholders with braces.** It once named
  `{{ blocks }}` inside its header comment, and `str.replace` injected a second copy of the whole
  document into that comment. Covered by `test_template_placeholders_are_substituted_once`.
- **SonarCloud is red on this PR — the Security half is identified and looks like a false positive.**
  Late in the session `github-advanced-security[bot]` posted the finding as an inline review comment
  (the dashboard itself was egress-blocked from the container, which is why it went undiagnosed for
  most of the run):

  > `skills/deep-primer/scripts/research/discovery.py:114` — S5332 *Clear-text protocols should not
  > be used. Using HTTP protocol is insecure. Use HTTPS instead.*

  Line 114 is `for prefix in ("https://", "http://"):` inside `normalize_url`, which strips a scheme
  prefix to canonicalize a URL for **source identity**. Nothing there opens a connection — the rule
  targets code that *uses* clear-text protocols, so this reads as a false positive. Note the
  canonicalization is deliberate and tested: `http://` and `https://` forms of one URL are treated as
  the same source (`test_cluster_merges_urls_differing_only_cosmetically`), so *removing* the
  `"http://"` literal would change dedup behaviour — mark it won't-fix in SonarCloud rather than
  "fixing" it.

  The **Reliability (C)** finding is still unidentified; no inline comment arrived for it. Both are
  visible on the dashboard from your machine. `build-validate-bundle` has been green on every commit.

---

## 5. Stage G — the one genuinely outstanding piece

A real `/deep-research` campaign + grounding run on `spec-01`. **It could not run in the web
container**: outbound egress to general hosts is refused by the network proxy (`curl
https://arxiv.org` → `CONNECT tunnel failed, 403`; the harness fetcher returns `EGRESS_BLOCKED`;
only package registries are reachable). Nothing about it is deferred by choice — it needs your
machine.

Everything it needs is in place and exercised offline against frozen artifacts:

1. **Campaign** — `planner.front_load_campaign(topic, params, snapshot_dir, backend=...)`. Pass
   `deep_research.CallableBackend(fn)` wrapping a real `/deep-research` invocation; the default
   `ReplayBackend` reads the frozen snapshot instead.
2. **Grounding** — `retrieval_loop.fetch_source_leads` / `retrieve_for_questions` with a live
   `Fetcher` (the offline default is `ReplayFetcher`), then `claim_extractor.build_ledger` →
   `corroborate` → `mark_recency`.
3. **Score** — `python skills/deep-primer/scripts/eval.py --spec spec-01-rag-chunking` with the NLI
   or Claude entailment backend (`verify/_entailment.py::resolve_backend`).
4. **Settle the TODOs** — take the proposed `citation_recall` / `citation_precision` into
   `references/eval/eval-rubric.yaml`, and `per_run_token_cap` in the registry `budgets` from the
   observed spend.

---

## 6. Suggested first actions locally

1. **Run `/code-review` over `origin/main..HEAD`.** An adversarial review workflow was launched near
   the end of the session and stopped before finishing, so Stages A–F have had **no independent
   review pass** — only my own verification as I went. That did catch six real bugs (doubled template
   render; the MD projection dropping subsection blocks; URL over-clustering in lead dedup; a
   version regex that missed lowercase names like `pgvector`; a rename counted as a structural
   reorder; cwd-dependent tests), which suggests a fresh pass is worth the time.
2. Open the SonarCloud dashboard and settle the red gate (§4).
3. If you want the eval to mean something, do Stage G (§5) — until then the model_verified tier is
   scored by a proxy that cannot support a threshold.
4. Optional: `scripts/research/kb.py` (V2 Mixedbread KB) is the only stub left.

---

## 7. Map of what was added

```
scripts/
  run_manifest.py          phase ledger; resume_from() = first INCOMPLETE phase
  eval.py                  spec scoring, per-tier coverage, threshold refusal
  research/
    discovery.py           pure: clustering, support, novelty, saturation
    planner.py             model-judged seams + campaign cascade + convergence driver
    deep_research.py       Backend protocol, ReplayBackend, snapshot freezing
    retrieval_loop.py      Document (the only thing a claim may anchor to), bounded loop
    claim_extractor.py     anchor_claims = the firewall gate; corroborate/mark_recency
    coverage.py            covered/thin/open + non-vendor perf corroboration
    recency.py             version sweep, flag-only without a lookup
    convergence.py         pure: tau, struct_distance, clustering, trajectory
    curate.py              ledger -> concept-map + outline seed (G1/G6 land here)
  checks/                  discovery.py, convergence.py, ledger.py + 7 new structural checks
tests/                     test_discovery, test_grounding, test_convergence, test_eval (+ additions)
tests/fixtures/            *.full.yaml reference artifact; discovery-snapshot/ frozen reports
```

Entry points worth knowing: `lint.py` exposes `run_lint` (IR) plus `run_html_pass`,
`run_ledger_pass`, `run_convergence_pass`, `run_llm_md_pass` — one per `check.input` tag.
