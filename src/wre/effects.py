"""Effect sizes and uncertainty for between-condition comparisons.

All effects are expressed as Cohen's d so that a model's effect can be compared with the
human effect reported in replication studies:

* binary outcomes: d = ln(odds ratio) * sqrt(3) / pi  (Hasselblad & Hedges, 1995);
* continuous outcomes (ratings, estimates): standardized mean difference with pooled SD.

Uncertainty uses a cluster bootstrap over items, because the item (not the sampled answer) is
the unit of replication.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable, Sequence

SQRT3_OVER_PI = math.sqrt(3.0) / math.pi

Row = tuple[str, str, float]  # (item_key, "hi" | "lo", value)


def d_from_counts(k_hi: int, n_hi: int, k_lo: int, n_lo: int, correction: float = 0.5) -> float:
    """Cohen's d from two proportions via the log odds ratio (continuity-corrected)."""
    a, b = k_hi + correction, (n_hi - k_hi) + correction
    c, d = k_lo + correction, (n_lo - k_lo) + correction
    return math.log((a / b) / (c / d)) * SQRT3_OVER_PI


def d_from_proportions(p_hi: float, p_lo: float) -> float:
    """Cohen's d from two population proportions via the log odds ratio (no correction)."""
    return math.log((p_hi / (1 - p_hi)) / (p_lo / (1 - p_lo))) * SQRT3_OVER_PI


def d_from_summary(m_hi: float, sd_hi: float, m_lo: float, sd_lo: float) -> float:
    """Cohen's d from group means and SDs, assuming equal group sizes."""
    pooled = math.sqrt((sd_hi**2 + sd_lo**2) / 2)
    return (m_hi - m_lo) / pooled


def d_from_samples(hi: Sequence[float], lo: Sequence[float]) -> float:
    """Standardized mean difference (hi minus lo) with pooled standard deviation."""
    n1, n0 = len(hi), len(lo)
    if n1 < 2 or n0 < 2:
        return float("nan")
    m1, m0 = sum(hi) / n1, sum(lo) / n0
    v1 = sum((x - m1) ** 2 for x in hi) / (n1 - 1)
    v0 = sum((x - m0) ** 2 for x in lo) / (n0 - 1)
    pooled = math.sqrt(((n1 - 1) * v1 + (n0 - 1) * v0) / (n1 + n0 - 2))
    if pooled == 0:
        return 0.0 if m1 == m0 else math.copysign(float("inf"), m1 - m0)
    return (m1 - m0) / pooled


def effect_d(rows: Iterable[Row], kind: str) -> float:
    """Pooled effect (hi minus lo) over all rows. kind is "binary" or "continuous"."""
    hi = [v for _, c, v in rows if c == "hi"]
    lo = [v for _, c, v in rows if c == "lo"]
    if not hi or not lo:
        return float("nan")
    if kind == "binary":
        return d_from_counts(int(sum(hi)), len(hi), int(sum(lo)), len(lo))
    return d_from_samples(hi, lo)


def proportion_gap(rows: Iterable[Row]) -> float:
    """Raw difference in mean outcome (hi minus lo); for binary outcomes a difference in proportions."""
    hi = [v for _, c, v in rows if c == "hi"]
    lo = [v for _, c, v in rows if c == "lo"]
    if not hi or not lo:
        return float("nan")
    return sum(hi) / len(hi) - sum(lo) / len(lo)


def cluster_bootstrap(rows: Sequence[Row], kind: str, n_boot: int = 2000, level: float = 0.90,
                      seed: int = 0, stat=None) -> tuple[float, float]:
    """Percentile interval for a statistic, resampling items with replacement.

    With a single item (e.g. one canonical vignette) it falls back to resampling answers within
    each condition. `stat` defaults to effect_d(rows, kind).
    """
    rng = random.Random(seed)
    fn = stat or (lambda r: effect_d(r, kind))
    by_item: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_item[r[0]].append(r)
    keys = list(by_item)
    vals: list[float] = []
    for _ in range(n_boot):
        if len(keys) > 1:
            sample = [r for k in (rng.choice(keys) for _ in keys) for r in by_item[k]]
        else:
            hi = [r for r in rows if r[1] == "hi"]
            lo = [r for r in rows if r[1] == "lo"]
            if not hi or not lo:
                return float("nan"), float("nan")
            sample = [rng.choice(hi) for _ in hi] + [rng.choice(lo) for _ in lo]
        v = fn(sample)
        if math.isfinite(v):
            vals.append(v)
    if not vals:
        return float("nan"), float("nan")
    vals.sort()
    lo_i = int(((1 - level) / 2) * len(vals))
    hi_i = min(len(vals) - 1, int((1 - (1 - level) / 2) * len(vals)))
    return vals[lo_i], vals[hi_i]


def econ_index(d_model: float, d_human: float) -> float:
    """Model effect as a multiple of the human effect: ~0 Econ, ~1 human-sized, >1 exaggerated."""
    return d_model / d_human if d_human else float("nan")


def within_item_z(rows: Sequence[Row], log: bool = False) -> list[Row]:
    """Standardize values within each item (optionally after a log transform).

    Needed when items live on different scales (e.g. anchoring estimates), so that answers can
    be pooled across items. Items with zero variance are dropped.
    """
    by_item: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_item[r[0]].append(r)
    out: list[Row] = []
    for key, rs in by_item.items():
        vals = [math.log(v) if log else v for _, _, v in rs if (v > 0 or not log)]
        if len(vals) < 2:
            continue
        mean = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
        if sd == 0:
            continue
        out.extend((key, c, ((math.log(v) if log else v) - mean) / sd)
                   for _, c, v in rs if (v > 0 or not log))
    return out


def within_item_rank_z(rows: Sequence[Row], keep_constant: bool = True) -> list[Row]:
    """Rank-transform values within each item (ties get the average rank), then standardize.

    Mirrors the rank-transformed analysis Many Labs 1 used for anchoring estimates, which are
    skewed and multimodal. An item where every value is tied shows NO effect; by default it is
    kept with z = 0 so that it counts as a null item. (Dropping such items, as an earlier version
    did, overstates the average effect.) Pass keep_constant=False to drop them.
    """
    by_item: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_item[r[0]].append(r)
    out: list[Row] = []
    for key, rs in by_item.items():
        order = sorted(range(len(rs)), key=lambda i: rs[i][2])
        ranks = [0.0] * len(rs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and rs[order[j + 1]][2] == rs[order[i]][2]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        mean = sum(ranks) / len(ranks)
        sd = math.sqrt(sum((x - mean) ** 2 for x in ranks) / (len(ranks) - 1)) if len(ranks) > 1 else 0
        if sd == 0:
            if keep_constant:
                out.extend((key, rs[i][1], 0.0) for i in range(len(rs)))
            continue
        out.extend((key, rs[i][1], (ranks[i] - mean) / sd) for i in range(len(rs)))
    return out
