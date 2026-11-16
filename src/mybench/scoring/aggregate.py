from __future__ import annotations
# Cross-model summary of normalised score files (runs/scores/<model>/<source>.json). Stdlib only, no LLM calls.
#
# (a) headline per model x source with a 95% CI over items: Wilson interval when the headline is a mean of binary
#     (0/1) item scores, otherwise a percentile bootstrap (B_RESAMPLES resamples, fixed seed) of the same statistic
#     as the headline (mean, F1 of mean P/R, pooled ratio);
# (b) per source: best and worst model, spread between them, optional anchor checks (weak anchor lowest, strong
#     anchor highest) and saturation (0-1 metrics: all models >= 0.9 or all <= 0.1);
# (c) item discrimination on 0-1 metrics: pass = score >= threshold; items scored for >= 2 models on which all
#     models agree (all pass / all fail) are drop candidates. Continuous ("raw") metrics are n/a.
import csv
import json
import math
import random
from pathlib import Path
from typing import Any

B_RESAMPLES = 2000
SEED = 20261116
DEFAULT_PASS = 0.5

def load_scores(scores_dir: Path, models: list[str] | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for p in sorted(scores_dir.glob("*/*.json")):
        if p.parent.name.startswith("_"):
            continue
        s = json.loads(p.read_text(encoding="utf-8"))
        if models is None or s["model"] in models:
            out[(s["model"], s["source"])] = s
    return out

def stat(kind: str, items: list[dict[str, Any]]) -> float | None:
    if not items:
        return None
    if kind == "ratio":
        den = sum(x["den"] for x in items)
        return sum(x["num"] for x in items) / den if den else None
    if kind == "f1_pr":
        p = sum(x["p"] for x in items) / len(items)
        r = sum(x["r"] for x in items) / len(items)
        return 2 * p * r / (p + r) if p + r else 0.0
    return sum(x["score"] for x in items) / len(items)

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)

def bootstrap(kind: str, items: list[dict[str, Any]], seed: int = SEED) -> tuple[float | None, float | None]:
    if len(items) < 2:
        return None, None
    rng = random.Random(seed)
    res = sorted(v for v in (stat(kind, [rng.choice(items) for _ in items]) for _ in range(B_RESAMPLES)) if v is not None)
    return res[int(0.025 * len(res))], res[min(len(res) - 1, int(0.975 * len(res)))]

def ci(s: dict[str, Any]) -> tuple[float | None, float | None, str]:
    items = [x for x in s["items"].values() if x.get("score") is not None]
    if s["stat"] == "mean" and items and all(x["score"] in (0, 1) for x in items):
        return (*wilson(sum(int(x["score"]) for x in items), len(items)), "wilson")
    return (*bootstrap(s["stat"], items), "bootstrap")

def fmt(x: float | None, nd: int = 3) -> str:
    return "—" if x is None else f"{x:.{nd}f}"

def discrimination(
    scores: dict[tuple[str, str], dict[str, Any]], source: str, threshold: float
) -> tuple[list[str], list[str], dict[str, dict[str, bool]]]:
    """(all-pass ids, all-fail ids, {id: {model: passed}} for items scored for >= 2 models)."""
    per_item: dict[str, dict[str, bool]] = {}
    for (m, src), s in scores.items():
        if src == source:
            for iid, v in s["items"].items():
                if v.get("score") is not None:
                    per_item.setdefault(iid, {})[m] = v["score"] >= threshold
    multi = {i: v for i, v in per_item.items() if len(v) >= 2}
    all_pass = sorted(i for i, v in multi.items() if all(v.values()))
    all_fail = sorted(i for i, v in multi.items() if not any(v.values()))
    return all_pass, all_fail, multi

