# HANDOFF — resuming deep-primer work in a local session

Written at the end of a Claude Code **web** session that implemented `PLAN.md` Stages A–F, and
extended by three local sessions since (§8, §9, §10). Branch **`claude/deep-primer-skill-review-n3egin`**,
PR **#1** (draft), 46 commits on `f80ff65` / 70 ahead of `main`. Read `PLAN.md` for the full
stage-by-stage rationale; this file is the what-you-need-to-start. **§1 is the current state; §10 is
the most recent work.**

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
| `make test` | `525 passed, 0 skipped` (~2m20s; longer if `make eval` runs alongside it) |
| `make validate` | `OK — 1 skill(s) valid (lockstep in sync), 2 skipped` |
| `make lint` | **144 errors** — the baseline moved from 136 as the research path grew. 58 of the 144 are `unused-noqa`, i.e. ruff disagreeing with suppressions rather than finding defects. It is ruff over `scripts/`, `tests/` and repo `tests/`, with `tools/` deliberately excluded (see the Makefile comment). Not in CI. A number *above* 144 is the signal |
| `make eval` | **6/6 specs scored**, enforcement coverage **79/79 (100%)** — every tier at 100%: hard_lint 32/32, model_verified 3/3, soft_critic 35/35, human 9/9. Thresholds still **refused** on the lexical proxy (see §4). Exit **0** without `--strict` |
| `eval.py --strict` | exit **1**, and since the five-spec judgement it is red on **all six specs**, not two — see §10. Every reason is critic-side: `lint fail=0 warn=0` on all six (spec-06 `warn=1`), and no spec reports `blocking lint failure`. The documented set is 13 MUST rules headed by `R-SUMM-01` (6/6) and `R-ARCH-01` (5/6), plus spec-02's composition **and** spine failures under `primer_type=frontier` (**GAPS G13**, red on purpose). A *deterministic* failure — a `blocking lint failure` line, or a lint `fail>0` — is the regression signal now |
| `make bundle` | `deep-primer: 88 files -> dist/deep-primer, bundled 1/1` |
| strict lint (below) | `clean — fail=0 warn=0 pass=22 skip=0`, exit 0 |

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
| **G (live run)** | **seams built, one brief run live** | `HttpFetcher`, `ClaudeResearchBackend` and the Claude entailment backend all exist and have run against the network. What remains is a full multi-wave campaign and a generated primer. See §5 |
| H (local session) | done | Coverage ratchet (`eval.py --strict`), the critic tier's first real judge, determinism fix, Sonar security half. See §8 |
| **H2 (second local session)** | **done** | Two adversarial review rounds (55 findings), the artifact fixes for `R-ARCH-01`/`R-EVID-01`, and the re-judge that took coverage 46/79 → **79/79**. Opened G14. See §9 |
| **H3 (third local session)** | **done** | Four real grounding campaigns (specs 03–06), a model-backed claim extractor and campaign driver, G13's per-type composition route, G14 resolved, G15/G16/G17/G18 opened, the wall gate at fetch, and the five-spec critic judgement that ended 44% of the registry resting on one document. See §10 |

`GAPS.md` is the live list and it has moved twice since this paragraph first said "two OPEN gaps".
**G13 and G14 are both settled** — G13 as an implemented route (a per-`primer_type` composition cap
paired with a spine floor; spec-02 is still red under it, on purpose), G14 as a control decision
(the first verdict gates, the retest is recorded as a flake measurement). **What is open now is
G15(a), G16, G17 classes 2–3, and what G18 found.** Each is the same shape — a seam with no live
supplier, or a measurement that had only ever run on one document — and none is cleared by spending
alone. Read them before touching a reference artifact; §10 is the narrative. (G11 and G12 are
RESOLVED; see §8.)

The only remaining `NotImplementedError` in the tree is `scripts/research/kb.py` — a deliberate V2
deferral (Mixedbread-backed source KB).

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

**(d) A test that cannot fail is a skip in disguise.** (a) is about rules that never run; this is the
same failure in the test suite. `test_outline_seed_assignment_is_deterministic` asserted
`f(x) == f(x)` — it could only ever fail on global-state mutation, and was structurally blind to the
thing it was named for: set/dict iteration order over strings is stable *within* a process and
varies only across processes via `PYTHONHASHSEED`. Rewritten to run the chain in fresh interpreters
at different seeds, it failed on the first execution. `StubCurator.name_concept` fed a `frozenset`
into a `Counter` and took `most_common(2)`; short claims tie almost everywhere, and `most_common`
breaks ties by insertion order — so `canonical_term`, and therefore `concept_id`, differed run to
run. The same ledger produced different concept-maps in different processes, which is precisely the
reproducibility `R-DISC-04` / `R-CONV-02` are built on. Fixed with an explicit `(-count, key)`
tiebreak, the idiom `assign_section` and `outline_seed` already used.

---

## 4. Live landmines / non-obvious decisions

- **`make eval` reports FAIL for spec-01, but no longer for the reason written here.** It used to be
  that two expected `soft_critic` rules (`R-ARCH-03`, `R-CARD-01`) needed a judge model, so they were
  *not exercised* — and an unexercised expected rule is deliberately not a pass. Both are judged and
  passing now, and spec-01 clears its whole `expect.must_pass` list. The one thing still failing it
  is `R-SUMM-01 [lede-reranking]`, which is **GAPS G14** — judge drift across runs on byte-identical
  input, not a defect in the artifact. The `not_exercised_reason` classifier (judge gap vs missing
  artifact vs a real silent skip) is still the first thing to read before assuming a bug.
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

  **Both halves are now identified, and the framing above is wrong.** Queried from the Sonar API:
  exactly **two** gate conditions fail — `new_reliability_rating` (C, needs A) and
  `new_security_rating` (D, needs A). `new_maintainability_rating` already passes at **A**, so the
  ~70 code smells (cognitive complexity, composite assertions, unused params, the lone BLOCKER
  S3516) block nothing and can be triaged at leisure.

  **Reliability (C)** was one single BUG in the entire scan: `python:S5863` at
  `tests/test_grounding.py:353` — `assert outline_seed(cm, p) == outline_seed(cm, p)`, the same
  expression on both sides. **Fixed**, and not cosmetically: replacing it with a real cross-process
  check exposed a genuine determinism bug — see §3(d).

  **Security (D)** is set by the two **CRITICAL** `python:S4790` sha1 findings, *not* by S5332
  (MINOR — worth at most a B). All three sha1 sites now pass `usedforsecurity=False`, which declares
  the non-crypto intent **without changing the digest**, so every `source_id` already in a fixture or
  snapshot stays byte-identical. `dorny/paths-filter` is now SHA-pinned (S7637). That leaves **16
  vulnerabilities needing dashboard won't-fix**, dominated by 12× `S8707` (argparse path → `open()`
  across `lint.py`, `render_*.py`, `parse_primer.py`, `eval.py`, `validate_skill.py`) and 2× `S5332`.
  Note there are **two** S5332 sites, not one — `discovery.py:114` and `retrieval_loop.py:35`, the
  same `canonical_url` prefix-strip — and the won't-fix reasoning above holds for both.

  Rating **A** requires clearing *all* 16, so the gate stays red until someone with a Sonar login
  dismisses them. `build-validate-bundle` has been green on every commit.

