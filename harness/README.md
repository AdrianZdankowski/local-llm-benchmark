# Harnesses for the fresh benchmarks

How to run each benchmark of the fresh-benchmark track against a local model. Each directory has a `README.md` (source pin, license, setup, patch, run commands, cost, scoring, known issues) and, where needed, our patch or helper script. Benchmark background is in `benchmark_cards/`.

| Directory | Benchmark | Runner | Our files |
|---|---|---|---|
| `astra/` | ASTRA-bench | official CLI | `astra-endpoint.patch` |
| `sequor/` | SEQUOR | official CLI | `sequor-eval-turns.patch` |
| `toolbenchx/` | ToolBench-X | official runner | `download_toolbenchx.sh` |
| `vaguebench/` | VagueBench | official `evaluate.py` | `vaguebench_config.py` |
| `eqbench4/` | EQ-Bench 4 | official CLI + our ladder | `eqbench4-own-ladder.patch` |
| `listqa/` | ListQA | repo pipeline + official ListQA-Eval code | none |
| `slopbench/` | SlopBench | repo pipeline + official scorer | none |
| `ideafix/` | IDEAFix | repo pipeline + local metrics | none |
| `wmt26-metricx/` | WMT26 General MT | repo pipeline + MetricX-24 | `wmt26_metricx_input.py` (standalone helper) |

## Common conventions

**Endpoints.** Every harness is configured through four environment variables:

| Variable | Meaning | Example |
|---|---|---|
| `BENCH_BASE_URL` | model under test, OpenAI-compatible (`infra/llama_server/serve.sh`) | `http://127.0.0.1:8080/v1` |
| `BENCH_MODEL` | model name at that endpoint (a key from `configs/models.json`) | `qwen35-9b` |
| `JUDGE_BASE_URL` | LLM judge / user simulator, any OpenAI-compatible endpoint | `http://127.0.0.1:8900/v1` |
| `JUDGE_MODEL` | model name at the judge endpoint | |

Optional `BENCH_API_KEY` / `JUDGE_API_KEY` (default `EMPTY` or any dummy value for local servers). The judge endpoint must support `tools` / `tool_calls` (ASTRA user simulator) and `response_format` JSON (VagueBench, ListQA batched judge). Keep the same judge model for every model under test; results with different judges are not comparable.

**Layout.** Run everything from the repository root.

- `external/<benchmark>/`: clone of the official repository at the pinned commit, with its own `uv` virtual environment in `external/<benchmark>/.venv`. Not committed.
- `data/raw/<benchmark>/`: downloaded data. Not committed: the licenses forbid redistribution for most of these benchmarks.
- `data/splits/<benchmark>.json`: our selected item ids (`"ids": [...]`) with the sampling method and seed.
- `runs/`: outputs. Not committed.

**Single-turn benchmarks** (ListQA, SlopBench, IDEAFix, WMT26) run through the repository pipeline instead of an upstream harness: `scripts/download_fresh_sources.py` → `scripts/build_dataset.py` (adapters in `src/mybench/adapters/`) → `scripts/run_benchmark.py --source <source> --model <key>` → `scripts/score.py --source <source> --model <key>`. See `scripts/README.md`; the READMEs here document the prompts and scoring rules those scripts implement.

Commands use Linux paths (`.venv/bin/`). On Windows (Git Bash) use `.venv/Scripts/` and set `PYTHONUTF8=1`.

**Protocol.** Q4_K_M weights, thinking off, vendor-recommended sampling and seed 20261116, all set server-side by `serve.sh`. Strip any leftover `<think>…</think>` from outputs before scoring. Use one llama-server slot per harness worker (`PARALLEL` in `serve.sh` = harness concurrency).
