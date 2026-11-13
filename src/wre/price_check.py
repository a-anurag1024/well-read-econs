"""Does the paid-minus-free gap grow with the ticket price?

The sunk cost scenarios name a price for the paid ticket ($45 to $150). If the gap were a response to
"money spent", it should be larger in the scenarios with the higher price. For each model this module takes
the per-scenario gap (average rating with the paid ticket minus the average with the free one) and
correlates it with the price of that scenario, plus a simpler split: the six cheapest scenarios against
the six most expensive ones.

    python -m wre.price_check

Uses the run 2 answers on the revised items (the same cells as `chart_sunk_cost.png`). Deterministic: no
resampling. With 12 scenarios, a correlation has to be beyond about +/-0.58 to be told apart from zero.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import StatisticsError, correlation

from .part2 import _ok, load

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ITEMS = ROOT / "items" / "main.jsonl"
CRITICAL_R = 0.58  # two-sided 5% threshold for a correlation over 12 points


def prices(path: Path = ITEMS) -> dict[str, float]:
    """Price named in each revised fresh sunk cost scenario, keyed by scenario."""
    out: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["task"] == "sunkcost" and r["version"] == "fresh" and "-v11" in r["id"]:
            out[r["item_key"]] = float(r["meta"]["price"])
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _ranks(xs: list[float]) -> list[float]:
    """Average ranks, so tied values share a rank."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def _corr(x: list[float], y: list[float]) -> float:
    try:
        return correlation(x, y)
    except (StatisticsError, ZeroDivisionError):
        return float("nan")  # fewer than two points, or one of the two series is constant


def scenario_gaps(recs: list[dict], price: dict[str, float]) -> list[tuple[float, float]]:
    """(price, gap) per scenario that has a scored answer in both versions. `hi` is paid, `lo` free."""
    cells: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"hi": [], "lo": []})
    for r in recs:
        if _ok(r) and r["item_key"] in price:
            cells[r["item_key"]][r["condition"]].append(float(r["parsed"]))
    return [(price[k], _mean(v["hi"]) - _mean(v["lo"])) for k, v in cells.items() if v["hi"] and v["lo"]]


def model_row(pairs: list[tuple[float, float]]) -> dict:
    pairs = sorted(pairs, key=lambda p: p[0])
    x, y = [p[0] for p in pairs], [p[1] for p in pairs]
    half = len(pairs) // 2
    return {
        "scenarios": len(pairs),
        "pearson": _corr(x, y),
        "spearman": _corr(_ranks(x), _ranks(y)),
        "cheap_gap": _mean(y[:half]),
        "dear_gap": _mean(y[len(y) - half :]),
    }


def analyze(base_sunk: list[dict], price: dict[str, float]) -> dict[str, dict]:
    """{model: row} from run 2 sunk cost answers on the revised fresh scenarios."""
    recs = [
        r
        for r in base_sunk
        if r["task"] == "sunkcost" and r["version"] == "fresh" and "-v11" in r["id"]
    ]
    models = list(dict.fromkeys(r["model"] for r in recs))
    return {m: model_row(scenario_gaps([r for r in recs if r["model"] == m], price)) for m in models}


def render(out: dict[str, dict], price: dict[str, float]) -> str:
    lo, hi = min(price.values()), max(price.values())
    lines = [
        "DOES THE PAID-MINUS-FREE GAP GROW WITH THE TICKET PRICE?",
        f"{len(price)} scenarios, paid ticket priced from ${lo:.0f} to ${hi:.0f}. Gap = average rating with the paid ticket",
        "minus average with the free ticket (1-9 scale, run 2, revised items), computed per scenario.",
        "r = Pearson and rho = Spearman correlation of the scenario gap with the scenario price.",
        "cheap/dear = average gap over the six cheapest / six most expensive scenarios.",
        f"With 12 scenarios, |r| must exceed about {CRITICAL_R} to be told apart from zero. nan = no variation in the gap.",
        "",
        f"{'model':20s} {'scenarios':>9s} {'r':>7s} {'rho':>7s} {'cheap':>7s} {'dear':>7s}",
    ]
    for m, c in out.items():
        lines.append(
            f"{m:20s} {c['scenarios']:9d} {c['pearson']:+7.2f} {c['spearman']:+7.2f} "
            f"{c['cheap_gap']:+7.2f} {c['dear_gap']:+7.2f}"
        )
    rs = [c["pearson"] for c in out.values() if c["pearson"] == c["pearson"]]
    lines += [
        "",
        (
            f"models with a correlation: {len(rs)} of {len(out)}; positive {sum(r > 0 for r in rs)}, "
            f"negative {sum(r < 0 for r in rs)}"
        ),
        f"range of r: {min(rs):+.2f} to {max(rs):+.2f}",
        f"models with |r| above {CRITICAL_R}: {sum(abs(r) > CRITICAL_R for r in rs)}",
    ]
    return "\n".join(lines)


def main() -> None:
    base = load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    price = prices()
    print(render(analyze(base, price), price))


if __name__ == "__main__":
    main()
