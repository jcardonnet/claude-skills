#!/usr/bin/env python3
"""Structural validation for any skill folder.

Checks: frontmatter description <=1024 chars; SKILL.md <=~300 lines; if a rule-registry.yaml exists,
every R-<NS>-<n> id referenced in the skill's *.md files resolves (excluding the JSON placeholder);
and, with --check-build, that the lockstep-derived files are in sync with the registry.

Usage: python tools/validate_skill.py skills/deep-primer skills/other ...
       python tools/validate_skill.py --check-build skills/*"""
import sys, re, glob, os, shutil, subprocess, tempfile, filecmp
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

def check_build_idempotence(skill_dir):
    """Regenerating the lockstep files must reproduce what is committed.

    A non-empty diff means a generated file was hand-edited or the registry changed without a
    rebuild — the drift the lockstep convention exists to prevent. Runs build.sh against a COPY so
    validation never mutates the tree it is validating (a validator with side effects can turn a
    red run green just by being run).
    """
    build = os.path.join(skill_dir, "tools", "build.sh")
    if not os.path.isfile(build):
        return []
    errs = []
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, os.path.basename(skill_dir.rstrip("/")) or "skill")
        shutil.copytree(skill_dir, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        r = subprocess.run(["bash", "tools/build.sh"], cwd=work, capture_output=True, text=True)
        if r.returncode != 0:
            return [f"{skill_dir}: build.sh failed: {r.stderr.strip() or r.stdout.strip()}"]
        for rel in ("references/rule-registry.md",):
            a, b = os.path.join(skill_dir, rel), os.path.join(work, rel)
            if os.path.isfile(b) and not (os.path.isfile(a) and filecmp.cmp(a, b, shallow=False)):
                errs.append(f"{skill_dir}: {rel} is out of sync with rule-registry.yaml (run build.sh)")
        a_dir, b_dir = os.path.join(skill_dir, "references", "critic-prompts"), os.path.join(work, "references", "critic-prompts")
        if os.path.isdir(b_dir):
            names = sorted(set(os.listdir(b_dir)) | set(os.listdir(a_dir) if os.path.isdir(a_dir) else []))
            match, mismatch, errors = filecmp.cmpfiles(a_dir, b_dir, names, shallow=False)
            for n in sorted(mismatch) + sorted(errors):
                errs.append(f"{skill_dir}: references/critic-prompts/{n} is out of sync (run build.sh)")
    return errs


def main(argv):
    check_build = "--check-build" in argv
    argv = [a for a in argv if not a.startswith("--")]
    all_errs, checked, skipped = [], 0, []
    for d in argv:
        if not os.path.isfile(os.path.join(d, "SKILL.md")):
            skipped.append(d); continue
        all_errs += check(d)
        if check_build:
            all_errs += check_build_idempotence(d)
        checked += 1
    for s in skipped:
        print(f"skip (no SKILL.md, placeholder): {s}")
    if all_errs:
        print("\n".join(all_errs)); sys.exit(1)
    print(f"OK — {checked} skill(s) valid{' (lockstep in sync)' if check_build else ''}, {len(skipped)} skipped")

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args if [a for a in args if not a.startswith('--')] else args + glob.glob("skills/*"))
