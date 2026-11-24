"""Small statistics helpers for the EpiReason analysis, in plain Python.

Uncertainty follows Miller (2024): the scenario is the unit.
A cluster bootstrap resamples whole scenarios with replacement, keeping every response of a
drawn scenario (all its samples, and both versions or hint levels where a statistic pairs them).

A percentile bootstrap gives a zero-width interval when every response agrees (100% or 0%),
which says nothing about uncertainty. In that case the interval is replaced by an exact
Clopper-Pearson interval that treats each scenario as one trial: for k of k it is
[(alpha/2)^(1/k), 1]. With 9 scenarios that is [66%, 100%]. This is conservative, since the
3 samples per scenario add some information, and it is stated wherever it is used.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Hashable, Sequence

ALPHA = 0.05
N_BOOT = 4000
SEED = 20261123


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def quantile(sorted_xs: Sequence[float], q: float) -> float:
    """Linear interpolation between order statistics (type 7, the R and numpy default)."""
    if not sorted_xs:
        return float("nan")
    pos = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


def cluster_bootstrap(clusters: dict[Hashable, object], stat: Callable[[list[object]], float],
                      n_boot: int = N_BOOT, seed: int = SEED, alpha: float = ALPHA) -> tuple[float, float, float]:
    """Point estimate and percentile interval of stat over clusters resampled with replacement.

    clusters maps a cluster id (a scenario) to whatever stat needs for that cluster; stat takes a
    list of those values (with repeats when a cluster is drawn twice) and returns a number.
    Draws where stat is undefined (nan) are dropped.
    """
    keys = sorted(clusters, key=str)
    values = [clusters[k] for k in keys]
    est = stat(values)
    rng = random.Random(seed)
    draws = []
    for _ in range(n_boot):
        d = stat([values[rng.randrange(len(values))] for _ in values])
        if d == d:
            draws.append(d)
    draws.sort()
    return est, quantile(draws, alpha / 2), quantile(draws, 1 - alpha / 2)


def clopper_pearson(k: int, n: int, alpha: float = ALPHA) -> tuple[float, float]:
    """Exact binomial interval, only for the two boundary cases used here (k = 0 or k = n)."""
    if n <= 0:
        return float("nan"), float("nan")
    if k == n:
        return (alpha / 2) ** (1 / n), 1.0
    if k == 0:
        return 0.0, 1 - (alpha / 2) ** (1 / n)
    raise ValueError("clopper_pearson here handles only k = 0 or k = n")


def rate_by_cluster(flags_by_cluster: dict[Hashable, list[bool]], **kw) -> dict:
    """A rate with its scenario-clustered interval.

    Returns est, lo, hi, k (count met), n (responses), clusters and method
    ('bootstrap', or 'exact' when every response agrees).
    """
    flags_by_cluster = {c: [bool(f) for f in fs if f is not None] for c, fs in flags_by_cluster.items()}
    flags_by_cluster = {c: fs for c, fs in flags_by_cluster.items() if fs}
    allf = [f for fs in flags_by_cluster.values() for f in fs]
    k, n, m = sum(allf), len(allf), len(flags_by_cluster)
    if n == 0:
        return {"est": float("nan"), "lo": float("nan"), "hi": float("nan"), "k": 0, "n": 0, "clusters": 0, "method": "none"}
    if k in (0, n):
        lo, hi = clopper_pearson(m if k == n else 0, m, kw.get("alpha", ALPHA))
        return {"est": k / n, "lo": lo, "hi": hi, "k": k, "n": n, "clusters": m, "method": "exact"}

    def stat(vals: list[list[bool]]) -> float:
        flat = [f for fs in vals for f in fs]
        return sum(flat) / len(flat)

    est, lo, hi = cluster_bootstrap(flags_by_cluster, stat, **kw)
    return {"est": est, "lo": lo, "hi": hi, "k": k, "n": n, "clusters": m, "method": "bootstrap"}


def mean_by_cluster(values_by_cluster: dict[Hashable, list[float]], **kw) -> dict:
    """A mean (such as the normalised score) with its scenario-clustered bootstrap interval."""
    values_by_cluster = {c: vs for c, vs in values_by_cluster.items() if vs}
    n = sum(len(v) for v in values_by_cluster.values())

    def stat(vals: list[list[float]]) -> float:
        flat = [x for vs in vals for x in vs]
        return mean(flat)

    est, lo, hi = cluster_bootstrap(values_by_cluster, stat, **kw)
    return {"est": est, "lo": lo, "hi": hi, "n": n, "clusters": len(values_by_cluster), "method": "bootstrap"}


def paired_difference(pairs_by_cluster: dict[Hashable, tuple[list[float], list[float]]], **kw) -> dict:
    """Mean of the second list minus mean of the first, resampling clusters with both lists together.

    Used for the hint effect (direct minus neutral), where the same scenarios appear at both
    levels. A difference whose two arms are identical in every scenario has a zero-width interval;
    that is reported as it is, with method 'degenerate'.
    """
    pairs_by_cluster = {c: p for c, p in pairs_by_cluster.items() if p[0] and p[1]}

    def stat(vals: list[tuple[list[float], list[float]]]) -> float:
        a = [x for p in vals for x in p[0]]
        b = [x for p in vals for x in p[1]]
        return mean(b) - mean(a)

    est, lo, hi = cluster_bootstrap(pairs_by_cluster, stat, **kw)
    return {"est": est, "lo": lo, "hi": hi, "clusters": len(pairs_by_cluster),
            "method": "degenerate" if lo == hi else "bootstrap"}


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Cohen's kappa for two binary raters. nan when chance agreement is 1 (both raters constant and equal)."""
    n = len(a)
    if n == 0 or n != len(b):
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)