- **`make lint` is reproducible now, and is still not in CI.** It used not to be: `pyproject.toml` declared `ruff>=0.5` with
  no `[tool.ruff]` config at all, so the outcome depended on whichever ruff happened to be installed:
  `All checks passed!` under the container's older narrow default, 92 findings under ruff 0.16
  (whose defaults are far broader and no longer enable `E402`, orphaning all 48 `# noqa: E402`).
  A `[tool.ruff]` block now exists. Both things this paragraph flagged for checking were real and
  are **fixed** (`49e0e08`): `per-file-ignores` keyed on `"tests/**"`, which matches nothing here —
  the tests live at `skills/deep-primer/tests/**`, so all nine exemptions were inert and the nine
  rules they name were live on every test file (145 → 136 findings once keyed on `**/tests/**`,
  exactly the nine `SLF001`); and `target-version = "py313"` against `requires-python = ">=3.11"`,
  now `py311`, which produced no finding delta but could have offered rewrites the declared floor
  cannot parse. Both are pinned by `tests/test_lint_config.py`, which asks ruff itself via
  `--stdin-filename` rather than re-implementing globset matching, and fails when either setting is
  reverted. Those pins sit at the repo root, not inside the skill: a bundled skill must not reach up
  to a repo-level file.

  `make lint` still reports **136 pre-existing findings** and is still not in CI. They are dominated
  by 52 `RUF100` (the orphaned `# noqa: E402`), 24 `PERF401`, 8 `BLE001`, 8 `C901`, 8 `UP042`. The
  target covers `skills/deep-primer/{scripts,tests}` and the repo-level `tests/`; `tools/` is
  deliberately excluded, with a comment in the Makefile saying why — `validate_skill.py` is the
  working-minimal version and `bundle.py` is a stub, and between them they carry 16 findings that
  are noise until Stage 6 rewrites both.

---

## 5. Stage G — the one genuinely outstanding piece

A real `/deep-research` campaign + grounding run on `spec-01`. **It could not run in the web
container**: outbound egress to general hosts is refused by the network proxy (`curl
https://arxiv.org` → `CONNECT tunnel failed, 403`; the harness fetcher returns `EGRESS_BLOCKED`;
only package registries are reachable). Nothing about it is deferred by choice — it needs your
machine.

Everything it needs is in place and exercised offline against frozen artifacts:

1. **Campaign** — `planner.front_load_campaign(topic, params, snapshot_dir, backend=...)`. A live
   backend now exists: `research/claude_backend.py::ClaudeResearchBackend`, satisfying the same
   `Backend` protocol `ReplayBackend` does. One brief ran end-to-end against the live network
   (4.6k-char report, 4 leads, $0.04).

   **Read this before wiring any other backend.** Probed here, `claude -p` does *not* actually
   search: `usage.server_tool_use.web_search_requests` came back **0** even with
   `--tools WebSearch,WebFetch --permission-mode bypassPermissions`. It answered from training data,
   produced plausible URLs, and when asked directly reported `"searched": true`. Asked the same
   question twice it gave two different version numbers.

   So the backend fetches every URL before returning it, and the live run justified that
   immediately — **2 of 4 leads did not survive**: one `404` (a confabulated source) and one
   robots-disallowed. `run_brief` FREEZES what a backend returns, so an unverified URL is not a bad
   lead, it is a fabrication with a permanent home, replayed as fact by every eval run afterwards.
   Dropped leads are kept with `status: "dropped"` and a reason rather than deleted — proposed-vs-
   survived is a signal about the backend, and deleting the evidence hides it.

   None of this promotes anything to provenance; that still requires `anchor_claims` finding the
   quote verbatim in a fetched document. This only ensures the pointers are real pointers.
2. **Grounding** — **done, and exercised live.** `research/http_fetcher.py::HttpFetcher` implements
   the `Fetcher` protocol: robots.txt honored, size/timeout capped, HTML→text via the already-
   declared bs4/lxml, failures recorded in `.refused` rather than raised (an unfetchable lead is not
   evidence). Verified against real hosts, including the firewall itself — a substring of the fetched
   body matches, an invented quote does not. `freeze_corpus()` writes the corpus in the exact layout
   `ReplayFetcher(corpus_dir=...)` reads, so the intended shape is **fetch live once, freeze, replay
   forever**; the roundtrip preserves `source_id` and `content_hash` byte-for-byte. Feed it to
   `fetch_source_leads` / `retrieve_for_questions`, then `claim_extractor.build_ledger` →
   `corroborate` → `mark_recency`.
3. **Score** — **the Claude backend now exists.** `verify/claude_entailment.py` supplies the
   `judge_fn` that `resolve_backend("claude")` always demanded and nothing ever provided, and
   `eval.py` takes `--backend {auto,lexical,nli,claude}` plus `--entailment-cost-cap`:

       python skills/deep-primer/scripts/eval.py --spec spec-01-rag-chunking --backend claude

4. **Settle the TODOs** — still open, but no longer unmeasurable. On spec-01 (11 calls, $0.39):

   | backend | recall | precision |
   |---|---|---|
   | lexical proxy | 0.1429 | 0.125 |
   | **claude** | **0.5714** | **0.5** |

   The proxy was understating by ~4x, exactly as §4 predicted. `propose_thresholds()` now proposes
   0.52 / 0.45 instead of refusing. **Deliberately not adopted:** the denominators are 7 factual
   statements and 8 citations, on a hand-built fixture rather than a real generation. A repo-wide
   quality floor set from that is calibration theatre. Settle it here, in Stage G, against real runs
   and more than one spec — along with `per_run_token_cap` from observed spend.

   Note this also means `--backend claude --strict` currently FAILS, correctly: the rubric demands
   0.75/0.90 and reality is 0.57/0.50. Either the primer misses the bar or the bar was never
   validated. It is the second. That was invisible before, because nothing could measure it.

