from __future__ import annotations
import re
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "listqa"
LICENSE = "CC-BY-NC-4.0"  # data and code; not for training
RAW_FILE = Path("listqa/all.jsonl")  # HF AmazonScience/ListQA @ 748eb345a110c4a7cb2af6b6be8074840974e15f
TEMPLATE = "listqa-zero-shot"
EVAL_CODE = "github.com/amazon-science/ListQA-Eval@83faa7c3a089a7c835c89f408f44b5b88ed27469"

def gold_elements(answer: str) -> list[str]:
    """Gold list elements, parsed like listqa_eval.metrics.parse_reference_list_elements."""
    target = answer.replace("\n ", "\n").lower()
    return [e.strip() for e in re.findall(r"\n\d+\.\s(.+?)(?=\n\d+\.|\Z)", target, re.DOTALL)]

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    # The dataset has no item id: the 0-based line index is the id.
    for idx, row in enumerate(read_jsonl(path)):
        messages = render(TEMPLATE, user_request=row["problem"])
        yield Record(
            id=make_id(SOURCE, "all", pad(idx)),
            category="info",
            subcategory=row["category"],
            source=SOURCE,
            source_subset=row["prompt_type"],
            source_id=f"all-{idx}",
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            inputs={"user_request": row["problem"]},
            messages=messages,
            # answer is the verbatim target the official scorer needs; key_facts is for inspection.
            reference={"answer": row["answer"], "key_facts": gold_elements(row["answer"])},
            eval={
                "type": "llm_judge",
                "params": {
                    "protocol": "listqa-official",
                    "code": EVAL_CODE,
                    # Predicted and gold elements are paired by ROUGE-1 + Hungarian assignment, then
                    # each pair is graded A/B with LLM_JUDGE_PROMPT_TEMPLATE; P/R averaged over items.
                    "grading": "element-level (A=correct, B=incorrect)",
                    "metrics": ["llm_judge_f1", "format_correctness"],
                    "prompt_type": row["prompt_type"],
                    "ordered": row["ordered"],
                    "strip_thinking": True,
                },
            },
            meta=meta(
                messages,
                metadata=row["metadata"],  # original JSON string, read by the official scorer
                year_range=row["year_range"],
                country=row["country"],
                wikitable_source=row["wikitable_source"],
            ),
        )
