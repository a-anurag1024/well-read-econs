"""Summarize run results: per-model, per-task effects against the human reference.

    python -m wre.report runs/gate1.jsonl [--gate1]

--gate1 also evaluates the pre-registered stop/continue rules of run 1 (preregistration/run1-plan.md).
Effects are Cohen's d (hi minus lo condition) with 90% item-level bootstrap intervals.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .effects import cluster_bootstrap, effect_d, proportion_gap, within_item_rank_z
from .human_reference import HUMAN
from .tasks import TASKS


def _rows(recs: list[dict], task: str, version: str):
    t = TASKS[task]
    out = []
    for r in recs:
        if r["task"] != task or r["version"] != version or r.get("err") or r.get("parsed") is None:
            continue
        out.append((r["item_key"], r["condition"], float(r["parsed"])))
    if task == "anchoring":
        out = within_item_rank_z(out)
    return out, t.outcome_kind


def summarize(recs: list[dict], n_boot: int = 1500) -> dict:
    """Return {model: {task: {...}}} with effects, CIs, parse rates and cost."""
    models = []
    for r in recs:
        if r["model"] not in models:
            models.append(r["model"])
    res: dict = {}
    for m in models:
        mr = [r for r in recs if r["model"] == m]
        res[m] = {"_meta": {"order": mr[0]["order"], "tier": mr[0]["tier"],
                            "cost": sum(r["cost"] for r in mr),
                            "out_tok": sum(r["out_tok"] for r in mr) / len(mr),
                            "errors": sum(1 for r in mr if r["err"]),
                            "calls": len(mr),
                            "truncated": sum(1 for r in mr if str(r["stop"]) in ("length", "max_tokens", "max_output_tokens")),
                            "effort": next((r["effort_used"] for r in mr if r.get("effort_used")), None)}}
        for task in TASKS:
            tr = [r for r in mr if r["task"] == task]
            if not tr:
                continue
            valid = [r for r in tr if not r["err"] and r.get("parsed") is not None]
            d: dict = {"parse": len(valid) / len(tr)}
            for version in ("fresh", "canonical"):
                rows, kind = _rows(mr, task, version)
                if not rows:
                    continue
                d[version] = effect_d(rows, kind)
                d[version + "_ci"] = cluster_bootstrap(rows, kind, n_boot, 0.90, seed=1)
                if kind == "binary":
                    d[version + "_gap"] = proportion_gap(rows)
            h = HUMAN[TASKS[task].human_key].own_d
            if "fresh" in d:
                d["index"] = d["fresh"] / h
            res[m][task] = d
    return res


def spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(v):
        idx = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and v[idx[j + 1]] == v[idx[i]]:
                j += 1
            for k in range(i, j + 1):
                r[idx[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def gate1(res: dict) -> dict:
    """Evaluate the pre-registered rules of run 1 (preregistration/run1-plan.md)."""
    out: dict = {}
    valid = {m: {t: v for t, v in tasks.items() if t != "_meta" and v["parse"] >= 0.90 and "fresh" in v}
             for m, tasks in res.items()}
    out["G1a_invalid"] = [(m, t) for m, tasks in res.items() for t, v in tasks.items()
                          if t != "_meta" and v["parse"] < 0.90]
    spreads = {}
    for t in TASKS:
        ds = [valid[m][t]["fresh"] for m in valid if t in valid[m]]
        spreads[t] = (max(ds) - min(ds)) if len(ds) >= 3 else float("nan")
    out["G1b_spreads"] = spreads
    out["G1b_pass"] = sum(1 for v in spreads.values() if math.isfinite(v) and v >= 0.4) >= 2
    hit, trend = [], []
    for t in TASKS:
        for m, vm in valid.items():
            if t in vm and res[m]["_meta"]["tier"] == "frontier":
                d = vm[t]
                if d["fresh"] >= 0.3 and d["fresh_ci"][0] > 0:
                    hit.append((m, t))
        pts = [(res[m]["_meta"]["order"], valid[m][t]["fresh"], valid[m][t]) for m in valid if t in valid[m]]
        if len(pts) >= 5:
            pts.sort()
            rho = spearman([p[0] for p in pts], [p[1] for p in pts])
            early = pts[0][2]
            if rho <= -0.5 and early["fresh"] >= 0.3 and early["fresh_ci"][0] > 0:
                trend.append((t, round(rho, 2)))
    out["G1c_frontier_nonzero"] = hit
    out["G1c_trend"] = trend
    out["G1c_pass"] = bool(hit or trend)
    out["verdict"] = ("CONTINUE to run 2" if (out["G1b_pass"] and out["G1c_pass"] and not out["G1a_invalid"])
                      else "STOP or FIX (see which rule failed)")
    return out


def render(res: dict) -> str:
    lines = []
    tasks = list(TASKS)
    hum = {t: HUMAN[TASKS[t].human_key].own_d for t in tasks}
    lines.append("Human reference d (this package's estimator): " +
                 ", ".join(f"{t} {hum[t]:.2f}" for t in tasks))
    lines.append("")
    lines.append(f"{'model':18s} {'tier':8s} " + " ".join(f"{t:>26s}" for t in tasks) + "   cost  out/call")
    lines.append(" " * 28 + " ".join(f"{'fresh d [90% CI] (idx) | canon':>26s}" for _ in tasks))
    for m, tt in sorted(res.items(), key=lambda kv: kv[1]["_meta"]["order"]):
        cells = []
        for t in tasks:
            v = tt.get(t)
            if not v or "fresh" not in v:
                cells.append(f"{'n/a':>26s}")
                continue
            lo, hi = v["fresh_ci"]
            cv = v.get("canonical")
            c = f" |{cv:+.2f}" if cv is not None and math.isfinite(cv) else " |  n/a"
            flag = "!" if v["parse"] < 0.90 else " "
            cells.append(f"{v['fresh']:+.2f} [{lo:+.2f},{hi:+.2f}] ({v['index']:+.1f}){c}{flag}".rjust(26))
        meta = tt["_meta"]
        lines.append(f"{m:18s} {meta['tier']:8s} " + " ".join(cells) + f"   ${meta['cost']:.3f}  {meta['out_tok']:.0f}")
    lines.append("")
    lines.append("idx = model fresh d / human d (about 0 Econ, about 1 human-sized, >1 exaggerated). '!' = parse rate < 90%.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="wre.report")
    ap.add_argument("results")
    ap.add_argument("--gate1", action="store_true")
    a = ap.parse_args(argv)
    recs = [json.loads(line) for line in Path(a.results).read_text(encoding="utf-8").splitlines()]
    res = summarize(recs)
    print(render(res))
    if a.gate1:
        g = gate1(res)
        print("\nGATE 1")
        for k, v in g.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

