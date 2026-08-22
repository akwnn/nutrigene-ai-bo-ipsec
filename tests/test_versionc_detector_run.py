"""Version C section 3.2's fitting run -- statistics on the THREE FITTING FAMILIES only.

Section 3.3's protocol: fit the rule and its threshold on hill, levy and rosenbrock;
freeze both; score ONCE on hartmann6 and ackley. This runner must therefore refuse to
touch the held-out families at all -- a fitting run that can reach hartmann6 is one
`--family` flag away from tuning on the evaluation set.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_run_versionc_detector", ROOT / "scripts" / "run_versionc_detector.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)


def test_only_the_three_fitting_families_are_reachable():
    """The held-out families must not be constructible from this runner at all."""
    assert set(D.FITTING_FAMILIES) == {"hill", "levy", "rosenbrock"}
    assert "hartmann6" not in D.FITTING_FAMILIES
    assert "ackley" not in D.FITTING_FAMILIES


def test_asking_for_a_held_out_family_raises_by_name():
    """Not a KeyError. A named refusal, so the traceback says why rather than looking
    like a typo -- this is the single most consequential mistake available here."""
    with pytest.raises(D.HeldOutFamily) as e:
        D.evaluator_for("hartmann6", dim=6, sigma=0.10, seed=0)
    assert "hartmann6" in str(e.value)
    with pytest.raises(D.HeldOutFamily):
        D.evaluator_for("ackley", dim=6, sigma=0.10, seed=0)


def test_an_unknown_family_raises_too():
    with pytest.raises(D.HeldOutFamily):
        D.evaluator_for("not_a_family", dim=6, sigma=0.10, seed=0)


@pytest.mark.parametrize("family", ["hill", "levy", "rosenbrock"])
def test_each_fitting_family_builds_an_evaluator_and_a_plate(family):
    # d=6: `load_ensemble` is committed at 6 and 8 only, and hill instances must come
    # from that committed ensemble rather than be sampled fresh -- a threshold fitted on
    # freshly drawn landscapes would not be fitted on the population the study reports.
    ev, bounds, mu_max = D.evaluator_for(family, dim=6, sigma=0.10, seed=0)
    X, Y, Yvar = D.plate_one(ev, bounds, n=16, seed=0)
    assert X.shape == (16, 6)
    assert Y.shape[0] == 16 and Yvar.shape[0] == 16
    assert mu_max == pytest.approx(mu_max)  # finite


def test_a_row_carries_every_detector_statistic_and_no_truth():
    """The row is the fitting set. If a truth-derived column leaked in, the threshold
    fitted on it would not be computable at run time on a real plate."""
    row = D.score_one("levy", dim=3, sigma=0.10, seed=0, n_plate1=16,
                      grid_n=256, n_bins=8)  # levy is analytic at any d
    for key in ("n_components_plausible", "n_local_maxima", "additive_share",
                "ard_separation_ratio", "additive_refit_residual", "family"):
        assert key in row
    forbidden = [k for k in row if "truth" in k or "regret" in k or k == "optimum_value"]
    assert not forbidden, f"oracle-derived columns leaked into the fitting set: {forbidden}"


def test_n_local_maxima_as_specified_is_degenerate_at_this_budget():
    """**An alarm, not a target.** Section 3.2 offers "count of distinct local maxima of
    the posterior mean whose LCB clears the second-highest UCB" as a candidate statistic.

    Measured at the real operating point -- 40 wells, d=6, sigma=0.10, the 20,000-point
    Sobol grid -- it is **identically zero**, on both hill and levy. An LCB has to exceed
    the *second-highest UCB among peaks* to count, and at 0.49 neighbours per lengthscale
    the posterior is nowhere near tight enough for that to happen. A statistic that cannot
    vary cannot detect anything, so this candidate is **not viable at this budget** and
    the fitting run must not select it.

    `n_peaks_raw` -- local maxima of the posterior mean on the neighbourhood graph, with
    no confidence bar -- is the usable form and does vary (135 and 149 on the same two
    fits). It is reported alongside.

    If the budget or the noise level ever moves far enough that this test fails, the
    candidate has become viable and this docstring has stopped being true out loud.
    """
    rows = [D.score_one(fam, dim=6, sigma=0.10, seed=0, n_plate1=40,
                        grid_n=20_000, n_bins=20)
            for fam in ("hill", "levy")]
    assert all(r["n_local_maxima"] == 0 for r in rows), (
        "n_local_maxima is no longer identically zero at 40 wells / d=6 / sigma=0.10; "
        "the candidate has become viable and the registration should say so")
    assert all(r["n_peaks_raw"] > 0 for r in rows)
    assert len({r["n_peaks_raw"] for r in rows}) > 1, "the usable form must vary too"
