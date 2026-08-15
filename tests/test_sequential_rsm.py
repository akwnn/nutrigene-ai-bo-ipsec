"""`doe_ascent` — the classical arm allowed to walk. Prompt 1 of `docs/PROMPTS-NEXT.md`.

WHY THIS ARM HAD TO EXIST BEFORE ANY COST-CURVE CLAIM COULD STAND
------------------------------------------------------------------
The stored `doe_repeat` arm does not move its design region. After the first 20+27+1
pipeline it starts a **new independent 48-well pipeline with a fresh seed** and carries
the best forward, so at 200 wells it has explored the same neighbourhood four times.
Textbook sequential RSM does the opposite: it follows the steepest-ascent path off the
fitted surface, relocates the design centre, and rebuilds a CCD there.

Every published cost curve in this project therefore carries the concession *"biased in
favour of BO because the classical arm has no steepest ascent"*. This module removes the
bias rather than restating it. If ascent still loses, that is a result; if it wins, that
is a result. Neither was pre-written.

WHAT IS DELIBERATELY NOT TESTED HERE
--------------------------------------
Whether `doe_ascent` beats qLogEI. That is what the run is for, and a test that asserted
a direction would be a registration written after the numbers.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.diagnostics import reported_best_curve
from boec.oracles import load_ensemble
from boec.sequential_rsm import (ASCENT_RULES, ASCENT_STEP, ASCENT_STEPS, CCD_BUDGET,
                                 N_KEEP, SCREEN_BUDGET, SequentialRSMResult,
                                 rounds_for_sequential_rsm, run_sequential_rsm)
from boec.torch_oracle import BiphasicOracle

D = 6
CAP = 200


# --------------------------------------------------------------------------
# fixtures — quadratics with a stationary point we choose, so the branch under
# test is the branch that actually runs
# --------------------------------------------------------------------------
class PolyOracle:
    """``f(x) = b . (x - c) + (x - c)' A (x - c)``, noiseless unless asked otherwise.

    The point of this fixture is control over the *Hessian*: `run_sequential_rsm`
    branches on whether the fitted surface has an interior maximum, a saddle, or a
    ridge, and a fixture that cannot produce all three on demand would leave two of
    those branches untested.
    """

    def __init__(self, A: np.ndarray, b: np.ndarray, *, centre: float = 0.5,
                 sigma: float = 0.0, seed: int = 0):
        self.A, self.b, self.c = A, b, centre
        self.sigma, self._rng = sigma, np.random.default_rng(seed)
        self.n_evaluated, self.batches = 0, []

    def truth(self, X: torch.Tensor) -> torch.Tensor:
        Z = X.double().numpy() - self.c
        quad = np.einsum("ij,jk,ik->i", Z, self.A, Z)
        return torch.from_numpy((Z @ self.b + quad).reshape(-1, 1))

    def evaluate(self, X: torch.Tensor):
        self.n_evaluated += X.shape[0]
        self.batches.append(int(X.shape[0]))
        y = self.truth(X)
        if self.sigma:
            y = y + torch.from_numpy(
                self._rng.normal(0.0, self.sigma, size=(X.shape[0], 1)))
        return y, torch.full_like(y, self.sigma**2)


#: A gentle linear tilt on every factor, strictly decreasing. Two jobs: it makes the
#: screen's factor ranking deterministic (the main effect of factor ``i`` in a two-level
#: screen of a symmetric quadratic is exactly ``b_i``), and it makes the best screen run
#: the all-high corner. Without it the corners tie and which four factors survive becomes
#: a property of `argsort`'s tie-breaking.
_TILT = np.linspace(0.06, 0.01, D)


def _ramp(d: int = D) -> PolyOracle:
    """Pure first-order, so the optimum sits in a corner the screen already visits.

    Kept as a fixture because it is a real edge case rather than a convenience: when the
    screen's best run *is* the optimum, the CCD is pinned against the boundary and the
    ascent path has nowhere to go. The campaign must converge immediately rather than
    spin, and it must not claim rounds for plates it never ran.
    """
    b = np.linspace(1.0, 0.5, d)
    return PolyOracle(np.zeros((d, d)), b)


#: Where :func:`_offset_max` peaks, in every coordinate.
_PEAK = 0.90


def _offset_max(d: int = D) -> PolyOracle:
    """A peak at 0.90 that the screen's best run overshoots.

    ``f = -||x - 0.5||^2 + b.(x - 0.5)`` with ``b ~ 0.8`` puts the maximum at
    ``0.5 + b/2 = 0.90``. That is nearer the all-high corner than the screen's centre
    points, so the screen's best run is the corner and the first CCD is centred at 1.0 —
    *past* the peak. The fitted stationary point then sits below the box, and the ascent
    direction points back into the space rather than into a wall, which is the case
    `doe_repeat` can never act on.

    The ``b`` components differ in the fourth decimal so the screen's factor ranking is
    strict. The main effect of factor ``i`` on a symmetric quadratic is exactly ``b_i``,
    so ties here would make the surviving four a property of `argsort`.
    """
    b = 2.0 * (_PEAK - 0.5) + np.linspace(0.006, 0.001, d)
    return PolyOracle(-np.eye(d), b)


def _saddle(d: int = D) -> PolyOracle:
    """Up in some directions, down in others — and singular in none.

    Every factor carries curvature, with alternating sign. Zero curvature on any *kept*
    factor would make the Hessian singular, and `classify_stationary_point` would
    correctly return ``"ridge"`` rather than ``"saddle"`` — leaving this fixture unable
    to produce the case it is named for.
    """
    A = np.diag(np.array([2.0, -2.0, 1.5, -1.5, 1.0, -1.0])[:d])
    return PolyOracle(A, _TILT)


def _interior_max(d: int = D) -> PolyOracle:
    """A clean interior peak at the centre of the space."""
    return PolyOracle(-np.eye(d), np.zeros(d))


@pytest.fixture
def bounds():
    return torch.stack([torch.zeros(D, dtype=torch.double),
                        torch.ones(D, dtype=torch.double)])


# --------------------------------------------------------------------------
# (i) ascent relocates the centre when the peak is outside the CCD
# --------------------------------------------------------------------------
def test_ascent_relocates_the_centre_when_the_peak_is_outside_the_ccd(bounds):
    """The whole reason this arm exists: `doe_repeat` cannot do this.

    The screen's best run is the all-high corner, so the first CCD is centred at 1.0 and
    the peak at 0.90 sits below it. The cycle must walk back down to it.

    **The box is deliberately narrow here.** A screen visits 0, 0.5 and 1 in every
    coordinate, so no peak is ever more than 0.25 from *some* run it made — at the
    production half-width of 0.25 an exact quadratic can never place its stationary point
    outside its own box, and the branch would be untestable on a noiseless fixture. The
    mechanism is checked here; that the condition genuinely arises at the production
    width is checked against the real oracle in
    :func:`test_the_fitted_peak_really_does_escape_the_design_box_in_production`.
    """
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=0.0,
                           cap=CAP, seed=0, stage2_half_width=0.05)

    assert len(r.cycles) >= 2, "cap 200 affords more than one cycle"
    assert not r.cycles[0].stopped_at_interior_maximum, (
        "the first CCD is centred half the range from the peak with a half-width of "
        "0.25, so its stationary point cannot be inside its own box")
    assert r.cycles[0].relocated, (
        "the first cycle found no interior maximum and still did not move — that is "
        "`doe_repeat`'s behaviour, not ascent's")
    moved = torch.norm(r.cycles[1].centre - r.cycles[0].centre)
    assert float(moved) > ASCENT_STEP / 2, (
        f"the design centre moved {float(moved):.4f}, less than half one registered "
        f"ascent step ({ASCENT_STEP}) — the relocation is nominal")

    # and it moved UPHILL, which is the only direction that makes it ascent
    f0 = float(o.truth(_full(r.cycles[0].centre, r)))
    f1 = float(o.truth(_full(r.cycles[1].centre, r)))
    assert f1 > f0, f"the centre moved downhill: {f0:.4f} -> {f1:.4f}"


def test_the_fitted_peak_really_does_escape_the_design_box_in_production(bounds):
    """The companion to the test above, at the production half-width on real landscapes.

    The narrow-box test proves the ascent branch works. This proves the branch is
    *reached* by the arm as it will actually be run — that on the Hill oracles, at
    ``stage2_half_width=0.25`` and real noise, the fitted quadratic does put its optimum
    outside the region it was fitted on. That escape is the published failure mode E4
    reports as a distribution; here it is the trigger for walking.

    Without this, the narrow box would be a special case dressed as a mechanism.
    """
    escaped = 0
    for inst in load_ensemble(dim=D)[:6]:
        o = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
        r = run_sequential_rsm(o, bounds, truth=o.truth,
                               optimum_value=float(inst.optimum_value),
                               cap=CAP, seed=0)
        escaped += sum(not c.stopped_at_interior_maximum for c in r.cycles)
    assert escaped > 0, (
        "on six real landscapes at the production half-width, every single cycle found "
        "its optimum inside its own design box — the ascent branch never runs, and this "
        "arm is `doe_repeat` with extra steps")


def test_the_ascent_reference_is_the_centre_replicate_mean(bounds):
    """Regression. The reference decides whether the design ever moves.

    The first version compared each path point to ``Yc.max()`` — the best of 27 *noisy*
    CCD readings. That is an inflated order statistic: on real landscapes at
    sigma_rel=0.25 it sits 0.22 to 0.60 above the centre estimate, so no single noisy
    path point could ever beat it, no cycle ever relocated, and the arm degenerated into
    `doe_repeat` running one pipeline. Every campaign came back with exactly one cycle.

    The reference must be the CCD's own centre replicates, recomputed here from the
    visit log rather than trusted from the field.
    """
    o = BiphasicOracle(load_ensemble(dim=D)[0], sigma_rel=0.25, seed=0)
    r = run_sequential_rsm(o, bounds, truth=o.truth,
                           optimum_value=float(load_ensemble(dim=D)[0].optimum_value),
                           cap=CAP, seed=0)
    kept = list(r.kept_factors)
    # Slice the visit log by cycle rather than searching it for the centre coordinates:
    # when the best screen run is itself a centre point, the screen's own 4 centre runs
    # sit at exactly the same place and a coordinate search picks those up instead.
    offset = SCREEN_BUDGET
    for c in r.cycles:
        ccd_Y = r.Y_visited[offset:offset + CCD_BUDGET]
        ccd_X = r.X_visited[offset:offset + CCD_BUDGET]
        offset += c.evaluations

        at_centre = (ccd_X[:, kept] - c.centre.reshape(1, -1)).abs().max(dim=1).values
        reps = ccd_Y[at_centre < 1e-9]
        assert reps.numel() == 3, (
            f"found {reps.numel()} centre runs in this cycle's CCD; the design carries "
            "exactly 3 and they are what the ascent references")
        assert abs(c.centre_response - float(reps.double().mean())) < 1e-9, (
            "centre_response is not the mean of this cycle's CCD centre replicates")
        assert c.centre_response < float(ccd_Y.max()), (
            "the reference equals the best reading in the CCD, which is the "
            "order-statistic bug this test exists for")


def test_on_real_noisy_landscapes_the_design_actually_relocates(bounds):
    """The behavioural half of the regression above.

    An ascent arm that never walks is not an ascent arm, and the concession it exists to
    retire would still stand. Asserted as *some* relocation across six landscapes rather
    than a rate, because how often steepest ascent walks under noise is a **result** of
    this study and must not be pinned by a test.
    """
    cycles, relocations = [], 0
    for inst in load_ensemble(dim=D)[:6]:
        o = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
        r = run_sequential_rsm(o, bounds, truth=o.truth,
                               optimum_value=float(inst.optimum_value), cap=CAP, seed=0)
        cycles.append(len(r.cycles))
        relocations += sum(c.relocated for c in r.cycles)
    assert relocations > 0, (
        "no cycle relocated on any of six real landscapes — the design never moves and "
        "this arm is `doe_repeat` with extra bookkeeping")
    assert max(cycles) > 1, (
        f"every campaign stopped after one cycle (cycle counts {cycles}); the ascent "
        "loop is not running")


def test_the_two_registered_ascent_rules_give_materially_different_campaigns(bounds):
    """If they agreed, running and reporting both would be theatre.

    They do not: `first_decline` reads a single noisy point at step one and usually stops
    there, so it relocates far less often than `path_argmax`. Which is the honest reason
    the primary had to be chosen and declared rather than silently taken.
    """
    stats = {}
    for rule in ASCENT_RULES:
        cycles, reloc = [], 0
        for inst in load_ensemble(dim=D)[:6]:
            o = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
            r = run_sequential_rsm(o, bounds, truth=o.truth,
                                   optimum_value=float(inst.optimum_value),
                                   cap=CAP, seed=0, ascent_rule=rule)
            assert r.ascent_rule == rule
            cycles.append(len(r.cycles))
            reloc += sum(c.relocated for c in r.cycles)
        stats[rule] = (sum(cycles), reloc)

    assert stats["path_argmax"][1] > stats["first_decline"][1], (
        f"path_argmax relocated {stats['path_argmax'][1]} times and first_decline "
        f"{stats['first_decline'][1]}; if the literal rule walks as often, the primary "
        "did not need choosing and the module docstring is overstating the problem")


def test_an_unregistered_ascent_rule_raises_rather_than_defaulting(bounds):
    """Silently falling back would file a campaign under a policy it did not run."""
    o = _offset_max()
    with pytest.raises(ValueError, match="not registered"):
        run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=0.0, cap=CAP,
                           seed=0, ascent_rule="steepest")


def _full(x_kept: torch.Tensor, r: SequentialRSMResult) -> torch.Tensor:
    """Put a kept-factor point back into the full space at the campaign's held levels."""
    full = torch.tensor([r.dropped_held_at.get(i, 0.0) for i in range(D)],
                        dtype=torch.double)
    full[list(r.kept_factors)] = x_kept.double().reshape(-1)
    return full.unsqueeze(0)


