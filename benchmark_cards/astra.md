# ASTRA-bench

Category: agents (tool use). "ASTRA-bench: Evaluating Tool-Use Agent Reasoning and Action Planning with Personal User Context" (Apple, arXiv 2603.01357). A personal assistant works on a simulated phone (contacts, SMS, email, calendar, WhatsApp, calls) through tools; an LLM user simulator plays the user.

| | |
|---|---|
| Source | https://github.com/apple-aiml-research/ml-astra, commit `d150a8af6a8f5442eaf25ef6dc287464ca1341f0` (only commit) |
| Data date | public 2026-10-20/21 (repo creation); arXiv v1 (2026-03-02) shipped no data. The in-scenario dates (2024) are fiction. |
| License | code: Apple Sample Code License; data: CC BY-NC-ND 4.0 (non-commercial; no modified scenarios may be published). We commit scenario names only. |
| Size | 2,428 scenarios over 5 personas (14 of them `test` smoke scenarios) |
| Run | `harness/astra/` (official CLI + endpoint patch) |

## Our sampling

300 scenarios (seed 20261116), stratified by **persona × primary app**. Population: all scenarios minus the 14 smoke tests (2,414). Primary app = the rarest app the scenario touches, in the order phone call → WhatsApp → email → SMS → calendar → contact, so rare apps are not absorbed by calendar or contact. Proportional allocation (largest remainder, floor 2 per stratum) over 29 non-empty strata. About half of the sample (149) needs the user simulator (has an agent→user milestone).

## Scoring

Rule-based milestone matching, no judge: `similarity` in [0, 1] per scenario. Score = mean similarity over the selected scenarios (null = 0); scenarios with an infrastructure exception are reported separately. Breakdown by persona and primary app.

## Cost per model (300 scenarios)

Model under test: about 3–8 calls per scenario (1.0–2.4k total). Simulator (judge endpoint): 1–3 per scenario (300–900 total). Tool outputs can dump whole databases (up to about 17k tokens): at least 32k context per slot.

## Caveats

- The user simulator is an LLM judge behind an OpenAI-compatible endpoint, not the paper's simulator; it must return real `tool_calls` for `end_conversation`.
- Sampling parameters cannot be set from the harness; they come from the server defaults.
- Local chat templates (Qwen, Gemma) reject system messages after the first position; our patch merges them into one leading system message.
- Scores of strong models cluster near 1 on easy scenarios (pilot: 0.90–0.95 for the best local models); the full 300 with complexity breakdowns are needed to separate them.
