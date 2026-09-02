"""Q56 — `doe_ascent` against BO, the classical arm finally allowed to walk. Prompt 1.

    python scripts/run_q56_doe_ascent.py [n_instances]
    python scripts/run_q56_doe_ascent.py --time-one
    python scripts/run_q56_doe_ascent.py --workers 3

WHAT IS BEING RETIRED
----------------------
Every cost curve in this project carries a concession registered before its numbers
landed: *"biased in favour of BO, because the classical arm has no steepest ascent."*
`doe_repeat` re-runs one 48-well pipeline four times with fresh seeds and never moves its
design region, while qLogEI re-aims after every batch of four. That is not a fair race
past 48 wells, and the concession said so.

:mod:`boec.sequential_rsm` is the textbook arm that removes it. This script races it.
**`doe_repeat` is not dropped** — the contrast *ascent versus repeated CCD* is the entire
point, so all three arms appear in every table.

WHAT IS REGISTERED BEFORE THE RUN, AND WHERE
----------------------------------------------
* **The batching rule.** ``1 + 2k`` rounds for ``k`` cycles, defined once in
  :func:`boec.sequential_rsm.rounds_for_sequential_rsm` and read from there by this
  script. `tests/test_sequential_rsm.py` checks the campaign really plated that many
  batches, so the rounds column is verified against plating events rather than asserted.
* **The step size and path length**, :data:`~boec.sequential_rsm.ASCENT_STEP` = 0.10 and
  :data:`~boec.sequential_rsm.ASCENT_STEPS` = 5. No value of either was tried against a
  result.
* **The censoring rule**, inherited from Q52: above 50% censored, report the rate and no
  point estimate. A savings ratio needs both arms to arrive.
* **The two-seed rule.** Each landscape is run at two campaign seeds. An instance's
  arrival is the mean of its two seeds', and the instance is **censored if either seed
  fails to arrive** — you cannot claim a lab would get there when half your replicate
  campaigns did not. This is the conservative direction for the new arm.

THE ASYMMETRY THAT MUST BE REPORTED, NOT HIDDEN
-------------------------------------------------
The comparators are read from the committed `q52-budget-to-target.json` and were run at
**one** campaign seed per landscape. `doe_ascent` gets two. That makes the new arm's
per-instance number the less noisy of the pair. It is stated in the output and in
`RESULTS.md` rather than being quietly enjoyed, and the first of the two seeds is Q52's
own ``base``, so a like-for-like single-seed contrast is also reported beside it.

NO WINNER IS PRE-WRITTEN
--------------------------
If ascent still loses, that is a result. If it wins, that is a result. Prompt 1 §8.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target   # noqa: E402
from boec.diagnostics import instance_bootstrap                    # noqa: E402
from boec.doe_repeat import PIPELINE_BUDGET                        # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.sequential_rsm import (ASCENT_RULES, ASCENT_STEP, ASCENT_STEPS,  # noqa: E402
                                 CYCLE_BUDGET, SCREEN_BUDGET,
                                 rounds_for_sequential_rsm, run_sequential_rsm)
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

DIM = 6
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
CAP = 200

#: Prompt 1 §7. Rule A at the loose end, where a lab actually operates; rule C on Q52's
#: own ladder so the two studies' tables line up.
TARGETS_RULE_A = (0.15, 0.12, 0.10, 0.08, 0.05)
TARGETS_RULE_C = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05)
CENSOR_LIMIT = 0.50
N_BOOT = 4000

#: Seed 0 is Q52's own campaign seed, so a single-seed contrast is exactly like-for-like.
#: Seed 1 is a registered offset, not a counter, so a landscape's second seed does not
#: depend on how many other jobs ran first.
SEED_SALTS = (0, 9000)

OUT = ROOT / "results" / "q56-doe-ascent.json"
Q52 = ROOT / "results" / "q52-budget-to-target.json"
RULE = "=" * 100


def _seed_of(instance_id: str, salt: int) -> int:
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


def _campaign_seed(instance_id: str, k: int) -> int:
    """Seed ``k`` for a landscape. ``k=0`` reproduces Q52's ``base`` exactly."""
    if k == 0:
        return _seed_of(instance_id, 0) % 10_000
    return _seed_of(instance_id, SEED_SALTS[k])


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def rounds_for(arm: str, n: int) -> int:
    """Q52's cost model, extended by the one registered row this study adds."""
    if arm == "doe":
        return 3 * (n // PIPELINE_BUDGET)
    if arm == "qlogei":
        n_init = 2 * DIM + 2
        return 1 if n <= n_init else 1 + math.ceil((n - n_init) / 4)
    return 1


def _holm(ps: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, monotonised. Q39's form, verbatim."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return adj


def _mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar on discordant pairs. Undefined with none, so returns 1.0."""
    if b + c == 0:
        return 1.0
    from scipy import stats
    return float(min(1.0, 2.0 * stats.binom.cdf(min(b, c), b + c, 0.5)))


def one(job: tuple[int, float, int, str]) -> dict:
    """One landscape x one noise level x one campaign seed x one ascent rule."""
    idx, sigma, k, rule = job
    t0 = time.time()
    inst = load_ensemble(dim=DIM)[idx]
    opt = float(inst.optimum_value)
    seed = _campaign_seed(inst.instance_id, k)

    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    r = run_sequential_rsm(o, _bounds(), truth=o.truth, optimum_value=opt,
                           cap=CAP, seed=seed, ascent_rule=rule)
    return dict(
        instance_index=idx, instance_id=inst.instance_id, sigma=sigma,
        seed_slot=k, seed=seed, ascent_rule=rule, secs=round(time.time() - t0, 1),
        n_cycles=len(r.cycles), evaluations_spent=r.evaluations_spent,
        unspent=r.unspent, converged=r.converged,
        checkpoints=list(r.checkpoints), rounds=r.rounds,
        oracle_best=r.oracle_best, rule_a=r.rule_a,
        rule_c=r.rule_c_unconstrained, rule_c_constrained=r.rule_c_constrained,
        kept_factors=list(r.kept_factors),
        stationary_kinds=[c.stationary_kind for c in r.cycles],
        relocated=[bool(c.relocated) for c in r.cycles],
        n_ascent=[int(c.n_ascent) for c in r.cycles],
        centre_response=[float(c.centre_response) for c in r.cycles])


# ---------------------------------------------------------------------------
# arrival
# ---------------------------------------------------------------------------

def _arrival_two_seed(rows: list[dict], rule: str, target: float):
    """Registered two-seed rule: mean of the seeds, censored if either seed is."""
    arrs = [first_budget_to_target(r[rule], target=target, cap=CAP) for r in rows]
    if not arrs or any(a is ARRIVAL_CENSORED for a in arrs):
        return ARRIVAL_CENSORED
    return float(np.mean([float(a) for a in arrs]))


def _q52_arrival(stored: dict, arm: str, rule: str, target: float):
    curve = stored.get(arm, {}).get(rule)
    if curve is None:
        return None
    return first_budget_to_target(curve, target=target, cap=CAP)


def analyse(rows: list[dict], q52_rows: list[dict], ascent_rule: str) -> dict:
    """Arrival contrasts for one ascent rule. Holm runs within that rule's own family.

    The two rules are two candidate definitions of the same arm, not two arms in one
    experiment, so pooling their tests into a single Holm family would penalise each for
    the other's existence. Each is corrected over its own tests and both are printed.
    """
    q52 = {(r["instance_id"], r["sigma"]): r["arms"] for r in q52_rows}
    by = {}
    for r in rows:
        if r.get("ascent_rule", "path_argmax") != ascent_rule:
            continue
        by.setdefault((r["instance_id"], r["sigma"]), []).append(r)

    cells, tests = [], []
    for sigma in SIGMAS:
        for rule, targets in (("rule_a", TARGETS_RULE_A), ("rule_c", TARGETS_RULE_C)):
            for t in targets:
                keys = sorted(k for k in by if abs(k[1] - sigma) < 1e-12 and k in q52)
                asc, bo, rep, spr = [], [], [], []
                for k in keys:
                    asc.append(_arrival_two_seed(by[k], rule, t))
                    bo.append(_q52_arrival(q52[k], "qlogei", rule, t))
                    rep.append(_q52_arrival(q52[k], "doe", rule, t))
                    spr.append(_q52_arrival(q52[k], "spread_gp", rule, t))

                def hits(a):
                    return sum(1 for x in a if x is not None and x is not ARRIVAL_CENSORED)

                # paired, complete cases only, against qLogEI
                b = sum(1 for x, y in zip(asc, bo)
                        if x is not ARRIVAL_CENSORED and (y is ARRIVAL_CENSORED))
                c = sum(1 for x, y in zip(asc, bo)
                        if x is ARRIVAL_CENSORED and y is not ARRIVAL_CENSORED
                        and y is not None)
                p = _mcnemar_exact(b, c)
                n = len(keys)

                pairs = [float(y) / float(x) for x, y in zip(asc, bo)
                         if x is not ARRIVAL_CENSORED and y is not ARRIVAL_CENSORED
                         and y is not None and float(x) > 0]
                if pairs and len(pairs) / max(n, 1) >= (1 - CENSOR_LIMIT):
                    m, lo, hi = instance_bootstrap(np.array(pairs), n_boot=N_BOOT)
                    savings = dict(mean=float(m), lo=float(lo), hi=float(hi),
                                   n_pairs=len(pairs))
                else:
                    savings = None

                cells.append(dict(
                    sigma=sigma, rule=rule, target=t, n=n,
                    hits_ascent=hits(asc), hits_qlogei=hits(bo),
                    hits_repeat=hits(rep), hits_spread=hits(spr),
                    only_ascent=b, only_qlogei=c, p=p,
                    median_evals_ascent=(float(np.median(
                        [float(x) for x in asc
                         if x is not ARRIVAL_CENSORED])) if hits(asc) else None),
                    savings=savings))
                tests.append(p)

    # Holm over everything, AND within each rule's own family.
    #
    # The all-26 correction is the conservative headline. But Q52 corrected its arrival
    # tests over a family of ten, so comparing a Holm verdict here against Q52's would
    # charge this arm for a multiplicity Q52 never paid — and the difference would read
    # as a property of `doe_ascent` when part of it is the family size. Rule A and rule C
    # are also different estimands, which is the standard reason to correct within
    # families rather than across them. Both are reported; neither is chosen after the
    # fact.
    adj_all = _holm(tests)
    by_family: dict[str, list[int]] = {}
    for i, cell in enumerate(cells):
        by_family.setdefault(cell["rule"], []).append(i)
    adj_fam = [0.0] * len(cells)
    for fam, idxs in by_family.items():
        for j, a in zip(idxs, _holm([tests[j] for j in idxs])):
            adj_fam[j] = a

    for i, cell in enumerate(cells):
        cell["p_holm"] = adj_all[i]
        cell["survives_holm"] = bool(adj_all[i] < 0.05)
        cell["p_holm_within_rule"] = adj_fam[i]
        cell["survives_holm_within_rule"] = bool(adj_fam[i] < 0.05)
    return dict(ascent_rule=ascent_rule, cells=cells, n_tests=len(tests),
                family_sizes={k: len(v) for k, v in by_family.items()})


def report(rows: list[dict], analysis: dict) -> None:
    ar = analysis["ascent_rule"]
    rows = [r for r in rows if r.get("ascent_rule", "path_argmax") == ar]
    primary = " (REGISTERED PRIMARY)" if ar == "path_argmax" else ""
    print(f"\n{RULE}\n  ASCENT RULE: {ar}{primary}\n{RULE}")
    print(f"\n  THE CAMPAIGN ITSELF — what ascent actually did")
    for sigma in SIGMAS:
        sub = [r for r in rows if abs(r["sigma"] - sigma) < 1e-12]
        if not sub:
            continue
        cyc = np.array([r["n_cycles"] for r in sub])
        spent = np.array([r["evaluations_spent"] for r in sub])
        reloc = np.array([sum(r["relocated"]) for r in sub])
        conv = np.mean([r["converged"] for r in sub])
        kinds: dict[str, int] = {}
        for r in sub:
            for kd in r["stationary_kinds"]:
                kinds[kd] = kinds.get(kd, 0) + 1
        print(f"    sigma={sigma}:  cycles {cyc.mean():.1f} (min {cyc.min()}, "
              f"max {cyc.max()})   wells {spent.mean():.0f}/{CAP}   "
              f"relocations {reloc.mean():.1f}   converged early {100*conv:.0f}%")
        print(f"              fitted surface: "
              + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))

    print(f"\n{RULE}\n  ARRIVAL — landscapes reaching the target inside {CAP} wells"
          f"\n{RULE}")
    print(f"    {'sigma':>6}{'rule':>6}{'target':>8}{'ascent':>9}{'qLogEI':>9}"
          f"{'repeat':>9}{'spread':>9}{'only asc':>10}{'only BO':>9}"
          f"{'p':>8}{'Holm26':>8}{'Holm/rule':>9}{'savings':>18}")
    for c in analysis["cells"]:
        sv = ("undef" if c["savings"] is None
              else f"{c['savings']['mean']:.2f} "
                   f"[{c['savings']['lo']:.2f},{c['savings']['hi']:.2f}]")
        star = "*" if c["survives_holm"] else " "
        star2 = "*" if c["survives_holm_within_rule"] else " "
        print(f"    {c['sigma']:>6.2f}{c['rule'][-1].upper():>6}{c['target']:>8.2f}"
              f"{c['hits_ascent']:>6}/{c['n']:<2}{c['hits_qlogei']:>6}/{c['n']:<2}"
              f"{c['hits_repeat']:>6}/{c['n']:<2}{c['hits_spread']:>6}/{c['n']:<2}"
              f"{c['only_ascent']:>10}{c['only_qlogei']:>9}"
              f"{c['p']:>8.4f}{c['p_holm']:>7.4f}{star}"
              f"{c['p_holm_within_rule']:>7.4f}{star2}{sv:>18}")
    print(f"\n    savings = qLogEI wells / doe_ascent wells, paired per landscape, "
          f"complete cases only.")
    print(f"    undefined wherever either arm is censored above {CENSOR_LIMIT:.0%} — the "
          "cap is never substituted for an arrival.")
    fam = analysis["family_sizes"]
    print(f"    Holm26 = corrected over all {analysis['n_tests']} tests. Holm/rule = "
          f"within each rule's own family ({', '.join(f'{k}: {v}' for k, v in sorted(fam.items()))}),")
    print(f"    which is the like-for-like comparison against Q52, whose arrival Holm ran "
          "over a family of ten. * = survives at 0.05.")

    surv = [c for c in analysis["cells"] if c["survives_holm"]]
    print(f"\n{RULE}\n  WHAT THIS LICENSES\n{RULE}")
    if not surv:
        print("    No arrival contrast between doe_ascent and qLogEI survives Holm.")
        print("    The registered concession is therefore retired WITHOUT a replacement")
        print("    claim: on these landscapes, letting the classical design walk does not")
        print("    produce a detectable arrival difference either way.")
    else:
        for c in surv:
            who = "doe_ascent" if c["only_ascent"] > c["only_qlogei"] else "qLogEI"
            print(f"    sigma={c['sigma']} rule {c['rule'][-1].upper()} "
                  f"target {c['target']:.2f}: {who} arrives more often "
                  f"({c['only_ascent']} vs {c['only_qlogei']} discordant, "
                  f"Holm p={c['p_holm']:.4f})")
    print("\n    The sentence 'cost curves are biased in favour of BO because the")
    print("    classical arm has no steepest ascent' now applies to `doe_repeat` ONLY.")


def compare_rules(analyses: list[dict]) -> None:
    """Does the conclusion depend on which reading of Prompt 1's sentence was taken?

    This is the question the two-rule design exists to answer. If both rules reach the
    same verdict everywhere, the choice of primary did not matter and can be reported as
    an aside. If they diverge, the choice is load-bearing and must be stated in the
    result rather than buried in a module docstring.
    """
    print(f"\n{RULE}\n  DOES THE ANSWER DEPEND ON THE ASCENT RULE?\n{RULE}")
    by_cell: dict[tuple, dict] = {}
    for a in analyses:
        for c in a["cells"]:
            by_cell.setdefault((c["sigma"], c["rule"], c["target"]), {})[
                a["ascent_rule"]] = c
    disagree = []
    for key, per in sorted(by_cell.items()):
        verdicts = {ar: c["survives_holm"] for ar, c in per.items()}
        if len(set(verdicts.values())) > 1:
            disagree.append((key, per))
    print(f"    {len(by_cell)} cells compared across {len(analyses)} rules.")
    if not disagree:
        print("    The Holm verdict is IDENTICAL under both readings in every cell.")
        print("    The choice of ascent rule is therefore not load-bearing for the")
        print("    arrival conclusion, and the primary can be reported as registered.")
    else:
        print(f"    {len(disagree)} cells where the verdict FLIPS with the rule:")
        for (sigma, rule, target), per in disagree:
            bits = ", ".join(f"{ar}={'sig' if c['survives_holm'] else 'ns'}"
                             for ar, c in sorted(per.items()))
            print(f"      sigma={sigma} rule {rule[-1].upper()} target {target:.2f}: {bits}")
        print("\n    The choice of ascent rule IS load-bearing. It must be stated in the")
        print("    result, not left to the module docstring.")

    print(f"\n    how often each rule relocated, and how far it got:")
    for a in analyses:
        hits = sum(c["hits_ascent"] for c in a["cells"])
        tot = sum(c["n"] for c in a["cells"])
        print(f"      {a['ascent_rule']:>14}: {hits} arrivals over {tot} "
              f"landscape-targets")


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(git_sha=_git("rev-parse", "HEAD"),
                git_dirty=bool(_git("status", "--porcelain")),
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=list(argv),
                python=platform.python_version(), torch=torch.__version__,
                botorch=botorch.__version__, gpytorch=gpytorch.__version__,
                numpy=np.__version__, scipy=scipy.__version__,
                config=dict(dim=DIM, sigmas=list(SIGMAS), cap=CAP,
                            n_instances=N_INSTANCES, seed_salts=list(SEED_SALTS),
                            screen_budget=SCREEN_BUDGET, cycle_budget=CYCLE_BUDGET,
                            ascent_step=ASCENT_STEP, ascent_steps=ASCENT_STEPS,
                            ascent_rules=list(ASCENT_RULES),
                            ascent_rule_primary="path_argmax",
                            targets_rule_a=list(TARGETS_RULE_A),
                            targets_rule_c=list(TARGETS_RULE_C),
                            censor_limit=CENSOR_LIMIT, n_boot=N_BOOT,
                            comparators_from=Q52.name,
                            rounds_rule="1 + 2k, from sequential_rsm"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_instances", nargs="?", type=int, default=N_INSTANCES)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--time-one", action="store_true")
    args = ap.parse_args()

    print(f"{RULE}\nQ56 — doe_ascent (sequential RSM with steepest ascent)\n{RULE}")
    print(f"  d={DIM}, sigma in {SIGMAS}, {args.n_instances} landscapes x "
          f"{len(SEED_SALTS)} seeds, cap {CAP}")
    print(f"  screen {SCREEN_BUDGET} + cycles of {CYCLE_BUDGET} "
          f"(CCD 27 + ascent <={ASCENT_STEPS} + confirm 1), step {ASCENT_STEP}")
    print(f"  rounds = {rounds_for_sequential_rsm(1)} at one cycle, "
          f"{rounds_for_sequential_rsm(5)} at five — registered, not fitted")
    print(f"  comparators read from {Q52.name}, never re-run\n")

    if args.time_one:
        t = time.time()
        r = one((0, SIGMAS[0], 0, "path_argmax"))
        secs = time.time() - t
        total = secs * args.n_instances * len(SIGMAS) * len(SEED_SALTS)
        print(f"  one campaign: {secs:.1f}s  ({r['n_cycles']} cycles, "
              f"{r['evaluations_spent']} wells, kinds {r['stationary_kinds']})")
        print(f"  full grid ~ {total/60:.0f} min single-core")
        return

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["instance_index"], r["sigma"], r["seed_slot"],
             r.get("ascent_rule", "path_argmax")) for r in done}
    todo = [(i, s, k, ar) for ar in ASCENT_RULES for k in range(len(SEED_SALTS))
            for s in SIGMAS for i in range(args.n_instances)
            if (i, s, k, ar) not in have]
    if have:
        print(f"  resuming — {len(have)} campaigns already on disk")
    print(f"  {len(todo)} campaigns to run on {args.workers} workers\n")

    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(
                    dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 10 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min elapsed, "
                          f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    q52_rows = json.loads(Q52.read_text())["rows"]
    analyses = [analyse(done, q52_rows, ar) for ar in ASCENT_RULES]
    for a in analyses:
        report(done, a)
    compare_rules(analyses)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv),
                                   analyses=analyses, rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.0f} min)")


if __name__ == "__main__":
    main()
