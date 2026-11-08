"""Balanced framing robustness set: label format (A/B vs 1/2) crossed with scenario, certain-option
position balanced 50/50 per format. Same scenarios and numbers as framing.PARAMS / SETTINGS.

Items carry task="framing" so reports treat them like the main framing task; ids start with
"framing-v2-" and meta records the label format and certain-option position.
"""
from __future__ import annotations

import random

from .base import Item
from .framing import CANONICAL_GAIN, CANONICAL_LOSS, PARAMS, SETTINGS


def _scenario(setting, params, frame, sure_first, labels):
    intro, unit, pos, neg = setting
    n, s, pa, pn = params
    if frame == "gain":
        sure = f"{s} of the {n} {unit} will be {pos}."
        risky = (f"There is a {pa} chance that all {n} {unit} will be {pos}, and a {pn} chance "
                 f"that none will be {pos}.")
    else:
        sure = f"{n - s} of the {n} {unit} will be {neg}."
        risky = (f"There is a {pa} chance that none of the {unit} will be {neg}, and a {pn} "
                 f"chance that all {n} will be {neg}.")
    first, second = (sure, risky) if sure_first else (risky, sure)
    head = f"{intro.format(N=n)} Two {'plans' if labels == 'AB' else 'options'} have been proposed. " \
           "Assume the estimates below are exact.\n\n"
    if labels == "AB":
        body = f"Plan A: {first}\nPlan B: {second}\n\nWhich plan do you choose? Answer with only the letter A or B."
    else:
        body = (f"Option 1: {first}\nOption 2: {second}\n\n"
                "Which option do you choose? Answer with only the number 1 or 2.")
    return head + body


def _canon_swapped(text: str, labels_ab=True) -> str:
    """Swap the order of the two program lines so the certain option is listed second."""
    lines = text.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("If Program")]
    a, b = lines[idx[0]], lines[idx[1]]
    lines[idx[0]] = b.replace("Program B", "Program A")
    lines[idx[1]] = a.replace("Program A", "Program B")
    return "\n".join(lines)


def build(seed: int = 0) -> list[Item]:
    rng = random.Random(seed)
    settings = SETTINGS[:]
    rng.shuffle(settings)
    items: list[Item] = []
    for i, params in enumerate(PARAMS):
        setting = settings[i % len(settings)]
        for fmt, labels in (("ab", "AB"), ("n", "12")):
            # position balanced within each format; each scenario gets both positions across formats
            sure_first = (i % 2 == 0) if labels == "AB" else (i % 2 == 1)
            sure = ("A" if sure_first else "B") if labels == "AB" else ("1" if sure_first else "2")
            for frame, cond in (("gain", "hi"), ("loss", "lo")):
                items.append(Item(
                    f"framing-v2-{fmt}{i:02d}-{cond}", "framing", "fresh", cond,
                    f"framing-v2-{i:02d}", _scenario(setting, params, frame, sure_first, labels),
                    {"sure": sure, "labels": labels, "sure_first": sure_first, "frame": frame, "fmt": fmt}))
    for pos in ("first", "second"):
        for text, cond in ((CANONICAL_GAIN, "hi"), (CANONICAL_LOSS, "lo")):
            t = text if pos == "first" else _canon_swapped(text)
            items.append(Item(f"framing-v2-canon-{pos}-{cond}", "framing", "canonical", cond,
                              f"framing-v2-canon-{pos}", t,
                              {"sure": "A" if pos == "first" else "B", "labels": "AB",
                               "sure_first": pos == "first", "fmt": "ab"}))
    return items
