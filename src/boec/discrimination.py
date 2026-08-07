"""The discrimination test — Experiment 4's actual measurement.

OWNERSHIP: Person B. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

The story people will remember from this project is "the traditional method
confidently pointed at a recipe that didn't work". But that is the *narrative
hook*, not the finding. The finding is measured here, and it never looks at
that headline recipe at all.

The actual question is: **when the traditional method is about to be badly
wrong, does anything warn you?**

So we take a few hundred recipes spread across the whole space. At each one we
know how wrong the traditional fit is, because we can check against the truth.
Then we ask three different warning systems to rank those recipes by how
worried they are, and we see which ranking best matches where the errors
actually are.

The three warning systems:

  1. **The model's own uncertainty.** This is the claim.
  2. **The traditional method's own error bars.** The fair comparison — the old
     method is not defenceless and pretending otherwise would be dishonest.
  3. **Plain distance to the nearest measured recipe.** The one that must be
     beaten.

------------------------------------------------------------------------------
WHY NUMBER 3 IS THE WHOLE GAME
------------------------------------------------------------------------------

"The model is unsure about things far from data" is very nearly a tautology.
Of course it is — that is how it was built. A result that amounts to restating
the definition is not a result.

So the comparison that matters is against **plain distance**, which requires no
model at all. If simply measuring "how far is this from anything we've tried?"
warns you just as well, then the sophisticated model is an expensive distance
calculator, and we should say so. That is the first objection any reviewer will
reach for, so we reach for it first.

If the model does win, the reason is that it learns *which ingredients matter*
and stretches its notion of distance accordingly — far in a direction that
matters counts for more than far in one that doesn't. Plain distance treats
every direction alike.

------------------------------------------------------------------------------
THE HONESTY CHECK THAT COMES FIRST
------------------------------------------------------------------------------

Before any of the above, we report how much the three warning systems agree
with each other.

If all three rank the recipes almost identically, then the comparison cannot
show anything either way — there is no room for one to beat another. That would
be a real finding about the experiment's design, and it must be **reported, not
buried**. So the agreement table is computed first and printed first, before
anyone sees who won.

------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import torch
from scipy.stats import rankdata, spearmanr
from torch import Tensor

__all__ = [
    "DiscriminationResult",
    "ScorerAgreement",
    "auc_against_threshold",
    "discrimination_test",
    "exact_paired_sign_test",
    "instance_bootstrap_ci",
    "nearest_neighbour_distance",
    "paired_difference_ci",
    "scorer_agreement",
]

SCORER_NAMES = ("gp_predictive_sd", "second_order_pi_width", "nearest_neighbour_distance")


def nearest_neighbour_distance(query: Tensor, train_X: Tensor) -> Tensor:
    """How far each query recipe is from the closest one already measured.

    **The warning system that must be beaten.** Needs no model, no fitting, and
    no assumptions — just a ruler.

    Nearest-neighbour rather than distance-to-the-average-of-the-data: the
    average ignores the shape of what was measured. If the measurements sit in
    a ring, a point in the middle of the ring is close to the average and far
    from everything actually measured. Nearest-neighbour gets that right, which
    makes it the sharper thing to have to beat.

    Args:
        query: ``(n, d)`` recipes to score.
        train_X: ``(m, d)`` recipes already measured.

    Returns:
        ``(n, 1)`` distances.
    """
    if query.ndim != 2 or train_X.ndim != 2:
        raise ValueError(
            f"both must be (n, d); got {tuple(query.shape)} and {tuple(train_X.shape)}"
        )
    if query.shape[1] != train_X.shape[1]:
        raise ValueError(
            f"query has {query.shape[1]} factors, train_X has {train_X.shape[1]}"
        )
    if train_X.shape[0] == 0:
        raise ValueError("train_X is empty — nothing to measure distance to")
    return torch.cdist(query.double(), train_X.double()).min(dim=1).values.unsqueeze(-1)


@dataclass(frozen=True)
class ScorerAgreement:
    """How much the three warning systems agree with each other.

    Attributes:
        names: the scorer names, in matrix order.
        matrix: ``(3, 3)`` rank-correlation between every pair.
        max_offdiagonal: the strongest agreement between any two.
        has_headroom: False when they agree so closely that the comparison
            cannot distinguish them.
        threshold: the agreement level above which headroom is judged absent.
    """

    names: tuple[str, ...]
    matrix: np.ndarray
    max_offdiagonal: float
    has_headroom: bool
    threshold: float

    def summary(self) -> str:
        """A human-readable line, for printing before any result."""
        verdict = (
            "headroom present — the comparison can distinguish the scorers"
            if self.has_headroom
            else (
                f"NO HEADROOM (max agreement {self.max_offdiagonal:.3f} > "
                f"{self.threshold}). The scorers rank almost identically, so "
                "the comparison cannot show anything either way. Report this "
                "as the finding rather than reporting a null result."
            )
        )
        return f"scorer agreement: max off-diagonal rho = {self.max_offdiagonal:.3f} — {verdict}"


def scorer_agreement(
    scores: dict[str, np.ndarray],
    *,
    threshold: float = 0.95,
) -> ScorerAgreement:
    """Rank-correlation between every pair of warning systems.

    **Compute and report this before the result.** The reader needs to see
    whether there was room for the comparison to show anything, before being
    told what it showed.

    Args:
        scores: name to ``(n,)`` array of scores.
        threshold: agreement above which headroom is judged absent. The spec
            pre-registers 0.95.

    Returns:
        A :class:`ScorerAgreement`.
    """
    names = tuple(scores.keys())
    k = len(names)
    if k < 2:
        raise ValueError("need at least two scorers to compare")
    mat = np.eye(k)
    max_off = 0.0
    for i in range(k):
        for j in range(i + 1, k):
            rho = float(spearmanr(scores[names[i]], scores[names[j]]).statistic)
            if np.isnan(rho):
                rho = 0.0
            mat[i, j] = mat[j, i] = rho
            max_off = max(max_off, abs(rho))
    return ScorerAgreement(
        names=names,
        matrix=mat,
        max_offdiagonal=max_off,
        has_headroom=max_off <= threshold,
        threshold=threshold,
    )


def auc_against_threshold(score: np.ndarray, error: np.ndarray, *, tau_quantile: float) -> float:
    """How well a warning system separates the worst errors from the rest.

    1.0 means it ranks every badly-wrong recipe above every acceptable one.
    0.5 means it does no better than a coin flip. Below 0.5 means it is
    actively pointing the wrong way.

    **On the threshold.** To ask "did it flag the bad ones" you need to decide
    what counts as bad. We use a *within-instance quantile* — the worst 20% of
    this instance's errors — rather than a fixed number, because instances
    differ in scale and a fixed number would mean something different on each.
    A quantile also fixes the proportion of "bad" recipes at the same value
    everywhere, which is what makes these numbers comparable across instances.

    The value is pre-registered in ``configs/experiment/e4.yaml``.

    Args:
        score: ``(n,)`` how worried each warning system is.
        error: ``(n,)`` how wrong the traditional fit actually is.
        tau_quantile: e.g. 0.80 means the worst 20% count as bad.

    Returns:
        Area under the ROC curve.
    """
    if score.shape != error.shape:
        raise ValueError(f"shape mismatch: {score.shape} vs {error.shape}")
    if not 0.0 < tau_quantile < 1.0:
        raise ValueError(f"tau_quantile must be in (0, 1), got {tau_quantile}")

    tau = float(np.quantile(error, tau_quantile))
    positive = error > tau
    n_pos = int(positive.sum())
    n_neg = int((~positive).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    # Rank-based AUC (Mann-Whitney), which handles ties correctly.
    ranks = rankdata(score)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


@dataclass(frozen=True)
class DiscriminationResult:
    """One instance's worth of the discrimination test.

    Attributes:
        agreement: the honesty check. **Read this first.**
        spearman: scorer name to rank-correlation with actual error. **Primary.**
        auc: scorer name to AUC. Secondary.
        n_candidates: how many recipes were scored.
        tau_quantile: the pre-registered threshold used for AUC.
        scores: the raw scores, kept for bootstrapping.
        error: the raw errors, kept for bootstrapping.
    """

    agreement: ScorerAgreement
    spearman: dict[str, float]
    auc: dict[str, float]
    n_candidates: int
    tau_quantile: float
    scores: dict[str, np.ndarray] = field(repr=False, default_factory=dict)
    error: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))

    def beats_the_null(self, *, margin: float = 0.0) -> bool:
        """Did the model's uncertainty beat plain distance?

        **If this is False the result is that the model is an expensive
        distance calculator**, and that is what should be reported.
        """
        return self.spearman["gp_predictive_sd"] > (
            self.spearman["nearest_neighbour_distance"] + margin
        )


def discrimination_test(
    gp_sd: Tensor,
    poly_pi_width: Tensor,
    nn_distance: Tensor,
    poly_abs_error: Tensor,
    *,
    tau_quantile: float = 0.80,
    headroom_threshold: float = 0.95,
) -> DiscriminationResult:
    """Run the discrimination test for one instance.

    Note this **never touches the headline recipe**. It is a rank correlation
    between warning systems and actual error, across a few hundred recipes
    spread over the whole space.

    Args:
        gp_sd: ``(n, 1)`` the model's uncertainty at each candidate.
        poly_pi_width: ``(n, 1)`` the traditional method's error-bar width.
        nn_distance: ``(n, 1)`` distance to the nearest measured recipe.
        poly_abs_error: ``(n, 1)`` how wrong the traditional fit actually is.
        tau_quantile: pre-registered AUC threshold.
        headroom_threshold: pre-registered agreement limit.

    Returns:
        A :class:`DiscriminationResult`.
    """
    arrays = {
        "gp_predictive_sd": gp_sd,
        "second_order_pi_width": poly_pi_width,
        "nearest_neighbour_distance": nn_distance,
    }
    n = poly_abs_error.shape[0]
    if n < 20:
        raise ValueError(
            f"only {n} candidate points — too few for a usable standard error. "
            "The spec is explicit that one point per instance is not enough; "
            "the pre-registered count is 512."
        )

    scores: dict[str, np.ndarray] = {}
    for name, t in arrays.items():
        if t.shape[0] != n:
            raise ValueError(f"{name} has {t.shape[0]} rows, error has {n}")
        scores[name] = t.detach().double().numpy().ravel()
    err = poly_abs_error.detach().double().numpy().ravel()
    if np.any(err < 0):
        raise ValueError("poly_abs_error must be an absolute error — no negatives")

    agreement = scorer_agreement(scores, threshold=headroom_threshold)

    spearman: dict[str, float] = {}
    auc: dict[str, float] = {}
    for name, s in scores.items():
        rho = float(spearmanr(s, err).statistic)
        spearman[name] = 0.0 if np.isnan(rho) else rho
        auc[name] = auc_against_threshold(s, err, tau_quantile=tau_quantile)

    return DiscriminationResult(
        agreement=agreement,
        spearman=spearman,
        auc=auc,
        n_candidates=n,
        tau_quantile=tau_quantile,
        scores=scores,
        error=err,
    )


def instance_bootstrap_ci(
    per_instance: list[float],
    *,
    n_bootstrap: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Error bars, by resampling whole instances.

    **Resample instances, never individual recipes within a run.** Recipes
    within a run were chosen one after another, each informed by the last, so
    they are not interchangeable and shuffling them would give a confidence
    interval that means nothing. Whole instances are independent, so they can
    be shuffled.

    Args:
        per_instance: one number per instance.
        n_bootstrap: how many resamples.
        alpha: 0.05 gives a 95% interval.
        seed: fixes the resampling.

    Returns:
        ``(point_estimate, lower, upper)``.
    """
    vals = np.asarray(per_instance, dtype=np.float64)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return (float("nan"),) * 3
    if vals.size == 1:
        return float(vals[0]), float("nan"), float("nan")

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, vals.size, size=(n_bootstrap, vals.size))
    means = vals[idx].mean(axis=1)
    return (
        float(vals.mean()),
        float(np.quantile(means, alpha / 2.0)),
        float(np.quantile(means, 1.0 - alpha / 2.0)),
    )


