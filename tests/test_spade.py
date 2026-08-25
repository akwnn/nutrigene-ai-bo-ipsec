"""Contract tests for the unified 48-evaluation SPADE protocol."""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, replace

import pytest
import torch

from boec.spade import (
    SpadeCampaignResult,
    SpadeConfig,
    run_qlognei48,
    run_sobol48,
    run_spade,
)


D = 6
BOUNDS = torch.stack(
    [torch.zeros(D, dtype=torch.double), torch.ones(D, dtype=torch.double)]
)


class TruthTrapEvaluator:
    """A deterministic evaluator that fails immediately on oracle access."""

    def __init__(self) -> None:
        self.calls: list[torch.Tensor] = []

    def evaluate(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self.calls.append(X.detach().clone())
        y = (
            0.6
            + 0.2 * torch.sin(2 * torch.pi * X[:, :1])
            - 0.05 * (X[:, 1:] - 0.35).square().sum(dim=1, keepdim=True)
        )
        return y.double(), torch.full_like(y, 0.01, dtype=torch.double)

    def truth(self, X: torch.Tensor) -> torch.Tensor:  # pragma: no cover - must not run
        raise AssertionError("campaign decision code accessed oracle truth")


class EvaluateOnly:
    def evaluate(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        y = X.mean(dim=1, keepdim=True)
        return y, torch.full_like(y, 0.01)


@pytest.mark.parametrize("opening,rounds", [(32, 5), (40, 3), (44, 2)])
def test_spade_uses_exactly_48_unique_evaluations(opening: int, rounds: int):
    evaluator = TruthTrapEvaluator()
    result = run_spade(
        evaluator,
        BOUNDS,
        SpadeConfig(opening=opening, policy="fixed_hybrid", root_seed=7),
        tau=0.5,
        fast=True,
    )

    assert isinstance(result, SpadeCampaignResult)
    assert result.X.shape == (48, D)
    assert result.Y.shape == result.Yvar.shape == (48, 1)
    assert torch.unique(result.X, dim=0).shape[0] == 48
    assert result.rounds == rounds
    assert sum(batch.shape[0] for batch in evaluator.calls) == 48
    assert [log.n_train_before for log in result.round_logs] == [
        0,
        *range(opening, 48, 4),
    ]


@pytest.mark.parametrize("bad", [31, 33, 41, 45, 48])
def test_unregistered_openings_refuse(bad: int):
    with pytest.raises(ValueError, match="opening"):
        SpadeConfig(opening=bad)


def test_validity_gated_refuses_to_invent_a_threshold():
    with pytest.raises(ValueError, match="tau"):
        run_spade(
            TruthTrapEvaluator(),
            BOUNDS,
            SpadeConfig(opening=44, policy="validity_gated", root_seed=7),
            fast=True,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("budget", 52, "budget"),
        ("batch_size", 2, "batch_size"),
        ("policy", "weighted_blend", "policy"),
        ("candidate_menu_size", 8_192, "candidate_menu_size"),
        ("reference_grid_size", 1_024, "reference_grid_size"),
        ("fit_restarts", 3, "fit_restarts"),
        ("qlognei_mc_samples", 128, "qlognei_mc_samples"),
        ("gamma", 0.90, "gamma"),
        ("boundary_ess_min", 31, "boundary_ess_min"),
        ("root_seed", -1, "root_seed"),
    ],
)
def test_config_refuses_invalid_or_unregistered_values(field, value, message):
    kwargs = {field: value}
    with pytest.raises(ValueError, match=message):
        SpadeConfig(**kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opening", 40.0),
        ("opening", True),
        ("budget", 48.0),
        ("budget", True),
        ("batch_size", 4.0),
        ("batch_size", True),
        ("candidate_menu_size", 16_384.0),
        ("candidate_menu_size", True),
        ("reference_grid_size", 2_048.0),
        ("reference_grid_size", True),
        ("fit_restarts", 4.0),
        ("fit_restarts", True),
        ("qlognei_mc_samples", 256.0),
        ("qlognei_mc_samples", True),
        ("boundary_ess_min", 32.0),
        ("boundary_ess_min", True),
        ("root_seed", 7.0),
        ("root_seed", True),
    ],
)
def test_integer_contracts_reject_floats_and_bools(field, value):
    with pytest.raises(ValueError, match=field):
        SpadeConfig(**{field: value})


