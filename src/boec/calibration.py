"""Murphy's calibration-refinement decomposition of the Brier score.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

Every design-space table in this project reports the Brier score of a probability map
as a single number. A Brier score is a sum of three things that move independently
(Murphy 1973):

    Brier = calibration - refinement + uncertainty

*Calibration* (reliability) is how far the forecast probabilities sit from the observed
frequencies they promised, and is a defect -- lower is better, zero is perfect.
*Refinement* (resolution) is how far those observed frequencies sit from the base rate,
and is the skill -- higher is better, and it is the only term that rewards a map for
separating the superlevel set from its complement. *Uncertainty* is the base-rate
variance, a property of the threshold and the instance that no arm can influence.

Two arms can therefore tie on Brier while one is well-calibrated and uninformative and
the other is informative and overconfident. Amendment A5's argument is that refinement
is the quantity the design-space question was always about; this module is what makes
that testable.

------------------------------------------------------------------------------
EQUAL-COUNT BINS, NOT EQUAL-WIDTH
------------------------------------------------------------------------------

Registered: 10 **equal-count** bins. Prevalence at ``tau_frac = 0.95`` is 0.00294, so
these maps live in the tails, and equal-width bins are empty exactly there -- an empty
bin contributes nothing to either term and silently shrinks the decomposition to the
handful of bins near the mode.

Ties are never split. A calibration function must be a function *of the forecast value*;
putting two identical probabilities in two bins with two different observed frequencies
manufactures refinement out of nothing but rank order. So a tie group is assigned whole
to the bin its first member's rank falls in, and :func:`murphy_decomposition` reports
``bin_counts`` so that any binning distorted by ties is visible in the output rather
than inferred from it.

------------------------------------------------------------------------------
THE DECOMPOSED QUANTITY IS THE BINNED BRIER. THIS IS NOT A DODGE.
------------------------------------------------------------------------------

Murphy (1973) is stated for a forecast taking finitely many values, where the bins *are*
the distinct forecast values. Applied to a continuous forecast through binning, the
three-term identity is exact for the **binned** forecast and inexact for the raw one:

    brier_raw - brier_binned = mean_k n_k [ var_k(p) - 2 cov_k(p, o) ]

That within-bin term is real, it carries either sign -- negative when the forecast has
genuine within-bin resolution the bin mean destroys, positive when it is only scatter --
it does not vanish under any choice of sign convention,
and the only ways to make the identity close against ``brier_raw`` are to add a fourth
term or to fold the residual into a redefined "calibration" -- which would make the
identity true by construction and so test nothing. Instead ``brier`` is the Brier score
of the binned forecast, which the identity governs exactly to float64; ``brier_raw`` is
the project's published quantity, bitwise :func:`boec.designspace.brier_and_auc`; and
``within_bin`` is the gap, named and reported. It is zero when the forecast is already
discrete.

------------------------------------------------------------------------------
DEGENERATE IS NOT SMALL
------------------------------------------------------------------------------

Following :func:`boec.vorobev.empirical_containment`, an input that measures nothing
returns ``None`` rather than a number. Everything short of that returns the numbers it
genuinely has, plus a ``degenerate`` flag list, because a component that is *exactly*
zero is not the same as one that is undefined:

* ``single_class`` -- the truth is all one class, so uncertainty is 0 and refinement is
  0 **by construction, for every arm alike**. Returning nan would break the registered
  identity check, which must hold on every row; returning 0.0 unflagged would let a cell
  that can rank nothing enter a ranking. It is returned as 0.0 and flagged, and callers
  drop it. Dropping is arm-symmetric: the truth does not depend on the arm.
* ``few_bins`` -- fewer distinct forecast values than bins, so the decomposition has
  less resolution than registered.
* ``singleton_bin`` -- a bin with one member, whose observed frequency is exactly 0 or 1
  and therefore contributes an uncontrolled amount to both terms.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["N_BINS", "average_precision", "equal_count_bins",
           "murphy_decomposition"]

#: Registered bin count. Not a parameter of the study -- a different value answers a
#: different question, because both terms move monotonically with resolution.
N_BINS = 10


def equal_count_bins(p: Tensor, n_bins: int = N_BINS) -> Tensor:
    """``(n,)`` long: which equal-count bin each forecast falls in. **Ties stay whole.**

    A tie group goes to the bin its first member's rank falls in, so identical forecasts
    always share a bin and the counts are equal only when the forecast has no ties. Bin
    indices are in ascending forecast order and may skip values; callers should read the
    occupied bins, not assume ``n_bins`` of them.
    """
    v = p.reshape(-1).double()
    n = v.numel()
    order = torch.argsort(v, stable=True)
    srt = v[order]

    starts_group = torch.ones(n, dtype=torch.bool)
    starts_group[1:] = srt[1:] != srt[:-1]
    positions = torch.arange(n)
    # cummax over ranks masked to 0 at non-starts: the rank at which this tie group began.
    group_start = torch.cummax(torch.where(starts_group, positions,
                                           torch.zeros_like(positions)), dim=0).values

    binned = (group_start * n_bins) // n
    out = torch.empty(n, dtype=torch.long)
    out[order] = binned
    return out


def murphy_decomposition(p: Tensor, truth: Tensor, tau: float,
                         n_bins: int = N_BINS) -> dict | None:
    """Decompose the Brier score of ``p`` against ``1{truth >= tau}``.

    Same ``(p, truth, tau)`` signature as :func:`boec.designspace.brier_and_auc`, so the
    two score the identical object and ``brier_raw`` is that function's Brier bitwise.

    Returns ``None`` for an empty input -- nothing was measured, so nothing is said.
    Otherwise a dict carrying, per the P7 registration:

        brier         Brier score of the BINNED forecast. The identity's subject.
        calibration   mean_k n_k (pbar_k - obar_k)^2   -- a defect, lower better
        refinement    mean_k n_k (obar_k - obar)^2     -- the skill, higher better
        uncertainty   obar (1 - obar)                  -- base rate, arm-independent
        bin_counts    occupied bin sizes, ascending forecast order

    and, so that nothing is hidden by the binning:

        brier_raw     Brier of the unbinned forecast; the project's published column
        within_bin    brier_raw - brier. Negative when the raw forecast resolves
                      inside its own bins, positive when binning removes only scatter.
        base_rate     obar
        degenerate    [] or some of single_class / few_bins / singleton_bin

    ``calibration - refinement + uncertainty == brier`` holds to float64 (measured
    residual ~1e-16, registered bar 1e-10). ``brier`` is computed point-wise from the
    bin means and **not** from the three terms, so the identity is a test and not a
    tautology.
    """
    v = p.reshape(-1).double()
    n = v.numel()
    if n == 0:
        return None

    label = (truth.reshape(-1) >= tau).double()
    idx = equal_count_bins(v, n_bins)
    width = int(idx.max()) + 1

    counts = torch.bincount(idx, minlength=width).double()
    sum_p = torch.zeros(width, dtype=torch.double).scatter_add_(0, idx, v)
    sum_o = torch.zeros(width, dtype=torch.double).scatter_add_(0, idx, label)
    occupied = counts > 0
    safe = counts.clamp_min(1.0)
    pbar = sum_p / safe
    obar = sum_o / safe
    base = float(label.mean())

    calibration = float((counts * (pbar - obar) ** 2).sum() / n)
    refinement = float((counts * (obar - base) ** 2).sum() / n)
    uncertainty = base * (1.0 - base)
    # Independent of the three terms above: this is what the identity is checked against.
    brier = float(((pbar[idx] - label) ** 2).mean())
    brier_raw = float(((v - label) ** 2).mean())

    bin_counts = [int(c) for c in counts[occupied]]
    n_pos = int(label.sum())
    degenerate = []
    if n_pos == 0 or n_pos == n:
        degenerate.append("single_class")
    if len(bin_counts) < n_bins:
        degenerate.append("few_bins")
    if min(bin_counts) == 1:
        degenerate.append("singleton_bin")

    return {"brier": brier, "calibration": calibration, "refinement": refinement,
            "uncertainty": uncertainty, "bin_counts": bin_counts,
            "brier_raw": brier_raw, "within_bin": brier_raw - brier,
            "base_rate": base, "degenerate": degenerate}


def average_precision(p: Tensor, truth: Tensor, tau: float) -> float | None:
    """AUPRC (average precision) of ``p`` against ``1{truth >= tau}``. **Amendment F2b.**

    Same ``(p, truth, tau)`` signature as :func:`boec.designspace.brier_and_auc`, so the
    two score the identical object and can sit in one row.

    **Why this is reported beside AUC and above it under imbalance.** AUC counts ranked
    pairs, so a false positive is weighed against the whole negative class. When the
    negative class is 19,976 of 20,000 grid points, a hundred false positives per true
    positive barely move it -- AUC stays above 0.9 while precision, and therefore this,
    collapses. F2 measures that imbalance at gamma=0.99, tau_frac=0.60: about 16 minority
    points in 20,000 (Davis & Goadrich 2006).

    **Read it against its baseline.** A ranker with no skill scores the prevalence, not
    0.5, so AP is not comparable across cells whose prevalence runs from 0.0012 to 0.999
    unless the prevalence travels with it. Callers report both.

    Returns ``None`` when either class is absent -- as with AUC's ``nan`` there, the
    honest answer is "undefined", and 1.0 (which is what a degenerate AP evaluates to
    with no negatives) would average into a mean as if it were skill.

    Ties are handled as ``sklearn.metrics.average_precision_score`` handles them: the
    curve steps only at DISTINCT scores, so a tie group is wholly included or wholly
    excluded and no ordering is invented inside it.
    """
    v = p.reshape(-1).double()
    if v.numel() == 0:
        return None
    label = (truth.reshape(-1) >= tau).double()
    n_pos = int(label.sum())
    if n_pos == 0 or n_pos == v.numel():
        return None

    order = torch.argsort(v, descending=True, stable=True)
    v_sorted, y_sorted = v[order], label[order]
    # Step only where the score changes; within a tie group precision is not defined
    # pointwise and sklearn does not pretend it is.
    last = torch.ones(v.numel(), dtype=torch.bool)
    last[:-1] = v_sorted[1:] != v_sorted[:-1]
    idx = torch.nonzero(last, as_tuple=False).reshape(-1)

    tps = torch.cumsum(y_sorted, dim=0)[idx]
    predicted = (idx + 1).double()
    precision = tps / predicted
    recall = tps / float(n_pos)
    prev_recall = torch.cat([torch.zeros(1, dtype=torch.double), recall[:-1]])
    return float(((recall - prev_recall) * precision).sum())
