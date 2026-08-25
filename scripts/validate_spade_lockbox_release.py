#!/usr/bin/env python3
"""Fail-closed release gate for SPADE lockbox artifacts; it never reruns campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts import analyse_spade_lockbox as confirmatory


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("spade", "sobol48", "qlognei48")
LOCKBOX_FAMILIES = ("toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau")
LOCKBOX_SAMPLE_SIZE = 350
PERMISSIBLE_PASS_CLAIM = ("After prespecified selection on development families, the frozen 48-evaluation SPADE protocol matched the specialist Sobol map and qLogNEI optimizer within registered practical margins while issuing empirically calibrated conservative regions on four untouched randomized synthetic generator families.")
PERMISSIBLE_FAIL_CLAIM = "The registered lockbox intersection-union success rule did not pass; no superiority claim is supported."


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _violation(violations: list[str], message: str) -> None:
    if message not in violations:
        violations.append(message)


def collect_release_violations(*, manifest: Mapping[str, object], selection: Mapping[str, object], analysis: Mapping[str, object], rows: Mapping[str, Sequence[Mapping[str, object]]], actual_hashes: Mapping[str, str]) -> list[str]:
    """Return every independently detectable release violation, never fail fast."""
    violations: list[str] = []
    if not isinstance(manifest, Mapping):
        _violation(violations, "manifest schema violation"); manifest = {}
    if not isinstance(selection, Mapping):
        _violation(violations, "selection schema violation"); selection = {}
    if not isinstance(analysis, Mapping):
        _violation(violations, "analysis schema violation"); analysis = {}
    if not isinstance(rows, Mapping):
        _violation(violations, "raw row mapping schema violation"); rows = {}
    if not isinstance(actual_hashes, Mapping):
        _violation(violations, "actual hash mapping schema violation"); actual_hashes = {}
    if manifest.get("status") != "COMPLETE": _violation(violations, "lockbox manifest is not COMPLETE")
    sample_size = manifest.get("sample_size")
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size != LOCKBOX_SAMPLE_SIZE:
        _violation(violations, "unregistered sample size")
    if selection.get("status") != "SELECTED": _violation(violations, "premature lockbox without selected protocol")
    if manifest.get("lockbox_started_before_selection_commit") is True:
        _violation(violations, "premature lockbox before selection commit")
    valid_rows: list[Mapping[str, object]] = []
    for filename, shard_rows in rows.items():
        if not isinstance(filename, str) or not isinstance(shard_rows, Sequence) or isinstance(shard_rows, (str, bytes)):
            _violation(violations, "raw row schema violation"); continue
        for row in shard_rows:
            if not isinstance(row, Mapping):
                _violation(violations, "raw row schema violation"); continue
            valid_rows.append(row)
    if manifest.get("source_dirty") is not False or any(row.get("source_dirty") is not False for row in valid_rows):
        _violation(violations, "dirty source SHA or row")
    protocol = manifest.get("protocol_digest")
    if protocol != selection.get("study_protocol_digest") or not _digest(protocol):
        _violation(violations, "wrong protocol digest")
    raw_shards = manifest.get("raw_shards")
    if not isinstance(raw_shards, list):
        raw_shards = []
        _violation(violations, "manifest has no raw shards")
    seen_files: set[str] = set()
    expected_environment: object | None = None
    all_keys: set[tuple[object, object, object, object]] = set()
    all_key_arms: dict[tuple[object, object, object], set[object]] = {}
    for item in raw_shards:
        if not isinstance(item, Mapping) or not isinstance(item.get("raw_file"), str):
            _violation(violations, "invalid raw shard manifest entry"); continue
        filename = item["raw_file"]
        if filename in seen_files: _violation(violations, "duplicate raw shard")
        seen_files.add(filename)
        if filename not in rows or filename not in actual_hashes:
            _violation(violations, "absent raw shard")
            continue
        if item.get("raw_sha256") != actual_hashes[filename]: _violation(violations, "raw shard hash mismatch")
        for row in rows[filename]:
            if not isinstance(row, Mapping):
                _violation(violations, "raw row schema violation"); continue
            key3 = (row.get("family"), row.get("instance_seed"), row.get("campaign_seed"))
            identity = (*key3, row.get("arm"))
            if identity in all_keys: _violation(violations, "duplicate campaign key")
            all_keys.add(identity)
            all_key_arms.setdefault(key3, set()).add(row.get("arm"))
            if row.get("budget") != 48: _violation(violations, "wrong budget")
            if row.get("terminal_rule") != "P": _violation(violations, "mixed terminal rule")
            if row.get("protocol_digest") != protocol: _violation(violations, "wrong protocol row")
            environment = row.get("environment")
            if expected_environment is None: expected_environment = environment
            elif environment != expected_environment: _violation(violations, "wrong environment")
            parents = row.get("parent_artifacts")
            if not isinstance(parents, Mapping) or any(parents.get(field) != row.get(f"{field}_digest") for field in ("spec", "config")) or parents.get("generator") != manifest.get("generator_digest"):
                _violation(violations, "parent-hash mismatch")
            score = row.get("scores")
            if isinstance(score, Mapping) and score.get("certificate_nonempty") is False and score.get("certificate_empirical_containment") is not None:
                _violation(violations, "invalid certificate denominator")
    for key, arms in all_key_arms.items():
        if arms != set(ARMS): _violation(violations, "missing campaign key or paired arm")
    expected_key_arms = {(family, key, 0, arm) for family in LOCKBOX_FAMILIES for key in range(LOCKBOX_SAMPLE_SIZE) for arm in ARMS}
    if all_keys != expected_key_arms:
        _violation(violations, "missing campaign key or unregistered campaign key")
    all_rows = valid_rows
    provenance = {
        "protocol_digest": manifest.get("protocol_digest"),
        "spec_digest": manifest.get("spec_digest"),
        "config_digest": manifest.get("config_digest"),
        "generator_digest": manifest.get("generator_digest"),
        "generator_manifest_sha256": manifest.get("generator_manifest_sha256"),
        "source_commit": manifest.get("source_commit"),
        "environment": all_rows[0].get("environment") if all_rows else None,
    }
    try:
        recomputed = confirmatory.analyse_lockbox_rows(all_rows, execution_mode="REGISTERED", provenance=provenance)
    except (TypeError, ValueError) as exc:
        _violation(violations, f"recomputed registered analysis invalid: {exc}")
        recomputed = None
    if recomputed is not None and (
        analysis.get("families") != recomputed["families"]
        or analysis.get("overall_verdict") != recomputed["overall_verdict"]
        or analysis.get("permissible_claim") != recomputed["permissible_claim"]
    ):
        _violation(violations, "analysis disagrees with recomputed registered bounds or denominators")
    families = analysis.get("families")
    expected_endpoints = {
        "map_noninferiority": "upper",
        "regret_noninferiority": "upper",
        "certificate_willingness": "lower",
        "certificate_validity": "lower",
    }
    computed_pass = True
    if not isinstance(families, Mapping) or set(families) != set(LOCKBOX_FAMILIES):
        computed_pass = False
    else:
        for family in LOCKBOX_FAMILIES:
            endpoints = families.get(family)
            if not isinstance(endpoints, Mapping) or set(endpoints) != set(expected_endpoints):
                computed_pass = False; continue
            for name, direction in expected_endpoints.items():
                endpoint = endpoints[name]
                if not isinstance(endpoint, Mapping):
                    computed_pass = False; continue
                bound, margin = endpoint.get("one_sided_bound"), endpoint.get("margin")
                valid = isinstance(bound, (int, float)) and not isinstance(bound, bool) and isinstance(margin, (int, float)) and not isinstance(margin, bool)
                passed = valid and (bound < margin if direction == "upper" else bound > margin)
                if endpoint.get("verdict") != ("PASS" if passed else "FAIL"):
                    _violation(violations, "analysis endpoint verdict disagrees with computed primary bound")
                computed_pass = computed_pass and passed
    if (analysis.get("overall_verdict") == "PASS") != computed_pass:
        _violation(violations, "analysis verdict disagrees with computed primary bounds")
    expected_claim = PERMISSIBLE_PASS_CLAIM if analysis.get("overall_verdict") == "PASS" else PERMISSIBLE_FAIL_CLAIM
    if analysis.get("permissible_claim") != expected_claim:
        _violation(violations, "unsupported prose claim")
    return violations


def build_release_report(**kwargs: object) -> dict[str, object]:
    violations = collect_release_violations(**kwargs)  # type: ignore[arg-type]
    analysis = kwargs["analysis"]
    manifest = kwargs["manifest"]
    verdict = "PASS" if not violations and analysis.get("overall_verdict") == "PASS" else "FAIL"
    claim = PERMISSIBLE_PASS_CLAIM if verdict == "PASS" else PERMISSIBLE_FAIL_CLAIM
    return {"schema": "boec-spade-lockbox-release-v1", "checks": {"all_registered_checks_pass": not violations, "analysis_verdict": analysis.get("overall_verdict")}, "hashes": dict(kwargs["actual_hashes"]), "row_counts": {name: len(value) for name, value in kwargs["rows"].items()}, "manifest_sample_size": manifest.get("sample_size"), "verdict": verdict, "violations": violations, "permissible_claim": claim}


def write_release_report(path: Path, report: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(report) + "\n").encode()
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle: handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True); raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path); parser.add_argument("--selection", required=True, type=Path); parser.add_argument("--analysis", required=True, type=Path); parser.add_argument("--out", default=ROOT / "results" / "spade-lockbox-release.json", type=Path)
    args = parser.parse_args(argv)
    manifest, selection, analysis = (json.loads(path.read_text()) for path in (args.manifest, args.selection, args.analysis))
    rows: dict[str, list[dict]] = {}; hashes: dict[str, str] = {}
    from boec.spade_study import read_jsonl_gzip
    protocol = manifest.get("protocol_digest")
    if not _digest(protocol):
        protocol = "0" * 64
    for shard in manifest.get("raw_shards", []):
        path = args.manifest.parent / shard["raw_file"]
        if path.is_file():
            hashes[path.name] = _sha256(path)
            try:
                rows[path.name] = read_jsonl_gzip(path, protocol_digest=protocol)
            except ValueError:
                rows[path.name] = []
    report = build_release_report(manifest=manifest, selection=selection, analysis=analysis, rows=rows, actual_hashes=hashes)
    write_release_report(args.out, report); print(_canonical_json(report)); return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
