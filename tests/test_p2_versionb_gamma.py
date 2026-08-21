"""P2 — Version B on the gamma ladder, and the columns it has never had.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION", before `scripts/run_p2_versionb_gamma.py` existed.

THE DEFECTS THESE TESTS EXIST TO MAKE IMPOSSIBLE
------------------------------------------------
COVERAGE-MATRIX §3.1/§3.2 measured three of them at once, and each gets a test:

* **One gamma, and it coincides with K6's.** `run_versionb.py` computes
  `theta = tau_frac * mu_max` and carries no gamma constant, so its AUC column is
  200/200 bitwise identical to `k6-designspace.json`'s gamma=0.50 row -- because
  `tau_max(0.50, sigma) = 1.0` exactly. A ladder that re-derived tau by any other
  arithmetic than `run_k6_designspace.py`'s would not be the registered ladder, so the
  tau table is asserted against the **committed** `k6-designspace-spread.json` columns
  (D12: never against a regeneration of itself).

* **No region metric that depends on gamma at all.** `iou_pred`, `iou_latent`,
  `sup_err`, `grid_r2`, `fi_pred`, `fi_latent`, `vol_pred`, `empty_pred` are absent from
  every row of `results/versionb.json`. A scored row must carry all of them *and* keep
  `alpha_star`, `vorobev_deviation`, `ce_contain`, `ce_empirical`, `ce_vol`, `ce_empty`.

* **No gate.** `plate1_only` is `lhs` at 48 wells and the two committed columns agree to
  a worst |delta| of 4.44e-16 -- an artefact of the 20-ordering mean `run_e2.static_curve`
  takes for the spread arms, which `boec.replay.regenerate` reproduces deliberately. So
  the bar here is **exactly 0.0** and the repair for a miss is to match the arithmetic,
  never to widen the bar. `versionb`/`versionb_random`/`versionb_predictive` are
  UNGATABLE IN PRINCIPLE and every table must say so.

Two further properties are pinned because getting them wrong would produce a number that
looks like a result:

* `ce_empirical` must come from `vorobev.empirical_containment` against **truth**, not
  from `containment_probability`, which `conservative_estimate` selects on and which
  therefore cannot fall below alpha (`vorobev.py` labels it circular in its own
  docstring). A synthetic campaign where the two disagree is the test.
* `plate1_only` may never be counted as a separate arm in a ranking (D23.1) -- it *is*
  `lhs`, to 4.44e-16.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_p2_versionb_gamma.py"
ANALYSE = ROOT / "scripts" / "analyse_p2.py"
SPREAD = ROOT / "results" / "k6-designspace-spread.json"

#: The registration's own ladder. Written here, not read from the runner, so a runner
#: that quietly dropped a gamma would fail rather than agree with itself.
GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
TAU_FRACS = (0.60, 0.75, 0.85, 0.95)
ALPHAS = (0.50, 0.80, 0.95)
ARMS = ("versionb", "versionb_random", "plate1_only", "versionb_predictive")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    assert SCRIPT.exists(), f"{SCRIPT} does not exist yet"
    return _load(SCRIPT, "p2_versionb_gamma")


@pytest.fixture(scope="module")
def ana():
    assert ANALYSE.exists(), f"{ANALYSE} does not exist yet"
    return _load(ANALYSE, "analyse_p2")


@pytest.fixture(scope="module")
def spread_rows():
    assert SPREAD.exists(), f"{SPREAD} is the committed gate target and is missing"
    return json.loads(SPREAD.read_text())["rows"]


# ------------------------------------------------------------------- the tau ladder


def test_the_ladder_is_the_full_24_cell_k6_grid(mod):
    assert tuple(mod.GAMMAS) == GAMMAS
    assert tuple(mod.TAU_FRACS) == TAU_FRACS
    assert tuple(mod.ALPHAS) == ALPHAS
    assert set(mod.ARMS) == set(ARMS)
    assert len(mod.GAMMAS) * len(mod.TAU_FRACS) == 24


def test_tau_matches_the_committed_k6_column_at_every_cell(mod, spread_rows):
    """Gated against a committed file, never against a regeneration of itself (D12)."""
    committed = {(r["gamma"], r["tau_frac"]): (r["tau"], r["tau_max"])
                 for r in spread_rows}
    assert len(committed) == 24, f"expected 24 committed cells, got {len(committed)}"
    for gamma in GAMMAS:
        for tf in TAU_FRACS:
            tau, tmax = mod.tau_for(gamma, tf, 0.25)
            ref_tau, ref_tmax = committed[(gamma, tf)]
            assert tmax == ref_tmax, f"tau_max at gamma={gamma}: {tmax} != {ref_tmax}"
            assert tau == ref_tau, f"tau at ({gamma},{tf}): {tau} != {ref_tau}"


def test_gamma_050_is_the_only_cell_where_tau_is_unconstrained(mod):
    """§3.1's measured ladder: 1.0000 / 0.8689 / 0.7896 / 0.6796 / 0.5888 / 0.4184."""
    ladder = [mod.tau_for(g, 1.0, 0.25)[1] for g in GAMMAS]
    assert ladder[0] == 1.0
    assert [round(v, 4) for v in ladder] == [1.0, 0.8689, 0.7896, 0.6796, 0.5888, 0.4184]
    assert ladder == sorted(ladder, reverse=True)


