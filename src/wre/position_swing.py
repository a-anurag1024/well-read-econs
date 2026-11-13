"""Framing swing by position of the sure plan (run 3), in percentage points.

`robust` reports one pooled number per model. The sure plan was listed first in exactly half of the questions
and second in the other half, and every scenario appears in both layouts. This module splits the same answers
by that layout, so a swing that exists in only one layout is visible.

    python -m wre.position_swing

Swing = share choosing the sure plan under the "saved" wording minus under the "lost" wording.
"First-listed share" = share of answers that chose whichever option was listed first.
"""

from __future__ import annotations

from pathlib import Path

from .part2 import _ok, load

DATA = Path(__file__).resolve().parents[2] / "data"
HUMAN_SWING = 65.5 - 34.5  # Many Labs 1 (see human_reference.py)


def _share(recs: list[dict], condition: str) -> float:
    xs = [float(r["parsed"]) for r in recs if r["condition"] == condition]
    return 100 * sum(xs) / len(xs) if xs else float("nan")


def cell(recs: list[dict]) -> dict:
    saved, lost = _share(recs, "hi"), _share(recs, "lo")
    return {
        "saved": saved,
        "lost": lost,
        "swing": saved - lost,
        "n_saved": sum(r["condition"] == "hi" for r in recs),
        "n_lost": sum(r["condition"] == "lo" for r in recs),
    }


def first_listed_share(recs: list[dict]) -> float:
    """Share of answers choosing the option that was listed first (the sure plan when it was first)."""
    hits = sum((float(r["parsed"]) == 1.0) == bool(r["meta"]["sure_first"]) for r in recs)
    return 100 * hits / len(recs) if recs else float("nan")


def analyze(results: list[dict]) -> dict[str, dict]:
    """{model: {"pooled": cell, "sure_first": cell, "sure_second": cell, "first_listed": percent}}."""
    fresh = [r for r in results if r["task"] == "framing" and r["version"] == "fresh" and _ok(r)]
    out: dict[str, dict] = {}
    for m in dict.fromkeys(r["model"] for r in fresh):
        mine = [r for r in fresh if r["model"] == m]
        out[m] = {
            "pooled": cell(mine),
            "sure_first": cell([r for r in mine if r["meta"]["sure_first"]]),
            "sure_second": cell([r for r in mine if not r["meta"]["sure_first"]]),
            "first_listed": first_listed_share(mine),
        }
    return out


def render(out: dict[str, dict]) -> str:
    lines = [
        "FRAMING SWING BY POSITION OF THE SURE PLAN (run 3, fresh scenarios, percentage points)",
        f"people (Many Labs 1): 65.5% vs 34.5%, swing {HUMAN_SWING:.0f}",
        "sure first / sure second: the sure plan was listed first / second; saved/lost = % choosing the sure plan.",
        "pooled = both layouts together (the swing in chart_swing.png). first-listed = % choosing the first-listed option.",
        "",
        (
            f"{'model':18s} {'pooled':>6s}  {'sure first':>10s} {'saved/lost':>11s}  "
            f"{'sure second':>11s} {'saved/lost':>11s}  {'first-listed':>12s}  n per cell"
        ),
    ]
    for m, c in out.items():
        a, b = c["sure_first"], c["sure_second"]
        lines.append(
            f"{m:18s} {c['pooled']['swing']:6.0f}  {a['swing']:10.0f} {a['saved']:5.0f}/{a['lost']:<5.0f}  "
            f"{b['swing']:11.0f} {b['saved']:5.0f}/{b['lost']:<5.0f}  {c['first_listed']:11.0f}%  "
            f"{a['n_saved']}/{a['n_lost']}/{b['n_saved']}/{b['n_lost']}"
        )
    return "\n".join(lines)


def main() -> None:
    results = load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    print(render(analyze(results)))


if __name__ == "__main__":
    main()
