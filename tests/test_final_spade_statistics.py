"""The final-study analyser's statistics, and the eleven guards that keep them honest.

Every test here pins a defect this repository has **already committed once**. That is the
selection rule for what is in this file: not "what could go wrong with a binomial", but
"what did go wrong, in `docs/FINDINGS-SPADE.md`, with a section number".

------------------------------------------------------------------------------
THE ROLL OF FAILURES BEING PINNED
------------------------------------------------------------------------------

* **§22** — a Holm correction computed with a continuity-corrected normal approximation.
  The leading cell's adjusted p was reported as 0.043 and is 0.2296 on the exact tail, a
  **5.31x** error on the raw p. The inferential claim built on it was withdrawn. So the
  analyser's tails are :func:`scipy.stats.binom.cdf` and its intervals are Clopper-Pearson,
  and one test **greps the module source** for the approximation rather than trusting that
  nobody will reintroduce it.
* **§9.5** — a published containment table pooled four ``tau_frac`` values computed on the
  same campaign, the same posterior and the same draws, and called them independent
  Bernoulli trials. **Eleven** pooling sites were found, not the one flagged. Two claims
  did not survive un-pooling. So every pooling prohibition in spec §8.2 **raises** here; a
  warning is what the eleven sites already had.
* **§29.3** — same-draw and cross-fit containment differ by up to 3.5 points and the gap is
  concentrated exactly where the Vorob'ev quantiles tie. So cross-fit is primary, same-draw
  is emitted beside it labelled diagnostic, and the difference is a column.
* **§9.4** — type I error volume read alone **ranks silence first**: an arm certifying the
  empty set scores exactly 0. So a type-I-only ranking is refused, and a test builds the
  silent arm and shows it winning that ranking before the refusal stops it.
* **§9.6** — the project's two sample-size conventions (n=25 seeds-averaged, n=50
  ``(instance, seed)``) contradicted each other and **nothing recorded the switch**. So
  paired contrasts report both, and a direction disagreement is a loud column.
* **§43.1** — a regret bar in rule A was compared against a number in rule P. "Beaten" was
  withdrawn and the honest claim became *parity, not a win*. So mixing terminal rules
  across arms raises.

------------------------------------------------------------------------------
WHY THE FIXTURES ARE SYNTHETIC, AND WHAT THAT COSTS
------------------------------------------------------------------------------

No `results/final-spade-primary.json` exists yet -- the registration is frozen *before* the
study runs, and so is its analyser. The rows below are built by hand against
:data:`boec.final_spade.ROW_SCHEMA`, which is the frozen raw-row contract, so a schema
change breaks these tests rather than silently passing them.

What that buys: every guard is exercised on data constructed to trip it, including the
corners a real run may never reach (a cell that is 62% empty, a unit disagreement, an
above-ceiling row that escaped the pre-run exclusion). What it does not buy: any evidence
about the study's numbers. These tests prove the analyser refuses the right things. They
prove nothing about SPADE.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from scipy.stats import beta, binom, norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.final_spade import ROW_SCHEMA  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_analyse_final_spade_benchmark", ROOT / "scripts" / "analyse_final_spade_benchmark.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

MODULE_SOURCE_PATH = ROOT / "scripts" / "analyse_final_spade_benchmark.py"


# ===========================================================================
# Fixtures -- built against the FROZEN row schema, not against a convenient dict
# ===========================================================================

def _row(**over) -> dict:
    """One raw row, every ``ROW_SCHEMA`` field present, sensible primary-cell defaults.

    Starting from ``{name: None for name in ROW_SCHEMA}`` is deliberate: if the frozen
    schema gains a field, every fixture here gains it as ``None`` and any analyser that
    silently depends on it fails loudly instead of reading a key that a hand-written test
    dict happened to omit.
    """
    row = {name: None for name in ROW_SCHEMA}
    row.update({
        "study_id": "spade-final-2026-08-23", "registration_commit": "c4f58d3",
        "code_commit": "0000000", "git_hash": "0000000",
        "family": "hill", "dimension": 6, "sigma": 0.25,
        "instance_seed": 0, "campaign_seed": 0, "regime_class": "TARGET",
        "arm": "spade_cf_m0", "arm_family": "SPADE",
        "total_wells": 48, "plate1_wells": 40, "plate2_wells": 8, "rounds": 2,
        "m_local": 0, "m_local_short": False,
        "terminal_rule": "both", "gamma": 0.95, "alpha": 0.95,
        "tau_definition": "tau = tau_frac * mu_max", "tau_raw": 0.60,
        "tau_frac_or_quantile": 0.60, "tau_max": 0.80, "above_ceiling": False,
        "true_prevalence": 0.30,
        "rankable": True, "empty_predictive_region": False, "nonempty_certificate": True,
        "posterior_draws": 4096, "selection_draws": 2048, "evaluation_draws": 2048,
        "draw_split_seed": 0,
        "same_draw_containment": 0.99, "crossfit_containment": 0.98,
        "empirical_containment": 0.98, "certificate_volume": 0.12,
        "regret_rule_a": 0.10, "regret_rule_p": 0.08, "oracle_best_regret": 0.02,
        "symmetric_difference_pred": 0.20, "type_i_volume_pred": 0.05,
        "type_ii_volume_pred": 0.15, "brier": 0.10, "murphy_calibration": 0.010,
        "murphy_refinement": 0.05, "auc_pred": 0.80, "iou_pred": 0.50,
        "false_inclusion_pred": 0.05, "gate_status": "OK",
    })
    row.update(over)
    return row


def _cell_rows(arm: str = "spade_cf_m0", *, n_nonempty: int = 20, n_contained: int = 20,
               n_empty: int = 0, same_draw_contained: int | None = None,
               alpha: float = 0.95, **over) -> list[dict]:
    """One (arm, condition, tau_frac, gamma, alpha) cell's campaigns.

    ``n_contained`` of the non-empty campaigns carry a cross-fit containment at or above
    ``alpha``; the rest sit below it. Empty campaigns carry ``None`` in **both** containment
    columns and ``nonempty_certificate = False`` -- an empty certificate is never scored,
    which is spec §2.1's "the empty set is never scored as a success".
    """
    if same_draw_contained is None:
        same_draw_contained = n_contained
    rows, k = [], 0
    for i in range(n_nonempty):
        rows.append(_row(arm=arm, alpha=alpha,
                         instance_seed=k // 2, campaign_seed=k % 2,
                         nonempty_certificate=True, empty_predictive_region=False,
                         crossfit_containment=(0.999 if i < n_contained else 0.500),
                         same_draw_containment=(0.999 if i < same_draw_contained
                                                else 0.500),
                         **over))
        k += 1
    # The §9.4 mechanism, in the fixture: a certificate that says nothing has NO false
    # inclusions, so its type I volume is exactly 0 and it wins a type-I-only ranking.
    empty_defaults = {"type_i_volume_pred": 0.0, "type_ii_volume_pred": 0.30,
                      "symmetric_difference_pred": 0.30, "certificate_volume": 0.0}
    empty_defaults.update(over)
    for _ in range(n_empty):
        rows.append(_row(arm=arm, alpha=alpha,
                         instance_seed=k // 2, campaign_seed=k % 2,
                         nonempty_certificate=False, empty_predictive_region=True,
                         crossfit_containment=None, same_draw_containment=None,
                         empirical_containment=None, **empty_defaults))
        k += 1
    return rows


def _full_comparator_condition(**over) -> list[dict]:
    """One primary condition with every mandatory arm of spec §4 present."""
    rows = []
    for arm in A.MANDATORY_ARMS:
        rows.extend(_cell_rows(arm, n_nonempty=12, n_contained=12, **over))
    return rows


# ===========================================================================
# Requirement 1 -- exact binomial only. §22.
# ===========================================================================

def test_the_module_source_contains_no_normal_approximation():
    """§22, enforced by grep rather than by intention.

    The defect was not that someone believed a normal approximation was correct here. It is
    that `Binom(50, 0.95)` has `np(1-p) = 2.5` -- an order of magnitude under the usual bar
    -- and the far-left tail is exactly where the approximation is worst, so the substitution
    is invisible unless something looks for it. This looks for it.
    """
    src = MODULE_SOURCE_PATH.read_text()
    forbidden = ("norm.cdf", "norm.ppf", "norm.isf", "norm.sf", "stats.norm",
                 "import norm", "1.96", "sqrt(p*(1-p)", "sqrt(p * (1 - p)",
                 "normaltest", "continuity")
    hits = [f for f in forbidden if f in src]
    assert not hits, (
        f"the analyser's source contains {hits} -- §22 records this project's Holm "
        "correction being computed with a normal approximation and not surviving the "
        "exact tail")


def test_the_lower_tail_reproduces_section_22s_exact_binomial_table():
    """The four cells §22 recomputed, to the printed precision.

    If this passes, the analyser's tail is the one §22 says the study must use, and the
    number it produces is checkable against a table already in the repository.
    """
    assert A.exact_lower_tail(42, 50, 0.95) == pytest.approx(0.00318834, abs=1e-8)
    assert A.exact_lower_tail(44, 50, 0.95) == pytest.approx(0.03777617, abs=1e-8)
    assert A.exact_lower_tail(45, 50, 0.95) == pytest.approx(0.10361681, abs=1e-8)
    assert A.exact_lower_tail(40, 50, 0.95) == pytest.approx(0.000159, abs=1e-6)


def test_the_lower_tail_is_the_exact_binom_cdf_and_not_the_normal_it_replaced():
    """The same measurement, two tails, and the ratio §22 recovered.

    The normal-with-continuity-correction value is computed **here in the test** -- the one
    place it is allowed to exist -- so the test states the size of the error it prevents
    rather than merely asserting the right function was called.
    """
    x, n, p = 42, 50, 0.95
    exact = A.exact_lower_tail(x, n, p)
    assert exact == pytest.approx(float(binom.cdf(x, n, p)))
    normal_cc = float(norm.cdf((x + 0.5 - n * p) / (n * p * (1 - p)) ** 0.5))
    assert normal_cc == pytest.approx(0.00058843, abs=1e-8)
    assert exact / normal_cc > 5.0, "§22 measured this ratio at 5.31x"


def test_an_absent_denominator_yields_no_tail_rather_than_a_fabricated_one():
    """A cell with nothing in it must not produce a p-value. §7.1's INCONCLUSIVE exists
    precisely so that "no evidence" and "evidence of no effect" stay distinguishable."""
    assert A.exact_lower_tail(0, 0, 0.95) is None


def test_the_interval_is_the_exact_clopper_pearson_beta_interval():
    """Clopper-Pearson, not Wald. At X = n the Wald interval is the single point [1, 1] --
    a certificate measured 50 times out of 50 would be reported as *proven* rather than as
    bounded below by 0.929."""
    lo, hi = A.clopper_pearson(45, 50, level=0.95)
    assert lo == pytest.approx(float(beta.ppf(0.025, 45, 6)))
    assert hi == pytest.approx(float(beta.ppf(0.975, 46, 5)))
    assert lo < 45 / 50 < hi

    lo_all, hi_all = A.clopper_pearson(50, 50, level=0.95)
    assert hi_all == 1.0
    assert lo_all == pytest.approx(float(beta.ppf(0.025, 50, 1)))
    assert 0.90 < lo_all < 0.95, "the Wald interval would have collapsed this to [1, 1]"

    lo_none, hi_none = A.clopper_pearson(0, 12, level=0.95)
    assert lo_none == 0.0
    assert hi_none > 0.0


def test_an_interval_is_refused_when_there_is_no_denominator():
    assert A.clopper_pearson(0, 0) == (None, None)


# ===========================================================================
# Requirement 2 -- cross-fit is primary, same-draw is diagnostic. §29.3.
# ===========================================================================

def test_the_certificate_never_labels_same_draw_as_primary():
    """§9 publication guard 3. The same-draw number is the flattering one -- §29.3 measured
    it up to 3.5 points above cross-fit, concentrated where the quantiles tie -- so the
    label is asserted on every cell rather than left to whoever writes the table."""
    report = A.certificate_report(_cell_rows(n_nonempty=20, n_contained=20))
    assert report["primary_estimator"] == "crossfit"
    assert report["diagnostic_estimator"] == "same_draw"
    assert report["cells"]
    for cell in report["cells"]:
        assert cell["primary_estimator"] == "crossfit"
        assert cell["crossfit"]["role"] == "primary"
        assert cell["same_draw"]["role"] == "diagnostic"


def test_every_cell_emits_both_estimators_and_the_difference_between_them():
    """The protocol's whole value is that the gap stays visible in every cell rather than
    being resolved once in an analysis nobody re-reads (`ROW_SCHEMA`'s own comment)."""
    rows = _cell_rows(n_nonempty=20, n_contained=18, same_draw_contained=20)
    cell = A.certificate_report(rows)["cells"][0]

    assert cell["crossfit"]["x"] == 18 and cell["crossfit"]["n"] == 20
    assert cell["same_draw"]["x"] == 20 and cell["same_draw"]["n"] == 20
    assert cell["crossfit"]["proportion"] == pytest.approx(0.90)
    assert cell["same_draw"]["proportion"] == pytest.approx(1.00)
    assert cell["same_draw_minus_crossfit"] == pytest.approx(0.10)


def test_the_exact_interval_and_tail_are_computed_on_the_crossfit_column():
    """Not on same-draw, and not on `empirical_containment`. The primary safety endpoint has
    exactly one source."""
    rows = _cell_rows(n_nonempty=50, n_contained=45, same_draw_contained=50)
    cell = A.certificate_report(rows)["cells"][0]
    assert cell["crossfit"]["exact_p"] == pytest.approx(0.10361681, abs=1e-8)
    assert cell["crossfit"]["ci_lo"] == pytest.approx(float(beta.ppf(0.025, 45, 6)))


# ===========================================================================
# Requirement 3 -- the pooling prohibitions HARD-FAIL. Spec §8.2, FINDINGS §9.5.
# ===========================================================================

def test_pooling_two_tau_fracs_from_one_campaign_raises():
    """Spec §8.2.1. §3.7 pooled four `tau_frac` computed on the same campaign, the same
    posterior and the same draws, and called them four Bernoulli trials. They are one."""
    rows = (_cell_rows(n_nonempty=6, n_contained=6, tau_frac_or_quantile=0.60)
            + _cell_rows(n_nonempty=6, n_contained=6, tau_frac_or_quantile=0.75))
    with pytest.raises(A.InvalidPooling, match="tau_frac"):
        A.containment_cell(rows, alpha=0.95)


def test_pooling_two_gammas_from_one_campaign_raises():
    """Spec §8.2.2. gamma is a per-point margin on the SAME posterior; two gammas from one
    campaign are two readings of one draw, not two campaigns."""
    rows = (_cell_rows(n_nonempty=6, n_contained=6, gamma=0.50)
            + _cell_rows(n_nonempty=6, n_contained=6, gamma=0.95))
    with pytest.raises(A.InvalidPooling, match="gamma"):
        A.containment_cell(rows, alpha=0.95)


def test_pooling_empty_with_non_empty_without_the_denominator_raises():
    """Spec §8.2.4. The registered policy is the only one accepted: an empty certificate
    leaves the numerator AND the denominator. Asking for any other treatment raises rather
    than quietly producing a rate whose denominator nobody can reconstruct."""
    rows = _cell_rows(n_nonempty=10, n_contained=10, n_empty=10)
    for policy in ("count_as_contained", "pool", "denominator_only"):
        with pytest.raises(A.InvalidPooling, match="empt"):
            A.containment_cell(rows, alpha=0.95, empty_policy=policy)


def test_an_empty_certificate_carrying_a_containment_score_raises():
    """The same prohibition, caught one level lower -- at the row.

    §2.1: `empirical_containment` returns None for an empty mask and
    `conservative_estimate_split` returns nan. A row that says `nonempty_certificate =
    False` and also carries a number has had an empty set scored, and a method that
    certifies nothing would post perfect containment.
    """
    rows = _cell_rows(n_nonempty=10, n_contained=10)
    rows.append(_row(nonempty_certificate=False, empty_predictive_region=True,
                     crossfit_containment=1.0, instance_seed=9, campaign_seed=0))
    with pytest.raises(A.InvalidPooling, match="empt"):
        A.containment_cell(rows, alpha=0.95)


def test_the_registered_empty_policy_keeps_the_denominator_visible():
    """The other half of the same guard: when the policy IS the registered one, the empty
    count, the total and the rate all survive into the output. §11 prohibits "reporting a
    certificate rate without its non-empty denominator"."""
    cell = A.containment_cell(_cell_rows(n_nonempty=10, n_contained=9, n_empty=6),
                              alpha=0.95)
    assert cell["n_nonempty"] == 10
    assert cell["n_empty"] == 6
    assert cell["n_total"] == 16
    assert cell["empty_rate"] == pytest.approx(6 / 16)
    assert cell["x"] == 9


def test_a_map_contrast_spanning_two_thresholds_raises():
    """The same prohibition on the map side. `symmetric_difference_pred` depends on the
    threshold, so averaging it across two `tau_frac` from one campaign is §9.5 again in a
    different column."""
    rows = (_cell_rows("spade_cf_m0", n_nonempty=4, tau_frac_or_quantile=0.60)
            + _cell_rows("spade_cf_m0", n_nonempty=4, tau_frac_or_quantile=0.75)
            + _cell_rows("sobol", n_nonempty=4, tau_frac_or_quantile=0.60)
            + _cell_rows("sobol", n_nonempty=4, tau_frac_or_quantile=0.75))
    with pytest.raises(A.InvalidPooling, match="tau_frac"):
        A.paired_contrast(rows, "spade_cf_m0", "sobol", "symmetric_difference_pred")


def test_a_campaign_invariant_column_is_deduplicated_rather_than_counted_once_per_cell():
    """Regret does not depend on tau_frac, gamma or alpha, but the row grid does -- so a
    naive mean over rows would count each campaign once per certificate cell and inflate n
    by the multiplicity. That is §9.5's arithmetic wearing a different column's name."""
    rows = []
    for tf in (0.60, 0.75):
        for g in (0.50, 0.95):
            rows.extend(_cell_rows("spade_cf_m0", n_nonempty=4, tau_frac_or_quantile=tf,
                                   gamma=g, regret_rule_p=0.08))
            rows.extend(_cell_rows("sobol", n_nonempty=4, tau_frac_or_quantile=tf,
                                   gamma=g, regret_rule_p=0.11))
    c = A.paired_contrast(rows, "sobol", "spade_cf_m0", "regret_rule_p")
    assert c["n50"]["n"] == 4, f"regret was counted {c['n50']['n']} times, not 4"
    assert c["n50"]["mean"] == pytest.approx(0.03)


def test_a_campaign_invariant_column_that_disagrees_across_cells_raises():
    """If one campaign's regret differs between two of its own rows, the column is not what
    it claims to be and silently averaging the disagreement away would hide a runner bug."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=2, tau_frac_or_quantile=0.60,
                      regret_rule_p=0.08)
    rows += _cell_rows("spade_cf_m0", n_nonempty=2, tau_frac_or_quantile=0.75,
                       regret_rule_p=0.09)
    rows += _cell_rows("sobol", n_nonempty=2, tau_frac_or_quantile=0.60)
    rows += _cell_rows("sobol", n_nonempty=2, tau_frac_or_quantile=0.75)
    with pytest.raises(A.InvalidPooling, match="disagree"):
        A.paired_contrast(rows, "sobol", "spade_cf_m0", "regret_rule_p")


# ===========================================================================
# Requirement 4 -- comparator completeness. Spec §4, §8.2.5.
# ===========================================================================

def test_a_primary_condition_missing_a_mandatory_arm_refuses_a_primary_conclusion():
    """Spec §4: a missing mandatory comparator is a HARD FAILURE that blocks any primary
    conclusion. §4.2b's Q57 trap is the concrete reason -- a headline that holds against
    `qLogEI` and dies against the noisy acquisition. Running only the weaker one
    manufactures a win, and so does dropping the stronger one."""
    rows = [r for r in _full_comparator_condition() if r["arm"] != "qlognei"]
    report = A.certificate_report(rows)
    cond = report["conditions"]["hill-d6-s0.25"]

    assert cond["primary_conclusion_available"] is False
    assert "qlognei" in cond["missing_mandatory"]
    assert "qlognei" in cond["unavailable_reason"]
    for cell in report["cells"]:
        assert cell["confirmatory"] is False


def test_a_declared_unavailable_arm_does_not_block_the_primary_conclusion():
    """Spec §4's `doe_unscreened` clause. A full second-order RSM in d=8 needs 45
    coefficients against a 48-well budget; when the arithmetic does not close the arm is
    recorded `unavailable_reason` BEFORE any run and is never approximated into existence
    (§14). A structured declaration is compliance; silence is not."""
    rows = [r for r in _full_comparator_condition() if r["arm"] != "doe_unscreened"]
    rows.append(_row(arm="doe_unscreened", arm_family="classical RSM", rounds=3,
                     unavailable_reason="second-order RSM infeasible at shared budget",
                     nonempty_certificate=None, crossfit_containment=None,
                     same_draw_containment=None, symmetric_difference_pred=None,
                     regret_rule_a=None, regret_rule_p=None))
    cond = A.certificate_report(rows)["conditions"]["hill-d6-s0.25"]

    assert cond["primary_conclusion_available"] is True
    assert cond["missing_mandatory"] == []
    assert cond["unavailable"]["doe_unscreened"].startswith("second-order RSM infeasible")


def test_a_declared_unavailable_arm_contributes_no_measurements():
    """A placeholder row declares absence. If it were also averaged in, the declaration
    would become a data point and `doe_unscreened` would be fabricated at d=8 -- which §11
    names as a prohibited action outright."""
    rows = _cell_rows("sobol", n_nonempty=4, symmetric_difference_pred=0.4)
    rows.append(_row(arm="sobol", unavailable_reason="declared", instance_seed=99,
                     symmetric_difference_pred=0.0))
    means = A.arm_means(rows, "symmetric_difference_pred", tau_frac=0.60, gamma=0.95,
                        alpha=0.95)
    assert means["sobol"] == pytest.approx(0.4)


# ===========================================================================
# Requirement 5 -- the non-empty denominator floor of 10. Spec §6.
# ===========================================================================

def test_a_cell_below_the_non_empty_floor_is_non_confirmatory_and_never_passes():
    """Spec §6's evidence floor and §7.1's INCONCLUSIVE branch. "Non-significance is not
    proof of validity": a cell of 8 that fails to reject has no power to reject, and
    printing PASS beside it converts an absence of evidence into a claim."""
    rows = _cell_rows(n_nonempty=8, n_contained=8)
    cell = A.certificate_report(rows)["cells"][0]

    assert cell["crossfit"]["n"] == 8
    assert cell["meets_nonempty_floor"] is False
    assert cell["confirmatory"] is False
    assert cell["verdict"] == "INCONCLUSIVE"
    assert cell["verdict"] != "PASS"


def test_the_floor_is_ten_and_is_read_from_the_registered_constant():
    assert A.NONEMPTY_FLOOR == 10
    at_floor = A.certificate_report(_cell_rows(n_nonempty=10, n_contained=10))["cells"][0]
    assert at_floor["meets_nonempty_floor"] is True


def test_a_cell_that_certified_nothing_at_all_is_inconclusive_not_a_pass():
    """The degenerate corner of the same rule. An arm that never certifies has no
    containment, and §2.1 forbids carrying that through as 1.0."""
    cell = A.certificate_report(_cell_rows(n_nonempty=0, n_empty=20))["cells"][0]
    assert cell["crossfit"]["n"] == 0
    assert cell["crossfit"]["proportion"] is None
    assert cell["crossfit"]["exact_p"] is None
    assert cell["verdict"] == "INCONCLUSIVE"


# ===========================================================================
# Requirement 6 -- the empty-rate guard, KF-10.
# ===========================================================================

def test_a_pass_cell_with_more_than_half_empty_is_downgraded_to_inconclusive():
    """KF-10, spec §10: "Empty-set degeneracy does not explain a pass".

    The cell below is 20 contained of 20 scored -- a perfect containment record -- on 32
    campaigns of which 12 certified nothing... inverted: 12 scored, 20 empty. A method that
    declines to answer two campaigns in three has not demonstrated a valid certificate; it
    has demonstrated that its non-answers are safe.
    """
    rows = _cell_rows(n_nonempty=12, n_contained=12, n_empty=20)
    cell = A.certificate_report(rows)["cells"][0]

    assert cell["empty_rate"] == pytest.approx(20 / 32)
    assert cell["empty_rate"] > A.EMPTY_RATE_CEILING
    assert cell["verdict"] == "INCONCLUSIVE"
    assert cell["downgraded_by"] == "KF-10"
    assert "PASS" in cell["verdict_reason"], "the downgrade must say what it downgraded"


def test_a_cell_that_answers_most_of_the_time_is_allowed_to_pass():
    """The control for the test above -- if the guard fired on everything it would be a
    constant, not a guard."""
    cell = A.certificate_report(_cell_rows(n_nonempty=20, n_contained=20,
                                           n_empty=2))["cells"][0]
    assert cell["verdict"] == "PASS"
    assert cell["downgraded_by"] is None


def test_a_cell_demonstrably_below_nominal_after_holm_fails():
    """§7.1's FAIL branch, on the exact tail. 40 of 50 at nominal 0.95 has exact
    p = 1.59e-4 (§22's own table), which survives Holm in a one-member family."""
    cell = A.certificate_report(_cell_rows(n_nonempty=50, n_contained=40))["cells"][0]
    assert cell["crossfit"]["exact_p"] < 0.001
    assert cell["crossfit"]["p_holm"] < 0.05
    assert cell["verdict"] == "FAIL"


def test_the_empty_rate_guard_does_not_rescue_a_failing_cell():
    """A FAIL is not downgraded by KF-10 -- KF-10 protects against a flattering pass, and
    turning a demonstrated failure into INCONCLUSIVE would be the guard running backwards."""
    cell = A.certificate_report(_cell_rows(n_nonempty=50, n_contained=40,
                                           n_empty=60))["cells"][0]
    assert cell["empty_rate"] > A.EMPTY_RATE_CEILING
    assert cell["verdict"] == "FAIL"
    assert cell["downgraded_by"] is None


# ===========================================================================
# Requirement 7 -- type I alone must never be emitted as a ranking. §9.4.
# ===========================================================================

def test_an_empty_certificate_scores_type_i_exactly_zero():
    """The mechanism, before the refusal. §9.4: "type I volume read alone ranks silence
    first -- an arm certifying the empty set scores exactly 0"."""
    silent = _cell_rows("spade_cf_m8", n_nonempty=0, n_empty=10)
    means = A.arm_means(silent, "type_i_volume_pred", tau_frac=0.60, gamma=0.95,
                        alpha=0.95)
    assert means["spade_cf_m8"] == 0.0


def test_ranking_on_type_i_volume_alone_is_refused():
    """§13.5 / §7.2. The silent arm below would top a type-I ranking with a perfect 0 while
    certifying nothing at all in ten campaigns. The analyser refuses the ranking rather than
    printing it with a footnote -- a footnote is what §9.4 already had."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=10, type_i_volume_pred=0.05)
    rows += _cell_rows("spade_cf_m8", n_nonempty=0, n_empty=10)
    with pytest.raises(A.TypeIOnlyRanking, match="silence"):
        A.rank_arms(rows, "type_i_volume_pred", tau_frac=0.60, gamma=0.95, alpha=0.95)


def test_the_primary_map_scalar_is_the_symmetric_difference_and_it_ranks_silence_last():
    """§7.2's replacement scalar, and the demonstration that it fixes the pathology: the
    same silent arm that wins on type I comes last on type I + type II."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=10, symmetric_difference_pred=0.20)
    rows += _cell_rows("spade_cf_m8", n_nonempty=0, n_empty=10)

    assert A.PRIMARY_MAP_SCALAR == "symmetric_difference_pred"
    ranked = A.rank_arms(rows, A.PRIMARY_MAP_SCALAR, tau_frac=0.60, gamma=0.95, alpha=0.95)
    assert ranked[0]["arm"] == "spade_cf_m0"
    assert ranked[-1]["arm"] == "spade_cf_m8"


def test_auc_is_never_offered_as_the_primary_map_scalar():
    """§7.2 / §9.4: AUC is invariant to monotone transformation and therefore cannot see
    calibration, while mean `grid_r2` is negative for all eight arms. §24 revised the
    grounds for superseding it without restoring it."""
    assert A.PRIMARY_MAP_SCALAR != "auc_pred"
    assert A.SECONDARY_MAP_SCALARS == ("auc_pred",) or "auc_pred" in A.SECONDARY_MAP_SCALARS


# ===========================================================================
# Requirement 8 -- both units, and a loud disagreement. §9.6.
# ===========================================================================

def test_a_paired_contrast_reports_both_the_n25_and_the_n50_unit():
    """§8's unit clause. `K6-TECHNICAL-REPORT` §3.8 used n=50 `(instance, seed)`;
    `RESEARCH-SUMMARY` used n=25 seeds-averaged; **nothing recorded the switch**. Both are
    reported here so a future reader never has to guess which one a number came from."""
    rows = []
    for inst in (0, 1):
        for seed in (0, 1):
            rows.append(_row(arm="spade_cf_m0", instance_seed=inst, campaign_seed=seed,
                             symmetric_difference_pred=0.20))
            rows.append(_row(arm="sobol", instance_seed=inst, campaign_seed=seed,
                             symmetric_difference_pred=0.26))
    c = A.paired_contrast(rows, "sobol", "spade_cf_m0", "symmetric_difference_pred")

    assert c["n50"]["n"] == 4
    assert c["n25"]["n"] == 2
    assert c["n50"]["mean"] == pytest.approx(0.06)
    assert c["n25"]["mean"] == pytest.approx(0.06)
    assert c["units_disagree"] is False


def test_a_direction_disagreement_between_the_two_units_is_recorded_loudly():
    """§8: "the analysis fails loudly if they disagree in direction".

    The two units cannot disagree on a balanced design -- averaging within instance and
    then across is the same arithmetic. They disagree exactly when the seeds-per-instance
    counts are unequal, which is what an excluded or crashed campaign produces. So the
    fixture is unbalanced on purpose: instance 0 carries three campaigns favouring one arm,
    instance 1 carries a single campaign favouring the other by more.
    """
    rows = []
    for seed, diff in ((0, 1.0), (1, 1.0), (2, 1.0)):
        rows.append(_row(arm="sobol", instance_seed=0, campaign_seed=seed,
                         symmetric_difference_pred=0.20 + diff))
        rows.append(_row(arm="spade_cf_m0", instance_seed=0, campaign_seed=seed,
                         symmetric_difference_pred=0.20))
    rows.append(_row(arm="sobol", instance_seed=1, campaign_seed=0,
                     symmetric_difference_pred=0.20 - 2.5))
    rows.append(_row(arm="spade_cf_m0", instance_seed=1, campaign_seed=0,
                     symmetric_difference_pred=0.20))

    c = A.paired_contrast(rows, "sobol", "spade_cf_m0", "symmetric_difference_pred")
    assert c["n50"]["mean"] == pytest.approx(0.125)
    assert c["n25"]["mean"] == pytest.approx(-0.75)
    assert c["units_disagree"] is True
    assert "direction" in c["unit_disagreement_note"].lower()


def test_the_default_unit_for_an_unpaired_quantity_is_n25():
    """§9.6's measured ICC. The n=25 default is for UNPAIRED quantities -- arm means,
    prevalence, containment proportions -- because raw per-arm ICC runs -0.226 to +0.581 and
    the conservative unit is the defensible one there."""
    assert A.DEFAULT_UNPAIRED_UNIT == "n25"


# ===========================================================================
# Requirement 9 -- both terminal rules, never mixed. §43.1.
# ===========================================================================

def test_comparing_rule_a_for_one_arm_against_rule_p_for_another_raises():
    """§43.1, the exact mistake. K-C1's registered bar `r*` is a rule A column from
    `e2-grid.json`; Version C's number is rule P. Against the mixed bar the arm was "below
    it"; like-for-like it was +0.0165 above, inside SESOI, and the claim became **parity,
    not a win**. The comparison is refused rather than footnoted."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=6) + _cell_rows("qlognei", n_nonempty=6)
    with pytest.raises(A.MixedEstimand, match="rule"):
        A.compare_regret(rows, "spade_cf_m0", "qlognei", rule_a="P", rule_b="A")


def test_a_like_for_like_regret_comparison_is_allowed_under_either_rule():
    rows = _cell_rows("spade_cf_m0", n_nonempty=6, regret_rule_a=0.10, regret_rule_p=0.08)
    rows += _cell_rows("qlognei", n_nonempty=6, regret_rule_a=0.12, regret_rule_p=0.11)
    for rule, expected in (("A", 0.02), ("P", 0.03)):
        c = A.compare_regret(rows, "qlognei", "spade_cf_m0", rule_a=rule)
        assert c["rule"] == rule
        assert c["n25"]["mean"] == pytest.approx(expected)


def test_an_unregistered_terminal_rule_raises_rather_than_defaulting():
    """Three different non-maximising rules are already on disk (§34.6) and they are not one
    estimator. A silent default would pick one of them for the reader."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=4) + _cell_rows("sobol", n_nonempty=4)
    with pytest.raises(A.MixedEstimand, match="rule"):
        A.compare_regret(rows, "sobol", "spade_cf_m0", rule_a="oracle_best")


def test_the_pareto_report_carries_regret_under_both_rules_for_every_arm():
    """§7.4: "Compute under BOTH terminal rules for every arm". Rule P is the primary
    estimand and rule A is a REQUIRED robustness outcome, not an optional one."""
    rows = _full_comparator_condition()
    report = A.regret_pareto_report(rows)
    assert report["primary_terminal_rule"] == "P"
    assert report["rows"]
    for entry in report["rows"]:
        assert set(entry["regret"]) == {"A", "P"}
        assert entry["regret"]["A"] is not None
        assert entry["regret"]["P"] is not None
        assert entry["primary_rule"] == "P"


# ===========================================================================
# Requirement 10 -- the four frozen Holm families. Spec §8.1.
# ===========================================================================

def test_the_holm_families_are_exactly_the_four_frozen_ones():
    """Spec §8.1: "Frozen here, before any result. They are not combined, split, or
    redefined afterwards." §22 is the cost of getting the family wrong -- the one surviving
    cell reappears only in an 18-cell subfamily chosen after seeing the table, which is not
    available."""
    assert set(A.HOLM_FAMILIES) == {"F-CERT", "F-BOUND", "F-ALLOC", "F-MAP"}


def test_an_unregistered_or_combined_holm_family_raises():
    pvals = {"a": 0.01, "b": 0.02}
    for bad in ("F-CERT+F-MAP", "F-ALL", "F-cert", "", "F-EVERYTHING"):
        with pytest.raises(A.UnregisteredHolmFamily):
            A.holm_within_family(bad, pvals)


def test_each_registered_contrast_routes_to_its_frozen_family():
    """The routing is registered, so an analyst cannot move a contrast into a larger family
    to soften its correction or into a smaller one to sharpen it."""
    assert A.family_for_contrast("spade_cf_m0", "spade_random_plate2") == "F-BOUND"
    assert A.family_for_contrast("spade_cf_m0", "spade_plate1_only") == "F-BOUND"
    assert A.family_for_contrast("spade_cf_m0", "spade_cf_m4") == "F-ALLOC"
    assert A.family_for_contrast("spade_cf_m4", "spade_cf_m8") == "F-ALLOC"
    for comparator in ("sobol", "qlognei", "doe"):
        assert A.family_for_contrast("spade_cf_m0", comparator) == "F-MAP"


def test_a_contrast_no_frozen_family_covers_raises_rather_than_being_invented_one():
    with pytest.raises(A.UnregisteredHolmFamily):
        A.family_for_contrast("sobol", "lhs")


def test_the_certificate_family_is_f_cert_and_carries_its_members():
    report = A.certificate_report(_cell_rows(n_nonempty=20, n_contained=20))
    assert report["holm"]["family"] == "F-CERT"
    assert report["holm"]["members"] == [c["cell_id"] for c in report["cells"]
                                         if c["cell_id"] in report["holm"]["members"]]
    assert report["holm"]["n_members"] == len(report["holm"]["members"])


def test_holm_is_a_monotone_step_down_and_matches_the_house_implementation():
    """The same step-down `analyse_fix1._holm` and `analyse_p8_certificate.holm` use, with
    the running max that enforces monotonicity."""
    adj = A.holm({"a": 0.01, "b": 0.02, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["b"] == pytest.approx(0.04)
    assert adj["c"] == pytest.approx(0.04)
    assert adj["b"] <= adj["c"]


def test_holm_reproduces_section_22s_correction_on_the_exact_tail():
    """§22's headline arithmetic: 72 x 0.00318834 = 0.2296, not the 0.043 that 72 x the
    normal-approximated 0.00058843 produced. No cell survives Holm at 0.05 across the 72."""
    pvals = {f"c{i}": 1.0 for i in range(72)}
    pvals["c0"] = A.exact_lower_tail(42, 50, 0.95)
    adj = A.holm(pvals)
    assert adj["c0"] == pytest.approx(0.229561, abs=1e-5)
    assert adj["c0"] > 0.05


def test_a_diagnostic_gamma_cell_is_never_confirmatory():
    """Spec §2: gamma = 0.99 is "diagnostic only". A diagnostic corner that could carry a
    confirmatory verdict would be a fifth Holm family created after the fact."""
    cell = A.certificate_report(_cell_rows(n_nonempty=30, n_contained=30,
                                           gamma=0.99))["cells"][0]
    assert cell["gamma_role"] == "diagnostic"
    assert cell["confirmatory"] is False
    assert cell["cell_id"] not in A.certificate_report(
        _cell_rows(n_nonempty=30, n_contained=30, gamma=0.99))["holm"]["members"]


def test_a_secondary_condition_cannot_carry_a_confirmatory_certificate_cell():
    """Spec §5.3: "Secondary results are robustness/context and may not carry a
    confirmatory endpoint." §41 records ackley certifying nothing in 1,200 campaigns."""
    cell = A.certificate_report(_cell_rows(n_nonempty=30, n_contained=30, family="ackley",
                                           regime_class="EXCEPTION"))["cells"][0]
    assert cell["primary_condition"] is False
    assert cell["confirmatory"] is False


# ===========================================================================
# Requirement 11 -- --allow-partial prints tables but emits NO verdict.
# ===========================================================================

def test_allow_partial_emits_no_verdict_anywhere():
    """A partial run is a table, not a conclusion. §6: "If compute cannot reach 200 for a
    high-assurance cell, the sample size is NOT silently reduced" -- the same principle one
    level up, where an incomplete campaign set must not silently become a study."""
    rows = _full_comparator_condition()
    cert = A.certificate_report(rows, allow_partial=True)
    assert cert["verdicts_withheld"] is True
    assert cert["cells"], "the tables are still built"
    for cell in cert["cells"]:
        assert "verdict" not in cell
        assert cell["verdict_withheld"] is True
        assert cell["crossfit"]["x"] is not None, "the counts are still reported"

    pareto = A.regret_pareto_report(rows, certificate=cert, allow_partial=True)
    for entry in pareto["rows"]:
        assert entry["certificate_status"] == "WITHHELD"

    ledger = A.kill_ledger(rows, cert, pareto, allow_partial=True)
    for kill in ledger["kills"].values():
        assert "status" not in kill
        assert kill["status_withheld"] is True


def test_without_allow_partial_a_verdict_is_emitted():
    """The control. A guard that withholds unconditionally is not a guard."""
    rows = _full_comparator_condition()
    cert = A.certificate_report(rows)
    assert cert["verdicts_withheld"] is False
    assert all("verdict" in c for c in cert["cells"])
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))
    assert all("status" in k for k in ledger["kills"].values())


def test_gate_failures_block_a_verdict_unless_partial_is_explicit():
    """`analyse_fix1` refuses to read a run with gate failures at all: "the rule-P column
    describes a different experiment". Same rule here, with an explicit escape hatch that
    cannot produce a verdict."""
    payload = {"study_id": "spade-final-2026-08-23", "gate_failures": ["cell C4 crashed"],
               "rows": _cell_rows(n_nonempty=4)}
    with pytest.raises(A.GateFailure):
        A.assert_gate_clean(payload)
    A.assert_gate_clean(payload, allow_partial=True)


# ===========================================================================
# The Pareto front -- both axes, both lower-better
# ===========================================================================

def test_pareto_domination_uses_both_axes_and_lower_is_better_on_each():
    """Spec §7.2 and §7.4 give two primary scalars in different currencies. A single scalar
    would need a weighting nobody registered, so the front is reported instead: an arm is
    non-dominated when nothing beats it on regret without losing on the map, or vice versa.
    """
    front = A.pareto_nondominated({
        "best_regret": (0.05, 0.30),      # wins the regret axis
        "best_map": (0.12, 0.18),         # wins the map axis
        "dominated": (0.13, 0.31),        # worse than both on both
        "tied_but_worse": (0.05, 0.31),   # ties on regret, loses on the map
    })
    assert front == {"best_regret", "best_map"}


def test_the_pareto_report_carries_rounds_wells_and_the_certificate_status():
    """§4.1's separate axes. `spade_plate1_only` is budget-short by 8 wells and is a
    rounds/wells reference, NOT an equal-well comparator -- so a table without both columns
    invites exactly the comparison the spec forbids."""
    rows = _full_comparator_condition()
    cert = A.certificate_report(rows)
    report = A.regret_pareto_report(rows, certificate=cert)

    by_arm = {e["arm"]: e for e in report["rows"]}
    assert by_arm["spade_cf_m0"]["rounds"] == 2
    assert by_arm["spade_cf_m0"]["wells"] == 48
    assert by_arm["spade_cf_m0"]["certificate_status"] in {"PASS", "FAIL", "INCONCLUSIVE"}
    assert isinstance(by_arm["spade_cf_m0"]["pareto_nondominated"], bool)
    assert by_arm["spade_cf_m0"]["symmetric_difference"] is not None


def test_the_pareto_report_names_the_map_axis_as_the_symmetric_difference():
    """Not type I. The refusal in §9.4 has to hold on the Pareto axes too, or the ranking
    comes back through the front door."""
    report = A.regret_pareto_report(_full_comparator_condition())
    assert report["axes"] == ("regret_rule_p", "symmetric_difference_pred")


# ===========================================================================
# The kill ledger -- spec §10, every one of the ten
# ===========================================================================

def test_the_ledger_carries_every_registered_kill_from_kf1_to_kf10():
    """§35's lesson, one level up: "a registered kill that nothing evaluates is not a kill
    -- it is a paragraph". A kill that quietly disappears is indistinguishable from one that
    passed."""
    rows = _full_comparator_condition()
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))
    assert set(ledger["kills"]) == {f"KF-{i}" for i in range(1, 11)}