def paired_difference_ci(
    a: list[float],
    b: list[float],
    *,
    n_bootstrap: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float, bool]:
    """Test whether scorer ``a`` beats scorer ``b`` — **paired, not side by side.**

    **Why this exists and a pair of separate error bars does not do the job.**

    The obvious thing is to compute an error bar for the model's score, another
    for plain distance, and check whether they overlap. That is a genuinely
    common mistake and it is wrong in both directions: overlapping error bars
    can still be a real difference, and non-overlapping ones can be produced by
    a shared source of variation rather than a real gap.

    The reason is that the two scores are measured **on the same landscapes**.
    A landscape that is hard for one scorer is usually hard for the other, so
    most of the spread in each is shared and cancels out when you subtract.
    Comparing the two spreads separately throws that cancellation away and
    hides a real effect behind noise the comparison should never have seen.

    So: take the difference **on each landscape first**, then put the error bar
    on the differences. Resample whole landscapes, never points within a run —
    points within a run were chosen one after another and are not
    interchangeable.

    Args:
        a: one value per landscape, for the scorer being claimed.
        b: one value per landscape, for the scorer that must be beaten.
        n_bootstrap: resamples.
        alpha: 0.05 gives a 95% interval.
        seed: fixes the resampling.

    Returns:
        ``(mean_difference, lower, upper, is_significant)``. ``is_significant``
        is True only when the whole interval sits above zero.
    """
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    if va.shape != vb.shape:
        raise ValueError(
            f"paired test needs one value per landscape from each scorer; "
            f"got {va.shape} and {vb.shape}"
        )
    diff = va - vb
    diff = diff[np.isfinite(diff)]
    if diff.size == 0:
        return float("nan"), float("nan"), float("nan"), False
    if diff.size == 1:
        return float(diff[0]), float("nan"), float("nan"), False

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, diff.size, size=(n_bootstrap, diff.size))
    means = diff[idx].mean(axis=1)
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return float(diff.mean()), lo, hi, bool(lo > 0.0)


