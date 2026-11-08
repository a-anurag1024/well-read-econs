"""One-line instructions placed before an otherwise unchanged prompt (Part 2, what prompting does).

The texts are fixed in preregistration/run4-prompting-plan.md before any data. "none" (baseline) is not a
persona here: baseline answers come from the earlier runs on the same items.
"""

from __future__ import annotations

from dataclasses import replace

from .base import Item

PERSONAS: dict[str, str] = {
    "typical": (
        "You are a typical adult taking part in an online survey. Answer the way you would "
        "honestly answer, as an ordinary person, not as an expert."
    ),
    "gut": (
        "Go with your first gut feeling. Do not calculate or analyze anything; answer quickly "
        "and intuitively."
    ),
    "rational": "Answer as a perfectly rational economic decision-maker would.",
}


def with_persona(items: list[Item], tag: str) -> list[Item]:
    """Copies of `items` with the instruction prepended; ids get an `@tag` suffix, item_key is kept."""
    text = PERSONAS[tag]
    return [
        replace(
            it,
            id=f"{it.id}@{tag}",
            prompt=f"{text}\n\n{it.prompt}",
            meta={**it.meta, "persona": tag},
        )
        for it in items
    ]