def report(
    scores: dict[tuple[str, str], dict[str, Any]],
    out_dir: Path,
    *,
    pass_thresholds: dict[str, float] | None = None,
    weak_anchor: str | None = None,
    strong_anchor: str | None = None,
) -> Path:
    """Writes summary.md, summary.csv and drop_candidates.json to `out_dir`; returns the summary.md path."""
    pass_thresholds = pass_thresholds or {}
    out_dir.mkdir(parents=True, exist_ok=True)
    models = sorted({m for m, _ in scores})
    sources = sorted({s for _, s in scores})
    first = {src: next(s for (_, k), s in scores.items() if k == src) for src in sources}
    md = ["# Benchmark summary", "",
          f"Models: {', '.join(models) or 'none'}. Cells: headline [95% CI] (n items / n expected, errors). "
          "`*` = partial (not all expected items scored). `—` = no score. ↓ = lower is better.", ""]

    # (a) headline table
    rows_csv, cells = [], {}
    for (m, src), s in sorted(scores.items()):
        lo, hi, method = ci(s)
        cells[(m, src)] = (lo, hi)
        rows_csv.append({"model": m, "source": src, "headline": s["headline"], "ci_lo": lo, "ci_hi": hi,
                         "ci_method": method, "n_items": s["n_items"], "n_expected": s["n_expected"],
                         "n_errors": s["n_errors"], "complete": s["complete"],
                         "higher_is_better": s["higher_is_better"], "metric": s["metric"]})
    md += ["## (a) Headline scores", "",
           "| model | " + " | ".join(src + ("" if first[src]["higher_is_better"] else " ↓") for src in sources) + " |",
           "|---|" + "---|" * len(sources)]
    for m in models:
        row = [m]
        for src in sources:
            s = scores.get((m, src))
            if not s:
                row.append("—")
                continue
            lo, hi = cells[(m, src)]
            interval = f" [{fmt(lo)}, {fmt(hi)}]" if lo is not None else ""
            row.append(f"{fmt(s['headline'])}{interval} ({s['n_items']}/{s['n_expected']}, e{s['n_errors']})"
                       f"{'' if s['complete'] else ' *'}")
        md.append("| " + " | ".join(row) + " |")
    md += ["", "Metrics: " + "; ".join(f"**{src}** = {first[src]['metric']}" for src in sources), ""]
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0]) if rows_csv else ["model"])
        w.writeheader()
        w.writerows(rows_csv)

    # (b) spread between models
    md += ["## (b) Spread between models", "",
           "| source | models | best | worst | spread | weak anchor lowest? | strong anchor highest? | saturated? |",
           "|---|---|---|---|---|---|---|---|"]
    for src in sources:
        hib, scale = first[src]["higher_is_better"], first[src]["scale"]
        have = {m: s["headline"] for (m, k), s in scores.items() if k == src and s["headline"] is not None}

        def key(m: str) -> float:
            return have[m] if hib else -have[m]

        def anchor(a: str | None, lowest: bool) -> str:
            if not a or a not in have:
                return "n/a"
            others = [m for m in have if m != a]
            if not others:
                return "no comparison"
            ok = all(key(a) < key(o) for o in others) if lowest else all(key(a) > key(o) for o in others)
            return ("yes" if ok else "NO") + f" ({fmt(have[a])})"

        if have:
            best, worst = max(have, key=key), min(have, key=key)
            best_s, worst_s = f"{best} {fmt(have[best])}", f"{worst} {fmt(have[worst])}"
            spread = abs(have[best] - have[worst])
        else:
            best_s = worst_s = "—"
            spread = None
        sat = "n/a (raw scale)"
        if scale == "0-1" and have:
            vals = list(have.values())
            sat = "YES (all ≥ 0.9)" if min(vals) >= 0.9 else "YES (all ≤ 0.1)" if max(vals) <= 0.1 else "no"
        md.append(f"| {src} | {len(have)} | {best_s} | {worst_s} | {fmt(spread)} | {anchor(weak_anchor, True)} | "
                  f"{anchor(strong_anchor, False)} | {sat} |")
    md.append("")

    # (c) item discrimination
    md += ["## (c) Items with the same outcome across models (drop candidates)", "",
           "Only items scored for ≥ 2 models count. Pass = item score ≥ threshold.", "",
           "| source | threshold | items (≥ 2 models) | all pass | all fail | % same outcome |",
           "|---|---|---|---|---|---|"]
    drop: dict[str, dict[str, list[str]]] = {}
    for src in sources:
        if first[src]["scale"] != "0-1":
            md.append(f"| {src} | n/a (continuous metric) | | | | |")
            continue
        t = pass_thresholds.get(src, DEFAULT_PASS)
        all_pass, all_fail, multi = discrimination(scores, src, t)
        drop[src] = {"all_pass": all_pass, "all_fail": all_fail}
        pct = fmt(100 * (len(all_pass) + len(all_fail)) / len(multi), 0) + "%" if multi else "—"
        md.append(f"| {src} | {t} | {len(multi)} | {len(all_pass)} | {len(all_fail)} | {pct} |")
    md.append("")
    (out_dir / "drop_candidates.json").write_text(json.dumps(drop, indent=1, ensure_ascii=False), encoding="utf-8")
    path = out_dir / "summary.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    return path
