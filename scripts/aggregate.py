from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mybench.scoring.aggregate import DEFAULT_PASS, load_scores, report  # noqa: E402

DESCRIPTION = """Summarise normalised score files across models: headline with 95% CI (Wilson / bootstrap),
spread between models and items with the same outcome for every model (drop candidates)."""

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scores-dir", type=Path, default=ROOT / "runs" / "scores")
    p.add_argument("-o", "--out-dir", type=Path, default=ROOT / "runs" / "report")
    p.add_argument("--models", nargs="+", help="only these models (default: all found)")
    p.add_argument("--pass", dest="passes", nargs="+", default=[], metavar="SOURCE=T",
                   help=f"pass threshold per 0-1 source (default {DEFAULT_PASS}), e.g. listqa=0.5")
    p.add_argument("--weak-anchor", help="model expected to score lowest")
    p.add_argument("--strong-anchor", help="model expected to score highest")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        thresholds = {k: float(v) for k, v in (x.split("=", 1) for x in args.passes)}
    except ValueError:
        print("[ERROR] --pass expects SOURCE=THRESHOLD", file=sys.stderr)
        return 1
    scores = load_scores(args.scores_dir, args.models)
    if not scores:
        print(f"[ERROR] no score files in {args.scores_dir}; run score.py first", file=sys.stderr)
        return 1
    path = report(scores, args.out_dir, pass_thresholds=thresholds, weak_anchor=args.weak_anchor,
                  strong_anchor=args.strong_anchor)
    n_models = len({m for m, _ in scores})
    n_sources = len({s for _, s in scores})
    print(f"{len(scores)} score files, {n_models} models, {n_sources} sources -> {path}, summary.csv, "
          "drop_candidates.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
