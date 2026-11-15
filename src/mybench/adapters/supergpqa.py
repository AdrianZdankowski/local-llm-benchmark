from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, pad, read_jsonl
from mybench.schema import Record
from mybench.templates import choice_letters, render

SOURCE = "supergpqa"
LICENSE = "ODC-BY-1.0"
RAW_FILE = Path("supergpqa/SuperGPQA-all.jsonl")
TEMPLATE = "mc-v1"

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    path = raw_dir / RAW_FILE
    version = file_version(path)
    for n, row in enumerate(read_jsonl(path)):
        choices = row["options"]
        letters = choice_letters(len(choices))
        letter = row["answer_letter"]
        if letter not in letters or choices[letters.index(letter)] != row["answer"]:
            skips.add("supergpqa: answer_letter does not match answer")
            continue
        messages = render(TEMPLATE, question=row["question"], choices=choices)
        yield Record(
            id=make_id(SOURCE, pad(n, 5)),
            category="info",
            subcategory=row["discipline"],
            source=SOURCE,
            source_id=row["uuid"],
            source_version=version,
            source_license=LICENSE,
            lang="en",
            prompt_template_id=TEMPLATE,
            messages=messages,
            choices=choices,
            answer={"type": "mc", "index": letters.index(letter), "letter": letter},
            eval={
                "type": "mc_generate",
                "params": {
                    "field": row["field"],
                    "subfield": row["subfield"],
                    "difficulty": row["difficulty"],
                    "is_calculation": row["is_calculation"],
                },
            },
            meta=meta(messages),
        )