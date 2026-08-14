"""The gate between the pipeline's candidate numbers and the optimizer.

:mod:`boec.lab.dataset` writes ``derived/candidate_campaign_coating_flow.csv`` with a
``y_candidate`` column and ``status = awaiting_human_signoff``. This module is what
refuses to turn that into an evaluator.

The refusal is the point. Three judgement calls stand between a candidate percentage
and a measurement -- no compensation, no live/singlet gate, and a positivity threshold
that is a convention worth 9-14 percentage points of spread (see ``data/lab/overlay/GATE.md``).
None of them is arithmetic, so none of them can be closed here. What this module does is
make the boundary explicit and loud: an unsigned table raises
:class:`GatingIncompleteError` naming the offending rows, rather than quietly seeding a
campaign with software output.

The signed table is ``data/lab/overlay/bo_primary_conditions.csv`` with ``y`` filled and
``status = gated``. Until a human does that, every path here ends in an exception.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ..evaluators import ContinuousLookupEvaluator
from ..space import SearchSpace

#: Statuses that mean "a human has signed this row off".
SIGNED_OFF = frozenset({"gated", "signed_off"})

COATING_CODES = {"fibronectin": 0.0, "vitronectin": 1.0}
DOSE_LOW, DOSE_HIGH = 0.5, 20.0


class GatingIncompleteError(ValueError):
    """The table still holds unsigned rows. Do not invent CD31%."""


class MetricMismatchError(ValueError):
    """The space's metric is not the one this table measures. Requirement 7."""


def coded_dose(dose_ug_ml: float) -> float:
    return (dose_ug_ml - DOSE_LOW) / (DOSE_HIGH - DOSE_LOW)


def load_conditions(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _float_or_nan(raw: str | None) -> float:
    text = (raw or "").strip()
    return float("nan") if text == "" else float(text)


def conditions_to_arrays(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(X (n, 2), y (n,), sd (n,))``. Missing values are ``nan``, never 0.0."""
    X = np.empty((len(rows), 2), dtype=float)
    y = np.empty(len(rows), dtype=float)
    sd = np.empty(len(rows), dtype=float)
    for i, row in enumerate(rows):
        coating = row["coating"].strip().lower()
        if coating not in COATING_CODES:
            raise ValueError(f"row {i}: unknown coating {row['coating']!r}")
        X[i, 0] = COATING_CODES[coating]
        X[i, 1] = coded_dose(float(row["dose_ug_mL"]))
        y[i] = _float_or_nan(row.get("y"))
        sd[i] = _float_or_nan(row.get("y_sd"))
    return X, y, sd


def unsigned_rows(rows: list[dict]) -> list[str]:
    """Files whose row is not both signed off and populated."""
    out = []
    for row in rows:
        status = (row.get("status") or "").strip().lower()
        has_y = (row.get("y") or "").strip() != ""
        if status not in SIGNED_OFF or not has_y:
            out.append(row.get("file", "<unnamed>"))
    return out


def load_lab_evaluator(
    conditions_csv: Path,
    space: SearchSpace,
    *,
    sd_floor: float = 0.05,
) -> ContinuousLookupEvaluator:
    """Build an evaluator from a **signed-off** conditions table.

    Raises:
        GatingIncompleteError: any row lacks ``y`` or a signed-off ``status``. The
            message names the files so the fix is obvious.
        MetricMismatchError: ``space.metric`` is not this table's metric. Guards against
            a coating campaign being scored as Hall/Ogle ``CD31_area_per_DAPI`` or as
            the phase-contrast ``coverage_frac_phase``.
    """
    conditions_csv = Path(conditions_csv)
    rows = load_conditions(conditions_csv)
    if not rows:
        raise GatingIncompleteError(f"{conditions_csv} has no rows")

    pending = unsigned_rows(rows)
    if pending:
        raise GatingIncompleteError(
            f"{conditions_csv}: {len(pending)} of {len(rows)} rows are awaiting_gating "
            f"and have no y. CD31% has not been signed off; see data/lab/overlay/GATE.md. "
            f"Do not invent percentages. First offenders: {pending[:3]}"
        )

    table_metric = rows[0].get("metric_name", "").strip()
    if space.metric.name != table_metric:
        raise MetricMismatchError(
            f"table measures {table_metric!r} but the space declares "
            f"{space.metric.name!r}. Different numbers must not share a campaign."
        )
    versions = {r.get("metric_protocol_version", "").strip() for r in rows}
    if len(versions) != 1:
        raise MetricMismatchError(f"table mixes protocol versions: {sorted(versions)}")
    if space.metric.protocol_version not in versions:
        raise MetricMismatchError(
            f"table protocol_version {versions.pop()!r} != space "
            f"{space.metric.protocol_version!r}"
        )

    X, y, sd = conditions_to_arrays(rows)
    return ContinuousLookupEvaluator(
        X_table=X, y_table=y, sd_table=sd, metric=space.metric, sd_floor=sd_floor
    )