---

## 6. Suggested first actions locally

1. ~~**Run `/code-review` over `origin/main..HEAD`.**~~ **Done, twice.** Two independent adversarial
   rounds: 39 confirmed findings on the branch, then 16 confirmed on my own fixes to those (5 high).
   All 55 addressed. The second round is the instructive one — it found that I had put the
   composition guard behind the lexical bypass where it could not fail, and re-stamped the critic
   digest on a circular proof. `git log f80ff65..HEAD` carries the reasoning per commit.
2. ~~Open the SonarCloud dashboard and dismiss the 16 remaining vulnerabilities (§4).~~
   **Out of scope — explicitly deprioritised.** The gate is red and stays red; nothing can move it
   without a Sonar login, and the finding in §4 reads as a false positive on inspection.
3. **Settle G13 and G14 — they are the only two things between `--strict` and exit 0.** Neither is
   an engineering task and neither is cleared by spending. **G13** asks what spec-02 is allowed to
   claim when its sources ground nothing (`ungrounded_share=1.0` against a `0.6` bound that was set
   by judgement, not principle). **G14** asks what a MUST verdict from a stochastic judge is worth,
   given one flipped across two runs on byte-identical input. `GAPS.md` states three options for
   G14; both are surfaced rather than applied, on purpose.
4. If you want the eval to mean something, do Stage G (§5) — until then the model_verified tier is
   scored by a proxy that cannot support a threshold. The grounding half is now live-capable; what
   remains is a real campaign `Backend`.
5. ~~**Raise the `soft_critic` coverage floor.**~~ **Done — it is 35, i.e. the whole tier.** A real
   judged critic report is committed as spec-01's artifact and every one of the 35 is exercised
   against it. The floor was raised to match the gain and then held there through a period when the
   honest reading was 2/35, which is the only test of a ratchet that means anything.
6. **Decide what the `human` tier *is*.** Still open, and now sharper: `checks/conformance.py` checks
   all nine against the source tree and they pass 9/9, so the tier is no longer *unexercised* — but
   the registry still files them under `human`, which says a person judges them. Either the
   conformance check is the real enforcement and they should be reclassified, or it is a proxy and
   the nine need a slot in the review workflow. Deliberately left as the maintainer's call.
7. **Consider whether 79 rules is the right number.** Every one is now exercised (79/79), so the
   question is no longer "which are implementable" but "which have earned their place" — which is
   the harder version. `evidence-map.md` is where each rule states its warrant, and it is the right
   place to test that claim rule by rule.
8. Optional: `scripts/research/kb.py` (V2 Mixedbread KB) is the only stub left.

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

---

## 8. Stage H — the local session

Framing: Stages A–F built the machinery; almost none of it had ever been pointed at reality. 48 of
79 rules had never executed once, and the largest tier — the 35 `soft_critic` rules that carry the
primer's actual quality thesis — sat at 2/35. What follows is mostly the consequence of *running*
things rather than building new ones.

**The coverage ratchet (`eval.py --strict`).** `enforcement_coverage` had been reported since
Prompt 7 and nothing had ever failed on it: measured, never gated — Stage A's hole one tier up.
`--strict` now fails on three things: a tier dropping below its `coverage_floor` in
`eval-rubric.yaml`, a deterministic rule going dark with no attributable reason, or a spec failing
for any reason other than the documented offline judge/artifact gap. That last distinction is what
makes it usable: spec-01 legitimately fails offline, so a gate keyed on `passed` would be red on
every run and would get switched off within a week. Floors are counts, not fractions — a fractional
floor weakens itself every time the registry grows. Wired into CI.

It earned its place on the first run by catching **`R-PROJ-04`** — `model_verified`, MUST, with a
verifier (`verify/chunk_selfcontained.py`) that had existed and been unit-tested since Stage A. The
eval harness simply never called it, so the rule read as unexercised forever while looking exactly
like a passing one. `model_verified` is now 3/3.

**The critic tier got a real judge, and coverage went 32/79 → 65/79 (82%).** `soft_critic` moved
**2/35 → 35/35**. `critics/claude_judge.py` implements the `Judge` seam against the local `claude`
CLI — one scoped call per (rule, block), never batched, `{pass, fail}` only, hard USD cap.
`run_critics --judge claude` replaces the hardcoded `StubJudge`. That first committed run *was* 114
haiku judgements, $5.15, `pass=51 fail=16 unstable=6 error=0`, frozen at
`tests/fixtures/critic-report.full.json` and wired into spec-01 — frozen for the same reason the
discovery snapshot is, so eval scores the same verdicts every time. It has been superseded twice
since; **§9 holds the figures for the report that ships today.**

Two safety properties: reports are stamped with which judge produced them, and `eval.py` refuses to
credit a stub report as coverage. A stub returns `pass` for all 73 pairs without reading a word, so
counting it would manufacture a green 35/35 tier — the silent-skip failure with the sign flipped,
and flattering enough to survive review.

Getting there took four attempts, and **every failure was a defect worth having found**:

1. `_view()` fed critics `text or caption`, but a card's content **is** its typed rows and a recall
   block's **is** its Q&A items — both arrived empty, and the judge duly failed `R-SUMM-04` on a card
   with *"Card block contains no text"*. Four soft_critic rules target exactly those roles.
2. A `subprocess.TimeoutExpired` nobody caught destroyed ~100 completed judgements. Failures are now
   contained per item as an explicit `error` verdict — never coerced to `pass`, because a judge that
   did not answer has not cleared the rule.
3. An absent `verdict` key was being reported as an R-REJECT-05 *contract breach*. Missing ≠
   non-binary: the first is a formatting slip (retry it), the second is the model trying to score
   holistically (stop the run). Conflating them killed a finished run over formatting.
4. `run_critics.py` runs as a script, so it exists twice — `__main__` and `critics.run_critics`. The
   exception class defined there was two classes, and the `except` never matched what was raised.
   Containment logic that was correct on paper did nothing. `critics/_errors.py` exists solely to
   give both importers the same object.