def test_config_is_frozen_and_digest_is_canonical_and_complete():
    config = SpadeConfig(opening=40, policy="validity_gated", root_seed=13)
    decoded = json.loads(config.canonical_json)

    assert list(decoded) == sorted(decoded)
    assert decoded["candidate_menu_size"] == 16_384
    assert decoded["reference_grid_size"] == 2_048
    assert decoded["fit_restarts"] == 4
    assert decoded["qlognei_mc_samples"] == 256
    assert len(config.protocol_digest) == 64
    assert config.protocol_digest == SpadeConfig(
        opening=40, policy="validity_gated", root_seed=13
    ).protocol_digest
    assert config.protocol_digest != SpadeConfig(
        opening=44, policy="validity_gated", root_seed=13
    ).protocol_digest
    assert config.protocol_digest != SpadeConfig(
        opening=40, policy="validity_gated", root_seed=14
    ).protocol_digest
    with pytest.raises(FrozenInstanceError):
        config.opening = 32  # type: ignore[misc]


def test_fast_path_is_cryptographically_test_only_and_cannot_masquerade():
    config = SpadeConfig(opening=44, policy="staged", root_seed=3)
    expected_json = config.canonical_json
    expected_digest = config.protocol_digest

    result = run_spade(
        TruthTrapEvaluator(), BOUNDS, config, tau=0.5, fast=True
    )

    assert config.canonical_json == expected_json
    assert result.protocol_digest == expected_digest
    assert result.config == config
    assert result.execution_mode == "TEST_ONLY"
    assert result.registered is False
    assert result.effective_settings.candidate_menu_size == 64
    assert result.effective_settings.reference_grid_size == 64
    assert result.effective_settings.fit_restarts == 1
    assert result.effective_settings.qlognei_mc_samples == 16
    assert result.run_digest != result.protocol_digest
    assert all(log.run_digest == result.run_digest for log in result.round_logs)
    assert all(log.execution_mode == "TEST_ONLY" for log in result.round_logs)
    assert all(log.registered is False for log in result.round_logs)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.execution_mode = "REGISTERED"  # type: ignore[misc]
    with pytest.raises(ValueError, match="registered|REGISTERED"):
        replace(result, execution_mode="REGISTERED", registered=True)


def test_nonfast_sobol_run_is_registered_with_full_effective_settings():
    result = run_sobol48(
        TruthTrapEvaluator(), BOUNDS, root_seed=5, tau=0.5, fast=False
    )

    assert result.execution_mode == "REGISTERED"
    assert result.registered is True
    assert result.effective_settings.candidate_menu_size == 16_384
    assert result.effective_settings.reference_grid_size == 2_048
    assert result.effective_settings.fit_restarts == 4
    assert result.effective_settings.qlognei_mc_samples == 256


def test_fixed_hybrid_assigns_whole_batches_without_scalarization():
    result = run_spade(
        TruthTrapEvaluator(),
        BOUNDS,
        SpadeConfig(opening=32, policy="fixed_hybrid", root_seed=17),
        tau=0.5,
        fast=True,
    )

    assert [log.objective for log in result.round_logs] == [
        "sobol_opening",
        "qlognei",
        "global_ivr",
        "qlognei",
        "global_ivr",
    ]
    assert [log.scheduled_objective for log in result.round_logs] == [
        "sobol_opening",
        "qlognei",
        "global_ivr",
        "qlognei",
        "global_ivr",
    ]
    assert all(log.objective_values is not None for log in result.round_logs[1:])
    assert all(log.Y_observed is None for log in result.round_logs)
    assert result.terminal_fit_seed is not None
    assert result.terminal_fit_diagnostics


