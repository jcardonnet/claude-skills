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
| `make test` | `314 passed, 0 skipped` |
| `make validate` | `OK — 1 skill(s) valid (lockstep in sync), 2 skipped` |
| `make lint` | **not reproducible; not in CI** — see §4. Was `All checks passed!` only against the container's ruff |
| `make eval` | 2/6 specs scored, enforcement coverage **79/79 (100%)**, thresholds **refused** (see §4) |
| `eval.py --strict` | exit **0** — the coverage ratchet holds (§8) |
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
| **G (live run)** | **seams built, one brief run live** | `HttpFetcher`, `ClaudeResearchBackend` and the Claude entailment backend all exist and have run against the network. What remains is a full multi-wave campaign and a generated primer. See §5 |
| H (local session) | done | Coverage ratchet (`eval.py --strict`), the critic tier's first real judge, determinism fix, Sonar security half. See §8 |

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

- **`make lint` is not reproducible, and is not in CI.** `pyproject.toml` declared `ruff>=0.5` with
  no `[tool.ruff]` config at all, so the outcome depended on whichever ruff happened to be installed:
  `All checks passed!` under the container's older narrow default, 92 findings under ruff 0.16
  (whose defaults are far broader and no longer enable `E402`, orphaning all 48 `# noqa: E402`).
  A `[tool.ruff]` block now exists in the working tree. Two things in it to check before trusting it:
  `per-file-ignores` keys on `"tests/**"`, which does **not** match this repo's tests at
  `skills/deep-primer/tests/**` — verified with `--stdin-filename`, so all nine test exemptions are
  currently inert — and `target-version = "py313"` against `requires-python = ">=3.11"`.

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

1. **Run `/code-review` over `origin/main..HEAD`.** An adversarial review workflow was launched near
   the end of the session and stopped before finishing, so Stages A–F have had **no independent
   review pass** — only my own verification as I went. That did catch six real bugs (doubled template
   render; the MD projection dropping subsection blocks; URL over-clustering in lead dedup; a
   version regex that missed lowercase names like `pgvector`; a rename counted as a structural
   reorder; cwd-dependent tests), which suggests a fresh pass is worth the time.
2. Open the SonarCloud dashboard and dismiss the 16 remaining vulnerabilities (§4). The code half is
   done; nothing else can move that gate without a Sonar login.
3. If you want the eval to mean something, do Stage G (§5) — until then the model_verified tier is
   scored by a proxy that cannot support a threshold. The grounding half is now live-capable; what
   remains is a real campaign `Backend`.
4. **Raise the `soft_critic` coverage floor.** `eval-rubric.yaml`'s `coverage_floor` is a ratchet
   pinned to what the offline run actually achieves. The critic tier can now be judged for real
   (§8), so once a critic report is committed as a spec artifact, that floor should rise with it —
   the ratchet is only worth anything if it is tightened after each genuine gain.
5. Decide what the `human` tier *is*. All 9 rules are unexercised, including the five `MUST_NOT`
   `R-REJECT-*` criteria. Either they are a checklist someone actually runs at review time — in
   which case they need a slot in the workflow — or they are aspirational and should say so.
6. Consider whether 79 rules is the right number. 32/79 have ever been exercised and the largest
   tier sat at 6% until this session. Some rules may be better retired than implemented;
   `evidence-map.md` is where to test which have earned their place.
7. Optional: `scripts/research/kb.py` (V2 Mixedbread KB) is the only stub left.

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
`run_critics --judge claude` replaces the hardcoded `StubJudge`. The committed run is 114 haiku
judgements, $5.15, `pass=51 fail=16 unstable=6 error=0`, frozen at
`tests/fixtures/critic-report.full.json` and wired into spec-01 — frozen for the same reason the
discovery snapshot is, so eval scores the same verdicts every time.

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
committed report is now that tiered run** — 113 calls, $17.85, `pass=56 fail=16 unstable=1 error=0`.
Unstable 6 → 1 is the whole point.

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
**`make test` is now 314 passed, 0 skipped.**

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
`make eval` reports **2/6 scored**.

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

**What the ratchet now pins:** `hard_lint: 32`, `model_verified: 3`, `soft_critic: 35`, `human: 9` — **79/79, every rule in the registry exercised.**

`R-CONV-01` was the last one dark, and it was NOT closed by handing `run_convergence_loop` the `ScriptedStructureJudge` — that replays findings it was told in advance, which is the stub-critic problem wearing a third hat. `research/claude_structure_judge.py` is a real `StructureJudge`, and it splits the work exactly the way R-CONV-02 states: the model decides whether a finding is structural and WHICH edit it implies (named as an operation over concept ids), while merge/split/rename are applied here deterministically. Letting a model emit a whole ConceptMap would hand it the deterministic half too and make `Delta_struct` a function of how verbose the model felt. Run against spec-02's real concept map it judged the two concepts structurally sound, so the loop terminated `coherent` through the documented no-further-finding exit — one genuine judgement, $0.06.

The `human` tier went 0/9 to 9/9 without a review pass, because it was never a review tier. Read together, not one of the nine is about a generated primer: `R-REJECT-01..05` are prohibitions on the pipeline's own design (no E-Prime, no surprisal target, no MECE gate, no RST auto-restructure, critics never score holistically) and `R-PROJ-01`/`R-CONV-02`/`R-DISC-01`/`R-DISC-04` are architecture invariants about what is deterministic versus model-judged. All nine are assertions about THIS CODEBASE, so `checks/conformance.py` checks them against the source tree — AST purity analysis, a holistic-question sweep over the generated prompts, renderer signatures, and the firewall asserted by running it. `R-REJECT-05` makes the point: its directive calls itself "the primary guard" and it was already enforced by `_validate_verdict`; the registry just never said so.

The registry still classifies them `human` — reclassifying is yours, and the pass deliberately does not route through `run_artifact_pass` (which filters to `hard_lint`), so the rules bind either way. Every check carries a NEGATIVE test proving it fails on a violating tree; 9/9 on a clean repo is otherwise indistinguishable from nine tautologies, which is the trap this project has now fallen into twice.

G10 is resolved (R-DISC-02 scoped to the breadth wave), which unblocked wiring the campaign artifacts into eval: the discovery passes had existed since Stage B but no spec had ever handed them an artifact, so R-DISC-02/03/05/06 sat permanently in the "needs a campaign artifact" bucket. The only deterministic rule still dark is **R-CONV-01**, and deliberately so — `run_convergence_loop` would emit a valid-looking log driven by a stub judge that never looked at anything, which is the stub-critic problem wearing a different hat. It needs a real drafting loop. The other nine are the `human` tier, which needs a person, not a script.
The five dark `hard_lint` rules are the DISC/CONV pair that needs Stage G artifacts; the nine
`human` rules need a person. Those two numbers are the honest remaining gap — 65/79.
