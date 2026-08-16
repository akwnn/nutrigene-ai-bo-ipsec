"""Selection rules — how a lab turns a finished campaign into one recipe.

Workstream 6. Every headline in this project scores the campaign at the **single noisy
readout**: take the well whose one measurement read highest. That is one operational
rule, and Q55 showed it is a *bad* one — the noisy argmax is the true argmax between 2%
and 18% of the time.

Real laboratories often do something else: replicate, confirm the top few, or trust a
model over any single plate reading. If the classical arm's advantage at the higher-noise
condition is just an artefact of taking the luckiest single spike, it should shrink under
those rules. If it survives, the finding is about selection generally, not about one
convention.

These are the rules. They are tested here rather than written inline in a script because
the whole point of the sensitivity run is that the *rule* is the independent variable.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.selection import (SELECTION_RULES, mean_of_replicates,
                            posterior_mean_at_visited, single_readout, top_k_confirm)


def _col(v):
    return torch.tensor(v, dtype=torch.double).reshape(-1, 1)


# --------------------------------------------------------------- single readout
def test_single_readout_picks_the_loudest_reading():
    assert single_readout(_col([0.1, 0.9, 0.4])) == 1


def test_single_readout_is_what_the_headline_rule_already_does():
    """Guards against the sensitivity run silently comparing a rule against itself.

    `reported_best_curve` locates by noisy y; this must agree, or the "baseline" column
    of the sensitivity table is not the published baseline.
    """
    from boec.diagnostics import reported_best_curve
    rng = np.random.default_rng(0)
    for _ in range(20):
        truth = _col(rng.normal(size=12))
        obs = _col(rng.normal(size=12))
        want = float(truth[single_readout(obs)])
        assert abs(reported_best_curve(truth, obs)[-1] - want) < 1e-12


# --------------------------------------------------------------- replicates
def test_averaging_replicates_rejects_a_spike_that_fools_one_reading():
    """The point of the rule, stated as a test.

    Well 0 is genuinely mediocre but reads highest once by luck. Well 2 is genuinely best.
    One reading picks the spike; the mean of two does not.
    """
    first = _col([0.95, 0.30, 0.80])     # well 0 spikes
    second = _col([0.10, 0.30, 0.82])    # and does not repeat
    assert single_readout(first) == 0
    assert mean_of_replicates(first, second) == 2


def test_replicates_must_be_the_same_shape():
    with pytest.raises(ValueError, match="same shape"):
        mean_of_replicates(_col([1.0, 2.0]), _col([1.0, 2.0, 3.0]))


# --------------------------------------------------------------- top-k confirm
def test_top_k_confirm_never_leaves_the_shortlist():
    """A confirmation run cannot promote a well the screen never shortlisted.

    Well 3 confirms best of all, but it was 4th on the first reading and k=2, so a lab
    following this protocol never measures it again and cannot pick it.
    """
    first = _col([0.9, 0.8, 0.2, 0.1])
    conf = _col([0.1, 0.5, 0.4, 0.99])
    assert top_k_confirm(first, conf, k=2) == 1


def test_top_k_confirm_with_k_of_one_is_the_single_readout():
    """Degenerate case, pinned: k=1 shortlists one well, so confirmation cannot move it."""
    first = _col([0.2, 0.7, 0.5])
    conf = _col([0.9, 0.1, 0.9])
    assert top_k_confirm(first, conf, k=1) == single_readout(first)


def test_top_k_confirm_rejects_a_k_bigger_than_the_campaign():
    with pytest.raises(ValueError, match="k="):
        top_k_confirm(_col([1.0, 2.0]), _col([1.0, 2.0]), k=5)


# --------------------------------------------------------------- posterior mean
def test_posterior_mean_at_visited_returns_a_visited_index():
    """It must choose among measured wells, never invent one.

    That is what separates this rule from the model *recommendation* scored elsewhere:
    here the lab is still making a recipe it has already run.
    """
    X = torch.rand(9, 3, dtype=torch.double)
    idx = posterior_mean_at_visited(lambda Z: Z.sum(dim=1, keepdim=True), X)
    assert 0 <= idx < X.shape[0]
    assert idx == int(torch.argmax(X.sum(dim=1)))


# --------------------------------------------------------------- the set itself
def test_every_registered_rule_returns_a_visited_index_on_the_same_data():
    """The sensitivity table compares rules on one campaign; all must be commensurable."""
    rng = np.random.default_rng(3)
    n = 15
    first, second = _col(rng.normal(size=n)), _col(rng.normal(size=n))
    X = torch.rand(n, 4, dtype=torch.double)
    picks = {
        "single": single_readout(first),
        "replicate": mean_of_replicates(first, second),
        "top3": top_k_confirm(first, second, k=3),
        "posterior": posterior_mean_at_visited(lambda Z: Z.sum(dim=1, keepdim=True), X),
    }
    assert set(picks) == set(SELECTION_RULES)
    for name, i in picks.items():
        assert 0 <= i < n, f"{name} returned {i}, outside the {n} visited wells"


def test_the_rules_actually_disagree_on_noisy_data():
    """Guards the sensitivity run from being vacuous.

    If every rule always picked the same well the whole workstream would be measuring
    nothing.
    """
    rng = np.random.default_rng(11)
    disagreements = 0
    for _ in range(40):
        first, second = _col(rng.normal(size=20)), _col(rng.normal(size=20))
        if single_readout(first) != mean_of_replicates(first, second):
            disagreements += 1
    assert disagreements >= 10, (
        f"single readout and replicate-mean agreed on all but {disagreements} of 40 "
        "noisy campaigns; the rules are not distinguishable and the run proves nothing")
