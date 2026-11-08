"""Evaluate the Part 2 rules (preregistration/run4-prompting-plan.md): what do one-line instructions do?

    python -m wre.part2 --results runs/part2.jsonl \
        --baseline-framing runs/robust_openai.jsonl runs/robust_anthropic.jsonl \
        --baseline-sunk runs/gate2_openai_rerun.jsonl runs/gate2_anthropic.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from .effects import cluster_bootstrap, effect_d
from .human_reference import HUMAN
from .tasks.base import first_letter

HUMAN_FRAMING = HUMAN["framing"].own_d
HUMAN_SUNK = HUMAN["sunkcost"].own_d
ANCHORS = ["gpt-6.1-sol", "gpt-6-astra", "claude-sonnet-5.5", "claude-opus-5.5"]
EXTRAS = ["gpt-4o", "gpt-4.1", "gpt-5-mini"]
HUMAN_PROMPTS = ("typical", "gut")


def load(paths: list[str]) -> list[dict]:
    out: list[dict] = []
    for p in paths:
        out.extend(json.loads(line) for line in Path(p).read_text(encoding="utf-8").splitlines())
    return out


def band(d: float, valid: bool = True) -> str:
    """Framing-d band from the rules: reversed / Econ / weak / human-sized / exaggerated."""
    if not valid or math.isnan(d):
        return "invalid"
    if d < -0.15:
        return "reversed"
    if d < 0.15:
        return "Econ"
    if d < 0.36:
        return "weak"
    return "human-sized" if d <= 1.42 else "exaggerated"


def _ok(r: dict) -> bool:
    return not r.get("err") and r.get("parsed") is not None


def _label(r: dict) -> str | None:
    if r["meta"].get("fmt") == "n":
        m = re.search(r"(?<!\d)([12])(?!\d)", r["text"])
        return m.group(1) if m else None
    return first_letter(r["text"], "AB")


def framing_cell(recs: list[dict], n_boot: int = 2000) -> dict:
    """Framing statistics for one (model, instruction) cell of fresh prompts."""
    ok = [r for r in recs if _ok(r)]
    rows = [(r["item_key"], r["condition"], float(r["parsed"])) for r in ok]
    d = effect_d(rows, "binary") if rows else float("nan")
    ci = cluster_bootstrap(rows, "binary", n_boot, 0.90, seed=3) if rows else (float("nan"),) * 2

    def p_certain(cond: str) -> float:
        v = [r["parsed"] for r in ok if r["condition"] == cond]
        return sum(v) / len(v) if v else float("nan")

    first = [1.0 if (r["parsed"] == 1.0) == r["meta"]["sure_first"] else 0.0 for r in ok]
    first_share = sum(first) / len(first) if first else float("nan")
    biased = first_share >= 0.95 or first_share <= 0.05
    for fmt in ("ab", "n"):
        labs = [_label(r) for r in ok if r["meta"].get("fmt") == fmt]
        labs = [x for x in labs if x]
        if labs and max(labs.count(x) for x in set(labs)) / len(labs) >= 0.95:
            biased = True
    parse = len(ok) / len(recs) if recs else 0.0
    valid = bool(recs) and parse >= 0.90 and not biased
    return {
        "d": d,
        "ci": ci,
        "gain": p_certain("hi"),
        "loss": p_certain("lo"),
        "first": first_share,
        "parse": parse,
        "biased": biased,
        "valid": valid,
        "band": band(d, valid),
        "n": len(recs),
        "out_tok": sum(r["out_tok"] for r in recs) / len(recs) if recs else float("nan"),
    }


def sunk_cell(recs: list[dict], n_boot: int = 2000) -> dict:
    rows = [(r["item_key"], r["condition"], float(r["parsed"])) for r in recs if _ok(r)]
    if not rows:
        return {"d": float("nan"), "ci": (float("nan"),) * 2, "n": 0}
    return {
        "d": effect_d(rows, "continuous"),
        "ci": cluster_bootstrap(rows, "continuous", n_boot, 0.90, seed=3),
        "n": len(rows),
    }


def anchor_status(cells: dict) -> str:
    """C1 for one model: calibrated / partly / immovable / still exaggerated / mixed."""
    bands = [cells[p]["band"] for p in HUMAN_PROMPTS]
    n_human = bands.count("human-sized")
    if n_human == 2:
        return "calibrated"
    if n_human == 1:
        return "partly"
    if all(b in ("reversed", "Econ", "weak") for b in bands):
        return "immovable"
    if all(b == "exaggerated" for b in bands):
        return "still exaggerated"
    return "mixed"


def verdict(statuses: dict[str, str]) -> str:
    n = sum(1 for s in statuses.values() if s == "calibrated")
    if n == len(statuses):
        return "PROMPTING CALIBRATES"
    return "PROMPTING CALIBRATES SOME" if n else "PROMPTING DOES NOT CALIBRATE"


def analyze(
    results: list[dict], base_framing: list[dict], base_sunk: list[dict], n_boot: int = 2000
) -> dict:
    models = [m for m in ANCHORS + EXTRAS if any(r["model"] == m for r in results)]
    out: dict = {"cells": {}, "sunk": {}}
    for m in models:
        fr = {
            "none": framing_cell(
                [
                    r
                    for r in base_framing
                    if r["model"] == m and r["task"] == "framing" and r["version"] == "fresh"
                ],
                n_boot,
            )
        }
        su = {
            "none": sunk_cell(
                [
                    r
                    for r in base_sunk
                    if r["model"] == m
                    and r["task"] == "sunkcost"
                    and r["version"] == "fresh"
                    and "-v11" in r["id"]
                ],
                n_boot,
            )
        }
        for p in ("typical", "gut", "rational"):
            mine = [r for r in results if r["model"] == m and r["meta"].get("persona") == p]
            fr[p] = framing_cell([r for r in mine if r["task"] == "framing"], n_boot)
            su[p] = sunk_cell([r for r in mine if r["task"] == "sunkcost"], n_boot)
        out["cells"][m], out["sunk"][m] = fr, su
    c = out["cells"]
    out["C1"] = {m: anchor_status(c[m]) for m in ANCHORS if m in c}
    out["C2_overshoot"] = [
        (m, p)
        for m in c
        for p in HUMAN_PROMPTS
        if c[m]["none"]["d"] <= 1.42 and c[m][p]["valid"] and c[m][p]["d"] > 1.42
    ]
    out["C3_steers_to_econ"] = {
        m: bool(c[m]["rational"]["valid"] and c[m]["rational"]["d"] < 0.15)
        for m in c
        if m not in ("gpt-6.1-sol", "gpt-6-astra") and c[m]["none"]["d"] >= 0.36
    }
    out["C4_wording_agrees"] = {m: c[m]["typical"]["band"] == c[m]["gut"]["band"] for m in c}
    out["verdict"] = (
        verdict(out["C1"]) if len(out["C1"]) == len(ANCHORS) else "INCOMPLETE (anchor missing)"
    )
    out["sunk_sign_matches"] = {
        m: {
            p: (
                (out["sunk"][m][p]["d"] - out["sunk"][m]["none"]["d"])
                * (c[m][p]["d"] - c[m]["none"]["d"])
                > 0
            )
            for p in ("typical", "gut", "rational")
        }
        for m in c
    }
    return out


def render(out: dict) -> str:
    header = (
        f"{'model':18s} {'prompt':9s} {'framing d [90% CI]':24s} {'band':12s} {'gain/loss':>10s} "
        f"{'first':>6s} {'parse':>6s} {'tok':>5s}  sunk d [90% CI]"
    )
    lines = [f"human framing d = {HUMAN_FRAMING:.2f}; sunk cost d = {HUMAN_SUNK:.2f}", header]
    for m, cells in out["cells"].items():
        for p in ("none", "typical", "gut", "rational"):
            x, s = cells[p], out["sunk"][m][p]
            lines.append(
                f"{m:18s} {p:9s} {x['d']:+6.2f} [{x['ci'][0]:+.2f},{x['ci'][1]:+.2f}]".ljust(54)
                + f"{x['band']:12s} {x['gain']:.2f}/{x['loss']:.2f}  {x['first']:6.2f} {x['parse']:6.2f} "
                f"{x['out_tok']:5.0f}  {s['d']:+.2f} [{s['ci'][0]:+.2f},{s['ci'][1]:+.2f}]"
            )
    lines += [
        "",
        f"C1 anchors: {out['C1']}",
        f"C2 overshoot (model, prompt): {out['C2_overshoot']}",
        f"C3 rational steers to Econ: {out['C3_steers_to_econ']}",
        f"C4 typical and gut in the same band: {out['C4_wording_agrees']}",
        f"verdict: {out['verdict']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="wre.part2")
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--baseline-framing", nargs="+", required=True)
    ap.add_argument("--baseline-sunk", nargs="+", required=True)
    a = ap.parse_args(argv)
    print(render(analyze(load(a.results), load(a.baseline_framing), load(a.baseline_sunk))))


if __name__ == "__main__":
    main()
