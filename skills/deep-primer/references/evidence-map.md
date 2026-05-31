# Designing Research-Grade Technical Primers for Expert Readers
### A Cross-Disciplinary Evidence Map — Combined Edition

*This document merges two research phases. **Part I** maps the foundational, cross-disciplinary techniques for expert-primer design (progressive disclosure, inverted pyramid, layered/fractal summarization, information foraging, retrieval practice, and the figure/visualization layer). **Part II** is an evidence-graded analysis of ten additional frameworks proposed for an automated "Deep Primer" generation pipeline (RST, Minto/SCQA/MECE, Simplified Technical English, Theme-Rheme, UID, Toulmin, Cognitive Flexibility Theory, E-Prime, Google style mechanics, and the "primer-as-typed-AST" engineering vision). **Part III** is a single synthesis that audits a concrete primer design against all of it, ranks the frameworks, reconciles the cross-report empirical threads, and assesses the engineering vision. **Parts IV–V** give unified recommendations and caveats.*

*Throughout, the organizing lens is the **expert reader** — a senior practitioner moving into an adjacent technical domain — because the single most consequential finding in this whole literature (the **expertise reversal effect**) inverts much of the standard, novice-oriented instructional-design playbook.*

---

## Unified TL;DR

- **The strongest evidence converges on one architectural prescription**: an expert primer should be a layered, depth-dialable artifact whose top layer is dense gist (inverted-pyramid + Shneiderman's "overview first" + Reigeluth's epitome + Minto's answer-first), whose middle layers are chunked, labeled, single-idea blocks (Horn's Information Mapping + Carroll/Farkas layering + given-new coherence), and whose bottom layer is reference-mode lookup (Diátaxis Reference + Tufte-grade figures) — knit together by signaling cues (Mayer) and information scent (Pirolli & Card) so a satisficing skim reader (Duggan & Payne 2011) can stop at any depth and still be coherent.

- **The expertise reversal effect (Kalyuga, Ayres, Chandler & Sweller 2003) is the master boundary condition.** Techniques that help novices — heavy worked examples, redundant text+picture, exhaustive scaffolding, fully explicit guidance — measurably *hurt* experts. Primers for senior practitioners should default to "least first," elide what experts already chunk into schemas, and offer scaffolding as opt-in depth layers. The one framework whose evidence base is *strongest specifically for experts* is **Cognitive Flexibility Theory** (multiple representations of the same complex content), which is essentially the inverse design to novice scaffolding.

- **Of the ten additional frameworks, the load-bearing winners are**: Cognitive Flexibility Theory (multi-view coverage), given-new / theme-rheme ordering (Haviland & Clark 1974), Toulmin argument structure (for recommendation/tradeoff blocks), Simplified-Technical-English *structural* rules, and the condition-before-instruction rule from Google's style guide. **Flagged as overhyped or over-extended**: E-Prime (no rigorous evidence; and a "4–16× token compression" claim that turns out to be a misattribution from prompt-compression research), UID-surprisal-smoothing as an editing target, strict MECE as a quality gate, and RST-driven *automatic* rendering (parser accuracy sits at the human inter-annotator floor).

- **The "primer-as-typed-lintable-AST" engineering vision is sound at the lexical/terminological/topic-type layers** (DITA validation, STE linting, ISO-704 terminology univocity, given-new coherence checks) **but is ahead of the evidence at the discourse-relation layer**: state-of-the-art RST parsers reach only ~57–58 Full F1 against a human agreement ceiling of ~55 F1. Treat discourse-level constraints as *soft signals for human review*, never as deterministic blockers.

- **Three concrete strengthening moves for an existing field-guide-style primer** (detailed in Part III): (1) make the per-section "at-a-glance" card act as a true *advance organizer* that names the reader's existing home-domain schema before introducing new concepts; (2) replace illustrative worked examples for experts with *contrastive comparison* artifacts (expertise reversal); (3) promote cross-domain mappings out of supplementary content into the top (L1) card, because for experts the analogy is the highest-yield gist-bearing device.

---

# PART I — The Cross-Disciplinary Foundation: Five Primer-Design Functions

This part is organized by **primer-design function** rather than by source discipline, because the strongest findings are convergent: the same architectural moves are independently recommended by HCI usability research, journalism, instructional design, cognitive psychology, and information visualization. The disciplines disagree more about *why* a technique works than about *whether* it works.

Five functions structure it:

1. **Gist-bearing top layers** — ledes, cards, "at-a-glance" (the BLUF / inverted-pyramid / epitome layer).
2. **Chunked middle layers** — sections, subsections, the field-guide tier (Information Mapping, Diátaxis, minimalism, Mayer).
3. **Navigation and scent** — so a scanning expert can stop at any depth (information foraging, signaling, F/layer-cake reading, the Visual Information-Seeking Mantra).
4. **Active-recall and decision-support overlays** — recall blocks and the four operational artifacts (testing effect, checklists, decision matrices).
5. **Figures, cross-domain mappings, and epistemic-honesty layers** — Tufte layering/separation, schema activation, dual coding, fuzzy-trace gist.

Within each function: the technique, its source, the mechanism, the strongest evidence (with the empirical/craft distinction explicit), tradeoffs and especially **what changes for an expert reader**, and a concrete styleguide rule.

## 1. The gist-bearing top layer: lede, "at-a-glance" card, section summary

The lede → card → 300–500-word summary stack is a compound device combining the journalistic inverted pyramid, Reigeluth's epitome, Ausubel's advance organizer, Shneiderman's "overview first," and Reyna & Brainerd's gist trace. The convergence is strong enough to treat as the primer's load-bearing wall.