# --------------------------------------------------------------------------
# (ii) a saddle is not an interior maximum
# --------------------------------------------------------------------------
def test_a_saddle_is_never_confirmed_as_an_interior_maximum(bounds):
    """Solving ``Hx = -b`` on a saddle returns a point. Believing it is the failure.

    A saddle has a stationary point that is a *minimum* along at least one eigenvector.
    Treating it as the optimum and stopping is the classic RSM error, and it is exactly
    what `classify_stationary_point` exists to prevent.
    """
    o = _saddle()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    saddles = [c for c in r.cycles if c.stationary_kind == "saddle"]
    assert saddles, "the saddle fixture produced no saddle — the test is vacuous"
    for c in saddles:
        assert not c.stopped_at_interior_maximum, (
            f"cycle centred at {c.centre.tolist()} classified '{c.stationary_kind}' "
            "and was still treated as a confirmed interior maximum")


def test_an_interior_maximum_is_recognised_so_the_saddle_test_is_not_vacuous(bounds):
    """Guards the test above: if nothing is ever an interior maximum, it proves nothing."""
    o = _interior_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=0.0,
                           cap=CAP, seed=0)
    kinds = {c.stationary_kind for c in r.cycles}
    assert "maximum" in kinds, f"no cycle found an interior maximum; saw {kinds}"


