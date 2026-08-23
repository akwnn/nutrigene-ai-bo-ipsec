"""Rule L1 -- the frozen local-exploitation allocation for `spade_cf_m{0,4,8}`.

Registered in ``docs/SPADE-FINAL-SPEC.md`` §3.2, frozen at commit `c4f58d3`, **before this
file existed**.

------------------------------------------------------------------------------
WHY THE SIGNATURE IS THE FIRST TEST
------------------------------------------------------------------------------

L1 may not inspect plate-2 outcomes, truth at unobserved locations, final metrics, or any
competitor's output. This project already learned that a *convention* is not a guard: the
Version C detector statistics take no ``truth`` argument **architecturally**, so a scoring
function cannot be wired into the decision path by accident (``src/boec/versionc.py`` module
docstring).

L1 follows that pattern and goes one step further -- it takes **no model object at all**,
only arrays. A model carries a ``.posterior`` and therefore a route to anything the caller
has already computed; arrays carry nothing. The no-oracle-access property is then a fact
about the type signature rather than a promise in a docstring.
"""

from __future__ import annotations

import pytest
import torch

from boec.final_spade import local_wells
from boec.versionc import n_effective


def _lengthscales(d: int, value: float = 0.25) -> torch.Tensor:
    return torch.full((d,), float(value), dtype=torch.double)


def _grid_candidates(n: int, d: int, seed: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    return torch.rand(n, d, generator=g, dtype=torch.double)


def _peaked_mean(cand: torch.Tensor, peak: torch.Tensor) -> torch.Tensor:
    """A mean surface whose argmax is exactly the candidate nearest ``peak``."""
    return -((cand - peak) ** 2).sum(dim=1)


# ---------------------------------------------------------------------------
# The property the rule exists for
# ---------------------------------------------------------------------------

def test_every_local_well_lands_inside_the_ard_ball_that_defines_n_effective():
    """L1's radius is 1 because that IS ``n_effective``'s bound -- so each local well
    provably increments the statistic §9.3 identified as governing the identification gap.

    This is the whole justification for the rule. If a well can land outside the ball the
    radius is just a tuned constant and the registered rationale is false.
    """
    d = 4
    cand = _grid_candidates(2048, d, seed=1)
    peak = torch.full((d,), 0.5, dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(40, d, seed=2)
    ls = _lengthscales(d, 0.30)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=4)

    x_hat = torch.as_tensor(diag["x_hat"], dtype=torch.double)
    dist = ((X_loc - x_hat) / ls).pow(2).sum(dim=1).sqrt()
    assert bool((dist <= 1.0 + 1e-12).all()), f"a local well escaped the ball: {dist.tolist()}"


def test_local_wells_raise_n_effective_relative_to_the_plate_one_design_alone():
    """The rule's purpose, measured on the registered statistic rather than asserted."""
    d = 4
    cand = _grid_candidates(2048, d, seed=3)
    peak = torch.full((d,), 0.5, dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(40, d, seed=4)
    ls = _lengthscales(d, 0.30)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=4)
    x_hat = torch.as_tensor(diag["x_hat"], dtype=torch.double)

    before = n_effective(X1, x_hat, ls)
    after = n_effective(torch.cat([X1, X_loc]), x_hat, ls)
    assert after == before + 4, f"n_eff went {before} -> {after}, expected +4"


def test_x_hat_is_the_grid_argmax_of_the_posterior_mean():
    """A GRID argmax, not a continuous optimiser. §4.1 records that this project's one
    non-reproducible path was a post-hoc L-BFGS-B locator with 20 restarts."""
    d = 3
    cand = _grid_candidates(512, d, seed=5)
    peak = torch.tensor([0.2, 0.8, 0.4], dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(20, d, seed=6)

    _, diag = local_wells(cand, mean, X1, _lengthscales(d), m=2)

    expected = cand[int(mean.argmax())]
    assert torch.allclose(torch.as_tensor(diag["x_hat"], dtype=torch.double), expected)


# ---------------------------------------------------------------------------
# Determinism and budget
# ---------------------------------------------------------------------------

def test_the_rule_is_bitwise_deterministic():
    d = 5
    cand = _grid_candidates(1024, d, seed=7)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=8)
    ls = _lengthscales(d)

    a, da = local_wells(cand, mean, X1, ls, m=4)
    b, db = local_wells(cand, mean, X1, ls, m=4)

    assert torch.equal(a, b)
    assert da["x_hat"] == db["x_hat"]


def test_m_zero_returns_no_wells_so_m0_is_exactly_the_boundary_arm():
    """`spade_cf_m0` must be bit-identical to pure boundary allocation, or the m=0 arm is
    not the control it is registered as."""
    d = 4
    cand = _grid_candidates(512, d, seed=9)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=10)

    X_loc, diag = local_wells(cand, mean, X1, _lengthscales(d), m=0)

    assert X_loc.shape == (0, d)
    assert diag["m_local_short"] is False