# --------------------------------------------------------- the gate, and what is not


def test_plate1_only_reproduces_the_committed_lhs_regret_exactly(mod, spread_rows):
    """The only gate Version B has. Bar is 0.0; the arithmetic is matched, not the bar.

    `run_versionb.py` scores `plate1_only` with a single `scored_curve` call and misses
    the committed `lhs` column by 4.44e-16, because `run_e2.static_curve` averages 20
    orderings and the float64 mean of 20 copies of x is not bitwise x.
    """
    lhs = {(r["instance"], r["seed"]): r["regret"]
           for r in spread_rows if r["arm"] == "lhs"}
    keys = sorted(lhs)[:2]
    assert keys, "no committed lhs rows to gate against"
    for inst_id, seed in keys:
        rec = mod.plate1_only_record(inst_id, 6, 0.25, seed)
        assert rec.regret == lhs[(inst_id, seed)], (
            f"{inst_id} seed={seed}: {rec.regret!r} != committed {lhs[(inst_id, seed)]!r} "
            f"(delta {rec.regret - lhs[(inst_id, seed)]:.3e})")
        assert int(rec.X.shape[0]) == 48


def test_gate_tolerance_is_exactly_zero(mod):
    assert mod.GATE_TOL == 0.0


def test_the_three_two_plate_arms_are_declared_ungatable(mod):
    """No comparator exists and none ever will; every table must carry that."""
    assert set(mod.UNGATABLE) == {"versionb", "versionb_random", "versionb_predictive"}
    assert "plate1_only" not in mod.UNGATABLE
    assert mod.GATED_ARM == "plate1_only"
    assert "lhs" in mod.gate_note().lower()
    assert "ungatable" in mod.gate_note().lower()


def test_a_missing_comparator_raises_rather_than_passing(mod, tmp_path):
    """§3.6's defect: `committed.get(...)` returning None was a silent skip."""
    empty = tmp_path / "no-lhs.json"
    empty.write_text(json.dumps({"rows": []}))
    with pytest.raises(SystemExit):
        mod.committed_lhs_index(empty)


# ----------------------------------------------------------------- the scored row


@pytest.fixture(scope="module")
def scored(mod):
    """One synthetic campaign scored on a small grid. Shape only -- not a result."""
    return mod.score_campaign(**mod.synthetic_campaign())


def test_the_row_carries_every_column_version_b_never_had(scored):
    """§3.2's absent list, all of it, on every row."""
    missing_in_versionb = {"iou_pred", "iou_latent", "sup_err", "grid_r2",
                           "fi_pred", "fi_latent", "vol_pred", "empty_pred"}
    for row in scored:
        assert missing_in_versionb <= set(row), missing_in_versionb - set(row)


