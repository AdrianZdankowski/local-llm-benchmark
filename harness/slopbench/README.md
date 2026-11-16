# SlopBench (The Slop Index)

Everyday writing requests (email, social post, essay, Slack message), scored mechanically against pre-ChatGPT human baselines: length overshoot, templated openers, paragraph rhythm and stylistic "tells". **No LLM judge.** It measures style and length, not content quality.

| | |
|---|---|
| Repository | https://github.com/hgaddipati1118/slop-index (code, scenarios, derived human baselines) |
| Pinned commit | `4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f` (2026-11-15); scenarios `scenarios/pilot/{email,social,essay,slack}.json` last changed 2026-07-15 |
| License | MIT (repo); the paper states prompts, outputs and statistics are CC BY 4.0 |
| Our files | none (official scorer, no patch) |

The repo and the paper definitions drift; `harness/score.py` at the pinned commit is the reference.

## Setup

```bash
git clone https://github.com/hgaddipati1118/slop-index external/slopbench
git -C external/slopbench checkout 4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f
```

The scorer is stdlib-only Python; no venv needed.

## Generation (model under test)

All 112 scenarios, **5 samples per scenario** (560 requests per model). Format as in `harness/generate.py`:

- **system**: the per-domain `SCAFFOLD` (e.g. email: "You are helping the user write an email. Output only the email body, no subject line, no commentary.");
- **user**: `build_user_prompt(s)`: `About me: {persona}`, `Who this is going to: {recipient}` (if present), one `They wrote: "…"` line per context message, a blank line, then `{prompt}`;
- `max_tokens=4000`; if the visible text is empty, retry once with 8000; no temperature override (server defaults).

Strip `<think>…</think>`; only visible text is scored.

## Scoring (official, offline)

Write the generations to `external/slopbench/runs/<run_id>/outputs.jsonl`, one row per sample with `scenario_id`, `domain`, `model`, `sample` (0..4), `text`, `length_target` (`[lo, hi]` from the scenario) and optionally `error`. Then, from `external/slopbench/`:

```bash
python harness/score.py --run-id <run_id>
python harness/rank_spread.py --run-id <run_id>     # bootstrap rank ranges
```

Axes per model × domain on 0–100 (0 = human-like):

| Axis | Weight | Definition |
|---|---|---|
| conciseness | 0.35 | mean `max(0, words/hi − 1)` × 100, capped at 100 |
| templating | 0.30 | share of samples sharing the most common first-5-word opener per scenario, rescaled with floor `1/n`; **needs ≥ 2 samples per scenario** |
| rhythm | 0.20 | `max(0, 1 − paragraph-length variance / human variance)`; human baselines exist only for email and Slack (inverted in Slack), so effectively email-only |
| tells | 0.15 | rate of validated tells (em dash and others) per 1k words vs the human rate; 1× = 0, 3× = 100 |

Domain composite = weighted mean of available axes (weights renormalised); overall = mean of the 4 domain composites. **Lower is better.** Report each axis, not only the composite: the paper's ranking was unstable under reweighting, and crowd preference vs mechanical score correlated at only about −0.1.

In this repository the same steps run as:

```bash
python scripts/download_fresh_sources.py --sources slopbench
python scripts/build_dataset.py --sources slopbench --out-dir data/unified_fresh   # never the tracked data/unified/
python scripts/run_benchmark.py --source slopbench --model $BENCH_MODEL -i data/unified_fresh/writing.jsonl
python scripts/score.py --source slopbench --model $BENCH_MODEL -i data/unified_fresh/writing.jsonl        # calls the official score.py in external/slopbench
```

## Calls per item

5 model calls per scenario (short outputs, 10–700 words). Judge and simulator: 0. Scoring takes seconds on CPU.

## Known issues

- **n matters.** With 1 sample, templating (30% weight, the axis that separates models most) is undefined. Its floor depends on n, so compare only models run with the same n.
- **Not the site's headline.** The public "Human Score" mixes crowd votes (Elo) with the axes; only the mechanical layer is reproducible offline.
- **Freshness:** scenarios were public on 2026-07-15, after every model's freshness bound (`benchmark_cards/README.md`), though before the release of Muse Glimmer 30B. There are no gold answers either: the score is reference-free style statistics.
- **Pilot:** the score has only 4 units (domain composites), so its CIs are very wide; the strong reference model had the highest (worst) score, which reflects style and length, not quality.