def test_exactly_m_wells_are_returned_when_the_ball_is_rich_enough():
    d = 4
    cand = _grid_candidates(4096, d, seed=11)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=12)

    for m in (1, 4, 8):
        X_loc, diag = local_wells(cand, mean, X1, _lengthscales(d, 0.4), m=m)
        assert X_loc.shape == (m, d), f"m={m} gave {tuple(X_loc.shape)}"
        assert diag["m_local_short"] is False


def test_local_wells_are_distinct_points():
    """Greedy maximin must not return the same candidate twice -- a duplicated well is a
    wasted well and would silently break the equal-well budget."""
    d = 4
    cand = _grid_candidates(2048, d, seed=13)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=14)

    X_loc, _ = local_wells(cand, mean, X1, _lengthscales(d, 0.4), m=8)

    assert torch.unique(X_loc, dim=0).shape[0] == 8


# ---------------------------------------------------------------------------
# The short-ball case, recorded rather than absorbed
# ---------------------------------------------------------------------------

def test_a_ball_too_poor_to_fill_reports_short_rather_than_silently_returning_fewer():
    """§3.2 step 5. The runner falls back to the boundary rule for the remainder, and the
    row records that it happened. A silent short return would break the well budget and
    make `m4` secretly an `m2`."""
    d = 6
    cand = _grid_candidates(256, d, seed=15)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=16)
    # A tiny lengthscale makes the ARD ball almost empty at this candidate density.
    ls = _lengthscales(d, 0.01)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=8)

    assert diag["m_local_short"] is True
    assert X_loc.shape[0] < 8
    assert diag["n_in_ball"] == X_loc.shape[0]


# ---------------------------------------------------------------------------
# The architectural guard
# ---------------------------------------------------------------------------

def test_local_wells_accepts_no_truth_or_model_argument():
    """The no-oracle-access property, enforced on the signature itself.

    ``versionc``'s detector statistics use exactly this guard. A rule that *could* be handed
    truth eventually is, and the failure is silent.
    """
    import inspect

    names = set(inspect.signature(local_wells).parameters)
    for forbidden in ("truth", "model", "oracle", "orc", "y", "Y"):
        assert forbidden not in names, (
            f"L1's signature exposes {forbidden!r}; the rule must be computable from "
            "plate-1 arrays alone")


def test_a_width_mismatch_raises_rather_than_broadcasting():
    """``n_effective`` raises on this for the same reason: a broadcast answers a different
    question silently."""
    d = 4
    cand = _grid_candidates(256, d, seed=17)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(20, d, seed=18)

    with pytest.raises(ValueError, match="width|lengthscale"):
        local_wells(cand, mean, X1, _lengthscales(d + 1), m=2)


# ===========================================================================
# The pre-run regime classifier -- spec §5.1
# ===========================================================================
#
# The classifier exists to make one specific fraud impossible: relabelling a cell
# TARGET after its results are known. It therefore takes only quantities computable
# BEFORE any final-study arm runs -- geometry, prevalence, and a plate-1 pilot -- and
# it takes no arm outcome of any kind.

from boec.final_spade import classify_regime  # noqa: E402


def _feasible_kw(**over):
    kw = {"tau": 0.5, "tau_max_by_gamma": {0.50: 1.0, 0.95: 0.80},
          "prevalence": 0.30, "nonempty_rate": 0.80, "boundary_frac": 0.20,
          "structural_exception": None}
    kw.update(over)
    return kw


def test_a_threshold_above_the_ceiling_at_any_primary_gamma_is_infeasible():
    """§4.5's ceiling. No method certifies above `tau_max` at any budget, ever, so this is
    a property of the threshold and NOT a method failure."""
    cls, reason = classify_regime(**_feasible_kw(tau=0.90))
    assert cls == "INFEASIBLE"
    assert "ceiling" in reason.lower() or "tau_max" in reason.lower()


def test_infeasibility_is_decided_on_the_WORST_primary_gamma_not_the_best():
    """gamma=0.50 gives tau_max = 1.0 exactly (z=0), so testing only the easy corner would
    pass every threshold. §9.8 records that gamma=0.50 is clean BY CONSTRUCTION."""
    cls, _ = classify_regime(**_feasible_kw(tau=0.85,
                                           tau_max_by_gamma={0.50: 1.0, 0.95: 0.80}))
    assert cls == "INFEASIBLE"


def test_a_degenerate_region_is_infeasible_at_both_ends():
    for prev in (0.005, 0.995):
        cls, reason = classify_regime(**_feasible_kw(prevalence=prev))
        assert cls == "INFEASIBLE", f"prevalence {prev} should be degenerate"
        assert "degenerate" in reason.lower() or "prevalence" in reason.lower()


