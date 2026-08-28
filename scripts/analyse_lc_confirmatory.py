"""LC adjudicator. Implements docs/SPADE-LC-CONFIRMATORY-SPEC.md verbatim.

WRITTEN BEFORE THE DATA LANDED, while the run was in flight. Gates LC-1..LC-4 are
transcribed from the frozen spec.

Reads `ce_empirical_*` for truth containment, NEVER `ce_contain_*`, the circular internal
statistic that sits at 1.0000 regardless of whether the certificate is right.

Runs on partial checkpoints and PRINTS THE SEED COUNT IT USED (spec §7).
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BAR, CONF, MIN_ANSWER = "0.95", 0.90, 0.95, 0.05
SESOI = 0.02          # pre-registered in SPADE-ROUND-SWEEP-SPEC.md §8
NBOOT = 8000


def cp_lower(k, n):
    return 0.0 if n == 0 or k == 0 else float(beta.ppf(1 - CONF, k, n - k + 1))


def load(paths, alpha):
    """cells[(arm, rounds, family, seed, p, c)] = (nonempty, contained, volume)."""
    ck, ek, vk = f"ce_empirical_{alpha}", f"ce_empty_{alpha}", f"ce_vol_{alpha}"
    cells, regret = {}, {}
    for path in paths:
        raw = json.load(open(path))
        for r in (raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw):
            key = (r["arm"], int(r["rounds"]), r["family"], int(r["seed"]),
                   float(r["p_value"]), float(r["inflation_c"]))
            empty = bool(r.get(ek))
            ec = r.get(ck)
            good = (not empty) and ec is not None and not (
                isinstance(ec, float) and math.isnan(ec)) and bool(ec)
            cells[key] = (not empty, good, 0.0 if empty else float(r.get(vk) or 0.0))
            regret[(r["arm"], int(r["rounds"]), r["family"], int(r["seed"]))] = \
                float(r.get("regret", float("nan")))
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


def pooled(cells, arm, R, fams, c):
    n = k = ne = tot = 0
    for (a, r, f, s, p, cc), (nonempty, good, _v) in cells.items():
        if a != arm or r != R or f not in fams or cc != c:
            continue
        tot += 1
        ne += nonempty
        if nonempty:
            n += 1
            k += good
    return cp_lower(k, n), n, (k / n if n else None), (ne / tot if tot else 0.0)


def select_c(cells, arm, R, fams, grid):
    for c in grid:
        lb, n, ct, ar = pooled(cells, arm, R, fams, c)
        if lb >= BAR and ar >= MIN_ANSWER:
            return c
    return None


def lofo(cells, arm, R, fams, grid):
    """Leave-one-family-out: calibrate c on the others, evaluate on the held-out one."""
    vols, folds, good, n_ans, tot = {}, [], [0, 0], 0, 0
    for held in fams:
        c = select_c(cells, arm, R, [f for f in fams if f != held], grid)
        folds.append((held, c))
        base = grid[0]
        for (a, r, f, s, p, cc), (nonempty, ok_, v) in cells.items():
            if a != arm or r != R or f != held:
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
    return {"folds": folds, "vols": vols, "lb": cp_lower(good[0], good[1]),
            "containment": (good[0] / good[1]) if good[1] else None, "n": good[1],
            "answer": (n_ans / tot) if tot else 0.0,
            "e_vol": (sum(vols.values()) / len(vols)) if vols else 0.0}


# ---------------------------------------------------------------------------
# POST-HOC ADDITION, added after the frozen gates were committed and after the
# LOFO degeneracy below was observed. Labelled as post-hoc; it changes no gate
# threshold (BAR, MIN_ANSWER, SESOI and the LOFO procedure are untouched).
#
# WHY: leave-one-FAMILY-out is degenerate here. Only ackley and hartmann6 supply
# certificates at a usable rate, so a fold that holds out a live family destroys
# the calibration signal, and a fold that holds out a saturated family cannot
# answer. LOFO therefore reports ~0 for reasons that have nothing to do with
# whether the certificate is sound.
#
# Leave-one-SEED-out keeps every family in the calibration set and still scores
# out-of-sample. Read it for what it is: out-of-sample with respect to a RUN
# (noise and design realisation). Except for `hill`, every seed of a family
# shares one landscape, so LOSO does NOT demonstrate generalisation to a new
# landscape -- LOFO is that test, and it is the one saturation has broken.
# ---------------------------------------------------------------------------


def sub_pooled(cells, arm, R, c, keep):
    n = k = ne = tot = 0
    for (a, r, f, s, p, cc), (nonempty, good, _v) in cells.items():
        if a != arm or r != R or cc != c or not keep(f, s):
            continue
        tot += 1
        ne += nonempty
        if nonempty:
            n += 1
            k += good
    return cp_lower(k, n), n, (ne / tot if tot else 0.0)


def select_keep(cells, arm, R, grid, keep):
    for c in grid:
        lb, n, ar = sub_pooled(cells, arm, R, c, keep)
        if lb >= BAR and ar >= MIN_ANSWER:
            return c
    return None


def loso(cells, arm, R, grid, seeds):
    """Calibrate c on all seeds but s, score the held-out seed. Abstain if no c."""
    good, ne, tot, used = [0, 0], 0, 0, 0
    for s in seeds:
        c = select_keep(cells, arm, R, grid, lambda f, ss, s=s: ss != s)
        if c is None:
            tot += sum(1 for k in cells
                       if k[0] == arm and k[1] == R and k[3] == s and k[5] == grid[0])
            continue
        used += 1
        for (a, r, f, sd, p, cc), (nonempty, ok_, _v) in cells.items():
            if a != arm or r != R or sd != s or cc != c:
                continue
            tot += 1
            ne += nonempty
            if nonempty:
                good[1] += 1
                good[0] += ok_
    return {"lb": cp_lower(good[0], good[1]), "n": good[1], "folds": used,
            "containment": (good[0] / good[1]) if good[1] else None,
            "answer": (ne / tot if tot else 0.0)}


def verdict_lc1(lo, hi):
    if lo >= -SESOI and hi <= SESOI:
        return "PASS -- parity within the registered SESOI"
    if lo > SESOI:
        return "FAIL -- qLogNEI better beyond SESOI; SPADE-ROUND-SWEEP-SPEC.md §8 RETRACTED"
    if hi < -SESOI:
        return "SPADE better beyond SESOI (stronger than registered)"
    return "INCONCLUSIVE -- CI straddles a SESOI edge; parity UNDEMONSTRATED, not disproven"


def regret_pair(regret, fams, a_arm, a_R, b_arm, b_R):
    """Positive = the FIRST arm has more regret (is worse)."""
    d, keys = [], []
    for (arm, R, f, s) in regret:
        if arm != a_arm or R != a_R or f not in fams:
            continue
        o = regret.get((b_arm, b_R, f, s))
        if o is not None and not math.isnan(o) and not math.isnan(regret[(arm, R, f, s)]):
            d.append(regret[(arm, R, f, s)] - o)
            keys.append((f, s))
    return d, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=str(ROOT / "results" / "lc-*.json"))
    a = ap.parse_args()
    paths = sorted(glob.glob(a.glob))
    cells, regret = load(paths, ALPHA)
    if not cells:
        print("no LC rows yet"); return
    fams = sorted({k[2] for k in cells})
    grid = sorted({k[5] for k in cells})
    rounds = sorted({k[1] for k in cells})
    seeds = sorted({k[3] for k in cells})

    print("=== LC adjudication — docs/SPADE-LC-CONFIRMATORY-SPEC.md ===")
    print(f"files={len(paths)} families={fams}")
    print(f"c grid={grid} rounds={rounds}")
    print(f"SEEDS USED: {len(seeds)} (max {max(seeds)}) — spec §7 requires this be stated")
    per = {f: len({k[3] for k in cells if k[2] == f}) for f in fams}
    print(f"seeds per family: {per}")
    if len(seeds) < 25:
        print("*** PARTIAL DATA — this is a smaller balanced experiment, not the full LC")
    print()

    # ---- which families are live (spec §7) ---------------------------------
    print("=== certificate supply per family (spec §7: which families are live) ===")
    print(f"{'family':<12}{'cells':>8}{'non-empty':>11}{'rate':>9}")
    live, dead = [], []
    for f in fams:
        ne = [nonempty for (arm, r, ff, s, p, c), (nonempty, _g, _v) in cells.items()
              if ff == f]
        rate = sum(ne) / len(ne) if ne else 0.0
        # A family is LIVE only if it supplies certificates at a usable rate. A single
        # non-empty cell in hundreds is saturation, not life.
        (live if rate >= MIN_ANSWER else dead).append(f)
        print(f"{f:<12}{len(ne):>8}{sum(ne):>11}{100*rate:>8.1f}%")
    print(f"\n  live (rate >= {MIN_ANSWER:.0%}): {live}")
    print(f"  saturated (never usefully certify): {dead}\n")

    # ---- LC-1 --------------------------------------------------------------
    print("=== LC-1 (PRIMARY): SPADE R=5 vs qLogNEI R=10 on regret, ONE process ===")
    print(f"positive = SPADE worse. SESOI = +/-{SESOI}")
    for label, sel in [("all families", fams)] + [(f"{f} only", [f]) for f in fams]:
        d, keys = regret_pair(regret, sel, "spade", 5, "qlognei", 10)
        if not d:
            print(f"  {label:<18} no pairs"); continue
        mean, lo, hi, p = boot(d, seed=1)
        tag = verdict_lc1(lo, hi) if label == "all families" else ""
        print(f"  {label:<18} n={len(d):3d} mean={mean:+.4f} "
              f"CI[{lo:+.4f},{hi:+.4f}] p={p:.3f}  {tag}")
    print()

    # ---- LC-2 --------------------------------------------------------------
    print("=== LC-2: certification, LOFO-calibrated c (LB>=0.90 at answer>=0.05) ===")
    print("  POOLED = c chosen on all families (diagnostic).")
    print("  LOFO   = the registered path (spec §2): calibrate on the others,")
    print("           evaluate on the held-out family.\n")
    print(f"{'arm':<9}{'R':>3} | {'pool c*':>8}{'pool LB':>9}{'pool ans':>9} | "
          f"{'folds c':>10}{'LOFO ans':>9}{'LOFO LB':>9}{'E[vol]':>10}  certifies?")
    cert = {}
    for arm in ("spade", "qlognei"):
        for R in rounds:
            c = select_c(cells, arm, R, fams, grid)
            plb, pn, pct, par = pooled(cells, arm, R, fams, c) if c else (0., 0, None, 0.)
            res = lofo(cells, arm, R, fams, grid)
            ok = res["lb"] >= BAR and res["answer"] >= MIN_ANSWER
            cert[(arm, R)] = ok
            nsel = sum(1 for _f, cc in res["folds"] if cc is not None)
            print(f"{arm:<9}{R:>3} | {(f'{c:g}' if c else 'none'):>8}{plb:>9.4f}"
                  f"{100*par:>8.1f}% | {f'{nsel}/{len(fams)}':>10}"
                  f"{100*res['answer']:>8.1f}%{res['lb']:>9.4f}{res['e_vol']:>10.6f}"
                  f"  {'YES' if ok else 'no'}")
    print("\n  'folds c' = how many leave-one-out folds selected any c at all.")

    print("\n  --- POST-HOC: leave-one-SEED-out (see note at top of file) ---")
    print("  LOFO is degenerate under saturation; this keeps every family in the")
    print("  calibration set. Out-of-sample w.r.t. RUN, not w.r.t. landscape.")
    seeds_all = sorted({k[3] for k in cells})
    print(f"\n{'arm':<9}{'R':>3}{'LOSO LB':>10}{'contain':>9}{'answer':>9}"
          f"{'folds':>8}  certifies OOS?")
    for arm in ("spade", "qlognei"):
        for R in rounds:
            r_ = loso(cells, arm, R, grid, seeds_all)
            ok = r_["lb"] >= BAR and r_["answer"] >= MIN_ANSWER
            ct = r_["containment"]
            ctxt = f"{ct:.4f}" if ct is not None else "n/a"
            folds = f"{r_['folds']}/{len(seeds_all)}"
            print(f"{arm:<9}{R:>3}{r_['lb']:>10.4f}{ctxt:>9}"
                  f"{100*r_['answer']:>8.1f}%{folds:>8}"
                  f"  {'YES' if ok else 'no'}")
    print("\n  If LOSO LB equals pooled LB, every fold chose the same c -- selection")
    print("  is STABLE and the pooled number was not an in-sample artefact.")
    exp = cert.get(("spade", 5)) and not cert.get(("qlognei", 5)) \
        and cert.get(("qlognei", 10))
    print(f"\n  registered pattern (SPADE certifies at R=5, qLogNEI only at R=10): "
          f"{'PASS' if exp else 'FAIL'}")
    if cert.get(("qlognei", 5)):
        print("  !! qLogNEI certifies at R=5 -- 'half the differentiation cycles' is dead")
    print()

    # ---- LC-3 --------------------------------------------------------------
    print("=== LC-3 (CO-PRIMARY): hill, the only dose-response shape ===")
    if "hill" not in fams:
        print("  hill absent from this data")
    else:
        h_live = "hill" in live
        print(f"  1. does hill certify at all (either arm)? {'YES' if h_live else 'NO'}")
        if not h_live:
            print("     *** hill SATURATES like levy/rosenbrock. Every certification")
            print("     *** claim in this paper is then a claim about test functions")
            print("     *** that do not resemble a dose-response. Write it that way.")
        for R in rounds:
            for arm in ("spade", "qlognei"):
                res = lofo(cells, arm, R, ["hill"], grid)
                print(f"     hill {arm:<9} R={R}: answer={100*res['answer']:5.1f}% "
                      f"LB={res['lb']:.4f} E[vol]={res['e_vol']:.6f}")
        d, _ = regret_pair(regret, ["hill"], "spade", 5, "qlognei", 10)
        if d:
            mean, lo, hi, p = boot(d, seed=3)
            print(f"  2. hill regret parity: n={len(d)} mean={mean:+.4f} "
                  f"CI[{lo:+.4f},{hi:+.4f}] -> {verdict_lc1(lo, hi)}")
    print()

    # ---- LC-4 --------------------------------------------------------------
    print("=== LC-4: the R=3 spike (NON-BLIND replication of an exploratory finding) ===")
    print("  certified volume, SPADE - qLogNEI at matched R, positive = SPADE better")
    for R in rounds:
        sv = lofo(cells, "spade", R, fams, grid)["vols"]
        qv = lofo(cells, "qlognei", R, fams, grid)["vols"]
        keys = sorted(set(sv) & set(qv))
        if not keys:
            continue
        mean, lo, hi, p = boot([sv[k] - qv[k] for k in keys], seed=10 + R)
        print(f"    R={R} n={len(keys):3d} mean={mean:+.6f} "
              f"CI[{lo:+.6f},{hi:+.6f}] p={p:.4f}")
    print("\n  Ceiling (spec §7): sigma_rel = 0.25 here. At the measured real assay noise")
    print("  of 0.68, NOTHING certifies for any arm. No LC result stands without it.")


if __name__ == "__main__":
    main()
