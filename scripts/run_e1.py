"""E1 — correctness. Does the machinery work at all?

OWNERSHIP: Person A. Reproduce with `python scripts/run_e1.py`.

**E1 is not a result and must not be reported as one.** It is the smoke test that the
optimisation loop, the model, the acquisition function and the evaluator interface are
wired up correctly, checked on functions whose optima come from the literature rather
than from us. Branin, Hartmann6 and Ackley, 20 seeds each, Bayesian optimization against
random search on an identical budget.

**The kill condition: if BO loses to random on Hartmann6, that is a bug and everything
downstream is void.** Hartmann6 is a standard 6-dimensional benchmark that BO is
expected to win comfortably; losing means something in the loop is wrong -- an
orientation flip, a broken noise path, a mis-seeded design -- and no result computed
afterwards can be trusted. It is emphatically NOT an interesting finding about Hartmann6.

Ackley is included knowing BO may *not* beat random on it, and that is fine and stated in
advance: Ackley is a needle-in-a-haystack function whose global structure is nearly flat
noise at d=6, so a Gaussian process has almost nothing to learn. It is here to show the
harness runs on a hostile landscape, not as a pass/fail gate. **Only Hartmann6 is the
gate.** Writing that down before the run so a poor Ackley number cannot later be
explained away.

Fairness, enforced here as in E2: identical budget, identical batch plan, and the
non-adaptive baseline is averaged over many random orderings, because a one-shot design
has no natural running order and a best-so-far curve read off an arbitrary one is
meaningless.
"""

from __future__ import annotations

import numpy as np
import torch

from boec.campaign import Campaign, CampaignConfig
from boec.oracles import Ackley, Branin, Hartmann6
from boec.runner import run_static_baseline
from boec.torch_oracle import TorchEvaluator

N_SEEDS = 20
BUDGET = 48
SIGMA_REL = 0.10
GATE = "hartmann6"


def unit_bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def main() -> None:
    print(f"{'=' * 88}")
    print(f"E1 · CORRECTNESS SMOKE TEST · {N_SEEDS} seeds · budget {BUDGET} "
          f"· sigma_rel {SIGMA_REL}")
    print(f"{'=' * 88}")
    print(f"{'function':>12} {'d':>3} {'known opt':>11} {'BO':>20} {'random':>20} "
          f"{'BO - random':>13}")

    verdicts = {}
    for fn in (Branin(), Hartmann6(), Ackley(dim=6)):
        d = fn.dim
        bounds = unit_bounds(d)
        bo, rnd = [], []
        for seed in range(N_SEEDS):
            c = Campaign(
                TorchEvaluator(fn, sigma_rel=SIGMA_REL, seed=seed),
                bounds, CampaignConfig(d=d, budget=BUDGET, q=4, seed=seed),
            )
            c.run()
            bo.append(float(c.best_so_far()[-1]))
            rnd.append(float(run_static_baseline(
                TorchEvaluator(fn, sigma_rel=SIGMA_REL, seed=seed),
                bounds, "random", BUDGET, seed)[-1]))

        bo_a, rnd_a = np.array(bo), np.array(rnd)
        diff = bo_a - rnd_a
        # Paired across seeds -- same seed means the same noise draws and the same
        # opening design, so the pairing is real and the comparison is much tighter.
        rng = np.random.default_rng(0)
        boot = np.array([diff[rng.integers(0, len(diff), len(diff))].mean()
                         for _ in range(4000)])
        lo, hi = np.percentile(boot, [2.5, 97.5])
        verdicts[fn.name] = (diff.mean(), lo, hi)
        print(f"{fn.name:>12} {d:>3} {fn.optimum_value:>11.4f} "
              f"{bo_a.mean():>11.4f}+-{bo_a.std():<7.3f} "
              f"{rnd_a.mean():>11.4f}+-{rnd_a.std():<7.3f} "
              f"{diff.mean():>+8.4f}")

    print(f"\n{'=' * 88}\nPAIRED DIFFERENCE, BO minus random, 95% bootstrap over seeds"
          f"\n{'=' * 88}")
    for name, (m, lo, hi) in verdicts.items():
        gate = "  <-- THE GATE" if name == GATE else ""
        print(f"  {name:>12}: {m:>+8.4f}  [{lo:>+8.4f}, {hi:>+8.4f}]{gate}")

    m, lo, _ = verdicts[GATE]
    ok = lo > 0
    verdict = ("PASS — the loop works, proceed to E2/E3/E4."
               if ok else
               "*** FAIL — BO does not beat random on Hartmann6. This is a BUG. STOP. ***")
    print(f"\n{'=' * 88}")
    print(f"  {verdict}")
    print(f"{'=' * 88}")
    print("\n  Ackley is reported, not gated -- stated before the run. Its global "
          "structure is\n  near-flat at d=6, so a GP has little to learn and BO is not "
          "expected to win.")


if __name__ == "__main__":
    main()
