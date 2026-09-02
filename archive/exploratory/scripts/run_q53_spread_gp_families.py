"""Q53 — spread_gp on Q42's four external families. Registered in `docs/OPEN-QUESTIONS.md`
BEFORE this file existed (commit 73d2361; check the timestamps).

    python scripts/run_q53_spread_gp_families.py --time-one-cell     # do this first
    python scripts/run_q53_spread_gp_families.py --family levy
    python scripts/run_q53_spread_gp_families.py --merge

THE GAP THIS CLOSES
-------------------
`docs/INFORMATION-MATRIX.md` measured `spread_gp` — one-shot LHS, one GP fit, scored at the
posterior-mean argmax — as **statistically indistinguishable from qLogEI on the Hill family**
under both rules at both noise levels, at budget 48, while spending **1 round against 10**. It
also found the arm has run on **nothing but Hill**. Q42 answers exactly this generality question
for `doe` vs `qlogei`; this closes it for `spread_gp`.

THE REGISTERED PREDICTION, fixed before this file existed
---------------------------------------------------------
    PRIMARY: spread_gp LOSES to qLogEI on Hartmann6, both dimensions, both noise levels,
             under both rules. A one-shot space-filling design has nothing to exploit on a
             deceptive surface, and Q42/Q51 put BO ahead there by +0.2460 to +0.4134.
    FALSIFIER: if spread_gp ties or beats qLogEI on Hartmann6, the HILL result becomes the
             suspicious one and both need re-examining.

THE DESIGN LOTTERY, HANDLED IN ADVANCE
--------------------------------------
`spread_gp`'s two independent measurements of the *same* Hill cell differ by 0.0239 — about one
design SD (Q48/D16, seen a second time). So this runs **D=5 independent LHS draws per
(family, cell, seed)**, averages within seed before any test, and reports the design SD beside
every point estimate. `boec.spread_gp.within_design_noise` applies the registered rule that a
contrast smaller than its cell's design SD is not a result.

WHY THE COMPARATOR IS READ AND NOT RE-RUN
-----------------------------------------
qLogEI's numbers come from the committed `results/q42-families.json`, not from a fresh campaign.
Re-running them would cost hours and would answer a question nobody asked — whether Q42
reproduces — while introducing a second chance to get the configuration subtly different. The
fidelity gate below re-runs a *sample* of them precisely so the read-in rows can be trusted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import wilcoxon                                       # noqa: E402

from boec.campaign import Campaign, CampaignConfig                     # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve   # noqa: E402
from boec.metrics import constrained_argmax                            # noqa: E402
from boec.oracles import (                                             # noqa: E402
    Ackley, Embedded, Hartmann6, Levy, Rosenbrock, UnitScaled)
from boec.spread_gp import (                                           # noqa: E402
    N_RESTARTS, RAW_SAMPLES, design_average, spread_gp_once, within_design_noise)
from boec.torch_oracle import TorchEvaluator                           # noqa: E402

# ---- matched to run_q42_families.py, and none of it is tunable --------------------
BUDGET = 48
N_REPS = 25                       # Q42's N_REPS. Single functions, so the unit is SEED.
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
FAMILIES = {"hartmann6": lambda d: (Hartmann6() if d == 6
                                    else Embedded(Hartmann6(), dim=d, seed=0)),
            "ackley": lambda d: Ackley(dim=d),
            "levy": lambda d: Levy(dim=d),
            "rosenbrock": lambda d: Rosenbrock(dim=d)}

#: Registered in Q53 §3. Five independent LHS draws per (family, cell, seed).
N_DRAWS = 5

#: qLogEI's cost at this budget: 14-point opening, then batches of q=4. spread_gp is one plate.
ROUNDS = {"spread_gp": 1, "qlogei": 1 + -(-(BUDGET - 14) // 4)}
RULE = "=" * 100


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _design_seed(family: str, dim: int, sigma: float, seed: int, draw: int) -> int:
    """Deterministic, and distinct for every draw so the five are genuinely independent.

    Derived by hash rather than by arithmetic on the seed, so that draw 0 here is not silently
    the same design some other experiment already drew at the same (dim, n, seed).
    """
    key = f"q53|{family}|{dim}|{sigma}|{seed}|{draw}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16) % (2**31 - 1)


# --------------------------------------------------------------------------- fidelity

def fidelity_gate(n_check: int = 6) -> dict:
    """Re-run Q42's BO arm on stored rows and reproduce them, before trusting anything new.

    Q42's rows are this experiment's comparator. If they do not regenerate, nothing here is
    comparable and the run is void — so this is a gate, not a diagnostic. Compared against the
    COMMITTED file, never against a regeneration (D12).
    """
    src = ROOT / "results" / "q42-families.json"
    if not src.exists():
        raise SystemExit("results/q42-families.json missing — the comparator does not exist")
    stored = json.loads(src.read_text())["rows"]
    worst, checked = 0.0, 0
    print(f"{RULE}\nFIDELITY GATE — regenerating Q42's qLogEI arm on {n_check} stored rows\n{RULE}")
    for row in stored:
        if checked >= n_check:
            break
        if row["seed"] > 2:                     # cheap sample, spread over families
            continue
        fam, dim, sigma, seed = row["family"], row["dim"], float(row["sigma"]), row["seed"]
        inner = FAMILIES[fam](dim)
        oracle = UnitScaled(inner)
        bounds, opt = _bounds(dim), float(oracle.optimum_value)
        ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
        c = Campaign(ev, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed)).run()
        bo_a = opt - float(reported_best_curve(ev.truth(c.train_X), c.train_Y)[-1])
        model = c.fit()

        def gp_mean(Z: torch.Tensor, _m=model) -> torch.Tensor:
            with torch.no_grad():
                return _m.posterior(Z).mean

        x, _, _ = constrained_argmax(gp_mean, bounds, n_restarts=N_RESTARTS,
                                     raw_samples=RAW_SAMPLES, seed=seed)
        bo_c = opt - float(ev.truth(x.reshape(1, -1)))
        da, dc = abs(bo_a - row["bo_a"]), abs(bo_c - row["bo_c"])
        worst = max(worst, da, dc)
        checked += 1
        print(f"  {fam:<11} d={dim} s={sigma:<5} seed={seed}  "
              f"|dA|={da:.3e}  |dC|={dc:.3e}", flush=True)
    print(f"\n  worst |delta| over {checked} rows: {worst:.3e}")
    if worst > 1e-12:
        raise SystemExit(
            f"FIDELITY GATE FAILED: Q42's qLogEI arm does not regenerate (worst {worst:.3e}). "
            "The comparator is not reproducible, so no contrast computed here is meaningful.")
    print("  PASS — Q42's rows are reproducible and may be used as the comparator.\n")
    return dict(rows_checked=checked, worst_delta=worst)


# --------------------------------------------------------------------------- the run

def run_cell(family: str, dim: int, sigma: float) -> list[dict]:
    inner = FAMILIES[family](dim)
    oracle = UnitScaled(inner)
    bounds, opt = _bounds(dim), float(oracle.optimum_value)
    ox = oracle.optimum_x
    centred = ox is not None and bool(np.allclose(np.asarray(ox), 0.5, atol=1e-9))
    rows = []
    for seed in range(N_REPS):
        a_draws, c_draws = [], []
        for draw in range(N_DRAWS):
            ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
            a, c = spread_gp_once(ev, bounds, truth=ev.truth, optimum_value=opt,
                                  n=BUDGET, seed=_design_seed(family, dim, sigma, seed, draw))
            a_draws.append(a)
            c_draws.append(c)
        a_mean, a_sd = design_average(a_draws)
        c_mean, c_sd = design_average(c_draws)
        rows.append(dict(family=family, dim=dim, sigma=sigma, seed=seed,
                         spread_a=a_mean, spread_a_sd=a_sd,
                         spread_c=c_mean, spread_c_sd=c_sd,
                         a_draws=a_draws, c_draws=c_draws,
                         n_draws=N_DRAWS, scale=oracle.scale,
                         optimum_at_design_centre=centred))
    return rows


# --------------------------------------------------------------------------- analysis

def _paired(a: np.ndarray, b: np.ndarray) -> dict:
    """spread_gp minus comparator. Positive = the comparator is better."""
    d = a - b
    m, lo, hi = instance_bootstrap(d, n_boot=4000)
    try:
        p = float(wilcoxon(d).pvalue)
    except ValueError:
        p = float("nan")
    return dict(diff=m, lo=lo, hi=hi, p=p, n=int(d.size),
                verdict=("comparator better" if lo > 0 else
                         ("spread_gp better" if hi < 0 else "null")))


def _holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down, returning adjusted p in the original order (Q39)."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def _d20_corrected_doe_a() -> dict:
    """Per-seed DoE rule A **after** the D20 fix.

    `q42-families.json` still holds the pre-D20 column on disk — the rescore was written to
    `d20-rescore.json` and never back into the shard. Reading `doe_a` straight from Q42 therefore
    reproduces the oracle-best bug, and the tell is Ackley scoring **exactly** 0.0000. It is not a
    rounding difference: Levy moves 0.0040 -> 0.0392, a factor of ten.

    Rule C is untouched by D20 at every site, so `doe_c_unconstrained` is read from Q42 directly.
    """
    p = ROOT / "results" / "d20-rescore.json"
    if not p.exists():
        raise SystemExit("results/d20-rescore.json missing — cannot correct Q42's doe_a column")
    return {(r["family"], r["dim"], round(float(r["sigma"]), 6), r["seed"]): r["doe_a_new"]
            for r in json.loads(p.read_text())["rows"]}


def analyse(rows: list[dict]) -> dict:
    q42 = {(r["family"], r["dim"], round(float(r["sigma"]), 6), r["seed"]): r
           for r in json.loads((ROOT / "results" / "q42-families.json").read_text())["rows"]}
    doe_a_fixed = _d20_corrected_doe_a()
    cells, raw_p = [], []
    for family in sorted(FAMILIES):
        for dim, sigma in CELLS:
            sub = [r for r in rows if r["family"] == family and r["dim"] == dim
                   and abs(r["sigma"] - sigma) < 1e-12]
            if not sub:
                continue
            keys = [(family, dim, round(sigma, 6), r["seed"]) for r in sub]
            if any(k not in q42 for k in keys):
                print(f"  !! {family} d={dim} s={sigma}: seeds missing from Q42, skipped")
                continue
            sa = np.array([r["spread_a"] for r in sub])
            sc = np.array([r["spread_c"] for r in sub])
            qa = np.array([q42[k]["bo_a"] for k in keys])
            qc = np.array([q42[k]["bo_c"] for k in keys])
            if any(k not in doe_a_fixed for k in keys):
                raise SystemExit(f"{family} d={dim} s={sigma}: no D20 rows; refusing to fall "
                                 "back on Q42's superseded doe_a column")
            da = np.array([doe_a_fixed[k] for k in keys])          # D20-corrected
            da_stale = np.array([q42[k]["doe_a"] for k in keys])   # kept only to show the delta
            dcu = np.array([q42[k]["doe_c_unconstrained"] for k in keys])
            sd_a = float(np.nanmean([r["spread_a_sd"] for r in sub]))
            sd_c = float(np.nanmean([r["spread_c_sd"] for r in sub]))
            va, vc = _paired(sa, qa), _paired(sc, qc)
            cells.append(dict(
                family=family, dim=dim, sigma=sigma, n=len(sub),
                spread_a=float(sa.mean()), spread_a_design_sd=sd_a,
                spread_c=float(sc.mean()), spread_c_design_sd=sd_c,
                qlogei_a=float(qa.mean()), qlogei_c=float(qc.mean()),
                doe_a=float(da.mean()), doe_a_superseded=float(da_stale.mean()),
                doe_c_unconstrained=float(dcu.mean()),
                vs_qlogei_rule_a=va, vs_qlogei_rule_c=vc,
                vs_doe_rule_a=_paired(sa, da), vs_doe_rule_c=_paired(sc, dcu),
                a_within_design_noise=within_design_noise(diff=va["diff"], design_sd=sd_a),
                c_within_design_noise=within_design_noise(diff=vc["diff"], design_sd=sd_c),
                optimum_at_design_centre=sub[0]["optimum_at_design_centre"]))
            raw_p += [va["p"], vc["p"]]
    adj = _holm(raw_p)
    for i, c in enumerate(cells):
        c["vs_qlogei_rule_a"]["p_holm"] = adj[2 * i]
        c["vs_qlogei_rule_c"]["p_holm"] = adj[2 * i + 1]
    return dict(cells=cells, n_contrasts=len(raw_p))


def report(summary: dict) -> None:
    cells = summary["cells"]
    print(f"\n{RULE}\nQ53 — spread_gp vs qLogEI on the external families "
          f"(positive = qLogEI better) · {N_DRAWS} design draws/seed · n={N_REPS} seeds\n{RULE}")
    hdr = (f"{'family':<11}{'cell':<12}{'spread A':>10}{'(dSD)':>8}{'qlogei A':>10}"
           f"{'diff A':>9}{'pHolm':>9}   {'spread C':>10}{'(dSD)':>8}{'qlogei C':>10}"
           f"{'diff C':>9}{'pHolm':>9}")
    print(hdr)
    for c in cells:
        a, cc = c["vs_qlogei_rule_a"], c["vs_qlogei_rule_c"]
        fa = "~" if c["a_within_design_noise"] else " "
        fc = "~" if c["c_within_design_noise"] else " "
        print(f"{c['family']:<11}d={c['dim']} s={c['sigma']:<6}"
              f"{c['spread_a']:>10.4f}{c['spread_a_design_sd']:>8.4f}{c['qlogei_a']:>10.4f}"
              f"{a['diff']:>+9.4f}{fa}{a['p_holm']:>8.4f}   "
              f"{c['spread_c']:>10.4f}{c['spread_c_design_sd']:>8.4f}{c['qlogei_c']:>10.4f}"
              f"{cc['diff']:>+9.4f}{fc}{cc['p_holm']:>8.4f}")
    print("\n  ~ = contrast smaller than the cell's design SD; registered as NOT a result (Q53 §3)")
    print(f"  rounds at budget {BUDGET}: spread_gp {ROUNDS['spread_gp']}, "
          f"qlogei {ROUNDS['qlogei']}")

    print(f"\n{RULE}\nTHE REGISTERED PREDICTION — spread_gp loses to qLogEI on Hartmann6, "
          f"every cell, both rules\n{RULE}")
    h = [c for c in cells if c["family"] == "hartmann6"]
    held = 0
    for c in h:
        for rule, k in (("A", "vs_qlogei_rule_a"), ("C", "vs_qlogei_rule_c")):
            v = c[k]
            ok = v["verdict"] == "comparator better" and v["p_holm"] < 0.05
            held += ok
            print(f"  hartmann6 d={c['dim']} s={c['sigma']:<5} rule {rule}: "
                  f"{v['diff']:+.4f} [{v['lo']:+.4f},{v['hi']:+.4f}] "
                  f"p_holm={v['p_holm']:.4f} -> {'LOSES (predicted)' if ok else v['verdict'].upper()}")
    print(f"\n  PREDICTION HELD IN {held} OF {2 * len(h)} HARTMANN6 CONTRASTS")
    if held < 2 * len(h):
        print("  *** NOT fully held. Per the registration, the FALSIFIER now applies: the HILL\n"
              "      result is the one to re-examine, not this one. Do not take either at face value.")

    print(f"\n{RULE}\nspread_gp vs the CLASSICAL arm (positive = doe better)\n"
          f"DoE rule A is D20-CORRECTED; the superseded column is shown so the size of the fix "
          f"is visible\n{RULE}")
    print(f"{'family':<11}{'cell':<12}{'doe A (D20)':>12}{'was':>9}{'diff A':>10}   "
          f"{'doe C uncon':>12}{'diff C':>10}")
    for c in cells:
        print(f"{c['family']:<11}d={c['dim']} s={c['sigma']:<6}{c['doe_a']:>12.4f}"
              f"{c['doe_a_superseded']:>9.4f}{c['vs_doe_rule_a']['diff']:>+10.4f}   "
              f"{c['doe_c_unconstrained']:>12.4f}{c['vs_doe_rule_c']['diff']:>+10.4f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=sorted(FAMILIES))
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--time-one-cell", action="store_true")
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--gate-only", action="store_true",
                    help="run the fidelity gate alone and persist it, so the four family "
                         "shards can then run in parallel without each paying for it again")
    args = ap.parse_args()
    outdir = ROOT / "results"
    outdir.mkdir(exist_ok=True)

    if args.gate_only:
        g = fidelity_gate(8)
        (outdir / "q53-fidelity-gate.json").write_text(json.dumps(g, indent=1))
        print(f"  written to results/q53-fidelity-gate.json")
        return

    if args.time_one_cell:
        t0 = time.time()
        rows = run_cell("levy", 6, 0.25)
        dt = time.time() - t0
        total = dt * len(FAMILIES) * len(CELLS)
        print(f"\n  one cell (levy d=6 s=0.25): {dt:.0f}s for {len(rows)} seeds "
              f"x {N_DRAWS} draws = {len(rows) * N_DRAWS} fits")
        print(f"  per fit: {dt / (len(rows) * N_DRAWS):.2f}s")
        print(f"  PROJECTED FULL GRID (16 cells): {total / 60:.0f} min "
              f"({total / 3600:.1f} h) sequential")
        return

    if args.merge:
        allrows = []
        for f in sorted(FAMILIES):
            p = outdir / f"q53-spread-gp-{f}.json"
            if not p.exists():
                print(f"  MISSING shard: {p.name}")
                continue
            allrows.extend(json.loads(p.read_text()))
        summary = analyse(allrows)
        report(summary)
        out = outdir / "q53-spread-gp-families.json"
        out.write_text(json.dumps(dict(rows=allrows, summary=summary,
                                       n_draws=N_DRAWS, n_reps=N_REPS,
                                       budget=BUDGET, rounds=ROUNDS), indent=1))
        print(f"\n  written to {out.relative_to(ROOT)}  ({len(allrows)} rows)")
        return

    if not args.family:
        raise SystemExit("give --family, --merge, or --time-one-cell")

    if not args.skip_gate:
        fidelity_gate()

    t0 = time.time()
    out = outdir / f"q53-spread-gp-{args.family}.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    have = {(r["dim"], round(float(r["sigma"]), 6)) for r in rows}
    for dim, sigma in CELLS:
        if (dim, round(float(sigma), 6)) in have:
            print(f"  {args.family} d={dim} s={sigma} already present, skipping", flush=True)
            continue
        rows.extend(run_cell(args.family, dim, sigma))
        out.write_text(json.dumps(rows, indent=1))     # checkpoint per cell, not at the end
        print(f"  {args.family} d={dim} s={sigma} done ({time.time() - t0:.0f}s), "
              f"checkpointed {len(rows)} rows", flush=True)
    print(f"  -> {out.relative_to(ROOT)}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
