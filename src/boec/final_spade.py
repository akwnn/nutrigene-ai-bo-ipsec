"""Rule L1 -- the frozen local-exploitation allocation for the final prospective study.

Registered in ``docs/SPADE-FINAL-SPEC.md`` §3.2 at commit ``c4f58d3``, **before this module
existed**. Nothing here is tunable: every constant is either inherited from a registered
formula or is an argument the caller must state.

------------------------------------------------------------------------------
WHAT THIS MODULE IS, AND WHAT IT DELIBERATELY IS NOT
------------------------------------------------------------------------------

``spade_cf_m4`` and ``spade_cf_m8`` spend ``m`` of their eight plate-2 wells near the
plate-1 posterior-mean optimum instead of on the acceptability boundary. This module decides
**where those m wells go**, and nothing else. The remaining ``8 - m`` wells are chosen by the
*identical* :func:`boec.lse.batch_lse` call the ``m0`` arm uses, in the runner, so the three
arms differ in exactly one registered quantity.

It is **not** a trust-region optimiser and it is not an acquisition function. The question
this study asks is not "what is the best local rule" -- that would be a tuning exercise, and
tuning after seeing results is what §11 of the spec prohibits. It is "does spending wells
locally buy regret without costing the certificate", and answering it needs *a* frozen local
rule, defensible and simple, not an optimal one.

------------------------------------------------------------------------------
WHY THE RADIUS IS 1, AND WHY THAT IS NOT A TUNED CONSTANT
------------------------------------------------------------------------------

:func:`boec.versionc.n_effective` counts ``1 + |{x_i : ||x_i - x_hat||_ARD <= 1}|`` -- the
wells informing the argmax. FINDINGS §9.3 measured that ``doe``'s identification gap is
noise-invariant while every BO arm's roughly halves, and attributed the difference to a
winner's-curse term scaling with ``sigma / sqrt(n_eff)``. ``n_eff`` is the denominator of the
only quantity that mechanism predicts.

So the trust region here is **the ARD ball of radius 1** -- literally ``n_effective``'s own
bound. Every well this rule places provably increments the registered statistic. The radius
is *inherited from a registered formula*, not chosen to make the arm perform; a different
radius would be a different statistic, and the project has already logged (D8) what happens
when a decision rule is anchored on an invented constant instead of on the object it is
about.

------------------------------------------------------------------------------
NO ORACLE ACCESS, ENFORCED ON THE SIGNATURE
------------------------------------------------------------------------------

:func:`local_wells` takes **arrays** -- candidates, a posterior mean, the plate-1 design and
the fitted lengthscales. It takes no ``truth``, no oracle, and **no model object**. A model
carries a ``.posterior`` and therefore a route to anything the caller has already computed;
arrays carry nothing. The no-oracle-access property is a fact about the type signature, which
is the guard ``boec.versionc`` uses for its detector statistics and for the same reason: a
rule that *could* be handed truth eventually is, and the failure is silent.

``mean`` must be the **plate-1** posterior mean. That is the caller's obligation and the
runner's test asserts it; this module cannot check it, and says so rather than implying a
guarantee it does not provide.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["DEGENERATE_HI", "DEGENERATE_LO", "LOCAL_RADIUS", "MIN_BOUNDARY_FRAC",
           "MIN_NONEMPTY_RATE", "TARGET_PREVALENCE", "classify_regime", "local_wells"]

#: ``n_effective``'s bound, inherited. See the module docstring -- not a tuning knob.
LOCAL_RADIUS = 1.0

# --------------------------------------------------------------------------
# The frozen bars of the pre-run regime classifier -- spec §5.1, commit c4f58d3.
# Every one of these was written down before any final-study number existed.
# --------------------------------------------------------------------------

#: Outside this the true region is degenerate and nothing is assessable either way.
DEGENERATE_LO, DEGENERATE_HI = 0.01, 0.99
#: A TARGET cell's true region is neither nearly-empty nor nearly-the-whole-box. The upper
#: bar is the one that matters: §14's reading is that at gamma=0.99, tau_frac=0.60 the true
#: set covers 0.99916 of the box, so certifying it is nearly free. That is the EASY corner
#: and calling it a target would flatter every arm.
TARGET_PREVALENCE = (0.05, 0.60)
#: Below this the containment denominator is too thin for the cell to carry the central
#: claim -- KF-10, and §4.8's "cells with n=1-8 are excluded from claims".
MIN_NONEMPTY_RATE = 0.50
#: The straddle band plate 2 exists to resolve. With no band there is nothing for the
#: mechanism under test to do, so a win there would not be evidence for it.
MIN_BOUNDARY_FRAC = 0.05


def local_wells(cand: Tensor, mean: Tensor, X1: Tensor, lengthscales: Tensor, m: int,
                *, radius: float = LOCAL_RADIUS) -> tuple[Tensor, dict]:
    """The ``m`` local exploitation wells, by frozen rule **L1**.

    The rule, implemented literally as registered:

    1. ``x_hat`` is the **grid argmax** of ``mean`` over ``cand``. Deliberately a grid
       argmax and not a continuous optimiser: FINDINGS §4.1 records that this project's one
       non-reproducible path was a post-hoc L-BFGS-B locator with 20 restarts, and the
       campaigns themselves were exact. A grid argmax over a seeded candidate set is bitwise
       reproducible.
    2. The trust region is the ARD ball ``{x : ||(x - x_hat)/ell||_2 <= radius}``.
    3. The ``m`` wells are chosen by **greedy farthest-point (maximin) in the ARD metric**
       from the union of ``X1`` and the wells already chosen, restricted to candidates
       inside the ball. Maximin rather than "closest to ``x_hat``" because stacking wells on
       the predicted optimum re-measures one location; spreading them inside the ball is what
       raises ``n_eff``, which is the statistic the rule exists to move.
    4. Ties are broken by **lowest candidate index**, so the result is deterministic rather
       than dependent on ``torch.argmax``'s tie behaviour across versions.

    Args:
        cand: ``(N, d)`` the frozen candidate set -- the *same* one plate 2's boundary rule
            uses, so the two allocations are drawn from one population.
        mean: ``(N,)`` the **plate-1** posterior mean at ``cand``.
        X1: ``(n1, d)`` the plate-1 design.
        lengthscales: ``(d,)`` fitted ARD lengthscales, from
            :func:`boec.versionc.ard_lengthscales`.
        m: how many local wells to place. ``0`` returns an empty ``(0, d)`` tensor, which is
            what makes ``spade_cf_m0`` bit-identical to the pure boundary arm.
        radius: the ARD ball radius. Defaults to :data:`LOCAL_RADIUS`; exposed as an
            argument so a sensitivity analysis can state a different value **explicitly**
            rather than by editing a constant.

    Returns:
        ``(X_local, diag)``. ``X_local`` is ``(k, d)`` with ``k <= m``. ``diag`` carries
        ``x_hat``, ``n_in_ball``, ``m_requested``, ``m_placed``, ``m_local_short`` and
        ``radius`` -- every quantity needed to recompute the decision from the row.

        ``m_local_short`` is ``True`` when the ball held fewer than ``m`` candidates. The
        caller **must** fall back to the boundary rule for the remainder; returning fewer
        wells silently would break the equal-well budget and make an ``m4`` arm secretly an
        ``m2``.

    Raises:
        ValueError: on a width mismatch, on a non-positive lengthscale, or on ``m < 0``.
            :func:`boec.versionc.n_effective` raises on the first of these for the same
            reason -- a broadcast answers a different question silently.
    """
    C = torch.as_tensor(cand, dtype=torch.double)
    if C.ndim != 2:
        raise ValueError(f"cand must be (N, d), got {tuple(C.shape)}")
    N, d = C.shape
    mu = torch.as_tensor(mean, dtype=torch.double).reshape(-1)
    Xd = torch.as_tensor(X1, dtype=torch.double).reshape(-1, d)
    ls = torch.as_tensor(lengthscales, dtype=torch.double).reshape(-1)

    if mu.numel() != N:
        raise ValueError(
            f"width mismatch: cand has N={N} rows, mean has {mu.numel()} -- broadcasting "
            "these would answer a different question silently")
    if ls.numel() != d:
        raise ValueError(
            f"width mismatch: cand has d={d}, lengthscales has {ls.numel()}")
    if bool((ls <= 0).any()):
        raise ValueError(f"non-positive lengthscale in {ls.tolist()}")
    if m < 0:
        raise ValueError(f"m must be non-negative, got {m}")

    x_hat = C[int(mu.argmax())]

    # Step 2 -- the ARD ball. `x_hat` is itself a candidate and sits at distance 0, so the
    # ball is never empty; `n_in_ball >= 1` always.
    in_ball = (((C - x_hat) / ls).pow(2).sum(dim=1).sqrt() <= radius).nonzero().reshape(-1)
    n_in_ball = int(in_ball.numel())

    diag = {"x_hat": x_hat.tolist(), "n_in_ball": n_in_ball, "m_requested": int(m),
            "radius": float(radius)}

    if m == 0:
        diag.update({"m_placed": 0, "m_local_short": False})
        return C.new_zeros((0, d)), diag

    k = min(int(m), n_in_ball)
    pool = C[in_ball]

    # Step 3 -- greedy maximin in the ARD metric, seeded by the plate-1 design so the local
    # wells are far from wells that already exist rather than merely far from each other.
    scaled_pool = pool / ls
    best = (scaled_pool.unsqueeze(1) - (Xd / ls).unsqueeze(0)).pow(2).sum(dim=2).sqrt()
    dmin = best.min(dim=1).values if Xd.shape[0] else torch.full((pool.shape[0],),
                                                                 float("inf"),
                                                                 dtype=torch.double)
    chosen: list[int] = []
    for _ in range(k):
        # Step 4 -- lowest index wins a tie. `argmax` on a tensor returns the first maximal
        # index already, but the intent is registered so it is asserted rather than assumed.
        j = int(torch.argmax(dmin))
        chosen.append(j)
        # Picking a point sets its own distance to 0, so it cannot be chosen twice.
        dnew = (scaled_pool - scaled_pool[j]).pow(2).sum(dim=1).sqrt()
        dmin = torch.minimum(dmin, dnew)

    X_loc = pool[torch.tensor(chosen, dtype=torch.long)]
    diag.update({"m_placed": int(X_loc.shape[0]),
                 "m_local_short": bool(n_in_ball < int(m))})
    return X_loc, diag


def classify_regime(tau: float, tau_max_by_gamma: dict, prevalence: float,
                    nonempty_rate: float, boundary_frac: float,
                    structural_exception: str | None = None) -> tuple[str, str]:
    """The pre-run regime class for one planned condition, and the reason for it.

    Registered in ``docs/SPADE-FINAL-SPEC.md`` §5.1. Returns one of ``TARGET``,
    ``ROBUSTNESS``, ``EXCEPTION``, ``INFEASIBLE`` with a human-readable reason that goes
    into ``results/final-spade-feasibility.json`` verbatim.

    **This function takes no arm outcome of any kind**, and a test asserts that of its
    signature. The fraud it exists to prevent is relabelling a cell ``TARGET`` after its
    results are known, at which point ``TARGET`` silently comes to mean "where SPADE won".
    Every argument is computable before a single final-study campaign runs: three from
    oracle geometry, two from the frozen 20-campaign plate-1 pilot.

    **The order of the branches is itself registered**, and only one ordering is honest:

    1. ``INFEASIBLE`` first, because an above-ceiling threshold is a property of the
       *threshold*. §4.5: no method certifies above ``tau_max`` at any budget, ever. Scoring
       an arm there and calling the zero a failure is the error the whole check exists to
       stop.
    2. ``EXCEPTION`` **before** ``TARGET``, so a condition pre-declared as structurally
       unfavourable cannot be promoted once its pilot numbers look agreeable. §41 records
       ackley certifying nothing in 1,200 campaigns; it is declared in advance and stays
       declared.
    3. ``TARGET`` only on the full conjunction.
    4. ``ROBUSTNESS`` otherwise -- feasible and informative, but it may not carry the
       central claim.

    Args:
        tau: the raw threshold.
        tau_max_by_gamma: ``{gamma: tau_max}`` over the **primary** gammas. Feasibility is
            decided on the *worst* of them: gamma=0.50 gives ``tau_max`` = 1.0 exactly
            (z=0), so testing only that corner would pass every threshold, and §9.8 records
            that gamma=0.50 is clean **by construction**.
        prevalence: true fraction of the grid above ``tau``.
        nonempty_rate: pilot fraction of campaigns producing a non-empty certificate.
        boundary_frac: pilot fraction of the grid inside the straddle band after plate 1.
        structural_exception: a pre-declared reason SPADE is not expected to win here, or
            ``None``. Declaring one **after** seeing results is a protocol violation.
    """
    worst_gamma = min(tau_max_by_gamma, key=lambda g: tau_max_by_gamma[g])
    ceiling = float(tau_max_by_gamma[worst_gamma])
    if float(tau) >= ceiling:
        return ("INFEASIBLE",
                f"tau={tau:.4f} is at or above the certifiability ceiling "
                f"tau_max={ceiling:.4f} at gamma={worst_gamma}; no method certifies there "
                "at any budget, so this is a property of the threshold and not a method "
                "failure")
    if not (DEGENERATE_LO <= float(prevalence) <= DEGENERATE_HI):
        return ("INFEASIBLE",
                f"true prevalence {prevalence:.5f} is degenerate (outside "
                f"[{DEGENERATE_LO}, {DEGENERATE_HI}]); no valid non-empty certificate is "
                "meaningfully assessable")
    if structural_exception:
        return ("EXCEPTION",
                f"pre-declared structural exception: {structural_exception}")

    lo, hi = TARGET_PREVALENCE
    fails = []
    if not (lo <= float(prevalence) <= hi):
        fails.append(f"prevalence {prevalence:.4f} outside the nontrivial band [{lo}, {hi}]")
    if float(nonempty_rate) < MIN_NONEMPTY_RATE:
        fails.append(f"pilot non-empty rate {nonempty_rate:.4f} < {MIN_NONEMPTY_RATE}")
    if float(boundary_frac) < MIN_BOUNDARY_FRAC:
        fails.append(f"pilot boundary fraction {boundary_frac:.4f} < {MIN_BOUNDARY_FRAC}")

    if fails:
        return ("ROBUSTNESS", "feasible but not a target regime: " + "; ".join(fails))
    return ("TARGET",
            f"feasible (tau={tau:.4f} < tau_max={ceiling:.4f} at gamma={worst_gamma}), "
            f"prevalence {prevalence:.4f} in [{lo}, {hi}], pilot non-empty rate "
            f"{nonempty_rate:.4f}, pilot boundary fraction {boundary_frac:.4f}")


def threshold_facts(tau_frac: float, mu_max: float, sigma_rel: float, gammas,
                    truth: Tensor) -> dict:
    """Everything about one condition's threshold that is knowable before any arm runs.

    Returns ``tau_frac``, ``tau_raw``, ``tau_max_by_gamma``, ``worst_gamma``,
    ``tau_max_worst``, ``above_ceiling`` and ``true_prevalence`` -- the exact inputs
    :func:`classify_regime` consumes, plus the provenance a row needs.

    **tau is a FRACTION of ``mu_max``, never an absolute number.** §4.5 records why: an
    earlier registration of this project used absolute thresholds {0.70, 0.80, 0.85, 0.90}
    and **all four sat above the ceiling**, so every arm would have certified nothing and
    the published table would have been zeros. The re-parameterisation is not a convenience
    -- Amendment C2's algebra makes ``theta = tau_frac * mu_max`` exact for every gamma, so
    the fraction is the natural coordinate for the object.
    """
    from boec.designspace import tau_max as _tau_max

    tau_raw = float(tau_frac) * float(mu_max)
    by_gamma = {float(g): float(_tau_max(float(g), float(sigma_rel), float(mu_max)))
                for g in gammas}
    worst = min(by_gamma, key=lambda g: by_gamma[g])
    t = torch.as_tensor(truth, dtype=torch.double).reshape(-1)
    return {"tau_frac": float(tau_frac), "tau_raw": tau_raw,
            "tau_max_by_gamma": by_gamma, "worst_gamma": worst,
            "tau_max_worst": by_gamma[worst],
            "above_ceiling": bool(tau_raw >= by_gamma[worst]),
            "true_prevalence": float((t >= tau_raw).double().mean())}


#: The raw-row contract, frozen with the registration. §14 of the brief.
#:
#: **No final result claim may rely on a field that is not here**, and a test asserts the
#: required set rather than trusting the list. ``same_draw_containment`` and
#: ``crossfit_containment`` are deliberately SEPARATE columns that never collapse into one
#: ``containment``: §29.3 measured them differing by up to 3.5 points, and the protocol's
#: whole value is that the difference stays visible in every row rather than being resolved
#: once in an analysis nobody re-reads.
ROW_SCHEMA = (
    # provenance
    "study_id", "registration_commit", "code_commit", "timestamp", "git_hash",
    "environment_fingerprint",
    # condition
    "family", "dimension", "sigma", "instance_seed", "campaign_seed",
    "noise_stream_seed", "regime_class",
    # arm and budget -- wells and rounds on SEPARATE axes, spec §4.1/§4.2
    "arm", "arm_family", "total_wells", "plate1_wells", "plate2_wells",
    "confirmation_wells", "rounds", "adaptive_decisions", "model_fits", "m_local",
    "m_local_short", "n_effective",
    # threshold and assurance
    "terminal_rule", "gamma", "alpha", "tau_definition", "tau_raw",
    "tau_frac_or_quantile", "tau_max", "above_ceiling", "true_prevalence",
    # certificate -- cross-fit primary, same-draw diagnostic, denominators preserved
    "rankable", "empty_predictive_region", "nonempty_certificate", "posterior_draws",
    "selection_draws", "evaluation_draws", "draw_split_seed", "selected_quantile",
    "candidate_quantile_count", "same_draw_containment", "crossfit_containment",
    "empirical_containment", "certificate_volume",
    # regret -- BOTH rules, always, spec §7.4
    "regret_rule_a", "regret_rule_p", "oracle_best_regret",
    "identification_gap_rule_a", "identification_gap_rule_p",
    # map quality -- symmetric difference primary, AUC secondary
    "symmetric_difference_pred", "type_i_volume_pred", "type_ii_volume_pred",
    "brier", "murphy_calibration", "murphy_refinement", "auc_pred", "iou_pred",
    "false_inclusion_pred",
    # gating
    "gate_status", "exclusion_reason", "unavailable_reason",
)


def spade_plate2(adapter, cand: Tensor, X1: Tensor, theta: float, n_plate2: int, m: int,
                 lengthscales: Tensor, *, exclude: float = 0.1,
                 sigma: Tensor | None = None) -> tuple[Tensor, dict]:
    """The full plate-2 batch for ``spade_cf_m{m}``: ``m`` local wells then the rest on
    the boundary.

    **Local wells come first in the returned tensor**, so a stored ``plate2_X`` can be
    split at ``diag["m_placed"]`` without ambiguity.

    ------------------------------------------------------------------------------
    THE NESTING, AND WHY IT IS THE POINT
    ------------------------------------------------------------------------------

    The boundary remainder is chosen by the **identical** :func:`boec.lse.batch_lse` call
    ``m0`` uses, at ``q = n_plate2 - m``, and it is **not** told about the local wells.
    That is deliberate and is what the registration says: *"all remaining Plate-2 wells
    [use] exactly the same boundary-targeting rule as spade_cf_m0."*

    Because ``batch_lse`` is greedy with exclusion, a call at ``q=4`` returns precisely the
    first four picks of a call at ``q=8``. So ``m4``'s boundary wells are a **prefix** of
    ``m0``'s, the three arms are nested, and the difference between them is attributable to
    the *substituted* wells rather than to a re-planned boundary batch. Telling
    ``batch_lse`` to avoid the local wells would break that nesting and confound KF-5 with
    a second, unregistered change.

    Returns:
        ``(X2, diag)`` with ``X2`` of shape ``(n_plate2, d)``. ``diag`` carries L1's
        diagnostics plus ``n_boundary``. When the ARD ball cannot supply ``m`` wells the
        shortfall goes to the boundary rule, ``m_local_short`` is ``True``, and the budget
        is still exactly ``n_plate2`` -- an ``m8`` arm must never silently become an ``m2``.
    """
    from boec.lse import batch_lse

    mean, _sd = adapter.posterior_mean_and_sd(cand)
    X_loc, diag = local_wells(cand, mean, X1, lengthscales, m)
    n_boundary = int(n_plate2) - int(X_loc.shape[0])
    diag["n_boundary"] = n_boundary

    if n_boundary <= 0:
        return X_loc, diag

    X_bnd = batch_lse(adapter, cand, theta, n_boundary, exclude=exclude, sigma=sigma)
    if int(X_loc.shape[0]) == 0:
        return X_bnd, diag
    return torch.cat([X_loc, X_bnd]), diag


def row_above_ceiling(tau_raw: float, gamma: float, tau_max_by_gamma: dict) -> bool:
    """Is ``tau_raw`` at or above the certifiability ceiling **at this row's own gamma**?

    🔴 **REGRESSION this function replaces.** The benchmark runner originally copied a
    single condition-level ``above_ceiling`` flag onto every row regardless of that row's
    own ``gamma``. That flag is correct as a *condition*-level fact -- the feasibility
    gate computes it over the union of primary and diagnostic gammas, so it can warn that
    a threshold breaches the ceiling at the gamma=0.99 diagnostic even when it is fine at
    the primary gammas -- but wrong as a *per-row* one: a gamma=0.50 row inherited "True"
    from a threshold that only breaches the ceiling three gammas away.

    Found running C2 (hill, sigma=0.10) through the analyser: KF-9 flagged 6,600 of
    13,200 rows as above-ceiling, when only the 2,200 at ``(tau_q_p=0.10, gamma=0.99)``
    actually are. §4.5's rule -- no method certifies above ``tau_max`` at any budget, so
    this must be excluded before it is read as a method failure -- only holds if the
    exclusion is evaluated at the gamma the row was actually scored at.

    Args:
        tau_raw: the row's raw threshold.
        gamma: the row's own point-level confidence, never the condition's worst.
        tau_max_by_gamma: ``{gamma: tau_max}``, possibly JSON-round-tripped with string
            keys (a committed feasibility file always has them). Both key types are
            tried; a genuinely missing gamma raises rather than defaulting to "feasible",
            because a silent default would hide exactly this class of bug again.

    Raises:
        KeyError: if ``gamma`` (as float or as its string form) is not a key.
    """
    if gamma in tau_max_by_gamma:
        ceiling = tau_max_by_gamma[gamma]
    elif str(gamma) in tau_max_by_gamma:
        ceiling = tau_max_by_gamma[str(gamma)]
    else:
        raise KeyError(
            f"gamma={gamma} has no entry in tau_max_by_gamma "
            f"(keys: {sorted(tau_max_by_gamma)}); a missing gamma is a wiring error, not "
            "an implicit 'feasible'")
    return bool(float(tau_raw) >= float(ceiling))


def merge_condition_rows(paths) -> dict:
    """Combine multiple per-condition raw-row files into one envelope for the analyser.

    ------------------------------------------------------------------------------
    WHY THIS EXISTS
    ------------------------------------------------------------------------------

    ``scripts/analyse_final_spade_benchmark.py`` writes to three FIXED, singular paths
    (``final-spade-certificate.json``, ``-regret-pareto.json``, ``-kill-ledger.json``) --
    named that way in the frozen spec §15 because the study's kill ledger is a single
    document, not one per condition. **KF-2 needs hill and hartmann6 rows in the SAME
    analysis** to answer "does certificate validity extend beyond hill" at all; it cannot
    be answered from a hill-only file no matter how many times that file is re-analysed.

    Running the analyser once per condition's raw file therefore does not accumulate
    evidence -- it **overwrites** the previous condition's committed artefact under the
    same name, discovered running C1 immediately after C2 had already been committed
    under those exact filenames. This function is the fix: combine every completed
    condition's rows first, and analyse the union exactly once.

    ------------------------------------------------------------------------------
    WHAT IT GUARDS
    ------------------------------------------------------------------------------

    Every input file must share the same ``study_id`` and ``registration_commit``. A
    mismatch on either is refused rather than silently pooled -- combining files from two
    different studies, or a pre- and post-erratum registration, would mix incompatible
    threshold definitions into one kill ledger without any visible sign that it happened.

    Args:
        paths: condition raw-row files, in the order their rows should appear in the
            merged output. Order is preserved because some downstream diagnostics print
            "first offending row" and a stable order makes that reproducible.

    Returns:
        ``{"study_id", "registration_commit", "code_commits": [...], "rows": [...],
        "missing_mandatory_arms": {condition: [...]}, "gate_failures": [...]}`` -- shaped
        for direct use as ``analyse_final_spade_benchmark.py --file``'s input.

    Raises:
        ValueError: on an empty ``paths``, or a ``study_id``/``registration_commit``
            mismatch between files.
    """
    import json
    from pathlib import Path as _Path

    paths = list(paths)
    if not paths:
        raise ValueError("merge_condition_rows needs at least one file")

    payloads = [json.loads(_Path(p).read_text()) for p in paths]
    study_ids = {p.get("study_id") for p in payloads}
    if len(study_ids) > 1:
        raise ValueError(f"study_id mismatch across files: {sorted(study_ids)}")
    commits = {p.get("registration_commit") for p in payloads}
    if len(commits) > 1:
        raise ValueError(f"registration_commit mismatch across files: {sorted(commits)}")

    rows: list = []
    missing: dict = {}
    gate_failures: list = []
    code_commits: list = []
    for path, payload in zip(paths, payloads):
        cond = payload.get("condition") or _Path(path).stem
        rows.extend(payload.get("rows", []))
        missing[cond] = payload.get("missing_mandatory_arms", [])
        gate_failures.extend(payload.get("gate_failures", []))
        code_commits.append(payload.get("code_commit"))

    return {"study_id": study_ids.pop(), "registration_commit": commits.pop(),
            "code_commits": code_commits, "source_files": [str(p) for p in paths],
            "missing_mandatory_arms": missing, "gate_failures": gate_failures,
            "rows": rows}
