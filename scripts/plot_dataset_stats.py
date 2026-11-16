from __future__ import annotations
import argparse
import json
import sys
import matplotlib
import matplotlib.pyplot as plt
from collections import Counter
from pathlib import Path
from matplotlib.patches import Patch

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]

CATEGORY_ORDER = ["writing", "info", "summarization", "translation", "chat", "agents"]

CATEGORY_COLORS = {
    "writing": "#2a78d6",
    "info": "#eb6834",
    "summarization": "#1baf7a",
    "translation": "#eda100",
    "chat": "#e87ba4",
    "agents": "#008300",
}

SINGLE_SERIES_COLOR = "#2a78d6"
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", type=Path, default=ROOT / "data" / "benchmark.jsonl")
    p.add_argument("-o", "--out-dir", type=Path, default=ROOT / "reports" / "figures")
    p.add_argument("--format", choices=["png", "svg", "pdf"], default="png")
    p.add_argument("--dpi", type=int, default=150)
    return p.parse_args()

def load_counts(path: Path) -> tuple[Counter[str], Counter[tuple[str, str]]]:
    per_category: Counter[str] = Counter()
    per_source: Counter[tuple[str, str]] = Counter()  # (category, source)
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            per_category[rec["category"]] += 1
            per_source[(rec["category"], rec["source"])] += 1
    return per_category, per_source

def style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", " ")))

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def label_bars(ax: plt.Axes, bars, values: list[int]) -> None:
    xmax = max(values)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_width() + xmax * 0.01,
            bar.get_y() + bar.get_height() / 2,
            fmt(v),
            va="center",
            ha="left",
            fontsize=9,
            color=TEXT_PRIMARY,
        )
    ax.set_xlim(0, xmax * 1.12)  # room for the value labels

def plot_categories(per_category: Counter[str], out: Path, dpi: int) -> None:
    cats = [c for c in CATEGORY_ORDER if per_category[c]] + sorted(
        c for c in per_category if c not in CATEGORY_ORDER
    )
    values = [per_category[c] for c in cats]
    total = sum(values)

    fig, ax = plt.subplots(figsize=(8, 0.55 * len(cats) + 1.6), facecolor=SURFACE)
    style_axes(ax)
    bars = ax.barh(cats, values, color=SINGLE_SERIES_COLOR, height=0.6)
    ax.invert_yaxis()
    label_bars(ax, bars, values)
    ax.tick_params(axis="y", colors=TEXT_PRIMARY, labelsize=10)
    ax.set_xlabel("prompts", color=TEXT_SECONDARY)
    ax.set_title(
        f"Prompts per task category (total: {fmt(total)})",
        loc="left",
        color=TEXT_PRIMARY,
        fontsize=12,
        pad=12,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)

def plot_sources(per_source: Counter[tuple[str, str]], out: Path, dpi: int) -> None:
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    keys = sorted(per_source, key=lambda k: (order.get(k[0], len(order)), -per_source[k]))
    labels = [src for _, src in keys]
    values = [per_source[k] for k in keys]
    colors = [CATEGORY_COLORS.get(cat, "#8a8984") for cat, _ in keys]

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(keys) + 2.0), facecolor=SURFACE)
    style_axes(ax)
    bars = ax.barh(labels, values, color=colors, height=0.6)
    ax.invert_yaxis()
    label_bars(ax, bars, values)
    ax.tick_params(axis="y", colors=TEXT_PRIMARY, labelsize=10)
    ax.set_xlabel("prompts", color=TEXT_SECONDARY)
    ax.set_title(
        f"Prompts per source, grouped by task category (total: {fmt(sum(values))})",
        loc="left",
        color=TEXT_PRIMARY,
        fontsize=12,
        pad=12,
    )
    present = list(dict.fromkeys(cat for cat, _ in keys))
    handles = [Patch(color=CATEGORY_COLORS.get(c, "#8a8984"), label=c) for c in present]
    legend = ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9)
    for text in legend.get_texts():
        text.set_color(TEXT_PRIMARY)
    fig.tight_layout()
    fig.savefig(out, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)

def main() -> int:
    args = parse_args()
    if not args.input.exists():
        print(f"[ERROR] missing input file {args.input}; run merge_unified.py first", file=sys.stderr)
        return 1
    per_category, per_source = load_counts(args.input)
    if not per_category:
        print(f"[ERROR] no records in {args.input}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "prompts_per_category": lambda p: plot_categories(per_category, p, args.dpi),
        "prompts_per_source": lambda p: plot_sources(per_source, p, args.dpi),
    }
    for name, plot in outputs.items():
        path = args.out_dir / f"{name}.{args.format}"
        plot(path)
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)

    print(f"\nTotal prompts: {fmt(sum(per_category.values()))}")
    for cat in sorted(per_category, key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99):
        print(f"  {cat:<15} {per_category[cat]:>7}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
