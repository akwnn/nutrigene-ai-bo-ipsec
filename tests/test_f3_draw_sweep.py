"""F3 · the draw × seed sweep's contract, checked without running a campaign.

Registered in `docs/OPEN-QUESTIONS.md` (commit 445c028) **before this runner existed**.

WHAT THIS FILE PINS, AND WHY EACH ONE COST SOMETHING
-----------------------------------------------------
1. **The draw levels must be NESTED subsamples.** `torch.randn(N, n_draws)` fills
   row-major, so calling it at 512 and again at 1024 gives a *completely different*
   realisation for every grid point after the first — verified below. A sweep built that
   way confounds "more draws" with "different draws", which is the exact confound this
   project spent Part IV isolating. The runner draws ONCE at `max(DRAW_LEVELS)` and
   slices, which also makes the sweep paired.
2. **Exact binomial tails, never a normal approximation** (Erratum 21). At n=50, p=0.95
   the continuity-corrected normal is 5.31× off at X=42, and that substitution is what
   turned §14's "one failure survives Holm" into an artefact.
3. **No constant may be a `max(observed)`** (Erratum 20).
4. **A negative control cell must be registered.** The bias is a maximum over near-tied
   candidates, so it must be near-absent at γ=0.50 where the quantiles separate. A sweep
   that moves there too is measuring something other than selection bias.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import torch
from scipy.stats import binom, norm

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def f3():
    spec = importlib.util.spec_from_file_location(
        "f3", ROOT / "scripts" / "run_f3_draw_sweep.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["f3"] = mod
    spec.loader.exec_module(mod)
    return mod


# ======================================================================================
# 1. THE NESTING PROPERTY — the design decision this file exists to pin
# ======================================================================================
def test_torch_randn_is_NOT_nested_across_n_draws():
    """The motivating fact, asserted so nobody "simplifies" the runner back into it.

    This is a property of torch, not of our code, and it is why `nested_draws` exists.
    """
    z512 = torch.randn(5, 512, generator=torch.Generator().manual_seed(0),
                       dtype=torch.double)
    z1024 = torch.randn(5, 1024, generator=torch.Generator().manual_seed(0),
                        dtype=torch.double)
    assert not torch.equal(z512, z1024[:, :512]), (
        "if this ever passes, torch changed its fill order and the runner could be "
        "simplified -- but check it at EVERY row, not just the first")
    assert z512[0, 0] == z1024[0, 0], "row 0 does start the same, which is the trap"
    assert z512[1, 0] != z1024[1, 0], "row 1 shifts -- the fill is row-major"


def test_draw_levels_are_nested_subsamples(f3):
    """Every smaller draw level must be a prefix of the largest, exactly.

    Without this the sweep cannot attribute a containment change to the draw count.
    """
    n_pts, seed = 7, 3
    mean = torch.zeros(n_pts, dtype=torch.double)
    L = torch.eye(n_pts, dtype=torch.double)
    full = f3.nested_draws(mean, L, seed=seed, n_draws=max(f3.DRAW_LEVELS))
    assert full.shape == (max(f3.DRAW_LEVELS), n_pts)
    for n in f3.DRAW_LEVELS:
        sub = f3.nested_draws(mean, L, seed=seed, n_draws=n)
        assert sub.shape == (n, n_pts)
        assert torch.equal(sub, full[:n]), (
            f"draw level {n} is not a prefix of {max(f3.DRAW_LEVELS)}; the sweep would "
            f"confound draw count with a different noise realisation")


def test_nested_draws_is_seed_deterministic(f3):
    n_pts = 4
    mean = torch.zeros(n_pts, dtype=torch.double)
    L = torch.eye(n_pts, dtype=torch.double)
    a = f3.nested_draws(mean, L, seed=11, n_draws=64)
    b = f3.nested_draws(mean, L, seed=11, n_draws=64)
    c = f3.nested_draws(mean, L, seed=12, n_draws=64)
    assert torch.equal(a, b)
    assert not torch.equal(a, c)


# ======================================================================================
# 2. EXACT TAILS — Erratum 21
# ======================================================================================
def test_binomial_tail_is_exact_and_is_not_the_normal_approximation(f3):
    """The substitution that made §14's correction wrong, asserted against directly."""
    for x, n, p in ((42, 50, 0.95), (44, 50, 0.95), (45, 50, 0.95), (180, 200, 0.95)):
        assert f3.exact_tail(x, n, p) == pytest.approx(binom.cdf(x, n, p), rel=1e-12)

    # and it must NOT be the continuity-corrected normal, which is 5.31x off at X=42
    z = (42 + 0.5 - 50 * 0.95) / (50 * 0.95 * 0.05) ** 0.5
    assert f3.exact_tail(42, 50, 0.95) / norm.cdf(z) > 5.0, (
        "the exact tail must differ sharply from the normal approximation here; "
        "if it does not, exact_tail is the approximation")


