"""Paid-minus-free gaps in rating points, under each one-line instruction (Part 2).

`part2` reports the sunk cost test as an effect size. This module reports the same cells in plain units:
the average 1-9 rating with a paid ticket minus the average with a free ticket, plus how many of the 12
scenarios go up, go down or stay equal when only the ticket sentence changes.

    python -m wre.sunk_gaps

"No instruction" comes from the earlier run (run 2, revised items), because the prompting run has no
matching arm. Everything is deterministic: no resampling.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .part2 import ANCHORS, EXTRAS, _ok, load

DATA = Path(__file__).resolve().parents[2] / "data"
PROMPTS = ("none", "typical", "gut", "rational")
HUMAN_PAID, HUMAN_FREE = 7.85, 7.24  # Many Labs 1 means, 1-9 scale (see human_reference.py)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def cell_gap(recs: list[dict]) -> dict:
    """Gap for one model and one instruction. `hi` is the paid ticket, `lo` the free one."""
    paid = [float(r["parsed"]) for r in recs if _ok(r) and r["condition"] == "hi"]
    free = [float(r["parsed"]) for r in recs if _ok(r) and r["condition"] == "lo"]
    by_scenario: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"hi": [], "lo": []})
    for r in recs:
        if _ok(r):
            by_scenario[r["item_key"]][r["condition"]].append(float(r["parsed"]))
    diffs = [_mean(v["hi"]) - _mean(v["lo"]) for v in by_scenario.values() if v["hi"] and v["lo"]]
    return {
        "paid": _mean(paid),
        "free": _mean(free),
        "gap": _mean(paid) - _mean(free),
        "n_paid": len(paid),
        "n_free": len(free),
        "unscored": sum(1 for r in recs if not _ok(r)),
        "scenarios": len(diffs),
        "up": sum(d > 0 for d in diffs),
        "down": sum(d < 0 for d in diffs),
    }


def analyze(results: list[dict], base_sunk: list[dict]) -> dict[str, dict[str, dict]]:
    """{model: {instruction: cell}} for the seven models in the prompting run."""
    out: dict[str, dict[str, dict]] = {}
    for m in (x for x in ANCHORS + EXTRAS if any(r["model"] == x for r in results)):
        base = [
            r
            for r in base_sunk
            if r["model"] == m
            and r["task"] == "sunkcost"
            and r["version"] == "fresh"
            and "-v11" in r["id"]
        ]
        out[m] = {"none": cell_gap(base)}
        for p in PROMPTS[1:]:
            mine = [
                r
                for r in results
                if r["model"] == m and r["task"] == "sunkcost" and r["meta"].get("persona") == p
            ]
            out[m][p] = cell_gap(mine)
    return out


def render(out: dict[str, dict[str, dict]]) -> str:
    human = HUMAN_PAID - HUMAN_FREE
    lines = [
        "PAID MINUS FREE, IN RATING POINTS (1-9 scale), UNDER EACH ONE-LINE INSTRUCTION",
        f"people (Many Labs 1): paid {HUMAN_PAID:.2f} vs free {HUMAN_FREE:.2f}, gap {human:+.2f}",
        "'none' is run 2 (revised items); typical, gut and rational are run 4. 12 fresh scenarios per cell.",
        "up/down: scenarios where the paid version was rated higher/lower than the free one (both versions scored).",
        "unscored: answers that could not be turned into a number (for example, an explanation instead of a rating).",
        "",
        (
            f"{'model':18s} {'prompt':9s} {'paid':>6s} {'free':>6s} {'gap':>6s}  {'up/down/of':>10s}  "
            f"{'answers paid/free':>17s}  unscored"
        ),
    ]
    for m, cells in out.items():
        for p in PROMPTS:
            c = cells[p]
            lines.append(
                f"{m:18s} {p:9s} {c['paid']:6.2f} {c['free']:6.2f} {c['gap']:+6.2f}  "
                f"{c['up']:>3d}/{c['down']}/{c['scenarios']:<4d}  {c['n_paid']:>8d}/{c['n_free']:<8d}  {c['unscored']:>8d}"
            )
    return "\n".join(lines)


def main() -> None:
    results = load([str(DATA / "run4_prompting.jsonl")])
    base = load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    print(render(analyze(results, base)))


if __name__ == "__main__":
    main()
