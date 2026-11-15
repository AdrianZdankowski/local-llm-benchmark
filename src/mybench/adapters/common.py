import csv
import hashlib
import json
from __future__ import annotations
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from mybench.schema import count_chars

@dataclass
class Skips:
    """Counter of examples skipped by adapters, keyed by reason."""

    counts: dict[str, int] = field(default_factory=dict)

    def add(self, reason: str) -> None:
        self.counts[reason] = self.counts.get(reason, 0) + 1

def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e

def read_csv(path: Path) -> Iterator[dict[str, str]]:
    csv.field_size_limit(2**31 - 1)
    with path.open(encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)

@lru_cache(maxsize=None)
def file_version(path: Path) -> str:
    """Source version: sha256 digest of the raw file (reproducibility without HF revisions/commits)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()[:16]}"

def make_id(*parts: object) -> str:
    """`<source>-<subset>-<no>`; empty parts are omitted."""
    return "-".join(str(p) for p in parts if p not in (None, ""))

def pad(n: int | str, width: int = 4) -> str:
    return str(n).zfill(width) if str(n).isdigit() else str(n)

def meta(messages: list[dict[str, str]], **extra: Any) -> dict[str, Any]:
    return {"input_tokens": None, "input_chars": count_chars(messages), **extra}
