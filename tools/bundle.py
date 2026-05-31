#!/usr/bin/env python3
"""Emit each skill as a SELF-CONTAINED, deployable folder (Stage 6, Prompt 8).

Why: a deployed skill must be standalone — it cannot import from repo-level shared/. This step vendors
any shared/ code each skill uses into that skill's own folder under dist/, so the result drops cleanly
into claude.ai (upload) or Claude Code (repo skills dir). Mirrors the lockstep discipline: source stays
DRY, the shipped artifact is self-contained.
TODO: detect shared/ imports, copy them in, rewrite imports, run tools/validate_skill.py on each bundle."""
raise NotImplementedError("bundle: implement in Prompt 8")
