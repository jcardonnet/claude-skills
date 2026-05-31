#!/usr/bin/env bash
# Regenerate all lockstep-derived files (rule-registry.md, critic-prompts/*) from
# rule-registry.yaml — the single source of truth. Run from anywhere: bash tools/build.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../references"

python3 "$HERE/gen_registry_md.py"
rm -f critic-prompts/*.md
python3 "$HERE/gen_critic_prompts.py"
echo "build complete"
