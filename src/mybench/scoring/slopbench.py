from __future__ import annotations
# SlopBench (Slop Index, mechanical layer) via the official `harness/score.py` of a local clone of
# https://github.com/hgaddipati1118/slop-index (`slopbench_dir`). Stdlib only, no judge.
#
# The run outputs are converted to the harness format (`<work_dir>/slopbench_harness/outputs.jsonl`), the official
# score.py main() is run on them (its printed board is saved to `<work_dir>/slopbench.score.log`) and the same numbers
# are returned as JSON using the official score_model()/composite():
#   headline = mean of domain composites; axes = mean over domains (as score.py prints them);
#   per item = score_model() on one scenario's samples (rhythm and tells are ratio-of-means axes, so items do not
#   average to the domain score). Lower = closer to human writing.
#
# Record fields used: scenario id = source_id; domain = subcategory (else meta.domain);
# length target [lo, hi] = reference.length_target_words.
# The harness reads files with the platform encoding: run Python in UTF-8 mode (`python -X utf8`).
import contextlib
import io
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from mybench.schema import Record
from mybench.scoring.common import load_outputs, pick, strip_think, summary

def domain(rec: Record) -> str:
    return pick(rec, "subcategory", "meta.domain")

def score(
    records: list[Record], outputs_path: Path, *, model: str, slopbench_dir: Path, work_dir: Path
) -> dict[str, Any]:
    sys.path.insert(0, str(slopbench_dir / "harness"))
    import score as S

    items = {r.id: r for r in records}
    raw = load_outputs(outputs_path, set(items))
    harness_rows, errors, empty = [], [], []
    for (iid, s), r in sorted(raw.items()):
        rec = items[iid]
        row = {"scenario_id": rec.source_id, "domain": domain(rec), "model": model, "sample": s,
               "text": "" if "error" in r else strip_think(r.get("output")),
               "length_target": pick(rec, "reference.length_target_words")}
        if "error" in r:
            row["error"] = r["error"]
            errors.append({"id": iid, "sample": s, "error": r["error"]})
        elif not row["text"]:
            empty.append({"id": iid, "sample": s})
        harness_rows.append(row)

    hdir = work_dir / "slopbench_harness"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "outputs.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in harness_rows), encoding="utf-8", newline="\n"
    )

    # 1. official CLI, pointed at our work dir
    S.RUNS = work_dir
    buf, argv = io.StringIO(), sys.argv
    sys.argv = ["score.py", "--run-id", hdir.name]
    try:
        with contextlib.redirect_stdout(buf):
            S.main()
    finally:
        sys.argv = argv
    (work_dir / "slopbench.score.log").write_text(buf.getvalue(), encoding="utf-8")
    print(buf.getvalue())

    # 2. same numbers as JSON (same filter as score.main)
    rows = [r for r in harness_rows if r.get("text") and not r.get("error")]
    domains = sorted({r["domain"] for r in rows})
    baselines = {d: S._load_baseline(d) for d in domains}
    by_domain = {}
    for d in domains:
        axes = S.score_model([r for r in rows if r["domain"] == d], baselines[d])
        by_domain[d] = {"composite": S.composite(axes), "axes": axes, "n_outputs": sum(r["domain"] == d for r in rows)}
    comps = [v["composite"] for v in by_domain.values() if v["composite"] is not None]
    axes_overall = {}
    for ax in S.WEIGHTS:
        vals = [v["axes"][ax] for v in by_domain.values() if v["axes"].get(ax) is not None]
        axes_overall[ax] = st.mean(vals) if vals else None

    by_scen: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_scen[r["scenario_id"]].append(r)
    per_item = {}
    for iid, rec in items.items():
        rs = by_scen.get(rec.source_id)
        if rs:
            axes = S.score_model(rs, baselines[domain(rec)])
            per_item[iid] = {"score": S.composite(axes), "domain": domain(rec), "n_samples": len(rs), "axes": axes}

    failed = {e["id"] for e in errors + empty}
    return summary(
        "slopbench", model,
        headline=st.mean(comps) if comps else None,
        metric="Slop Index mechanical layer, mean of domain composites (lower = better)",
        higher_is_better=False, scale="raw", stat="mean", items=per_item, n_expected=len(items),
        n_errors=len(errors) + len(empty), n_covered=len(per_item) + len(failed - set(per_item)),
        extra={"weights": S.WEIGHTS, "axes": axes_overall, "by_domain": by_domain,
               "samples_per_scenario": sorted({len(v) for v in by_scen.values()}), "errors": errors, "empty": empty},
    )
