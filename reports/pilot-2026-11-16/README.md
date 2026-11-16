# Pilot run, 2026-11-16

A small end-to-end pilot of the fresh-benchmark track: does every harness run against a local llama-server, do the scores look plausible, and how long does each benchmark take per item? It is **not** a ranking of the models.

Files:

- `results.md`: headline scores with 95% bootstrap CIs, n and errors, plus sanity checks.
- `results.csv`: the same in machine-readable form (one row per model × benchmark).
- `timing.csv`: measured wall time per unit (no host or path information).

No model outputs, judge outputs or logs are included.

## What was run

| Benchmark | Pilot units | Harness |
|---|---|---|
| ListQA | 20 questions | single-turn generation + official scorer with an LLM judge |
| WMT26 | 21 items (7 paragraphs × 3 languages) | single-turn generation + MetricX-24 |
| SlopBench | 4 scenarios × 5 samples = 20 generations | official scorer |
| IDEAFix | 20 generations | our implementation of the paper's metrics |
| VagueBench | 21 items (7 scenarios × A/B/C); score on the 14 B/C items | official `evaluate.py` |
| ASTRA-bench | 20 scenarios | official CLI + endpoint patch |
| ToolBench-X | 9 tasks | official runner |
| SEQUOR | 3 conversations × 50 turns | official CLI + sparse-judging patch |

EQ-Bench 4 was not run. Item lists are small subsets of the selections described in `benchmark_cards/`.

**Models.** Scored: Qwen3.5-9B, Gemma 4 12B, gpt-oss-20b, Gemma 4 26B-A4B (tested), Qwen3.5-2B (weak anchor) and Claude Sonnet 5.5 (strong reference, served through an OpenAI-compatible endpoint). Qwen3.6-27B and Muse Glimmer 30B were only timed (see below). Model details: `configs/models.json`.

**Judge.** Claude Sonnet 5.5 behind an OpenAI-compatible endpoint served as the LLM judge (ListQA, VagueBench, SEQUOR) and as the user simulator (ASTRA, VagueBench). The strong reference model is therefore the same model as the judge.

**Hardware.** One NVIDIA RTX 4070 Ti (12 GB) per machine, llama.cpp built with CUDA (`infra/llama_server/`). Models that do not fit in 12 GB are partly offloaded to the CPU by `--fit on`. Four machines in parallel, one model per machine.

**Protocol** (`infra/llama_server/serve.sh`):

- Q4_K_M GGUF weights (gpt-oss-20b: native MXFP4; Gemma 4 26B: UD-Q4_K_M);
- thinking off via chat-template kwargs (gpt-oss: reasoning effort low);
- vendor-recommended sampling as server defaults, fixed seed 20261116; benchmarks that prescribe their own settings override them per request (WMT26: temperature 0; ToolBench-X: temperature 0; VagueBench target: temperature 0);
- 64k context split over 2 slots; harness concurrency 2.

## Timing

`timing.csv` has two phases:

- `pilot`: the scored runs above, concurrency 2. Several rows for one model × benchmark are separate runs; rows with a non-zero `exit_code` are runs that ended with an error.
- `measure`: a separate timing run on a few units per benchmark, concurrency 1, one model at a time on one lab machine. This is the only data for Qwen3.6-27B and Muse Glimmer 30B.

`s_per_unit` is wall time per unit, where the unit is one generation (ListQA, WMT26, SlopBench, IDEAFix), one item including judge and simulator calls (VagueBench), one scenario (ASTRA), one task (ToolBench-X) or one 50-turn conversation (SEQUOR). Judge time for ListQA and MetricX scoring time are not included.

Measured (concurrency 1), seconds per unit:

| model | listqa | wmt26 | slopbench | ideafix | vaguebench | astra | toolbenchx | sequor |
|---|---|---|---|---|---|---|---|---|
| qwen35-2b | 6.3 | 0.3 | 0.6 | 4.6 | 15.0 | 12.0 | 24.0 | 74 |
| qwen35-9b | 3.3 | 1.3 | 2.3 | 9.6 | 26.0 | 15.5 | 51.2 | 164 |
| gptoss-20b | 4.0 | 1.3 | 2.0 | 12.3 | 33.3 | 17.0 | 44.2 | 179 |
| gemma4-26b | 3.0 | 2.0 | 2.7 | 13.3 | 30.3 | 14.0 | 131.8 | 290 |
| qwen36-27b | 97.3 | 15.3 | 23.9 | 91.2 | 235.0 | 67.0 | 100.2 | 351 |
| muse-30b | 77.0 | 41.0 | 31.7 | 119.6 | 108.7 | 72.5 | 99.2 | 585 |

The dense 27–30B models are 5–30× slower than the rest because they do not fit in 12 GB and run partly on the CPU.

## Limitations

- **n ≈ 20 per benchmark** (9 tasks for ToolBench-X, 3 conversations for SEQUOR, 4 domain units for SlopBench). Most confidence intervals overlap; no ranking claims can be made from this pilot.
- **ListQA floor effect.** All local models score 0.065–0.145 F1, and 13 of 20 questions were failed by every model including the strong reference. The full run needs the simple-subset and Format-Correctness breakdowns.
- **ToolBench-X technical errors.** Some failures are not model failures: HTTP 503 while llama-server was still loading the model, HTTP 403 from tools that make real outbound requests, and dropped connections. The Gemma 4 26B score (0.11) is strongly affected by HTTP 503 errors (its run overlapped with model loading) and should not be read as a model result. The harness error count also includes intended hazards, so it is not a clean technical-error count.
- **SEQUOR: only 2 models** (Qwen3.5-9B and Qwen3.5-2B) finished, on 3 conversations; the strong reference run was timed but not scored.
- **ASTRA: the strong reference is excluded** because of an integration error in the endpoint it was served behind; its score (0.22) is not a valid measurement. One scenario failed with HTTP 400 for both Gemma 4 models and was excluded for them.
- **SlopBench and IDEAFix measure style and diversity, not quality.** The strong reference had the worst SlopBench score and a lower IDEAFix diversity than three local models; neither says anything about usefulness.
- **VagueBench errors.** Gemma 4 26B lost 5 items to server-side errors (connection drops, HTTP 500), so its score covers 10 of 14 B/C items.
- **Qwen3.6-27B and Muse Glimmer 30B: timing only.** They were not scored in the pilot.
- **Judge = strong reference.** The same model judged and simulated users for all models, including its own runs; self-preference cannot be ruled out where the judge rates the reference.
- **Anchors misordered.** On most benchmarks the weak anchor (Qwen3.5-2B) is not the lowest; with n ≈ 20 this is within noise, but it means the pilot does not validate the benchmarks' discriminative power.
