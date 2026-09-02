"""EXPLORATORY Part C — Knowledge Gradient. A GENUINE ACQUISITION SWAP.

**NOT REGISTERED. NOT A RESULT.**

**THIS IS THE THING THE FAIRNESS RULES EXIST TO CATCH.** `e2.yaml` registers
qLogEI as the primary acquisition and forbids per-method tuning; qLogEI lost;
this changes the acquisition. Unlike Parts A and B -- which changed only which
quantity gets reported, leaving the search untouched -- there is no reading of
this that is not "trying a different method after the registered one lost". It
is run because the mechanism question is worth answering, and it is labelled as
what it is everywhere it appears.

    OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/exploratory_kg.py

------------------------------------------------------------------------------
WHY KG SPECIFICALLY
------------------------------------------------------------------------------

qLogEI asks how much a point improves on the BEST OBSERVED VALUE. Part A showed
that reference is unreliable at 25% noise: recommending from the posterior mean
instead was worth -0.0320 regret and accounted for 54% of the DoE arm's margin.
Knowledge Gradient asks how much a point improves the MAXIMUM OF THE POSTERIOR
MEAN -- the quantity you would actually recommend from. So it pairs with Part B:
if you recommend from the model, acquire to improve the model's maximum.

------------------------------------------------------------------------------
THE DESIGN, AND WHY IT IS A 2x2 RATHER THAN A SINGLE ARM
------------------------------------------------------------------------------

Scoring KG only under the posterior rule would confound the acquisition change
with the recommendation change, and both are on the table. So every combination
is measured:

                      observed-best rule        posterior-argmax rule
    qLogEI            E2, all four cells        Part A (d=6) + here (d=8)
    qKG               here                      here

**All four cells** -- d in {6, 8} x sigma_rel in {0.25, 0.10}. Running only the
cell where BO lost would be selection on the outcome, which is the same defect
as choosing the comparator after the fact.

COST, measured before committing rather than guessed: qKG at 64 fantasies is
9.04 s per ask against qLogEI's 0.52 s -- 17.4x -- at IDENTICAL solver settings
(num_restarts=10, raw_samples=512). Matching those settings matters: running KG
at reduced restarts to save time would handicap it, and `no_per_method_tuning`
cuts both ways.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import json                                      # noqa: E402
from multiprocessing import Pool                 # noqa: E402
from pathlib import Path                         # noqa: E402

import numpy as np                               # noqa: E402

DIMS = (6, 8)
SIGMAS = (0.25, 0.10)
N_INSTANCES = 25
N_SEEDS = 2
BUDGET = 48
NUM_FANTASIES = 64             # BoTorch's default; not tuned
N_RESTARTS = 10                # IDENTICAL to qLogEI's registered setting
RAW_SAMPLES = 512
REC_RESTARTS = 20              # for the posterior-argmax recommendation only
REC_RAW = 1024


def _row(task) -> dict:
    import torch

    torch.set_num_threads(1)

    from botorch.acquisition.analytic import PosteriorMean
    from botorch.acquisition.knowledge_gradient import qKnowledgeGradient
    from botorch.optim import optimize_acqf

    from boec.campaign import Campaign, CampaignConfig
    from boec.diagnostics import reported_best_curve
    from boec.optimizers import AcqConfig
    from boec.oracles import load_ensemble
    from boec.surrogate import build_gp
    from boec.torch_oracle import BiphasicOracle

    acq, dim, sigma, i_inst, seed = task
    inst = load_ensemble(dim=dim)[i_inst]
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])

    class _KG(Campaign):
        """Only the proposal step differs. Everything else is the shared class."""

        def ask(self, q):
            model = self.fit()
            kg = qKnowledgeGradient(model, num_fantasies=NUM_FANTASIES)
            X, _ = optimize_acqf(kg, bounds=self.bounds, q=q,
                                 num_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES)
            X = X.detach()
            self._round += 1
            self.X_pending = torch.cat([self.X_pending, X])
            return X

    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    cls = _KG if acq == "qkg" else Campaign
    camp = cls(orc, bounds,
               CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed,
                              acq=AcqConfig(kind="qlogei"))).run()
    assert camp.train_X.shape[0] == BUDGET

    opt = float(inst.optimum_value)
    y_obs = float(reported_best_curve(orc.truth(camp.train_X), camp.train_Y)[-1])

    model = build_gp(camp.train_X, camp.train_Y, camp.train_Yvar, bounds)
    failed = False
    try:
        xh, _ = optimize_acqf(PosteriorMean(model), bounds=bounds, q=1,
                              num_restarts=REC_RESTARTS, raw_samples=REC_RAW)
    except Exception:                                        # noqa: BLE001
        failed = True
        xh = camp.train_X[int(camp.train_Y.argmax())].unsqueeze(0)
    y_post = float(orc.truth(xh).detach().double().cpu().numpy().ravel()[0])

    return dict(acq=acq, dim=dim, sigma=sigma, instance=inst.instance_id, seed=seed,
                best=y_obs,
                regret_observed=opt - y_obs,
                regret_posterior=opt - y_post,
                rec_failed=failed)


def by_instance(rows, key, ins=None):
    if ins is None:
        ins = sorted({r["instance"] for r in rows})
    return np.array([np.mean([r[key] for r in rows if r["instance"] == i]) for i in ins])


def report(rows, grid, partA) -> None:
    from scipy.stats import wilcoxon

    from boec.diagnostics import instance_bootstrap

    print("\n" + "=" * 100)
    print("PART C — KNOWLEDGE GRADIENT. A GENUINE ACQUISITION SWAP AFTER THE")
    print("REGISTERED ACQUISITION LOST. NOT REGISTERED. NOT A RESULT.")
    print("=" * 100)
    print("Both scoring rules are reported for both acquisitions, so the acquisition")
    print("effect separates from the recommendation effect. All four cells are run;")
    print("reporting only d=6/sigma=0.25 would be selection on the outcome.\n")

    for dim in DIMS:
        for sigma in SIGMAS:
            kg = [r for r in rows if r["acq"] == "qkg" and r["dim"] == dim
                  and r["sigma"] == sigma]
            ei = [r for r in rows if r["acq"] == "qlogei" and r["dim"] == dim
                  and r["sigma"] == sigma]
            if not kg:
                continue
            # qLogEI/observed comes from the stored E2 grid where available; the
            # posterior rule for qLogEI comes from Part A at d=6 and from this run
            # at d=8.
            e2 = [r for r in grid if r["dim"] == dim and r["sigma"] == sigma
                  and r["arm"] == "qlogei"]
            pa = [r for r in partA if r["sigma"] == sigma] if dim == 6 else ei
            doe = [r for r in grid if r["dim"] == dim and r["sigma"] == sigma
                   and r["arm"] == "doe"]

            ins = sorted({r["instance"] for r in kg} & {r["instance"] for r in e2}
                         & {r["instance"] for r in pa})
            tag = "  <-- E2 PRIMARY CELL" if (dim, sigma) == (6, 0.25) else ""
            print(f"  d={dim}  sigma_rel={sigma}   (n={len(ins)}){tag}")
            print(f"    {'':>16} {'observed-best':>16} {'posterior rule':>16}")
            ke_o = by_instance(e2, "regret", ins)
            ke_p = by_instance(pa, "regret_posterior", ins)
            kk_o = by_instance(kg, "regret_observed", ins)
            kk_p = by_instance(kg, "regret_posterior", ins)
            print(f"    {'qLogEI':>16} {np.median(ke_o):>16.4f} {np.median(ke_p):>16.4f}")
            print(f"    {'qKG':>16} {np.median(kk_o):>16.4f} {np.median(kk_p):>16.4f}")
            if doe:
                print(f"    {'DoE (E2)':>16} "
                      f"{np.median(by_instance(doe, 'regret', ins)):>16.4f} {'—':>16}")

            for lbl, d_ in (("acquisition effect, observed rule", kk_o - ke_o),
                            ("acquisition effect, posterior rule", kk_p - ke_p),
                            ("recommendation effect, under qKG", kk_p - kk_o)):
                m, lo, hi = instance_bootstrap(d_, n_boot=2000)
                print(f"      {lbl:>36}: {m:>+8.4f} [{lo:>+7.4f},{hi:>+7.4f}]  "
                      f"p={wilcoxon(d_).pvalue:.4f}")
            if doe:
                d_ = kk_p - by_instance(doe, "regret", ins)
                m, lo, hi = instance_bootstrap(d_, n_boot=2000)
                print(f"      {'qKG + posterior rule vs DoE':>36}: {m:>+8.4f} "
                      f"[{lo:>+7.4f},{hi:>+7.4f}]  p={wilcoxon(d_).pvalue:.4f}")
            nf = sum(r["rec_failed"] for r in kg)
            if nf:
                print(f"      {nf} recommendation optimisations failed")
            print()

    print("  Multiplicity: 4 cells x 3 registered-style contrasts = 12 tests, plus 4")
    print("  against DoE. Nothing here is corrected for that, because nothing here is")
    print("  a claim. Any single number lifted out of this table needs a registration")
    print("  and a clean re-run on fresh instances before it means anything.")


CHECKPOINT = Path("results/exploratory-kg.jsonl")


def _load_checkpoint() -> dict:
    """Rows already on disk, keyed by task.

    A previous run of this script was stopped at 125/300 and lost every one of
    them, because results were held in memory and written once at the end. Two
    hours of compute for nothing. Each row is now appended as it arrives -- from
    the PARENT process, so there is exactly one writer and no interleaving -- and
    a restart skips whatever is already done.
    """
    done = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            done[(r["acq"], r["dim"], r["sigma"], r["instance"], r["seed"])] = r
    return done


def main() -> None:
    grid = json.loads(Path("results/e2-grid.json").read_text())
    partA = json.loads(Path("results/exploratory-recommendation.json").read_text())

    tasks = [("qkg", d, s, i, sd) for d in DIMS for s in SIGMAS
             for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    # qLogEI under the posterior rule at d=8 -- Part A covered d=6 only, and
    # without it the 2x2 has an empty corner at eight factors
    tasks += [("qlogei", 8, s, i, sd) for s in SIGMAS
              for i in range(N_INSTANCES) for sd in range(N_SEEDS)]
    # resume: instance ids are needed to key the checkpoint, so map task -> id
    from boec.oracles import load_ensemble
    ids = {d: [inst.instance_id for inst in load_ensemble(dim=d)] for d in DIMS}

    def key(t):
        acq, d, sg, i, sd = t
        return (acq, d, sg, ids[d][i], sd)

    done = _load_checkpoint()
    rows = list(done.values())
    todo = [t for t in tasks if key(t) not in done]
    n_all = len(tasks)
    if done:
        print(f"resuming: {len(done)}/{n_all} already on disk, {len(todo)} to run",
              flush=True)
    print(f"{len(todo)} campaigns to run "
          f"({sum(1 for t in todo if t[0] == 'qkg')} qKG at ~17x qLogEI cost)",
          flush=True)

    Path("results").mkdir(exist_ok=True)
    with CHECKPOINT.open("a") as fh, Pool(7) as pool:
        for k, r in enumerate(pool.imap_unordered(_row, todo), 1):
            rows.append(r)
            fh.write(json.dumps(r) + "\n")
            fh.flush()                       # survive a kill, not just a clean exit
            if k % 25 == 0:
                print(f"  {k + len(done)}/{n_all}", flush=True)

    # fidelity on the qLogEI arm only -- qKG has no stored counterpart by design
    ref = {(r["dim"], r["sigma"], r["instance"], r["seed"]): r["best"] for r in grid
           if r["arm"] == "qlogei"}
    bad = [r for r in rows if r["acq"] == "qlogei"
           and abs(r["best"] - ref[(r["dim"], r["sigma"], r["instance"],
                                    r["seed"])]) > 1e-9]
    if bad:
        raise SystemExit(f"FIDELITY: {len(bad)} qLogEI runs do not reproduce E2. Stop.")
    nq = sum(1 for r in rows if r["acq"] == "qlogei")
    print(f"\nFIDELITY: {nq}/{nq} qLogEI control runs reproduce their stored E2 `best`.")

    Path("results/exploratory-kg.json").write_text(json.dumps(rows, indent=1))
    report(rows, grid, partA)


if __name__ == "__main__":
    main()
