from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mybench.run.runner import default_split, load_records, load_split, select  # noqa: E402
from mybench.scoring import DEFAULT_SCORER, SCORERS  # noqa: E402
from mybench.scoring.common import write_json  # noqa: E402

DESCRIPTION = """Score runner outputs (runs/<model>/<source>.jsonl) and write normalised score files
(runs/scores/<model>/<source>.json) for aggregate.py."""

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="record source, e.g. listqa")
    p.add_argument("--model", required=True, nargs="+", help="model key(s) (directories under --runs-dir)")
    p.add_argument("--scorer", choices=SCORERS, help="default: by source (" +
                   ", ".join(f"{k} -> {v}" for k, v in DEFAULT_SCORER.items()) + ")")
    p.add_argument("-i", "--input", type=Path, nargs="+", help="unified JSONL file(s) (default: data/unified/*.jsonl)")
    p.add_argument("--split", type=Path,
                   help="split file (default: data/splits/<source>.json or the data/splits/*.json with that source)")
    p.add_argument("--all", action="store_true", help="score against every record of the source, not the split")
    p.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    p.add_argument("--scores-dir", type=Path, default=ROOT / "runs" / "scores")
    p.add_argument("--device", default="cpu", help="ideafix/metricx: cpu or cuda/gpu")
    g = p.add_argument_group("listqa (judge: $JUDGE_BASE_URL, $JUDGE_MODEL, optional $JUDGE_API_KEY)")
    g.add_argument("--listqa-dir", type=Path, default=Path(os.environ.get("LISTQA_DIR", ROOT / "external" / "listqa")))
    g.add_argument("--judge-concurrency", type=int, default=4)
    g.add_argument("--batch-pairs", type=int, default=20)
    g = p.add_argument_group("slopbench")
    g.add_argument("--slopbench-dir", type=Path,
                   default=Path(os.environ.get("SLOPBENCH_DIR", ROOT / "external" / "slopbench")))
    g = p.add_argument_group("metricx")
    g.add_argument("--metricx-dir", type=Path, default=Path(os.environ.get("METRICX_DIR", ROOT / "external" / "metricx")))
    g.add_argument("--metricx-python", default=os.environ.get("METRICX_PYTHON", sys.executable),
                   help="Python of the MetricX environment (default: $METRICX_PYTHON or this Python)")
    g.add_argument("--metricx-checkpoint", default="google/metricx-24-hybrid-xl-v2p6-bfloat16")
    g.add_argument("--metricx-tokenizer", default="google/mt5-xl")
    g.add_argument("--metricx-batch-size", type=int, default=1)
    g.add_argument("--metricx-cache", type=Path, help="default: <scores-dir>/_work/metricx_cache.jsonl")
    return p.parse_args()

def main() -> int:
    if not sys.flags.utf8_mode:  # third-party scorers read files with the platform encoding
        return subprocess.run([sys.executable, "-X", "utf8", *sys.argv]).returncode
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    scorer = args.scorer or DEFAULT_SCORER.get(args.source)
    if not scorer:
        print(f"[ERROR] no default scorer for source {args.source!r}; pass --scorer", file=sys.stderr)
        return 1
    inputs = args.input or sorted((ROOT / "data" / "unified").glob("*.jsonl"))
    try:
        split = None if args.all else args.split or default_split(ROOT / "data" / "splits", args.source)
        records = select(load_records(inputs, args.source), load_split(split) if split else None)
    except (OSError, KeyError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    if not records:
        print(f"[ERROR] no records of source {args.source!r}", file=sys.stderr)
        return 1
    outputs = {m: args.runs_dir / m / f"{args.source}.jsonl" for m in args.model}
    for m, path in outputs.items():
        if not path.exists():
            print(f"[ERROR] {m}: no outputs at {path}", file=sys.stderr)
            return 1
    work = args.scores_dir / "_work"
    device = "cuda" if args.device == "gpu" else args.device

    if scorer == "metricx":
        from mybench.scoring import metricx
        cache = args.metricx_cache or work / "metricx_cache.jsonl"
        rows = [r for p in outputs.values() for r in metricx.rows_for(records, p, args.metricx_checkpoint)]
        metricx.predict_missing(rows, cache, metricx_dir=args.metricx_dir, python_exe=args.metricx_python,
                                checkpoint=args.metricx_checkpoint, tokenizer=args.metricx_tokenizer,
                                device="cpu" if device == "cpu" else "gpu", batch_size=args.metricx_batch_size)

    failed = []
    for m, path in outputs.items():
        try:
            if scorer == "listqa":
                from mybench.scoring import listqa
                judge_url, judge_model = os.environ.get("JUDGE_BASE_URL"), os.environ.get("JUDGE_MODEL")
                if not judge_url or not judge_model:
                    raise RuntimeError("set JUDGE_BASE_URL and JUDGE_MODEL")
                res = listqa.score(records, path, model=m, listqa_dir=args.listqa_dir,
                                   cache_path=work / m / f"{args.source}.judged.jsonl", judge_url=judge_url,
                                   judge_model=judge_model, judge_api_key=os.environ.get("JUDGE_API_KEY"),
                                   concurrency=args.judge_concurrency, batch_pairs=args.batch_pairs)
            elif scorer == "slopbench":
                from mybench.scoring import slopbench
                res = slopbench.score(records, path, model=m, slopbench_dir=args.slopbench_dir, work_dir=work / m)
            elif scorer == "ideafix":
                from mybench.scoring import ideafix
                res = ideafix.score(records, path, model=m, device=device)
            else:
                res = metricx.score(records, path, model=m, cache_path=cache, checkpoint=args.metricx_checkpoint)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {m}/{args.source}: {e}", file=sys.stderr)
            failed.append(m)
            continue
        res["source"] = args.source
        out = args.scores_dir / m / f"{args.source}.json"
        write_json(out, res)
        hl = "None" if res["headline"] is None else f"{res['headline']:.4f}"
        print(f"{m}/{args.source}: headline {hl}  items {res['n_items']}/{res['n_expected']}  errors "
              f"{res['n_errors']}{'' if res['complete'] else '  (INCOMPLETE)'} -> {out}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
