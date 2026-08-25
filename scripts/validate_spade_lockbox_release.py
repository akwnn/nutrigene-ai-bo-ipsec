#!/usr/bin/env python3
"""Fail-closed release gate for SPADE lockbox artifacts; it never reruns campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts import analyse_spade_lockbox as confirmatory
from scripts import run_spade_lockbox as lockbox_contract


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("spade", "sobol48", "qlognei48")
LOCKBOX_FAMILIES = (
    "toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau",
)
LOCKBOX_SAMPLE_SIZE = 350
PERMISSIBLE_PASS_CLAIM = (
    "After prespecified selection on development families, the frozen 48-evaluation "
    "SPADE protocol matched the specialist Sobol map and qLogNEI optimizer within "
    "registered practical margins while issuing empirically calibrated conservative "
    "regions on four untouched randomized synthetic generator families."
)
PERMISSIBLE_FAIL_CLAIM = (
    "The registered lockbox intersection-union success rule did not pass; no superiority "
    "claim is supported."
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object, *, length: int = 64) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _violation(violations: list[str], message: str) -> None:
    if message not in violations:
        violations.append(message)


def _hash_actual(
    path: Path, *, key: str, label: str, hashes: dict[str, str], violations: list[str]
) -> bytes | None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        _violation(violations, f"{label} is missing or unreadable: {exc}")
        return None
    hashes[key] = hashlib.sha256(data).hexdigest()
    return data


def _load_json_mapping(
    path: Path, *, key: str, label: str, hashes: dict[str, str], violations: list[str]
) -> dict[str, object]:
    data = _hash_actual(path, key=key, label=label, hashes=hashes, violations=violations)
    if data is None:
        return {}
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _violation(violations, f"{label} JSON parse violation: {exc}")
        return {}
    if not isinstance(value, Mapping):
        _violation(violations, f"{label} schema violation: expected a JSON object")
        return {}
    return dict(value)


def _artifact_basename(
    item: Mapping[str, object], field: str, *, violations: list[str]
) -> str | None:
    value = item.get(field)
    if not isinstance(value, str) or not value or Path(value).name != value:
        _violation(violations, f"invalid raw shard {field} schema")
        return None
    return value


def _analysis_provenance(
    manifest: Mapping[str, object], rows: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return {
        "protocol_digest": manifest.get("protocol_digest"),
        "spec_digest": manifest.get("spec_digest"),
        "config_digest": manifest.get("config_digest"),
        "generator_digest": manifest.get("generator_digest"),
        "generator_manifest_sha256": manifest.get("generator_manifest_sha256"),
        "source_commit": manifest.get("source_commit"),
        "environment": rows[0].get("environment") if rows else None,
    }


def _recompute_registered_analysis(
    manifest: Mapping[str, object], rows: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return confirmatory.analyse_lockbox_rows(
        rows,
        execution_mode="REGISTERED",
        provenance=_analysis_provenance(manifest, rows),
    )


def _canonical_analysis_mismatch(
    stored: Mapping[str, object], recomputed: Mapping[str, object]
) -> bool:
    try:
        return _canonical_json(stored) != _canonical_json(recomputed)
    except (TypeError, ValueError):
        return True


def load_release_inputs(
    *, manifest_path: Path, selection_path: Path, analysis_path: Path
) -> dict[str, object]:
    """Defensively load, hash, normalize, and recompute every release input."""
    violations: list[str] = []
    hashes: dict[str, str] = {}
    manifest = _load_json_mapping(
        manifest_path,
        key="merged_manifest_sha256",
        label="merged manifest",
        hashes=hashes,
        violations=violations,
    )
    selection = _load_json_mapping(
        selection_path,
        key="selected_protocol_sha256",
        label="selected protocol",
        hashes=hashes,
        violations=violations,
    )
    analysis = _load_json_mapping(
        analysis_path,
        key="stored_analysis_sha256",
        label="stored analysis",
        hashes=hashes,
        violations=violations,
    )

    rows: dict[str, list[dict[str, object]]] = {}
    raw_shards = manifest.get("raw_shards")
    if not isinstance(raw_shards, list):
        _violation(violations, "merged manifest raw_shards schema violation")
        raw_shards = []
    protocol = manifest.get("protocol_digest")
    read_protocol = str(protocol) if _digest(protocol) else "0" * 64
    from boec.spade_study import read_jsonl_gzip

    seen_artifacts: set[str] = set()
    for index, item in enumerate(raw_shards):
        if not isinstance(item, Mapping):
            _violation(violations, f"invalid raw shard manifest entry at index {index}")
            continue
        raw_file = _artifact_basename(item, "raw_file", violations=violations)
        shard_file = _artifact_basename(item, "manifest_file", violations=violations)
        sidecar_file = _artifact_basename(item, "sha256_file", violations=violations)
        if raw_file is not None and (
            shard_file != f"{raw_file}.manifest.json"
            or sidecar_file != f"{raw_file}.sha256"
        ):
            _violation(violations, "raw shard artifact filename identity mismatch")
        names = [name for name in (raw_file, shard_file, sidecar_file) if name is not None]
        for name in names:
            if name in seen_artifacts:
                _violation(violations, f"duplicate release artifact filename: {name}")
            seen_artifacts.add(name)
        if raw_file is None:
            continue
        raw_path = manifest_path.parent / raw_file
        raw_data = _hash_actual(
            raw_path, key=raw_file, label="raw shard", hashes=hashes, violations=violations
        )
        if raw_data is not None and item.get("raw_sha256") != hashes[raw_file]:
            _violation(violations, f"raw shard hash mismatch: {raw_file}")

        if shard_file is not None:
            shard_path = manifest_path.parent / shard_file
            shard_manifest = _load_json_mapping(
                shard_path,
                key=shard_file,
                label="shard manifest",
                hashes=hashes,
                violations=violations,
            )
            if item.get("manifest_sha256") != hashes.get(shard_file):
                _violation(violations, f"shard manifest hash mismatch: {shard_file}")
            if shard_manifest and (
                set(shard_manifest) != lockbox_contract.SHARD_MANIFEST_FIELDS
                or shard_manifest.get("schema") != lockbox_contract.MANIFEST_SCHEMA
                or shard_manifest.get("status") != "COMPLETE"
            ):
                _violation(violations, f"shard manifest schema/completion violation: {shard_file}")
            if shard_manifest:
                shared = (
                    "family", "start", "stop", "raw_file", "raw_sha256", "protocol_digest",
                    "spec_digest", "config_digest", "generator_digest",
                    "generator_manifest_sha256", "source_commit", "source_dirty",
                    "selected_protocol_sha256", "selection_source_commit",
                )
                for field in shared:
                    expected = item.get(field) if field in item else manifest.get(field)
                    if shard_manifest.get(field) != expected:
                        _violation(
                            violations,
                            f"shard manifest {field} identity mismatch: {shard_file}",
                        )

        if sidecar_file is not None:
            sidecar_path = manifest_path.parent / sidecar_file
            sidecar_data = _hash_actual(
                sidecar_path,
                key=sidecar_file,
                label="SHA-256 sidecar",
                hashes=hashes,
                violations=violations,
            )
            if item.get("sha256_sha256") != hashes.get(sidecar_file):
                _violation(violations, f"SHA-256 sidecar hash mismatch: {sidecar_file}")
            if sidecar_data is not None:
                try:
                    sidecar_tokens = sidecar_data.decode("ascii").split()
                except UnicodeDecodeError:
                    sidecar_tokens = []
                if sidecar_tokens != [item.get("raw_sha256"), raw_file]:
                    _violation(violations, f"SHA-256 sidecar content mismatch: {sidecar_file}")

        if raw_data is not None:
            try:
                rows[raw_file] = read_jsonl_gzip(raw_path, protocol_digest=read_protocol)
            except Exception as exc:  # untrusted artifact parsers must become report violations
                rows[raw_file] = []
                _violation(violations, f"raw shard parse/schema violation {raw_file}: {exc}")

    all_rows = [row for shard_rows in rows.values() for row in shard_rows]
    recomputed: dict[str, object] | None
    try:
        recomputed = _recompute_registered_analysis(manifest, all_rows)
    except (KeyError, TypeError, ValueError) as exc:
        recomputed = None
        _violation(violations, f"recomputed registered analysis invalid: {exc}")
    if recomputed is not None and _canonical_analysis_mismatch(analysis, recomputed):
        _violation(
            violations,
            "stored analysis canonical document disagrees with recomputed REGISTERED analysis",
        )
    return {
        "manifest": manifest,
        "selection": selection,
        "analysis": analysis,
        "rows": rows,
        "actual_hashes": hashes,
        "input_violations": violations,
        "recomputed_analysis": recomputed,
    }


def collect_release_violations(
    *,
    manifest: Mapping[str, object],
    selection: Mapping[str, object],
    analysis: Mapping[str, object],
    rows: Mapping[str, Sequence[Mapping[str, object]]],
    actual_hashes: Mapping[str, str],
    input_violations: Sequence[str] = (),
    recomputed_analysis: Mapping[str, object] | None = None,
) -> list[str]:
    """Return every independently detectable release violation, never fail fast."""
    violations = [value for value in input_violations if isinstance(value, str)]
    if not isinstance(manifest, Mapping):
        _violation(violations, "manifest schema violation")
        manifest = {}
    if not isinstance(selection, Mapping):
        _violation(violations, "selection schema violation")
        selection = {}
    if not isinstance(analysis, Mapping):
        _violation(violations, "analysis schema violation")
        analysis = {}
    if not isinstance(rows, Mapping):
        _violation(violations, "raw row mapping schema violation")
        rows = {}
    if not isinstance(actual_hashes, Mapping):
        _violation(violations, "actual hash mapping schema violation")
        actual_hashes = {}

    if set(manifest) != lockbox_contract.MERGED_MANIFEST_FIELDS:
        _violation(violations, "merged manifest schema violation")
    if manifest.get("schema") != lockbox_contract.MERGED_MANIFEST_SCHEMA:
        _violation(violations, "merged manifest schema identity violation")
    if manifest.get("status") != "COMPLETE":
        _violation(violations, "lockbox manifest is not COMPLETE")
    sample_size = manifest.get("sample_size")
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size != LOCKBOX_SAMPLE_SIZE:
        _violation(violations, "unregistered sample size")
    if manifest.get("source_dirty") is not False:
        _violation(violations, "dirty source SHA or row")
    for field, length in (
        ("protocol_digest", 64), ("spec_digest", 64), ("config_digest", 64),
        ("generator_digest", 64), ("generator_manifest_sha256", 64),
        ("selected_protocol_sha256", 64), ("source_commit", 40),
        ("selection_source_commit", 40),
    ):
        if not _digest(manifest.get(field), length=length):
            _violation(violations, f"merged manifest {field} digest schema violation")

    try:
        validated_selection = lockbox_contract.validate_selected_protocol_payload(selection)
    except (TypeError, ValueError) as exc:
        validated_selection = dict(selection)
        _violation(violations, f"selection schema violation: {exc}")
    if validated_selection.get("status") != "SELECTED":
        _violation(violations, "premature lockbox without selected protocol")
    selected_actual = actual_hashes.get("selected_protocol_sha256")
    if not _digest(selected_actual) or selected_actual != manifest.get("selected_protocol_sha256"):
        _violation(violations, "actual selection hash does not match merged selected protocol hash")
    selection_bindings = (
        ("study_protocol_digest", "protocol_digest", "selection study protocol mismatch"),
        ("source_commit", "selection_source_commit", "selection source mismatch"),
        ("spec_digest", "spec_digest", "selection spec mismatch"),
        ("config_digest", "config_digest", "selection config mismatch"),
        ("generator_digest", "generator_digest", "selection generator source mismatch"),
        (
            "generator_manifest_sha256", "generator_manifest_sha256",
            "selection generator manifest mismatch",
        ),
    )
    for selection_field, manifest_field, message in selection_bindings:
        if validated_selection.get(selection_field) != manifest.get(manifest_field):
            _violation(violations, message)
    if manifest.get("lockbox_started_before_selection_commit") is True:
        _violation(violations, "premature lockbox before selection commit")

    valid_rows: list[Mapping[str, object]] = []
    for filename, shard_rows in rows.items():
        if (
            not isinstance(filename, str)
            or not isinstance(shard_rows, Sequence)
            or isinstance(shard_rows, (str, bytes))
        ):
            _violation(violations, "raw row schema violation")
            continue
        for row in shard_rows:
            if not isinstance(row, Mapping):
                _violation(violations, "raw row schema violation")
                continue
            valid_rows.append(row)

    raw_shards = manifest.get("raw_shards")
    if not isinstance(raw_shards, list):
        raw_shards = []
        _violation(violations, "manifest has no raw shards")
    seen_files: set[str] = set()
    ranges: dict[str, list[tuple[int, int]]] = {family: [] for family in LOCKBOX_FAMILIES}
    for item in raw_shards:
        if not isinstance(item, Mapping) or set(item) != lockbox_contract.MERGED_RAW_SHARD_FIELDS:
            _violation(violations, "invalid raw shard manifest entry")
            if not isinstance(item, Mapping):
                continue
        filename = item.get("raw_file")
        if not isinstance(filename, str) or Path(filename).name != filename:
            _violation(violations, "invalid raw shard manifest entry")
            continue
        if filename in seen_files:
            _violation(violations, "duplicate raw shard")
        seen_files.add(filename)
        if (
            item.get("manifest_file") != f"{filename}.manifest.json"
            or item.get("sha256_file") != f"{filename}.sha256"
        ):
            _violation(violations, "raw shard artifact filename identity mismatch")
        if filename not in rows or filename not in actual_hashes:
            _violation(violations, "absent raw shard")
        elif item.get("raw_sha256") != actual_hashes.get(filename):
            _violation(violations, "raw shard hash mismatch")
        for file_field, digest_field, label in (
            ("manifest_file", "manifest_sha256", "shard manifest hash mismatch"),
            ("sha256_file", "sha256_sha256", "SHA-256 sidecar hash mismatch"),
        ):
            artifact = item.get(file_field)
            if not isinstance(artifact, str) or artifact not in actual_hashes:
                _violation(violations, f"absent {label.removesuffix(' hash mismatch')}")
            elif item.get(digest_field) != actual_hashes.get(artifact):
                _violation(violations, label)
        family, start, stop = item.get("family"), item.get("start"), item.get("stop")
        if (
            family not in LOCKBOX_FAMILIES
            or isinstance(start, bool) or not isinstance(start, int)
            or isinstance(stop, bool) or not isinstance(stop, int)
            or not 0 <= start < stop <= LOCKBOX_SAMPLE_SIZE
        ):
            _violation(violations, "raw shard has unregistered family/range")
        else:
            ranges[str(family)].append((start, stop))
    if set(rows) != seen_files:
        _violation(violations, "raw row mapping does not exactly match merged raw shards")
    for family, intervals in ranges.items():
        cursor = 0
        for start, stop in sorted(intervals):
            if start != cursor:
                _violation(violations, f"raw shard ranges are missing or overlap for {family}")
                break
            cursor = stop
        if cursor != LOCKBOX_SAMPLE_SIZE:
            _violation(violations, f"raw shard ranges are incomplete for {family}")

    expected_environment: object | None = None
    all_keys: set[tuple[object, object, object, object]] = set()
    all_key_arms: dict[tuple[object, object, object], set[object]] = {}
    for row in valid_rows:
        key3 = (row.get("family"), row.get("instance_seed"), row.get("campaign_seed"))
        identity = (*key3, row.get("arm"))
        if identity in all_keys:
            _violation(violations, "duplicate campaign key")
        all_keys.add(identity)
        all_key_arms.setdefault(key3, set()).add(row.get("arm"))
        if row.get("budget") != 48:
            _violation(violations, "wrong budget")
        if row.get("terminal_rule") != "P":
            _violation(violations, "mixed terminal rule")
        if row.get("source_dirty") is not False:
            _violation(violations, "dirty source SHA or row")
        for row_field, manifest_field, label in (
            ("protocol_digest", "protocol_digest", "wrong protocol row"),
            ("spec_digest", "spec_digest", "wrong spec row"),
            ("config_digest", "config_digest", "wrong config row"),
            ("source_commit", "source_commit", "wrong source row"),
        ):
            if row.get(row_field) != manifest.get(manifest_field):
                _violation(violations, label)
        environment = row.get("environment")
        if expected_environment is None:
            expected_environment = environment
        elif environment != expected_environment:
            _violation(violations, "wrong environment")
        parents = row.get("parent_artifacts")
        expected_parents = {
            "spec": manifest.get("spec_digest"),
            "config": manifest.get("config_digest"),
            "generator": manifest.get("generator_digest"),
            "generator_manifest": manifest.get("generator_manifest_sha256"),
            "selected_protocol": manifest.get("selected_protocol_sha256"),
        }
        if not isinstance(parents, Mapping) or any(
            parents.get(name) != digest for name, digest in expected_parents.items()
        ):
            _violation(violations, "parent-hash mismatch")
        score = row.get("scores")
        if (
            isinstance(score, Mapping)
            and score.get("certificate_nonempty") is False
            and score.get("certificate_empirical_containment") is not None
        ):
            _violation(violations, "invalid certificate denominator")
    for arms in all_key_arms.values():
        if arms != set(ARMS):
            _violation(violations, "missing campaign key or paired arm")
    expected_key_arms = {
        (family, key, 0, arm)
        for family in LOCKBOX_FAMILIES
        for key in range(LOCKBOX_SAMPLE_SIZE)
        for arm in ARMS
    }
    if all_keys != expected_key_arms:
        _violation(violations, "missing campaign key or unregistered campaign key")

    recomputed = recomputed_analysis
    if recomputed is None:
        try:
            recomputed = _recompute_registered_analysis(manifest, valid_rows)
        except (KeyError, TypeError, ValueError) as exc:
            _violation(violations, f"recomputed registered analysis invalid: {exc}")
    if recomputed is not None and _canonical_analysis_mismatch(analysis, recomputed):
        _violation(
            violations,
            "stored analysis canonical document disagrees with recomputed REGISTERED analysis",
        )

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
                computed_pass = False
                continue
            for name, direction in expected_endpoints.items():
                endpoint = endpoints[name]
                if not isinstance(endpoint, Mapping):
                    computed_pass = False
                    continue
                bound, margin = endpoint.get("one_sided_bound"), endpoint.get("margin")
                valid = (
                    isinstance(bound, (int, float)) and not isinstance(bound, bool)
                    and math.isfinite(float(bound))
                    and isinstance(margin, (int, float)) and not isinstance(margin, bool)
                    and math.isfinite(float(margin))
                )
                passed = valid and (bound < margin if direction == "upper" else bound > margin)
                if endpoint.get("verdict") != ("PASS" if passed else "FAIL"):
                    _violation(
                        violations,
                        "analysis endpoint verdict disagrees with computed primary bound",
                    )
                computed_pass = computed_pass and passed
    if (analysis.get("overall_verdict") == "PASS") != computed_pass:
        _violation(violations, "analysis verdict disagrees with computed primary bounds")
    expected_claim = (
        PERMISSIBLE_PASS_CLAIM
        if analysis.get("overall_verdict") == "PASS"
        else PERMISSIBLE_FAIL_CLAIM
    )
    if analysis.get("permissible_claim") != expected_claim:
        _violation(violations, "unsupported prose claim")
    return violations


def build_release_report(**kwargs: object) -> dict[str, object]:
    violations = collect_release_violations(**kwargs)  # type: ignore[arg-type]
    analysis = kwargs.get("analysis")
    manifest = kwargs.get("manifest")
    rows = kwargs.get("rows")
    hashes = kwargs.get("actual_hashes")
    analysis_mapping = analysis if isinstance(analysis, Mapping) else {}
    manifest_mapping = manifest if isinstance(manifest, Mapping) else {}
    row_mapping = rows if isinstance(rows, Mapping) else {}
    hash_mapping = hashes if isinstance(hashes, Mapping) else {}
    verdict = (
        "PASS"
        if not violations and analysis_mapping.get("overall_verdict") == "PASS"
        else "FAIL"
    )
    claim = PERMISSIBLE_PASS_CLAIM if verdict == "PASS" else PERMISSIBLE_FAIL_CLAIM
    row_counts = {
        str(name): len(value)
        for name, value in row_mapping.items()
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
    }
    return {
        "schema": "boec-spade-lockbox-release-v1",
        "checks": {
            "all_registered_checks_pass": not violations,
            "analysis_verdict": analysis_mapping.get("overall_verdict"),
        },
        "hashes": dict(hash_mapping),
        "row_counts": row_counts,
        "manifest_sample_size": manifest_mapping.get("sample_size"),
        "verdict": verdict,
        "violations": violations,
        "permissible_claim": claim,
    }


def write_release_report(path: Path, report: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(report) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument(
        "--out", default=ROOT / "results" / "spade-lockbox-release.json", type=Path
    )
    args = parser.parse_args(argv)
    loaded = load_release_inputs(
        manifest_path=args.manifest,
        selection_path=args.selection,
        analysis_path=args.analysis,
    )
    report = build_release_report(**loaded)
    write_release_report(args.out, report)
    print(_canonical_json(report))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
