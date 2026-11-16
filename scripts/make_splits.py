"""Recompute the evaluation splits data/splits/<source>.json from built records.

Input is the output of build_dataset.py (one `<category>.jsonl` per category); the split is a seeded
stratified sample over the records of one source (src/mybench/sampling.py). Only the ids are
written, so the split can be committed even when the data cannot.

  python scripts/build_dataset.py --sources listqa vaguebench slopbench ideafix --out-dir data/unified_fresh
  python scripts/make_splits.py                       # rewrite data/splits/<source>.json
  python scripts/make_splits.py --check               # compare with the committed splits, write nothing

wmt26 (wmt26_humanref records) and the pilot splits are not recomputed here: their selection used a
custom procedure (see the "method" field of those files), so the committed id lists are the reference.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mybench.sampling import stratified_sample  # noqa: E402

SEED = 20261116

@dataclass(frozen=True)
class Spec:
    method: str
    record_stratum: Callable[[dict], str]  # stratum reported in "strata" (per record)
    n_units: int | None = None  # None: take every record
    unit: Callable[[dict], str] = lambda r: r["id"]  # sampling unit (records sharing it are kept together)
    unit_stratum: Callable[[dict], str] | None = None  # stratum used for allocation (per unit)

SPECS: dict[str, Spec] = {
    "listqa": Spec(
        method="1500 items, stratified by category x prompt_type, proportional allocation with largest "
        "remainder, random.Random(seed).sample per stratum (HF AmazonScience/ListQA @ 748eb345)",
        record_stratum=lambda r: f"{r['subcategory']}|{r['source_subset']}",
        n_units=1500,
    ),
    "vaguebench": Spec(
        method="100 whole scenarios x 3 variants (A complete, B intent-vague, C fully vague) = 300 items; "
        "scenarios stratified by query_type, proportional allocation with largest remainder "
        "(HF rongyu0101/VagueBench @ 62d4cc6f)",
        record_stratum=lambda r: f"{r['source_subset']}|{r['subcategory']}",
        n_units=100,
        unit=lambda r: r["meta"]["scenario_id"],
        unit_stratum=lambda r: r["subcategory"],
    ),
    "slopbench": Spec(
        method="all 112 public scenarios, no sampling (slop-index @ 4eb24d9b)",
        record_stratum=lambda r: r["subcategory"],
    ),
    "ideafix": Spec(
        method="all 82 briefs except jailbreak (E) and ethical-dilemma (O) categories = 54, neutral framing, "
        "control prompt only, no sampling (anonymous mirror CreativityAndEthicalFramework-C01E)",
        record_stratum=lambda r: "all",
    ),
}

def load_records(in_dir: Path, source: str) -> list[dict]:
    records = []
    for path in sorted(in_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            records += [r for r in map(json.loads, filter(str.strip, f)) if r["source"] == source]
    return records

def make_split(source: str, records: list[dict]) -> dict:
    spec = SPECS[source]
    if spec.n_units is None:
        chosen = records
    else:
        unit_stratum: dict[str, str] = {}
        for r in records:
            s = (spec.unit_stratum or spec.record_stratum)(r)
            if unit_stratum.setdefault(spec.unit(r), s) != s:
                raise ValueError(f"{source}: unit {spec.unit(r)} spans several strata")
        units = set(stratified_sample(sorted(unit_stratum), unit_stratum.__getitem__, spec.n_units, SEED))
        chosen = [r for r in records if spec.unit(r) in units]
    return {
        "source": source,
        "seed": SEED,
        "method": spec.method,
        "strata": dict(sorted(Counter(spec.record_stratum(r) for r in chosen).items())),
        "source_version": " ".join(sorted({r["source_version"] for r in chosen})),
        "ids": sorted(r["id"] for r in chosen),
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in-dir", type=Path, default=ROOT / "data" / "unified_fresh")
    p.add_argument("--out-dir", type=Path, default=ROOT / "data" / "splits")
    p.add_argument("--sources", nargs="+", choices=sorted(SPECS), default=list(SPECS))
    p.add_argument("--check", action="store_true", help="compare with existing splits instead of writing")
    args = p.parse_args()

    failed = 0
    for source in args.sources:
        records = load_records(args.in_dir, source)
        if not records:
            print(f"[ERROR] {source}: no records in {args.in_dir}", file=sys.stderr)
            failed += 1
            continue
        split = make_split(source, records)
        out = args.out_dir / f"{source}.json"
        text = json.dumps(split, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            same = out.exists() and json.loads(out.read_text(encoding="utf-8")) == split
            print(f"{source}: {len(split['ids'])} ids, {'matches' if same else 'DIFFERS from'} {out.name}")
            failed += not same
        else:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8", newline="\n")
            print(f"{source}: {len(split['ids'])} ids -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
