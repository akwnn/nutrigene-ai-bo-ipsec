#!/usr/bin/env python3
"""Plan and publish the frozen development-based SPADE lockbox sample size."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec.spade import SpadeConfig  # noqa: E402
from boec.spade_power import (  # noqa: E402
    DEVELOPMENT_FAMILIES,
    POWER_PLAN_SCHEMA,
    plan_lockbox_sample_size,
    validate_power_plan_payload,
)
from scripts import run_spade_development as development  # noqa: E402
from scripts import select_spade_protocol as selector  # noqa: E402


_REGISTERED_SELECTION = Path("results/spade-selected-protocol.json")
_REGISTERED_ANALYSIS = Path("results/spade-development-analysis.json")
_REGISTERED_OUTPUT = Path("results/spade-lockbox-power.json")
_FROZEN_POST_DEVELOPMENT_DEPENDENCIES = (
    Path("scripts/plan_spade_lockbox_power.py"),
    Path("scripts/run_spade_development.py"),
    Path("scripts/select_spade_protocol.py"),
    Path("src/boec/seedbook.py"),
    Path("src/boec/spade.py"),
    Path("src/boec/spade_power.py"),
    Path("src/boec/spade_study.py"),
)
_SELECTION_FIELDS = frozenset(
    {
        "schema",
        "status",
        "selected_candidate",
        "source_commit",
        "study_protocol_digest",
        "spec_digest",
        "config_digest",
        "generator_digest",
        "generator_manifest_sha256",
        "development_artifacts",
        "analysis_file",
        "analysis_sha256",
        "selection_trace",
        "lofo_folds",
        "selection_trace_digest",
        "selected_canonical_config",
        "selected_canonical_config_json",
        "selected_template_protocol_digest",
        "campaign_root_seed_binding",
    }
)
_FOLD_FIELDS = frozenset(
    {
        "held_out_family",
        "training_families",
        "status",
        "selected_candidate",
        "training_selection_trace",
        "held_out_metrics",
        "rationale",
    }
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_bytes(value: object) -> bytes:
    return (_canonical_json(value) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object, name: str, *, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            f"{name} must be exactly {length} lowercase ASCII hexadecimal characters"
        )
    return value


def _exact_mapping(
    value: object, fields: set[str] | frozenset[str], name: str
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise ValueError(f"{name} fields must be exactly {sorted(fields)}")
    return value


def _parse_canonical_json(data: bytes, name: str) -> dict[str, object]:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    try:
        expected = _canonical_bytes(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not finite canonical JSON") from exc
    if data != expected:
        raise ValueError(f"{name} bytes are not the exact canonical serialization")
    return payload


def registered_metadata(repo_root: Path = ROOT) -> dict[str, object]:
    """Return the development runner's fully validated frozen identities."""
    return development.registered_metadata(repo_root)


def git_state(repo_root: Path = ROOT) -> tuple[str, bool]:
    return development.git_state(repo_root)


def _lexical_repo_relative(repo_root: Path, path: str | Path) -> tuple[Path, Path]:
    """Return an unfollowed lexical repository path and reject traversal."""
    root = Path(os.path.abspath(repo_root))
    supplied = Path(path)
    if ".." in supplied.parts:
        raise ValueError(f"repository path contains traversal: {supplied}")
    candidate = supplied if supplied.is_absolute() else root / supplied
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact lies outside the repository: {supplied}") from exc
    if not relative.parts or candidate != root / relative:
        raise ValueError(f"artifact path is not lexically canonical: {supplied}")
    return root / relative, relative


def _exact_registered_path(
    repo_root: Path, supplied: str | Path, expected_relative: Path, name: str
) -> Path:
    candidate, relative = _lexical_repo_relative(repo_root, supplied)
    if relative != expected_relative:
        raise ValueError(f"{name} must be the exact registered path {expected_relative}")
    return candidate


