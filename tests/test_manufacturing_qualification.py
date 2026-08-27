from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
import yaml

from boec.manufacturing_qualification import (
    CqaDefinition,
    bonferroni_endpoint_alpha,
    qualify_multi_cqa,
)


ROOT = Path(__file__).resolve().parents[1]


def definition(name: str, *, direction: str = "greater_equal", threshold: float = 0.5):
    return CqaDefinition(
        name=name,
        units="fraction",
        threshold=threshold,
        direction=direction,
        gamma=0.95,
        assay_id=f"assay-{name}",
        assay_version="synthetic-v1",
        sigma_rel=0.10,
        sigma_add=0.01,
    )


def valid_inputs():
    X = torch.tensor([[0.0], [0.25], [0.5], [0.75]], dtype=torch.double)
    Y = torch.tensor(
        [[0.9, 0.2], [0.8, 0.6], [0.4, 0.7], [0.1, 0.9]], dtype=torch.double
    )
    Yvar = torch.full_like(Y, 0.01)
    bounds = torch.tensor([[0.0], [1.0]], dtype=torch.double)
    return X, Y, Yvar, bounds


def test_bonferroni_allocation_for_three_cqas():
    assert bonferroni_endpoint_alpha(0.95, 3) == pytest.approx(1.0 - 0.05 / 3.0)


def test_bonferroni_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="alpha"):
        bonferroni_endpoint_alpha(1.0, 2)
    with pytest.raises(ValueError, match="n_cqas"):
        bonferroni_endpoint_alpha(0.95, 1)


def test_validation_rejects_mismatched_cqa_columns():
    X, Y, Yvar, bounds = valid_inputs()
    with pytest.raises(ValueError, match="Yvar.*shape"):
        qualify_multi_cqa(X, Y, Yvar[:, :1], bounds, (definition("a"), definition("b")))


def test_validation_rejects_bad_names_and_column_labels():
    X, Y, Yvar, bounds = valid_inputs()
    with pytest.raises(ValueError, match="unique"):
        qualify_multi_cqa(
            X,
            Y,
            Yvar,
            bounds,
            (definition("same"), definition("same")),
        )
    with pytest.raises(ValueError, match="cqa_names"):
        qualify_multi_cqa(
            X,
            Y,
            Yvar,
            bounds,
            (definition("a"), definition("b")),
            cqa_names=("b", "a"),
        )


@pytest.mark.parametrize(
    "bad",
    [
        ("nan", lambda X, Y, V, B: (X.clone().fill_(float("nan")), Y, V, B)),
        ("negative variance", lambda X, Y, V, B: (X, Y, V.clone().fill_(-1.0), B)),
    ],
)
def test_validation_rejects_nonfinite_grid_and_invalid_variance(bad):
    _, make_bad = bad
    X, Y, Yvar, bounds = make_bad(*valid_inputs())
    with pytest.raises(ValueError, match="finite|variance"):
        qualify_multi_cqa(X, Y, Yvar, bounds, (definition("a"), definition("b")))


def test_validation_rejects_incomplete_noise_pair():
    X, Y, Yvar, bounds = valid_inputs()
    with pytest.raises(ValueError, match="noise"):
        qualify_multi_cqa(
            X,
            Y,
            Yvar,
            bounds,
            (
                definition("a"),
                CqaDefinition(
                    name="b",
                    units="fraction",
                    threshold=0.5,
                    direction="greater_equal",
                    gamma=0.95,
                    assay_id="assay-b",
                    assay_version="synthetic-v1",
                    sigma_rel=0.1,
                    sigma_add=None,
                ),
            ),
        )


def test_lower_tail_transform_intersection_and_setpoint(monkeypatch):
    X, Y, Yvar, bounds = valid_inputs()
    seen_y = []
    seen_alphas = []
    masks = (
        torch.tensor([[True, True, False, False], [True, True, False, False]]),
        torch.tensor([[True, False, True, False], [True, False, True, False]]),
    )

    def fake_build_gp(train_X, train_Y, train_Yvar, train_bounds, **kwargs):
        seen_y.append(train_Y.clone())
        return len(seen_y) - 1

    def fake_draws(model, grid, tau, gamma, n_draws, seed, **kwargs):
        assert grid.shape == X.shape
        assert n_draws == 2
        return masks[model]

    def fake_certificate(draws, alpha, n_rho, volume_rule):
        seen_alphas.append(alpha)
        mask = draws[0].clone()
        return SimpleNamespace(
            mask=mask,
            volume=float(mask.double().mean()),
            selection_containment=0.98,
            crossfit_containment=0.96,
        )

    monkeypatch.setattr("boec.manufacturing_qualification.build_gp", fake_build_gp)
    monkeypatch.setattr(
        "boec.manufacturing_qualification.reliable_set_draws", fake_draws
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.conservative_set_split", fake_certificate
    )

    result = qualify_multi_cqa(
        X,
        Y,
        Yvar,
        bounds,
        (definition("identity"), definition("viability", direction="less_equal")),
        alpha=0.95,
        n_draws=2,
        utility=torch.tensor([0.1, 0.8, 0.5, 0.3], dtype=torch.double),
        truth_masks=(masks[0][0], masks[1][0]),
    )

    assert torch.equal(seen_y[0].flatten(), Y[:, 0])
    assert torch.equal(seen_y[1].flatten(), -Y[:, 1])
    assert seen_alphas == [pytest.approx(0.975), pytest.approx(0.975)]
    assert torch.equal(result.joint_mask, torch.tensor([True, False, False, False]))
    assert result.status == "QUALIFIED"
    assert result.joint_volume == pytest.approx(0.25)
    assert result.setpoint_index == 0
    assert result.limiting_cqa == "identity"
    assert result.endpoint_results[1].direction == "less_equal"
    assert result.endpoint_results[0].truth_containment is True


