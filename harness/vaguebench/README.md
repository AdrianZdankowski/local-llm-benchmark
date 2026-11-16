# VagueBench

Does the assistant ask for clarification on underspecified everyday requests, and how much of the user's hidden intent does its final answer cover? An LLM judge classifies ask/answer behaviour and scores coverage; the same judge endpoint plays the simulated user who reveals hidden details when asked.

Not to be confused with the unrelated embodied-agent "VagueBench" (arXiv 2611.03765).

| | |
|---|---|
| Code | https://github.com/zhangrongyu0101/VagueBench, commit `af4587d6584cad36cba85d42fba4eef2a80bde6d` (2026-11-02) |
| Data | https://huggingface.co/datasets/rongyu0101/VagueBench, revision `62d4cc6f17cb5efaa46da02e7d42bbf64c96aa02`; `VagueBench_en.jsonl`, 750 rows, sha256 `77d025b671d83a0cd0730c9d590d4efe18d5539eaef90aabd7d6fb806b334265` |
| License | `apache-2.0` only as an HF card tag; no LICENSE in the repo, the paper says "for research purposes". Private evaluation; check before redistributing. |
| Our files | `vaguebench_config.py` (writes the harness config from the env vars; no upstream patch) |

## Setup

```bash
git clone https://github.com/zhangrongyu0101/VagueBench external/vaguebench    # Windows: add -c core.autocrlf=false
git -C external/vaguebench checkout af4587d6584cad36cba85d42fba4eef2a80bde6d
uv venv external/vaguebench/.venv --python 3.12
uv pip install --python external/vaguebench/.venv -r external/vaguebench/requirements.txt
```

The dataset has 250 scenarios × 3 variants (`group`): **A** complete query, **B** intent hidden, **C** intent and details hidden. `data/splits/vaguebench.json` keeps whole scenarios with all three variants (the groups are paired). `scripts/download_fresh_sources.py --sources vaguebench` fetches `data/raw/vaguebench/VagueBench_en.jsonl`; `evaluate.py --input` takes the original records unchanged, so write the selected ones to a separate file:

```bash
python - <<'EOF'
import json
ids = {i.removeprefix("vaguebench-") for i in json.load(open("data/splits/vaguebench.json"))["ids"]}
src, dst = "data/raw/vaguebench/VagueBench_en.jsonl", "data/raw/vaguebench/VagueBench_en.selected.jsonl"
with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8", newline="\n") as out:
    out.writelines(line for line in f if json.loads(line)["sample_id"] in ids)
EOF
```

## Run

```bash
export BENCH_BASE_URL=http://127.0.0.1:8080/v1 BENCH_MODEL=qwen35-9b BENCH_API_KEY=local
export JUDGE_BASE_URL=... JUDGE_MODEL=... JUDGE_API_KEY=local
export VAGUEBENCH_MAX_TURNS=5          # repo default; the paper uses 10. Keep it fixed across models.
python harness/vaguebench/vaguebench_config.py runs/vaguebench/$BENCH_MODEL/config.json
external/vaguebench/.venv/bin/python external/vaguebench/evaluate.py \
  --input  data/raw/vaguebench/VagueBench_en.selected.jsonl \
  --config runs/vaguebench/$BENCH_MODEL/config.json \
  --output runs/vaguebench/$BENCH_MODEL/results.jsonl
```

Smoke test first with `--limit 3` and a different `--output` (the script never overwrites an output file). Config: target temperature 0.0; judge temperature 0.1 with `json_mode` (needs `response_format` support). Samples run sequentially.

## Calls per item

With k = clarification rounds (0..`VAGUEBENCH_MAX_TURNS`):

| Role | Calls |
|---|---|
| Model under test | 1 + k |
| Judge, behaviour classifier | 1 + k |
| Judge, coverage | 1 |
| Simulated user (judge endpoint) | k |

8B–30B models rarely ask (k = 0 for almost every item), so expect about 1 model call and 2 judge calls per item. Contexts are a few thousand tokens.

## Score

From `results_metrics.json`:

- **Coverage** (official metric 3, `metric3_coverage`): per item precision = covered / (covered + extra), recall = covered / (gold intents + gold details); F1 averaged per group. **Headline: coverage F1 on B ∪ C** = mean of `metric3_coverage.B.f1` and `.C.f1`; A coverage F1 is the reference ceiling.
- **Asking** (official metric 1, `metric1_should_ask`): `recall_B`, `recall_C` (Ask% on vague queries), over-asking rate on A (FP / number of A items), and metric 2 `avg_turns_B` / `avg_turns_C`. `did_ask` is the first-turn behaviour label. Expect Ask% near 0–2% for this model class.

Not comparable with the paper (different judge and simulator, possibly different T_max).

## Known issues

- **Failed samples are dropped from the metrics** (`status: error`, `metric_denominator: successful_samples_only`). Report `counts.failed`, re-run the failed ids into a new output file, and compare models only on items that succeeded for all of them. In the pilot all errors came from the model-under-test side (`error_stage: target`: `APIConnectionError`, HTTP 500 `InternalServerError` from llama-server, one `ValueError`); they hit Gemma 4 26B (5 errors) and Qwen3.5-2B (1).
- **`finish_reason` must be `stop`.** `evaluate.py` sends no `max_tokens`; do not cap generation on the server (`-n`), or long answers fail the sample.
- **Reasoning.** Keep llama-server's default reasoning separation so `content` holds only the answer.
- **The judge also plays the user.** The paper used a separate simulator model; this is the repo default.
