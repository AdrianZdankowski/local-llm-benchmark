# SlopBench (The Slop Index)

Category: writing. "SlopBench: How Well Can We Rank Language Models by Slop?" (Roongta, Gaddipati, Huynh; arXiv 2609.33905). Everyday writing requests (email, social post, essay, Slack message), scored mechanically against pre-ChatGPT human baselines.

| | |
|---|---|
| Source | https://github.com/hgaddipati1118/slop-index, commit `4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f` |
| Data date | scenarios last changed 2026-07-15; paper 2026-09-27 |
| License | repo MIT; prompts, outputs and statistics CC BY 4.0 (paper). Only derived human statistics are shipped. |
| Size | 112 scenarios (email 30, social 28, essay 27, Slack 27) |
| Run | `harness/slopbench/` (official offline scorer) |

## Our sampling

All 112 scenarios, **5 samples each** (560 generations per model). Prompts are byte-identical to the official published run (per-domain system scaffold + persona/recipient/context user prompt).

## Scoring

Official `harness/score.py`, stdlib only, no judge. Four axes per model × domain on 0–100, 0 = human-like: conciseness (0.35), templating of openers (0.30, needs ≥ 2 samples), paragraph rhythm (0.20, email only in practice), stylistic tells vs human rates (0.15). Domain composite = weighted mean, overall = mean of 4 domains. **Lower is better.**

## Cost per model

560 short generations; no judge; scoring takes seconds.

## Caveats

- Measures **style and length, not content quality**. The paper's ranking was unstable under reweighting, and crowd preference correlated with the mechanical score at only about −0.1. Report per axis.
- Templating depends on the number of samples; compare only runs with the same n.
- The site's headline "Human Score" (crowd votes) is not reproducible offline.
- The overall score has only 4 units (domains), so confidence intervals are wide.
