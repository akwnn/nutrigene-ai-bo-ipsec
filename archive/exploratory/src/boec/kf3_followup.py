"""KF-3 follow-up: does a better-aligned criterion or a diversity-aware batch earn what
plain boundary-targeted LSE/SUR could not?

Registered in ``docs/SPADE-KF3-FOLLOWUP-SPEC.md``, frozen at commit `6c5e860`, corrected by
Erratum 1 (`4326de1`, ground-truth leakage in the original `EV(x)` recipe) and Erratum 2
(`4a23175`, a hardcoded exclusion radius and a kernel unit mismatch) before this file existed.

------------------------------------------------------------------------------
WHY THIS IS A SEPARATE MODULE FROM `boec.final_spade`
------------------------------------------------------------------------------

`spade-final-2026-08-23`'s KF-3 answered one question (does `spade_cf_m0` beat random) with
a single FAIL. It does not answer *why*. This module isolates two independently-registered
candidate fixes -- an acquisition criterion aligned with the study's own outcome metric
(`expected_deviation_reduction`, §2.1), and a diversity-aware batch selector
(`repulsion_penalized_batch`, §2.2) -- into functions that can be composed into arms and
tested in isolation, so a result is attributable to the mechanism that earned it.

------------------------------------------------------------------------------
`expected_deviation_reduction` TAKES NO `truth` ARGUMENT -- ARCHITECTURALLY
------------------------------------------------------------------------------

Erratum 1 exists because the first-registered recipe would have scored fantasy outcomes
against ground truth. The fix follows the same guard `boec.final_spade.local_wells` and
`boec.versionc`'s detector statistics already use: the function's signature carries no
`truth` parameter at all, so a scoring value cannot be wired into the acquisition path by
accident. `tests/test_kf3_followup.py` asserts this directly, the same way
`test_local_wells_accepts_no_truth_or_model_argument` does for L1.
"""

from __future__ import annotations

import torch
from torch import Tensor

from boec.designspace import gp_adapter
from boec.lse import exclusion_radius, straddle_score
from boec.surrogate import build_gp
from boec.torch_oracle import _plug_in_yvar
from boec.versionc import split_joint_draws
from boec.vorobev import vorobev_deviation

__all__ = [
    "EV_N_DRAWS", "EV_SCORING_N", "K_ERR", "K_FANTASY", "LAMBDA",
    "expected_deviation_reduction", "fantasy_quantiles", "repulsion_penalized_batch",
    "select_diverse_batch", "select_erroraware_batch",
]

#: §2.1/§2.2. Frozen constants -- see docs/SPADE-KF3-FOLLOWUP-SPEC.md §2 for the reasoning
#: behind each value.
K_FANTASY = 8
K_ERR = 64
EV_SCORING_N = 200
EV_N_DRAWS = 128
LAMBDA = 1.0

_LN2 = 0.6931471805599453


def fantasy_quantiles(mean: float, sd: float, k: int = K_FANTASY) -> Tensor:
    """``(k,)`` fixed quantile fantasy outcomes -- §2.1 step 4.

    A fixed ladder, not a random draw: ``y_j = mean + sd * Phi^-1((j - 0.5) / k)`` for
    ``j = 1..k``. Bitwise reproducible given the same ``mean``/``sd``, and does not add a
    second source of Monte Carlo noise on top of the certificate's own draws.
    """
    ladder = (torch.arange(1, k + 1, dtype=torch.double) - 0.5) / k
    z = torch.distributions.Normal(0.0, 1.0).icdf(ladder)
    return float(mean) + float(sd) * z


