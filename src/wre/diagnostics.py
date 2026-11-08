"""Response-style diagnostics that guard against reading artifacts as behavior.

A model that always answers the same letter has a framing effect of exactly zero by construction;
a model that says "Yes" to both "should X be allowed?" and "should X be forbidden?" is acquiescent,
not rational or human. These checks are reported next to every effect.
"""
from __future__ import annotations


def letter_shares(recs: list[dict], model: str, task: str = "framing") -> dict[str, float]:
    """Share of A / B answers among parsed fresh answers (letter tasks only)."""
    rows = [r for r in recs if r["model"] == model and r["task"] == task and r["version"] == "fresh"
            and not r["err"] and r.get("parsed") is not None]
    out = {"A": 0.0, "B": 0.0}
    for r in rows:
        t = r["text"].strip().upper()
        if t[:1] in out:
            out[t[:1]] += 1
    n = sum(out.values())
    return {k: v / n for k, v in out.items()} if n else {"A": float("nan"), "B": float("nan")}


def letter_biased(shares: dict[str, float], threshold: float = 0.95) -> bool:
    """True if a single letter accounts for at least `threshold` of the answers."""
    return any(v >= threshold for v in shares.values())


def yes_bias(recs: list[dict], model: str) -> dict[str, float]:
    """For the allowed/forbidden task: P(yes) under each wording on fresh items, the acquiescence
    index P(yes|allow) + P(yes|forbid) - 1 (0 = consistent, >0 yes-bias, <0 no-bias) and the share
    of answers that could not be parsed as yes/no (refusals or hedges)."""
    rows = [r for r in recs if r["model"] == model and r["task"] == "forbid" and r["version"] == "fresh"
            and not r["err"]]
    out: dict[str, float] = {}
    for cond, key in (("hi", "p_yes_allow"), ("lo", "p_yes_forbid")):
        sel = [r for r in rows if r["condition"] == cond]
        parsed = [r for r in sel if r.get("parsed") is not None]
        yes = sum(1 for r in parsed if r["text"].strip().lower().startswith("yes"))
        out[key] = yes / len(parsed) if parsed else float("nan")
        out["unparsed_" + cond] = 1 - len(parsed) / len(sel) if sel else float("nan")
    out["acquiescence"] = out["p_yes_allow"] + out["p_yes_forbid"] - 1
    out["unparsed"] = (out["unparsed_hi"] + out["unparsed_lo"]) / 2
    return out