def _reject_symlink_components(repo_root: Path, relative: Path) -> os.stat_result:
    root = Path(os.path.abspath(repo_root))
    try:
        root_status = os.lstat(root)
    except OSError as exc:
        raise ValueError(f"repository root is unavailable: {root}") from exc
    if stat.S_ISLNK(root_status.st_mode):
        raise ValueError("repository root must not be a symlink")
    current = root
    final_status = root_status
    for index, component in enumerate(relative.parts):
        current = current / component
        try:
            final_status = os.lstat(current)
        except OSError as exc:
            raise ValueError(f"required committed artifact is missing: {relative}") from exc
        if stat.S_ISLNK(final_status.st_mode):
            raise ValueError(f"symlink paths are forbidden: {relative}")
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(final_status.st_mode):
            raise ValueError(f"artifact parent is not a directory: {relative}")
    return final_status


def _git_regular_blob(
    repo_root: Path,
    revision: str,
    relative: Path,
    *,
    expected_mode: str = "100644",
) -> bytes:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-z", revision, "--", relative.as_posix()],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"cannot inspect committed tree entry {revision}:{relative}"
        ) from exc
    entries = [entry for entry in result.stdout.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ValueError(f"artifact is not an exact committed tree entry: {relative}")
    header, encoded_name = entries[0].split(b"\t", 1)
    parts = header.split()
    if len(parts) != 3:
        raise ValueError(f"committed tree entry is malformed: {relative}")
    mode, kind, object_id = (part.decode("ascii") for part in parts)
    if encoded_name.decode("utf-8") != relative.as_posix():
        raise ValueError(f"committed tree path identity drifted: {relative}")
    if mode == "120000":
        raise ValueError(f"committed symlink entries are forbidden: {relative}")
    if kind != "blob" or mode != expected_mode:
        raise ValueError(
            f"committed artifact must be a regular {expected_mode} blob, "
            f"got {mode} {kind}: {relative}"
        )
    try:
        return subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"cannot read committed blob {revision}:{relative}") from exc


def _committed_regular_file_bytes(
    repo_root: Path,
    path: str | Path,
    *,
    revision: str = "HEAD",
    expected_mode: str = "100644",
) -> bytes:
    """Read only a lexical, regular, exact-mode file matching a committed blob."""
    source, relative = _lexical_repo_relative(repo_root, path)
    committed = _git_regular_blob(
        repo_root, revision, relative, expected_mode=expected_mode
    )
    status = _reject_symlink_components(repo_root, relative)
    if not stat.S_ISREG(status.st_mode):
        raise ValueError(f"artifact is not a regular file: {relative}")
    actual = source.read_bytes()
    if actual != committed:
        raise ValueError(
            f"artifact bytes differ from committed {revision} blob: {relative}"
        )
    return committed


def _committed_file_bytes(repo_root: Path, path: Path) -> bytes:
    """Compatibility wrapper for exact regular data artifacts at HEAD."""
    return _committed_regular_file_bytes(repo_root, path)


def _validate_frozen_dependency_blobs(repo_root: Path, selected_source: str) -> None:
    """Prove post-development interpretation code is byte-identical to selection."""
    _digest(selected_source, "selected source commit", length=40)
    for relative in _FROZEN_POST_DEVELOPMENT_DEPENDENCIES:
        path = Path(os.path.abspath(repo_root)) / relative
        current = _committed_regular_file_bytes(repo_root, path)
        selected = _git_regular_blob(repo_root, selected_source, relative)
        if current != selected:
            raise ValueError(
                f"post-development dependency drifted from selected source: {relative}"
            )


def _is_ancestor(repo_root: Path, older: str, newer: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=repo_root,
            capture_output=True,
        ).returncode
        == 0
    )


