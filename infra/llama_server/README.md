# llama-server

Scripts that build llama.cpp, download the GGUF files and serve one model under test behind an OpenAI-compatible endpoint (`/v1/chat/completions`). All harnesses in `harness/` talk to this endpoint through `BENCH_BASE_URL` / `BENCH_MODEL`.

Run the scripts from the repository root on a Linux machine with an NVIDIA GPU, CUDA toolkit, `cmake`, `git`, `python3` and [uv](https://docs.astral.sh/uv/). On shared lab machines, follow `infra/lab/README.md` first and set `GUARD=infra/lab/guard.sh`.

## Protocol

Every model is served with the same protocol, enforced by `serve.sh` so that each harness gets it even when it cannot set sampling itself:

| Setting | Value |
|---|---|
| Quantisation | Q4_K_M (gpt-oss-20b: its native MXFP4 release; Gemma 4 26B: Unsloth UD-Q4_K_M) |
| Thinking | off, via `--chat-template-kwargs` from `configs/models.json` (gpt-oss: `reasoning_effort: low`, Muse: `reasoning_strength: low`) |
| Sampling | vendor-recommended non-thinking settings from `configs/models.json`, as server defaults (a harness may still override per request) |
| Seed | `--seed 20261116` |
| GPU/CPU split | automatic, `--fit on` (large models are partly offloaded to the CPU) |
| Context | `-c 65536 -np 2`, so 32k tokens per slot; flash attention, q8_0 KV cache |
| Templates | `--jinja` (needed for tool calls) |

## setup_llamacpp.sh

Clones and builds llama.cpp with CUDA into `llama.cpp/` (gitignore it). The build commit is written to `llama.cpp/build-version.txt`; cite it in reports.

```bash
CUDA_ARCH=89 sh infra/llama_server/setup_llamacpp.sh                     # RTX 40xx
CUDA_ARCH=86 LLAMA_CPP_REF=<commit> sh infra/llama_server/setup_llamacpp.sh
```

| Variable | Default | Description |
|---|---|---|
| `LLAMA_CPP_DIR` | `llama.cpp` | Clone and build directory |
| `LLAMA_CPP_REF` | latest | Commit or tag to build |
| `CUDA_ARCH` | `89` | `CMAKE_CUDA_ARCHITECTURES` (86 = RTX 30xx, 89 = RTX 40xx) |
| `JOBS` | `nproc` | Parallel build jobs |

## download_models.sh

Downloads the GGUF file of each requested key (`gguf_repo` + `gguf_file` in `configs/models.json`). Existing files are skipped.

```bash
sh infra/llama_server/download_models.sh qwen35-9b gemma4-12b
MODELS_DIR=/path/to/models sh infra/llama_server/download_models.sh all
```

| Variable | Default | Description |
|---|---|---|
| `MODELS_DIR` | `models` | Target directory (gitignore it) |
| `HF_HOME` | huggingface_hub default | Download cache; put it on the same filesystem as `MODELS_DIR` |
| `HF_CMD` | `uv tool run --from huggingface_hub hf` | Hugging Face CLI |

The largest file is about 17 GB (Muse Glimmer 30B).

## serve.sh

```bash
sh infra/llama_server/serve.sh qwen35-9b 8080        # key from configs/models.json
sh infra/llama_server/serve.sh models/other.gguf 8081 # any GGUF, thinking off, llama.cpp default sampling
```

The model key becomes the server's model name (`--alias`), so use the same string as `BENCH_MODEL`. The server binds to `127.0.0.1`; reach it from another machine through an SSH tunnel (`infra/lab/tunnel.sh`). Check readiness with `curl http://127.0.0.1:8080/health` before starting a harness: while the model loads, the server answers `503 Loading model`, which several harnesses record as a failed item.

| Variable | Default | Description |
|---|---|---|
| `MODELS_DIR` | `models` | Where the GGUF files are |
| `LLAMA_SERVER` | `llama.cpp/build/bin/llama-server` | Server binary |
| `CTX`, `PARALLEL` | `65536`, `2` | Total context and slots; keep at least 32k per slot for the multi-turn benchmarks |
| `THREADS` | `nproc` | CPU threads |
| `HOST` | `127.0.0.1` | Bind address |
| `SEED` | `20261116` | Sampling seed |
| `CHAT_TEMPLATE_KWARGS` | `{"enable_thinking":false}` | Only for a raw `.gguf` path |
| `GUARD` | none | Script run before starting; a non-zero exit aborts |

Match the harness concurrency to `PARALLEL`.
