"""Version C: local information, and the statistics the regime detector is built from.

------------------------------------------------------------------------------
WHAT THIS MODULE IS FOR
------------------------------------------------------------------------------

Version B wins the design-space map and ties or beats BO on regret at ``sigma_rel = 0.25``,
but sits **10th of 12** at ``sigma_rel = 0.10`` under rule A. Q53 measured one-shot spread
**losing** on hartmann6 by +0.13 to +0.28, every ``p_holm <= 0.0016``. Version C closes the
first gap and **declares** the second rather than pretending to close it.

Two objects live here.

``n_effective`` is the local-information count. It is the input to section 2.2's
allocation rule and the independent variable in section 0's regression, and it is the
reason section 0 is a gate rather than a formality: if regret is governed by
``sigma / sqrt(n_eff)`` then the sigma = 0.10 deficit is an *identification* artefact of
rule A and no trust region is required; if it is not, the allocation rule has no basis and
must be replaced by empirical calibration.

The detector statistics answer a different question -- **not** "how do we beat hartmann6"
but "can the first plate tell us that we are on a landscape where we will lose". Three
things break a spread design on a multimodal landscape and **only one of them is fixable
at 48 wells**: a disconnected ``{f >= tau}`` bounds a single inscribed box by its largest
component (fixable -- see :func:`boec.designspace.component_report`); a stationary GP
cannot serve basins of different widths with one ARD lengthscale (not fixable without
changing the model to fit a benchmark); and 0.378 neighbours per lengthscale split across
four or five basins is nothing anywhere (not fixable -- that is the budget).

BO wins on Hartmann for a real reason: it commits to one basin and resolves it properly,
which is the **correct** thing to do when you cannot afford to resolve all of them. A
detector that fires on that case and responds the same way arrives at BO's strategy by a
different route, and only when the data say to.

------------------------------------------------------------------------------
THE PROTOCOL, AND WHY IT CONSTRAINS THIS FILE
------------------------------------------------------------------------------

Section 3.3 is **freeze then score once**: fit the rule and its threshold on hill, levy and
rosenbrock only; freeze both in ``docs/OPEN-QUESTIONS.md`` and commit; score **once** on
hartmann6 and ackley. Scoring the held-out families more than once is tuning on the
evaluation set, which is the exact failure this project exists to document.

**One protocol hazard, stated rather than managed.** Version C's *performance* on
hartmann6 depends on the detector, and the detector is *scored* on hartmann6. Both are
measured on the same single pass. If the detector misfires that is a Version C result, not
a reason to refit.

So: every function here is a **statistic**, computed from plate 1 with no oracle access.
None of them is a rule, and no threshold appears in this file. The rule is a registration.

------------------------------------------------------------------------------
NO ORACLE ACCESS, AND WHY IT IS ARCHITECTURAL RATHER THAN A CONVENTION
------------------------------------------------------------------------------

A detector that reads the truth is not a detector; it is a label. Every function here takes
a fitted model and a design and returns a number, and none of them accepts a ``truth``
argument -- so a scoring function cannot be wired into the decision path by accident. The
scoring functions that *do* need truth live in
:func:`boec.designspace.component_report`, on the other side of that line.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["ard_lengthscales", "n_effective"]


def ard_lengthscales(model) -> Tensor:
    """``(d,)`` fitted ARD lengthscales, read off the live model.

    Read, never hardcoded -- the rule :func:`boec.lse.exclusion_radius` already follows,
    and for the same reason: a fixed width means something different at every noise level
    and dimension, and this repository has already documented (D8) what happens when a
    decision rule is anchored on a constant instead of on the object it is about.

    Raises:
        AttributeError: if the model carries no ARD kernel. Deliberately not caught and
            defaulted: a silent fallback would make ``n_eff`` a statement about a made-up
            width, and every number downstream of it -- section 2.2's well count, section
            0's regression -- would be about that width rather than about the fit.
    """
    return model.covar_module.base_kernel.lengthscale.detach().reshape(-1).double()


def n_effective(X: Tensor, x_hat: Tensor, lengthscales: Tensor) -> int:
    """``1 + |{x_i : ||x_i - x_hat||_ARD <= 1}|`` -- wells informing the argmax.

    The registered formula (section 2.2, step 2), implemented literally.

    **What it means.** Under a posterior-mean terminal rule, regret is governed by how well
    the posterior localises the argmax. For a peak of local curvature ``c``, a posterior
    mean error of size ``s`` displaces the argmax by ``r ~ sqrt(s/c)``, giving regret
    ``~ c*r^2 ~ s``; and ``s ~ sigma / sqrt(n_eff)``. So ``n_eff`` is the denominator of the
    only quantity section 0 predicts, and section 0 exists to test whether that model
    holds at all before section 2.2 is allowed to allocate wells on the strength of it.

    **The ARD metric, not Euclidean.** Distance is measured in units of the model's own
    fitted lengthscale per axis. A Euclidean ball would answer a question about the *box*;
    what the allocation rule needs is a question about the *fit*, because an axis the GP
    has decided is inert should not be able to push a well out of the neighbourhood.

    **The bound is inclusive**, ``<= 1``, as registered. At 0.378 neighbours per
    lengthscale a single point either way is a third of the statistic, so an exclusive
    bound is a different estimator rather than a rounding choice.

    **The ``+1`` is the argmax's own local information**, and it is added unconditionally.
    ``x_hat`` is the argmax of a posterior mean and is generically not a design point, so
    the two terms describe different wells; where a design point does sit exactly on
    ``x_hat`` it is counted twice. That is a property of the registered formula, not of
    this implementation, and special-casing it here would make the shipped number differ
    from the registered one -- which is the failure mode this project logs as "every
    constant in a registration names the population it was measured on".

    Args:
        X: ``(n, d)`` the campaign's own wells.
        x_hat: ``(d,)`` the posterior-mean argmax.
        lengthscales: ``(d,)`` fitted ARD lengthscales, from :func:`ard_lengthscales`.

    Raises:
        ValueError: on a width mismatch between ``X``, ``x_hat`` and ``lengthscales``. A
            broadcast would silently answer a different question.
    """
    Xd = torch.as_tensor(X, dtype=torch.double).reshape(-1, X.shape[-1])
    x = torch.as_tensor(x_hat, dtype=torch.double).reshape(-1)
    ls = torch.as_tensor(lengthscales, dtype=torch.double).reshape(-1)
    d = Xd.shape[1]
    if x.numel() != d or ls.numel() != d:
        raise ValueError(
            f"width mismatch: X has d={d}, x_hat has {x.numel()}, "
            f"lengthscales has {ls.numel()} -- broadcasting these would answer a "
            "different question silently")
    if bool((ls <= 0).any()):
        raise ValueError(f"non-positive lengthscale in {ls.tolist()}")
    dist = ((Xd - x) / ls).pow(2).sum(dim=1).sqrt()
    return 1 + int((dist <= 1.0).sum())
