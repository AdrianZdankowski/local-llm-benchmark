# Benchmark cards: fresh benchmarks

One card per benchmark of the fresh-benchmark track: source, data date, license, size, how we sample items, how we score, caveats. How to run each one is in `harness/<benchmark>/README.md`.

## Freshness criterion

A benchmark counts as fresh for a model if its test data became public **after the model's stated knowledge cutoff**. Qwen does not publish cutoffs, so for Qwen models the bound is the **release date**. Bounds for the models in `configs/models.json`:

| Model | Release | Stated cutoff | Freshness bound |
|---|---|---|---|
| gpt-oss-20b | 2025-08-05 | 2024-06 | 2024-06 |
| Gemma 4 12B / 26B-A4B | 2026-06-03 / 2026-04-02 | 2025-01 | 2025-01 |
| Qwen3.5-2B / 9B | 2026-03-02 | not published | 2026-03-02 |
| Qwen3.6-27B | 2026-04-22 | not published | 2026-04-22 |
| Muse Glimmer 30B | 2026-08-10 | 2026-01-04 | 2026-01-04 |

The latest bound is **2026-04-22**. Every benchmark below published its test data later.

## Benchmarks

| Category | Benchmark | Data public | Why fresh | Card |
|---|---|---|---|---|
| writing | SEQUOR | 2026-05-07 | after all bounds; constraints from older LMSYS chats, but the conversations and constraint schedules are new | [sequor.md](sequor.md) |
| writing | SlopBench | 2026-07-15 (scenarios) | after all bounds; reference-free style statistics, no gold answers to memorise | [slopbench.md](slopbench.md) |
| vague requests (chat) | VagueBench | 2026-11-02 | after every model's release | [vaguebench.md](vaguebench.md) |
| information | ListQA | 2026-10-01 | after every model's release; questions are new, the underlying Wikipedia facts are old by design | [listqa.md](listqa.md) |
| agents (tool use) | ASTRA-bench | 2026-10-21 | after every model's release (the earlier arXiv version shipped no data) | [astra.md](astra.md) |
| agents (tool use) | ToolBench-X | 2026-07-24 (repo 2026-06-23) | after all bounds | [toolbenchx.md](toolbenchx.md) |
| chat and creativity | EQ-Bench 4 | 2026-06-08 (personas) | after all bounds | [eqbench4.md](eqbench4.md) |
| chat and creativity | IDEAFix | 2026-04-28 | after all bounds (5 days after Qwen3.6); 9 classic briefs are old and flagged | [ideafix.md](ideafix.md) |
| translation | WMT26 General MT | 2026-06-18 (test), 2026-07-27 (references) | after all bounds; sources are news and posts from early 2026 | [wmt26.md](wmt26.md) |

"Fresh" here means the items were not public before the bound. It does not rule out that a model saw similar content (old facts, classic creativity tasks, public constraint types); each card lists such caveats.