def test_every_kill_entry_carries_the_registered_reporting_fields():
    """§10: "Every item resolves to PASS / FAIL / INCONCLUSIVE / NOT_RUN / MOOT, with
    effect, interval, p, adjusted p, SESOI comparison, denominator, and source artefact
    path + key"."""
    rows = _full_comparator_condition()
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))

    for name, kill in ledger["kills"].items():
        assert kill["status"] in {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN", "MOOT"}, name
        for field in ("claim", "fires_when", "effect", "ci", "p", "p_adjusted",
                      "sesoi", "sesoi_comparison", "denominator", "source",
                      "interpretation"):
            assert field in kill, f"{name} is missing {field!r}"
        assert kill["sesoi"] == A.SESOI
        assert kill["source"]["artefact"].startswith("results/final-spade-")
        assert kill["source"]["key"]
        assert kill["interpretation"]


def test_kf1_fails_when_a_primary_certificate_cell_is_below_nominal():
    rows = _full_comparator_condition()
    rows = [r for r in rows if r["arm"] != "spade_cf_m0"]
    rows += _cell_rows("spade_cf_m0", n_nonempty=50, n_contained=40)
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))

    assert ledger["kills"]["KF-1"]["status"] == "FAIL"
    assert ledger["kills"]["KF-1"]["denominator"] == 50
    assert ledger["kills"]["KF-1"]["p_adjusted"] is not None