def test_validity_gate_records_and_uses_only_pre_outcome_model_diagnostics(monkeypatch):
    def stable_boundary(_model, X, _tau):
        return torch.linspace(0.60, 0.99, X.shape[0], dtype=torch.double)

    monkeypatch.setattr("boec.spade.model_reliability_probability", stable_boundary)
    result = run_spade(
        TruthTrapEvaluator(),
        BOUNDS,
        SpadeConfig(opening=40, policy="validity_gated", root_seed=19),
        tau=0.5,
        fast=True,
    )

    map_log = result.round_logs[2]
    assert map_log.scheduled_objective == "map"
    assert map_log.objective == "boundary_ivr"
    assert map_log.reliable_count > 0
    assert map_log.boundary_ess >= 32
    assert map_log.gate_eligible is True


def test_validity_gate_falls_back_when_reliable_region_is_empty(monkeypatch):
    monkeypatch.setattr(
        "boec.spade.model_reliability_probability",
        lambda _model, X, _tau: torch.full((X.shape[0],), 0.2, dtype=torch.double),
    )
    result = run_spade(
        TruthTrapEvaluator(),
        BOUNDS,
        SpadeConfig(opening=40, policy="validity_gated", root_seed=23),
        tau=0.5,
        fast=True,
    )

    map_log = result.round_logs[2]
    assert map_log.scheduled_objective == "map"
    assert map_log.objective == "global_ivr"
    assert map_log.reliable_count == 0
    assert map_log.gate_eligible is False


def test_staged_is_qlognei_only_after_opening():
    result = run_spade(
        TruthTrapEvaluator(),
        BOUNDS,
        SpadeConfig(opening=32, policy="staged", root_seed=29),
        tau=0.5,
        fast=True,
    )
    assert {log.objective for log in result.round_logs[1:]} == {"qlognei"}


def test_qlognei48_uses_registered_14_plus_eight_fours_plus_two_schedule():
    evaluator = TruthTrapEvaluator()
    result = run_qlognei48(evaluator, BOUNDS, root_seed=31, tau=0.5, fast=True)

    assert result.X.shape == (48, D)
    assert result.rounds == 10
    assert [log.X_proposed.shape[0] for log in result.round_logs] == [14] + [4] * 8 + [2]
    assert [log.objective for log in result.round_logs] == ["sobol_opening"] + [
        "qlognei"
    ] * 9
    assert torch.unique(result.X, dim=0).shape[0] == 48
    assert sum(batch.shape[0] for batch in evaluator.calls) == 48


def test_sobol48_is_one_complete_design_and_uses_common_terminal_fit():
    evaluator = TruthTrapEvaluator()
    result = run_sobol48(evaluator, BOUNDS, root_seed=37, tau=0.5, fast=True)

    assert result.X.shape == (48, D)
    assert result.rounds == 1
    assert len(evaluator.calls) == 1
    assert result.round_logs[0].objective == "sobol48"
    assert result.terminal_model is not None


def test_all_runners_accept_an_evaluator_with_only_evaluate():
    assert run_spade(
        EvaluateOnly(),
        BOUNDS,
        SpadeConfig(opening=44, policy="staged", root_seed=41),
        tau=0.5,
        fast=True,
    ).X.shape[0] == 48
    assert run_sobol48(
        EvaluateOnly(), BOUNDS, root_seed=41, tau=0.5, fast=True
    ).X.shape[0] == 48
    assert run_qlognei48(
        EvaluateOnly(), BOUNDS, root_seed=41, tau=0.5, fast=True
    ).X.shape[0] == 48


@pytest.mark.parametrize("runner", [run_spade, run_sobol48, run_qlognei48])
def test_public_decision_signatures_have_no_oracle_or_truth_parameter(runner):
    parameters = inspect.signature(runner).parameters
    assert "oracle" not in parameters
    assert "truth" not in parameters
    assert "truth_fn" not in parameters


def test_same_seed_is_deterministic_despite_ambient_rng_changes():
    config = SpadeConfig(opening=44, policy="staged", root_seed=43)
    torch.manual_seed(1)
    first = run_spade(TruthTrapEvaluator(), BOUNDS, config, tau=0.5, fast=True)
    torch.manual_seed(999)
    second = run_spade(TruthTrapEvaluator(), BOUNDS, config, tau=0.5, fast=True)

    assert torch.equal(first.X, second.X)
    assert torch.equal(first.Y, second.Y)
    assert first.protocol_digest == second.protocol_digest
    assert first.run_digest == second.run_digest
    assert [log.objective for log in first.round_logs] == [
        log.objective for log in second.round_logs
    ]


