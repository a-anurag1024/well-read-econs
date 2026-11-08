"""Release integrity: frozen items match the code, and every row of data/ refers to a frozen item."""

import json
from pathlib import Path

import pytest

from wre import freeze

ROOT = Path(__file__).resolve().parents[1]
DATA_TO_SET = {
    "run1_openai": "main_run1",
    "run2_openai": "main",
    "run2_anthropic": "main",
    "run3_framing_openai": "framing_v2",
    "run3_framing_anthropic": "framing_v2",
    "run4_prompting": "prompting",
}


def test_frozen_items_match_code():
    assert freeze.check(ROOT / "items") == []


@pytest.mark.parametrize("name", sorted(DATA_TO_SET))
def test_every_data_row_refers_to_a_frozen_item(name):
    ids = {
        json.loads(line)["id"]
        for line in (ROOT / "items" / f"{DATA_TO_SET[name]}.jsonl").read_text(encoding="utf-8").splitlines()
    }
    rows = [json.loads(line) for line in (ROOT / "data" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and {r["id"] for r in rows} <= ids
    assert all(not r["err"] for r in rows)


def test_data_row_counts_match_the_dataset_card():
    card = (ROOT / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    total = 0
    for name in DATA_TO_SET:
        n = sum(1 for _ in (ROOT / "data" / f"{name}.jsonl").open(encoding="utf-8"))
        total += n
        assert f"{n:,}" in card, name
    assert f"{total:,}" in card
