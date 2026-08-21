"""P4b — does `alpha*` rank the arms backwards, and is posterior width the reason?

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before**
`scripts/run_p4b_alpha_anomaly.py` existed.

THE ANOMALY, WHICH IS MEASURED BEFORE IT IS EXPLAINED
------------------------------------------------------
At tau_frac = 0.75 the mean `alpha_star` of the three spread arms runs
`random` 0.6521 > `lhs` 0.6291 > `sobol` 0.5275, while their committed regret runs
`lhs` 0.1270 < `sobol` 0.1724 < `random` 0.2216 — very nearly the reverse. And `doe`,
whose response surface is the worst in the project at `grid_r2` = -6.19, scores
`alpha_star` = **1.0000** at tau_frac = 0.60, the maximum the statistic can take.

`test_the_registered_anomaly_is_present_in_the_committed_files` re-measures all four of
those claims from `results/k6b-conservative*.json`. It is not decoration: the anomaly is
the premise of everything else here, and a premise read once from a table and then
carried forward in prose is how a project ends up defending a number nobody rechecked.

WHAT THE BOOTSTRAP MUST RESAMPLE
---------------------------------
The unit of analysis is `(instance, seed)`, n = 50, paired — **not** the arm. A ranking
correlation over 9 arms has 9 points in it, but those 9 points are means over the same
50 units, and the sampling variability being estimated is the units'. A bootstrap that
resampled the 9 arms would be estimating the wrong thing and would also, on any resample
with duplicates, compute a Spearman coefficient over fewer than 9 distinct arms. Two
tests pin this: perfectly anti-correlated arms must return rho = -1 with a CI that does
not wander off it, and every resample must still see all 9 arms.

WHERE THE POSTERIOR WIDTH IS MEASURED
--------------------------------------
`alpha_star` is a functional of joint draws taken on K6b's 2,000-point Sobol subset —
and, for an arm that screened factors out, on that subset with the dropped coordinates
pinned (Amendment B3). The width regressed against it has to live on the same points, or
the regression relates two quantities defined on different sets.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_p4b_alpha_anomaly.py"

DIM, SIGMA = 6, 0.25
NINE = ("coord", "doe", "lhs", "qlogei", "qlogei-add", "qlogei-addonly", "qlognei",
        "random", "sobol")


def _load():
    spec = importlib.util.spec_from_file_location("p4b_alpha_anomaly", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def p4b():
    return _load()


def _k6b(path: str) -> list[dict]:
    d = json.loads((ROOT / "results" / path).read_text())
    return d["rows"] if "rows" in d else d["k6b_rows"]


# --------------------------------------------------------------------------------------
# THE PREMISE
# --------------------------------------------------------------------------------------

def test_the_registered_anomaly_is_present_in_the_committed_files():
    """All four registered numbers, re-measured rather than quoted."""
    rows = _k6b("k6b-conservative.json") + _k6b("k6b-conservative-spread.json")

    def mean_alpha(arm: str, tf: float) -> float:
        v = [r["alpha_star"] for r in rows if r["arm"] == arm and r["tau_frac"] == tf]
        assert len(v) == 50, f"{arm} @ {tf}: {len(v)} rows, expected 50"
        return float(np.mean(v))

    a_random, a_lhs, a_sobol = (mean_alpha(a, 0.75) for a in ("random", "lhs", "sobol"))
    assert round(a_random, 4) == 0.6521
    assert round(a_lhs, 4) == 0.6291
    assert round(a_sobol, 4) == 0.5275
    assert a_random > a_lhs > a_sobol, "alpha* no longer ranks random > lhs > sobol"
    assert round(mean_alpha("doe", 0.60), 4) == 1.0000

    e2 = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    def mean_regret(arm: str) -> float:
        v = [r["regret"] for r in e2 if r["arm"] == arm and r["dim"] == DIM
             and abs(r["sigma"] - SIGMA) < 1e-12]
        assert len(v) == 50
        return float(np.mean(v))

    r_lhs, r_sobol, r_random = (mean_regret(a) for a in ("lhs", "sobol", "random"))
    assert round(r_lhs, 4) == 0.1270
    assert round(r_sobol, 4) == 0.1724
    assert round(r_random, 4) == 0.2216
    assert r_lhs < r_sobol < r_random, "regret no longer ranks lhs < sobol < random"


# --------------------------------------------------------------------------------------
# THE BOOTSTRAP RESAMPLES UNITS, NOT ARMS
# --------------------------------------------------------------------------------------

def _synthetic(sign: int, n_instances: int = 25) -> dict[str, dict[tuple[str, int], tuple]]:
    """``arm -> unit -> (alpha_star, regret)`` with a ranking fixed by construction.

    Shaped like the real design — 25 instances x 2 seeds — so the n=25 collapse has
    something to collapse. A fixture of 50 singly-seeded instances would leave
    `instance_level` a no-op and the dual-unit tests would pass while testing nothing.
    """
    rng = np.random.default_rng(7)
    out = {}
    for k, arm in enumerate(NINE):
        out[arm] = {}
        for u in range(n_instances):
            for s in (0, 1):
                regret = 0.1 + 0.01 * k + 0.001 * rng.standard_normal()
                out[arm][("i%02d" % u, s)] = (sign * regret, regret)
    return out


def test_perfectly_anticorrelated_arms_give_rho_minus_one(p4b):
    res = p4b.spearman_across_arms(_synthetic(-1))
    assert res["rho"] == -1.0
    assert res["ci_hi"] <= -0.9, res
    assert res["n_arms"] == 9


def test_perfectly_correlated_arms_give_rho_plus_one(p4b):
    res = p4b.spearman_across_arms(_synthetic(+1))
    assert res["rho"] == 1.0
    assert res["ci_lo"] >= 0.9, res


def test_every_resample_still_sees_all_nine_arms(p4b):
    """Resampling units may never reduce the number of arms the coefficient is taken over."""
    res = p4b.spearman_across_arms(_synthetic(-1))
    assert res["n_boot"] == 4000
    assert res["n_arms_per_resample"] == 9


def test_the_bootstrap_is_reproducible(p4b):
    """`default_rng(0)`, so two calls on the same data are identical."""
    data = _synthetic(-1)
    a, b = p4b.spearman_across_arms(data), p4b.spearman_across_arms(data)
    assert a == b


def test_resampling_units_moves_the_ci_when_units_disagree(p4b):
    """A degenerate CI on noisy, weakly-ordered data would mean units are not resampled."""
    rng = np.random.default_rng(3)
    data = {arm: {("i%02d" % u, 0): (float(rng.standard_normal()),
                                     float(rng.standard_normal()))
                  for u in range(50)} for arm in NINE}
    res = p4b.spearman_across_arms(data)
    assert res["ci_hi"] - res["ci_lo"] > 0.1, res
    assert res["ci_lo"] <= res["rho"] <= res["ci_hi"]


# --------------------------------------------------------------------------------------
# THE WIDTH IS MEASURED WHERE alpha* WAS
# --------------------------------------------------------------------------------------

@pytest.mark.slow
def test_posterior_sd_is_measured_on_the_arms_own_active_subspace(p4b):
    """For `doe`, the evaluation points must be pinned bitwise at `dropped_held_at`."""
    from boec.norms import sobol_grid
    from boec.replay import regenerate

    e2 = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    key = sorted({(r["instance"], int(r["seed"])) for r in e2
                  if r["arm"] == "doe" and r["dim"] == DIM
                  and abs(r["sigma"] - SIGMA) < 1e-12})[0]
    rec = regenerate(key[0], DIM, SIGMA, key[1], "doe")
    X_sub = sobol_grid(DIM, p4b.SUBSET_N, seed=p4b.GRID_SEED)

    X_eval = p4b.active_subspace_grid(rec, X_sub)
    for j, v in rec.dropped_held_at.items():
        assert bool((X_eval[:, int(j)] == v).all()), f"axis {j} not pinned at {v}"
    for j in rec.kept_factors:
        assert bool((X_eval[:, int(j)] == X_sub[:, int(j)]).all()), f"axis {j} moved"


def test_an_all_axes_arm_is_scored_on_the_unpinned_grid(p4b):
    """`lhs` varies every factor, so Amendment B3's pin must not fire for it."""
    import torch

    from boec.norms import sobol_grid
    from boec.replay import CampaignRecord

    X_sub = sobol_grid(DIM, p4b.SUBSET_N, seed=p4b.GRID_SEED)
    rec = CampaignRecord(X=torch.zeros(1, DIM, dtype=torch.double),
                         Y=torch.zeros(1, 1, dtype=torch.double),
                         Yvar=torch.ones(1, 1, dtype=torch.double),
                         instance="x", dim=DIM, sigma=SIGMA, seed=0, arm="lhs",
                         regret=0.0, optimum_value=1.0)
    assert torch.equal(p4b.active_subspace_grid(rec, X_sub), X_sub)


