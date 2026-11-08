import re

import pytest

from wre.human_reference import HUMAN
from wre.tasks import TASKS, anchoring, build_all, forbid, framing, sunkcost
from wre.tasks.base import first_letter, first_number


def test_ids_unique_and_deterministic():
    a, b = build_all(7), build_all(7)
    assert [i.id for i in a] == [i.id for i in b]
    assert len({i.id for i in a}) == len(a)
    assert [i.prompt for i in build_all(7)] == [i.prompt for i in build_all(7)]


@pytest.mark.parametrize("name", list(TASKS))
def test_every_item_has_a_pair_hi_lo(name):
    items = TASKS[name].build(0)
    keys = {i.item_key for i in items}
    for k in keys:
        conds = sorted(i.condition for i in items if i.item_key == k)
        assert conds == ["hi", "lo"], k


def test_human_reference_keys_exist():
    for t in TASKS.values():
        assert t.human_key in HUMAN


def test_human_reference_values():
    assert abs(HUMAN["framing"].own_d - 0.707) < 0.01
    assert abs(HUMAN["forbid"].own_d - 0.765) < 0.01
    assert abs(HUMAN["sunkcost"].own_d - 0.274) < 0.01
    assert abs(HUMAN["anchoring"].own_d - 1.895) < 1e-9


def test_framing_fresh_equal_expected_value_and_shared_sure_label():
    items = framing.build(0)
    by = {}
    for i in items:
        by.setdefault(i.item_key, {})[i.condition] = i
    for k, d in by.items():
        assert d["hi"].meta["sure"] == d["lo"].meta["sure"], k
    for n, s, pa, pn in framing.PARAMS:
        num = {"one-in-three": 3, "one-in-four": 4, "one-in-five": 5}[pa]
        assert n / num == s, (n, s, pa)  # expected saved by the gamble equals the sure number


def test_framing_parse_counts_sure_choice():
    gain = next(i for i in framing.build(0) if i.id == "framing-fresh00-hi")
    sure = gain.meta["sure"]
    other = "B" if sure == "A" else "A"
    assert framing.parse(sure, gain) == 1.0
    assert framing.parse(f"I choose {other}.", gain) == 0.0
    assert framing.parse("hmm", gain) is None


def test_sunkcost_pairs_differ_only_in_ticket_sentence_and_parse_range():
    items = sunkcost.build(0)
    hi = next(i for i in items if i.id == "sunkcost-v11-fresh00-hi")
    lo = next(i for i in items if i.id == "sunkcost-v11-fresh00-lo")
    assert "paid $" in hi.prompt and "promotional giveaway" in lo.prompt and "gift" not in lo.prompt
    v1 = sunkcost.build(0, variant="v1")
    assert any("free gift" in i.prompt for i in v1) and v1[2].id == "sunkcost-fresh00-hi"
    assert sunkcost.parse("7", hi) == 7.0
    assert sunkcost.parse("12", hi) is None
    assert sunkcost.parse("0", hi) is None


def test_anchoring_anchors_bracket_truth_and_parse_takes_last_number():
    for key, q, unit, truth, low, high in anchoring.TOPICS:
        assert low < truth < high, key
    item = anchoring.build(0)[0]
    assert anchoring.parse("more\n1,250", item) == 1250.0
    assert anchoring.parse("less\n12.5", item) == 12.5
    assert anchoring.parse("no idea", item) is None


def test_forbid_parse_restrictive_semantics():
    items = forbid.build(0)
    allow = next(i for i in items if i.id == "forbid-canon-hi")
    forb = next(i for i in items if i.id == "forbid-canon-lo")
    assert forbid.parse("No", allow) == 1.0 and forbid.parse("Yes", allow) == 0.0
    assert forbid.parse("Yes", forb) == 1.0 and forbid.parse("No.", forb) == 0.0
    assert forbid.parse("It depends", forb) is None
    assert re.search(r"should allow", allow.prompt) and re.search(r"should forbid", forb.prompt)


def test_helpers():
    assert first_letter("Answer: B.", "AB") == "B"
    assert first_number("about 3,400 km") == 3400.0


def test_forbid_v11_topics_are_new_and_v1_reproducible():
    new = forbid.build(0)
    old = forbid.build(0, variant="v1")
    assert {i.item_key for i in new if i.version == "fresh"}.isdisjoint({i.item_key for i in old if i.version == "fresh"})
    assert len([i for i in new if i.version == "fresh"]) == 24
    assert all("the law should" in i.prompt for i in new if i.version == "fresh")
    assert [i.id for i in old][:2] == ["forbid-canon-hi", "forbid-canon-lo"]
    assert any("civil" in t or "journalists" in t for _, t in forbid.TOPICS_V1)


def test_build_all_task_filter():
    only = build_all(0, tasks=["forbid", "sunkcost"])
    assert {i.task for i in only} == {"forbid", "sunkcost"}


def test_framing_v2_balanced_and_parseable():
    from wre.tasks import framing_v2
    items = framing_v2.build(0)
    fresh = [i for i in items if i.version == "fresh" and i.condition == "hi"]
    assert len(fresh) == 24 and len(items) == 52
    for fmt in ("ab", "n"):
        first = [i.meta["sure_first"] for i in fresh if i.meta["fmt"] == fmt]
        assert sum(first) == 6 and len(first) == 12
    # each scenario has the certain option in each position once across the two formats
    for k in {i.item_key for i in fresh}:
        pos = sorted(i.meta["sure_first"] for i in fresh if i.item_key == k)
        assert pos == [False, True]
    by = {}
    for i in items:
        by.setdefault(i.item_key + i.meta.get("fmt", ""), {})[i.condition] = i
    assert all(set(d) == {"hi", "lo"} for d in by.values())
    # parsing both formats, sure label shared across frames
    for i in items:
        sure = i.meta["sure"]
        assert framing.parse(sure, i) == 1.0
        other = {"A": "B", "B": "A", "1": "2", "2": "1"}[sure]
        assert framing.parse(other, i) == 0.0
    n12 = next(i for i in items if i.meta["labels"] == "12")
    assert "Option 1:" in n12.prompt and "number 1 or 2" in n12.prompt
    sec = [i for i in items if i.item_key == "framing-v2-canon-second"]
    assert all(i.meta["sure"] == "B" for i in sec)
    gain = next(i for i in sec if i.condition == "hi")
    assert gain.prompt.index("1/3 probability") < gain.prompt.index("200 people will be saved")
    assert framing.parse("Option 2", n12) in (0.0, 1.0)
    assert framing.parse("I choose 12", n12) is None
