import math

from wre.effects import (
    cluster_bootstrap,
    d_from_counts,
    d_from_proportions,
    d_from_samples,
    d_from_summary,
    econ_index,
    effect_d,
    proportion_gap,
    within_item_rank_z,
    within_item_z,
)


def test_binary_d_matches_known_framing_numbers():
    # Original Asian-disease proportions 72% vs 22% (n ~ 150 each): d should be about 1.1-1.3.
    d = d_from_counts(108, 150, 33, 150)
    assert 1.1 < d < 1.35


def test_binary_d_zero_when_equal_and_sign():
    assert abs(d_from_counts(20, 40, 20, 40)) < 1e-9
    assert d_from_counts(30, 40, 10, 40) > 0 > d_from_counts(10, 40, 30, 40)


def test_binary_d_finite_at_extremes():
    assert math.isfinite(d_from_counts(40, 40, 0, 40))


def test_continuous_d():
    assert abs(d_from_samples([2, 3, 4], [1, 2, 3]) - 1.0) < 1e-9
    assert d_from_samples([1, 1, 1], [1, 1, 1]) == 0.0


def test_effect_d_and_gap_direction():
    rows = [("a", "hi", 1.0)] * 8 + [("a", "hi", 0.0)] * 2 + [("a", "lo", 1.0)] * 3 + [("a", "lo", 0.0)] * 7
    assert effect_d(rows, "binary") > 0
    assert abs(proportion_gap(rows) - 0.5) < 1e-9


def test_cluster_bootstrap_contains_point_and_is_deterministic():
    rows = []
    for i in range(10):
        rows += [(f"i{i}", "hi", 1.0 if (i + j) % 4 else 0.0) for j in range(4)]
        rows += [(f"i{i}", "lo", 1.0 if (i + j) % 2 else 0.0) for j in range(4)]
    lo, hi = cluster_bootstrap(rows, "binary", n_boot=300, seed=1)
    point = effect_d(rows, "binary")
    assert lo <= point <= hi
    assert (lo, hi) == cluster_bootstrap(rows, "binary", n_boot=300, seed=1)


def test_bootstrap_single_item_falls_back_to_answers():
    rows = [("c", "hi", 1.0)] * 18 + [("c", "hi", 0.0)] * 2 + [("c", "lo", 1.0)] * 5 + [("c", "lo", 0.0)] * 15
    lo, hi = cluster_bootstrap(rows, "binary", n_boot=300, seed=2)
    assert 0 < lo < hi


def test_within_item_z_pools_different_scales():
    rows = [("big", "hi", 1000.0), ("big", "lo", 100.0), ("big", "hi", 900.0), ("big", "lo", 200.0),
            ("small", "hi", 10.0), ("small", "lo", 1.0), ("small", "hi", 9.0), ("small", "lo", 2.0)]
    z = within_item_z(rows)
    assert effect_d(z, "continuous") > 1.5
    assert within_item_z([("x", "hi", 5.0), ("x", "lo", 5.0)]) == []


def test_econ_index():
    assert econ_index(0.3, 0.6) == 0.5
    assert math.isnan(econ_index(0.3, 0.0))


def test_d_from_proportions_and_summary():
    assert abs(d_from_proportions(0.5, 0.5)) < 1e-12
    assert d_from_proportions(0.7, 0.3) > 0 > d_from_proportions(0.3, 0.7)
    assert abs(d_from_summary(7.85, 2.02, 7.24, 2.42) - 0.274) < 0.01


def test_rank_z_handles_ties_and_drops_constant_items():
    rows = [("a", "hi", 5.0), ("a", "hi", 5.0), ("a", "lo", 1.0), ("a", "lo", 2.0),
            ("const", "hi", 3.0), ("const", "lo", 3.0)]
    z = within_item_rank_z(rows, keep_constant=False)
    assert {r[0] for r in z} == {"a"}
    assert effect_d(z, "continuous") > 1.0
    kept = within_item_rank_z(rows)
    assert {r[0] for r in kept} == {"a", "const"}
    assert all(v == 0.0 for k, _, v in kept if k == "const")
    # a null item must shrink the pooled effect, not be ignored
    assert effect_d(kept, "continuous") < effect_d(z, "continuous")
