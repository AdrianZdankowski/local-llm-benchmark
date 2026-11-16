# ASTRA-bench

Personal-assistant tool use on a simulated phone (contacts, SMS, email, calendar, WhatsApp, calls). An LLM user simulator plays the user and ends the conversation with an `end_conversation` tool call. Scoring is rule-based (milestone graph), no judge.

| | |
|---|---|
| Repository | https://github.com/apple-aiml-research/ml-astra |
| Pinned commit | `d150a8af6a8f5442eaf25ef6dc287464ca1341f0` (2026-10-21; scenarios ship inside the package) |
| License | code: Apple Sample Code License; data: CC BY-NC-ND 4.0 (no modified scenarios may be published; commit scenario names only) |
| Our patch | `astra-endpoint.patch` (3 files, +44/−2) |

## Setup

```bash
git clone https://github.com/apple-aiml-research/ml-astra external/astra
git -C external/astra checkout d150a8af6a8f5442eaf25ef6dc287464ca1341f0
git -C external/astra apply ../../harness/astra/astra-endpoint.patch
uv venv external/astra/.venv --python 3.11
uv pip install --python external/astra/.venv -e "external/astra[agent-all]" tzdata   # tzdata only needed on Windows
```

The install is editable so that the patch is live. Check with `external/astra/.venv/bin/astra_tool_sandbox --help`: `BenchEndpoint` must be listed under `--agent` and `JudgeEndpoint` under `--user`.

## What the patch does

Upstream hard-codes `https://api.openai.com/v1` for every role. The patch:

- adds `--agent BenchEndpoint`: ASTRA's native function-calling agent (`OpenAIAPIAgent`) at `BENCH_BASE_URL` / `BENCH_MODEL` / `BENCH_API_KEY` (default `EMPTY`). It sends `tools=` and expects `message.tool_calls`, so llama-server needs `--jinja`;
- adds `--user JudgeEndpoint`: the user simulator (`OpenAIAPIUser`) at `JUDGE_BASE_URL` / `JUDGE_MODEL` / `JUDGE_API_KEY`;
- reads the playback budget from `ASTRA_PLAY_TIMEOUT_SECONDS` (default 180 s as upstream);
- merges all system messages into one leading system message before each agent request (see known issues);
- skips the playback timer where `signal.SIGALRM` does not exist (Windows), which otherwise crashes the CLI.

## Run

```bash
export BENCH_BASE_URL=http://127.0.0.1:8080/v1 BENCH_MODEL=qwen35-9b        # BENCH_MODEL goes into the output dir name; no "/"
export JUDGE_BASE_URL=... JUDGE_MODEL=...
export ASTRA_PLAY_TIMEOUT_SECONDS=1200 PYTHONUTF8=1

# smoke test: one scenario, check that the agent emits tool_calls and the simulator ends with end_conversation
external/astra/.venv/bin/astra_tool_sandbox --agent BenchEndpoint --user JudgeEndpoint \
  -p 1 -o runs/astra/smoke --scenarios get_contact_count_DAWEI_SHEN

# selected scenarios
external/astra/.venv/bin/astra_tool_sandbox --agent BenchEndpoint --user JudgeEndpoint \
  -p 2 -o runs/astra/$BENCH_MODEL \
  --scenarios $(python -c "import json;print(' '.join(json.load(open('data/splits/astra.json'))['ids']))")
```

- `-p` = worker processes; match it to llama-server `PARALLEL`.
- Do not pass `--llm_evaluation` (optional judge via public paid APIs; not part of our score).
- Sampling cannot be set from the harness (the request carries only `model/messages/tools`); it comes from the llama-server defaults.
- Runs resume from `trajectories/` in the output directory. The CLI exits 1 if any scenario failed to play out.

## Calls per scenario

- Model under test: one call per agent turn, typically 3–8 (cap: 30 sandbox messages per scenario, about 15 agent calls).
- User simulator (judge endpoint): typically 1–3; the first user message is pre-written, the simulator answers each agent→user message and ends with `end_conversation`.
- Context: tool schemas up to about 3k tokens, `get_all_*` tools can return whole databases (up to about 17k tokens). Plan for at least 32k context per slot.

## Score

Output: `runs/astra/<model>/agent_<BENCH_MODEL>_user_<JUDGE_MODEL>_<timestamp>/result_summary.json`. Each `per_scenario_results[]` row has `name`, `similarity` (0–1, rule-based), `exception_type`, `turn_count` and milestone details.

Our score: mean `similarity` over the selected scenarios, with missing or `null` similarity counted as 0; report the number of rows with `exception_type` separately (in the pilot, errored scenarios were excluded and counted). Break down by persona and primary app (strata in `data/splits/astra.json`; the ids are the official scenario names, `name` in the results).

## Known issues

- **Chat template rejects non-leading system messages.** ASTRA inserts extra system messages mid-conversation; the Qwen (and some Gemma) chat templates raise an error for a system message that is not first. The patch merges all system messages into one leading message before each agent request.
- **Simulator must return real tool calls.** After each agent→user message the simulator gets `tools=[end_conversation]`. If the judge endpoint returns the call as text instead of a `tool_calls` entry, the call is silently ignored and the conversation runs to the 30-message cap.
- **Timeout.** The upstream 180 s playback budget is too short for a local model plus a remote simulator; on timeout the scenario is graded on its partial trajectory and `exception_type` is set. Use 1200 s. On Windows there is no playback timeout at all.
- **Empty content.** The agent asserts `content is not None` when there are no tool calls; keep llama-server's default reasoning separation so the answer lands in `content`.
- **Pilot:** one scenario (`JOHN_QUINN_13_…_single_turn_0`) failed with `BadRequestError` (HTTP 400 from llama-server) for both Gemma 4 models; cause not investigated. The strong reference model's ASTRA run was excluded because of an integration error in the endpoint it was served behind (its score is not a valid measurement). Run the smoke test above for every new endpoint.
