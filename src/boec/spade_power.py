"""Pure deterministic power planning for the frozen SPADE lockbox protocol."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
from scipy.stats import beta, norm

from boec.seedbook import derive_seed

__all__ = [
    "DEVELOPMENT_FAMILIES",
    "POWER_ENDPOINTS",
    "POWER_PLAN_SCHEMA",
    "PowerConstants",
    "PowerDecision",
    "SensitivityPoint",
    "paired_normal_power",
    "plan_lockbox_sample_size",
    "sensitivity_power_curve",
    "validate_power_plan_payload",
]


DEVELOPMENT_FAMILIES = ("hill", "ackley", "hartmann6", "levy", "rosenbrock")
POWER_ENDPOINTS = ("map", "regret")
POWER_PLAN_SCHEMA = "boec-spade-lockbox-power-v1"

_ANALYTIC_FORMULA = (
    "Phi((margin-mean)*sqrt(n)/standard_deviation-z_(1-alpha))"
)
_SENSITIVITY_SUCCESS_RULE = (
    "mean+z_(sensitivity_confidence)*sample_sd/sqrt(n)<margin"
)
_SENSITIVITY_LOWER_BOUND = (
    "beta.ppf(1-sensitivity_confidence,successes,replicates-successes+1)"
)
_FORMULAS = {
    "paired_normal_power": _ANALYTIC_FORMULA,
    "sensitivity_success": _SENSITIVITY_SUCCESS_RULE,
    "clopper_pearson_lower_bound": _SENSITIVITY_LOWER_BOUND,
}
_DIGEST_FIELDS = frozenset(
    {
        "study_protocol_sha256",
        "specification_sha256",
        "configuration_sha256",
        "generator_sha256",
        "generator_manifest_sha256",
        "power_design_sha256",
        "power_engine_sha256",
        "power_planner_sha256",
    }
)


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer, never a boolean")
    return int(value)


def _finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite real number, never a boolean")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _probability(value: object, name: str, *, open_interval: bool) -> float:
    result = _finite_real(value, name)
    valid = 0.0 < result < 1.0 if open_interval else 0.0 <= result <= 1.0
    if not valid:
        interval = "(0, 1)" if open_interval else "[0, 1]"
        raise ValueError(f"{name} must lie in {interval}")
    return result


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _lower_hex(value: object, name: str, length: int) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"{name} must be a {length}-character lowercase hex string")
    if value != value.lower():
        raise ValueError(f"{name} must use lowercase hexadecimal")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _exact_fields(
    value: object, expected: set[str] | frozenset[str], name: str
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != set(expected):
        raise ValueError(f"{name} fields must be exactly {sorted(expected)}")
    return value


@dataclass(frozen=True)
class PowerConstants:
    """Registered constants for analytic and sensitivity power planning."""

    minimum_n: int = 350
    maximum_n: int = 2000
    margin: float = 0.02
    alpha: float = 0.05
    target_power: float = 0.80
    sensitivity_replicates: int = 2000
    sensitivity_confidence: float = 0.95
    root_seed: int = 2_026_08_25

    def __post_init__(self) -> None:
        minimum_n = _integer(self.minimum_n, "minimum_n")
        maximum_n = _integer(self.maximum_n, "maximum_n")
        replicates = _integer(self.sensitivity_replicates, "sensitivity_replicates")
        root_seed = _integer(self.root_seed, "root_seed")
        if minimum_n < 2:
            raise ValueError("minimum_n must be at least two for a sample variance")
        if maximum_n < minimum_n:
            raise ValueError("maximum_n must be at least minimum_n")
        if replicates < 1:
            raise ValueError("sensitivity_replicates must be positive")
        if root_seed < 0:
            raise ValueError("root_seed must be nonnegative")
        margin = _finite_real(self.margin, "margin")
        if margin <= 0.0:
            raise ValueError("margin must be positive")
        _probability(self.alpha, "alpha", open_interval=True)
        _probability(self.target_power, "target_power", open_interval=True)
        _probability(
            self.sensitivity_confidence,
            "sensitivity_confidence",
            open_interval=True,
        )

    def as_dict(self) -> dict[str, int | float]:
        return {
            "minimum_n": int(self.minimum_n),
            "maximum_n": int(self.maximum_n),
            "margin": float(self.margin),
            "alpha": float(self.alpha),
            "target_power": float(self.target_power),
            "sensitivity_replicates": int(self.sensitivity_replicates),
            "sensitivity_confidence": float(self.sensitivity_confidence),
            "root_seed": int(self.root_seed),
        }


@dataclass(frozen=True)
class SensitivityPoint:
    """One immutable point on the deterministic nonparametric power curve."""

    n: int
    successes: int
    point_power: float
    lower_bound: float

    def __post_init__(self) -> None:
        n = _integer(self.n, "n")
        successes = _integer(self.successes, "successes")
        if not 350 <= n <= 2000:
            raise ValueError("n lies outside the frozen 350..2000 range")
        if not 0 <= successes <= 2000:
            raise ValueError("successes lies outside the frozen replicate count")
        point = _probability(self.point_power, "point_power", open_interval=False)
        lower = _probability(self.lower_bound, "lower_bound", open_interval=False)
        if point != successes / 2000:
            raise ValueError("point_power must equal successes / 2000 exactly")
        if lower > point:
            raise ValueError("Clopper-Pearson lower bound cannot exceed point power")


@dataclass(frozen=True)
class _EndpointDecision:
    held_out_count: int
    mean: float
    standard_deviation: float
    analytic_required_n: int | None
    sensitivity_required_n: int | None
    required_n: int | None
    reported_n: int
    analytic_power: float
    sensitivity_successes: int
    sensitivity_point_power: float
    sensitivity_lower_bound: float
    sensitivity_seed: int

    def as_dict(self) -> dict[str, object]:
        return {
            "held_out_count": self.held_out_count,
            "mean": self.mean,
            "standard_deviation": self.standard_deviation,
            "analytic_required_n": self.analytic_required_n,
            "sensitivity_required_n": self.sensitivity_required_n,
            "required_n": self.required_n,
            "reported_n": self.reported_n,
            "analytic_power": self.analytic_power,
            "sensitivity_successes": self.sensitivity_successes,
            "sensitivity_point_power": self.sensitivity_point_power,
            "sensitivity_lower_bound": self.sensitivity_lower_bound,
            "sensitivity_seed": self.sensitivity_seed,
        }


@dataclass(frozen=True)
class PowerDecision:
    """Immutable sample-size decision with a canonical JSON representation."""

    status: str
    selected_sample_size: int | None
    selected_instance_prefix: dict[str, int] | None
    families: tuple[tuple[str, tuple[tuple[str, _EndpointDecision], ...]], ...]
    constants: PowerConstants = PowerConstants()

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "selected_sample_size": self.selected_sample_size,
            "selected_instance_prefix": (
                None
                if self.selected_instance_prefix is None
                else dict(self.selected_instance_prefix)
            ),
            "constants": self.constants.as_dict(),
            "formulas": dict(_FORMULAS),
            "families": {
                family: {
                    endpoint: result.as_dict() for endpoint, result in endpoints
                }
                for family, endpoints in self.families
            },
        }

    @property
    def canonical_json(self) -> str:
        return _canonical_json(self.as_dict())

    @property
    def decision_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


def paired_normal_power(
    mean: float,
    standard_deviation: float,
    n: int,
    constants: PowerConstants = PowerConstants(),
) -> float:
    """Return registered one-sided paired-normal non-inferiority planning power."""
    if not isinstance(constants, PowerConstants):
        raise TypeError("constants must be PowerConstants")
    mean_value = _finite_real(mean, "mean")
    standard_deviation_value = _finite_real(
        standard_deviation, "standard_deviation"
    )
    sample_size = _integer(n, "n")
    if standard_deviation_value < 0.0:
        raise ValueError("standard_deviation must be nonnegative")
    if not constants.minimum_n <= sample_size <= constants.maximum_n:
        raise ValueError("n lies outside the registered candidate range")
    if standard_deviation_value == 0.0:
        return 1.0 if mean_value < constants.margin else 0.0
    z_alpha = float(norm.ppf(1.0 - constants.alpha))
    argument = (
        (constants.margin - mean_value)
        * math.sqrt(sample_size)
        / standard_deviation_value
        - z_alpha
    )
    if not math.isfinite(argument):
        raise ValueError("paired-normal power argument is nonfinite")
    result = float(norm.cdf(argument))
    if not math.isfinite(result):
        raise ValueError("paired-normal power is nonfinite")
    return result


def _held_out_array(values: Sequence[float] | np.ndarray, name: str) -> np.ndarray:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a numeric vector")
    try:
        array = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a numeric vector") from exc
    if array.shape != (50,):
        raise ValueError(f"{name} must contain exactly 50 scalar differences")
    if np.issubdtype(array.dtype, np.bool_):
        raise TypeError(f"{name} cannot contain booleans")
    if np.issubdtype(array.dtype, np.complexfloating):
        raise TypeError(f"{name} cannot contain complex values")
    try:
        result = np.asarray(array, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain real numbers") from exc
    if not bool(np.isfinite(result).all()):
        raise ValueError(f"{name} must contain only finite differences")
    return result


def sensitivity_power_curve(
    values: Sequence[float] | np.ndarray,
    *,
    family: str,
    endpoint: str,
    constants: PowerConstants = PowerConstants(),
) -> tuple[SensitivityPoint, ...]:
    """Build the frozen deterministic nested-prefix sensitivity power curve."""
    if not isinstance(constants, PowerConstants):
        raise TypeError("constants must be PowerConstants")
    if isinstance(family, bool) or family not in DEVELOPMENT_FAMILIES:
        raise ValueError(f"family must be one of {DEVELOPMENT_FAMILIES}")
    if isinstance(endpoint, bool) or endpoint not in POWER_ENDPOINTS:
        raise ValueError(f"endpoint must be one of {POWER_ENDPOINTS}")
    differences = _held_out_array(values, f"{family}/{endpoint}")
    seed = derive_seed(
        constants.root_seed,
        "lockbox_power_sensitivity",
        family,
        endpoint,
    )
    indices = np.random.default_rng(seed).integers(
        0,
        differences.size,
        size=(constants.sensitivity_replicates, constants.maximum_n),
        dtype=np.int32,
    )
    sampled = differences[indices]
    with np.errstate(over="ignore", invalid="ignore"):
        cumulative_sum = np.cumsum(sampled, axis=1, dtype=np.float64)
        np.square(sampled, out=sampled)
        cumulative_square_sum = np.cumsum(sampled, axis=1, dtype=np.float64)
    del sampled, indices

    start = constants.minimum_n - 1
    stop = constants.maximum_n
    sums = cumulative_sum[:, start:stop]
    square_sums = cumulative_square_sum[:, start:stop]
    sample_sizes = np.arange(
        constants.minimum_n, constants.maximum_n + 1, dtype=np.float64
    )[None, :]
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        means = sums / sample_sizes
        variances = (square_sums - np.square(sums) / sample_sizes) / (
            sample_sizes - 1.0
        )
    if not bool(np.isfinite(means).all()) or not bool(np.isfinite(variances).all()):
        raise ValueError("sensitivity prefix moments are nonfinite")
    if bool(np.any(variances < -1e-14)):
        raise ValueError("sensitivity sample variance is materially negative")
    variances[variances < 0.0] = 0.0
    standard_deviations = np.sqrt(variances)
    z_confidence = float(norm.ppf(constants.sensitivity_confidence))
    upper = means + z_confidence * standard_deviations / np.sqrt(sample_sizes)
    if not bool(np.isfinite(upper).all()):
        raise ValueError("sensitivity upper bounds are nonfinite")
    successes = np.count_nonzero(upper < constants.margin, axis=0).astype(np.int64)
    point_power = successes.astype(np.float64) / constants.sensitivity_replicates
    lower_bound = np.zeros_like(point_power)
    positive = successes > 0
    lower_bound[positive] = beta.ppf(
        1.0 - constants.sensitivity_confidence,
        successes[positive],
        constants.sensitivity_replicates - successes[positive] + 1,
    )
    if not bool(np.isfinite(lower_bound).all()):
        raise ValueError("Clopper-Pearson lower bounds are nonfinite")
    return tuple(
        SensitivityPoint(
            n=n,
            successes=int(successes[index]),
            point_power=float(point_power[index]),
            lower_bound=float(lower_bound[index]),
        )
        for index, n in enumerate(
            range(constants.minimum_n, constants.maximum_n + 1)
        )
    )


def _first_passing_n(values: Sequence[float], constants: PowerConstants) -> int | None:
    for offset, value in enumerate(values):
        if value >= constants.target_power:
            return constants.minimum_n + offset
    return None


def _validate_held_out(
    held_out_differences: Mapping[str, Mapping[str, Sequence[float] | np.ndarray]],
) -> dict[str, dict[str, np.ndarray]]:
    if not isinstance(held_out_differences, Mapping) or set(held_out_differences) != set(
        DEVELOPMENT_FAMILIES
    ):
        raise ValueError("held-out evidence must contain exactly five registered families")
    validated: dict[str, dict[str, np.ndarray]] = {}
    for family in DEVELOPMENT_FAMILIES:
        endpoints = held_out_differences[family]
        if not isinstance(endpoints, Mapping) or set(endpoints) != set(POWER_ENDPOINTS):
            raise ValueError(f"{family} must contain exactly map and regret")
        validated[family] = {
            endpoint: _held_out_array(
                endpoints[endpoint], f"{family}/{endpoint}"
            )
            for endpoint in POWER_ENDPOINTS
        }
    return validated


def plan_lockbox_sample_size(
    held_out_differences: Mapping[
        str, Mapping[str, Sequence[float] | np.ndarray]
    ],
    constants: PowerConstants = PowerConstants(),
) -> PowerDecision:
    """Select the first candidate passing every frozen power conjunction."""
    if not isinstance(constants, PowerConstants):
        raise TypeError("constants must be PowerConstants")
    held_out = _validate_held_out(held_out_differences)
    curves: dict[
        tuple[str, str],
        tuple[float, float, tuple[float, ...], tuple[SensitivityPoint, ...]],
    ] = {}
    candidate_sizes = range(constants.minimum_n, constants.maximum_n + 1)
    for family in DEVELOPMENT_FAMILIES:
        for endpoint in POWER_ENDPOINTS:
            values = held_out[family][endpoint]
            mean = float(np.mean(values, dtype=np.float64))
            standard_deviation = float(np.std(values, ddof=1, dtype=np.float64))
            if not math.isfinite(mean) or not math.isfinite(standard_deviation):
                raise ValueError(f"{family}/{endpoint} moments are nonfinite")
            sensitivity = sensitivity_power_curve(
                values,
                family=family,
                endpoint=endpoint,
                constants=constants,
            )
            analytic = tuple(
                paired_normal_power(mean, standard_deviation, n, constants)
                for n in candidate_sizes
            )
            curves[(family, endpoint)] = (
                mean,
                standard_deviation,
                analytic,
                sensitivity,
            )

    selected_n: int | None = None
    for offset, n in enumerate(candidate_sizes):
        if all(
            curves[(family, endpoint)][2][offset] >= constants.target_power
            and curves[(family, endpoint)][3][offset].lower_bound
            >= constants.target_power
            for family in DEVELOPMENT_FAMILIES
            for endpoint in POWER_ENDPOINTS
        ):
            selected_n = n
            break

    status = "POWERED" if selected_n is not None else "INSUFFICIENT_POWER"
    reported_n = selected_n if selected_n is not None else constants.maximum_n
    reported_offset = reported_n - constants.minimum_n
    family_results: list[
        tuple[str, tuple[tuple[str, _EndpointDecision], ...]]
    ] = []
    for family in DEVELOPMENT_FAMILIES:
        endpoint_results: list[tuple[str, _EndpointDecision]] = []
        for endpoint in POWER_ENDPOINTS:
            mean, standard_deviation, analytic, sensitivity = curves[(family, endpoint)]
            analytic_required = _first_passing_n(analytic, constants)
            sensitivity_required = _first_passing_n(
                tuple(point.lower_bound for point in sensitivity), constants
            )
            required = next(
                (
                    constants.minimum_n + offset
                    for offset, (analytic_value, point) in enumerate(
                        zip(analytic, sensitivity, strict=True)
                    )
                    if analytic_value >= constants.target_power
                    and point.lower_bound >= constants.target_power
                ),
                None,
            )
            point = sensitivity[reported_offset]
            endpoint_results.append(
                (
                    endpoint,
                    _EndpointDecision(
                        held_out_count=50,
                        mean=mean,
                        standard_deviation=standard_deviation,
                        analytic_required_n=analytic_required,
                        sensitivity_required_n=sensitivity_required,
                        required_n=required,
                        reported_n=reported_n,
                        analytic_power=analytic[reported_offset],
                        sensitivity_successes=point.successes,
                        sensitivity_point_power=point.point_power,
                        sensitivity_lower_bound=point.lower_bound,
                        sensitivity_seed=derive_seed(
                            constants.root_seed,
                            "lockbox_power_sensitivity",
                            family,
                            endpoint,
                        ),
                    ),
                )
            )
        family_results.append((family, tuple(endpoint_results)))
    prefix = (
        None
        if selected_n is None
        else {"first": 0, "last": selected_n - 1, "count": selected_n}
    )
    return PowerDecision(
        status=status,
        selected_sample_size=selected_n,
        selected_instance_prefix=prefix,
        families=tuple(family_results),
        constants=constants,
    )


def _validate_constants_payload(value: object) -> None:
    expected = PowerConstants().as_dict()
    mapping = _exact_fields(value, set(expected), "decision.constants")
    for field, literal in expected.items():
        actual = mapping[field]
        if isinstance(literal, int):
            if isinstance(actual, bool) or not isinstance(actual, int) or actual != literal:
                raise ValueError(f"decision.constants.{field} drifted")
        elif (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or float(actual) != literal
        ):
            raise ValueError(f"decision.constants.{field} drifted")


def _optional_registered_n(value: object, name: str) -> int | None:
    if value is None:
        return None
    result = _integer(value, name)
    if not 350 <= result <= 2000:
        raise ValueError(f"{name} lies outside 350..2000")
    return result


def _validate_endpoint_metrics(
    value: object,
    *,
    name: str,
    status: str,
    reported_n: int,
) -> tuple[float, float]:
    expected = {
        "held_out_count",
        "mean",
        "standard_deviation",
        "analytic_required_n",
        "sensitivity_required_n",
        "required_n",
        "reported_n",
        "analytic_power",
        "sensitivity_successes",
        "sensitivity_point_power",
        "sensitivity_lower_bound",
        "sensitivity_seed",
    }
    metrics = _exact_fields(value, expected, name)
    if _integer(metrics["held_out_count"], f"{name}.held_out_count") != 50:
        raise ValueError(f"{name}.held_out_count must equal 50")
    _finite_real(metrics["mean"], f"{name}.mean")
    standard_deviation = _finite_real(
        metrics["standard_deviation"], f"{name}.standard_deviation"
    )
    if standard_deviation < 0.0:
        raise ValueError(f"{name}.standard_deviation must be nonnegative")
    analytic_required = _optional_registered_n(
        metrics["analytic_required_n"], f"{name}.analytic_required_n"
    )
    sensitivity_required = _optional_registered_n(
        metrics["sensitivity_required_n"], f"{name}.sensitivity_required_n"
    )
    required = _optional_registered_n(metrics["required_n"], f"{name}.required_n")
    if _integer(metrics["reported_n"], f"{name}.reported_n") != reported_n:
        raise ValueError(f"{name}.reported_n disagrees with decision status")
    analytic_power = _probability(
        metrics["analytic_power"], f"{name}.analytic_power", open_interval=False
    )
    successes = _integer(
        metrics["sensitivity_successes"], f"{name}.sensitivity_successes"
    )
    if not 0 <= successes <= 2000:
        raise ValueError(f"{name}.sensitivity_successes lies outside 0..2000")
    point_power = _probability(
        metrics["sensitivity_point_power"],
        f"{name}.sensitivity_point_power",
        open_interval=False,
    )
    lower_bound = _probability(
        metrics["sensitivity_lower_bound"],
        f"{name}.sensitivity_lower_bound",
        open_interval=False,
    )
    if point_power != successes / 2000 or lower_bound > point_power:
        raise ValueError(f"{name} sensitivity probability arithmetic drifted")
    seed = _integer(metrics["sensitivity_seed"], f"{name}.sensitivity_seed")
    if not 0 <= seed < 2**63 - 1:
        raise ValueError(f"{name}.sensitivity_seed lies outside derive_seed range")
    if required is not None:
        if analytic_required is None or sensitivity_required is None:
            raise ValueError(f"{name}.required_n needs both component requirements")
        if required < max(analytic_required, sensitivity_required):
            raise ValueError(f"{name}.required_n precedes a component requirement")
    if status == "POWERED":
        if required is None or required > reported_n:
            raise ValueError(f"{name} does not pass by selected sample size")
        if analytic_power < 0.80 or lower_bound < 0.80:
            raise ValueError(f"{name} fails the registered target at selected size")
    return analytic_power, lower_bound


def _validate_decision(value: object) -> Mapping[str, object]:
    expected = {
        "status",
        "selected_sample_size",
        "selected_instance_prefix",
        "constants",
        "formulas",
        "families",
    }
    decision = _exact_fields(value, expected, "decision")
    status = decision["status"]
    if status not in {"POWERED", "INSUFFICIENT_POWER"}:
        raise ValueError("decision.status must be POWERED or INSUFFICIENT_POWER")
    _validate_constants_payload(decision["constants"])
    formulas = _exact_fields(decision["formulas"], set(_FORMULAS), "decision.formulas")
    if dict(formulas) != _FORMULAS:
        raise ValueError("decision formulas drifted from the registered literals")
    if status == "POWERED":
        selected_n = _integer(
            decision["selected_sample_size"], "decision.selected_sample_size"
        )
        if not 350 <= selected_n <= 2000:
            raise ValueError("selected sample size lies outside 350..2000")
        prefix = _exact_fields(
            decision["selected_instance_prefix"],
            {"first", "last", "count"},
            "decision.selected_instance_prefix",
        )
        if (
            _integer(prefix["first"], "prefix.first"),
            _integer(prefix["last"], "prefix.last"),
            _integer(prefix["count"], "prefix.count"),
        ) != (0, selected_n - 1, selected_n):
            raise ValueError("selected instance prefix arithmetic drifted")
        reported_n = selected_n
    else:
        if decision["selected_sample_size"] is not None or decision[
            "selected_instance_prefix"
        ] is not None:
            raise ValueError("INSUFFICIENT_POWER decision must use null selection fields")
        reported_n = 2000
    families = _exact_fields(
        decision["families"], set(DEVELOPMENT_FAMILIES), "decision.families"
    )
    endpoint_powers: list[tuple[float, float]] = []
    for family in DEVELOPMENT_FAMILIES:
        endpoints = _exact_fields(
            families[family], set(POWER_ENDPOINTS), f"decision.families.{family}"
        )
        for endpoint in POWER_ENDPOINTS:
            endpoint_powers.append(
                _validate_endpoint_metrics(
                    endpoints[endpoint],
                    name=f"decision.families.{family}.{endpoint}",
                    status=str(status),
                    reported_n=reported_n,
                )
            )
    if status == "INSUFFICIENT_POWER" and all(
        analytic >= 0.80 and lower >= 0.80
        for analytic, lower in endpoint_powers
    ):
        raise ValueError("INSUFFICIENT_POWER must fail at least one metric at n=2000")
    return decision


def validate_power_plan_payload(payload: object) -> dict[str, object]:
    """Validate and defensively copy the exact immutable power-artifact schema."""
    expected = {
        "schema",
        "status",
        "source_commit",
        "source_dirty",
        "environment",
        "digests",
        "selected_protocol",
        "development_artifacts",
        "held_out_proof",
        "decision",
        "decision_sha256",
    }
    top = _exact_fields(payload, expected, "power plan")
    if top["schema"] != POWER_PLAN_SCHEMA:
        raise ValueError("power plan schema drifted")
    if top["source_dirty"] is not False:
        raise ValueError("power plan requires an explicitly clean source tree")
    _lower_hex(top["source_commit"], "source_commit", 40)
    environment = _exact_fields(
        top["environment"], {"python", "numpy", "scipy", "platform"}, "environment"
    )
    if any(
        not isinstance(environment[field], str) or not environment[field]
        for field in environment
    ):
        raise ValueError("environment identity fields must be nonempty strings")
    digests = _exact_fields(top["digests"], _DIGEST_FIELDS, "digests")
    for field in _DIGEST_FIELDS:
        _lower_hex(digests[field], f"digests.{field}", 64)
    selected = _exact_fields(
        top["selected_protocol"],
        {"file", "sha256", "source_commit"},
        "selected_protocol",
    )
    if selected["file"] != "spade-selected-protocol.json":
        raise ValueError("selected protocol filename drifted")
    _lower_hex(selected["sha256"], "selected_protocol.sha256", 64)
    _lower_hex(selected["source_commit"], "selected_protocol.source_commit", 40)

    artifacts = top["development_artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("development_artifacts must contain exactly five shards")
    artifact_fields = {
        "family",
        "raw_file",
        "raw_sha256",
        "manifest_file",
        "manifest_sha256",
    }
    for family, artifact in zip(DEVELOPMENT_FAMILIES, artifacts, strict=True):
        item = _exact_fields(artifact, artifact_fields, f"artifact.{family}")
        if item["family"] != family:
            raise ValueError("development artifact family order or identity drifted")
        for field in ("raw_file", "manifest_file"):
            if not isinstance(item[field], str) or not item[field]:
                raise ValueError(f"artifact.{family}.{field} must be nonempty")
        _lower_hex(item["raw_sha256"], f"artifact.{family}.raw_sha256", 64)
        _lower_hex(
            item["manifest_sha256"], f"artifact.{family}.manifest_sha256", 64
        )

    proof = _exact_fields(
        top["held_out_proof"],
        {"unanimous", "selected_candidate", "folds"},
        "held_out_proof",
    )
    candidate = proof["selected_candidate"]
    if proof["unanimous"] is not True or not isinstance(candidate, str) or not candidate:
        raise ValueError("held-out proof must record one unanimous candidate")
    folds = proof["folds"]
    if not isinstance(folds, list) or len(folds) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("held-out proof must contain five folds")
    for family, fold in zip(DEVELOPMENT_FAMILIES, folds, strict=True):
        item = _exact_fields(
            fold,
            {"held_out_family", "training_families", "selected_candidate"},
            f"held_out_proof.{family}",
        )
        expected_training = [other for other in DEVELOPMENT_FAMILIES if other != family]
        if (
            item["held_out_family"] != family
            or item["training_families"] != expected_training
            or item["selected_candidate"] != candidate
        ):
            raise ValueError("held-out fold identity or unanimous selection drifted")

    decision = _validate_decision(top["decision"])
    if top["status"] != decision["status"]:
        raise ValueError("top-level status disagrees with decision status")
    decision_digest = _lower_hex(top["decision_sha256"], "decision_sha256", 64)
    if decision_digest != _canonical_sha256(decision):
        raise ValueError("decision_sha256 does not bind the canonical decision")
    try:
        return json.loads(_canonical_json(top))
    except (TypeError, ValueError) as exc:
        raise ValueError("power plan is not finite canonical JSON") from exc
