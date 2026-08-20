"""Publication figures for the matched-budget DoE vs BO paper.

Numbers come from committed JSON. Empty cells stay empty. GP in-region uses
the stored unconstrained GP peak, which the manuscript states already lies
inside the sampled region.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from PIL import Image

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target
from boec.diagnostics import instance_bootstrap
from boec.tost import per_instance

__all__ = [
    "COLOURS",
    "OUT_DIR",
    "PNG_DPI",
    "ROOT",
    "figure_cost",
    "figure_saddle",
    "figure_terminal_rules",
    "figure_turbo",
    "make_paper_figures",
    "q62_locked_payload",
]

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "figures"

CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
CELL_TITLES = {
    (6, 0.25): "6 factors,  σ = 0.25",
    (6, 0.10): "6 factors,  σ = 0.10",
    (8, 0.25): "8 factors,  σ = 0.25",
    (8, 0.10): "8 factors,  σ = 0.10",
}
LOCATORS = (
    ("tested", "Hidden\nbest"),
    ("measured", "Measured\nargmax"),
    ("unconstrained", "Unconstrained\nmodel"),
    ("inregion", "In-region\nmodel"),
)
CAP, DIM, PIPELINE = 200, 6, 48
HIT_TARGET = 0.10
Q56_RULE = "path_argmax"

# Okabe–Ito, colour-blind safe.
COLOURS = {
    "doe": "#D55E00",
    "qlogei": "#0072B2",
    "qlognei": "#009E73",
    "ascent": "#CC79A7",
    "oneshot": "#56B4E9",
    "turbo": "#E69F00",
}
INK = "#1B1D21"
MUTED = "#5E6772"
HAIR = "#D9DEE5"
BAND = "#F3F5F7"
SESOI = 0.02
FONT = "Helvetica Neue"
PNG_DPI = 800


def _configure() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8,
        "axes.unicode_minus": False,
        "axes.linewidth": 0.6,
        "axes.labelsize": 8,
        "axes.titlesize": 8.5,
        "axes.titleweight": "regular",
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.8,
        "ytick.major.size": 2.8,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "pdf.use14corefonts": False,
        "mathtext.fontset": "custom",
        "mathtext.rm": FONT,
        "mathtext.it": FONT,
        "mathtext.bf": FONT,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "figure.dpi": 150,
        "savefig.facecolor": "white",
        "savefig.dpi": PNG_DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "lines.antialiased": True,
        "patch.antialiased": True,
        "path.simplify": False,
    })


def _style(ax, *, grid: str | None = "y") -> None:
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
        ax.spines[side].set_linewidth(0.6)
    ax.tick_params(colors=INK, length=2.8, width=0.6, pad=2.5)
    ax.grid(False)
    if grid == "y":
        ax.yaxis.grid(True, color=HAIR, linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.tick_params(axis="y", which="minor", left=False)


def _letter(ax, s: str) -> None:
    ax.text(
        -0.12, 1.08, s, transform=ax.transAxes, fontsize=11,
        fontweight="bold", color=INK, ha="right", va="bottom",
        fontfamily=FONT, clip_on=False,
    )


def _load(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


def _cell(rows: list[dict], dim: int, sigma: float, inst_key: str = "instance") -> list[dict]:
    return [
        r for r in rows
        if int(r["dim"]) == dim and abs(float(r["sigma"]) - sigma) < 1e-12
        and inst_key in r
    ]


def _ci(vals: np.ndarray) -> tuple[float, float, float]:
    return instance_bootstrap(vals, n_boot=4000, seed=0)


def _save(fig, stem: Path) -> dict[str, Path]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    pdf = stem.with_suffix(".pdf")
    png = stem.with_suffix(".png")
    fig.savefig(
        pdf, format="pdf", bbox_inches="tight", facecolor="white",
        edgecolor="none", dpi=PNG_DPI,
    )
    fig.savefig(
        png, format="png", bbox_inches="tight", facecolor="white",
        edgecolor="none", dpi=PNG_DPI, transparent=False,
        pil_kwargs={"dpi": (PNG_DPI, PNG_DPI)},
    )
    image = Image.open(png).convert("RGB")
    image.save(png, format="PNG", dpi=(PNG_DPI, PNG_DPI), optimize=True)
    plt.close(fig)
    return {"pdf": pdf, "png": png}


def _q57() -> list[dict]:
    return _load(ROOT / "results" / "q57-search-vs-id.json")


def _q34() -> list[dict]:
    return _load(ROOT / "results" / "q34-factorial.json")


def _q35() -> list[dict]:
    return _load(ROOT / "results" / "q35-constrained-rsm.json")


def locator_means(dim: int, sigma: float) -> dict[str, dict[str, tuple[float, float, float] | None]]:
    """Landscape-mean regret and 95% bootstrap interval, or None if not stored."""
    q57 = _cell(_q57(), dim, sigma)
    q35 = _cell(_q35(), dim, sigma)
    q34 = _cell(_q34(), dim, sigma)
    out: dict[str, dict[str, tuple[float, float, float] | None]] = {}
    keys = {
        "doe": ("doe_oracle_best", "doe_rule_a"),
        "qlogei": ("bo_oracle_best", "bo_rule_a"),
        "qlognei": ("nei_oracle_best", "nei_rule_a"),
    }
    for arm, (tested_k, measured_k) in keys.items():
        tested = _ci(per_instance(q57, tested_k))
        measured = _ci(per_instance(q57, measured_k))
        unconstrained = inregion = None
        if arm == "doe":
            unconstrained = _ci(per_instance(q35, "unconstrained"))
            inregion = _ci(per_instance(q35, "constrained"))
        elif arm == "qlogei":
            gp = _ci(per_instance(q34, "cell4_bo_gp"))
            unconstrained = gp
            inregion = gp
        out[arm] = {
            "tested": tested,
            "measured": measured,
            "unconstrained": unconstrained,
            "inregion": inregion,
        }
    return out


def winner_reverses() -> int:
    """Cells in which DoE vs qLogEI rank flips between measured and unconstrained."""
    n = 0
    for dim, sigma in CELLS:
        m = locator_means(dim, sigma)
        dm, du = m["doe"]["measured"][0], m["doe"]["unconstrained"][0]
        bm, bu = m["qlogei"]["measured"][0], m["qlogei"]["unconstrained"][0]
        if (dm < bm) != (du < bu):
            n += 1
    return n


def figure_terminal_rules(path: Path) -> dict[str, Path]:
    """Figure 1. Same 48-well campaigns under four terminal rules."""
    _configure()
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.85), sharey=True)
    fig.patch.set_facecolor("white")
    arms = (("doe", "DoE/RSM"), ("qlogei", "qLogEI"), ("qlognei", "qLogNEI"))
    width = 0.23
    xs = np.arange(len(LOCATORS), dtype=float)

    for ax, (dim, sigma) in zip(axes.ravel(), CELLS, strict=True):
        _style(ax)
        ax.axvspan(-0.5, 1.5, color=BAND, zorder=0, lw=0)
        ax.axvline(1.5, color=HAIR, linewidth=0.7, zorder=1)
        means = locator_means(dim, sigma)
        for i, (arm, _label) in enumerate(arms):
            offset = (i - 1) * width
            for j, (loc, _) in enumerate(LOCATORS):
                cell = means[arm][loc]
                x = xs[j] + offset
                if cell is None:
                    continue
                m, lo, hi = cell
                ax.bar(
                    x, m, width=width * 0.86, color=COLOURS[arm],
                    edgecolor="none", zorder=3, linewidth=0,
                )
                ax.errorbar(
                    x, m, yerr=[[m - lo], [hi - m]], fmt="none",
                    ecolor=COLOURS[arm], elinewidth=0.7, capsize=0, capthick=0.7,
                    zorder=4,
                )
        ax.set_xlim(-0.55, 3.55)
        ax.set_xticks(xs)
        ax.set_xticklabels([lab for _, lab in LOCATORS], fontsize=7, color=INK, linespacing=1.15)
        title = CELL_TITLES[(dim, sigma)]
        ax.set_title(title, loc="left", fontsize=8.5, color=INK, pad=8)
        if (dim, sigma) == (6, 0.25):
            ax.text(
                1.0, 1.08, "primary", transform=ax.transAxes, fontsize=7,
                color=MUTED, ha="right", va="bottom", style="italic",
                fontfamily=FONT,
            )

    for ax, letter in zip(axes.ravel(), "abcd", strict=True):
        _letter(ax, letter)
    axes[0, 0].set_ylim(0, 0.50)
    axes[0, 0].set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    axes[0, 0].set_ylabel("Simple regret", fontsize=8.5, color=INK)
    axes[1, 0].set_ylabel("Simple regret", fontsize=8.5, color=INK)

    handles = [
        Patch(facecolor=COLOURS[a], edgecolor="none", label=lab) for a, lab in arms
    ]
    fig.legend(
        handles=handles, loc="upper center", ncol=3, frameon=False,
        fontsize=8, bbox_to_anchor=(0.54, 1.01), handlelength=0.95,
        handleheight=0.85, columnspacing=1.6, borderaxespad=0,
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.88, bottom=0.11,
                        wspace=0.18, hspace=0.48)
    if winner_reverses() < 1:
        raise AssertionError(
            "Figure 1 exists to show a rank reversal; none is present in the JSON.")
    return _save(fig, path)


def _rounds(arm: str, n: int) -> int:
    if arm == "doe":
        return 3 * (n // PIPELINE)
    if arm == "qlogei":
        n_init = 2 * DIM + 2
        return 1 if n <= n_init else 1 + math.ceil((n - n_init) / 4)
    return 1


def _ascent_by_instance() -> dict[tuple[str, float], list[dict]]:
    """Walking RSM campaigns grouped by landscape. Both seeds are required."""
    by: dict[tuple[str, float], list[dict]] = {}
    for r in json.loads((ROOT / "results" / "q56-doe-ascent.json").read_text())["rows"]:
        if r.get("ascent_rule", Q56_RULE) != Q56_RULE:
            continue
        by.setdefault((r["instance_id"], float(r["sigma"])), []).append(r)
    return by


def hit_series(
    sigma: float, target: float = HIT_TARGET,
) -> dict[str, list[tuple[int, float, int | None]]]:
    """(n, P(T<=n), rounds) for each named arm. Failure stays in the denominator."""
    rows = [
        r for r in json.loads((ROOT / "results" / "q52-budget-to-target.json").read_text())["rows"]
        if abs(float(r["sigma"]) - sigma) < 1e-9
    ]
    ascent = {
        k: v for k, v in _ascent_by_instance().items() if abs(k[1] - sigma) < 1e-9
    }
    out: dict[str, list[tuple[int, float, int | None]]] = {}
    grid = sorted({int(k) for r in rows for k in r["arms"]["qlogei"]["rule_a"]})
    for arm in ("qlogei", "doe", "spread_gp"):
        pts = []
        for n in grid:
            hits = sum(
                1 for r in rows
                if first_budget_to_target(r["arms"][arm]["rule_a"], target=target, cap=n)
                is not ARRIVAL_CENSORED
            )
            pts.append((n, hits / len(rows), _rounds(arm, n)))
        out[arm] = pts
    if ascent:
        pts = []
        for n in grid:
            hits = 0
            for seeds in ascent.values():
                arrs = [
                    first_budget_to_target(r["rule_a"], target=target, cap=n)
                    for r in seeds
                ]
                if arrs and all(a is not ARRIVAL_CENSORED for a in arrs):
                    hits += 1
            pts.append((n, hits / len(ascent), None))
        out["ascent"] = pts
    return out


def figure_cost(path: Path) -> dict[str, Path]:
    """Figure 2. Probability of reaching regret 0.10, in wells and in rounds."""
    _configure()
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.7), sharey=True)
    fig.patch.set_facecolor("white")
    series = (
        ("qlogei", "qLogEI", COLOURS["qlogei"], 1.9),
        ("ascent", "Walking RSM", COLOURS["ascent"], 1.9),
        ("doe", "CCD in place", COLOURS["doe"], 1.5),
        ("spread_gp", "One-shot GP", COLOURS["oneshot"], 1.7),
    )
    for row, sigma in enumerate((0.25, 0.10)):
        data = hit_series(sigma)
        for col, mode in enumerate(("wells", "rounds")):
            ax = axes[row, col]
            _style(ax)
            if mode == "wells":
                ax.axvline(PIPELINE, color=HAIR, linewidth=0.8, linestyle=(0, (3, 2.2)), zorder=1)
            for key, _lab, colour, lw in series:
                if key not in data:
                    continue
                if mode == "rounds" and key == "ascent":
                    continue
                pts = data[key]
                if mode == "wells":
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    ax.plot(
                        xs, ys, color=colour, linewidth=lw, solid_capstyle="round",
                        solid_joinstyle="round", zorder=3,
                    )
                    mark = next(((n, p) for n, p, _r in pts if n == PIPELINE), None)
                    if mark is not None:
                        ax.scatter(
                            [mark[0]], [mark[1]], s=22, facecolor="white",
                            edgecolor=colour, linewidth=1.15, zorder=5,
                        )
                else:
                    xs, ys = [], []
                    for n, p, r in pts:
                        if r is None or r <= 0:
                            continue
                        if key == "spread_gp" and n != PIPELINE:
                            continue
                        xs.append(r)
                        ys.append(p)
                    if not xs:
                        continue
                    order = np.argsort(xs)
                    xs = list(np.array(xs)[order])
                    ys = list(np.array(ys)[order])
                    if key == "spread_gp":
                        ax.scatter(
                            xs, ys, s=42, marker="D", facecolor=colour,
                            edgecolor="white", linewidth=0.6, zorder=5,
                        )
                    else:
                        ax.plot(
                            xs, ys, color=colour, linewidth=lw,
                            solid_capstyle="round", zorder=3,
                        )
            ax.set_ylim(-0.02, 1.05)
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["0", "0.25", "0.50", "0.75", "1.00"])
            if mode == "wells":
                ax.set_xscale("log")
                ax.set_xlim(7, 230)
                ax.set_xticks([8, 16, 32, 48, 100, 200])
                ax.set_xticklabels(["8", "16", "32", "48", "100", "200"])
                ax.xaxis.set_minor_locator(plt.NullLocator())
                if row == 1:
                    ax.set_xlabel("Evaluations (wells)", fontsize=8, color=INK)
            else:
                ax.set_xscale("log")
                ax.set_xlim(0.75, 58)
                ax.set_xticks([1, 3, 6, 10, 24, 48])
                ax.set_xticklabels(["1", "3", "6", "10", "24", "48"])
                ax.xaxis.set_minor_locator(plt.NullLocator())
                if row == 1:
                    ax.set_xlabel("Sequential rounds", fontsize=8, color=INK)
            if row == 0:
                ax.set_title(
                    "Wells" if col == 0 else "Rounds",
                    loc="left", fontsize=8.5, color=INK, pad=8,
                )

    for ax, letter in zip(axes.ravel(), "abcd", strict=True):
        _letter(ax, letter)

    axes[0, 0].set_ylabel("P(regret ≤ 0.10)", fontsize=8.5, color=INK)
    axes[1, 0].set_ylabel("P(regret ≤ 0.10)", fontsize=8.5, color=INK)
    fig.text(0.015, 0.70, "σ = 0.25", rotation=90, va="center", ha="center",
             fontsize=8, color=MUTED, fontfamily=FONT)
    fig.text(0.015, 0.28, "σ = 0.10", rotation=90, va="center", ha="center",
             fontsize=8, color=MUTED, fontfamily=FONT)

    axes[0, 0].text(
        PIPELINE, 1.02, "N = 48", ha="center", va="bottom", fontsize=6.5,
        color=MUTED, fontfamily=FONT, clip_on=False,
    )

    handles = [
        Line2D([0], [0], color=c, linewidth=2.0, label=lab, solid_capstyle="round")
        for _, lab, c, _ in series
    ]
    fig.legend(
        handles=handles, loc="upper center", ncol=4, frameon=False,
        fontsize=8, bbox_to_anchor=(0.54, 1.01), columnspacing=1.4,
        handlelength=1.8, borderaxespad=0,
    )
    fig.subplots_adjust(left=0.13, right=0.98, top=0.88, bottom=0.10,
                        wspace=0.16, hspace=0.38)
    return _save(fig, path)


def saddle_stats() -> dict:
    rows = _q35()
    kinds = [r["stationary_kind"] for r in rows]
    n_saddle = sum(k == "saddle" for k in kinds)
    primary = _cell(rows, 6, 0.25)
    unc = per_instance(primary, "unconstrained")
    con = per_instance(primary, "constrained")
    gap = unc - con
    g_mean, g_lo, g_hi = _ci(gap)
    exits = [r["ridge_exit_radius"] for r in rows if r.get("ridge_exit_radius") is not None]
    corners = [r["ridge_region_corner_radius"] for r in rows]
    gp = per_instance(_cell(_q34(), 6, 0.25), "cell4_bo_gp")
    inregion_gap = con - gp
    ir_mean, ir_lo, ir_hi = _ci(inregion_gap)
    return {
        "n": len(rows),
        "n_saddle": n_saddle,
        "unc": float(unc.mean()),
        "con": float(con.mean()),
        "gp": float(gp.mean()),
        "gap": g_mean,
        "gap_lo": g_lo,
        "gap_hi": g_hi,
        "inregion": ir_mean,
        "inregion_lo": ir_lo,
        "inregion_hi": ir_hi,
        "ridge_exit": float(np.median(exits)) if exits else None,
        "ridge_corner": float(np.median(corners)) if corners else None,
    }


def figure_saddle(path: Path) -> dict[str, Path]:
    """Figure 3. Saddle geometry and the unconstrained minus in-region gap."""
    _configure()
    s = saddle_stats()
    if s["n_saddle"] != s["n"]:
        raise AssertionError(
            f"Figure 3 claims every quadratic is a saddle; got {s['n_saddle']}/{s['n']}.")
    fig = plt.figure(figsize=(7.2, 3.45))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.18], wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])

    muted = LinearSegmentedColormap.from_list(
        "saddle_muted",
        ["#2F4A6E", "#F4F1EC", "#B23A2F"],
    )
    x = np.linspace(-1.08, 1.08, 360)
    y = np.linspace(-1.08, 1.08, 360)
    X, Y = np.meshgrid(x, y)
    Z = X**2 - Y**2
    norm = TwoSlopeNorm(vmin=-1.05, vcenter=0.0, vmax=1.05)
    ax0.contourf(X, Y, Z, levels=9, cmap=muted, norm=norm)
    ax0.contour(X, Y, Z, levels=9, colors="white", linewidths=0.35, alpha=0.55)
    region = 0.44
    box = Rectangle(
        (-region, -region), 2 * region, 2 * region, fill=False,
        edgecolor=INK, linewidth=1.2, linestyle=(0, (3.5, 2.0)), zorder=4,
    )
    ax0.add_patch(box)
    ax0.plot([0, region], [0, 0], color=COLOURS["oneshot"], linewidth=1.7, zorder=5,
             solid_capstyle="round")
    ax0.plot(
        [region, 0.92], [0, 0], color=COLOURS["doe"], linewidth=1.35,
        linestyle=(0, (2.6, 1.5)), zorder=5, solid_capstyle="round",
    )
    ax0.scatter([0], [0], s=28, color=INK, zorder=6, edgecolors="white", linewidths=0.55)
    ax0.scatter(
        [region], [0], s=40, color=COLOURS["oneshot"], zorder=6,
        edgecolors="white", linewidths=0.7,
    )
    ax0.scatter(
        [0.92], [0], s=40, color=COLOURS["doe"], zorder=6,
        edgecolors="white", linewidths=0.7,
    )
    ax0.annotate(
        "saddle", xy=(0.02, 0.04), xytext=(0.08, 0.70),
        fontsize=7.5, color=INK, ha="left",
        arrowprops=dict(arrowstyle="-", color=INK, lw=0.55, shrinkA=0, shrinkB=2),
    )
    ax0.annotate(
        "in-region peak", xy=(region, -0.03), xytext=(-0.02, -0.78),
        fontsize=7.5, color=COLOURS["oneshot"], ha="center",
        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.55, shrinkA=0, shrinkB=2),
    )
    ax0.annotate(
        "unconstrained peak", xy=(0.92, 0.04), xytext=(0.18, 0.86),
        fontsize=7.5, color=COLOURS["doe"], ha="left",
        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.55, shrinkA=0, shrinkB=2),
    )
    ax0.set_xlim(-1.08, 1.08)
    ax0.set_ylim(-1.08, 1.08)
    ax0.set_aspect("equal")
    ax0.set_xticks([])
    ax0.set_yticks([])
    for side in ax0.spines.values():
        side.set_visible(True)
        side.set_color(INK)
        side.set_linewidth(0.5)
    ax0.set_title("Fitted quadratic is a saddle", loc="left", fontsize=8.5, color=INK, pad=8)
    ax0.text(
        0.0, -0.10,
        f"{s['n_saddle']}/{s['n']} Hill fits are saddles"
        f"  ·  ridge exits at {s['ridge_exit']:.2f}  (corner {s['ridge_corner']:.2f})",
        transform=ax0.transAxes, ha="left", va="top", fontsize=6.5,
        color=MUTED, fontfamily=FONT, clip_on=False,
    )
    ax0.text(
        -0.04, 1.08, "a", transform=ax0.transAxes, fontsize=11, fontweight="bold",
        color=INK, ha="right", va="bottom", fontfamily=FONT, clip_on=False,
    )

    _style(ax1, grid=None)
    ax1.axvspan(-SESOI, SESOI, color="#E7EEF3", lw=0, zorder=0)
    ax1.axvline(0, color=INK, linewidth=0.7, zorder=2)
    ax1.text(
        0.0, 1.55, "±0.02", ha="center", va="bottom", fontsize=6.5, color=MUTED,
        fontfamily=FONT,
    )
    rows = [
        ("Unconstrained − in-region\nDoE quadratic", s["gap"], s["gap_lo"], s["gap_hi"],
         COLOURS["doe"]),
        ("In-region DoE − GP\nprimary setting", s["inregion"], s["inregion_lo"],
         s["inregion_hi"], COLOURS["qlogei"]),
    ]
    for y, (_lab, m, lo, hi, colour) in enumerate(reversed(rows)):
        ax1.plot([lo, hi], [y, y], color=colour, linewidth=2.3,
                 solid_capstyle="round", zorder=3)
        ax1.scatter(
            [m], [y], s=44, color=colour, zorder=4,
            edgecolors="white", linewidths=0.8,
        )
        ax1.text(hi + 0.014, y, f"{m:+.3f}", ha="left", va="center",
                 fontsize=8, color=colour, fontfamily=FONT)
    ax1.set_yticks([0, 1])
    ax1.set_yticklabels([rows[1][0], rows[0][0]], fontsize=7.5, color=INK, linespacing=1.25)
    ax1.tick_params(axis="y", length=0, pad=7)
    ax1.set_xlabel("Regret difference", fontsize=8, color=INK)
    ax1.set_xlim(-0.055, 0.40)
    ax1.set_ylim(-0.7, 1.7)
    ax1.spines["left"].set_visible(False)
    ax1.set_title("Extrapolation, not search", loc="left", fontsize=8.5, color=INK, pad=8)
    ax1.text(
        -0.08, 1.08, "b", transform=ax1.transAxes, fontsize=11, fontweight="bold",
        color=INK, ha="right", va="bottom", fontfamily=FONT, clip_on=False,
    )
    fig.subplots_adjust(left=0.02, right=0.97, top=0.84, bottom=0.20)
    return _save(fig, path)


def q62_locked_payload(path: Path | None = None) -> dict | None:
    """Return Q62 JSON only when it is a finished 25-landscape grid, not smoke."""
    p = Path(path) if path is not None else ROOT / "results" / "q62-turbo.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    if data.get("smoke"):
        return None
    if int(data.get("budget", 0)) != 48:
        return None
    rows = data.get("rows") or []
    n_inst = len({r["instance"] for r in rows})
    if n_inst < 25:
        return None
    return data


def figure_turbo(path: Path, payload: dict | None = None) -> dict[str, Path]:
    """Measured-argmax means: 48-well DoE, unconstrained qLogNEI, TuRBO-1 qLogNEI."""
    data = payload if payload is not None else q62_locked_payload()
    if data is None:
        raise ValueError("Q62 figure needs a locked 25-landscape grid, not a smoke run")
    _configure()
    summary = {float(s["sigma"]): s for s in data["summary"]}
    fig, ax = plt.subplots(figsize=(5.4, 2.6), dpi=PNG_DPI)
    series = [
        ("DoE / RSM", "stored_doe", COLOURS["doe"]),
        ("qLogNEI, full box", "stored_qlognei", COLOURS["qlognei"]),
        ("TuRBO-1 qLogNEI", "turbo_measured", COLOURS["turbo"]),
    ]
    x = np.arange(2)
    width = 0.24
    for i, (lab, key, colour) in enumerate(series):
        vals = [summary[0.25][key], summary[0.10][key]]
        ax.bar(
            x + (i - 1) * width, vals, width=width, color=colour, label=lab,
            edgecolor="white", linewidth=0.4, zorder=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(["σ = 0.25", "σ = 0.10"], color=INK)
    ax.set_ylabel("Simple regret (measured argmax)", color=INK)
    ax.set_title(
        "Locally constrained BO is a sampling rule, not a new readout",
        loc="left", fontsize=8.5, color=INK, pad=8,
    )
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(HAIR)
    ax.spines["bottom"].set_color(HAIR)
    ax.tick_params(colors=INK, length=3)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=HAIR, linewidth=0.5)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.82, bottom=0.18)
    return _save(fig, path)


def make_paper_figures(out_dir: Path | None = None) -> dict[str, dict[str, Path]]:
    _configure()
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "fig1": figure_terminal_rules(out / "fig1-terminal-rules"),
        "fig2": figure_cost(out / "fig2-cost"),
        "fig3": figure_saddle(out / "fig3-saddle"),
    }
    locked = q62_locked_payload()
    if locked is not None:
        paths["fig4"] = figure_turbo(out / "fig4-turbo", payload=locked)
    return paths