def exact_paired_sign_test(differences: Sequence[float]) -> tuple[float, int, bool]:
    """Exact p-value for "is this difference really above zero", by enumeration.

    **With few landscapes this is better than a bootstrap, not merely different.**

    A bootstrap builds its answer out of the handful of numbers you gave it, so
    with ten landscapes its tail estimates rest on ten points and it can be
    optimistic. This instead enumerates **every possible way the signs could
    have come out** — with ten landscapes that is 1024 arrangements, few enough
    to check all of them — and asks how many are as extreme as what we saw.

    No approximation, no resampling, no assumption about the shape of the
    distribution. The answer is exact.

    Recommended for this project because it needs no asymptotics at a cluster
    count where cluster-robust methods are known to be optimistic (Cameron &
    Miller 2015; MacKinnon & Webb on few-cluster inference).

    Args:
        differences: one value per landscape — scorer A minus scorer B.

    Returns:
        ``(p_value, n_used, is_exact)``. ``is_exact`` is False when there were
        too many landscapes to enumerate and sampling was used instead.
    """
    vals = np.asarray([d for d in differences if np.isfinite(d)], dtype=np.float64)
    n = vals.size
    if n == 0:
        return float("nan"), 0, False
    observed = float(vals.mean())

    if n <= 20:  # 2**20 is a million; beyond that, sample instead
        signs = np.array(
            [[1 if (i >> b) & 1 else -1 for b in range(n)] for i in range(2**n)],
            dtype=np.float64,
        )
        means = (signs * vals).mean(axis=1)
        p = float((means >= observed).mean())
        return p, n, True

    rng = np.random.default_rng(0)
    signs = rng.choice([-1.0, 1.0], size=(20000, n))
    means = (signs * vals).mean(axis=1)
    return float((means >= observed).mean()), n, False
