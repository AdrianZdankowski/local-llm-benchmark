from __future__ import annotations
# Generation runner: sends `record.messages` to an OpenAI-compatible `/chat/completions` endpoint.
#
# Stdlib HTTP only (urllib), no vendor SDK. Resumable: rows already in the output file without an error are skipped.
# One output line per (record, sample): id, sample, model, source, output, reasoning, finish_reason, usage, secs,
# params (the request without messages), or id, sample, model, source, error.
#
# Request parameters, later ones override earlier ones:
#   1. defaults: max_tokens (CLI), seed = SEED + sample index;
#   2. the model's `sampling` from configs/models.json (and `model`, the served model name, if set);
#   3. benchmark-fixed generation params of the record: GEN_KEYS found in `record.eval.params`,
#      then the `record.eval.params["gen"]` dict, if present;
#   4. the model's `chat_template_kwargs`, passed through unchanged.
import json
import threading
import time
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from mybench.schema import Record

SEED = 20261116
GEN_KEYS = (
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "max_tokens",
    "presence_penalty",
    "frequency_penalty",
    "repetition_penalty",
    "stop",
)

def load_records(paths: list[Path], source: str) -> list[Record]:
    """All records of one source from unified JSONL files, validated against the schema."""
    out: list[Record] = []
    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = Record.model_validate_json(line)
                    if rec.source == source:
                        out.append(rec)
    return out

def load_split(path: Path) -> list[str]:
    """Record ids of a split file `{"source", "seed", "ids": [...], ...}`."""
    return list(json.loads(path.read_text(encoding="utf-8"))["ids"])

def default_split(splits_dir: Path, source: str) -> Path:
    """`<splits_dir>/<source>.json`, else the split file in `splits_dir` whose "source" field is `source`."""
    path = splits_dir / f"{source}.json"
    if path.exists():
        return path
    for p in sorted(splits_dir.glob("*.json")):
        if json.loads(p.read_text(encoding="utf-8")).get("source") == source:
            return p
    raise FileNotFoundError(f"no split file for source {source!r} in {splits_dir} (pass --split or --all)")

def select(records: list[Record], ids: list[str] | None) -> list[Record]:
    """Records in split order; every split id must exist."""
    if ids is None:
        return records
    by_id = {r.id: r for r in records}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise KeyError(f"{len(missing)} split ids are not in the input (e.g. {missing[0]})")
    return [by_id[i] for i in ids]

def load_model_config(path: Path, model: str) -> dict[str, Any]:
    models = json.loads(path.read_text(encoding="utf-8"))
    if model not in models:
        keys = ", ".join(k for k in models if not k.startswith("_"))
        raise KeyError(f"model {model!r} is not in {path} (available: {keys})")
    return models[model]

def chat(base_url: str, payload: dict[str, Any], api_key: str | None = None, timeout: float = 900) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), headers=headers
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def wait_for_server(base_url: str, timeout: float, api_key: str | None = None) -> bool:
    """Polls `<base_url>/models` until it answers or `timeout` seconds pass."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(urllib.request.Request(base_url.rstrip("/") + "/models", headers=headers), timeout=5)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(5)
    return False

def gen_params(rec: Record) -> dict[str, Any]:
    p = rec.eval.params
    out = {k: p[k] for k in GEN_KEYS if k in p}
    out.update(p.get("gen") or {})
    return out

def n_samples(rec: Record, override: int | None) -> int:
    return override if override else int(rec.eval.params.get("n_samples", 1))

def build_payload(rec: Record, sample: int, model: str, cfg: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": cfg.get("model", model),
        "messages": [m.model_dump() for m in rec.messages],
        "max_tokens": max_tokens,
        "seed": SEED + sample,
    }
    payload.update(cfg.get("sampling", {}))
    payload.update(gen_params(rec))  # benchmark-fixed params override model defaults
    if cfg.get("chat_template_kwargs"):
        payload["chat_template_kwargs"] = cfg["chat_template_kwargs"]
    return payload

def done_keys(out_path: Path) -> set[tuple[str, int]]:
    done: set[tuple[str, int]] = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue  # partial line from an interrupted run
                if "error" not in r:
                    done.add((r["id"], r["sample"]))
    return done

def run(
    records: list[Record],
    out_path: Path,
    *,
    base_url: str,
    model: str,
    cfg: dict[str, Any],
    api_key: str | None = None,
    concurrency: int = 2,
    max_tokens: int = 4096,
    samples: int | None = None,
    timeout: float = 900,
    log: Callable[[str], None] = print,
) -> tuple[int, int]:
    """Runs all missing (record, sample) jobs, appending to `out_path`. Returns (n_ok, n_errors)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(out_path)
    jobs = [(r, s) for r in records for s in range(n_samples(r, samples)) if (r.id, s) not in done]
    source = records[0].source if records else "?"
    log(f"{model}/{source}: {len(jobs)} jobs ({len(done)} already done)")
    lock = threading.Lock()

    def one(rec: Record, sample: int) -> dict[str, Any]:
        payload = build_payload(rec, sample, model, cfg, max_tokens)
        row: dict[str, Any] = {"id": rec.id, "sample": sample, "model": model, "source": rec.source}
        t0 = time.time()
        try:
            resp = chat(base_url, payload, api_key, timeout)
            choice = resp["choices"][0]
            msg = choice["message"]
            row.update(
                output=msg.get("content"),
                reasoning=msg.get("reasoning_content") or msg.get("reasoning"),
                finish_reason=choice.get("finish_reason"),
                usage=resp.get("usage"),
                secs=round(time.time() - t0, 2),
                params={k: v for k, v in payload.items() if k != "messages"},
            )
        except Exception as e:  # noqa: BLE001
            row["error"] = repr(e)[:500]
        with lock, out_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    n_ok = n_err = 0
    with ThreadPoolExecutor(max(1, concurrency)) as ex:
        futures = [ex.submit(one, r, s) for r, s in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            failed = "error" in fut.result()
            n_err += failed
            n_ok += not failed
            if i % 25 == 0 or i == len(jobs):
                log(f"  {i}/{len(jobs)} ok={n_ok} err={n_err}")
    return n_ok, n_err