# --------------------------------------------------------------------------
# (iii) the budget stops the pipeline; a partial CCD is not the method
# --------------------------------------------------------------------------
def test_a_budget_too_small_for_another_ccd_stops_rather_than_truncating(bounds):
    """Q52 §2's rule for `doe_repeat`, applied here: leftover wells go unspent.

    Spending 10 of the 27 wells a CCD needs does not produce a fitted surface; it
    produces a rank-deficient design and a campaign that reports a budget it did not
    really use.
    """
    o = _offset_max()
    cycle = CCD_BUDGET + ASCENT_STEPS + 1
    cap = SCREEN_BUDGET + cycle + 10          # room for exactly one cycle, 10 spare
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=cap, seed=0)

    assert len(r.cycles) == 1, f"{cap} wells afford one cycle, ran {len(r.cycles)}"
    assert r.evaluations_spent <= cap
    assert cap - r.evaluations_spent >= 10, (
        "the leftover wells were spent on something; a partial CCD is not the method")
    assert o.n_evaluated == r.evaluations_spent, (
        f"the arm reports {r.evaluations_spent} wells but the oracle handed out "
        f"{o.n_evaluated} — evaluations must be wells actually run")


def test_a_budget_too_small_for_even_one_cycle_raises(bounds):
    """Silently returning a screen-only campaign would report DoE numbers for no DoE."""
    o = _offset_max()
    with pytest.raises(ValueError, match="cannot fund"):
        run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=SCREEN_BUDGET + 5, seed=0)


