"""Gain vs loss framing of a risky choice (Tversky & Kahneman, 1981).

Outcome: 1 if the respondent chooses the certain option, else 0. Humans choose it more often
in the gain frame, so hi = "gain", lo = "loss". Both frames describe the same outcomes with equal
expected value.

The canonical item follows the description of the Many Labs 1 replication (Klein et al., 2014).
It is not guaranteed to match the original wording; no headline result depends on it.
"""
from __future__ import annotations

import random
import re

from .base import Item, Task, first_letter

CANONICAL_GAIN = (
    "Imagine that the country is preparing for the outbreak of an unusual disease, which is "
    "expected to kill 600 people. Two alternative programs to combat the disease have been "
    "proposed. Assume that the exact scientific estimates of the consequences of the programs "
    "are as follows:\n\n"
    "If Program A is adopted, 200 people will be saved.\n"
    "If Program B is adopted, there is a 1/3 probability that 600 people will be saved and a "
    "2/3 probability that no people will be saved.\n\n"
    "Which of the two programs would you favor? Answer with only the letter A or B."
)
CANONICAL_LOSS = (
    "Imagine that the country is preparing for the outbreak of an unusual disease, which is "
    "expected to kill 600 people. Two alternative programs to combat the disease have been "
    "proposed. Assume that the exact scientific estimates of the consequences of the programs "
    "are as follows:\n\n"
    "If Program A is adopted, 400 people will die.\n"
    "If Program B is adopted, there is a 1/3 probability that nobody will die and a 2/3 "
    "probability that 600 people will die.\n\n"
    "Which of the two programs would you favor? Answer with only the letter A or B."
)

# (setting with {N}, unit noun, positive participle, negative participle)
SETTINGS = [
    ("A wildfire is approaching a mountain town where {N} residents have not yet evacuated.",
     "residents", "evacuated safely", "left behind"),
    ("A manufacturer is closing a plant, which puts {N} jobs at risk.", "jobs", "kept", "cut"),
    ("A flood is expected to hit a river valley that contains {N} homes.",
     "homes", "protected", "destroyed"),
    ("A fungus is spreading through a nature reserve that holds {N} rare trees.",
     "trees", "saved", "lost"),
    ("A storm has stranded {N} shipping containers of medical supplies at a port.",
     "containers", "recovered", "lost"),
    ("A water main failure has cut off {N} households from clean water.",
     "households", "reconnected", "left without water"),
    ("A basement flood threatens an archive that contains {N} historic manuscripts.",
     "manuscripts", "preserved", "destroyed"),
    ("A cyberattack has exposed {N} customer accounts at a regional bank.",
     "accounts", "secured", "compromised"),
    ("A drought threatens {N} hectares of farmland in a farming region.",
     "hectares", "saved", "lost"),
    ("A marine heat wave puts {N} coral colonies on a protected reef at risk.",
     "coral colonies", "saved", "lost"),
    ("A leaking storage room threatens {N} paintings in a museum's collection.",
     "paintings", "saved", "damaged beyond repair"),
    ("A village grain store is flooding, putting {N} sacks of grain at risk.",
     "sacks", "saved", "spoiled"),
]
# (N, certain number saved, p_all, p_none): equal expected value in both frames
PARAMS = [(480, 160, "one-in-three", "two-in-three"), (900, 300, "one-in-three", "two-in-three"),
          (800, 200, "one-in-four", "three-in-four"), (400, 100, "one-in-four", "three-in-four"),
          (500, 100, "one-in-five", "four-in-five"), (720, 240, "one-in-three", "two-in-three"),
          (1000, 250, "one-in-four", "three-in-four"), (600, 120, "one-in-five", "four-in-five"),
          (360, 120, "one-in-three", "two-in-three"), (840, 280, "one-in-three", "two-in-three"),
          (300, 60, "one-in-five", "four-in-five"), (450, 150, "one-in-three", "two-in-three")]


def _fresh(setting, params, frame, sure_first):
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
    a, b = (sure, risky) if sure_first else (risky, sure)
    return (f"{intro.format(N=n)} Two plans have been proposed. Assume the estimates below are "
            f"exact.\n\nPlan A: {a}\nPlan B: {b}\n\n"
            "Which plan do you choose? Answer with only the letter A or B.")


def build(seed: int = 0) -> list[Item]:
    rng = random.Random(seed)
    items = [
        Item("framing-canon-hi", "framing", "canonical", "hi", "framing-canon", CANONICAL_GAIN,
             {"sure": "A"}),
        Item("framing-canon-lo", "framing", "canonical", "lo", "framing-canon", CANONICAL_LOSS,
             {"sure": "A"}),
    ]
    settings = SETTINGS[:]
    rng.shuffle(settings)
    for i, params in enumerate(PARAMS):
        sure_first = rng.random() < 0.5
        sure = "A" if sure_first else "B"
        for frame, cond in (("gain", "hi"), ("loss", "lo")):
            items.append(Item(f"framing-fresh{i:02d}-{cond}", "framing", "fresh", cond,
                              f"framing-fresh{i:02d}",
                              _fresh(settings[i % len(settings)], params, frame, sure_first),
                              {"sure": sure, "frame": frame}))
    return items


def parse(text: str, item: Item) -> float | None:
    if item.meta.get("labels") == "12":
        m = re.search(r"(?<!\d)([12])(?!\d)", text)
        choice = m.group(1) if m else None
    else:
        choice = first_letter(text, "AB")
    if choice is None:
        return None
    return 1.0 if choice == item.meta["sure"] else 0.0


TASK = Task("framing", "binary", "framing", build, parse)
