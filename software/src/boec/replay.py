"""Regenerate a committed campaign and hand back its observations.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

No file in ``research/results/`` stores ``X`` or ``Y``. ``research/results/e2-grid.json`` rows carry
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
rather than imported from ``software/scripts/run_e2.py``. Importing a script from a library module
needs a ``sys.path`` hack that breaks under pytest's rootdir handling, and the definition
is one line. It is asserted equal to the committed column by ``software/tests/test_replay.py``,
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

------------------------------------------------------------------------------
FAMILIES (B4)
------------------------------------------------------------------------------

``family="hill"`` is the default and is bit-identical to what this module has always
done. ``family`` in :data:`FAMILY_ORACLE` swaps the oracle for ``UnitScaled(FAMILY(d))``
wrapped in a ``TorchEvaluator`` -- the construction ``software/scripts/run_q42_families.py:105/112``
uses -- and reads ``optimum_value`` off the oracle (exactly 1.0) instead of off a
``HillInstance``. Nothing else changes: the same arms, the same scoring rule, the same
provenance.

Family campaigns are keyed by ``(family, dim, sigma, seed)``. There is no ``instance_id``,
so ``instance`` is the family label and a Hill id passed alongside a family is an error
rather than something to ignore.

**The evaluator is constructed fresh on every call, and that is load-bearing.** Q42 gives
the campaign and the DoE arm each their OWN ``TorchEvaluator`` at the same seed
(``run_q42_families.py:112`` and ``:125``), so both noise streams start at draw zero. One
call here regenerates one arm, so one fresh evaluator per call is exactly that. A cached
or shared evaluator would hand the second arm the continuation of the first arm's stream
and every family gate would miss by an amount that reads as a scoring bug.

The 20-ordering mean applied to the spread arms is ``run_e2.static_curve``'s arithmetic
and it is left in place off Hill too, unbranched. It averages 20 curves whose final values
are identical, so it moves the answer by a few ULP and no committed family column exists
for those arms either way; a second scoring definition inside one function would be worse
than 1e-16.

------------------------------------------------------------------------------
THE builder HOOK, AND WHAT THIS MODULE REFUSES TO LEARN
------------------------------------------------------------------------------

``versionb``/``versionb_random`` are two-plate campaigns: fit a GP, call ``batch_lse``,
evaluate twice. This module's registered responsibility is "regenerate a committed
campaign; return ``(X, Y, Yvar)`` + provenance. **Nothing else.**" Teaching it to fit GPs
would create ``replay -> surrogate, designspace, lse`` dependencies inside the one module
every gate imports, and a gate whose own module can fail to import for a reason unrelated
to regeneration is not a gate.

So ``builder`` inverts it. ``builder(orc, dim, seed) -> (X, Y, Yvar, kept, held)`` lives in
the runner that owns the arm; ``replay`` keeps the oracle construction, the scoring rule
and the provenance in one place, which is the property that makes the gate meaningful.
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
from boec.doe import run_doe_arm, run_doe_unscreened_arm
from boec.optimizers import AcqConfig
from boec.oracles import (Ackley, Embedded, Hartmann6, Levy, Rosenbrock, UnitScaled,
                          load_ensemble)
from boec.runner import PAIRING_EXEMPT, static_design
from boec.torch_oracle import BiphasicOracle, TorchEvaluator, _plug_in_yvar

__all__ = [
    "CampaignRecord",
    "DETERMINISTIC_ARMS",
    "FAMILY_ORACLE",
    "OPTIMISED_ARMS",
    "SPREAD_ARMS",
    "committed_rows",
    "family_evaluator",
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
#: `doe_unscreened` (spec §4's mandatory no-screening comparator) joins `doe` here for the
#: same reason: both fit a design and measure ITS predicted optimum, with no adaptive step.
DETERMINISTIC_ARMS = ("doe", "doe_unscreened")
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

#: The four standard families, built EXACTLY as `software/scripts/run_q42_families.py:88-92` does.
#: Copied rather than imported: a library module importing a script needs a `sys.path`
#: hack that breaks under pytest's rootdir handling, and a factory that drifted from Q42's
#: would miss the committed column -- which is what `software/tests/test_replay.py` checks.
#:
#: Hartmann6 is defined at d=6 only. `Embedded` gives it the structure the Hill oracle
#: already has at d=8 -- a fixed active subspace plus inert nuisance axes -- so the
#: dimension contrast is not confounded with a change in the active-factor count.
FAMILY_ORACLE = {
    "hartmann6": lambda d: (Hartmann6() if d == 6
                            else Embedded(Hartmann6(), dim=d, seed=0)),
    "ackley": lambda d: Ackley(dim=d),
    "levy": lambda d: Levy(dim=d),
    "rosenbrock": lambda d: Rosenbrock(dim=d),
}


def family_evaluator(family: str, dim: int, sigma: float, seed: int) -> TorchEvaluator:
    """A FRESH evaluator over ``UnitScaled(family(dim))``. Never cached -- see the docstring.

    ``UnitScaled`` is not cosmetic. Negated, ackley, levy and rosenbrock all have an
    optimum VALUE of exactly 0, so under ``y = f(1 + eps) + eta`` the multiplicative term
    vanishes at the optimum and the hardest region becomes the quietest. Rescaling to
    ``optimum = 1`` puts every family on the Hill oracle's footing, which is what makes
    ``sigma_rel`` mean the same thing in all five.
    """
    if family not in FAMILY_ORACLE:
        raise KeyError(f"unknown family {family!r}; expected 'hill' or one of "
                       f"{tuple(FAMILY_ORACLE)}")
    return TorchEvaluator(UnitScaled(FAMILY_ORACLE[family](dim)),
                          sigma_rel=sigma, seed=seed)


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
    #: Where the screen pinned each dropped factor. Needed to build the ACTIVE SUBSPACE
    #: for Amendment B3: an arm that never varied a factor may not certify a range for it,
    #: so its region is evaluated on a grid holding those factors at the pinned value.
    dropped_held_at: dict[int, float] | None = None
    #: Which oracle produced this. ``"hill"`` for the Hill ensemble, otherwise a key of
    #: :data:`FAMILY_ORACLE`. Off Hill ``instance`` repeats the family label, so a
    #: consumer that read only ``instance`` could not tell a family from a landscape id.
    family: str = "hill"


def unit_bounds(d: int) -> Tensor:
    """``(2, d)`` the unit box. Identical to ``run_e2.unit_bounds``."""
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def scored_curve(orc, X: Tensor, Y: Tensor) -> np.ndarray:
    """Pick by what the method SAW, score by what was really there (Q17)."""
    return reported_best_curve(orc.truth(X), Y)


def committed_rows(path: str | Path = "research/results/e2-grid.json") -> list[dict]:
    """The committed grid, exactly as stored."""
    return json.loads(Path(path).read_text())


def instance_by_id(instance: str, dim: int):
    """The committed instance carrying this id, from the versioned ensemble."""
    for inst in load_ensemble(dim):
        if inst.instance_id == instance:
            return inst
    raise KeyError(f"instance {instance!r} not in the d={dim} ensemble")


def regenerate(instance: str, dim: int, sigma: float, seed: int, arm: str, *,
               family: str = "hill", builder=None) -> CampaignRecord:
    """Re-run one committed campaign and return what it measured.

    Args:
        instance: ``instance_id`` from the committed row on Hill; the family label
            otherwise, since family campaigns are keyed by ``(family, dim, sigma, seed)``
            and carry no ``instance_id``. ``None`` is accepted off Hill.
        dim: 6 or 8.
        sigma: ``sigma_rel``; 0.25 primary, 0.10 the optimistic bound.
        seed: the committed row's seed. Seeds the oracle AND the campaign, as E2 did.
        arm: one of :data:`DETERMINISTIC_ARMS`, :data:`OPTIMISED_ARMS`, or a key of
            :data:`KERNEL_ARMS`. With ``builder`` it is a label only.
        family: ``"hill"`` (default, unchanged behaviour) or a key of
            :data:`FAMILY_ORACLE`.
        builder: ``builder(orc, dim, seed) -> (X, Y, Yvar, kept, held)``, for arms this
            module deliberately does not know how to build -- see the module docstring.
            When given it replaces the arm dispatch entirely; the oracle, the scoring
            rule and the provenance still come from here.

    Returns:
        A :class:`CampaignRecord`. Its ``regret`` is the quantity to gate on.
    """
    bounds = unit_bounds(dim)
    if family == "hill":
        inst = instance_by_id(instance, dim)
        orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        optimum = float(inst.optimum_value)
    else:
        # Raises KeyError on an unknown family, which is the right failure: a typo'd
        # family must not fall through to the Hill ensemble and regenerate the wrong
        # campaign under the right-looking label.
        orc = family_evaluator(family, dim, sigma, seed)
        if instance is not None and instance != family:
            raise ValueError(
                f"family {family!r} campaigns are keyed by (family, dim, sigma, seed) "
                f"and have no instance_id; instance={instance!r} is not the family "
                "label. Pass the family label or None.")
        instance = family
        optimum = float(orc.oracle.optimum_value)

    if builder is not None:
        X, Y, Yvar, kept, held = builder(orc, dim, seed)
    elif arm in OPTIMISED_ARMS or arm in KERNEL_ARMS:
        kind = arm if arm in OPTIMISED_ARMS else "qlogei"
        cfg = CampaignConfig(d=dim, budget=BUDGET, q=Q_BATCH, seed=seed,
                             acq=AcqConfig(kind=kind),
                             kernel_structure=KERNEL_ARMS.get(arm, "product"))
        c = Campaign(orc, bounds, cfg)
        c.run()
        X, Y, Yvar = c.train_X, c.train_Y, c.train_Yvar
        kept = held = None
    elif arm in SPREAD_ARMS:
        # One call to evaluate, exactly as `run_e2.static_curve` does. Calling it twice
        # would draw fresh noise and return a different campaign.
        X = static_design(bounds, arm, BUDGET, seed)
        Y, Yvar = orc.evaluate(X)
        kept = held = None
    elif arm in DETERMINISTIC_ARMS:
        # `doe_unscreened` raises ValueError at dimensions with no feasible centre-point
        # budget (d=8 -- see boec.doe.UNSCREENED_N_CENTRE). That is not caught here: the
        # caller (the benchmark runner) is the one that knows how to record a structured
        # `unavailable_reason` instead of a campaign, and letting it propagate is what makes
        # that distinction visible rather than silently producing a campaign at d=8.
        runner = run_doe_unscreened_arm if arm == "doe_unscreened" else run_doe_arm
        r = runner(orc, bounds, truth=orc.truth, budget=BUDGET, seed=seed)
        X, Y = r.X_visited, r.Y_visited
        # Recomputed from the STORED Y, never by re-evaluating -- see module docstring.
        Yvar = torch.from_numpy(
            _plug_in_yvar(Y.detach().cpu().numpy(), orc.sigma_rel, orc.sigma_add))
        kept = tuple(int(j) for j in r.kept_factors)
        held = {int(k): float(v) for k, v in r.dropped_held_at.items()}
    else:
        raise ValueError(
            f"unknown arm {arm!r}; expected one of "
            f"{DETERMINISTIC_ARMS + OPTIMISED_ARMS + SPREAD_ARMS + tuple(KERNEL_ARMS)}")

    if builder is None and arm in SPREAD_ARMS:
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
        arm=arm, regret=float(optimum - curve[-1]),
        optimum_value=optimum, kept_factors=kept,
        dropped_held_at=held, family=family,
    )
