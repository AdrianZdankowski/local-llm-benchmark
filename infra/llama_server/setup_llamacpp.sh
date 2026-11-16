#!/bin/sh
# Build llama.cpp (llama-server, llama-bench, llama-cli) with CUDA. Run once per shared filesystem.
#
# Usage: sh infra/llama_server/setup_llamacpp.sh
#
# Environment (defaults in brackets):
#   BENCH_ROOT     repository root                         [two levels above this script]
#   LLAMA_CPP_DIR  clone/build directory                   [$BENCH_ROOT/llama.cpp]
#   LLAMA_CPP_REF  commit or tag to build; empty = latest  []
#   CUDA_ARCH      CMAKE_CUDA_ARCHITECTURES                [89 = RTX 40xx (Ada)]
#   JOBS           parallel build jobs                     [nproc]
#   GUARD          optional script run first; non-zero exit aborts (e.g. infra/lab/guard.sh)
set -e
BENCH_ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$BENCH_ROOT/llama.cpp}"
if [ -n "$GUARD" ]; then sh "$GUARD"; fi

if [ ! -d "$LLAMA_CPP_DIR/.git" ]; then
  git clone https://github.com/ggml-org/llama.cpp.git "$LLAMA_CPP_DIR"
fi
cd "$LLAMA_CPP_DIR"
if [ -n "$LLAMA_CPP_REF" ]; then
  git fetch origin
  git checkout "$LLAMA_CPP_REF"
fi
# Record the exact build commit next to the binaries (cite it in reports).
git log -1 --format='llama.cpp commit %H %cd' | tee build-version.txt
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH:-89}" -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "${JOBS:-$(nproc)}" --target llama-server llama-bench llama-cli
ls -la build/bin/llama-server build/bin/llama-bench
echo BUILD_OK
