from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "marco_mif"
LICENSE = "Apache-2.0"
RAW_FILE = Path("marco-bench-mif/pl.jsonl")
LANG = "pl"
TEMPLATE = "chat-raw"

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for row in read_jsonl(path):
        messages = render(TEMPLATE, user_request=row["prompt"])
        yield Record(
            id=make_id(SOURCE, LANG, pad(row["key"])),
            category="writing",
            source=SOURCE,
            source_subset=LANG,
            source_id=str(row["key"]),
            source_version=version,
            source_license=LICENSE,
            lang=LANG,
            prompt_template_id=TEMPLATE,
            inputs={"user_request": row["prompt"]},
            messages=messages,
            eval={
                "type": "rules",
                "params": {
                    # Rules in the IFEval format (instruction_id_list + kwargs).
                    "checker": "ifeval",
                    "instruction_id_list": row["instruction_id_list"],
                    "kwargs": row["kwargs"],
                },
            },
            # The dataset was created by localizing the English IFEval.
            meta=meta(messages, translated_from="en"),
        )
