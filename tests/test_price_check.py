from pathlib import Path

import pytest

from wre.part2 import load
from wre.price_check import _ranks, analyze, model_row, prices, render, scenario_gaps

DATA = Path(__file__).resolve().parents[1] / "data"


def _rec(key: str, cond: str, value: float | None) -> dict:
    return {
        "item_key": key,
        "condition": cond,
        "parsed": value,
        "err": None,
        "task": "sunkcost",
        "version": "fresh",
        "id": f"{key}-v11-{cond}",
    }


def test_ranks_share_the_average_rank_for_ties():
    assert _ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_gap_that_grows_with_price_gives_correlation_one():
    price = {"a": 50.0, "b": 100.0, "c": 150.0, "d": 200.0}
    recs = []
    for i, k in enumerate(price):
        recs += [_rec(k, "hi", 5 + i), _rec(k, "lo", 5)]  # gap 0, 1, 2, 3
    row = model_row(scenario_gaps(recs, price))
    assert row["pearson"] == pytest.approx(1.0) and row["spearman"] == pytest.approx(1.0)
    assert row["cheap_gap"] == pytest.approx(0.5) and row["dear_gap"] == pytest.approx(2.5)


def test_constant_gap_has_no_correlation_and_unscored_answers_are_skipped():
    price = {"a": 50.0, "b": 100.0, "c": 150.0}
    recs = [_rec("a", "hi", 7), _rec("a", "lo", 5), _rec("b", "hi", 8), _rec("b", "lo", 6)]
    recs += [_rec("c", "hi", None), _rec("c", "lo", 5)]  # no scored paid answer: not a pair
    pairs = scenario_gaps(recs, price)
    assert [p[0] for p in pairs] == [50.0, 100.0]
    assert model_row(pairs)["pearson"] != model_row(pairs)["pearson"]  # nan: the gap is 2 in both


def test_released_data_show_no_model_with_a_clear_price_relationship():
    price = prices()
    assert len(price) == 12 and (min(price.values()), max(price.values())) == (45.0, 150.0)
    out = analyze(load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]), price)
    assert len(out) == 16
    rs = [c["pearson"] for c in out.values()]
    assert min(rs) == pytest.approx(-0.28, abs=0.005) and max(rs) == pytest.approx(0.48, abs=0.005)
    assert all(abs(r) < 0.58 for r in rs)
    assert "range of r: -0.28 to +0.48" in render(out, price)
