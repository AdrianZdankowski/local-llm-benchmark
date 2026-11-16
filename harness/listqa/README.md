# ListQA

Closed-book factual recall as a list: the model answers a question with a numbered list of 3–10 elements, and each element is graded against a gold list by an LLM judge.

| | |
|---|---|
| Data | https://huggingface.co/datasets/AmazonScience/ListQA (not gated), revision `748eb345a110c4a7cb2af6b6be8074840974e15f`; `data/all.jsonl`, 9,045 rows |
| Code | https://github.com/amazon-science/ListQA-Eval, commit `83faa7c3a089a7c835c89f408f44b5b88ed27469` (2026-10-14) |
| License | CC BY-NC 4.0 (data and code); not for training; the data carries a canary string |
| Our files | none; no upstream patch (the judge is swapped in our scorer code, see below) |

## Setup

```bash
git clone https://github.com/amazon-science/ListQA-Eval external/listqa
git -C external/listqa checkout 83faa7c3a089a7c835c89f408f44b5b88ed27469
python scripts/download_fresh_sources.py --sources listqa     # data/raw/listqa/all.jsonl at the pinned revision
```

The scorer needs `evaluate`, `rouge-score`, `scipy` and `nltk`.

The dataset has no item id; we use `source_id = all-<0-based line index in all.jsonl>`. `torch`/`transformers` are not needed once the judge is swapped. `evaluate.load("rouge")` fetches its metric script from the HF Hub on first use.

## Generation (model under test)

One request per item to `$BENCH_BASE_URL/chat/completions`, `model=$BENCH_MODEL`:

- one **user** message, no system message: `LISTQA_ZERO_SHOT_PROMPT` from `external/listqa/src/listqa_eval/prompts.py`, verbatim, with `{question}` = the question (zero-shot, as in the paper);
- no sampling override (the paper used each model's default generation config, which matches our server defaults); 1 sample per item;
- strip `<think>…</think>` before scoring.

Save one JSONL line per item: `{"id": ..., "output": ...}`.

## Scoring (official pipeline, judge swapped)

Follows `external/listqa/src/listqa_eval/{metrics,llm_judge,aggregator}.py`; import `listqa_eval.metrics` and `listqa_eval.aggregator` from `external/listqa/src` and replace only the judge call (`HFJudgeModel.generate` / `judge_list_elements`) with a call to `JUDGE_BASE_URL` / `JUDGE_MODEL`.

1. **Parse.** Prediction: `"\n" + pred.split("\nExample 4:")[0].lower()`; target: `target.replace("\n ", "\n").lower()`; elements via regex `\n\d+\.\s(.+?)(?=\n\d+\.|\Z)` (DOTALL).
2. **Match.** Pairwise ROUGE-1 F (stemmed) between predicted and gold elements, Hungarian assignment; extra predicted elements (more predicted than gold) are graded B without a judge call.
3. **Judge.** Each (question, gold element, predicted element) pair is graded A = CORRECT / B = INCORRECT with the official `LLM_JUDGE_PROMPT_TEMPLATE`; parse `^\s*(A|B)\s*$`, 3 retries, then B. If the prediction has no numbered list, the whole prediction is judged once against the whole gold answer (precision 0).
4. **Aggregate.** Per item `P = #A / num_pred`, `R = #A / num_gold`; average P and R over items, then **LLM-Judge-F1 = 2PR / (P + R)** (not a mean of per-item F1). Report also the simple (single-faceted) and complex (multi-faceted) subsets.
5. **Format-Correctness** (`compute_list_format_em`, no judge): share of predicted elements whose facet structure matches the prompt type; 0 for fewer than 3 elements.

**Batched judge.** To cut judge calls, about 20 pairs go in one request: system message = the official template's instructions and examples; user message = numbered `### Example k` blocks (`Question / Gold target / Predicted answer`) plus "Return JSON only: `{"grades": [{"k": 1, "grade": "A"}, …]}`", with `response_format={"type":"json_object"}`. Pack whole items (never split an item), accept a batch only if it has exactly N grades of A/B, otherwise retry once and fall back to single-pair official calls. Calibrate once on about 200 pairs (batched vs single, target ≥ 97% agreement; otherwise use batches of 10).

## Calls per item

- Model under test: 1 (short answer, about 50–300 tokens).
- Judge: 3–10 pairs per item; about 1 batched call per 2–5 items (single-pair judging would be 5–8 calls per item).

## Known issues

- **Floor effect.** The questions are new, but the facts are pre-2025 Wikipedia list facts; 8B–30B models score about 0.05–0.16 F1 (paper and our pilot), and 13 of the 20 pilot items were failed by every model including the strong reference. The complex subset sits near zero. Lead with the overall and simple-subset scores and report Format-Correctness, which spreads models more.
- **Judge differs from the paper** (the paper used gpt-oss-120b locally), so absolute F1 is not comparable with the paper's table; the paper reports model rankings stable across judges (ρ > 0.96).

## In this repository

```bash
python scripts/build_dataset.py --sources listqa --out-dir data/unified_fresh   # never the tracked data/unified/
python scripts/run_benchmark.py --source listqa --model $BENCH_MODEL -i data/unified_fresh/info.jsonl          # uses $BENCH_BASE_URL, data/splits/listqa.json
python scripts/score.py --source listqa --model $BENCH_MODEL -i data/unified_fresh/info.jsonl                  # judge: $JUDGE_BASE_URL, $JUDGE_MODEL
```

The steps above are the specification of `src/mybench/scoring/listqa.py`; options are documented in `scripts/README.md`.