# --------------------------------------------------------------------------
# (iv) rule A is not oracle-best
# --------------------------------------------------------------------------
def test_rule_a_and_oracle_best_differ_on_a_noisy_fixture(bounds):
    """D20's error, blocked on the new arm before it can ship a number.

    Oracle-best maximises the noiseless value over the visited set; rule A must first
    *identify* the winner from noisy readings. Oracle-best can therefore never carry
    more regret, and on a noisy landscape the two must actually differ — otherwise the
    new arm has quietly been scored on the flattering rule.
    """
    ob, ra = [], []
    for inst in load_ensemble(dim=D)[:4]:
        for seed in (0, 1):
            o = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
            r = run_sequential_rsm(o, bounds, truth=o.truth,
                                   optimum_value=float(inst.optimum_value),
                                   cap=CAP, seed=seed)
            last = r.checkpoints[-1]
            ob.append(r.oracle_best[last])
            ra.append(r.rule_a[last])

    ob, ra = np.array(ob), np.array(ra)
    assert np.all(ra >= ob - 1e-12), (
        "rule A came out better than oracle-best somewhere, which is impossible: "
        "they maximise over the same visited points and only rule A must identify it")
    assert (np.abs(ra - ob) > 1e-9).sum() >= len(ra) // 2, (
        "rule A and oracle-best agree almost everywhere on a noisy landscape, which "
        "means one of them is not computing what it claims")


