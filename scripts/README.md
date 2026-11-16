# Scripts

Run all scripts from the repository root with the project's virtual environment (`.venv`).

Setup (once):

```bash
uv pip install --python .venv/Scripts/python.exe -e .
```

The scripts also work without the editable install: they add `src/` to `sys.path` themselves.

Pipeline:

```
data/raw/  --build_dataset.py-->  data/unified/<category>.jsonl  --merge_unified.py-->  data/benchmark.jsonl
data/benchmark.jsonl  --plot_dataset_stats.py-->  reports/figures/*.png
```

## build_dataset.py

Runs the source adapters (`src/mybench/adapters/`) on the raw data, validates every record against the schema (`src/mybench/schema.py`, see `docs/plan_benchmarku.md`, section 2) and writes one JSONL file per category.

```bash
.venv/Scripts/python.exe scripts/build_dataset.py
```

Only selected sources:

```bash
.venv/Scripts/python.exe scripts/build_dataset.py --sources ifbench wmt26
```

| Option | Default | Description |
|---|---|---|
| `--raw-dir` | `data/raw` | Directory with the raw datasets |
| `--out-dir` | `data/unified` | Output directory for `<category>.jsonl` files |
| `--sources` | all | Sources to process: `facts_grounding`, `ifbench`, `marco_mif`, `noveltybench`, `supergpqa`, `wmt26` |

Output: one file per category (`writing`, `info`, `summarization`, `translation`, `chat`). A summary is printed with the number of records per source, the median and maximum prompt length in characters, and the number of skipped examples with the reason (e.g. multimodal or reference-less WMT26 records).

If any record fails validation, an id is duplicated or a raw file is missing, the script prints `[ERROR]` messages, writes nothing and exits with code 1.

## merge_unified.py

Merges the per-category files from `data/unified/` into a single JSONL file. Every record is validated against the schema, ids are checked for uniqueness and each record's `category` must match its file name. Lines are copied unchanged, in the category order from the benchmark plan (writing, info, summarization, translation, chat, agents).

```bash
.venv/Scripts/python.exe scripts/merge_unified.py
```

Only selected categories, to a different file:

```bash
.venv/Scripts/python.exe scripts/merge_unified.py --categories writing info -o data/writing_info.jsonl
```

| Option | Default | Description |
|---|---|---|
| `--in-dir` | `data/unified` | Directory with `<category>.jsonl` files |
| `-o`, `--output` | `data/benchmark.jsonl` | Output file |
| `--categories` | all files found | Categories to include: `writing`, `info`, `summarization`, `translation`, `chat`, `agents` |

Output: the merged file and a summary with the number of records per category and per source. On any error (missing input file, schema error, duplicate id, category mismatch) the script writes nothing and exits with code 1.

## plot_dataset_stats.py

Plots how many prompts the merged dataset contains. Requires `matplotlib` (`uv pip install --python .venv/Scripts/python.exe matplotlib`).

```bash
.venv/Scripts/python.exe scripts/plot_dataset_stats.py
```

Vector output to a different directory:

```bash
.venv/Scripts/python.exe scripts/plot_dataset_stats.py --format svg -o reports/figures_svg
```

| Option | Default | Description |
|---|---|---|
| `-i`, `--input` | `data/benchmark.jsonl` | Merged dataset (output of `merge_unified.py`) |
| `-o`, `--out-dir` | `reports/figures` | Output directory for the charts |
| `--format` | `png` | `png`, `svg` or `pdf` |
| `--dpi` | `150` | Resolution of raster output |

Output:

- `prompts_per_category.<format>`: number of prompts per task category, with the total in the title.
- `prompts_per_source.<format>`: number of prompts per source, grouped and colored by task category.

The script also prints the total and per-category counts. If the input file is missing or empty, it exits with code 1.

## Fresh sources

Sources released after the target models' cutoff live in a separate registry, `FRESH_ADAPTERS` (`src/mybench/adapters/__init__.py`). They are not part of the default build; pass them to `--sources` explicitly.

