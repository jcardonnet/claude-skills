#!/usr/bin/env bash
# Regenerate all lockstep-derived files from rule-registry.yaml, then re-sync the
# standalone top-level copies. Run from anywhere: bash tools/build.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../references"

python3 "$HERE/gen_registry_md.py"
rm -f critic-prompts/*.md
python3 "$HERE/gen_critic_prompts.py"

# standalone top-level copies live two levels up (outputs/)
cp rule-registry.yaml "$HERE/../../rule-registry.yaml"
cp rule-registry.md   "$HERE/../../rule-registry.md"
echo "build complete"
