"""Figures for Experiment 4 — spec Build Step 7.

OWNERSHIP: Person B. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

Turns the experiment's numbers into the pictures that go in the paper.

**The governing rule here is that the figures must not flatter the result.** Our
headline comparison came back null — the sophisticated model did not clearly
beat plain distance. There is an obvious way to draw that which makes it look
better than it is, and an honest way. This file does the honest one, on purpose,
and the docstrings say why at each point.

The specific trap: if you draw one error bar for the model and another for plain
distance side by side, a reader compares whether they overlap. That is the wrong
comparison — both were measured on the same landscapes, so most of their
wobble is shared and cancels out when you subtract. **The right picture is of
the difference itself, with a line at zero.** Panel C does that.

------------------------------------------------------------------------------
COLOUR
------------------------------------------------------------------------------

Three colours, from the Okabe-Ito set designed for colour-blind readers, and
**checked rather than assumed** — run through a validator that measures the
perceptual separation between every pair under three kinds of colour blindness.
Worst adjacent pair came out at 11.0 against a floor of 8.

Colour is never the only signal: every series is also directly labelled, and the
panels are legible in greyscale for anyone printing the paper in black and
white.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")  # no display needed; we only write files
import matplotlib.pyplot as plt

from boec.discrimination import instance_bootstrap_ci, paired_difference_ci

__all__ = [
    "COLOURS",
    "figure_discrimination",
    "figure_headroom",
    "figure_over_prediction",
    "make_all_figures",
]

# Okabe-Ito, validated: worst adjacent CVD separation 11.0 (floor 8).
COLOURS = {
    "gp": "#0072B2",         # blue   — the model
    "polynomial": "#D55E00",  # orange — the traditional method
    "distance": "#009E73",   # green  — the model-free null
}
INK = "#1a1a1a"
MUTED = "#6b6b6b"
GRID = "#dcdcdc"


def _style(ax) -> None:
    """Recessive axes and grid; the data is the only thing that should be loud."""
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=9, length=3, width=0.8)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def _by_kappa(results: Sequence, kappas: Sequence[float]) -> dict:
    return {k: [r for r in results if r.kappa == k and r.is_valid] for k in kappas}


# ---------------------------------------------------------------------------
# Panel A — the mechanism
# ---------------------------------------------------------------------------

def figure_over_prediction(results: Sequence, path: Path, kappas=(0.6, 0.7, 0.8, 0.9)):
    """How much each method over-promises, against how much of the space was hidden.

    **Form: lines with markers and error bars, on a log scale.**

    Log rather than linear because the two methods differ by about twentyfold
    at the tightest setting. On a linear axis the model's line would be flat
    against the baseline and you could not see that it also rises — the shape
    of the smaller quantity would be destroyed to accommodate the larger.

    A dashed line marks the response's own maximum, because "over-promised by
    9" means nothing until you know the best achievable value is 1.
    """
    groups = _by_kappa(results, kappas)
    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=200)
    _style(ax)

    for name, label in (("second_order", "Traditional fit"), ("gp", "Gaussian process")):
        colour = COLOURS["polynomial" if name == "second_order" else "gp"]
        mids, los, his = [], [], []
        for k in kappas:
            vals = [r.over_prediction[name] for r in groups[k]
                    if np.isfinite(r.over_prediction.get(name, np.nan))]
            m, lo, hi = instance_bootstrap_ci(vals)
            mids.append(m); los.append(lo); his.append(hi)
        mids = np.array(mids)
        err = np.abs(np.vstack([mids - np.array(los), np.array(his) - mids]))
        ax.errorbar(kappas, mids, yerr=err, color=colour, marker="o", markersize=6,
                    linewidth=2, capsize=3, capthick=1, elinewidth=1, label=label,
                    markeredgecolor="white", markeredgewidth=1.2)
        # Direct label, so identity never depends on colour alone.
        ax.annotate(label, (kappas[0], mids[0]), textcoords="offset points",
                    xytext=(8, 10), fontsize=9, color=colour, fontweight="bold")

    ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1)
    ax.annotate("best achievable response = 1.0", (kappas[-1], 1.0),
                textcoords="offset points", xytext=(-4, -14), fontsize=8,
                color=MUTED, ha="right")

    ax.set_yscale("log")
    # Plain numbers, not 10^0 / 10^1. The default log labels left the GP line's
    # whole range unlabelled, which made the smaller quantity unreadable —
    # exactly the thing the log scale was chosen to preserve.
    ax.set_yticks([0.2, 0.5, 1, 2, 5, 10])
    ax.set_yticklabels(["0.2", "0.5", "1", "2", "5", "10"])
    ax.minorticks_off()
    ax.set_xlabel("κ  —  more of the space hidden  ←", fontsize=10, color=INK)
    ax.set_ylabel("over-promise at its own\nclaimed optimum", fontsize=10, color=INK)
    ax.set_title("The traditional fit over-promises by ~10× the entire response range",
                 fontsize=10.5, color=INK, loc="left", pad=10)
    ax.set_xticks(list(kappas))
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Panel B — the honesty check, shown BEFORE the result
# ---------------------------------------------------------------------------

def figure_headroom(results: Sequence, path: Path, kappas=(0.6, 0.7, 0.8, 0.9),
                    threshold: float = 0.95):
    """Whether the three warning systems were different enough to be compared.

    **Form: one dot per landscape, with the kill threshold drawn as a line.**

    **This figure comes before the result, not after.** If all three warning
    systems ranked recipes almost identically, the comparison could not have
    shown anything either way — and a reader needs to know that *before* being
    told what it showed. Every point sitting below the line is what makes the
    null in panel C a real finding rather than an artefact.

    Individual dots rather than a summary: the spread matters, and with ten
    landscapes per setting there is no reason to hide them behind a mean.
    """
    groups = _by_kappa(results, kappas)
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=200)
    _style(ax)

    rng = np.random.default_rng(0)
    for i, k in enumerate(kappas):
        vals = [r.discrimination.agreement.max_offdiagonal for r in groups[k]]
        jitter = rng.uniform(-0.09, 0.09, len(vals))
        ax.scatter(np.full(len(vals), i) + jitter, vals, s=34,
                   color=COLOURS["gp"], alpha=0.75, edgecolor="white", linewidth=0.8,
                   zorder=3)
        if vals:
            ax.plot([i - 0.2, i + 0.2], [np.median(vals)] * 2,
                    color=INK, linewidth=2, zorder=4)

    ax.axhline(threshold, color=COLOURS["polynomial"], linestyle="--", linewidth=1.5)
    # Anchored in data coordinates inside the axes. An earlier version placed
    # this outside and it was silently clipped — the figure shipped with an
    # unexplained dashed line. Caught only by rendering and looking.
    ax.text(-0.35, threshold + 0.010,
            "above this line the warning systems agree too\nclosely for the "
            "comparison to show anything",
            fontsize=8, color=COLOURS["polynomial"], va="bottom", ha="left",
            linespacing=1.3)

    ax.set_xticks(range(len(kappas)))
    ax.set_xticklabels([f"κ = {k}" for k in kappas])
    ax.set_ylim(0.5, 1.09)
    ax.set_ylabel("strongest agreement between\nany two warning systems", fontsize=10, color=INK)
    ax.set_title("There was room for the comparison to show a difference",
                 fontsize=10.5, color=INK, loc="left", pad=10)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Panel C — the result, drawn the honest way
# ---------------------------------------------------------------------------

def figure_discrimination(results: Sequence, path: Path, kappas=(0.6, 0.7, 0.8, 0.9)):
    """Does the model warn you better than plain distance does?

    **Form: the paired difference, with a line at zero. Not two bars.**

    This is the whole point of the file's opening note. Drawing the model's
    score and plain distance's score as two separate bars invites the reader to
    compare error bars that share most of their wobble — a comparison that is
    not just weaker but actively misleading.

    So the picture is of the **difference itself**, computed landscape by
    landscape and then averaged. An interval clearing zero means the model
    genuinely warns better. An interval straddling zero means it does not, and
    the picture says so plainly rather than burying it.

    The left panel shows the raw scores for context; the right panel is the
    actual claim. They are drawn at different weights on purpose — the reader's
    eye should land on the right.
    """
    groups = _by_kappa(results, kappas)
    fig, (ax_raw, ax_diff) = plt.subplots(
        1, 2, figsize=(9.4, 3.6), dpi=200, gridspec_kw={"width_ratios": [1, 1.15]}
    )
    _style(ax_raw); _style(ax_diff)

    # --- left: context ----------------------------------------------------
    scorers = (
        ("gp_predictive_sd", "Gaussian process", COLOURS["gp"]),
        ("nearest_neighbour_distance", "Plain distance", COLOURS["distance"]),
        ("second_order_pi_width", "Traditional error bar", COLOURS["polynomial"]),
    )
    for name, label, colour in scorers:
        mids = []
        for k in kappas:
            vals = [r.discrimination.spearman[name] for r in groups[k]]
            mids.append(instance_bootstrap_ci(vals)[0])
        ax_raw.plot(kappas, mids, color=colour, marker="o", markersize=5,
                    linewidth=1.8, markeredgecolor="white", markeredgewidth=1)
        ax_raw.annotate(label, (kappas[-1], mids[-1]), textcoords="offset points",
                        xytext=(6, 0), fontsize=8, color=colour, va="center")

    ax_raw.set_xticks(list(kappas))
    ax_raw.set_xlim(0.55, 1.06)
    ax_raw.set_ylim(0, 0.75)
    ax_raw.set_xlabel("κ", fontsize=10, color=INK)
    ax_raw.set_ylabel("how well each warning system\ntracks the real error", fontsize=10, color=INK)
    ax_raw.set_title("Context: all three warn about equally well",
                     fontsize=10, color=MUTED, loc="left", pad=8)

    # --- right: the actual claim -----------------------------------------
    mids, los, his, sigs = [], [], [], []
    for k in kappas:
        gp = [r.discrimination.spearman["gp_predictive_sd"] for r in groups[k]]
        nn = [r.discrimination.spearman["nearest_neighbour_distance"] for r in groups[k]]
        m, lo, hi, sig = paired_difference_ci(gp, nn)
        mids.append(m); los.append(lo); his.append(hi); sigs.append(sig)

    all_gp = [r.discrimination.spearman["gp_predictive_sd"]
              for k in kappas for r in groups[k]]
    all_nn = [r.discrimination.spearman["nearest_neighbour_distance"]
              for k in kappas for r in groups[k]]
    pm, plo, phi, psig = paired_difference_ci(all_gp, all_nn)

    ys = list(range(len(kappas)))
    for y, m, lo, hi, sig in zip(ys, mids, los, his, sigs, strict=True):
        colour = COLOURS["gp"] if sig else MUTED
        ax_diff.plot([lo, hi], [y, y], color=colour, linewidth=2.4,
                     solid_capstyle="round", zorder=3)
        ax_diff.scatter([m], [y], s=52, color=colour, zorder=4,
                        edgecolor="white", linewidth=1.2)

    y_pooled = len(kappas) + 0.4
    ax_diff.plot([plo, phi], [y_pooled] * 2, color=INK, linewidth=3,
                 solid_capstyle="round", zorder=3)
    ax_diff.scatter([pm], [y_pooled], s=72, color=INK, zorder=4,
                    edgecolor="white", linewidth=1.2, marker="D")

    ax_diff.axvline(0, color=COLOURS["polynomial"], linewidth=1.5, zorder=2)
    ax_diff.annotate("no difference", (0, -0.85), textcoords="offset points",
                     xytext=(4, 0), fontsize=8, color=COLOURS["polynomial"])

    ax_diff.set_yticks(ys + [y_pooled])
    ax_diff.set_yticklabels([f"κ = {k}" for k in kappas] + ["all pooled"])
    ax_diff.set_ylim(-1.1, y_pooled + 0.7)
    ax_diff.set_xlabel("Gaussian process advantage over plain distance",
                       fontsize=10, color=INK)
    verdict = (
        "the advantage is established"
        if psig
        else "no interval clears zero — the advantage is NOT established"
    )
    ax_diff.set_title(f"The claim: {verdict}", fontsize=10.5, color=INK,
                      loc="left", pad=8)

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Not a chart
# ---------------------------------------------------------------------------

def stationary_point_summary(results: Sequence) -> str:
    """The turning-point breakdown, as text.

    **Deliberately not a figure.** Every one of the fitted surfaces came out the
    same kind of turning point, so a bar chart would be a single bar — which
    conveys less than the sentence does and takes a quarter page to do it. A
    chart of one category is not a chart.

    If a future run produces a genuine mix, this becomes worth drawing. It is
    not worth drawing now.
    """
    kinds: dict[str, int] = {}
    for r in results:
        if not r.is_valid:
            continue
        k = r.stationary_kind.get("second_order", "n/a")
        kinds[k] = kinds.get(k, 0) + 1
    total = sum(kinds.values())
    if len(kinds) == 1:
        only = next(iter(kinds))
        return (
            f"Every one of the {total} fitted surfaces was a {only}. "
            "The specification predicted a mix, and specifically warned that "
            "tight settings would produce minima. It was wrong, cleanly. "
            "(Reported as text rather than a figure: a chart of one category "
            "is not a chart.)"
        )
    parts = ", ".join(f"{v} {k}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
    return f"Turning points across {total} fitted surfaces: {parts}."


def make_all_figures(results: Sequence, out_dir: Path,
                     kappas=(0.6, 0.7, 0.8, 0.9)) -> dict[str, Path | str]:
    """Write every figure. Returns a map of name to path, plus the text summary.

    Ordering note: ``headroom`` is produced first and belongs first in the
    paper. The reader needs to know the comparison *could* show something
    before being told what it showed.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "headroom": figure_headroom(results, out_dir / "e4-headroom.png", kappas),
        "over_prediction": figure_over_prediction(
            results, out_dir / "e4-over-prediction.png", kappas),
        "discrimination": figure_discrimination(
            results, out_dir / "e4-discrimination.png", kappas),
        "stationary_points": stationary_point_summary(results),
    }