def test_the_row_keeps_every_column_version_b_did_have(scored):
    kept = {"alpha_star", "vorobev_deviation", "regret", "n_wells", "rounds"}
    for a in ALPHAS:
        kept |= {f"ce_contain_{a}", f"ce_empirical_{a}", f"ce_vol_{a}", f"ce_empty_{a}"}
    for row in scored:
        assert kept <= set(row), kept - set(row)


def test_one_row_per_gamma_tau_cell(scored):
    cells = sorted((r["gamma"], r["tau_frac"]) for r in scored)
    assert cells == sorted((g, t) for g in GAMMAS for t in TAU_FRACS)


def test_every_shared_k6_column_is_present_so_the_gate_can_be_full_width(mod, scored,
                                                                        spread_rows):
    """A gate that checks a hand-picked subset is not a gate (P1's lesson, §3.6)."""
    committed_keys = set(spread_rows[0]) - {"instance", "seed", "arm"}
    for row in scored:
        assert committed_keys <= set(row), committed_keys - set(row)
    assert committed_keys <= set(mod.GATED_COLUMNS)


# ------------------------------------------------- empirical containment, uncircled


def test_ce_empirical_is_the_non_circular_check_against_truth(mod):
    """`containment_probability` cannot fall below alpha; truth can and must be able to.

    A field whose posterior is confidently above theta everywhere, over a truth that is
    entirely below it. The model-internal number says 1.0; the honest one says False.
    """
    from boec.vorobev import conservative_estimate, containment_probability

    draws = torch.full((64, 32), 5.0, dtype=torch.double)
    truth = torch.full((32,), -5.0, dtype=torch.double)
    theta = 0.0
    ce = conservative_estimate(draws, theta, 0.95)
    assert int(ce.sum()) > 0, "the synthetic field must certify something"
    assert containment_probability(draws, ce, theta) == 1.0

    row = mod.vorobev_columns(draws, truth, theta, ALPHAS)
    assert row["ce_contain_0.95"] == 1.0
    assert row["ce_empirical_0.95"] == 0.0, "truth is below theta everywhere"
    assert row["ce_empty_0.95"] is False


def test_ce_empirical_is_nan_not_zero_when_nothing_was_certified(mod):
    """An empty set is vacuously contained; counting it would inflate the rate."""
    draws = torch.full((64, 32), -5.0, dtype=torch.double)
    truth = torch.full((32,), 5.0, dtype=torch.double)
    row = mod.vorobev_columns(draws, truth, 0.0, ALPHAS)
    assert row["ce_empty_0.95"] is True
    assert math.isnan(row["ce_empirical_0.95"])


# ------------------------------------------- Amendment F2a — the error volumes
#
# Registered at `07e98df`. Expected type I / type II error volumes replace AUC as the
# PRIMARY design-space metric (Azzimonti & Ginsbourger 2018, Table 1). AUC is invariant
# to monotone transformation, so it scores ranking and never calibration -- and mean
# `grid_r2` is negative for all eight arms, i.e. the posterior mean is a worse point
# predictor than the constant grid mean, which AUC cannot see.
#
# The reason they matter most HERE: at both ends of this gamma ladder `D_est` is empty
# or the classes are wildly imbalanced, and `iou`/`false_inclusion_rate` return `nan`
# there by design (`designspace.py`: "EMPTY IS NOT ZERO"). The error volumes stay
# defined exactly where IoU and AUC break.