def test_kf9_fails_when_an_above_ceiling_cell_reached_the_analysis():
    """§4.5 / KF-9. An above-ceiling threshold is a property of the threshold: no method
    certifies there at any budget. Scoring an arm in such a cell and reading the zero as a
    method failure is the error the pre-run feasibility gate exists to stop -- so if one
    reaches the analyser at all, that is a protocol breach, not a result."""
    rows = _full_comparator_condition()
    rows += _cell_rows("spade_cf_m0", n_nonempty=12, n_contained=0, above_ceiling=True,
                       tau_frac_or_quantile=0.85, regime_class="INFEASIBLE")
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))

    assert ledger["kills"]["KF-9"]["status"] == "FAIL"
    assert "ceiling" in ledger["kills"]["KF-9"]["interpretation"].lower()


def test_kf10_fires_exactly_when_a_pass_was_downgraded():
    rows = [r for r in _full_comparator_condition() if r["arm"] != "spade_cf_m0"]
    rows += _cell_rows("spade_cf_m0", n_nonempty=12, n_contained=12, n_empty=20)
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))

    assert ledger["kills"]["KF-10"]["status"] == "FAIL"
    assert ledger["kills"]["KF-10"]["effect"] == 1, "exactly one cell was downgraded"
    assert ledger["kills"]["KF-10"]["denominator"] >= 1

    clean = _full_comparator_condition()
    clean_cert = A.certificate_report(clean)
    clean_ledger = A.kill_ledger(clean, clean_cert,
                                 A.regret_pareto_report(clean, certificate=clean_cert))
    assert clean_ledger["kills"]["KF-10"]["status"] == "PASS"


