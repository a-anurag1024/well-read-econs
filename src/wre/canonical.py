"""Canonical wording against freshly written scenarios, per model, in percentage points and rating points.

Each test has one canonical item (a paraphrase of the textbook version, in two conditions) and 12 fresh
scenarios. The headline results use the fresh scenarios. This module puts the two side by side for every model:

* framing, run 3: canonical swing against fresh swing (both from the balanced run 3 design);
* sunk cost, run 2: canonical paid-minus-free gap against the fresh gap (revised "v11" items).

    python -m wre.canonical

How to read it. The canonical item is ONE scenario and each model answered it only a handful of times per
condition, so a single model's canonical number is noisy and has no interval here. The comparison that carries
information is across models: the mean of (canonical - fresh) over models, with a bootstrap over models, and
how many models show a larger or smaller effect on the canonical wording. A positive mean is what a
"recognition premium" (a stronger effect on the famous wording) would look like, but it is also what one
unusual scenario would look like, because there is only one canonical scenario.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from pathlib import Path
from statistics import fmean

from . import robust
from .item_level import NAN, scenario_diffs
from .part2 import _ok, load

DATA = Path(__file__).resolve().parents[2] / "data"


def _mean_of(recs: Sequence[dict], condition: str) -> tuple[float, int]:
    xs = [float(r["parsed"]) for r in recs if _ok(r) and r["condition"] == condition]
    return (fmean(xs) if xs else NAN), len(xs)


def _row(model: str, canon: Sequence[dict], fresh: Sequence[dict], scale: float) -> dict:
    """One model: canonical effect (pooled answers, one scenario), fresh effect (mean of scenario effects)."""
    hi, n_hi = _mean_of(canon, "hi")
    lo, n_lo = _mean_of(canon, "lo")
    diffs = list(scenario_diffs(fresh, scale).values())
    fresh_effect = fmean(diffs) if diffs else NAN
    canon_effect = (hi - lo) * scale
    return {
        "model": model,
        "canon_hi": hi * scale,
        "canon_lo": lo * scale,
        "n_hi": n_hi,
        "n_lo": n_lo,
        "canon": canon_effect,
        "fresh": fresh_effect,
        "delta": canon_effect - fresh_effect,
    }


def framing_rows(run3: Sequence[dict]) -> list[dict]:
    """Canonical vs fresh framing swing (percentage points) from run 3, one row per model."""
    out = []
    for m in dict.fromkeys(r["model"] for r in run3):
        mine = [r for r in run3 if r["model"] == m and r["task"] == "framing"]
        out.append(
            _row(
                m,
                [r for r in mine if r["version"] == "canonical"],
                [r for r in mine if r["version"] == "fresh"],
                100,
            )
        )
    return out


def sunk_rows(run2: Sequence[dict]) -> list[dict]:
    """Canonical vs fresh sunk cost gap (rating points) from run 2, one row per model."""
    out = []
    for m in dict.fromkeys(r["model"] for r in run2):
        mine = [r for r in run2 if r["model"] == m and r["task"] == "sunkcost"]
        canon = [r for r in mine if r["version"] == "canonical"]
        fresh = [r for r in mine if r["version"] == "fresh" and "-v11" in r["id"]]
        out.append(_row(m, canon, fresh, 1.0))
    return out


def _ranks(xs: Sequence[float]) -> list[float]:
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


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation (Pearson correlation of average ranks)."""
    if len(xs) < 3:
        return NAN
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = fmean(rx), fmean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else NAN


def across_models(rows: Sequence[dict], n_boot: int = 2000, seed: int = 0) -> dict:
    """Mean of (canonical - fresh) over models with a 95% bootstrap over models, sign counts and Spearman."""
    use = [r for r in rows if math.isfinite(r["delta"])]
    deltas = [r["delta"] for r in use]
    if len(deltas) < 3:
        return {
            "n": len(deltas),
            "mean": NAN,
            "ci": (NAN, NAN),
            "larger": 0,
            "smaller": 0,
            "same": 0,
            "rho": NAN,
        }
    rng = random.Random(seed)
    means = sorted(fmean(rng.choices(deltas, k=len(deltas))) for _ in range(n_boot))
    return {
        "n": len(deltas),
        "mean": fmean(deltas),
        "ci": (means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]),
        "larger": sum(d > 0 for d in deltas),
        "smaller": sum(d < 0 for d in deltas),
        "same": sum(d == 0 for d in deltas),
        "rho": spearman([r["canon"] for r in use], [r["fresh"] for r in use]),
    }


