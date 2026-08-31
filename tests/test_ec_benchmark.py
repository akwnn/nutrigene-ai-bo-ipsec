import torch
import pytest

from boec.ec_benchmark import ECConfig, CQA_NAMES, joint_success, make_ec_landscape

def test_ec_config_is_six_factor_and_fresh_seeded():
    cfg = ECConfig()
    assert cfg.n_factors == 6 and cfg.eval_seed_start == 64 and cfg.eval_seed_stop == 96
    assert cfg.min_answered_per_family == 16 and len(CQA_NAMES) == 3

def test_landscape_returns_three_cqas_and_all_six_factors_matter():
    landscape = make_ec_landscape("ec_broad", 3)
    x = torch.full((2, 6), 0.5); y = landscape.truth(x)
    assert y.shape == (2, 3)
    x2 = x.clone(); x2[:, 5] = 0.0
    assert not torch.equal(y, landscape.truth(x2))

def test_evaluator_returns_per_cqa_variances_deterministically():
    landscape = make_ec_landscape("ec_narrow", 4); x = torch.rand(5, 6)
    y1, v1 = landscape.evaluate(x); y2, v2 = landscape.evaluate(x)
    assert torch.equal(y1, y2) and torch.equal(v1, v2) and v1.shape == y1.shape
    assert torch.unique(v1).numel() > 1

def test_joint_success_requires_every_cqa_threshold():
    y = torch.tensor([[.8, .8, .7], [.8, .69, .7]])
    out = joint_success(y, (0.7, 0.7, 0.6))
    assert out.tolist() == [True, False]
    with pytest.raises(ValueError): joint_success(torch.ones(2), (0.7, 0.7, 0.6))
