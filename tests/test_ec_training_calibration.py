from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from boec.ec_calibration import (
    ECTrainingCandidate,
    TrainingContainmentRecord,
    boundary_candidates,
    choose_training_candidate,
    per_cqa_lower_utility,
)


def test_training_selector_rejects_any_evaluation_seed():
    candidate = ECTrainingCandidate(
        inflation_by_cqa=(1.0, 1.0, 1.0), candidate_density=128
    )
    with pytest.raises(ValueError, match="training seeds"):
        TrainingContainmentRecord(
            family="ec_broad", seed=64, contained_by_cqa=(True, True, True)
        )


def test_training_selector_requires_one_sided_90_percent_joint_containment():
    conservative = ECTrainingCandidate(
        inflation_by_cqa=(1.5, 1.5, 1.5), candidate_density=256
    )
    undercovered = ECTrainingCandidate(
        inflation_by_cqa=(1.0, 1.0, 1.0), candidate_density=64
    )
    good = tuple(
        TrainingContainmentRecord("ec_narrow", seed, (True, True, True))
        for seed in range(64)
    )
    bad = tuple(
        TrainingContainmentRecord("ec_narrow", seed, (seed < 12, True, True))
        for seed in range(16)
    )
    selected = choose_training_candidate({undercovered: bad, conservative: good})
    assert selected.candidate == conservative
    assert selected.joint_lower_bound >= 0.90


def test_per_cqa_utility_uses_each_endpoint_inflation_and_weakest_cqa():
    models = (
        SimpleNamespace(mean=torch.tensor([[0.90], [0.82]], dtype=torch.double),
                        variance=torch.tensor([[0.01], [0.01]], dtype=torch.double)),
        SimpleNamespace(mean=torch.tensor([[0.90], [0.80]], dtype=torch.double),
                        variance=torch.tensor([[0.01], [0.01]], dtype=torch.double)),
        SimpleNamespace(mean=torch.tensor([[0.70], [0.68]], dtype=torch.double),
                        variance=torch.tensor([[0.01], [0.01]], dtype=torch.double)),
    )
    utility = per_cqa_lower_utility(
        models, torch.zeros(2, 6), thresholds=(0.7, 0.7, 0.6),
        inflation_by_cqa=(1.0, 2.0, 1.0),
    )
    assert utility.shape == (2, 1)
    # Candidate 0's limiting CQA is viability after its larger calibrated band.
    assert utility[0].item() == pytest.approx((0.90 - .20) / .70)
    assert utility[1].item() == pytest.approx((0.80 - .20) / .70)


def test_boundary_candidates_are_exact_and_reserved_for_difficult_families():
    bounds = torch.stack((torch.zeros(6), torch.ones(6)))
    candidates = boundary_candidates(bounds, n=8, seed=9)
    assert candidates.shape == (8, 6)
    assert ((candidates == 0.0) | (candidates == 1.0)).any(dim=1).all()
    assert torch.unique(candidates, dim=0).shape[0] == 8


def test_training_seed_narrow_campaign_keeps_budget_and_boundary_exploration():
    import sys

    sys.path.insert(0, "scripts")
    import run_ec_benchmark as runner  # noqa: E402

    campaign = runner._run_arm("ec_narrow", 0, "spade", test_only=True)
    assert campaign.X.shape == (runner.WELLS, 6)
    assert torch.unique(campaign.X, dim=0).shape[0] == runner.WELLS
    # Narrow's adaptive batch is now interior local refinement rather than
    # literal hypercube-corner exploration (the optimum is interior).
    assert runner._BOUNDARY_RECIPES["ec_narrow"] == 0
    assert runner._LOCAL_RECIPES["ec_narrow"] == 4


def test_training_calibration_menu_includes_predeclared_heterogeneous_tails():
    import sys

    sys.path.insert(0, "scripts")
    import calibrate_ec_training as calibration  # noqa: E402

    inflations = {candidate.inflation_by_cqa for candidate in calibration.CANDIDATES}
    assert (2.0, 1.5, 2.0) in inflations
    assert (3.0, 2.0, 3.0) in inflations
    assert len(calibration.CANDIDATES) == 12
