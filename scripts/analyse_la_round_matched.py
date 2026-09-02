"""LA adjudicator. Implements paper/PROTOCOLS.md (LA) verbatim.

WRITTEN BEFORE THE DATA LANDED. Gates LA-1/2/3 are transcribed from the frozen spec.

Reads `ce_empirical_*` for truth containment, NEVER `ce_contain_*`, which is the
circular internal statistic that sits at 1.0000 regardless of whether the certificate is
right. That error was caught by the KT-7 analyser's reproduction gate and must not recur.
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from collections import defaultdict
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
ALPHA = "0.95"
BAR, CONF, MIN_ANSWER = 0.90, 0.95, 0.05
SPADE_ARMS = ("versionb", "spade_cert_rho95")


def cp_lower(k, n):
    return 0.0 if n == 0 or k == 0 else float(beta.ppf(1 - CONF, k, n - k + 1))


def load(paths, alpha):
    ck, ek, vk = f"ce_empirical_{alpha}", f"ce_empty_{alpha}", f"ce_vol_{alpha}"
    cells, regret = {}, {}
    for p in paths:
        raw = json.load(open(p))
        rows = raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw
        for r in rows:
            key = (r["arm"], r["family"], r["seed"], r["p_value"], float(r["inflation_c"]))
            empty = bool(r.get(ek))
            ec = r.get(ck)
            good = (not empty) and ec is not None and not (
                isinstance(ec, float) and math.isnan(ec)) and bool(ec)
            cells[key] = (not empty, good, 0.0 if empty else float(r.get(vk) or 0.0))
            regret[(r["arm"], r["family"], r["seed"])] = float(r.get("regret", float("nan")))
    return cells, regret


def pooled(cells, arm, fams, c):
    n = k = ne = tot = 0
    for (a, f, s, p, cc), (nonempty, good, _v) in cells.items():
        if a != arm or f not in fams or cc != c:
            continue
        tot += 1
        ne += nonempty
        if nonempty:
            n += 1
            k += good
    return cp_lower(k, n), n, (k / n if n else None), (ne / tot if tot else 0.0)


def select_c(cells, arm, fams, grid):
    for c in grid:
        lb, n, ct, ar = pooled(cells, arm, fams, c)
        if lb >= BAR and ar >= MIN_ANSWER:
            return c
    return None


def lofo(cells, arm, fams, grid):
    """Calibrate c on the other families, evaluate on the held-out one."""
    vols, folds, good, n_ans, tot = {}, [], [0, 0], 0, 0
    for held in fams:
        c = select_c(cells, arm, [f for f in fams if f != held], grid)
        folds.append((held, c))
        base = grid[0]
        for (a, f, s, p, cc), (nonempty, ok_, v) in cells.items():
            if a != arm or f != held:
                continue
            if c is None and cc == base:
                vols[(f, s, p)] = 0.0
            elif c is not None and cc == c:
                vols[(f, s, p)] = v
                tot += 1
                if nonempty:
                    n_ans += 1
                    good[1] += 1
                    good[0] += ok_
    return {"folds": folds, "vols": vols,
            "containment": (good[0] / good[1]) if good[1] else None,
            "lb": cp_lower(good[0], good[1]), "n": good[1],
            "answer": (n_ans / tot) if tot else 0.0,
            "e_vol": (sum(vols.values()) / len(vols)) if vols else 0.0}


def paired_boot(a, b, n=8000, seed=0):
    keys = sorted(set(a) & set(b))
    if not keys:
        return None, None, None
    d = [a[k] - b[k] for k in keys]
    rng = random.Random(seed)
    m = sorted(sum(d[rng.randrange(len(d))] for _ in range(len(d))) / len(d)
               for _ in range(n))
    return st.mean(d), m[int(.025 * n)], m[int(.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=str(ROOT / "results" / "la-*.json"))
    ap.add_argument("--alpha", default=ALPHA)
    a = ap.parse_args()
    paths = [p for p in glob.glob(a.glob) if "round-matched" not in p]
    cells, regret = load(paths, a.alpha)
    arms = sorted({k[0] for k in cells})
    fams = sorted({k[1] for k in cells})
    grid = sorted({k[4] for k in cells})
    print(f"files={len(paths)} families={fams}\nc grid={grid}\n")

    print("=== pooled, per arm (all families, no LOFO) ===")
    print(f"{'arm':<18}{'c*':>5}{'answer%':>9}{'contain':>9}{'LB':>8}")
    for arm in arms:
        c = select_c(cells, arm, fams, grid)
        lb, n, ct, ar = pooled(cells, arm, fams, c) if c else (0, 0, None, 0)
        print(f"{arm:<18}{(f'{c:g}' if c else 'none'):>5}{100*ar:>8.1f}%"
              f"{(f'{ct:.4f}' if ct is not None else 'n/a'):>9}{lb:>8.4f}")

    res = {arm: lofo(cells, arm, fams, grid) for arm in arms}
    print("\n=== LA held-out (leave-one-family-out calibration) ===")
    print(f"{'arm':<18}{'E[vol]':>12}{'contain':>9}{'LB':>8}{'answer%':>9}")
    for arm in sorted(arms, key=lambda x: -res[x]["e_vol"]):
        r = res[arm]
        ct = r["containment"]
        cts = f"{ct:.4f}" if ct is not None else "n/a"
        print(f"{arm:<18}{r['e_vol']:>12.6f}{cts:>9}"
              f"{r['lb']:>8.4f}{100*r['answer']:>8.1f}%")

    print("\n=== LA-1  best SPADE arm vs qlognei_r2 at MATCHED 2 rounds ===")
    if "qlognei_r2" not in res:
        print("  qlognei_r2 missing -- cannot adjudicate")
        return
    best_spade = max((x for x in SPADE_ARMS if x in res), key=lambda x: res[x]["e_vol"],
                     default=None)
    if best_spade is None:
        print("  no SPADE arm -- cannot adjudicate")
        return
    obs, lo, hi = paired_boot(res[best_spade]["vols"], res["qlognei_r2"]["vols"])
    print(f"  best SPADE arm: {best_spade}  E[vol]={res[best_spade]['e_vol']:.6f}")
    print(f"  qlognei_r2      E[vol]={res['qlognei_r2']['e_vol']:.6f}")
    if obs is not None:
        print(f"  paired diff = {obs:+.6f}  95% CI [{lo:+.6f}, {hi:+.6f}]")
        print(f"  LA-1: {'PASS' if lo > 0 else 'FAIL'} (bar: CI excludes zero, SPADE higher)")

    print("\n=== LA-2  how much of KX's margin was rounds alone? ===")
    if "qlognei_r10" in res:
        d10, d2 = res["qlognei_r10"]["e_vol"], res["qlognei_r2"]["e_vol"]
        print(f"  qlognei_r10 {d10:.6f} - qlognei_r2 {d2:.6f} = {d10-d2:+.6f}")
        print(f"  CONTROL: r10 must reproduce KX's direction, else no LA verdict is readable")

    print("\n=== LA-3  regret (honest second axis) ===")
    print(f"{'arm':<18}{'median regret':>15}")
    for arm in arms:
        v = [x for (aa, f, s), x in regret.items() if aa == arm and not math.isnan(x)]
        if v:
            print(f"{arm:<18}{st.median(v):>15.4f}")


if __name__ == "__main__":
    main()
