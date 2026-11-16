"""Seeded stratified sampling for evaluation splits."""
from __future__ import annotations
import random
from collections.abc import Callable, Hashable, Sequence

def allocate(sizes: dict[str, int], total: int, minimum: int = 0) -> dict[str, int]:
    """Split `total` over strata proportionally to their sizes (largest-remainder rounding).

    Every stratum first gets `min(minimum, size)`; the rest is allocated proportionally to the
    remaining capacity. Remainder ties go to the larger stratum, then to the smaller name.
    """
    if total > sum(sizes.values()):
        raise ValueError(f"cannot pick {total} of {sum(sizes.values())} units")
    base = {k: min(minimum, n) for k, n in sizes.items()}
    rest = total - sum(base.values())
    if rest < 0:
        raise ValueError(f"per-stratum minimum {minimum} needs more than {total} units")
    capacity = {k: sizes[k] - base[k] for k in sizes}
    cap_total = sum(capacity.values())
    quotas = {k: rest * c / cap_total if cap_total else 0.0 for k, c in capacity.items()}
    alloc = {k: int(q) for k, q in quotas.items()}
    order = sorted(sizes, key=lambda k: (-(quotas[k] - alloc[k]), -sizes[k], k))
    for k in order[: rest - sum(alloc.values())]:
        alloc[k] += 1
    return {k: base[k] + alloc[k] for k in sizes}

def stratified_sample(
    units: Sequence[Hashable],
    stratum: Callable[[Hashable], str],
    n: int,
    seed: int,
    minimum: int = 0,
) -> list[Hashable]:
    """Pick `n` units, stratified by `stratum(unit)`.

    Units keep their input order inside a stratum; strata are visited in sorted order and each
    draws `random.Random(seed).sample(members, k)` from one shared generator, so the result is
    fully determined by (input order, seed).
    """
    groups: dict[str, list[Hashable]] = {}
    for u in units:
        groups.setdefault(stratum(u), []).append(u)
    alloc = allocate({k: len(v) for k, v in groups.items()}, n, minimum)
    rng = random.Random(seed)
    chosen: list[Hashable] = []
    for k in sorted(groups):
        chosen.extend(rng.sample(groups[k], alloc[k]))
    return chosen
