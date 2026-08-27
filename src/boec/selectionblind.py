"""Selection-blind certification: mean from all wells, uncertainty from the unselected ones.

------------------------------------------------------------------------------
THE DEFECT THIS CORRECTS, MEASURED
------------------------------------------------------------------------------

`docs/SPADE-SELECTION-BLIND-SPEC.md` §1. Plate-2 targeting concentrates wells near the theta
contour; the posterior becomes locally confident there; the shrunken SD lets the Vorob'ev
quantile admit **6x more volume** (0.00714 against random's 0.00119); and that extra volume is
claimed on confidence E3 measured to be unearned -- coverage at **proposed** points is worse
than at **holdout** points by 0.052 to 0.090.

The result, measured on KV's prospective campaigns: the gap between the certificate's
model-internal containment and its truth containment is **+0.1918** for the targeted arm and
**-0.0208** for the random arm, paired difference +0.2171, 95% CI [+0.0746, +0.3838], p=0.0187.

**The acquisition converts unearned confidence into claimed volume.**

------------------------------------------------------------------------------
WHY THE CORRECTION IS EXACT AND NOT A TUNING PARAMETER
------------------------------------------------------------------------------

A Gaussian-process posterior covariance is a function of the design LOCATIONS and the kernel
alone:

    Sigma_post(A) = K(A,A) - K(A,D) [K(D,D) + noise]^-1 K(D,A)

The observed `y` values appear nowhere in it. So the covariance implied by the **unselected
sub-design** is exactly computable from the same fitted kernel, and -- because conditioning on
additional points can only reduce posterior variance -- it is **pointwise larger** than the
full design's. Using it is conservative *by construction*, with no free parameter to tune. A
test asserts that domination on real fits rather than assuming it.

The rule the certificate then follows is:

    the model may use plate 2 to say WHERE the region is,
    and may not use plate 2 to say HOW SURE it is.

------------------------------------------------------------------------------
WHAT THIS IS NOT
------------------------------------------------------------------------------

Not an acquisition rule -- KV-6 closed that question and KW does not reopen it. Not a claim
that it works: KW-1 through KW-6 are registered in the spec above, frozen before any KW number
existed, and include a ceiling (KW-6) recording the negative if the diagnosis is wrong.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["selection_blind_covariance"]


def selection_blind_covariance(model, Z: Tensor) -> Tensor:
    """The joint posterior covariance on ``Z`` implied by ``model``'s design.

    Args:
        model: a fitted GP. To obtain the **selection-blind** covariance, pass a model fitted
            to the UNSELECTED sub-design (plate 1) while taking the mean from a model fitted to
            every well.
        Z: ``(n, d)`` the evaluation points.

    Returns:
        ``(n, n)`` symmetric covariance. Jitter is **not** added here -- the caller adds the
        same ``1e-8`` the committed scorer uses, so the two paths stay comparable.
    """
    with torch.no_grad():
        return model.posterior(Z).mvn.covariance_matrix.double()