# --------------------------------------------------------------------------------------
# NINE ARMS, NOT EIGHT
# --------------------------------------------------------------------------------------

def test_the_ranking_includes_coord_and_every_spade_arm(p4b):
    """The ranking has been silently too narrow twice, in two different directions.

    P4 exists because `coord` was missing and it was 8 arms wide. The SPADE gap made it
    9 when `alpha*` IS SPADE's own statistic and every Version B arm was absent. Both
    are pinned here: nine gated arms plus the three ungatable ones, twelve ranked, and
    `plate1_only` scored beside them without a thirteenth vote.
    """
    assert set(NINE) <= set(p4b.RANKING_ARMS)
    assert set(p4b.UNGATABLE) <= set(p4b.RANKING_ARMS)
    assert len(p4b.RANKING_ARMS) == 12
    assert len(set(p4b.RANKING_ARMS)) == 12, "an arm is listed twice"
    assert "plate1_only" in p4b.SCORED_ARMS and "plate1_only" not in p4b.RANKING_ARMS


# --------------------------------------------------------------------------------------
# AMENDMENT F1 — THE SPEARMAN CI AT BOTH UNITS, n=25 GOVERNING
# --------------------------------------------------------------------------------------
#
# The registered rule -- rho <= -0.5 with a CI excluding 0 -- is decided on the n=25 CI.
# The coefficient is taken over nine arm MEANS, so resampling changes those means and
# nothing else; the point estimate is identical at both units on a balanced design and
# only the interval moves. With nine points that interval is wide, and a conclusion that
# survives only at n=50 is not a conclusion.

