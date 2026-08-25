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
        return (
            0.80
            if n >= analytic_gate.get((family, endpoint), 350)
            else 0.80 - 1e-15
        )

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
                successes=1630 if n >= gate else 1629,
                point_power=(1630 if n >= gate else 1629) / 2000,
                lower_bound=(
                    0.8001290149827873 if n >= gate else 0.7996146866285787
                ),
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


def _valid_payload(
    held_out: dict[str, dict[str, list[float]]] | None = None,
) -> dict[str, object]:
    held_out = copy.deepcopy(held_out if held_out is not None else _held_out())
    decision = plan_lockbox_sample_size(held_out).as_dict()
    selected = "spade-o44-fixed_hybrid"
    payload: dict[str, object] = {
        "schema": "boec-spade-lockbox-power-v1",
        "status": decision["status"],
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
        "held_out_differences": held_out,
        "decision": decision,
        "decision_sha256": _canonical_sha256(decision),
    }
    return payload


@pytest.fixture(scope="module")
def exact_powered_payload() -> dict[str, object]:
    return _valid_payload()


@pytest.fixture(scope="module")
def exact_insufficient_payload() -> dict[str, object]:
    return _valid_payload(_held_out(0.03))


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


@pytest.mark.parametrize(
    "changes",
    [
        {"minimum_n": 351},
        {"maximum_n": 1999},
        {"margin": 0.03},
        {"alpha": 0.10},
        {"target_power": 0.90},
        {"sensitivity_replicates": 1999},
        {"sensitivity_confidence": 0.90},
        {"root_seed": 2_026_08_26},
    ],
)
def test_valid_looking_power_constant_drift_is_rejected(changes):
    with pytest.raises(ValueError, match="frozen|registered"):
        replace(PowerConstants(), **changes)


def test_functions_reject_subclasses_that_bypass_frozen_constant_validation():
    class UnfrozenPowerConstants(PowerConstants):
        def __post_init__(self) -> None:
            pass

    bypass = UnfrozenPowerConstants(margin=0.03)
    calls = [
        lambda: paired_normal_power(0.0, 0.2, 350, bypass),
        lambda: sensitivity_power_curve(
            _held_out()["hill"]["map"],
            family="hill",
            endpoint="map",
            constants=bypass,
        ),
        lambda: plan_lockbox_sample_size(_held_out(), constants=bypass),
    ]
    for call in calls:
        with pytest.raises(TypeError, match="frozen|PowerConstants"):
            call()


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


@pytest.mark.parametrize(
    ("value", "expected_successes"),
    [(0.7, 0), (-0.7, 2000)],
)
def test_sensitivity_constant_translations_have_exact_zero_variance(
    value: float, expected_successes: int
):
    curve = sensitivity_power_curve([value] * 50, family="hill", endpoint="map")
    assert all(point.successes == expected_successes for point in curve)


def test_centered_prefix_moments_preserve_means_and_translation_invariant_variance():
    sampled = np.array(
        [
            [0.01, 0.02, -0.01, 0.03, 0.00],
            [-0.02, 0.01, 0.04, -0.01, 0.02],
        ],
        dtype=np.float64,
    )
    means, variances = power._centered_prefix_moments(
        sampled, minimum_n=2, maximum_n=5
    )
    for shift in (0.7, -0.7):
        shifted_means, shifted_variances = power._centered_prefix_moments(
            sampled + shift, minimum_n=2, maximum_n=5
        )
        assert shifted_means == pytest.approx(means + shift, abs=2e-16)
        assert shifted_variances == pytest.approx(variances, abs=2e-18)
    expected_variances = np.column_stack(
        [sampled[:, :n].var(axis=1, ddof=1) for n in range(2, 6)]
    )
    assert variances == pytest.approx(expected_variances, abs=2e-18)


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
        [0.0] * 49 + ["-0.01"],
        [0.0] * 48 + [False, "-0.01"],
        [1j] * 50,
        np.array([0.0] * 49 + ["-0.01"], dtype=object),
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


