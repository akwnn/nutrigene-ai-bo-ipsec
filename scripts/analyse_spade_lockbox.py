#!/usr/bin/env python3
"""Confirmatory, family-stratified analysis for frozen SPADE lockbox rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
LOCKBOX_FAMILIES = (
    "toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau",
)
ARMS = ("spade", "sobol48", "qlognei48")
BOOTSTRAP_REPLICATES = 10_000
ONE_SIDED_CONFIDENCE = 0.95
MAP_MARGIN = 0.02
REGRET_MARGIN = 0.02
ANSWER_MINIMUM = 0.50
CONTAINMENT_MINIMUM = 0.90
SCHEMA = "boec-spade-lockbox-analysis-v1"
PERMISSIBLE_PASS_CLAIM = "After prespecified selection on development families, the frozen 48-evaluation SPADE protocol matched the specialist Sobol map and qLogNEI optimizer within registered practical margins while issuing empirically calibrated conservative regions on four untouched randomized synthetic generator families."
PERMISSIBLE_FAIL_CLAIM = "The registered lockbox intersection-union success rule did not pass; no superiority claim is supported."


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(value) + "\n").encode()
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def paired_bootstrap_upper(values: Sequence[float], *, replicates: int = BOOTSTRAP_REPLICATES, seed: int = 0) -> float:
    """One-sided percentile upper bound for paired mean differences."""
    data = np.asarray(values, dtype=float)
    if data.ndim != 1 or not len(data) or not np.isfinite(data).all():
        raise ValueError("paired differences must be a non-empty finite vector")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
        raise ValueError("bootstrap replicate count must be a positive integer")
    draws = np.random.default_rng(seed).integers(0, len(data), size=(replicates, len(data)))
    return float(np.quantile(data[draws].mean(axis=1), ONE_SIDED_CONFIDENCE, method="higher"))


def clopper_pearson_lower(successes: int, denominator: int, *, confidence: float = ONE_SIDED_CONFIDENCE) -> float:
    if isinstance(successes, bool) or isinstance(denominator, bool) or not isinstance(successes, int) or not isinstance(denominator, int):
        raise ValueError("Clopper-Pearson counts must be integers")
    if not 0 <= successes <= denominator or denominator < 1:
        raise ValueError("Clopper-Pearson denominator must be positive with successes in range")
    return 0.0 if successes == 0 else float(beta.ppf(1.0 - confidence, successes, denominator - successes + 1))


def _endpoint(effect: float | None, bound: float | None, denominator: int, margin: float, *, direction: str, reason: str | None = None) -> dict[str, object]:
    passed = bound is not None and ((bound < margin) if direction == "upper" else (bound > margin))
    if reason is None:
        comparator = "below" if direction == "upper" else "above"
        reason = f"one-sided {'upper' if direction == 'upper' else 'lower'} bound {bound:.8g} is {'not ' if not passed else ''}{comparator} registered margin {margin:.8g}"
    return {"effect": effect, "one_sided_bound": bound, "denominator": denominator, "margin": margin, "verdict": "PASS" if passed else "FAIL", "reason": reason, "superiority": bool(direction == "upper" and bound is not None and bound < 0.0)}


def _family_rows(rows: Sequence[Mapping[str, object]], family: str) -> dict[tuple[int, int], dict[str, Mapping[str, object]]]:
    indexed: dict[tuple[int, int], dict[str, Mapping[str, object]]] = {}
    for row in rows:
        if row.get("family") != family:
            continue
        key = (row.get("instance_seed"), row.get("campaign_seed"))
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in key):
            raise ValueError("lockbox row has invalid campaign key")
        arm = row.get("arm")
        if arm not in ARMS:
            raise ValueError("lockbox row has unregistered arm")
        if arm in indexed.setdefault(key, {}):
            raise ValueError("duplicate lockbox campaign key")
        indexed[key][arm] = row
    if not indexed:
        raise ValueError(f"family {family} has no rows")
    if any(set(group) != set(ARMS) for group in indexed.values()):
        raise ValueError(f"family {family} has missing paired arm rows")
    return indexed


def _score(row: Mapping[str, object], name: str) -> float:
    score = row.get("scores")
    value = score.get(name) if isinstance(score, Mapping) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"lockbox score {name} must be finite")
    return float(value)


def analyse_lockbox_rows(rows: Sequence[Mapping[str, object]], *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES, bootstrap_seed: int = 2_026_08_25) -> dict[str, object]:
    """Compute the primary intersection-union verdict without pooling families."""
    by_family: dict[str, object] = {}
    pooled_rows: list[Mapping[str, object]] = []
    present = {row.get("family") for row in rows}
    families = tuple(family for family in LOCKBOX_FAMILIES if family in present)
    if not families:
        raise ValueError("no registered lockbox family rows supplied")
    for family_index, family in enumerate(families):
        groups = _family_rows(rows, family)
        ordered = [groups[key] for key in sorted(groups)]
        map_differences = [_score(group["spade"], "map_loss") - _score(group["sobol48"], "map_loss") for group in ordered]
        regret_differences = [_score(group["spade"], "regret_rule_p") - _score(group["qlognei48"], "regret_rule_p") for group in ordered]
        spade = [group["spade"] for group in ordered]
        nonempty = [row for row in spade if row.get("scores", {}).get("certificate_nonempty") is True]
        invalid_empty = [row for row in spade if row.get("scores", {}).get("certificate_nonempty") is False and row.get("scores", {}).get("certificate_empirical_containment") is not None]
        if invalid_empty:
            raise ValueError("empty certificates must not have containment outcomes")
        contained = sum(row.get("scores", {}).get("certificate_empirical_containment") is True for row in nonempty)
        n = len(spade)
        answer_successes = len(nonempty)
        map_bound = paired_bootstrap_upper(map_differences, replicates=bootstrap_replicates, seed=bootstrap_seed + family_index * 2)
        regret_bound = paired_bootstrap_upper(regret_differences, replicates=bootstrap_replicates, seed=bootstrap_seed + family_index * 2 + 1)
        answer_lower = clopper_pearson_lower(answer_successes, n)
        validity = _endpoint(float(np.mean(map_differences)), map_bound, n, MAP_MARGIN, direction="upper")
        regret = _endpoint(float(np.mean(regret_differences)), regret_bound, n, REGRET_MARGIN, direction="upper")
        willingness = _endpoint(answer_successes / n, answer_lower, n, ANSWER_MINIMUM, direction="lower")
        if not nonempty:
            containment = _endpoint(None, None, 0, CONTAINMENT_MINIMUM, direction="lower", reason="no non-empty SPADE certificates; conditional containment denominator is zero")
        else:
            containment = _endpoint(contained / len(nonempty), clopper_pearson_lower(contained, len(nonempty)), len(nonempty), CONTAINMENT_MINIMUM, direction="lower")
        by_family[family] = {"map_noninferiority": validity, "regret_noninferiority": regret, "certificate_willingness": willingness, "certificate_validity": containment}
        pooled_rows.extend(spade)
    all_pass = all(endpoint["verdict"] == "PASS" for endpoints in by_family.values() for endpoint in endpoints.values())
    verdict = "PASS" if all_pass else "FAIL"
    return {"schema": SCHEMA, "families": by_family, "overall_verdict": verdict, "permissible_claim": PERMISSIBLE_PASS_CLAIM if verdict == "PASS" else PERMISSIBLE_FAIL_CLAIM, "primary_rule": "intersection_union_all_endpoints_in_every_family", "secondary": {"pooled": {"row_count": len(pooled_rows), "does_not_change_primary": True, "label": "secondary descriptive pooled analysis only"}}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--out", default=ROOT / "results" / "spade-lockbox-analysis.json", type=Path)
    args = parser.parse_args(argv)
    rows = json.loads(args.rows.read_text(encoding="utf-8"))
    report = analyse_lockbox_rows(rows)
    _atomic_json(args.out, report)
    print(_canonical_json(report))
    return 0 if report["overall_verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