def test_spearman_is_reported_at_both_units_with_n25_governing(p4b):
    res = p4b.dual_spearman(_synthetic(-1))
    assert res["governing_unit"] == "n25"
    assert res["n50"]["n_units"] == 50
    assert res["n25"]["n_units"] == 25
    assert res["n50"]["n_arms"] == res["n25"]["n_arms"] == 9
    # Arm means are unchanged by re-grouping a balanced design, so rho cannot move.
    assert res["n50"]["rho"] == res["n25"]["rho"]


def test_n50_is_anti_conservative_exactly_when_the_landscape_effect_is_real(p4b):
    """The mechanism F1 exists to correct, made visible in both directions.

    **Not** "n=25 is always wider" — that is false and this team has already measured it
    false (median CI inflation 0.9884, median ICC −0.0231, negative in 73 of 137
    contrasts, because a landscape effect cancels in a paired difference). Averaging two
    iid seeds halves each unit's variance while halving the unit count, so on pure noise
    the interval barely moves.

    What IS true is the thing the correction is for: when the two seeds of an instance
    agree, `(instance, seed)` counts 50 units where 25 exist, and n=50's interval is
    then too narrow. Both halves are pinned here so neither can be claimed loosely.
    """
    rng = np.random.default_rng(11)

    # Strong landscape effect: both seeds of an instance carry the identical value, so
    # there are genuinely 25 units and n=50 double-counts every one of them.
    shared = {arm: {u: (float(rng.standard_normal()), float(rng.standard_normal()))
                    for u in range(25)} for arm in NINE}
    clustered = {arm: {(f"i{u:02d}", s): shared[arm][u]
                       for u in range(25) for s in (0, 1)} for arm in NINE}
    res = p4b.dual_spearman(clustered)
    w50 = res["n50"]["ci_hi"] - res["n50"]["ci_lo"]
    w25 = res["n25"]["ci_hi"] - res["n25"]["ci_lo"]
    assert w50 < w25, ("n=50 must be the narrower, anti-conservative unit when the "
                       "seeds are redundant", w50, w25)

    # No landscape effect: seeds are independent draws, and the two units carry the same
    # information about the arm mean, so the intervals are comparable rather than sqrt(2)
    # apart. Pinned loosely on purpose -- the claim is "comparable", not a constant.
    indep = {arm: {(f"i{u:02d}", s): (float(rng.standard_normal()),
                                      float(rng.standard_normal()))
                   for u in range(25) for s in (0, 1)} for arm in NINE}
    res2 = p4b.dual_spearman(indep)
    r = ((res2["n25"]["ci_hi"] - res2["n25"]["ci_lo"])
         / (res2["n50"]["ci_hi"] - res2["n50"]["ci_lo"]))
    assert 0.7 < r < 1.4, r


