"""Regression test that the DC DoE path consumes evaluator variances verbatim."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dc_runner", ROOT / "scripts" / "run_dc_doe_certificate.py")
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


def test_build_uses_exact_per_well_variance(monkeypatch):
    class Evaluator:
        pass

    evaluator = Evaluator()
    expected = torch.tensor([[0.01], [0.04], [0.09]])
    result = SimpleNamespace(
        X_visited=torch.zeros(3, 2), Y_visited=torch.ones(3, 1), Yvar_visited=expected
    )
    fake_lc = SimpleNamespace(
        kv=lambda: SimpleNamespace(p8=lambda: SimpleNamespace(DIM=2)),
        instance_for=lambda family, seed: "instance",
    )
    evaluator_factory = lambda family, instance, seed: evaluator
    fake_p = fake_lc.kv().p8()
    fake_p.evaluator_for = evaluator_factory
    fake_lc.kv = lambda: SimpleNamespace(p8=lambda: fake_p)
    monkeypatch.setattr(dc, "lc", lambda: fake_lc)
    monkeypatch.setattr("boec.doe.run_doe_arm", lambda *args, **kwargs: result)
    monkeypatch.setattr("boec.replay.unit_bounds", lambda dim: torch.zeros(dim, 2))

    (_, _, yvar), orc = dc.build("ackley", "doe", 32, 3)
    assert orc is evaluator
    assert torch.equal(yvar, expected)