def test_power_plan_validator_accepts_exact_canonical_schema(exact_powered_payload):
    payload = copy.deepcopy(exact_powered_payload)
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
    exact_powered_payload, mutation
):
    payload = copy.deepcopy(exact_powered_payload)
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


def test_power_plan_validator_enforces_negative_status_null_semantics(
    exact_insufficient_payload,
):
    payload = copy.deepcopy(exact_insufficient_payload)
    assert validate_power_plan_payload(payload)["status"] == "INSUFFICIENT_POWER"


def test_power_plan_validator_does_not_alias_caller_payload(exact_powered_payload):
    payload = copy.deepcopy(exact_powered_payload)
    validated = validate_power_plan_payload(payload)
    assert validated == payload
    assert validated is not payload
    validated["environment"]["python"] = "changed"
    assert payload["environment"]["python"] == "3.11.9"


@pytest.mark.parametrize("bad_value", [True, "-0.01"])
def test_fully_recomputed_artifact_rejects_non_real_source_elements(
    exact_powered_payload, bad_value
):
    payload = copy.deepcopy(exact_powered_payload)
    payload["held_out_differences"]["hill"]["map"][0] = bad_value
    with pytest.raises(TypeError, match=r"finite .*Real"):
        decision = plan_lockbox_sample_size(payload["held_out_differences"]).as_dict()
        payload["status"] = decision["status"]
        payload["decision"] = decision
        payload["decision_sha256"] = _canonical_sha256(decision)
        validate_power_plan_payload(payload)


@pytest.mark.parametrize("unicode_digit", ["٠", "𝟘", "０"])
def test_digest_validation_rejects_non_ascii_hex_digits(unicode_digit: str):
    with pytest.raises(ValueError, match="ASCII|hex"):
        power._lower_hex(unicode_digit * 40, "source_commit", 40)


def test_sensitivity_point_rejects_impossible_probabilities():
    with pytest.raises((TypeError, ValueError)):
        SensitivityPoint(n=350, successes=2001, point_power=1.0, lower_bound=1.0)
    with pytest.raises((TypeError, ValueError)):
        SensitivityPoint(n=350, successes=1000, point_power=0.4, lower_bound=0.5)


def test_clopper_pearson_1629_fails_and_1630_passes_literal_target():
    lower_1629 = float(beta.ppf(0.05, 1629, 2000 - 1629 + 1))
    lower_1630 = float(beta.ppf(0.05, 1630, 2000 - 1630 + 1))
    assert lower_1629 == pytest.approx(0.7996146866285787, abs=1e-16)
    assert lower_1630 == pytest.approx(0.8001290149827873, abs=1e-16)
    assert lower_1629 < 0.80 <= lower_1630
    with pytest.raises(ValueError, match="Clopper-Pearson"):
        SensitivityPoint(
            n=350,
            successes=1629,
            point_power=1629 / 2000,
            lower_bound=0.80,
        )
    assert SensitivityPoint(
        n=350,
        successes=1630,
        point_power=1630 / 2000,
        lower_bound=0.8001290149827873,
    ).lower_bound >= 0.80


def _endpoint(payload: dict[str, object]) -> dict[str, object]:
    return payload["decision"]["families"]["hill"]["map"]


def _select_nonminimal_351(payload: dict[str, object]) -> None:
    decision = payload["decision"]
    decision["selected_sample_size"] = 351
    decision["selected_instance_prefix"] = {"first": 0, "last": 350, "count": 351}
    for family in DEVELOPMENT_FAMILIES:
        for endpoint in POWER_ENDPOINTS:
            decision["families"][family][endpoint]["reported_n"] = 351


