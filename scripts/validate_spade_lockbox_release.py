#!/usr/bin/env python3
"""Fail-closed release gate for SPADE lockbox artifacts; it never reruns campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from boec.spade_power import validate_power_plan_payload
from scripts import analyse_spade_lockbox as confirmatory
from scripts import run_spade_lockbox as lockbox_contract


ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = Path(__file__).resolve().parents[1]
ARMS = ("spade", "sobol48", "qlognei48")
LOCKBOX_FAMILIES = (
    "toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau",
)
POWER_RELATIVE_PATH = Path("results/spade-lockbox-power.json")
POWER_SOURCE_BLOBS = {
    "power_design_sha256": Path(
        "docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md"
    ),
    "power_engine_sha256": Path("src/boec/spade_power.py"),
    "power_planner_sha256": Path("scripts/plan_spade_lockbox_power.py"),
}
EXECUTION_SOURCE_BLOBS = (
    Path("scripts/run_spade_lockbox.py"),
    Path("scripts/analyse_spade_lockbox.py"),
    Path("scripts/validate_spade_lockbox_release.py"),
    Path("src/boec/spade_study.py"),
)
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


def _canonical_bytes(value: object) -> bytes:
    return (_canonical_json(value) + "\n").encode("utf-8")


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


def _strict_json_loads(data: bytes) -> object:
    def finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value

    def reject_constant(token: str) -> object:
        raise ValueError(f"non-finite JSON constant: {token}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    return json.loads(
        data,
        parse_float=finite_float,
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        converted = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


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
        value = _strict_json_loads(data)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        _violation(violations, f"{label} JSON parse violation: {exc}")
        return {}
    if not isinstance(value, Mapping):
        _violation(violations, f"{label} schema violation: expected a JSON object")
        return {}
    return dict(value)


def _git_output(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(message or f"git {' '.join(args)} failed")
    return completed.stdout


def _validated_repo_root(repo_root: Path) -> Path:
    lexical = Path(os.path.abspath(repo_root))
    output = _git_output(lexical, "rev-parse", "--show-toplevel")
    actual = Path(output.decode("utf-8").strip())
    if actual != lexical:
        raise ValueError("release repository root does not match its Git worktree root")
    return lexical


def _reject_symlink_components(repo_root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("power plan is outside its repository") from exc
    cursor = repo_root
    for component in relative.parts:
        cursor = cursor / component
        try:
            metadata = os.lstat(cursor)
        except OSError as exc:
            raise ValueError(f"power plan is missing or unreadable: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"power plan path contains a symlink: {cursor}")
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise ValueError("power plan path is not a regular file")


def _committed_power_bytes(repo_root: Path) -> bytes:
    relative = POWER_RELATIVE_PATH.as_posix()
    entry = _git_output(repo_root, "ls-tree", "-z", "HEAD", "--", relative)
    try:
        metadata, recorded_path = entry.rstrip(b"\0").split(b"\t", 1)
        mode, kind, _object_id = metadata.split(b" ", 2)
    except ValueError as exc:
        raise ValueError("power plan has no unique committed HEAD tree entry") from exc
    if recorded_path.decode("utf-8") != relative or kind != b"blob" or mode not in {
        b"100644",
        b"100755",
    }:
        raise ValueError("power plan HEAD entry is not the registered regular file")
    return _git_output(repo_root, "show", f"HEAD:{relative}")


def _git_commit_exists(repo_root: Path, commit: object) -> bool:
    if not _digest(commit, length=40):
        return False
    try:
        _git_output(repo_root, "cat-file", "-e", f"{commit}^{{commit}}")
    except ValueError:
        return False
    return True


def _git_is_ancestor(repo_root: Path, older: str, newer: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", older, newer],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.returncode == 0


def _committed_blob_sha256(repo_root: Path, commit: str, path: Path) -> str:
    relative = path.as_posix()
    entry = _git_output(repo_root, "ls-tree", "-z", commit, "--", relative)
    try:
        metadata, recorded_path = entry.rstrip(b"\0").split(b"\t", 1)
        mode, kind, _object_id = metadata.split(b" ", 2)
    except ValueError as exc:
        raise ValueError(f"registered source blob is absent: {relative}") from exc
    if recorded_path.decode("utf-8") != relative or kind != b"blob" or mode not in {
        b"100644",
        b"100755",
    }:
        raise ValueError(f"registered source path is not a regular blob: {relative}")
    return hashlib.sha256(_git_output(repo_root, "show", f"{commit}:{relative}")).hexdigest()


def _load_power_plan(
    path: Path,
    *,
    repo_root: Path,
    hashes: dict[str, str],
    violations: list[str],
) -> dict[str, object]:
    """Authenticate the exact committed power file before any outcome shard is read."""
    lexical = Path(os.path.abspath(path))
    safe_regular_file = False
    try:
        repo_root = _validated_repo_root(repo_root)
        expected = repo_root / POWER_RELATIVE_PATH
        if lexical != expected:
            raise ValueError(f"power plan must use the exact registered path {expected}")
        _reject_symlink_components(repo_root, lexical)
        safe_regular_file = True
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _violation(violations, f"power plan registered path violation: {exc}")

    data = (
        _hash_actual(
            lexical,
            key="power_plan_sha256",
            label="power plan",
            hashes=hashes,
            violations=violations,
        )
        if safe_regular_file
        else None
    )
    if data is None:
        return {}

    if repo_root is not None:
        try:
            if data != _committed_power_bytes(repo_root):
                raise ValueError("working-tree bytes differ from committed HEAD bytes")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            _violation(violations, f"power plan committed-file violation: {exc}")

    try:
        parsed = _strict_json_loads(data)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        _violation(violations, f"power plan JSON parse violation: {exc}")
        return {}
    if not isinstance(parsed, Mapping):
        _violation(violations, "power plan schema violation: expected a JSON object")
        return {}
    try:
        if data != _canonical_bytes(parsed):
            raise ValueError("bytes are not the exact canonical serialization")
    except (RecursionError, TypeError, ValueError) as exc:
        _violation(violations, f"power plan canonical-byte violation: {exc}")
        return dict(parsed)
    try:
        return validate_power_plan_payload(parsed)
    except (OverflowError, RecursionError, TypeError, ValueError) as exc:
        _violation(violations, f"power plan schema/decision violation: {exc}")
        return dict(parsed)


def _power_sample_size(
    power_plan: Mapping[str, object], *, violations: list[str]
) -> int | None:
    if power_plan.get("status") != "POWERED":
        _violation(violations, "release requires an authentic POWERED power plan")
        return None
    decision = power_plan.get("decision")
    selected_n = decision.get("selected_sample_size") if isinstance(decision, Mapping) else None
    if (
        isinstance(selected_n, bool)
        or not isinstance(selected_n, int)
        or not 350 <= selected_n <= 2000
    ):
        _violation(violations, "power plan selected sample size is invalid")
        return None
    return selected_n


def _canonical_equal(left: object, right: object) -> bool:
    try:
        return _canonical_json(left) == _canonical_json(right)
    except (RecursionError, TypeError, ValueError):
        return False


def _preflight_power_bindings(
    *,
    repo_root: Path,
    manifest: Mapping[str, object],
    selection: Mapping[str, object],
    power_plan: Mapping[str, object],
    top_level_hashes: Mapping[str, str],
    violations: list[str],
) -> int | None:
    """Authorize outcome reads only after every immutable power binding is proven."""
    if (
        set(manifest) != lockbox_contract.MERGED_MANIFEST_FIELDS
        or manifest.get("schema") != lockbox_contract.MERGED_MANIFEST_SCHEMA
        or manifest.get("status") != "COMPLETE"
        or manifest.get("source_dirty") is not False
    ):
        _violation(violations, "merged manifest preflight schema/provenance violation")
    try:
        validated_selection = lockbox_contract.validate_selected_protocol_payload(selection)
    except (TypeError, ValueError) as exc:
        validated_selection = dict(selection)
        _violation(violations, f"selection preflight schema violation: {exc}")
    try:
        validated_power = validate_power_plan_payload(power_plan)
    except (OverflowError, RecursionError, TypeError, ValueError) as exc:
        _violation(violations, f"power plan preflight schema/decision violation: {exc}")
        return None
    sample_size = _power_sample_size(validated_power, violations=violations)

    selected_actual = top_level_hashes.get("selected_protocol_sha256")
    power_actual = top_level_hashes.get("power_plan_sha256")
    if (
        not _digest(selected_actual)
        or selected_actual != manifest.get("selected_protocol_sha256")
    ):
        _violation(violations, "preflight selection hash mismatch")
    if not _digest(power_actual) or power_actual != manifest.get("power_plan_sha256"):
        _violation(violations, "preflight power hash mismatch")
    if sample_size is None or manifest.get("sample_size") != sample_size:
        _violation(violations, "preflight power sample-size mismatch")
    try:
        lockbox_contract.validate_environment_compatibility(
            manifest.get("environment_compatibility")
        )
    except (TypeError, ValueError) as exc:
        _violation(violations, f"preflight environment compatibility violation: {exc}")

    selection_bindings = {
        "study_protocol_digest": "protocol_digest",
        "spec_digest": "spec_digest",
        "config_digest": "config_digest",
        "generator_digest": "generator_digest",
        "generator_manifest_sha256": "generator_manifest_sha256",
    }
    if any(
        validated_selection.get(selection_field) != manifest.get(manifest_field)
        for selection_field, manifest_field in selection_bindings.items()
    ):
        _violation(violations, "preflight selection/manifest provenance mismatch")

    power_selected = validated_power.get("selected_protocol")
    if not isinstance(power_selected, Mapping) or (
        power_selected.get("sha256") != selected_actual
        or power_selected.get("source_commit")
        != validated_selection.get("source_commit")
    ):
        _violation(violations, "preflight power selected protocol binding mismatch")
    if validated_power.get("source_commit") != manifest.get("power_source_commit"):
        _violation(violations, "preflight power source provenance mismatch")

    power_digests = validated_power.get("digests")
    expected_power_digests = {
        "study_protocol_sha256": manifest.get("protocol_digest"),
        "specification_sha256": manifest.get("spec_digest"),
        "configuration_sha256": manifest.get("config_digest"),
        "generator_sha256": manifest.get("generator_digest"),
        "generator_manifest_sha256": manifest.get("generator_manifest_sha256"),
    }
    if not isinstance(power_digests, Mapping) or any(
        power_digests.get(field) != digest
        for field, digest in expected_power_digests.items()
    ):
        _violation(violations, "preflight power digest provenance mismatch")

    try:
        selected_artifacts, selected_folds = lockbox_contract._selection_power_bindings(
            validated_selection
        )
    except (TypeError, ValueError) as exc:
        selected_artifacts, selected_folds = [], []
        _violation(
            violations, f"preflight selection development provenance violation: {exc}"
        )
    proof = validated_power.get("held_out_proof")
    if (
        not isinstance(proof, Mapping)
        or proof.get("selected_candidate")
        != validated_selection.get("selected_candidate")
        or not _canonical_equal(proof.get("folds"), selected_folds)
        or not _canonical_equal(
            validated_power.get("development_artifacts"), selected_artifacts
        )
    ):
        _violation(violations, "preflight power development provenance mismatch")

    selection_source = validated_selection.get("source_commit")
    power_source = validated_power.get("source_commit")
    execution_source = manifest.get("source_commit")
    try:
        head = _git_output(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    except (UnicodeDecodeError, ValueError) as exc:
        head = ""
        _violation(violations, f"release HEAD provenance violation: {exc}")
    for label, commit in (
        ("selection", selection_source),
        ("power", power_source),
        ("execution", execution_source),
    ):
        if not _git_commit_exists(repo_root, commit):
            _violation(
                violations, f"{label} source commit does not exist in project Git"
            )
    if all(
        _git_commit_exists(repo_root, commit)
        for commit in (selection_source, power_source, execution_source, head)
    ):
        selection_commit = str(selection_source)
        power_commit = str(power_source)
        execution_commit = str(execution_source)
        if not _git_is_ancestor(repo_root, selection_commit, power_commit):
            _violation(violations, "selection source is not an ancestor of power source")
        if not _git_is_ancestor(repo_root, power_commit, execution_commit):
            _violation(violations, "power source is not an ancestor of execution source")
        if not _git_is_ancestor(repo_root, execution_commit, head):
            _violation(violations, "execution source is not an ancestor of release HEAD")
        for path in EXECUTION_SOURCE_BLOBS:
            try:
                committed_digest = _committed_blob_sha256(
                    repo_root, execution_commit, path
                )
                live_digest = hashlib.sha256(
                    (_SOURCE_ROOT / path).read_bytes()
                ).hexdigest()
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                _violation(
                    violations, f"execution source blob provenance violation: {exc}"
                )
                continue
            if committed_digest != live_digest:
                _violation(
                    violations,
                    f"execution source blob digest mismatch: {path.as_posix()}",
                )
        if isinstance(power_digests, Mapping):
            for field, path in POWER_SOURCE_BLOBS.items():
                try:
                    actual = _committed_blob_sha256(repo_root, power_commit, path)
                except (UnicodeDecodeError, ValueError) as exc:
                    _violation(
                        violations, f"power source blob provenance violation: {exc}"
                    )
                    continue
                if power_digests.get(field) != actual:
                    _violation(
                        violations,
                        f"power source blob digest mismatch: {field}",
                    )
    return sample_size if not violations else None


def _artifact_basename(
    item: Mapping[str, object], field: str, *, violations: list[str]
) -> str | None:
    value = item.get(field)
    if not isinstance(value, str) or not value or Path(value).name != value:
        _violation(violations, f"invalid raw shard {field} schema")
        return None
    return value


def _analysis_provenance(
    manifest: Mapping[str, object], rows: Sequence[Mapping[str, object]], *, sample_size: int
) -> dict[str, object]:
    return {
        "protocol_digest": manifest.get("protocol_digest"),
        "spec_digest": manifest.get("spec_digest"),
        "config_digest": manifest.get("config_digest"),
        "generator_digest": manifest.get("generator_digest"),
        "generator_manifest_sha256": manifest.get("generator_manifest_sha256"),
        "source_commit": manifest.get("source_commit"),
        "selected_protocol_sha256": manifest.get("selected_protocol_sha256"),
        "power_plan_sha256": manifest.get("power_plan_sha256"),
        "power_source_commit": manifest.get("power_source_commit"),
        "sample_size": sample_size,
        "environment_compatibility": manifest.get("environment_compatibility"),
    }


def _recompute_registered_analysis(
    manifest: Mapping[str, object], rows: Sequence[Mapping[str, object]], *, sample_size: int
) -> dict[str, object]:
    return confirmatory.analyse_lockbox_rows(
        rows,
        execution_mode="REGISTERED",
        sample_size=sample_size,
        provenance=_analysis_provenance(manifest, rows, sample_size=sample_size),
    )


def _canonical_analysis_mismatch(
    stored: Mapping[str, object], recomputed: Mapping[str, object]
) -> bool:
    try:
        return _canonical_json(stored) != _canonical_json(recomputed)
    except (TypeError, ValueError):
        return True


def load_release_inputs(
    *,
    manifest_path: Path,
    selection_path: Path,
    power_path: Path,
    analysis_path: Path,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Defensively load, hash, normalize, and recompute every release input."""
    violations: list[str] = []
    top_level_hashes: dict[str, str] = {}
    shard_hashes: dict[str, dict[str, str]] = {}
    hashes: dict[str, object] = {
        "top_level": top_level_hashes,
        "raw_shards": shard_hashes,
    }
    actual_repo_root = repo_root or ROOT
    power_plan = _load_power_plan(
        power_path,
        repo_root=actual_repo_root,
        hashes=top_level_hashes,
        violations=violations,
    )
    manifest = _load_json_mapping(
        manifest_path,
        key="merged_manifest_sha256",
        label="merged manifest",
        hashes=top_level_hashes,
        violations=violations,
    )
    selection = _load_json_mapping(
        selection_path,
        key="selected_protocol_sha256",
        label="selected protocol",
        hashes=top_level_hashes,
        violations=violations,
    )
    if violations:
        sample_size = None
    else:
        sample_size = _preflight_power_bindings(
            repo_root=_validated_repo_root(actual_repo_root),
            manifest=manifest,
            selection=selection,
            power_plan=power_plan,
            top_level_hashes=top_level_hashes,
            violations=violations,
        )
    if sample_size is None:
        analysis: dict[str, object] = {}
        _violation(
            violations,
            "stored analysis and lockbox outcomes were not opened because power preflight failed",
        )
    else:
        analysis = _load_json_mapping(
            analysis_path,
            key="stored_analysis_sha256",
            label="stored analysis",
            hashes=top_level_hashes,
            violations=violations,
        )

    rows: dict[str, list[dict[str, object]]] = {}
    raw_shards = manifest.get("raw_shards")
    if not isinstance(raw_shards, list):
        _violation(violations, "merged manifest raw_shards schema violation")
        raw_shards = []
    if sample_size is None:
        raw_shards = []
    protocol = manifest.get("protocol_digest")
    read_protocol = str(protocol) if _digest(protocol) else "0" * 64
    from boec.spade_study import read_jsonl_gzip_bytes

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
        if raw_file is not None:
            try:
                expected_raw_file = lockbox_contract.registered_raw_filename(
                    item.get("family"), item.get("start"), item.get("stop"),
                    sample_size=sample_size,
                )
            except (TypeError, ValueError) as exc:
                expected_raw_file = None
                _violation(violations, f"raw shard family/range violation: {exc}")
            if expected_raw_file is not None and raw_file != expected_raw_file:
                _violation(violations, f"exact registered raw filename mismatch: {raw_file}")
        names = [name for name in (raw_file, shard_file, sidecar_file) if name is not None]
        for name in names:
            if name in seen_artifacts:
                _violation(violations, f"duplicate release artifact filename: {name}")
            seen_artifacts.add(name)
        if raw_file is None:
            continue
        artifact_hashes = shard_hashes.setdefault(raw_file, {})
        raw_path = manifest_path.parent / raw_file
        sidecar_data: bytes | None = None
        raw_data = _hash_actual(
            raw_path,
            key="raw_sha256",
            label="raw shard",
            hashes=artifact_hashes,
            violations=violations,
        )
        if raw_data is not None and item.get("raw_sha256") != artifact_hashes["raw_sha256"]:
            _violation(violations, f"raw shard hash mismatch: {raw_file}")

        if shard_file is not None:
            shard_path = manifest_path.parent / shard_file
            shard_manifest = _load_json_mapping(
                shard_path,
                key="manifest_sha256",
                label="shard manifest",
                hashes=artifact_hashes,
                violations=violations,
            )
            if item.get("manifest_sha256") != artifact_hashes.get("manifest_sha256"):
                _violation(violations, f"shard manifest hash mismatch: {shard_file}")
            if shard_manifest:
                try:
                    lockbox_contract.validate_completed_shard_contract(
                        shard_manifest,
                        sample_size=sample_size,
                        merged_entry=item,
                        merged_manifest=manifest,
                    )
                except (TypeError, ValueError) as exc:
                    _violation(violations, f"shard manifest violation {shard_file}: {exc}")

        if sidecar_file is not None:
            sidecar_path = manifest_path.parent / sidecar_file
            sidecar_data = _hash_actual(
                sidecar_path,
                key="sha256_sha256",
                label="SHA-256 sidecar",
                hashes=artifact_hashes,
                violations=violations,
            )
            if item.get("sha256_sha256") != artifact_hashes.get("sha256_sha256"):
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
                if sidecar_data is None:
                    raise ValueError("raw shard sidecar bytes are unavailable")
                shard_rows = read_jsonl_gzip_bytes(
                    raw_data,
                    sidecar_data,
                    source_name=raw_file,
                    protocol_digest=read_protocol,
                )
                rows[raw_file] = shard_rows
                lockbox_contract.validate_shard_local_rows(
                    shard_rows,
                    family=item.get("family"),
                    start=item.get("start"),
                    stop=item.get("stop"),
                    sample_size=sample_size,
                )
            except Exception as exc:  # untrusted artifact parsers must become report violations
                rows.setdefault(raw_file, [])
                _violation(violations, f"raw shard parse/schema/local grid violation {raw_file}: {exc}")

    all_rows = [row for shard_rows in rows.values() for row in shard_rows]
    recomputed: dict[str, object] | None
    if sample_size is None:
        recomputed = None
    else:
        try:
            recomputed = _recompute_registered_analysis(
                manifest, all_rows, sample_size=sample_size
            )
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
        "power_plan": power_plan,
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
    power_plan: Mapping[str, object],
    analysis: Mapping[str, object],
    rows: Mapping[str, Sequence[Mapping[str, object]]],
    actual_hashes: Mapping[str, object],
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
    if not isinstance(power_plan, Mapping):
        _violation(violations, "power plan schema violation")
        power_plan = {}
    if not isinstance(analysis, Mapping):
        _violation(violations, "analysis schema violation")
        analysis = {}
    if not isinstance(rows, Mapping):
        _violation(violations, "raw row mapping schema violation")
        rows = {}
    if not isinstance(actual_hashes, Mapping):
        _violation(violations, "actual hash mapping schema violation")
        actual_hashes = {}
    top_level_hashes = actual_hashes.get("top_level")
    per_shard_hashes = actual_hashes.get("raw_shards")
    if not isinstance(top_level_hashes, Mapping):
        _violation(violations, "top-level actual hash namespace schema violation")
        top_level_hashes = {}
    if not isinstance(per_shard_hashes, Mapping):
        _violation(violations, "per-shard actual hash namespace schema violation")
        per_shard_hashes = {}

    try:
        validated_power = validate_power_plan_payload(power_plan)
    except (OverflowError, RecursionError, TypeError, ValueError) as exc:
        validated_power = dict(power_plan)
        power_valid = False
        _violation(violations, f"power plan schema/decision violation: {exc}")
    else:
        power_valid = True
    power_sample_size = (
        _power_sample_size(validated_power, violations=violations)
        if power_valid
        else None
    )

    if set(manifest) != lockbox_contract.MERGED_MANIFEST_FIELDS:
        _violation(violations, "merged manifest schema violation")
    if manifest.get("schema") != lockbox_contract.MERGED_MANIFEST_SCHEMA:
        _violation(violations, "merged manifest schema identity violation")
    if manifest.get("status") != "COMPLETE":
        _violation(violations, "lockbox manifest is not COMPLETE")
    sample_size = manifest.get("sample_size")
    if power_sample_size is None or sample_size != power_sample_size:
        _violation(violations, "manifest sample size does not match authentic power decision")
    if manifest.get("source_dirty") is not False:
        _violation(violations, "dirty source SHA or row")
    for field, length in (
        ("protocol_digest", 64), ("spec_digest", 64), ("config_digest", 64),
        ("generator_digest", 64), ("generator_manifest_sha256", 64),
        ("selected_protocol_sha256", 64), ("source_commit", 40),
        ("selection_source_commit", 40), ("power_plan_sha256", 64),
        ("power_source_commit", 40),
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
    selected_actual = top_level_hashes.get("selected_protocol_sha256")
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

    actual_power_sha256 = top_level_hashes.get("power_plan_sha256")
    if (
        not _digest(actual_power_sha256)
        or actual_power_sha256 != manifest.get("power_plan_sha256")
    ):
        _violation(violations, "actual power hash does not match merged power hash")
    if power_valid and validated_power.get("source_commit") != manifest.get("power_source_commit"):
        _violation(violations, "power source provenance mismatch")
    power_selected = validated_power.get("selected_protocol")
    if power_valid and (not isinstance(power_selected, Mapping) or (
        power_selected.get("sha256") != selected_actual
        or power_selected.get("source_commit")
        != validated_selection.get("source_commit")
    )):
        _violation(violations, "power selected protocol binding mismatch")
    power_digests = validated_power.get("digests")
    expected_power_digests = {
        "study_protocol_sha256": manifest.get("protocol_digest"),
        "specification_sha256": manifest.get("spec_digest"),
        "configuration_sha256": manifest.get("config_digest"),
        "generator_sha256": manifest.get("generator_digest"),
        "generator_manifest_sha256": manifest.get("generator_manifest_sha256"),
    }
    if power_valid and (not isinstance(power_digests, Mapping) or any(
        power_digests.get(field) != digest
        for field, digest in expected_power_digests.items()
    )):
        _violation(violations, "power frozen digest provenance mismatch")
    try:
        selected_artifacts, selected_folds = lockbox_contract._selection_power_bindings(
            validated_selection
        )
    except (TypeError, ValueError) as exc:
        selected_artifacts, selected_folds = [], []
        _violation(violations, f"selection power binding schema violation: {exc}")
    proof = validated_power.get("held_out_proof")
    if power_valid and (
        not isinstance(proof, Mapping)
        or proof.get("selected_candidate")
        != validated_selection.get("selected_candidate")
        or _canonical_json(proof.get("folds")) != _canonical_json(selected_folds)
        or _canonical_json(validated_power.get("development_artifacts"))
        != _canonical_json(selected_artifacts)
    ):
        _violation(violations, "power held-out selection provenance mismatch")
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
        artifact_hashes = per_shard_hashes.get(filename)
        if filename not in rows or not isinstance(artifact_hashes, Mapping):
            _violation(violations, "absent raw shard")
            artifact_hashes = {}
        elif item.get("raw_sha256") != artifact_hashes.get("raw_sha256"):
            _violation(violations, "raw shard hash mismatch")
        for hash_field, digest_field, label in (
            ("manifest_sha256", "manifest_sha256", "shard manifest hash mismatch"),
            ("sha256_sha256", "sha256_sha256", "SHA-256 sidecar hash mismatch"),
        ):
            actual_digest = artifact_hashes.get(hash_field)
            if not _digest(actual_digest):
                _violation(violations, f"absent {label.removesuffix(' hash mismatch')}")
            elif item.get(digest_field) != actual_digest:
                _violation(violations, label)
        family, start, stop = item.get("family"), item.get("start"), item.get("stop")
        if (
            family not in LOCKBOX_FAMILIES
            or isinstance(start, bool) or not isinstance(start, int)
            or isinstance(stop, bool) or not isinstance(stop, int)
            or power_sample_size is None
            or not 0 <= start < stop <= power_sample_size
        ):
            _violation(violations, "raw shard has unregistered family/range")
        else:
            ranges[str(family)].append((start, stop))
            if filename != lockbox_contract.registered_raw_filename(
                family, start, stop, sample_size=power_sample_size
            ):
                _violation(violations, "exact registered raw filename mismatch")
            try:
                lockbox_contract.validate_shard_local_rows(
                    rows.get(filename), family=family, start=start, stop=stop,
                    sample_size=power_sample_size,
                )
            except (TypeError, ValueError):
                _violation(violations, "raw shard does not contain the exact local key/arm grid")
    if set(rows) != seen_files:
        _violation(violations, "raw row mapping does not exactly match merged raw shards")
    for family, intervals in ranges.items():
        cursor = 0
        for start, stop in sorted(intervals):
            if start != cursor:
                _violation(violations, f"raw shard ranges are missing or overlap for {family}")
                break
            cursor = stop
        if power_sample_size is None or cursor != power_sample_size:
            _violation(violations, f"raw shard ranges are incomplete for {family}")

    try:
        expected_environment = lockbox_contract.validate_environment_compatibility(
            manifest.get("environment_compatibility")
        )
    except (TypeError, ValueError) as exc:
        expected_environment = None
        _violation(violations, f"manifest environment compatibility violation: {exc}")
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
        try:
            row_environment = lockbox_contract.environment_compatibility_projection(
                row.get("environment")
            )
        except (TypeError, ValueError):
            row_environment = None
        if expected_environment is None or row_environment != expected_environment:
            _violation(violations, "wrong environment compatibility")
        parents = row.get("parent_artifacts")
        expected_parents = {
            "spec": manifest.get("spec_digest"),
            "config": manifest.get("config_digest"),
            "generator": manifest.get("generator_digest"),
            "generator_manifest": manifest.get("generator_manifest_sha256"),
            "selected_protocol": manifest.get("selected_protocol_sha256"),
            "power_plan": manifest.get("power_plan_sha256"),
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
        for key in range(power_sample_size or 0)
        for arm in ARMS
    }
    if all_keys != expected_key_arms:
        _violation(violations, "missing campaign key or unregistered campaign key")

    recomputed = recomputed_analysis
    if recomputed is None:
        if power_sample_size is not None:
            try:
                recomputed = _recompute_registered_analysis(
                    manifest, valid_rows, sample_size=power_sample_size
                )
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
                finite_bound = _finite_number(bound)
                finite_margin = _finite_number(margin)
                valid = finite_bound is not None and finite_margin is not None
                passed = valid and (
                    finite_bound < finite_margin
                    if direction == "upper"
                    else finite_bound > finite_margin
                )
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
    power_plan = kwargs.get("power_plan")
    rows = kwargs.get("rows")
    hashes = kwargs.get("actual_hashes")
    analysis_mapping = analysis if isinstance(analysis, Mapping) else {}
    manifest_mapping = manifest if isinstance(manifest, Mapping) else {}
    power_mapping = power_plan if isinstance(power_plan, Mapping) else {}
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
    decision = power_mapping.get("decision")
    selected_sample_size = (
        decision.get("selected_sample_size") if isinstance(decision, Mapping) else None
    )
    return {
        "schema": "boec-spade-lockbox-release-v2",
        "checks": {
            "all_registered_checks_pass": not violations,
            "analysis_verdict": analysis_mapping.get("overall_verdict"),
        },
        "hashes": dict(hash_mapping),
        "row_counts": row_counts,
        "manifest_sample_size": manifest_mapping.get("sample_size"),
        "power_status": power_mapping.get("status"),
        "selected_sample_size": selected_sample_size,
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
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ValueError(f"immutable release target already exists: {path}") from exc
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--power", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument(
        "--out", default=ROOT / "results" / "spade-lockbox-release.json", type=Path
    )
    args = parser.parse_args(argv)
    loaded = load_release_inputs(
        manifest_path=args.manifest,
        selection_path=args.selection,
        power_path=args.power,
        analysis_path=args.analysis,
    )
    report = build_release_report(**loaded)
    write_release_report(args.out, report)
    print(_canonical_json(report))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
