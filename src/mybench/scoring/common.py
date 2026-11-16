from __future__ import annotations
# Shared helpers of the scorers: reading run outputs, record field access and the normalised score file.
#
# Normalised score file (runs/scores/<model>/<source>.json), read by aggregate.py:
#   source, model, headline, metric, higher_is_better, scale ("0-1" | "raw"),
#   stat (how items aggregate to the headline: "mean" | "f1_pr" | "ratio"), n_items, n_expected, n_errors,
#   n_covered, complete, scored_at, extra, items {record id: {"score": ..., ...}}.
import hashlib
import json
import re
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from mybench.schema import Record

def strip_think(text: str | None) -> str:
    """Final answer only: removes `<think>...</think>` blocks and anything before a dangling `</think>`."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    return text.split("</think>")[-1].strip()

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Rows of a JSONL file; unparsable lines (e.g. from an interrupted run) are skipped."""
    out: list[dict[str, Any]] = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out

def load_outputs(path: Path, ids: set[str] | None = None) -> dict[tuple[str, int], dict[str, Any]]:
    """(id, sample) -> last successful runner row, else the last error row. Rows outside `ids` are dropped."""
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for r in read_jsonl(path):
        if ids is not None and r.get("id") not in ids:
            continue
        key = (r["id"], r["sample"])
        if "error" not in r or key not in rows or "error" in rows[key]:
            rows[key] = r
    return rows

def pick(rec: Record, *paths: str, default: Any = None) -> Any:
    """First non-None value of dotted paths into the record, e.g. pick(rec, "reference.answer", "inputs.user_request")."""
    data = rec.model_dump()
    for path in paths:
        cur: Any = data
        for part in path.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is not None:
            return cur
    return default

def last_user_message(rec: Record) -> str:
    return next((m.content for m in reversed(rec.messages) if m.role == "user"), "")

def sha(parts: Iterable[Any]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]

def mean(xs: Iterable[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None

def summary(
    source: str,
    model: str,
    *,
    headline: float | None,
    metric: str,
    higher_is_better: bool,
    scale: str,
    stat: str,
    items: dict[str, dict[str, Any]],
    n_expected: int,
    n_errors: int,
    n_covered: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    covered = len(items) if n_covered is None else n_covered
    return {
        "source": source,
        "model": model,
        "headline": headline,
        "metric": metric,
        "higher_is_better": higher_is_better,
        "scale": scale,
        "stat": stat,
        "n_items": len(items),
        "n_expected": n_expected,
        "n_errors": n_errors,
        "n_covered": covered,  # expected items with an outcome (scored or errored)
        "complete": covered >= n_expected,
        "scored_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "extra": extra or {},
        "items": items,
    }

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
