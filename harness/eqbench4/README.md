# EQ-Bench 4

Multi-turn emotional-intelligence roleplay: the model under test talks to a simulated user persona for 8 turns per side (16 messages). Models are ranked by blind pairwise judging (both orders), fitted with soft Bradley–Terry on an Elo scale. Not run in the 2026-11-16 pilot.

| | |
|---|---|
| Repository | https://github.com/EQ-bench/eqbench4 |
| Pinned commit | `93dcb7f5d430433ad49d501e672a98bcff2c9678` (2026-09-26); dataset `src/eqbench/datasets/test.json`, 120 scenarios, `generated_at` 2026-05-31 |
| License | BSD-3-Clause + Commons Clause (no selling as a service) |
| Our patch | `eqbench4-own-ladder.patch` |

## What the patch does

1. Adds `run_pair_plan.py`: a fixed-budget round-robin ladder for a small closed set of models (see below). It keeps the official judge prompt, AB+BA order, dimension weighting and soft-BT solver, and changes only which pairs are judged.
2. Adds `config.local.yaml`: every model under test at `${BENCH_BASE_URL}`, the judge/simulator at `${JUDGE_BASE_URL}`. `api_key: sk-local` is a dummy (the harness requires a non-empty key).
3. Adds a 10-line hook (`api_client.py`, `config.py`) that merges `model_creds.<id>.extra_body` into each request, so the vendor sampling from `configs/models.json` reaches llama-server (thinking-off settings are additionally enforced server-side by `infra/llama_server/serve.sh`). It overrides the harness default temperature 0.7 for the model under test.

In EQ-Bench the `model_creds` key is also the model name sent to the endpoint and the name on the ladder. After applying the patch, **rename the `judge-model` key in `external/eqbench4/config.local.yaml` (and `summary_model`) to your `JUDGE_MODEL`**, and use the same name for `--persona-models` and `--judge`. Tested-model keys are the keys of `configs/models.json`; add entries there when the model list changes.

## Setup

```bash
git clone https://github.com/EQ-bench/eqbench4 external/eqbench4
git -C external/eqbench4 checkout 93dcb7f5d430433ad49d501e672a98bcff2c9678
git -C external/eqbench4 apply ../../harness/eqbench4/eqbench4-own-ladder.patch
uv sync --project external/eqbench4
```

`eqbench --compute-elo-only` on an empty directory works without any LLM call (setup check).

## Run

**Step 1: conversations**, once per model (all tested models plus anchors). Load the matching GGUF in llama-server before each run. All result files go to one fresh directory; never use the repo's `results/` (the official ladder).

```bash
export BENCH_BASE_URL=http://127.0.0.1:8080/v1 JUDGE_BASE_URL=... JUDGE_MODEL=...
external/eqbench4/.venv/bin/eqbench --config external/eqbench4/config.local.yaml \
  --evaluated-model qwen35-9b --persona-models $JUDGE_MODEL \
  --disable-pointwise-scoring --skip-elo --skip-summary \
  --parallel 2 --out runs/eqbench4/results/qwen35-9b.json --run-id qwen35-9b
```

Re-running resumes. The printed "FINAL SCORE" is the persona-state average, informational only.

**Step 2: pairwise ladder**, after all result files exist:

```bash
M=qwen35-9b,gemma4-12b,gptoss-20b,gemma4-26b,qwen36-27b,muse-30b
A=qwen35-2b,$JUDGE_MODEL          # weak and strong anchors
P="external/eqbench4/.venv/bin/python external/eqbench4/run_pair_plan.py --config external/eqbench4/config.local.yaml \
   --results-dir runs/eqbench4/results --models $M --anchors $A --judge $JUDGE_MODEL --parallel 4"
$P --dry-run      # prints the plan, no calls
$P                # stage 1
$P --stage 2      # optional: rest of the --max-judge-calls budget (default 3000) on the closest adjacent pairs
```

Output: `runs/eqbench4/results/ladder_pairwise.json` (all comparisons) and `elo_results.json` (ratings with bootstrap CIs). Recompute ratings only: `eqbench --compute-elo-only --results-dir runs/eqbench4/results`.

**Why not the official ELO step.** `eqbench` without `--skip-elo` inserts one model into the existing ladder with an adaptive schedule; adding 8 models one after another gives the early models fewer comparisons and an unbounded number of matchups. `run_pair_plan.py` judges every pair (round robin) on a deterministic, balanced scenario subset (seed 20261116):

| Pair class | Scenarios per pair | Example: 6 tested + 2 anchors |
|---|---|---|
| tested vs tested | 60 (`--n-tt`) | 15 pairs, 900 matchups |
| tested vs anchor | 30 (`--n-ta`) | 12 pairs, 360 matchups |
| anchor vs anchor | 20 (`--n-aa`) | 1 pair, 20 matchups |

Each pair's subset is exactly half generated, half hand-authored scenarios. Each matchup = 2 judge calls (AB + BA): 2,560 calls in stage 1 for the example.

## Calls per model

- Model under test: 120 scenarios × 8 turns = 960 calls.
- Persona simulator (judge endpoint): 960, plus format retries (up to 3 attempts per turn).
- Pairwise judge: 720 per tested model in stage 1 (360 matchups × 2). Judge prompts are long (two 16-message transcripts, hidden monologues, persona card).
- Pointwise trait judging and summaries are switched off.
- llama-server needs at least 16k context per slot (32k recommended); `evaluated_model_timeout` is 600 s and also applies to persona calls.

## Score

Soft Bradley–Terry rating on the Elo scale (`elo` in `elo_results.json`) with bootstrap 95% CI, from our own ladder. The rating is relative: adding or removing a model shifts it, so report rank and CI as well. Not comparable with eqbench.com (different persona model, single judge instead of a 3-judge panel). When the judge model is also the strong anchor, it is judged by itself (self-preference is possible); read its rating as an upper reference only.

## Known issues

- **Simulator refuses the patient role.** In therapy-style scenarios the persona is a patient or client in distress. Safety-tuned judge models sometimes refuse to play that role or break character; the turn then fails format validation (3 attempts) and the scenario stays incomplete. After step 1, count incomplete scenarios per model, re-run (resumes), and report what is left. If refusals persist, use a different simulator model for all models; never mix simulators within one ladder.
- **Subsets.** To reduce simulator load use `--dataset <filtered test.json>`, not `--scenarios N` (that takes the first N scenarios, which are all generated ones).
- **Model ids.** The model id is the llama-server model name and the ladder name; a mismatch between the loaded GGUF and `--evaluated-model` silently mislabels results.