def test_rule_a_is_computed_from_the_observed_argmax_not_the_running_true_best(bounds):
    """Recomputes rule A independently from the stored visit log."""
    o = BiphasicOracle(load_ensemble(dim=D)[0], sigma_rel=0.25, seed=0)
    opt = float(load_ensemble(dim=D)[0].optimum_value)
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=opt,
                           cap=CAP, seed=0)
    last = r.checkpoints[-1]
    want = opt - float(reported_best_curve(o.truth(r.X_visited), r.Y_visited)[-1])
    assert abs(r.rule_a[last] - want) < 1e-12


# --------------------------------------------------------------------------
# (v) the rounds formula matches the registered batching rule
# --------------------------------------------------------------------------
def test_the_rounds_formula_matches_the_registered_batching_rule(bounds):
    """Registered BEFORE the run: screen = 1 round; each CCD = 1; each ascent batch = 1.

    The ascent path and that cycle's confirmation plate **together**, because both are
    computed from the same fitted CCD and a lab would not wait a cycle to run one well.
    So a campaign of ``k`` cycles costs ``1 + 2k`` rounds, and nothing about the measured
    values may change that count.
    """
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    for k, ckpt in enumerate(r.checkpoints, start=1):
        assert r.rounds[ckpt] == 1 + 2 * k, (
            f"checkpoint {ckpt} is the end of cycle {k} and should cost {1 + 2*k} "
            f"rounds, got {r.rounds[ckpt]}")
        assert rounds_for_sequential_rsm(k) == r.rounds[ckpt], (
            "the free function and the campaign disagree about rounds, so a report "
            "built from either one is unverifiable against the other")


