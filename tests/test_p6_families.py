"""P6 · the family runner's contract, checked without running a single campaign.

P6 is BLOCKED on Amendment F's analysis half (F2a/F2c/F4). This file is the whole of
what can be verified before release, and it is deliberately zero-compute: no campaign is
regenerated, no GP is fitted against a real oracle, nothing here costs more than a second.

WHAT IT PINS, AND WHY EACH ONE COST SOMETHING TO LEARN
------------------------------------------------------
1. **Amendment F's columns exist from the first row written.** F2b's AUPRC is NOT
   derivable after the fact -- it needs the full ``p_pred`` vector and the truth labels
   over the 20,000-point grid, and no stored row carries either. ``results/p4-coord.json``
   is committed with 1,400 rows and no AUPRC for exactly this reason. A schema test is
   cheap; a re-run of five families is not.
2. **tau is READ from `results/p5-tau-quantile.json`, never recomputed.** The committed
   file is the registered artefact; a runner that recomputes the quantile is gating a
   regeneration against another regeneration of itself (D12).
3. **Rows carry `family` and never `instance`.** Off Hill, `replay` sets `instance` to the
   family label, so a consumer reading `instance` alone cannot tell a family from a Hill
   landscape id. The fix is that the key is not there to read.
4. **The `doe` gate is asserted BOTH ways.** `d20-rescore.json · doe_a_new` must
   reproduce AND `q42-families.json · doe_a` must be shown to differ where it differs.
   The two columns agree on 22 of 25 ackley rows and 15 of 25 hartmann6 rows at d=6
   sigma=0.25, so a gate silently pointed at the pre-D20 column would pass on most rows
   and be wrong (Erratum 4). A positive-only assertion cannot detect that.
5. **Erratum 5a: the two `nan` conditions are different and are recorded separately.**
   `fi` is `nan` when `D_est` is empty; `iou` is `nan` only when the UNION is empty. An
   empty `D_est` against a non-empty true set gives IoU = 0, not `nan`.
6. **Erratum 5b: AUPRC inverts.** gamma enters tau multiplicatively through `tau_max`, so
   high gamma means a LOW absolute threshold and a huge positive class -- and a
   positive-class AUPRC is then trivially ~1 exactly where F2b flags it as primary.
   `auprc_minority` and the AP baseline (the prevalence, not 0.5) travel on every row.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import pytest
import torch

SCRIPT = Path("scripts/run_p6_families.py")
TAU_TABLE = Path("results/p5-tau-quantile.json")
Q42 = Path("results/q42-families.json")
D20 = Path("results/d20-rescore.json")
Q59 = Path("results/q59-hartmann-no-screen.json")


@pytest.fixture(scope="module")
def p6():
    spec = importlib.util.spec_from_file_location("p6", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    # `@dataclass` resolves annotations through `sys.modules[cls.__module__]`, so a module
    # executed outside the import system must be registered before it runs or the
    # decorator raises on a None lookup. This is harness plumbing, not a design constraint.
    sys.modules["p6"] = m
    spec.loader.exec_module(m)          # must not run anything on import
    return m


class _FixedMap:
    """A posterior with values chosen by the test. No GP, no oracle, no campaign."""

    def __init__(self, mean, sd):
        self._mean = torch.as_tensor(mean, dtype=torch.double)
        self._sd = torch.as_tensor(sd, dtype=torch.double)

    def posterior_mean_and_sd(self, X):
        return self._mean, self._sd


# -- 2. tau comes from the committed table -----------------------------------------
def test_tau_is_read_from_the_committed_p5_table(p6):
    rows = json.loads(TAU_TABLE.read_text())["rows"]
    for r in rows:
        if r["family"] == "hill":
            continue
        got = p6.tau_for(r["family"], r["dim"], r["p"])
        assert got.tau == r["tau_q"], f"{r['family']} d={r['dim']} p={r['p']}"
        assert got.true_frac_above_tau == r["true_frac_above_tau"]
        assert got.sensitivity is (r["family"] == "ackley")


def test_the_runner_never_recomputes_the_quantile(p6):
    """D12 in its cheapest form: the committed table is the artefact, not a suggestion."""
    src = SCRIPT.read_text()
    for forbidden in ("np.quantile", "numpy.quantile", "torch.quantile"):
        assert forbidden not in src, (
            f"{forbidden} appears in the runner; tau must be READ from {TAU_TABLE}, "
            "which is the registered artefact, not recomputed beside it")
    # The 20,000-point Sobol grid at seed 0 is the opposite case: it is the registered
    # grid and `sobol_grid` is its canonical constructor, so building it here is correct
    # and re-deriving it any other way would be the defect. Asserted positively.
    assert "sobol_grid(" in src
    assert str(TAU_TABLE) in src


def test_tau_lookup_raises_on_a_cell_the_committed_table_does_not_carry(p6):
    with pytest.raises(KeyError):
        p6.tau_for("ackley", 6, 0.5)            # not one of the registered four
    with pytest.raises(KeyError):
        p6.tau_for("branin", 6, 0.75)


# -- 3 + 5. the row contract --------------------------------------------------------
def _row(p6, mean, sd, truth, tau, gamma=0.90, sigma_rel=0.25, sigma_add=0.01):
    grid = torch.linspace(0, 1, len(mean), dtype=torch.double).reshape(-1, 1)
    m = _FixedMap(mean, sd)
    truth = torch.as_tensor(truth, dtype=torch.double)
    sigma_pred = ((sigma_rel * m.posterior_mean_and_sd(grid)[0]).abs() ** 2
                  + sigma_add ** 2).sqrt()
    return p6.map_row(m, grid, truth, tau=tau, gamma=gamma, sigma_pred=sigma_pred,
                      active=torch.ones(1, dtype=torch.bool))


def test_map_row_carries_every_amendment_F_column(p6):
    r = _row(p6, mean=[0.2, 0.5, 0.9, 0.95], sd=[0.1] * 4,
             truth=[0.1, 0.4, 0.95, 0.99], tau=0.5)
    required = {
        "true_frac_above_tau",
        "auprc_pred", "auprc_minority_pred", "ap_baseline",
        "auprc_latent", "auprc_minority_latent",
        "type_I_vol_pred", "intersect_pred", "type_II_vol_pred",
        "type_I_vol_latent", "intersect_latent", "type_II_vol_latent",
        "empty_pred", "empty_latent", "empty_true", "empty_union_pred",
        "iou_pred", "fi_pred", "brier_pred", "auc_pred", "vol_pred",
    }
    missing = required - set(r)
    assert not missing, f"F2a/F2b columns missing from the row: {sorted(missing)}"


def test_rows_carry_family_and_never_instance(p6):
    """A consumer reading `instance` alone must be unable to confuse the two.

    Off Hill `replay` sets `CampaignRecord.instance` to the family label, so `instance`
    is ambiguous by construction. The runner does not emit it.
    """
    base = p6.row_identity(family="levy", dim=6, sigma=0.25, seed=3, arm="doe")
    assert base["family"] == "levy"
    assert "instance" not in base
    assert p6.ROW_KEY == ("family", "dim", "sigma", "seed", "arm")


def test_ackley_rows_are_flagged_as_a_declared_sensitivity(p6):
    assert p6.row_identity(family="ackley", dim=6, sigma=0.25, seed=0,
                           arm="qlogei")["sensitivity"] is True
    assert p6.row_identity(family="levy", dim=6, sigma=0.25, seed=0,
                           arm="qlogei")["sensitivity"] is False


# -- 5a. the two nan conditions are different --------------------------------------
def test_the_two_nan_conditions_are_recorded_separately(p6):
    """Erratum 5a, against Amendment F2a's own overstatement.

    An empty `D_est` against a NON-EMPTY true set: `fi` is nan (0/0 over the certified
    points), but IoU is 0.0 -- the union is not empty. F2a claimed both were nan and the
    error volumes were "defined precisely where IoU breaks"; that half was retracted.
    """
    r = _row(p6, mean=[0.0, 0.0, 0.0, 0.0], sd=[1e-9] * 4,
             truth=[0.9, 0.95, 0.99, 0.99], tau=0.5, gamma=0.99)
    assert r["empty_pred"] is True
    assert r["empty_true"] is False
    assert r["empty_union_pred"] is False
    assert math.isnan(r["fi_pred"]), "fi is nan when D_est is empty"
    assert r["iou_pred"] == 0.0, "IoU is 0, NOT nan, when the union is non-empty"
    # The error volumes are exact here, which is the half of F2a that survived.
    assert r["type_I_vol_pred"] == 0.0
    assert r["type_II_vol_pred"] == r["true_frac_above_tau"]


def test_error_volume_identity_reproduces_iou(p6):
    """F2a's derivation is checkable, not asserted -- the gate travels with the function."""
    r = _row(p6, mean=[0.2, 0.6, 0.9, 0.95], sd=[0.02] * 4,
             truth=[0.1, 0.4, 0.95, 0.99], tau=0.5, gamma=0.50)
    assert not r["empty_pred"]
    assert abs(r["implied_iou_pred"] - r["iou_pred"]) <= 2.3e-16