def test_the_seeds_axis_is_what_makes_the_experiment_powered(f3):
    """Why n=200 was registered: at n=50 the design cannot reach significance.

    This is the arithmetic that justified changing a registered design, so it is pinned.
    """
    assert binom.cdf(45, 50, 0.95) > 0.10, "45/50 can never reach p<0.10"
    assert binom.cdf(42, 50, 0.95) * 72 > 0.05, "after Holm x72 even 42/50 fails at 0.05"

    # The comparison that justifies the seeds axis: the SAME containment rate, callable
    # at n=200 and not at n=50. 0.840 is section 14's worst observed cell.
    assert binom.cdf(42, 50, 0.95) * 72 > 0.05, "0.840 at n=50 cannot be called"
    assert binom.cdf(168, 200, 0.95) * 72 < 0.05, (
        "0.840 at n=200 MUST be callable -- this is the whole reason for the seeds axis")

    # The detection threshold at n=200, asserted so the runner's power is a known number
    # rather than an impression. 170/200 = 0.850 is the worst containment still callable.
    assert binom.cdf(170, 200, 0.95) * 72 < 0.05
    assert binom.cdf(171, 200, 0.95) * 72 < 0.05, "and everything below it"

    # NOT 180/200. The registration first claimed that survived Holm x72; it does not
    # (tail 0.00266, x72 = 0.192). Pinned so the wrong figure cannot come back.
    assert binom.cdf(180, 200, 0.95) * 72 > 0.05, (
        "180/200 does NOT survive Holm x72 -- see Erratum 27")
    assert f3.N_SEEDS == 200


# ======================================================================================
# 3. THE MECHANISM, AND WHY THE CIRCULAR STATISTIC CANNOT SEE IT
# ======================================================================================
def test_circular_containment_cannot_fall_below_alpha(f3):
    """`ce_contain` is what `conservative_estimate` selects on, so it is a tautology.

    Pinned because F3's whole point is that the bias is invisible to the statistic the
    project was reporting.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from boec.vorobev import conservative_estimate, containment_probability

    g = torch.Generator().manual_seed(0)
    draws = torch.randn(256, 40, generator=g, dtype=torch.double)
    for alpha in (0.50, 0.80, 0.95):
        ce = conservative_estimate(draws, theta=0.0, alpha=alpha, n_rho=64)
        if int(ce.sum()) == 0:
            continue
        assert containment_probability(draws, ce, 0.0) >= alpha - 1e-12, (
            "the in-sample statistic fell below alpha, which it cannot do by "
            "construction -- conservative_estimate changed")


def test_negative_control_cell_is_registered(f3):
    """γ=0.50 must be in the sweep: the bias should be near-absent where quantiles separate."""
    gammas = {g for g, _ in f3.CELLS}
    assert 0.50 in gammas, (
        "without a well-separated control cell, a draw-count trend cannot be "
        "attributed to selection bias rather than to draws generally")
    assert (0.99, 0.60) in f3.CELLS, "the peak-bias cell must be present"


def test_n_rho_is_swept_because_the_bias_is_a_maximum_over_n_rho(f3):
    assert set(f3.N_RHO_LEVELS) == {16, 64}


# ======================================================================================
# 4. ERRATUM 20 — no fitted constants
# ======================================================================================
def test_no_constant_is_derived_from_observed_data(f3):
    """A `max(observed)` masquerading as a bound is what broke P6 (§18)."""
    src = (ROOT / "scripts" / "run_f3_draw_sweep.py").read_text()
    for banned in ("max(observed", "worst_observed", "= max(errs", "measured bound"):
        assert banned not in src, f"{banned!r} suggests a fitted tolerance (Erratum 20)"


def test_output_path_has_a_gitignore_negation(f3):
    """`results/*` is ignored by default; a registered artefact needs its negation."""
    gi = (ROOT / ".gitignore").read_text()
    assert "!results/f3-draw-sweep.json" in gi
    assert f3.OUT.name == "f3-draw-sweep.json"
