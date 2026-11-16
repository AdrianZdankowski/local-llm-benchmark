#!/bin/sh
# Start llama-server for one model with the benchmark protocol enforced server-side:
# thinking off (chat_template_kwargs), vendor sampling as server defaults, fixed seed,
# GPU/CPU split chosen by llama.cpp (--fit on).
#
# Usage: sh infra/llama_server/serve.sh <model-key | path/to/model.gguf> [port]
#   model-key  a key from configs/models.json (sampling + kwargs are read from there)
#   .gguf path any GGUF; no sampling flags, kwargs from CHAT_TEMPLATE_KWARGS
#
# Environment (defaults in brackets):
#   BENCH_ROOT     repository root                        [two levels above this script]
#   MODELS_DIR     directory with GGUF files               [$BENCH_ROOT/models]
#   LLAMA_SERVER   llama-server binary                     [$BENCH_ROOT/llama.cpp/build/bin/llama-server]
#   CTX            total context (split across slots)      [65536]
#   PARALLEL       number of slots (-np)                   [2]
#   THREADS        CPU threads                             [nproc]
#   HOST           bind address                            [127.0.0.1]
#   SEED           sampling seed                           [20261116]
#   CHAT_TEMPLATE_KWARGS  kwargs for a raw .gguf path      [{"enable_thinking":false}]
#   GUARD          optional script run first; non-zero exit aborts (e.g. infra/lab/guard.sh)
set -e
[ -n "$1" ] || { echo "usage: $0 <model-key|file.gguf> [port]" >&2; exit 2; }
BENCH_ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
MODELS_DIR="${MODELS_DIR:-$BENCH_ROOT/models}"
LLAMA_SERVER="${LLAMA_SERVER:-$BENCH_ROOT/llama.cpp/build/bin/llama-server}"
PORT="${2:-8080}"
if [ -n "$GUARD" ]; then sh "$GUARD"; fi

case "$1" in
  *.gguf)
    MODEL="$1"
    ALIAS="$(basename "$1" .gguf)"
    KWARGS='{"enable_thinking":false}'
    [ -n "$CHAT_TEMPLATE_KWARGS" ] && KWARGS="$CHAT_TEMPLATE_KWARGS"
    SAMPLING=""
    ;;
  *)
    # Prints three lines: GGUF file name, chat_template_kwargs JSON, sampling flags.
    CFG="$(python3 - "$BENCH_ROOT/configs/models.json" "$1" <<'EOF'
import json, sys
models = json.load(open(sys.argv[1], encoding="utf-8"))
m = models.get(sys.argv[2])
if not isinstance(m, dict):
    sys.exit(f"unknown model key {sys.argv[2]!r} (see configs/models.json)")
flags = {"temperature": "--temp", "top_p": "--top-p", "top_k": "--top-k", "min_p": "--min-p"}
print(m["gguf_file"])
print(json.dumps(m.get("chat_template_kwargs", {}), separators=(",", ":")))
print(" ".join(f"{flags[k]} {v}" for k, v in m.get("sampling", {}).items() if k in flags))
EOF
)"
    MODEL="$MODELS_DIR/$(echo "$CFG" | sed -n 1p)"
    KWARGS="$(echo "$CFG" | sed -n 2p)"
    SAMPLING="$(echo "$CFG" | sed -n 3p)"
    ALIAS="$1"
    ;;
esac

[ -f "$MODEL" ] || { echo "model file not found: $MODEL" >&2; exit 1; }
echo "serving $ALIAS ($MODEL) port=$PORT kwargs=$KWARGS sampling=$SAMPLING"
# shellcheck disable=SC2086  # SAMPLING is a list of flags
exec "$LLAMA_SERVER" \
  -m "$MODEL" --alias "$ALIAS" --host "${HOST:-127.0.0.1}" --port "$PORT" \
  --jinja --chat-template-kwargs "$KWARGS" $SAMPLING --seed "${SEED:-20261116}" \
  -c "${CTX:-65536}" -np "${PARALLEL:-2}" --fit on -fa on --cache-type-k q8_0 --cache-type-v q8_0 \
  --threads "${THREADS:-$(nproc)}" --metrics
