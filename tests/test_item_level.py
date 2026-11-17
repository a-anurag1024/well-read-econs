import math
from pathlib import Path

import pytest

from wre.item_level import (
    HUMAN_GAP,
    HUMAN_SWING,
    boot_interval,
    framing,
    includes,
    layout_label,
    scenario_diffs,
    summarize_diffs,
    sunk_cost,
    t_crit,
)
from wre.part2 import load

DATA = Path(__file__).resolve().parents[1] / "data"


def _rec(key: str, condition: str, parsed: float, sure_first: bool = True, fmt: str = "ab") -> dict:
    return {
        "item_key": key,
        "condition": condition,
        "parsed": parsed,
        "err": None,
        "meta": {"sure_first": sure_first, "fmt": fmt},
    }


def test_t_crit_table_and_fallback():
    assert t_crit(11) == pytest.approx(2.201)
    assert t_crit(1) == pytest.approx(12.706)
    assert t_crit(11.9) == t_crit(11)  # non-integer df round down
    assert t_crit(40) == pytest.approx(1.96)
    assert math.isnan(t_crit(0.5))


def test_summarize_diffs_matches_hand_calculation():
    s = summarize_diffs([1.0, 2.0, 3.0, 4.0])
    assert s["mean"] == pytest.approx(2.5)
    assert s["sd"] == pytest.approx(1.2909944)
    half = 3.182 * 1.2909944 / 2
    assert s["t_ci"] == pytest.approx((2.5 - half, 2.5 + half))
    assert (s["up"], s["down"], s["k"]) == (4, 0, 4)


def test_zero_spread_gives_a_single_point_interval():
    s = summarize_diffs([0.0] * 12)
    assert s["t_ci"] == (0.0, 0.0) and s["boot_ci"] == (0.0, 0.0)
    assert includes(s["t_ci"], 0.0) and not includes(s["t_ci"], HUMAN_SWING)


def test_one_scenario_has_no_interval():
    s = summarize_diffs([5.0])
    assert math.isnan(s["sd"]) and math.isnan(s["t_ci"][0])
    assert math.isnan(boot_interval([5.0])[0])


def test_bootstrap_is_reproducible_and_brackets_the_mean():
    diffs = [1.0, 3.0, 2.0, 5.0, 4.0, 2.5]
    assert boot_interval(diffs, seed=1) == boot_interval(diffs, seed=1)
    lo, hi = boot_interval(diffs, seed=1)
    assert lo <= sum(diffs) / len(diffs) <= hi


def test_scenario_diffs_use_only_scored_scenarios_in_both_conditions():
    recs = [
        _rec("a", "hi", 1.0),
        _rec("a", "hi", 0.0),
        _rec("a", "lo", 0.0),
        _rec("b", "hi", 1.0),  # no lo answer: dropped
        {**_rec("c", "hi", 1.0), "parsed": None},
        _rec("c", "lo", 0.0),
    ]
    assert scenario_diffs(recs, 100) == {"a": 50.0}


def _layout_recs(layout: float, label: float, noise: dict[int, float]) -> list[dict]:
    """Scenarios 0..7. Even scenarios: letters first, numbers second. Odd: the reverse.

    swing(layout, label) = 10 + layout * [sure second] + label * [numbers]; noise only in the second layout.
    """
    recs = []
    for s in range(8):
        for first, fmt in (
            (True, "ab" if s % 2 == 0 else "n"),
            (False, "n" if s % 2 == 0 else "ab"),
        ):
            swing = 10 + (0 if first else layout) + (label if fmt == "n" else 0)
            if not first:
                swing += noise[s]
            recs.append(_rec(f"s{s}", "hi", 0.5 + swing / 200, first, fmt))
            recs.append(_rec(f"s{s}", "lo", 0.5 - swing / 200, first, fmt))
    return recs


def test_layout_and_label_effects_are_separated():
    noise = {0: 2.0, 2: -2.0, 4: 2.0, 6: -2.0, 1: 3.0, 3: -3.0, 5: 3.0, 7: -3.0}
    out = layout_label(_layout_recs(layout=40.0, label=10.0, noise=noise))
    assert out["layout"]["est"] == pytest.approx(40.0)
    assert out["label"]["est"] == pytest.approx(10.0)
    lo, hi = out["layout"]["ci"]
    assert lo < 40.0 < hi
    assert (out["n_a"], out["n_b"]) == (4, 4)


def test_released_framing_matches_the_headline_numbers():
    out = framing(
        load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    )
    assert len(out) == 16
    sonnet = out["claude-sonnet-5.5"]
    assert sonnet["pooled"]["mean"] == pytest.approx(48.6, abs=0.2)
    assert sonnet["pooled"]["k"] == 12 and (sonnet["pooled"]["up"], sonnet["pooled"]["down"]) == (
        12,
        0,
    )
    assert not includes(sonnet["pooled"]["t_ci"], HUMAN_SWING)
    assert sonnet["layout"]["ci"][0] > 0  # the swing depends on where the sure plan is listed
    assert sonnet["first"]["mean"] == pytest.approx(8.3, abs=0.2)
    assert sonnet["second"]["mean"] == pytest.approx(88.9, abs=0.2)
    for m in ("gpt-6.1-sol", "gpt-6-astra"):
        assert out[m]["pooled"]["mean"] == 0.0 and out[m]["pooled"]["sd"] == 0.0


def test_released_sunk_cost_matches_the_headline_numbers():
    out = sunk_cost(load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]))
    assert len(out) == 16
    assert out["gpt-6.1-sol"]["mean"] == pytest.approx(0.56, abs=0.01)
    assert includes(out["gpt-6.1-sol"]["t_ci"], HUMAN_GAP)
    assert out["gpt-4.1"]["mean"] == pytest.approx(2.43, abs=0.01)
    assert (out["gpt-4.1"]["up"], out["gpt-4.1"]["down"]) == (12, 0)
    assert not includes(out["gpt-4.1"]["t_ci"], HUMAN_GAP)
