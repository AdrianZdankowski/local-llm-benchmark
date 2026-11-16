from __future__ import annotations
# Reference-based translation scoring with MetricX-24, run from a local clone of
# https://github.com/google-research/metricx (`metricx_dir`, module `metricx24.predict`) in its own Python
# environment (`python_exe`; the clone pins old transformers/datasets versions, see scripts/README.md).
#
# Rows are normalised like the WMT inputs (<p>/</p> removed, <br> -> newline, whitespace stripped) and cached by
# (checkpoint, source, hypothesis, reference), so the model is loaded once for all models' uncached rows and
# re-scoring is free. Score = predicted error in [0, 25], lower = better; the floor is not 0, compare models only
# with each other on the same items. Missing/empty answers are scored as empty hypotheses.
#
# Record fields used: source = inputs.source_text; reference = reference.translation;
# reported per pair (src_lang-tgt_lang) and per domain (subcategory).
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from mybench.schema import Record
from mybench.scoring.common import load_outputs, mean, read_jsonl, sha, strip_think, summary

DEFAULT_CHECKPOINT = "google/metricx-24-hybrid-xl-v2p6-bfloat16"
DEFAULT_TOKENIZER = "google/mt5-xl"

def clean(text: str | None) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    return re.sub(r"</?p>", "", text, flags=re.I).strip()

def rows_for(records: list[Record], outputs_path: Path, checkpoint: str) -> list[dict[str, Any]]:
    """One MetricX row per (record, sample) with an output (errors become empty hypotheses)."""
    items = {r.id: r for r in records}
    out = []
    for (iid, s), r in sorted(load_outputs(outputs_path, set(items)).items()):
        rec = items[iid]
        hyp = "" if "error" in r else clean(strip_think(r.get("output")))
        row = {"id": iid, "sample": s, "source": clean(rec.inputs.source_text if rec.inputs else ""),
               "hypothesis": hyp, "reference": clean(rec.reference.translation if rec.reference else ""),
               "failed": "error" in r or not hyp}
        row["key"] = sha([checkpoint, row["source"], row["hypothesis"], row["reference"]])
        out.append(row)
    return out

def load_cache(cache_path: Path) -> dict[str, float]:
    return {r["key"]: r["prediction"] for r in read_jsonl(cache_path)}

def predict_missing(
    rows: list[dict[str, Any]],
    cache_path: Path,
    *,
    metricx_dir: Path,
    python_exe: str,
    checkpoint: str = DEFAULT_CHECKPOINT,
    tokenizer: str = DEFAULT_TOKENIZER,
    device: str = "cpu",
    batch_size: int = 1,
    max_input_length: int = 1536,
) -> int:
    """Runs MetricX on rows not in the cache and appends the predictions to it. Returns the number of new rows."""
    cache = load_cache(cache_path)
    todo = {r["key"]: r for r in rows if r["key"] not in cache}
    if not todo:
        return 0
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_path.parent) as tmp:
        inp, outp = Path(tmp) / "in.jsonl", Path(tmp) / "out.jsonl"
        inp.write_text("".join(json.dumps({k: r[k] for k in ("key", "source", "hypothesis", "reference")},
                                          ensure_ascii=False) + "\n" for r in todo.values()),
                       encoding="utf-8", newline="\n")
        env = {**os.environ, "PYTHONPATH": str(metricx_dir), "PYTHONUTF8": "1"}
        if device == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = ""  # metricx24.predict uses CUDA whenever torch sees a GPU
        cmd = [python_exe, "-m", "metricx24.predict", "--tokenizer", tokenizer, "--model_name_or_path", checkpoint,
               "--max_input_length", str(max_input_length), "--batch_size", str(batch_size),
               "--input_file", str(inp), "--output_file", str(outp)]
        print(f"MetricX: {len(todo)} rows ({checkpoint}, {device})", flush=True)
        subprocess.run(cmd, env=env, check=True)
        preds = read_jsonl(outp)
    with cache_path.open("a", encoding="utf-8", newline="\n") as f:
        for r in preds:
            f.write(json.dumps({"key": r["key"], "prediction": r["prediction"], "checkpoint": checkpoint}) + "\n")
    return len(preds)

def score(
    records: list[Record], outputs_path: Path, *, model: str, cache_path: Path, checkpoint: str = DEFAULT_CHECKPOINT
) -> dict[str, Any]:
    cache = load_cache(cache_path)
    rows = rows_for(records, outputs_path, checkpoint)
    missing = [r for r in rows if r["key"] not in cache]
    if missing:
        raise RuntimeError(f"{model}: {len(missing)} rows have no MetricX prediction; run predict_missing first")
    by_rec = {r.id: r for r in records}
    per_id: dict[str, list[float]] = {}
    for r in rows:
        per_id.setdefault(r["id"], []).append(cache[r["key"]])
    items = {}
    for iid, preds in per_id.items():
        rec = by_rec[iid]
        items[iid] = {"score": mean(preds), "lang_pair": f"{rec.src_lang}-{rec.tgt_lang}", "domain": rec.subcategory}
    by_pair: dict[str, list[float]] = {}
    by_domain: dict[str, list[float]] = {}
    for v in items.values():
        by_pair.setdefault(v["lang_pair"], []).append(v["score"])
        by_domain.setdefault(str(v["domain"]), []).append(v["score"])
    return summary(
        records[0].source if records else "wmt26", model,
        headline=mean(v["score"] for v in items.values()),
        metric=f"MetricX-24 error ({checkpoint}), mean over items (0-25, lower = better)",
        higher_is_better=False, scale="raw", stat="mean", items=items, n_expected=len(records),
        n_errors=sum(r["failed"] for r in rows),
        extra={"checkpoint": checkpoint, "by_lang_pair": {k: mean(v) for k, v in sorted(by_pair.items())},
               "by_domain": {k: mean(v) for k, v in sorted(by_domain.items())}},
    )