# --------------------------------------------------------------------------------------
# AMENDMENT F2a/F2c — ERROR VOLUMES, AND THE ONE CELL WHERE alpha* AND K6 SHARE A THRESHOLD
# --------------------------------------------------------------------------------------

def test_k6_tau_matches_k6b_theta_only_at_gamma_one_half():
    """The threshold-matching fact the symmetric-difference comparison rests on.

    K6b's `theta = tau_frac * mu_max` is gamma-free -- margin 1 collapses into the
    tau-as-fraction parameterisation. K6's `tau = tau_frac * tau_max(gamma)` is not, and
    `tau_max(gamma) = mu_max * (1 - z(gamma) * sigma_rel)`. Since z(0.5) = 0 the two
    coincide at gamma = 0.50 and nowhere else, so pairing alpha* against an error volume
    at any other gamma compares two different superlevel sets.

    **Not asserted as exact equality, because they are not the same expression.** K6
    calls `tau_max(gamma, sigma_rel)` at its DEFAULT `mu_max = 1.0` and rounds to 10 dp;
    K6b multiplies by the instance's own `optimum_value`, which is 1.0 only to within
    3.331e-16 over the 25-instance ensemble (13 of 25 are exactly 1.0). So the residual
    at gamma = 0.50 is that normalisation's float error and nothing else. The test pins
    the measured SEPARATION -- ULP scale here, and larger than SESOI by more than a
    factor of six at every other gamma -- which is the property the comparison needs.
    """
    k6b = {(r["instance"], r["seed"], r["arm"], r["tau_frac"]): r
           for r in _k6b("k6b-conservative.json")}
    k6 = json.loads((ROOT / "results" / "k6-designspace.json").read_text())["rows"]
    worst = {}
    for r in k6:
        key = (r["instance"], r["seed"], r["arm"], r["tau_frac"])
        if key in k6b:
            worst[r["gamma"]] = max(worst.get(r["gamma"], 0.0),
                                    abs(r["tau"] - k6b[key]["theta"]))
    assert len(worst) == 6, worst
    assert worst[0.50] < 1e-15, worst[0.50]
    for g, w in worst.items():
        if g != 0.50:
            assert w > 0.12, (g, w)


def test_error_volumes_reproduce_the_committed_iou(p4b):
    """F2a's arithmetic, gated against the committed `iou_pred` column, not asserted.

    `implied_iou` exists ONLY for this check. It is not a new estimand and is not
    reported as one.
    """
    rows = [r for r in p4b.k6_rows() if not r["empty_pred"]
            and np.isfinite(r["iou_pred"])]
    assert len(rows) > 500, len(rows)
    worst = 0.0
    for r in rows:
        ev = p4b.error_volumes(r["vol_pred"], r["fi_pred"], r["true_frac_above_tau"])
        worst = max(worst, abs(ev["implied_iou"] - r["iou_pred"]))
    assert worst < 1e-12, worst


def test_an_empty_region_is_iou_zero_not_nan_when_the_true_set_is_not_empty():
    """`fi` and `iou` do NOT go nan together, and assuming they do has already caught
    one worker on this team. `fi` is nan whenever `D_est` is empty; `iou` is nan only
    when the UNION is empty, so an empty `D_est` against a non-empty true set is 0."""
    rows = [r for r in json.loads(
        (ROOT / "results" / "k6-designspace.json").read_text())["rows"]
        if r["empty_pred"] and r["true_frac_above_tau"] > 0]
    assert rows, "no empty-region rows against a non-empty true set to check"
    assert all(not np.isfinite(r["fi_pred"]) for r in rows)
    assert all(r["iou_pred"] == 0.0 for r in rows), (
        [r["iou_pred"] for r in rows[:5]])


def test_the_nine_arm_ranking_covers_iou_and_brier(p4b):
    """F2c: `analyse_k6.py` ranks on neither, and both are committed per row."""
    r = p4b.rank_arms(gamma=0.50, tau_frac=0.75)
    assert set(r) >= {"iou_pred", "brier_pred", "symmetric_difference",
                      "type_I_vol", "type_II_vol"}
    for metric, ranking in r.items():
        assert len(ranking) == 9, (metric, ranking)


# --------------------------------------------------------------------------------------
# A RANK CORRELATION OVER NINE POINTS HAS LEVERAGE, AND THE SIGN NEEDS WORDS
# --------------------------------------------------------------------------------------

