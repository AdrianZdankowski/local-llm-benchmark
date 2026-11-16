# VagueBench

Category: vague requests (chat). "Don't Guess, Ask Wisely" (Zhang et al., arXiv 2611.01878, EMNLP 2026). Does the assistant ask for clarification on underspecified everyday requests, and how much of the real intent does its final answer cover? Not the unrelated embodied-agent "VagueBench" (arXiv 2611.03765).

| | |
|---|---|
| Source | code https://github.com/zhangrongyu0101/VagueBench, commit `af4587d6584cad36cba85d42fba4eef2a80bde6d`; data HF `rongyu0101/VagueBench`, revision `62d4cc6f17cb5efaa46da02e7d42bbf64c96aa02` (750 rows, sha256 `77d025b6…`) |
| Data date | first public 2026-11-02; paper 2026-11-01 |
| License | `apache-2.0` only as an HF card tag; no LICENSE in the repo, "for research purposes" in the paper |
| Size | 250 scenarios × 3 variants: A complete query, B intent hidden, C intent and details hidden |
| Run | `harness/vaguebench/` (official `evaluate.py`, config from env vars) |

## Our sampling

100 whole scenarios (seed 20261116) with all three variants, so groups stay paired: 300 items = 100 A + 100 B + 100 C. Stratified by query type: consultation and analysis 48, information query 28, recommendation and decision 17, creative generation 5, task execution 2.

## Scoring

An LLM judge behind an OpenAI-compatible endpoint classifies the first-turn behaviour (ask vs answer) and scores the final answer's coverage of the hidden intents and details; the same endpoint plays the simulated user, revealing only what is asked. Headline: **coverage F1 on B ∪ C** (mean of the group F1s), with A as the ceiling. Reported alongside: Ask% on B and C, over-asking rate on A, turns when asking. Max 5 clarification turns, fixed for all models.

## Cost per model (300 items)

Model under test 1 + k calls per item, judge 2 + k, simulator k (k = clarification rounds). Models of this size rarely ask: about 300 model and 600 judge calls in total.

## Caveats

- Ask% sits near 0–2% for 8B–30B models and does not separate them on its own.
- Failed samples are excluded from the metrics; report the count and compare on common items.
- Not comparable with the paper (different judge and simulator).
