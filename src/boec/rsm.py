"""Response-surface models — the parametric comparator in E4.

Phase 1 only. Thrown away after the paper.

This is the *DoE side* of the comparison. It must be a fair representation of
what a response-surface practitioner would actually do, because the whole E4
claim rests on comparing a GP against a competently-fitted polynomial rather
than a straw man.

The second-order model is **primary**, for three reasons (spec §6 E4a):

  * Estimability — 28 terms at d=6 leaves 20 residual df at n=48. A full
    third-order model is 84 terms at d=6, rank-deficient at n=48, so
    ``(X'X)^-1`` does not exist and the prediction interval is undefined.
  * Literature — canonical and ridge analysis are second-order techniques.
  * Post-selection inference — a stepwise-reduced model picks its terms from
    the same data its interval is computed from, making that interval
    anticonservative. Fatal here, since "the polynomial's interval is too
    narrow" is precisely the finding.

Shape contract: X is ``(n, d)``, outcomes are ``(n, 1)``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations, combinations_with_replacement

import numpy as np
import torch
from scipy import stats
from torch import Tensor

__all__ = [
    "SecondOrderModel",
    "StationaryPoint",
    "StepwiseThirdOrderModel",
    "classify_stationary_point",
    "fit_second_order",
    "fit_stepwise_third_order",
    "second_order_design_matrix",
    "second_order_n_terms",
    "third_order_n_terms",
]


def second_order_n_terms(d: int) -> int:
    """Number of terms in a full second-order model: ``1 + 2d + C(d, 2)``."""
    return 1 + 2 * d + d * (d - 1) // 2


def second_order_design_matrix(X: Tensor | np.ndarray) -> np.ndarray:
    """Build the second-order model matrix.

    Column order is fixed and must not change — the coefficient vector is
    unpacked positionally by :func:`fit_second_order`:

        ``[1] + [x_i] + [x_i^2] + [x_i * x_j for i < j]``

    Args:
        X: ``(n, d)``.

    Returns:
        ``(n, 1 + 2d + C(d, 2))`` float64 array.
    """
    A = np.asarray(X.numpy() if isinstance(X, Tensor) else X, dtype=np.float64)
    if A.ndim != 2:
        raise ValueError(f"X must be (n, d), got {A.shape}")
    n, d = A.shape

    cols = [np.ones((n, 1))]
    cols.append(A)                       # linear
    cols.append(A**2)                    # pure quadratic
    if d > 1:
        inter = np.stack([A[:, i] * A[:, j] for i, j in combinations(range(d), 2)], 1)
        cols.append(inter)
    return np.concatenate(cols, axis=1)


@dataclass(frozen=True)
class StationaryPoint:
    """Where the fitted surface turns over, and what kind of turn it is.

    Reported as a *distribution* across instances, descriptively. It is not the
    E4a primary outcome — see ``metrics.over_prediction_at_constrained_argmax``
    for why.

    Attributes:
        x: ``(d,)`` the stationary point, or ``None`` for a ridge — where the
            Hessian is singular and there is a line of stationary points rather
            than one.
        eigenvalues: ``(d,)`` eigenvalues of the Hessian, ascending.
        kind: one of ``"maximum"``, ``"minimum"``, ``"saddle"``, ``"ridge"`` —
            the four categories the spec asks for in the E4 distribution.
        inside_box: whether ``x`` lies within the supplied box. Always False
            for a ridge.
    """

    x: Tensor | None
    eigenvalues: Tensor
    kind: str
    inside_box: bool


def classify_stationary_point(
    beta: np.ndarray,
    d: int,
    bounds: Tensor | None = None,
    *,
    ridge_rtol: float = 1e-6,
) -> StationaryPoint:
    """Locate and classify the stationary point of a fitted second-order model.

    With ``f = b0 + sum b_i x_i + sum c_i x_i^2 + sum_{i<j} e_ij x_i x_j``:

        ``dF/dx_i = b_i + 2 c_i x_i + sum_{j != i} e_ij x_j``
        ``H[i,i] = 2 c_i``,  ``H[i,j] = e_ij``

    so the stationary point solves ``H x = -b``.

    Args:
        beta: coefficient vector in :func:`second_order_design_matrix` order.
        d: dimension.
        bounds: ``(2, d)``; if given, ``inside_box`` is computed against it.
        ridge_rtol: an eigenvalue below ``ridge_rtol * max|eigenvalue|`` counts
            as zero, giving a ridge rather than a max/min/saddle.

    Returns:
        A :class:`StationaryPoint`.
    """
    b = beta[1 : 1 + d]
    c = beta[1 + d : 1 + 2 * d]

    H = np.zeros((d, d), dtype=np.float64)
    np.fill_diagonal(H, 2.0 * c)
    if d > 1:
        for k, (i, j) in enumerate(combinations(range(d), 2)):
            e = beta[1 + 2 * d + k]
            H[i, j] = e
            H[j, i] = e

    eig = np.linalg.eigvalsh(H)
    scale = np.max(np.abs(eig)) if eig.size else 0.0
    tol = ridge_rtol * scale if scale > 0 else 0.0

    near_zero = np.abs(eig) <= tol
    if np.any(near_zero):
        # A zero eigenvalue means the Hessian is singular: the surface is flat
        # along that eigenvector, so there is a *line* of stationary points
        # rather than one. Classify as a ridge and return no point. Solving
        # here would either raise or, worse, return garbage on a near-singular
        # matrix — and E4 reports these as a distribution, so a wrong location
        # would quietly pollute it.
        return StationaryPoint(None, torch.from_numpy(eig), "ridge", False)
    if np.all(eig < 0):
        kind = "maximum"
    elif np.all(eig > 0):
        kind = "minimum"
    else:
        kind = "saddle"

    x = torch.from_numpy(np.linalg.solve(H, -b))

    inside = False
    if bounds is not None:
        lo, hi = bounds[0].double(), bounds[1].double()
        inside = bool(torch.all(x >= lo) and torch.all(x <= hi))

    return StationaryPoint(x, torch.from_numpy(eig), kind, inside)


@dataclass
class SecondOrderModel:
    """An OLS second-order response surface with prediction intervals.

    Attributes:
        beta: ``(p,)`` coefficients in design-matrix order.
        XtX_inv: ``(p, p)``.
        sigma2: residual variance estimate ``SSE / (n - p)``.
        n: number of design runs.
        p: number of terms.
        d: dimension.
        residual_df: ``n - p``.
    """

    beta: np.ndarray
    XtX_inv: np.ndarray
    sigma2: float
    n: int
    p: int
    d: int

    @property
    def residual_df(self) -> int:
        return self.n - self.p

    def predict(self, X: Tensor) -> Tensor:
        """Mean prediction. ``(n, d) -> (n, 1)``, matching ``metrics.PredictFn``."""
        M = second_order_design_matrix(X)
        return torch.from_numpy((M @ self.beta).reshape(-1, 1))

    def prediction_interval(self, X: Tensor, alpha: float = 0.05) -> tuple[Tensor, Tensor, Tensor]:
        """Prediction interval for a **new observation**.

            ``yhat +/- t_{1-a/2, n-p} * sigma * sqrt(1 + x0' (X'X)^-1 x0)``

        The ``1 +`` is what makes this a prediction interval rather than a
        confidence interval on the mean. E4's comparison is GP *posterior
        predictive* against this — both include observation noise, or the
        comparison is not like-for-like.

        Args:
            X: ``(n, d)`` query points.
            alpha: 0.05 gives a 95% interval.

        Returns:
            ``(mean, lower, upper)``, each ``(n, 1)``.
        """
        if self.residual_df <= 0:
            raise ValueError(
                f"no residual df (n={self.n}, p={self.p}) — interval undefined. "
                "This is why the stepwise third-order model gets no interval."
            )
        M = second_order_design_matrix(X)
        mean = M @ self.beta
        leverage = np.einsum("ij,jk,ik->i", M, self.XtX_inv, M)
        half = (
            stats.t.ppf(1.0 - alpha / 2.0, self.residual_df)
            * np.sqrt(self.sigma2)
            * np.sqrt(1.0 + leverage)
        )
        return (
            torch.from_numpy(mean.reshape(-1, 1)),
            torch.from_numpy((mean - half).reshape(-1, 1)),
            torch.from_numpy((mean + half).reshape(-1, 1)),
        )

    def prediction_interval_width(self, X: Tensor, alpha: float = 0.05) -> Tensor:
        """Full interval width — the DoE comparator scorer in E4's test.

        ``(n, d) -> (n, 1)``.
        """
        _, lo, hi = self.prediction_interval(X, alpha=alpha)
        return hi - lo

    def stationary_point(self, bounds: Tensor | None = None) -> StationaryPoint:
        return classify_stationary_point(self.beta, self.d, bounds)


def fit_second_order(X: Tensor, Y: Tensor) -> SecondOrderModel:
    """Fit a full second-order response surface by ordinary least squares.

    No term selection. Selection is what makes an interval anticonservative,
    and this model's interval is E4's comparator.

    Args:
        X: ``(n, d)`` design points.
        Y: ``(n, 1)`` observed responses.

    Returns:
        A fitted :class:`SecondOrderModel`.

    Raises:
        ValueError: if the design is rank-deficient for a second-order model —
            in which case ``(X'X)^-1`` does not exist and the whole E4
            comparator is undefined. Fail loudly; do not fall back to a
            pseudo-inverse, which would silently produce an interval that
            means something else.
    """
    if Y.ndim != 2 or Y.shape[1] != 1:
        raise ValueError(f"Y must be (n, 1), got {tuple(Y.shape)}")
    if X.shape[0] != Y.shape[0]:
        raise ValueError(f"X has {X.shape[0]} rows, Y has {Y.shape[0]}")

    d = X.shape[1]
    M = second_order_design_matrix(X)
    n, p = M.shape
    if n <= p:
        raise ValueError(
            f"n={n} runs cannot fit p={p} second-order terms at d={d} "
            f"(need n > {p} for any residual df)"
        )

    rank = np.linalg.matrix_rank(M)
    if rank < p:
        raise ValueError(
            f"design matrix is rank-deficient ({rank} < {p}). The design does "
            "not support a full second-order model, so (X'X)^-1 and the "
            "prediction interval do not exist."
        )

    y = Y.double().numpy().ravel()
    XtX_inv = np.linalg.inv(M.T @ M)
    beta = XtX_inv @ (M.T @ y)
    resid = y - M @ beta
    sigma2 = float(resid @ resid) / (n - p)

    return SecondOrderModel(beta=beta, XtX_inv=XtX_inv, sigma2=sigma2, n=n, p=p, d=d)


# ===========================================================================
# The stepwise-reduced third-order model — DESCRIPTIVE ONLY
# ===========================================================================
#
# WHAT THIS IS, IN PLAIN LANGUAGE
#
# The published study we are building on did something slightly fancier than a
# plain curved surface: it allowed more wiggly terms, then threw away the ones
# that did not seem to be doing anything. That is a very common practice, and
# including it here means we are comparing against what people actually do
# rather than a simplified version of it.
#
# WHY IT NEVER GETS ERROR BARS
#
# This is the important part, and it is subtle enough to be worth spelling out.
#
# If you look at a pile of data, pick out the terms that look strongest, and
# then compute error bars from that same pile of data, the error bars come out
# too narrow. You have already used the data once — to choose what to keep —
# and the error bars do not know that. They act as though the terms were chosen
# in advance.
#
# Normally that is a modest technical caveat. Here it is fatal, because "the
# traditional method's error bars are too narrow" is exactly the finding we are
# testing. Reporting error bars that are too narrow *for an unrelated reason*
# would make our own result meaningless.
#
# So this model reports what it predicts, where it thinks the peak is, and how
# many terms survived — and never, under any circumstances, an error bar.
# `prediction_interval` is not implemented. That is deliberate, not an omission.
# ===========================================================================


def third_order_n_terms(d: int) -> int:
    """Terms in a full third-order model: ``C(d + 3, 3)``.

    At d=6 that is **84** — more than the 48 measurements available, which is
    why the full version cannot be fitted at all and reduction is not optional.
    """
    return math.comb(d + 3, 3)


def _third_order_terms(d: int) -> list[tuple[int, ...]]:
    """Exponent patterns for every third-order term, as sorted index tuples.

    ``()`` is the intercept, ``(0,)`` is x0, ``(0, 0)`` is x0 squared,
    ``(0, 1, 2)`` is x0*x1*x2, and so on.
    """
    terms: list[tuple[int, ...]] = [()]
    terms += [(i,) for i in range(d)]
    terms += [tuple(sorted(c)) for c in combinations_with_replacement(range(d), 2)]
    terms += [tuple(sorted(c)) for c in combinations_with_replacement(range(d), 3)]
    return terms


def _build_matrix(X: np.ndarray, terms: list[tuple[int, ...]]) -> np.ndarray:
    n = X.shape[0]
    cols = np.empty((n, len(terms)), dtype=np.float64)
    for j, t in enumerate(terms):
        col = np.ones(n, dtype=np.float64)
        for idx in t:
            col = col * X[:, idx]
        cols[:, j] = col
    return cols


@dataclass
class StepwiseThirdOrderModel:
    """A third-order surface reduced to its apparently-useful terms.

    **Descriptive only. Has no prediction interval and never will.**

    Attributes:
        terms: the surviving term patterns.
        beta: ``(len(terms),)`` fitted coefficients.
        d: dimension.
        n: number of measurements used.
        n_terms_start: how many terms it began with.
        n_terms_kept: how many survived.
        criterion: which rule decided what to drop.
        alpha_out: the p-value above which a term was removed.
    """

    terms: list[tuple[int, ...]]
    beta: np.ndarray
    d: int
    n: int
    n_terms_start: int
    n_terms_kept: int
    criterion: str
    alpha_out: float

    def predict(self, X: Tensor) -> Tensor:
        """Mean prediction. ``(n, d) -> (n, 1)``, matching ``metrics.PredictFn``."""
        A = np.asarray(X.numpy() if isinstance(X, Tensor) else X, dtype=np.float64)
        if A.ndim != 2:
            raise ValueError(f"X must be (n, d), got {A.shape}")
        if A.shape[1] != self.d:
            raise ValueError(f"X has {A.shape[1]} factors, model has {self.d}")
        return torch.from_numpy((_build_matrix(A, self.terms) @ self.beta).reshape(-1, 1))

    def prediction_interval(self, X: Tensor, alpha: float = 0.05):
        """Deliberately not implemented. See the note above this class.

        Raises:
            NotImplementedError: always.
        """
        raise NotImplementedError(
            "The stepwise model has no prediction interval, on purpose. Its "
            "terms were selected using the same data the interval would be "
            "computed from, which makes the interval too narrow for reasons "
            "that have nothing to do with extrapolation. Since 'the "
            "polynomial's interval is too narrow' is exactly what Experiment 4 "
            "is testing, reporting this one would confound the central "
            "finding. Use SecondOrderModel for any interval. "
            "(phase1_build.md §6 E4a, 'post-selection inference'.)"
        )

    def stationary_point(self, bounds: Tensor | None = None) -> StationaryPoint:
        """Where the surface turns over, using only its second-order part.

        A third-order surface can have several turning points and no single
        closed form. This reports the one implied by the quadratic part, which
        is what canonical analysis would look at. Descriptive, like everything
        else here.
        """
        beta_2nd = np.zeros(second_order_n_terms(self.d))
        pos = {(): 0}
        for i in range(self.d):
            pos[(i,)] = 1 + i
            pos[(i, i)] = 1 + self.d + i
        for k, (i, j) in enumerate(combinations(range(self.d), 2)):
            pos[(i, j)] = 1 + 2 * self.d + k
        for t, b in zip(self.terms, self.beta, strict=True):
            if t in pos:
                beta_2nd[pos[t]] = b
        return classify_stationary_point(beta_2nd, self.d, bounds)


def fit_stepwise_third_order(
    X: Tensor,
    Y: Tensor,
    *,
    alpha_out: float = 0.05,
    max_terms: int | None = None,
    protect_main_effects: bool = True,
) -> StepwiseThirdOrderModel:
    """Fit a third-order surface, then drop terms that look inactive.

    Matches the published study's stated practice: "only significant terms up
    to the 3rd order".

    **Method: backward elimination on p-values.** Start from as many terms as
    the data can support, repeatedly remove the least convincing one, stop when
    everything left clears the bar. Recorded in ``.criterion`` so the choice is
    visible rather than buried. See OPEN-QUESTIONS.md Q6.

    Args:
        X: ``(n, d)`` design points.
        Y: ``(n, 1)`` measurements.
        alpha_out: drop terms whose p-value exceeds this.
        max_terms: cap on the starting term count. Defaults to ``n - 5``, so
            there is always some slack left to estimate the noise. A full
            third-order model has 84 terms at d=6 and cannot be fitted from 48
            measurements at all, so some cap is unavoidable.
        protect_main_effects: never drop the intercept or a plain single-factor
            term. Standard practice — dropping a main effect while keeping a
            term built from it produces a model that is hard to interpret and
            behaves oddly away from the data.

    Returns:
        A :class:`StepwiseThirdOrderModel`.
    """
    if Y.ndim != 2 or Y.shape[1] != 1:
        raise ValueError(f"Y must be (n, 1), got {tuple(Y.shape)}")
    if X.shape[0] != Y.shape[0]:
        raise ValueError(f"X has {X.shape[0]} rows, Y has {Y.shape[0]}")

    A = np.asarray(X.numpy() if isinstance(X, Tensor) else X, dtype=np.float64)
    y = Y.double().numpy().ravel()
    n_obs, d = A.shape

    all_terms = _third_order_terms(d)
    n_start_full = len(all_terms)
    cap = max_terms if max_terms is not None else max(1 + d, n_obs - 5)

    # Keep the low-order terms first — they are the ones a practitioner would
    # regard as least droppable, and the ordering from _third_order_terms is
    # already intercept, linear, quadratic, cubic.
    terms = all_terms[: min(cap, n_start_full)]

    # Drop any term that is collinear with the ones already kept; a
    # rank-deficient start makes every p-value meaningless.
    M = _build_matrix(A, terms)
    keep_idx: list[int] = []
    for j in range(M.shape[1]):
        trial = keep_idx + [j]
        if np.linalg.matrix_rank(M[:, trial]) == len(trial):
            keep_idx.append(j)
    terms = [terms[j] for j in keep_idx]
    n_terms_start = len(terms)

    protected: set[tuple[int, ...]] = set()
    if protect_main_effects:
        protected = {()} | {(i,) for i in range(d)}

    while True:
        M = _build_matrix(A, terms)
        n, p = M.shape
        if n - p <= 1 or p <= len(protected):
            break
        XtX_inv = np.linalg.pinv(M.T @ M)
        beta = XtX_inv @ (M.T @ y)
        resid = y - M @ beta
        sigma2 = float(resid @ resid) / (n - p)
        if sigma2 <= 0:
            break
        se = np.sqrt(np.clip(np.diag(XtX_inv) * sigma2, 1e-300, None))
        pvals = 2.0 * (1.0 - stats.t.cdf(np.abs(beta / se), n - p))

        droppable = [j for j, t in enumerate(terms) if t not in protected]
        if not droppable:
            break
        worst = max(droppable, key=lambda j: pvals[j])
        if pvals[worst] <= alpha_out:
            break
        terms = [t for j, t in enumerate(terms) if j != worst]

    M = _build_matrix(A, terms)
    beta = np.linalg.pinv(M.T @ M) @ (M.T @ y)

    return StepwiseThirdOrderModel(
        terms=terms,
        beta=beta,
        d=d,
        n=n_obs,
        n_terms_start=n_terms_start,
        n_terms_kept=len(terms),
        criterion=f"backward elimination on p-values, alpha_out={alpha_out}",
        alpha_out=alpha_out,
    )
