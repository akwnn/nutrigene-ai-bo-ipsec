"""KX adjudicator. Implements docs/SPADE-CALIBRATED-BENCHMARK-SPEC.md verbatim.

WRITTEN BEFORE THE DATA LANDED (spec frozen 08b9650, runner verified, no rows yet).

Every arm is calibrated ON ITS OWN TERMS by leave-one-family-out: `c` is chosen on the
other families and the held-out family is scored at that `c`. Selection and evaluation
never touch the same family, so no arm -- SPADE included -- can win by overfitting `c`.
"""
from __future__ import annotations

import argparse, json, math
from collections import defaultdict
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
ALPHA = "0.95"
BAR = 0.90
CONF = 0.95
SPADE = "versionb"
#: KX §7: a c* landing here is TRUNCATED, not passed.
GRID_MAX = 8.0
#: KX-2: an arm calibrated to honesty only by certifying nothing has not been calibrated.
MIN_ANSWER = 0.05


def cp_lower(k, n):
    if n == 0 or k == 0:
        return 0.0
    return float(beta.ppf(1.0 - CONF, k, n - k + 1))


def load(path, alpha):
    """-> cells[(arm, family, seed, p, c)] = (nonempty, contained, volume)."""
    raw = json.load(open(path))
    rows = raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw
    ck, ek, vk = f"ce_empirical_{alpha}", f"ce_empty_{alpha}", f"ce_vol_{alpha}"
    cells = {}
    for r in rows:
        key = (r["arm"], r["family"], r["seed"], r["p_value"], float(r["inflation_c"]))
        empty = bool(r.get(ek))
        ec = r.get(ck)
        contained = (not empty) and ec is not None and not (
            isinstance(ec, float) and math.isnan(ec)) and bool(ec)
        vol = float(r.get(vk) or 0.0)
        cells[key] = (not empty, contained, 0.0 if empty else vol)
    return cells


def pooled_lb(cells, arm, fams, c):
    n = k = 0
    for (a, f, s, p, cc), (ne, ct, _v) in cells.items():
        if a == arm and f in fams and cc == c and ne:
            n += 1
            k += ct
    return cp_lower(k, n), n, (k / n if n else None)


def answer_rate(cells, arm, fams, c):
    ne = tot = 0
    for (a, f, s, p, cc), (nonempty, _ct, _v) in cells.items():
        if a == arm and f in fams and cc == c:
            tot += 1
            ne += nonempty
    return (ne / tot if tot else 0.0), tot


def select_c(cells, arm, fams, grid):
    """Smallest c whose pooled containment LB >= BAR at a non-trivial answer rate."""
    for c in grid:
        lb, n, _ = pooled_lb(cells, arm, fams, c)
        ar, _ = answer_rate(cells, arm, fams, c)
        if lb >= BAR and ar >= MIN_ANSWER:
            return c
    return None


def lofo(cells, arm, families, grid):
    """Per-arm LOFO. Returns held-out cells keyed by (family, seed, p) -> volume."""
    vols, folds, contained, answered = {}, [], [0, 0], [0, 0]
    for held in families:
        others = [f for f in families if f != held]
        c = select_c(cells, arm, others, grid)
        folds.append({"held_out": held, "c_star": c})
        if c is None:
            for (a, f, s, p, cc), (_ne, _ct, _v) in cells.items():
                if a == arm and f == held and cc == grid[0]:
                    vols[(f, s, p)] = 0.0        # never calibrated => certifies nothing
            continue
        for (a, f, s, p, cc), (ne, ct, v) in cells.items():
            if a == arm and f == held and cc == c:
                vols[(f, s, p)] = v
                answered[1] += 1
                if ne:
                    answered[0] += 1
                    contained[1] += 1
                    contained[0] += ct
    return {
        "arm": arm, "folds": folds, "vols": vols,
        "held_containment": (contained[0] / contained[1]) if contained[1] else None,
        "held_lb": cp_lower(contained[0], contained[1]),
        "held_n": contained[1],
        "answer_rate": (answered[0] / answered[1]) if answered[1] else 0.0,
        "e_vol": (sum(vols.values()) / len(vols)) if vols else 0.0,
    }


