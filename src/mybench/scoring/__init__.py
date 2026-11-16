from __future__ import annotations

# Scorer modules (listqa, slopbench, ideafix, metricx) import their heavy dependencies lazily;
# import them directly, e.g. `from mybench.scoring import listqa`.
SCORERS = ("listqa", "slopbench", "ideafix", "metricx")
# Default scorer per source.
DEFAULT_SCORER = {"listqa": "listqa", "slopbench": "slopbench", "ideafix": "ideafix", "wmt26": "metricx", "wmt26_humanref": "metricx"}

__all__ = ["DEFAULT_SCORER", "SCORERS"]
