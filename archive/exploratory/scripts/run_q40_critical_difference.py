"""Q40 / T2.3 — a critical-difference diagram instead of a wall of p-values.

    python scripts/run_q40_critical_difference.py
    -> results/figures/critical-difference-d6-s0.25.png  (and the other three cells)

Seven arms compared pairwise across four cells is 84 pairwise tests. A table of them is
unreadable and invites exactly the multiplicity error Q39 found. The Demsar (2006)
presentation is one line per cell: arms placed at their **mean rank** across landscapes,
with a bar joining every group that is **not** significantly different.

Friedman first — if the omnibus test does not reject, no post-hoc comparison is licensed
and the diagram is drawn with every arm joined. Then Nemenyi:

    CD = q_alpha * sqrt( k (k+1) / (6 N) )

with `k` arms, `N` landscapes, and `q_alpha` the Studentized range statistic at infinite
df divided by sqrt(2). Taken from `scipy.stats.studentized_range` rather than from a
copied table, so it is checkable and correct for any `k`.

**Ranks are computed per landscape, over instance-mean regret** — the same n=25
clustering unit as every other inference in this project, not n=50 over runs. The
Friedman/Nemenyi machinery assumes independent blocks, and a landscape is the block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402
from scipy.stats import friedmanchisquare, studentized_range  # noqa: E402

GRID = ROOT / "results" / "e2-grid.json"
FIGDIR = ROOT / "results" / "figures"
ALPHA = 0.05
CELLS = ((6, 0.25), (6, 0.1), (8, 0.25), (8, 0.1))


def nemenyi_cd(k: int, n: int, alpha: float = ALPHA) -> float:
    """Critical difference in mean-rank units. Computed, not copied from a table."""
    q = float(studentized_range.ppf(1 - alpha, k, np.inf)) / np.sqrt(2.0)
    return q * np.sqrt(k * (k + 1) / (6.0 * n))


def cell_ranks(rows, dim, sigma):
    sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
    arms = sorted({r["arm"] for r in sub})
    insts = sorted({r["instance"] for r in sub})
    # instance-mean regret, arms x instances; drop arms absent from this cell
    M = []
    keep = []
    for a in arms:
        col = []
        ok = True
        for i in insts:
            v = [r["regret"] for r in sub if r["arm"] == a and r["instance"] == i]
            if not v:
                ok = False
                break
            col.append(np.mean(v))
        if ok:
            M.append(col)
            keep.append(a)
    M = np.array(M)                       # (k, N) — lower regret is better
    # rank 1 = best (lowest regret) within each landscape
    ranks = np.apply_along_axis(lambda c: c.argsort().argsort() + 1, 0, M).astype(float)
    return keep, M, ranks


def draw(names, mean_ranks, cd, path: Path, title: str, friedman_p: float):
    order = np.argsort(mean_ranks)
    names = [names[i] for i in order]
    mr = mean_ranks[order]
    k = len(names)
    lo, hi = 1.0, float(k)

    fig, ax = plt.subplots(figsize=(7.2, 2.4 + 0.22 * k), dpi=200)
    ax.set_xlim(lo - 0.35, hi + 0.35)
    ax.set_ylim(-0.6 - 0.34 * k, 1.95)
    ax.axis("off")

    ax.plot([lo, hi], [1.0, 1.0], "k-", lw=1.2)
    for t in range(int(lo), int(hi) + 1):
        ax.plot([t, t], [1.0, 1.12], "k-", lw=1.0)
        ax.text(t, 1.20, str(t), ha="center", va="bottom", fontsize=9)
    ax.text((lo + hi) / 2, 1.74, title, ha="center", va="bottom", fontsize=10)
    ax.text(lo, 1.74, "better", ha="left", va="bottom", fontsize=8, style="italic")
    ax.text(hi, 1.74, "worse", ha="right", va="bottom", fontsize=8, style="italic")

    for j, (nm, r) in enumerate(zip(names, mr)):
        y = -0.30 - 0.34 * j
        ax.plot([r, r], [1.0, y], color="0.45", lw=0.9)
        side = lo - 0.30 if j < k / 2 else hi + 0.30
        ha = "right" if j < k / 2 else "left"
        ax.plot([r, side], [y, y], color="0.45", lw=0.9)
        ax.text(side + (-0.05 if ha == "right" else 0.05), y,
                f"{nm}  ({r:.2f})", ha=ha, va="center", fontsize=9)

    # cliques: maximal runs of adjacent arms within CD of each other
    cliques, i = [], 0
    while i < k:
        j = i
        while j + 1 < k and mr[j + 1] - mr[i] <= cd:
            j += 1
        if j > i:
            cliques.append((i, j))
        i += 1
    drawn, yb = [], 0.86
    for a, b in cliques:
        if any(a >= x and b <= y for x, y in drawn):
            continue
        drawn.append((a, b))
        ax.plot([mr[a] - 0.03, mr[b] + 0.03], [yb, yb], "k-", lw=3.0,
                solid_capstyle="butt")
        yb -= 0.10

    ax.plot([lo, lo + cd], [1.52, 1.52], "k-", lw=1.4)
    ax.plot([lo, lo], [1.49, 1.55], "k-", lw=1.0)
    ax.plot([lo + cd, lo + cd], [1.49, 1.55], "k-", lw=1.0)
    ax.text(lo + cd / 2, 1.58, f"CD = {cd:.2f}", ha="center", va="bottom", fontsize=8)
    ax.text(hi + 0.30, -0.30 - 0.34 * k - 0.18,
            f"Friedman p = {friedman_p:.2e}", ha="right", va="top", fontsize=7,
            color="0.35")

    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    rows = json.loads(GRID.read_text())
    out = []
    for dim, sigma in CELLS:
        names, M, ranks = cell_ranks(rows, dim, sigma)
        k, n = ranks.shape
        mr = ranks.mean(axis=1)
        stat, p = friedmanchisquare(*[M[i] for i in range(k)])
        cd = nemenyi_cd(k, n)
        tag = f"d={dim}, sigma={sigma}" + ("   [REGISTERED PRIMARY]"
                                           if (dim, sigma) == (6, 0.25) else "")
        print(f"\n{tag}   k={k} arms, N={n} landscapes")
        print(f"  Friedman chi2 = {stat:.3f}, p = {p:.3e}"
              f"   -> {'post-hoc licensed' if p < ALPHA else 'NO post-hoc: omnibus not rejected'}")
        print(f"  Nemenyi CD at alpha={ALPHA}: {cd:.3f} mean-rank units")
        for nm, r in sorted(zip(names, mr), key=lambda t: t[1]):
            print(f"      {nm:>9}  mean rank {r:.3f}")
        path = FIGDIR / f"critical-difference-d{dim}-s{sigma}.png"
        draw(names, mr, cd if p < ALPHA else float(k),
             path, f"E2 mean rank, {tag}", p)
        print(f"  -> {path.relative_to(ROOT)}")
        out.append(dict(dim=dim, sigma=sigma, arms=names,
                        mean_ranks=mr.tolist(), cd=cd, friedman_p=float(p), n=n))
    (ROOT / "results" / "q40-critical-difference.json").write_text(json.dumps(out, indent=1))
    print("\n  A bar joins arms that are NOT significantly different. Arms further apart\n"
          "  than CD differ at the family-wise alpha, so the diagram already carries a\n"
          "  multiplicity correction rather than needing one applied to a pairwise table.")
    print("""
  WHERE THIS AND Q39 DISAGREE, AND WHY — read before quoting either.
  These two corrections control DIFFERENT families and can therefore differ:

    Nemenyi here   family = the arms WITHIN one cell (15 pairs at k=6, 21 at k=7).
                   Answers "in this cell, which arms differ?"
    Holm in Q39    family = ALL 39 non-primary contrasts reported by this project,
                   across four cells and several experiments.
                   Answers "which of the claims this paper makes survive?"

  Holm's family is far larger, so it is strictly more conservative, and the two part
  company on `lhs` vs `qlogei` at d=8 sigma=0.25: rank gap 1.600 > CD 1.508 (Nemenyi
  says differ) while Holm gives p 0.0187 -> 0.2249 (says not). Both are correct for
  their own question.

  RULING, so the paper does not quote whichever is convenient: a claim MADE IN THE
  PAPER is one of the 39, so Q39's Holm governs any sentence asserting an arm beats
  another. The diagrams are the summary presentation and are read as within-cell
  structure, never cited as significance for an individual pair. At the registered
  primary cell the two agree anyway -- doe-qlogei 2.520 > CD, lhs-qlogei 1.240 < CD --
  which is the only cell the headline rests on.""")


if __name__ == "__main__":
    main()