def expected_deviation_reduction(
    model,
    x: Tensor,
    X_train: Tensor,
    Y_train: Tensor,
    Yvar_train: Tensor,
    bounds: Tensor,
    theta: float,
    X_er: Tensor,
    *,
    sigma_rel: float,
    sigma_add: float,
    k_fantasy: int = K_FANTASY,
    ev_n_draws: int = EV_N_DRAWS,
    seed: int = 0,
) -> float:
    """``EV(x)`` -- §2.1, corrected by Erratum 1. Higher is better.

    Args:
        model: the current (fitted) ``SingleTaskGP`` -- the raw model, not a
            :func:`boec.designspace.gp_adapter` wrapper, since :func:`boec.versionc.
            split_joint_draws` calls ``model.posterior`` directly.
        x: ``(d,)`` the candidate under consideration.
        X_train, Y_train, Yvar_train: the design so far. Refit, not conditioned in closed
            form -- see the module docstring on why a rank-1 update was rejected.
        bounds: ``(2, d)``, passed through to :func:`boec.surrogate.build_gp`.
        theta: the certifiability threshold. **Not** derived from ``x`` or from any fantasy.
        X_er: ``(EV_SCORING_N, d)`` -- ``EV(x)``'s own scoring grid. Never the certificate's
            ``X_sub``; see spec §2.1 for why a 2,000-point joint draw would dominate cost.
        sigma_rel, sigma_add: the experiment's own, already-known assumed-noise model
            (the same constants every arm's evaluator is configured with) -- used only to
            assign a plausible observation variance to a *fantasized* outcome. This is not
            ground truth: it is the experiment's own noise design, known before any well is
            run, identical to how :func:`boec.lse.predictive_sigma` already uses it.

    Returns:
        ``deviation_before - mean_k(deviation_after_k)``. Positive means the candidate is
        expected to shrink the model's own posterior symmetric-difference ambiguity
        (:func:`boec.vorobev.vorobev_deviation`); it is never computed from ``truth``.
    """
    draws_before, _ = split_joint_draws(model, X_er, n_draws=ev_n_draws, seed=seed)
    dev_before = vorobev_deviation(draws_before, theta)

    mean_x, sd_x = gp_adapter(model).posterior_mean_and_sd(x.reshape(1, -1).double())
    ys = fantasy_quantiles(float(mean_x[0]), float(sd_x[0]), k_fantasy)

    devs_after = []
    for y in ys:
        X_f = torch.cat([X_train, x.reshape(1, -1).double()])
        Y_f = torch.cat([Y_train, y.reshape(1, 1).double()])
        yvar_y = float(_plug_in_yvar(y.reshape(1).numpy(), sigma_rel, sigma_add)[0])
        Yvar_f = torch.cat([Yvar_train, torch.tensor([[yvar_y]], dtype=torch.double)])
        model_f = build_gp(X_f, Y_f, Yvar_f, bounds)
        draws_after, _ = split_joint_draws(model_f, X_er, n_draws=ev_n_draws, seed=seed)
        devs_after.append(vorobev_deviation(draws_after, theta))

    return dev_before - (sum(devs_after) / len(devs_after))