# -- 5b. AUPRC inverts at high gamma -----------------------------------------------
def test_auprc_minority_and_the_ap_baseline_travel_on_every_row(p6):
    """A positive-class AP is trivially ~1 when the positive class is nearly everything.

    That is the regime F2b flags as primary, so the positive-class number is exactly the
    one that cannot be read there. The complement and the baseline are what make it
    interpretable.
    """
    n = 200
    truth = torch.full((n,), 0.9, dtype=torch.double)
    truth[0] = 0.0                                    # one negative in 200
    mean = torch.full((n,), 0.9, dtype=torch.double)
    r = _row(p6, mean=mean, sd=[0.05] * n, truth=truth, tau=0.5, gamma=0.50)
    assert r["ap_baseline"] == pytest.approx(199 / 200)
    assert r["auprc_pred"] > 0.99, "positive-class AP is trivially high here"
    assert r["auprc_minority_pred"] is not None
    assert r["auprc_minority_pred"] < r["auprc_pred"]


def test_auprc_is_none_rather_than_one_when_a_class_is_absent(p6):
    r = _row(p6, mean=[0.9] * 4, sd=[0.05] * 4, truth=[0.9] * 4, tau=0.5)
    assert r["auprc_pred"] is None and r["auprc_minority_pred"] is None
    assert r["empty_true"] is False


