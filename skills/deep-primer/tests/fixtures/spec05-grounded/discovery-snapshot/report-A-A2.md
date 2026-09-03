# debates — wave A (brief A-A2)

## Live Controversies in Adaptive Clinical Trial Design

### 1. Type I Error Control (No Consensus on Methods)
**Controversy:** Three competing alpha-spending strategies (O'Brien-Fleming, Pocock, and novel e-value approaches) are mathematically equivalent but lack guidance on which fits specific trial contexts. The ICH E20 draft (2025) acknowledges both but provides limited prescriptive rules. *Supporting sources: 4 independent* (ICH E20, arXiv anytime-valid testing, CRAN gsDesign, PMC multi-arm inflation review).

**Key disagreement:** Whether pre-specification alone controls Type I error when both sample size AND allocation change simultaneously in multi-armed trials. EMA states "strict control is a regulatory pre-requisite" but no consensus on adequate statistical penalties. *2 sources disagree on methodology.*

### 2. Frequentist vs. Bayesian Regulatory Divergence (Active Fragmentation)
**FDA 2026 Stance:** Newly permissive Bayesian guidance allows informative priors with sensitivity analysis but leaves "reasonable alternative prior" undefined. Creates tension: informative priors improve efficiency but risk masking safety signals. *Supporting sources: 3 independent* (FDA 2026 draft, arXiv regulatory commentary, Frontiers Medicine 2026).

**EMA Position:** No standalone Bayesian guidance equivalent to FDA 2026; embedded in ICH E20 with emphasis on Type I error equivalence, suggesting more conservative stance. *2 sources show EMA/FDA divergence.*

**Unresolved:** Sensitivity analysis scope sufficient for multi-region approval, external data borrowing thresholds, and whether dynamic borrowing controls Type I error under model misspecification. *4 sources identify methodological gaps.*

### 3. Sample Size Re-Estimation: Blinded vs. Unblinded (Implementation Unclear)
**Regulatory Preference:** Blinded methods favored (avoid operational bias) but unreliable nuisance parameter estimates at interim. Unblinded methods more accurate but require extensive simulation with no consensus on minimum standards. *Supporting sources: 4 independent* (Applied Clinical Trials, arXiv blinded/unblinded, crossover study, practical guidance).

**Open Problem:** No decision rules specify when efficiency gains justify operational complexity, or which outcomes (continuous/time-to-event) face highest re-estimation error. *Unresolved in all 4 sources.*

### 4. Multiplicity & Confirmatory Testing (Fundamental Semantic Gap)
**The Core Problem:** Adaptive arm/population selection changes hypotheses mid-trial. Three mathematical approaches (combination tests, conditional error functions, sample-size-increase) are equivalent but create ambiguity: Are we testing the original, revised, or intermediate hypothesis? *Supporting sources: 3 independent* (EMA guidance, ICH E20 2025, PMC conditional error functions).

**Regulatory Tension:** EMA 2007 states adaptive selection "contradicts confirmatory nature," yet ICH E20 explicitly permits adaptive enrichment—signaling a shift but leaving reporting ambiguity. *2 sources show explicit disagreement.*

**Unresolved:** How to report confidence intervals after adaptive selection without ambiguous interpretation. *Identified in 3 sources.*

### 5. Regulatory Fragmentation: FDA, EMA, ICH, Others (No Global Consensus Yet)
**Historical Gap:** FDA 2019 vs. EMA 2007 divergence (12-year gap, different prescriptiveness levels). *2 independent historical sources.*

**ICH E20 (2025) Harmonization Attempt:** Unifies FDA/EMA concepts, introduces common lexicon for prospectively planned adaptations. Draft released June 2025; finalization expected 2026. *Supporting sources: 3 independent* (ICH Step 2b, EMA comment overview, Pharmaphorum analysis).

**Remaining Fragmentation:** China NMPA, Japan PMDA, Health Canada not yet formally aligned. EMA member-state comments (Feb 2025) raise unresolved questions about flexibility compatibility with "confirmatory" claims. *2 sources indicate post-ICH divergence expected.*

**Bayesian Divergence:** FDA 2026 guidance is most permissive globally; EMA position embedded in ICH E20 without equivalent standalone document. *2 sources flag regulatory ambiguity.*

### 6. Practical Implementation Gaps: Method-Reality Disconnect
**Response Adaptive Randomization (RAR) Adoption Collapse:** Despite FDA encouragement and theoretical appeal, systematic review of 652 articles identified only 39 completed/ongoing RAR trials as of Oct 2024. Concentrated in US oncology (25%). Primary barriers are operational, not regulatory: infrastructure costs, reporting gaps (71% lack implementation details), limited software, ethical disclosure uncertainty. *Supporting sources: 4 independent* (PMC 2025 systematic review, 2024 practical challenges, rare-disease implementation, systematic scan).

**Confidence Intervals After Adaptation (Severely Underdeveloped):** After arm dropping, enrichment, or sample size changes, maximum likelihood estimators become biased and standard CIs fail to cover nominal probability. No consensus on whether to report biased (ML) or adjusted estimates. Software for adjusted CIs "relatively rare" despite acknowledged importance. *Supporting sources: 4 independent* (PMC methodological review 2025, point estimation 2021, case study 2024, multi-hypothesis communication 2026).

**External Data Borrowing (Unmeasured Temporal Confounding):** Regulators approve external controls under vague "specific conditions." No structured sensitivity analysis template. Unresolved: How much borrowing is safe? Does dynamic borrowing control Type I error under model misspecification? How to prevent secular trend bias? *Supporting sources: 3 independent* (2024 practical framework, 2025 scoping review, 2025 Wasserstein ambiguity sets).

**Data Monitoring Committees (Operational Bias Vulnerability):** FDA 2024 draft guidance emphasizes specialized statisticians but few sites have access, no standardized training exists. Guidance provides principles (independence required) but not procedures (how to decide equivocal interim results). *Supporting sources: 2 independent* (Icon/FDA DMC analysis, Oxford biometrics changing interim monitoring).

### Core Tension
Adaptive designs trade prospective complexity for efficiency gains. Regulatory frameworks require pre-specification and operating characteristics evaluation, but: (1) pre-specification is incomplete—real scenarios remain unantici­pated, (2) simulations explore finite scenarios; worst-case behavior unknown, (3) full documentation is lengthy and hard to independently verify. ICH E20 harmonizes framing (expected 2026 final) but will not resolve underlying methodological debates.
