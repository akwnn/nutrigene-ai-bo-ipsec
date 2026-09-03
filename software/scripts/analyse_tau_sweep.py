"""TAU adjudicator. Implements publication/manuscript/PROTOCOLS.md (TAU) verbatim.

WRITTEN WHILE THE RUN WAS IN FLIGHT, before any TAU outcome was inspected.

Reads `ce_empirical_*`, NEVER `ce_contain_*`. Prints the seed count it used.
"""
from __future__ import annotations

import argparse, glob, json, math, random, statistics as st
from pathlib import Path

from scipy.stats import beta, spearmanr

ROOT = Path(__file__).resolve().parents[2]
ALPHA, BAR, CONF, MIN_ANSWER = "0.95", 0.90, 0.95, 0.05
RHO_BAR = 0.80          # TAU-1 gate
NBOOT = 8000
#: Named explicitly. A bare `research/results/generalization/tau-*.json` also matches
#: `research/results/generalization/tau-quantile-followup.json`, an unrelated Aug-25 experiment with a different
#: schema, which is exactly what a loose glob is for getting wrong.
FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
BINS = ((0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 99.0))


def cp_lower(k, n):
    return 0.0 if n == 0 or k == 0 else float(beta.ppf(1 - CONF, k, n - k + 1))


def load(paths):
    ck, ek, vk = f"ce_empirical_{ALPHA}", f"ce_empty_{ALPHA}", f"ce_vol_{ALPHA}"
    cells, margins = {}, {}
    for path in paths:
        with open(path) as handle:
            raw = json.load(handle)
        for r in (raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw):
            key = (r["arm"], r["family"], int(r["seed"]), float(r["p_value"]),
                   float(r["inflation_c"]))
            empty = bool(r.get(ek))
            ec = r.get(ck)
            good = (not empty) and ec is not None and not (
                isinstance(ec, float) and math.isnan(ec)) and bool(ec)
            incoming = (not empty, good, 0.0 if empty else float(r.get(vk) or 0.0))
            if key in cells:
                raise ValueError(f"duplicate TAU cell key {key}: existing={cells[key]}, "
                                 f"incoming={incoming}")
            cells[key] = incoming
            margin_key = (r["family"], int(r["seed"]), float(r["p_value"]))
            margin = float(r.get("margin_sd", float("nan")))
            if not math.isfinite(margin):
                raise ValueError(f"non-finite margin_sd for {margin_key}: {margin}")
            if margin_key in margins and margins[margin_key] != margin:
                raise ValueError(f"inconsistent margin_sd for {margin_key}: "
                                 f"{margins[margin_key]} != {margin}")
            margins[margin_key] = margin
    return cells, margins


def tau1_points(cells, margins, arm="spade", c=1.0, margin_summary=st.mean,
                expected_seed_count=64):
    """Return registered TAU-1 points as ``(margin, answer rate, family, p)``.

    A margin is a property of one family/seed/prevalence landscape and is repeated in the
    raw rows across arms and inflation values.  ``margins`` therefore contains one unique
    value per seed, while answer rate is restricted to the named arm and inflation.
    """
    fam_ps = sorted({(family, p) for family, _seed, p in margins})
    out = []
    for family, p in fam_ps:
        seed_margins = {seed: margin for (f, seed, prevalence), margin in margins.items()
                        if f == family and prevalence == p}
        answers = {seed: nonempty for (a, f, seed, prevalence, inflation),
                   (nonempty, _good, _volume) in cells.items()
                   if a == arm and f == family and prevalence == p and inflation == c}
        if set(seed_margins) != set(answers):
            raise ValueError(f"seed mismatch for family={family}, p={p}, arm={arm}, c={c}: "
                             f"margin_only={sorted(set(seed_margins) - set(answers))}, "
                             f"answer_only={sorted(set(answers) - set(seed_margins))}")
        if len(seed_margins) != expected_seed_count:
            raise ValueError(f"expected {expected_seed_count} seeds for family={family}, "
                             f"p={p}, arm={arm}, c={c}; got {len(seed_margins)}")
        ordered_seeds = sorted(seed_margins)
        out.append((float(margin_summary([seed_margins[s] for s in ordered_seeds])),
                    st.mean(answers[s] for s in ordered_seeds), family, p))
    return out


def tau3_bin_differences(cells, margins, bins=BINS):
    """Paired SPADE-minus-qLogNEI volumes by seed-specific difficulty bin."""
    result = {}
    for lo_b, hi_b in bins:
        spade, qlognei = {}, {}
        for (arm, family, seed, p, c), (_nonempty, _good, volume) in cells.items():
            if c != 1.0:
                continue
            margin = margins[(family, seed, p)]
            if not lo_b <= margin < hi_b:
                continue
            (spade if arm == "spade" else qlognei)[(family, seed, p)] = volume
        keys = sorted(set(spade) & set(qlognei))
        result[(lo_b, hi_b)] = [spade[key] - qlognei[key] for key in keys]
    return result


