"""Evaluate the framing robustness rules (preregistration/run3-framing-plan.md).

    python -m wre.robust --results runs/robust_openai.jsonl runs/robust_anthropic.jsonl \
        --earlier runs/gate1.jsonl runs/gate2_anthropic.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .effects import cluster_bootstrap, effect_d
from .human_reference import HUMAN
from .report import spearman

HUMAN_D = HUMAN["framing"].own_d


def load(paths: list[str]) -> list[dict]:
    out: list[dict] = []
    for p in paths:
        out.extend(json.loads(line) for line in Path(p).read_text(encoding="utf-8").splitlines())
    return out


def _rows(recs, model, fmt=None):
    return [(r["item_key"], r["condition"], float(r["parsed"])) for r in recs
            if r["model"] == model and r["task"] == "framing" and r["version"] == "fresh"
            and not r["err"] and r.get("parsed") is not None
            and (fmt is None or r["meta"].get("fmt") == fmt)]


def p_certain(recs, model, cond):
    v = [r["parsed"] for r in recs if r["model"] == model and r["version"] == "fresh" and r["condition"] == cond
         and not r["err"] and r.get("parsed") is not None]
    return sum(v) / len(v) if v else float("nan")


def position_shares(recs, model):
    """Share of answers choosing the FIRST-listed option; and max single-label share per format."""
    out = {}
    rows = [r for r in recs if r["model"] == model and r["version"] == "fresh" and not r["err"] and r.get("parsed") is not None]
    chose_first = []
    for r in rows:
        sure_first = r["meta"]["sure_first"]
        chose_sure = r["parsed"] == 1.0
        chose_first.append(1.0 if chose_sure == sure_first else 0.0)
    out["first"] = sum(chose_first) / len(chose_first) if chose_first else float("nan")
    for fmt in ("ab", "n"):
        sel = [r for r in rows if r["meta"].get("fmt") == fmt]
        labels: dict[str, int] = {}
        for r in sel:
            t = r["text"].strip().upper()[:1]
            labels[t] = labels.get(t, 0) + 1
        n = sum(labels.values())
        out["max_label_" + fmt] = max(labels.values()) / n if n else float("nan")
    return out


def analyze(recs: list[dict], earlier: list[dict], n_boot: int = 2000) -> dict:
    models = list(dict.fromkeys(r["model"] for r in recs))
    res: dict = {}
    for m in models:
        allr = _rows(recs, m)
        d = effect_d(allr, "binary")
        lo, hi = cluster_bootstrap(allr, "binary", n_boot, 0.90, seed=3)
        da = effect_d(_rows(recs, m, "ab"), "binary")
        dn = effect_d(_rows(recs, m, "n"), "binary")
        ps = position_shares(recs, m)
        parse = sum(1 for r in recs if r["model"] == m and not r["err"] and r.get("parsed") is not None) / \
            max(1, sum(1 for r in recs if r["model"] == m))
        biased = (ps["first"] >= 0.95 or ps["first"] <= 0.05 or ps["max_label_ab"] >= 0.95 or ps["max_label_n"] >= 0.95)
        res[m] = {"d": d, "ci": (lo, hi), "d_ab": da, "d_n": dn, "gain": p_certain(recs, m, "hi"),
                  "loss": p_certain(recs, m, "lo"), "first": ps["first"], "parse": parse, "biased": biased,
                  "format_robust": (abs(da - dn) <= 0.6) if math.isfinite(da) and math.isfinite(dn) else None,
                  "order": next(r["order"] for r in recs if r["model"] == m)}
    out: dict = {"res": res}
    r1 = {m: (m in res and res[m]["d"] < 0.15 and res[m]["gain"] >= 0.9 and res[m]["loss"] >= 0.9)
          for m in ("gpt-6.1-sol", "gpt-6-astra")}
    r2 = {m: (m in res and res[m]["d"] >= 1.0 and res[m]["d_ab"] >= 1.0 and res[m]["d_n"] >= 1.0)
          for m in ("claude-sonnet-5.5", "claude-opus-5.5")}
    out["R1"], out["R2"] = r1, r2
    out["R3_format_sensitive"] = [m for m, v in res.items() if v["format_robust"] is False]
    out["R4_biased"] = [m for m, v in res.items() if v["biased"]]
    out["R0_invalid"] = [m for m, v in res.items() if v["parse"] < 0.90]
    if all(r1.values()) and all(r2.values()):
        out["verdict"] = "HEADLINE FIRM"
    elif all(r1.values()):
        out["verdict"] = "HEADLINE PARTIAL (Claude exaggeration is format-dependent)"
    else:
        out["verdict"] = "HEADLINE NOT SUPPORTED (Econ pattern failed for at least one of Sol, Astra)"
    # informational: stability of the cross-model ordering versus the framing d of runs 1 and 2
    from .report import summarize
    old = summarize([r for r in earlier if r["task"] == "framing"], n_boot=300)
    common = [m for m in res if m in old and "framing" in old[m] and "fresh" in old[m]["framing"]]
    if len(common) >= 5:
        out["spearman_vs_earlier"] = spearman([old[m]["framing"]["fresh"] for m in common],
                                              [res[m]["d"] for m in common])
        out["n_models_compared"] = len(common)
    out["_old"] = {m: old[m]["framing"]["fresh"] for m in common}
    return out


def render(out: dict) -> str:
    lines = [f"human framing d = {HUMAN_D:.2f}; certain option 0.66 (gain) / 0.35 (loss)",
             f"{'model':18s} {'d [90% CI]':22s} {'d A/B':>7s} {'d 1/2':>7s} {'P(cert) gain/loss':>18s} {'first-listed':>12s}  earlier d  flags"]
    old = out.get("_old", {})
    for m, v in sorted(out["res"].items(), key=lambda kv: kv[1]["order"]):
        flags = []
        if v["biased"]:
            flags.append("BIASED")
        if v["format_robust"] is False:
            flags.append("format-sensitive")
        if v["parse"] < 0.9:
            flags.append("parse<90%")
        o = old.get(m)
        lines.append(f"{m:18s} {v['d']:+.2f} [{v['ci'][0]:+.2f},{v['ci'][1]:+.2f}]".ljust(41) +
                     f" {v['d_ab']:+7.2f} {v['d_n']:+7.2f} {v['gain']:.2f} / {v['loss']:.2f}".ljust(31) +
                     f" {v['first']:.2f}".ljust(14) + (f" {o:+.2f}" if o is not None else "    n/a") + "  " + ",".join(flags))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="wre.robust")
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--earlier", nargs="+", required=True)
    a = ap.parse_args(argv)
    out = analyze(load(a.results), load(a.earlier))
    print(render(out))
    print()
    for k in ("R0_invalid", "R1", "R2", "R3_format_sensitive", "R4_biased", "spearman_vs_earlier",
              "n_models_compared", "verdict"):
        if k in out:
            print(f"{k}: {out[k]}")


if __name__ == "__main__":
    main()
