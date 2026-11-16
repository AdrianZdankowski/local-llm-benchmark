# ListQA

Category: information. "ListQA: A Benchmark for Evaluating List-Formatted Factual Knowledge Retrieval in LLMs" (Kulkarni, Vaideeswaran; arXiv 2610.19165, NeurIPS 2026 E&D). Closed-book questions answered with a numbered list of 3–10 elements, each graded against a gold list.

| | |
|---|---|
| Source | data HF `AmazonScience/ListQA`, revision `748eb345a110c4a7cb2af6b6be8074840974e15f`; code https://github.com/amazon-science/ListQA-Eval, commit `83faa7c3a089a7c835c89f408f44b5b88ed27469` |
| Data date | HF upload 2026-10-01; paper 2026-10-13. Facts from a 2025 Wikipedia dump, validated as of 2024-12-31. |
| License | CC BY-NC 4.0 (data and code); not for training; canary string |
| Size | 9,045 questions in 8 categories, single- and multi-faceted |
| Run | `harness/listqa/` (official parsing, matching and aggregation; judge swapped) |

## Our sampling

1,500 questions (seed 20261116), stratified by category × prompt type (16 strata), proportional with largest remainder: 892 single-faceted, 608 multi-faceted. Gold lists have 3–8 elements (mean 4.6). Item id = `all-<line index>` (the dataset has no id).

## Scoring

Official pipeline: parse numbered elements, match predicted to gold elements with ROUGE-1 + Hungarian assignment, an LLM judge grades each matched pair CORRECT/INCORRECT (official prompt; we batch about 20 pairs per call; a calibration against single-pair judging is still to be done). **LLM-Judge-F1** = 2PR/(P+R) of item-averaged precision and recall. Also: simple/complex subsets and Format-Correctness (no judge).

## Cost per model

1,500 short generations; about 7.5k–12k judged pairs, about 400–600 batched judge calls.

## Caveats

- **Floor effect.** It tests recall of pre-2025 facts; 8B–30B models score about 0.05–0.16 F1, and the complex subset is near zero. Many items are failed by every model.
- The questions are new, but the underlying facts were certainly in pretraining (by design).
- The judge is not the paper's (gpt-oss-120b), so absolute F1 is not comparable with the paper; rankings are reported stable across judges.
