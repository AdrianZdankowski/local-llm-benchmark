# SEQUOR

Category: writing (multi-turn constraint following). "SEQUOR: A Multi-Turn Benchmark for Realistic Constraint Following" (Canaverde et al., COLM 2026, arXiv 2605.06353). Real user constraints (format, length, tone, persona) are introduced, replaced and accumulated over 50 fixed user turns.

| | |
|---|---|
| Source | https://github.com/deep-spin/SEQUOR, commit `6574f28abcc128f2a497ef8a7bf5b628aa432903` (code and data; no HF dataset) |
| Data date | `data/` in the first commit, 2026-05-07 (arXiv v1 the same day) |
| License | none stated. Constraints derive from LMSYS-Chat-1M (own agreement), personas from PersonaHub. Private evaluation only; we commit conversation ids only. |
| Size | 7 testset folders × 200 conversations = 1,400; the official evaluation uses the first 50 turns |
| Run | `harness/sequor/` (official CLI + patch for sparse judging) |

## Our sampling

150 conversations (seed 20261116), 30 per constraint regime: single (1 constraint), tuples (3 constraints), replace (every 5/10 turns, 15 + 15), add (accumulating, 15 + 15), everything (random mix). Every conversation has a different persona (150 of 200). No "everyday" filter exists: personas are expert professionals, so the tasks are expert-flavoured.

All 50 turns are generated, but only turns **1, 10, 20, 30, 40, 50** are judged (1,653 constraint judgments instead of about 20k).

## Scoring

An LLM judge checks each active constraint at each judged turn (`Final Verdict: [[Yes]]/[[No]]`). Turn success = all active constraints satisfied. Score = pooled constraint-following rate over all judged turns. Also: per regime, per turn (turn 50 − turn 1 = drift), and an optional constraint-blind task-completion rate.

## Cost per model

7,500 model calls (150 × 50, growing context, up to 8,192 output tokens each), 1,653 constraint-judge calls, 900 optional task-judge calls. No simulator.

## Caveats

- The slowest benchmark: minutes per conversation even for small models.
- Needs at least 32k context per slot; on overflow the oldest turn pair is dropped (official behaviour), which must be counted.
- Not comparable with the paper (different judge, 150 of 1,400 conversations, 6 of 50 turns judged).