def test_empty_intersection_abstains_without_setpoint(monkeypatch):
    X, Y, Yvar, bounds = valid_inputs()

    monkeypatch.setattr(
        "boec.manufacturing_qualification.build_gp", lambda *args, **kwargs: 0
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.reliable_set_draws",
        lambda *args, **kwargs: torch.tensor([[True, False, False, False], [True, False, False, False]]),
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.conservative_set_split",
        lambda *args, **kwargs: SimpleNamespace(
            mask=torch.tensor([False, False, False, False]),
            volume=0.0,
            selection_containment=None,
            crossfit_containment=None,
        ),
    )

    result = qualify_multi_cqa(
        X,
        Y,
        Yvar,
        bounds,
        (definition("a"), definition("b")),
        n_draws=2,
        utility=torch.ones(4, dtype=torch.double),
    )
    assert result.status == "ABSTAIN_EMPTY_JOINT"
    assert result.setpoint_index is None
    assert result.setpoint is None
    assert result.limiting_cqa is None


def test_limiting_cqa_and_setpoint_ties_are_deterministic(monkeypatch):
    X, Y, Yvar, bounds = valid_inputs()
    masks = iter(
        [
            torch.tensor([True, True, False, False]),
            torch.tensor([True, True, False, False]),
        ]
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.build_gp", lambda *args, **kwargs: 0
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.reliable_set_draws",
        lambda *args, **kwargs: next(masks).unsqueeze(0).repeat(2, 1),
    )
    monkeypatch.setattr(
        "boec.manufacturing_qualification.conservative_set_split",
        lambda draws, *args, **kwargs: SimpleNamespace(
            mask=draws[0], volume=0.5, selection_containment=1.0, crossfit_containment=1.0
        ),
    )
    result = qualify_multi_cqa(
        X,
        Y,
        Yvar,
        bounds,
        (definition("alpha"), definition("beta")),
        n_draws=2,
        utility=torch.tensor([1.0, 1.0, 0.0, 0.0], dtype=torch.double),
    )
    assert result.limiting_cqa == "alpha"
    assert result.setpoint_index == 0


def test_seeded_runs_do_not_mutate_inputs_and_per_cqa_seeds_are_stable(monkeypatch):
    X, Y, Yvar, bounds = valid_inputs()
    originals = tuple(t.clone() for t in (X, Y, Yvar, bounds))
    seeds = []
    monkeypatch.setattr(
        "boec.manufacturing_qualification.build_gp", lambda *args, **kwargs: 0
    )

    def fake_draws(*args, **kwargs):
        seeds.append(kwargs["seed"] if "seed" in kwargs else args[5])
        return torch.ones((2, 4), dtype=torch.bool)

    monkeypatch.setattr("boec.manufacturing_qualification.reliable_set_draws", fake_draws)
    monkeypatch.setattr(
        "boec.manufacturing_qualification.conservative_set_split",
        lambda draws, *args, **kwargs: SimpleNamespace(
            mask=draws[0], volume=1.0, selection_containment=1.0, crossfit_containment=1.0
        ),
    )
    first = qualify_multi_cqa(X, Y, Yvar, bounds, (definition("a"), definition("b")), n_draws=2)
    second = qualify_multi_cqa(X, Y, Yvar, bounds, (definition("a"), definition("b")), n_draws=2)
    assert seeds[:2] == seeds[2:]
    assert torch.equal(first.joint_mask, second.joint_mask)
    for got, original in zip((X, Y, Yvar, bounds), originals):
        assert torch.equal(got, original)


def test_registered_synthetic_configuration_is_explicit():
    config_path = ROOT / "configs" / "experiment" / "spade-multi-cqa-qualification.yaml"
    assert config_path.exists()
    config = yaml.safe_load(config_path.read_text())
    assert config["protocol"]["certificate_volume_rule"] == "smallest"
    assert config["protocol"]["predictive_observation_noise"] == "assay_relative_additive"
    assert config["protocol"]["base_seed"] == 270827
    assert [entry["name"] for entry in config["cqas"]] == ["identity", "viability", "yield"]
    assert config["claim_scope"] == "computational_synthetic_only"