@pytest.mark.parametrize(
    ("name", "mutate"),
    [
        (
            "forged_clopper_pearson_lower_bound",
            lambda payload: _endpoint(payload).update(
                sensitivity_successes=1629,
                sensitivity_point_power=1629 / 2000,
                sensitivity_lower_bound=0.80,
            ),
        ),
        (
            "wrong_labelled_seed",
            lambda payload: _endpoint(payload).__setitem__(
                "sensitivity_seed", _endpoint(payload)["sensitivity_seed"] + 1
            ),
        ),
        ("forged_mean", lambda payload: _endpoint(payload).__setitem__("mean", -0.02)),
        (
            "forged_standard_deviation",
            lambda payload: _endpoint(payload).__setitem__(
                "standard_deviation", 0.001
            ),
        ),
        (
            "forged_analytic_power",
            lambda payload: _endpoint(payload).__setitem__("analytic_power", 0.99),
        ),
        ("nonminimal_selected_n", _select_nonminimal_351),
        (
            "forged_required_n",
            lambda payload: (
                _select_nonminimal_351(payload),
                _endpoint(payload).__setitem__("required_n", 351),
            ),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_power_plan_validator_recomputes_complete_decision(
    exact_powered_payload, name, mutate
):
    del name
    payload = copy.deepcopy(exact_powered_payload)
    mutate(payload)
    payload["decision_sha256"] = _canonical_sha256(payload["decision"])
    with pytest.raises(ValueError, match="recomputed"):
        validate_power_plan_payload(payload)


def test_power_plan_validator_rejects_held_out_vector_tampering(
    exact_powered_payload,
):
    payload = copy.deepcopy(exact_powered_payload)
    payload["held_out_differences"]["hill"]["map"][0] = 0.03
    with pytest.raises(ValueError, match="recomputed"):
        validate_power_plan_payload(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda values: values.pop("hill"),
        lambda values: values["hill"].pop("map"),
        lambda values: values["hill"].__setitem__("map", [0.0] * 49),
        lambda values: values["hill"]["map"].__setitem__(0, math.nan),
        lambda values: values["hill"]["map"].__setitem__(0, True),
    ],
)
def test_power_plan_payload_requires_exact_held_out_vectors(
    exact_powered_payload, mutation
):
    payload = copy.deepcopy(exact_powered_payload)
    mutation(payload["held_out_differences"])
    with pytest.raises((TypeError, ValueError)):
        validate_power_plan_payload(payload)


def test_power_decision_prefix_is_derived_and_cannot_mutate_decision_or_digest():
    decision = plan_lockbox_sample_size(_held_out())
    digest = decision.decision_sha256
    prefix = decision.selected_instance_prefix
    assert prefix == {"first": 0, "last": 349, "count": 350}
    prefix["last"] = 999
    prefix["count"] = 1000
    assert decision.selected_instance_prefix == {
        "first": 0,
        "last": 349,
        "count": 350,
    }
    assert decision.decision_sha256 == digest


def test_power_decision_direct_construction_rejects_contradictory_invariants():
    powered = plan_lockbox_sample_size(_held_out())
    insufficient = plan_lockbox_sample_size(_held_out(0.03))
    invalid = [
        lambda: replace(powered, status="INSUFFICIENT_POWER"),
        lambda: replace(powered, status="UNKNOWN"),
        lambda: replace(powered, selected_sample_size=None),
        lambda: replace(powered, selected_sample_size=True),
        lambda: replace(powered, selected_sample_size=np.int64(350)),
        lambda: replace(powered, selected_sample_size=349),
        lambda: replace(powered, selected_sample_size=2001),
        lambda: replace(insufficient, selected_sample_size=350),
        lambda: replace(powered, constants=object()),
        lambda: replace(powered, families=powered.families[:-1]),
        lambda: replace(
            powered,
            families=(
                (powered.families[0][0], powered.families[0][1][:-1]),
                *powered.families[1:],
            ),
        ),
    ]
    for construct in invalid:
        with pytest.raises((TypeError, ValueError)):
            construct()
