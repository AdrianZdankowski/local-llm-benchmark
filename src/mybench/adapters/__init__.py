from __future__ import annotations
from collections.abc import Callable, Iterator
from pathlib import Path
from mybench.adapters import (
    facts_grounding,
    ifbench,
    marco_mif,
    noveltybench,
    supergpqa,
    wmt26,
)
from mybench.adapters.common import Skips
from mybench.schema import Record

AdapterFn = Callable[[Path, Skips], Iterator[Record]]

ADAPTERS: dict[str, AdapterFn] = {
    "ifbench": ifbench.load,
    "marco_mif": marco_mif.load,
    "supergpqa": supergpqa.load,
    "noveltybench": noveltybench.load,
    "wmt26": wmt26.load,
    "facts_grounding": facts_grounding.load,
}

__all__ = ["ADAPTERS", "AdapterFn", "Skips"]