And one false FAIL that would have been read as a defect in the primer: document-level rules were
judged against the LLM-MD projection, which is *by design* a flat block-addressable surface with no
section titles. `R-SCENT-01` ("headings are predictive claims, not topic labels") therefore failed a
primer whose headings are exactly that. With `_judge_document_view` supplying the section headings it
passes, with the judge quoting them back: *"Both headings are claim-bearing statements... gist
reconstructable from headings alone."* The lesson generalises — **a rule is only as honest as the
surface it is judged on.**

**The judge, not the rules, was the unstable part — and the committed report is judge-noisy.** A
calibration sweep re-judged the 5 unstable rules on sonnet (42 calls, $8.57):

| judge | unstable | per call |
|---|---|---|
| haiku | **6/21 (29%)** | ~$0.045 |
| sonnet | **1/21 (5%)** | ~$0.20 |

29% is a coin flip on rules that *block*. Worse, sonnet **passed two items haiku scored as hard
FAILs** (`R-PROSE-01@subsum-chunk-size`, `R-PROSE-02@card-chunking`), so part of the report's 16
fails is noise rather than primer defects — the spec now carries that caveat inline, so nobody reads
those verdicts as findings. `R-XREF-04@document` was unstable under *both* models; that one is worth
looking at as a rule, not a model choice.

`run_critics --gating-model sonnet` routes MUST-priority rules to a stronger judge while leaving the
rest on haiku (80 gating calls, 33 non-gating). Gating rules already get test-retest precisely
because they block; spending the better model exactly there is the cheap half of the fix. **The
report committed at the end of that session was that tiered run** — 113 calls, $17.85,
`pass=56 fail=16 unstable=1 error=0`. Unstable 6 → 1 is the whole point. That report was later found
to have judged a *superseded* IR and has been re-judged; the shipping figures are in **§9**.

**Frozen reports now record what they judged.** `ir_sha256` is stamped into every report, and
`_tier_soft_critic` refuses to credit one whose digest no longer matches the spec's IR. This is not
theoretical: editing two sentences of the fixture silently invalidated an $18 report, with nothing
anywhere to indicate it. A stale report credited as coverage is coverage for judging a document that
no longer exists — the stub-crediting lie again, just far harder to notice.

**A determinism bug, found by fixing a test that could not fail.** See §3(d) — this is the one worth
reading.

**Live grounding.** `research/http_fetcher.py` — see §5 step 2.

**A real entailment backend.** `verify/claude_entailment.py` + `utils/claude_cli.py` — see §5 steps
3–4. `resolve_backend("claude")` had raised without a `judge_fn` since it was written and nothing in
the tree ever passed one, so *every citation number the harness has ever produced* came from the
lexical proxy. Entailment is precisely the question overlap cannot answer: does this quote support
this statement when they deliberately share few words? Failures resolve to **not supported** — a
citation the verifier could not check has not been shown to be good, and resolving it the other way
would let an outage quietly raise the score. `utils/claude_cli.py` is the one cost-capped CLI caller
both model-backed seams sit on, so subprocess handling and spend tracking cannot drift apart.

**Sonar security + reliability.** See §4.

**The prose lint had never actually run — anywhere, including CI.** `R-PROSE-01`'s native entity-grid
path needs spaCy; without it the check degrades to a warn-only fallback, and no environment had a
model. Installing one turned 6 skipped tests into 3 failures immediately. Five findings, and only
two were about the primer:

  1. **Pronominal subjects counted as new entities.** `which`, `it`, `they` are `nsubj` but are
     *given* by construction — an anaphor only means anything if its referent already appeared.
     Flagging one as "not introduced in the prior 2 sentences" inverts the rule being checked.
  2. **The no-subject fallback returned `sent.root`** — a VERB for any imperative or fragment
     (`shrink`), then compared against a set of noun lemmas it could never appear in. Guaranteed
     false break, regardless of the prose.
  3. **Toulmin label prefixes wrecked the parse.** `Qualifier:` / `Rebuttal:` are *required* by the
     schema, and spaCy read `shrinks` as a noun subject and `Rebuttal` as the subject because of
     them. Now stripped before parsing — and re-capitalised, because a sentence left starting
     lowercase derails the parse just as badly.
  4. `en_core_web_sm` still mis-parsed one sentence after all that; `en_core_web_md` gets it right.
     The check already preferred larger models, the environment just had none.
  5. With the parse finally correct, **two genuine `R-PROSE-01` breaks remained in the reference
     fixture** — prose written while the check could not run. Both fixed, minimally.

CI now installs spaCy + `en_core_web_md` (~50MB) so the native path is exercised. Deliberately not
the `[nlp]` extra, which pulls fastcoref → torch for a coref feature that is off by default.
**`make test` went to 322 passed, 0 skipped** at that point (475 today — §1).

**A real 3-wave campaign ran live, and the discovery checks had never been dispatched at all.**
11 briefs against spec-02's topic, 124 source leads, snapshot frozen. Two things fell out:

  - **`checks/discovery.py` had no entry in `lint.py`'s `_ARTIFACT_CHECKS`.** Four MUST rules
    (`R-DISC-02/03/05/06`) were implemented, tagged in the registry, and unreachable: with no
    dispatch entry `run_artifact_pass` records `skip`, and skip does not block. Stage A's failure
    one layer further out than Stage A looked. Now wired, with `run_discovery_log_pass` /
    `run_discovery_leads_pass` / `run_snapshot_pass`.
  - Dispatching them immediately failed **`R-DISC-03`**: the log recorded `max_waves=4` while the
    default wave list is three, so every unsaturated campaign reported terminal `'max_waves'` after
    3 of 4 — a label for a cap never reached. Fixed: the log now records the cap it actually ran
    under. And **`R-DISC-02`** fails on waves B and C, which is **[G10 in `GAPS.md`, now OPEN]** —
    two authored contracts disagree and picking between them is a design call, not a lint fix.

**The backend's URL verification was being thrown away — twice.** The live campaign returned 124
source leads, *every one* marked `accepted`, and **none** with a fetched title. Two seams, same
failure:

  - `StubJudge.extract_leads` rebuilt each source lead from `url` + `type` alone, so a lead the
    fetcher had marked `dropped` (404, robots-disallowed) came back with the default `accepted`.
  - `triage_leads` then re-promoted anything the judge accepted, overturning the fetch verdict a
    second time.

Both fixed: a fetch failure is a **fact**, not a judgement, so the judge may downgrade a lead but
never upgrade one the fetcher could not retrieve. Checked *before* the R-DISC-06 seed exemption on
purpose — a user seed that will not load is still not evidence. Without this a confabulated 404 is
laundered into a real source and frozen into the snapshot, which is R-DISC-01's "a lead is a
pointer, not evidence" failing at exactly the seam meant to enforce it.

