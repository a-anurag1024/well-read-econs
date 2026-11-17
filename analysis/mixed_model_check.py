"""Cross-check of the scenario-level estimates against a linear mixed model.

    pip install -e ".[stats]"
    python analysis/mixed_model_check.py        # -> analysis/results/item_level_mixed_check.txt

`wre.item_level` reports each model's effect as the mean of its 12 scenario differences, with a t interval
on the spread of those differences. In a balanced design that mean is the fixed effect of a linear mixed
model with a random intercept and a random condition slope for scenario. This script fits that model
(statsmodels MixedLM, REML) for every model and test and prints both standard errors side by side.

For framing there is a second fit that also includes the layout (sure plan first or second) and the label
style as fixed terms interacting with the wording. Within a scenario the layout and label style vary, so
the scenario-level mean averages them out; a mixed model that ignores them counts that variation as noise.

It is not part of `reproduce.py` because it needs statsmodels and pandas (not dependencies of the
package), and its numbers depend on those library versions. A fit can fail or land on a boundary when a
model answers the same way everywhere (for example GPT-6.1 Sol on framing); those rows say so.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import pandas as pd
import statsmodels
import statsmodels.formula.api as smf

from wre.item_level import scenario_diffs, summarize_diffs
from wre.part2 import _ok, load

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "results" / "item_level_mixed_check.txt"


def _frame(recs: list[dict], scale: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "y": float(r["parsed"]) * scale,
                "c": 1.0 if r["condition"] == "hi" else 0.0,
                "g": r["item_key"],
                "first": 0.5 if r.get("meta", {}).get("sure_first") else -0.5,
                "fmt": 0.5 if r.get("meta", {}).get("fmt") == "n" else -0.5,
            }
            for r in recs
            if _ok(r)
        ]
    )


def _fit(df: pd.DataFrame, formula: str) -> tuple[float, float] | None:
    """Fixed effect of the wording and its standard error, or None if the fit fails."""
    if df["y"].nunique() < 2:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = smf.mixedlm(formula, df, groups=df["g"], re_formula="~c").fit(
                reml=True, method="lbfgs"
            )
        return float(fit.params["c"]), float(fit.bse["c"])
    except Exception:  # noqa: BLE001  (a failed fit is reported, not raised)
        return None


def _cell(fit: tuple[float, float] | None, digits: int) -> str:
    if fit is None or not all(math.isfinite(x) for x in fit):
        return f"{'no fit':>{2 * digits + 11}s}"
    return f"{fit[0]:+8.{digits}f} (se {fit[1]:.{digits}f})"


def main() -> None:
    run3 = load(
        [str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]
    )
    run2 = load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    lines = [
        f"MIXED-MODEL CROSS-CHECK (statsmodels {statsmodels.__version__}; MixedLM, REML, random scenario intercept and slope)",
        "by-scenario = mean of the 12 scenario differences with se = sd / sqrt(12) (wre.item_level).",
        "mixed = fixed effect of the wording from the mixed model. mixed+layout adds layout and label style as fixed terms",
        "that interact with the wording (centred, so the wording effect is the average over both layouts and label styles).",
        "",
        "FRAMING SWING (percentage points)",
        f"{'model':18s} {'by-scenario':>20s} {'mixed':>22s} {'mixed+layout':>22s}",
    ]
    for m in dict.fromkeys(r["model"] for r in run3):
        recs = [
            r
            for r in run3
            if r["model"] == m and r["task"] == "framing" and r["version"] == "fresh"
        ]
        s = summarize_diffs(list(scenario_diffs(recs, 100).values()))
        base = f"{s['mean']:+8.1f} (se {s['sd'] / math.sqrt(s['k']):.1f})"
        df = _frame(recs, 100)
        lines.append(
            f"{m:18s} {base:>20s} {_cell(_fit(df, 'y ~ c'), 1):>22s} "
            f"{_cell(_fit(df, 'y ~ c * first + c * fmt'), 1):>22s}"
        )
    lines += [
        "",
        "SUNK COST GAP (rating points)",
        f"{'model':18s} {'by-scenario':>20s} {'mixed':>22s}",
    ]
    for m in dict.fromkeys(r["model"] for r in run2):
        recs = [
            r
            for r in run2
            if r["model"] == m
            and r["task"] == "sunkcost"
            and r["version"] == "fresh"
            and "-v11" in r["id"]
        ]
        s = summarize_diffs(list(scenario_diffs(recs).values()))
        base = f"{s['mean']:+8.2f} (se {s['sd'] / math.sqrt(s['k']):.2f})"
        lines.append(f"{m:18s} {base:>20s} {_cell(_fit(_frame(recs, 1.0), 'y ~ c'), 2):>22s}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
