"""Search space definition.

Canonical representation is coded [0, 1] in every dimension, in all three project
phases. Physical units are labels carried alongside; nothing in the optimizer ever
sees them. Phase 2's digitized figures are coded by construction, and Phase 3's lab
variables get coded against whatever min/max the lab declares.

Shapes: points are always ``(n, d)`` float arrays. There is no ``(d,)`` fast path —
a single point is ``(1, d)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

ParamType = Literal["continuous", "integer", "categorical"]


@dataclass(frozen=True)
class Parameter:
    """One search dimension.

    Phase 1 uses only ``continuous``. ``integer`` and ``categorical`` are carried in
    the schema now because Phase 3 has an integer treatment-day count and a
    categorical base medium, and retrofitting the type system later would touch
    every call site.
    """

    name: str
    unit: str = "coded"
    ptype: ParamType = "continuous"
    #: Physical bounds, for reporting only. The optimizer works in coded [0, 1].
    physical_low: float | None = None
    physical_high: float | None = None
    #: Category labels, ``categorical`` only.
    categories: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.ptype == "categorical" and not self.categories:
            raise ValueError(f"categorical parameter {self.name!r} needs categories")
        if self.ptype != "categorical" and self.categories:
            raise ValueError(f"{self.ptype} parameter {self.name!r} must not set categories")


@dataclass(frozen=True)
class MetricIdentity:
    """Which number is in the outcome column.

    Requirement 7 of the forward-compatibility contract. CD31% by flow cytometry and
    CD31 area by immunofluorescence are different numbers and must never be mixed
    within a campaign, so the identity travels on every data row rather than living
    in a README.
    """

    name: str
    unit: str
    protocol_version: str

    def as_dict(self) -> dict[str, str]:
        return {
            "metric_name": self.name,
            "metric_unit": self.unit,
            "metric_protocol_version": self.protocol_version,
        }


@dataclass
class SearchSpace:
    """Coded [0, 1]^d search space plus the constraint hooks Phase 3 will need.

    The constraint fields are deliberately plumbed through from config even though
    Phase 1 leaves them empty. Phase 3 has total-protein caps and plate arithmetic,
    and the Ogle failure was itself a constraint problem — the true optimum needed
    fibronectin below a design floor of 22 ug/mL. These are passed straight to
    ``optimize_acqf`` by the optimizer module; nothing here interprets them.
    """

    parameters: tuple[Parameter, ...]
    metric: MetricIdentity
    equality_constraints: list[Any] = field(default_factory=list)
    inequality_constraints: list[Any] = field(default_factory=list)
    nonlinear_inequality_constraints: list[Any] = field(default_factory=list)
    fixed_features_list: list[dict[int, float]] | None = None

    @property
    def dim(self) -> int:
        return len(self.parameters)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.parameters)

    @property
    def bounds(self) -> np.ndarray:
        """``(2, d)`` array of coded bounds — all zeros then all ones.

        Always pass this explicitly to any input transform. A BoTorch ``Normalize``
        constructed without ``bounds=`` learns them from the training data's min/max,
        which silently rescales E4's sub-box experiment.
        """
        return np.vstack([np.zeros(self.dim), np.ones(self.dim)])

    def validate(self, X: np.ndarray) -> np.ndarray:
        """Check shape and coded range. Returns ``X`` unchanged. Raises loudly."""
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"points must be (n, d); got shape {X.shape}")
        if X.shape[1] != self.dim:
            raise ValueError(f"expected d={self.dim} columns; got {X.shape[1]}")
        if not np.all(np.isfinite(X)):
            raise ValueError("points contain non-finite values")
        lo, hi = X.min(), X.max()
        if lo < -1e-9 or hi > 1 + 1e-9:
            raise ValueError(f"points outside coded [0,1]: min={lo:.6g} max={hi:.6g}")
        return X

    def to_physical(self, X: np.ndarray) -> np.ndarray:
        """Coded ``(n, d)`` -> physical ``(n, d)``, for reporting only.

        Dimensions without declared physical bounds pass through unchanged.
        """
        X = self.validate(X)
        out = X.copy()
        for j, p in enumerate(self.parameters):
            if p.physical_low is not None and p.physical_high is not None:
                out[:, j] = p.physical_low + X[:, j] * (p.physical_high - p.physical_low)
        return out

    @classmethod
    def unit_cube(
        cls,
        dim: int,
        metric: MetricIdentity | None = None,
        prefix: str = "x",
    ) -> "SearchSpace":
        """Plain coded space with generic names — what Phase 1 experiments use."""
        params = tuple(Parameter(name=f"{prefix}{i}") for i in range(dim))
        if metric is None:
            metric = MetricIdentity(
                name="synthetic_response", unit="normalized", protocol_version="phase1-v1"
            )
        return cls(parameters=params, metric=metric)

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "SearchSpace":
        """Build from a parsed YAML/JSON config dict.

        Expected shape::

            parameters:
              - {name: collagen_I, unit: ug/mL, ptype: continuous,
                 physical_low: 0.0, physical_high: 71.0}
            metric: {name: CD31_area_per_DAPI, unit: ratio, protocol_version: IF-day10-v1}
            constraints: {equality: [], inequality: [], nonlinear_inequality: []}
        """
        params = tuple(Parameter(**p) for p in cfg["parameters"])
        metric = MetricIdentity(**cfg["metric"])
        con = cfg.get("constraints", {}) or {}
        return cls(
            parameters=params,
            metric=metric,
            equality_constraints=list(con.get("equality", []) or []),
            inequality_constraints=list(con.get("inequality", []) or []),
            nonlinear_inequality_constraints=list(con.get("nonlinear_inequality", []) or []),
            fixed_features_list=con.get("fixed_features_list"),
        )

    def acqf_constraint_kwargs(self) -> dict[str, Any]:
        """Exactly the constraint kwargs ``optimize_acqf`` accepts.

        Omits empty lists rather than passing ``[]``, because BoTorch treats an empty
        list and ``None`` differently in some code paths.
        """
        kw: dict[str, Any] = {}
        if self.equality_constraints:
            kw["equality_constraints"] = self.equality_constraints
        if self.inequality_constraints:
            kw["inequality_constraints"] = self.inequality_constraints
        if self.nonlinear_inequality_constraints:
            kw["nonlinear_inequality_constraints"] = self.nonlinear_inequality_constraints
        if self.fixed_features_list:
            kw["fixed_features_list"] = self.fixed_features_list
        return kw
