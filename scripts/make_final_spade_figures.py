"""The figures for `spade-final-2026-08-23`, drawn from committed artefacts only.

    .venv/bin/python scripts/make_final_spade_figures.py

Reads `results/final-spade-*.json`. Writes `results/figures/final-spade/`.

------------------------------------------------------------------------------
THIS MODULE CANNOT COMPUTE A RESULT, AND THAT IS THE POINT
------------------------------------------------------------------------------

It imports json, numpy and matplotlib. It cannot fit a model, evaluate an oracle
or draw a posterior, because it does not import anything that can. That is a
structural guarantee rather than a promise: a figure script able to recompute a
number can put a number on a page that appears in no committed artefact, and a
reader has no way to tell which kind of number they are looking at.

A test asserts the absence (`tests/test_final_spade_reproducibility.py`). The
same test asserts that every path this module opens matches
`results/final-spade-*.json`.

**A missing artefact skips its figure with a printed message and returns None.**
It never crashes, and it never substitutes a plausible value. The study has not
run; most of these inputs do not exist yet, and a script that dies on the first
absent file cannot be exercised before it is needed.

------------------------------------------------------------------------------
WHAT EVERY FIGURE MUST CARRY
------------------------------------------------------------------------------

Condition, terminal rule, and n — in the title or the caption, on every panel.
Spec §7.4 makes the terminal rule load-bearing (comparing rule A for one arm
against rule P for another is a protocol violation), §5 makes the regime class
load-bearing (a TARGET number and a ROBUSTNESS number are not interchangeable),
and §11 lists reporting a rate without its denominator among the prohibited
actions. A figure is a table with the numbers taken out, so it inherits all
three obligations.

Each function returns a :class:`Rendered` carrying the caption, the visual
encoding as data, the text annotations and the reference lines. The encoding is
returned rather than only drawn so a test can assert the *meaning* of a channel
instead of the pixels — asserting that a scatter has markers proves nothing
about what shape means.

------------------------------------------------------------------------------
THE CENTRAL FIGURE
------------------------------------------------------------------------------

`figure_pareto` is the paper's central figure and is mandatory. Its job is to
make one thing unmissable: **the lowest-regret arm need not be the best-map
arm.** FINDINGS §13 measured exactly that inversion — SPADE arms 1st-3rd of 12
on the map at (d=6, sigma=0.10) while 9th-11th on regret — and a paper that
reports a regret table and a map table on different pages lets the reader
average them into a ranking that neither supports. So both axes are on one pair
of axes, and the caption names the two arms by name when they differ.

------------------------------------------------------------------------------
COLOUR
------------------------------------------------------------------------------

Okabe-Ito, the same set `src/boec/figures.py` validated for colour-blind
separation. Colour carries method family only, and never carries anything alone:
every point is directly labelled with its arm, certificate status is carried by
fill rather than hue, and round count is carried by marker shape.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")  # no display; we only write files
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "figures" / "final-spade"

#: Every file this module is allowed to open. A test asserts the shape of these
#: names, so a future edit cannot quietly widen the module's reach.
ARTEFACTS = {
    "benchmark": "final-spade-primary.json",
    "certificates": "final-spade-certificate.json",
    "feasibility": "final-spade-feasibility.json",
    "kill_ledger": "final-spade-kill-ledger.json",
    "manifest": "final-spade-manifest.json",
}

FIGURES = ("crossfit_containment", "same_draw_vs_crossfit", "allocation_tradeoff",
           "causal_controls", "pareto", "murphy", "threshold_feasibility",
           "cross_condition")

# Okabe-Ito. One hue per method family; families, not arms, because twelve hues
# would be twelve indistinguishable hues.
FAMILY_COLOUR = {
    "SPADE": "#0072B2",           # blue
    "SPADE control": "#56B4E9",   # light blue -- kin to SPADE, deliberately
    "space-filling": "#009E73",   # green
    "BO": "#D55E00",              # vermillion
    "classical RSM": "#CC79A7",   # purple
}
UNKNOWN_COLOUR = "#6b6b6b"
INK = "#1a1a1a"
MUTED = "#6b6b6b"
GRID = "#dcdcdc"

#: Rounds and wells are separate axes (spec §4.1), so rounds gets its own channel.
ROUND_MARKER = {1: "o", 2: "s", 3: "^", 10: "D"}

#: Certificate status at alpha=0.95, carried by FILL. UNAVAILABLE is a real
#: fourth state, not a stand-in for INCONCLUSIVE: a cell with no certificate row
#: was not assessed, and drawing it as though it had been is invention.
STATUS_FILL = {"PASS": "solid", "FAIL": "open", "INCONCLUSIVE": "hatched",
               "UNAVAILABLE": "dotted"}

ARM_FAMILY_FALLBACK = {
    "spade_cf_m0": "SPADE", "spade_cf_m4": "SPADE", "spade_cf_m8": "SPADE",
    "spade_plate1_only": "SPADE control", "spade_random_plate2": "SPADE control",
    "sobol": "space-filling", "lhs": "space-filling", "random": "space-filling",
    "qlognei": "BO", "qlogei": "BO", "doe": "classical RSM",
    "doe_unscreened": "classical RSM",
}

#: `scripts/run_final_spade_benchmark.py` writes the short names. Mapped rather
#: than renamed at the source: the artefact is the record, and a figure script
#: that edits the record to suit its own legend is doing the wrong repair.
FAMILY_ALIAS = {"spade-ctrl": "SPADE control", "spade control": "SPADE control",
                "spade_control": "SPADE control", "classical": "classical RSM",
                "classical rsm": "classical RSM", "spade": "SPADE", "bo": "BO",
                "space-filling": "space-filling", "space filling": "space-filling"}


@dataclass
class Rendered:
    """One written figure, plus the parts of it a test can check."""
    path: Path
    caption: str
    encoding: dict = field(default_factory=dict)
    annotations: list[str] = field(default_factory=list)
    reference_lines: list[float] = field(default_factory=list)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

def _stamp(item: dict, envelope_condition) -> dict:
    """Give a row or cell an explicit ``condition_id``.

    ``run_final_spade_benchmark.py`` writes **one file per condition** and records
    the condition once, in the envelope, not on every row; the analyser's
    certificate cells call the same field ``condition``. Neither is wrong — but a
    figure that groups by a key half the artefacts do not carry would silently
    collapse four conditions into one panel, which is the pooling §8.2 hard-fails
    on. So the key is reconstructed here, from the envelope or from the cell's own
    geometry, and never assumed.
    """
    cid = item.get("condition_id") or item.get("condition") or envelope_condition
    if not cid and item.get("family"):
        cid = (f"{item.get('family')} d={item.get('dimension')} "
               f"σ={item.get('sigma')}")
    return {**item, "condition_id": str(cid)} if cid else dict(item)


def _read(results_dir: Path, key: str) -> dict | None:
    """One artefact, merged across ``<stem>.json`` and any ``<stem>-*.json``.

    The benchmark runner takes ``--condition`` and writes a file per condition, so
    a release may hold ``final-spade-primary-C1.json`` … ``-C4.json`` rather than
    one file. Reading only the bare name would draw one condition and skip three
    without saying so.
    """
    stem = ARTEFACTS[key][:-len(".json")]
    d = Path(results_dir)
    paths = sorted({*d.glob(f"{stem}.json"), *d.glob(f"{stem}-*.json")})
    if not paths:
        print(f"SKIP  {ARTEFACTS[key]} — absent; every figure that needs it is "
              f"skipped rather than drawn from substituted values")
        return None
    merged: dict = {}
    rows, cells = [], []
    for p in paths:
        obj = json.loads(p.read_text())
        if not isinstance(obj, dict):
            continue
        cond = obj.get("condition")
        merged = {**{k: v for k, v in obj.items() if k not in ("rows", "cells")},
                  **merged}
        rows += [_stamp(r, cond) for r in obj.get("rows") or [] if isinstance(r, dict)]
        cells += [_stamp(c, cond) for c in obj.get("cells") or [] if isinstance(c, dict)]
    if rows:
        merged["rows"] = rows
    if cells:
        merged["cells"] = cells
    merged["source_files"] = [p.name for p in paths]
    return merged


def _cell(c: dict) -> dict:
    """A certificate cell flattened.

    `analyse_final_spade_benchmark.py` nests the primary estimate under
    ``crossfit`` and the diagnostic under ``same_draw``, each carrying its own
    ``role``. That nesting is a good decision — it makes the primary/diagnostic
    split structural rather than a naming convention — so it is read as written
    and flattened here rather than asked to change.
    """
    cf = c.get("crossfit") if isinstance(c.get("crossfit"), dict) else {}
    sd = c.get("same_draw") if isinstance(c.get("same_draw"), dict) else {}

    def pick(flat, nested, src):
        v = c.get(flat)
        return src.get(nested) if v is None else v

    return {**c,
            "crossfit_rate": pick("crossfit_rate", "proportion", cf),
            "crossfit_x": pick("crossfit_x", "x", cf),
            "crossfit_n": pick("crossfit_n", "n", cf),
            "ci_lo": pick("ci_lo", "ci_lo", cf), "ci_hi": pick("ci_hi", "ci_hi", cf),
            "same_draw_rate": pick("same_draw_rate", "proportion", sd),
            "same_draw_x": pick("same_draw_x", "x", sd),
            "same_draw_n": pick("same_draw_n", "n", sd)}


def _rows(obj: dict | None, *keys: str) -> list[dict]:
    if not obj:
        return []
    for k in keys or ("rows",):
        v = obj.get(k)
        if isinstance(v, list):
            items = [r for r in v if isinstance(r, dict)]
            return [_cell(r) for r in items] if k == "cells" else items
    return []


def _num(r: dict, key: str):
    v = r.get(key)
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _mean(rows: Sequence[dict], key: str) -> float | None:
    vals = [v for v in (_num(r, key) for r in rows) if v is not None and np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def _family(r: dict) -> str:
    raw = r.get("arm_family")
    if raw:
        return FAMILY_ALIAS.get(str(raw).strip().lower(), str(raw))
    return ARM_FAMILY_FALLBACK.get(str(r.get("arm")), "other")


def _by(rows: Sequence[dict], key: str) -> dict:
    out: dict = {}
    for r in rows:
        out.setdefault(r.get(key), []).append(r)
    return out


def _terminal_rules(rows: Sequence[dict]) -> str:
    """What the caption says about the terminal rule.

    The runner writes ``terminal_rule = "both"`` because each row carries both
    ``regret_rule_a`` and ``regret_rule_p``. Spelling that out matters: §7.4 makes
    rule P the primary estimand and rule A a required robustness outcome, and
    §43.1 records a claim withdrawn for comparing one arm's rule A against
    another's rule P. "both" alone would let a reader assume the figure chose.
    """
    rules = sorted({str(r.get("terminal_rule")) for r in rows if r.get("terminal_rule")})
    if rules == ["both"]:
        return "A and P both recorded per row; rule P is the primary estimand (§7.4)"
    return "/".join(rules) if rules else "n/a"


def _style(ax) -> None:
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8, length=3, width=0.8)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _caption(fig, text: str) -> None:
    fig.text(0.0, -0.035, text, fontsize=7.5, color=MUTED, ha="left", va="top",
             wrap=True)


# ==========================================================================
# 1. Cross-fit containment by arm and assurance
# ==========================================================================

def figure_crossfit_containment(certs: dict | None, out: Path) -> Rendered | None:
    """Cross-fit containment, exact interval, denominator on every bar.

    **Form: bars with exact Clopper-Pearson whiskers, nominal drawn as a line.**

    The denominator is printed *on* each bar rather than in a legend because
    FINDINGS §9.5 is the case where it was not: a containment table pooled four
    thresholds from one campaign and one posterior, reported `0.646 ok`, and the
    cell underneath it was 1 of 7 non-empty sets. The proportion was never the
    problem. The missing `n` was.

    The whisker is the exact interval and never a normal one (§8, FINDINGS §22).
    An empty certificate scores no containment at all (§2.1) — it is carried in
    the empty rate printed beside the denominator, never as a success.
    """
    cells = _rows(certs, "cells", "rows")
    if not cells:
        return None

    alphas = sorted({_num(c, "alpha") for c in cells if _num(c, "alpha") is not None})
    arms = sorted({str(c.get("arm")) for c in cells})
    conds = sorted({str(c.get("condition_id")) for c in cells})
    fig, axes = plt.subplots(1, max(1, len(conds)), figsize=(4.6 * max(1, len(conds)), 3.8),
                             dpi=200, squeeze=False)
    annotations, width = [], 0.8 / max(1, len(alphas))

    for ax, cond in zip(axes[0], conds, strict=False):
        _style(ax)
        for k, alpha in enumerate(alphas):
            for j, arm in enumerate(arms):
                sel = [c for c in cells if str(c.get("condition_id")) == cond
                       and str(c.get("arm")) == arm and _num(c, "alpha") == alpha]
                if not sel:
                    continue
                c = sel[0]
                rate, n = _num(c, "crossfit_rate"), _num(c, "crossfit_n")
                if rate is None or n is None:
                    continue
                x = j + (k - (len(alphas) - 1) / 2) * width
                lo, hi = _num(c, "ci_lo"), _num(c, "ci_hi")
                colour = FAMILY_COLOUR.get(_family(c), UNKNOWN_COLOUR)
                ax.bar(x, rate, width=width * 0.9, color=colour,
                       alpha=0.45 + 0.55 * k / max(1, len(alphas) - 1),
                       edgecolor=colour, linewidth=1.0, zorder=3)
                if lo is not None and hi is not None:
                    ax.plot([x, x], [lo, hi], color=INK, linewidth=1.3, zorder=4,
                            solid_capstyle="butt")
                x_n = _num(c, "crossfit_x")
                label = f"{int(x_n)}/{int(n)}" if x_n is not None else f"n={int(n)}"
                annotations.append(label)
                ax.text(x, min(hi or rate, 1.0) + 0.012, label, rotation=90,
                        fontsize=6.5, ha="center", va="bottom", color=INK)
        for alpha in alphas:
            ax.axhline(alpha, color=MUTED, linestyle="--", linewidth=1, zorder=2)
            ax.annotate(f"nominal α={alpha:g}", (len(arms) - 0.5, alpha),
                        textcoords="offset points", xytext=(-2, 3), fontsize=6.5,
                        color=MUTED, ha="right")
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels(arms, rotation=30, ha="right", fontsize=7)
        ax.set_ylim(0.5, 1.06)
        ax.set_title(f"{cond} — cross-fit containment (primary)", fontsize=9.5,
                     color=INK, loc="left", pad=8)
    axes[0][0].set_ylabel("cross-fit containment", fontsize=9, color=INK)

    n_tot = int(sum(_num(c, "crossfit_n") or 0 for c in cells))
    rule = _terminal_rules(cells)
    cap = (f"Cross-fit containment by arm and assurance. Conditions {', '.join(conds)}; "
           f"terminal rule {rule}; n={n_tot} scored non-empty certificates across "
           f"{len(cells)} cells. Whiskers are exact Clopper-Pearson intervals (§8 — "
           f"never a normal approximation, FINDINGS §22). The count printed on each bar "
           f"is its own denominator; an empty certificate scores no containment (§2.1).")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-crossfit-containment.png"), cap,
                    encoding={"x": "arm", "y": "crossfit_rate", "group": "alpha",
                              "whisker": "exact Clopper-Pearson"},
                    annotations=annotations, reference_lines=list(alphas))


# ==========================================================================
# 2. Same-draw vs cross-fit — the §29.3 gap, made visible
# ==========================================================================

def figure_same_draw_vs_crossfit(certs: dict | None, out: Path) -> Rendered | None:
    """The diagnostic §2.1 requires to be reported *beside* the primary.

    **Form: scatter against the identity line.** Selection bias has a direction —
    same-draw containment is the flattering one — and a direction is what a
    difference plot against y=x shows and two bar charts do not. §29.3 measured
    the residual gap at 4,096 draws at 1.5-3.5 points, concentrated where the
    Vorob'ev quantiles tie; points sitting above the line are that bias, and the
    figure exists so it stays visible rather than being resolved once in an
    analysis nobody re-reads.
    """
    cells = _rows(certs, "cells", "rows")
    pts = [(c, _num(c, "crossfit_rate"), _num(c, "same_draw_rate")) for c in cells]
    pts = [(c, x, y) for c, x, y in pts if x is not None and y is not None]
    if not pts:
        return None

    fig, ax = plt.subplots(figsize=(4.6, 4.2), dpi=200)
    _style(ax)
    ax.plot([0, 1], [0, 1], color=MUTED, linestyle="--", linewidth=1.2, zorder=2)
    ax.annotate("y = x  (no selection bias)", (0.98, 0.98), textcoords="offset points",
                xytext=(-4, -10), fontsize=7, color=MUTED, ha="right")
    for c, x, y in pts:
        colour = FAMILY_COLOUR.get(_family(c), UNKNOWN_COLOUR)
        ax.scatter([x], [y], s=44, color=colour, alpha=0.85, edgecolor="white",
                   linewidth=0.9, zorder=4)
        ax.annotate(f"{c.get('arm')} {c.get('condition_id')}", (x, y),
                    textcoords="offset points", xytext=(6, -3), fontsize=6,
                    color=colour)
    gaps = [y - x for _, x, y in pts]
    lo = min(min(x for _, x, _ in pts), min(y for _, _, y in pts)) - 0.02
    ax.set_xlim(lo, 1.01)
    ax.set_ylim(lo, 1.01)
    ax.set_xlabel("cross-fit containment  (PRIMARY)", fontsize=9, color=INK)
    ax.set_ylabel("same-draw containment  (diagnostic, non-primary)", fontsize=9,
                  color=INK)
    ax.set_title("Same-draw containment is the flattering one", fontsize=10,
                 color=INK, loc="left", pad=8)

    conds = sorted({str(c.get("condition_id")) for c, _, _ in pts})
    cap = (f"Same-draw versus cross-fit containment, one point per certificate cell. "
           f"Conditions {', '.join(conds)}; terminal rule {_terminal_rules(cells)}; "
           f"n={len(pts)} cells. Mean same-draw minus cross-fit = "
           f"{np.mean(gaps):+.4f} (max {max(gaps):+.4f}). Cross-fit is the primary "
           f"endpoint (§2.1); same-draw appears here as a diagnostic and nowhere as "
           f"evidence.")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-samedraw-vs-crossfit.png"), cap,
                    encoding={"x": "crossfit_rate", "y": "same_draw_rate",
                              "identity_line": True, "colour": "arm_family"})


# ==========================================================================
# 3. m0 / m4 / m8 — regret, map, certificate
# ==========================================================================

ALLOCATION_ARMS = ("spade_cf_m0", "spade_cf_m4", "spade_cf_m8")


def figure_allocation_tradeoff(bench: dict | None, out: Path) -> Rendered | None:
    """The §7.5 conjunction, drawn as a conjunction.

    **Form: three panels sharing one x axis of arms, never one composite score.**
    §7.5 makes `m > 0` an improvement only if it lowers rule-P regret by >= SESOI
    *and* does not worsen the map by more than 0.02 *and* does not worsen
    calibration beyond 0.005 *and* keeps the certificate. A single blended score
    would let a regret gain pay for a certificate loss, which §7.5 names as the
    thing it is not: that is a trade-off, and it is reported as one.
    """
    rows = [r for r in _rows(bench) if str(r.get("arm")) in ALLOCATION_ARMS]
    if not rows:
        return None
    conds = sorted({str(r.get("condition_id")) for r in rows})
    panels = (("regret_rule_p", "primary-rule (P) regret", "lower better"),
              ("symmetric_difference_pred", "symmetric-difference map error",
               "lower better"),
              ("crossfit_containment", "cross-fit containment", "higher better"))

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), dpi=200)
    for ax, (key, title, sense) in zip(axes, panels, strict=True):
        _style(ax)
        for ci, cond in enumerate(conds):
            xs, ys = [], []
            for j, arm in enumerate(ALLOCATION_ARMS):
                sel = [r for r in rows if str(r.get("arm")) == arm
                       and str(r.get("condition_id")) == cond]
                v = _mean(sel, key)
                if v is not None:
                    xs.append(j)
                    ys.append(v)
            if xs:
                ax.plot(xs, ys, marker="o", markersize=5, linewidth=1.6,
                        color=FAMILY_COLOUR["SPADE"], alpha=0.35 + 0.65 * ci / max(1, len(conds) - 1),
                        markeredgecolor="white", markeredgewidth=0.9)
                ax.annotate(cond, (xs[-1], ys[-1]), textcoords="offset points",
                            xytext=(5, 0), fontsize=6.5, color=INK, va="center")
        ax.set_xticks(range(len(ALLOCATION_ARMS)))
        ax.set_xticklabels(["m=0", "m=4", "m=8"], fontsize=8)
        ax.set_title(f"{title}  ({sense})", fontsize=9, color=INK, loc="left", pad=6)
    axes[0].set_xlabel("plate-2 wells spent locally", fontsize=8.5, color=INK)

    n = len(rows)
    cap = (f"Allocation variants m=0/4/8 on the three §7.5 axes separately. "
           f"Conditions {', '.join(conds)}; terminal rule P (primary estimand, §7.4); "
           f"n={n} rows. §7.5: m>0 is an improvement only under the full conjunction — "
           f"a regret reduction that damages the certificate is a trade-off and is "
           f"reported as one, which is why there is no composite panel.")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-allocation-tradeoff.png"), cap,
                    encoding={"x": "m_local", "panels": [p[0] for p in panels],
                              "colour": "condition_id"})


# ==========================================================================
# 4. The causal controls
# ==========================================================================

CONTROL_ARMS = ("spade_cf_m0", "spade_plate1_only", "spade_random_plate2")


def figure_causal_controls(bench: dict | None, out: Path) -> Rendered | None:
    """Does boundary targeting earn its complexity, and does plate 2 do anything?

    **Form: bars per condition, with `plate1_only` marked budget-short.**
    §3.3 makes `m0` vs `random_plate2` the load-bearing causal comparison of the
    study — same wells, same rounds, one differing rule — and makes
    `plate1_only` a rounds/wells reference rather than an equal-well comparator,
    because it is eight wells behind. Drawing all three as peers would invite the
    reader to credit boundary targeting with a budget difference, so the
    budget-short bar is hatched and says so.
    """
    rows = [r for r in _rows(bench) if str(r.get("arm")) in CONTROL_ARMS]
    if not rows:
        return None
    conds = sorted({str(r.get("condition_id")) for r in rows})
    fig, ax = plt.subplots(figsize=(1.9 + 1.5 * len(conds), 3.6), dpi=200)
    _style(ax)
    width = 0.26
    for j, arm in enumerate(CONTROL_ARMS):
        xs, ys = [], []
        for i, cond in enumerate(conds):
            sel = [r for r in rows if str(r.get("arm")) == arm
                   and str(r.get("condition_id")) == cond]
            v = _mean(sel, "symmetric_difference_pred")
            if v is not None:
                xs.append(i + (j - 1) * width)
                ys.append(v)
        short = arm == "spade_plate1_only"
        ax.bar(xs, ys, width=width * 0.9,
               color=FAMILY_COLOUR["SPADE" if arm == "spade_cf_m0" else "SPADE control"],
               hatch="//" if short else None, edgecolor="white", linewidth=0.8,
               label=arm + (" (40 wells, 1 round — reference)" if short else ""),
               zorder=3)
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, fontsize=8)
    ax.set_ylabel("symmetric-difference error  (lower better)", fontsize=9, color=INK)
    ax.set_title("m0 vs plate-1-only vs random plate 2", fontsize=10, color=INK,
                 loc="left", pad=8)
    ax.legend(fontsize=6.5, frameon=False, loc="upper right")

    n = len(rows)
    cap = (f"Symmetric-difference map error for the two causal controls. Conditions "
           f"{', '.join(conds)}; terminal rule {_terminal_rules(rows)}; n={n} rows. "
           f"m0 vs random_plate2 is the load-bearing comparison (§3.3): equal wells, "
           f"equal rounds, one differing rule. plate1_only is hatched because it is "
           f"eight wells short and is a rounds/wells reference, not an equal-well "
           f"comparator (§4.1).")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-causal-controls.png"), cap,
                    encoding={"x": "condition_id", "y": "symmetric_difference_pred",
                              "arms": list(CONTROL_ARMS),
                              "budget_short_marked": "spade_plate1_only"})


# ==========================================================================
# 5. THE CENTRAL FIGURE — regret against map quality
# ==========================================================================

def _status_at_alpha(certs: dict | None, cond: str, arm: str,
                     alpha: float = 0.95) -> str:
    for c in _rows(certs, "cells", "rows"):
        if (str(c.get("condition_id")) == cond and str(c.get("arm")) == arm
                and _num(c, "alpha") == alpha):
            v = str(c.get("verdict", "INCONCLUSIVE")).upper()
            return v if v in STATUS_FILL else "INCONCLUSIVE"
    return "UNAVAILABLE"


def _draw_marker(ax, x, y, marker, colour, status, size=90):
    if status == "PASS":
        ax.scatter([x], [y], marker=marker, s=size, color=colour, zorder=5,
                   edgecolor=INK, linewidth=0.7)
    elif status == "FAIL":
        ax.scatter([x], [y], marker=marker, s=size, facecolor="white", zorder=5,
                   edgecolor=colour, linewidth=1.6)
    elif status == "INCONCLUSIVE":
        ax.scatter([x], [y], marker=marker, s=size, facecolor="white", zorder=5,
                   edgecolor=colour, linewidth=1.2, hatch="////")
    else:
        ax.scatter([x], [y], marker=marker, s=size, facecolor="white", zorder=5,
                   edgecolor=colour, linewidth=0.9, linestyle=":")


def figure_pareto(bench: dict | None, certs: dict | None, out: Path) -> Rendered | None:
    """**The paper's central figure.** Regret against map quality, one panel per
    condition.

    Four channels, all four load-bearing:

    * **x** primary-rule (P) regret — §7.4's primary estimand, and *only* rule P;
      mixing rules across arms is a protocol violation (§43.1 records this project
      doing it and withdrawing the claim);
    * **y** predictive symmetric-difference error — §7.2's primary map scalar, and
      the only honest single one: type I read alone ranks silence first (§9.4);
    * **shape** rounds, because wells and rounds are separate axes (§4.1) and a
      2-round arm and a 10-round arm are not the same kind of procedure;
    * **fill** certificate status at α=0.95 — PASS solid, FAIL open, INCONCLUSIVE
      hatched, UNAVAILABLE dotted. A cell with no certificate row was not
      assessed, and the fourth state exists so that is visible rather than
      collapsed into the third.

    Colour is method family and every point is directly labelled with its arm, so
    identity never depends on hue.

    The Pareto frontier is drawn because the figure's entire job is to show that
    **the lowest-regret arm need not be the best-map arm.** FINDINGS §13 measured
    that inversion directly. Where the two differ the caption names both arms,
    because a reader who takes one number away from this figure should not be able
    to take away the wrong one.
    """
    rows = _rows(bench)
    if not rows:
        return None
    conds = sorted({str(r.get("condition_id")) for r in rows})
    fig, axes = plt.subplots(1, max(1, len(conds)),
                             figsize=(4.4 * max(1, len(conds)), 4.2), dpi=200,
                             squeeze=False)
    best_regret_arm = best_map_arm = None

    for ax, cond in zip(axes[0], conds, strict=False):
        _style(ax)
        pts = []
        for arm, arm_rows in sorted(_by([r for r in rows
                                         if str(r.get("condition_id")) == cond],
                                        "arm").items()):
            x = _mean(arm_rows, "regret_rule_p")
            y = _mean(arm_rows, "symmetric_difference_pred")
            if x is None or y is None:
                continue
            rounds = int(_num(arm_rows[0], "rounds") or 0)
            pts.append((str(arm), x, y, rounds, _family(arm_rows[0]),
                        _status_at_alpha(certs, cond, str(arm))))
        if not pts:
            continue
        for arm, x, y, rounds, fam, status in pts:
            colour = FAMILY_COLOUR.get(fam, UNKNOWN_COLOUR)
            _draw_marker(ax, x, y, ROUND_MARKER.get(rounds, "P"), colour, status)
            ax.annotate(arm, (x, y), textcoords="offset points", xytext=(7, -3),
                        fontsize=6, color=colour)

        front = []
        for arm, x, y, *_ in sorted(pts, key=lambda p: (p[1], p[2])):
            if not front or y < front[-1][2]:
                front.append((arm, x, y))
        ax.plot([p[1] for p in front], [p[2] for p in front], color=MUTED,
                linewidth=1.1, linestyle="-", alpha=0.7, zorder=3)

        br = min(pts, key=lambda p: p[1])
        bm = min(pts, key=lambda p: p[2])
        if best_regret_arm is None:
            best_regret_arm, best_map_arm, first_cond = br[0], bm[0], cond
        ax.set_title(f"{cond} — regret (rule P) vs map error", fontsize=9.5,
                     color=INK, loc="left", pad=8)
        ax.set_xlabel("primary-rule (P) regret  →  worse", fontsize=8.5, color=INK)
    axes[0][0].set_ylabel("predictive symmetric difference  →  worse", fontsize=8.5,
                          color=INK)

    handles = [Line2D([], [], marker=m, linestyle="", color=INK, markersize=6,
                      markerfacecolor="none", label=f"{r} round(s)")
               for r, m in sorted(ROUND_MARKER.items())]
    handles += [Line2D([], [], marker="o", linestyle="", color=c, markersize=6,
                       label=f) for f, c in FAMILY_COLOUR.items()]
    handles += [Line2D([], [], marker="o", linestyle="", color=INK, markersize=6,
                       label="cert α=0.95: PASS solid · FAIL open · INCONCLUSIVE "
                             "hatched · UNAVAILABLE dotted")]
    axes[0][-1].legend(handles=handles, fontsize=5.8, frameon=False,
                       loc="upper right", ncol=1)

    if best_regret_arm is None:
        plt.close(fig)
        return None
    same = best_regret_arm == best_map_arm
    verdict = (f"In {first_cond} the lowest-regret arm is {best_regret_arm} and the "
               f"lowest-symmetric-difference arm is {best_map_arm} — these are NOT the "
               f"same arm, and no single ranking of the twelve is available."
               if not same else
               f"In {first_cond} {best_regret_arm} is lowest on both axes; that "
               f"coincidence is a result about this condition, not a general ordering.")
    cap = (f"Regret against map quality, the study's central figure. Conditions "
           f"{', '.join(conds)}; terminal rule P throughout (§7.4 — rule A is never "
           f"mixed in); n={len(rows)} rows. Shape = rounds (§4.1), colour = method "
           f"family, fill = certificate status at α=0.95, label = arm. {verdict}")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-pareto.png"), cap,
                    encoding={"x": "regret_rule_p",
                              "y": "symmetric_difference_pred",
                              "shape": "rounds", "colour": "arm_family",
                              "fill": "certificate_status_alpha_0.95",
                              "label": "arm", "frontier": True},
                    annotations=[verdict])


# ==========================================================================
# 6. Murphy decomposition
# ==========================================================================

def figure_murphy(bench: dict | None, out: Path) -> Rendered | None:
    """Calibration against refinement, the two halves reported separately.

    **Form: scatter, calibration on x with lower-is-better pointing left.**
    §28's table is why the two are never summarised into one number: `doe` is
    first on regret and *ninth of nine* on calibration, at 5.2x the calibration
    error of any other arm in the study, and a combined score hides precisely that
    arm. A design space is a calibrated absolute statement (§9.4), so calibration
    is the axis a certificate claim has to survive.
    """
    rows = _rows(bench)
    pts = []
    for cond, crows in sorted(_by(rows, "condition_id").items()):
        for arm, arows in sorted(_by(crows, "arm").items()):
            cal, ref = _mean(arows, "murphy_calibration"), _mean(arows, "murphy_refinement")
            if cal is not None and ref is not None:
                pts.append((str(cond), str(arm), cal, ref, _family(arows[0])))
    if not pts:
        return None

    fig, ax = plt.subplots(figsize=(5.4, 4.2), dpi=200)
    _style(ax)
    for cond, arm, cal, ref, fam in pts:
        colour = FAMILY_COLOUR.get(fam, UNKNOWN_COLOUR)
        ax.scatter([cal], [ref], s=40, color=colour, alpha=0.85, edgecolor="white",
                   linewidth=0.8, zorder=4)
        ax.annotate(f"{arm}", (cal, ref), textcoords="offset points", xytext=(6, -3),
                    fontsize=5.6, color=colour)
    ax.set_xlabel("Murphy calibration  →  worse", fontsize=9, color=INK)
    ax.set_ylabel("Murphy refinement  →  worse", fontsize=9, color=INK)
    ax.set_title("Calibration and refinement, never combined into one score",
                 fontsize=10, color=INK, loc="left", pad=8)

    conds = sorted({c for c, *_ in pts})
    cap = (f"Murphy calibration against refinement, one point per arm per condition. "
           f"Conditions {', '.join(conds)}; terminal rule {_terminal_rules(rows)}; "
           f"n={len(rows)} rows over {len(pts)} arm-condition points. Reported "
           f"separately on purpose: FINDINGS §28 has an arm first on regret and last "
           f"on calibration in the same cell, and any combined score hides it.")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-murphy.png"), cap,
                    encoding={"x": "murphy_calibration", "y": "murphy_refinement",
                              "colour": "arm_family", "combined_score": False})


# ==========================================================================
# 7. Threshold feasibility — tau against the ceiling
# ==========================================================================

def figure_threshold_feasibility(feas: dict | None, out: Path) -> Rendered | None:
    """`tau` against `tau_max`, with the excluded cells drawn, not dropped.

    **Excluded cells stay on the page.** §4.5 records an earlier registration whose
    four absolute thresholds *all* sat above the ceiling: every arm would have
    certified nothing and the published table would have been zeros, read
    inevitably as a method failure. KF-9 makes an above-ceiling cell INFEASIBLE
    and excludes it before campaigns run — but a figure that also excludes it
    makes the exclusion invisible, and an invisible exclusion is indistinguishable
    from a cell that was never planned.
    """
    rows = _rows(feas)
    pts = [(r, _num(r, "tau_raw"), _num(r, "tau_max_worst")) for r in rows]
    pts = [(r, t, c) for r, t, c in pts if t is not None and c is not None]
    if not pts:
        return None

    fig, ax = plt.subplots(figsize=(5.4, 4.0), dpi=200)
    _style(ax)
    hi = max(max(t for _, t, _ in pts), max(c for _, _, c in pts)) * 1.08
    ax.plot([0, hi], [0, hi], color=MUTED, linestyle="--", linewidth=1.2, zorder=2)
    ax.annotate("τ = τ_max — the certifiability ceiling", (hi, hi),
                textcoords="offset points", xytext=(-4, -12), fontsize=7,
                color=MUTED, ha="right")
    excluded = 0
    for r, tau, ceil in pts:
        cls = str(r.get("regime_class"))
        out_of_range = cls == "INFEASIBLE"
        excluded += out_of_range
        ax.scatter([ceil], [tau], s=52,
                   marker="X" if out_of_range else "o",
                   facecolor="white" if out_of_range else FAMILY_COLOUR["SPADE"],
                   edgecolor=FAMILY_COLOUR["BO"] if out_of_range else "white",
                   linewidth=1.4 if out_of_range else 0.9, zorder=4)
        ax.annotate(f"{r.get('condition_id')} τf={r.get('tau_frac')}", (ceil, tau),
                    textcoords="offset points", xytext=(6, -3), fontsize=6,
                    color=FAMILY_COLOUR["BO"] if out_of_range else INK)
    ax.set_xlabel("τ_max at the worst primary γ", fontsize=9, color=INK)
    ax.set_ylabel("τ (raw) = τ_frac · μ_max", fontsize=9, color=INK)
    ax.set_title(f"Threshold feasibility — {excluded} cell(s) excluded pre-run, shown",
                 fontsize=10, color=INK, loc="left", pad=8)

    conds = sorted({str(r.get("condition_id")) for r, _, _ in pts})
    cap = (f"Every planned threshold against its own certifiability ceiling. "
           f"Conditions {', '.join(conds)}; terminal rule n/a (this is a pre-run "
           f"classification, computed from oracle geometry and the frozen plate-1 "
           f"pilot only, §5.1); n={len(pts)} cells, of which {excluded} are above the "
           f"ceiling and excluded. Excluded cells are drawn as crosses rather than "
           f"removed: an above-ceiling τ is a property of the threshold and never a "
           f"method failure (KF-9), and an invisible exclusion cannot be checked.")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-threshold-feasibility.png"), cap,
                    encoding={"x": "tau_max_worst", "y": "tau_raw",
                              "excluded_shown": True, "n_excluded": excluded})


# ==========================================================================
# 8. Cross-condition — TARGET / ROBUSTNESS / EXCEPTION kept apart
# ==========================================================================

CLASS_ORDER = ("TARGET", "ROBUSTNESS", "EXCEPTION", "INFEASIBLE")
CLASS_COLOUR = {"TARGET": "#0072B2", "ROBUSTNESS": "#E69F00",
                "EXCEPTION": "#D55E00", "INFEASIBLE": "#6b6b6b"}


def figure_cross_condition(feas: dict | None, bench: dict | None,
                           out: Path) -> Rendered | None:
    """Every condition, grouped by its pre-run regime class, with a visible gutter.

    **The separation is the content.** §5.1 assigns the class from oracle geometry
    and a frozen pilot, before any arm runs, precisely so `TARGET` cannot come to
    mean "where SPADE won". A figure that laid all conditions on one axis would
    invite exactly the pooling the classification exists to prevent — and §10 KF-2
    turns on whether validity extends *beyond* the historical condition, which is
    a question about the gutter.

    A condition with no benchmark rows still gets its slot, labelled with its
    class and reason. §9.5: an exception is reported, not omitted.
    """
    rows = _rows(feas)
    if not rows:
        return None
    by_cond: dict[str, dict] = {}
    for r in rows:
        by_cond.setdefault(str(r.get("condition_id")), r)
    order = sorted(by_cond, key=lambda c: (
        CLASS_ORDER.index(str(by_cond[c].get("regime_class")))
        if str(by_cond[c].get("regime_class")) in CLASS_ORDER else 9, c))
    groups = sorted({str(by_cond[c].get("regime_class")) for c in order},
                    key=lambda k: CLASS_ORDER.index(k) if k in CLASS_ORDER else 9)

    brows = _rows(bench)
    fig, ax = plt.subplots(figsize=(2.2 + 1.6 * len(order), 3.8), dpi=200)
    _style(ax)
    x, ticks, labels, n_used = 0.0, [], [], 0
    prev_class = None
    for cond in order:
        cls = str(by_cond[cond].get("regime_class"))
        if prev_class is not None and cls != prev_class:
            x += 0.9  # the gutter -- the whole point of the figure
            ax.axvline(x - 0.45, color=GRID, linewidth=1.0, zorder=1)
        prev_class = cls
        sel = [r for r in brows if str(r.get("condition_id")) == cond]
        vals = [v for v in (_num(r, "symmetric_difference_pred") for r in sel)
                if v is not None]
        n_used += len(vals)
        if vals:
            ax.scatter(np.full(len(vals), x) + np.linspace(-0.16, 0.16, len(vals)),
                       vals, s=18, color=CLASS_COLOUR.get(cls, UNKNOWN_COLOUR),
                       alpha=0.75, edgecolor="white", linewidth=0.5, zorder=4)
            ax.plot([x - 0.24, x + 0.24], [np.median(vals)] * 2, color=INK,
                    linewidth=1.8, zorder=5)
        else:
            ax.annotate("no benchmark rows\n(reported, not omitted)", (x, 0.5),
                        xycoords=("data", "axes fraction"), fontsize=6,
                        color=CLASS_COLOUR.get(cls, UNKNOWN_COLOUR), ha="center")
        ticks.append(x)
        labels.append(f"{cond}\n{cls}")
        x += 1.0
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=6.8)
    ax.set_ylabel("symmetric-difference error", fontsize=9, color=INK)
    ax.set_title("Conditions kept apart by pre-run regime class", fontsize=10,
                 color=INK, loc="left", pad=8)

    cap = (f"Every planned condition, grouped by the regime class assigned before any "
           f"arm ran (§5.1). Conditions {', '.join(order)}; terminal rule "
           f"{_terminal_rules(brows) if brows else 'n/a'}; n={n_used} rows. Classes "
           f"present: {', '.join(groups)}. The gutters are load-bearing: a TARGET "
           f"number and a ROBUSTNESS number are not interchangeable, and KF-2 turns "
           f"on whether validity extends beyond the historical condition.")
    _caption(fig, cap)
    return Rendered(_save(fig, out / "final-spade-cross-condition.png"), cap,
                    encoding={"groups": groups, "x": "condition_id",
                              "y": "symmetric_difference_pred",
                              "colour": "regime_class"})


# ==========================================================================
# Driver
# ==========================================================================

def make_all_figures(results_dir: Path = RESULTS,
                     out_dir: Path = OUT_DIR) -> dict[str, Rendered | None]:
    """Write every figure that has its input. Returns name -> Rendered or None.

    Nothing here raises on a missing artefact. Every input is skipped with a
    printed message, because the study has not run and a script that dies on the
    first absent file cannot be exercised before it is needed — and a figure
    script first exercised on the real results is a figure script whose framing
    choices were made with the results visible.
    """
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bench = _read(results_dir, "benchmark")
    certs = _read(results_dir, "certificates")
    feas = _read(results_dir, "feasibility")

    made: dict[str, Rendered | None] = {
        "crossfit_containment": figure_crossfit_containment(certs, out_dir),
        "same_draw_vs_crossfit": figure_same_draw_vs_crossfit(certs, out_dir),
        "allocation_tradeoff": figure_allocation_tradeoff(bench, out_dir),
        "causal_controls": figure_causal_controls(bench, out_dir),
        "pareto": figure_pareto(bench, certs, out_dir),
        "murphy": figure_murphy(bench, out_dir),
        "threshold_feasibility": figure_threshold_feasibility(feas, out_dir),
        "cross_condition": figure_cross_condition(feas, bench, out_dir),
    }
    for name in FIGURES:
        r = made.get(name)
        if r is None:
            print(f"SKIP  {name} — its input artefact is absent; not drawn")
        else:
            print(f"wrote {r.path.relative_to(out_dir.parent.parent) if out_dir.is_absolute() else r.path}")
    return made


if __name__ == "__main__":
    make_all_figures()
