"""Regenerate every table in analysis/results/ from data/.

    python analysis/reproduce.py

Nothing here calls a model API. Bootstrap intervals use fixed seeds, so the output is
reproducible byte for byte on the same Python and library versions.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from wre import diagnostics, gate2, part2, robust
from wre.report import gate1 as run1_checks
from wre.report import render, summarize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "results"


def run1() -> str:
    res = summarize(part2.load([str(DATA / "run1_openai.jsonl")]))
    lines = [render(res), "", "STOP/CONTINUE CHECKS (run 1 plan)"]
    lines += [f"  {k}: {v}" for k, v in run1_checks(res).items()]
    return "\n".join(lines)


def run2() -> str:
    out = gate2.check(
        gate2.load(str(DATA / "run2_anthropic.jsonl")),
        gate2.load(str(DATA / "run2_openai.jsonl")),
        gate2.load(str(DATA / "run1_openai.jsonl")),
    )
    lines = [render(out.pop("_res_new")), "", "RUN 2 CHECKS"]
    lines += [f"  {k}: {v}" for k, v in out.items()]
    lines += [
        "",
        "ALLOWED/FORBIDDEN RESPONSE STYLE (v1.1 items, all 16 models)",
        "  acquiescence = P(yes|allow) + P(yes|forbid) - 1; humans (Many Labs): 0.763 + 0.072 - 1 = -0.17",
        f"  {'model':20s} {'P(yes|allow)':>13s} {'P(yes|forbid)':>14s} {'acquiescence':>13s} {'unparsed':>9s}",
    ]
    recs = gate2.load(str(DATA / "run2_openai.jsonl")) + gate2.load(str(DATA / "run2_anthropic.jsonl"))
    for m in dict.fromkeys(r["model"] for r in recs):
        y = diagnostics.yes_bias(recs, m)
        lines.append(
            f"  {m:20s} {y['p_yes_allow']:13.2f} {y['p_yes_forbid']:14.2f} "
            f"{y['acquiescence']:+13.2f} {y['unparsed']:9.2f}"
        )
    return "\n".join(lines)


def run3() -> str:
    recs = part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    earlier = part2.load([str(DATA / "run1_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    out = robust.analyze(recs, earlier)
    lines = [robust.render(out), ""]
    for k in (
        "R0_invalid",
        "R1",
        "R2",
        "R3_format_sensitive",
        "R4_biased",
        "spearman_vs_earlier",
        "n_models_compared",
        "verdict",
    ):
        if k in out:
            lines.append(f"{k}: {out[k]}")
    return "\n".join(lines)


def run4() -> str:
    out = part2.analyze(
        part2.load([str(DATA / "run4_prompting.jsonl")]),
        part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]),
        part2.load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]),
    )
    return part2.render(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (
        ("run1_openai", run1),
        ("run2_anthropic_and_rerun", run2),
        ("run3_framing_robustness", run3),
        ("run4_prompting", run4),
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            text = fn()
        (OUT / f"{name}.txt").write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"wrote analysis/results/{name}.txt")


if __name__ == "__main__":
    main()
