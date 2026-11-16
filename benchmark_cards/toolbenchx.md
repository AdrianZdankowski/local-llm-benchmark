# ToolBench-X

Category: agents (tool use). "Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability" (Tian, Shi, Zhao; arXiv 2606.25819). Multi-step tasks with executable Python tools that carry injected hazards; the agent must recover and return one exact scalar answer.

| | |
|---|---|
| Source | code https://github.com/Foreverskyou/ToolBench-X, commit `125c30611fbdf85d6e7bf5b4a22dceb5fa8da58d`; data HF `datasets/Foreverskyou/ToolBench-X`, revision `faaf5e8f7b71206c7fe60d015460dc5433fc0185` |
| Data date | repo created 2026-06-23, data uploaded 2026-07-24 |
| License | code MIT; data academic research only, no distribution, publication, copying or modification without approval. We commit task ids only. |
| Size | 1,106 tasks with a hazard tool file (378 sequential, 358 parallel, 370 mixture) out of 2,610 candidates |
| Run | `harness/toolbenchx/` (official runner, unmodified) |

## Our sampling

All 1,106 tasks (no sampling); the id list is built with the harness's own loader, so it equals what the runner executes. Topics: commerce 234, entertainment 215, health 192, government 172, finance 139, data 138, communication 16. Hazard folders: execution 265, output 264, cross-source 263, invocation 173, specification 141.

## Scoring

Exact string match of the final answer against the expected answer (case-sensitive, stripped), no judge and no simulator. Baseline (no-hint) mode, `--fail-seed 7`, 30 rounds max, temperature 0. Score = exact matches / tasks; breakdown by split, topic and hazard.

## Cost per model

About 9–15 model calls per task (policy call + argument call per round, 5–8 rounds), about 10–17k calls in total; growing context, 16k–32k per slot.

## Caveats

- One task is broken upstream (import error) and 78 listed tools have no implementation; same for every model.
- Some tools make real outbound HTTP requests; in the pilot these returned HTTP 403 on the same tasks for every model. Model loading (HTTP 503) and dropped connections also produced failed tasks. The harness `error` field mixes these technical errors with intended hazards and wrong answers, so count technical errors separately.
- The harness may replace the model's answer with a scalar extracted from tool outputs (official protocol, same for all models).
- Tool code from the dataset runs in-process: use an isolated environment.
