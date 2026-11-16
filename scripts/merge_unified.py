from __future__ import annotations
import argparse
import sys
from pathlib import Path
from collections import Counter
from pydantic import ValidationError  # noqa: E402
from mybench.schema import Record  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CATEGORY_ORDER = ["writing", "info", "summarization", "translation", "chat", "agents"]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in-dir", type=Path, default=ROOT / "data" / "unified")
    p.add_argument("-o", "--output", type=Path, default=ROOT / "data" / "benchmark.jsonl")
    p.add_argument(
        "--categories",
        nargs="+",
        choices=CATEGORY_ORDER,
        help="categories to include (default: all files found in --in-dir)",
    )
    return p.parse_args()

def input_files(in_dir: Path, categories: list[str] | None) -> list[Path]:
    if categories:
        files = [in_dir / f"{c}.jsonl" for c in categories]
        missing = [str(f) for f in files if not f.exists()]
        if missing:
            raise FileNotFoundError(", ".join(missing))
    else:
        files = [in_dir / f"{c}.jsonl" for c in CATEGORY_ORDER if (in_dir / f"{c}.jsonl").exists()]
    return files

def main() -> int:
    args = parse_args()
    try:
        files = input_files(args.in_dir, args.categories)
    except FileNotFoundError as e:
        print(f"[ERROR] missing input file(s): {e}", file=sys.stderr)
        return 1
    if not files:
        print(f"[ERROR] no <category>.jsonl files in {args.in_dir}; run build_dataset.py first", file=sys.stderr)
        return 1

    seen: set[str] = set()
    per_category: Counter[str] = Counter()
    per_source: Counter[str] = Counter()
    lines: list[str] = []
    errors = 0

    for path in files:
        expected = path.stem
        with path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = Record.model_validate_json(line)
                except ValidationError as e:
                    print(f"[ERROR] {path.name}:{lineno}: record does not match the schema:\n{e}", file=sys.stderr)
                    errors += 1
                    continue
                if rec.category != expected:
                    print(f"[ERROR] {path.name}:{lineno}: category {rec.category!r} in file for {expected!r}", file=sys.stderr)
                    errors += 1
                if rec.id in seen:
                    print(f"[ERROR] {path.name}:{lineno}: duplicate id {rec.id}", file=sys.stderr)
                    errors += 1
                    continue
                seen.add(rec.id)
                per_category[rec.category] += 1
                per_source[rec.source] += 1
                lines.append(line)

    if errors:
        print(f"\nAborted: {errors} errors, nothing was written.", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

    shown = args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output
    print(f"{shown}: {len(lines)} records from {len(files)} files")
    print("\nCategory          records")
    for cat in CATEGORY_ORDER:
        if per_category[cat]:
            print(f"  {cat:<15} {per_category[cat]:>7}")
    print("\nSource            records")
    for src, n in sorted(per_source.items()):
        print(f"  {src:<15} {n:>7}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