| Source | Category | Eval | Adapter |
|---|---|---|---|
| `listqa` | info | `llm_judge` (official ListQA element-level grading) | `listqa.py` |
| `vaguebench` | info | `llm_judge` (multi-turn with a simulated user, run via the official harness) | `vaguebench.py` |
| `slopbench` | writing | `metric` (slop index, 5 samples per prompt) | `slopbench.py` |
| `ideafix` | chat | `diversity` (3 samples per prompt) | `ideafix.py` |
| `wmt26_humanref` | translation | `metric` (MetricX-24) | `wmt26_humanref.py` |

`wmt26_humanref` reads the same raw file as `wmt26`, but emits one record per paragraph for EN→cs/de/et (news and social, human references only, social documents as text only). The `wmt26` adapter emits whole documents and skips documents with a screenshot, so it cannot express the paragraph-level selection.

```bash
.venv/Scripts/python.exe scripts/download_fresh_sources.py
.venv/Scripts/python.exe scripts/build_dataset.py --sources listqa vaguebench slopbench ideafix wmt26_humanref --out-dir data/unified_fresh
.venv/Scripts/python.exe scripts/make_splits.py --check
```

### download_fresh_sources.py

Downloads the raw files of `listqa`, `vaguebench`, `slopbench` and `ideafix` into `data/raw/<source>/` from the official sources at pinned revisions (see `data/raw/README.MD`) and verifies their sha256. No authentication. Existing files are only re-verified unless `--force` is given.

| Option | Default | Description |
|---|---|---|
| `--raw-dir` | `data/raw` | Target directory |
| `--sources` | all four | Sources to download |
| `--force` | off | Re-download existing files |

### Splits (`data/splits/`)

`data/splits/<source>.json` holds the evaluation subset of a source as record ids only: `{"source", "seed", "method", "strata", "source_version", "ids"}`. `data/splits/pilot/<source>.json` is the small pilot subset. For the harness-only benchmarks (`astra`, `sequor`, `toolbenchx`, `eqbench4`), whose data stays in their official harness, the ids are the official task ids.

`make_splits.py` recomputes the splits of `listqa`, `vaguebench`, `slopbench` and `ideafix` from built records with the seeded stratified sampler in `src/mybench/sampling.py` (proportional allocation with largest remainder, optional per-stratum minimum). The `wmt26` and pilot splits come from a custom selection procedure described in their `method` field and are not recomputed.

| Option | Default | Description |
|---|---|---|
| `--in-dir` | `data/unified_fresh` | Output of `build_dataset.py` |
| `--out-dir` | `data/splits` | Where to write `<source>.json` |
| `--sources` | all four | Splits to recompute |
| `--check` | off | Compare with the existing files instead of writing; exit code 1 on a difference |

## Running and scoring models

```
data/unified_fresh/<category>.jsonl + data/splits/<source>.json  --run_benchmark.py-->  runs/<model>/<source>.jsonl
runs/<model>/<source>.jsonl  --score.py-->  runs/scores/<model>/<source>.json  --aggregate.py-->  runs/report/
```

`runs/` and `external/` are gitignored.

## run_benchmark.py

Sends `record.messages` of every record of one source (filtered by the split file) to an OpenAI-compatible `/chat/completions` endpoint, e.g. llama-server or vLLM. Standard library only. Resumable: `(id, sample)` pairs already in the output without an error are skipped, so re-running retries only failed or missing requests.

```bash
.venv/Scripts/python.exe scripts/run_benchmark.py --source listqa --model qwen35-9b --base-url http://127.0.0.1:8080/v1 -i data/unified_fresh/info.jsonl
```

Fresh sources built to a separate directory, first 5 records, 3 samples each:

```bash
.venv/Scripts/python.exe scripts/run_benchmark.py --source slopbench --model qwen35-9b -i data/unified_fresh/writing.jsonl --limit 5 --n-samples 3
```