def test_leave_one_arm_out_is_reported_for_every_arm(p4b):
    """Nine points is few enough that one arm can carry the coefficient.

    Reporting rho without the sensitivity would let a single high-leverage arm stand in
    for a ranking claim about nine. The diagnostic is cheap and it is not optional.
    """
    # Eight arms in perfect POSITIVE order, then `doe` dragged to the opposite corner:
    # the highest alpha* paired with the lowest regret. That is the shape of the real
    # data, where `doe` sits at the extreme of both axes and the other eight are nearly
    # unordered. A fixture that merely made `doe` extreme in the SAME direction as the
    # rest would create no leverage at all and the test would pass while testing nothing.
    data = _synthetic(+1)
    for u in data["doe"]:
        data["doe"][u] = (5.0, -5.0)
    res = p4b.spearman_across_arms(data)

    loo = res["rho_leave_one_arm_out"]
    assert set(loo) == set(NINE)
    assert loo["doe"] == 1.0, loo["doe"]
    assert abs(loo["doe"] - res["rho"]) > 0.1, (loo["doe"], res["rho"])
    assert all(-1.0 <= v <= 1.0 for v in loo.values())


def test_the_sign_is_spelled_out_because_regret_is_a_loss(p4b):
    """`rho <= -0.5` and "anti-correlated" do not mean the same thing for a LOSS.

    Regret is a loss, so a NEGATIVE rho between alpha* and regret means arms with a
    higher alpha* have LOWER regret -- alpha* agreeing with the validated metric, not
    opposing it. A label alone is misreadable in exactly the direction that matters, so
    the direction travels as a sentence.
    """
    agrees = p4b.spearman_across_arms(_synthetic(-1))     # alpha* = -regret
    assert agrees["rho"] == -1.0
    assert "lower" in agrees["direction_in_words"].lower()

    opposes = p4b.spearman_across_arms(_synthetic(+1))    # alpha* = +regret
    assert opposes["rho"] == 1.0
    assert "higher" in opposes["direction_in_words"].lower()
    assert agrees["direction_in_words"] != opposes["direction_in_words"]


def test_the_spread_arm_subset_is_reported_beside_the_nine(p4b):
    """The registration's anomaly is stated over three arms. It is measured over three."""
    res = p4b.spearman_across_arms(_synthetic(+1))
    assert res["rho_spread_arms_only"]["arms"] == ["lhs", "random", "sobol"]
    assert -1.0 <= res["rho_spread_arms_only"]["rho"] <= 1.0


def test_a_degenerate_correlation_reports_nan_not_significance(p4b):
    """A constant input makes Spearman undefined. The p-value must follow it to nan.

    This is not hypothetical: at tau_frac = 0.95 every arm certifies nothing, so the
    symmetric difference is identical across all nine and rho is nan. The bootstrap
    resamples are then nan too -- and `nan >= 0` is False, so a tail-mass p computed
    without a guard returns 0 and floors to 1/N_BOOT. An undefined coefficient would
    arrive in the output file wearing a significant p-value.
    """
    data = {arm: {(f"i{u:02d}", s): (1.0, float(u))
                  for u in range(25) for s in (0, 1)} for arm in NINE}
    res = p4b.spearman_across_arms(data)

    assert not np.isfinite(res["rho"])
    assert not np.isfinite(res["bootstrap_p"]), res["bootstrap_p"]
    assert res["ci_excludes_zero"] is False
    assert "undefined" in res["direction_in_words"].lower()


# --------------------------------------------------------------------------------------
# THE SPADE ARMS — alpha* IS SPADE's OWN STATISTIC
# --------------------------------------------------------------------------------------
#
# `alpha*` is the largest confidence at which a non-empty conservative estimate exists,
# and the conservative estimate IS the SPADE certificate. Testing "does alpha* reward
# not-knowing?" while omitting every Version B arm asks the question everywhere except
# where the answer decides something. The three Version B arms are UNGATABLE IN
# PRINCIPLE -- no comparator exists and none ever will -- so they carry `gated: false`
# and the reason on every row.
#
# `versionb_random` is the control the hypothesis actually wants: same 40-well plate 1,
# same budget, 8 RANDOM plate-2 wells instead of LSE-chosen. If alpha* rewards posterior
# width it should score HIGHER than `versionb` while being no better on the validated
# metrics. That is a within-design comparison, and it is sharper than a rank correlation
# over twelve arms.