def test_kf3_fails_when_targeted_plate_two_does_not_beat_random_plate_two():
    """§7.3 / KF-3, the load-bearing causal comparison. If it fails the registered response
    is not a smaller claim -- it is: "targeted plate-2 SUR did not demonstrate value beyond
    random second-plate wells", and the mechanistic claim comes out of the paper."""
    rows = [r for r in _full_comparator_condition()
            if r["arm"] not in ("spade_cf_m0", "spade_random_plate2")]
    rows += _cell_rows("spade_cf_m0", n_nonempty=12, symmetric_difference_pred=0.200)
    rows += _cell_rows("spade_random_plate2", n_nonempty=12,
                       symmetric_difference_pred=0.205)
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))

    kf3 = ledger["kills"]["KF-3"]
    assert kf3["status"] == "FAIL"
    assert kf3["effect"] == pytest.approx(0.005, abs=1e-9)
    assert "SESOI" in kf3["sesoi_comparison"] or "sesoi" in kf3["sesoi_comparison"]
    assert "mechanis" in kf3["interpretation"].lower()


def test_kf3_passes_when_targeted_plate_two_clears_the_sesoi():
    rows = [r for r in _full_comparator_condition()
            if r["arm"] not in ("spade_cf_m0", "spade_random_plate2")]
    rows += _cell_rows("spade_cf_m0", n_nonempty=12, symmetric_difference_pred=0.200)
    rows += _cell_rows("spade_random_plate2", n_nonempty=12,
                       symmetric_difference_pred=0.240)
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))
    assert ledger["kills"]["KF-3"]["status"] == "PASS"


