#!/usr/bin/env python3
"""Structural validation for any skill folder. Minimal-but-working reference impl; extend in Prompt 8.

Checks: frontmatter description <=1024 chars; SKILL.md <=~300 lines; if a rule-registry.yaml exists,
every R-<NS>-<n> id referenced in the skill's *.md files resolves (excluding the JSON placeholder).
Usage: python tools/validate_skill.py skills/deep-primer skills/other ..."""
import sys, re, glob, os
try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

def check(skill_dir):
    errs = []
    sk = os.path.join(skill_dir, "SKILL.md")
    txt = open(sk).read()
    parts = txt.split("---")
    if len(parts) >= 3:
        fm = yaml.safe_load(parts[1]) or {}
        d = (fm.get("description") or "")
        if len(d) > 1024: errs.append(f"{skill_dir}: description {len(d)}>1024 chars")
    nlines = txt.count("\n") + 1
    if nlines > 300: errs.append(f"{skill_dir}: SKILL.md {nlines} lines (>300 — consider splitting)")
    reg = os.path.join(skill_dir, "references", "rule-registry.yaml")
    if os.path.isfile(reg):
        ids = {r["id"] for r in (yaml.safe_load(open(reg)).get("rules") or [])}
        for f in glob.glob(os.path.join(skill_dir, "**", "*.md"), recursive=True):
            for rid in set(re.findall(r"R-[A-Z]+-\d+", open(f).read())):
                if rid not in ids and rid != "R-XXX-00":
                    errs.append(f"{f}: dangling rule id {rid}")
    return errs

def main(argv):
    all_errs, checked, skipped = [], 0, []
    for d in argv:
        if not os.path.isfile(os.path.join(d, "SKILL.md")):
            skipped.append(d); continue
        all_errs += check(d); checked += 1
    for s in skipped:
        print(f"skip (no SKILL.md, placeholder): {s}")
    if all_errs:
        print("\n".join(all_errs)); sys.exit(1)
    print(f"OK — {checked} skill(s) valid, {len(skipped)} skipped")

if __name__ == "__main__":
    main(sys.argv[1:] or glob.glob("skills/*"))
