"""KT-7 adjudicator. Implements SPADE-ASSURANCE-CALIBRATION-SPEC.md §8.3 verbatim.

WRITTEN BEFORE THE DATA LANDED. The gates 7a/7b/7c/7d are transcribed from the frozen
spec; nothing here may be tuned after seeing results/ktb-inflation-fine.json.

Convention check: `--reproduce` re-derives §7's published alpha=0.95 LOFO numbers
(containment 0.9699, LB 0.9377, c*=1.5) from the OLD complete file. If that does not
reproduce, this analyser's conventions differ from §7's and its verdicts are void.
"""
from __future__ import annotations

import argparse, json, sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]

#: KT-7a is registered at alpha=0.50; KT-7d reports at alpha=0.95.
ALPHA_PRIMARY = "0.5"
#: RCPS risk ceiling: certificate failure rate must be provably <= this.
RISK = 0.10
#: One-sided confidence for both the RCPS selection and the final gate.
CONF = 0.95
#: SPADE's own arm. The certificate being adjudicated is the one SPADE emits.
ARM = "versionb"


def cp_upper(k, n):
    """One-sided upper Clopper-Pearson bound on a rate, k failures of n."""
    if n == 0:
        return 1.0
    if k == n:
        return 1.0
    return float(beta.ppf(CONF, k + 1, n - k))


def cp_lower(k, n):
    """One-sided lower Clopper-Pearson bound on a rate, k successes of n."""
    if n == 0:
        return 0.0
    if k == 0:
        return 0.0
    return float(beta.ppf(1.0 - CONF, k, n - k + 1))


def load(path, alpha, arm):
    """Rows -> (family, c) -> [contained bools], deduped over the redundant gamma loop.

    `tau` comes from tau_quantile(p) and never from gamma, so every ce_* column takes
    exactly one value across the 6 gammas. Keying on (family, seed, arm, c, p_value)
    and keeping the first collapses that 6x redundancy; double-counting it would inflate
    every n by 6 and shrink every confidence interval by ~2.4x.
    """
    raw = json.load(open(path))
    rows = raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw
    # ce_contain is the CIRCULAR internal statistic (identically 1.0000 at every c).
    # ce_empirical is truth containment. Reading the former is the error this
    # analyser's reproduction gate was written to catch, and did.
    ck, ek = f"ce_empirical_{alpha}", f"ce_empty_{alpha}"
    seen, out, answered = set(), defaultdict(list), defaultdict(int)
    total = defaultdict(int)
    for r in rows:
        if r["arm"] != arm:
            continue
        key = (r["family"], r["seed"], r["arm"], r["inflation_c"], r["p_value"])
        if key in seen:
            continue
        seen.add(key)
        fam, c = r["family"], float(r["inflation_c"])
        total[(fam, c)] += 1
        if r.get(ek):                      # empty certificate = abstention, not a failure
            continue
        answered[(fam, c)] += 1
        out[(fam, c)].append(bool(r[ck]))
    return out, answered, total


def select_c(cal, grid):
    """RCPS: smallest c whose CP UPPER bound on failure rate is <= RISK."""
    for c in grid:
        hits = []
        for fam in cal:
            hits += cal[fam].get(c, [])
        n = len(hits)
        k = n - sum(hits)                  # failures
        if n > 0 and cp_upper(k, n) <= RISK:
            return c, cp_upper(k, n), n
    return None, None, 0


def lofo(by_fc, families, grid):
    """Leave-one-family-out. Calibrate c on the others, evaluate on the held-out one."""
    pooled_hits, per_fold = [], []
    for held in families:
        cal = {f: {c: by_fc.get((f, c), []) for c in grid} for f in families if f != held}
        c_star, bound, n_cal = select_c(cal, grid)
        if c_star is None:
            per_fold.append({"held_out": held, "c_star": None, "n": 0,
                             "containment": None, "note": "no c met the risk ceiling"})
            continue
        hits = by_fc.get((held, c_star), [])
        pooled_hits += hits
        per_fold.append({
            "held_out": held, "c_star": c_star, "n": len(hits),
            "containment": (sum(hits) / len(hits)) if hits else None,
            "cal_bound": bound, "n_cal": n_cal,
        })
    n = len(pooled_hits)
    k = sum(pooled_hits)
    return {
        "per_fold": per_fold, "pooled_n": n,
        "pooled_containment": (k / n) if n else None,
        "pooled_lb": cp_lower(k, n),
    }