class BadEvaluator:
    def evaluate(self, X):
        return torch.zeros(X.shape[0] + 1, 1), torch.ones(X.shape[0] + 1, 1)


def test_bad_evaluator_cannot_corrupt_the_budget_record():
    with pytest.raises(ValueError, match="evaluator"):
        run_sobol48(BadEvaluator(), BOUNDS, root_seed=47, tau=0.5, fast=True)


def test_tau_is_bound_into_immutable_result_and_every_round_identity():
    config = SpadeConfig(opening=44, policy="staged", root_seed=53)
    low = run_spade(TruthTrapEvaluator(), BOUNDS, config, tau=0.50, fast=True)
    high = run_spade(TruthTrapEvaluator(), BOUNDS, config, tau=0.60, fast=True)

    assert low.protocol_digest == high.protocol_digest
    assert low.run_digest != high.run_digest
    assert low.tau == 0.50
    assert high.tau == 0.60
    assert all(log.tau == low.tau for log in low.round_logs)
    assert all(log.run_digest == low.run_digest for log in low.round_logs)


def test_comparator_identities_bind_arm_opening_schedule_and_effective_settings():
    sobol = run_sobol48(
        TruthTrapEvaluator(), BOUNDS, root_seed=59, tau=0.5, fast=True
    )
    qlognei = run_qlognei48(
        TruthTrapEvaluator(), BOUNDS, root_seed=59, tau=0.5, fast=True
    )

    assert sobol.arm == "sobol48"
    assert sobol.opening == 48
    assert sobol.batch_schedule == (48,)
    assert qlognei.arm == "qlognei48"
    assert qlognei.opening == 14
    assert qlognei.batch_schedule == (14, *([4] * 8), 2)
    assert sobol.protocol_digest != qlognei.protocol_digest
    assert sobol.run_digest != qlognei.run_digest
    assert sobol.effective_settings == qlognei.effective_settings


def test_public_runners_preserve_cpu_rng_and_never_seed_accelerators(monkeypatch):
    accelerator_seed_calls: list[tuple[str, int]] = []
    accelerator_state_calls: list[str] = []

    def record(name):
        return lambda seed: accelerator_seed_calls.append((name, int(seed)))

    monkeypatch.setattr(torch.cuda, "manual_seed_all", record("cuda"))
    monkeypatch.setattr(torch.mps, "manual_seed", record("mps"))
    monkeypatch.setattr(torch.xpu, "manual_seed_all", record("xpu"))
    monkeypatch.setattr(torch.mtia, "manual_seed_all", record("mtia"))
    # Simulate one CUDA generator even on CPU-only CI. A default fork_rng() would
    # snapshot and then write it back; the public runners must force CPU-only forks.
    monkeypatch.setattr(
        torch.accelerator, "current_accelerator", lambda: torch.device("cuda")
    )
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(
        torch.cuda,
        "get_rng_state",
        lambda _device=0: torch.tensor([7], dtype=torch.uint8),
    )
    monkeypatch.setattr(
        torch.cuda,
        "set_rng_state",
        lambda *_args, **_kwargs: accelerator_state_calls.append("cuda"),
    )
    original_manual_seed = torch.manual_seed
    original_fork_rng = torch.random.fork_rng
    torch.random.default_generator.manual_seed(61)
    before = torch.get_rng_state().clone()

    run_spade(
        TruthTrapEvaluator(),
        BOUNDS,
        SpadeConfig(opening=44, policy="staged", root_seed=61),
        tau=0.5,
        fast=True,
    )
    run_sobol48(TruthTrapEvaluator(), BOUNDS, root_seed=61, tau=0.5, fast=True)
    run_qlognei48(TruthTrapEvaluator(), BOUNDS, root_seed=61, tau=0.5, fast=True)

    assert torch.equal(torch.get_rng_state(), before)
    assert torch.manual_seed is original_manual_seed
    assert torch.random.fork_rng is original_fork_rng
    assert accelerator_seed_calls == []
    assert accelerator_state_calls == []
