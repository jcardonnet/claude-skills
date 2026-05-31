#!/usr/bin/env python3
"""Emit each skill as a SELF-CONTAINED, deployable folder (and optional zip).

A monorepo skill may use repo-level dev code (`shared/`) and ships lockstep-generated references
(`rule-registry.md`, `critic-prompts/`) derived from `rule-registry.yaml`. A *deployed* skill must
stand alone: no imports from `shared/`, generated files current, no dev caches. For each skill this:

  1. copies the skill tree (dropping caches and, by default, tests/),
  2. regenerates its lockstep files IN THE COPY (via tools/build.sh) so the bundle is never stale,
  3. vendors the `shared/` package into the bundle iff a bundled module imports it,
  4. verifies self-containment (no `shared` left dangling, no cross-skill `skills.*` imports),
  5. validates structurally (reuses tools/validate_skill.py),
  6. optionally zips to <out>/<skill>.zip.

The source tree is never mutated. Exit code is non-zero if any skill fails.

Usage:
    python tools/bundle.py skills/* --out dist/ [--zip]
                                    [--shared-root shared] [--shared-pkg shared]
                                    [--no-build] [--with-tests]
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# make the sibling validator importable whether run as a script or imported as a module
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_skill  # noqa: E402

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".git"}
EXCLUDE_SUFFIX = {".pyc", ".pyo"}
EXCLUDE_NAMES = {".DS_Store"}
SHARED_DEFAULT = "shared"


def _ignore(with_tests: bool):
    def ignore(dirpath, names):
        drop = set()
        for n in names:
            p = Path(dirpath) / n
            if n in EXCLUDE_DIRS or n in EXCLUDE_NAMES or n.endswith(".egg-info"):
                drop.add(n)
            elif p.suffix in EXCLUDE_SUFFIX:
                drop.add(n)
            elif n == "tests" and p.is_dir() and not with_tests:
                drop.add(n)
        return drop

    return ignore


def copy_tree(src: Path, dst: Path, with_tests: bool) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore(with_tests))


def iter_py(root: Path):
    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        yield p


def top_level_imports(pyfile: Path) -> set[str]:
    """Top-level package of every ABSOLUTE import (relative imports are intra-bundle, ignored)."""
    out: set[str] = set()
    try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def regen_lockstep(bundle: Path) -> str | None:
    """Run the skill's build.sh inside the bundle so generated files match the bundled YAML."""
    if not (bundle / "tools" / "build.sh").is_file():
        return None
    r = subprocess.run(["bash", "tools/build.sh"], cwd=bundle, capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr.strip() or "build.sh failed")


def vendor_shared(bundle: Path, shared_root: Path, shared_pkg: str) -> tuple[list[str], list[str]]:
    """Vendor `shared_root` into the bundle iff a bundled module imports `shared_pkg`.

    Returns (files_that_import_it, errors).
    """
    importers = sorted(
        str(py.relative_to(bundle)) for py in iter_py(bundle) if shared_pkg in top_level_imports(py)
    )
    errs: list[str] = []
    if importers:
        if not shared_root.is_dir():
            errs.append(f"imports `{shared_pkg}` (e.g. {importers[0]}) but shared root {shared_root} not found")
        else:
            copy_tree(shared_root, bundle / shared_pkg, with_tests=False)
    return importers, errs


def verify_self_contained(bundle: Path, shared_pkg: str) -> list[str]:
    errs: list[str] = []
    vendored_prefix = shared_pkg + os.sep
    for py in iter_py(bundle):
        rel = str(py.relative_to(bundle))
        if rel.startswith(vendored_prefix):  # vendored dependency code itself
            continue
        tops = top_level_imports(py)
        if "skills" in tops:
            errs.append(f"{rel}: cross-skill import (`skills...`) — not self-contained")
        if shared_pkg in tops and not (bundle / shared_pkg).is_dir():
            errs.append(f"{rel}: imports `{shared_pkg}` but it was not vendored")
    return errs


def bundle_one(
    skill: Path,
    out: Path,
    shared_root: Path,
    shared_pkg: str,
    do_build: bool,
    with_tests: bool,
    make_zip: bool,
) -> dict:
    dst = out / skill.name
    info: dict = {"skill": skill.name, "out": str(dst), "shared_refs": [], "errors": [], "zip": None}
    copy_tree(skill, dst, with_tests)
    if do_build:
        be = regen_lockstep(dst)
        if be:
            info["errors"].append(f"lockstep regen failed: {be}")
    refs, verrs = vendor_shared(dst, shared_root, shared_pkg)
    info["shared_refs"] = refs
    info["errors"] += verrs
    info["errors"] += verify_self_contained(dst, shared_pkg)
    info["errors"] += validate_skill.check(str(dst))
    info["files"] = sum(1 for p in dst.rglob("*") if p.is_file())
    if make_zip and not info["errors"]:
        zpath = out / f"{skill.name}.zip"
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(dst.rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(out))
        info["zip"] = str(zpath)
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bundle skills as self-contained deployable folders.")
    ap.add_argument("paths", nargs="+", help="skill dirs (entries without SKILL.md are skipped)")
    ap.add_argument("--out", default="dist", help="output dir (default: dist)")
    ap.add_argument("--zip", action="store_true", help="also emit <out>/<skill>.zip")
    ap.add_argument("--shared-root", default=SHARED_DEFAULT, help="repo shared/ dir to vendor from")
    ap.add_argument("--shared-pkg", default=SHARED_DEFAULT, help="import name of the shared package")
    ap.add_argument("--no-build", action="store_true", help="don't regenerate lockstep files in the bundle")
    ap.add_argument("--with-tests", action="store_true", help="keep tests/ in the bundle")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    shared_root = Path(a.shared_root)

    skills, skipped = [], []
    for p in a.paths:
        pp = Path(p)
        (skills if (pp / "SKILL.md").is_file() else skipped).append(pp)
    for s in skipped:
        print(f"skip (no SKILL.md): {s}")
    if not skills:
        print("no skills to bundle")
        return 1

    failed = 0
    for sk in skills:
        info = bundle_one(
            sk, out, shared_root, a.shared_pkg,
            do_build=not a.no_build, with_tests=a.with_tests, make_zip=a.zip,
        )
        ok = not info["errors"]
        failed += not ok
        shared_note = (
            f" | vendored `{a.shared_pkg}` (used by {len(info['shared_refs'])} file(s))"
            if info["shared_refs"] else ""
        )
        zip_note = f" | {info['zip']}" if info["zip"] else ""
        print(f"[{'OK  ' if ok else 'FAIL'}] {info['skill']}: {info['files']} files -> {info['out']}{shared_note}{zip_note}")
        for e in info["errors"]:
            print(f"         - {e}")

    print(f"\nbundled {len(skills) - failed}/{len(skills)} skill(s) into {out}/" + (f"; {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
