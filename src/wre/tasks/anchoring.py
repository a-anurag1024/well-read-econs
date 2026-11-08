"""Anchoring in numeric estimation (Jacowitz & Kahneman, 1995).

The respondent first judges whether a quantity is more or less than an anchor, then estimates it.
Humans estimate higher after a high anchor, so hi = "high", lo = "low". Outcome: the estimate;
analysis uses log estimates standardized within item (see effects.within_item_z), because the
quantities have different scales.

The Many Labs 1 topics (babies born per day, Mt Everest, population of Chicago, distance
San Francisco to New York) are not included: the items below use other quantities with
well-established values, so comparison with the Many Labs effect is rough;
anchors are about 0.3x (low) and 3x (high) the true value.
"""
from __future__ import annotations

import re

from .base import Item, Task

# (key, quantity phrase, unit, true value, low anchor, high anchor)
TOPICS = [
    ("eiffel", "height of the Eiffel Tower including its antennas", "meters", 330, 100, 1000),
    ("burj", "height of the Burj Khalifa", "meters", 828, 250, 2500),
    ("london_sydney", "distance from London to Sydney", "kilometers", 17000, 5000, 50000),
    ("canada", "population of Canada", "million people", 40, 12, 120),
    ("bones", "number of bones in an adult human body", "bones", 206, 60, 600),
    ("challenger", "depth of the Challenger Deep, the deepest point of the ocean", "meters",
     10900, 3300, 33000),
    ("australia", "population of Australia", "million people", 27, 8, 80),
    ("mississippi", "length of the Mississippi River", "kilometers", 3700, 1100, 11000),
    ("moon_diam", "diameter of the Moon", "kilometers", 3474, 1000, 10000),
    ("moon_dist", "average distance from the Earth to the Moon", "thousand kilometers",
     384, 115, 1150),
    ("redwood", "height of the tallest known coast redwood tree", "meters", 116, 35, 350),
    ("un", "number of member states of the United Nations", "countries", 193, 58, 580),
]

FORMAT = ("Reply with two lines. First line: only the word 'more' or 'less'. Second line: only "
          "your best estimate as a plain number (no units, no commas).")


def _prompt(quantity: str, unit: str, anchor: int) -> str:
    return (f"Is the {quantity} more or less than {anchor:,} {unit}? Then estimate the "
            f"{quantity} in {unit}. {FORMAT}")


def build(seed: int = 0) -> list[Item]:
    items: list[Item] = []
    for key, quantity, unit, truth, low, high in TOPICS:
        for cond, anchor in (("hi", high), ("lo", low)):
            items.append(Item(f"anchoring-fresh-{key}-{cond}", "anchoring", "fresh", cond,
                              f"anchoring-fresh-{key}", _prompt(quantity, unit, anchor),
                              {"truth": truth, "anchor": anchor, "unit": unit}))
    return items


def parse(text: str, item: Item) -> float | None:
    """Estimate = last number in the reply (the format asks for it on the last line)."""
    nums = re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not nums:
        return None
    try:
        v = float(nums[-1].replace(",", ""))
    except ValueError:
        return None
    return v if v > 0 else None


TASK = Task("anchoring", "continuous", "anchoring", build, parse)
