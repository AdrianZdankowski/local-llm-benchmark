# WMT26 General MT (EN→CS, EN→DE, EN→ET)

Category: translation. Paragraph-level translation of English news and social posts, scored with MetricX-24 against human references.

| | |
|---|---|
| Source | https://github.com/wmt-conference/wmt26-general-mt, commit `63aa5d24311a7e7e3e8173528f3771c7e8b4be78`, `data/wmt26-genmt.jsonl` (4,897 documents) |
| Data date | sources: news from early 2026, Mastodon posts Mar–Apr 2026; test set released 2026-06-18; references 2026-07-27 |
| License | no LICENSE file; "can be freely used for research purposes", cite the WMT26 Findings paper; no redistribution |
| Size | 201 items = 67 English paragraphs × 3 target languages |
| Run | `harness/wmt26-metricx/` |

## Our sampling

Unit = one `<p>` paragraph (source and reference are line-aligned in the news and social domains). Paragraphs of 40–1,500 characters with a non-empty human reference in all three languages, shuffled with seed 20261116, at most 3 per news document and 1 per social document: 34 news + 33 social paragraphs from 46 documents. Speech (needs video) and software (UI strings) domains excluded.

| Pair | Reference type |
|---|---|
| en-cs, en-de | human post-edit (`refPE`) of Qwen3.5-397B or Gemma-4-31B output |
| en-et | human translation from scratch (`refA`), control |

Prompt: the official WMT26 participant instruction for the pair and domain, then the paragraph with its tags. Temperature 0, max 2,048 tokens.

## Scoring

MetricX-24 hybrid XL (`google/metricx-24-hybrid-xl-v2p6-bfloat16`), reference-based, error in [0, 25], **lower is better**. Mean per pair, per domain and overall. Runs on a 12 GB GPU or on CPU. Synthetic references are never used.

## Cost per model

201 single-turn calls, no judge, 201 MetricX passes.

## Caveats

- MetricX is an approximation of the official human evaluation; not comparable with the Findings rankings.
- `refPE` references may favour the Qwen3.5 and Gemma 4 families; compare with the en-et control.
- The metric floor is not 0 (about 3–5 for a perfect copy of the reference); compare models only with each other.
- Segment level without document context; screenshots of social posts are not sent; no Polish.
