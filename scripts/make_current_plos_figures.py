#!/usr/bin/env python3
"""PLOS figures — Mock A: lead with SPADE’s region win.

Fig 1  Method selection (when to use SPADE)
Fig 2  MAIN: absolute certified volume + containment honesty
Fig 3  Point trade-off (secondary; framed as different job)
Fig 4  Extra SPADE wins (C4 vs LHS; C6 Hill biology case)

Layout: reserved annotation bands; no overlapping labels.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
CMP = ROOT / "research" / "results" / "comparisons"
OUT = ROOT / "results" / "paper-figures" / "plos"
FAMILIES = ["hill", "ackley", "hartmann6", "levy", "rosenbrock"]
INK = "#111827"
SPADE = "#0072B2"
QLOG = "#D55E00"
DOE = "#009E73"
DOE2 = "#66C2A5"
MUTED = "#6B7280"
SESOI = 0.02
C_GRID = [1.0, 1.5, 2.0, 3.0]
# Locked ledger display values
C3_MEAN, C3_LO, C3_HI = 0.000855, 0.000691, 0.001028
C1_MEAN, C1_LO, C1_HI = -0.0005, -0.0221, 0.0207
C2_DOE_REGRET = (0.1026, 0.0486, 0.1578)  # SPADE−DoE
C4_MEAN = -0.0783  # SPADE−LHS

for p in [
    ROOT / ".worktrees/paper-ready/software/scripts",
    ROOT / "software/scripts",
    ROOT / "scripts",
]:
    if (p / "analyse_lc_confirmatory.py").exists():
        sys.path.insert(0, str(p))
        break
from analyse_lc_confirmatory import ALPHA, boot, load, lofo  # noqa: E402


def style() -> None:
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.titlesize": 9,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.edgecolor": INK,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def panel_letter(ax, letter: str) -> None:
    ax.text(
        -0.08, 1.06, letter, transform=ax.transAxes,
        fontsize=11, fontweight="bold", color=INK, va="bottom", ha="right",
        clip_on=False,
    )


def fmt_p(p: float) -> str:
    if p < 0.0001:
        return "p<0.0001"
    if p < 0.001:
        return f"p={p:.3f}"
    if p < 0.01:
        return f"p={p:.3f}"
    return f"p={p:.2f}"


def load_dc_regret():
    rows = []
    for fam in FAMILIES:
        raw = json.loads((CMP / f"dc-{fam}.json").read_text())
        data = raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw
        rows.extend(data)

    def get(r, *keys, default=None):
        for k in keys:
            if k in r:
                return r[k]
        return default

    by = {}
    for r in rows:
        arm = str(get(r, "arm", "method", default="")).lower()
        rounds = int(get(r, "rounds", "R", "n_rounds", default=-1))
        fam = get(r, "family", "fam")
        seed = int(get(r, "seed", "campaign_seed", default=-1))
        regret = float(get(r, "regret", "simple_regret", default=math.nan))
        if fam is None or seed < 0 or math.isnan(regret):
            continue
        by[(arm, rounds, fam, seed)] = regret

    def pick(arm_opts, R, fam, seed):
        for a in arm_opts:
            if (a, R, fam, seed) in by:
                return by[(a, R, fam, seed)]
        return None

    seeds = sorted({k[3] for k in by})
    spade_q, spade_doe = [], []
    for fam in FAMILIES:
        for seed in seeds:
            s5 = pick(["spade", "spade_r5", "spade5"], 5, fam, seed)
            q10 = pick(["qlognei", "qlognei_r10", "qlognei10"], 10, fam, seed)
            doe3 = pick(["doe", "doe_screened", "screened_doe", "rsm", "doe_screen"], 3, fam, seed)
            if s5 is not None and q10 is not None:
                spade_q.append(s5 - q10)
            if s5 is not None and doe3 is not None:
                spade_doe.append(s5 - doe3)
    if len(spade_q) < 10:
        raise SystemExit(f"DC parse failed; n={len(by)}")
    return spade_q, spade_doe


def fig1():
    """Study-design schematic: fixed campaign → two decisions → method roles."""
    style()
    fig = plt.figure(figsize=(7.2, 2.85))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.86, bottom=0.08)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Study design under a fixed 48-well budget", pad=8, fontsize=10, color=INK)

    # Panel letters via small tags on each column
    def card(x, y, w, h, face, edge, title, body, letter):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, transform=ax.transAxes,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor=face, edgecolor=edge, linewidth=1.4, clip_on=False,
        ))
        ax.text(x + 0.015, y + h - 0.02, letter, transform=ax.transAxes,
                fontsize=10, fontweight="bold", color=INK, va="top", ha="left")
        ax.text(x + w / 2, y + h - 0.10, title, transform=ax.transAxes,
                ha="center", va="top", fontsize=8.5, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + 0.10, body, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=7.2, color=MUTED, linespacing=1.3)

    # A — campaign
    card(
        0.02, 0.12, 0.28, 0.72, "#E8F1F8", SPADE,
        "One 48-well campaign",
        "Same total wells for\nevery method arm.\nMethod chooses how to\nsplit rounds and what\nto return at the end.",
        "A",
    )
    # Arrow A→B
    ax.annotate("", xy=(0.34, 0.48), xytext=(0.31, 0.48),
                xycoords=ax.transAxes, textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.2))

    # B — two decisions
    ax.add_patch(FancyBboxPatch(
        (0.35, 0.12), 0.30, 0.72, transform=ax.transAxes,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor="#FAFAFA", edgecolor=INK, linewidth=1.2, clip_on=False,
    ))
    ax.text(0.365, 0.80, "B", transform=ax.transAxes, fontsize=10, fontweight="bold", color=INK, va="top")
    ax.text(0.50, 0.78, "Two end-of-run decisions", transform=ax.transAxes,
            ha="center", va="top", fontsize=8.5, fontweight="bold", color=INK)
    # point box
    ax.add_patch(FancyBboxPatch(
        (0.37, 0.48), 0.26, 0.22, transform=ax.transAxes,
        boxstyle="round,pad=0.01,rounding_size=0.015",
        facecolor="#FDE9DD", edgecolor=QLOG, linewidth=1.1, clip_on=False,
    ))
    ax.text(0.50, 0.66, "Point recipe", transform=ax.transAxes,
            ha="center", fontsize=8, fontweight="bold", color=INK)
    ax.text(0.50, 0.52, "Score = simple regret\n(one carry-forward setting)",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=6.8, color=MUTED, linespacing=1.25)
    # region box
    ax.add_patch(FancyBboxPatch(
        (0.37, 0.18), 0.26, 0.26, transform=ax.transAxes,
        boxstyle="round,pad=0.01,rounding_size=0.015",
        facecolor="#DDF3E8", edgecolor=DOE, linewidth=1.1, clip_on=False,
    ))
    ax.text(0.50, 0.40, "Operating region", transform=ax.transAxes,
            ha="center", fontsize=8, fontweight="bold", color=INK)
    ax.text(0.50, 0.21, "Score = certified volume,\ncontainment, or abstain\nif evidence is weak",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=6.8, color=MUTED, linespacing=1.2)

    ax.annotate("", xy=(0.69, 0.48), xytext=(0.66, 0.48),
                xycoords=ax.transAxes, textcoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.2))

    # C — methods in this study
    ax.add_patch(FancyBboxPatch(
        (0.70, 0.12), 0.28, 0.72, transform=ax.transAxes,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor="#F8FAFC", edgecolor=INK, linewidth=1.2, clip_on=False,
    ))
    ax.text(0.715, 0.80, "C", transform=ax.transAxes, fontsize=10, fontweight="bold", color=INK, va="top")
    ax.text(0.84, 0.78, "Methods compared here", transform=ax.transAxes,
            ha="center", va="top", fontsize=8.5, fontweight="bold", color=INK)

    rows = [
        (0.62, SPADE, "SPADE", "Region-first; may abstain"),
        (0.44, QLOG, "qLogNEI (BO)", "Point search; region via\nshared post-processing"),
        (0.22, DOE, "DoE (RSM)", "Classical designs;\nstrong on one recipe"),
    ]
    for y, color, name, note in rows:
        ax.add_patch(FancyBboxPatch(
            (0.72, y), 0.24, 0.14, transform=ax.transAxes,
            boxstyle="round,pad=0.008,rounding_size=0.012",
            facecolor="white", edgecolor=color, linewidth=1.3, clip_on=False,
        ))
        ax.text(0.84, y + 0.095, name, transform=ax.transAxes,
                ha="center", va="top", fontsize=7.5, fontweight="bold", color=color)
        ax.text(0.84, y + 0.02, note, transform=ax.transAxes,
                ha="center", va="bottom", fontsize=6.5, color=MUTED, linespacing=1.15)
    return fig



def fig2():
    """MAIN: absolute volume bars + containment — SPADE leads visually."""
    style()
    paths = sorted(CMP.glob("lc-*.json"))
    if not paths:
        paths = sorted((ROOT / "results").glob("lc-*.json"))
    cells, _ = load(paths, ALPHA)
    sp = lofo(cells, "spade", 5, FAMILIES, C_GRID)
    qn = lofo(cells, "qlognei", 5, FAMILIES, C_GRID)
    keys = sorted(set(sp["vols"]) & set(qn["vols"]))
    sv = np.array([sp["vols"][k] for k in keys], dtype=float)
    qv = np.array([qn["vols"][k] for k in keys], dtype=float)
    spade_mean = float(sv.mean())
    qlog_mean = float(qv.mean())
    d = (sv - qv).tolist()

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), gridspec_kw={"width_ratios": [1.15, 1.0], "wspace": 0.34})
    fig.subplots_adjust(left=0.10, right=0.98, top=0.84, bottom=0.30)

    # A — locked volume contrast (readable; no microscopic comparator bar)
    ax = axes[0]
    panel_letter(ax, "A")
    ax.axhline(0, color=MUTED, lw=0.9, zorder=1)
    # Live R5 contrast for error bar; annotate locked ledger mean/CI
    m_live, lo_live, hi_live, p_vol = boot(d)
    ax.errorbar(
        [0], [C3_MEAN],
        yerr=[[C3_MEAN - C3_LO], [C3_HI - C3_MEAN]],
        fmt="o", color=SPADE, ecolor=SPADE,
        elinewidth=1.8, capsize=5, capthick=1.5, markersize=8, zorder=3,
    )
    ax.set_xlim(-0.6, 0.6)
    ax.set_xticks([])
    ax.set_ylabel("Certified volume difference\n(SPADE − qLogNEI at matched R=5)")
    ax.set_title("SPADE returns larger trusted regions", pad=8, fontsize=9, color=INK)
    # Headroom above CI
    ax.set_ylim(-0.00015, C3_HI + 0.00030)  # keep zero visible
    ax.annotate(
        f"{C3_MEAN:+.6f}",
        xy=(0, C3_MEAN), xytext=(0.28, C3_MEAN),
        fontsize=9, fontweight="bold", color=SPADE, va="center",
        arrowprops=dict(arrowstyle="-", color=SPADE, lw=0.7),
    )
    ax.text(
        0.5, -0.14,
        f"95% CI [{C3_LO:+.6f}, {C3_HI:+.6f}]   ·   {fmt_p(p_vol)}   ·   n={len(keys)}",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.0, color=MUTED, clip_on=False,
    )
    ax.text(
        0.5, -0.26,
        f"Means: SPADE {spade_mean:.6f}  ·  qLogNEI {qlog_mean:.6f}\n"
        "Matched 5 rounds · 48 wells · moderate noise · five families",
        transform=ax.transAxes, ha="center", va="top", fontsize=6.8, color=MUTED,
        clip_on=False, linespacing=1.25,
    )

    # B — containment honesty
    ax = axes[1]
    panel_letter(ax, "B")
    arms = ["SPADE", "Screened\nDoE", "Unscreened\nDoE"]
    vals = [66 / 66, 85 / 122, 77 / 134]
    counts = ["66/66", "85/122", "77/134"]
    colors = [SPADE, DOE, DOE2]
    ax.bar(range(3), vals, color=colors, edgecolor=INK, linewidth=0.8, width=0.72)
    for i, (v, c) in enumerate(zip(vals, counts)):
        ax.text(i, v + 0.04, f"{v:.0%}\n{c}", ha="center", va="bottom", fontsize=7.5, color=INK, linespacing=1.15)
    ax.set_ylim(0, 1.32)
    ax.set_ylabel("Observed containment\n(among answered regions)")
    ax.set_xticks(range(3))
    ax.set_xticklabels(arms, fontsize=8)
    ax.set_title("SPADE’s answered regions stay inside truth", pad=8, fontsize=9, color=INK)
    ax.text(
        0.5, -0.22,
        "Prevalence 0.30 · noise 0.25 · assurance 0.95 · 48 wells",
        transform=ax.transAxes, ha="center", va="top", fontsize=6.8, color=MUTED, clip_on=False,
    )
    return fig


def fig3(spade_q, spade_doe):
    """Point as secondary trade-off — different job, not SPADE failure."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25), gridspec_kw={"wspace": 0.30})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.80, bottom=0.30)
    fig.suptitle(
        "Point-recipe trade-off (secondary): different job than operating regions",
        fontsize=9.5, color=INK, y=0.96,
    )

    # A — vs longer BO: competitive
    m, lo, hi, p = boot(spade_q)
    # Prefer locked C1 for display consistency
    m, lo, hi = C1_MEAN, C1_LO, C1_HI
    ax = axes[0]
    panel_letter(ax, "A")
    ax.axvline(0, color=MUTED, lw=0.9, zorder=1)
    ax.axvspan(-SESOI, SESOI, color="#E5E7EB", alpha=0.9, zorder=0)
    ax.errorbar([m], [0], xerr=[[m - lo], [hi - m]], fmt="o", color=SPADE,
                ecolor=SPADE, elinewidth=1.6, capsize=4.5, capthick=1.4, markersize=7.5, zorder=3)
    ax.set_yticks([])
    ax.set_ylim(-0.6, 0.6)
    ax.set_xlim(-0.035, 0.035)
    ax.set_title("vs longer BO (qLogNEI R10)", pad=8, fontsize=9)
    ax.set_xlabel("Paired regret difference\n(positive = SPADE worse)", labelpad=6)
    ax.text(0.5, -0.40, f"{m:+.4f}  [{lo:+.4f}, {hi:+.4f}]   ·   n={len(spade_q)}   ·   {fmt_p(p)}",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0, color=MUTED, clip_on=False)
    ax.text(0.5, -0.55, "No detectable gap at half the rounds\n(not claimed as equivalence)",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.4, color=INK,
            fontstyle="italic", clip_on=False, linespacing=1.25)
    ax.text(0.98, 0.90, "±0.02 SESOI", transform=ax.transAxes, ha="right", va="top", fontsize=6.5, color=MUTED)

    # B — vs DoE: DoE wins recipe (honest, demoted framing)
    m2, lo2, hi2, p2 = boot(spade_doe)
    m2, lo2, hi2 = C2_DOE_REGRET
    ax = axes[1]
    panel_letter(ax, "B")
    ax.axvline(0, color=MUTED, lw=0.9, zorder=1)
    ax.errorbar([m2], [0], xerr=[[m2 - lo2], [hi2 - m2]], fmt="o", color=DOE,
                ecolor=DOE, elinewidth=1.6, capsize=4.5, capthick=1.4, markersize=7.5, zorder=3)
    ax.set_yticks([])
    ax.set_ylim(-0.6, 0.6)
    ax.set_xlim(-0.02, 0.20)
    ax.set_title("vs screened DoE (R3)", pad=8, fontsize=9)
    ax.set_xlabel("Paired regret difference\n(positive = SPADE worse)", labelpad=6)
    ax.text(0.5, -0.40, f"{m2:+.4f}  [{lo2:+.4f}, {hi2:+.4f}]   ·   n={len(spade_doe)}   ·   {fmt_p(p2)}",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0, color=MUTED, clip_on=False)
    ax.text(0.5, -0.55, "DoE wins the single-recipe job\n(expected when that is the goal)",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.4, color=INK,
            fontstyle="italic", clip_on=False, linespacing=1.25)
    return fig


