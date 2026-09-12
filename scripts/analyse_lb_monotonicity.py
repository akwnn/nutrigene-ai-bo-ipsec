"""LB non-monotonicity diagnostic -- EXPLORATORY, POST-HOC. Not a registered gate.

`SPADE-ROUND-SWEEP-SPEC.md` §7.1 records SPADE's certified-volume win over qLogNEI as
R=3 p=0.0004, R=4 a tie (p=0.503), R=5 marginal (p=0.079), and states the effect "is NOT
monotone in rounds -- that is recorded as measured and is not explained."

This asks the one question a reviewer asks first: **is the non-monotonicity an effect at
all, or is it sampling noise?** §7.1 tests each R against zero SEPARATELY. Four separate
tests against zero cannot establish that R=3 and R=4 DIFFER -- that needs the contrast
itself, paired on the same landscapes, which is what this computes.

HONESTY CONSTRAINTS
  - The data already exists, so no gate can be honestly pre-registered. Everything here is
    descriptive. It can DISSOLVE the §7.1 puzzle (show the R's are indistinguishable); it
    cannot license a new claim.
  - Reads `ce_empirical_*`, NEVER `ce_contain_*` (circular, sits at 1.0000).
  - Reproduction gate runs FIRST: if §7.1's four published numbers do not come back, every
    number below is untrustworthy and the script says so.
"""
from __future__ import annotations

import glob, json, math, random, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALPHA, C_STAR, NBOOT = "0.95", 1.0, 8000
#: §7.1 as published, for the reproduction gate.
PUBLISHED = {2: 0.000300, 3: 0.001000, 4: 0.000203, 5: 0.000381}


def load():
    """-> vols[(rounds, arm, family, seed, p)] = volume (empty certificate counts as 0)."""
    vk, ek = f"ce_vol_{ALPHA}", f"ce_empty_{ALPHA}"
    vols, empty = {}, {}
    for path in glob.glob(str(ROOT / "results" / "lb-*.json")):
        raw = json.load(open(path))
        for r in (raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw):
            if float(r["inflation_c"]) != C_STAR:
                continue
            key = (int(r["rounds"]), r["arm"], r["family"], int(r["seed"]),
                   float(r["p_value"]))
            is_empty = bool(r.get(ek))
            vols[key] = 0.0 if is_empty else float(r.get(vk) or 0.0)
            empty[key] = is_empty
    return vols, empty


def boot(d, seed=0, n=NBOOT):
    """Mean, 95% CI and two-sided bootstrap p for a vector of paired differences."""
    if not d:
        return None
    rng = random.Random(seed)
    m = sorted(sum(d[rng.randrange(len(d))] for _ in range(len(d))) / len(d)
               for _ in range(n))
    le = sum(1 for x in m if x <= 0) / n
    ge = sum(1 for x in m if x >= 0) / n
    return st.mean(d), m[int(.025 * n)], m[int(.975 * n)], min(1.0, 2 * min(le, ge))


def paired_diff(vols, R):
    """SPADE - qLogNEI at round count R, keyed by the (family, seed, p) landscape."""
    out = {}
    for (r, arm, f, s, p), v in vols.items():
        if r != R or arm != "spade":
            continue
        q = vols.get((r, "qlognei", f, s, p))
        if q is not None:
            out[(f, s, p)] = v - q
    return out


