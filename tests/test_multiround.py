"""Multi-round SPADE. Adaptivity, not acquisition, is what buys certification.

LA measured this directly (`docs/SPADE-ROUND-MATCHED-SPEC.md`): strip `qlognei` from ten
adaptive rounds down to two and its answer rate collapses from 29.0% to 0.0% -- the same
0.0% every 2-round arm gets, SPADE included. The whole margin KX attributed to BO's
*design* was its *round count*.

So the lever is rounds. This generalises the fixed 40+8 two-plate design to
`n_init` + an arbitrary batch schedule, keeping the certificate-contour acquisition
(`boec.certstraddle`) that LA showed cuts regret 0.4008 -> 0.2996.
"""

import torch

from boec.multiround import multiround_design, round_schedule


def test_schedule_sums_to_the_budget():
    n_init, batches = round_schedule(budget=48, rounds=4, n_init=24)
    assert n_init + sum(batches) == 48
    assert len(batches) == 3


def test_two_rounds_is_the_committed_forty_plus_eight():
    n_init, batches = round_schedule(budget=48, rounds=2, n_init=40)
    assert (n_init, batches) == (40, [8])


def test_more_rounds_never_changes_the_total_budget():
    for r in (2, 3, 4, 6):
        n_init, batches = round_schedule(budget=48, rounds=r, n_init=24)
        assert n_init + sum(batches) == 48, (r, n_init, batches)


def test_uneven_remainder_is_absorbed_not_dropped():
    """A budget that does not divide evenly must still spend every well."""
    n_init, batches = round_schedule(budget=50, rounds=4, n_init=24)
    assert n_init + sum(batches) == 50
    assert all(b > 0 for b in batches)


def test_rounds_below_two_is_rejected():
    """One round is a static design; it is not this function's job."""
    try:
        round_schedule(budget=48, rounds=1, n_init=40)
    except ValueError:
        return
    raise AssertionError("rounds=1 should raise")


def test_n_init_larger_than_budget_is_rejected():
    try:
        round_schedule(budget=48, rounds=2, n_init=48)
    except ValueError:
        return
    raise AssertionError("no wells left for any adaptive round should raise")


class _Oracle:
    """Deterministic stand-in: f = -sum(x), fixed noise. No randomness to fight."""
    sigma_rel = 0.0
    sigma_add = 0.1

    def evaluate(self, X):
        Y = (-X.sum(dim=-1, keepdim=True)).double()
        return Y, torch.full_like(Y, 0.01)


def test_design_returns_the_requested_number_of_wells():
    X, Y, Yvar = multiround_design(_Oracle(), dim=3, seed=0, mu_max=1.0,
                                   n_init=12, batches=[4, 4], rho=0.95)
    assert X.shape == (20, 3)
    assert Y.shape == (20, 1)
    assert Yvar.shape == (20, 1)


def test_design_is_seeded_and_reproducible():
    a = multiround_design(_Oracle(), dim=3, seed=7, mu_max=1.0,
                          n_init=12, batches=[4], rho=0.95)[0]
    b = multiround_design(_Oracle(), dim=3, seed=7, mu_max=1.0,
                          n_init=12, batches=[4], rho=0.95)[0]
    assert torch.allclose(a, b)


def test_later_rounds_see_earlier_data():
    """The point of adaptivity: round 3's batch must depend on round 2's measurements.

    Same total wells, same seed, same opening -- only the SPLIT differs. If the two
    designs came out identical the extra round would be doing nothing.
    """
    one = multiround_design(_Oracle(), dim=3, seed=1, mu_max=1.0,
                            n_init=12, batches=[8], rho=0.95)[0]
    two = multiround_design(_Oracle(), dim=3, seed=1, mu_max=1.0,
                            n_init=12, batches=[4, 4], rho=0.95)[0]
    assert one.shape == two.shape
    assert not torch.allclose(one, two), "splitting a batch changed nothing"
