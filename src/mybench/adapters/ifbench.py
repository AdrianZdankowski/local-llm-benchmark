from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "ifbench"
LICENSE = "ODC-BY-1.0"  # data license; the IFBench code is Apache-2.0
RAW_FILE = Path("ifbench/IFBench_test.jsonl")
TEMPLATE = "chat-raw"

def clean_kwargs(kwargs: list[dict]) -> list[dict]:
    """IFBench stores every possible argument, unset ones as null; keep only the set ones."""
    return [{k: v for k, v in kw.items() if v is not None} for kw in kwargs]

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for row in read_jsonl(path):
        messages = render(TEMPLATE, user_request=row["prompt"])
        yield Record(
            id=make_id(SOURCE, pad(row["key"])),
            category="writing",
            source=SOURCE,
            source_id=str(row["key"]),
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            inputs={"user_request": row["prompt"]},
            messages=messages,
            eval={
                "type": "rules",
                "params": {
                    "checker": "ifbench",
                    "instruction_id_list": row["instruction_id_list"],
                    "kwargs": clean_kwargs(row["kwargs"]),
                },
            },
            meta=meta(messages),
        )
