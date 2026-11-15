from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
from mybench.adapters.common import Skips, file_version, make_id, meta, read_jsonl
from mybench.schema import Record
from mybench.templates import render

SOURCE = "noveltybench"
LICENSE = "MIT"
SUBSETS = {
    "curated": Path("novelty-bench/curated.jsonl"),
    "wildchat": Path("novelty-bench/wildchat-1k.jsonl"),
}
TEMPLATE = "chat-raw"
GROUP_SIZE = 10  # k from NoveltyBench
PATIENCE = 0.8

def load(raw_dir: Path, skips: Skips) -> Iterator[Record]:
    for subset, rel in SUBSETS.items():
        path = raw_dir / rel
        version = file_version(path)
        for row in read_jsonl(path):
            if row.get("chosen") is False:
                skips.add(f"noveltybench/{subset}: chosen=false")
                continue
            messages = render(TEMPLATE, user_request=row["prompt"])
            # Source IDs look like "curated-0" or "WildChat-<hash>".
            local_id = row["id"].split("-", 1)[1]
            if subset == "curated":
                local_id = local_id.zfill(3)
            yield Record(
                id=make_id(SOURCE, subset, local_id),
                category="chat",
                subcategory=row.get("category"),
                source=SOURCE,
                source_subset=subset,
                source_id=row["id"],
                source_version=version,
                source_license=LICENSE,
                lang="en",
                prompt_template_id=TEMPLATE,
                inputs={"user_request": row["prompt"]},
                messages=messages,
                eval={
                    "type": "diversity",
                    "params": {"patience": PATIENCE},
                    "group_size": GROUP_SIZE,
                },
                meta=meta(messages),
            )