def fig4():
    """Extra SPADE wins: C4 vs LHS + C6 Hill."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.95), gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.18)
    fig.suptitle("Additional SPADE evidence (same claim ledger)", fontsize=9.5, color=INK, y=0.96)

    # A — C4 schematic bar: SPADE better than LHS (negative = SPADE better on regret)
    ax = axes[0]
    panel_letter(ax, "A")
    # Show as "advantage" so SPADE is positive visually: −(SPADE−LHS) = LHS−SPADE
    advantage = -C4_MEAN  # +0.0783
    ax.barh([0], [advantage], color=SPADE, edgecolor=INK, height=0.45, linewidth=0.8)
    ax.set_yticks([0])
    ax.set_yticklabels(["SPADE R3 vs\none-shot LHS"])
    ax.set_xlabel("Point-regret difference\n(LHS − SPADE; higher favors SPADE)")
    ax.set_xlim(0, 0.12)
    ax.set_title("Beats one-shot space-filling (C4)", pad=8, fontsize=9)
    ax.text(advantage + 0.003, 0, f"{advantage:.3f}\n(locked C4:\nLHS−SPADE)",
            va="center", ha="left", fontsize=7.2, color=INK, linespacing=1.2)
    ax.text(0.5, -0.22, "n=80 · four LA families × 20 seeds", transform=ax.transAxes,
            ha="center", va="top", fontsize=7.0, color=MUTED, clip_on=False)

    # B — C6 Hill answer rates
    ax = axes[1]
    panel_letter(ax, "B")
    # Locked: SPADE 40/64, qLogNEI 27/64 at p=.70 Hill
    labs = ["SPADE", "qLogNEI"]
    vals = [40 / 64, 27 / 64]
    colors = [SPADE, QLOG]
    ax.bar(range(2), vals, color=colors, edgecolor=INK, linewidth=0.8, width=0.55)
    for i, (v, c) in enumerate(zip(vals, ["40/64", "27/64"])):
        ax.text(i, v + 0.03, f"{v:.0%}\n{c} answered\n(all contained)", ha="center", va="bottom",
                fontsize=7.2, color=INK, linespacing=1.15)
    ax.set_ylim(0, 1.05)
    ax.set_xticks(range(2))
    ax.set_xticklabels(labs)
    ax.set_ylabel("Answer rate\n(biology-shaped Hill, p=0.70)")
    ax.set_title("More trusted answers on Hill (C6)", pad=8, fontsize=9)
    ax.text(0.5, -0.22, "c=1.0 · α=0.95 · both arms perfect among answered",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0, color=MUTED, clip_on=False)
    return fig


def save(fig, stem, caption, alt):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{ext}", bbox_inches="tight", pad_inches=0.08,
                    facecolor="white", edgecolor="none")
    try:
        fig.savefig(
            OUT / f"{stem}.tiff", dpi=300, bbox_inches="tight", pad_inches=0.08,
            facecolor="white", pil_kwargs={"compression": "tiff_lzw"},
        )
    except Exception as e:
        print("tiff skip", stem, e)
    (OUT / f"{stem}.caption.txt").write_text(caption.strip() + "\n")
    (OUT / f"{stem}.alt.txt").write_text(alt.strip() + "\n")
    (OUT / f"{stem}.description.txt").write_text(caption.strip() + "\n")
    plt.close(fig)
    print("wrote", stem)


def main():
    spade_q, spade_doe = load_dc_regret()
    print("DC n", len(spade_q), len(spade_doe))

    save(
        fig1(), "fig1",
        "Fig 1. Study design under a fixed 48-well budget. "
        "(A) Every compared arm uses the same 48-well campaign total; the method chooses round structure and the terminal return. "
        "(B) The same wells can be scored as a point-recipe decision (simple regret) or as an operating-region decision "
        "(certified volume, truth containment, or abstention). "
        "(C) SPADE is evaluated as the region-first architecture; qLogNEI is the noisy Bayesian-optimization comparator; "
        "DoE pipelines are classical response-surface designs that often win the single-recipe job. "
        "This schematic defines the benchmark and contains no performance result.",
        "Three-panel study schematic: fixed 48-well campaign, point versus region decisions, and compared methods.",
    )
    save(
        fig2(), "fig2",
        "Fig 2. SPADE’s primary advantage: trusted operating regions. "
        "(A) Certified-volume difference (SPADE minus qLogNEI) at matched five rounds under leave-one-family-out "
        "calibration: +0.000855 (95% CI [+0.000691, +0.001028], p<0.0001, n=320); absolute means are noted under the panel. "
        "(B) Observed truth containment among answered regions at prevalence 0.30: "
        "SPADE 66/66 versus screened DoE 85/122 and unscreened DoE 77/134.",
        "Certified-volume contrast and containment bars favoring SPADE on the region decision.",
    )
    save(
        fig3(spade_q, spade_doe), "fig3",
        "Fig 3. Point-recipe trade-off (secondary to the region decision). "
        "(A) SPADE at five rounds minus qLogNEI at ten rounds on simple regret: no detectable difference "
        "(−0.0005, 95% CI [−0.0221, +0.0207], n=160); not claimed as equivalence. "
        "(B) SPADE at five rounds minus screened DoE at three rounds: DoE finds the better single recipe "
        "(+0.1026, 95% CI [+0.0486, +0.1578]); expected when the goal is one point rather than a region.",
        "Secondary forest plots framing point regret as a different job from operating regions.",
    )
    save(
        fig4(), "fig4",
        "Fig 4. Additional locked SPADE evidence. "
        "(A) At three rounds SPADE has lower regret than one-shot Latin hypercube sampling "
        "(SPADE−LHS −0.0783; shown as positive SPADE advantage). "
        "(B) On the biology-shaped Hill family at prevalence 0.70, SPADE answers 40/64 trusted regions "
        "versus 27/64 for qLogNEI; both arms contain truth in every answered cell.",
        "C4 regret advantage versus LHS and C6 Hill answer-rate comparison.",
    )


if __name__ == "__main__":
    main()
