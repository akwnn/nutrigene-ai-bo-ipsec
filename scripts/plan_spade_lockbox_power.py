#!/usr/bin/env python3
"""Plan and publish the frozen development-based SPADE lockbox sample size."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
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


def _repository_relative(repo_root: Path, path: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact lies outside the repository: {path}") from exc


def _committed_file_bytes(repo_root: Path, path: Path) -> bytes:
    """Read a file only when its working bytes equal the blob committed at HEAD."""
    relative = _repository_relative(repo_root, path)
    if not path.is_file():
        raise ValueError(f"required committed artifact is missing: {relative}")
    try:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative.as_posix()}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"artifact is not committed at HEAD: {relative}") from exc
    actual = path.read_bytes()
    if actual != committed:
        raise ValueError(f"artifact bytes differ from the committed HEAD blob: {relative}")
    return committed


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


def _require_committed_development_inputs(
    repo_root: Path,
    manifest_paths: Sequence[str | Path],
    artifacts: Sequence[Mapping[str, object]],
) -> None:
    """Prove every byte used by the selector is the byte committed at HEAD."""
    results_root = (repo_root / "results").resolve()
    supplied: dict[str, Path] = {}
    for value in manifest_paths:
        path = Path(value)
        if not path.is_absolute():
            path = repo_root / path
        if path.parent.resolve() != results_root or path.name in supplied:
            raise ValueError(
                "development manifests must be unique files in the registered results directory"
            )
        supplied[path.name] = path
    expected_names = {str(artifact["manifest_file"]) for artifact in artifacts}
    if set(supplied) != expected_names:
        raise ValueError("supplied development manifest files disagree with selection")

    for artifact in artifacts:
        manifest_path = supplied[str(artifact["manifest_file"])]
        raw_path = results_root / str(artifact["raw_file"])
        resume_path = results_root / str(artifact["resume_file"])
        sidecar_path = Path(f"{raw_path}.sha256")
        manifest_bytes = _committed_file_bytes(repo_root, manifest_path)
        raw_bytes = _committed_file_bytes(repo_root, raw_path)
        resume_bytes = _committed_file_bytes(repo_root, resume_path)
        sidecar_bytes = _committed_file_bytes(repo_root, sidecar_path)
        if _sha256_bytes(manifest_bytes) != artifact["manifest_sha256"]:
            raise ValueError("committed development manifest SHA-256 mismatch")
        if _sha256_bytes(raw_bytes) != artifact["raw_sha256"]:
            raise ValueError("committed development raw SHA-256 mismatch")
        if _sha256_bytes(resume_bytes) != artifact["resume_sha256"]:
            raise ValueError("committed development resume SHA-256 mismatch")
        expected_sidecar = (
            f"{artifact['raw_sha256']}  {artifact['raw_file']}\n".encode("ascii")
        )
        if sidecar_bytes != expected_sidecar:
            raise ValueError("committed development SHA-256 sidecar mismatch")


def power_payload_from_shards(
    manifest_paths: Sequence[str | Path],
    *,
    selection_path: str | Path,
    repo_root: Path = ROOT,
) -> dict[str, object]:
    """Build the exact power envelope from committed selection and held-out rows."""
    root = Path(repo_root)
    selection = Path(selection_path)
    expected_selection = root / _REGISTERED_SELECTION
    if selection.resolve() != expected_selection.resolve():
        raise ValueError(f"selection must be the exact registered path {expected_selection}")
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

    analysis_path = root / _REGISTERED_ANALYSIS
    analysis_bytes = _committed_file_bytes(root, analysis_path)
    if _sha256_bytes(analysis_bytes) != selected["analysis_sha256"]:
        raise ValueError("committed development analysis SHA-256 mismatch")
    stored_analysis = _parse_canonical_json(analysis_bytes, "development analysis")

    rows, artifacts = selector._load_complete_shards(
        manifest_paths,
        metadata=metadata,
        source_commit=selected_source,
    )
    if _canonical_json(artifacts) != _canonical_json(selected["development_artifacts"]):
        raise ValueError("selected development artifact hashes disagree with loaded bytes")
    _require_committed_development_inputs(root, manifest_paths, artifacts)
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
    root = Path(repo_root)
    destination = Path(output_path)
    expected = root / _REGISTERED_OUTPUT
    if destination.resolve() != expected.resolve():
        raise ValueError(f"power output must be the exact registered path {expected}")
    if destination.exists():
        raise ValueError("power plan is write-once and already exists")
    payload = power_payload_from_shards(
        manifest_paths,
        selection_path=selection_path,
        repo_root=root,
    )
    _write_once_json(destination, payload)
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
