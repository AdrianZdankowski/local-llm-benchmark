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
