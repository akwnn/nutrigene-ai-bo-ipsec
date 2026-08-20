"""Regenerate a committed campaign and hand back its observations.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

No file in ``results/`` stores ``X`` or ``Y``. ``results/e2-grid.json`` rows carry
``[instance, dim, sigma, seed, arm, best, regret, auc_post_init]`` and nothing else;
Q42, Q57, Q58 and the D20 rescore are likewise scalar summaries. Every question in the
K-series -- which norm governs regret, what a replicate-identified sigma buys, what a
certified design space looks like -- needs the observations, so they must be regenerated.

``Campaign.state_dict`` has always persisted ``train_X``/``train_Y``/``train_Yvar``. The
runners simply never called ``save()``. That is the whole gap this module closes.

------------------------------------------------------------------------------
IT REPRODUCES; IT NEVER RE-DERIVES
------------------------------------------------------------------------------

The regret returned here is computed by the same two lines ``run_e2.py`` used --
``reported_best_curve(truth(X), Y)`` then ``optimum_value - curve[-1]`` -- so a mismatch
means the *regeneration* is wrong, not that the definition drifted. Callers gate on that
mismatch before reading anything else (**D12**: a gate comparing one fresh run to another
can only report that the code agrees with itself).

``scored_curve`` is deliberately re-expressed from :func:`boec.diagnostics.reported_best_curve`
rather than imported from ``scripts/run_e2.py``. Importing a script from a library module
needs a ``sys.path`` hack that breaks under pytest's rootdir handling, and the definition
is one line. It is asserted equal to the committed column by ``tests/test_replay.py``,
which is the only guarantee that matters.

------------------------------------------------------------------------------
THE Yvar TRAP
------------------------------------------------------------------------------

The DoE arm returns ``X_visited``/``Y_visited`` but no variance. The obvious repair --
call ``evaluator.evaluate(X)`` again -- is **wrong**: that draws fresh noise, so it returns
a different ``y`` and therefore a different plug-in variance from the one the campaign
actually carried. The variance is instead recomputed from the **stored** ``Y_visited`` with
:func:`boec.torch_oracle._plug_in_yvar`, which is exactly what the arm was handed.

This matters beyond bookkeeping. ``_plug_in_yvar`` is a function of the **noisy reading**,
not of ``f``, so assumed precision is correlated with the residual: a well whose noise draw
came out low is declared precise and trusted more. That coupling is what K1 tests, and
regenerating it faithfully is a precondition for testing it at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import Tensor

from boec.campaign import Campaign, CampaignConfig
from boec.diagnostics import reported_best_curve
from boec.doe import run_doe_arm
from boec.optimizers import AcqConfig
from boec.oracles import load_ensemble
from boec.runner import PAIRING_EXEMPT, static_design
from boec.torch_oracle import BiphasicOracle, _plug_in_yvar

__all__ = [
    "CampaignRecord",
    "DETERMINISTIC_ARMS",
    "OPTIMISED_ARMS",
    "SPREAD_ARMS",
    "committed_rows",
    "instance_by_id",
    "regenerate",
    "scored_curve",
    "unit_bounds",
]

#: Budget E2 ran. Not a parameter -- a regenerated campaign at a different budget is a
#: different campaign and cannot be gated against the committed column.
BUDGET = 48
Q_BATCH = 4
#: `run_e2.static_curve`'s ordering count. Load-bearing for bitwise reproduction.
N_ORDERINGS = 20

#: Arms whose acquisition never calls an optimiser, so exact equality is the right bar.
DETERMINISTIC_ARMS = ("doe",)
#: Arms routed through multi-start L-BFGS-B. Q54 measured that path at ~1e-06, not exact.
OPTIMISED_ARMS = ("qlogei", "qlognei")
#: Q30's post-hoc kernel arms, needed by K6 (Amendment A1). Same acquisition, other kernel.
KERNEL_ARMS = {"qlogei-add": "additive+interaction", "qlogei-addonly": "additive"}
#: One-shot space-filling arms: 48 points, evaluated once, ONE round against BO's ten.
#:
#: **This is the comparator SPADE is actually about**, and the first K6 run did not have
#: it. That run used ``doe`` as the classical arm, which is not a spread design at all --
#: it is a 20-run screen plus a 27-run CCD confined to a sub-box, with two of six axes
#: pinned by the screen. It answers "is screening fatal for a design space" (it is), not
#: "does a one-shot spread design map better than adaptive search".
SPREAD_ARMS = ("lhs", "sobol", "random")


@dataclass(frozen=True)
class CampaignRecord:
    """One regenerated campaign: what it measured, and what that scored."""

    X: Tensor
    Y: Tensor
    Yvar: Tensor
    instance: str
    dim: int
    sigma: float
    seed: int
    arm: str
    regret: float
    optimum_value: float
    #: Factors the classical arm's stage 2 varied, ascending; ``None`` for adaptive arms
    #: (which vary every axis). Needed for Amendment B3's refuse-to-certify policy.
    #:
    #: **Not derivable from ``X``.** The screen varies all ``d`` factors across its 20
    #: runs and only stage 2 pins the dropped ones, so every column of ``X_visited`` has
    #: nonzero variance even for factors the CCD never moved. An "axis with zero variance"
    #: test would therefore find nothing and silently certify a factor on 20 screening
    #: points that the response-surface fit never saw vary.
    kept_factors: tuple[int, ...] | None = None


def unit_bounds(d: int) -> Tensor:
    """``(2, d)`` the unit box. Identical to ``run_e2.unit_bounds``."""
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def scored_curve(orc, X: Tensor, Y: Tensor) -> np.ndarray:
    """Pick by what the method SAW, score by what was really there (Q17)."""
    return reported_best_curve(orc.truth(X), Y)


def committed_rows(path: str | Path = "results/e2-grid.json") -> list[dict]:
    """The committed grid, exactly as stored."""
    return json.loads(Path(path).read_text())


def instance_by_id(instance: str, dim: int):
    """The committed instance carrying this id, from the versioned ensemble."""
    for inst in load_ensemble(dim):
        if inst.instance_id == instance:
            return inst
    raise KeyError(f"instance {instance!r} not in the d={dim} ensemble")


def regenerate(instance: str, dim: int, sigma: float, seed: int,
               arm: str) -> CampaignRecord:
    """Re-run one committed campaign and return what it measured.

    Args:
        instance: ``instance_id`` from the committed row.
        dim: 6 or 8.
        sigma: ``sigma_rel``; 0.25 primary, 0.10 the optimistic bound.
        seed: the committed row's seed. Seeds the oracle AND the campaign, as E2 did.
        arm: one of :data:`DETERMINISTIC_ARMS`, :data:`OPTIMISED_ARMS`, or a key of
            :data:`KERNEL_ARMS`.

    Returns:
        A :class:`CampaignRecord`. Its ``regret`` is the quantity to gate on.
    """
    inst = instance_by_id(instance, dim)
    bounds = unit_bounds(dim)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)

    if arm in OPTIMISED_ARMS or arm in KERNEL_ARMS:
        kind = arm if arm in OPTIMISED_ARMS else "qlogei"
        cfg = CampaignConfig(d=dim, budget=BUDGET, q=Q_BATCH, seed=seed,
                             acq=AcqConfig(kind=kind),
                             kernel_structure=KERNEL_ARMS.get(arm, "product"))
        c = Campaign(orc, bounds, cfg)
        c.run()
        X, Y, Yvar = c.train_X, c.train_Y, c.train_Yvar
        kept = None
    elif arm in SPREAD_ARMS:
        # One call to evaluate, exactly as `run_e2.static_curve` does. Calling it twice
        # would draw fresh noise and return a different campaign.
        X = static_design(bounds, arm, BUDGET, seed)
        Y, Yvar = orc.evaluate(X)
        kept = None
    elif arm in DETERMINISTIC_ARMS:
        r = run_doe_arm(orc, bounds, truth=orc.truth, budget=BUDGET, seed=seed)
        X, Y = r.X_visited, r.Y_visited
        # Recomputed from the STORED Y, never by re-evaluating -- see module docstring.
        Yvar = torch.from_numpy(
            _plug_in_yvar(Y.detach().cpu().numpy(), orc.sigma_rel, orc.sigma_add))
        kept = tuple(int(j) for j in r.kept_factors)
    else:
        raise ValueError(
            f"unknown arm {arm!r}; expected one of "
            f"{DETERMINISTIC_ARMS + OPTIMISED_ARMS + SPREAD_ARMS + tuple(KERNEL_ARMS)}")

    if arm in SPREAD_ARMS:
        # Reproduce run_e2.static_curve's ARITHMETIC, not merely its result. It averages
        # `N_ORDERINGS` curves whose final values are all identical (the final value is
        # order-invariant), and the float64 mean of 20 copies of x is not bitwise x --
        # measured at up to 5.6e-17, a few ULP. Computing a single curve therefore misses
        # the committed column by ~1e-16 and the gate fires on an arithmetic artefact.
        # The fix is to match the arithmetic, so the gate stays EXACT and no tolerance is
        # invented. Constants below are run_e2's, not chosen here.
        n_init = 2 * dim + 2 if arm not in PAIRING_EXEMPT else 0
        rng = np.random.default_rng(seed)
        curves = []
        for _ in range(N_ORDERINGS):
            order = np.concatenate([np.arange(n_init),
                                    n_init + rng.permutation(BUDGET - n_init)])
            curves.append(scored_curve(orc, X[order], Y[order]))
        curve = np.stack(curves).mean(axis=0)
    else:
        curve = scored_curve(orc, X, Y)
    return CampaignRecord(
        X=X, Y=Y, Yvar=Yvar, instance=instance, dim=dim, sigma=sigma, seed=seed,
        arm=arm, regret=float(inst.optimum_value - curve[-1]),
        optimum_value=float(inst.optimum_value), kept_factors=kept,
    )
