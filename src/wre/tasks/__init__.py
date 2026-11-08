"""Benchmark tasks. Each module exposes a `TASK` (see base.Task)."""
from __future__ import annotations

from . import anchoring, forbid, framing, framing_v2, sunkcost
from .base import Item, Task
from .personas import PERSONAS, with_persona

TASKS: dict[str, Task] = {
    "framing": framing.TASK,
    "sunkcost": sunkcost.TASK,
    "anchoring": anchoring.TASK,
    "forbid": forbid.TASK,
}


def build_all(seed: int = 0, tasks: list[str] | None = None, suite: str = "main",
              personas: list[str] | None = None) -> list[Item]:
    """suite "main" = the four benchmark tasks; "framing_v2" = the balanced framing robustness set;
    "part2" = fresh framing_v2 and sunk cost v1.1 prompts, each behind every instruction in `personas`."""
    if suite == "framing_v2":
        return framing_v2.build(seed)
    if suite == "part2":
        base = [it for it in framing_v2.build(seed) + sunkcost.build(seed, "v1.1") if it.version == "fresh"]
        return [it for tag in (personas or list(PERSONAS)) for it in with_persona(base, tag)]
    items: list[Item] = []
    for name, task in TASKS.items():
        if tasks is None or name in tasks:
            items.extend(task.build(seed))
    return items


__all__ = ["PERSONAS", "TASKS", "Item", "Task", "build_all"]
