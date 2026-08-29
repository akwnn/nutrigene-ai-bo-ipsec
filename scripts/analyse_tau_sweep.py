"""TAU adjudicator. Implements docs/SPADE-TAU-DEGENERACY-SPEC.md verbatim.

WRITTEN WHILE THE RUN WAS IN FLIGHT, before any TAU outcome was inspected.

Reads `ce_empirical_*`, NEVER `ce_contain_*`. Prints the seed count it used.
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from pathlib import Path

from scipy.stats import beta, spearmanr

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BAR, CONF, MIN_ANSWER = "0.95", 0.90, 0.95, 0.05
RHO_BAR = 0.80          # TAU-1 gate
NBOOT = 8000
#: Named explicitly. A bare `results/tau-*.json` also matches
#: `results/tau-quantile-followup.json`, an unrelated Aug-25 experiment with a different
#: schema, which is exactly what a loose glob is for getting wrong.
FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")


def cp_lower(k, n):
    return 0.0 if n == 0 or k == 0 else float(beta.ppf(1 - CONF, k, n - k + 1))


def load(paths):
    ck, ek, vk = f"ce_empirical_{ALPHA}", f"ce_empty_{ALPHA}", f"ce_vol_{ALPHA}"
    cells, diff = {}, {}
    for path in paths:
        raw = json.load(open(path))
        for r in (raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw):
            key = (r["arm"], r["family"], int(r["seed"]), float(r["p_value"]),
                   float(r["inflation_c"]))
            empty = bool(r.get(ek))
            ec = r.get(ck)
            good = (not empty) and ec is not None and not (
                isinstance(ec, float) and math.isnan(ec)) and bool(ec)
            cells[key] = (not empty, good, 0.0 if empty else float(r.get(vk) or 0.0))
            diff[(r["family"], float(r["p_value"]))] = float(r.get("margin_sd", float("nan")))
    return cells, diff


def boot(d, seed=0, n=NBOOT):
    if not d:
        return None
    rng = random.Random(seed)
    m = sorted(sum(d[rng.randrange(len(d))] for _ in range(len(d))) / len(d)
               for _ in range(n))
    le = sum(1 for x in m if x <= 0) / n
    ge = sum(1 for x in m if x >= 0) / n
    return st.mean(d), m[int(.025 * n)], m[int(.975 * n)], min(1.0, 2 * min(le, ge))


def pooled(cells, sel):
    n = k = ne = tot = 0
    for key, (nonempty, good, _v) in cells.items():
        if not sel(key):
            continue
        tot += 1
        ne += nonempty
        if nonempty:
            n += 1
            k += good
    return cp_lower(k, n), n, (ne / tot if tot else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=None,
                    help="override; defaults to the five named TAU family files")
    a = ap.parse_args()
    paths = (sorted(glob.glob(a.glob)) if a.glob else
             [str(ROOT / "results" / f"tau-{f}.json") for f in FAMILIES
              if (ROOT / "results" / f"tau-{f}.json").exists()])
    cells, diff = load(paths)
    if not cells:
        print("no TAU rows yet"); return
    fams = sorted({k[1] for k in cells})
    ps = sorted({k[3] for k in cells}, reverse=True)
    grid = sorted({k[4] for k in cells})
    seeds = sorted({k[2] for k in cells})
    print("=== TAU adjudication — docs/SPADE-TAU-DEGENERACY-SPEC.md ===")
    print(f"families={fams}\np grid (prevalence; LARGER = EASIER)={ps}\nc grid={grid}")
    print(f"SEEDS USED: {len(seeds)} (max {max(seeds)})")
    per = {f: len({k[2] for k in cells if k[1] == f}) for f in fams}
    print(f"seeds per family: {per}")
    if len(seeds) < 32:
        print("*** PARTIAL DATA")
    print()

    # ---- answer rate per (family, p), pooled over arms and c=1.0 ----------
    print("=== answer rate by family and prevalence p (c=1.0) ===")
    print(f"{'family':<12}" + "".join(f"{'p='+format(p,'.2f'):>10}" for p in ps))
    xs, ys = [], []
    for f in fams:
        row = []
        for p in ps:
            lb, n, ar = pooled(cells, lambda k, f=f, p=p: k[1] == f and k[3] == p
                               and k[4] == 1.0)
            row.append(f"{100*ar:>9.1f}%")
            ms = diff.get((f, p), float("nan"))
            if ms == ms:
                xs.append(ms); ys.append(ar)
        print(f"{f:<12}" + "".join(row))

    print(f"\n{'family':<12}" + "".join(f"{'p='+format(p,'.2f'):>10}" for p in ps)
          + "   <- margin/sd")
    for f in fams:
        print(f"{f:<12}" + "".join(f"{diff.get((f,p),float('nan')):>10.3f}" for p in ps))

    # ---- TAU-1 -----------------------------------------------------------
    print("\n=== TAU-1 (PRIMARY): does margin/sd govern certification? ===")
    if len(xs) >= 3:
        rho, pv = spearmanr(xs, ys)
        ok = rho >= RHO_BAR
        print(f"  Spearman rho(margin/sd, answer rate) = {rho:.4f} over {len(xs)} "
              f"(family, p) cells, p={pv:.4f}")
        print(f"  gate: rho >= {RHO_BAR}  ->  {'PASS' if ok else 'FAIL'}")
        if not ok:
            print("  *** FAIL retracts SPADE-LC-CONFIRMATORY-SPEC.md §9.2's root cause.")
    else:
        print("  not enough cells yet")

    # ---- TAU-2 -----------------------------------------------------------
    print("\n=== TAU-2: can hill certify at ANY prevalence? ===")
    print(f"{'family':<12}{'p':>6}{'arm':>10}{'c*':>6}{'answer':>9}{'LB':>9}  certifies?")
    hill_ok = False
    for f in fams:
        for p in ps:
            for arm in ("spade", "qlognei"):
                best = None
                for c in grid:
                    lb, n, ar = pooled(cells, lambda k, f=f, p=p, arm=arm, c=c:
                                       k[0] == arm and k[1] == f and k[3] == p
                                       and k[4] == c)
                    if lb >= BAR and ar >= MIN_ANSWER:
                        best = (c, ar, lb); break
                if best and f == "hill":
                    hill_ok = True
                if best and (f == "hill" or p >= 0.50):
                    print(f"{f:<12}{p:>6.2f}{arm:>10}{best[0]:>6g}"
                          f"{100*best[1]:>8.1f}%{best[2]:>9.4f}  YES")
    print(f"\n  TAU-2 (hill certifies at some p): {'PASS' if hill_ok else 'FAIL'}")
    if not hill_ok:
        print("  -> the limitation is real at every prevalence tested; §8.3 stands.")

    # ---- TAU-3 -----------------------------------------------------------
    print("\n=== TAU-3 (ADVERSARIAL): SPADE's volume win at MATCHED difficulty ===")
    print("  Binned by margin/sd. If the win vanishes, LC §9.1 was a difficulty artefact.")
    bins = [(0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 99.0)]
    print(f"{'margin/sd bin':>16}{'n':>6}{'mean diff':>12}{'95% CI':>26}{'p':>9}")
    for lo_b, hi_b in bins:
        sv, qv = {}, {}
        for (arm, f, s, p, c), (_ne, _g, v) in cells.items():
            if c != 1.0:
                continue
            ms = diff.get((f, p), float("nan"))
            if not (ms == ms and lo_b <= ms < hi_b):
                continue
            (sv if arm == "spade" else qv)[(f, s, p)] = v
        keys = sorted(set(sv) & set(qv))
        if not keys:
            print(f"{f'[{lo_b},{hi_b})':>16}{0:>6}   (no cells)")
            continue
        mean, lo, hi, pv = boot([sv[k] - qv[k] for k in keys], seed=int(lo_b * 10))
        print(f"{f'[{lo_b},{hi_b})':>16}{len(keys):>6}{mean:>+12.6f}"
              f"   [{lo:>+9.6f}, {hi:>+9.6f}]{pv:>9.4f}")
    print("\n  Positive = SPADE better. A win that survives INSIDE difficulty bins is a")
    print("  method effect; one that only exists across bins is a difficulty artefact.")


if __name__ == "__main__":
    main()
