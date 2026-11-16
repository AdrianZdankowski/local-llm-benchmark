# Dataset sources

- [IFBench](https://github.com/allenai/IFBench)
- [Marco-Bench-MIF](https://github.com/ATH-MaaS/Marco-LLM)
- [SuperGPQA](https://github.com/SuperGPQA/SuperGPQA)
- [NoveltyBench](https://github.com/novelty-bench/novelty-bench)
- [WMT26](https://github.com/wmt-conference/wmt26-general-mt)
- [Facts grounding public](https://huggingface.co/datasets/google/FACTS-grounding-public)

## Fresh sources

Not committed (licensed data, gitignored). Fetch them at the pinned revisions with `python scripts/download_fresh_sources.py`, which verifies sha256.

| Source | Directory | Official source (pinned) | License |
|---|---|---|---|
| ListQA | `listqa/` | [HF AmazonScience/ListQA](https://huggingface.co/datasets/AmazonScience/ListQA) @ `748eb345a110c4a7cb2af6b6be8074840974e15f`, `data/all.jsonl`; scorer [ListQA-Eval](https://github.com/amazon-science/ListQA-Eval) @ `83faa7c3a089a7c835c89f408f44b5b88ed27469` | CC BY-NC 4.0 (data and code), not for training |
| VagueBench | `vaguebench/` | [HF rongyu0101/VagueBench](https://huggingface.co/datasets/rongyu0101/VagueBench) @ `62d4cc6f17cb5efaa46da02e7d42bbf64c96aa02`, `VagueBench_en.jsonl`; harness [VagueBench](https://github.com/zhangrongyu0101/VagueBench) @ `af4587d6584cad36cba85d42fba4eef2a80bde6d` | Apache-2.0 on the HF card only; no LICENSE in the repo, paper says research purposes |
| SlopBench (The Slop Index) | `slopbench/` | [slop-index](https://github.com/hgaddipati1118/slop-index) @ `4eb24d9b400ecbd31bf16b630cc0a8f3ffb3278f`, `scenarios/pilot/{email,social,essay,slack}.json` | MIT (repo); prompts CC BY 4.0 |
| IDEAFix | `ideafix/` | [anonymous mirror CreativityAndEthicalFramework-C01E](https://anonymous.4open.science/r/CreativityAndEthicalFramework-C01E), `data/202510_ProtocolCreativityEthics_VF/{Briefs,Crea_prompts}-Table 1.csv` (no git history: pinned by sha256); dataset card [HF soummyaah/IDEAFix](https://huggingface.co/datasets/soummyaah/IDEAFix) | CC BY 4.0 (data), MIT (code) |
| WMT26 human references (`wmt26_humanref`) | `wmt26/` | same file as WMT26 above, [wmt26-general-mt](https://github.com/wmt-conference/wmt26-general-mt) @ `63aa5d24311a7e7e3e8173528f3771c7e8b4be78` | research use, cite the WMT26 Findings paper |
