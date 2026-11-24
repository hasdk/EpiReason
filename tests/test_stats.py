import math

import pytest

from analysis.stats import (clopper_pearson, cluster_bootstrap, cohen_kappa, mean_by_cluster, paired_difference,
                            quantile, rate_by_cluster)


def test_quantile_matches_type_7():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert quantile(xs, 0.0) == 1.0
    assert quantile(xs, 1.0) == 4.0
    assert quantile(xs, 0.5) == pytest.approx(2.5)
    assert quantile(xs, 0.25) == pytest.approx(1.75)


def test_clopper_pearson_boundaries():
    lo, hi = clopper_pearson(9, 9)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** (1 / 9))
    assert lo == pytest.approx(0.664, abs=0.001)
    lo, hi = clopper_pearson(0, 9)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 9))
    with pytest.raises(ValueError):
        clopper_pearson(3, 9)


def test_rate_all_met_uses_exact_interval_on_scenarios():
    r = rate_by_cluster({f"S{i}": [True, True, True] for i in range(9)})
    assert r["est"] == 1.0 and r["method"] == "exact"
    assert (r["k"], r["n"], r["clusters"]) == (27, 27, 9)
    assert r["lo"] == pytest.approx(0.664, abs=0.001) and r["hi"] == 1.0


def test_rate_mixed_uses_bootstrap_and_covers_estimate():
    flags = {f"S{i}": [i % 3 == 0, True, False] for i in range(9)}
    r = rate_by_cluster(flags)
    assert r["method"] == "bootstrap"
    assert r["lo"] <= r["est"] <= r["hi"]
    assert r["est"] == pytest.approx(12 / 27)


def test_rate_ignores_missing_flags():
    r = rate_by_cluster({"S1": [True, None], "S2": [None]})
    assert (r["k"], r["n"], r["clusters"]) == (1, 1, 1)


def test_cluster_bootstrap_is_reproducible():
    clusters = {i: [float(i)] for i in range(10)}
    stat = lambda vals: sum(v[0] for v in vals) / len(vals)
    assert cluster_bootstrap(clusters, stat) == cluster_bootstrap(clusters, stat)


def test_cluster_bootstrap_resamples_whole_clusters():
    # One cluster holds all the successes: the interval must be wide, not the tight
    # interval that resampling single responses would give.
    flags = {"S1": [True] * 10, **{f"S{i}": [False] * 10 for i in range(2, 11)}}
    r = rate_by_cluster(flags)
    assert r["est"] == pytest.approx(0.1)
    assert r["lo"] == 0.0 and r["hi"] >= 0.25


def test_mean_by_cluster():
    r = mean_by_cluster({"S1": [0.0, 1.0], "S2": [1.0, 1.0]})
    assert r["est"] == pytest.approx(0.75) and r["n"] == 4


def test_paired_difference_sign_and_degenerate():
    d = paired_difference({f"S{i}": ([0.0, 0.0], [1.0, 1.0]) for i in range(5)})
    assert d["est"] == 1.0 and d["method"] == "degenerate"
    d = paired_difference({f"S{i}": ([0.0], [float(i % 2)]) for i in range(6)})
    assert d["est"] == pytest.approx(0.5) and d["lo"] < 0.5 < d["hi"]


def test_cohen_kappa():
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert cohen_kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert math.isnan(cohen_kappa([True, True], [True, True]))
