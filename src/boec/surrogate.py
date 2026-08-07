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

from dataclasses import dataclass

import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.models.utils.gpytorch_modules import get_covar_module_with_dim_scaled_prior
from gpytorch.kernels import Kernel, MaternKernel, RBFKernel, ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood
from torch import Tensor

__all__ = [
    "Predictive",
    "base_kernel",
    "build_gp",
    "kernel_is_matern",
    "lengthscale_lower_bound",
    "lengthscales",
    "outcome_scale",
    "predictive",
]

MAX_KERNEL_DEPTH = 10


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
    for _ in range(MAX_KERNEL_DEPTH):
        inner = getattr(k, "base_kernel", None)
        if inner is None:
            return k
        k = inner
    raise RuntimeError(
        f"kernel nested more than {MAX_KERNEL_DEPTH} deep — refusing to keep "
        "unwrapping. Something is wrong with the model configuration."
    )


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

def build_gp(
    train_X: Tensor,
    train_Y: Tensor,
    train_Yvar: Tensor,
    bounds: Tensor,
    *,
    use_scale_kernel: bool = True,
    fit: bool = True,
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

    d = train_X.shape[-1]
    m = train_Y.shape[-1]

    # TRAP 1: use_rbf_kernel defaults to True. This override is what makes the
    # methods section true. Removing it is a silent change of model.
    covar: Kernel = get_covar_module_with_dim_scaled_prior(
        ard_num_dims=d, use_rbf_kernel=False
    )
    if use_scale_kernel:
        # The factory returns a BARE kernel (trap 2). We add the wrapper that
        # lets the model learn its own overall magnitude. This is why
        # base_kernel() must be used to read anything back.
        covar = ScaleKernel(covar)

    model = SingleTaskGP(
        train_X.double(),
        train_Y.double(),
        train_Yvar.double(),
        covar_module=covar,
        # TRAP 3: explicit bounds, always.
        input_transform=Normalize(d=d, bounds=bounds.double()),
        outcome_transform=Standardize(m=m),
    )

    if fit:
        fit_gpytorch_mll(ExactMarginalLogLikelihood(model.likelihood, model))
    return model


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
