#!/usr/bin/env python3
"""Generate the scoped critic prompts from rule-registry.yaml. Run from references/ (or via tools/build.sh).
Emits 6 files into critic-prompts/: structure-architecture, structure-fieldguide, coherence,
expertise-calibration, evidence-grounding, figures."""
import yaml, re, os

reg = yaml.safe_load(open('rule-registry.yaml'))
R = {r['id']: r for r in reg['rules']}

# --- membership ---------------------------------------------------------------
soft_by_pass = {}
for r in reg['rules']:
    if r['enforcement'] == 'soft_critic':
        soft_by_pass.setdefault(r['check']['pass'], []).append(r['id'])

ARCH_GROUP = ['R-ARCH-01','R-ARCH-03','R-ARCH-04','R-SCENT-01','R-SCENT-02',
              'R-DEPTH-01','R-XREF-01','R-XREF-03','R-VOCAB-02']
# field-guide = the rest of the soft 'structure' rules, plus the folded R-MV-01 companion
FIELDGUIDE_GROUP = [rid for rid in soft_by_pass.get('structure', []) if rid not in ARCH_GROUP] + ['R-MV-01']

MEMBERS = {
 'structure-architecture': ARCH_GROUP,
 'structure-fieldguide':    FIELDGUIDE_GROUP,
 'coherence':               ['R-PROSE-01'] + soft_by_pass.get('coherence', []),   # folded given-new + fractal coherence
 'expertise-calibration':   soft_by_pass.get('expertise-calibration', []),
 'evidence-grounding':      soft_by_pass.get('evidence-grounding', []),
 'figures':                 soft_by_pass.get('figures', []),
}

PASS_TITLE = {
 'structure-architecture': 'Structure — architecture & navigation',
 'structure-fieldguide':   'Structure — field-guide layer & artifacts',
 'coherence':              'Coherence',
 'expertise-calibration':  'Expertise calibration',
 'evidence-grounding':     'Evidence grounding',
 'figures':                'Figures',
}
PASS_JUDGES = {
 'structure-architecture': "the primer's skeleton — scope block, answer-first opening, predictive/parallel headings, reading paths, L1 actionability, cross-domain-mapping placement, and cross-reference integrity.",
 'structure-fieldguide':   "the per-section field-guide layer and operational artifacts — cards, ledes, recall, the four artifacts, multi-view concept coverage, apparatus proportionality, and further-reading.",
 'coherence':              "information flow the entity-grid script cannot see — whether prose moves given->new, and whether each layer is self-contained at its depth (fractal coherence).",
 'expertise-calibration':  "whether the writing respects the reader's seniority — scaffolding level, trade-off framing, stance, and apparatus proportionality.",
 'evidence-grounding':     "evidence *quality and framing* — Toulmin completeness, epistemic tagging, and vendor corroboration. It does NOT check citation correctness; Phase-6 (model_verified) owns recall/precision and fabrication.",
 'figures':                "figures — captions, emphasis, contiguity, and comparison form.",
}
CALIB = {
 'structure-architecture': "Judge each item independently against the named block. The common failures are generic topic-label headings (R-SCENT-01) and burying the lede behind an introduction (R-ARCH-03).",
 'structure-fieldguide':   "The single most common failure is the card written as a teaser (R-CARD-01): a card that restates the section in its own terms is a FAIL even if well written. Watch for manufactured artifacts that pad a thin section (R-DEPTH-03).",
 'coherence':              "A paragraph can satisfy the mechanical entity grid yet still read as disconnected assertions — that is a FAIL. You judge logical flow and whether a layer stands alone at its depth, not keyword overlap.",
 'expertise-calibration':  "The dominant failure is the model defaulting to tutorial scaffolding (R-EXPERT-01): a step-by-step worked example on the primary surface is a FAIL above early_career even when correct. Read seniority_band from parameters.yaml before judging.",
 'evidence-grounding':     "You judge framing, not citation correctness. A recommendation with no rebuttal (R-ART-03) is a FAIL; speculation phrased with the grammar of settled fact (R-EVID-01) is a FAIL. Leave citation recall/precision to the Phase-6 model_verified stage.",
 'figures':                "The dominant failure is the label caption (R-FIG-01): 'Figure 3: architecture' is a FAIL because it states no conclusion. Emphasizing everything (R-FIG-02) emphasizes nothing.",
}
# each pass: list of (rule_id, FAIL-example, PASS-example)
EXAMPLE = {
 'structure-architecture': [("R-SCENT-01",
   "## Background  /  ## Key Concepts  /  ## Conclusion",
   "## Why long context didn't kill chunking  /  ## When a reranker is dead weight")],
 'structure-fieldguide': [("R-CARD-01",
   "This section explains how vector databases index and query embeddings at scale.",
   "If you know SQL B-tree indexes, a vector index is the same idea for 'nearest' instead of 'equal'; new is the distance metric and the recall-vs-speed knob.")],
 'coherence': [("R-PROSE-01",
   "Retrieval augments generation. Latency matters in production. Rerankers improve precision.",
   "Retrieval augments generation by injecting passages; those passages add latency, and a reranker spends part of that budget to raise precision.")],
 'expertise-calibration': [("R-PROSE-02",
   "HNSW is an excellent choice for vector search.",
   "HNSW buys sub-linear query latency at the cost of high memory and slow, immutable index builds.")],
 'evidence-grounding': [
   ("R-ART-03",
    "Use a cross-encoder reranker for best results.",
    "Use a cross-encoder reranker when top-k precision dominates (qualifier); skip it on high-QPS or sub-100ms paths, where its per-pair cost dominates (rebuttal)."),
   ("R-EVID-01",  # non-software, to reinforce domain-independence
    "Drug X reduces mortality by 30%.",
    "Drug X reduced mortality in one RCT in that population (settled there); generalization to comorbid patients is contested.")],
 'figures': [("R-FIG-01",
   "Figure 2: The retrieval pipeline.",
   "Figure 2: Reranking, not retrieval, is the precision bottleneck — recall saturates by k=50 while precision keeps climbing.")],
}

