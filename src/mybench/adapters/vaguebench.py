from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "vaguebench"
LICENSE = "Apache-2.0 (HF card tag only; the paper says research purposes)"
RAW_FILE = Path("vaguebench/VagueBench_en.jsonl")  # HF rongyu0101/VagueBench @ 62d4cc6f17cb5efaa46da02e7d42bbf64c96aa02
TEMPLATE = "chat-raw"
TARGET_SYSTEM = "You are a helpful AI assistant."  # TARGET_SYSTEM of the official evaluate.py
HARNESS = "github.com/zhangrongyu0101/VagueBench@af4587d6584cad36cba85d42fba4eef2a80bde6d"
GROUP_LABEL = {"A": "complete", "B": "intent_vague", "C": "fully_vague"}

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for row in read_jsonl(path):
        scenario_id, group = row["sample_id"].rsplit("_", 1)
        messages = render(TEMPLATE, user_request=row["initial_query"], system_instruction=TARGET_SYSTEM)
        yield Record(
            id=make_id(SOURCE, row["sample_id"]),
            category="info",
            subcategory=row["query_type"],
            source=SOURCE,
            source_subset=group,
            source_id=row["sample_id"],
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            inputs={"user_request": row["initial_query"], "system_instruction": TARGET_SYSTEM},
            messages=messages,
            # Hidden user intent: used by the simulated user and the coverage judge, never sent to the model.
            reference={
                "needs_clarification": row["needs_clarification"],
                "source_query": row["source_query"],
                "intents": row["intents"],
                "details": row["details"],
                "hidden_intent_ids": row["hidden_intent_ids"],
                "hidden_detail_ids": row["hidden_detail_ids"],
                "simulator_prompt": row["simulator_prompt"],
            },
            eval={
                "type": "llm_judge",
                "params": {
                    "harness": "vaguebench",
                    "code": HARNESS,
                    "note": (
                        "multi-turn with a simulated user: the model may ask clarification questions, "
                        "which an LLM simulator answers from the hidden intent; run via the official "
                        "evaluate.py (harness/vaguebench), judge and simulator behind JUDGE_BASE_URL"
                    ),
                    "max_clarification_turns": 5,
                    "metrics": ["metric1_should_ask", "metric2_avg_turns", "metric3_coverage"],
                },
            },
            meta=meta(messages, scenario_id=scenario_id, variant=GROUP_LABEL[group]),
        )