**The campaign never saturated** (`novel_fraction` 0.96 → 0.90 → **1.00**), which is worth sitting
with: saturation-gated stopping assumes novelty *falls* as coverage grows. With a backend that does
not really search, each brief simply invents fresh URLs, so novelty stays pinned at 1.0 and
`R-DISC-03`'s stopping signal measures the model's willingness to confabulate rather than coverage
of a literature. Saturation only means something once the backend genuinely retrieves.

**spec-02 now has a real, grounded artifact — the eval has two data points instead of one.**
Sources found by web search, fetched over the network by `HttpFetcher`, every ledger quote verified
verbatim against the fetched body at ≤15 words. One candidate was rejected at 16 words, which is the
cap working rather than a nuisance. `tests/fixtures/spec02/` holds the IR, concept map and ledger;
`make eval` reported **2/6 scored** at that point (6/6 today — §1).

The instructive part is what scoring it revealed. It lints clean — `fail=0 warn=0 pass=22 skip=0` —
but the real entailment backend returned **recall 0.15 / precision 0.10**, against spec-01's
0.57/0.50. That number is correct and the primer was wrong: four abstracts about *line-segment
detection* and *promptable segmentation* cannot ground claims about *callouts, exploded views and
seated parts*. Those claims are synthesis from adjacent evidence, and labelling them `verified` was
over-claiming. They now carry `provenance: inferred`, which is exactly what the G4 axis and
`R-PROJ-05` exist for. **Structural compliance is not grounding**, the two tiers disagree on purpose,
and the disagreement is the signal — this is the clearest demonstration in the repo of why the
model_verified tier is not decoration.

**Not done, and why:** the 16 remaining Sonar vulnerabilities need a dashboard login — the write API
returns 401 and there is no token in the environment, in `gh secret list`, or on disk, so this one
is genuinely blocked rather than deferred. Specs 02–06 still have no artifacts: producing them means
authoring five complete compliant primers, which is the generation pipeline's job, not a fixture
edit — the eval still has exactly one data point and that remains its biggest weakness.

**Citation thresholds: SETTLED, on `verified_recall: 0.95` / `verified_precision: 0.90`.**

Getting there meant fixing the metric three times, because every early reading was measuring the
instrument rather than the primer. `inferred` blocks sat in the same denominator as `verified`
ones, so honest labelling scored identically to fabrication. Cards were compared against `""`,
since their content is typed rows and the code took `text or caption` — the same defect the critic
seam had, in a second module, now fixed once on the schema as `Block.readable_text`. And a card is
seven rows against a <=15-word quote cap, so nothing could entail the concatenation and every card
failed structurally; entailment now runs per claim-bearing ROW via `Block.entailment_units`, which
took spec-01 from 2/7 to 4/7 — the two blocks that flipped are exactly the two cards.

Final calibration (sonnet, `--entailment-votes 3`, per-unit; 3 split ballots in 32 pairs, ~9%):

| spec | verified_recall | verified_precision | inferred_share |
|---|---|---|---|
| spec-01 | 0.57 (4/7) | 0.50 | 0.00 |
| spec-02 | 0.00 (0/2) | 0.00 | 0.85 |

The floor is deliberately NOT fitted to those numbers — `min-0.05` would put the bar under the
worst artifact, a gate that cannot fail. It is set from principle: a block declaring itself
`verified` that its own citation does not entail is a defect. **Both artifacts fail it, and that is
the correct result.** spec-01 over-cites on `matrix-chunking`, `body-chunk-size` and
`toulmin-reranking` — a general quote attached to a specific claim it does not support. spec-02
labels `body-leader-breaks` and `fig-anchor` `verified` when neither entails; they belong with the
other eleven as `inferred`. Fix the artifacts, do not lower the bar.

`--strict` now gates on the verified pair. The legacy `citation_recall`/`citation_precision` stay
for the pre-partition report shape and gate nothing, because mixing declared synthesis with
claimed grounding makes no value of them meaningful.

**The artifacts were fixed rather than the bar lowered.** spec-01's `matrix-chunking`,
`body-chunk-size` and `toulmin-reranking` now carry `provenance: inferred`: a matrix's baseline
recommendation, a table-specific elaboration and a Toulmin claim/qualifier/rebuttal are synthesis
GROUNDED IN a source rather than stated by it, which is what `inferred` means. spec-02's
`body-leader-breaks` and `fig-anchor` joined its other eleven for the same reason. spec-01 keeps a
verified spine (its ledes and cards, 4/7); spec-02 has none, which is the honest verdict on a topic
whose sources did not support it.

That exposed a vacuum: `verified_recall` cannot fail for a primer that declares NOTHING verified,
so spec-02 would have passed a grounding gate by declining to claim any grounding. `max_inferred_share: 0.60` closes it — the one number here set by judgement rather than principle,
and so the one to revisit as specs accumulate.

**Two more shared-definition bugs surfaced while doing it, both the same shape as `readable_text`.**
`eval.py` carried a second `_ir_digest` whose docstring said it "mirrors run_critics._ir_digest" —
and then didn't: when the stamp moved, one copy moved and the soft_critic tier silently fell from
35 to 2. And the digest itself hashed raw file BYTES, so relabelling three provenance lines — which
the critics cannot see, since `BlockView` carries no provenance — invalidated a $17 run. It now
digests the judged SURFACE (block views + section headings), verified equal across the relabel by
digesting the pre-edit IR out of git. A comment is not a mechanism.

**What the ratchet now pins:** `hard_lint: 32`, `model_verified: 3`, `soft_critic: 35`, `human: 9` — **79/79, every rule in the registry exercised.**

`R-CONV-01` was the last one dark, and it was NOT closed by handing `run_convergence_loop` the `ScriptedStructureJudge` — that replays findings it was told in advance, which is the stub-critic problem wearing a third hat. `research/claude_structure_judge.py` is a real `StructureJudge`, and it splits the work exactly the way R-CONV-02 states: the model decides whether a finding is structural and WHICH edit it implies (named as an operation over concept ids), while merge/split/rename are applied here deterministically. Letting a model emit a whole ConceptMap would hand it the deterministic half too and make `Delta_struct` a function of how verbose the model felt. Run against spec-02's real concept map it judged the two concepts structurally sound, so the loop terminated `coherent` through the documented no-further-finding exit — one genuine judgement, $0.06.