def cross_test(
    framing: Sequence[dict], sunk: Sequence[dict], unreliable: Sequence[str] = ()
) -> dict:
    """Spearman correlation across models between the fresh framing swing and the fresh sunk cost gap.

    `unreliable` lists framing results to leave out of the second (reliable-only) figure.
    """
    gap = {r["model"]: r["fresh"] for r in sunk}
    pairs = [(r["model"], r["fresh"], gap[r["model"]]) for r in framing if r["model"] in gap]

    def rho(keep: list[tuple[str, float, float]]) -> float:
        return spearman([p[1] for p in keep], [p[2] for p in keep])

    reliable = [p for p in pairs if p[0] not in unreliable]
    return {
        "n_all": len(pairs),
        "rho_all": rho(pairs),
        "n_reliable": len(reliable),
        "rho_reliable": rho(reliable),
    }


def _render_rows(
    rows: Sequence[dict], unit: str, digits: int, unreliable: Sequence[str]
) -> list[str]:
    lines = [
        f"{'model':18s} {'canon hi':>8s} {'canon lo':>8s} {'n hi/lo':>8s} {'canon':>8s} {'fresh':>8s} {'canon-fresh':>11s}",
    ]
    for r in rows:
        mark = "*" if r["model"] in unreliable else " "
        if not math.isfinite(r["canon"]):
            lines.append(f"{r['model']:18s}{mark}no canonical answers in this run")
            continue
        lines.append(
            f"{r['model']:18s}{mark}{r['canon_hi']:8.{digits}f} {r['canon_lo']:8.{digits}f} "
            f"{r['n_hi']:>3d}/{r['n_lo']:<4d} {r['canon']:+8.{digits}f} {r['fresh']:+8.{digits}f} {r['delta']:+11.{digits}f}"
        )
    lines.append(f"(units: {unit})")
    return lines


def _render_summary(label: str, s: dict, digits: int) -> str:
    return (
        f"{label}: {s['n']} models, mean canonical-minus-fresh {s['mean']:+.{digits}f} "
        f"[95% bootstrap over models {s['ci'][0]:+.{digits}f}, {s['ci'][1]:+.{digits}f}]; "
        f"canonical larger in {s['larger']}, smaller in {s['smaller']}, equal in {s['same']}; "
        f"Spearman rho canonical vs fresh {s['rho']:+.2f}"
    )


def _render_cross(c: dict) -> str:
    return (
        f"Spearman rho between a model's fresh framing swing and its fresh sunk cost gap: "
        f"{c['rho_all']:+.2f} over {c['n_all']} models, {c['rho_reliable']:+.2f} over the {c['n_reliable']} "
        "models whose framing result is not marked unreliable. Descriptive; 12 scenarios per test."
    )


def render(framing: Sequence[dict], sunk: Sequence[dict], unreliable: Sequence[str]) -> str:
    reliable = [r for r in framing if r["model"] not in unreliable]
    lines = [
        "CANONICAL WORDING VS FRESH SCENARIOS",
        "Canonical = one paraphrased textbook item per test (one scenario, a handful of answers per condition per model).",
        "Fresh = 12 scenarios written for this project. canonical hi/lo = share choosing the sure plan (framing, %) or",
        "mean rating (sunk cost); canon / fresh = swing (saved minus lost, points) or gap (paid minus free, rating points).",
        "Per-model canonical numbers are noisy and carry no interval. * = framing results marked unreliable in run 3",
        "(label-sensitive or position-biased). Canonical-minus-fresh above 0 means a stronger effect on the famous wording.",
        "",
        "FRAMING (run 3; pooled over both layouts and both label styles)",
        *_render_rows(framing, "percentage points", 0, unreliable),
        "",
        _render_summary("framing, all models with canonical answers", across_models(framing), 1),
        _render_summary("framing, reliable models only", across_models(reliable), 1),
        "",
        "SUNK COST (run 2; revised fresh scenarios)",
        *_render_rows(sunk, "rating points", 2, []),
        "",
        _render_summary("sunk cost, all models", across_models(sunk), 2),
        "",
        "DOES THE FRAMING SWING PREDICT THE SUNK COST GAP? (fresh scenarios, across models)",
        _render_cross(cross_test(framing, sunk, unreliable)),
    ]
    return "\n".join(lines)


def main() -> None:
    run3 = load(
        [str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]
    )
    earlier = load([str(DATA / "run1_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    flags = robust.analyze(run3, earlier)
    unreliable = [*flags["R3_format_sensitive"], *flags["R4_biased"]]
    run2 = load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    print(render(framing_rows(run3), sunk_rows(run2), unreliable))


if __name__ == "__main__":
    main()
