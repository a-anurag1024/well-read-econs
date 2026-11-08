"""Shared types for benchmark tasks."""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Item:
    """One prompt shown to one simulated respondent.

    `condition` is "hi" or "lo": hi is the condition in which humans produce the larger value of
    the outcome (e.g. the gain frame for choosing the sure option). `item_key` groups the two
    conditions of the same scenario; the item, not the sampled answer, is the unit of analysis.
    """

    id: str
    task: str
    version: str          # "canonical" or "fresh"
    condition: str        # "hi" | "lo"
    item_key: str
    prompt: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    name: str
    outcome_kind: str                      # "binary" | "continuous"
    human_key: str                         # key into human_reference.HUMAN (or prefix)
    build: Callable[[int], list[Item]]     # seed -> items
    parse: Callable[[str, Item], float | None]


def first_letter(text: str, allowed: str) -> str | None:
    """First standalone capital letter from `allowed` (e.g. "AB")."""
    m = re.search(rf"\b([{allowed}])\b", text)
    return m.group(1) if m else None


def first_number(text: str) -> float | None:
    """First number in text; accepts thousands separators."""
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None