**Inverted pyramid / BLUF / 5 Ws + nut graf (journalism craft, mid-19th c.).** Put the single most important claim first; arrange subsequent paragraphs in descending importance so the reader can "cut from the bottom" without losing essential meaning. The *nut graf* is the dedicated "why this matters" beat; the *Wall Street Journal formula* opens with a concrete anecdote, then a nut graf, then thematic development. **Empirical status**: editorial craft, not formally tested, but supported indirectly by satisficing-skim evidence (Duggan & Payne 2011, *CHI '11*) — readers under time pressure read top-down until the rate of information gain drops, then skip. The failure mode is also empirical: readers literally do not read past the lede, so anything not in the first paragraph is at risk. **For experts**: the inverted pyramid is *more* effective for expert/scanning readers than for novices, because experts can extract gist from a single dense paragraph. **Rule**: "Lede-first, nut-second" — every section MUST be cuttable from the bottom; the lede MUST be a complete claim, not a teaser.

**Reigeluth's elaboration theory and the epitome / "zoom lens" (Reigeluth 1979; Reigeluth & Stein 1983).** Sequence content general-to-detailed: present an *epitome* (the smallest set of fundamental ideas of the whole subject), then progressively elaborate each, returning to the epitome between elaborations (the cognitive zoom). **Empirical status**: widely used instructional-design framework; direct support is moderate (English & Reigeluth 1996; Wilson & Cole 1992 critique). The deep claim — that a stable general schema improves assimilation of later detail — is supported by the better-evidenced advance-organizer literature. **Rule**: "Every primer is a zoom" — L1 = epitome; deeper levels are elaborations whose summarizers always return the reader to the epitome.

**Ausubel's advance organizer and Mayer's signaling/segmenting (Ausubel 1960; Mayer 2009; Luiten, Ames & Ackerson 1980 meta-analysis of 135 studies; Mayer 1979 meta-analysis).** An advance organizer is a short, abstract, conceptually-higher passage that activates and bridges to prior knowledge before new material arrives. Luiten et al. found a small but reliable facilitative effect across content areas and ability levels; Mayer's signaling principle shows cues that highlight organization reliably improve learning, and the segmenting principle shows learner-paced chunks outperform monolithic presentations. **For experts**: the effect is contingent on the learner *having* relevant prior knowledge to activate — for an expert entering an adjacent domain, the activation target is their *existing* schema in the *neighboring* domain (i.e., the cross-domain mapping). **Rule**: "The card is an advance organizer, not a teaser" — every card MUST name (a) the closest analogue in the reader's likely home domain, (b) the 3–5 anchor concepts, (c) what is genuinely new vs. merely renamed.

**Shneiderman's Visual Information-Seeking Mantra (Shneiderman 1996, "The Eyes Have It").** "Overview first, zoom and filter, details on demand." Formulated for information visualization but domain-independent. **Empirical status**: heavily cited design heuristic; usability evidence comes from interface studies, not controlled comparisons. Note: very-high-prior-knowledge users sometimes prefer "details first," consistent with expertise reversal. **Rule**: the depth dial L1→L5 *is* the mantra — L1 overview, L2–L3 zoom-and-filter, L4–L5 details-on-demand.

**Fuzzy-trace theory: gist as the durable trace (Reyna & Brainerd 1995, 2011).** Verbatim and gist traces are *encoded in parallel*; verbatim fades faster than gist. **Consequence**: what you want the expert to remember in six months is the gist (the qualitative model, the renamed analogue), not verbatim definitions; optimize the top layer for gist transmission and treat lower layers as gist-supporting verbatim that can be re-consulted. **Rule**: "Optimize the lede and card for gist, not verbatim" — paraphrase rather than parrot definitions; use analogies and contrasts; precise statements live in lower layers.

## 2. The chunked middle layers: the field-guide tier, sections, subsections

**Information Mapping (Robert E. Horn 1969).** Seven principles: chunking (small units, from Miller's 7±2), relevance (one main point per chunk), labeling (every chunk gets a meaningful label), consistency, integrated graphics, accessible detail, hierarchy. Each chunk is a *block* (single information type) assembled into a *map*. Six information types: procedure, process, principle, concept, structure, fact. **Empirical status**: large body of independent industry studies, but the underlying research has been critiqued — Kintsch & Stark reading research suggests paragraph size does *not* significantly affect comprehension, contradicting one IM claim. Treat as **mostly craft with mixed evidence**, except *labeling*, which is independently supported by Mayer's signaling principle. **For experts**: labeling and visually-separated blocks are exactly the navigation surface the layer-cake reading mode (§3) exploits. **Rule**: "One main idea per block; the label is the contract" — the label MUST predict the block content well enough that a scanning reader can skip the body and lose no gist.

**Diátaxis (Procida, 2017–present; adopters include Canonical, Cloudflare, Gatsby).** Four documentation modes — tutorial (learning), how-to (task), reference (information), explanation (understanding) — on a 2×2 grid. Core claim: mixing modes produces confused documentation. **Empirical status**: practitioner framework, widely adopted, no controlled validation; the adoption pattern is itself evidence of practitioner judgment. **For an expert primer**: the primer is dominantly *Reference + Explanation* (the two cognition modes), with light how-to overlays only in the operational artifacts. Tutorials are out of scope. **Rule**: "Tag every block by Diátaxis mode and refuse to mix modes within a block."

**Carroll's minimalism / the "Nurnberg Funnel" (Carroll 1990; Carroll et al. 1987–88; van der Meij & Carroll 1995).** Four principles: action-oriented; anchor in the real task; support error recognition and recovery; support reading to do/study/locate. Heuristic 4.1 — "slash the verbiage" — is the operational core. **Empirical status: one of the strongest empirically-supported documentation methods.** Carroll et al. (1987) found guided-exploration learners spent under half the learning time, under a third of the reading time, and committed half as many errors as users of a conventional 94-page manual. The Ginns, Hollender & Reimann (2006) meta-analysis (13 effects, n=288) found overall **d = 1.12** favoring minimalism (d = 0.89 for "slash the verbiage"; d = 0.59 for error-recovery support); van der Meij & Lazonder (1993) replicated (~50% more tasks completed). **Caveat**: nearly all studies are word-processing/software training with office workers. **For experts**: Hackos (1998) argues minimalism is *especially* suited to experts because they fill in the elided context themselves (Carroll & Rosson's "paradox of the active user"). **Rule**: "Slash the verbiage at every depth" — compress, don't expand, as you go deeper; hand verbosity to the next depth, not to padding.

**Layering / "safety-net" documentation (Farkas 1998, in Carroll Ed., *Minimalism Beyond the Nurnberg Funnel*).** Provide "clearly marked and useful reading choices, alternative channels" — the "least first" strategy: display the smallest amount that usually suffices, with mechanisms to demand more. Layering directly addresses Carroll's own caveat that minimalist learners may lack enough information to reason successfully. **For experts**: layering converts minimalism's tradeoff into a depth-dial — confident experts stay at L1–L2; less confident readers descend. **Rule**: "Every minimalist statement at depth N has a safety-net link to depth N+1."

**DITA / topic-based authoring / single-sourcing (OASIS DITA, 2004→).** Modular, reusable typed XML topics (concept/task/reference). **Empirical status**: strong ecosystem/operational benefits (consistency, reuse, multi-channel, translation savings); no controlled comparative *learning* evidence. **For a primer**: DITA's contribution is *engineering* — a discipline for keeping each block self-contained and uniquely sourced so the depth dial can be assembled by configuration. **Rule**: "Each block has exactly one source location and is referenced (not copied) into every assembly." (Expanded as a full framework in Part II §10.)

## 3. Navigation and scent: making the primer scannable for an expert who stops at any depth

This is where the strongest single body of empirical evidence sits — eye-tracking, information-foraging, and scanning research.

**Information foraging theory (Pirolli & Card 1999, *Psychological Review* 106; Pirolli 2007).** Users seeking information behave as optimal foragers maximizing relevant-information-gain per unit cost, following *information scent* — proximal cues (titles, snippets, links) imperfectly predicting distal value — and abandoning a "patch" when in-patch gain drops below the environmental average (marginal value theorem). ACT-IF / SNIF-ACT models predict scanpaths from spreading activation between query terms and proximal cues. **Empirical status**: very strong — IFT predicts observed navigation, abandonment, and "information snacking" consistently. **Implication**: every label, caption, and callout title is a scent cue evaluated against the expected value of reading further. Weak scent → abandonment; misleading scent → frustration. **Rule**: "Every navigable label is a scent cue and must be evaluated as a forecast" — labels must predict the chunk's content well enough that a skipping reader decides correctly whether to enter. (Deepened in Part II §5 and the navigation constraints there.)

**F-shaped and layer-cake reading patterns (NN/G 2006; Pernice 2017; Duggan & Payne 2011).** The F-shape (top-bar sweep → shorter second sweep → left-side vertical scan) is a *dominant* pattern on poorly-structured text, not universal (EyeQuant 2018 critique; Pernice 2017: "good design can prevent F-shape scanning"). The desired counterpart is the **layer-cake pattern**: with strong, scannable headings, users scan headings and skip body text until they hit the heading they want, then read. Duggan & Payne (2011) showed skim readers "satisfice" — read until the rate of information gain drops, then skip. **Implication**: weak headings → F-shape (waste); strong, predictive, parallel headings → layer-cake (excellent for experts). **Rule**: "Headings carry the story" — a reader should be able to read only the L1 headings and have an accurate gist of every section; subheadings must be parallel in form and predictive in content.

**Progressive disclosure (Nielsen 1995, 2006; Spillers 2004; Carroll's minimalism roots).** Defer advanced/rarely-used material to secondary views; the primary view shows only what most users need most of the time. Nielsen distinguishes *progressive* (more on request) from *staged* (forced sequence — the wizard). **Critical caveat (Nielsen 2006)**: "You must disclose everything users frequently need up front." The common failure is hiding something frequently-needed. **Rule**: "L1 is the depth at which a senior practitioner can act without descending" — if a senior reader must descend from L1 to L2 to make a routine decision, L1 has hidden something it shouldn't.

**Sticht / Redish / Guthrie: reading to do / to learn / to locate (Sticht 1985; Redish 1989; Guthrie 1988).** Sticht's distinction: "reading to do" (extract for immediate action, then forget) vs. "reading to learn" (absorb for future recall); Redish added "reading to learn to do"; Guthrie added "locating information." The classic Sticht/Mikulecky figure: ~85% of workplace reading is reading-to-do, ~15% reading-to-learn (treat as a 1970s rule of thumb, not a modern fact). **For primers**: expert use is overwhelmingly reading-to-locate and reading-to-do, with a thin reading-to-learn overlay. **Rule**: "Tag every callout with its primary reading goal" — locate/do/learn — and surface the locate-mode path explicitly (random-access TOC, label density).

**Schriver (1997) on reading sequence.** Pictures and captions first, then headings, then body — craft synthesis corroborated by NN/G eye-tracking. **Implication**: captions and figure titles bear disproportionate gist load. **Rule**: "Every figure has a complete-claim caption" — captions state the conclusion, not just a label.

## 4. Active recall and decision-support overlays

**The testing effect / retrieval practice (Roediger & Karpicke 2006, *Psychological Science* 17(3); Rowland 2014, *Psychological Bulletin* 140(6) meta-analysis; Adesope et al. 2017; Pan & Rickard 2018).** Active retrieval beats repeated study for long-term retention. Rowland's meta-analysis: **g ≈ 0.50** (medium-to-large). Roediger & Karpicke's prose-passage Experiment 1: after a 1-week delay the tested group recalled 56% of idea units vs. 42% for the additional-study group (**d = 0.83**); the tested group recalled as much after a week as the study group did after two days. Robust across ages, materials, settings. **Caveats**: learners rarely use retrieval practice spontaneously and have poor metacognitive calibration about it; the effect is most robust when initial retrieval success is ≥ 75% (Rowland 2014). **For experts**: well-established in educational contexts; transfer to expert self-study is less directly tested, but the mechanism (retrieval as an encoding event) is content-neutral. **Rule**: "Every section has a 3-question recall block, calibrated so an attentive L1-scan reader can answer ≥ 2 of 3" (hits the ≥75% threshold); questions should require *generation*, not recognition (generation effect, Slamecka & Graf 1978).

**Desirable difficulties (Bjork 1994; Bjork & Bjork 2011, 2020).** Spacing, interleaving, contextual variation, retrieval practice, and reduced feedback frequency lower immediate performance but improve long-term retention and transfer; the storage-strength vs. retrieval-strength distinction explains why re-reading *feels* like learning without producing it. **For experts**: the relevant desirable difficulty for an adjacent-domain primer is *contrastive variation* — the same concept in multiple framings (home domain, adjacent domain, a third analogue) forces re-encoding. **Boundary**: difficulty must be *desirable* — beyond the learner's threshold it stops helping, and the expert's threshold is higher than the novice's. **Rule**: "Recall blocks should force generation across at least one cross-domain mapping" — not "define X," but "in your home domain, what plays the role X plays here?"

**Gawande's checklists (Gawande 2009; Haynes et al. 2009, *NEJM*, WHO Surgical Safety Checklist).** The WHO pilot in eight hospitals: major complications fell from 11% to 7% (~one-third), inpatient deaths from 1.5% to 0.8% (>40%). Design principles: short (≤9 items per pause), action-verb-first, "killer items" only (the steps that fail most often and most consequentially), defined pause points, two-person verification. **For primers**: the *diagnostic checklist* and *failure-modes catalog* are the right artifacts; import the item-count discipline, pause-point structure, and killer-item criterion. **Rule**: "Checklists are not glossaries" — every checklist item must be (a) action-orienting and (b) high-frequency-failure; if you can't show it routinely fails, it goes elsewhere.

**Decision matrices / Pugh matrices (Pugh 1981).** Multi-criterion scoring against a datum. Empirical evidence is weak (mostly case studies), but the *cognitive* function — making criteria explicit and forcing comparison — is supported by the broader decision-aid literature (Hammond, Keeney & Raiffa 1999). **For primers**: the matrix makes comparison dimensions explicit and contrastive (itself a desirable difficulty); it is the operational complement to the cross-domain mapping. **Rule**: "Every decision matrix has named criteria, a named baseline, and a named recommendation — no 'it depends' cells without a disambiguating rule."

## 5. Figures, cross-domain mappings, epistemic-honesty layers

**Tufte's analytical-design principles (Tufte 1983, 1990, 1997, 2006).** Relevant for a figure vocabulary: maximize data-ink, erase non-data ink; *small multiples* (replicate one chart structure across a categorical variable to enable comparison); **layering and separation** (distinct elements coexist by varying value/weight/hue/transparency, with data on top, labels next, scaffolding faintest); micro/macro readings; the smallest effective difference; sparklines / word-data integration; avoid chartjunk and 3-D distortion. **Empirical status**: strong professional consensus; some claims contested — Bateman et al. (*CHI* 2010, n=20) found embellished Holmes-style charts were recalled significantly better than plain Tufte-style charts after 2–3 weeks, with interpretation accuracy not significantly different. The *layering and separation* principle is especially well-supported by Gestalt perception. **Rule**: "Data > labels > scaffolding > decoration; one accent color per page" — and "every cross-domain mapping is a small-multiple table, never a single composite figure."

**Cognitive load theory (Sweller 1988, 1994; Sweller, van Merriënboer & Paas 1998; Sweller 2010): intrinsic / extraneous / germane load.** Sub-effects: worked-example effect, split-attention effect (text and figure spatially separated → higher extraneous load), redundancy effect (text + identical narration hurts), modality effect, expertise reversal effect (below). **Critique**: the three load types are hard to measure independently (de Jong 2010; Schnotz & Kürschner 2007). Treat CLT's qualitative predictions as well-supported and its quantitative load measurements as contested. **Rule**: "Eliminate split attention — figure and its explanation are always in the same eyeshot; if not, replicate the key label inline." (Empirical anchor: Ginns 2006 spatial-contiguity meta-analysis — see the reconciliation in Part III for the exact figures.)

**The expertise reversal effect (Kalyuga, Ayres, Chandler & Sweller 2003, *Educational Psychologist* 38(1); Kalyuga 2007; Kalyuga & Renkl 2010).** Techniques that help novices reverse for experts: the worked-example advantage disappears and then inverts as expertise rises (Kalyuga et al. 2001b — problem-solving outperforms worked examples for high-prior-knowledge learners); split-attention/integration aids and dual-modality formats lose effectiveness; explicit guidance becomes redundant or harmful. Mechanism: the redundancy effect — information that scaffolds a novice's schema construction is, for an expert, redundant with stored schema and imposes ineffective working-memory load. **Empirical status**: very strong — replicated across algebra, programmable-logic-controller programming, geometry, and less-structured domains (Van Gog et al. 2011). **For primers (the master boundary condition)**: default to expert-calibrated, schema-redundancy-free presentation — (a) elide what experts already chunk; (b) prefer comparison/contrast over worked steps; (c) prefer dense gist over scaffolded build-up; (d) treat heavy explanation as opt-in deeper layers. **Rule**: "Default to expert-mode; novice scaffolding is opt-in" — the primary surface assumes the reader has the home-domain schema, and novice scaffolding lives behind explicit "if you don't have X, read Y first" gates.

**Cross-domain mappings (analogical reasoning: Gentner 1983 structure-mapping; Holyoak & Thagard 1995).** Analogy is how experts assimilate adjacent-domain content: structural correspondences (relations, not surface features) map from a familiar source to a less-familiar target. **For primers**: cross-domain mappings are the *primary gist-bearing device* for an expert reader — they activate existing schemas at the highest information value per unit cost (information-foraging argument) and install a durable gist trace (fuzzy-trace argument). **Rule**: "Cross-domain mappings are first-class content" — they belong in the L1 card, not a footnote. (This becomes strengthening flag 3 in Part III; and Cognitive Flexibility Theory in Part II §7 deepens the multi-representation case.)

**Schema activation, dual coding, modality (Paivio 1986; Mayer's modality and multimedia principles).** Information encoded both verbally and visually is better remembered. The multimedia principle: people learn better from words *and* pictures than words alone. For a written primer (no narration), the operational forms are: pair every dense conceptual claim with a diagram; keep label and graphic adjacent (spatial contiguity). **Rule**: "Every L2 card has a figure; every figure has a labeled gist."

**Epistemic-honesty layers (settled / contested / speculative).** The analogue is academic *hedging* (Hyland 1998) and clinical-evidence grading (GRADE 2004; Oxford CEBM). Gist quality depends on epistemic calibration: if the reader can't tell load-bearing facts from live debates from conjecture, the gist trace is corrupted. **Rule**: "Every claim that is not settled bears a one-word epistemic tag inline — settled/contested/speculative — and contested claims name at least one dissenting view by name." (Operationalized further by Toulmin's Qualifier/Rebuttal slots, Part II §6.)

**Hypertext theory (Nelson 1965; transclusion).** Ideas are inherently linked; documents should be navigable webs with content transcluded (referenced, not copied). **For primers**: the assembly layer for the depth dial; transclusion enforces the single-source rule (realized by DITA, Part II §10).

---

# PART II — Ten Additional Evidence-Graded Frameworks

These are the frameworks proposed for an automated "Deep Primer" generation pipeline that go *beyond* Part I. For each: origin, mechanism, evidence (with an empirical / craft / over-extension label), expert-reader boundary conditions, automated-tooling maturity (since the goal is a lintable pipeline), and concrete primer application.

**Ranked by strength-of-evidence for an expert primer** (detailed below): (1) Given-New / Theme-Rheme; (2) Cognitive Flexibility Theory; (3) Toulmin; (4) Minto/SCQA/MECE; (5) ASD-STE100 / controlled language; (6) Google condition-before-instruction; (7) RST; (8) DITA / typed authoring; (9) UID; (10) E-Prime.

## 1. Rhetorical Structure Theory (RST) — Mann & Thompson 1988

**Origin.** William C. Mann & Sandra A. Thompson, "Rhetorical Structure Theory: Toward a functional theory of text organization," *Text* 8(3): 243–281, 1988; developed at USC/ISI from ~1983 with Christian Matthiessen.

**Mechanism.** Text decomposes into **Elementary Discourse Units (EDUs)**, roughly clause-sized. Adjacent units/subtrees join by **rhetorical relations** (Elaboration, Background, Contrast, Evidence, Concession, Condition, Cause, ~16–25 relations) with a **nucleus/satellite** asymmetry: the nucleus is the load-bearing claim; the satellite is supporting material that could in principle be collapsed.

**Empirical status.** Primarily a **descriptive theory**, not an intervention. No controlled study shows that "writing in good RST form" improves comprehension per se; RST is used to *describe* coherent vs. incoherent text and as a feature in downstream NLP (summarization, coherence ranking). Label: *descriptive theory + downstream NLP utility — not a validated reading intervention.*

**Automated parser maturity (the load-bearing question).** On RST-DT with original Parseval (Morey, Muller & Asher 2017), the **human inter-annotator agreement ceiling** is approximately: Span 78.7 F1, Nuclearity 66.8, Relation 57.1, **Full (labeled) 55.0**. State of the art:
- EDU **segmentation** is essentially solved (DMRST+ToNy ~97.9 F1; human ceiling ~98.3).
- **DMRST** (Liu, Shi & Chen, CODI 2021) end-to-end ~50.1 Full F1.
- **Kobayashi et al. 2022** (bottom-up + DeBERTa) 55.4 Full F1.
- **Maekawa et al. 2024** (arXiv:2403.05065; Llama-2-70B + QLoRA, bottom-up) ~57–58 Full F1 — current SOTA.
- **RST-LoRA** (Liu et al. 2024, arXiv:2405.00657) injects RST relation uncertainties as soft features into a LoRA-tuned long-document summarizer — it does not produce parses.

**Critical conclusion.** SOTA full-relation parsing sits *at or barely above the human agreement floor*. Two competent annotators agree on the full labeled tree only ~55% of the time. **You cannot use RST parser output to deterministically drive UI decisions** (e.g., "if this EDU is an Elaboration satellite, auto-collapse it into a toggle"). Use it as a *soft* feature: rank candidate paragraphs by satellite-density, surface high-nuclearity sentences as TL;DR candidates, use it as a reranker — but do not let it gate rendering.

**Tooling.** DMRST (open source, six languages), isanlp_rst, Feng-Hirst shift-reduce, RSTFinder/ETS.

**Primer application.** Lint *signal* for: imbalanced satellite/nucleus ratios in long sections; argument-without-evidence patterns (Elaboration-heavy, no Evidence relations); ranking sentences for an executive summary. **Do not auto-collapse.**

## 2. Minto Pyramid Principle and SCQA / MECE — Barbara Minto, 1987

**Origin.** Barbara Minto, *The Pyramid Principle: Logic in Writing and Thinking* (1978/1987); developed at McKinsey from 1963.

**Mechanism.** Answer/conclusion at the top, supported vertically by Q&A scaffolding (the **SCQA** opener — Situation, Complication, Question, Answer — sets up the governing question) and horizontally by **MECE** (Mutually Exclusive, Collectively Exhaustive) groups. Each parent summarizes its children; each child set answers the question its parent raises.

**Empirical status.** **Essentially no peer-reviewed empirical evidence** — consulting craft refined over 60+ years. Its tenets (answer first, group related ideas, summarize upward) converge with BLUF/inverted-pyramid (which *does* have NN/G and journalism evidence) and with CLT chunking. Label: *practitioner craft + convergent indirect evidence.* (Nenkova & Passonneau's "Pyramid Method" for summarization evaluation, HLT-NAACL 2004, borrows the name only.)

**Expert-reader fit.** Strong: senior engineers want the answer first, then drill only into the children whose parent claims they doubt — exactly what Minto's vertical Q&A enables. MECE is most useful when readers are *evaluating completeness* (a frequent expert mode); least useful for narrative/conceptual material where overlap is unavoidable. **Do not make strict MECE a quality gate** (see synthesis).

**Tooling.** None directly. Structural lints can enforce: leading paragraph contains a one-sentence answer; each heading is a complete claim or question; each top-level child group has ≤ 7 items.

**Primer application.** Make the **first paragraph of every primer a complete SCQA + Answer**; make each major heading a declarative claim or question (not a topic label); for decision/tradeoff sections, MECE-partition the option space (a lint can flag overlapping options via embedding similarity).

## 3. ASD-STE100 Simplified Technical English + ISO 704 Terminology

**Origin.** Developed by AECMA (now ASD) from 1983; currently **ASD-STE100 Issue 9 (Jan 15, 2025)**, an international Standard. ISO 704 ("Terminology work — Principles and methods") supplies the terminology-science substrate.

**Mechanism — verified numbers from Issue 9 (asd-ste100.org / STEMG):** 53 writing rules in 9 sections; ~900 approved words (with ~1,200 unapproved alternatives listed); **max procedural sentence 20 words**; **max descriptive sentence 25 words**; **max noun cluster 3 nouns** (Rule 2.1; articles/prepositions don't count); **max descriptive paragraph 6 sentences**; core lexical principle "one word, one part of speech, one meaning" (e.g., "test" is a noun only; "follow" means "come after," not "obey"); verbs restricted to simple tenses, no -ing participles except approved nouns/adjectives, passive forbidden in procedures. **ISO 704** complements: each concept has one designation (univocity), concept systems organized by generic/partitive/associative relations, definitions giving necessary-and-sufficient characteristics.

**Empirical status.** Shubert, Spyridakis, Holmback & Coney (1995), "The Comprehensibility of Simplified English in Procedures," *Technical Communication* 42(3): using Simplified English **significantly improves comprehensibility of more complex documents**, with non-native readers benefiting more than native speakers. Beyond this, industrial evidence is solid but largely *operational* (translation cost ↓, maintenance error rate ↓). Label: *practitioner-strong; comprehension gains best supported for non-native readers and safety-critical procedures, not expert L1 readers reading explanatory prose.* **Expertise-reversal risk**: a senior engineer doesn't need "make sure" instead of "verify/confirm/ensure"; the ~900-word dictionary can flatten technical nuance.

**Tooling maturity.** Mature: Acrolinx, Congree, HyperSTE (Etteplan), Boeing Simplified English Checker, TechScribe term checker. Checkers reliably handle sentence length, noun-cluster length, passive detection, approved-word lookups, verb forms; they explicitly *cannot* check semantic rules ("is the first sentence the topic sentence?").

**Primer application.** Adopt STE's **structural rules** (sentence ≤ 25 desc / ≤ 20 proc, noun cluster ≤ 3, paragraph ≤ 6, condition-first procedures) and **terminology univocity** (one term per concept, glossary-enforced). **Do not** adopt the full ~900-word dictionary — it's calibrated for non-native maintenance technicians. Use a hybrid: STE-style structure lints + project-specific approved terminology + free vocabulary for explanatory prose.

## 4. Theme-Rheme and Given-New — Halliday; Haviland & Clark 1974

**Origin.** Theme-Rheme: Prague School (Mathesius, Firbas), systematized in Halliday's Systemic Functional Linguistics. Given-New contract: Haviland & Clark, "What's new? Acquiring new information as a process in comprehension," *Journal of Verbal Learning and Verbal Behavior* 13: 512–521 (1974); Clark & Haviland (1977).

**Mechanism.** Writers mark what the reader is presumed to know (Given) and what is novel (New). The Given-New Strategy: identify Given content, find its antecedent in memory, attach the New content to it. Sentence-initial position tends to carry Given/Theme; sentence-final position carries New/Rheme. Coherence rests on chaining — each sentence's Given hooks to a previous sentence's New.

**Empirical status.** Robust and replicated. Haviland & Clark 1974: comprehension times shorter when the antecedent of a definite expression was explicitly mentioned. Vande Kopple (1982) extended to natural expository paragraphs with reading-time and recall advantages. Barzilay & Lapata's **entity-grid model** ("Modeling Local Coherence: An Entity-Based Approach," *Computational Linguistics* 34(1), 2008) operationalized local coherence as entity-transition patterns and performed strongly on sentence-ordering, summary-coherence, and readability; neural extensions (Nguyen & Joty 2017) validated it further. Label: *load-bearing empirical finding + computationally measurable.*

**Expert-reader fit.** Excellent, and *improves* with expertise: the more domain entities a reader knows, the more given-new chaining accelerates comprehension. Violations (every sentence's subject introduces a wholly new entity) are the textbook signature of "choppy" technical prose.

**Tooling.** spaCy/Stanza dependency parsing + coreference resolvers (fastcoref, AllenNLP coref) + entity-grid implementations. Reliable and deterministic enough to lint.

**Primer application.** A coherence lint that builds an entity grid per section, flags sentences whose subject entity is absent from the previous two sentences, and flags paragraphs where every sentence introduces a new subject entity. Also: section openings should restate the prior section's terminal entity (cross-section theme-rheme chaining).

## 5. Uniform Information Density (UID) — Levy & Jaeger 2007; Jaeger 2010

**Origin.** Levy & Jaeger, "Speakers optimize information density through syntactic reduction," NIPS 2006/2007; Jaeger, "Redundancy and reduction: Speakers manage syntactic information density," *Cognitive Psychology* 61(1): 23–62, 2010; predecessor Genzel & Charniak (2002), "Entropy rate constancy in text," ACL.

**Mechanism (precise).** UID is a **production-side** hypothesis: *speakers* prefer to distribute information density (surprisal under a probabilistic LM) uniformly across an utterance, avoiding spikes (exceed processing capacity) and troughs (under-use channel capacity), via choices among alternative encodings (omit "that," contract auxiliaries, choose syntactic variants).

**Empirical status — and the over-extension warning.**
- **Strong, replicated**: speakers' encoding choices (contraction, optional "that" omission, syntactic reduction) are predicted by local surprisal (Jaeger 2010; Frank & Jaeger 2008; Mahowald et al. 2013).
- **Weaker but plausible**: non-uniform information density correlates with lower *acceptability judgments* (Meister et al., "Revisiting the Uniform Information Density Hypothesis," EMNLP 2021).
- **Mixed / not directly supportive**: reading time predicted by UID per se — Meister et al. 2021 find effects "consistent with a weakly super-linear effect of surprisal," far weaker than "smoothing surprisal improves comprehension."
- **No controlled study** shows that *editing a document to smooth GPT-2 surprisal* improves reader comprehension or retention.

Label: *theory being over-extended when applied as a document-editing intervention.* Using LM per-token surprisal to flag "dense" passages may be a useful *heuristic* for finding revision candidates, but presenting smoothness as an evidence-based reading rule is unjustified.

**Tooling.** Trivial to compute (per-token log-probability under any LM). The interpretive scaffolding is the problem, not the math.

**Primer application.** Use surprisal as a **diagnostic heuristic only**: spikes are *candidates* for human review (often they flag undefined jargon, missing context, or genuinely dense reasoning). Do not auto-edit; do not treat smoothness as a quality target.

## 6. Toulmin Argument Model — Toulmin 1958

**Origin.** Stephen Toulmin, *The Uses of Argument*, Cambridge University Press, 1958.

**Mechanism.** Six functional components: **Claim** (conclusion), **Data/Grounds** (evidence), **Warrant** (the inference rule licensing Data → Claim), **Backing** (support for the warrant), **Qualifier** (claim strength — "presumably," "in most cases"), **Rebuttal** (conditions under which the claim fails).

**Empirical status.** Strong evidence from writing pedagogy that explicit Toulmin instruction improves measured *argument quality* (e.g., Yang & Pan 2023, *SAGE Open* 13, pre/post-test gains across argumentative elements; Crossley and colleagues show argument-feature density predicts human essay-quality ratings). Weaker evidence that it improves *reader comprehension*. Reliability caveat: Sampson & Clark (2008), Kunnan (2010) document inter-rater unreliability in classifying argument elements (claim vs. warrant vs. qualifier blur). Label: *practitioner-strong + moderate empirical for writing quality; classification reliability shakier.*

**Expert-reader fit.** Excellent — senior engineers reading design-recommendation/RFC documents specifically want the **Qualifier** and **Rebuttal** ("how strong is your confidence?", "under what conditions does this fail?"). These are precisely the expert's questions.

**Tooling.** Argument mining is moderately mature; LLM-based component classification works adequately for Claim-vs-Premise but degrades on Warrant/Backing distinctions (expect ~70–80% agreement at best).

**Primer application.** For every **recommendation, design tradeoff, or superiority claim**, enforce a six-slot block: Claim, Data (benchmark/citation/measurement), Warrant, Backing (assumptions/conditions), Qualifier (strength — "in most production workloads," "for sequence lengths ≤ X"), Rebuttal (known failure modes). Make these *typed* blocks in the AST. This also operationalizes the epistemic-honesty layer from Part I §5.

## 7. Cognitive Flexibility Theory (CFT) — Spiro et al. 1988–1992

**Origin.** Rand Spiro, Paul Feltovich, Richard Coulson, Michael Jacobson and colleagues, 1988 (Cognitive Science Society) through 1991–92 (esp. in Duffy & Jonassen's *Constructivism and the Technology of Instruction*, 1992).

**Mechanism.** For **ill-structured domains** (medicine, law, complex engineering) and **advanced knowledge acquisition** — the regime where senior engineers operate — single mental models and tidy schemas *cause* misconceptions through "reductive bias" and "knowledge shielding." The remedy is to **criss-cross the landscape**: revisit the same concept through multiple representations, multiple cases, multiple lenses, deliberately resisting oversimplification. Hypertext is its native medium.

**Empirical status.** Genuine empirical work, mostly in medical education (Jonassen, Ambruso & Olesen 1992, transfusion medicine; Feltovich et al. on cardiovascular concepts). The keystone study is Jacobson & Spiro (1995), "Hypertext Learning Environments, Cognitive Flexibility, and the Transfer of Complex Knowledge: An Empirical Investigation," *Journal of Educational Computing Research* 12(2): the hypertext (multi-representation) group showed superior *transfer* while the control group showed higher *factual recall* — directly confirming that reductive single-model instruction produces brittle knowledge that recalls well but transfers poorly. Label: *empirically supported specifically for advanced/expert learning in ill-structured domains.*

**Expert-reader fit. This is the single framework on the list whose evidence base is strongest *for* experts.** Novices may genuinely benefit from one simplified model first; experts need multiple views. It is the principled inverse of novice scaffolding and the deepest framework here for an expert primer.

**Tooling.** None directly. A structural lint can enforce: "for every core concept, the primer must include ≥ N representations from a distinct view set {architecture diagram, tradeoff table, failure taxonomy, benchmark, cost model, code example, mental model, historical analogue}."

**Primer application.** Treat every primary concept as a **multi-view block**: do not present "X is Y" as a single canonical definition; require an architecture view, a tradeoff/limitation view, a failure-mode view, a benchmark/quantitative view, and a code/concrete-example view. Make this the *organizing principle* of section structure, not a decoration. (This is the rigorous backing for Part I's "cross-domain mappings are first-class content" and strengthening flag 3 in Part III.)

## 8. E-Prime — D. David Bourland Jr., 1965 (and two claims to reject)

**Origin.** D. David Bourland Jr. (student of Korzybski), "A Linguistic Note: Writing in E-Prime," *General Semantics Bulletin* 32/33 (1965/66). Eliminates all forms of "to be" (am, is, are, was, were, be, been, being, contractions).

**Mechanism (claimed).** Forces explicit agency/process (avoiding identity statements "X is Y," which Korzybski regarded as epistemologically dangerous), prefers active verbs, makes passive constructions awkward.

**Empirical status. Essentially none.** No rigorous controlled study shows E-Prime improves technical-writing comprehension, retention, or accuracy. The occasionally-cited 2019 study (197 participants correlating "to be" frequency with irrational beliefs) is small, correlational, and about psychological beliefs, not technical comprehension. Linguists (Lakoff 1992; Murphy 1992) explicitly criticized the underlying claim that the copula causes cognitive rigidity. Label: *general-semantics philosophical craft — no rigorous evidence for technical-writing utility.*

**Two specific claims from the source documents, checked:**
1. **"Umwelt Engineering: Designing the Cognitive Worlds of Linguistic Agents," arXiv 2603.27626** — *appears to exist* as a single-author March-2026 preprint (Rodney Jehu-Appiah). Its abstract reports experiments on *LLM* reasoning under "No-Have" and "E-Prime" vocabulary constraints (claimed gains e.g. +19.1 pp ethical reasoning). **Caveats**: single-author, no clear peer review, and it experiments on *language models*, not on *human-reader comprehension of technical documents*. Its existence does not validate E-Prime for technical writing.
2. **"4–16× token compression with near-parity accuracy"** — this **does not come from E-Prime or "synthetic reasoning languages."** The numbers come from **In-Context Autoencoder (ICAE)** prompt-compression (Ge et al. 2024, ICLR — 32/64/128 learned special tokens compressing 512 natural-language tokens = the 4×–16× range) and related work (GIST tokens, Mu et al. NeurIPS 2023; LLMLingua-2, Pan et al. ACL 2024). These are *learned neural prompt compressions for LLM inference efficiency*, not a controlled natural language and not a human-reader intervention. **The source-document claim is a misattribution. Reject it and do not propagate it.**

**Primer application.** **Do not adopt E-Prime.** The bits it converges with (prefer active verbs, name agents, avoid weak copulas) are already covered by Google mechanics and STE on stronger evidence.

## 9. Google Developer Documentation Style Guide

**Origin.** Maintained by Google's developer-documentation team (developers.google.com/style); an editorial guide, not research output.

**Mechanism.** Active voice, second person ("you"), present tense, descriptive/task-based headings, and — most importantly for evidence — **condition before instruction**. Verbatim (developers.google.com/style/sentence-structure): mention the circumstance, condition, or goal before the instruction, so the reader can skip the instruction if it doesn't apply. Example: "To delete the entire document, click Delete." rather than "Click Delete if you want to delete the entire document."

**Empirical status.** The guide as a whole is editorial craft. **But the specific "condition-before-instruction" rule is supported** by adjacent working-memory / procedural-comprehension evidence (the reader holds framing context before the action) and is consistent with given-new and with STE's procedural rules. Active voice and direct address have weaker but generally positive support in plain-language / health-literacy research. Label: *editorial craft, with condition-first specifically supported.*

**Expert-reader fit.** Strong — experts scanning to find applicable steps benefit most from condition-first because they skip irrelevant blocks fastest.

**Tooling.** Vale (open-source, Google style package), Acrolinx, Microsoft Style Intelligence. Active-voice detection is reliable; descriptive-heading and condition-first detection need LLM-judge support and are less deterministic.

**Primer application.** Adopt the set as baseline house style; make **condition-first a blocking lint** on procedural sentences (the most important and most evidence-backed rule of the set).

## 10. Primer-as-Typed-Lintable-AST: DITA + Single-Sourcing + LLM Critics

**Origin.** DITA (Darwin Information Typing Architecture): originated at IBM, donated to OASIS in 2004, currently DITA 2.0 (2022); single-sourcing and topic-based authoring descend from Information Mapping (Horn 1969+) and structured writing.

**Mechanism.** Decompose a document into **typed topics** (concept, task, reference, glossary), each conforming to an XML schema; topic *shells* and *constraint modules* enforce required/optional elements; cross-references and conditional processing enable single-sourcing. Validation is hard — an XML schema validator rejects ill-formed topics deterministically.

**Empirical status.** **Strong industry evidence for production efficiency, reuse, consistency, and translation cost reduction** (e.g., Hackos/CIDM: a project with <15% new content cut translation cost from \$50,000 to \$1,500). **Weak direct evidence that DITA-authored documents yield better reader outcomes**, separate from the better content the discipline enables. Label: *strong for production quality / consistency; indirect for reader outcomes.*

**LLM-as-judge / critic-model state of the art.** Zheng et al. (2023), "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (arXiv:2306.05685): GPT-4 vs. human agreement reaches ~85% (≥ the ~81% human-human agreement) on open-ended evaluation (setup S2, w/o ties). Prometheus (Kim et al. 2024), a 13B evaluator, reports Pearson ~0.897 with humans given customized rubrics. **Known failure modes**: position bias, verbosity bias, self-preference bias, and much lower agreement at the *item* level than at the *model-ranking* level. LLM judges are reliable for **ranking** alternative drafts, less reliable for **absolute** scoring, and **unreliable** for fine-grained discourse-level constraints unless coupled with task-specific rubrics and human-aligned calibration.

**Realistic engineering vision — reliability by layer:**

| Layer | Reliability of automated enforcement |
|---|---|
| XML schema / DITA topic types | Deterministic |
| Approved terminology, sentence length, noun-cluster length, passive detection (STE/Acrolinx) | High (deterministic regex + POS) |
| Active voice, second person, descriptive headings | High–moderate (rule-based + light NLP) |
| Coreference / entity-grid coherence | Moderate (SOTA coref ~80% F1; entity-grid scoring informative but noisy) |
| Argument-component classification (Toulmin) | Moderate (LLM judge + rubric) |
| RST discourse relations | Low (~57% F1 at human ceiling ~55% — not deterministic) |
| "Is this section coherent / well-organized?" | Moderate via LLM-as-judge, *with* rubric and pairwise framing |

**Recommendation.** Build the pipeline as a *layered* set of typed constraints: **hard lints** at the lexical/structural layers (DITA validation, STE-style sentence rules, glossary terminology) and **soft critics** at the discourse layer (RST as a feature; LLM-judge for pairwise reranking with explicit rubrics for given-new chaining, Toulmin completeness, multi-view coverage). No single discourse-level critic should *block* a document; it should *flag* for human review.

---

# PART III — Unified Synthesis

This synthesis does five things: (A) audits a concrete field-guide-style primer design against the full evidence base; (B) states the three highest-leverage strengthening moves; (C) ranks the Part II frameworks by evidence and by value-to-an-expert-primer, and flags the overhyped ones; (D) reconciles the cross-cutting empirical threads — most importantly the spatial-contiguity effect-size discrepancy and how the two layers of frameworks fit together; (E) assesses the overarching "primer-as-linted-AST" engineering vision.

## §A — Per-feature audit of an existing field-guide primer design

The reference design under audit has: a per-section field-guide layer (lede → at-a-glance card → 300–500-word section summary → per-subsection summaries → callouts → 3-question recall block); a multi-level depth dial (L1 Scan = ledes+cards only, up to L5 Reference); four operational artifacts (decision matrix, diagnostic checklist, failure-modes catalog, decision aid); cross-domain mappings as first-class content; epistemic-honesty tiers (settled/contested/speculative); and a figure vocabulary. It holds up well.

- **Lede**: inverted pyramid + BLUF + Minto answer-first + Reigeluth epitome — load-bearing structure, well-supported. Move: make the lede a *complete claim*, cuttable from the bottom; never a teaser.
- **At-a-glance card**: in effect an advance organizer (Ausubel; Mayer signaling). See strengthening flag 1 — make it function as an organizer (analogy + anchor list), not a summary-in-the-section's-own-terms.
- **300–500-word section summary**: the textbase supporting situation-model construction (Kintsch). Keep within the Carroll "slash the verbiage" discipline; at this length the temptation to scaffold for novices reverses for experts.
- **Per-subsection summaries**: Reigeluth's internal summarizers — well-supported. Given-new chaining (Part II §4) applies here.
- **Callouts**: Mayer signaling + Tufte layering-and-separation. Use sparingly — a callout on every paragraph signals nothing.
- **3-question recall block**: testing effect (Rowland 2014 g ≈ 0.50; Roediger & Karpicke 2006 Exp 1 d = 0.83). Calibrate to ≥ 75% initial success; prefer generation over recognition; force at least one cross-domain-mapping question.
- **Depth dial (L1–L5)**: direct realization of Shneiderman's Mantra, Nielsen's progressive disclosure, Reigeluth's zoom, Farkas's safety-net layering. Caveat (Nielsen 2006): "disclose everything users frequently need up front" — a senior reader at L1 should be able to make routine decisions without descending.
- **Four operational artifacts**: decision matrix (Pugh — contrast-forcing; cognitive function strong, direct empirical mixed); diagnostic checklist (apply Gawande/WHO design — short ≤9, action-verb-first, killer items, pause points; Haynes 2009 36%/47% reductions); failure-modes catalog (anti-pattern recognition memory; Klein's recognition-primed decision); decision aid (clinical-decision-rule literature — works best when validated, with a clear action threshold, and when the user knows its failure modes; tag each aid with expected error rate and boundary conditions).
- **Cross-domain mappings**: the design's most underrated choice. Analogical-reasoning (Gentner), fuzzy-trace gist (Reyna & Brainerd), advance-organizer (Ausubel), information-foraging (Pirolli & Card), and Cognitive Flexibility Theory (Spiro) all independently argue this is the single highest-yield gist-bearing device for an expert. See flag 3.
- **Epistemic-honesty tiers**: supported by academic-hedging research, GRADE evidence-grading, and cognitive-calibration literature; operationalized by Toulmin's Qualifier/Rebuttal. Contested claims should name a dissenting view; speculative claims should name the inference type ("by analogy from X").
- **Figure vocabulary**: adopt Tufte's "data > labels > scaffolding > decoration," small multiples for comparisons, complete-claim captions (Schriver: captions are read first), and inline micro-figures/sparklines for inline data references.

## §B — The three highest-leverage strengthening moves

**Flag 1 — Make the "at-a-glance" card a true advance organizer, not a teaser.** The advance-organizer literature (Ausubel; Mayer 1979; Luiten et al. 1980, 135 studies, small reliable facilitative effect) shows an organizer works *only if* it activates and bridges to the reader's existing schema. For an expert audience, the card must explicitly name (a) the closest home-domain analogue, (b) the 3–5 anchor concepts the reader already knows, (c) what is genuinely new vs. renamed. If the card instead summarizes the section in the section's own terminology, the advance-organizer effect does not fire. **Change**: rewrite cards to lead with the analogy and anchor list, not the headline finding.

**Flag 2 — Replace worked examples with contrastive comparison for experts (expertise reversal).** The strongest negative-prediction finding in the whole report: techniques recommended for novices (scaffolded worked examples, exhaustive split-attention reduction, redundant text-plus-figure) progressively lose effectiveness as expertise rises and, in multiple replicated studies, cross zero into harm (Kalyuga et al. 2001b; Kalyuga 2007). **Change**: where a section uses a worked example to *teach* a concept, replace it with a contrastive comparison (decision matrix, this-vs-that, home-domain-vs-adjacent-domain mapping). Hold worked examples at L4–L5 as opt-in scaffolding for self-identified readers. Cognitive Flexibility Theory (Part II §7) gives the positive form: multiple contrasting representations of the same concept.

**Flag 3 — Promote cross-domain mappings into the L1 card.** Per analogical-reasoning, fuzzy-trace, advance-organizer, and CFT literatures, the cross-domain mapping is the highest-yield gist device for an expert. If it lives below the L1 card, the primer pays its highest-leverage cost (deriving the mapping) without collecting the benefit (gist installation at first read). **Change**: bake the home-domain analogue into the L1 card's opening sentence wherever a mapping exists.

**Two minor design risks the research flags:**
- *F-pattern as a failure signature.* If readers exhibit F-pattern scanning (NN/G), the headings are not predictive enough; the target is layer-cake reading (parallel, predictive headings). Testable by asking readers to guess section content from headings alone.
- *Checklist inflation.* Gawande/WHO data come from short, killer-item-only checklists. Long exhaustive checklists are not used. ≤ 9 items per pause; killer items only.

## §C — Framework rankings and overhyped flags

**Ranked by strength-of-evidence for an expert primer:**
1. **Given-New / Theme-Rheme** — strong, decades-old psycholinguistic evidence; improves reading time and recall; computationally measurable.
2. **Cognitive Flexibility Theory** — the one framework whose evidence base is *strongest for experts*; transfer gains in medical-education and hypertext studies.
3. **Toulmin** — solid evidence that explicit claim/warrant/rebuttal improves argument *quality*; weaker for reader comprehension; tooling mature enough to lint recommendation blocks.
4. **Minto / SCQA / MECE** — converges with BLUF/inverted-pyramid; ~zero direct studies; practitioner craft riding on adjacent evidence.
5. **ASD-STE100 / controlled language** — practitioner-strong; comprehension gains best supported for non-native readers and safety-critical procedures; tooling mature.
6. **Google condition-before-instruction** — house style, but condition-first specifically supported by working-memory evidence.
7. **RST** — strong as an analytical lens and a useful soft NLP signal; weak as a deterministic rendering substrate (parser ceiling ≈ human IAA ≈ 55 F1).
8. **DITA / typed authoring** — strong for production efficiency/consistency; little direct evidence for reader outcomes.
9. **UID** — a production-side psycholinguistic theory; evidence that smoothing surprisal in a document helps readers is thin and indirect.
10. **E-Prime** — philosophical craft; essentially no rigorous comprehension evidence.

**Overhyped or weakly supported — do not make load-bearing:**
- **E-Prime** for technical writing (no rigorous studies; frequent overclaiming; the "4–16×" claim is a misattribution from ICAE/gist-token prompt-compression research).
- **UID-as-document-intervention** (misapplies a production theory to a comprehension problem).
- **Strict MECE** as a quality gate (useful framing heuristic; no evidence that strict partitioning beats looser organization in primers).
- **Auto-rendering from RST trees** (parser quality and inter-annotator agreement both too low).

## §D — Reconciling the cross-cutting empirical threads

**The spatial-contiguity effect size (the one genuine numeric conflict across the two phases).** Part I cited the spatial-contiguity effect via Ginns (2006) at d ≈ 0.72; the source documents cited Mayer at d ≈ 1.09–1.12. Both are correct but refer to different things:

| Source | What it measures | Effect size |
|---|---|---|
| Mayer (Cambridge handbook, Table 12.7) | Median of 22 individual experiments of Mayer's own integrated-text-and-graphics studies | d ≈ 1.10 (median); individual experiments include Brakes d=1.36, Lightning d=1.09 and d=1.12, Tindall-Ford et al. 1997 d=1.08 |
| Ginns (2006), *Learning and Instruction* 16(6) | Meta-analysis of 50 studies (37 spatial + 13 temporal) | weighted mean d ≈ 0.72 (combined split-attention ~0.85, 95% CI 0.68–1.02) |
| Schroeder & Cenkci (2018), *Educational Psychology Review* | Meta-analysis of 58 spatial-contiguity comparisons, n=2426, random-effects | g ≈ 0.63 (p < 0.001) |

Mayer's 1.09–1.12 are *individual-experiment* effects from his own lab on materials designed to elicit the effect (high element interactivity, novice learners). Ginns's 0.72 and Schroeder & Cenkci's 0.63 are *meta-analytic averages* across heterogeneous studies and populations — the more defensible figures for general claims. **Crucial expert-primer moderator**: the effect is much larger for *complex* materials (high element interactivity, d ≈ 0.78) than simple ones (d ≈ 0.28, often non-significant). Expert primer content is high-complexity, so the *higher* end of the range applies. **Canonical phrasing to use**: "Spatial contiguity has a robust positive effect, ranging from g ≈ 0.63 (Schroeder & Cenkci 2018, 58 comparisons) and d ≈ 0.72 (Ginns 2006, 50 studies) on average, up to d ≈ 1.10 (Mayer's lab) on the specific paradigms most relevant to dense technical content with complex graphics."

**How the two framework layers reconcile with each other.**
- **Minto/SCQA + BLUF/inverted pyramid** → the same recommendation from consulting and journalism. Strong via convergence.
- **Given-new + entity-grid** → operationalizes what F-pattern/layer-cake scanning *rewards* in coherent prose.
- **STE noun-cluster and sentence-length rules** → mechanical realization of CLT intrinsic-load management.
- **Cognitive Flexibility Theory** → completes the expertise-reversal story: novices benefit from progressive disclosure and elaboration; experts benefit from criss-crossing multiple representations of the *same* content — the opposite design. CFT is the positive form of strengthening flag 2.
- **Toulmin** → operationalizes the epistemic-honesty tier and "show your work"; each Toulmin block doubles as a retrieval cue for the recall blocks.
- **RST** → analytic complement to Reigeluth's elaboration; soft signal, not deterministic substrate.
- **DITA + critics** → the engineering realization of Information Mapping (Horn) and Diátaxis.
- **UID and E-Prime** → over-extensions; not load-bearing.

## E. The "primer-as-linted-AST" engineering vision — is it sound?

The vision (treat a primer as a typed AST of metadata-tagged blocks — `diataxis_domain`, `info_type`, `utility_rank`, `discourse_relation`, `nuclearity`, `scent_label`, `concept_ids`, `preferred_terms`, `representation_mode`, `case_ids`, `evidence_refs`, `visibility_policy` — validated by a layered lint pipeline with DITA as the substrate) is **sound and genuinely valuable at the layers where the underlying signal is reliable, and ahead of the evidence at the discourse layer.**

- **Sound and ready now (hard lints)**: schema/topic typing (DITA-deterministic); terminology univocity (ISO 704; one preferred term per concept; acronym binding); STE-style structural caps (sentence length, noun-cluster ≤ 3, paragraph ≤ 6, condition-first); Google mechanics (active voice, second person, descriptive headings); evidence-completeness (facts carry refs, recommendations carry claim cards); Diátaxis domain gate (reject tutorial/how-to leakage); block purity (one info type per block).
- **Sound but advisory (soft critics, must not block)**: given-new coherence via coreference + entity grid (moderate reliability); Toulmin completeness via argument mining + LLM judge (moderate); CFT multi-view coverage (requires a semantic critic); LLM-as-judge pairwise reranking against explicit rubrics (reliable for ranking, not absolute scoring).
- **Ahead of the evidence (do not deterministically enforce)**: RST-driven auto-collapse of satellites (parser ~57 F1 at human ceiling ~55 F1); UID surprisal-smoothing as an editing target; strict MECE partitioning as a gate; E-Prime as a global constraint.

The right build order is dependency-driven: (1) typed schema + terminology binding (reduces variance everywhere else); (2) discourse relations and nuclearity as *metadata authored or critic-flagged*, not parser-gated; (3) reader-economics lints (scent scoring, redundancy/split-attention, heading lints); (4) coverage lints (CFT multi-view, rebuttal/break-condition presence); (5) adjunct critic packs (Toulmin, spatial-contiguity layout anchors, given-new), promoted from warning to blocker only after corpus calibration. The single most important engineering discipline: **keep the hard/soft boundary honest** — never let a discourse-level critic whose accuracy is unknown silently gate a document.

---

# PART IV — Unified Recommendations

These merge the content/structure moves (from the foundational analysis) with the pipeline constraints (from the frameworks analysis). They are complementary: the first set is about *what to write*, the second about *how to enforce it*.

## Content and structure (stage by leverage and reversibility)

**Stage 1 — immediate, low-risk, high-leverage:**
1. Rewrite every "at-a-glance" card to open with the home-domain analogue and a 3–5-item anchor list (flag 1).
2. Audit each L1 lede for completeness — cuttable from the bottom and a complete claim, not a teaser.
3. Audit headings for parallelism and predictiveness ("can a reader who reads only L1 headings construct an accurate gist?").
4. Add an inline epistemic tag (settled/contested/speculative) to every load-bearing claim; for contested claims, name the dissenting view.

**Stage 2 — medium-effort, section-by-section:**
5. Move every cross-domain mapping into the L1 card opening (flag 3).
6. Replace worked-example scaffolding on the primary surface with contrastive comparisons; hold scaffolded examples at L4–L5 (flag 2); add a CFT multi-view requirement per complex concept.
7. Apply Tufte layering-and-separation to all figures (data > labels > scaffolding > decoration; one accent color per page; small multiples for any comparison; complete-claim captions).
8. Constrain checklists to ≤ 9 killer items with defined pause points.

**Stage 3 — longer-horizon, infrastructural:**
9. Adopt DITA-style topic-based single-sourcing so each block has exactly one source and is referenced (not copied) into every depth-dial assembly.
10. Build a recall-block calibration loop targeting ≥ 75% initial-recall success for an attentive L1 reader (Rowland 2014 threshold).

## Pipeline constraints (for an automated generation/lint system)

**Adopt as load-bearing (hard lints):**
1. DITA-style typed topics with required Toulmin slots on every recommendation block.
2. STE-style structural lints (sentence ≤ 25 desc / ≤ 20 proc, noun cluster ≤ 3, paragraph ≤ 6, condition-before-instruction).
3. Glossary-enforced terminology univocity (ISO 704): one designation per concept, project-wide; acronym expansion + binding on first use.
4. Given-new coherence lint (coreference + entity grid): flag sentences whose subject entity is absent from the previous two sentences.
5. CFT multi-view requirement: each complex concept appears in ≥ 3 representation modes and ≥ 2 contrasting cases.
6. Google mechanics (active voice, second person, descriptive headings, condition-first) as deterministic lints.
7. Diátaxis domain gate (reject tutorial/how-to leakage) + block-purity gate (one info type per block).

**Use as soft signals only (advisory, never blocking):**
- RST parser output for ranking summary candidates and flagging satellite-heavy paragraphs.
- LM per-token surprisal for flagging candidate dense passages for human review.
- LLM-as-judge for pairwise reranking of draft sections against an explicit rubric (given-new compliance, Toulmin completeness, multi-view coverage), not for absolute pass/fail.

**Reject or de-prioritize:**
- E-Prime as a constraint; UID surprisal-smoothing as an editing target; strict MECE partitioning as a gate; auto-collapsing satellite EDUs from RST output.

## Benchmarks that would change these recommendations

- If reader-research showed L1 cards being *skipped*: the issue is scent quality — strengthen signaling and labels, not card content.
- If senior readers descend past L2 routinely: L1 is hiding things it shouldn't; rebalance the dial.
- If recall blocks show < 50% initial success: below the testing-effect threshold — either L1 isn't dense enough or questions are miscalibrated.
- If senior readers report worked examples *help*: the audience is less expert in that subdomain than assumed; relax the expertise-reversal default for that section only (Kalyuga's adaptive-fading approach).
- If a future RST parser reaches > 70 Full F1 with documented IAA > 70 F1: promote RST from soft signal to deterministic input.
- If a controlled study shows surprisal-smoothed prose improves expert retention by d > 0.3: promote UID. If any controlled study shows E-Prime improves comprehension at all: revisit.

---

# PART V — Caveats

- **Empirical strength is uneven.** Load-bearing anchors: the expertise reversal effect (multiple replications, meta-analytic synthesis); minimalism vs. systematic documentation (Ginns et al. 2006, d = 1.12); the testing effect (Rowland 2014, g ≈ 0.50; Roediger & Karpicke 2006 Exp 1, d = 0.83 at one week); the WHO Surgical Safety Checklist (Haynes et al. 2009, 36%/47% reductions); information foraging theory (computational models that predict behavior); F-pattern and layer-cake reading (NN/G eye-tracking); spatial contiguity (Ginns 2006 d ≈ 0.72; Schroeder & Cenkci 2018 g ≈ 0.63; Mayer's lab up to d ≈ 1.10); given-new (Haviland & Clark 1974 and replications); Cognitive Flexibility Theory transfer effects (Jacobson & Spiro 1995).
- **Several widely-cited claims are craft, not science.** Most of Information Mapping, much of Diátaxis, Minto/SCQA/MECE, the Pugh matrix, hypertext/transclusion theory, the Google style guide as a whole, and many specific Tufte principles are practitioner consensus with limited or contested controlled evidence. Useful heuristics; not laws.
- **Generalizability gaps.** Most minimalism evidence is on word-processing manuals; most testing-effect evidence is classroom; most advance-organizer evidence is school/university students; STE comprehension evidence is strongest for non-native readers and procedures. The inference to senior-practitioner adjacent-domain self-study is plausible (the mechanisms — schema activation, retrieval encoding, scent following, given-new chaining — are content-neutral) but it is inference, not direct evidence.
- **Contested findings worth flagging in any styleguide built on this.** The F-shaped pattern is not universal (EyeQuant 2018); some Tufte principles are contested (Bateman et al. 2010 found embellished charts recalled better after 2–3 weeks, with interpretation accuracy not significantly different); CLT's intrinsic/extraneous/germane decomposition is critiqued as not independently measurable (de Jong 2010; Schnotz & Kürschner 2007); Toulmin element classification is inter-rater-unreliable on real text (Sampson & Clark 2008; Kunnan 2010).
- **Specific source-document claims handled.** The "4–16× token compression with near-parity accuracy" attributed to E-Prime/"synthetic reasoning languages" is, on the evidence, a **misattribution** from ICAE/gist-token prompt-compression research (Ge et al. 2024; Mu et al. 2023) — do not propagate. The arXiv 2603.27626 "Umwelt Engineering" preprint appears to exist but is a single-author, apparently non-peer-reviewed paper about *LLM* reasoning, not human-reader comprehension; do not rely on it as authoritative. STE Issue 9 numbers are corroborated by the official STEMG site and secondary sources but were not extracted from the proprietary PDF. RST-DT SOTA Full F1 ~57–58 is inferred from Maekawa et al. 2024's stated margin over Kobayashi et al. 2022 (55.4). The "~85% LLM-judge agreement with humans" is from Zheng et al. 2023 MT-Bench (open-ended, no ties) and varies substantially by task and setup.
- **The master caveat for this audience** is the **expertise reversal effect**, which inverts much of the standard instructional-design playbook. A primer that uncritically imports K–12 or undergraduate instructional-design recommendations will systematically over-scaffold for senior practitioners and may produce *measurably worse* outcomes than a sparser design. When in doubt for this audience, the evidence favors *less* explicit scaffolding and *more* contrast, comparison, analogy, and multi-representation coverage.

---

# PART VI — Addendum: evidence for the generation pipeline

*Added during the deep-primer skill build. Grounds the rules that govern research (Phase 1), verification (Phase 6), and the critics (Phase 7). Attributions are to primary sources; claims are paraphrased.*

## §A — Attributable generation & citation evaluation — ALCE (Gao et al., EMNLP 2023)
ALCE ("Enabling Large Language Models to Generate Text with Citations," Gao, Yen, Yu & Chen, EMNLP 2023; arXiv 2305.14627) is the first reproducible benchmark for LLM citation quality. It scores generations on fluency, correctness, and citation quality, with automatic metrics that correlate strongly with human judgement. Citation quality splits into the two measures the verification stage uses directly: **citation recall** (every statement is supported by its citations) and **citation precision** (each cited source actually supports the statement; no irrelevant citations). The sobering baseline: even strong models lack complete citation support roughly half the time on long-form (ELI5) answers. Follow-on work on fine-grained rewards for attributable generation (and RARR-style retrofit-attribution) finds that localized, sentence-level signals beat holistic ones. **Phase-6 implementation options:** MiniCheck (a small, cheap NLI fact-checker) for the entailment step, or FActScore / SAFE-style decompose-and-verify for finer-grained per-claim checking; either is wrapped behind `verify/citation_quality.py` (the `model_verified` enforcement type). **Grounds:** R-GROUND-01/02/03 and the Phase-6 verification stage.

## §B — Pre-writing is the bottleneck — STORM (Shao et al., NAACL 2024)
STORM ("Assisting in Writing Wikipedia-like Articles From Scratch," Shao et al., NAACL 2024; Stanford OVAL; arXiv 2402.14207) isolates the hard part of long-form generation as the **pre-writing stage** — researching the topic and preparing an outline before any prose. Its two mechanisms: **perspective-guided question asking** (personify the writer with a specific perspective to focus questions) and **simulated conversations** (follow-up questions arise as answers update understanding). Collected Q&A is curated into an outline; the article is then written against outline + references with citations (recall/precision per Gao 2023). Co-STORM (EMNLP 2024) adds collaborative human-in-the-loop discourse. **Grounds:** the Phase-1 research arc and `research-perspectives.md` — perspectives derived from the primer's own structure, iterative follow-ups, curate-then-outline.

## §C — Orchestrator-worker research & the separate citation pass — Anthropic (2025)
Anthropic's multi-agent Research system uses an **orchestrator-worker** pattern: a lead agent plans and spawns parallel subagents, each in its own context window, then synthesizes their findings; a separate **CitationAgent** attaches citations as its own pass. Reported ~90% improvement over single-agent on breadth-first research at ~15× the token cost, with token usage explaining most of the performance variance. Lessons that shaped this design: each subagent needs an explicit **contract** (objective, output format, tool/source guidance, boundaries) or it drifts; the published architecture has **no built-in circuit breakers**, and early failures were excessive subagent spawning and redundant search; an **external-memory** pattern lets the lead survive context limits. **Grounds:** the single-agent-V1 decision (synthesizer consumes the external-memory ledger so multi-agent fan-out is a V2 drop-in), the mandatory circuit breakers, and verification-as-a-separate-stage.

## §D — LLM-as-judge reliability & bias (2023–2026)
LLM judges reach near inter-human agreement on controlled chat evaluation (MT-Bench, Zheng et al. 2023) but carry systematic biases that matter for an all-Claude critic: **position bias** (favoring the first/last candidate — mitigated by swap-and-average), **verbosity bias** (rewarding longer answers regardless of value — which directly fights the minimalism rule), and **self-preference / family bias** (a model favors its own outputs; Claude-judging-Claude compounds it). Audits from 2025–2026 find that reference- and rubric-anchored scoring is more reliable than prompt-only; **binary single-criterion** judgments are more robust than holistic scores; test-retest reliability must be measured (run gating judgments more than once); divergence above ~20–25% from human spot-checks signals the rubric needs recalibration; and multi-agent debate among judges amplifies bias after the first round, while meta-judge designs are more robust. **Grounds:** R-REJECT-05 (critics binary-only; the verbosity/self-preference guard) and the critic-prompt discipline (swap-and-average, twice-run gating, calibration against the human-labeled eval set).