The `human` tier went 0/9 to 9/9 without a review pass, because it was never a review tier. Read together, not one of the nine is about a generated primer: `R-REJECT-01..05` are prohibitions on the pipeline's own design (no E-Prime, no surprisal target, no MECE gate, no RST auto-restructure, critics never score holistically) and `R-PROJ-01`/`R-CONV-02`/`R-DISC-01`/`R-DISC-04` are architecture invariants about what is deterministic versus model-judged. All nine are assertions about THIS CODEBASE, so `checks/conformance.py` checks them against the source tree — AST purity analysis, a holistic-question sweep over the generated prompts, renderer signatures, and the firewall asserted by running it. `R-REJECT-05` makes the point: its directive calls itself "the primary guard" and it was already enforced by `_validate_verdict`; the registry just never said so.

The registry still classifies them `human` — reclassifying is yours, and the pass deliberately does not route through `run_artifact_pass` (which filters to `hard_lint`), so the rules bind either way. Every check carries a NEGATIVE test proving it fails on a violating tree; 9/9 on a clean repo is otherwise indistinguishable from nine tautologies, which is the trap this project has now fallen into twice.

G10 is resolved (R-DISC-02 scoped to the breadth wave), which unblocked wiring the campaign artifacts into eval: the discovery passes had existed since Stage B but no spec had ever handed them an artifact, so R-DISC-02/03/05/06 sat permanently in the "needs a campaign artifact" bucket. The only deterministic rule still dark is **R-CONV-01**, and deliberately so — `run_convergence_loop` would emit a valid-looking log driven by a stub judge that never looked at anything, which is the stub-critic problem wearing a different hat. It needs a real drafting loop. The other nine are the `human` tier, which needs a person, not a script.

---

## 9. Stage H, second local session — the re-judge, and what it cost to find out

§8's session ended believing coverage was 79/79. It was not. This session's whole content is that
one number being wrong, what it took to make it true, and the one thing it uncovered that is still
open.

**G12: the frozen report had judged a document that no longer existed.** `critic-report.full.json`
was produced against `document-ir.full.yaml` as of `49764e0`; `f80ff65` then relabelled three blocks
`verified` → `inferred` and kept the report credited by making the staleness digest blind to
provenance, on the stated grounds that critics "cannot see" it. **They can.** The document unit is
built by `render_llm_md`, which prints `provenance:` into every block heading — so three lines of
the surface every document-level critic reads were different, and provenance is precisely what
`R-EVID-01` judges. The honest reading was `soft_critic` **2/35**, total coverage **46/79**.

The tempting fix was to lower the floor from 35 to 2 and call the tier green. That is the exact
silent erosion the ratchet exists to catch, so the floor stayed and the report was re-judged.

**G11: with the report credited again, three MUST failures appeared that no gate could previously
see.** `expect.must_pass` is a spec's *curated* list of rules it wants exercised (six, for spec-01) —
not a statement about the registry's MUST set — so a critic failure on any other MUST rule was
invisible. Two were real defects and were fixed in the artifact (`c0c3477`), which is what
`eval-rubric.yaml` instructs:

  - **`R-ARCH-01`** — the primer opened on a claim, with no scope-and-decisions block. The IR now has
    a slot for one and spec-01 uses it: a place to say what the primer is *not* about.
  - **`R-EVID-01`** — `aid-reranking` / `fig-reranking` stated precise thresholds (recall@k 0.8, 100
    candidates) as flat fact under `Sources: [none yet — inferred]`, with no epistemic tag. Both are
    now tagged as the estimates they are.

Both now PASS, and so do `R-EXPERT-02`, `R-EXPERT-03` and `R-FIG-02[fig-reranking]`. **Coverage
46/79 → 79/79, every tier at 100%.**

**The re-judge itself: 119 calls, $11.89-equivalent, ~40 minutes**, haiku advisory + sonnet gating,
`pass=64 fail=12 unstable=1 error=0` — 77 scoped binary verdicts (calls exceed verdicts because
gating rules are judged twice). Installed verbatim, no hand-edits.

That is **5% more calls for 33% less spend** than the run it replaced ($17.85 → $11.89), and the
difference is the `--tools ""` default on `ClaudeCli` showing up as a number. Every `claude -p` is a
cold session re-paying the harness preamble — ~37.8k tokens with the default tool set against ~15.9k
with none — and a critic judging a block of text needs no tools. On a MAX subscription the binding
constraint is rate limit, not dollars, so this is the measurement that matters.

**G14 is what the re-judge uncovered, and it is open.** One MUST still fails on spec-01:
`R-SUMM-01 [lede-reranking]`. It is **not** an artifact defect. That block's text is byte-identical
across the two judged runs, and for a block-scoped rule the judged unit is only the block's
`readable_text` plus its metadata — so the two prompts were byte-identical too. Sonnet returned
*opposite* verdicts, each internally test-retest-**agreeing**:

> run 1 — "Complete claim about reranking's limit, not a topic announcement" → pass
> run 2 — "States a fact/limitation, not a defended claim/thesis" → fail

The test-retest control in `run_pass` is **within-run only**; it structurally cannot see drift
*between* runs. Editing the lede to chase this would be optimising against noise — it already
satisfies the rule's own written contrast pair — and would stale a fresh $11.89 run. So it is
surfaced as **G14** with three options (re-judge across sessions / treat a cross-run flip as
`unstable` / accept single-verdict gating and record the flake rate) and deliberately not applied.
Measured drift so far is 1 rule in 77 verdicts across two runs — too small a sample to pick from.

**The load-bearing claim in that diagnosis is asserted by a mechanism, not by this paragraph.**
`test_a_block_scoped_judgement_cannot_see_the_rest_of_the_document` in `test_critics.py` mutates a
*sibling* lede exactly the way the last report was staled (a `verified` → `inferred` relabel plus a
text change) and asserts the `R-SUMM-01 [lede-reranking]` instruction is byte-identical across it,
while the document-scoped `R-ARCH-01` instruction must **differ**. That second half is what stops the
test being un-failable: a `unit_text` returning `""` for everything would pass the first half alone.
Both assertions were mutation-verified to fail when they should.

