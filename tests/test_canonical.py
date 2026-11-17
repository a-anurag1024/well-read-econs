import math
from pathlib import Path

import pytest

from wre.canonical import across_models, cross_test, framing_rows, spearman, sunk_rows
from wre.part2 import load

DATA = Path(__file__).resolve().parents[1] / "data"


def test_spearman_known_values():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 2, 2, 4], [1, 2, 2, 4]) == pytest.approx(1.0)  # ties get average ranks
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3]))  # no spread in one variable


def test_across_models_counts_signs_and_brackets_the_mean():
    rows = [{"delta": d, "canon": d, "fresh": 0.0} for d in (10.0, 20.0, -5.0, 0.0, 15.0)]
    s = across_models(rows)
    assert (s["n"], s["larger"], s["smaller"], s["same"]) == (5, 3, 1, 1)
    assert s["mean"] == pytest.approx(8.0)
    assert s["ci"][0] <= s["mean"] <= s["ci"][1]


def test_models_without_canonical_answers_are_left_out():
    rows = [{"delta": float("nan"), "canon": float("nan"), "fresh": 0.0}] + [
        {"delta": d, "canon": d, "fresh": 0.0} for d in (1.0, 2.0, 3.0)
    ]
    assert across_models(rows)["n"] == 3


def test_released_framing_canonical_rows():
    rows = {
        r["model"]: r
        for r in framing_rows(
            load(
                [
                    str(DATA / "run3_framing_openai.jsonl"),
                    str(DATA / "run3_framing_anthropic.jsonl"),
                ]
            )
        )
    }
    assert len(rows) == 16
    assert rows["gpt-4o"]["canon"] == pytest.approx(100.0)
    assert rows["gpt-4o"]["fresh"] == pytest.approx(27.8, abs=0.2)
    assert rows["claude-sonnet-5.5"]["canon"] == pytest.approx(83.3, abs=0.2)
    assert rows["gpt-6.1-sol"]["canon"] == 0.0 and rows["gpt-6.1-sol"]["fresh"] == 0.0
    assert math.isnan(rows["gpt-6-astra"]["canon"])  # no run 3 canonical answers for this model


def test_released_sunk_cost_canonical_rows():
    rows = {
        r["model"]: r
        for r in sunk_rows(
            load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
        )
    }
    assert len(rows) == 16
    assert rows["gpt-4.1"]["canon"] == pytest.approx(1.0)
    assert rows["gpt-4.1"]["fresh"] == pytest.approx(2.43, abs=0.01)
    assert rows["gpt-6.1-sol"]["canon_hi"] == pytest.approx(8.0)


def test_cross_test_correlation_uses_models_in_both_tests():
    framing = [
        {"model": m, "fresh": f} for m, f in (("a", 1.0), ("b", 2.0), ("c", 3.0), ("d", 4.0))
    ]
    sunk = [
        {"model": m, "fresh": g} for m, g in (("a", 10.0), ("b", 20.0), ("c", 30.0), ("d", 5.0))
    ]
    out = cross_test(framing, sunk, unreliable=["d"])
    assert out["n_all"] == 4 and out["n_reliable"] == 3
    assert out["rho_reliable"] == pytest.approx(1.0)
    assert out["rho_all"] == pytest.approx(-0.2)
