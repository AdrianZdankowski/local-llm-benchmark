from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_csv
from mybench.schema import Record
from mybench.templates import render

SOURCE = "facts_grounding"
ID_PREFIX = "facts"
LICENSE = "CC-BY-4.0"
RAW_FILE = Path("facts-grounding/examples.csv")
SUBSET = "public"
TEMPLATE = "facts-original"

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for n, row in enumerate(read_csv(path)):
        if not row["full_prompt"].strip() or not row["context_document"].strip():
            skips.add("facts_grounding: empty prompt or document")
            continue
        messages = render(TEMPLATE, full_prompt=row["full_prompt"])
        yield Record(
            id=make_id(ID_PREFIX, SUBSET, pad(n)),
            category="summarization",
            source=SOURCE,
            source_subset=SUBSET,
            source_id=str(n),
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            # Separate fields for the judge (evaluation templates use {user_request}, {context_document}).
            inputs={
                "system_instruction": row["system_instruction"],
                "context_document": row["context_document"],
                "user_request": row["user_request"],
            },
            messages=messages,
            eval={"type": "llm_judge", "params": {"protocol": "facts_two_stage"}},
            meta=meta(messages),
        )