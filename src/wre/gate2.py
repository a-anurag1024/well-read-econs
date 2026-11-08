"""Evaluate the pre-registered checks of run 2 (preregistration/run2-plan.md).

    python -m wre.gate2 --anthropic runs/gate2_anthropic.jsonl --openai-rerun runs/gate2_openai_rerun.jsonl \
        --gate1 runs/gate1.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report import render, summarize

FRONTIER_SUNK = ["gpt-6.1-sol", "gpt-6-astra", "claude-opus-5.5"]


def load(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def restrictive_rates(recs: list[dict]) -> dict[str, tuple[float, float]]:
    """P(restrictive) per model for fresh items: (allow wording, forbid wording)."""
    out: dict[str, tuple[float, float]] = {}
    for m in {r["model"] for r in recs}:
        rows = [r for r in recs if r["model"] == m and r["task"] == "forbid" and r["version"] == "fresh"
                and not r["err"] and r["parsed"] is not None]
        a = [r["parsed"] for r in rows if r["condition"] == "hi"]
        f = [r["parsed"] for r in rows if r["condition"] == "lo"]
        if a and f:
            out[m] = (sum(a) / len(a), sum(f) / len(f))
    return out


def check(anth: list[dict], rerun: list[dict], gate1: list[dict]) -> dict:
    allrecs = anth + rerun
    res_new = summarize(allrecs, n_boot=1500)
    res_old = summarize(gate1, n_boot=1500)
    out: dict = {}
    # G2a validity
    out["G2a_invalid"] = [(m, t) for m, tt in res_new.items() for t, v in tt.items()
                          if t != "_meta" and v["parse"] < 0.90]
    out["G2a_truncated"] = {m: tt["_meta"]["truncated"] for m, tt in res_new.items() if tt["_meta"]["truncated"]}
    # G2b forbid discriminates
    rates = restrictive_rates(allrecs)
    mid = [m for m, (a, f) in rates.items() if (0.05 <= a <= 0.95) or (0.05 <= f <= 0.95)]
    out["G2b_models_not_at_floor"] = f"{len(mid)} of {len(rates)}"
    out["G2b_pass"] = len(mid) >= 8
    out["G2b_rates"] = {m: (round(a, 2), round(f, 2)) for m, (a, f) in sorted(rates.items())}
    # G2c sunk-cost wording
    g2c = {}
    for m in FRONTIER_SUNK:
        new = res_new.get(m, {}).get("sunkcost", {})
        old = res_old.get(m, {}).get("sunkcost", {})
        if "fresh" in new:
            lo, hi = new["fresh_ci"]
            verdict = ("artifact" if (new["fresh"] < 0.15 or lo <= 0)
                       else "paid-vs-free sensitivity (not bias)")
            g2c[m] = {"v1.1": round(new["fresh"], 2), "ci": (round(lo, 2), round(hi, 2)),
                      "v1": round(old["fresh"], 2) if "fresh" in old else None, "reading": verdict}
    out["G2c"] = g2c
    # G2d frontier framing across vendors
    g2d = {}
    for m in ("gpt-6.1-sol", "gpt-6-astra", "claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-4.5"):
        v = res_new.get(m, {}).get("framing") or res_old.get(m, {}).get("framing")
        if v and "fresh" in v:
            g2d[m] = (round(v["fresh"], 2), tuple(round(x, 2) for x in v["fresh_ci"]))
    out["G2d_framing"] = g2d
    out["_res_new"] = res_new
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="wre.gate2")
    ap.add_argument("--anthropic", required=True)
    ap.add_argument("--openai-rerun", required=True)
    ap.add_argument("--gate1", required=True)
    a = ap.parse_args(argv)
    out = check(load(a.anthropic), load(a.openai_rerun), load(a.gate1))
    print(render(out.pop("_res_new")))
    print("\nGATE 2 CHECKS")
    for k, v in out.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
