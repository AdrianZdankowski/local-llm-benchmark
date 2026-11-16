# IDEAFix

Category: chat and creativity (divergent ideation). "IDEAFix: An Evaluation Framework for Creative Defixation Prompting in LLMs" (arXiv 2606.00875). The model lists as many diverse solutions as possible to a design brief.

| | |
|---|---|
| Source | code and briefs: https://anonymous.4open.science/r/CreativityAndEthicalFramework-C01E (anonymous mirror, no commit hash; we pin file sizes and hashes); data HF `soummyaah/IDEAFix` (gated, sha `baa8f109…`, holds model outputs we do not need) |
| Data date | HF 2026-04-27/28; paper 2026-05-30 |
| License | data CC BY 4.0; code MIT |
| Size | 82 briefs, 25 prompt strategies, 7 framings per brief |
| Run | `harness/ideafix/` |

## Our sampling

54 briefs: all except jailbreak (14) and ethical-dilemma (14) briefs. Neutral framing and the official control prompt only (the other prompts test prompting methods, not models). 3 samples per brief, as in the paper. 9 classic creativity tasks (e.g. Alternative Uses for a Brick) are flagged; report with and without them.

## Scoring

Local, judge-free metrics from the paper, our implementation (the repo ships none): fluency (number of ideas), **diversity** (mean minimum cosine distance between ideas of one response, `all-mpnet-base-v2`; headline), overlap with brief keywords (spaCy), median GPT-2 perplexity. CPU only, minutes per model.

## Cost per model

162 generations (54 × 3), typically 500–2,000 tokens each. No judge.

## Caveats

- Measures **quantity and diversity, not idea quality**: in our pilot the strong reference model scored below several local models.
- The metric choices (embedding model, spaCy model, idea splitting) are ours; the paper names no checkpoints. Not comparable with the paper.
- The upstream inference runner is incomplete (empty module), so prompts are rebuilt from the official templates.
- The anonymous mirror can change; keep the hashes.
