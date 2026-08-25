from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import beta

import boec.spade_power as power
from boec.seedbook import derive_seed
from boec.spade_power import (
    DEVELOPMENT_FAMILIES,
    POWER_ENDPOINTS,
    PowerConstants,
    SensitivityPoint,
    paired_normal_power,
    plan_lockbox_sample_size,
    sensitivity_power_curve,
    validate_power_plan_payload,
)


def _held_out(value: float = -0.01) -> dict[str, dict[str, list[float]]]:
    return {
        family: {endpoint: [value] * 50 for endpoint in POWER_ENDPOINTS}
        for family in DEVELOPMENT_FAMILIES
    }


def _install_literal_curves(
    monkeypatch: pytest.MonkeyPatch,
    *,
    analytic_gate: dict[tuple[str, str], int] | None = None,
    sensitivity_gate: dict[tuple[str, str], int] | None = None,
) -> None:
    analytic_gate = analytic_gate or {}
    sensitivity_gate = sensitivity_gate or {}
    state: dict[str, str] = {}

    def fake_analytic(
        mean: float,
        standard_deviation: float,
        n: int,
        constants: PowerConstants = PowerConstants(),
    ) -> float:
        del mean, standard_deviation, constants
        family, endpoint = state["identity"].split(":")
        return 0.80 if n >= analytic_gate.get((family, endpoint), 350) else 0.79

    def fake_sensitivity(
        values: object,
        *,
        family: str,
        endpoint: str,
        constants: PowerConstants = PowerConstants(),
    ) -> tuple[SensitivityPoint, ...]:
        del values
        state["identity"] = f"{family}:{endpoint}"
        gate = sensitivity_gate.get((family, endpoint), constants.minimum_n)
        return tuple(
            SensitivityPoint(
                n=n,
                successes=1800,
                point_power=0.90,
                lower_bound=0.80 if n >= gate else 0.80 - 1e-15,
            )
            for n in range(constants.minimum_n, constants.maximum_n + 1)
        )

    monkeypatch.setattr(power, "paired_normal_power", fake_analytic)
    monkeypatch.setattr(power, "sensitivity_power_curve", fake_sensitivity)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_payload(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _install_literal_curves(monkeypatch)
    decision = plan_lockbox_sample_size(_held_out()).as_dict()
    selected = "spade-o44-fixed_hybrid"
    payload: dict[str, object] = {
        "schema": "boec-spade-lockbox-power-v1",
        "status": "POWERED",
        "source_commit": "a" * 40,
        "source_dirty": False,
        "environment": {
            "python": "3.11.9",
            "numpy": "2.1.0",
            "scipy": "1.14.0",
            "platform": "test-platform",
        },
        "digests": {
            "study_protocol_sha256": "0" * 64,
            "specification_sha256": "1" * 64,
            "configuration_sha256": "2" * 64,
            "generator_sha256": "3" * 64,
            "generator_manifest_sha256": "4" * 64,
            "power_design_sha256": "5" * 64,
            "power_engine_sha256": "6" * 64,
            "power_planner_sha256": "7" * 64,
        },
        "selected_protocol": {
            "file": "spade-selected-protocol.json",
            "sha256": "8" * 64,
            "source_commit": "b" * 40,
        },
        "development_artifacts": [
            {
                "family": family,
                "raw_file": f"spade-development-{family}-000-050.jsonl.gz",
                "raw_sha256": f"{index:x}" * 64,
                "manifest_file": (
                    f"spade-development-{family}-000-050.jsonl.gz.manifest.json"
                ),
                "manifest_sha256": f"{index + 5:x}" * 64,
            }
            for index, family in enumerate(DEVELOPMENT_FAMILIES)
        ],
        "held_out_proof": {
            "unanimous": True,
            "selected_candidate": selected,
            "folds": [
                {
                    "held_out_family": family,
                    "training_families": [
                        other for other in DEVELOPMENT_FAMILIES if other != family
                    ],
                    "selected_candidate": selected,
                }
                for family in DEVELOPMENT_FAMILIES
            ],
        },
        "decision": decision,
        "decision_sha256": _canonical_sha256(decision),
    }
    return payload


def test_frozen_power_constants_are_literal_and_immutable():
    constants = PowerConstants()
    assert constants.as_dict() == {
        "minimum_n": 350,
        "maximum_n": 2000,
        "margin": 0.02,
        "alpha": 0.05,
        "target_power": 0.80,
        "sensitivity_replicates": 2000,
        "sensitivity_confidence": 0.95,
        "root_seed": 2_026_08_25,
    }
    with pytest.raises((AttributeError, TypeError)):
        constants.margin = 0.03  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"minimum_n": True},
        {"minimum_n": 1},
        {"maximum_n": 349},
        {"margin": math.nan},
        {"alpha": 0.0},
        {"alpha": 1.0},
        {"target_power": True},
        {"target_power": 0.0},
        {"target_power": 1.0},
        {"target_power": 1.01},
        {"sensitivity_replicates": 0},
        {"sensitivity_confidence": 0.0},
        {"sensitivity_confidence": 1.0},
        {"root_seed": False},
    ],
)
def test_power_constants_reject_invalid_values(changes: dict[str, object]):
    with pytest.raises((TypeError, ValueError)):
        replace(PowerConstants(), **changes)