def validate_canonical(cells, margins):
    expected_families = set(FAMILIES)
    expected_seeds = set(range(64))
    expected_arms = {"spade", "qlognei"}
    expected_ps = {0.70, 0.50, 0.30, 0.20, 0.10}
    expected_cs = {1.0, 1.5, 2.0, 3.0}
    expected_cells = {(a, f, s, p, c) for f in expected_families
                      for s in expected_seeds for a in expected_arms
                      for p in expected_ps for c in expected_cs}
    if set(cells) != expected_cells:
        missing, extra = expected_cells - set(cells), set(cells) - expected_cells
        raise ValueError(f"incomplete canonical TAU grid: missing={len(missing)}, extra={len(extra)}")
    expected_margins = {(f, s, p) for f in expected_families for s in expected_seeds
                        for p in expected_ps}
    if set(margins) != expected_margins:
        missing, extra = expected_margins - set(margins), set(margins) - expected_margins
        raise ValueError(f"incomplete canonical margin grid: missing={len(missing)}, extra={len(extra)}")


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
             [str(ROOT / "research" / "results" / "generalization" / f"tau-{f}.json") for f in FAMILIES
              if (ROOT / "research" / "results" / "generalization" / f"tau-{f}.json").exists()])
    cells, margins = load(paths)
    if not cells:
        print("no TAU rows yet"); return
    if a.glob:
        print("*** DIAGNOSTIC OVERRIDE: canonical completeness validation skipped for --glob")
    else:
        validate_canonical(cells, margins)
    fams = sorted({k[1] for k in cells})
    ps = sorted({k[3] for k in cells}, reverse=True)
    grid = sorted({k[4] for k in cells})
    seeds = sorted({k[2] for k in cells})
    print("=== TAU adjudication — publication/manuscript/PROTOCOLS.md (TAU) ===")
    print(f"families={fams}\np grid (prevalence; LARGER = EASIER)={ps}\nc grid={grid}")
    print(f"SEEDS USED: {len(seeds)} (max {max(seeds)})")
    per = {f: len({k[2] for k in cells if k[1] == f}) for f in fams}
    print(f"seeds per family: {per}")
    if len(seeds) < 32:
        print("*** PARTIAL DATA")
    print()

    # ---- answer rate per (family, p), SPADE-only at c=1.0 -----------------
    print("=== SPADE answer rate by family and prevalence p (c=1.0) ===")
    print(f"{'family':<12}" + "".join(f"{'p='+format(p,'.2f'):>10}" for p in ps))
    xs, ys = [], []
    for f in fams:
        row = []
        for p in ps:
            lb, n, ar = pooled(cells, lambda k, f=f, p=p: k[0] == "spade" and
                               k[1] == f and k[3] == p and k[4] == 1.0)
            row.append(f"{100*ar:>9.1f}%")
        print(f"{f:<12}" + "".join(row))

    primary = tau1_points(cells, margins)
    xs, ys = [x for x, _y, _f, _p in primary], [y for _x, y, _f, _p in primary]
    primary_margin = {(f, p): x for x, _y, f, p in primary}
    print(f"\n{'family':<12}" + "".join(f"{'p='+format(p,'.2f'):>10}" for p in ps)
          + "   <- mean seed-specific margin/sd")
    for f in fams:
        print(f"{f:<12}" + "".join(f"{primary_margin.get((f,p),float('nan')):>10.3f}" for p in ps))

    # ---- TAU-1 -----------------------------------------------------------
    print("\n=== TAU-1 (PRIMARY): does margin/sd govern certification? ===")
    if len(xs) >= 3:
        rho, _pv = spearmanr(xs, ys)
        ok = rho >= RHO_BAR
        print(f"  descriptive Spearman rho(mean seed-specific margin/sd, SPADE answer rate) "
              f"= {rho:.10f} over {len(xs)} nested (family, p) cells")
        print(f"  gate: rho >= {RHO_BAR}  ->  {'PASS' if ok else 'FAIL'}")
        median_points = tau1_points(cells, margins, margin_summary=st.median)
        median_rho, _ = spearmanr([x for x, *_ in median_points],
                                  [y for _x, y, *_ in median_points])
        qlog_points = tau1_points(cells, margins, arm="qlognei")
        qlog_rho, _ = spearmanr([x for x, *_ in qlog_points],
                                [y for _x, y, *_ in qlog_points])
        print(f"  sensitivity: median seed-specific margin rho={median_rho:.10f}")
        print(f"  sensitivity: qLogNEI-only mean-margin rho={qlog_rho:.10f}")
        print("  Descriptive registered-gate result: nested cells are dependent and are not")
        print("  exchangeable population samples; no naive correlation p-value is inferred.")
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
    print(f"{'margin/sd bin':>16}{'n':>6}{'mean diff':>12}{'95% CI':>26}{'p':>9}")
    for (lo_b, hi_b), differences in tau3_bin_differences(cells, margins).items():
        if not differences:
            print(f"{f'[{lo_b},{hi_b})':>16}{0:>6}   (no cells)")
            continue
        mean, lo, hi, pv = boot(differences, seed=int(lo_b * 10))
        print(f"{f'[{lo_b},{hi_b})':>16}{len(differences):>6}{mean:>+12.6f}"
              f"   [{lo:>+9.6f}, {hi:>+9.6f}]{pv:>9.4f}")
    print("\n  Positive = SPADE better. A win that survives INSIDE difficulty bins is a")
    print("  method effect; one that only exists across bins is a difficulty artefact.")


if __name__ == "__main__":
    main()