def per_family_cstar(by_fc, families, grid):
    """KT-7b: each family calibrated on ITSELF, to see if one constant serves all."""
    out = {}
    for f in families:
        c_star, bound, n = select_c({f: {c: by_fc.get((f, c), []) for c in grid}}, grid)
        out[f] = {"c_star": c_star, "bound": bound, "n": n}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(ROOT / "results" / "ktb-inflation-fine.json"))
    ap.add_argument("--alpha", default=ALPHA_PRIMARY)
    ap.add_argument("--arm", default=ARM)
    ap.add_argument("--reproduce", action="store_true",
                    help="convention check against the OLD file at alpha=0.95")
    a = ap.parse_args()

    if a.reproduce:
        a.path = str(ROOT / "results" / "ktb-inflation.json")
        a.alpha = "0.95"

    by_fc, answered, total = load(a.path, a.alpha, a.arm)
    families = sorted({f for f, _ in by_fc})
    grid = sorted({c for _, c in by_fc})
    print(f"file={Path(a.path).name} alpha={a.alpha} arm={a.arm}")
    print(f"families={families}")
    print(f"c grid={grid}\n")

    if a.reproduce:
        # §7 validated c on ackley+hartmann6 only. Reproduce THAT, not the 4-family run.
        fams2 = [f for f in families if f in ("ackley", "hartmann6")]
        r = lofo(by_fc, fams2, grid)
        print("=== REPRODUCTION of §7 (alpha=0.95, ackley+hartmann6 LOFO) ===")
        for fold in r["per_fold"]:
            print(f"  hold out {fold['held_out']:<11} c*={fold['c_star']} "
                  f"n={fold['n']} containment={fold['containment']}")
        print(f"  pooled containment={r['pooled_containment']}  LB={r['pooled_lb']}")
        print(f"  §7 published:       0.9699                     0.9377")
        return

    r = lofo(by_fc, families, grid)
    print("=== KT-7a  four-family LOFO transfer ===")
    for fold in r["per_fold"]:
        print(f"  hold out {fold['held_out']:<11} c*={fold['c_star']} "
              f"n={fold['n']} containment={fold['containment']}")
    pc, lb = r["pooled_containment"], r["pooled_lb"]
    print(f"  pooled n={r['pooled_n']} containment={pc} LB={lb}")
    print(f"  KT-7a: {'PASS' if lb >= 0.90 else 'FAIL'} (bar LB >= 0.90)\n")

    pf = per_family_cstar(by_fc, families, grid)
    print("=== KT-7b  is one constant enough? ===")
    for f, v in pf.items():
        print(f"  {f:<11} c*={v['c_star']} (n={v['n']})")
    cs = [v["c_star"] for v in pf.values() if v["c_star"] is not None]
    if len(cs) >= 2:
        spread = max(cs) / min(cs)
        print(f"  spread = {max(cs)}/{min(cs)} = {spread:.2f}x")
        print(f"  KT-7b: {'PASS' if spread < 2.0 else 'FAIL'} (bar < 2x)\n")
    else:
        print("  KT-7b: FAIL (fewer than 2 families produced a c*)\n")

    print("=== KT-7c  no free lunch (answer rate at selected c*) ===")
    rates = []
    for fold in r["per_fold"]:
        c = fold["c_star"]
        if c is None:
            continue
        f = fold["held_out"]
        n_ans, n_tot = answered.get((f, c), 0), total.get((f, c), 0)
        if n_tot:
            rates.append((f, c, n_ans / n_tot, n_ans, n_tot))
    for f, c, rate, na, nt in rates:
        print(f"  {f:<11} c*={c} answer rate={rate:.4f} ({na}/{nt})")
    if rates:
        pooled_rate = sum(x[3] for x in rates) / sum(x[4] for x in rates)
        print(f"  pooled answer rate={pooled_rate:.4f}")
        print(f"  KT-7c: {'PASS' if pooled_rate >= 0.10 else 'FAIL'} (bar >= 0.10)\n")
    else:
        print("  KT-7c: FAIL (no c* selected)\n")


if __name__ == "__main__":
    main()
