"""The model — the thing that learns from measurements and says what it expects.

OWNERSHIP: Person B. **Long-lived** — Phases 2 and 3 depend on it. Person A must
be able to explain this file back; that is the definition of done, not a review
checkbox.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

You have run some experiments. You want two things from them:

  1. A guess about what would happen at combinations you have *not* tried.
  2. **An honest statement of how sure that guess is.**

The second is the whole point of this project. A model that says "I predict 0.8"
is far less useful than one that says "I predict 0.8, and near your existing
data I'd bet on that, but way over there I'm really just guessing."

The tool used here is a **Gaussian process**. The intuition: it assumes nearby
recipes give similar results, so it is confident close to things you have
measured and progressively less confident as you move away. That is exactly the
behaviour the paper's argument rests on — a curved-line fit has no way to
express "I have never seen anything like this", and a Gaussian process does.

------------------------------------------------------------------------------
WHY THIS FILE IS SO DEFENSIVE
------------------------------------------------------------------------------

There are **five known ways to configure this wrongly where nothing complains.**
No error, no warning, plausible-looking output, and a completely wrong statement
about how confident the model is. Since "how confident the model is" *is* the
finding, every one of them is fatal and silent.

Three were documented in the spec. Two more were found by running the checks in
`scripts/preflight_pf3.py` against the actually-installed library. All five are
handled here, in one place, so no other file has to remember them:

  1. The library defaults to a different similarity assumption than the one we
     want, and switching costs one argument that is easy to forget.
  2. Two library functions that do nearly the same job return differently-shaped
     objects, so any hardcoded path to read the model's internals works with one
     and crashes with the other.
  3. If you do not tell the model the real boundaries of the space, it invents
     them from whatever data it has seen — which silently destroys Experiment 4,
     whose entire design is to train on a small corner.
  4. Asking the model to include measurement noise in its prediction makes it
     quietly average all the noise it has seen and apply that flat figure
     everywhere.
  5. Fixing (4) by supplying the noise yourself requires it on a *rescaled*
     axis, not the one the training noise uses. Get it wrong and you are off by
     a factor of over a hundred, silently.

**Rule for everyone: nothing outside this file may ask the model for a
prediction directly.** Use :func:`predictive`. That is the only place traps 4
and 5 are handled, and routing everything through it is what stops them coming
back.

------------------------------------------------------------------------------
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

import gpytorch
import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.transforms.input import ChainedInputTransform, Normalize, Warp
from botorch.models.transforms.outcome import Standardize
from botorch.models.utils.gpytorch_modules import get_covar_module_with_dim_scaled_prior
from gpytorch.constraints import GreaterThan
from gpytorch.kernels import AdditiveKernel, Kernel, MaternKernel, RBFKernel, ScaleKernel
from gpytorch.priors import GammaPrior, LogNormalPrior
from gpytorch.mlls import ExactMarginalLogLikelihood
from torch import Tensor

__all__ = [
    "KERNEL_STRUCTURES",
    "Predictive",
    "BiphasicMean",
    "base_kernel",
    "biphasic_mean_from_fit",
    "build_gp",
    "component_variances",
    "is_additive",
    "kernel_is_matern",
    "lengthscale_lower_bound",
    "lengthscales",
    "outcome_scale",
    "predictive",
]

MAX_KERNEL_DEPTH = 10

#: How the kernel decomposes the input space. **Q29.**
#:
#: * ``"product"`` — one ARD Matern over all d factors. The registered E2 model.
#:   Its similarity is a *product* across dimensions, which is the standard
#:   assumption that the response is fundamentally d-dimensional.
#: * ``"additive"`` — a *sum* of d one-dimensional Matern kernels, each with its
#:   own outputscale. Matches a response that is a sum of per-factor terms.
#: * ``"additive+interaction"`` — the sum above plus one full product ARD term.
#:   **Nests both of the others**: drive the additive outputscales to zero and it
#:   is ``"product"``; drive the interaction outputscale to zero and it is
#:   ``"additive"``. So it cannot do worse than either except through estimation
#:   error, which is the honest cost and is what the experiment measures.
KERNEL_STRUCTURES = ("product", "additive", "additive+interaction")


# ---------------------------------------------------------------------------
# Trap 2 — reading the model's internals safely
# ---------------------------------------------------------------------------

def base_kernel(kernel_or_model: Kernel | SingleTaskGP) -> Kernel:
    """Dig down to the kernel that actually holds the lengthscales.

    **Why this exists.** The library has two functions that build a similarity
    measure. One returns it bare. The other returns it wrapped in an extra
    layer. Our main configuration adds that wrapper ourselves. So:

      * ``model.covar_module.lengthscale`` works on the bare one, crashes on the
        wrapped one
      * ``model.covar_module.base_kernel.lengthscale`` is the reverse

    Any hardcoded path is therefore wrong in one of the two configurations we
    actually use, and Experiment 4 uses both. This walks down whatever it is
    handed until it reaches the bottom.

    **Use this everywhere, including in tests.** A test that hardcodes a path is
    a test that stops testing the moment the configuration changes.

    Args:
        kernel_or_model: a kernel, or a model whose kernel to inspect.

    Returns:
        The innermost kernel.
    """
    k = getattr(kernel_or_model, "covar_module", kernel_or_model)
    if isinstance(k, AdditiveKernel):
        raise ValueError(
            "this model has an ADDITIVE kernel, which has no single innermost "
            "kernel and no per-factor lengthscale to read. Relevance under an "
            "additive kernel lives in the per-component OUTPUTSCALE, not the "
            "lengthscale — use `component_variances(model)`. Returning any one "
            "component's lengthscale here would be a believable wrong number, "
            "which is the exact failure this function exists to prevent."
        )
    for _ in range(MAX_KERNEL_DEPTH):
        inner = getattr(k, "base_kernel", None)
        if inner is None:
            return k
        k = inner
    raise RuntimeError(
        f"kernel nested more than {MAX_KERNEL_DEPTH} deep — refusing to keep "
        "unwrapping. Something is wrong with the model configuration."
    )


def is_additive(kernel_or_model: Kernel | SingleTaskGP) -> bool:
    """Does this model decompose the space as a sum rather than a product?"""
    k = getattr(kernel_or_model, "covar_module", kernel_or_model)
    return isinstance(k, AdditiveKernel)


def component_variances(kernel_or_model: Kernel | SingleTaskGP) -> Tensor:
    """``(d,)`` how much of the response each factor's own term explains.

    **This is the additive kernel's relevance measure, and it is a better one
    than ARD's.** Under a product ARD kernel, "this factor does nothing" is said
    by pushing its lengthscale to infinity — a direction in which the likelihood
    is nearly flat, so the estimate is weakly identified and needs a lot of data
    to move. Q25 measured exactly that: at the d=6 opening design the ARD
    separation between inert and active factors was **1.000 against a null of
    1.000**, i.e. no information at all, and it took about 30 evaluations to
    recover.

    Under an additive kernel the same statement is "this component's variance is
    zero", which is a *scale* parameter with data on both sides of it. It shrinks
    properly and is identified from the first fit.

    Returns:
        ``(d,)`` the outputscale of each per-factor component, in the order of
        the input dimensions. Excludes any interaction component.

    Raises:
        ValueError: if the model is not additive — a product kernel has no
            per-factor variance and inventing one would be a silent lie.
    """
    k = getattr(kernel_or_model, "covar_module", kernel_or_model)
    if not isinstance(k, AdditiveKernel):
        raise ValueError(
            "component_variances() needs an additive kernel; this model has a "
            "product kernel, whose relevance measure is the lengthscale. Use "
            "`lengthscales(model)`."
        )
    out = []
    for sub in k.kernels:
        inner = getattr(sub, "base_kernel", None)
        if inner is None or inner.active_dims is None or len(inner.active_dims) != 1:
            continue                      # the interaction term, not a factor term
        out.append((int(inner.active_dims[0]), sub.outputscale.reshape(())))
    return torch.stack([v for _, v in sorted(out, key=lambda t: t[0])])


def lengthscales(kernel_or_model: Kernel | SingleTaskGP) -> Tensor:
    """The model's learned sense of 'how far is far' for each ingredient.

    A small value means the response changes quickly as you vary that
    ingredient — it matters. A large value means the model thinks that
    ingredient barely does anything. Sometimes that is true and informative;
    sometimes it means the model has not seen enough data.

    Returns:
        ``(1, d)`` — one lengthscale per factor.
    """
    return base_kernel(kernel_or_model).lengthscale


def kernel_is_matern(kernel_or_model: Kernel | SingleTaskGP) -> bool:
    """Is the similarity assumption the one we claim in the methods section?

    Trap 1: the library's default is the *other* one, and choosing it is a
    silent no-op. A methods section saying "Matern" while the code ran the
    default would simply be false, so this is asserted in tests.
    """
    return isinstance(base_kernel(kernel_or_model), MaternKernel)


def lengthscale_lower_bound(kernel_or_model: Kernel | SingleTaskGP) -> float:
    """The floor the library puts under lengthscales, read off the live object.

    **Never hardcode this.** It is version-dependent — 0.025 on the installed
    version, but that is an observation, not a guarantee. It matters because a
    lengthscale sitting exactly at the floor is a diagnostic: it means the
    response is wilder than the model can represent.
    """
    return float(base_kernel(kernel_or_model).raw_lengthscale_constraint.lower_bound)


def outcome_scale(model: SingleTaskGP) -> Tensor:
    """The factor the model uses to rescale measurements internally.

    The model standardizes outcomes before working with them, then converts
    back afterwards. That is normally invisible — except when supplying noise
    (trap 5), where you have to convert by hand. Squared, this is the number
    that converts a variance between the two scales.

    Returns:
        ``(m,)``. Raises if the model has no outcome transform.
    """
    transform = getattr(model, "outcome_transform", None)
    if transform is None or not hasattr(transform, "stdvs"):
        raise ValueError(
            "model has no Standardize outcome transform, so there is no scale "
            "to convert by. build_gp always attaches one."
        )
    return transform.stdvs.detach().flatten()


# ---------------------------------------------------------------------------
# Building the model
# ---------------------------------------------------------------------------

def _dim_scaled_matern(ard_num_dims: int, prior_dims: int, active_dims=None) -> MaternKernel:
    """A Matern 5/2 whose lengthscale prior is scaled for ``prior_dims``.

    The library factory ties the two together: it always scales the prior by the
    number of dimensions the kernel itself spans. For the additive structure they
    must be separable, because a one-dimensional *component* still lives inside a
    d-dimensional *problem*, and which of those the prior should track is a real
    choice rather than an implementation detail.

    Holding ``prior_dims = d`` reproduces the production prior exactly, so an
    additive-versus-product comparison moves **one** thing. That is the same
    discipline Q25 applied to the Gamma counterfactual, where using the library's
    convenience constructor would have moved three things at once and made the
    difference unattributable.
    """
    from math import log, sqrt

    sqrt2, sqrt3 = sqrt(2.0), sqrt(3.0)
    prior = LogNormalPrior(loc=sqrt2 + log(prior_dims) * 0.5, scale=sqrt3)
    return MaternKernel(
        nu=2.5,
        ard_num_dims=ard_num_dims,
        active_dims=active_dims,
        lengthscale_prior=prior,
        lengthscale_constraint=GreaterThan(
            2.5e-2, transform=None, initial_value=prior.mode
        ),
    )


def _additive_covar(d: int, *, with_interaction: bool, prior_dims: int) -> Kernel:
    """A sum of d one-dimensional kernels, each carrying its own outputscale.

    **Why this is the indicated model here, from the project's own measurements.**
    Q22 measured the benchmark landscape at **93% additive** (0.930 at d=6, 0.927
    at d=8): almost all of the response is a sum of per-factor terms. A product
    ARD kernel cannot represent that cheaply — it treats the response as
    fundamentally d-dimensional, so learning it means filling a d-dimensional
    cube. At the E2 budget of 48 in six factors that is about 1.9 points per axis,
    and Q25 measured the consequence directly: the final model captured **16% of
    the shape variance** along the axes that matter.

    A sum of one-dimensional terms turns the same 48 points into 48 points *per
    axis*. The sample requirement stops being exponential in d and becomes linear.

    The interaction term, when included, is one full product ARD kernel over all d
    factors. It carries the remaining ~7% and makes this structure a strict
    superset of the production one, so the comparison cannot be won by removing
    capacity.
    """
    comps: list[Kernel] = [
        ScaleKernel(_dim_scaled_matern(1, prior_dims=prior_dims, active_dims=(i,)))
        for i in range(d)
    ]
    if with_interaction:
        comps.append(ScaleKernel(_dim_scaled_matern(d, prior_dims=prior_dims)))
    return AdditiveKernel(*comps)


def build_gp(
    train_X: Tensor,
    train_Y: Tensor,
    train_Yvar: Tensor,
    bounds: Tensor,
    *,
    use_scale_kernel: bool = True,
    fit: bool = True,
    mean_module=None,
    lengthscale_prior: str = "dim_scaled",
    kernel_structure: str = "product",
    additive_prior_dims: int | None = None,
    input_warping: bool = False,
    fit_restarts: int = 1,
) -> SingleTaskGP:
    """Build and fit the model. All five traps are handled here.

    Args:
        train_X: ``(n, d)`` the recipes that were run.
        train_Y: ``(n, 1)`` what was measured. **Always 2-D**, even with one
            outcome — a 1-D array is a different bug that produces plausible
            nonsense.
        train_Yvar: ``(n, 1)`` how noisy each measurement is, as a **variance**,
            in the **same units as train_Y**.

            Two classic mistakes live here, both silent and both producing
            believable but wrong confidence statements: passing a standard
            deviation instead of a variance, and passing it already rescaled.
            Pass the plain variance in the original units; the model handles
            the rescaling.

            This is always required, never optional. One model cannot mix
            "I know the noise here" with "I don't know the noise there", and
            Phase 3 will have both replicated and unreplicated measurements.
        bounds: ``(2, d)`` the **true** boundaries of the space.

            Trap 3: leave this out and the library quietly infers boundaries
            from the training data. Experiment 4 deliberately trains on a small
            corner, so inferred boundaries would place the question point far
            outside the assumed space and nothing would be comparable between
            instances. **Always explicit. Not negotiable.**
        use_scale_kernel: whether to let the model learn its own overall
            magnitude. Default True and this is the primary configuration.

            Fixing it instead pins the far-from-data confidence interval to
            roughly twice the spread of the training data. Experiment 4's
            training corner is exactly where that spread is squashed, so a
            fixed magnitude could make the interval narrow for a reason that
            has nothing to do with the hypothesis being tested. Leaving it free
            avoids confounding the result with the setting.
        fit: whether to fit. False gives an unfitted model, for tests.
        mean_module: what the model assumes where it has no data. ``None`` is
            the default flat fallback. Pass a :class:`BiphasicMean` to have it
            fall back onto the biology's shape instead — see that class for why
            the downside is bounded.
        kernel_structure: how the kernel decomposes the space; one of
            :data:`KERNEL_STRUCTURES`. **Default ``"product"``, which is the
            model E2 ran, and it stays the default.** ``"additive"`` and
            ``"additive+interaction"`` are Q29's arms.
        additive_prior_dims: which dimensionality the per-component lengthscale
            prior is scaled for. Additive structures only.

            **A real choice, not cosmetic.** The dim-scaled prior lengthens
            lengthscales as ``d`` grows, to stop a high-dimensional model
            overfitting. Applied to a *one-dimensional* component that reasoning
            does not hold, and the cost is large: at ``d=6`` the prior mode is
            **0.502** on a normalised axis against **0.205** at 1. The response
            is a biphasic Hill curve with structure at roughly 0.2-0.4, so a
            component sitting at mode 0.502 can barely bend.

            ``None`` means ``d``, which holds the prior identical to the
            production model so that switching structure moves exactly one thing
            — the Q25 discipline. ``1`` is the component-natural choice. Q29
            chooses between them on **held-out model fit, before any regret
            exists**, and reports both.
        input_warping: learn a monotone reparameterisation of each input axis
            (a Kumaraswamy CDF) jointly with the kernel.

            **Why it is a candidate here.** A stationary kernel assumes the
            response wiggles at the same rate everywhere along an axis. A
            dose-response curve does not: it is flat, then turns sharply near
            EC50, then flat again. One lengthscale has to serve both regimes, so
            it is either too long to catch the turn or too short to pool the
            plateaus. Warping lets the model stretch the axis where the action
            is and compress it where nothing happens, which is the same
            information a log-dose axis encodes by hand.

            Costs 2 extra parameters per axis, which at n=14 is not free.
        fit_restarts: how many times to fit the hyperparameters, keeping the
            best marginal likelihood. ``1`` is the library default and what E2
            ran.

            **Not a tuning knob — a correctness one.** Q25 found that a fit on
            outcomes with no signal returns the prior mode on every dimension to
            four decimals, which is also where gpytorch *initialises*. A fit that
            has not moved and a fit that has converged back to its start are
            indistinguishable from the outside, and only one of them is a fit.
            Restarting from perturbed initialisations and keeping the best MLL
            distinguishes them.

    Returns:
        A fitted model.
    """
    if train_X.ndim != 2:
        raise ValueError(f"train_X must be (n, d), got {tuple(train_X.shape)}")
    if train_Y.ndim != 2:
        raise ValueError(
            f"train_Y must be (n, m) even at m=1, got {tuple(train_Y.shape)}. "
            "A 1-D outcome array is a separate bug that fails quietly."
        )
    if train_Yvar.shape != train_Y.shape:
        raise ValueError(
            f"train_Yvar {tuple(train_Yvar.shape)} must match train_Y "
            f"{tuple(train_Y.shape)}"
        )
    if bounds.ndim != 2 or bounds.shape[0] != 2:
        raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
    if bounds.shape[1] != train_X.shape[1]:
        raise ValueError(
            f"bounds has {bounds.shape[1]} factors, train_X has {train_X.shape[1]}"
        )
    if bool(torch.any(train_Yvar < 0)):
        raise ValueError(
            "train_Yvar has negative entries — it is a VARIANCE, not a standard "
            "deviation and not a residual."
        )

    if kernel_structure not in KERNEL_STRUCTURES:
        raise ValueError(
            f"kernel_structure={kernel_structure!r}; expected one of "
            f"{list(KERNEL_STRUCTURES)}. A misspelling that fell through to the "
            "default would run the production model under another arm's label."
        )

    d = train_X.shape[-1]
    m = train_Y.shape[-1]

    if kernel_structure != "product":
        if lengthscale_prior != "dim_scaled":
            raise ValueError(
                f"kernel_structure={kernel_structure!r} with "
                f"lengthscale_prior={lengthscale_prior!r} moves two things at "
                "once, and a difference from such a run is unattributable to "
                "either. Q25 is the precedent."
            )
        # The prior is held at the production d-scaled value -- see
        # `_dim_scaled_matern`. Each per-factor component gets its own
        # outputscale, which is the additive structure's relevance measure, so
        # the outer ScaleKernel below would be redundant and unidentifiable
        # (one global scale multiplying d free scales).
        # The prior is held at the production d-scaled value by default -- see
        # `_dim_scaled_matern`. Each per-factor component carries its own
        # outputscale, which IS the additive structure's relevance measure, so
        # the outer ScaleKernel the product branch adds would be redundant here
        # and unidentifiable: one global scale multiplying d free scales.
        covar: Kernel = _additive_covar(
            d,
            with_interaction=(kernel_structure == "additive+interaction"),
            prior_dims=d if additive_prior_dims is None else int(additive_prior_dims),
        )
        return _finish(train_X, train_Y, train_Yvar, bounds, covar, d, m,
                       mean_module, fit, input_warping, fit_restarts)

    # TRAP 1: use_rbf_kernel defaults to True. This override is what makes the
    # methods section true. Removing it is a silent change of model.
    if lengthscale_prior == "dim_scaled":
        covar: Kernel = get_covar_module_with_dim_scaled_prior(
            ard_num_dims=d, use_rbf_kernel=False
        )
    elif lengthscale_prior == "gamma":
        # The pre-Hvarfner default, built by hand rather than via
        # `get_matern_kernel_with_gamma_prior`, because that factory would move
        # THREE variables at once: it returns an already-wrapped ScaleKernel (so
        # this function would double-wrap), it attaches an outputscale prior the
        # production model does not have, and it installs Positive() instead of
        # GreaterThan(0.025, transform=None), changing the optimiser's box. A
        # counterfactual that moves three things cannot attribute a difference to
        # any of them, so everything except the prior is held identical here.
        gp = GammaPrior(3.0, 6.0)
        covar = MaternKernel(
            nu=2.5,
            ard_num_dims=d,
            lengthscale_prior=gp,
            lengthscale_constraint=GreaterThan(
                2.5e-2, transform=None, initial_value=gp.mode
            ),
        )
    else:
        raise ValueError(
            f"lengthscale_prior={lengthscale_prior!r}; expected 'dim_scaled' "
            "(production) or 'gamma' (the pre-Hvarfner default, for counterfactuals)"
        )
    if use_scale_kernel:
        # The factory returns a BARE kernel (trap 2). We add the wrapper that
        # lets the model learn its own overall magnitude. This is why
        # base_kernel() must be used to read anything back.
        covar = ScaleKernel(covar)

    return _finish(train_X, train_Y, train_Yvar, bounds, covar, d, m,
                   mean_module, fit, input_warping, fit_restarts)


def _finish(train_X, train_Y, train_Yvar, bounds, covar, d, m,
            mean_module, fit, input_warping, fit_restarts) -> SingleTaskGP:
    """Assemble and fit. One path, so every kernel structure gets the same
    transforms, the same traps handled, and the same fitting policy."""
    # TRAP 3: explicit bounds, always.
    tf = Normalize(d=d, bounds=bounds.double())
    if input_warping:
        # Warping operates on the UNIT CUBE, so it must come after Normalize.
        # Chained the other way round it would warp raw units and the
        # Kumaraswamy CDF would saturate -- silently, with a believable fit.
        tf = ChainedInputTransform(
            normalize=tf, warp=Warp(d=d, indices=list(range(d))),
        )

    extra = {"mean_module": mean_module} if mean_module is not None else {}

    def build():
        return SingleTaskGP(
            train_X.double(),
            train_Y.double(),
            train_Yvar.double(),
            covar_module=copy.deepcopy(covar),
            input_transform=copy.deepcopy(tf),
            outcome_transform=Standardize(m=m),
            **extra,
        )

    model = build()
    if not fit:
        return model
    if fit_restarts <= 1:
        fit_gpytorch_mll(ExactMarginalLogLikelihood(model.likelihood, model))
        return model

    # Keep the best marginal likelihood over restarts. See `fit_restarts` in
    # build_gp's docstring for why this is a correctness measure and not tuning:
    # a fit that never moved off its initialisation is indistinguishable from a
    # converged one unless something compares them.
    best, best_mll = None, -float("inf")
    for r in range(int(fit_restarts)):
        cand = model if r == 0 else build()
        mll = ExactMarginalLogLikelihood(cand.likelihood, cand)
        if r:
            with torch.no_grad():
                for p in cand.parameters():
                    p.add_(torch.randn_like(p) * 0.5)
        try:
            fit_gpytorch_mll(mll)
        except Exception:
            continue                      # a failed restart is not a failed fit
        with torch.no_grad():
            cand.eval()
            score = float(mll(cand(*cand.train_inputs), cand.train_targets).sum())
            cand.train()
        if score > best_mll:
            best, best_mll = cand, score
    if best is None:
        raise RuntimeError(
            f"all {fit_restarts} hyperparameter fits failed — refusing to return "
            "an unfitted model that would look fitted."
        )
    return best


# ---------------------------------------------------------------------------
# Traps 4 and 5 — asking the model a question
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Predictive:
    """What the model expects at some points, and how sure it is.

    Attributes:
        mean: ``(n, m)`` the model's best guess.
        variance: ``(n, m)`` how unsure it is, squared.
        includes_noise: whether ``variance`` covers what a lab would actually
            measure (True) or only the underlying smooth response (False).

            Both are legitimate and they answer different questions. **Say
            which one every reported number is.** The measurement one is the
            primary metric for calibration; the underlying one is a model
            diagnostic.
    """

    mean: Tensor
    variance: Tensor
    includes_noise: bool

    @property
    def stddev(self) -> Tensor:
        """``(n, m)`` — the scorer Experiment 4 calls 'GP predictive sd'."""
        return self.variance.sqrt()

    def interval(self, alpha: float = 0.05) -> tuple[Tensor, Tensor]:
        """A 95% range by default. Returns ``(lower, upper)``, each ``(n, m)``."""
        z = torch.distributions.Normal(0.0, 1.0).icdf(
            torch.tensor(1.0 - alpha / 2.0, dtype=torch.double)
        )
        half = z * self.stddev
        return self.mean - half, self.mean + half


def predictive(
    model: SingleTaskGP,
    X: Tensor,
    *,
    noise: Tensor | None = None,
) -> Predictive:
    """Ask the model what it expects at ``X``. **The only sanctioned way.**

    Nothing else in this codebase may call ``model.posterior`` directly, because
    this is where traps 4 and 5 are handled.

    **Trap 4.** The obvious way to ask "including measurement noise" makes the
    library average every noise value it has ever seen and apply that single
    flat figure to every point you asked about. No warning. The source even
    carries a note from its authors saying it should be smarter. Since the
    headline calibration number is measured at points that have not been run,
    this would silently compute it against a noise level nobody chose. **So we
    never use that path.**

    **Trap 5.** Supplying the noise yourself fixes it — but the number has to be
    on the model's internal rescaled axis, whereas the training noise is on the
    original one. They are inconsistent. Passing it in the obvious units was
    wrong by a factor of 161 in testing. This function does the conversion, so
    callers can pass ordinary units and stop thinking about it.

    Args:
        model: a fitted model.
        X: ``(n, d)`` points to ask about, in **original** units — the input
            transform handles the rest.
        noise: ``(n, m)`` expected measurement noise at those points, as a
            **variance in the same units as the training outcomes**.

            ``None`` gives the underlying smooth response with no measurement
            noise added — a model diagnostic, not what a lab measures.

            To get what a lab measures, pass the plug-in estimate
            ``y_hat**2 * sigma_rel**2 + sigma_add**2``. Say so in methods: the
            noise at an unrun point is a modelling assumption, not an
            observation, and stating which assumption was made is the honest
            thing to do.

    Returns:
        A :class:`Predictive`.
    """
    if X.ndim != 2:
        raise ValueError(f"X must be (n, d), got {tuple(X.shape)}")

    model.eval()
    with torch.no_grad():
        if noise is None:
            post = model.posterior(X.double())
            return Predictive(post.mean, post.variance, includes_noise=False)

        if noise.ndim != 2:
            raise ValueError(
                f"noise must be (n, m), got {tuple(noise.shape)} — a 1-D array "
                "is the same class of bug as a 1-D outcome."
            )
        if noise.shape[0] != X.shape[0]:
            raise ValueError(
                f"noise has {noise.shape[0]} rows, X has {X.shape[0]}"
            )
        if bool(torch.any(noise < 0)):
            raise ValueError("noise is a VARIANCE — it cannot be negative.")

        # TRAP 5: convert from the original axis to the model's internal one.
        # Skipping this line was wrong by 161x in the PF3 test case, silently.
        scale2 = outcome_scale(model).pow(2)
        post = model.posterior(X.double(), observation_noise=noise.double() / scale2)
        return Predictive(post.mean, post.variance, includes_noise=True)


# ---------------------------------------------------------------------------
# Giving the model a shape to fall back on
# ---------------------------------------------------------------------------

class BiphasicMean(gpytorch.means.Mean):
    """Tells the model what shape to assume where it has no data.

    **The problem this solves.** Far from anything measured, a standard GP
    reverts to a flat guess. That is honest but useless: it is exactly where
    we need a prediction, and "flat" is the one thing the biology certainly is
    not. Every ingredient helps, plateaus, then hurts.

    So instead of falling back to flat, it falls back to *that shape* — fitted
    from the data by the practitioner-form model. Near the data the GP does
    what it always did; far away it settles onto biology rather than onto zero.

    **Why there is a learned weight on it, and why that matters.** The shape
    might be wrong, and a confidently wrong fallback is worse than a flat one.
    So the shape is multiplied by a weight the model learns for itself:

        mean(x) = scale * shape(x) + offset

    If the shape is not helping, ``scale`` shrinks toward zero and what is left
    is a constant — **exactly the model we already had**. So this cannot do
    worse than the current setup other than by the optimiser landing badly. The
    downside is bounded by construction, which is the only reason it is worth
    trying on a short timeline.

    **The trap this design avoids.** The obvious implementation freezes the
    fitted shape and inserts it directly. That fails silently, because the model
    works internally on rescaled measurements — so a mean supplied in the
    original units is wrong by whatever the rescaling factor happens to be, and
    nothing complains. Learning ``scale`` and ``offset`` absorbs that
    conversion, so there is no unit to get wrong. Same class of trap as the two
    already documented above; designed out rather than documented around.

    Args:
        ec50: ``(d,)`` fitted rise points, from the practitioner-form model.
        ic50: ``(d,)`` fitted decline points.
        n: ``(d,)`` fitted steepness.
        weights: ``(d,)`` per-ingredient contribution.
    """

    def __init__(self, ec50: Tensor, ic50: Tensor, n: Tensor, weights: Tensor) -> None:
        super().__init__()
        # Frozen: fitted beforehand, not re-fitted here. Fitting the shape and
        # the kernel together at 48 points invites them to explain each other.
        self.register_buffer("ec50", ec50.double())
        self.register_buffer("ic50", ic50.double())
        self.register_buffer("n_exp", n.double())
        self.register_buffer("weights", weights.double())
        # Learned. These are what make the fallback optional rather than forced.
        self.register_parameter("raw_scale", torch.nn.Parameter(torch.zeros(1, dtype=torch.double)))
        self.register_parameter("offset", torch.nn.Parameter(torch.zeros(1, dtype=torch.double)))

    @property
    def shape_weight(self) -> float:
        """How much the model ended up trusting the shape. Near 0 means not at all."""
        return float(self.raw_scale.detach())

    def forward(self, x: Tensor) -> Tensor:
        from boec.parametric import biphasic_response_torch

        per_factor = biphasic_response_torch(x, self.ec50, self.ic50, self.n_exp)
        shape = (per_factor * self.weights).sum(-1)
        return self.raw_scale * shape + self.offset


def biphasic_mean_from_fit(fit) -> BiphasicMean:
    """Build the fallback shape from an already-fitted practitioner-form model.

    Raises:
        ValueError: if that fit never converged. A fallback built from a failed
            fit would be arbitrary, and arbitrary is worse than flat.
    """
    if not fit.converged:
        raise ValueError(
            "cannot build a fallback shape from a fit that did not converge — "
            f"it would be arbitrary. Optimizer said: {fit.message}"
        )
    return BiphasicMean(
        torch.as_tensor(fit.ec50), torch.as_tensor(fit.ic50),
        torch.as_tensor(fit.n), torch.as_tensor(fit.weights),
    )