def main():
    vols, empty = load()
    rounds = sorted({k[0] for k in vols})
    if not rounds:
        print("no LB rows found under results/lb-*.json; diagnostic not run")
        return
    print(f"c = {C_STAR}, alpha = {ALPHA}, rounds = {rounds}\n")

    diffs = {R: paired_diff(vols, R) for R in rounds}

    # ---- Reproduction gate -------------------------------------------------
    print("=== REPRODUCTION GATE vs SPADE-ROUND-SWEEP-SPEC.md §7.1 ===")
    print(f"{'R':>2}{'n':>5}{'mean':>12}{'published':>12}{'match':>8}")
    ok = True
    for R in rounds:
        d = list(diffs[R].values())
        mean, lo, hi, p = boot(d, seed=R)
        pub = PUBLISHED.get(R)
        hit = pub is not None and abs(mean - pub) < 5e-6
        ok &= hit
        print(f"{R:>2}{len(d):>5}{mean:>+12.6f}{pub:>+12.6f}{'OK' if hit else 'FAIL':>8}")
    if not ok:
        print("\n!! GATE FAILED -- published §7.1 numbers not reproduced. STOP.\n")
        return
    print("Gate passed: §7.1 reproduces exactly.\n")

    print("=== §7.1 as published: each R tested against ZERO, separately ===")
    print(f"{'R':>2}{'mean':>12}{'95% CI':>26}{'p':>9}")
    for R in rounds:
        mean, lo, hi, p = boot(list(diffs[R].values()), seed=R)
        print(f"{R:>2}{mean:>+12.6f}   [{lo:>+9.6f}, {hi:>+9.6f}]{p:>9.4f}")

    # ---- The contrast §7.1 never ran ---------------------------------------
    print("\n=== THE CONTRAST: does the effect actually DIFFER between round counts? ===")
    print("Paired on the same (family, seed, p) landscape at both round counts.")
    print("CI containing zero => the two R's are INDISTINGUISHABLE; the")
    print("'non-monotonicity' is then noise, not a phenomenon needing explanation.\n")
    print(f"{'contrast':>12}{'n':>5}{'mean diff':>12}{'95% CI':>26}{'p':>9}  verdict")
    pairs = [(a, b) for i, a in enumerate(rounds) for b in rounds[i + 1:]]
    for a, b in pairs:
        keys = sorted(set(diffs[a]) & set(diffs[b]))
        d = [diffs[a][k] - diffs[b][k] for k in keys]
        mean, lo, hi, p = boot(d, seed=100 * a + b)
        sep = "DISTINGUISHABLE" if (lo > 0 or hi < 0) else "indistinguishable"
        print(f"{f'R{a} - R{b}':>12}{len(d):>5}{mean:>+12.6f}"
              f"   [{lo:>+9.6f}, {hi:>+9.6f}]{p:>9.4f}  {sep}")

    # ---- Is one family driving R=3? ---------------------------------------
    print("\n=== per-family paired mean diff (is one family driving R=3?) ===")
    fams = sorted({k[0] for k in diffs[rounds[0]]})
    print(f"{'family':<12}" + "".join(f"{'R'+str(R):>13}" for R in rounds))
    for f in fams:
        cells = []
        for R in rounds:
            d = [v for k, v in diffs[R].items() if k[0] == f]
            cells.append(f"{st.mean(d):>+13.6f}" if d else f"{'--':>13}")
        print(f"{f:<12}" + "".join(cells))

    # ---- Sensitivity: drop the families that never certify ------------------
    live = [f for f in fams
            if any(v != 0.0 for R in rounds for k, v in diffs[R].items() if k[0] == f)]
    dead = [f for f in fams if f not in live]
    print(f"\n=== SENSITIVITY: families contributing any signal = {live}")
    print(f"    structural zeros (never certify, either arm) = {dead}")
    print("    If p-values barely move, the zero cells are PAIRED and NEUTRAL --")
    print("    not an inflation of significance, but a limit on GENERALISATION.\n")
    for label, sel in (("all families", fams), ("live only", live)) + \
                      tuple(("%s only" % f, [f]) for f in live):
        print(f"  --- {label} ---")
        for R in rounds:
            d = [v for k, v in diffs[R].items() if k[0] in sel]
            mean, lo, hi, pv = boot(d, seed=R)
            print(f"    R={R} n={len(d):3d} mean={mean:+.6f} "
                  f"CI[{lo:+.6f},{hi:+.6f}] p={pv:.4f}")
        ka = {k: v for k, v in diffs[3].items() if k[0] in sel}
        kb = {k: v for k, v in diffs[4].items() if k[0] in sel}
        keys = sorted(set(ka) & set(kb))
        mean, lo, hi, pv = boot([ka[k] - kb[k] for k in keys], seed=304)
        print(f"    R3-R4  n={len(keys):3d} mean={mean:+.6f} "
              f"CI[{lo:+.6f},{hi:+.6f}] p={pv:.4f}")

    # ---- Mechanism check: empty-certificate rate by round -------------------
    print("\n=== empty-certificate rate by round and arm (a mechanism, if it moves) ===")
    print(f"{'R':>2}{'spade':>10}{'qlognei':>10}")
    for R in rounds:
        cells = []
        for arm in ("spade", "qlognei"):
            e = [v for k, v in empty.items() if k[0] == R and k[1] == arm]
            cells.append(f"{100 * sum(e) / len(e):>9.1f}%" if e else f"{'--':>10}")
        print(f"{R:>2}" + "".join(cells))


if __name__ == "__main__":
    main()
