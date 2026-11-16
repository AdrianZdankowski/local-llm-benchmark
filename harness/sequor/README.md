# SEQUOR

Multi-turn constraint following: real user constraints (format, length, tone, persona) are introduced, replaced and accumulated over 50 fixed user turns, and the model must keep obeying them. An LLM judge checks each active constraint at selected turns. No user simulator (the user turns are pre-written).

| | |
|---|---|
| Repository | https://github.com/deep-spin/SEQUOR (code and data; no HF dataset) |
| Pinned commit | `6574f28abcc128f2a497ef8a7bf5b628aa432903` (2026-09-29; `data/` unchanged since the first commit, 2026-05-07) |
| License | none stated (no LICENSE file). Constraints derive from LMSYS-Chat-1M, personas from PersonaHub. Private evaluation only; commit conversation ids only. |
| Our patch | `sequor-eval-turns.patch` |

## Setup

```bash
git clone https://github.com/deep-spin/SEQUOR external/sequor
git -C external/sequor checkout 6574f28abcc128f2a497ef8a7bf5b628aa432903
git -C external/sequor apply ../../harness/sequor/sequor-eval-turns.patch
uv venv external/sequor/.venv --python 3.12
uv pip install --python external/sequor/.venv jsonargparse==4.42.0 Jinja2==3.1.6 matplotlib==3.10.7 \
  numpy==2.2.6 openai==2.30.0 pandas==2.3.2 seaborn==0.13.2 tqdm==4.67.1
```

This is the runtime subset of the pinned `requirements.txt`; vllm, datatrove, transformers and datasets are only needed for data creation and local serving. Use the plain CLI (`multi_if/cli.py`), not `submit_*.py` (those generate SLURM/sglang wrappers).

## What the patch does

1. Adds `--eval_turns "[1,10,20,30,40,50]"` to `evaluate` and `evaluate_task`. Only the listed turns call the judge; other turns get a placeholder row without judgments, so turn indices stay aligned and the official scorer ignores them.
2. Makes `_is_context_length_error` recognise llama-server's message ("exceeds the available context size"). Without it, a context overflow burns 20 retries and records an error turn instead of the official sliding window (drop the oldest turn pair).

## Run

The ids in `data/splits/sequor.json` are testset paths relative to `external/sequor/data/testsets/` (e.g. `add/step_size_10/conversation_100_1`). Copy the selected files into `data/raw/sequor/selected/` with the same layout; the first path component is the regime (`single tuples replace add everything`):

```bash
python - <<'EOF'
import json, shutil
from pathlib import Path
for i in json.load(open("data/splits/sequor.json"))["ids"]:
    dst = Path("data/raw/sequor/selected", i + ".jsonl")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path("external/sequor/data/testsets", i + ".jsonl"), dst)
EOF
```

```bash
export BENCH_BASE_URL=http://127.0.0.1:8080/v1 BENCH_MODEL=qwen35-9b
export JUDGE_BASE_URL=... JUDGE_MODEL=...
export PYTHONPATH=external/sequor PYTHONUTF8=1
PY=external/sequor/.venv/bin/python
OUT=runs/sequor/$BENCH_MODEL
mkdir -p $OUT
for R in single tuples replace add everything; do
  # 1) model under test: 50 turns, full history each turn
  $PY external/sequor/multi_if/cli.py generate_responses \
    --run_dir $OUT/$R --output_dir $OUT/$R/chat --testset_dir data/raw/sequor/selected/$R \
    --api_url $BENCH_BASE_URL --api_model $BENCH_MODEL --api_key local \
    --max_turns 50 --max_tokens 8192 --batch_size 30 --max_concurrent 2 | tee $OUT/$R.generate.log
  # 2) constraint judge on the judged turns only
  $PY external/sequor/multi_if/cli.py evaluate \
    --run_dir $OUT/$R --testset_dir data/raw/sequor/selected/$R --output_dir $OUT/evals/$R \
    --api_url $JUDGE_BASE_URL --api_model $JUDGE_MODEL --api_key local \
    --max_turns 50 --eval_turns "[1,10,20,30,40,50]" --max_concurrent 4
  # 3) optional constraint-blind task-completion judge
  $PY external/sequor/multi_if/cli.py evaluate_task \
    --run_dir $OUT/$R --testset_dir data/raw/sequor/selected/$R --output_dir $OUT/task_evals/$R \
    --api_url $JUDGE_BASE_URL --api_model $JUDGE_MODEL --api_key local \
    --max_turns 50 --eval_turns "[1,10,20,30,40,50]" --max_concurrent 4
done
# 4) verdict extraction and official scores
$PY external/sequor/multi_if/process_evals.py --src-root $OUT/evals --dst-root $OUT/processed_evals
$PY external/sequor/multi_if/cli.py compute_eval_scores_tree --root_dir $OUT/processed_evals --output_dir $OUT/eval_scores
$PY external/sequor/multi_if/process_evals.py --src-root $OUT/task_evals --dst-root $OUT/processed_task_evals
$PY external/sequor/multi_if/cli.py compute_eval_scores_tree --root_dir $OUT/processed_task_evals --output_dir $OUT/task_scores
```

`--max_concurrent` of `generate_responses` = llama-server `PARALLEL`. Runs and evals resume from existing files.

## Calls per conversation

- Model under test: 50 chat completions with growing context (up to 8,192 output tokens each).
- Constraint judge: one call per active constraint per judged turn, 6–18 per conversation (1–3 active constraints × 6 turns).
- Task judge (optional): 6.
- Simulator: 0.

## Score

Turn success = all constraints active at that turn judged satisfied (official `_turn_success`). Headline: pooled constraint-following rate over all judged turns = Σ`successful_turns` / Σ`total_turns` over every `*_eval_scores.json` in `$OUT/eval_scores/`. Also report the per-regime rate, the per-turn rate (turn 50 − turn 1 = drift) and the task-completion rate. Do not use `avg_turns_without_error` (breaks with sparse judging). Not comparable with the paper (different judge, subset of conversations, 6 of 50 turns judged).

## Known issues

- **Use a local host in `BENCH_BASE_URL`** (`127.0.0.1` or `localhost`): `conversation.py` sleeps 20 s before every turn for any other host (an upstream rate-limit workaround). With a remote GPU, use an SSH tunnel (`infra/lab/tunnel.sh`).
- **Context.** History grows over 50 turns; give llama-server at least 32k per slot (64k is better; the paper used 131k–256k). On overflow the oldest turn pair is dropped. Grep the generate logs for "Context length exceeded" and report how many turns were truncated.
- **Error turns.** Failed turns are stored as `"[Error: Unable to generate response]"` and count as judged failures; check for them before scoring.
- **Reasoning.** Only `message.content` is stored. Keep llama-server's default reasoning separation; with `--reasoning-format none`, raw thinking text would be judged.
- **Cost.** Each conversation takes minutes even for small models (pilot: about 3–7 min per 50-turn conversation for 2B–9B models), so only 2 models finished SEQUOR in the pilot.
