"""Sunk cost: willingness to attend an event when the ticket was paid for vs free.

Format follows Oppenheimer, Meyvis & Davidenko (2009) as replicated in Many Labs 1
(Klein et al., 2014): imagine tickets to a game, bad weather on the day, rate the likelihood of
attending from 1 (definitely stay at home) to 9 (definitely go). Humans give higher ratings when
the ticket was paid for, so hi = "paid", lo = "free".

The canonical wording is not guaranteed to match the original materials; no headline result
depends on it.
"""
from __future__ import annotations

import random

from .base import Item, Task, first_number

SCALE = ("Rate how likely you are to attend on a scale from 1 (definitely stay at home) to 9 "
         "(definitely go). Answer with only a number.")

CANONICAL = {
    "hi": ("Imagine that you have tickets to see your favorite football team play an important "
           "game, but it is freezing cold on the day of the game. You paid for the ticket. " + SCALE),
    "lo": ("Imagine that you have tickets to see your favorite football team play an important "
           "game, but it is freezing cold on the day of the game. The ticket was free. " + SCALE),
}

# (what you are going to, bad-conditions clause)
EVENTS = [
    ("a concert by your favorite band", "it is pouring rain and the venue is a long drive away"),
    ("an important basketball game", "a snowstorm has made the roads slippery"),
    ("a play at the city theater", "you feel tired after a long week and it is raining"),
    ("a stand-up comedy night", "it is bitterly cold and the last train home is early"),
    ("the final of a local tennis tournament", "it is windy, wet and cold"),
    ("a music festival day", "the forecast is for heavy rain all day"),
    ("an outdoor film screening", "it is freezing and the screening is outdoors"),
    ("a sold-out dance performance", "there is heavy traffic and it is snowing"),
    ("a baseball game", "it is drizzling and a cold wind has picked up"),
    ("a charity gala dinner", "a storm warning is in effect for your area"),
    ("a cycling race you wanted to watch", "it is icy and the course is far from home"),
    ("an opera performance", "you have a head cold and it is sleeting"),
]
PRICES = [45, 60, 80, 95, 120, 150, 70, 110, 55, 85, 130, 100]


FREE = {"v1": "The ticket was a free gift.",
        "v1.1": "The ticket was free: you got it in a promotional giveaway."}


def build(seed: int = 0, variant: str = "v1.1") -> list[Item]:
    """variant "v1" is the wording of run 1 ("a free gift", which adds a social-obligation cue);
    "v1.1" uses a neutral promotional free ticket. v1.1 item ids carry a "-v11" tag."""
    rng = random.Random(seed)
    tag = "" if variant == "v1" else "-v11"
    items = [Item(f"sunkcost-canon-{c}", "sunkcost", "canonical", c, "sunkcost-canon",
                  CANONICAL[c]) for c in ("hi", "lo")]
    events = EVENTS[:]
    rng.shuffle(events)
    for i, (event, bad) in enumerate(events):
        price = PRICES[i % len(PRICES)]
        base = f"Imagine that you have tickets to {event}, but {bad} on the day. "
        text = {"hi": base + f"You paid ${price} for the ticket. " + SCALE,
                "lo": base + FREE[variant] + " " + SCALE}
        for cond in ("hi", "lo"):
            items.append(Item(f"sunkcost{tag}-fresh{i:02d}-{cond}", "sunkcost", "fresh", cond,
                              f"sunkcost{tag}-fresh{i:02d}", text[cond],
                              {"price": price, "variant": variant}))
    return items


def parse(text: str, item: Item) -> float | None:
    v = first_number(text)
    return v if v is not None and 1 <= v <= 9 else None


TASK = Task("sunkcost", "continuous", "sunkcost", build, parse)