def paired_bootstrap(a_vols, b_vols, n_boot=10000, seed=0):
    import random
    keys = sorted(set(a_vols) & set(b_vols))
    if not keys:
        return None, None, None
    d = [a_vols[k] - b_vols[k] for k in keys]
    obs = sum(d) / len(d)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        means.append(sum(d[rng.randrange(len(d))] for _ in range(len(d))) / len(d))
    means.sort()
    return obs, means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(ROOT / "results" / "kx-calibrated-benchmark.json"))
    ap.add_argument("--alpha", default=ALPHA)
    a = ap.parse_args()

    cells = load(a.path, a.alpha)
    arms = sorted({k[0] for k in cells})
    families = sorted({k[1] for k in cells})
    grid = sorted({k[4] for k in cells})
    print(f"alpha={a.alpha} families={families}")
    print(f"c grid={grid}\n")

    res = {arm: lofo(cells, arm, families, grid) for arm in arms}

    print("=== KX-2  can each arm be calibrated to honesty at all? ===")
    print(f"{'arm':<12}{'c* (pooled)':>13}{'contain':>9}{'LB':>8}{'answer%':>9}{'note':>13}")
    for arm in arms:
        c = select_c(cells, arm, families, grid)
        lb, n, ct = pooled_lb(cells, arm, families, c) if c else (0.0, 0, None)
        ar, _ = answer_rate(cells, arm, families, c) if c else (0.0, 0)
        note = "TRUNCATED" if c == GRID_MAX else ("none" if c is None else "")
        cs = "none" if c is None else f"{c:g}"
        cts = "n/a" if ct is None else f"{ct:.4f}"
        print(f"{arm:<12}{cs:>13}{cts:>9}{lb:>8.4f}{100*ar:>8.1f}%{note:>13}")

    print("\n=== KX-1  held-out expected certified volume at each arm's own c* ===")
    print(f"{'arm':<12}{'E[vol]':>12}{'contain':>9}{'LB':>8}{'answer%':>9}")
    order = sorted(arms, key=lambda x: -res[x]["e_vol"])
    for arm in order:
        r = res[arm]
        ctn = r["held_containment"]
        print(f"{arm:<12}{r['e_vol']:>12.6f}"
              f"{(f'{ctn:.4f}' if ctn is not None else 'n/a'):>9}"
              f"{r['held_lb']:>8.4f}{100*r['answer_rate']:>8.1f}%")

    print("\n=== KX-1 verdict ===")
    comps = [x for x in order if x != SPADE and x != "doe"]
    if SPADE not in res:
        print("  SPADE arm absent -- cannot adjudicate")
        return
    best = max(comps, key=lambda x: res[x]["e_vol"]) if comps else None
    if best is None:
        print("  no comparator -- cannot adjudicate")
        return
    obs, lo, hi = paired_bootstrap(res[SPADE]["vols"], res[best]["vols"])
    print(f"  best comparator (excl. doe, KX-3): {best}  E[vol]={res[best]['e_vol']:.6f}")
    print(f"  SPADE E[vol]={res[SPADE]['e_vol']:.6f}")
    if obs is None:
        print("  no paired cells -- cannot adjudicate")
        return
    print(f"  paired diff = {obs:+.6f}  95% CI [{lo:+.6f}, {hi:+.6f}]")
    beats_all = all(res[SPADE]["e_vol"] > res[x]["e_vol"] for x in comps)
    print(f"  beats every comparator: {beats_all}")
    print(f"  CI excludes zero: {lo > 0}")
    print(f"  KX-1: {'PASS' if (beats_all and lo > 0) else 'FAIL'}")

    print("\n=== KX-3  doe reported separately (screening design, not like-for-like) ===")
    if "doe" in res:
        r = res["doe"]
        ctn = r["held_containment"]
        print(f"  doe c*={select_c(cells,'doe',families,grid)} E[vol]={r['e_vol']:.6f} "
              f"containment={(f'{ctn:.4f}' if ctn is not None else 'n/a')} "
              f"answer={100*r['answer_rate']:.1f}%")


if __name__ == "__main__":
    main()