PREAMBLE = """You are a **scoped critic** for the {ptitle} pass. You judge ONLY the rules listed in this file. Every other aspect of the primer is out of scope — other passes own it.

**Discipline (mandatory):**
- Return a **binary** verdict — `pass` or `fail` — for each rubric item against a specific block. **Never** score holistic "quality", "thoroughness", or "how good"; holistic scoring rewards length and self-preference and is prohibited (`R-REJECT-05`).
- **Block enumeration:** you are given the primer's block list (id + type) from the parsed AST. Apply each rule only to the block types it targets — card rules to card blocks, heading rules to headings, figure rules to figures, document-level rules to `"document"`. One verdict per (rule x applicable block).
- **Length is not evidence of compliance.** A shorter block that satisfies the rule passes over a longer one that does not.
- **Pointwise, not pairwise.** These are pointwise verdicts; the reliability control is **test-retest** — judge each gating item **twice** and return `unstable` on disagreement. **Swap-and-average applies only when you are explicitly comparing two candidate revisions** (a pairwise call), never to a pointwise verdict.
- Cite the `rule_id`, the `block_id`, and a one-line factual `evidence` string (plus a short `span` where useful). Keep evidence factual, never graded.
- Rationale for each rule is in `references/evidence-map.md`; full contrast pairs are in `references/exemplars.md`."""

OUTPUT = """## Output
Return one JSON object:
```json
{{"pass":"{passname}","verdicts":[
  {{"rule_id":"R-XXX-00","block_id":"<id or 'document'>","verdict":"pass|fail|unstable","evidence":"<one factual line>","span":"<optional short quote>"}}
]}}
```
Emit a verdict for every rule in this file against every block it applies to. Do not add commentary outside the JSON."""


def item_fields(rid):
    r = R[rid]; chk = r['check']
    if r['enforcement'] == 'soft_critic':
        q = chk['question']
        pe = chk.get('pass_example')
        companion = chk.get('also_hard_lint')
        comp = f"A script (`{companion}`) checks the mechanical part; you judge what it cannot." if companion else None
    else:  # folded hard_lint companion (R-PROSE-01, R-MV-01)
        q = re.sub(r'\s*\([a-z]+ pass\)\s*$', '', chk['also_rubric'])
        pe = None
        comp = f"The script `{chk['ref']}` performs the mechanical check; you judge what it cannot — {chk.get('detail','')}."
    return r['title'], q, r['counters'], r['evidence_ref'], pe, comp


def render_item(rid):
    title, q, fail, rationale, pe, comp = item_fields(rid)
    L = [f"#### {rid} — {title}",
         f"**Verdict question (binary):** {q}",
         f"- **FAIL looks like:** {fail}"]
    if pe: L.append(f"- **PASS looks like:** {pe}")
    L.append(f"- **Rationale:** {rationale}")
    if comp: L.append(f"- **Companion:** {comp}")
    return "\n".join(L)


def render_examples(pass_):
    out = []
    for rid, bad, good in EXAMPLE[pass_]:
        out.append(f"**Calibration example ({rid}):**\n- FAIL: *\"{bad}\"*\n- PASS: *\"{good}\"*")
    return "\n\n".join(out)


os.makedirs('critic-prompts', exist_ok=True)
for pass_, ids in MEMBERS.items():
    out = []; w = out.append
    w(f"# Critic prompt — {PASS_TITLE[pass_]} pass\n")
    w(f"*Generated from `rule-registry.yaml` (edit the registry, regenerate via `tools/build.sh`). This pass judges {PASS_JUDGES[pass_]}*\n")
    w(PREAMBLE.format(ptitle=PASS_TITLE[pass_]))
    w("")
    w(f"**Calibration note.** {CALIB[pass_]}\n")
    w(render_examples(pass_))
    w("\n---\n")
    w("## Rubric\n")
    for rid in ids:
        w(render_item(rid)); w("")
    w("---\n")
    w(OUTPUT.format(passname=pass_))
    open(f"critic-prompts/{pass_}.md", 'w').write("\n".join(out))
    print(f"wrote critic-prompts/{pass_}.md ({len(ids)} rules)")
