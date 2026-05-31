# Discovery brief templates

The careful, diverse prompts that drive the recall campaign. Each template fills a `research-brief.yaml`
and is run as one deep-research call. Diversity across the matrix is the lever (`R-DISC-02`); keep >=1
orthogonal framing (contrarian / adjacent-field) live per wave. All briefs carry the **standing
instructions** below. Output is mined for *leads only* (`R-DISC-01`).

**Standing instructions (every brief):** prioritize primary / non-vendor sources; report the count of
independent supporting sources per key claim and flag any disagreement; pin the latest version + release
date of every named tool; return sources with URLs.

## Wave A - divergent landscape (>= MIN_FRAMINGS parallel runs)
- **A1 structure** (framing=structure, angle=by-method-family): "Map the full landscape of {topic}: subfields, the canonical taxonomy/decomposition, and how practitioners carve it up."
- **A2 debates** (framing=debates, angle=by-failure-mode): "What are the live controversies and open problems in {topic}? Where is there no consensus?"
- **A3 recency-frontier** (framing=recency-frontier, source_class=latest-release): "What changed in {topic} in the last 6-12 months - new releases, SOTA shifts, deprecated approaches? Give versions and dates."
- **A4 source-authority** (framing=source-authority, source_class=primary): "The most authoritative primary sources, the seminal-but-still-relevant works, the key recent papers, and the best practitioner writeups on {topic}."
- **A5 adjacent-field** (framing=adjacent-field, ORTHOGONAL): "What adjacent fields or techniques does {topic} borrow from, resemble, or get confused with? Where are the false friends?"
- **A6 contrarian-seed** (framing=contrarian-seed, stance=against-dominant, ORTHOGONAL): "Make the strongest case *against* the dominant approach in {topic}. What do skeptics and critics argue, and on what evidence?"

## Wave B - convergent targeted dives (parallel over the residual; adaptive)
- **B-seed** (a user directive - author/entity, or "explore around this URL"): "Survey the work of {author} on {topic}", or "Start from {url} and follow its citations / neighbors." Summarize their key claims and where they sit relative to the consensus; flag divergences. Grounded and corroboration-graded like any source; marked `provenance_origin=user` (`R-DISC-06`).
- **B-dive** (per high-salience gap/hard concept): "Deep dive on {concept} within {topic}: mechanism, key tradeoffs, when it fails / degrades (trigger conditions), current best practice, and primary sources."
- **B-conflict** (per contested point from Wave A): "Claim: {X}. Counter-claim: {not-X}. Find the deciding evidence, the current consensus if any, and *why* the two camps disagree (assumptions, regimes, metrics)."

## Wave C - findings audit (>=3 parallel runs; aimed at the draft ledger)
- **C-omission**: "Here is a summary of what a primer on {topic} currently covers: {coverage}. What important aspects, subtopics, or considerations are missing?"
- **C-disconfirm** (ORTHOGONAL): "Here are the key claims of a primer on {topic}: {claims}. Find the strongest evidence that any of them are wrong, outdated, or overstated."
- **C-source-completeness**: "Here are the sources a primer on {topic} cites: {sources}. What authoritative or important sources on {topic} are NOT in this list?"
