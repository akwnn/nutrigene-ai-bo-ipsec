"""P8.1's four registered predictions, adjudicated.

    .venv/bin/python scripts/adjudicate_p8_predictions.py --file results/p8-certificate-families.json

**Written before `rosenbrock` finished and before `ackley` started.** That ordering is the
whole point. An adjudicator authored after seeing the numbers can be tuned to them, however
honestly — by choosing which statistic to privilege, or where to put a boundary that the
registration left slightly loose. This one was written blind, and the bars below are copied
from the registration commits rather than recomputed.

    P1  (c504558)  rosenbrock  <= 8 of 24 cells all-empty   AND  mean alpha_star  > 0.80
    P2  (c504558)  ackley      >= 22 of 24 cells all-empty  AND  mean alpha_star  < 0.10
    P3  (c504558)  cells-empty ranking is the exact reverse of max tau_q, ties allowed
    P4  (5a3d082)  ackley mean empty rate > 0.90  AND  rosenbrock mean empty rate < 0.70

**P3 is expected to fail**, and that expectation is registered in Erratum 33 — recorded
*before* the adjudication, because an expectation announced afterwards is worth nothing.
:data:`P3_EXPECTED_TO_FAIL` records it. **No branch reads it.** A test greps this file for a
conditional on that constant and fails if one appears, so the expectation cannot quietly
become a special case. (That test caught this very docstring on the first run, when it
spelled the forbidden conditional out as an example — which is exactly the check working.)

WHY TWO METRICS
---------------
P1–P3 are in **cells-all-empty** units, which Erratum 33 found is **monotone decreasing in
n** — `levy` read 6/24 at 26 seeds and 2/24 at 50. Every family here runs at n = 50 so the
comparison is sound, and the registered bars are honoured **as written**. P4 uses the
**n-stable mean empty rate**. Both are reported for every family so the difference between
them is visible rather than argued about.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
ALPHA = 0.95
ARM = "versionb"

#: Copied from the registration commits. A test pins them; drift means the prediction
#: adjudicated is not the prediction registered.
BARS = {
    "P1": {"family": "rosenbrock", "max_all_empty": 8, "min_alpha_star": 0.80},
    "P2": {"family": "ackley", "min_all_empty": 22, "max_alpha_star": 0.10},
    "P4": {"ackley_min_empty_rate": 0.90, "rosenbrock_max_empty_rate": 0.70},
}

#: Erratum 33, registered BEFORE this adjudication. Recorded, never acted on.
P3_EXPECTED_TO_FAIL = True

#: `ackley` carries `sensitivity: true` on every p5 row. In for a certificate study, but
#: every ackley figure travels with the flag.
SENSITIVITY_FLAGGED = ("ackley",)


class RunIncomplete(RuntimeError):
    """P1/P2 are per-family bars at n = 50. A partial family answers a different question."""


def assert_complete(payload: dict) -> None:
    if str(payload.get("status", "")).upper() != "COMPLETE":
        raise RunIncomplete(
            f"status={payload.get('status')!r}, "
            f"{payload.get('keys_present')}/{payload.get('keys_expected')} campaigns. "
            f"P1 and P2 are bars at n=50 per family; adjudicating a partial run answers a "
            f"different question and Erratum 33 is what happens when that is forgotten.")


def _a8():
    spec = importlib.util.spec_from_file_location(
        "_p8a", ROOT / "scripts" / "analyse_p8_certificate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def family_stats(rows: list, family: str) -> dict:
    """`all_empty` count, n-stable `empty_rate`, and mean `alpha_star` for one family."""
    a8 = _a8()
    fr = [r for r in rows if r["family"] == family and r["arm"] == ARM]
    if not fr:
        return {"family": family, "n_campaigns": 0, "all_empty": None,
                "empty_rate": None, "alpha_star": None, "n_cells": 0}
    all_empty, rates = 0, []
    for g in GAMMAS:
        for tf in TAU_FRACS:
            sub = [r for r in fr
                   if abs(float(r["gamma"]) - g) < 1e-9
                   and abs(float(r["tau_frac"]) - tf) < 1e-9]
            if not sub:
                continue
            c = a8.containment_rate(sub, ALPHA)
            rates.append(c["empty_rate"])
            if c["n_scored"] == 0:
                all_empty += 1
    ast = [r["alpha_star"] for r in fr
           if r.get("alpha_star") is not None
           and not (isinstance(r["alpha_star"], float) and math.isnan(r["alpha_star"]))]
    return {"family": family, "n_campaigns": len(fr) // (len(GAMMAS) * len(TAU_FRACS)),
            "all_empty": all_empty, "n_cells": len(rates),
            "empty_rate": (st.mean(rates) if rates else None),
            "alpha_star": (st.mean(ast) if ast else None),
            "sensitivity_flagged": family in SENSITIVITY_FLAGGED}


def p1(all_empty: int, alpha_star: float) -> dict:
    b = BARS["P1"]
    c1 = all_empty <= b["max_all_empty"]
    c2 = alpha_star > b["min_alpha_star"]
    return {"prediction": "P1", "held": bool(c1 and c2),
            "all_empty": all_empty, "bar_all_empty": f"<= {b['max_all_empty']}", "c1": c1,
            "alpha_star": alpha_star, "bar_alpha_star": f"> {b['min_alpha_star']}", "c2": c2}


def p2(all_empty: int, alpha_star: float) -> dict:
    b = BARS["P2"]
    c1 = all_empty >= b["min_all_empty"]
    c2 = alpha_star < b["max_alpha_star"]
    return {"prediction": "P2", "held": bool(c1 and c2),
            "all_empty": all_empty, "bar_all_empty": f">= {b['min_all_empty']}", "c1": c1,
            "alpha_star": alpha_star, "bar_alpha_star": f"< {b['max_alpha_star']}", "c2": c2}


def p3(by_family: dict) -> dict:
    """`{family: (max_tau_q, all_empty)}`. Higher `tau_q` must never have MORE empty cells.

    Pairwise rather than by rank position, so ties are allowed on either side and the
    verdict names the offending pair instead of only saying "the ordering failed".
    """
    fams = sorted(by_family)
    violations = []
    for i, a in enumerate(fams):
        for b in fams[i + 1:]:
            (tq_a, ce_a), (tq_b, ce_b) = by_family[a], by_family[b]
            if tq_a > tq_b and ce_a > ce_b:
                violations.append((a, b, tq_a, tq_b, ce_a, ce_b))
            elif tq_b > tq_a and ce_b > ce_a:
                violations.append((b, a, tq_b, tq_a, ce_b, ce_a))
    return {"prediction": "P3", "held": not violations,
            "n_pairs": len(fams) * (len(fams) - 1) // 2, "violations": violations}


def p4(ackley_rate: float, rosenbrock_rate: float) -> dict:
    b = BARS["P4"]
    c1 = ackley_rate > b["ackley_min_empty_rate"]
    c2 = rosenbrock_rate < b["rosenbrock_max_empty_rate"]
    return {"prediction": "P4", "held": bool(c1 and c2),
            "ackley_rate": ackley_rate, "bar_ackley": f"> {b['ackley_min_empty_rate']}",
            "c1": c1, "rosenbrock_rate": rosenbrock_rate,
            "bar_rosenbrock": f"< {b['rosenbrock_max_empty_rate']}", "c2": c2}


def max_tau_q(family: str, dim: int = 6) -> float:
    rows = json.loads((ROOT / "results" / "p5-tau-quantile.json").read_text())["rows"]
    v = [r["tau_q"] for r in rows if r.get("family") == family and r.get("dim") == dim]
    return max(v) if v else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "results" / "p8-certificate-families.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-partial", action="store_true",
                    help="report the table but adjudicate nothing")
    args = ap.parse_args()

    payload = json.loads(Path(args.file).read_text())
    if not args.allow_partial:
        assert_complete(payload)
    rows = payload["rows"]

    fams = ("rosenbrock", "levy", "hill", "hartmann6", "ackley")
    stats = {f: family_stats(rows, f) for f in fams}

    print(f"P8.1 · adjudicating four registered predictions · {Path(args.file).name}")
    print(f"status={payload.get('status')} · arm={ARM} · alpha={ALPHA}\n")
    print(f"  {'family':<12}{'n':>4}{'max tau_q':>11}{'all-empty':>11}"
          f"{'empty rate':>12}{'alpha*':>9}  flag")
    for f in fams:
        s = stats[f]
        if not s["n_campaigns"]:
            print(f"  {f:<12}{'--- not present ---':>47}")
            continue
        cells = "{}/{}".format(s["all_empty"], s["n_cells"])
        flag = "SENSITIVITY" if s["sensitivity_flagged"] else ""
        print(f"  {f:<12}{s['n_campaigns']:>4}{max_tau_q(f):>11.5f}{cells:>11}"
              f"{s['empty_rate']:>12.4f}{s['alpha_star']:>9.4f}  {flag}")

    if args.allow_partial:
        print("\n  --allow-partial: table only, nothing adjudicated.")
        return

    v1 = p1(stats["rosenbrock"]["all_empty"], stats["rosenbrock"]["alpha_star"])
    v2 = p2(stats["ackley"]["all_empty"], stats["ackley"]["alpha_star"])
    v3 = p3({f: (max_tau_q(f), stats[f]["all_empty"]) for f in fams})
    v4 = p4(stats["ackley"]["empty_rate"], stats["rosenbrock"]["empty_rate"])

    print()
    for v in (v1, v2, v3, v4):
        mark = "HELD" if v["held"] else "🔴 FAILED"
        print(f"  {v['prediction']}  {mark}")
        if v["prediction"] == "P1":
            print(f"        all-empty {v['all_empty']} (bar {v['bar_all_empty']}) -> {v['c1']}"
                  f" · alpha* {v['alpha_star']:.4f} (bar {v['bar_alpha_star']}) -> {v['c2']}")
        elif v["prediction"] == "P2":
            print(f"        all-empty {v['all_empty']} (bar {v['bar_all_empty']}) -> {v['c1']}"
                  f" · alpha* {v['alpha_star']:.4f} (bar {v['bar_alpha_star']}) -> {v['c2']}")
        elif v["prediction"] == "P3":
            print(f"        {len(v['violations'])} inverted pairs of {v['n_pairs']}")
            for a, b, tqa, tqb, ca, cb in v["violations"]:
                print(f"          {a} (tau_q {tqa:.5f}, {ca} empty) vs "
                      f"{b} (tau_q {tqb:.5f}, {cb} empty)")
        else:
            print(f"        ackley {v['ackley_rate']:.4f} (bar {v['bar_ackley']}) -> {v['c1']}"
                  f" · rosenbrock {v['rosenbrock_rate']:.4f} "
                  f"(bar {v['bar_rosenbrock']}) -> {v['c2']}")

    print(f"\n  P3 was registered as EXPECTED TO FAIL (Erratum 33) before this ran. "
          f"It {'held anyway' if v3['held'] else 'did fail'}.")

    if args.out:
        Path(args.out).write_text(json.dumps(
            {"source": Path(args.file).name, "bars": BARS,
             "p3_expected_to_fail": P3_EXPECTED_TO_FAIL,
             "stats": stats, "verdicts": [v1, v2, v3, v4]}, indent=1, default=str))
        print(f"\nwrote {Path(args.out).name}")


if __name__ == "__main__":
    main()