# -- the noise ceiling stays visible ------------------------------------------------
def test_tau_above_the_predictive_ceiling_is_flagged(p6):
    """An empty region above `tau_max` is the noise floor, not the design.

    Under `tau_q` the threshold no longer moves with gamma, so a high-p cell can sit above
    the predictive ceiling. Without the flag that reads as an arm certifying nothing.
    """
    t = p6.tau_for("rosenbrock", 6, 0.01)
    assert t.tau > 0.98
    assert p6.above_ceiling(t.tau, gamma=0.99, sigma=0.25) is True
    assert p6.above_ceiling(t.tau, gamma=0.50, sigma=0.25) is False


# -- 4. the gate, both halves, with a count floor -----------------------------------
def test_doe_gates_on_d20_and_keeps_the_pre_d20_column_to_be_shown_wrong(p6):
    d20 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r
           for r in json.loads(D20.read_text())["rows"]}
    q42 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r
           for r in json.loads(Q42.read_text())["rows"]}
    for family in p6.FAMILIES:
        index, superseded, ungated = p6.build_gate_index(family, 6, 0.25)
        assert "doe" not in ungated
        n_distinguishing = 0
        for seed in range(25):
            assert index[("doe", seed)] == d20[(family, 6, 0.25, seed)]["doe_a_new"]
            assert superseded[("doe", seed)] == q42[(family, 6, 0.25, seed)]["doe_a"]
            if index[("doe", seed)] != superseded[("doe", seed)]:
                n_distinguishing += 1
        assert n_distinguishing == p6.count_distinguishing(family, 6, 0.25, "doe")
        # Recorded per family, never pooled: the count is 3/25 on ackley and 19/25 on
        # rosenbrock, so a floor that holds pooled would be vacuous on ackley.
        assert n_distinguishing >= 3, family