def test_error_volumes_reproduce_the_committed_iou(mod, spread_rows):
    """Registered validation, re-measured against the COMMITTED column, not a rerun.

    `intersect / (vol_pred + true_frac - intersect)` is IoU by construction. If this
    identity does not hold on the committed rows then the decomposition is not the one
    `designspace.iou` computes, and the volumes are describing a different region.
    """
    worst = 0.0
    checked = negatives = 0
    for r in spread_rows:
        t1, inter, t2 = mod.error_volumes(r["vol_pred"], r["fi_pred"],
                                          r["true_frac_above_tau"])
        union = r["vol_pred"] + r["true_frac_above_tau"] - inter
        if union <= 0:                        # both sets empty: iou is nan by design
            assert math.isnan(r["iou_pred"])
            continue
        worst = max(worst, abs(inter / union - r["iou_pred"]))
        negatives += int(t1 < 0 or t2 < -1e-12 or inter < 0)
        checked += 1
    assert checked > 2000, f"only {checked} committed rows exercised"
    assert negatives == 0, f"{negatives} impossible negative volumes"
    assert worst <= 2.220446049250313e-16, f"worst |delta| vs committed iou_pred {worst:.3e}"


def test_error_volumes_are_defined_where_iou_and_fi_are_nan(mod):
    """The whole point at gamma = 0.99. Empty region: 0 false positives, all misses."""
    t1, inter, t2 = mod.error_volumes(0.0, float("nan"), 0.42)
    assert t1 == 0.0, "an empty region certifies nothing, so it cannot be wrong"
    assert inter == 0.0
    assert t2 == 0.42, "every truly-good point was missed, which is the prevalence"

    # And the complementary degenerate case: a region covering everything.
    t1, inter, t2 = mod.error_volumes(1.0, 0.58, 0.42)
    assert t1 == pytest.approx(0.58)
    assert inter == pytest.approx(0.42)
    assert t2 == pytest.approx(0.0)


def test_the_row_carries_the_amendment_f_columns(scored):
    """F2a's volumes, F2b's AUPRC, and the prevalence F4 requires beside containment."""
    needed = {"type_I_vol", "intersect", "type_II_vol",
              "type_I_vol_latent", "intersect_latent", "type_II_vol_latent",
              "auprc_pred", "auprc_latent", "true_frac_above_tau"}
    for row in scored:
        assert needed <= set(row), needed - set(row)


def test_type_ii_volume_is_never_negative_on_a_real_campaign(scored):
    for row in scored:
        assert row["type_I_vol"] >= 0.0
        assert row["intersect"] >= 0.0
        assert row["type_II_vol"] >= -1e-12, row


# ------------------------------------------------- Amendment F2b — AUPRC beside AUC


def test_auprc_matches_sklearn_average_precision(mod):
    """Not hand-rolled. `average_precision_score` is the reference implementation."""
    from sklearn.metrics import average_precision_score

    g = torch.Generator().manual_seed(3)
    p = torch.rand(500, generator=g, dtype=torch.double)
    truth = torch.rand(500, generator=torch.Generator().manual_seed(4),
                       dtype=torch.double)
    for tau in (0.2, 0.5, 0.9):
        label = (truth >= tau).double().numpy()
        assert mod.auprc(p, truth, tau) == pytest.approx(
            float(average_precision_score(label, p.numpy())), abs=1e-12)


def test_auprc_is_nan_when_one_class_is_absent(mod):
    """Same convention as `brier_and_auc`: 'undefined', never a number that averages."""
    p = torch.rand(64, generator=torch.Generator().manual_seed(5), dtype=torch.double)
    truth = torch.zeros(64, dtype=torch.double)
    assert math.isnan(mod.auprc(p, truth, 0.5)), "no positives -> undefined"
    assert math.isnan(mod.auprc(p, truth, -1.0)), "no negatives -> undefined"


def test_auprc_is_primary_under_heavy_imbalance_at_both_ends(ana):
    """Davis & Goadrich cuts both ways, and this ladder is imbalanced at both ends.

    gamma=0.99 tau_frac=0.60 leaves ~17 NEGATIVE points of 20,000; gamma=0.50
    tau_frac=0.95 leaves ~59 POSITIVE. Both are below the 1% floor.
    """
    assert ana.MINORITY_PREVALENCE_FLOOR == 0.01
    assert ana.primary_ranking_metric(0.99916) == "auprc_pred"
    assert ana.primary_ranking_metric(0.00294) == "auprc_pred"
    assert ana.primary_ranking_metric(0.73569) == "auc_pred"
    assert ana.minority_prevalence(0.99916) == pytest.approx(0.00084)
    assert ana.minority_prevalence(0.00294) == pytest.approx(0.00294)


