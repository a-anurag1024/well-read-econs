from pathlib import Path

import pytest

from wre.part2 import load
from wre.position_swing import analyze, cell, first_listed_share, render

DATA = Path(__file__).resolve().parents[1] / "data"


def _rec(condition: str, sure: float, sure_first: bool) -> dict:
    return {
        "task": "framing",
        "version": "fresh",
        "model": "m",
        "condition": condition,
        "parsed": sure,
        "err": None,
        "meta": {"sure_first": sure_first},
    }


def test_cell_swing_is_saved_minus_lost():
    recs = [_rec("hi", 1.0, True), _rec("hi", 1.0, True), _rec("lo", 1.0, True), _rec("lo", 0.0, True)]
    c = cell(recs)
    assert (c["saved"], c["lost"], c["swing"]) == (100.0, 50.0, 50.0)
    assert (c["n_saved"], c["n_lost"]) == (2, 2)


def test_first_listed_share_follows_the_layout_not_the_plan():
    # sure plan first and chosen, sure plan second and not chosen: both are the first-listed option
    recs = [_rec("hi", 1.0, True), _rec("lo", 0.0, False), _rec("hi", 0.0, True), _rec("lo", 1.0, False)]
    assert first_listed_share(recs) == 50.0


def test_known_cells_from_the_released_data():
    out = analyze(
        load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    )
    assert len(out) == 16
    sonnet = out["claude-sonnet-5.5"]
    assert sonnet["pooled"]["swing"] == pytest.approx(49, abs=0.6)
    assert sonnet["sure_first"]["swing"] == pytest.approx(8, abs=0.6)
    assert sonnet["sure_second"]["swing"] == pytest.approx(89, abs=0.6)
    assert sonnet["sure_first"]["lost"] == pytest.approx(92, abs=0.6)
    assert sonnet["sure_second"]["lost"] == pytest.approx(8, abs=0.6)
    for m in ("gpt-6.1-sol", "gpt-6-astra"):
        assert out[m]["sure_first"]["swing"] == out[m]["sure_second"]["swing"] == 0.0
    assert out["claude-haiku-4.5"]["first_listed"] == pytest.approx(8, abs=0.6)
    assert "swing 31" in render(out)
