"""Item-level intervals for the framing swing and the sunk cost gap, in the units people report.

The scenario (not the sampled answer) is the unit of replication. For each model, every scenario gives one
difference between its two conditions (framing: saved minus lost share, in percentage points; sunk cost:
paid minus free rating, in rating points). The model's effect is the mean of those scenario differences.

With the same 12 scenarios in every condition and cell, the mean of the scenario differences is the
estimate of a model with a random intercept and a random condition slope for scenario, and its standard
error is the standard deviation of the differences divided by the square root of the number of scenarios.
The intervals here are therefore the item-random-effects intervals, with Student's t on (scenarios - 1)
degrees of freedom; a scenario-level percentile bootstrap is shown beside them. Nothing here needs a
statistics library.

    python -m wre.item_level

Layout and label style are crossed by scenario in run 3: within a scenario, the sure plan is listed first
under one label style and second under the other, and the two label styles swap roles in odd and even
scenarios. The layout effect and the label effect are estimated from that structure (see `layout_label`).

Models that answer identically in every scenario (for example GPT-6.1 Sol on framing) have zero
between-scenario spread, so their interval is a single point and says nothing about uncertainty.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from statistics import fmean, variance

from .part2 import ANCHORS, _ok, framing_cell, load
from .sunk_gaps import HUMAN_FREE, HUMAN_PAID

DATA = Path(__file__).resolve().parents[2] / "data"
HUMAN_SWING = 65.5 - 34.5  # Many Labs 1 (see human_reference.py), percentage points
HUMAN_GAP = HUMAN_PAID - HUMAN_FREE  # Many Labs 1, rating points
PROMPTS = ("none", "typical", "gut", "rational")

# Two-sided 95% critical values of Student's t, degrees of freedom 1 to 30.
_T975 = (
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
)  # fmt: skip
NAN = float("nan")


def t_crit(df: float) -> float:
    """97.5th percentile of Student's t. Non-integer df are rounded down (slightly wider interval)."""
    if not math.isfinite(df) or df < 1:
        return NAN
    return _T975[int(df) - 1] if df < 31 else 1.96


def _span(estimate: float, se: float, df: float) -> tuple[float, float]:
    if se == 0:
        return estimate, estimate
    half = t_crit(df) * se
    return estimate - half, estimate + half


def boot_interval(
    diffs: Sequence[float], n_boot: int = 2000, level: float = 0.95, seed: int = 0
) -> tuple[float, float]:
    """Percentile interval for the mean of scenario differences, resampling scenarios."""
    if len(diffs) < 2:
        return NAN, NAN
    rng = random.Random(seed)
    k = len(diffs)
    means = sorted(fmean(rng.choices(diffs, k=k)) for _ in range(n_boot))
    lo = int(((1 - level) / 2) * n_boot)
    hi = min(n_boot - 1, int((1 - (1 - level) / 2) * n_boot))
    return means[lo], means[hi]


def summarize_diffs(diffs: Sequence[float], seed: int = 0) -> dict:
    """Mean, between-scenario SD, 95% t interval, 95% bootstrap interval and up/down counts."""
    k = len(diffs)
    if k == 0:
        return {
            "mean": NAN,
            "sd": NAN,
            "k": 0,
            "t_ci": (NAN, NAN),
            "boot_ci": (NAN, NAN),
            "up": 0,
            "down": 0,
        }
    m = fmean(diffs)
    sd = math.sqrt(variance(diffs)) if k > 1 else NAN
    t_ci = _span(m, sd / math.sqrt(k), k - 1) if k > 1 else (NAN, NAN)
    return {
        "mean": m,
        "sd": sd,
        "k": k,
        "t_ci": t_ci,
        "boot_ci": boot_interval(diffs, seed=seed),
        "up": sum(d > 0 for d in diffs),
        "down": sum(d < 0 for d in diffs),
    }