def test_qlogei_gates_on_q42_bo_a_and_d20_agrees_with_it(p6):
    q42 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r
           for r in json.loads(Q42.read_text())["rows"]}
    d20 = {(r["family"], r["dim"], r["sigma"], r["seed"]): r
           for r in json.loads(D20.read_text())["rows"]}
    index, _, ungated = p6.build_gate_index("levy", 6, 0.25)
    assert "qlogei" not in ungated
    for seed in range(25):
        ref = q42[("levy", 6, 0.25, seed)]["bo_a"]
        assert index[("qlogei", seed)] == ref
        assert d20[("levy", 6, 0.25, seed)]["bo_a"] == ref


def test_qlognei_is_gateable_on_hartmann6_only(p6):
    q59 = {(r["sigma"], r["seed"]): r for r in json.loads(Q59.read_text())["rows"]}
    index, _, ungated = p6.build_gate_index("hartmann6", 6, 0.25)
    assert "qlognei" not in ungated
    for seed in range(25):
        assert index[("qlognei", seed)] == q59[(0.25, seed)]["arms"]["qlognei"]["rule_a"]
    for family in ("ackley", "levy", "rosenbrock"):
        _, _, ung = p6.build_gate_index(family, 6, 0.25)
        assert "qlognei" in ung and "hartmann6" in ung["qlognei"]
    # d=8 has no q59 column either -- q59 is d=6 only.
    _, _, ung8 = p6.build_gate_index("hartmann6", 8, 0.25)
    assert "qlognei" in ung8


def test_spread_arms_are_recorded_ungatable_with_a_reason_never_skipped(p6):
    for family in p6.FAMILIES:
        _, _, ungated = p6.build_gate_index(family, 6, 0.25)
        for arm in ("lhs", "sobol", "random"):
            assert arm in ungated
            assert "ungatable" in ungated[arm].lower() or "no " in ungated[arm].lower()
            assert len(ungated[arm]) > 30, "a reason string, not a shrug"


def test_check_gate_refuses_to_score_a_campaign_it_cannot_gate(p6):
    """The §3.6 defect: `.get()` returns None, `if ref is not None` swallows it, and
    100 campaigns lose their gate with nothing in the output saying so."""
    index, superseded, ungated = p6.build_gate_index("levy", 6, 0.25)

    class _Rec:
        family, dim, sigma, seed, arm, regret = "levy", 6, 0.25, 99, "qlogei", 0.1

    with pytest.raises(p6.MissingGateTarget):
        p6.check_gate(_Rec(), index, superseded, ungated)


def test_check_gate_reports_both_halves_on_a_distinguishing_row(p6):
    index, superseded, ungated = p6.build_gate_index("rosenbrock", 6, 0.25)

    class _Rec:
        family, dim, sigma, seed, arm = "rosenbrock", 6, 0.25, 0, "doe"
        regret = index[("doe", 0)]

    v = p6.check_gate(_Rec(), index, superseded, ungated)
    assert v["gated"] is True and v["abs_delta"] == 0.0
    assert v["superseded_column"] == superseded[("doe", 0)]
    assert v["distinguishes"] is True
    assert v["superseded_abs_delta"] > 0.0


def test_an_ungatable_arm_is_recorded_rather_than_dropped(p6):
    index, superseded, ungated = p6.build_gate_index("levy", 6, 0.25)

    class _Rec:
        family, dim, sigma, seed, arm, regret = "levy", 6, 0.25, 0, "lhs", 0.1

    v = p6.check_gate(_Rec(), index, superseded, ungated)
    assert v["gated"] is False and v["abs_delta"] is None
    assert v["reason"] and "hill" in v["reason"].lower()


