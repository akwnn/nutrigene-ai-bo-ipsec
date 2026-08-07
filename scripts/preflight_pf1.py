"""PF1 — over-prediction versus kappa, on the real generated landscapes.

OWNERSHIP: Person A. Reproduce with `python scripts/preflight_pf1.py`.

**This check decides whether Experiment 4 has a mechanism.** If over-prediction is
near zero at every kappa, the traditional model is not over-promising when pushed
outside what it has seen, E4a has nothing to measure, and the plan says we shrink it
and let E2 carry the paper.

Uses B's shared functions throughout -- `metrics.over_prediction_at_constrained_argmax`,
`rsm.fit_second_order`, `rsm.classify_stationary_point`, `designs.central_composite` --
so this number and E4a's are the same number computed once, not two numbers that
disagree with no way to adjudicate.

**Read the turning-point breakdown alongside the rate, not after it.** Inside
`[0, kappa*x*]` the fit sits on the rising arm, and for `n > 1` a Hill function is
convex below its inflection, so at low kappa the fitted surface has positive curvature
and its stationary point is a *minimum*. A bare over-prediction number hides that, and
"the model found a minimum and we walked to a corner" means something quite different
from "the model found a maximum outside the box and it was not there".

**Interpretation caveat, stated before the numbers rather than after.** The scoring box
here is the unit cube, matching `e4.py`. That is a 2-6.7x extrapolation in every
coordinate at once, with training occupying ~1.9e-4 of the cube at kappa=0.6. The
published study extrapolated 1.20x in one coordinate. These magnitudes are therefore
the geometry of the chosen box as much as a property of the model -- see
OPEN-QUESTIONS Q12, which proposes rho as a declared factor. **Do not quote PF1's
absolute over-prediction as the E4 result.**
"""

from __future__ import annotations

import numpy as np
import torch

from boec.designs import central_composite, scale_to_box, sub_box_bounds
from boec.metrics import over_prediction_at_constrained_argmax
from boec.oracles import load_ensemble
from boec.rsm import fit_second_order
from boec.torch_oracle import BiphasicOracle

KAPPAS = (0.6, 0.7, 0.8, 0.9)
N_INSTANCES = 10
SIGMA_REL = 0.10
KINDS = ("maximum", "minimum", "saddle", "ridge")


def run(dim: int = 6, sigma_rel: float = SIGMA_REL) -> dict:
    unit = torch.stack([torch.zeros(dim, dtype=torch.double),
                        torch.ones(dim, dtype=torch.double)])
    design = central_composite(dim, n_centre=4, n_derived=1, face_centred=True)
    out: dict = {}

    for kappa in KAPPAS:
        overs, escaped, kinds, pi_at_argmax, inside_flags = [], [], [], [], []
        for seed, inst in enumerate(load_ensemble(dim=dim)[:N_INSTANCES]):
            orc = BiphasicOracle(inst, sigma_rel=sigma_rel, seed=seed)
            sub = sub_box_bounds(orc.x_star, kappa)
            train_X = scale_to_box(design.coded, sub)
            train_Y, _ = orc.observe(train_X)

            fit = fit_second_order(train_X, train_Y)
            res = over_prediction_at_constrained_argmax(
                fit.predict, orc.truth, unit, n_restarts=20, raw_samples=4096, seed=seed
            )
            overs.append(res.over_prediction)
            escaped.append(not bool(
                torch.all(res.x_argmax >= sub[0] - 1e-12)
                and torch.all(res.x_argmax <= sub[1] + 1e-12)
            ))
            sp = fit.stationary_point(sub)
            kinds.append(sp.kind)
            inside_flags.append(bool(sp.inside_box))
            pi_at_argmax.append(
                float(fit.prediction_interval_width(res.x_argmax.unsqueeze(0)))
            )

        out[kappa] = dict(
            over=np.array(overs), escaped=np.array(escaped),
            kinds=kinds, pi=np.array(pi_at_argmax), sp_inside=np.array(inside_flags),
        )
    return out


def report(dim: int, res: dict) -> None:
    print(f"\n{'=' * 86}\nPF1 · d={dim} · {N_INSTANCES} instances · sigma_rel={SIGMA_REL}"
          f" · scoring box = unit cube\n{'=' * 86}")
    print(f"{'kappa':>6} {'over-prediction (median [IQR])':>34} {'>0':>6} {'escaped':>9} "
          f"{'PI width':>10}")
    for kap in KAPPAS:
        o = res[kap]["over"]
        q1, q3 = np.percentile(o, [25, 75])
        print(f"{kap:>6} {np.median(o):>14.3f}  [{q1:>7.3f},{q3:>8.3f}] "
              f"{np.mean(o > 0):>6.0%} {np.mean(res[kap]['escaped']):>9.0%} "
              f"{np.median(res[kap]['pi']):>10.3f}")

    print(f"\n{'turning point of the fitted surface':>44}")
    print(f"{'kappa':>6} " + "".join(f"{k:>10}" for k in KINDS) + f"{'inside box':>12}")
    for kap in KAPPAS:
        ks = res[kap]["kinds"]
        row = "".join(f"{sum(1 for k in ks if k == kind):>10}" for kind in KINDS)
        print(f"{kap:>6} {row}{np.mean(res[kap]['sp_inside']):>11.0%}")


if __name__ == "__main__":
    # d=6 only, matching the pre-registration in configs/experiment/e4.yaml, which
    # excludes d=8 because a second-order model there has 45 terms and 48 runs leave
    # 3 residual df -- the interval balloons for reasons unrelated to extrapolation.
    # `designs.fractional_factorial` independently refuses d=8 at a half fraction for
    # want of a minimum-aberration generator, so the two constraints agree.
    dim = 6
    res = run(dim)
    report(dim, res)

    lo, hi = np.median(res[0.6]["over"]), np.median(res[0.9]["over"])
    dead = abs(lo) < 1e-3 and abs(hi) < 1e-3
    print(f"\n{'=' * 86}\nKILL CONDITION\n{'=' * 86}")
    print(f"  d={dim}: median over-prediction {lo:.3f} at kappa=0.6, {hi:.3f} at 0.9"
          f"  ->  {'*** NO MECHANISM — E4 must be replanned ***' if dead else 'mechanism present'}")
    print("\n  Magnitudes are unit-cube geometry as much as model behaviour."
          "\n  See OPEN-QUESTIONS Q12 before quoting any of these as the E4 result.")
