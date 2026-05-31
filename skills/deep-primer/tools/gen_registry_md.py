#!/usr/bin/env python3
"""Generate rule-registry.md from rule-registry.yaml. Run from references/ (or via tools/build.sh)."""
import yaml

d = yaml.safe_load(open('rule-registry.yaml'))

NS_TITLES = {
 'PARAM':'Parameters & calibration','ARCH':'Document architecture','SCENT':'Headings as information scent',
 'CARD':'The at-a-glance card','SUMM':'Fractal summary discipline','DEPTH':'Progressive disclosure',
 'MV':'Multi-view (cognitive flexibility)','PROSE':'Prose & tone','VOCAB':'Vocabulary & univocity',
 'EXPERT':'Expertise reversal','RECALL':'Retrieval practice','ART':'Operational artifacts',
 'EVID':'Empirical claims & epistemic honesty','GROUND':'Anti-hallucination / citation grounding',
 'FIG':'Figures & diagrams','XREF':'Cross-domain mapping & cross-referencing',
 'PROJ':'IR-first & projections',
 'DISC':'Discovery campaign (recall augmentation)',
 'CONV':'Convergence guard (escalate loop)',
 'CONSIST':'Consistency & build invariants','REJECT':'Anti-rules / do-not-adopt',
}
order = list(NS_TITLES)
rules = d['rules']
by_ns = {ns:[r for r in rules if r['id'].split('-')[1]==ns] for ns in order}

L = []; w = L.append
w("# Deep Primer — Rule Registry (companion)\n")
w("*Human-readable rendering of `rule-registry.yaml`, generated from it (edit the YAML, regenerate via `tools/build.sh`). "
  "The YAML is the source of truth consumed by the generator, the critics, and the linter; this file is for reading and review.*\n")
w(f"**Version {d['meta']['version']}** · applies to: {d['meta']['applies_to']}.\n")

lg = d['meta']['legend']
w("## Legend\n")
w("**Priority** — " + " · ".join(f"`{k}` {v}" for k, v in lg['priority'].items()) + "\n")
w("**Blocking** — " + lg['blocking'] + "\n")
w("**Enforcement** — " + " · ".join(f"`{k}` {v}" for k, v in lg['enforcement'].items()) + "\n")
w("**Evidence grade** — " + " · ".join(f"`{k}` {v}" for k, v in lg['evidence_grade'].items()) + "\n")

w("## Per-run parameters\n")
w("The generalization layer — set once per primer; rules reference these.\n")
for k, v in d['parameters'].items():
    extra = f" *(values: {', '.join(v['values'])})*" if 'values' in v else ""
    w(f"- **`{k}`** ({v['type']}){extra} — {v['desc']}")
w("")

w("## Circuit-breaker & calibration defaults\n")
w("Defaults; tuned in the eval loop.\n")
for k, v in d['budgets'].items():
    w(f"- `{k}`: {v}")
w("")

w("## Generator core (always resident)\n")
w("The highest-leverage generation-time MUSTs the generator holds in context. Mechanical hard-lint MUSTs are "
  "intentionally excluded here — the linter enforces them after the fact.\n")
core_titles = {r['id']: r['title'] for r in rules}
for cid in d['must_core']:
    w(f"- **{cid}** — {core_titles.get(cid,'?')}")
w("")

w("## Rules by category\n")
for ns in order:
    w(f"- [{ns} — {NS_TITLES[ns]}](#{ns.lower()}) ({len(by_ns[ns])})")
w("")

for ns in order:
    w(f"<a id='{ns.lower()}'></a>\n")
    w(f"### {ns} — {NS_TITLES[ns]}\n")
    for r in by_ns[ns]:
        core = " · **CORE**" if r['id'] in d['must_core'] else ""
        w(f"#### {r['id']} — {r['title']}")
        w(f"`{r['priority']}` · `{r['enforcement']}` · *{r['evidence_grade']}*{core}  ")
        w(f"{r['directive']}  ")
        chk = r['check']
        t = chk.get('type')
        if t == 'script':
            w(f"- **Check (hard lint):** `{chk['ref']}` — {chk.get('detail','')}")
            if 'also_rubric' in chk: w(f"- **Also (soft):** {chk['also_rubric']}")
        elif t == 'model':
            w(f"- **Check (model-verified):** `{chk['ref']}` — {chk.get('detail','')}")
        elif t == 'rubric':
            w(f"- **Check (critic · {chk.get('pass','?')} pass):** \u201c{chk['question']}\u201d")
            if 'pass_example' in chk: w(f"- **PASS looks like:** {chk['pass_example']}")
            if 'also_hard_lint' in chk: w(f"- **Also (hard):** `{chk['also_hard_lint']}`")
        else:
            w(f"- **Check (human):** {chk.get('inspect','')}")
        ph = ','.join(str(x) for x in r['phase']) if r['phase'] else '—'
        w(f"- **Counters:** {r['counters']}")
        w(f"- **Phase:** {ph} · **Evidence:** {r['evidence_ref']}")
        if r.get('params_used'): w(f"- **Params:** {', '.join(r['params_used'])}")
        w("")

open('rule-registry.md', 'w').write("\n".join(L))
print("wrote rule-registry.md")