# -- the machine hazards, aimed at this runner specifically -------------------------
def test_every_posterior_goes_through_the_chunked_adapter(p6):
    """The 20,000-point posterior trap, which does not crash -- it STARVES.

    `model.posterior(X)` builds the JOINT covariance over all of X, so it is quadratic in
    grid size while only the per-point marginals are ever used: 0.06 s at 2,000 points and
    100.6 s at 20,000, and a 3.2 GB dense matrix. A D23 draft re-introduced it on a pinned
    grid and spent 35 minutes of uninterruptible wait for 1 min 47 s of CPU, which reads
    as "the machine is slow" rather than as a bug.

    This runner builds a NEW grid path for four families x two dimensions, which is
    exactly where the trap is invisible: the grid gets copied from an existing runner
    without copying how it is evaluated.
    """
    src = SCRIPT.read_text()
    assert ".posterior(" not in src, (
        "a raw model.posterior call builds the joint covariance over the whole grid; "
        "route it through boec.designspace.gp_adapter")
    assert "gp_adapter(" in src


def test_the_result_json_is_never_written_incrementally(p6):
    """A half-finished run must not be mistakable for a finished result.

    This box SIGKILLs workers -- three runs died with BrokenProcessPool, one losing 8
    completed campaigns. So every finished campaign is appended to a checkpoint before the
    next starts, and `results/p6-families.json` is written once, whole, by `--merge`.
    """
    src = SCRIPT.read_text()
    # Match the bare `OUT`, not `CENSUS_OUT`, which is a different file.
    writes = re.findall(r"(?<![A-Z_])OUT\.write_text\(", src)
    assert len(writes) == 1, f"OUT is written in {len(writes)} places, expected 1"
    body = src[src.index("def main("):]
    assert not re.search(r"(?<![A-Z_])OUT\.write_text\(", body), (
        "main() must not write the result JSON")
    assert "def merge(" in src and "ckpt.open(\"a\")" in src


def test_a_shrinking_merge_is_refused(p6):
    src = SCRIPT.read_text()
    assert "refusing to shrink" in src


# -- convention 1: the ranking scalar is the symmetric difference -------------------
def test_the_ranking_scalar_is_the_symmetric_difference_not_type_I(p6):
    """Type I read alone ranks SILENCE first: an empty region scores exactly 0.

    `doe` is 2nd of 8 on type I for that reason and no other, while being last of 8 on
    type II, symmetric difference, IoU and Brier.
    """
    assert p6.RANKING_SCALAR == "total_error_vol_pred"
    silent = _row(p6, mean=[0.0] * 4, sd=[1e-9] * 4, truth=[0.9, 0.95, 0.99, 0.99],
                  tau=0.5, gamma=0.99)
    assert silent["type_I_vol_pred"] == 0.0, "silence is perfect on type I alone"
    assert silent["total_error_vol_pred"] == silent["true_frac_above_tau"]
    assert silent["total_error_vol_pred"] > 0.0, "and is correctly penalised on the sum"
    good = _row(p6, mean=[0.2, 0.6, 0.9, 0.95], sd=[0.02] * 4,
                truth=[0.1, 0.4, 0.95, 0.99], tau=0.5, gamma=0.50)
    assert good["total_error_vol_pred"] < silent["total_error_vol_pred"]


