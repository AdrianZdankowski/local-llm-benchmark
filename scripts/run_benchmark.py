from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mybench.run.runner import (  # noqa: E402
    default_split,
    load_model_config,
    load_records,
    load_split,
    run,
    select,
    wait_for_server,
)

DESCRIPTION = """Send the prompts of one source to an OpenAI-compatible endpoint.

Records come from the unified JSONL files, filtered by source and by the split file; outputs are appended
to runs/<model>/<source>.jsonl (resumable: (id, sample) pairs already done without an error are skipped)."""

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="record source, e.g. listqa")
    p.add_argument("--model", required=True, help="model key in --models-config")
    p.add_argument("--base-url", default=os.environ.get("BENCH_BASE_URL"),
                   help="OpenAI-compatible base URL ending in /v1 (default: $BENCH_BASE_URL)")
    p.add_argument("-i", "--input", type=Path, nargs="+",
                   help="unified JSONL file(s) (default: all data/unified/*.jsonl)")
    p.add_argument("--split", type=Path,
                   help="split file (default: data/splits/<source>.json or the data/splits/*.json with that source)")
    p.add_argument("--all", action="store_true", help="ignore the split and run every record of the source")
    p.add_argument("--models-config", type=Path, default=ROOT / "configs" / "models.json")
    p.add_argument("--api-key-env", default="BENCH_API_KEY", help="environment variable with the API key, if needed")
    p.add_argument("--out-dir", type=Path, default=ROOT / "runs")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--max-tokens", type=int, default=4096, help="default when the record sets no max_tokens")
    p.add_argument("--n-samples", type=int, help="override eval.params.n_samples of every record")
    p.add_argument("--limit", type=int, default=0, help="only the first N records")
    p.add_argument("--timeout", type=float, default=900, help="seconds per request")
    p.add_argument("--wait-server", type=float, default=0, help="wait up to N seconds for <base-url>/models")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    if not args.base_url:
        print("[ERROR] no --base-url and BENCH_BASE_URL is not set", file=sys.stderr)
        return 1
    api_key = os.environ.get(args.api_key_env)
    inputs = args.input or sorted((ROOT / "data" / "unified").glob("*.jsonl"))
    try:
        split = None if args.all else args.split or default_split(ROOT / "data" / "splits", args.source)
        cfg = load_model_config(args.models_config, args.model)
        records = select(load_records(inputs, args.source), load_split(split) if split else None)
    except (OSError, KeyError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    if not records:
        print(f"[ERROR] no records of source {args.source!r} in {len(inputs)} input file(s)", file=sys.stderr)
        return 1
    if args.limit:
        records = records[: args.limit]
    if args.wait_server and not wait_for_server(args.base_url, args.wait_server, api_key):
        print(f"[ERROR] server not ready at {args.base_url}", file=sys.stderr)
        return 1
    out = args.out_dir / args.model / f"{args.source}.jsonl"
    _, n_err = run(records, out, base_url=args.base_url, model=args.model, cfg=cfg, api_key=api_key,
                   concurrency=args.concurrency, max_tokens=args.max_tokens, samples=args.n_samples,
                   timeout=args.timeout, log=lambda s: print(s, flush=True))
    print(f"-> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 1 if n_err else 0

if __name__ == "__main__":
    sys.exit(main())
