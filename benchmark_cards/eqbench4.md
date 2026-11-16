# EQ-Bench 4

Category: chat and creativity (emotional intelligence). Multi-turn roleplay: the model under test talks to a simulated user persona for 8 turns per side; models are ranked by blind pairwise judging.

| | |
|---|---|
| Source | https://github.com/EQ-bench/eqbench4, commit `93dcb7f5d430433ad49d501e672a98bcff2c9678`; dataset `src/eqbench/datasets/test.json` (`generated_at` 2026-05-31) |
| Data date | personas first public 2026-06-08; leaderboard 2026-07-23; repo 2026-07-29 |
| License | BSD-3-Clause + Commons Clause (LICENSE added 2026-09-26) |
| Size | 120 scenarios: 60 generated, 60 hand-authored (15 each: power imbalance, reality distortion, ego threat / accountability, social exclusion) |
| Run | `harness/eqbench4/` (official CLI + our fixed-budget ladder patch) |

## Our sampling

All 120 scenarios for the conversations. The pairwise ladder judges every model pair on a deterministic balanced subset (seed 20261116): 60 scenarios per tested–tested pair, 30 per tested–anchor pair, 20 for the anchor pair, each half generated and half hand-authored. Anchors: Qwen3.5-2B (weak) and the judge model (strong).

## Scoring

An LLM judge behind an OpenAI-compatible endpoint plays the persona and judges each matchup in both orders with the official prompt and dimension weights. Ratings: official soft Bradley–Terry solver on the Elo scale with bootstrap 95% CI.

## Cost

Per model: 960 model calls (120 × 8) and 960 simulator calls plus format retries. Pairwise judge: about 2,560 calls for 6 tested models + 2 anchors (stage 1), up to 3,000 with stage 2. Long judge prompts (two transcripts and the persona card).

## Caveats

- Ratings are relative to our ladder and not comparable with eqbench.com (different persona model, single judge).
- When the judge is also the strong anchor it rates itself; treat that rating as an upper reference.
- Safety-tuned simulators sometimes refuse to play the patient role in therapy-style scenarios, leaving scenarios incomplete; count and report them.
- Not run in the 2026-11-16 pilot.