def test_paired_normal_power_matches_literal_fixture():
    constants = PowerConstants()
    got = paired_normal_power(
        mean=0.0, standard_deviation=0.2, n=350, constants=constants
    )
    z_95_literal = 1.644853626951472
    expected = 0.5893895935672152
    assert (constants.margin * math.sqrt(350) / 0.2) - z_95_literal == pytest.approx(
        0.2259750664354987, abs=1e-15
    )
    assert got == pytest.approx(expected, abs=1e-15)


def test_zero_variance_and_noninferior_margin_are_fail_closed():
    constants = PowerConstants()
    assert paired_normal_power(0.019, 0.0, 350, constants) == 1.0
    assert paired_normal_power(0.02, 0.0, 350, constants) == 0.0
    assert paired_normal_power(0.021, 0.1, 2000, constants) == pytest.approx(
        0.018216251379700874, abs=1e-16
    )


@pytest.mark.parametrize(
    ("mean", "standard_deviation", "n"),
    [
        (True, 0.1, 350),
        (0.0, True, 350),
        (0.0, -0.1, 350),
        (0.0, math.nan, 350),
        (math.inf, 0.1, 350),
        (0.0, 0.1, True),
        (0.0, 0.1, 349),
        (0.0, 0.1, 2001),
    ],
)
def test_paired_normal_power_rejects_invalid_inputs(
    mean: object, standard_deviation: object, n: object
):
    with pytest.raises((TypeError, ValueError)):
        paired_normal_power(mean, standard_deviation, n)  # type: ignore[arg-type]


def test_sensitivity_curve_is_seeded_nested_and_exactly_bounded():
    values = np.array([-0.01, 0.00, 0.01, 0.015, 0.02] * 10)
    first = sensitivity_power_curve(values, family="hill", endpoint="map")
    second = sensitivity_power_curve(values, family="hill", endpoint="map")
    assert first == second
    assert len(first) == 1651
    assert first[0].n == 350 and first[-1].n == 2000
    assert all(0 <= row.successes <= 2000 for row in first)
    assert all(
        0.0 <= row.lower_bound <= row.point_power <= 1.0 for row in first
    )


def test_sensitivity_first_prefix_matches_independent_literal_calculation():
    values = np.linspace(-0.03, 0.07, 50)
    got = sensitivity_power_curve(values, family="hill", endpoint="map")[0]
    seed = derive_seed(
        2_026_08_25, "lockbox_power_sensitivity", "hill", "map"
    )
    indices = np.random.default_rng(seed).integers(
        0, 50, size=(2000, 2000), dtype=np.int32
    )
    prefixes = values[indices[:, :350]]
    means = prefixes.mean(axis=1)
    standard_deviations = prefixes.std(axis=1, ddof=1)
    upper = means + 1.644853626951472 * standard_deviations / math.sqrt(350)
    successes = int(np.count_nonzero(upper < 0.02))
    expected_lower = 0.0 if successes == 0 else float(
        beta.ppf(0.05, successes, 2000 - successes + 1)
    )
    assert successes == 102
    assert expected_lower == pytest.approx(0.04315177862207051, abs=1e-16)
    assert got == SensitivityPoint(
        n=350,
        successes=successes,
        point_power=successes / 2000,
        lower_bound=expected_lower,
    )


