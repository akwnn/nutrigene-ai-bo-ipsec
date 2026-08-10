"""Does the published failure mode reproduce in the benchmark, unstaged?

OWNERSHIP: Person A. Reproduce with `python scripts/run_doe_arm.py`.

Experiment 4 hides part of the space on purpose and then asks whether the traditional
model over-promises outside it. The objection to that design is that the hiding is
staged -- we chose kappa, so of course the model extrapolates.

This arm stages nothing. It runs a textbook two-stage DoE campaign over the **full**
space, exactly the procedure the published study ran, and measures whatever optimum
the fitted surface predicts. If that prediction lands outside the region stage 2
explored and under-delivers, the failure mode has reproduced without anyone arranging
for it -- which is a materially stronger result than E4a in isolation, and it matters
more now that E4's own discrimination claim came back null.

Scored with B's `over_prediction_at_constrained_argmax`, the same function E4a uses.
"""

from __future__ import annotations

import numpy as np

from boec.doe import run_doe_arm
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle
import torch

SIGMAS = (0.10, 0.25)
N_SEEDS = 2


def main() -> None:
    for dim in (6, 8):
        if dim == 8:
            print(f"\n(d=8 skipped: the arm's 20+27+1 split is defined at d=6; "
                  f"a d=8 screen needs its own budget arithmetic and that is a "
                  f"separate decision.)")
            continue

        bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                              torch.ones(dim, dtype=torch.double)])
        ens = load_ensemble(dim=dim)[:10]

        for sigma in SIGMAS:
            rows = []
            for inst in ens:
                for seed in range(N_SEEDS):
                    o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                    r = run_doe_arm(o, bounds, truth=o.truth, budget=48, seed=seed)
                    true_at_conf = float(o.truth(r.confirmation_x.unsqueeze(0)))
                    rows.append(dict(
                        over=r.over_prediction,
                        inside=r.confirmation_inside_stage2,
                        on_edge=r.confirmation_on_stage2_boundary,
                        best_design=float(r.curve[-2]),
                        conf_true=true_at_conf,
                        under=true_at_conf < r.curve[-2],
                        kept=set(r.kept_factors),
                        active=set(inst.active_idx.tolist()),
                        kind=r.stationary_kind,
                    ))

            over = np.array([r["over"] for r in rows])
            escaped = np.array([not r["inside"] for r in rows])
            under = np.array([r["under"] for r in rows])
            recall = np.mean([len(r["kept"] & r["active"]) / 4 for r in rows])
            print(f"\n{'=' * 78}")
            print(f"DoE arm · d={dim} · sigma_rel={sigma} · {len(rows)} runs "
                  f"(10 landscapes x {N_SEEDS} seeds)")
            print(f"{'=' * 78}")
            print(f"  predicted optimum fell OUTSIDE the stage-2 region : "
                  f"{escaped.mean():>6.0%}")
            print(f"  confirmation under-delivered vs best design point : "
                  f"{under.mean():>6.0%}")
            print(f"  over-prediction  median {np.median(over):+.4f}   "
                  f"IQR [{np.percentile(over, 25):+.4f}, {np.percentile(over, 75):+.4f}]"
                  f"   >0 in {np.mean(over > 0):.0%}")
            on_edge = np.array([r["on_edge"] for r in rows])
            print(f"  predicted optimum sat ON the stage-2 boundary        : "
                  f"{on_edge.mean():>6.0%}   (constrained-optimiser signature)")
            print(f"  screen recovered {recall:.0%} of the planted active factors")
            kinds: dict[str, int] = {}
            for r in rows:
                kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
            print(f"  fitted surface turning point: {kinds}")

            print(f"\n  READ: over-prediction here is on the SAME scale as E4a "
                  f"(response max ~1.0),")
            print(f"        but this arm hid nothing -- the narrowness of stage 2 "
                  f"came from the screen.")


if __name__ == "__main__":
    main()
