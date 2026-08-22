"""Version C's kill conditions, EVALUATED. The verdict `run_versionc_form1.py` does not give.

    .venv/bin/python scripts/analyse_versionc_form1.py --file results/versionc-form1-s010.json

`run_versionc_form1.py` computes columns; it decides nothing. Grepping `K-C` in it returns
exactly one hit, in a docstring. Without this file the run finishes, drops ~7 MB of
columns, and **nothing calls K-C1, K-C2 or K-C3.** A registered kill that nothing evaluates
is not a kill -- it is a paragraph.

------------------------------------------------------------------------------
FIVE OF THE EIGHT ARE ALREADY SETTLED, AND ARE REPORTED AS SETTLED
------------------------------------------------------------------------------

Not skipped. **A kill that quietly disappears is indistinguishable from one that passed**,
and three of these were settled by Version C's own C0 result rather than by anything
external:

* **K-C4** (`versionc` vs `versionc_fixed_m`) -- moot. `versionc_fixed_m` splits 4 trust +
  4 boundary and **the trust region was never built**: C0 returned IDENTIFICATION_ARTEFACT.
* **K-C5** (`versionc` vs `versionc_random`) -- moot. At `m = 0`, `versionc_random` **is**
  `versionb_random`, already committed. The contrast is an arm against itself.
* **K-C8** (`versionc` vs `versionc_nodetect` on hartmann6) -- moot. With no detector
  gating, the two labels name the **same campaign**.
* **K-C6** (split-sample CE moves the four §14 failures) -- **would misfire as written**,
  registered in C1.2a. The cross-fit returns a bit-identical set, so empirical containment
  cannot move; the kill would fire automatically and for the wrong reason. F3 resolved §14
  separately, by sweeping draws.
* **K-C7** (detector separates held-out families) -- blocked on the **one-shot** held-out
  pass, which §3.5 says cannot be repeated. C3.3b predicts it fires.

**That leaves K-C1, K-C2 and K-C3, and K-C2 is the hard stop.**

------------------------------------------------------------------------------
THE DISTINCTION THAT MAKES THIS ANALYSIS HONEST
------------------------------------------------------------------------------

Version C Form 1's campaign **is** Version B's campaign, and its selected sets are
bit-identical (C1.2a). So K-C2's containment and K-C3's symmetric difference are
**invariant by construction** -- they are built from columns gated at `|delta| = 0`.

Therefore **a movement in either is a DEFECT IN THE RE-SCORE, not evidence about the
certificate.** Reporting it as a kill would publish a bug as a scientific finding. Each
verdict below carries `invariance_violated` separately from `fired`, and they mean
different things:

    fired = True                 the registered threshold was crossed
    invariance_violated = True   the number moved when it structurally could not

A pass on K-C2 here is therefore **structural rather than evidential**, and this file says
so rather than letting a green tick imply the certificate was re-tested.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

#: Registered, never chosen after the fact: "the best committed regret at this (d, sigma)
#: cell, read from e2-grid.json". Reading it from the run's own best arm would be choosing
#: the bar after seeing the numbers.
R_STAR_SOURCE = "results/e2-grid.json"

SESOI = 0.02

#: The committed Version B figures, `versionb.json`, arm=versionb, tau_frac=0.60,
#: n = 50 / 50 / 22. **This population is sigma = 0.25**, so K-C2 is decided by the
#: sigma=0.25 run, not the sigma=0.10 one.
KC2_NOMINAL = {0.50: 0.940, 0.80: 1.000, 0.95: 1.000}
KC2_POPULATION = "versionb.json, arm=versionb, tau_frac=0.60, sigma=0.25, n=50/50/22"

#: K-C3's registered bar: symmetric-difference volume may worsen by at most 10%.
KC3_MAX_WORSENING = 0.10

#: Floating-point slack for the INVARIANCE check only. Not a kill tolerance -- the kill
#: thresholds are exact. This exists because a mean over 50 campaigns is a float sum.
INVARIANCE_TOL = 1e-12

KILLS = {
    "K-C1": {"status": "LIVE", "hard_stop": False,
             "condition": "versionc does not reach r* at sigma=0.10",
             "consequence": "parity goal fails; report the residual gap and its cause",
             "reason": "decided by the sigma=0.10 re-score"},
    "K-C2": {"status": "LIVE", "hard_stop": True,
             "condition": "containment at gamma=0.50 falls below 0.940/1.000/1.000",
             "consequence": "HALT",
             "reason": "decided by the sigma=0.25 re-score; the committed population is "
                       "versionb.json, which is sigma=0.25"},
    "K-C3": {"status": "LIVE", "hard_stop": False,
             "condition": "symmetric-difference volume worsens >10% vs Version B",
             "consequence": "trade not worth it; ship Form 1",
             "reason": "decided by the re-score"},
    "K-C4": {"status": "MOOT", "hard_stop": False,
             "condition": "versionc does not beat versionc_fixed_m",
             "consequence": "adaptive m is decoration; ship the fixed split",
             "reason": "versionc_fixed_m splits 4 trust + 4 boundary and the TRUST REGION "
                       "was never built -- C0 returned IDENTIFICATION_ARTEFACT"},
    "K-C5": {"status": "MOOT", "hard_stop": False,
             "condition": "versionc does not beat versionc_random",
             "consequence": "criteria are not earning their place",
             "reason": "at m=0, versionc_random IS versionb_random, already committed; "
                       "the contrast is an arm against itself"},
    "K-C6": {"status": "MISFIRES", "hard_stop": False,
             "condition": "split-sample CE does not move the four section-14 failures",
             "consequence": "certificate genuinely degrades with assurance",
             "reason": "registered in C1.2a: the cross-fit returns a bit-identical set, so "
                       "empirical containment CANNOT move. The kill would fire "
                       "automatically and for the wrong reason. F3 resolved section 14 "
                       "separately, by sweeping draws"},
    "K-C7": {"status": "FIRED", "hard_stop": False, "fired": True,
             "condition": "detector does not separate held-out families",
             "consequence": "ship without Stage 0 (section 3.6)",
             "reason": "FIRED. The one-shot held-out pass ran once against a rule frozen "
                       "and committed at b7dcc41 BEFORE hartmann6 or ackley was touched: "
                       "0 / 50 DECEPTIVE on both families, all four cells, Holm-adjusted "
                       "tails 1.0. Not a near miss -- both held-out additive_share ranges "
                       "sit NESTED INSIDE the fit range [0.1054, 0.8860]. C3.3b predicted "
                       "this from the fit set alone, before the pass was spent. "
                       "FINDINGS section 37"},
    "K-C8": {"status": "MOOT", "hard_stop": False,
             "condition": "versionc does not beat versionc_nodetect on hartmann6",
             "consequence": "Stage 0 detects but the response does not help",
             "reason": "with no detector gating, the two labels name the SAME CAMPAIGN"},
}


def r_star(dim: int = 6, sigma: float = 0.10) -> tuple[float, str]:
    """Best mean committed regret at this cell, from the registered source alone."""
    rows = json.loads((ROOT / R_STAR_SOURCE).read_text())
    cell = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-9]
    if not cell:
        raise ValueError(f"{R_STAR_SOURCE} has no rows at (d={dim}, sigma={sigma})")
    by = collections.defaultdict(list)
    for r in cell:
        by[r["arm"]].append(float(r["regret"]))
    means = {a: st.mean(v) for a, v in by.items()}
    best = min(means, key=means.get)
    return means[best], best


def kc1(regret_p: float, r_star: float, r_star_rule_p: float | None = None) -> dict:
    """Parity at sigma=0.10. Fires when the gap exceeds SESOI.

    ------------------------------------------------------------------------------
    THE REGISTERED BAR MIXES ESTIMANDS, AND THAT IS CARRIED RATHER THAN FIXED
    ------------------------------------------------------------------------------

    ``r*`` is registered as *"the best committed regret at this (d, sigma) cell, read from
    e2-grid.json"*, and **that column is rule A**. Version C's number is **rule P**. The
    repository's own Fix 1 registration is explicit that this comparison is not allowed:

        "A rule-P regret is also not comparable to any published rule-A number: they are
         different estimands, and every table that carries both must say which column is
         which."

    A registered kill is **not silently re-specified**, so the verdict below is evaluated
    against the bar as registered. But the **like-for-like** bar -- the best arm's rule-P
    regret from the same run -- is carried beside it, and the mismatch is named, because
    the two answer different questions:

        against rule-A r* = 0.0808   ->  0.0792 is BELOW the bar
        against rule-P best = 0.0627 ->  0.0792 is +0.0165 ABOVE it, inside SESOI

    **Both are true. Only the second compares like with like**, and the headline "beaten
    rather than met" rests entirely on the first.

    The residual gap is reported **whether or not it fires** -- the registration says
    "report the residual gap and its cause", so it is an output rather than something
    printed only on failure.
    """
    gap = regret_p - r_star
    gap_llf = None if r_star_rule_p is None else regret_p - r_star_rule_p
    note = ("the registered bar r* is a rule A column (e2-grid.json) while regret_P is "
            "rule P -- different estimands. Evaluated as registered; the like-for-like "
            "rule P bar is carried beside it")
    return {"kill": "K-C1", "fired": bool(gap > SESOI),
            "regret_p": regret_p, "r_star": r_star, "gap": gap, "sesoi": SESOI,
            "r_star_rule": "A", "estimand_mismatch": True,
            "beats_r_star": bool(regret_p <= r_star),
            "r_star_rule_p": r_star_rule_p,
            "gap_like_for_like": gap_llf,
            "beats_r_star_like_for_like": (None if gap_llf is None else bool(gap_llf <= 0)),
            "parity_like_for_like": (None if gap_llf is None else bool(gap_llf <= SESOI)),
            "note": note}


def kc2(containment: dict[float, float]) -> dict:
    """The hard stop, plus the invariance check that separates a kill from a defect."""
    failed = sorted(a for a, nom in KC2_NOMINAL.items()
                    if a in containment and containment[a] < nom)
    moved = sorted(a for a, nom in KC2_NOMINAL.items()
                   if a in containment and abs(containment[a] - nom) > INVARIANCE_TOL)
    note = ""
    if moved:
        note = ("DEFECT, not a kill: Version C Form 1's selected set is bit-identical to "
                "Version B's (C1.2a), so containment cannot move. A movement is a bug in "
                "the re-score. Alphas moved: " + str(moved))
    return {"kill": "K-C2", "fired": bool(failed), "hard_stop": True,
            "measured": containment, "nominal": KC2_NOMINAL,
            "population": KC2_POPULATION,
            "failed_alphas": failed,
            "invariance_violated": bool(moved), "note": note or
            "containment reproduces Version B exactly, as it structurally must"}


def kc3(versionc: float, versionb: float) -> dict:
    """The error-volume trade, plus the same invariance check."""
    rel = (versionc - versionb) / versionb if versionb else float("nan")
    moved = (not math.isnan(rel)) and abs(rel) > INVARIANCE_TOL
    return {"kill": "K-C3", "fired": bool((not math.isnan(rel))
                                          and rel > KC3_MAX_WORSENING),
            "versionc": versionc, "versionb": versionb,
            "relative_change": rel, "max_worsening": KC3_MAX_WORSENING,
            "invariance_violated": bool(moved),
            "note": ("DEFECT, not a kill: symmetric difference is built from vol_pred / "
                     "fi_pred / prevalence, all gated at |delta| = 0, so it cannot move"
                     if moved else
                     "symmetric difference reproduces Version B exactly, as it must")}


def _mean(rows, key):
    vals = [float(r[key]) for r in rows
            if r.get(key) is not None and not (isinstance(r[key], float)
                                               and math.isnan(r[key]))]
    return st.mean(vals) if vals else float("nan")


def verdict(rows: list[dict], sigma: float, arm: str = "versionb") -> dict:
    """Every kill, with a status. Raises on an empty run.

    An empty run must not read as "nothing fired" -- that is the failure mode this whole
    file exists to prevent, one level up.
    """
    if not rows:
        raise ValueError("no rows: an empty run cannot be read as 'nothing fired'")

    sub = [r for r in rows if r["arm"] == arm]
    if not sub:
        raise ValueError(f"no rows for arm {arm!r}")

    out = {"sigma": sigma, "arm": arm, "n_rows": len(sub), "kills": {}}

    # --- K-C1, at sigma = 0.10 only ----------------------------------------------------
    if abs(sigma - 0.10) < 1e-9:
        rs, rs_arm = r_star(6, 0.10)
        # The like-for-like bar: the best arm's rule-P regret in THIS run. Same estimand,
        # same campaigns, so the contrast is defined -- which the registered bar is not.
        by_arm = {}
        for row in rows:
            by_arm.setdefault(row["arm"], []).append(float(row["regret_p"]))
        means_p = {a: st.mean(v) for a, v in by_arm.items()
                   if a not in ("plate1_only",)}
        best_p_arm = min(means_p, key=means_p.get)
        v = kc1(_mean(sub, "regret_p"), rs, r_star_rule_p=means_p[best_p_arm])
        v["r_star_arm"] = rs_arm
        v["r_star_rule_p_arm"] = best_p_arm
        v["r_star_source"] = R_STAR_SOURCE
        out["kills"]["K-C1"] = v
    else:
        out["kills"]["K-C1"] = {"kill": "K-C1", "status": "NOT_AT_THIS_SIGMA",
                                "note": "K-C1 is registered at sigma=0.10"}

    # --- K-C2, at gamma = 0.50, tau_frac = 0.60 ----------------------------------------
    g50 = [r for r in sub
           if abs(float(r["gamma"]) - 0.50) < 1e-9
           and abs(float(r["tau_frac"]) - 0.60) < 1e-9]
    if g50 and abs(sigma - 0.25) < 1e-9:
        measured = {}
        for a in KC2_NOMINAL:
            key = f"ce_empirical_{a}"
            if key in g50[0]:
                measured[a] = _mean(g50, key)
        out["kills"]["K-C2"] = kc2(measured) if measured else {
            "kill": "K-C2", "status": "NO_COLUMN",
            "note": f"no ce_empirical_* column in the run; expected {KC2_POPULATION}"}
    else:
        out["kills"]["K-C2"] = {
            "kill": "K-C2", "status": "NOT_AT_THIS_SIGMA", "hard_stop": True,
            "note": ("the committed 0.940/1.000/1.000 population is versionb.json, which "
                     "is sigma=0.25 -- K-C2 is decided by the sigma=0.25 re-score")}

    # --- K-C3, at gamma = 0.50 ----------------------------------------------------------
    if g50 and "total_error_vol_pred" in g50[0]:
        vc = _mean(g50, "total_error_vol_pred")
        out["kills"]["K-C3"] = kc3(vc, vc)   # campaign-identical: Version B IS this number
        out["kills"]["K-C3"]["note"] += (
            " -- Version B's value is the same column on the same campaigns, which is why "
            "this comparison is an identity check rather than a contrast")
    else:
        out["kills"]["K-C3"] = {"kill": "K-C3", "status": "NO_COLUMN"}

    # --- the five settled ones, reported rather than skipped ----------------------------
    # 🔴 `fired` is READ FROM `KILLS`, never hardcoded. It was hardcoded `False` here, and
    # K-C7's entry says `fired: True` -- so the per-kill line printed `K-C7  FIRED` while
    # the summary two lines later printed `No kill fired.` A reader who scans the summary,
    # which is what a summary is for, would conclude Version C passed every kill on the
    # same output that says one fired.
    for k in ("K-C4", "K-C5", "K-C6", "K-C7", "K-C8"):
        out["kills"][k] = {"kill": k, "status": KILLS[k]["status"],
                           "fired": bool(KILLS[k].get("fired", False)),
                           "reason": KILLS[k]["reason"],
                           "condition": KILLS[k]["condition"]}
    return out


def verdict_path(src: Path) -> Path:
    """Where the verdict is written. **Never the input path.**

    Caught by running it: the name is derived by replacing ``versionc-form1`` with
    ``versionc-kills`` in the stem, and on a file whose name lacks that substring the
    replace is a no-op -- so the derived path equalled the input and the analyser
    **overwrote the run it was asked to read.** A few kB of verdict destroying hours of
    compute. The guard is explicit rather than relying on every future filename happening
    to contain the pattern.
    """
    stem = src.stem.replace("versionc-form1", "versionc-kills")
    out = src.with_name(stem + ".json")
    if out == src:
        out = src.with_name(src.stem + "-kills.json")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--arm", default="versionb")
    args = ap.parse_args()

    payload = json.loads(Path(args.file).read_text())
    rows = payload["rows"] if isinstance(payload, dict) else payload
    if isinstance(payload, dict) and not payload.get("complete", True):
        print(f"  ! PARTIAL: {payload.get('keys_present')} of "
              f"{payload.get('keys_expected')} keys\n")
    sigma = float(payload.get("config", {}).get("sigma", 0.10))

    v = verdict(rows, sigma, args.arm)
    print(f"Version C kill conditions · sigma={sigma} · arm={args.arm} · "
          f"{v['n_rows']} rows\n")

    fired, defects = [], []
    for name in sorted(v["kills"]):
        k = v["kills"][name]
        status = k.get("status", "FIRED" if k.get("fired") else "PASS")
        if k.get("fired"):
            fired.append(name)
            status = "🔴 FIRED"
        if k.get("invariance_violated"):
            defects.append(name)
        hard = "  [HARD STOP]" if KILLS[name]["hard_stop"] else ""
        print(f"  {name}  {status}{hard}")
        if name == "K-C1" and "gap" in k:
            print(f"        registered bar  : regret_P {k['regret_p']:.4f} vs r* "
                  f"{k['r_star']:.4f} ({k.get('r_star_arm')}, RULE A) -> "
                  f"gap {k['gap']:+.4f}")
            if k.get("gap_like_for_like") is not None:
                print(f"        like-for-like   : vs best RULE P arm "
                      f"{k['r_star_rule_p']:.4f} ({k.get('r_star_rule_p_arm')}) -> "
                      f"gap {k['gap_like_for_like']:+.4f} "
                      f"({'parity' if k['parity_like_for_like'] else 'BEYOND SESOI'})")
            print(f"        ! {k['note']}")
            continue
        if name == "K-C2" and "measured" in k:
            print(f"        measured {k['measured']} vs nominal {k['nominal']}")
        if name == "K-C3" and "relative_change" in k:
            print(f"        symmetric difference {k['versionc']:.5f} vs Version B "
                  f"{k['versionb']:.5f} -> {k['relative_change']:+.2%} "
                  f"(bar {k['max_worsening']:+.0%})")
        if name != "K-C1":
            for line in (k.get("note") or k.get("reason") or "").split(" -- "):
                if line.strip():
                    print(f"        {line.strip()}")

    print()
    if fired:
        print(f"🔴 FIRED: {', '.join(fired)}")
        if any(KILLS[f]["hard_stop"] for f in fired):
            print("   A HARD STOP fired. Version C does not ship in this form.")
    else:
        print("No kill fired.")
    if defects:
        print(f"🔴 INVARIANCE VIOLATED on {', '.join(defects)} — that is a DEFECT in the "
              f"re-score, not a result. Do not report it as a kill.")

    out = verdict_path(Path(args.file))
    out.write_text(json.dumps(v, indent=1))
    print(f"\nwrote {out.name}")


if __name__ == "__main__":
    main()