def scenario_diffs(recs: Sequence[dict], scale: float = 1.0) -> dict[str, float]:
    """{scenario: (mean of hi answers - mean of lo answers) * scale}, for scenarios scored in both conditions."""
    cells: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"hi": [], "lo": []})
    for r in recs:
        if _ok(r):
            cells[r["item_key"]][r["condition"]].append(float(r["parsed"]))
    return {
        k: (fmean(v["hi"]) - fmean(v["lo"])) * scale
        for k, v in sorted(cells.items())
        if v["hi"] and v["lo"]
    }


def includes(ci: tuple[float, float], value: float) -> bool:
    """True when the interval contains the value (a degenerate interval contains it only if equal)."""
    return math.isfinite(ci[0]) and ci[0] <= value <= ci[1]


def _welch(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Standard error of (mean(a) - mean(b)) and Welch degrees of freedom."""
    if len(a) < 2 or len(b) < 2:
        return NAN, NAN
    va, vb = variance(a) / len(a), variance(b) / len(b)
    se = math.sqrt(va + vb)
    if se == 0:
        return 0.0, NAN
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    return se, df


def layout_label(recs: Sequence[dict]) -> dict:
    """Layout effect (swing with the sure plan second minus first) and label effect (numbers minus letters).

    In each scenario one label style carries the sure-first layout and the other carries sure-second, and
    the two styles swap roles between scenarios. For a scenario where letters are first,
    contrast = second - first = layout + label; where numbers are first, contrast = layout - label.
    So layout = (mean_A + mean_B) / 2 and label = (mean_A - mean_B) / 2, where A and B are the two groups
    of scenarios. Assumes layout and label effects add up (no interaction).
    """
    first = scenario_diffs([r for r in recs if r["meta"]["sure_first"]], 100)
    second = scenario_diffs([r for r in recs if not r["meta"]["sure_first"]], 100)
    letters_first = {
        r["item_key"] for r in recs if r["meta"]["sure_first"] and r["meta"]["fmt"] == "ab"
    }
    grp_a = [second[k] - first[k] for k in first if k in second and k in letters_first]
    grp_b = [second[k] - first[k] for k in first if k in second and k not in letters_first]
    if len(grp_a) < 2 or len(grp_b) < 2:
        nan2 = {"est": NAN, "ci": (NAN, NAN)}
        return {"layout": nan2, "label": nan2, "n_a": len(grp_a), "n_b": len(grp_b)}
    se, df = _welch(grp_a, grp_b)
    se /= 2  # both effects are half of a sum or difference of the two group means
    layout = (fmean(grp_a) + fmean(grp_b)) / 2
    label = (fmean(grp_a) - fmean(grp_b)) / 2
    return {
        "layout": {"est": layout, "ci": _span(layout, se, df)},
        "label": {"est": label, "ci": _span(label, se, df)},
        "n_a": len(grp_a),
        "n_b": len(grp_b),
    }


def framing(recs: Sequence[dict]) -> dict[str, dict]:
    """{model: {pooled, first, second, layout, label}} from run 3 fresh scenarios, in percentage points."""
    fresh = [r for r in recs if r["task"] == "framing" and r["version"] == "fresh"]
    out: dict[str, dict] = {}
    for m in dict.fromkeys(r["model"] for r in fresh):
        mine = [r for r in fresh if r["model"] == m]
        out[m] = {
            "pooled": summarize_diffs(list(scenario_diffs(mine, 100).values())),
            "first": summarize_diffs(
                list(scenario_diffs([r for r in mine if r["meta"]["sure_first"]], 100).values())
            ),
            "second": summarize_diffs(
                list(scenario_diffs([r for r in mine if not r["meta"]["sure_first"]], 100).values())
            ),
            **layout_label(mine),
        }
    return out


def sunk_cost(recs: Sequence[dict]) -> dict[str, dict]:
    """{model: summary} of paid-minus-free scenario gaps, run 2 revised ("v11") fresh scenarios."""
    fresh = [
        r for r in recs if r["task"] == "sunkcost" and r["version"] == "fresh" and "-v11" in r["id"]
    ]
    return {
        m: summarize_diffs(list(scenario_diffs([r for r in fresh if r["model"] == m]).values()))
        for m in dict.fromkeys(r["model"] for r in fresh)
    }


def prompting(
    run4: Sequence[dict], base_framing: Sequence[dict], base_sunk: Sequence[dict]
) -> dict:
    """{model: {"framing": {prompt: cell}, "sunk": {prompt: cell}}} for the four anchor models.

    "none" comes from run 3 (framing) and run 2 (sunk cost); the other arms from run 4. A framing cell
    carries `valid` (the run's own reliability rule); a sunk cost cell carries `unscored`.
    """
    out: dict[str, dict] = {}
    for m in (a for a in ANCHORS if any(r["model"] == a for r in run4)):
        fr = {
            "none": _cell(
                [
                    r
                    for r in base_framing
                    if r["model"] == m and r["task"] == "framing" and r["version"] == "fresh"
                ],
                100,
                framing_check=True,
            )
        }
        su = {
            "none": _cell(
                [
                    r
                    for r in base_sunk
                    if r["model"] == m
                    and r["task"] == "sunkcost"
                    and r["version"] == "fresh"
                    and "-v11" in r["id"]
                ],
                1.0,
            )
        }
        for p in PROMPTS[1:]:
            fr[p] = _cell(
                [
                    r
                    for r in run4
                    if r["model"] == m and r["task"] == "framing" and r["meta"].get("persona") == p
                ],
                100,
                framing_check=True,
            )
            su[p] = _cell(
                [
                    r
                    for r in run4
                    if r["model"] == m and r["task"] == "sunkcost" and r["meta"].get("persona") == p
                ],
                1.0,
            )
        out[m] = {"framing": fr, "sunk": su}
    return out


def _cell(recs: Sequence[dict], scale: float, framing_check: bool = False) -> dict:
    cell = summarize_diffs(list(scenario_diffs(recs, scale).values()))
    cell["unscored"] = sum(1 for r in recs if not _ok(r))
    cell["valid"] = framing_cell(list(recs), n_boot=1)["valid"] if framing_check and recs else True
    return cell


def _fmt_ci(ci: tuple[float, float], digits: int = 0) -> str:
    if not math.isfinite(ci[0]):
        return "n/a"
    return f"[{ci[0]:+.{digits}f}, {ci[1]:+.{digits}f}]"


def render_framing(out: dict[str, dict]) -> str:
    lines = [
        "FRAMING SWING WITH SCENARIO-LEVEL INTERVALS (run 3, fresh scenarios, percentage points)",
        f"people (Many Labs 1): swing {HUMAN_SWING:.0f}. Swing = share choosing the sure plan under the saved wording",
        "minus under the lost wording. Estimate = mean of the 12 scenario swings; sd = spread of the swings between",
        "scenarios; t95 = Student's t interval on 11 degrees of freedom (the item-random-effects interval); boot95 =",
        "percentile bootstrap over scenarios. 'human?' says whether the t interval contains 31. A zero sd gives a",
        "single-point interval that carries no information about uncertainty.",
        "",
        f"{'model':18s} {'swing':>6s} {'sd':>5s}  {'t95':>14s}  {'boot95':>14s}  {'up/down':>7s}  human?",
    ]
    for m, c in out.items():
        p = c["pooled"]
        lines.append(
            f"{m:18s} {p['mean']:6.1f} {p['sd']:5.1f}  {_fmt_ci(p['t_ci']):>14s}  {_fmt_ci(p['boot_ci']):>14s}  "
            f"{p['up']:>3d}/{p['down']:<3d}  {'yes' if includes(p['t_ci'], HUMAN_SWING) else 'no'}"
        )
    lines += [
        "",
        "LAYOUT AND LABEL EFFECTS ON THE SWING (percentage points)",
        "layout = swing with the sure plan listed second minus listed first; label = swing under 'Option 1 / Option 2'",
        "minus under 'Plan A / Plan B'. Both come from the crossed design (see wre/item_level.py), 6 + 6 scenarios.",
        "A layout interval that excludes 0 means the swing depends on where the sure plan is listed.",
        "",
        f"{'model':18s} {'sure first':>10s} {'sure second':>11s}  {'layout effect':>13s}  {'t95':>14s}  {'label effect':>12s}  {'t95':>14s}",
    ]
    for m, c in out.items():
        lines.append(
            f"{m:18s} {c['first']['mean']:10.1f} {c['second']['mean']:11.1f}  {c['layout']['est']:13.1f}  "
            f"{_fmt_ci(c['layout']['ci']):>14s}  {c['label']['est']:12.1f}  {_fmt_ci(c['label']['ci']):>14s}"
        )
    return "\n".join(lines)


def render_sunk(out: dict[str, dict]) -> str:
    lines = [
        "SUNK COST GAP WITH SCENARIO-LEVEL INTERVALS (run 2, revised fresh scenarios, rating points)",
        f"people (Many Labs 1): gap {HUMAN_GAP:+.2f}. Gap = mean rating with a paid ticket minus with a free ticket.",
        "Estimate = mean of the 12 scenario gaps; sd = spread of the gaps between scenarios; t95 and boot95 as above.",
        "'human?' says whether the t interval contains +0.61.",
        "",
        f"{'model':18s} {'gap':>6s} {'sd':>5s}  {'t95':>16s}  {'boot95':>16s}  {'up/down':>7s}  human?",
    ]
    for m, p in out.items():
        lines.append(
            f"{m:18s} {p['mean']:+6.2f} {p['sd']:5.2f}  {_fmt_ci(p['t_ci'], 2):>16s}  {_fmt_ci(p['boot_ci'], 2):>16s}  "
            f"{p['up']:>3d}/{p['down']:<3d}  {'yes' if includes(p['t_ci'], HUMAN_GAP) else 'no'}"
        )
    return "\n".join(lines)


def render_prompting(out: dict) -> str:
    lines = [
        "EFFECT UNDER EACH ONE-LINE INSTRUCTION WITH SCENARIO-LEVEL INTERVALS (four anchor models)",
        "Framing: swing in percentage points ('none' from run 3). Sunk cost: gap in rating points ('none' from run 2).",
        "Each cell is the mean of the scenario differences with its 95% t interval; k = scenarios scored in both",
        "conditions. Run 4 has one answer per prompt (two for gpt-6.1-sol), so a cell's interval mixes scenario",
        "spread with answer noise. '!' = the run's reliability rule failed (framing) or answers could not be scored.",
        "",
    ]
    for test, scale_digits in (("framing", 0), ("sunk", 2)):
        lines.append("FRAMING SWING" if test == "framing" else "SUNK COST GAP")
        lines.append(f"{'model':18s} " + " ".join(f"{p:>26s}" for p in PROMPTS))
        for m, cells in out.items():
            parts = []
            for p in PROMPTS:
                c = cells[test][p]
                flag = "!" if (not c["valid"] or c["unscored"]) else ""
                mean_txt = f"{c['mean']:+.{scale_digits}f}" if math.isfinite(c["mean"]) else "n/a"
                parts.append(
                    f"{mean_txt} {_fmt_ci(c['t_ci'], scale_digits)} k={c['k']}{flag}".rjust(26)
                )
            lines.append(f"{m:18s} " + " ".join(parts))
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    run3 = load(
        [str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]
    )
    run2 = load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    run4 = load([str(DATA / "run4_prompting.jsonl")])
    print(render_framing(framing(run3)))
    print()
    print(render_sunk(sunk_cost(run2)))
    print()
    print(render_prompting(prompting(run4, run3, run2)))


if __name__ == "__main__":
    main()
