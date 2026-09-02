"""KS adjudication. Implements `docs/SPADE-SELF-CALIBRATION-SPEC.md` §3 and §5 exactly.

KS-1 (PRIMARY) transfer · KS-2 mechanism · KS-3 abstention floor · KS-4 Occam · KS-5 ceiling.

The two-variable rule is §5 verbatim and is NOT a free parameter: a 5x5 quantile grid of
(box volume, kappa_tail); a cell is admissible when the one-sided 95% Clopper-Pearson UPPER
bound on its local failure rate is <= 0.10 AND it holds >= 25 calibration campaigns. Cells
with fewer are INADMISSIBLE -- abstain -- never assumed safe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KS = ROOT / "results" / "ks-self-calibration.json"
P8 = ROOT / "results" / "p8-certificate-families.json"
TQ = ROOT / "results" / "tau-quantile-followup.json"
OUT = ROOT / "results" / "ks-analysis.json"

GAMMA = "0.95"
ALPHA = 0.10
TARGET = 0.90
MIN_CELL = 25
EASY = ("hill", "levy", "rosenbrock")
HARD = ("ackley", "hartmann6")


def cp_upper(k: int, n: int, d: float = 0.05) -> float:
    return 1.0 if n == 0 or k == n else float(beta.ppf(1 - d, k + 1, n - k))


def cp_lower(k: int, n: int, d: float = 0.05) -> float:
    return 0.0 if k == 0 else float(beta.ppf(d, k, n - k + 1))


def load() -> list[dict]:
    ks = {(r["family"], r["instance"], r["seed"], r["arm"]): r
          for r in json.loads(KS.read_text())["rows"]}
    out = []
    for path, fams in ((P8, EASY), (TQ, HARD)):
        for r in json.loads(path.read_text())["rows"]:
            fam = r.get("family") or r.get("instance")
            if fam not in fams or r.get(f"ce_empty_{GAMMA}"):
                continue
            k = ks.get((fam, r["instance"], r["seed"], r["arm"]))
            if k is None or k.get("gate_ok") is False:
                continue
            out.append({"family": fam, "seed": int(r["seed"]), "arm": r["arm"],
                        "vol": float(r[f"ce_vol_{GAMMA}"]),
                        "kappa_tail": float(k["kappa_tail"]),
                        "kappa_mean": float(k["kappa_mean"]),
                        "contained": float(r[f"ce_empirical_{GAMMA}"])})
    return out


def fit_2d(vol: np.ndarray, kap: np.ndarray, c: np.ndarray):
    """Spec §5: admissible set over a 5x5 quantile grid. Returns (v_edges, k_edges, ok)."""
    # ERRATUM (found while adjudicating, fixed to match the FROZEN spec, not to change it).
    # The first version set the outer edges to +/-inf, so a test campaign whose statistic
    # fell OUTSIDE the calibration range was mapped into the nearest extreme bin and
    # inherited its verdict. Spec §5 says a cell holding fewer than MIN_CELL calibration
    # campaigns is "inadmissible (abstain), NEVER ASSUMED SAFE" -- and an out-of-range value
    # sits in a cell holding ZERO. Extrapolating admissibility past the calibration range is
    # exactly the failure this rule exists to prevent, so the edges stay finite and
    # `apply_2d` abstains outside them.
    ve = np.quantile(vol, np.linspace(0, 1, 6))
    ke = np.quantile(kap, np.linspace(0, 1, 6))
    ok = np.zeros((5, 5), dtype=bool)
    for i in range(5):
        for j in range(5):
            m = (vol >= ve[i]) & (vol < ve[i + 1]) & (kap >= ke[j]) & (kap < ke[j + 1])
            n = int(m.sum())
            if n < MIN_CELL:
                continue                      # inadmissible: abstain, never assume safe
            ok[i, j] = cp_upper(int((1 - c[m]).sum()), n) <= ALPHA
    return ve, ke, ok


def apply_2d(ve, ke, ok, vol, kap) -> np.ndarray:
    """Admissible only INSIDE the calibration range. Outside it, abstain (spec §5)."""
    inside = (vol >= ve[0]) & (vol <= ve[-1]) & (kap >= ke[0]) & (kap <= ke[-1])
    i = np.clip(np.searchsorted(ve, vol, side="right") - 1, 0, 4)
    j = np.clip(np.searchsorted(ke, kap, side="right") - 1, 0, 4)
    return ok[i, j] & inside


def apply_1d(cap: float, lo: float, x: np.ndarray) -> np.ndarray:
    """Same rule in one dimension: inside the calibrated range, and under the cap."""
    return (x >= lo) & (x <= cap)


def fit_1d(x: np.ndarray, c: np.ndarray) -> float:
    edges = np.quantile(x, np.linspace(0, 1, 21))
    cap = 0.0
    for i in range(20):
        lo, hi = edges[i], edges[i + 1]
        m = (x >= lo) & (x <= hi) if i == 19 else (x >= lo) & (x < hi)
        if m.sum() < MIN_CELL:
            continue
        if cp_upper(int((1 - c[m]).sum()), int(m.sum())) <= ALPHA:
            cap = float(hi)
        else:
            break
    return cap


def report(name, c, m, n_tot):
    k, n = int(c[m].sum()), int(m.sum())
    lb = cp_lower(k, n)
    print(f"  {name:<32} contain={c[m].mean() if n else float('nan'):.4f}  "
          f"LB={lb:.4f}  answer={n/n_tot:.3f}  n={n:<5} "
          f"{'PASS' if lb >= TARGET else 'FAIL'}")
    return {"containment": float(c[m].mean()) if n else float("nan"), "lower_bound_95": lb,
            "answer_rate": n / n_tot, "n_retained": n,
            "verdict": "PASS" if lb >= TARGET else "FAIL"}


def main() -> None:
    rows = load()
    easy = [r for r in rows if r["family"] in EASY]
    hard = [r for r in rows if r["family"] in HARD]
    print(f"KS analysis · gamma={GAMMA} · easy={len(easy)} hard={len(hard)}\n")

    ve_, ke_, ce_ = (np.array([r["vol"] for r in easy]),
                     np.array([r["kappa_tail"] for r in easy]),
                     np.array([r["contained"] for r in easy]))
    vh, kh, ch = (np.array([r["vol"] for r in hard]),
                  np.array([r["kappa_tail"] for r in hard]),
                  np.array([r["contained"] for r in hard]))

    print("KS-1 (PRIMARY) · calibrate on hill/levy/rosenbrock -> ackley/hartmann6")
    ve, ke, ok = fit_2d(ve_, ke_, ce_)
    kr1 = report("(volume, kappa_tail) 2-D rule", ch, apply_2d(ve, ke, ok, vh, kh), len(hard))
    cap_v = fit_1d(ve_, ce_)
    base = report("box volume alone [comparator]", ch, apply_1d(cap_v, ve_.min(), vh), len(hard))
    cap_k = fit_1d(ke_, ce_)
    konly = report("kappa_tail alone", ch, apply_1d(cap_k, ke_.min(), kh), len(hard))

    print("\nKS-2 · mechanism: does the model know it is bad?")
    med_e, med_h = float(np.median(ke_)), float(np.median(kh))
    ratio = med_h / med_e if med_e else float("nan")
    kr2 = {"median_easy": med_e, "median_hard": med_h, "ratio": ratio,
           "verdict": "PASS" if ratio >= 1.20 else "FAIL"}
    print(f"  median kappa_tail  easy={med_e:.4f}  hard={med_h:.4f}  "
          f"ratio={ratio:.3f}  (bar >= 1.20) -> {kr2['verdict']}")

    kr3 = {"answer_rate": kr1["answer_rate"],
           "verdict": "PASS" if kr1["answer_rate"] >= 0.30 else "FAIL"}
    print(f"\nKS-3 · abstention floor: answer rate {kr3['answer_rate']:.3f} "
          f"(bar >= 0.30) -> {kr3['verdict']}")

    sep = {}
    for nm, x in (("kappa_tail", kh), ("box vol", vh)):
        sep[nm] = float(abs(x[ch == 1].mean() - x[ch == 0].mean()) / (x.std() + 1e-12))
    gain = sep["kappa_tail"] - sep["box vol"]
    kr4 = {"separation": sep, "gain_SD": gain,
           "verdict": "DROP kappa_tail" if (kr1["verdict"] == base["verdict"]
                                            and gain < 0.25) else "kappa_tail EARNS ITS PLACE"}
    print(f"\nKS-4 · Occam: separation kappa_tail={sep['kappa_tail']:.2f} SD vs "
          f"box vol={sep['box vol']:.2f} SD (gain {gain:+.2f}) -> {kr4['verdict']}")

    if kr1["verdict"] == "FAIL":
        print("\nKS-5 FIRES · no run-time-observable statistic tested by this project "
              "detects localization\n  failure. SPADE's certificate is valid only where the "
              "surrogate fits, and that scope must\n  be DECLARED IN ADVANCE -- it cannot "
              "currently be detected at run time. This is the second\n  independent "
              "confirmation, after the 0/50 scope detector (RESULTS-AND-ANALYSIS §3).")

    payload = {"spec": "docs/SPADE-SELF-CALIBRATION-SPEC.md", "gamma": GAMMA,
               "n_easy": len(easy), "n_hard": len(hard),
               "KS_1": kr1, "KS_1_comparators": {"box_volume": base, "kappa_only": konly},
               "KS_2": kr2, "KS_3": kr3, "KS_4": kr4,
               "KS_5_fires": kr1["verdict"] == "FAIL"}
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