def test_family_and_endpoint_labels_derive_independent_sensitivity_streams():
    # Center on the margin so the Bernoulli summary does not saturate at 0 or 1.
    values = np.linspace(-0.03, 0.07, 50)
    hill_map = sensitivity_power_curve(values, family="hill", endpoint="map")
    assert hill_map != sensitivity_power_curve(
        values, family="ackley", endpoint="map"
    )
    assert hill_map != sensitivity_power_curve(
        values, family="hill", endpoint="regret"
    )


@pytest.mark.parametrize(
    "values",
    [
        [0.0] * 49,
        [0.0] * 51,
        [0.0] * 49 + [math.nan],
        [0.0] * 49 + [math.inf],
        [True] * 50,
        [1j] * 50,
        np.zeros((50, 1)),
    ],
)
def test_sensitivity_rejects_malformed_held_out_vectors(values: object):
    with pytest.raises((TypeError, ValueError)):
        sensitivity_power_curve(values, family="hill", endpoint="map")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("family", "endpoint"),
    [("unknown", "map"), ("hill", "unknown"), (True, "map")],
)
def test_sensitivity_rejects_unregistered_labels(family: object, endpoint: object):
    with pytest.raises((TypeError, ValueError)):
        sensitivity_power_curve(
            [0.0] * 50, family=family, endpoint=endpoint  # type: ignore[arg-type]
        )


def test_plan_selects_the_first_integer_passing_every_family_endpoint(monkeypatch):
    bottleneck = ("hartmann6", "regret")
    _install_literal_curves(
        monkeypatch,
        analytic_gate={bottleneck: 412},
        sensitivity_gate={bottleneck: 412},
    )
    decision = plan_lockbox_sample_size(_held_out())
    assert decision.status == "POWERED"
    assert decision.selected_sample_size == 412
    assert decision.selected_instance_prefix == {
        "first": 0,
        "last": 411,
        "count": 412,
    }
    assert decision.as_dict()["families"]["hartmann6"]["regret"][
        "required_n"
    ] == 412


def test_no_size_through_2000_is_an_immutable_negative_decision():
    bad = _held_out(0.03)
    decision = plan_lockbox_sample_size(bad)
    assert decision.status == "INSUFFICIENT_POWER"
    assert decision.selected_sample_size is None
    assert decision.selected_instance_prefix is None
    assert decision.as_dict()["families"]["hill"]["map"]["reported_n"] == 2000


@pytest.mark.parametrize(
    ("analytic_gate", "sensitivity_gate", "expected"),
    [
        (350, 350, 350),
        (2000, 350, 2000),
        (350, 2000, 2000),
        (2001, 350, None),
        (350, 2001, None),
    ],
)
def test_exact_target_equality_and_350_2000_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    analytic_gate: int,
    sensitivity_gate: int,
    expected: int | None,
):
    identity = ("hill", "map")
    _install_literal_curves(
        monkeypatch,
        analytic_gate={identity: analytic_gate},
        sensitivity_gate={identity: sensitivity_gate},
    )
    decision = plan_lockbox_sample_size(_held_out())
    assert decision.selected_sample_size == expected
    assert decision.status == ("POWERED" if expected is not None else "INSUFFICIENT_POWER")


def test_every_family_and_both_endpoints_participate_in_conjunction(monkeypatch):
    for family in DEVELOPMENT_FAMILIES:
        for endpoint in POWER_ENDPOINTS:
            _install_literal_curves(
                monkeypatch,
                sensitivity_gate={(family, endpoint): 351},
            )
            assert plan_lockbox_sample_size(_held_out()).selected_sample_size == 351


