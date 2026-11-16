#!/bin/sh
# Download GGUF files for model keys listed in configs/models.json (gguf_repo + gguf_file).
#
# Usage: sh infra/llama_server/download_models.sh <key> [<key> ...]
#        sh infra/llama_server/download_models.sh all
#
# Environment (defaults in brackets):
#   BENCH_ROOT  repository root                      [two levels above this script]
#   MODELS_DIR  target directory for GGUF files      [$BENCH_ROOT/models]
#   HF_HOME     Hugging Face cache                   [huggingface_hub default]
#   HF_CMD      Hugging Face CLI                     [uv tool run --from huggingface_hub hf]
#   GUARD       optional script run first; non-zero exit aborts (e.g. infra/lab/guard.sh)
set -e
[ -n "$1" ] || { echo "usage: $0 <key>... | all" >&2; exit 2; }
BENCH_ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
MODELS_DIR="${MODELS_DIR:-$BENCH_ROOT/models}"
HF_CMD="${HF_CMD:-uv tool run --from huggingface_hub hf}"
if [ -n "$GUARD" ]; then sh "$GUARD"; fi
mkdir -p "$MODELS_DIR"

# One "<key> <repo> <file>" line per requested key; fails on an unknown key.
LIST="$(python3 - "$BENCH_ROOT/configs/models.json" "$@" <<'EOF'
import json, sys
models = {k: v for k, v in json.load(open(sys.argv[1], encoding="utf-8")).items() if isinstance(v, dict)}
keys = list(models) if sys.argv[2:] == ["all"] else sys.argv[2:]
for k in keys:
    if k not in models:
        sys.exit(f"unknown model key {k!r} (see configs/models.json)")
    print(k, models[k]["gguf_repo"], models[k]["gguf_file"])
EOF
)"

echo "$LIST" | while read -r key repo file; do
  if [ -f "$MODELS_DIR/$file" ]; then echo "exists: $key ($file)"; continue; fi
  echo "downloading $key: $repo/$file"
  # shellcheck disable=SC2086  # HF_CMD may contain several words
  $HF_CMD download "$repo" "$file" --local-dir "$MODELS_DIR"
done
echo DOWNLOAD_OK
