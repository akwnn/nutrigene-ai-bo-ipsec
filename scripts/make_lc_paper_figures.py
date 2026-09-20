#!/usr/bin/env python3
"""Build PLOS fig1–4 from LC confirmatory results (5-round / certified-volume story)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyse_lc_confirmatory import (  # noqa: E402
    ALPHA,
    SESOI,
    boot,
    load,
    lofo,
    regret_pair,
)

C_GRID = [1.0, 1.5, 2.0, 3.0]


OUT = ROOT / "results" / "paper-figures" / "plos"
FAMILIES = ["hill", "ackley", "hartmann6", "levy", "rosenbrock"]
INK = "#243746"
SPADE_C = "#0072B2"
QLOG_C = "#D55E00"
MUTED = "#6B7280"
SESOI_FILL = "#E5E7EB"


def _style():
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _panel(ax, label):
    ax.text(
        -0.12,
        1.05,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="bottom",
        color=INK,
    )


def build_fig1():
    """Schematic: point vs claimed region; matched 48-well round schedules."""
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
    # A: one campaign
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    _panel(ax, "A")
    ax.add_patch(FancyBboxPatch((1, 3), 8, 4, boxstyle="round,pad=0.2", facecolor="#E8F1F8", edgecolor=INK))
    ax.text(5, 6.5, "ONE 48-WELL CAMPAIGN", ha="center", va="center", fontweight="bold", color=INK)
    ax.text(5, 5.0, "SPADE or qLogNEI\nsame wells, chosen rounds", ha="center", va="center", color=INK, fontsize=8)
    ax.set_title("Matched budget", color=INK, pad=8)

    # B: two deliverables
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    _panel(ax, "B")
    ax.add_patch(FancyBboxPatch((0.8, 5.5), 8.4, 3.2, boxstyle="round,pad=0.15", facecolor="#FDE9DD", edgecolor=INK))
    ax.text(5, 7.8, "POINT DECISION", ha="center", fontweight="bold", color=INK, fontsize=8)
    ax.text(5, 6.6, "One recipe → simple regret\n(SPADE R=5 vs qLogNEI R=10)", ha="center", color=INK, fontsize=7.5)
    ax.add_patch(FancyBboxPatch((0.8, 1.2), 8.4, 3.2, boxstyle="round,pad=0.15", facecolor="#DDF3E8", edgecolor=INK))
    ax.text(5, 3.5, "CLAIMED OPERATING REGION", ha="center", fontweight="bold", color=INK, fontsize=8)
    ax.text(5, 2.3, "Conservative set → certified volume\n(matched R=5)", ha="center", color=INK, fontsize=7.5)
    ax.set_title("Two scores", color=INK, pad=8)

    # C: round schedules
    ax = axes[2]
    _panel(ax, "C")
    # Batch-of-8 schedules used for SPADE/qLogNEI at R=3 and R=5.
    rows = [("3", 32, 2), ("5", 16, 4)]
    for i, (R, n0, nb) in enumerate(rows):
        ax.barh(i, n0, color="#A6CEE3", edgecolor=INK, height=0.55, label="Opening" if i == 0 else None)
        ax.barh(i, 8 * nb, left=n0, color="#1F78B4", edgecolor=INK, height=0.55, label="Batches ×8" if i == 0 else None)
        ax.text(50, i, f"R={R}", va="center", ha="left", color=INK, fontsize=8)
    ax.text(0.0, -0.22, 'qLogNEI R=10 also uses 48 wells total (10-round BO schedule).', transform=ax.transAxes, fontsize=6.5, color=MUTED, va='top')
    ax.set_xlim(0, 58)
    ax.set_yticks([])
    ax.set_xlabel("Wells (total = 48)")
    ax.legend(loc="lower right", fontsize=7, frameon=False)
    ax.set_title("Round schedules", color=INK, pad=8)
    fig.tight_layout()
    return fig


def _mean_ci(diffs):
    out = boot(diffs)
    if out is None:
        return None
    mean, lo, hi, p = out
    return mean, lo, hi, p


def build_fig2(cells, regret):
    """Regret contrasts: R5 vs R10 parity, R3 vs R10, matched R5."""
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8), sharey=False)

    contrasts = [
        ("SPADE R=5 −\nqLogNEI R=10", *regret_pair(regret, FAMILIES, "spade", 5, "qlognei", 10)[:1], "spade", 5, "qlognei", 10),
    ]
    # rebuild properly
    specs = [
        ("A", "SPADE R=5 − qLogNEI R=10", "spade", 5, "qlognei", 10, "Headline regret parity"),
        ("B", "SPADE R=3 − qLogNEI R=10", "spade", 3, "qlognei", 10, "Three rounds insufficient"),
        ("C", "SPADE − qLogNEI at R=5", "spade", 5, "qlognei", 5, "Matched-round regret"),
    ]
    for ax, (lab, title, a, ar, b, br, subtitle) in zip(axes, specs):
        d, _ = regret_pair(regret, FAMILIES, a, ar, b, br)
        mean, lo, hi, p = _mean_ci(d)
        _panel(ax, lab)
        ax.axvspan(-SESOI, SESOI, color=SESOI_FILL, alpha=0.9, zorder=0)
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.errorbar([mean], [0], xerr=[[mean - lo], [hi - mean]], fmt="o", color=SPADE_C, ms=7, capsize=4, zorder=3)
        ax.set_yticks([])
        ax.set_xlabel("Paired regret difference\n(positive = SPADE worse)")
        ax.set_title(title, fontsize=8.5, color=INK)
        ax.text(0.5, -0.28, f"mean {mean:+.4f}\n95% CI [{lo:+.4f}, {hi:+.4f}]\nn={len(d)}", transform=ax.transAxes, ha="center", va="top", fontsize=7, color=MUTED)
        ax.set_xlim(-0.06, 0.06)
        if lab == "A":
            ax.text(0.02, 0.92, "±0.02 SESOI", transform=ax.transAxes, fontsize=7, color=MUTED)
    fig.suptitle("Point regret under matched 48-well budgets (LC, 32 seeds)", color=INK, fontsize=10, y=1.02)
    fig.tight_layout()
    return fig


def build_fig3(cells):
    """Certified volume SPADE − qLogNEI at matched R=3 and R=5; family breakdown at R=5."""
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.1, 1.4]})

    # Panel A: overall matched R
    ax = axes[0]
    _panel(ax, "A")
    xs, means, los, his, labels = [], [], [], [], []
    for i, R in enumerate([3, 5]):
        sp = lofo(cells, "spade", R, FAMILIES, C_GRID)
        qn = lofo(cells, "qlognei", R, FAMILIES, C_GRID)
        # pair volumes on intersecting keys
        keys = sorted(set(sp["vols"]) & set(qn["vols"]))
        d = [sp["vols"][k] - qn["vols"][k] for k in keys]
        mean, lo, hi, p = _mean_ci(d)
        xs.append(i)
        means.append(mean)
        los.append(lo)
        his.append(hi)
        labels.append(f"R={R}\np={p:.1e}" if p < 0.001 else f"R={R}\np={p:.3f}")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.errorbar(xs, means, yerr=[np.array(means) - np.array(los), np.array(his) - np.array(means)], fmt="o", color=SPADE_C, ms=8, capsize=4)
    ax.set_xticks(xs)
    ax.set_xticklabels(["Matched R=3", "Matched R=5"])
    ax.set_ylabel("Certified volume difference\n(SPADE − qLogNEI)")
    ax.set_title("Matched-round claimed region", fontsize=9, color=INK)
    for x, lab in zip(xs, labels):
        ax.text(x, his[x] + 0.00015, lab, ha="center", fontsize=6.5, color=MUTED)

    # Panel B: per-family at R=5
    ax = axes[1]
    _panel(ax, "B")
    fam_means, fam_lo, fam_hi, fam_names = [], [], [], []
    for fam in FAMILIES:
        sp = lofo(cells, "spade", 5, [fam], C_GRID)
        # For single-family LOFO degenerate — use pooled c selected on other families
        others = [f for f in FAMILIES if f != fam]
        sp = lofo(cells, "spade", 5, FAMILIES, C_GRID)
        qn = lofo(cells, "qlognei", 5, FAMILIES, C_GRID)
        keys = [k for k in set(sp["vols"]) & set(qn["vols"]) if k[0] == fam]
        d = [sp["vols"][k] - qn["vols"][k] for k in keys]
        if not d:
            continue
        mean, lo, hi, p = _mean_ci(d)
        fam_names.append(fam)
        fam_means.append(mean)
        fam_lo.append(lo)
        fam_hi.append(hi)
    y = np.arange(len(fam_names))
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.errorbar(fam_means, y, xerr=[np.array(fam_means) - np.array(fam_lo), np.array(fam_hi) - np.array(fam_means)], fmt="o", color=SPADE_C, ms=6, capsize=3)
    ax.set_yticks(y)
    ax.set_yticklabels(fam_names)
    ax.set_xlabel("Certified volume difference at R=5")
    ax.set_title("By family (LC LOFO volumes)", fontsize=9, color=INK)
    fig.suptitle("Claimed operating region (certified volume), LC confirmatory", color=INK, fontsize=10, y=1.02)
    fig.tight_layout()
    return fig


def build_fig4(cells, regret):
    """Answer rates / certification snapshot + noise ceiling note."""
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))

    # A: mean regret by arm×rounds (descriptive)
    ax = axes[0]
    _panel(ax, "A")
    configs = [("spade", 3), ("spade", 5), ("qlognei", 3), ("qlognei", 5), ("qlognei", 10)]
    means, ses, labels = [], [], []
    for arm, R in configs:
        vals = [regret[(a, r, f, s)] for (a, r, f, s) in regret if a == arm and r == R and not math.isnan(regret[(a, r, f, s)])]
        means.append(float(np.mean(vals)))
        ses.append(float(np.std(vals, ddof=1) / math.sqrt(len(vals))))
        labels.append(f"{arm}\nR={R}")
    x = np.arange(len(labels))
    colors = [SPADE_C if "spade" in lab else QLOG_C for lab in labels]
    ax.bar(x, means, yerr=ses, color=colors, edgecolor=INK, width=0.7, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Mean simple regret (±1 SE)")
    ax.set_title("Regret by arm and rounds", fontsize=9, color=INK)

    # B: answer rate (non-empty claimed region) at alpha 0.95 using LOFO answer field
    ax = axes[1]
    _panel(ax, "B")
    ar_spade, ar_qlog, Rs = [], [], [3, 5]
    for R in Rs:
        sp = lofo(cells, "spade", R, FAMILIES, C_GRID)
        qn = lofo(cells, "qlognei", R, FAMILIES, C_GRID)
        ar_spade.append(sp["answer"])
        ar_qlog.append(qn["answer"])
    x = np.arange(len(Rs))
    w = 0.35
    ax.bar(x - w / 2, ar_spade, w, label="SPADE", color=SPADE_C, edgecolor=INK)
    ax.bar(x + w / 2, ar_qlog, w, label="qLogNEI", color=QLOG_C, edgecolor=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"R={R}" for R in Rs])
    ax.set_ylabel("Answer rate (non-empty claimed region)")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("How often a region is returned", fontsize=9, color=INK)
    ax.text(0.5, -0.22, "LC at σ_rel=0.25. At σ_rel=0.68 nothing certified for either arm.", transform=ax.transAxes, ha="center", fontsize=7, color=MUTED)
    fig.suptitle("Supporting LC summaries", color=INK, fontsize=10, y=1.02)
    fig.tight_layout()
    return fig


def save(fig, stem: str, captions: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{ext}", bbox_inches="tight", facecolor="white")
    (OUT / f"{stem}.caption.txt").write_text(captions["caption"] + "\n")
    (OUT / f"{stem}.alt.txt").write_text(captions["alt"] + "\n")
    (OUT / f"{stem}.description.txt").write_text(captions["description"] + "\n")
    plt.close(fig)
    print(f"wrote {stem}")


def main():
    paths = sorted((ROOT / "results").glob("lc-*.json"))
    if not paths:
        raise SystemExit("no results/lc-*.json")
    cells, regret = load(paths, ALPHA)
    # ensure GRID exists in analyser module
    from analyse_lc_confirmatory import select_c  # noqa

    caps = {
        "fig1": {
            "caption": "Fig 1. Benchmark decisions for the LC confirmatory study. (A) Each method uses one 48-well campaign. (B) The same campaign supports a point decision (simple regret) and a claimed operating region (certified volume). (C) Round schedules share the 48-well total: opening size 48−8(R−1) plus (R−1) batches of eight.",
            "alt": "Three-panel schematic of matched 48-well campaigns, point versus claimed-region scores, and round schedules for R=3, 5, and 10.",
            "description": "Schematic only; no performance data.",
        },
        "fig2": {
            "caption": "Fig 2. Point-regret contrasts in the LC confirmatory study (32 seeds, five families). (A) SPADE at five rounds minus qLogNEI at ten rounds; shaded band is the ±0.02 SESOI. (B) SPADE at three rounds minus qLogNEI at ten rounds. (C) SPADE minus qLogNEI at matched five rounds. Points are paired means with 95% bootstrap intervals; positive values mean SPADE has higher (worse) regret.",
            "alt": "Three forest-style panels of paired regret differences for SPADE versus qLogNEI under LC.",
            "description": "Primary regret parity and negative three-round finding.",
        },
        "fig3": {
            "caption": "Fig 3. Claimed-operating-region (certified volume) contrasts from LC leave-one-family-out volumes. (A) SPADE minus qLogNEI at matched three and five rounds. (B) The five-round contrast by family. Positive values favor SPADE. The matched five-round advantage is the confirmatory volume headline; the three-round volume spike did not survive as a claimed result in the manuscript.",
            "alt": "Certified volume differences overall and by family for SPADE versus qLogNEI.",
            "description": "Primary certified-volume evidence.",
        },
        "fig4": {
            "caption": "Fig 4. Supporting LC summaries at relative noise 0.25. (A) Mean simple regret (±1 SE) by arm and round count. (B) Leave-one-family-out answer rates (non-empty claimed regions) for SPADE and qLogNEI at three and five rounds. At relative noise 0.68, nothing certified for either arm in the companion noise study.",
            "alt": "Bar charts of mean regret by configuration and answer rates for claimed regions.",
            "description": "Descriptive support; noise ceiling noted in caption.",
        },
    }

    save(build_fig1(), "fig1", caps["fig1"])
    save(build_fig2(cells, regret), "fig2", caps["fig2"])
    save(build_fig3(cells), "fig3", caps["fig3"])
    save(build_fig4(cells, regret), "fig4", caps["fig4"])

    # verify numbers printed for manuscript sync
    d, _ = regret_pair(regret, FAMILIES, "spade", 5, "qlognei", 10)
    m, lo, hi, p = _mean_ci(d)
    print(f"LC-1 regret R5 vs R10: {m:+.4f} [{lo:+.4f},{hi:+.4f}] n={len(d)}")
    sp = lofo(cells, "spade", 5, FAMILIES, C_GRID)
    qn = lofo(cells, "qlognei", 5, FAMILIES, C_GRID)
    keys = sorted(set(sp["vols"]) & set(qn["vols"]))
    d2 = [sp["vols"][k] - qn["vols"][k] for k in keys]
    m2, lo2, hi2, p2 = _mean_ci(d2)
    print(f"LC-4 volume matched R5: {m2:+.6f} [{lo2:+.6f},{hi2:+.6f}] p={p2:.6f} n={len(d2)}")


if __name__ == "__main__":
    main()