def test_kf3_is_inconclusive_when_no_target_condition_exists():
    """A kill evaluated in a regime it was not registered for is not a kill. §5.1 assigns
    regime class from oracle geometry and a frozen pilot, never from arm performance, so a
    study with no TARGET cell simply cannot answer KF-3."""
    rows = _full_comparator_condition(regime_class="ROBUSTNESS")
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))
    assert ledger["kills"]["KF-3"]["status"] in {"INCONCLUSIVE", "NOT_RUN"}


def test_a_kill_whose_arms_never_ran_is_not_run_rather_than_passing():
    """The §35.2 failure: "no artefact on disk carries a kill verdict", and silence read as
    a pass. NOT_RUN and PASS must never be the same output."""
    rows = _cell_rows("spade_cf_m0", n_nonempty=12)
    cert = A.certificate_report(rows)
    ledger = A.kill_ledger(rows, cert, A.regret_pareto_report(rows, certificate=cert))
    assert ledger["kills"]["KF-4"]["status"] == "NOT_RUN"
    assert ledger["kills"]["KF-6"]["status"] == "NOT_RUN"


# ===========================================================================
# The artefacts themselves
# ===========================================================================

def test_the_three_artefacts_are_written_and_are_valid_json(tmp_path):
    """Every artefact must regenerate from frozen code and manifests (§10.1 item 7), which
    starts with being writable and readable at all."""
    rows = _full_comparator_condition()
    paths = A.write_reports(rows, out_dir=tmp_path,
                            envelope={"study_id": "spade-final-2026-08-23",
                                      "registration_commit": "c4f58d3",
                                      "code_commit": "0000000"})
    expected = {"results/final-spade-certificate.json",
                "results/final-spade-regret-pareto.json",
                "results/final-spade-kill-ledger.json"}
    assert {f"results/{Path(p).name}" for p in paths} == expected
    for p in paths:
        payload = json.loads(Path(p).read_text())
        assert payload["study_id"] == "spade-final-2026-08-23"
        assert payload["registration_commit"] == "c4f58d3"