def test_a_feasible_nontrivial_well_bounded_cell_is_TARGET():
    cls, _ = classify_regime(**_feasible_kw())
    assert cls == "TARGET"


def test_a_predeclared_structural_exception_beats_TARGET():
    """The ordering that stops a pre-declared exception being promoted after the fact.
    §41 records ackley certifying NOTHING in 1,200 campaigns; it is declared EXCEPTION in
    advance and must stay one even if its pilot numbers look agreeable."""
    cls, reason = classify_regime(
        **_feasible_kw(structural_exception="centre-point optimum advantages classical designs"))
    assert cls == "EXCEPTION"
    assert "centre-point" in reason


def test_a_mostly_empty_certificate_cannot_be_TARGET():
    """§13.9/KF-10. If most certificates are empty the containment denominator is thin and
    the cell cannot carry the central claim."""
    cls, _ = classify_regime(**_feasible_kw(nonempty_rate=0.20))
    assert cls == "ROBUSTNESS"


def test_no_boundary_uncertainty_left_after_plate_one_cannot_be_TARGET():
    """Plate 2 exists to resolve the straddle band. If there is no band, there is nothing
    for the mechanism under test to do, and a win there would not be evidence for it."""
    cls, _ = classify_regime(**_feasible_kw(boundary_frac=0.01))
    assert cls == "ROBUSTNESS"


def test_a_region_covering_most_of_the_box_is_not_TARGET_even_though_it_is_feasible():
    """§14's reading: at gamma=0.99, tau_frac=0.60 the true set covers 0.99916 of the box,
    so certifying it is nearly free. That is the EASY corner, and calling it a target would
    flatter every arm."""
    cls, _ = classify_regime(**_feasible_kw(prevalence=0.85))
    assert cls == "ROBUSTNESS"


def test_the_classifier_accepts_no_arm_outcome():
    """The architectural guard again. A classifier that CAN see an arm's result eventually
    does, and then TARGET means 'where SPADE won'."""
    import inspect

    names = set(inspect.signature(classify_regime).parameters)
    for forbidden in ("regret", "containment", "arm", "auc", "sym_diff", "result", "rows"):
        assert forbidden not in names, f"classifier exposes {forbidden!r}"


# ===========================================================================
# Threshold derivation and prevalence -- the inputs the classifier consumes
# ===========================================================================

from boec.final_spade import ROW_SCHEMA, threshold_facts  # noqa: E402


def test_tau_is_derived_from_mu_max_and_the_fraction_never_stated_absolutely():
    """§4.5. An earlier draft of this project registered ABSOLUTE thresholds
    {0.70, 0.80, 0.85, 0.90} and all four sat above the ceiling -- every arm would have
    certified nothing and the table would have been zeros. tau is a FRACTION of mu_max."""
    truth = torch.linspace(0.0, 1.0, 1001, dtype=torch.double)
    facts = threshold_facts(tau_frac=0.60, mu_max=1.0, sigma_rel=0.25,
                            gammas=(0.50, 0.95), truth=truth)
    assert facts["tau_raw"] == pytest.approx(0.60)
    assert facts["tau_frac"] == 0.60


def test_prevalence_is_the_true_grid_fraction_at_or_above_tau():
    truth = torch.linspace(0.0, 1.0, 1001, dtype=torch.double)
    facts = threshold_facts(tau_frac=0.60, mu_max=1.0, sigma_rel=0.25,
                            gammas=(0.50, 0.95), truth=truth)
    # 401 of 1001 points sit at or above 0.60 on a uniform ramp: index 600 holds exactly
    # 0.6 (asserted below, because it is only true because linspace hits the endpoint
    # exactly), so indices 600..1000 inclusive qualify.
    #
    # 🔴 This assertion read `601 / 1001` when first written and FAILED. The test was
    # wrong and the code was right -- the same defect FINDINGS §5 records for the first
    # `tau_max` test, which hardcoded the textbook z=1.645 against a module using the exact
    # inverse-normal CDF. Recorded rather than quietly corrected.
    assert float(truth[600]) == 0.6
    assert facts["true_prevalence"] == pytest.approx(401 / 1001, abs=1e-9)


def test_tau_max_falls_as_gamma_rises_and_is_exactly_mu_max_at_gamma_half():
    """§9.8: gamma=0.50 gives z=0 so tau_max = mu_max EXACTLY. That is why the classifier
    reads the worst gamma and not this one."""
    truth = torch.linspace(0.0, 1.0, 101, dtype=torch.double)
    facts = threshold_facts(tau_frac=0.60, mu_max=1.0, sigma_rel=0.25,
                            gammas=(0.50, 0.95, 0.99), truth=truth)
    tm = facts["tau_max_by_gamma"]
    assert tm[0.50] == pytest.approx(1.0)
    assert tm[0.95] < tm[0.50]
    assert tm[0.99] < tm[0.95]


