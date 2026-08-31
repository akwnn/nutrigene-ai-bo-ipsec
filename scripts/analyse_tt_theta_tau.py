"""TT adjudicator. Implements docs/SPADE-THETA-TAU-SPEC.md verbatim.

WRITTEN WHILE THE RUN WAS IN FLIGHT, before any TT outcome was inspected.
Reads `ce_empirical_*`, NEVER `ce_contain_*`. Prints the seed count it used.
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BAR, CONF, MIN_ANSWER = "0.95", 0.90, 0.95, 0.05
SESOI, TARGET_P, NBOOT = 0.02, 0.30, 8000
FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")


def holm(p_values):
    """Holm step-down adjusted p-values, returned in input order."""
    indexed = sorted(enumerate(float(p) for p in p_values), key=lambda x: x[1])
    adjusted, running = [0.0] * len(indexed), 0.0
    m = len(indexed)
    for rank, (index, p) in enumerate(indexed):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[index] = running
    return adjusted


def cp_lower(k, n):
    return 0.0 if n == 0 or k == 0 else float(beta.ppf(1 - CONF, k, n - k + 1))


def load(paths):
    ck, ek, vk = f"ce_empirical_{ALPHA}", f"ce_empty_{ALPHA}", f"ce_vol_{ALPHA}"
    cells, regret = {}, {}
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
            regret[(r["arm"], r["family"], int(r["seed"]))] = float(r["regret"])
    return cells, regret


def boot(d, seed=0, n=NBOOT):
    if not d:
        return None
    rng = random.Random(seed)
    m = sorted(sum(d[rng.randrange(len(d))] for _ in range(len(d))) / len(d)
               for _ in range(n))
    le = sum(1 for x in m if x <= 0) / n
    ge = sum(1 for x in m if x >= 0) / n
    return st.mean(d), m[int(.025 * n)], m[int(.975 * n)], min(1.0, 2 * min(le, ge))


def vols(cells, arm, p, c=1.0):
    return {(f, s): v for (a, f, s, pp, cc), (_ne, _g, v) in cells.items()
            if a == arm and pp == p and cc == c}


def counts(cells, arm, p, c=1.0, fam=None):
    n = k = tot = 0
    for (a, f, s, pp, cc), (ne, good, _v) in cells.items():
        if a != arm or pp != p or cc != c or (fam and f != fam):
            continue
        tot += 1
        if ne:
            n += 1; k += good
    return n, k, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=None)
    a = ap.parse_args()
    paths = (sorted(glob.glob(a.glob)) if a.glob else
             [str(ROOT / "results" / f"tt-{f}.json") for f in FAMILIES
              if (ROOT / "results" / f"tt-{f}.json").exists()])
    cells, regret = load(paths)
    if not cells:
        print("no TT rows yet"); return
    seeds = sorted({k[2] for k in cells})
    fams = sorted({k[1] for k in cells})
    print("=== TT adjudication — docs/SPADE-THETA-TAU-SPEC.md ===")
    print(f"families={fams}\nSEEDS USED: {len(seeds)} (max {max(seeds)})")
    if len(seeds) < 32:
        print("*** PARTIAL DATA")
    print()

    # ---- TT-1 -------------------------------------------------------------
    print(f"=== TT-1 (PRIMARY): certified volume at p={TARGET_P}, "
          f"spade_tau - spade ===")
    sv, tv = vols(cells, "spade", TARGET_P), vols(cells, "spade_tau", TARGET_P)
    keys = sorted(set(sv) & set(tv))
    if keys:
        mean, lo, hi, p = boot([tv[k] - sv[k] for k in keys], seed=1)
        verdict = ("PASS -- correct targeting BEATS the disabled mechanism; KF-3's "
                   "negative result is confined to the disabled implementation"
                   if lo > 0 else
                   ("targeting is WORSE when correctly aimed" if hi < 0 else
                    "FAIL -- no difference; KF-3's conclusion stands on its merits"))
        print(f"  n={len(keys):3d} mean={mean:+.6f} CI[{lo:+.6f},{hi:+.6f}] p={p:.4f}")
        print(f"  -> {verdict}")
        print("\n  per family (Holm-adjusted across five families):")
        family_stats = []
        for f in fams:
            kk = [k for k in keys if k[0] == f]
            if not kk:
                continue
            m2, l2, h2, p2_ = boot([tv[k] - sv[k] for k in kk], seed=2)
            family_stats.append((f, len(kk), m2, l2, h2, p2_))
        adjusted = dict(zip((row[0] for row in family_stats), holm(row[5] for row in family_stats)))
        for f, n, m2, l2, h2, p2_ in family_stats:
            print(f"    {f:<11} n={n:3d} {m2:+.6f} [{l2:+.6f},{h2:+.6f}] "
                  f"p={p2_:.3f} p_holm={adjusted[f]:.3f} descriptive")

    # ---- TT-2 -------------------------------------------------------------
    print(f"\n=== TT-2 (GUARDRAIL): regret, spade_tau - spade (positive = worse) ===")
    keys = sorted({(f, s) for (arm, f, s) in regret if arm == "spade"}
                  & {(f, s) for (arm, f, s) in regret if arm == "spade_tau"})
    if keys:
        d = [regret[("spade_tau", f, s)] - regret[("spade", f, s)] for f, s in keys]
        mean, lo, hi, p = boot(d, seed=3)
        ok = hi <= SESOI
        print(f"  n={len(keys):3d} mean={mean:+.4f} CI[{lo:+.4f},{hi:+.4f}] p={p:.4f}")
        print(f"  non-inferior within SESOI {SESOI}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            print("  *** buys volume by abandoning the optimum -- NOT an improvement")

    # ---- TT-3 -------------------------------------------------------------
    print("\n=== TT-3 (descriptive): ackley, the largest theta/tau mismatch (13.6x) ===")
    for arm in ("spade", "spade_tau", "qlognei"):
        v = [regret[(arm, "ackley", s)] for s in seeds if (arm, "ackley", s) in regret]
        if v:
            print(f"  {arm:<11} mean regret = {st.mean(v):.4f}  (n={len(v)})")

    # ---- certification summary -------------------------------------------
    print(f"\n=== certification at p={TARGET_P}, c=1.0 (spec §7: answered AND contained) ===")
    print(f"{'arm':<12}{'answered':>10}{'contained':>11}{'contain':>9}{'LB':>9}")
    for arm in ("spade", "spade_tau", "qlognei"):
        n, k, tot = counts(cells, arm, TARGET_P)
        ct = f"{k/n:.4f}" if n else "n/a"
        print(f"{arm:<12}{f'{n}/{tot}':>10}{k:>11}{ct:>9}{cp_lower(k, n):>9.4f}")


if __name__ == "__main__":
    main()
