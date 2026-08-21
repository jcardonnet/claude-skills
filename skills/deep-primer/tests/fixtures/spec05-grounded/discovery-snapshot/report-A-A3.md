# recency-frontier — wave A (brief A-A3)

# Adaptive Clinical Trial Design: Regulatory Updates and SOTA (2025–2026)

## Regulatory Milestones

**ICH E20 Global Harmonization (June 2025).** The ICH released E20 Step 2b draft (June 25, 2025; public consultation through Nov 30, 2025) providing standardized expectations for adaptive designs across FDA, EMA, and PMDA. E20 covers interim analysis frameworks, Bayesian methodology, Type I error preservation, and integration with estimand principles. Comment overview published Feb 16, 2026; finalization expected 2026. This is the first globally harmonized adaptive guidance (3 independent regulatory sources confirm).

**FDA Bayesian Methodology Guidance (January 2026).** FDA released "Use of Bayesian Methodology in Clinical Trials" (Jan 9–12, 2026; comment deadline March 13, 2026) signaling formal acceptance of Bayesian primary inference in pivotal trials. Key requirements: pre-specification of success criteria, operating characteristics simulation, prior justification with effective sample size quantification, sensitivity analyses, and regulatory reproducibility documentation. This removes a longstanding barrier to Bayesian adaptive trials (4 independent sources confirm regulatory shift).

**FDA Master Protocols Revision (2026).** Revised draft emphasizes robust pre-specified protocols, simulation-based operating characteristics, transparent decision rules for adaptation, and continued FDA Complex Innovative Design program support for novel designs.

**FDA Real-World Evidence Policy Shift (December 2025).** FDA eliminated requirement for individually identifiable source data in RWE submissions for medical devices with intent to extend to drugs/biologics. This opens adaptive trial designs incorporating external real-world data without privacy barriers.

## State-of-the-Art Methodological Advances

**E-Values and Anytime-Valid Inference (15+ papers, 2025–2026).** E-values enable Type I error control at *any* stopping time, eliminating reliance on pre-specified monitoring schedules. Four major papers (Feb–May 2026) establish equivalence between adaptive design tools and e-value sequential tests, with practitioner guidance and automation in new `evalinger` R package (released Feb 2026). All papers explicitly align with FDA January 2026 Bayesian guidance, positioning e-values as alternative to classical group-sequential and Bayesian adaptive approaches.

**Bayesian Response-Adaptive Randomization (4 peer-reviewed papers, 2025–2026).** Thompson sampling-based dynamic arm allocation, covariate-adjusted allocation, cluster randomized trials, and unified Bayesian frameworks now enable allocation skewed to superior arms while maintaining statistical rigor. ICH E20 and FDA Bayesian guidance acknowledge BAR as valid adaptive tool.

**Seamless Phase II/III Designs (Oncology).** Two-in-1 adaptive designs combining dose selection with confirmatory analysis via surrogate endpoints (ORR, PFS) now routine, eliminating traditional 6–12 month inter-phase gaps. Covariate-adaptive randomization and flexible sample size adaptation enable model-robust inference.

**AI/Machine Learning Operational Deployment (2025–2026).** AI moved from experimental to operational use. PhaseV (Series A $50M, Feb 2026) platforms adaptive protocol optimization with 40+ global pharma sponsors. ClinicalReTrial Framework achieves 83.3% success improvement (+5.7% avg. success probability). Outcome prediction models (SPOT, TransTab, MediTab) enable endpoint selection, sample size optimization, and patient stratification.

**Platform Trial Expansion Beyond COVID-19.** Adaptive platform designs now standard in traumatic brain injury, ALS (HEALEY Platform Trial), and cardiovascular disease—formerly COVID-exclusive designs becoming mainstream across chronic and rare disease development.

## Tool Releases and Versions (2025–2026)

**R Ecosystem.** rpact 4.4.0 (March 4, 2026); adoptr 1.1.2 (May 3, 2026); adaptr 1.5.0; EValue (May 7, 2026); evalinger (new Feb 2026, GitHub release; accompanies arXiv 2602.06379). CRAN Task View: Clinical Trial Design updated June 10, 2026 with curated packages across adaptive designs, dose-finding, group sequential, and randomization.

**Python Packages.** adaptivetesting (2025, PyPI/conda-forge) for Bayesian Computerized Adaptive Testing; ADOpy (actively maintained on PyPI/GitHub); clintrials (active development, GitHub brockk/clintrials).

## Deprecated Approaches and Tightened Constraints

**Eliminated.** FDA requirement for individually identifiable patient data in RWE submissions (Dec 2025).

**Superseded.** Pre-specified monitoring schedules requirement replaced by anytime-valid e-value methodology and flexible interim analysis (ICH E20, FDA Bayesian guidance both acknowledge time-flexible interim analysis).

**Relaxed.** Prior specification constraints: FDA January 2026 guidance replaced subjective prior rejection with explicit transparency requirements (effective sample size, sensitivity analyses, robustness checks), enabling empirical and robust priors in Bayesian adaptive designs.

**Significance.** Regulatory landscape has shifted from rigid pre-specification to justified flexibility. E-values, Bayesian RAR, seamless designs, and AI/ML integration are now mainstream with formal regulatory endorsement. Global harmonization via ICH E20 reduces cross-region friction for adaptive trial sponsors. Platform designs and adaptive platforms beyond COVID demonstrate matured institutional adoption across therapeutic areas.
