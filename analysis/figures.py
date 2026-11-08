"""Draw the two figures in analysis/results/ from data/.

    pip install -e ".[plots]"
    python analysis/figures.py
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
OPENAI, ANTHROPIC = "#2563c9", "#c4661f"  # blue and orange: separable under common colour blindness
HUMAN_D, BAND_LO, BAND_HI = part2.HUMAN_FRAMING, 0.36, 1.42


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _band(ax, vertical: bool) -> None:
    (ax.axvspan if vertical else ax.axhspan)(BAND_LO, BAND_HI, color=BAND, zorder=0)
    (ax.axvline if vertical else ax.axhline)(HUMAN_D, color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)


def framing_by_model() -> Path:
    recs = part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")])
    earlier = part2.load([str(DATA / "run1_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")])
    res = robust.analyze(recs, earlier)["res"]
    rows = sorted(res.items(), key=lambda kv: kv[1]["d"])
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    _style(ax)
    _band(ax, vertical=True)
    for y, (m, v) in enumerate(rows):
        flagged = v["biased"] or v["format_robust"] is False
        color = ANTHROPIC if m.startswith("claude") else OPENAI
        marker = "D" if m.startswith("claude") else "o"
        lo, hi = v["ci"]
        ax.plot([lo, hi], [y, y], color=color, linewidth=1.6, solid_capstyle="round", zorder=2, alpha=0.6)
        ax.plot(
            v["d"],
            y,
            marker,
            markersize=7,
            markerfacecolor="white" if flagged else color,
            markeredgecolor=color,
            markeredgewidth=1.6,
            zorder=3,
        )
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([m for m, _ in rows], color=INK, fontsize=9)
    ax.set_xlabel("Framing effect, Cohen's d (gain frame minus loss frame)", color=INK, fontsize=10)
    ax.set_xlim(-0.6, 3.1)
    ax.set_ylim(-0.7, len(rows) + 0.5)
    ax.text(HUMAN_D, len(rows) - 0.1, "humans 0.71", color=MUTED, fontsize=8.5, ha="center", va="bottom")
    fig.suptitle(
        "Framing effect by model (balanced positions, two label formats)\n"
        "Shaded: within a factor of two of humans. Hollow: flagged (position bias or format-sensitive).",
        x=0.01,
        ha="left",
        fontsize=10,
        color=INK,
    )
    handles = [
        plt.Line2D([], [], marker="o", color=OPENAI, linestyle="", markersize=7, label="OpenAI"),
        plt.Line2D([], [], marker="D", color=ANTHROPIC, linestyle="", markersize=7, label="Anthropic"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9, labelcolor=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = OUT / "fig1_framing_by_model.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def prompting() -> Path:
    out = part2.analyze(
        part2.load([str(DATA / "run4_prompting.jsonl")]),
        part2.load([str(DATA / "run3_framing_openai.jsonl"), str(DATA / "run3_framing_anthropic.jsonl")]),
        part2.load([str(DATA / "run2_openai.jsonl"), str(DATA / "run2_anthropic.jsonl")]),
    )
    labels = ["none", "typical", "gut", "rational"]
    fig, axes = plt.subplots(1, 4, figsize=(9.6, 3.6), sharey=True)
    for ax, m in zip(axes, part2.ANCHORS, strict=True):
        _style(ax)
        ax.grid(axis="x", visible=False)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        _band(ax, vertical=False)
        color = ANTHROPIC if m.startswith("claude") else OPENAI
        for i, p in enumerate(labels):
            c = out["cells"][m][p]
            lo, hi = c["ci"]
            ax.plot([i, i], [lo, hi], color=color, linewidth=1.6, alpha=0.6, solid_capstyle="round")
            ax.plot(
                i,
                c["d"],
                "D" if m.startswith("claude") else "o",
                markersize=7,
                markeredgecolor=color,
                markeredgewidth=1.6,
                markerfacecolor="white" if not c["valid"] else color,
            )
        ax.set_xticks(range(4))
        ax.set_xticklabels(labels, fontsize=8.5, color=MUTED, rotation=30)
        ax.set_title(m, fontsize=10, color=INK, loc="left")
        ax.set_xlim(-0.5, 3.5)
    axes[3].text(1.5, 3.85, "estimator\nceiling", color=MUTED, fontsize=8, ha="center", va="top")
    axes[0].set_ylabel("Framing effect, Cohen's d", color=INK, fontsize=10)
    axes[0].set_ylim(-0.3, 4.6)
    axes[0].text(-0.45, HUMAN_D + 0.08, "humans 0.71", color=MUTED, fontsize=8)
    fig.suptitle(
        "What a one-line instruction does to the framing effect (one answer per prompt; Sol two)\n"
        "Shaded: within a factor of two of the human effect. Hollow: invalid cell (position bias).",
        x=0.01,
        ha="left",
        fontsize=10,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    path = OUT / "fig2_prompting.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (framing_by_model, prompting):
        print(f"wrote {fn().relative_to(ROOT)}")


if __name__ == "__main__":
    main()
