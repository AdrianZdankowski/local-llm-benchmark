# WMT26 General MT, scored with MetricX-24

Paragraph-level translation from English into Czech, German and Estonian, scored with reference-based MetricX-24 against **human** references only. No LLM judge.

| | |
|---|---|
| Data | https://github.com/wmt-conference/wmt26-general-mt, commit `63aa5d24311a7e7e3e8173528f3771c7e8b4be78` (2026-09-20); `data/wmt26-genmt.jsonl` (also in `data/raw/wmt26/` of this repo) |
| Data license | no LICENSE file; "can be freely used for research purposes", cite the WMT26 Findings paper. Private evaluation; do not redistribute. |
| Metric code | https://github.com/google-research/metricx, commit `fc4978eb064670f7cc33e93ea4f52d38396b8ae6` (2024-12-12), Apache-2.0 |
| Metric model | `google/metricx-24-hybrid-xl-v2p6-bfloat16` (HF sha `1aa765b1705d36c85c9fab40e2f7ce1e0ff69705`), tokenizer `google/mt5-xl` |
| Our files | `wmt26_metricx_input.py` (builds the MetricX input from items + model outputs) |

## References

Use only the `refs` field. **Never use `synthetic_references/`**: those are selected system outputs, including outputs of model families we test. EN→CS and EN→DE references are human post-edits (`refPE`) of Qwen3.5-397B or Gemma-4-31B output, which may favour those families; EN→ET references are human translations from scratch (`refA`). The same source paragraphs are used for all three languages, so EN→ET acts as a control. Report per pair.

## Generation (model under test)

One request per item, one **user** message, no system message: the official WMT26 participant instruction for the pair and domain (`prompt_instruction`, verbatim), a blank line, then the source paragraph with its `<p>` tags. Temperature 0, `max_tokens` 2048 (overrides the server sampling; thinking stays off). Use the final `content` only; strip leftover `<think>…</think>`. Save `{"id": ..., "output": ...}` per line.

## Setup (MetricX)

```bash
git clone https://github.com/google-research/metricx external/metricx
git -C external/metricx checkout fc4978eb064670f7cc33e93ea4f52d38396b8ae6
uv venv external/metricx/.venv --python 3.11
uv pip install --python external/metricx/.venv \
  --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match \
  torch==2.5.1 transformers==4.30.2 sentencepiece==0.1.99 datasets==2.13.1 accelerate==0.30.1 \
  "pyarrow<15" "numpy<2" protobuf==3.20.3 fsspec==2023.9.2
```

On a GPU machine use the CUDA torch index instead of `/whl/cpu`. Two pins beyond the repo's `requirements.txt` are required: `protobuf` 3.20.x (on 4.x the mT5 tokenizer conversion fails with "Descriptors cannot be created directly") and `fsspec` 2023.9.2 (newer versions break `datasets==2.13.1` with "Loading a dataset cached in a LocalFileSystem is not supported"). `mt-metrics-eval` is only needed for the repo's meta-evaluation scripts.

## Run

In this repository (items from the WMT26 human-reference adapter, split `data/splits/wmt26.json`):

```bash
python scripts/build_dataset.py --sources wmt26_humanref --out-dir data/unified_fresh   # never the tracked data/unified/
python scripts/run_benchmark.py --source wmt26_humanref --model $BENCH_MODEL -i data/unified_fresh/translation.jsonl
METRICX_PYTHON=external/metricx/.venv/bin/python python scripts/score.py --source wmt26_humanref --model $BENCH_MODEL -i data/unified_fresh/translation.jsonl
```

Standalone, with `wmt26_metricx_input.py` (items in the selection format below, outputs as `{"id", "output"}` lines):

```bash
python harness/wmt26-metricx/wmt26_metricx_input.py runs/wmt26/$BENCH_MODEL.jsonl runs/wmt26/$BENCH_MODEL.metricx_in.jsonl \
  --items ITEMS.jsonl
export PYTHONPATH=external/metricx PYTHONUTF8=1
external/metricx/.venv/bin/python -m metricx24.predict \
  --tokenizer google/mt5-xl \
  --model_name_or_path google/metricx-24-hybrid-xl-v2p6-bfloat16 \
  --max_input_length 1536 --batch_size 1 \
  --input_file runs/wmt26/$BENCH_MODEL.metricx_in.jsonl \
  --output_file runs/wmt26/$BENCH_MODEL.metricx_out.jsonl
```

The item file needs, per line: `id`, `input.lang_pair`, `input.domain`, `input.source` (with tags) and `reference` (human reference, with tags). `wmt26_metricx_input.py` normalises source, hypothesis and reference the same way (removes `<p>`/`</p>`, `<br>` → newline); a missing answer becomes an empty hypothesis. Smoke test (reference as hypothesis): `python harness/wmt26-metricx/wmt26_metricx_input.py --ref-as-hyp --limit 2 --items ITEMS.jsonl runs/wmt26/smoke.jsonl`, then the same predict command.

Hardware: XL (about 3.7B parameters, 7.5 GB in bf16) fits a 12 GB GPU at batch 1, or runs on CPU (8 threads, 24 GB RAM: a 2-segment test took 143 s end to end including model load; about 200 segments should take well under an hour). If RAM is short, use `google/metricx-24-hybrid-large-v2p6-bfloat16`, but never mix Large and XL scores. If anonymous HF downloads fail with "Repository Not Found", a stale local HF token is the usual cause: set `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`.

## Calls per item

1 model call per item (single turn). Judge: 0. Scoring: 1 MetricX forward pass per item.

## Score

MetricX predicted error in [0, 25], **lower is better**. Report the mean per language pair, per domain and over all items.

## Known issues

- **The floor is not 0.** The hybrid model gives about 3–5 even when the hypothesis equals the reference (smoke test: 5.25 / 3.05 for reference-as-hypothesis vs 17.25 / 14.69 for the untranslated source). Compare models with each other on the same items only.
- There is no official automatic WMT26 metric (the official evaluation was human); MetricX is an approximation, not comparable with the Findings rankings.
- Text only, segment level, no document context (WMT translated whole documents); 41 of 44 social documents come with a screenshot we do not send.
- No Polish; 3 European target languages only.
- `refPE` may favour the Qwen3.5 and Gemma 4 families; compare against the EN→ET `refA` control.
