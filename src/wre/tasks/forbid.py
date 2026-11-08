"""Allowed vs forbidden question wording (Rugg, 1941).

The same civil-liberties question is asked as "should X be allowed?" or "should X be forbidden?".
Humans are more likely to answer "No" to allowing than "Yes" to forbidding, so a restrictive
position is expressed more often under the "allow" wording: hi = "allow", lo = "forbid".
Outcome: 1 if the answer is restrictive ("No" to allow, "Yes" to forbid).

Models often decline to give opinions; unparseable answers are recorded as missing and the
rate is reported. The canonical wording is not guaranteed to match the original materials.
"""
from __future__ import annotations

import re

from .base import Item, Task

COUNTRY = "the United States"
# v1.1 topics: practices on which opinion is divided, so that answers are not at floor. The
# human allow/forbid effect for these topics is NOT verified; only the democracy-speech item
# (canonical) has a Many Labs reference.
TOPICS_V11 = [
    ("patios", "smoking on outdoor restaurant patios"),
    ("helmets", "cyclists riding without helmets on city streets"),
    ("email", "employers monitoring employees' work email"),
    ("energy", "stores selling energy drinks to teenagers"),
    ("bars", "bars staying open until 4 a.m."),
    ("pets", "landlords banning pets in rental apartments"),
    ("fireworks", "private fireworks displays in residential neighborhoods"),
    ("offleash", "dogs running off leash in city parks"),
    ("gambling", "gambling advertisements on television"),
    ("office", "companies requiring employees to work from the office five days a week"),
    ("leaf", "the use of gas-powered leaf blowers in residential areas"),
    ("uniforms", "mandatory school uniforms in public schools"),
]
# v1 topics (run 1): civil-liberties items; models gave 0% restrictive answers (floor).
TOPICS_V1 = [
    ("canon", "public speeches against democracy"),
    ("govt_speech", "public speeches against the elected government"),
    ("army_press", "newspapers to publish harsh criticism of the army"),
    ("protests", "peaceful street protests in the capital"),
    ("open_air", "religious groups to hold open-air meetings in public squares"),
    ("flag_books", "books that strongly criticize the national flag"),
    ("radical_rallies", "rallies by small radical political parties"),
    ("class_critic", "teachers to criticize the government in class"),
    ("pamphlets", "citizens to distribute anonymous political pamphlets"),
    ("journalists", "foreign journalists to report freely from the country"),
    ("dictator_talk", "public speeches in favor of dictatorship"),
    ("strikes", "workers in public services to go on strike"),
]
FORMAT = "Answer as a survey respondent would. Reply with only 'Yes' or 'No'."


def _prompt(verb: str, topic: str, who: str = COUNTRY) -> str:
    return f"Do you think {who} should {verb} {topic}? {FORMAT}"


def build(seed: int = 0, variant: str = "v1.1") -> list[Item]:
    """variant "v1" reproduces run 1 (civil-liberties topics); "v1.1" is the final item set:
    the canonical democracy-speech item plus mid-controversy topics ("the law should ...")."""
    items: list[Item] = []
    canon = TOPICS_V1[0]
    for cond, verb in (("hi", "allow"), ("lo", "forbid")):
        items.append(Item(f"forbid-canon-{cond}", "forbid", "canonical", cond, "forbid-canon",
                          _prompt(verb, canon[1]), {"wording": verb}))
    if variant == "v1":
        for key, topic in TOPICS_V1[1:]:
            for cond, verb in (("hi", "allow"), ("lo", "forbid")):
                items.append(Item(f"forbid-{key}-{cond}", "forbid", "fresh", cond, f"forbid-{key}",
                                  _prompt(verb, topic), {"wording": verb}))
    else:
        for key, topic in TOPICS_V11:
            for cond, verb in (("hi", "allow"), ("lo", "forbid")):
                items.append(Item(f"forbid-v11-{key}-{cond}", "forbid", "fresh", cond,
                                  f"forbid-v11-{key}", _prompt(verb, topic, "the law"),
                                  {"wording": verb, "variant": variant}))
    return items


def parse(text: str, item: Item) -> float | None:
    m = re.search(r"\b(yes|no)\b", text, flags=re.IGNORECASE)
    if not m:
        return None
    said_yes = m.group(1).lower() == "yes"
    if item.meta["wording"] == "allow":
        return 1.0 if not said_yes else 0.0   # "No" to allowing = restrictive
    return 1.0 if said_yes else 0.0           # "Yes" to forbidding = restrictive


TASK = Task("forbid", "binary", "forbid", build, parse)
