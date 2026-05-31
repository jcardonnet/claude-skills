<!-- assets/llm_md_template.md — shape of the OPERATIONALLY-DISTILLED projection (render/render_llm_md.py, Prompt 4).
Front-matter index (concept-map as glossary/map), then one '## [block: <id>]' section per kept block.
Roles kept: lede->claim, card->distilled, toulmin, matrix, figure->caption-only, glossary, further_reading->annotated.
Roles dropped: recall. SVG dropped, captions kept. Provenance printed inline. block-ids == HTML block-ids (R-PROJ-02..06). -->
---
title: "<primer title>"
generated_at: "<iso>"
concepts:   # the concept-map, as the LLM's index/glossary
  - {id: <concept_id>, canonical_term: "<term>", aliases: [], home_anchor: "<…>", fidelity_boundary: "<…>"}
---

## [block: <block_id>]   concept: <concept_id>   mode: <mode>   provenance: <verified|inferred|unverified>
Claim: <self-contained claim, referents restated>
Holds-when: <qualifier>
Rebuttal: <when it fails>
Sources: [<source_id> | none yet — inferred]