def select_erroraware_batch(
    model,
    X_train: Tensor,
    Y_train: Tensor,
    Yvar_train: Tensor,
    bounds: Tensor,
    cand: Tensor,
    theta: float,
    X_er: Tensor,
    q: int,
    *,
    sigma_rel: float,
    sigma_add: float,
    k_err: int = K_ERR,
    k_fantasy: int = K_FANTASY,
    ev_n_draws: int = EV_N_DRAWS,
    seed: int = 0,
) -> Tensor:
    """``(q, d)`` greedy ``EV``-maximizing batch, for `spade_cf_erroraware`'s plate 2.

    The shortlist of ``k_err`` candidates is a **uniform random subsample** of ``cand``,
    seeded independently of the acquisition itself -- never a `straddle_score` prefilter,
    which would leak the old criterion into the "new" one (spec §2.1).

    Between picks, the design-so-far is updated with the just-picked point at its **current
    posterior mean** (a "kriging believer" commit, not a real evaluation) so the next
    candidate's ``EV`` is scored against a design that already accounts for the pick ahead of
    it -- the spec's "re-scoring EV after each pick against the design-so-far," not a
    one-shot ranking.
    """
    g = torch.Generator().manual_seed(int(seed))
    idx = torch.randperm(cand.shape[0], generator=g)[:k_err]
    shortlist = cand[idx]

    X_c, Y_c, V_c, m = X_train.clone(), Y_train.clone(), Yvar_train.clone(), model
    picks = []
    for _ in range(q):
        scores = torch.tensor([
            expected_deviation_reduction(
                m, shortlist[i], X_c, Y_c, V_c, bounds, theta, X_er,
                sigma_rel=sigma_rel, sigma_add=sigma_add,
                k_fantasy=k_fantasy, ev_n_draws=ev_n_draws, seed=seed)
            for i in range(shortlist.shape[0])
        ])
        j = int(torch.argmax(scores))
        x_pick = shortlist[j]
        picks.append(x_pick)

        mean_pick, _ = gp_adapter(m).posterior_mean_and_sd(x_pick.reshape(1, -1).double())
        y_commit = mean_pick.reshape(1, 1).double()
        yvar_commit = float(_plug_in_yvar(mean_pick.numpy(), sigma_rel, sigma_add)[0])
        X_c = torch.cat([X_c, x_pick.reshape(1, -1).double()])
        Y_c = torch.cat([Y_c, y_commit])
        V_c = torch.cat([V_c, torch.tensor([[yvar_commit]], dtype=torch.double)])
        m = build_gp(X_c, Y_c, V_c, bounds)

    return torch.stack(picks)


def repulsion_penalized_batch(
    mean: Tensor, sd: Tensor, theta: float, cand: Tensor, q: int, *,
    bandwidth: float, lam: float = LAMBDA,
) -> Tensor:
    """``(<=q, d)`` greedy batch under `straddle_score` minus a repulsion penalty -- §2.2.

    Unlike :func:`boec.lse.batch_lse`'s hard exclusion radius, a pick near an already-chosen
    well is penalized smoothly rather than forbidden outright -- the qualitative behaviour is
    the same at the registered ``bandwidth`` (the penalty equals half the straddle score's
    own scale there), but no candidate is ever removed from consideration purely by distance.

    Args:
        mean, sd: ``(n,)`` posterior mean/sd at ``cand``, precomputed by the caller -- this
            function takes no model, mirroring :func:`boec.final_spade.local_wells`'s
            architectural no-model-object guard.
        bandwidth: the scale at which the repulsion penalty reaches half its maximum.
            **Must be `exclusion_radius(model)`, called live** -- see Erratum 2. This
            function does not compute it, so a caller passing a literal is a caller's bug,
            not this function's.
        lam: repulsion weight, frozen at ``LAMBDA = 1.0`` (chosen by analogy, not tuned --
            see spec §2.2).
    """
    score = straddle_score(mean, sd, theta)
    picked_idx: list[int] = []
    for _ in range(min(q, cand.shape[0])):
        if picked_idx:
            picked = cand[picked_idx]
            dist = torch.cdist(cand, picked)
            penalty = lam * torch.exp(-_LN2 * (dist / bandwidth) ** 2).amax(dim=1)
        else:
            penalty = torch.zeros(cand.shape[0], dtype=cand.dtype)
        adjusted = score - penalty
        adjusted[picked_idx] = float("-inf")
        picked_idx.append(int(torch.argmax(adjusted)))
    return cand[picked_idx]


def select_diverse_batch(model, cand: Tensor, theta: float, q: int) -> Tensor:
    """``spade_cf_diverse_batch``'s plate-2 selection: unchanged `straddle_score`, repulsion
    instead of hard exclusion (§2.2). ``bandwidth = exclusion_radius(model)``, called live.
    """
    mean, sd = gp_adapter(model).posterior_mean_and_sd(cand)
    bandwidth = exclusion_radius(model)
    return repulsion_penalized_batch(mean, sd, theta, cand, q, bandwidth=bandwidth)
