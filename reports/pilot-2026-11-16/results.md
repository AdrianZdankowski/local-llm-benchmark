# Pilot results, 2026-11-16

Cells: score [95% bootstrap CI] (units scored / pilot units, e = errors). `—` = not run. ↓ = lower is better. Raw numbers: `results.csv`. Read the limitations in `README.md` before using any of these numbers.

Notes: confidence intervals in this pilot are percentile bootstrap intervals (1000 resamples) for every cell; the current `src/mybench/scoring/aggregate.py` uses Wilson intervals for 0/1 means, so re-aggregating will give slightly different bounds. `wmt26` here is the source `wmt26_humanref` in the code and splits.

| model (role) | listqa | wmt26 ↓ | slopbench ↓ | ideafix | vaguebench | astra | toolbenchx | sequor |
|---|---|---|---|---|---|---|---|---|
| qwen35-9b (tested) | 0.065 [0.017, 0.122] (20/20, e0) | 6.22 [4.54, 7.96] (21/21, e0) | 30.87 [17.00, 43.48] (4/4, e0) | 0.336 [0.294, 0.374] (20/20, e0) | 0.646 [0.445, 0.845] (14/14, e0) | 0.951 [0.894, 1.000] (20/20, e0) | 0.444 [0.111, 0.778] (9/9, e5) | 0.611 [0.167, 1.000] (3/3, e0) |
| gemma4-12b (tested) | 0.077 [0.011, 0.156] (20/20, e0) | 7.11 [4.90, 9.55] (21/21, e0) | 26.09 [9.02, 43.16] (4/4, e0) | 0.417 [0.393, 0.443] (20/20, e0) | 0.770 [0.594, 0.923] (14/14, e0) | 0.896 [0.768, 0.987] (19/20, e1) | 0.667 [0.333, 1.000] (9/9, e3) | — |
| gptoss-20b (tested) | 0.088 [0.017, 0.179] (20/20, e0) | 7.47 [5.66, 9.40] (21/21, e0) | 18.35 [8.39, 27.56] (4/4, e0) | 0.413 [0.387, 0.438] (20/20, e0) | 0.661 [0.471, 0.846] (14/14, e0) | 0.662 [0.467, 0.850] (20/20, e0) | 0.556 [0.222, 0.889] (9/9, e4) | — |
| gemma4-26b (tested) | 0.145 [0.040, 0.270] (20/20, e0) | 6.84 [4.62, 9.15] (21/21, e0) | 33.91 [24.06, 43.77] (4/4, e0) | 0.437 [0.415, 0.458] (20/20, e0) | 0.791 [0.653, 0.955] (10/14, e5 of 21 items, 4 of them B/C) | 0.948 [0.889, 1.000] (19/20, e1) | 0.111 [0.000, 0.333] (9/9, e8) | — |
| qwen35-2b (anchor-weak) | 0.082 [0.006, 0.182] (20/20, e0) | 12.15 [9.54, 14.73] (21/21, e0) | 28.23 [12.86, 43.59] (4/4, e0) | 0.309 [0.243, 0.365] (20/20, e0) | 0.742 [0.642, 0.860] (13/14, e1) | 0.669 [0.483, 0.846] (20/20, e0) | 0.556 [0.222, 0.889] (9/9, e4) | 0.389 [0.167, 0.667] (3/3, e0) |
| claude-sonnet (reference-strong) | 0.345 [0.190, 0.507] (20/20, e0) | 4.33 [3.16, 5.76] (21/21, e1) | 45.24 [39.34, 51.15] (4/4, e0) | 0.364 [0.337, 0.389] (20/20, e0) | 0.695 [0.527, 0.856] (14/14, e0) | excluded | 0.889 [0.667, 1.000] (9/9, e1) | — |

`claude-sonnet` = Claude Sonnet 5.5, the strong reference model, run through the same harnesses via an OpenAI-compatible endpoint (it was also the LLM judge and user simulator in this pilot).

## Metrics

| Benchmark | Metric | Unit of n |
|---|---|---|
| listqa | LLM-Judge-F1 (official aggregator: 2PR/(P+R) of item-mean P and R) | question |
| wmt26 | MetricX-24 hybrid XL predicted error, mean over items (0–25, lower is better) | paragraph × language |
| slopbench | Slop Index mechanical layer, mean of domain composites (0–100, lower = more human-like) | domain (4), from 4 scenarios × 5 samples |
| ideafix | diversity: mean minimum cosine distance between the ideas of one response | generation |
| vaguebench | coverage F1 on groups B and C (official metric 3) | B/C item (of 7 scenarios × 3 variants) |
| astra | mean rule-based similarity (null = 0); errored scenarios excluded and counted in e | scenario |
| toolbenchx | exact match rate, baseline (no-hint) mode | task |
| sequor | pooled constraint-following rate over judged turns 1, 10, …, 50 | 50-turn conversation |

Errors (`e`): for astra and vaguebench, errored units are excluded from the score. For toolbenchx, `e` counts tasks whose harness `error` field is set; this includes intended hazards, wrong answers and technical errors, and all tasks stay in the score (failed = 0). The reference model's wmt26 run logged 1 error while all 21 items were scored.

## Sanity checks

| Benchmark | Weak anchor lowest? | Strong reference highest (best)? | Items with identical outcome for all models |
|---|---|---|---|
| listqa | no | yes | 13 of 20 failed by every model |
| wmt26 | yes | yes | n/a (continuous) |
| slopbench | no | no (worst) | n/a |
| ideafix | yes | no | n/a |
| vaguebench | no | no | 8 of 14 passed by all, 1 failed by all (pass = F1 ≥ 0.5) |
| astra | no | excluded | 3 of 20 failed by all (pass = similarity 1) |
| toolbenchx | no | yes | 1 of 9 passed by all, 1 failed by all |
| sequor | yes (2 models only) | not run | 2 of 3 failed by both models |

With n ≈ 20 most confidence intervals overlap; the only clear separations are the strong reference on listqa and wmt26 and the weak anchor on wmt26.