| Option | Default | Description |
|---|---|---|
| `--source` | required | Record `source` to run |
| `--model` | required | Model key in `--models-config` |
| `--base-url` | `$BENCH_BASE_URL` | Endpoint base URL, ending in `/v1` |
| `-i`, `--input` | `data/unified/*.jsonl` | Unified JSONL file(s) |
| `--split` | `data/splits/<source>.json`, else the `data/splits/*.json` whose `source` matches | Split file; only its `ids` are run, in its order (pilot: `data/splits/pilot/<source>.json`) |
| `--all` | off | Ignore the split, run every record of the source |
| `--models-config` | `configs/models.json` | Model configs: `sampling`, `chat_template_kwargs`, optional `model` (served name) |
| `--api-key-env` | `BENCH_API_KEY` | Environment variable with the API key (sent as a Bearer token if set) |
| `--out-dir` | `runs` | Output root |
| `--concurrency` | `2` | Parallel requests |
| `--max-tokens` | `4096` | Used when the record sets no `max_tokens` |
| `--n-samples` | from record | Overrides `eval.params.n_samples` (default 1) for every record |
| `--limit` | all | Only the first N records |
| `--timeout` | `900` | Seconds per request |
| `--wait-server` | `0` | Wait up to N seconds for `<base-url>/models` before starting |

Request parameters, later ones override earlier ones: `max_tokens` and `seed` (= 20261116 + sample index), the model's `sampling`, the record's generation params (`temperature`, `top_p`, `top_k`, `min_p`, `max_tokens`, `presence_penalty`, `frequency_penalty`, `repetition_penalty`, `stop` from `eval.params`, then the `eval.params.gen` dict). The model's `chat_template_kwargs` are passed unchanged. Only `messages` are sent: `followup_turns` and `tools` are not handled by this runner.

Output: `runs/<model>/<source>.jsonl`, one line per record and sample with `id`, `sample`, `model`, `source`, `output`, `reasoning`, `finish_reason`, `usage` (token counts from the server), `secs` (latency) and `params` (the request without messages); failed requests have `error` instead. Exit code 1 if any request failed or the input is invalid.

## score.py

Scores the outputs of one source for one or more models and writes a normalised score file per model. Scorer by source: `listqa` (official ListQA-Eval pipeline with an LLM judge), `slopbench` (official Slop Index scorer, mechanical layer), `ideafix` (local metrics: diversity, fluency, overlap, perplexity), `wmt26` and `wmt26_humanref` → `metricx` (MetricX-24). `<think>` blocks are stripped before scoring.

Third-party code is used from local clones, pinned to the commits we tested:

```bash
git clone https://github.com/amazon-science/ListQA-Eval external/listqa && git -C external/listqa checkout 83faa7c3a089a7c835c89f408f44b5b88ed27469
git clone https://github.com/hgaddipati1118/slop-index external/slopbench && git -C external/slopbench checkout 4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f
git clone https://github.com/google-research/metricx external/metricx && git -C external/metricx checkout fc4978eb064670f7cc33e93ea4f52d38396b8ae6
```

Dependencies: `uv pip install --python .venv/Scripts/python.exe -e ".[scoring-listqa]"` (ListQA) or `-e ".[scoring-ideafix]"` plus the spaCy model `https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl` (IDEAFix). SlopBench needs nothing extra. MetricX needs its own environment because it pins old libraries (use the CUDA torch index on a GPU machine):

```bash
uv venv --python 3.11 external/metricx/.venv
uv pip install --python external/metricx/.venv/Scripts/python.exe --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match torch==2.5.1 transformers==4.30.2 sentencepiece==0.1.99 datasets==2.13.1 accelerate==0.30.1 "pyarrow<15" "numpy<2" protobuf==3.20.3 fsspec==2023.9.2
```

```bash
JUDGE_BASE_URL=<judge-url> JUDGE_MODEL=<judge> .venv/Scripts/python.exe scripts/score.py --source listqa --model qwen35-9b gemma4-12b -i data/unified_fresh/info.jsonl
.venv/Scripts/python.exe scripts/score.py --source wmt26_humanref --model qwen35-9b gemma4-12b -i data/unified_fresh/translation.jsonl --metricx-python external/metricx/.venv/Scripts/python.exe --device gpu
```

