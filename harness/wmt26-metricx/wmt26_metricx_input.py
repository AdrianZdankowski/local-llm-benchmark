"""Build the MetricX-24 input JSONL for WMT26 from the item file and one model's outputs.

  python harness/wmt26-metricx/wmt26_metricx_input.py PRED.jsonl OUT.jsonl --items ITEMS.jsonl
  python harness/wmt26-metricx/wmt26_metricx_input.py --ref-as-hyp OUT.jsonl --items ITEMS.jsonl [--limit N]   # smoke test

ITEMS.jsonl: one selected WMT26 item per line with `id`, `input.lang_pair`, `input.domain`,
`input.source` (with <p> tags) and `reference` (human reference, with tags).
PRED.jsonl: one line per item with the item id and the model's raw answer
(field names set by --id-field / --text-field).

Source, hypothesis and reference get the same light normalisation: <p>/</p> removed,
<br> -> newline, surrounding whitespace stripped. Missing or empty answers are scored as
empty hypotheses (MetricX then gives a bad score, as it should).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def clean(text: str | None) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"</?p>", "", text, flags=re.I)
    return text.strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="[PRED.jsonl] OUT.jsonl")
    ap.add_argument("--items", type=Path, required=True, help="selected WMT26 items (JSONL, format above)")
    ap.add_argument("--ref-as-hyp", action="store_true", help="use the reference as hypothesis (smoke test)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--id-field", default="id")
    ap.add_argument("--text-field", default="output")
    args = ap.parse_args()

    with args.items.open(encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()][: args.limit]
    if args.ref_as_hyp:
        if len(args.paths) != 1:
            ap.error("--ref-as-hyp takes exactly one path: OUT.jsonl")
        (out,) = args.paths
        hyps = {it["id"]: it["reference"] for it in items}
    else:
        if len(args.paths) != 2:
            ap.error("expected two paths: PRED.jsonl OUT.jsonl")
        pred, out = args.paths
        hyps = {}
        with open(pred, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    hyps[row[args.id_field]] = row.get(args.text_field) or ""

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps({
                "id": it["id"],
                "lang_pair": it["input"]["lang_pair"],
                "domain": it["input"]["domain"],
                "source": clean(it["input"]["source"]),
                "hypothesis": clean(hyps.get(it["id"], "")),
                "reference": clean(it["reference"]),
            }, ensure_ascii=False) + "\n")
    print(f"wrote {len(items)} rows -> {out}")


if __name__ == "__main__":
    main()
