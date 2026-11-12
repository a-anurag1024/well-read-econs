"""Plain-percentage charts: how often each model picks an option, next to what people did.

    python analysis/simple_charts.py

Writes chart_framing.png, chart_swing.png, chart_sunk_cost.png, chart_act_human.png, chart_format_check.png,
chart_position_check.png and chart_paid_free_slopes.png to analysis/results/.
Human values: Many Labs 1 (Klein et al., 2014); see src/wre/human_reference.py.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from wre import part2, robust

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "results"

INK, MUTED, GRID, BAND = "#1f2933", "#65717d", "#e3e7eb", "#eef1f4"
SAVED, LOST = "#2563c9", "#c4661f"  # blue and orange stay apart under common colour blindness
FMT_AB, FMT_N = "#0f766e", "#7c3aed"  # teal and violet for the two label styles
HUMAN_SURE = {"saved": 65.5, "lost": 34.5}  # % choosing the sure option (Many Labs 1)
HUMAN_SUNK = {"paid": 7.85, "free": 7.24}  # mean 1-9 rating of going to the event

# Models whose framing result is unreliable on this test (see docs/limitations.md and run 3 results).
UNRELIABLE = {"claude-haiku-4.5", "gpt-5.1", "gpt-5.2", "gpt-5.6-luna", "gpt-6-luna"}


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _pair(ax, y, a, b, color_a=SAVED, color_b=LOST, size=8, alpha=1.0):
    """Two dots joined by a thin line (the gap is the message)."""
    ax.plot([a, b], [y, y], color=MUTED, linewidth=1.4, alpha=0.5 * alpha, zorder=1, solid_capstyle="round")
    ax.plot(a, y, "o", markersize=size, color=color_a, markeredgecolor="white", markeredgewidth=1, zorder=3, alpha=alpha)
    ax.plot(b, y, "o", markersize=size, color=color_b, markeredgecolor="white", markeredgewidth=1, zorder=3, alpha=alpha)


def _legend(ax, a_label, b_label, loc="lower right"):
    handles = [
        plt.Line2D([], [], marker="o", color=SAVED, linestyle="", markersize=8, label=a_label),
        plt.Line2D([], [], marker="o", color=LOST, linestyle="", markersize=8, label=b_label),
    ]
    ax.legend(handles=handles, loc=loc, frameon=False, fontsize=9, labelcolor=INK)


def framing() -> Path:
    recs = part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    models = list(dict.fromkeys(r["model"] for r in recs))
    rows = []
    for m in models:
        saved = 100 * robust.p_certain(recs, m, "hi")
        lost = 100 * robust.p_certain(recs, m, "lo")
        rows.append((m, saved, lost))
    rows.sort(key=lambda r: r[1] - r[2])  # smallest gap at the bottom
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    _style(ax)
    n = len(rows)
    ax.axhspan(n - 0.5, n + 0.6, color=BAND, zorder=0)
    _pair(ax, n, HUMAN_SURE["saved"], HUMAN_SURE["lost"], size=9)
    ax.text(2, n, "People (study)", color=INK, fontsize=9.5, fontweight="bold", va="center")
    for y, (m, saved, lost) in enumerate(rows):
        _pair(ax, y, saved, lost, alpha=0.45 if m in UNRELIABLE else 1.0)
    ax.set_yticks(range(n))
    ax.set_yticklabels([m + (" *" if m in UNRELIABLE else "") for m, *_ in rows], color=INK, fontsize=9)
    ax.set_xlim(-2, 104)
    ax.set_ylim(-0.7, n + 0.7)
    ax.set_xlabel("% of answers choosing the sure option", color=INK, fontsize=10)
    fig.suptitle(
        "Same choice, two wordings: described as lives saved vs lives lost\n"
        "A pure Econ gives the same answer both ways (the two dots sit on top of each other).",
        x=0.01,
        ha="left",
        fontsize=10,
        color=INK,
    )
    _legend(ax, "worded as 'saved'", "worded as 'lost'", loc="lower left")
    fig.text(0.01, 0.01, "* answers depend on formatting or position; treat as unreliable (faded)", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = OUT / "chart_framing.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def sunk_cost() -> Path:
    recs = part2.load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    rows = []
    for m in dict.fromkeys(r["model"] for r in recs):
        sel = [r for r in recs if r["model"] == m and r["task"] == "sunkcost" and r["version"] == "fresh"
               and "-v11" in r["id"] and not r["err"] and r.get("parsed") is not None]
        paid = [r["parsed"] for r in sel if r["condition"] == "hi"]
        free = [r["parsed"] for r in sel if r["condition"] == "lo"]
        if paid and free:
            rows.append((m, sum(paid) / len(paid), sum(free) / len(free)))
    rows.sort(key=lambda r: r[1] - r[2])
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    _style(ax)
    n = len(rows)
    ax.axhspan(n - 0.5, n + 0.6, color=BAND, zorder=0)
    _pair(ax, n, HUMAN_SUNK["paid"], HUMAN_SUNK["free"], size=9)
    ax.text(1.05, n, "People (study)", color=INK, fontsize=9.5, fontweight="bold", va="center")
    for y, (_, paid, free) in enumerate(rows):
        _pair(ax, y, paid, free)
    ax.set_yticks(range(n))
    ax.set_yticklabels([m for m, *_ in rows], color=INK, fontsize=9)
    ax.set_xlim(1, 9)
    ax.set_ylim(-0.7, n + 0.7)
    ax.set_xlabel("average rating of going to the event (1 = stay home, 9 = definitely go)", color=INK, fontsize=10)
    fig.suptitle(
        "Would you go in bad weather? Ticket you paid for vs a free ticket\n"
        "A pure Econ ignores what was paid (the two dots sit on top of each other).",
        x=0.01,
        ha="left",
        fontsize=10,
        color=INK,
    )
    _legend(ax, "ticket was paid for", "ticket was free", loc="lower left")
    fig.text(0.01, 0.01, "People: a different set of event descriptions, so compare the gap, not the level.", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = OUT / "chart_sunk_cost.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def act_human() -> Path:
    out = part2.analyze(
        part2.load([str(DATA / "run4_prompting.jsonl")]),
        part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]),
        part2.load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]),
    )
    rows = [
        ("none", "no instruction"),
        ("typical", "'act like a typical person'"),
        ("gut", "'go with your gut'"),
        ("rational", "'act perfectly rational'"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(10, 3.9), sharey=True, sharex=True)
    for ax, m in zip(axes, part2.ANCHORS, strict=True):
        _style(ax)
        ax.axhspan(len(rows) - 0.5, len(rows) + 0.5, color=BAND, zorder=0)
        _pair(ax, len(rows), HUMAN_SURE["saved"], HUMAN_SURE["lost"], size=8)
        for y, (key, _) in enumerate(reversed(rows)):
            c = out["cells"][m][key]
            _pair(ax, y, 100 * c["gain"], 100 * c["loss"], size=8, alpha=1.0 if c["valid"] else 0.4)
        ax.set_title(m, fontsize=10, color=INK, loc="left")
        ax.set_xlim(-4, 104)
        ax.set_ylim(-0.6, len(rows) + 0.6)
        ax.set_xticks([0, 50, 100])
    axes[0].set_yticks(range(len(rows) + 1))
    axes[0].set_yticklabels([lab for _, lab in reversed(rows)] + ["People (study)"], fontsize=8.5, color=INK)
    fig.supxlabel("% of answers choosing the sure option", color=INK, fontsize=10)
    fig.suptitle(
        "Does telling the model to act human (or rational) change the gap? (blue: worded as 'saved', orange: 'lost')\n"
        "Humans: dots about 30 points apart. An Econ: dots on top of each other. Faded: unreliable (always favored one position).",
        x=0.01,
        ha="left",
        fontsize=10,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = OUT / "chart_act_human.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _framing_recs() -> list[dict]:
    return part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])


def _swing(recs, model, fmt=None) -> float:
    """Percentage-point gap in choosing the sure option: 'saved' wording minus 'lost' wording."""
    def share(cond):
        v = [r["parsed"] for r in recs if r["model"] == model and r["version"] == "fresh"
             and r["condition"] == cond and not r["err"] and r.get("parsed") is not None
             and (fmt is None or r["meta"]["fmt"] == fmt)]
        return sum(v) / len(v)
    return 100 * (share("hi") - share("lo"))


def swing() -> Path:
    recs = _framing_recs()
    rows = sorted(((m, _swing(recs, m)) for m in dict.fromkeys(r["model"] for r in recs)), key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    _style(ax)
    ax.grid(axis="y", visible=False)
    human = HUMAN_SURE["saved"] - HUMAN_SURE["lost"]
    ax.axvline(human, color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(human + 1, len(rows) - 0.4, "people: 31 points", color=MUTED, fontsize=9, va="bottom")
    for y, (m, g) in enumerate(rows):
        ax.barh(y, g, height=0.5, color=SAVED, alpha=0.4 if m in UNRELIABLE else 1.0, zorder=2)
        ax.text(max(g, 0) + 1, y, f"{g:.0f}", va="center", color=INK, fontsize=8.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([m + (" *" if m in UNRELIABLE else "") for m, _ in rows], color=INK, fontsize=9)
    ax.set_xlim(-8, 100)
    ax.set_ylim(-0.7, len(rows))
    ax.set_xlabel("swing between the two wordings (percentage points)", color=INK, fontsize=10)
    fig.suptitle(
        "How much does the wording change the answer?\n"
        "Swing = % choosing the sure option when worded 'saved' minus when worded 'lost'. An Econ: 0.",
        x=0.01, ha="left", fontsize=10, color=INK,
    )
    fig.text(0.01, 0.01, "* unreliable on this test (faded)", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93))
    path = OUT / "chart_swing.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def format_check() -> Path:
    recs = _framing_recs()
    rows = sorted(
        ((m, _swing(recs, m, "ab"), _swing(recs, m, "n")) for m in dict.fromkeys(r["model"] for r in recs)),
        key=lambda r: abs(r[1] - r[2]),
    )
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    _style(ax)
    n = len(rows)
    for y, (m, a, b) in enumerate(rows):
        _pair(ax, y, a, b, color_a=FMT_AB, color_b=FMT_N, alpha=0.4 if m in UNRELIABLE else 1.0)
    ax.set_yticks(range(n))
    ax.set_yticklabels([m + (" *" if m in UNRELIABLE else "") for m, *_ in rows], color=INK, fontsize=9)
    ax.set_xlim(min(-10, min(min(a, b) for _, a, b in rows) - 4), 100)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlabel("swing between the two wordings (percentage points)", color=INK, fontsize=10)
    fig.suptitle(
        "Is the result a trick of formatting?\n"
        "Same questions with 'Plan A / Plan B' labels vs 'Option 1 / Option 2' labels. Close dots = stable.",
        x=0.01, ha="left", fontsize=10, color=INK,
    )
    handles = [
        plt.Line2D([], [], marker="o", color=FMT_AB, linestyle="", markersize=8, label="Plan A / Plan B"),
        plt.Line2D([], [], marker="o", color=FMT_N, linestyle="", markersize=8, label="Option 1 / Option 2"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9, labelcolor=INK)
    fig.text(0.01, 0.01, "* flagged in the robustness check as format-sensitive or position-biased (faded)", color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.92))
    path = OUT / "chart_format_check.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def position_check() -> Path:
    recs = _framing_recs()
    res = robust.analyze(recs, part2.load([str(DATA / "run1_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]))["res"]
    rows = sorted(((m, 100 * v["first"]) for m, v in res.items()), key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    _style(ax)
    ax.axvspan(35, 65, color=BAND, zorder=0)
    ax.axvline(50, color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    for y, (m, s) in enumerate(rows):
        ax.plot([50, s], [y, y], color=MUTED, linewidth=1.2, alpha=0.5, zorder=2)
        ax.plot(s, y, "o", markersize=8, color=SAVED if s > 20 else LOST, markeredgecolor="white", zorder=3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([m for m, _ in rows], color=INK, fontsize=9)
    ax.text(rows[0][1] + 2, 0.35, "picks the second-listed option 92% of the time", color=MUTED, fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of answers choosing whichever option was listed first", color=INK, fontsize=10)
    fig.suptitle(
        "Does the model just pick the first (or second) option?\n"
        "The sure option was listed first in exactly half the questions, so about 50% is expected.",
        x=0.01, ha="left", fontsize=10, color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = OUT / "chart_position_check.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _sunk_recs() -> list[dict]:
    recs = part2.load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    return [r for r in recs if r["task"] == "sunkcost" and r["version"] == "fresh" and "-v11" in r["id"]
            and not r["err"] and r.get("parsed") is not None]


def _sunk_by_scenario(recs, model) -> dict[str, tuple[float, float]]:
    """{scenario: (average rating with a free ticket, average rating with a paid ticket)}."""
    out = {}
    for key in sorted({r["item_key"] for r in recs if r["model"] == model}):
        free = [r["parsed"] for r in recs if r["model"] == model and r["item_key"] == key and r["condition"] == "lo"]
        paid = [r["parsed"] for r in recs if r["model"] == model and r["item_key"] == key and r["condition"] == "hi"]
        if free and paid:
            out[key] = (sum(free) / len(free), sum(paid) / len(paid))
    return out


def paid_free_slopes() -> Path:
    """One line per scenario: how the average rating moves when only the ticket sentence changes."""
    recs = _sunk_recs()
    models = [
        ["gpt-6.1-sol", "gpt-6-astra", "claude-sonnet-5.5", "claude-opus-5.5"],
        ["gpt-4.1", "claude-haiku-4.5", "gpt-4o-mini", "gpt-5-nano"],
    ]
    fig, axes = plt.subplots(2, 4, figsize=(10, 6.2), sharey=True)
    for ax, m in zip(axes.flat, [m for row in models for m in row], strict=True):
        by = _sunk_by_scenario(recs, m)
        up = down = 0
        for free, paid in by.values():
            color = SAVED if paid > free else LOST if paid < free else MUTED
            up, down = up + (paid > free), down + (paid < free)
            ax.plot([0, 1], [free, paid], color=color, alpha=0.55, linewidth=1.6, marker="o", markersize=3.5, zorder=2)
        mean_free = sum(f for f, _ in by.values()) / len(by)
        mean_paid = sum(p for _, p in by.values()) / len(by)
        ax.plot([0, 1], [mean_free, mean_paid], color=INK, linewidth=3, marker="o", markersize=6, zorder=3)
        _style(ax)
        ax.grid(axis="x", visible=False)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_xlim(-0.35, 1.35)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["free", "paid"], color=INK, fontsize=9)
        ax.set_ylim(1, 9)
        ax.set_title(f"{m}\n{mean_paid - mean_free:+.1f} points; {up} up, {down} down of {len(by)}",
                     fontsize=9, color=INK, loc="left")
    for ax in axes[:, 0]:
        ax.set_ylabel("average rating (1-9)", color=INK, fontsize=9)
    fig.suptitle(
        "Same story, one sentence changed: does the rating follow?\n"
        "Each thin line is one of the 12 scenarios (blue: rated higher when paid, orange: higher when free). "
        "Thick line: average.",
        x=0.01, ha="left", fontsize=10, color=INK,
    )
    fig.text(0.01, 0.01, "Eight of the 16 models are shown. Top row: the two models with no framing effect and the two Claude models.\n"
             "Bottom row: the largest gap (GPT-4.1) and the three models with no gap or a reversed one.\n"
             "The other eight have average gaps from -0.1 to +1.5 points; all 16 are in chart_sunk_cost.png.",
             color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    path = OUT / "chart_paid_free_slopes.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (framing, swing, sunk_cost, act_human, format_check, position_check,
               paid_free_slopes):
        print(f"wrote {fn().relative_to(ROOT)}")


if __name__ == "__main__":
    main()