| Option | Default | Description |
|---|---|---|
| `--source` | required | Record `source` to score |
| `--model` | required | One or more model keys (directories under `--runs-dir`) |
| `--scorer` | by source | `listqa`, `slopbench`, `ideafix` or `metricx` |
| `-i`, `--input`, `--split`, `--all` | as in `run_benchmark.py` | Records to score against (items outside the split are ignored) |
| `--runs-dir` | `runs` | Runner outputs |
| `--scores-dir` | `runs/scores` | Score files; work files (judge cache, scorer inputs, MetricX cache) go to `<scores-dir>/_work/` |
| `--device` | `cpu` | IDEAFix and MetricX: `cpu` or `gpu` |
| `--listqa-dir` | `$LISTQA_DIR` or `external/listqa` | ListQA-Eval clone |
| `--judge-concurrency` | `4` | Parallel judge calls |
| `--batch-pairs` | `20` | Element pairs per judge call (whole items only) |
| `--slopbench-dir` | `$SLOPBENCH_DIR` or `external/slopbench` | slop-index clone |
| `--metricx-dir` | `$METRICX_DIR` or `external/metricx` | MetricX clone |
| `--metricx-python` | `$METRICX_PYTHON` or current Python | Python of the MetricX environment |
| `--metricx-checkpoint` | `google/metricx-24-hybrid-xl-v2p6-bfloat16` | Do not mix scores from different checkpoints |
| `--metricx-tokenizer` | `google/mt5-xl` | |
| `--metricx-batch-size` | `1` | |
| `--metricx-cache` | `<scores-dir>/_work/metricx_cache.jsonl` | Predictions keyed by checkpoint, source, hypothesis and reference |

ListQA judge: an LLM judge served behind an OpenAI-compatible endpoint (`JUDGE_BASE_URL`, `JUDGE_MODEL`, optional `JUDGE_API_KEY`). Grades are cached in `<scores-dir>/_work/<model>/listqa.judged.jsonl`, so an interrupted run resumes; if some items stay unjudged, no score file is written.

Record fields the scorers read: ListQA `inputs.user_request` (question), `reference.answer` (gold answer string), `meta.metadata` (official metadata JSON with `prompt_type`); SlopBench `source_id` (scenario id), `subcategory` (domain), `reference.length_target_words`; IDEAFix `inputs.user_request` (brief), `meta.classic_task`; MetricX `inputs.source_text`, `reference.translation`, `src_lang`/`tgt_lang`, `subcategory`.

Output: `runs/scores/<model>/<source>.json` with `headline`, `metric`, `higher_is_better`, `scale` (`0-1` or `raw`), `stat` (how items aggregate: `mean`, `f1_pr`, `ratio`), `n_items`, `n_expected`, `n_errors`, `complete`, `extra` (per-subset and per-axis breakdowns) and `items` (`{record id: {"score": ...}}`). Exit code 1 if any model failed.

## aggregate.py

Summarises all score files across models. Standard library only, no LLM calls.

```bash
.venv/Scripts/python.exe scripts/aggregate.py --weak-anchor qwen35-2b --pass listqa=0.5
```

| Option | Default | Description |
|---|---|---|
| `--scores-dir` | `runs/scores` | Score files from `score.py` |
| `-o`, `--out-dir` | `runs/report` | Output directory |
| `--models` | all found | Only these models |
| `--pass` | `0.5` for every source | Pass thresholds for 0-1 metrics, `SOURCE=T` |
| `--weak-anchor` | none | Model expected to score lowest (checked per source) |
| `--strong-anchor` | none | Model expected to score highest |

Output:

- `summary.md`: (a) headline per model and source with a 95% CI (Wilson interval for means of 0/1 item scores, otherwise a 2000-resample bootstrap of the headline statistic, seed 20261116); (b) per source the best and worst model, the spread between them, anchor checks and saturation (0-1 metrics with all models ≥ 0.9 or ≤ 0.1); (c) per 0-1 source the share of items (scored for ≥ 2 models) with the same outcome for every model.
- `summary.csv`: one row per model and source with the headline, CI and counts.
- `drop_candidates.json`: per 0-1 source, the ids of items every model passed (`all_pass`) or failed (`all_fail`).