# -- convention 3: flag degenerate cells, never rank them ---------------------------
def test_degenerate_cells_are_flagged_with_their_reason(p6):
    ok = _row(p6, mean=[0.2, 0.6, 0.9, 0.95], sd=[0.02] * 4,
              truth=[0.1, 0.4, 0.95, 0.99], tau=0.5, gamma=0.50)
    assert ok["degenerate"] == []

    empty = _row(p6, mean=[0.0] * 4, sd=[1e-9] * 4, truth=[0.9, 0.95, 0.99, 0.99],
                 tau=0.5, gamma=0.99)
    assert "empty_pred" in empty["degenerate"]
    assert "empty_true" not in empty["degenerate"]
    assert "empty_union_pred" not in empty["degenerate"]

    one_class = _row(p6, mean=[0.9] * 4, sd=[0.05] * 4, truth=[0.9] * 4, tau=0.5)
    assert "single_class" in one_class["degenerate"]
    assert one_class["auc_pred"] != one_class["auc_pred"]      # nan
    assert one_class["auprc_pred"] is None


# -- convention 4: campaign-level columns are declared, not inferred ----------------
def test_campaign_level_columns_are_declared_so_they_are_not_counted_row_wise(p6):
    """Erratum 6a: `grid_r2` is a campaign property repeated across 24 rows.

    A row-wise count of it inflated 50/50 into "1200/1200".
    """
    assert set(p6.CAMPAIGN_LEVEL_COLUMNS) == {"regret", "grid_r2", "sup_err",
                                              "n_active", "gate"}
    assert not set(p6.CAMPAIGN_LEVEL_COLUMNS) & set(p6.CELL_LEVEL_COLUMNS)
    for c in ("auc_pred", "iou_pred", "true_frac_above_tau", "vol_pred", "tau"):
        assert c in p6.CELL_LEVEL_COLUMNS


# -- the ceiling census, promoted to a registered secondary result -----------------
def test_gamma_half_is_clean_on_every_family_by_construction(p6):
    """z(0.50) = 0, so tau_max(0.50, sigma) = mu_max = 1.0 exactly; UnitScaled puts every
    family's optimum at 1; and the largest tau_q in the registered grid is 0.98631. So the
    headline column can never cross the ceiling on any family, at any p, at any sigma.
    """
    doc = p6.ceiling_census()
    at_half = [r for r in doc["rows"] if r["gamma"] == 0.50]
    assert at_half, "no gamma=0.50 rows"
    assert not any(r["above_ceiling"] for r in at_half)
    assert not any(r["n_landscapes_above"] for r in at_half)
    assert max(r["tau_q_max"] for r in doc["rows"]) < 1.0


def test_the_census_counts_cells_not_rows(p6):
    """Erratum 6a in a new place. Hill carries 25 landscapes per (d, p) and each external
    family carries 1, so a raw row count weights hill 25x and makes it look like an
    outlier. At the cell unit hill is THIRD of five, inside the range -- which is what
    makes 'the asymmetry is not a property of external families' true.
    """
    doc = p6.ceiling_census()
    per_cell = {r["family"]: r["n_landscapes"] for r in doc["rows"]}
    assert per_cell["hill"] == 25
    assert all(v == 1 for f, v in per_cell.items() if f != "hill")

    def rate(family, gamma=0.70, sigma=0.25):
        s = doc["summary"][f"{family}|sigma={sigma}|gamma={gamma}"]
        return s["above"] / s["cells"]

    assert rate("rosenbrock") > rate("levy") > rate("hill") > rate("hartmann6")
    assert rate("hill") > 0.0, "hill is not clean either -- it is in the middle"
    assert rate("ackley") == 0.0


def test_hill_is_the_only_family_whose_landscapes_straddle_the_ceiling(p6):
    """And where they do, 'above the ceiling' is a majority verdict, not a cell property.

    Only hill has landscape-to-landscape variation, so only hill can straddle. One cell
    lands at 13/25, which is a coin flip; those rows must carry the count, never a bare
    boolean.
    """
    doc = p6.ceiling_census()
    straddling = [r for r in doc["rows"] if not r["unanimous"]]
    assert {r["family"] for r in straddling} == {"hill"}
    assert any(8 <= r["n_landscapes_above"] <= 17 for r in straddling), (
        "expected at least one near-tie cell; the count is what makes it visible")
    for r in straddling:
        assert 0 < r["n_landscapes_above"] < 25
