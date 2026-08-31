from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

import boec.doe as doe
from scripts import run_dc_doe_certificate as dc


@pytest.mark.parametrize("arm,function_name", [
    ("doe", "run_doe_arm"),
    ("doe_unscreened", "run_doe_unscreened_arm"),
])
def test_dc_build_uses_the_exact_variance_returned_by_the_doe_arm(
        monkeypatch, arm, function_name):
    X = torch.zeros(3, 2, dtype=torch.double)
    Y = torch.tensor([[0.1], [0.2], [0.3]], dtype=torch.double)
    Yvar = torch.tensor([[0.001], [0.004], [0.009]], dtype=torch.double)
    result = SimpleNamespace(X_visited=X, Y_visited=Y, Yvar_visited=Yvar)

    def fake_arm(*args, **kwargs):
        return result

    monkeypatch.setattr(doe, function_name, fake_arm)
    oracle = SimpleNamespace(truth=lambda values: values[:, :1])
    protocol = SimpleNamespace(
        DIM=2,
        evaluator_for=lambda family, instance, seed: oracle,
    )
    fake_lc = SimpleNamespace(
        kv=lambda: SimpleNamespace(p8=lambda: protocol),
        instance_for=lambda family, seed: f"{family}-{seed}",
    )
    monkeypatch.setattr(dc, "lc", lambda: fake_lc)

    (got_X, got_Y, got_Yvar), got_oracle = dc.build("hill", arm, seed=3, rounds=3)

    assert got_oracle is oracle
    assert got_X is X
    assert got_Y is Y
    assert got_Yvar is Yvar
    assert torch.unique(got_Yvar).numel() == 3
