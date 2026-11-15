import sys
import statistics
import argparse
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
from pydantic import ValidationError
from mybench.adapters import ADAPTERS, Skips
from mybench.schema import Record

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--out-dir", type=Path, default=ROOT / "data" / "unified")
    p.add_argument(
        "--sources",
        nargs="+",
        choices=sorted(ADAPTERS),
        default=list(ADAPTERS),
        help="sources to process (default: all)",
    )
    return p.parse_args()

def main() -> int:
    args = parse_args()
    by_category: dict[str, list[Record]] = defaultdict(list)
    seen_ids: set[str] = set()
    per_source: Counter[str] = Counter()
    chars: dict[str, list[int]] = defaultdict(list)
    skips = Skips()
    errors = 0

    for name in args.sources:
        try:
            for rec in ADAPTERS[name](args.raw_dir, skips):
                if rec.id in seen_ids:
                    print(f"[ERROR] {name}: duplicate id {rec.id}", file=sys.stderr)
                    errors += 1
                    continue
                seen_ids.add(rec.id)
                by_category[rec.category].append(rec)
                per_source[name] += 1
                chars[name].append(rec.meta.input_chars or 0)
        except ValidationError as e:
            print(f"[ERROR] {name}: record does not match the schema:\n{e}", file=sys.stderr)
            errors += 1
        except FileNotFoundError as e:
            print(f"[ERROR] {name}: missing file {e.filename}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\nAborted: {errors} errors, nothing was written.", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for category, records in sorted(by_category.items()):
        out = args.out_dir / f"{category}.jsonl"
        with out.open("w", encoding="utf-8", newline="\n") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")
        print(f"{out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(records)} records")

    print("\nSource                 records   chars: median / max")
    for name in args.sources:
        c = chars[name]
        if c:
            print(f"  {name:<20} {per_source[name]:>7}   {int(statistics.median(c)):>7} / {max(c)}")
        else:
            print(f"  {name:<20} {0:>7}")
    if skips.counts:
        print("\nSkipped:")
        for reason, n in sorted(skips.counts.items()):
            print(f"  {n:>6}  {reason}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