def test_above_ceiling_is_flagged_on_the_facts_not_left_to_the_caller():
    truth = torch.linspace(0.0, 1.0, 101, dtype=torch.double)
    facts = threshold_facts(tau_frac=0.95, mu_max=1.0, sigma_rel=0.25,
                            gammas=(0.50, 0.95), truth=truth)
    assert facts["above_ceiling"] is True


def test_the_row_schema_carries_every_field_the_registration_requires():
    """§14 of the brief. No final result claim may rely on a field that does not exist in
    saved raw results, so the schema is asserted rather than trusted."""
    required = {
        "study_id", "registration_commit", "code_commit", "family", "dimension", "sigma",
        "instance_seed", "campaign_seed", "arm", "arm_family", "regime_class",
        "total_wells", "plate1_wells", "plate2_wells", "rounds", "m_local",
        "terminal_rule", "gamma", "alpha", "tau_raw", "tau_max", "above_ceiling",
        "true_prevalence", "nonempty_certificate", "posterior_draws", "selection_draws",
        "evaluation_draws", "draw_split_seed", "same_draw_containment",
        "crossfit_containment", "regret_rule_a", "regret_rule_p",
        "symmetric_difference_pred", "type_i_volume_pred", "type_ii_volume_pred",
        "brier", "murphy_calibration", "murphy_refinement", "auc_pred",
        "gate_status", "git_hash",
    }
    missing = required - set(ROW_SCHEMA)
    assert not missing, f"schema is missing required fields: {sorted(missing)}"


def test_the_schema_records_crossfit_and_same_draw_as_SEPARATE_fields():
    """They must never collapse into one 'containment' column. §29.3 measured them
    differing by up to 3.5 points, and the whole point of the protocol is that the
    difference is visible in every row."""
    assert "crossfit_containment" in ROW_SCHEMA
    assert "same_draw_containment" in ROW_SCHEMA
    assert "containment" not in ROW_SCHEMA


# ===========================================================================
# Per-row `above_ceiling` -- must be evaluated at THIS row's own gamma
# ===========================================================================

from boec.final_spade import row_above_ceiling  # noqa: E402


def test_row_above_ceiling_uses_the_rows_OWN_gamma_not_the_worst_of_the_condition():
    """🔴 REGRESSION, found running C2 through the analyser: KF-9 flagged 6,600 of 13,200
    rows as above-ceiling, when only 2,200 (p=0.10, gamma=0.99 -- the registered
    DIAGNOSTIC corner) actually are.

    The benchmark runner copied a single condition-level `above_ceiling` flag onto every
    row regardless of that row's own `gamma`. That flag was computed in the feasibility
    gate over the UNION of primary and diagnostic gammas (so it could warn that a
    threshold goes above ceiling at the gamma=0.99 diagnostic even though it is fine at
    the primary gammas) -- correct as a CONDITION-level fact, wrong as a PER-ROW one: a
    gamma=0.50 row inherited "True" from a threshold that only breaches the ceiling at
    gamma=0.99.

    tau=0.8284 (hill, sigma=0.10, tau_q p=0.10): tau_max(gamma=0.50)=1.0000,
    tau_max(gamma=0.95)=0.8355, tau_max(gamma=0.99)=0.7674. Above ceiling ONLY at 0.99.
    """
    tau_max_by_gamma = {0.50: 1.0000, 0.95: 0.8355, 0.99: 0.7674}
    tau_raw = 0.8284
    assert row_above_ceiling(tau_raw, 0.50, tau_max_by_gamma) is False
    assert row_above_ceiling(tau_raw, 0.95, tau_max_by_gamma) is False
    assert row_above_ceiling(tau_raw, 0.99, tau_max_by_gamma) is True


def test_row_above_ceiling_accepts_string_keyed_gamma_dicts():
    """JSON round-trips dict keys as strings; `tau_max_by_gamma` read back from a
    committed feasibility file has string keys, and the runner must not silently miss
    a match because of that."""
    tau_max_by_gamma = {"0.5": 1.0, "0.95": 0.8355, "0.99": 0.7674}
    assert row_above_ceiling(0.8284, 0.99, tau_max_by_gamma) is True
    assert row_above_ceiling(0.8284, 0.5, tau_max_by_gamma) is False


def test_row_above_ceiling_raises_on_an_unlisted_gamma_rather_than_defaulting():
    """A missing gamma is a wiring error, not an implicit 'feasible'. Silently defaulting
    to False would hide exactly the class of bug this function exists to fix."""
    with pytest.raises(KeyError):
        row_above_ceiling(0.60, 0.777, {0.50: 1.0, 0.95: 0.8355})
