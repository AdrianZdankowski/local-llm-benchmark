# IDEAFix

Divergent ideation: "Generate as many diverse and creative solutions as possible to …" for a design brief. The output is a list of ideas, scored with local, judge-free metrics (fluency, diversity, overlap, perplexity). It measures quantity and diversity, **not idea quality**.

| | |
|---|---|
| Paper | arXiv 2606.00875, v1 2026-05-30 |
| Code and briefs | https://anonymous.4open.science/r/CreativityAndEthicalFramework-C01E (ungated anonymous mirror; **no git commit hash**) |
| Data (HF) | https://huggingface.co/datasets/soummyaah/IDEAFix, gated, sha `baa8f109a1e563d753a35ae6f96930388ae8f007` (2026-04-28); holds the authors' model outputs, not needed |
| Pinned inputs | `data/202510_ProtocolCreativityEthics_VF/Briefs-Table 1.csv` (19,724 B, server sha `e183892e`), `Crea_prompts-Table 1.csv` (40,990 B, `4a7dffed`), `data/canonical_mapping.json` (`fca70fba`) |
| License | data CC BY 4.0; code MIT |
| Our files | none (the official repo ships no metric code; see below) |

## Setup

`scripts/download_fresh_sources.py --sources ideafix` fetches the input files into `data/raw/ideafix/` and checks them against pinned sha256 hashes (there is no commit to pin). The rest of the mirror (inference runner, optional judge prompts) is only needed for reference; if you download it to `external/ideafix/`, record path, size and server sha of every file.

Upstream `src/utils/inference.py` is an empty file in the mirror, so the official inference runner cannot run; build the prompts as `BriefFactory` and `Prompt.create_prompt_with_brief` do (below).

Scoring needs `sentence-transformers`, `torch`, `transformers` and `spacy` with the `en_core_web_sm` model (`python -m spacy download en_core_web_sm`) in the environment that runs the scorer; CPU is enough.

## Items and prompt

- The briefs CSV has 82 briefs. Exclude briefs with category **E** (jailbreak, 14) and **O** (ethical dilemma, 14): 54 remain. 9 of them are classic creativity tasks (categories L/N, e.g. Alternative Uses for a Brick); they are decades old and likely memorised, so report the score with and without them.
- Neutral framing only (the brief name, no attribute adjective) and only the official "Prompt - Control condition / Alternative 1".
- One **user** message, no system message: the CSV template with `[Brief context]` replaced by the brief name (the upstream typo "Eah" is kept), `\n` line endings:

```
Generate as many diverse and creative solutions as possible to address the following design challenge: <brief>. 
Instructions:
List all the solutions you find as a list.
Eah solution is composed of a maximum of two sentences enabling to understand the general concept behind the solution.
All solutions should be written in English.
The solutions are:
```

- 3 samples per brief (as the paper), `max_tokens=8192`, server-default (vendor) sampling. Strip thinking blocks.

## Scoring (our implementation of the paper's metrics)

The paper describes the metrics in prose only; these are our pinned choices.

**Idea splitting:** drop text before the first list element; if there are several lists keep the last; newlines, tabs and `Solution N:` are delimiters; strip markdown bullets and bold; drop refusals and ideas of ≤ 5 words; a response with ≤ 1 idea left is invalid.

| Metric | Definition | Model |
|---|---|---|
| Fluency | number of ideas | – |
| **Diversity** (headline) | mean over ideas of the minimum cosine distance to the other ideas in the same response | `sentence-transformers/all-mpnet-base-v2` |
| Overlap | share of brief keywords (lemmatised nouns/adjectives/adverbs) present in an idea, mean over ideas | spaCy `en_core_web_sm` |
| Perplexity | per idea; reported as the median | `openai-community/gpt2` |

Novelty and rarity from the paper are not computed (they need outputs from the other 24 prompts). Aggregate: mean over the 3 samples, then over briefs (perplexity: median). Runtime: a few minutes per model on CPU; model downloads about 1 GB.

An optional official LLM-judge (`run_scoring.py`: originality, surprise, relevance per idea) can be pointed at `JUDGE_BASE_URL`; it is not part of the headline.

## Calls per item

3 model calls per brief (lists of typically 500–2,000 tokens). Judge: 0.

## Known issues

- **Diversity is not quality.** In the pilot the strong reference model scored below three local models; a long list of loosely related ideas scores well.
- The anonymous mirror can change or disappear; keep the manifest and the input hashes.

## In this repository

```bash
python scripts/download_fresh_sources.py --sources ideafix     # briefs, pinned by sha256
python scripts/build_dataset.py --sources ideafix --out-dir data/unified_fresh   # never the tracked data/unified/
python scripts/run_benchmark.py --source ideafix --model $BENCH_MODEL -i data/unified_fresh/chat.jsonl
python scripts/score.py --source ideafix --model $BENCH_MODEL -i data/unified_fresh/chat.jsonl  # --device cuda on a GPU machine
```

The metric table above is the specification of `src/mybench/scoring/ideafix.py`; options are documented in `scripts/README.md`.
