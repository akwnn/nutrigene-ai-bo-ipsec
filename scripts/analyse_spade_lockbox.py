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


def _registered_row_contract(rows: Sequence[Mapping[str, object]], provenance: Mapping[str, object]) -> None:
    required_provenance = {"protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256", "source_commit", "environment"}
    if set(provenance) != required_provenance:
        raise ValueError("registered analysis provenance schema drift")
    expected_keys = {(family, key, 0, arm) for family in LOCKBOX_FAMILIES for key in range(350) for arm in ARMS}
    actual_keys = set()
    for row in rows:
        if not isinstance(row, Mapping) or row.get("schema") != "boec-spade-study-row-v1":
            raise ValueError("registered analysis requires validated study rows")
        identity = (row.get("family"), row.get("instance_seed"), row.get("campaign_seed"), row.get("arm"))
        if identity in actual_keys:
            raise ValueError("registered analysis has duplicate campaign key")
        actual_keys.add(identity)
        if row.get("budget") != 48 or row.get("terminal_rule") != "P" or row.get("source_dirty") is not False:
            raise ValueError("registered analysis row budget/rule/source drift")
        for field in ("protocol_digest", "spec_digest", "config_digest", "source_commit"):
            if row.get(field) != provenance[field]:
                raise ValueError("registered analysis row provenance mismatch")
        parent = row.get("parent_artifacts")
        if not isinstance(parent, Mapping) or parent.get("generator") != provenance["generator_digest"] or parent.get("generator_manifest") != provenance["generator_manifest_sha256"]:
            raise ValueError("registered analysis row parent provenance mismatch")
        if row.get("environment") != provenance["environment"]:
            raise ValueError("registered analysis common environment mismatch")
        score = row.get("scores")
        if not isinstance(score, Mapping) or score.get("budget") != 48 or score.get("terminal_rule") != "P" or score.get("execution_mode") != "REGISTERED":
            raise ValueError("registered analysis score contract drift")
    if actual_keys != expected_keys or len(rows) != len(expected_keys):
        raise ValueError("registered analysis requires exactly all four frozen families and 350 complete paired keys")


def analyse_lockbox_rows(rows: Sequence[Mapping[str, object]], *, bootstrap_replicates: int = BOOTSTRAP_REPLICATES, bootstrap_seed: int = 2_026_08_25, execution_mode: str = "REGISTERED", provenance: Mapping[str, object] | None = None) -> dict[str, object]:
    """Compute the primary intersection-union verdict without pooling families."""
    by_family: dict[str, object] = {}
    pooled_rows: list[Mapping[str, object]] = []
    present = {row.get("family") for row in rows}
    if execution_mode not in {"REGISTERED", "TEST_ONLY"}:
        raise ValueError("analysis execution mode is invalid")
    if execution_mode == "REGISTERED":
        if provenance is None:
            raise ValueError("registered analysis requires immutable provenance")
        _registered_row_contract(rows, provenance)
        families = LOCKBOX_FAMILIES
    else:
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
    verdict = "PASS" if all_pass and execution_mode == "REGISTERED" else "FAIL"
    return {"schema": SCHEMA, "execution_mode": execution_mode, "provenance": dict(provenance or {}), "families": by_family, "overall_verdict": verdict, "permissible_claim": PERMISSIBLE_PASS_CLAIM if verdict == "PASS" else PERMISSIBLE_FAIL_CLAIM, "primary_rule": "intersection_union_all_endpoints_in_every_family", "secondary": {"pooled": {"row_count": len(pooled_rows), "does_not_change_primary": True, "label": "secondary descriptive pooled analysis only"}}}


def analyse_merged_manifest(manifest_path: Path) -> dict[str, object]:
    """Read only hash-validated raw shards named by a completed merged manifest."""
    from boec.spade_study import read_jsonl_gzip
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("merged lockbox manifest is invalid") from exc
    required = {"schema", "status", "sample_size", "raw_shards", "protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256", "source_commit", "source_dirty", "selected_protocol_sha256"}
    if not isinstance(manifest, Mapping) or set(manifest) != required or manifest.get("schema") != "boec-spade-lockbox-manifest-v1" or manifest.get("status") != "COMPLETE" or manifest.get("source_dirty") is not False or manifest.get("sample_size") != 350:
        raise ValueError("merged lockbox manifest schema/provenance drift")
    shards = manifest.get("raw_shards")
    if not isinstance(shards, list):
        raise ValueError("merged lockbox manifest has invalid shards")
    rows: list[dict[str, object]] = []
    for shard in shards:
        if not isinstance(shard, Mapping) or not isinstance(shard.get("raw_file"), str) or not isinstance(shard.get("raw_sha256"), str):
            raise ValueError("merged lockbox manifest shard schema drift")
        raw = manifest_path.parent / shard["raw_file"]
        actual = hashlib.sha256(raw.read_bytes()).hexdigest() if raw.is_file() else None
        if actual != shard["raw_sha256"]:
            raise ValueError("merged lockbox raw hash mismatch")
        rows.extend(read_jsonl_gzip(raw, protocol_digest=str(manifest["protocol_digest"])))
    if not rows:
        raise ValueError("merged lockbox manifest has no rows")
    provenance = {field: manifest[field] for field in ("protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256", "source_commit")}
    provenance["environment"] = rows[0]["environment"]
    return analyse_lockbox_rows(rows, execution_mode="REGISTERED", provenance=provenance)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", default=ROOT / "results" / "spade-lockbox-analysis.json", type=Path)
    args = parser.parse_args(argv)
    report = analyse_merged_manifest(args.manifest)
    _atomic_json(args.out, report)
    print(_canonical_json(report))
    return 0 if report["overall_verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
