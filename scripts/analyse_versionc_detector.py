"""Version C section 3.3 -- select a statistic and fit the ONE-CLASS boundary.

    .venv/bin/python scripts/analyse_versionc_detector.py

**This script does not score hartmann6 or ackley and cannot be made to.** It proposes the
rule. Freezing it is a separate, deliberate act: the proposal is written into
`docs/OPEN-QUESTIONS.md` and committed, and only then is the held-out set scored, **once**.

WHY THE RULE IS ONE-CLASS
-------------------------
Section 3.3 says fit on hill / levy / rosenbrock and score once on hartmann6 / ackley.
Checked against the committed Q53 table: **levy is null at all four cells, rosenbrock is
null at all four**, and hill ties. So every family in the fit set is on the *same side* of
the boundary and both held-out families are the entire other side.

A discriminative threshold cannot be fitted on one class. Fitting one anyway would mean
looking at a deceptive landscape, which is the single thing this protocol exists to
forbid. What *is* fittable from one class is a **novelty boundary**:

    DECEPTIVE  if the statistic falls OUTSIDE the support observed on the tie families
    UNIMODAL   otherwise

HOW THE STATISTIC IS CHOSEN, USING ONLY THE FIT SET
----------------------------------------------------
Two criteria, both computable without a deceptive example:

* **Usable** -- the statistic must actually vary. A constant cannot exclude anything, and
  two of section 3.2's six candidates are constant at this budget (`n_local_maxima` is
  identically zero; `{x : LCB >= max LCB}` always has one component). Excluded by name.
* **Tight** -- among usable statistics, prefer the one whose support on the tie families
  is narrowest **relative to its own scale**, because a narrow support is a boundary that
  more of the space falls outside of. Relative and not absolute: `ard_separation_ratio`
  runs in the units of a ratio of lengthscales and `additive_share` in [0, 1], so an
  absolute spread would simply pick whichever happens to live on the smaller axis.

**No margin is added to the support.** A margin is a free parameter and the fit set
contains nothing to choose it against; choosing one by looking at hartmann6 is exactly the
forbidden move. The boundary is the empirical support, inclusive.

**The rule is two-sided.** A deceptive landscape could sit on either side of the tie
families' support, and picking a side would be a guess made without a single deceptive
example to check it against.

WHAT IT COSTS, STATED BEFORE THE PASS RATHER THAN AFTER
--------------------------------------------------------
A one-class boundary has **no fitted false-positive rate against real deceptive
landscapes**. Its power is unknown until the single scoring pass, and that pass cannot be
repeated to improve it. If it misfires, K-C7 fires and Version C ships without Stage 0 --
which section 3.6 already registered as an acceptable outcome and a smaller but real
finding.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

#: The four that survived measurement, plus the usable form of the peak count. See
#: `docs/OPEN-QUESTIONS.md` C3.2a for the two that did not and why.
VIABLE_STATISTICS = ("n_components_plausible", "n_peaks_raw", "additive_share",
                     "additive_refit_residual", "ard_separation_ratio")

FITTING_FAMILIES = ("hill", "levy", "rosenbrock")
HELD_OUT_FAMILIES = ("hartmann6", "ackley")

IN = ROOT / "results" / "versionc-detector-fit.json"

#: Attainable range, where one exists. A novelty rule can only fire OUTSIDE the support,
#: so how much attainable range the support leaves over is the rule's power -- and it is
#: computable from the fit set alone, before the single scoring pass rather than after it.
#: `n_peaks_raw` and `ard_separation_ratio` have no upper bound and get `None`, which is
#: honest where a number would read as power.
STATISTIC_BOUNDS = {"additive_share": (0.0, 1.0)}


def _values(rows: list[dict], stat: str) -> list[float]:
    return [float(r[stat]) for r in rows if r.get(stat) is not None]


def _guard(rows: list[dict]) -> None:
    """Defence in depth. The runner cannot construct a held-out family; this refuses to
    read one if it somehow reaches the file."""
    seen = {r.get("family") for r in rows} & set(HELD_OUT_FAMILIES)
    if seen:
        raise ValueError(
            f"held-out families {sorted(seen)} appear in the fitting set. Section 3.3 "
            f"scores them exactly once, after the rule is frozen and committed. Refusing "
            f"to fit a threshold on them.")


def is_usable(rows: list[dict], stat: str = "additive_share") -> bool:
    """Does the statistic vary at all? A constant cannot exclude anything."""
    vals = _values(rows, stat)
    return len(set(vals)) > 1


def one_class_boundary(rows: list[dict], stat: str) -> tuple[float, float]:
    """``(min, max)`` observed across **all** fitting families, pooled.

    Pooled and not per-family: the detector sees one plate with no family label on it, so
    a per-family boundary would be three rules and no way to choose between them.
    """
    vals = _values(rows, stat)
    if not vals:
        raise ValueError(f"no values for {stat!r}")
    return (min(vals), max(vals))


def tightness(rows: list[dict], stat: str) -> float:
    """Support width **relative to the statistic's own scale**. Lower is better.

    ``(max - min) / max(|median|, 1e-12)``. Relative because the candidates live on
    different axes and an absolute width would always prefer whichever is smaller.
    """
    lo, hi = one_class_boundary(rows, stat)
    med = st.median(_values(rows, stat))
    return (hi - lo) / max(abs(med), 1e-12)


def excluded_fraction(stat: str, boundary: tuple[float, float]) -> float | None:
    """Fraction of the statistic's attainable range the boundary would fire on.

    ``None`` for a statistic with no attainable range. **This is the rule's power**, and
    it needs no deceptive example: a novelty rule fires only outside the support, so if
    the tie families already span most of the range there is almost nothing left to fire
    on -- knowable before the scoring pass rather than after it.
    """
    bounds = STATISTIC_BOUNDS.get(stat)
    if bounds is None:
        return None
    lo_b, hi_b = bounds
    span = hi_b - lo_b
    lo, hi = boundary
    inside = min(hi, hi_b) - max(lo, lo_b)
    return max(0.0, (span - inside) / span)


def within_family_share(rows: list[dict], stat: str) -> float:
    """Mean per-family support width over the pooled support width.

    Near 1 means **each family alone spans nearly the whole pooled range**, so the
    statistic is dominated by seed-to-seed variation rather than by landscape class. A
    boundary drawn on such a statistic cannot separate classes it cannot even order, and
    that verdict is available from the fit set without touching a held-out family.
    """
    lo, hi = one_class_boundary(rows, stat)
    pooled = hi - lo
    if pooled <= 0:
        return 1.0
    widths = []
    for f in FITTING_FAMILIES:
        vals = _values([r for r in rows if r.get("family") == f], stat)
        if len(vals) > 1:
            widths.append(max(vals) - min(vals))
    return (sum(widths) / len(widths) / pooled) if widths else 1.0


def classify(value: float, boundary: tuple[float, float]) -> str:
    """Inside the support is UNIMODAL, outside in **either** direction is DECEPTIVE."""
    lo, hi = boundary
    return "UNIMODAL" if lo <= value <= hi else "DECEPTIVE"


def rank_statistics(rows: list[dict]) -> list[dict]:
    """Usable statistics, tightest first. Raises if a held-out family is present."""
    _guard(rows)
    out = []
    for stat in VIABLE_STATISTICS:
        if not _values(rows, stat) or not is_usable(rows, stat):
            continue
        lo, hi = one_class_boundary(rows, stat)
        vals = _values(rows, stat)
        out.append({"statistic": stat, "lo": lo, "hi": hi,
                    "tightness": tightness(rows, stat),
                    "excluded_fraction": excluded_fraction(stat, (lo, hi)),
                    "within_family_share": within_family_share(rows, stat),
                    "median": st.median(vals), "n": len(vals),
                    "per_family": {
                        f: [min(v), max(v)] for f in FITTING_FAMILIES
                        if (v := _values([r for r in rows if r.get("family") == f], stat))}})
    return sorted(out, key=lambda d: d["tightness"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(IN))
    args = ap.parse_args()

    payload = json.loads(Path(args.file).read_text())
    rows = payload["rows"] if isinstance(payload, dict) else payload
    if isinstance(payload, dict) and not payload.get("complete", True):
        print(f"  ! PARTIAL: {payload.get('keys_present')} of "
              f"{payload.get('keys_expected')} rows")

    ranked = rank_statistics(rows)
    fams = sorted({r["family"] for r in rows})
    print(f"Version C section 3.3 · one-class boundary · fit set {fams} · {len(rows)} rows")
    print("  the fit set is SINGLE-CLASS (levy and rosenbrock are null at every Q53 cell,")
    print("  hill ties), so the rule is a novelty boundary, not a discriminative one.\n")

    print(f"{'statistic':<26}{'support':>24}{'tight':>9}{'fires on':>10}"
          f"{'within/pooled':>15}")
    for r in ranked:
        support = f"[{r['lo']:.4g}, {r['hi']:.4g}]"
        ef = "n/a" if r["excluded_fraction"] is None else f"{r['excluded_fraction']:.1%}"
        print(f"{r['statistic']:<26}{support:>24}{r['tightness']:>9.3f}{ef:>10}"
              f"{r['within_family_share']:>15.2f}")

    if not ranked:
        print("\nNO USABLE STATISTIC. K-C7 fires: ship without Stage 0 (section 3.6).")
        return

    best = ranked[0]
    print(f"\nPROPOSED RULE (not yet frozen):")
    print(f"  DECEPTIVE if {best['statistic']} outside "
          f"[{best['lo']:.6g}, {best['hi']:.6g}], inclusive; UNIMODAL otherwise")
    print(f"  chosen as the tightest usable statistic on the fit set "
          f"(relative width {best['tightness']:.3f})")
    if best["excluded_fraction"] is not None:
        print(f"  POWER: fires on {best['excluded_fraction']:.1%} of the attainable range")
    noisy = best["within_family_share"] > 0.7
    note = "  <- dominated by seed noise, not by landscape class" if noisy else ""
    print(f"  within-family / pooled spread: {best['within_family_share']:.2f}{note}")
    weak = best["excluded_fraction"] is not None and best["excluded_fraction"] < 0.30
    if weak or noisy:
        print("\n  ** K-C7 IS LIKELY TO FIRE. ** The tie families already span most of")
        print("  this statistic's range, so the boundary has little left to fire on. That")
        print("  is a prediction made from the FIT SET ALONE, before the scoring pass --")
        print("  it does not consume the one look at hartmann6 and ackley.")
    print("\n  per-family support:")
    for f, (lo, hi) in best["per_family"].items():
        print(f"    {f:<12} [{lo:.6g}, {hi:.6g}]")
    print("\n  NOT FROZEN. Freezing is a deliberate act: write this into")
    print("  docs/OPEN-QUESTIONS.md, commit, and only then score hartmann6 and ackley,")
    print("  ONCE. The scoring pass cannot be repeated to improve the rule.")

    out = Path(args.file).with_name("versionc-detector-boundary.json")
    out.write_text(json.dumps({"source": str(args.file), "fit_families": fams,
                               "single_class": True, "ranked": ranked,
                               "proposed": best, "frozen": False}, indent=1))
    print(f"\nwrote {out.name}")


if __name__ == "__main__":
    main()