# ------------------------------------------------------ Amendment F1 — dual-n, both


def test_pairing_at_instance_level_averages_seeds_first(ana):
    """n=25, unit `instance`. Two seeds on one landscape share the landscape."""
    rows = []
    for i in range(3):
        for seed, v in ((0, 0.2), (1, 0.4)):
            rows.append({"instance": f"i{i}", "seed": seed, "arm": "a",
                         "gamma": 0.5, "tau_frac": 0.6, "m": v + i})
            rows.append({"instance": f"i{i}", "seed": seed, "arm": "b",
                         "gamma": 0.5, "tau_frac": 0.6, "m": v})
    pa50, pb50, _ = ana.paired(rows, "a", "b", "m", 0.5, 0.6, unit="instance_seed")
    pa25, pb25, _ = ana.paired(rows, "a", "b", "m", 0.5, 0.6, unit="instance")
    assert len(pa50) == 6 and len(pa25) == 3
    # seeds averaged FIRST, then paired
    assert list(pa25) == pytest.approx([0.3, 1.3, 2.3])
    assert list(pb25) == pytest.approx([0.3, 0.3, 0.3])


def test_both_n_are_reported_and_n25_governs(ana):
    """Where they disagree n=25 governs; n=50 is reported beside it, labelled."""
    rows = []
    for i in range(25):
        for seed in (0, 1):
            rows.append({"instance": f"i{i:02d}", "seed": seed, "arm": "a",
                         "gamma": 0.5, "tau_frac": 0.6, "m": 0.03 + 0.001 * seed})
            rows.append({"instance": f"i{i:02d}", "seed": seed, "arm": "b",
                         "gamma": 0.5, "tau_frac": 0.6, "m": 0.0})
    d = ana.dual_contrast(rows, "a", "b", "m", 0.5, 0.6)
    assert d["n50"]["n"] == 50
    assert d["n25"]["n"] == 25
    assert d["governs"] == "n25"
    assert "anti-conservative" in d["n50_label"]
    assert isinstance(d["disagree"], bool)


# --------------------------------------- Amendment F4 — containment is NEVER pooled


def test_containment_is_never_pooled_across_tau_frac(ana):
    """Hard prohibition. Four thresholds on ONE posterior and ONE set of 512 draws are
    not four Bernoulli trials, so §3.7's pooled figure is WITHDRAWN, not widened."""
    rows = []
    for tf in (0.60, 0.75, 0.85, 0.95):
        for i in range(5):
            rows.append({"arm": "versionb", "gamma": 0.99, "tau_frac": tf,
                         "instance": f"i{i}", "seed": 0, "true_frac_above_tau": 0.9,
                         "ce_empty_0.5": False, "ce_empirical_0.5": 1.0,
                         "ce_vol_0.5": 0.1})
    table = ana.containment_table(rows, alphas=(0.50,))
    assert len(table) == 4, "one cell per tau_frac, never a pooled row"
    assert sorted(c["tau_frac"] for c in table) == [0.60, 0.75, 0.85, 0.95]
    assert all(c["n"] == 5 for c in table), "n is per cell, never 20"
    assert not hasattr(ana, "pooled_containment")


# ---------------------------------------------------- the containment cache is inert


def test_the_two_rho_grids_are_elementwise_equal(mod):
    """The premise of the cache: both scans visit the SAME 64 Vorob'ev quantiles.

    `alpha_star` walks `linspace(0, 1, 64)` and `conservative_estimate` walks
    `linspace(1, 0, 64)`. If those differed by even a ULP the repeated calls would not
    be repeats, and the cache would be answering a question nobody asked.
    """
    up = torch.linspace(0.0, 1.0, 64, dtype=torch.double)
    down = torch.linspace(1.0, 0.0, 64, dtype=torch.double)
    assert torch.equal(up, down.flip(0))