def test_plate1_only_is_scored_but_never_ranked(p4b):
    """It is `lhs` to 4.44e-16 (D23.1). Ranking both double-weights one design.

    A Spearman coefficient across arms treats every arm as one point, so including the
    same 48 wells twice would give that design two votes out of thirteen.
    """
    assert "plate1_only" in p4b.SCORED_ARMS
    assert "plate1_only" not in p4b.RANKING_ARMS
    assert "lhs" in p4b.RANKING_ARMS
    assert set(p4b.RANKING_ARMS).isdisjoint({"plate1_only"})
    # And every ranking arm is scored, or the ranking would read a column that is absent.
    assert set(p4b.RANKING_ARMS) <= set(p4b.SCORED_ARMS)


def test_the_versionb_arms_declare_that_they_are_ungated(p4b):
    """Seed determinism is their only guarantee, and every table must say so."""
    assert set(p4b.UNGATABLE) == {"versionb", "versionb_random", "versionb_predictive"}
    for arm in p4b.UNGATABLE:
        assert arm in p4b.RANKING_ARMS
        assert p4b.gate_status(arm)["gated"] is False
        assert "no comparator" in p4b.gate_status(arm)["reason"].lower()
    for arm in ("lhs", "doe", "coord", "plate1_only"):
        assert p4b.gate_status(arm)["gated"] is True


def test_every_metric_declares_its_benefit_direction(p4b):
    """Raw signs are not comparable across metrics of opposite polarity.

    `alpha*` and AUC are higher-is-better; regret, Brier and every error volume are
    lower-is-better. Comparing `+0.0261 on alpha*` with `-0.0071 on Brier` as though
    both signs meant the same thing inverted two of four readings in another worker's
    audit. Every metric this runner reports carries its direction explicitly.
    """
    for metric in ("alpha_star", "auc_pred", "iou_pred"):
        assert p4b.BENEFIT_DIRECTION[metric] == "higher"
    for metric in ("regret", "brier_pred", "type_I_vol", "type_II_vol",
                   "symmetric_difference"):
        assert p4b.BENEFIT_DIRECTION[metric] == "lower"

    # The helper that turns a signed difference into "which arm is better", so no caller
    # has to remember the polarity.
    assert p4b.favours("alpha_star", +0.03) == "a"
    assert p4b.favours("alpha_star", -0.03) == "b"
    assert p4b.favours("regret", +0.03) == "b"
    assert p4b.favours("regret", -0.03) == "a"
    assert p4b.favours("brier_pred", -0.01) == "a"


def test_a_cross_metric_agreement_check_uses_direction_not_sign(p4b):
    """The exact inversion that caught the F-analysis worker.

    `+0.0261 on alpha*` and `-0.0071 on Brier` have opposite raw signs and BOTH favour
    the same arm. A checker comparing signs calls that a disagreement.
    """
    assert p4b.metrics_agree([("alpha_star", +0.0261), ("brier_pred", -0.0071)]) is True
    assert p4b.metrics_agree([("alpha_star", +0.0261), ("regret", +0.0071)]) is False
    assert p4b.metrics_agree([("regret", -0.01), ("symmetric_difference", -0.02)]) is True


def test_the_checkpoint_keeps_arms_it_already_has(p4b):
    """Adding arms must not discard the arms already computed.

    The Version B arms were added after 22 of 50 units had been scored on the original
    nine. A loader that demanded a complete arm set would have thrown all of that away.
    """
    rows = [{"instance": "i00", "seed": 0, "arm": a, "regret": 0.1,
             "mean_posterior_sd": 0.1} for a in ("lhs", "doe")]
    kept, missing = p4b.checkpoint_split(rows, [("i00", 0)], ("lhs", "doe", "versionb"))
    assert len(kept) == 2
    assert missing == {("i00", 0): ("versionb",)}


def test_the_output_declares_its_own_completeness(p4b):
    """A promoted file must say whether it is finished, not leave it to be inferred."""
    st = p4b.completeness([("i00", 0)], ("lhs", "doe"),
                          [{"instance": "i00", "seed": 0, "arm": "lhs"}])
    assert st["status"] == "PARTIAL"
    assert st["keys_present"] == 1 and st["keys_expected"] == 2
    full = p4b.completeness([("i00", 0)], ("lhs", "doe"),
                            [{"instance": "i00", "seed": 0, "arm": a}
                             for a in ("lhs", "doe")])
    assert full["status"] == "COMPLETE"
    assert full["keys_present"] == full["keys_expected"] == 2