**Three tests in `test_eval.py` were rewritten**, because they had been pinning the *broken* state —
"the frozen report is stale and says so", "the coverage gate reports the shortfall", "the artifact
fails on its two known critic MUSTs". Each now pins the fixed state, and the last one pins the shape
rather than the outcome: the two real failures must stay gone, and the flaky one must stay **alone**.
A fourth rule appearing there, or `R-ARCH-01`/`R-EVID-01` returning without the artifact changing,
means something moved. The staleness *guard* keeps independent coverage on synthetic fixtures where
it can still fail.

**Where that leaves `--strict`:** exit **1**, for two reasons, both recorded and both decisions
rather than bugs — **G13** (spec-02's composition bound) and **G14** (above). §1's table spells out
the exact strings; a third reason is a regression.

One footnote worth keeping: `GAPS.md` had blank lines *inside* its status table, and GFM ends a table
at the first blank line — so G11–G14 had been rendering as literal pipe-text rather than rows. Fixed
while editing it.

---

## 10. Stage H, third local session — four real campaigns, and the tier that had judged one document

Twenty-nine commits, `a225684` … `7a0f994`, all on 2026-08-19 → 2026-08-27. The one-line summary:
the skill went from **one** grounded artifact to **five**, and from **one** judged document to
**six** — and both of those moves made `eval.py --strict` *redder*, on purpose. That is the whole
character of this session. Nothing here was fixed by relaxing a bound.

### The two gaps that closed

**G14 — RESOLVED as (c)** (`a225684`). The cross-run judge flip on `R-SUMM-01` was a *control*
problem, not an artifact problem, so it was settled as one: the **first** verdict gates, and the
retest is recorded as a **flake measurement** rather than collapsing the pair to `unstable`. The
lede was not edited to make it green — see §9 for why that mattered.

**G13 — route implemented** (`424d0ac`), after being sequenced behind the four real campaigns it
needed data from. The composition guard is no longer one global `max_inferred_share`; it is an
explicit `primer_type` with two values, each carrying a **cap paired with a spine floor**. A survey
primer may infer a good deal as long as its ledes and cards are grounded; a frontier primer is held
looser on the cap (0.85) and still to a `min_spine_grounded` of 0.5. The five survey specs land at
`ungrounded_share` 0.40–0.57 with `spine_grounded` **1.0** across the board. **spec-02 still fails,
on purpose** — `ungrounded_share=1.0`, `spine_grounded=0.0`. It is the one spec with no real
campaign behind it, so it grounds nothing, and the guard says so instead of being widened until it
stops saying so.

### The four campaigns

Specs 03, 04, 05 and 06 each now have a real `campaign-run.json` (`301b61f`, `34a376d`, `7ca409e`,
`11130e8`, with re-grounding passes at `6233997`, `08d3495`, `1912684`, `30c3ec9`). Getting there
needed real machinery, not just spend: a model-backed claim extractor and campaign driver
(`97a6a37`), a model that **proposes** concept groups while the deterministic gate still **decides**
(`5a57f92`), campaign resume from frozen briefs (`5c13fff`), a retry for a lost grouping batch that
refuses to ship a degraded map (`c9abdd4`), and a rehydration fix so a resumed brief's documents come
back (`4df58e4`). **spec-01 and spec-02 are the two specs still without a campaign.**

### The four gaps that opened, in increasing order of how much they cost to close

**G15 — `R-DISC-06` had never been exercised by a real campaign** (`e8990bf`). The rule whose entire
subject is user seeds. Two bugs, both fixed with mutation-verified tests (`fa637be`): `seed_sources`
is a **top-level** spec key but `_spec_params` returned `spec["parameters"]` alone, so every campaign
ever run resolved its seeds to `[]`; and `front_load_campaign` dropped the directive half of
`route_seeds`, so an `author`/`entity` seed never set `params["seed"]` and the `B-seed` brief was
never built. The only thing that had ever produced one was a test setting `params["seed"]` by hand —
which is exactly why no test caught it. **(b) is decided and applied** (`08d3495`): spec-04's seed
was `https://example.org/hnsw-paper`, which cannot fetch, and `triage_leads` checks fetch-failure
*before* the R-DISC-06 exemption on purpose — so the rule was unfailable in the direction that
matters. It now points at the real HNSW paper (`arxiv.org/abs/1603.09320`), which was already source
#1 of spec-04's own ledger. **(a) stays open:** `planner.Judge` has exactly one implementor,
`StubJudge`, and `run_campaign` injects a model at the *structure* seam but passes no judge at the
*discovery* seam. Every real campaign has run the stub. Two visible consequences: spec-03 (143 leads)
and spec-04 (155) both carry **0 topic_leads**, and `triage` returns `accepted` for every cluster.

**G16 — no campaign has ever marked a conflict** (`26d0940`). `claim_extractor.mark_conflicts`
exists, is symmetric, and has a unit test. Nothing calls it: `run_campaign.py` imports `build_ledger`,
`corroborate` and `mark_recency`, not `mark_conflicts`. Across spec-03/04/05 — **897 claims** —
`contested` is 0 and `contradicts` is empty everywhere. Corroboration is the control that proves this
is a missing supplier rather than an agreeable corpus: the same stage sets it on 22 / 20 / 21 claims,
because `_corroborate_by_group` **does** have a live supplier. `R-DISC-06` (a MUST) grades on
`contested`, so it rests on a signal no campaign produces. GAPS names **(b)** — a cheap second pass
over the corroboration groups already computed — as the honest cheap route, recorded not applied.

**G17 — retrieval had no "is this the document?" gate** (`f3fad3f`, `7fe1ceb`, `f6e6557`), three
classes, one closed:

- **Class 1, walls — APPLIED** (`9729580`). 37 of spec-05's 131 retrieved documents were Cloudflare
  interstitials and 7 more were sub-60-word cookie notices: **34% of that corpus was not a document**,
  and six of them reached the ledger with 17 claims of the interstitial's own text (`quote: disable
  any ad blockers`) typed `primary_paper`, because `doc.source_type = doc.source_type or lead.type`
  inherits discovery's pre-fetch guess. The fix is `MIN_CONTENT_WORDS = 80` in `http_fetcher.py`,
  refused before a `Document` is constructed — and the threshold is **measured, not chosen**: across
  all 449 documents of the four committed corpora the word-count band **62–92 is empty**. Paired with
  **(d)**, `grouping.unnamed_singletons` → `curate.ungrouped_sources` →
  `campaign-run.json: grouping.stranded_sources`, which is **advisory, never a gate** (on
  `--lexical-grouping` every singleton would flag, so the signal would be meaningless).
- **Class 2, landing pages — OPEN.** The FDA adaptive-design guidance resolves to its 262-word
  landing page; EMA ICH E20 to 241. Faithfully extracted, 23 claims, all typed `standard`, all
  resolving cleanly — the primer loses the whole substance while every check stays green. Length
  cannot separate 222–262 words from a document, which is why 80 was deliberately **not** raised.
  Needs **(c)**, a model-side "is this the document you asked for?" seam.
- **Class 3, worked-example contamination — OPEN, and the hardest.** Source `8ee2ad4d` in spec-06's
  campaign is the RAGAS paper: genuine, primary, on topic, fetched in full. **8 of its 24 claims are
  about the 2023 film *Oppenheimer* and a clock tower in Vadodara** — the WikiEval passages RAGAS
  prints as worked examples of its own metrics. Every document-level signal reports green because the
  document *is* correct; the confusion is inside it, at the claim level. Nothing in the pipeline can
  see that today.

The four committed corpora are **not** retro-cleaned. The gate is a forward guarantee only, and
hand-curation is what caught all of this — which is not part of the skill's contract.

**G18 — 44% of the registry was credited from a single document** (`7a0f994`). `soft_critic` is 35 of
79 rules, and until 2026-08-27 exactly one spec declared a `critic_report`. Coverage read 35/35 and
was *correct* — `eval.py:713` unions `rules_exercised` across specs, so one report that touches every
rule saturates the tier. The number was never wrong; it was answering a weaker question than it
looked like it was answering. Specs 02–06 were judged with the real critic (haiku advisory, sonnet
gating), five concurrent runs, ~75 min: **883 calls, $111.32-equivalent** — roughly double the ~$60
implied by scaling spec-01, because the later specs are larger (spec-06 is 21 blocks, 249 calls).

| spec | calls | spend | pass | fail | err | flake | rules failed | MUST failed |
|---|---|---|---|---|---|---|---|---|
| 01\* | 119 | $11.89 | 64 | 12 | 0 | — | 12 | 1 |
| 02 | 118 | $14.31 | 57 | 15 | 1 | 3/39 | 14 | 5 |
| 03 | 146 | $18.74 | 63 | 22 | 2 | 5/48 | 20 | 7 |
| 04 | 180 | $24.56 | 83 | 18 | 3 | 6/53 | 16 | 7 |
| 05 | 190 | $22.78 | 85 | 29 | 0 | 10/65 | 20 | 9 |
| 06 | 249 | $30.91 | 111 | 33 | 1 | 6/80 | 20 | 8 |

<sub>\* pre-existing, from §9. `calls = items + gating_items`: gating items are judged twice, the
first verdict decides and the second is recorded as flake, per G14.</sub>

**Three things one document could not have shown.** (1) **`R-SUMM-01` fails 6/6.** As spec-01's lone
MUST failure it looked like judge drift; failing on every primer the skill has ever produced reframes
it as a rule/artifact mismatch, and the open question is which side is wrong. (2) **The flake rate
tracks document size** — 3/39 (7.7%) on spec-02 to 10/65 (15.4%) on spec-05 — so the figure G14
measured on spec-01 is not a constant of the judge and does not transfer. That is G18's own argument
arriving from the other direction. (3) **`R-ARCH-01` fails 5/6, and that was predicted before a call
was paid for**: `c0c3477` added a `front_matter` block to spec-01 for exactly this rule, and `grep
front_matter` finds it in no other IR. A *pass* on any of the five would have been rubber-stamping.

MUST rules failing, by how many of the six: `R-SUMM-01` 6 · `R-ARCH-01` 5 · `R-ARCH-03` 4 ·
`R-SUMM-04` 4 · `R-XREF-04` 4 · `R-PROSE-01` 3 · `R-EXPERT-01` 2 · `R-FIG-01` 2 · `R-PROSE-02` 2 ·
`R-XREF-01` 2 · `R-ART-03` 1 · `R-EVID-01` 1 · `R-RECALL-02` 1.

**One near-miss worth keeping:** `.gitignore`'s `*-report.json` glob would have swallowed all five
reports in silence. spec-01's survived it only by the accident of being named
`critic-report.full.json`. A critic report is not a transient run output — it costs real money,
`eval` replays it as the entire soft_critic tier, and it is digest-stamped so a stale one is caught
rather than trusted. The negation `!skills/deep-primer/tests/fixtures/**/critic-report.json` is now
`.gitignore` line 17.

### The sequencing trap, before you fix any of those 13 rules

Editing an IR moves its `ir_sha256`, and `eval` then refuses the critic report beside it as **stale**
— by design, so a report can never be credited to a document it did not judge. So **every artifact
fix costs a re-judge**, and a re-judge of the corpus is ~$110-equivalent. The fixes have to be
decided across all 13 rules and all 6 primers *first*, applied in one batch, then judged once. One at
a time is six re-judges. This is also why `R-ARCH-01` was deliberately left unfixed before the
judgement: fixing first would have meant judging five documents the session had just rewritten.

### Where that leaves `--strict`

Exit **1**, on all six specs. **Every reason is critic-side** — `lint fail=0 warn=0` on all six
(spec-06 `warn=1`), and no spec reports `blocking lint failure`. Note that the `expected rule(s)
FAILED` line is *not* a separate deterministic failure: it is `expected_must_pass_report["failed"]`,
the curated `expect.must_pass` subset, and every name in it also appears in the same line's `critic
MUST failure(s)`. The regression signal is now **a `blocking lint failure` line, or any lint
`fail>0`** — not the length of the critic list.

### What I would pick up next

1. **The G18 decision** — rule or artifacts, over 13 rules and 6 primers, batched into one re-judge.
   It is the one item where the corpus has already been paid for and the finding is sitting unacted on.
2. **G17 class 2 then class 3** — until those are settled, a campaign's output is not trustworthy
   without hand-curation, and hand-curation is not in the contract.
3. **G16 via option (b)**, the cheapest honest route to a `contested` signal that exists.
4. **G15(a)**, a `ClaudeDiscoveryJudge` — it changes what every grounded fixture contains, so it is
   cheaper to do before more campaigns than after.
5. **Ground spec-02**, which is what turns G13's two red lines green honestly rather than by moving a
   bound.

Still deliberately untouched, and still the maintainer's call: **reclassifying the nine `human`
rules** (`checks/conformance.py` checks all nine against the source tree and passes 9/9; the registry
still files them under `human`).
