"""KR adjudication. Implements `docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md` §3 and §5 exactly.

KR-1 (PRIMARY) transfer · KR-2 cap dispersion · KR-3 abstention floor · KR-4 Occam falsifier.

The calibration rule is §5 verbatim and is NOT a free parameter: 20 quantile strata of the
conditioning variable; the cap is the largest stratum edge at which the one-sided 95%
Clopper-Pearson UPPER bound on stratum-local failure stays <= 0.10, scanning upward and
stopping at the first stratum that fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.resolution import effective_resolution                     # noqa: E402

KR = ROOT / "results" / "kr-effective-resolution.json"
P8 = ROOT / "results" / "p8-certificate-families.json"
TQ = ROOT / "results" / "tau-quantile-followup.json"
OUT = ROOT / "results" / "kr-analysis.json"

GAMMA = "0.95"
ALPHA = 0.10           # registered map-level failure budget
TARGET = 0.90          # registered containment claim
EASY = ("hill", "levy", "rosenbrock")
HARD = ("ackley", "hartmann6")


def cp_upper(k: int, n: int, d: float = 0.05) -> float:
    return 1.0 if n == 0 or k == n else float(beta.ppf(1 - d, k + 1, n - k))


def cp_lower(k: int, n: int, d: float = 0.05) -> float:
    return 0.0 if k == 0 else float(beta.ppf(d, k, n - k + 1))


def calibrate(x: np.ndarray, contained: np.ndarray) -> float:
    """Spec §5: largest stratum edge whose local failure UB stays <= ALPHA."""
    edges = np.quantile(x, np.linspace(0, 1, 21))
    cap = 0.0
    for i in range(20):
        lo, hi = edges[i], edges[i + 1]
        m = (x >= lo) & (x <= hi) if i == 19 else (x >= lo) & (x < hi)
        if m.sum() < 25:
            continue
        if cp_upper(int((1 - contained[m]).sum()), int(m.sum())) <= ALPHA:
            cap = float(hi)
        else:
            break
    return cap


def load() -> list[dict]:
    """Join KR lengthscales onto the committed certificate rows. hill/levy/rosenbrock come
    from P8; ackley/hartmann6 from the tau-quantile grid, per spec §4."""
    kr = {(r["family"], r["instance"], r["seed"], r["arm"]): r
          for r in json.loads(KR.read_text())["rows"]}

    out = []
    for path, fams in ((P8, EASY), (TQ, HARD)):
        for r in json.loads(path.read_text())["rows"]:
            fam = r.get("family") or r.get("instance")
            if fam not in fams or r.get(f"ce_empty_{GAMMA}"):
                continue
            k = kr.get((fam, r["instance"], r["seed"], r["arm"]))
            if k is None or k.get("gate_ok") is False:
                continue
            vol = float(r[f"ce_vol_{GAMMA}"])
            out.append({
                "family": fam, "seed": int(r["seed"]), "arm": r["arm"],
                "vol": vol,
                "k_eff": effective_resolution(vol, k["lengthscales"]),
                "contained": float(r[f"ce_empirical_{GAMMA}"]),
                "n_total": 1,
            })
    return out


def transfer_test(rows: list[dict], key: str) -> dict:
    """Calibrate on EASY, apply unchanged to HARD. KR-1 / KR-4."""
    cal = np.array([r[key] for r in rows if r["family"] in EASY])
    cal_c = np.array([r["contained"] for r in rows if r["family"] in EASY])
    hard = [r for r in rows if r["family"] in HARD]
    x = np.array([r[key] for r in hard]); c = np.array([r["contained"] for r in hard])

    cap = calibrate(cal, cal_c)
    m = x <= cap
    k, n = int(c[m].sum()), int(m.sum())
    return {"conditioning_variable": key, "cap": cap,
            "uncalibrated_containment": float(c.mean()),
            "calibrated_containment": float(c[m].mean()) if n else float("nan"),
            "lower_bound_95": cp_lower(k, n), "n_retained": n, "n_total": len(hard),
            "answer_rate": n / len(hard) if hard else 0.0,
            "verdict": "PASS" if cp_lower(k, n) >= TARGET else "FAIL"}


def main() -> None:
    rows = load()
    print(f"KR analysis · {len(rows)} non-empty certificates at gamma={GAMMA} "
          f"(easy={sum(r['family'] in EASY for r in rows)}, "
          f"hard={sum(r['family'] in HARD for r in rows)})\n")

    kr1 = transfer_test(rows, "k_eff")
    kr4 = transfer_test(rows, "vol")

    print("KR-1 (PRIMARY) · calibrate on hill/levy/rosenbrock -> apply to ackley/hartmann6")
    for lbl, res in (("k_eff", kr1), ("box volume (comparator)", kr4)):
        print(f"  {lbl:<24} cap={res['cap']:.5g}  "
              f"uncal={res['uncalibrated_containment']:.4f} -> "
              f"calib={res['calibrated_containment']:.4f}  "
              f"LB={res['lower_bound_95']:.4f}  answer={res['answer_rate']:.3f}  "
              f"{res['verdict']}")

    # KR-2: per-family cap dispersion, each family calibrated on itself.
    caps = {}
    for fam in EASY + HARD:
        sub = [r for r in rows if r["family"] == fam]
        if len(sub) < 50:
            continue
        caps[fam] = {k: calibrate(np.array([r[k] for r in sub]),
                                  np.array([r["contained"] for r in sub]))
                     for k in ("k_eff", "vol")}
    print("\nKR-2 · per-family caps (each family calibrated on itself)")
    print(f"  {'family':<12}{'k_eff cap':>14}{'box-vol cap':>14}")
    for fam, c in caps.items():
        print(f"  {fam:<12}{c['k_eff']:>14.5g}{c['vol']:>14.5g}")
    def spread(k):
        v = [c[k] for c in caps.values() if c[k] > 0]
        return max(v) / min(v) if len(v) > 1 else float("nan")
    s_keff, s_vol = spread("k_eff"), spread("vol")
    kr2 = {"k_eff_spread": s_keff, "vol_spread": s_vol,
           "verdict": "PASS" if s_keff < 4.0 else "FAIL"}
    print(f"  spread (max/min): k_eff {s_keff:.1f}x   box volume {s_vol:.1f}x   "
          f"-> KR-2 {kr2['verdict']} (bar: k_eff < 4x)")

    kr3 = {"answer_rate": kr1["answer_rate"],
           "verdict": "PASS" if kr1["answer_rate"] >= 0.30 else "FAIL"}
    print(f"\nKR-3 · abstention floor: answer rate {kr3['answer_rate']:.3f} "
          f"(bar >= 0.30) -> {kr3['verdict']}")

    same = kr1["verdict"] == kr4["verdict"]
    kr4v = {"same_verdict_as_box_volume": same,
            "verdict": "DROP k_eff" if same else "k_eff EARNS ITS PLACE"}
    print(f"\nKR-4 · Occam: box volume {kr4['verdict']}, k_eff {kr1['verdict']} "
          f"-> {kr4v['verdict']}")

    payload = {"spec": "docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md", "gamma": GAMMA,
               "n_rows": len(rows), "KR_1": kr1, "KR_2": {**kr2, "caps": caps},
               "KR_3": kr3, "KR_4": {**kr4v, "box_volume_result": kr4}}
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
