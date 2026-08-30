"""DC adjudicator. Implements docs/SPADE-DOE-CERTIFICATE-SPEC.md verbatim.

WRITTEN WHILE THE RUN WAS IN FLIGHT, before any DC outcome was inspected.

Reads `ce_empirical_*`, NEVER `ce_contain_*`. Reports `answered` AND `contained` beside
every certification verdict, per SPADE-TAU-DEGENERACY-SPEC sec 7.3. States rounds per arm
in every table -- SPADE uses MORE rounds than DoE and no table may hide that.
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BAR, CONF, MIN_ANSWER = "0.95", 0.90, 0.95, 0.05
TARGET_P, NBOOT = 0.30, 8000
FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
ROUNDS = {"doe": 3, "doe_unscreened": 3, "spade": 5, "qlognei": 10}
ARMS = ("doe", "doe_unscreened", "spade", "qlognei")


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


def cert(cells, arm, p, c, fam=None):
    n = k = ne = tot = 0
    for (a, f, s, pp, cc), (nonempty, good, _v) in cells.items():
        if a != arm or pp != p or cc != c or (fam and f != fam):
            continue
        tot += 1; ne += nonempty
        if nonempty:
            n += 1; k += good
    return n, k, (ne / tot if tot else 0.0), tot


def best_c(cells, arm, p, grid, fam=None):
    for c in grid:
        n, k, ar, _t = cert(cells, arm, p, c, fam)
        if cp_lower(k, n) >= BAR and ar >= MIN_ANSWER:
            return c, n, k, ar
    return None, None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=None)
    a = ap.parse_args()
    paths = (sorted(glob.glob(a.glob)) if a.glob else
             [str(ROOT / "results" / f"dc-{f}.json") for f in FAMILIES
              if (ROOT / "results" / f"dc-{f}.json").exists()])
    cells, regret = load(paths)
    if not cells:
        print("no DC rows yet"); return
    seeds = sorted({k[2] for k in cells})
    grid = sorted({k[4] for k in cells})
    arms = [x for x in ARMS if any(k[0] == x for k in cells)]
    print("=== DC adjudication — docs/SPADE-DOE-CERTIFICATE-SPEC.md ===")
    print(f"SEEDS USED: {len(seeds)} (max {max(seeds)})   c grid={grid}")
    if len(seeds) < 32:
        print("*** PARTIAL DATA")
    print()

    # ---- DC-1 -------------------------------------------------------------
    print(f"=== DC-1 (PRIMARY): can each arm certify at p={TARGET_P}? ===")
    print("  Rounds are stated because SPADE uses MORE rounds than DoE (spec §6).\n")
    print(f"{'arm':<16}{'rounds':>7}{'c*':>6}{'answered':>11}{'contained':>11}"
          f"{'contain':>9}{'LB':>9}  certifies?")
    verdict = {}
    for arm in arms:
        c, n, k, ar = best_c(cells, arm, TARGET_P, grid)
        if c is None:
            n0, k0, ar0, tot0 = cert(cells, arm, TARGET_P, grid[0])
            ct = f"{k0/n0:.4f}" if n0 else "n/a"
            verdict[arm] = False
            print(f"{arm:<16}{ROUNDS.get(arm,'?'):>7}{'none':>6}{f'{n0}/{tot0}':>11}"
                  f"{k0:>11}{ct:>9}{cp_lower(k0,n0):>9.4f}  no")
        else:
            _n, _k, ar2, tot = cert(cells, arm, TARGET_P, c)
            verdict[arm] = True
            print(f"{arm:<16}{ROUNDS.get(arm,'?'):>7}{c:>6g}{f'{n}/{tot}':>11}"
                  f"{k:>11}{k/n:>9.4f}{cp_lower(k,n):>9.4f}  YES")
    spade_ok, doe_ok = verdict.get("spade"), verdict.get("doe")
    print()
    if spade_ok and not doe_ok:
        print("  DC-1 PASS -- SPADE certifies where DoE cannot. The extra rounds buy a")
        print("  guarantee DoE does not supply, and this is now MEASURED, not asserted.")
    elif doe_ok:
        print("  DC-1 FAIL -- DoE also certifies. The design-space argument against DoE")
        print("  COLLAPSES: SPADE costs more rounds for a deliverable DoE also provides.")
    else:
        print("  DC-1 FAIL -- SPADE does not certify here either. No claim available.")

    # ---- DC-2 -------------------------------------------------------------
    print("\n=== DC-2 (ADVERSARIAL): regret. Does DoE beat SPADE? ===")
    print("  positive = SPADE worse\n")
    for other in [x for x in arms if x != "spade"]:
        keys = sorted({(f, s) for (arm, f, s) in regret if arm == "spade"}
                      & {(f, s) for (arm, f, s) in regret if arm == other})
        if not keys:
            continue
        d = [regret[("spade", f, s)] - regret[(other, f, s)] for f, s in keys]
        mean, lo, hi, p = boot(d, seed=1)
        tag = ("SPADE WORSE" if lo > 0 else
               ("SPADE BETTER" if hi < 0 else "no difference"))
        print(f"  spade(R{ROUNDS['spade']}) vs {other}(R{ROUNDS.get(other,'?')}):"
              f" n={len(d):3d} {mean:+.4f} CI[{lo:+.4f},{hi:+.4f}] p={p:.4f}  {tag}")

    # ---- DC-3 -------------------------------------------------------------
    print("\n=== DC-3: does the 6->4 screen destroy certifiability? ===")
    print(f"{'arm':<16}{'answered':>11}{'contained':>11}{'contain':>9}{'LB':>9}")
    for arm in ("doe", "doe_unscreened"):
        if arm not in arms:
            continue
        n, k, ar, tot = cert(cells, arm, TARGET_P, 1.0)
        ct = f"{k/n:.4f}" if n else "n/a"
        print(f"{arm:<16}{f'{n}/{tot}':>11}{k:>11}{ct:>9}{cp_lower(k,n):>9.4f}")
    print("\n  If unscreened certifies and screened does not, the honest claim is about")
    print("  SCREENING, not about DoE as a method.")

    # ---- context ----------------------------------------------------------
    print("\n=== context: rounds spent per arm ===")
    for arm in arms:
        print(f"  {arm:<16} {ROUNDS.get(arm,'?')} rounds")
    print("\n  sigma_rel = 0.25 throughout. At the measured real assay noise of 0.68")
    print("  nothing certifies for any arm (SPADE-REALISTIC-NOISE-SPEC §6).")


if __name__ == "__main__":
    main()