def test_the_containment_cache_returns_bit_identical_columns(mod):
    """Not "close". `==`, on every Vorob'ev column, at both ends of the ladder.

    A cache hit must return the float the real function computed. If this ever fails,
    the cache is producing numbers and must be deleted -- not tolerated.
    """
    import contextlib as _c

    # Centred so that most of the field clears tau: an all-empty CE would compare two
    # tables of `nan` and prove nothing about the cache.
    g = torch.Generator().manual_seed(7)
    draws = torch.randn(128, 300, generator=g, dtype=torch.double) * 0.4 + 1.0
    truth = (torch.randn(300, generator=torch.Generator().manual_seed(8),
                         dtype=torch.double) * 0.4 + 1.0)

    non_empty = 0
    for tau in (mod.tau_for(0.50, 0.60, 0.25)[0], mod.tau_for(0.99, 0.60, 0.25)[0]):
        with_cache = mod.vorobev_columns(draws, truth, tau)
        assert mod._vorobev.containment_probability.__module__ == "boec.vorobev", (
            "the cache leaked out of its `with` block")

        saved, mod._memoised_containment = mod._memoised_containment, _c.nullcontext
        try:
            without = mod.vorobev_columns(draws, truth, tau)
        finally:
            mod._memoised_containment = saved

        assert set(with_cache) == set(without)
        for k in with_cache:
            # `_delta` is the project's comparison: nan == nan, bools as bools, and the
            # bar is exactly 0.0 -- the same bar the gate uses.
            assert mod._delta(with_cache[k], without[k]) == 0.0, (
                f"tau={tau} column {k}: {with_cache[k]!r} != {without[k]!r}")
        non_empty += sum(not with_cache[f"ce_empty_{a}"] for a in ALPHAS)

    assert non_empty >= 1, "every CE was empty; the comparison exercised nothing"


# ------------------------------------------------------------- the performance trap


def test_the_20k_grid_never_goes_through_posterior_in_one_call(mod, monkeypatch):
    """0.06s at N=2,000 against 100.6s at N=20,000. `gp_adapter` chunks at 2,048."""
    from boec.designspace import POSTERIOR_CHUNK

    sizes: list[int] = []
    real = mod.build_gp

    def spy(*a, **k):
        model = real(*a, **k)

        class _Watched:
            def __getattr__(self, name):
                return getattr(model, name)

            def posterior(self, X, *aa, **kk):
                sizes.append(int(X.shape[0]))
                return model.posterior(X, *aa, **kk)

        return _Watched()

    monkeypatch.setattr(mod, "build_gp", spy)
    mod.score_campaign(**mod.synthetic_campaign(grid_n=4096, subset_n=256))
    assert sizes, "no posterior call was observed; the spy did not bind"
    assert max(sizes) <= POSTERIOR_CHUNK, (
        f"a posterior call saw {max(sizes)} rows; the joint covariance is quadratic")


# -------------------------------------------------------------- D23.1, the ranking


def test_plate1_only_is_never_a_separate_arm_in_a_ranking(ana):
    """It IS `lhs`. Both are reported; neither is double-counted."""
    assert "plate1_only" not in ana.RANKED_ARMS
    assert set(ana.RANKED_ARMS) == {"versionb", "versionb_random", "versionb_predictive"}
    assert "plate1_only" in ana.REPORTED_ARMS