def test_the_analyser_never_writes_over_the_file_it_was_asked_to_read(tmp_path):
    """`analyse_versionc_form1.verdict_path` records this one from experience: a derived
    output path that collides with the input **overwrote the run it was asked to read** --
    a few kB of verdict destroying hours of compute."""
    src = tmp_path / "final-spade-certificate.json"
    src.write_text(json.dumps({"study_id": "spade-final-2026-08-23", "gate_failures": [],
                               "rows": _full_comparator_condition()}))
    with pytest.raises(A.RefusedOverwrite):
        A.write_reports(_full_comparator_condition(), out_dir=tmp_path, source=src)


def test_write_reports_honours_an_explicit_map_cell_on_a_multi_cell_run(tmp_path):
    """🔴 REGRESSION. `write_reports` calls `kill_ledger(rows, cert, pareto,
    allow_partial=..., envelope=...)` without forwarding `map_cell`, even though
    `kill_ledger`'s own signature accepts one and `_family_contrasts` needs it to avoid
    `_sole_map_cell`'s multi-cell `InvalidPooling` raise.

    Found running the real pipeline against C2 (11 arms x 6 (tau_frac, gamma, alpha)
    cells): `--map-cell 0.25,0.95,0.95` was accepted by argparse and threaded through
    `regret_pareto_report` correctly, but `kill_ledger` was still called with no
    `map_cell` at all, so it fell back to `_sole_map_cell` and raised on a run that had
    just been told explicitly which cell to use. The CLI flag existed and did nothing.

    None of the 64 pre-existing tests caught this because `_full_comparator_condition`
    builds rows in exactly ONE (tau_frac, gamma, alpha) cell, so `_sole_map_cell` never
    had anything to disambiguate and `map_cell=None` was silently correct by accident.
    This fixture spans two cells specifically so the fallback path is forced to fire.
    """
    cell_a = _full_comparator_condition(tau_frac_or_quantile=0.25, gamma=0.95, alpha=0.95)
    cell_b = _full_comparator_condition(tau_frac_or_quantile=0.25, gamma=0.50, alpha=0.80)
    rows = cell_a + cell_b

    paths = A.write_reports(rows, out_dir=tmp_path, map_cell=(0.25, 0.95, 0.95),
                            envelope={"study_id": "spade-final-2026-08-23",
                                      "registration_commit": "c4f58d3",
                                      "code_commit": "0000000"})

    ledger_path = next(p for p in paths if "kill-ledger" in p)
    ledger = json.loads(Path(ledger_path).read_text())
    assert ledger["kills"]["KF-6"]["status"] in ("PASS", "FAIL", "INCONCLUSIVE"), (
        "kill_ledger must have actually adjudicated KF-6 (a map-metric kill) rather than "
        "raising InvalidPooling on the explicitly-named cell")

    pareto_path = next(p for p in paths if "regret-pareto" in p)
    pareto = json.loads(Path(pareto_path).read_text())
    # `map_cell` rides on every per-arm entry, not at the payload's top level -- checked
    # against the actual writer (line ~1135) rather than assumed.
    entries = pareto["entries"] if "entries" in pareto else pareto.get("rows", [])
    assert entries, "regret-pareto artefact produced no entries"
    for e in entries:
        assert e["map_cell"] == {"tau_frac": 0.25, "gamma": 0.95, "alpha": 0.95}