def _validate_selection(
    selected: object, *, metadata: Mapping[str, object], current_commit: str
) -> dict[str, object]:
    item = _exact_mapping(selected, _SELECTION_FIELDS, "selected protocol")
    if item["schema"] != selector.SELECTION_SCHEMA:
        raise ValueError("selected protocol schema drifted")
    if item["status"] != "SELECTED":
        raise ValueError("power planning requires a SELECTED protocol")
    candidate = item["selected_candidate"]
    if candidate not in development.CANDIDATE_ARM_IDS:
        raise ValueError("selected protocol candidate is not registered")
    source_commit = _digest(item["source_commit"], "selection source commit", length=40)
    _digest(current_commit, "current source commit", length=40)
    expected_identities = {
        "study_protocol_digest": metadata["study_protocol_digest"],
        "spec_digest": metadata["spec_digest"],
        "config_digest": metadata["config_digest"],
        "generator_digest": metadata["generator_digest"],
        "generator_manifest_sha256": metadata["generator_manifest_sha256"],
    }
    for field, expected in expected_identities.items():
        if item[field] != expected:
            raise ValueError(f"selected protocol {field.replace('_', ' ')} mismatch")
        _digest(item[field], f"selected protocol {field}")
    if item["analysis_file"] != _REGISTERED_ANALYSIS.name:
        raise ValueError("selected protocol analysis filename drifted")
    _digest(item["analysis_sha256"], "selected protocol analysis SHA-256")
    _digest(item["selection_trace_digest"], "selected trace SHA-256")
    artifacts = item["development_artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("selected protocol must bind exactly five development artifacts")
    trace = item["selection_trace"]
    if not isinstance(trace, Mapping):
        raise ValueError("selected protocol selection trace must be a mapping")
    trace_digest = _sha256_bytes(_canonical_json(trace).encode("utf-8"))
    if trace_digest != item["selection_trace_digest"]:
        raise ValueError("selected protocol selection trace digest mismatch")
    if (
        trace.get("rule") != "unanimous_lofo_consensus"
        or trace.get("unanimous") is not True
        or trace.get("selected_candidate") != candidate
    ):
        raise ValueError("selected protocol does not prove unanimous LOFO selection")
    folds = item["lofo_folds"]
    if not isinstance(folds, list) or len(folds) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("selected protocol must contain exactly five LOFO folds")
    for family, fold in zip(DEVELOPMENT_FAMILIES, folds, strict=True):
        fold_item = _exact_mapping(fold, _FOLD_FIELDS, f"selection fold {family}")
        expected_training = [other for other in DEVELOPMENT_FAMILIES if other != family]
        if (
            fold_item["held_out_family"] != family
            or fold_item["training_families"] != expected_training
            or fold_item["status"] != "SELECTED"
            or fold_item["selected_candidate"] != candidate
        ):
            raise ValueError("selection fold identity or selected candidate drifted")
    opening, policy = development.candidate_spec(str(candidate))
    template = SpadeConfig(opening=opening, policy=policy, root_seed=0)
    if (
        item["selected_canonical_config_json"] != template.canonical_json
        or item["selected_canonical_config"] != json.loads(template.canonical_json)
        or item["selected_template_protocol_digest"] != template.protocol_digest
    ):
        raise ValueError("selected protocol canonical configuration drifted")
    if item["campaign_root_seed_binding"] != "sha256_labelled_derived_per_campaign":
        raise ValueError("selected protocol campaign seed binding drifted")
    result = json.loads(_canonical_json(item))
    result["source_commit"] = source_commit
    return result


def _score(row: Mapping[str, object], field: str, identity: str) -> float:
    scores = row.get("scores")
    if not isinstance(scores, Mapping):
        raise ValueError(f"{identity} scores must be a mapping")
    value = scores.get(field)
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{identity} {field} score must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{identity} {field} score must be finite")
    return result


def _extract_held_out_differences(
    rows: Sequence[Mapping[str, object]],
    *,
    selected_candidate: str,
    lofo_folds: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, list[float]]]:
    """Extract registered paired vectors only after proving each family was held out."""
    if len(lofo_folds) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("held-out extraction requires exactly five LOFO folds")
    for family, fold in zip(DEVELOPMENT_FAMILIES, lofo_folds, strict=True):
        if (
            fold.get("held_out_family") != family
            or fold.get("training_families")
            != [other for other in DEVELOPMENT_FAMILIES if other != family]
            or fold.get("status") != "SELECTED"
            or fold.get("selected_candidate") != selected_candidate
        ):
            raise ValueError("held-out fold does not select the unanimous final candidate")

    target_arms = {selected_candidate, "sobol48", "qlognei48"}
    indexed: dict[tuple[str, tuple[int, int], str], Mapping[str, object]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TypeError(f"development row {index} must be a mapping")
        family = row.get("family")
        if family not in DEVELOPMENT_FAMILIES:
            raise ValueError(f"development row {index} has an unregistered family")
        arm_id = selector.development_arm_id(row)
        if arm_id not in target_arms:
            continue
        key = selector._key(row)
        identity = (str(family), key, arm_id)
        if identity in indexed:
            raise ValueError(f"duplicate held-out development pair {identity}")
        indexed[identity] = row

    output: dict[str, dict[str, list[float]]] = {}
    for family in DEVELOPMENT_FAMILIES:
        map_differences: list[float] = []
        regret_differences: list[float] = []
        for key_index in range(development.CAMPAIGNS_PER_FAMILY):
            key = development.development_campaign_key(family, key_index)
            try:
                selected = indexed[(family, key, selected_candidate)]
                sobol = indexed[(family, key, "sobol48")]
                qlognei = indexed[(family, key, "qlognei48")]
            except KeyError as exc:
                raise ValueError(
                    f"held-out family {family} lacks all 50 matched comparator pairs"
                ) from exc
            map_differences.append(
                _score(selected, "map_loss", f"{family}/{key}/SPADE")
                - _score(sobol, "map_loss", f"{family}/{key}/Sobol48")
            )
            regret_differences.append(
                _score(selected, "regret_rule_p", f"{family}/{key}/SPADE")
                - _score(qlognei, "regret_rule_p", f"{family}/{key}/qLogNEI48")
            )
        if len(map_differences) != 50 or len(regret_differences) != 50:
            raise RuntimeError("held-out extraction did not produce exactly 50 pairs")
        output[family] = {"map": map_differences, "regret": regret_differences}
    return output


def _ordered_power_artifacts(
    artifacts: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    by_family: dict[str, Mapping[str, object]] = {}
    for artifact in artifacts:
        family = artifact.get("family")
        if family in by_family or family not in DEVELOPMENT_FAMILIES:
            raise ValueError("development artifact family identity is duplicate or unknown")
        by_family[str(family)] = artifact
    if set(by_family) != set(DEVELOPMENT_FAMILIES):
        raise ValueError("development artifacts do not cover all five families")
    output = []
    for family in DEVELOPMENT_FAMILIES:
        artifact = by_family[family]
        output.append(
            {
                "family": family,
                "raw_file": artifact["raw_file"],
                "raw_sha256": artifact["raw_sha256"],
                "manifest_file": artifact["manifest_file"],
                "manifest_sha256": artifact["manifest_sha256"],
            }
        )
    return output


def _preflight_development_inputs(
    repo_root: Path,
    manifest_paths: Sequence[str | Path],
    *,
    metadata: Mapping[str, object],
    selected_source: str,
) -> tuple[Path, ...]:
    """Validate every registered development path and byte before the loader opens it."""
    if len(manifest_paths) != len(DEVELOPMENT_FAMILIES):
        raise ValueError("power planning requires exactly five development manifests")
    expected_relatives = {
        family: Path(
            f"results/spade-development-{family}-000-050.jsonl.gz.manifest.json"
        )
        for family in DEVELOPMENT_FAMILIES
    }
    expected_by_name = {
        relative.name: (family, relative)
        for family, relative in expected_relatives.items()
    }
    supplied: dict[str, Path] = {}
    for value in manifest_paths:
        name = Path(value).name
        if name not in expected_by_name or name in supplied:
            raise ValueError("development manifest path is not a unique registered identity")
        _, expected_relative = expected_by_name[name]
        supplied[name] = _exact_registered_path(
            repo_root, value, expected_relative, "development manifest"
        )
    if set(supplied) != set(expected_by_name):
        raise ValueError("development manifest paths do not cover the registered families")

    records: dict[str, tuple[dict[str, object], Path, Path, Path, Path]] = {}
    for family in DEVELOPMENT_FAMILIES:
        manifest_path = supplied[expected_relatives[family].name]
        manifest_bytes = _committed_file_bytes(repo_root, manifest_path)
        manifest = development.validate_shard_manifest(
            _parse_canonical_json(manifest_bytes, f"development manifest {family}")
        )
        raw_name = f"spade-development-{family}-000-050.jsonl.gz"
        resume_name = f"{raw_name}.resume.json"
        expected_identity = {
            "family": family,
            "start": 0,
            "stop": development.CAMPAIGNS_PER_FAMILY,
            "raw_file": raw_name,
            "resume_file": resume_name,
            "study_protocol_digest": metadata["study_protocol_digest"],
            "spec_digest": metadata["spec_digest"],
            "config_digest": metadata["config_digest"],
            "generator_digest": metadata["generator_digest"],
            "generator_manifest_sha256": metadata["generator_manifest_sha256"],
            "source_commit": selected_source,
            "source_dirty": False,
        }
        for field, expected in expected_identity.items():
            if manifest[field] != expected:
                raise ValueError(
                    f"development manifest {family} registered {field} identity mismatch"
                )
        raw_path = _exact_registered_path(
            repo_root,
            Path("results") / str(manifest["raw_file"]),
            Path("results") / raw_name,
            "development raw shard",
        )
        resume_path = _exact_registered_path(
            repo_root,
            Path("results") / str(manifest["resume_file"]),
            Path("results") / resume_name,
            "development resume checkpoint",
        )
        sidecar_path = _exact_registered_path(
            repo_root,
            Path("results") / f"{manifest['raw_file']}.sha256",
            Path("results") / f"{raw_name}.sha256",
            "development SHA-256 sidecar",
        )
        records[family] = (
            manifest,
            manifest_path,
            raw_path,
            resume_path,
            sidecar_path,
        )

    for family in DEVELOPMENT_FAMILIES:
        manifest, _, raw_path, resume_path, sidecar_path = records[family]
        raw_bytes = _committed_file_bytes(repo_root, raw_path)
        resume_bytes = _committed_file_bytes(repo_root, resume_path)
        sidecar_bytes = _committed_file_bytes(repo_root, sidecar_path)
        if _sha256_bytes(raw_bytes) != manifest["raw_sha256"]:
            raise ValueError("committed development raw SHA-256 mismatch")
        if _sha256_bytes(resume_bytes) != manifest["resume_sha256"]:
            raise ValueError("committed development resume SHA-256 mismatch")
        expected_sidecar = (
            f"{manifest['raw_sha256']}  {manifest['raw_file']}\n".encode("ascii")
        )
        if sidecar_bytes != expected_sidecar:
            raise ValueError("committed development SHA-256 sidecar mismatch")
    return tuple(records[family][1] for family in DEVELOPMENT_FAMILIES)


def power_payload_from_shards(
    manifest_paths: Sequence[str | Path],
    *,
    selection_path: str | Path,
    repo_root: Path = ROOT,
) -> dict[str, object]:
    """Build the exact power envelope from committed selection and held-out rows."""
    root = Path(os.path.abspath(repo_root))
    selection = _exact_registered_path(
        root, selection_path, _REGISTERED_SELECTION, "selection"
    )
    current_commit, dirty = git_state(root)
    if dirty:
        raise ValueError("power planning refuses a dirty source tree")
    metadata = registered_metadata(root)
    if metadata.get("source_dirty") is not False or metadata.get("source_commit") != current_commit:
        raise ValueError("registered metadata does not describe the current clean source commit")

    selection_bytes = _committed_file_bytes(root, selection)
    selected = _validate_selection(
        _parse_canonical_json(selection_bytes, "selected protocol"),
        metadata=metadata,
        current_commit=current_commit,
    )
    selected_source = str(selected["source_commit"])
    if not _is_ancestor(root, selected_source, current_commit):
        raise ValueError("selected development source commit is not an ancestor of HEAD")
    _validate_frozen_dependency_blobs(root, selected_source)

    analysis_path = root / _REGISTERED_ANALYSIS
    analysis_bytes = _committed_file_bytes(root, analysis_path)
    if _sha256_bytes(analysis_bytes) != selected["analysis_sha256"]:
        raise ValueError("committed development analysis SHA-256 mismatch")
    stored_analysis = _parse_canonical_json(analysis_bytes, "development analysis")

    registered_manifests = _preflight_development_inputs(
        root,
        manifest_paths,
        metadata=metadata,
        selected_source=selected_source,
    )
    rows, artifacts = selector._load_complete_shards(
        registered_manifests,
        metadata=metadata,
        source_commit=selected_source,
    )
    if _canonical_json(artifacts) != _canonical_json(selected["development_artifacts"]):
        raise ValueError("selected development artifact hashes disagree with loaded bytes")
    recomputed_analysis = selector.analyse_development(
        rows,
        protocol_digest=str(metadata["study_protocol_digest"]),
    )
    if _canonical_json(stored_analysis) != _canonical_json(recomputed_analysis):
        raise ValueError("committed development analysis disagrees with recomputed analysis")
    if _canonical_bytes(recomputed_analysis) != analysis_bytes:
        raise ValueError("development analysis bytes disagree with canonical recomputation")
    if (
        recomputed_analysis.get("status") != "SELECTED"
        or recomputed_analysis.get("selected_candidate") != selected["selected_candidate"]
        or _canonical_json(recomputed_analysis.get("selection_trace"))
        != _canonical_json(selected["selection_trace"])
        or _canonical_json(recomputed_analysis.get("lofo_folds"))
        != _canonical_json(selected["lofo_folds"])
    ):
        raise ValueError("selected protocol and recomputed selection analysis mismatch")

    held_out = _extract_held_out_differences(
        rows,
        selected_candidate=str(selected["selected_candidate"]),
        lofo_folds=selected["lofo_folds"],
    )
    decision = plan_lockbox_sample_size(held_out)
    proof_folds = [
        {
            "held_out_family": fold["held_out_family"],
            "training_families": fold["training_families"],
            "selected_candidate": fold["selected_candidate"],
        }
        for fold in selected["lofo_folds"]
    ]
    payload = {
        "schema": POWER_PLAN_SCHEMA,
        "status": decision.status,
        "source_commit": current_commit,
        "source_dirty": False,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "digests": {
            "study_protocol_sha256": metadata["study_protocol_digest"],
            "specification_sha256": metadata["spec_digest"],
            "configuration_sha256": metadata["config_digest"],
            "generator_sha256": metadata["generator_digest"],
            "generator_manifest_sha256": metadata["generator_manifest_sha256"],
            "power_design_sha256": metadata["power_design_digest"],
            "power_engine_sha256": metadata["power_engine_digest"],
            "power_planner_sha256": metadata["power_planner_digest"],
        },
        "selected_protocol": {
            "file": _REGISTERED_SELECTION.name,
            "sha256": _sha256_bytes(selection_bytes),
            "source_commit": selected_source,
        },
        "development_artifacts": _ordered_power_artifacts(artifacts),
        "held_out_proof": {
            "unanimous": True,
            "selected_candidate": selected["selected_candidate"],
            "folds": proof_folds,
        },
        "held_out_differences": held_out,
        "decision": decision.as_dict(),
        "decision_sha256": decision.decision_sha256,
    }
    return validate_power_plan_payload(payload)


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    """Install canonical JSON atomically without any overwrite window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)
    return _sha256_bytes(data)


def write_power_plan(
    manifest_paths: Sequence[str | Path],
    *,
    selection_path: str | Path,
    output_path: str | Path,
    repo_root: Path = ROOT,
) -> dict[str, object]:
    root = Path(os.path.abspath(repo_root))
    destination = _exact_registered_path(
        root, output_path, _REGISTERED_OUTPUT, "power output"
    )
    parent_status = _reject_symlink_components(root, _REGISTERED_OUTPUT.parent)
    if not stat.S_ISDIR(parent_status.st_mode):
        raise ValueError("registered results path is not a directory")
    if os.path.lexists(destination):
        raise ValueError("power plan is write-once and already exists")
    payload = power_payload_from_shards(
        manifest_paths,
        selection_path=selection_path,
        repo_root=root,
    )
    _write_once_json(destination, payload)
    installed_status = _reject_symlink_components(root, _REGISTERED_OUTPUT)
    if not stat.S_ISREG(installed_status.st_mode):
        raise RuntimeError("installed power plan is not a regular file")
    if destination.read_bytes() != _canonical_bytes(payload):
        raise RuntimeError("installed power plan bytes failed canonical verification")
    return payload


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / _REGISTERED_SELECTION,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / _REGISTERED_OUTPUT,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = write_power_plan(
        args.manifest,
        selection_path=args.selection,
        output_path=args.out,
        repo_root=ROOT,
    )
    print(_canonical_json(payload))
    return 0 if payload["status"] == "POWERED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
