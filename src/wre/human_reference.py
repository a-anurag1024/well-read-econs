"""Human reference effects for the benchmark, from the Many Labs 1 replication.

Source: Klein, R. A., et al. (2014). Investigating variation in replicability: A "Many Labs"
replication project. Social Psychology, 45(3), 142-152 (36 samples, N = 6,344), plus its
Supplementary Materials (OSF project ydpbf, file ML.web.Supplement.pdf), which give the raw
proportions and means used here.

Why two kinds of d. The paper's Table 2 reports d converted from chi-square (binary tasks) and
t (continuous tasks). To compare a model with humans, both must be scored by the SAME estimator,
so for binary tasks we recompute d from the reported proportions with the log-odds estimator in
effects.py. The Table 2 values are kept as `paper_d`.

Allowed/forbidden: Table 2 reports d = 1.96, computed (it appears) on the raw yes/no answers, which
flip meaning between the two wordings. The wording effect on the restrictive stance is
23.7% ("no" to allow) vs 7.2% ("yes" to forbid), which is what the benchmark scores.

Note on the framing numbers: the supplement text gives 65.5% (gain, certain option) and 34.5%
(loss, certain option) but also lists 36.8% and 63.2% for the risky options, which do not sum to
100%; we use the certain-option proportions, which agree with the reported d.
"""
from __future__ import annotations

from dataclasses import dataclass

from .effects import d_from_proportions, d_from_summary

CITATION = ("Klein et al. (2014), Social Psychology 45(3):142-152, and Supplementary Materials. "
            "doi:10.1027/1864-9335/a000178")


@dataclass(frozen=True)
class HumanEffect:
    name: str
    kind: str                       # "binary" | "continuous"
    own_d: float                    # computed with this package's estimator
    paper_d: float                  # as reported (Table 2 or supplement)
    original_d: float | None        # original study, where reported
    detail: str


_framing = d_from_proportions(0.655, 0.345)
_forbid = d_from_proportions(0.237, 0.072)
_sunk = d_from_summary(7.85, 2.02, 7.24, 2.42)

HUMAN: dict[str, HumanEffect] = {
    "framing": HumanEffect(
        "Gain vs loss framing (Tversky & Kahneman, 1981)", "binary", _framing, 0.60, 1.13,
        "certain option chosen by 65.5% (gain frame) vs 34.5% (loss frame); original 72% vs 22%"),
    "sunkcost": HumanEffect(
        "Sunk costs (Oppenheimer, Meyvis & Davidenko, 2009)", "continuous", _sunk, 0.27, 0.23,
        "likelihood of attending (1-9): paid M=7.85 SD=2.02 vs free M=7.24 SD=2.42; original 7.46 vs 6.93"),
    "forbid": HumanEffect(
        "Allowed vs forbidden (Rugg, 1941)", "binary", _forbid, 1.96, 0.65,
        "restrictive stance: 23.7% (\"no\" to allow) vs 7.2% (\"yes\" to forbid); original 62% vs 46%; "
        "paper d = 1.96 is on raw yes/no answers"),
    "anchoring": HumanEffect(
        "Anchoring (Jacowitz & Kahneman, 1995), four topics", "continuous", 1.895, 1.895, 0.93,
        "rank-transformed d per topic: NYC 1.18, Chicago 1.8, Everest 2.2, babies 2.4 (mean 1.895); "
        "ML1 anchors are extreme and responses beyond the anchors were excluded, so treat as a rough band"),
}
