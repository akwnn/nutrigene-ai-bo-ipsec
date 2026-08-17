"""How a finished campaign becomes one recipe. Workstream 6.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------

Every headline number in this project scores a campaign at the **single noisy readout**:
take whichever well read highest on its one measurement, and report the true value there.
That is one operational rule, not a law of laboratories, and Q55 showed it is a poor one —
across both arms and all four cells the noisy argmax is the genuinely best visited well
only **2% to 18%** of the time.

So a reviewer can reasonably ask whether the classical arm's advantage at the higher-noise
condition is a fact about *design geometry* or an artefact of *one selection convention* —
specifically, whether the adaptive arm is punished for clustering its wells where the
differences are smaller than the noise, so that its single reading is a lottery among
near-ties.

These are the alternative rules. They are a module rather than three lines inside a script
because in Workstream 6 the rule **is** the independent variable, and a variable that
cannot be tested is a variable that will be misremembered.

------------------------------------------------------------------------------
WHAT THESE RULES ARE NOT
------------------------------------------------------------------------------

They are **not budget-matched**. Replicating every well doubles the campaign; confirming
the top three adds three wells. That is deliberate and it is the honest framing: the
question is not *"which arm wins at 48 wells under rule X"* — it is *"does the reported
advantage survive a lab that spends a little more to select more carefully"*. Any table
built from these must say what each rule cost.

They are also **not the model recommendation**. Every rule here chooses among wells the
campaign actually measured. Scoring a point the campaign never ran is a different
quantity, computed elsewhere, and mixing the two is the error that voided E2's first run.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
from torch import Tensor

__all__ = ["SELECTION_RULES", "mean_of_replicates", "posterior_mean_at_visited",
           "single_readout", "top_k_average", "top_k_confirm"]

#: The registered set. Named so a stored row can carry which rule produced it, and so the
#: sensitivity table cannot quietly gain a rule that was tried and liked.
SELECTION_RULES = ("single", "replicate", "top3", "posterior")


def single_readout(Y: Tensor) -> int:
    """The published convention: index of the highest single measurement.

    Kept here, rather than assumed, so the sensitivity run's baseline column is produced
    by the same code path as its alternatives — a baseline computed a different way is a
    second variable.
    """
    return int(torch.argmax(Y.double().reshape(-1)))


def mean_of_replicates(Y1: Tensor, Y2: Tensor) -> int:
    """Index of the highest **average of two independent measurements** of each well.

    Halves the selection noise variance. A well that reads high once because of a lucky
    draw has to do it twice, which is precisely the failure mode
    :func:`single_readout` is exposed to.

    Raises:
        ValueError: if the two replicate vectors differ in shape — that would silently
            pair well *i*'s first reading with well *j*'s second.
    """
    if Y1.shape != Y2.shape:
        raise ValueError(
            f"replicates must be the same shape, got {tuple(Y1.shape)} and "
            f"{tuple(Y2.shape)}; pairing mismatched vectors would average two different "
            "wells together.")
    return int(torch.argmax((Y1.double() + Y2.double()).reshape(-1)))


def top_k_confirm(Y: Tensor, Y_confirm: Tensor, *, k: int) -> int:
    """Shortlist the ``k`` best by first reading, re-measure them, take the best.

    The common laboratory protocol, and deliberately **not** equivalent to averaging: a
    well outside the shortlist is never re-measured, so it can never be promoted however
    good it really is. That ceiling is a real property of the protocol and the test suite
    pins it.

    Args:
        Y: the campaign's first readings.
        Y_confirm: a fresh measurement of every well; only the shortlisted entries are
            read, which is what makes the protocol cost ``k`` extra wells and not ``n``.
        k: shortlist size.

    Raises:
        ValueError: if ``k`` exceeds the number of wells, or is below 1.
    """
    y = Y.double().reshape(-1)
    n = int(y.numel())
    if not 1 <= k <= n:
        raise ValueError(f"k={k} outside 1..{n}; a shortlist cannot be longer than the "
                         "campaign or empty.")
    shortlist = torch.topk(y, k).indices
    conf = Y_confirm.double().reshape(-1)[shortlist]
    return int(shortlist[int(torch.argmax(conf))])


def top_k_average(Y: Tensor, Y_confirm: Tensor, *, k: int) -> int:
    """Shortlist ``k`` by first reading; pick argmax of (Y + Y_confirm) / 2.

    The protocol a lab actually uses when it re-measures a shortlist and keeps
    both readings. :func:`top_k_confirm` uses the confirmation reading **alone**,
    which discards the CCD's first readout. Q60 exists because those two rules
    can disagree.

    Cost is still ``k`` extra wells. A well outside the shortlist cannot be
    promoted.

    Raises:
        ValueError: if ``Y`` and ``Y_confirm`` differ in shape, or ``k`` is
            outside ``1..n``.
    """
    y = Y.double().reshape(-1)
    c = Y_confirm.double().reshape(-1)
    if y.shape != c.shape:
        raise ValueError(
            f"replicates must be the same shape, got {tuple(y.shape)} and "
            f"{tuple(c.shape)}; pairing mismatched vectors would average two "
            "different wells together.")
    n = int(y.numel())
    if not 1 <= k <= n:
        raise ValueError(f"k={k} outside 1..{n}; a shortlist cannot be longer "
                         "than the campaign or empty.")
    shortlist = torch.topk(y, k).indices
    avg = (y[shortlist] + c[shortlist]) / 2.0
    return int(shortlist[int(torch.argmax(avg))])


def posterior_mean_at_visited(mean_fn: Callable[[Tensor], Tensor], X: Tensor) -> int:
    """Index of the visited well with the highest fitted posterior mean.

    The rule Rummukainen's campaign ends on, restricted to points already run. A model
    pools information across the whole campaign, so it is not fooled by one well's noise
    draw — but it can be fooled by a misspecified surrogate, which is the trade this row
    of the table exists to show.
    """
    with torch.no_grad():
        m = mean_fn(X.double()).reshape(-1)
    return int(torch.argmax(m))
