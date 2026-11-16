# ToolBench-X

Multi-step tool use with executable Python tools that carry injected reliability hazards (execution, output, cross-source, invocation and specification faults). The agent must recover and return one exact scalar answer, checked by exact string match. No judge, no simulator.

| | |
|---|---|
| Code | https://github.com/Foreverskyou/ToolBench-X, commit `125c30611fbdf85d6e7bf5b4a22dceb5fa8da58d` (2026-09-22), unmodified |
| Data | https://huggingface.co/datasets/Foreverskyou/ToolBench-X, revision `faaf5e8f7b71206c7fe60d015460dc5433fc0185` (2026-07-24) |
| License | code: MIT. Data: academic research only; without approval it may not be distributed, published, copied or modified. Commit task ids only, never `data/raw/toolbenchx/`. |
| Our files | `download_toolbenchx.sh` (pinned data download) |

## Setup

```bash
git clone https://github.com/Foreverskyou/ToolBench-X external/toolbenchx
git -C external/toolbenchx checkout 125c30611fbdf85d6e7bf5b4a22dceb5fa8da58d
uv venv external/toolbenchx/.venv --python 3.11
uv pip install --python external/toolbenchx/.venv -r external/toolbenchx/requirements.txt
bash harness/toolbenchx/download_toolbenchx.sh            # -> data/raw/toolbenchx/{tasks,tools,tools_exception}
```

The benchmark is the 1,106 tasks (of 2,610 candidates) that have a hazard tool file in `tools_exception/`; the runner keeps exactly these by default ("kept 1106/2610").

The tool `.py` files from the dataset are imported and executed in-process. Run the harness only inside its venv on the benchmark machine.

## Run

Main setting: `baseline` mode on `tools_exception` (equivalent to no-hint).

```bash
export BENCH_BASE_URL=http://127.0.0.1:8080/v1 BENCH_MODEL=qwen35-9b
export PYTHONUTF8=1        # the runner prints emoji
external/toolbenchx/.venv/bin/python external/toolbenchx/run_evalscope_local_runtime.py \
  --mode baseline \
  --tasks-dir data/raw/toolbenchx/tasks --tools-dir data/raw/toolbenchx/tools_exception \
  --model "$BENCH_MODEL" --api-url "$BENCH_BASE_URL" --api-key "${BENCH_API_KEY:-EMPTY}" \
  --max-rounds 30 --max-workers 2 --fail-seed 7 --temperature 0 --request-timeout 600 \
  --output runs/toolbenchx/$BENCH_MODEL/baseline.json \
  --summary-output runs/toolbenchx/$BENCH_MODEL/summary.json
```

- `--tools-dir` must contain the string `tools_exception` (the loader keys on it).
- `--fail-seed 7` fixes the hazard randomness (paper value). `--max-rounds 30` is the code default.
- `--temperature 0`: one project-wide value for this benchmark; record it.
- `--max-tokens` is ignored by the runner (every call uses 8,192).
- A single task: `--task-id task_1 --pattern "sequential/Commerce__Transactions/*.json"`.
- `data/splits/toolbenchx.json` lists all 1,106 task keys (`<split>/<topic>/<subtopic>/<task_id>`, equal to the runner's `task_key`); the default run covers exactly these.
- Optional: `--mode ab --hint-catalog data/raw/toolbenchx/tools_exception/exception_hints_catalog.json` adds the with-hint condition (doubles the cost; not needed for the headline).

## Calls per task

Each round makes 1 policy call (JSON decision, no `tools`); a tool round adds 1 argument-generation call (`tools=[one function]` with an object `tool_choice`) and possibly 1 fallback call. Typically 5–8 rounds, about 9–15 model calls per task; cap 30 rounds. The policy prompt re-embeds all tool results so far: plan for 16k–32k context per slot. Judge and simulator calls: 0.

## Score

`--output` JSON: `results.results[]` per task (`task_key`, `final_answer`, `expected_answer`, `success`, `error`, trajectory) and `exact_match.exact_matches`. Accuracy = exact matches / number of tasks, where a task passes when `str(final_answer).strip() == str(expected_answer).strip()` (case-sensitive). Break down by split (`task_key` prefix: sequential / parallel / mixture), topic and hazard category. The harness may substitute a scalar extracted from tool outputs for the model's answer (`_finalize_answer_with_hint_guardrails`); this is part of the official protocol and identical for all models.

## Known issues

- **The `error` field is not a technical-error flag.** It is set for every failed task, including intended hazards (`TimeoutError injected at …`, `injected ConnectionError …`) and wrong answers (`Final answer does not match …`). Count technical errors separately by message.
- **Technical errors seen in the pilot** (they lower the score of the affected model and are not model failures):
  - `Error code: 503 … Loading model`: the run started before llama-server finished loading. Wait for `/health` to return OK first.
  - `api-primary-non-200; api-fallback-error: HTTP Error 403: Forbidden`: some tools make real outbound HTTP requests that the remote service refuses; this depends on the network and affected every model on the same tasks.
  - `Connection error.` / connection reset by the remote host: llama-server or the SSH tunnel dropped a long request. Raise `--request-timeout` (default 120 s) for slow, CPU-offloaded models and keep the tunnel alive.
- **Upstream data defects** (same for every model): `parallel/Commerce__Transactions/Cart_and_checkout_issue_support/task_2` always fails (its tool module raises `NameError: dataclass` at import); 78 tools listed in `tools_used` across tasks have no matching function and are left out of the runtime catalog.
- **`tool_choice` object.** llama-server is expected to accept only string `tool_choice` values (`auto`/`none`/`required`) and to treat the object form like `auto` (not verified); the harness then falls back to JSON parsed from `content`, then to a plain-JSON prompt. Check `llm_trace` in a smoke-test output.