def test_containment_is_reported_per_cell_with_its_own_n(ana):
    """Never averaged across cells with different n (the registration's own rule)."""
    rows = []
    for i in range(4):
        rows.append({"arm": "versionb", "gamma": 0.99, "tau_frac": 0.60,
                     "instance": f"i{i}", "seed": 0,
                     "ce_empty_0.5": False, "ce_empirical_0.5": float(i > 0)})
    for i in range(2):
        rows.append({"arm": "versionb", "gamma": 0.99, "tau_frac": 0.95,
                     "instance": f"i{i}", "seed": 0,
                     "ce_empty_0.5": False, "ce_empirical_0.5": 0.0})
    rows.append({"arm": "versionb", "gamma": 0.99, "tau_frac": 0.95,
                 "instance": "i9", "seed": 0,
                 "ce_empty_0.5": True, "ce_empirical_0.5": float("nan")})

    table = ana.containment_table(rows, alphas=(0.50,))
    by_cell = {(c["gamma"], c["tau_frac"]): c for c in table if c["alpha"] == 0.50}
    assert by_cell[(0.99, 0.60)]["n"] == 4
    assert by_cell[(0.99, 0.60)]["contained"] == 3
    assert by_cell[(0.99, 0.60)]["fraction"] == 0.75
    assert by_cell[(0.99, 0.60)]["below_nominal"] is False
    # The empty set is excluded from n, not counted as a success.
    assert by_cell[(0.99, 0.95)]["n"] == 2
    assert by_cell[(0.99, 0.95)]["fraction"] == 0.0
    assert by_cell[(0.99, 0.95)]["below_nominal"] is True


def test_a_cell_that_certified_nothing_reports_n_zero_and_no_verdict(ana):
    rows = [{"arm": "versionb", "gamma": 0.99, "tau_frac": 0.95, "instance": "i0",
             "seed": 0, "ce_empty_0.95": True, "ce_empirical_0.95": float("nan")}]
    cell = ana.containment_table(rows, alphas=(0.95,))[0]
    assert cell["n"] == 0
    assert math.isnan(cell["fraction"])
    assert cell["below_nominal"] is None, "no set certified is not a failed certificate"


# -------------------------------------------------- provenance, and what is read-only


def test_the_committed_result_files_cannot_be_written_over(mod):
    """`versionb.json` is the gate and the headline; `versionb-predictive.json` is E6's.

    `run_versionb.py` guards its own output the same way. The guard is by resolved path,
    so a relative `--out` pointing at the same file is refused too.
    """
    guarded = {p.name for p in mod.NEVER_OVERWRITE}
    assert {"versionb.json", "versionb-predictive.json", "k6-designspace-spread.json",
            "k6-designspace.json"} <= guarded
    for path in mod.NEVER_OVERWRITE:
        argv = ["run_p2_versionb_gamma.py", "--out", str(path)]
        with pytest.raises(SystemExit, match="refusing to overwrite"):
            _run_main(mod, argv)


def _run_main(mod, argv):
    import sys as _sys
    old = _sys.argv
    _sys.argv = argv
    try:
        mod.main()
    finally:
        _sys.argv = old


def test_provenance_carries_the_library_versions(mod):
    """`results/q52-budget-to-target.json` is the model: sha, dirty, time, argv, libs."""
    prov = mod._provenance(["scripts/run_p2_versionb_gamma.py"])
    assert {"git_sha", "git_dirty", "generated_at", "argv", "python", "torch",
            "botorch", "gpytorch", "numpy", "scipy"} <= set(prov)
    assert len(prov["git_sha"]) == 40
    assert prov["argv"] == ["scripts/run_p2_versionb_gamma.py"]


def test_the_config_names_the_gate_and_the_ungatable_arms(mod):
    cfg = mod._config(6, 0.25, None)
    assert cfg["gate"]["target_arm"] == "lhs"
    assert cfg["gate"]["tol"] == 0.0
    assert cfg["ungatable"] == list(mod.UNGATABLE)
    assert "ungatable" in cfg["note"].lower()
    assert cfg["tau"].startswith("tau_frac * tau_max(gamma, sigma_rel)")


def test_the_statistics_are_the_registered_ones(ana):
    assert ana.N_BOOT == 4000
    assert ana.BOOT_SEED == 0
    assert ana.SESOI == 0.02


def test_holm_is_applied_across_the_cells(ana):
    """Holm, not Bonferroni, and not raw p."""
    adj = ana.holm([0.01, 0.02, 0.03])
    assert adj == pytest.approx([0.03, 0.04, 0.04])
    assert ana.holm([]) == []
