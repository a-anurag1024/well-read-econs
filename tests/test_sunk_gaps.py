from pathlib import Path

import pytest

from wre.part2 import load
from wre.sunk_gaps import analyze, cell_gap, render

DATA = Path(__file__).resolve().parents[1] / "data"


def _rec(key: str, cond: str, value: float | None, err: str | None = None) -> dict:
    return {"item_key": key, "condition": cond, "parsed": value, "err": err}


def test_cell_gap_counts_scenarios_that_go_up_down_or_stay():
    recs = [
        _rec("a", "hi", 6),
        _rec("a", "lo", 4),  # up
        _rec("b", "hi", 3),
        _rec("b", "lo", 5),  # down
        _rec("c", "hi", 4),
        _rec("c", "lo", 4),  # equal
    ]
    c = cell_gap(recs)
    assert (c["up"], c["down"], c["scenarios"]) == (1, 1, 3)
    assert c["paid"] == pytest.approx(13 / 3) and c["free"] == pytest.approx(13 / 3)
    assert c["gap"] == pytest.approx(0.0)


def test_unscored_answers_are_counted_and_do_not_form_a_pair():
    recs = [
        _rec("a", "hi", 7),
        _rec("a", "lo", 5),
        _rec("b", "hi", None),
        _rec("b", "lo", 5),
        _rec("c", "hi", 5, "boom"),
    ]
    c = cell_gap(recs)
    assert c["unscored"] == 2 and c["scenarios"] == 1 and c["up"] == 1
    assert (c["n_paid"], c["n_free"]) == (1, 2)


def test_known_cells_from_the_released_data():
    out = analyze(
        load([str(DATA / "run4_prompting.jsonl")]),
        load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]),
    )
    assert list(out)[:4] == ["gpt-6.1-sol", "gpt-6-astra", "claude-sonnet-5.5", "claude-opus-5.5"]
    assert out["gpt-6.1-sol"]["none"]["gap"] == pytest.approx(0.56, abs=0.005)
    assert out["claude-opus-5.5"]["typical"]["gap"] == pytest.approx(2.92, abs=0.005)
    assert out["gpt-6-astra"]["rational"]["gap"] == pytest.approx(0.08, abs=0.005)
    assert out["claude-sonnet-5.5"]["rational"]["unscored"] == 6
    assert "gap +0.61" in render(out)
