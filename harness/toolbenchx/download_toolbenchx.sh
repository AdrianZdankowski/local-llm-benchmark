#!/usr/bin/env bash
# Download ToolBench-X data from Hugging Face at a pinned revision and unpack it into
# <out_dir>/{tasks,tools,tools_exception}. The data is research-only: do not modify,
# redistribute or commit it.
#
# Usage: bash harness/toolbenchx/download_toolbenchx.sh [out_dir]    (default: data/raw/toolbenchx)
set -euo pipefail
REV=faaf5e8f7b71206c7fe60d015460dc5433fc0185
OUT="${1:-data/raw/toolbenchx}"
mkdir -p "$OUT"
for f in README.md tasks.zip tools.zip tools_exception.zip; do
  curl -sSfL -o "$OUT/$f" "https://huggingface.co/datasets/Foreverskyou/ToolBench-X/resolve/$REV/$f"
done
for z in tasks tools tools_exception; do
  rm -rf "${OUT:?}/$z"
  unzip -q -o "$OUT/$z.zip" -d "$OUT"
done
rm -rf "${OUT:?}/__MACOSX"  # macOS resource-fork files shipped in tasks.zip
(cd "$OUT" && sha256sum README.md tasks.zip tools.zip tools_exception.zip > SHA256SUMS)
cat "$OUT/SHA256SUMS"