def test_the_batches_the_oracle_saw_match_the_rounds_that_were_claimed(bounds):
    """The strongest form of (v): rounds are counted against real plating events.

    A formula can be right about a campaign that never happened. This checks the arm
    actually handed the oracle one batch per claimed round.
    """
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    assert len(o.batches) == r.rounds[r.checkpoints[-1]], (
        f"claimed {r.rounds[r.checkpoints[-1]]} rounds but plated {len(o.batches)} "
        f"batches of sizes {o.batches}")
    assert o.batches[0] == SCREEN_BUDGET
    for k in range(len(r.cycles)):
        assert o.batches[1 + 2 * k] == CCD_BUDGET


# --------------------------------------------------------------------------
# structure the registration fixes
# --------------------------------------------------------------------------
def test_it_screens_to_the_same_four_factors_the_stored_arm_keeps(bounds):
    """Same 6 -> 4 cut as `run_doe_arm`, or this is not the same classical pipeline."""
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    assert len(r.kept_factors) == N_KEEP
    assert r.kept_factors == tuple(sorted(r.kept_factors))


def test_every_checkpoint_carries_all_four_registered_scorings(bounds):
    """Prompt 1 §5: oracle-best, rule A, unconstrained and constrained recommendation."""
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    for c in r.checkpoints:
        for name in ("oracle_best", "rule_a", "rule_c_unconstrained",
                     "rule_c_constrained"):
            assert c in getattr(r, name), f"{name} missing checkpoint {c}"


def test_the_recommendation_scored_at_each_checkpoint_was_actually_measured(bounds):
    """Prompt 1 §3: no scoring a predicted peak the campaign never ran.

    The confirmation well for each cycle must appear in the visit log.
    """
    o = _offset_max()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=10.0,
                           cap=CAP, seed=0)
    for c in r.cycles:
        d = torch.norm(r.X_visited - c.confirmation_x.reshape(1, -1), dim=1)
        assert float(d.min()) < 1e-9, (
            f"the confirmation point for the cycle centred at {c.centre.tolist()} "
            "is not in the visit log — it was scored but never measured")


def test_a_boundary_optimum_parks_the_design_against_the_wall(bounds):
    """The ramp edge case: the optimum is in a corner, so ascent walks into the boundary.

    The design centre is the *midpoint of the clamped box*, so on a ramp it sits one
    half-width inside the face and the path walks outward until it clips. From then on
    the box cannot move: relocating to the boundary rebuilds the same clamped box with
    the same midpoint. The arm then re-measures that region until the budget runs out,
    which is genuinely what sequential RSM does at an edge optimum — and is worth having
    a test pin down, because it is the one case where ascent buys nothing over
    `doe_repeat`.
    """
    o = _ramp()
    r = run_sequential_rsm(o, bounds, truth=o.truth, optimum_value=float(
        o.truth(torch.ones(1, D, dtype=torch.double))), cap=CAP, seed=0)

    boxes = {tuple(c.ccd_bounds.reshape(-1).tolist()) for c in r.cycles}
    assert len(boxes) == 1, (
        f"the box moved {len(boxes)} times on a ramp; against a boundary optimum the "
        "clamped box has a fixed midpoint and cannot")
    assert all(torch.allclose(c.centre, r.cycles[0].centre) for c in r.cycles)
    assert r.unspent >= 0 and r.evaluations_spent <= CAP
    assert o.n_evaluated == r.evaluations_spent
    assert len(o.batches) == r.rounds[r.checkpoints[-1]]


def test_the_arm_is_deterministic_given_a_seed(bounds):
    """Two runs at one seed must be the same campaign, or nothing above is reproducible."""
    a = _offset_max()
    b = _offset_max()
    ra = run_sequential_rsm(a, bounds, truth=a.truth, optimum_value=10.0, cap=CAP, seed=3)
    rb = run_sequential_rsm(b, bounds, truth=b.truth, optimum_value=10.0, cap=CAP, seed=3)
    assert ra.checkpoints == rb.checkpoints
    assert torch.allclose(ra.X_visited, rb.X_visited)
    for c in ra.checkpoints:
        assert ra.rule_a[c] == rb.rule_a[c]