@pytest.mark.parametrize(
    "mutation",
    [
        lambda values: values.pop("hill"),
        lambda values: values.__setitem__("extra", values["hill"]),
        lambda values: values["hill"].pop("map"),
        lambda values: values["hill"].__setitem__("extra", [0.0] * 50),
        lambda values: values["hill"].__setitem__("map", [0.0] * 49),
        lambda values: values["hill"].__setitem__("map", [0.0] * 49 + [math.nan]),
    ],
)
def test_plan_requires_exact_finite_held_out_schema(mutation):
    values = _held_out()
    mutation(values)
    with pytest.raises((TypeError, ValueError)):
        plan_lockbox_sample_size(values)


def test_power_plan_validator_accepts_exact_canonical_schema(monkeypatch):
    payload = _valid_payload(monkeypatch)
    assert validate_power_plan_payload(payload) == payload


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.__setitem__("extra", None),
        lambda payload: payload.pop("environment"),
        lambda payload: payload.__setitem__("schema", "wrong"),
        lambda payload: payload.__setitem__("status", "INSUFFICIENT_POWER"),
        lambda payload: payload.__setitem__("source_dirty", True),
        lambda payload: payload.__setitem__("source_commit", "A" * 40),
        lambda payload: payload["digests"].__setitem__("generator_sha256", "x" * 64),
        lambda payload: payload["digests"].__setitem__("extra", "0" * 64),
        lambda payload: payload["selected_protocol"].__setitem__("file", "alias.json"),
        lambda payload: payload["development_artifacts"].pop(),
        lambda payload: payload["development_artifacts"][0].__setitem__(
            "family", "ackley"
        ),
        lambda payload: payload["held_out_proof"].__setitem__("unanimous", False),
        lambda payload: payload["held_out_proof"]["folds"][0].__setitem__(
            "selected_candidate", "other"
        ),
        lambda payload: payload.__setitem__("decision_sha256", "f" * 64),
        lambda payload: payload["decision"]["constants"].__setitem__("margin", 0.03),
        lambda payload: payload["decision"]["families"]["hill"].pop("map"),
        lambda payload: payload["decision"]["families"]["hill"]["map"].__setitem__(
            "analytic_power", math.nan
        ),
        lambda payload: payload["decision"].__setitem__(
            "selected_instance_prefix", {"first": 0, "last": 350, "count": 350}
        ),
    ],
)
def test_power_plan_validator_rejects_schema_provenance_and_decision_drift(
    monkeypatch: pytest.MonkeyPatch, mutation
):
    payload = _valid_payload(monkeypatch)
    mutation(payload)
    if payload.get("decision_sha256") != "f" * 64:
        try:
            payload["decision_sha256"] = _canonical_sha256(payload["decision"])
        except ValueError:
            # A nonfinite decision cannot itself be canonically re-hashed; the
            # validator must still reject the malformed decision.
            pass
    with pytest.raises((TypeError, ValueError)):
        validate_power_plan_payload(payload)


def test_power_plan_validator_enforces_negative_status_null_semantics(monkeypatch):
    payload = _valid_payload(monkeypatch)
    payload["status"] = "INSUFFICIENT_POWER"
    decision = payload["decision"]
    decision["status"] = "INSUFFICIENT_POWER"
    decision["selected_sample_size"] = None
    decision["selected_instance_prefix"] = None
    for family in DEVELOPMENT_FAMILIES:
        for endpoint in POWER_ENDPOINTS:
            decision["families"][family][endpoint]["reported_n"] = 2000
    decision["families"]["hill"]["map"]["sensitivity_lower_bound"] = 0.79
    payload["decision_sha256"] = _canonical_sha256(decision)
    assert validate_power_plan_payload(payload)["status"] == "INSUFFICIENT_POWER"


def test_power_plan_validator_does_not_alias_caller_payload(monkeypatch):
    payload = _valid_payload(monkeypatch)
    validated = validate_power_plan_payload(payload)
    assert validated == payload
    assert validated is not payload
    validated["environment"]["python"] = "changed"
    assert payload["environment"]["python"] == "3.11.9"


def test_sensitivity_point_rejects_impossible_probabilities():
    with pytest.raises((TypeError, ValueError)):
        SensitivityPoint(n=350, successes=2001, point_power=1.0, lower_bound=1.0)
    with pytest.raises((TypeError, ValueError)):
        SensitivityPoint(n=350, successes=1000, point_power=0.4, lower_bound=0.5)
