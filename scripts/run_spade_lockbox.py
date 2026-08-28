#!/usr/bin/env python3
"""Guarded, resumable SPADE lockbox shard runner.

This module intentionally consumes only the committed selected configuration.  It never
loads development rows or development analyses, so campaign decisions cannot depend on
development outcome metrics.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec.lockbox_oracles import LOCKBOX_FAMILIES, make_lockbox_oracle  # noqa: E402
from boec.seedbook import IndexedGaussianNoise, derive_seed  # noqa: E402
from boec.spade import SpadeConfig, run_qlognei48, run_sobol48, run_spade  # noqa: E402
from boec.spade_power import DEVELOPMENT_FAMILIES, validate_power_plan_payload  # noqa: E402
from boec.spade_study import SealedOracleHarness, _validate_rows, build_study_row, collect_environment_provenance, controlled_tau, score_campaign, write_jsonl_gzip  # noqa: E402
from boec.torch_oracle import TorchEvaluator  # noqa: E402


LOCKBOX_ARMS = ("spade", "sobol48", "qlognei48")
STUDY_ROOT_SEED = 2_026_08_25
SIGMA_REL, SIGMA_ADD, GAMMA, ALPHA, Q_TAU = .10, .01, .95, .95, .75
MANIFEST_SCHEMA = "boec-spade-lockbox-shard-v2"
MERGED_MANIFEST_SCHEMA = "boec-spade-lockbox-manifest-v2"
RESUME_SCHEMA = "boec-spade-lockbox-resume-v2"
GENERATOR_FREEZE_SHA256 = "d9822e7017962ea667b6b42354e91603bdfb0a4e2b4fe046c0d403038a4cce0f"
GENERATOR_FREEZE_PARENT_COMMIT = "d1fab2c2099926945e399f741ccc79123a539066"
ENVIRONMENT_COMPATIBILITY_SCHEMA = "boec-spade-environment-compatibility-v1"
LOCKBOX_PROVENANCE_FIELDS = frozenset({
    "protocol_digest", "spec_digest", "config_digest", "generator_digest",
    "generator_manifest_sha256", "source_commit", "source_dirty",
    "selected_protocol_sha256", "selection_source_commit",
    "power_plan_sha256", "power_source_commit",
})
SHARD_MANIFEST_FIELDS = frozenset({
    "schema", "status", "family", "start", "stop", "sample_size", "expected_rows",
    "row_count", "complete", "raw_file", "raw_sha256",
    "environment_compatibility", "command_args",
}) | LOCKBOX_PROVENANCE_FIELDS
MERGED_MANIFEST_FIELDS = frozenset({
    "schema", "status", "sample_size", "raw_shards", "environment_compatibility",
}) | LOCKBOX_PROVENANCE_FIELDS
MERGED_RAW_SHARD_FIELDS = frozenset({
    "family", "start", "stop", "raw_file", "raw_sha256", "command_args",
    "manifest_file", "manifest_sha256", "sha256_file", "sha256_sha256",
})
SELECTED_PROTOCOL_FIELDS = frozenset({
    "schema", "status", "selected_candidate", "source_commit",
    "study_protocol_digest", "spec_digest", "config_digest", "generator_digest",
    "generator_manifest_sha256", "development_artifacts", "analysis_file",
    "analysis_sha256", "selection_trace", "lofo_folds", "selection_trace_digest",
    "selected_canonical_config", "selected_canonical_config_json",
    "selected_template_protocol_digest", "campaign_root_seed_binding",
})
_CONFIG_PATH = Path("configs/experiment/spade-joint.yaml")
_SPEC_PATH = Path("docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md")
_GENERATOR_PATH = Path("src/boec/lockbox_oracles.py")
_GENERATOR_MANIFEST = Path("results/spade-lockbox-generator-manifest.json")
_POWER_PATH = Path("results/spade-lockbox-power.json")
_POWER_DESIGN_PATH = Path("docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md")
_POWER_ENGINE_PATH = Path("src/boec/spade_power.py")
_POWER_PLANNER_PATH = Path("scripts/plan_spade_lockbox_power.py")
_EXECUTION_SOURCE_PATHS = {
    "actions_workflow_sha256": Path(".github/workflows/spade-distributed.yml"),
    "actions_matrix_sha256": Path("scripts/make_spade_actions_matrix.py"),
    "actions_worker_sha256": Path("scripts/run_spade_actions_worker.py"),
    "development_merger_sha256": Path("scripts/merge_spade_development_shards.py"),
    "requirements_sha256": Path("requirements.txt"),
}
_EXECUTION_PAYLOAD_SHA256 = (
    "5dae76d1495c009cf2ea0989142fe4563c2f2140d2dbe832249bdcc41fa4f80d"
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _canonical_bytes(value: object) -> bytes:
    return (_canonical_json(value) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_environment_compatibility(value: object) -> dict[str, object]:
    """Validate the science-affecting cross-host environment projection."""
    fields = {
        "schema", "python", "platform", "packages", "threads",
        "boec_distribution",
    }
    package_fields = {"numpy", "scipy", "torch", "gpytorch", "botorch"}
    thread_fields = {
        "torch", "torch_interop", "omp_num_threads", "mkl_num_threads",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("lockbox environment compatibility schema drift")
    result = dict(value)
    if result.get("schema") != ENVIRONMENT_COMPATIBILITY_SCHEMA:
        raise ValueError("lockbox environment compatibility schema drift")
    for field in ("python", "platform", "boec_distribution"):
        if not isinstance(result.get(field), str) or not result[field]:
            raise ValueError(f"lockbox environment compatibility {field} drift")
    packages = result.get("packages")
    if (
        not isinstance(packages, Mapping)
        or set(packages) != package_fields
        or any(not isinstance(version, str) or not version for version in packages.values())
    ):
        raise ValueError("lockbox environment compatibility package-version drift")
    threads = result.get("threads")
    if not isinstance(threads, Mapping) or set(threads) != thread_fields:
        raise ValueError("lockbox environment compatibility thread schema drift")
    for field in ("torch", "torch_interop"):
        thread_count = threads.get(field)
        if isinstance(thread_count, bool) or not isinstance(thread_count, int) or thread_count < 1:
            raise ValueError("lockbox environment compatibility thread-count drift")
    for field in ("omp_num_threads", "mkl_num_threads"):
        if threads.get(field) is not None and not isinstance(threads[field], str):
            raise ValueError("lockbox environment compatibility thread-setting drift")
    result["packages"] = dict(packages)
    result["threads"] = dict(threads)
    return result


def environment_compatibility_projection(environment: object) -> dict[str, object]:
    """Project full row provenance onto science-affecting cross-host fields.

    ``executable`` remains in every raw row for auditability, but is deliberately absent
    here because an absolute interpreter path is host-local rather than scientific state.
    """
    fields = {
        "python", "platform", "packages", "threads", "executable",
        "boec_distribution",
    }
    if not isinstance(environment, Mapping) or set(environment) != fields:
        raise ValueError("lockbox row environment schema drift")
    executable = environment.get("executable")
    if not isinstance(executable, str) or not executable:
        raise ValueError("lockbox row environment executable drift")
    return validate_environment_compatibility({
        "schema": ENVIRONMENT_COMPATIBILITY_SCHEMA,
        "python": environment.get("python"),
        "platform": environment.get("platform"),
        "packages": environment.get("packages"),
        "threads": environment.get("threads"),
        "boec_distribution": environment.get("boec_distribution"),
    })


def common_environment_compatibility(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    if not rows:
        raise ValueError("lockbox shard has no rows for environment compatibility")
    expected = environment_compatibility_projection(rows[0].get("environment"))
    if any(
        environment_compatibility_projection(row.get("environment")) != expected
        for row in rows[1:]
    ):
        raise ValueError("lockbox shard row environment compatibility drift")
    return expected


def _require_hex(value: object, name: str, *, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"selected protocol {name} must be a {length}-character digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"selected protocol {name} must be hexadecimal") from exc
    return value.lower()


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(payload) + "\n").encode()
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True); raise


def _write_once_json(path: Path, payload: Mapping[str, object]) -> None:
    """Publish final JSON without replacing an existing evidence artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(payload) + "\n").encode()
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        _install_new(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _row_chain_head(rows: Sequence[Mapping[str, object]]) -> str:
    head = "0" * 64
    for row in rows:
        digest = hashlib.sha256(_canonical_json(row).encode()).hexdigest()
        head = hashlib.sha256(f"{head}:{digest}".encode()).hexdigest()
    return head


def _registered_sample_size(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 350 <= value <= 2000:
        raise ValueError("lockbox sample size must lie in the registered 350..2000 range")
    return value


def _lockbox_publication_metadata(
    metadata: Mapping[str, object],
) -> dict[str, object]:
    """Project internal registered metadata onto the exact public shard contract."""
    missing = LOCKBOX_PROVENANCE_FIELDS - set(metadata)
    if missing:
        raise ValueError(f"lockbox publication metadata is missing {sorted(missing)}")
    return {field: metadata[field] for field in LOCKBOX_PROVENANCE_FIELDS}


def _validate_resume_rows(
    rows: Sequence[Mapping[str, object]], *, family: str, start: int, stop: int,
    sample_size: int,
) -> None:
    registered_raw_filename(family, start, stop, sample_size=sample_size)
    grouped: dict[int, set[str]] = {}
    for row in rows:
        if row.get("family") != family or row.get("campaign_seed") != 0:
            raise ValueError("resume row family or campaign key drift")
        key, arm = row.get("instance_seed"), row.get("arm")
        if isinstance(key, bool) or not isinstance(key, int) or not start <= key < stop or arm not in LOCKBOX_ARMS:
            raise ValueError("resume row is outside the requested registered key range")
        arms = grouped.setdefault(key, set())
        if arm in arms:
            raise ValueError("resume contains duplicate lockbox arm")
        arms.add(arm)
    if any(arms != set(LOCKBOX_ARMS) for arms in grouped.values()):
        raise ValueError("resume key is incomplete; it must contain all three matched arms")


def make_resume_payload(*, family: str, start: int, stop: int, sample_size: int, raw_file: str, rows: Sequence[Mapping[str, object]], metadata: Mapping[str, object]) -> dict[str, object]:
    _validate_resume_rows(rows, family=family, start=start, stop=stop, sample_size=sample_size)
    return {"schema": RESUME_SCHEMA, "family": family, "start": start, "stop": stop, "sample_size": sample_size, "raw_file": raw_file, "metadata": dict(metadata), "row_count": len(rows), "row_chain_head": _row_chain_head(rows), "rows": [dict(row) for row in rows]}


def validate_resume_payload(payload: Mapping[str, object], *, metadata: Mapping[str, object], family: str, start: int, stop: int, sample_size: int, raw_file: str) -> list[dict[str, object]]:
    expected = {"schema", "family", "start", "stop", "sample_size", "raw_file", "metadata", "row_count", "row_chain_head", "rows"}
    if not isinstance(payload, Mapping) or set(payload) != expected or payload.get("schema") != RESUME_SCHEMA:
        raise ValueError("resume checkpoint schema drift")
    if (payload.get("family"), payload.get("start"), payload.get("stop"), payload.get("sample_size"), payload.get("raw_file")) != (family, start, stop, sample_size, raw_file) or payload.get("metadata") != dict(metadata):
        raise ValueError("resume checkpoint identity drift")
    rows = payload.get("rows")
    if not isinstance(rows, list) or payload.get("row_count") != len(rows) or payload.get("row_chain_head") != _row_chain_head(rows):
        raise ValueError("resume checkpoint row hash-chain mismatch")
    _validate_resume_rows(rows, family=family, start=start, stop=stop, sample_size=sample_size)
    protocol = metadata.get("protocol_digest")
    if not isinstance(protocol, str):
        raise ValueError("resume metadata protocol schema drift")
    try:
        validated = _validate_rows(rows, protocol)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"resume rows violate boec-spade-study-row-v1: {exc}") from exc
    for row in validated:
        if row["source_dirty"] is not False or any(row[field] != metadata[field] for field in ("protocol_digest", "spec_digest", "config_digest", "source_commit")):
            raise ValueError("resume row provenance drift")
        parents = row["parent_artifacts"]
        if parents.get("generator") != metadata.get("generator_digest") or parents.get("generator_manifest") != metadata.get("generator_manifest_sha256") or parents.get("power_plan") != metadata.get("power_plan_sha256"):
            raise ValueError("resume row parent provenance drift")
    return [dict(row) for row in validated]


def _allowed_generated_path(path: str) -> bool:
    """Permit only exact registered generated names directly below results/."""
    normalized = path.replace("\\", "/")
    if not normalized.startswith("results/") or "/" in normalized.removeprefix("results/"):
        return False
    name = normalized.removeprefix("results/")
    import re
    return bool(re.fullmatch(r"spade-lockbox-(?:[a-z_]+-\d{4}-\d{4}\.jsonl\.gz(?:\.(?:sha256|manifest\.json|resume\.json))?|manifest\.json|analysis\.json|release\.json|power\.json)", name) or name == "spade-selected-protocol.json")


def git_state(repo_root: Path = ROOT) -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.splitlines()
    dirty = any(line and (line[:2] != "??" or not _allowed_generated_path(line[3:].split(" -> ")[-1])) for line in status)
    return commit, dirty


def registered_metadata(repo_root: Path = ROOT) -> dict[str, object]:
    config_path, spec_path, generator_path = (repo_root / _CONFIG_PATH, repo_root / _SPEC_PATH, repo_root / _GENERATOR_PATH)
    config = yaml.safe_load(config_path.read_text())
    protocol = config.get("protocol") if isinstance(config, Mapping) else None
    execution = config.get("execution") if isinstance(config, Mapping) else None
    digests = config.get("digests") if isinstance(config, Mapping) else None
    if (
        not isinstance(protocol, Mapping)
        or not isinstance(execution, Mapping)
        or not isinstance(digests, Mapping)
    ):
        raise ValueError("SPADE config is missing frozen protocol/execution digests")
    protocol_digest = hashlib.sha256(_canonical_json(protocol).encode()).hexdigest()
    if protocol_digest != digests.get("protocol_payload_sha256"):
        raise ValueError("configured study protocol digest mismatch")
    execution_digest = hashlib.sha256(_canonical_json(execution).encode()).hexdigest()
    if (
        execution_digest != _EXECUTION_PAYLOAD_SHA256
        or digests.get("execution_payload_sha256") != _EXECUTION_PAYLOAD_SHA256
    ):
        raise ValueError("configured execution payload digest mismatch")
    metadata = {
        "protocol_digest": protocol_digest,
        "spec_digest": _sha256(spec_path),
        "config_digest": _sha256(config_path),
        "generator_digest": _sha256(generator_path),
        "power_design_digest": _sha256(repo_root / _POWER_DESIGN_PATH),
        "power_engine_digest": _sha256(repo_root / _POWER_ENGINE_PATH),
        "power_planner_digest": _sha256(repo_root / _POWER_PLANNER_PATH),
    }
    expected_digests = {
        "spec_sha256": metadata["spec_digest"],
        "lockbox_oracles_source_sha256": metadata["generator_digest"],
        "power_design_sha256": metadata["power_design_digest"],
        "power_engine_sha256": metadata["power_engine_digest"],
        "power_planner_sha256": metadata["power_planner_digest"],
    }
    if any(digests.get(field) != digest for field, digest in expected_digests.items()):
        raise ValueError("frozen source digest mismatch")
    for field, relative in _EXECUTION_SOURCE_PATHS.items():
        if _sha256(repo_root / relative) != digests.get(field):
            raise ValueError(f"frozen execution source digest mismatch: {field}")
    metadata["source_commit"], metadata["source_dirty"] = git_state(repo_root)
    metadata["generator_manifest_sha256"] = _sha256(repo_root / _GENERATOR_MANIFEST)
    return metadata


def _committed_file_hash(repo_root: Path, revision: str, relative: str = "results/spade-selected-protocol.json") -> str | None:
    result = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=repo_root, capture_output=True)
    return None if result.returncode else hashlib.sha256(result.stdout).hexdigest()


def _is_ancestor(repo_root: Path, older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=repo_root).returncode == 0


def _selected_template_digest(selected: Mapping[str, object]) -> str:
    config = selected.get("selected_canonical_config")
    if not isinstance(config, Mapping):
        raise ValueError("selected protocol has no canonical SPADE configuration")
    return SpadeConfig(opening=config.get("opening"), policy=config.get("policy"), root_seed=0).protocol_digest


def validate_selected_protocol_payload(selected: object) -> dict[str, object]:
    if not isinstance(selected, Mapping) or set(selected) != SELECTED_PROTOCOL_FIELDS:
        raise ValueError("selected protocol schema fields drift")
    result = dict(selected)
    if result.get("schema") != "boec-spade-selected-protocol-v1":
        raise ValueError("selected protocol schema drift")
    if result.get("status") != "SELECTED":
        raise ValueError("lockbox requires a SELECTED protocol, never NO_SELECTION")
    _require_hex(result.get("source_commit"), "source_commit", length=40)
    for field in (
        "study_protocol_digest", "spec_digest", "config_digest", "generator_digest",
        "generator_manifest_sha256", "analysis_sha256", "selection_trace_digest",
        "selected_template_protocol_digest",
    ):
        _require_hex(result.get(field), field)
    if result.get("analysis_file") != "spade-development-analysis.json":
        raise ValueError("selected protocol analysis file identity drift")
    if not isinstance(result.get("development_artifacts"), list):
        raise ValueError("selected protocol development artifacts schema drift")
    trace = result.get("selection_trace")
    if not isinstance(trace, Mapping) or hashlib.sha256(
        _canonical_json(trace).encode("utf-8")
    ).hexdigest() != result["selection_trace_digest"]:
        raise ValueError("selected protocol selection trace digest mismatch")
    if not isinstance(result.get("lofo_folds"), list):
        raise ValueError("selected protocol LOFO folds schema drift")
    config = result.get("selected_canonical_config")
    config_json = result.get("selected_canonical_config_json")
    if not isinstance(config, Mapping) or config_json != _canonical_json(config):
        raise ValueError("selected protocol canonical configuration schema drift")
    opening, policy = config.get("opening"), config.get("policy")
    if result.get("selected_candidate") != f"spade-o{opening}-{policy}":
        raise ValueError("selected protocol candidate/configuration mismatch")
    if result.get("selected_template_protocol_digest") != _selected_template_digest(result):
        raise ValueError("selected protocol canonical configuration digest mismatch")
    if result.get("campaign_root_seed_binding") != "sha256_labelled_derived_per_campaign":
        raise ValueError("selected protocol campaign seed binding drift")
    return result


def _selection_power_bindings(
    selected: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    artifact_fields = (
        "family", "raw_file", "raw_sha256", "manifest_file", "manifest_sha256"
    )
    artifacts = selected.get("development_artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("selected protocol development artifacts schema drift")
    by_family: dict[str, dict[str, object]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ValueError("selected protocol development artifact schema drift")
        family = artifact.get("family")
        if family not in DEVELOPMENT_FAMILIES or family in by_family:
            raise ValueError("selected protocol development artifact identity drift")
        by_family[str(family)] = {field: artifact.get(field) for field in artifact_fields}
    if set(by_family) != set(DEVELOPMENT_FAMILIES):
        raise ValueError("selected protocol development artifacts are incomplete")

    folds = selected.get("lofo_folds")
    if not isinstance(folds, list):
        raise ValueError("selected protocol LOFO folds schema drift")
    by_held_out: dict[str, dict[str, object]] = {}
    for fold in folds:
        if not isinstance(fold, Mapping):
            raise ValueError("selected protocol LOFO fold schema drift")
        family = fold.get("held_out_family")
        if family not in DEVELOPMENT_FAMILIES or family in by_held_out:
            raise ValueError("selected protocol LOFO fold identity drift")
        by_held_out[str(family)] = {
            "held_out_family": family,
            "training_families": fold.get("training_families"),
            "selected_candidate": fold.get("selected_candidate"),
        }
    if set(by_held_out) != set(DEVELOPMENT_FAMILIES):
        raise ValueError("selected protocol LOFO folds are incomplete")
    return (
        [by_family[family] for family in DEVELOPMENT_FAMILIES],
        [by_held_out[family] for family in DEVELOPMENT_FAMILIES],
    )


def _load_generator_freeze(repo_root: Path) -> dict[str, object]:
    path = repo_root / _GENERATOR_MANIFEST
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("frozen lockbox generator manifest is missing or invalid") from exc
    expected = {"schema", "status", "frozen_date", "freeze_parent_commit", "dimension", "domain", "families", "instance_keys", "seed_derivation", "normalization", "generator_definitions", "digests"}
    if _sha256(path) != GENERATOR_FREEZE_SHA256 or not isinstance(manifest, dict) or set(manifest) != expected or manifest.get("schema") != "boec-spade-lockbox-generator-manifest-v1" or manifest.get("status") != "FROZEN_UNOPENED" or manifest.get("freeze_parent_commit") != GENERATOR_FREEZE_PARENT_COMMIT or tuple(manifest.get("families", ())) != LOCKBOX_FAMILIES:
        raise ValueError("lockbox generator manifest must remain FROZEN_UNOPENED")
    digests = manifest.get("digests")
    expected_digests = {
        "lockbox_oracles_source_sha256": _sha256(repo_root / _GENERATOR_PATH),
        "spade_study_source_sha256": _sha256(repo_root / "src/boec/spade_study.py"),
        "spec_sha256": _sha256(repo_root / _SPEC_PATH),
        "config_file_sha256": _sha256(repo_root / _CONFIG_PATH),
        "protocol_payload_sha256": registered_metadata(repo_root)["protocol_digest"],
    }
    if not isinstance(digests, Mapping) or any(digests.get(key) != value for key, value in expected_digests.items()):
        raise ValueError("lockbox generator manifest digest drift")
    return manifest


def validate_lockbox_access(*, repo_root: Path = ROOT, selected_path: Path | None = None, power_path: Path | None = None) -> dict[str, object]:
    path = selected_path or repo_root / "results/spade-selected-protocol.json"
    registered_selection = repo_root / "results/spade-selected-protocol.json"
    if path.resolve() != registered_selection.resolve():
        raise ValueError("selected protocol must use the exact registered path")
    if not path.is_file():
        raise ValueError("selected protocol artifact is missing")
    try:
        selected = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("selected protocol artifact is invalid JSON") from exc
    if not isinstance(selected, dict) or selected.get("status") != "SELECTED":
        raise ValueError("lockbox requires a SELECTED protocol, never NO_SELECTION")
    selected = validate_selected_protocol_payload(selected)
    metadata = registered_metadata(repo_root)
    current_commit, dirty = git_state(repo_root)
    if dirty or metadata.get("source_dirty"):
        raise ValueError("lockbox access refuses a dirty source tree")
    if metadata.get("source_commit") != current_commit:
        raise ValueError("registered metadata does not describe the current clean source commit")
    for field in ("protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256"):
        selected_field = "study_protocol_digest" if field == "protocol_digest" else field
        if selected.get(selected_field) != metadata.get(field):
            raise ValueError(f"selected protocol {field} digest mismatch")
    selected_sha256 = _sha256(path)
    selected_hash = _committed_file_hash(repo_root, "HEAD")
    if selected_hash != selected_sha256:
        raise ValueError("selected protocol must be committed at HEAD before lockbox access")

    plan_path = power_path or repo_root / _POWER_PATH
    if plan_path.resolve() != (repo_root / _POWER_PATH).resolve():
        raise ValueError("power plan must use the exact registered path")
    if not plan_path.is_file():
        raise ValueError("power plan artifact is missing")
    try:
        power_bytes = plan_path.read_bytes()
        parsed_power = json.loads(power_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("power plan artifact is invalid JSON") from exc
    if not isinstance(parsed_power, Mapping):
        raise ValueError("power plan artifact must be a JSON object")
    try:
        if power_bytes != _canonical_bytes(parsed_power):
            raise ValueError("power plan bytes are not the exact canonical serialization")
    except (TypeError, ValueError) as exc:
        raise ValueError("power plan bytes are not finite canonical JSON") from exc
    power_plan = validate_power_plan_payload(parsed_power)
    power_plan_sha256 = hashlib.sha256(power_bytes).hexdigest()
    if _committed_file_hash(repo_root, "HEAD", _POWER_PATH.as_posix()) != power_plan_sha256:
        raise ValueError("power plan must be committed at HEAD before lockbox access")
    if power_plan.get("status") != "POWERED":
        raise ValueError("lockbox requires a POWERED power plan")
    decision = power_plan.get("decision")
    sample_size = decision.get("selected_sample_size") if isinstance(decision, Mapping) else None
    sample_size = _registered_sample_size(sample_size)

    power_selection = power_plan.get("selected_protocol")
    if not isinstance(power_selection, Mapping) or power_selection.get("sha256") != selected_sha256 or power_selection.get("source_commit") != selected.get("source_commit"):
        raise ValueError("power plan selected protocol binding mismatch")
    selected_artifacts, selected_folds = _selection_power_bindings(selected)
    held_out_proof = power_plan.get("held_out_proof")
    if (
        not isinstance(held_out_proof, Mapping)
        or held_out_proof.get("selected_candidate") != selected.get("selected_candidate")
        or _canonical_json(held_out_proof.get("folds")) != _canonical_json(selected_folds)
    ):
        raise ValueError("power plan candidate/fold selection binding mismatch")
    if _canonical_json(power_plan.get("development_artifacts")) != _canonical_json(selected_artifacts):
        raise ValueError("power plan development artifact selection binding mismatch")
    power_digests = power_plan.get("digests")
    expected_power_digests = {
        "study_protocol_sha256": metadata["protocol_digest"],
        "specification_sha256": metadata["spec_digest"],
        "configuration_sha256": metadata["config_digest"],
        "generator_sha256": metadata["generator_digest"],
        "generator_manifest_sha256": metadata["generator_manifest_sha256"],
        "power_design_sha256": metadata.get("power_design_digest"),
        "power_engine_sha256": metadata.get("power_engine_digest"),
        "power_planner_sha256": metadata.get("power_planner_digest"),
    }
    if not isinstance(power_digests, Mapping) or any(
        power_digests.get(field) != digest
        for field, digest in expected_power_digests.items()
        if digest is not None
    ):
        raise ValueError("power plan frozen digest mismatch")
    freeze = _load_generator_freeze(repo_root)
    selected_commit = str(selected.get("source_commit", ""))
    freeze_commit = str(freeze.get("freeze_parent_commit", ""))
    if freeze_commit != GENERATOR_FREEZE_PARENT_COMMIT or not _is_ancestor(repo_root, freeze_commit, selected_commit):
        raise ValueError("selected protocol is older than the generator freeze commit")
    if not _is_ancestor(repo_root, selected_commit, metadata["source_commit"]):
        raise ValueError("selected protocol commit is not reachable from the clean source")
    power_commit = str(power_plan.get("source_commit", ""))
    if not _is_ancestor(repo_root, power_commit, metadata["source_commit"]):
        raise ValueError("power plan source commit is not an ancestor of the clean source")
    return {
        "selection": selected,
        "power_plan": power_plan,
        "sample_size": sample_size,
        "power_plan_sha256": power_plan_sha256,
    }


def assert_no_development_metric_dependency() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported_names = {
        alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    imported_modules = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported = imported_names | imported_modules
    if any(name.endswith(("run_spade_development", "select_spade_protocol")) for name in imported):
        raise RuntimeError("lockbox runner must not depend on development outcome metrics")


def registered_raw_filename(family: object, start: object, stop: object, *, sample_size: object) -> str:
    registered_n = _registered_sample_size(sample_size)
    if (
        family not in LOCKBOX_FAMILIES
        or isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(stop, bool)
        or not isinstance(stop, int)
        or not 0 <= start < stop <= registered_n
    ):
        raise ValueError("lockbox shard has unregistered family/range")
    return f"spade-lockbox-{family}-{start:04d}-{stop:04d}.jsonl.gz"


def validate_completed_shard_contract(
    shard: object,
    *,
    sample_size: int,
    merged_entry: Mapping[str, object] | None = None,
    merged_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Validate one immutable completed shard before any rows are pooled."""
    if (
        not isinstance(shard, Mapping)
        or set(shard) != SHARD_MANIFEST_FIELDS
        or shard.get("schema") != MANIFEST_SCHEMA
        or shard.get("status") != "COMPLETE"
    ):
        raise ValueError("lockbox shard manifest schema drift")
    result = dict(shard)
    family, start, stop = result.get("family"), result.get("start"), result.get("stop")
    registered_n = _registered_sample_size(sample_size)
    expected_name = registered_raw_filename(family, start, stop, sample_size=registered_n)
    if result.get("raw_file") != expected_name:
        raise ValueError("lockbox shard exact registered raw filename drift")
    if result.get("complete") is not True:
        raise ValueError("lockbox shard completion drift")
    if result.get("sample_size") != registered_n:
        raise ValueError("lockbox shard sample size drift")
    expected_rows = (stop - start) * len(LOCKBOX_ARMS)
    if result.get("expected_rows") != expected_rows:
        raise ValueError("lockbox shard expected row count drift")
    if result.get("row_count") != expected_rows:
        raise ValueError("lockbox shard row count drift")
    command_args = result.get("command_args")
    if not isinstance(command_args, list) or any(not isinstance(value, str) for value in command_args):
        raise ValueError("lockbox shard command args schema drift")
    result["environment_compatibility"] = validate_environment_compatibility(
        result.get("environment_compatibility")
    )
    if merged_entry is not None:
        if set(merged_entry) != MERGED_RAW_SHARD_FIELDS:
            raise ValueError("lockbox merged raw-shard schema drift")
        for field in ("family", "start", "stop", "raw_file", "raw_sha256", "command_args"):
            if result.get(field) != merged_entry.get(field):
                label = "command args" if field == "command_args" else field
                raise ValueError(f"lockbox shard {label} identity drift")
    if merged_manifest is not None:
        for field in (
            "protocol_digest", "spec_digest", "config_digest", "generator_digest",
            "generator_manifest_sha256", "source_commit", "source_dirty",
            "selected_protocol_sha256", "selection_source_commit",
            "power_plan_sha256", "power_source_commit",
            "environment_compatibility",
        ):
            if result.get(field) != merged_manifest.get(field):
                raise ValueError(f"lockbox shard {field} identity drift")
    return result


def validate_shard_local_rows(
    rows: object, *, family: object, start: object, stop: object, sample_size: int
) -> list[dict[str, object]]:
    """Require the exact registered key/arm grid belonging to this shard."""
    registered_raw_filename(family, start, stop, sample_size=sample_size)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("lockbox shard does not contain the exact local key/arm grid")
    identities: list[tuple[str, int, int, str]] = []
    normalized: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("lockbox shard does not contain the exact local key/arm grid")
        row_family = row.get("family")
        key = row.get("instance_seed")
        campaign_seed = row.get("campaign_seed")
        arm = row.get("arm")
        if (
            row_family != family
            or isinstance(key, bool)
            or not isinstance(key, int)
            or not start <= key < stop
            or campaign_seed != 0
            or arm not in LOCKBOX_ARMS
        ):
            raise ValueError("lockbox shard does not contain the exact local key/arm grid")
        identities.append((row_family, key, campaign_seed, arm))
        normalized.append(dict(row))
    expected = {
        (family, key, 0, arm)
        for key in range(start, stop)
        for arm in LOCKBOX_ARMS
    }
    if len(identities) != len(expected) or set(identities) != expected:
        raise ValueError("lockbox shard does not contain the exact local key/arm grid")
    return normalized


def expected_registered_output(repo_root: Path, family: str, start: int, stop: int, *, sample_size: int) -> Path:
    return repo_root / "results" / registered_raw_filename(family, start, stop, sample_size=sample_size)


def validate_shard_request(*, family: str, start: int, stop: int, output: Path, limit: int | None, smoke: bool, repo_root: Path, sample_size: int) -> None:
    registered_raw_filename(family, start, stop, sample_size=sample_size)
    in_results = (repo_root / "results").resolve() in output.resolve().parents
    if smoke and in_results:
        raise ValueError("TEST_ONLY output cannot be under registered results")
    if not smoke:
        if limit is not None:
            raise ValueError("--limit is forbidden at a registered lockbox output")
        expected = expected_registered_output(repo_root, family, start, stop, sample_size=sample_size)
        if output.resolve() != expected.resolve():
            raise ValueError("registered lockbox shard output must be exactly the registered path")
    elif limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        raise ValueError("TEST_ONLY limit must be a positive integer")


class _LockboxCore:
    def __init__(self, family: str, instance_seed: int) -> None:
        oracle = make_lockbox_oracle(family, instance_seed)
        self.family, self.instance_seed, self.dim = family, instance_seed, oracle.dim
        self.name = f"lockbox:{family}:{instance_seed}:{oracle.record.parameter_digest}"
    def f(self, X):
        return make_lockbox_oracle(self.family, self.instance_seed).f(X)


def _campaign_rows(family: str, key: int, selected: Mapping[str, object], metadata: Mapping[str, object], command_args: Sequence[str]):
    root_seed = derive_seed(STUDY_ROOT_SEED, "lockbox_campaign", family, key)
    noise_seed = derive_seed(STUDY_ROOT_SEED, "lockbox_noise", family, key)
    threshold_seed = derive_seed(STUDY_ROOT_SEED, "lockbox_threshold", family, key)
    scoring_seed = derive_seed(STUDY_ROOT_SEED, "lockbox_scoring", family, key)
    core = _LockboxCore(family, key)
    harness = SealedOracleHarness(core, optimum_value=1.0, oracle_identity=core.name)
    threshold = controlled_tau(harness, sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD, gamma=GAMMA, q_tau=Q_TAU, root_seed=threshold_seed)
    config = selected["selected_canonical_config"]
    for arm in LOCKBOX_ARMS:
        evaluator = TorchEvaluator(core, sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD, noise_source=IndexedGaussianNoise(noise_seed, SIGMA_REL, SIGMA_ADD))
        if arm == "spade":
            campaign = run_spade(evaluator, torch.stack([torch.zeros(6), torch.ones(6)]).double(), SpadeConfig(opening=config["opening"], policy=config["policy"], root_seed=root_seed), tau=threshold.tau)
        elif arm == "sobol48":
            campaign = run_sobol48(evaluator, torch.stack([torch.zeros(6), torch.ones(6)]).double(), root_seed=root_seed, tau=threshold.tau)
        else:
            campaign = run_qlognei48(evaluator, torch.stack([torch.zeros(6), torch.ones(6)]).double(), root_seed=root_seed, tau=threshold.tau)
        score = score_campaign(campaign, threshold.tau, harness.scorer(), sigma_rel=SIGMA_REL, sigma_add=SIGMA_ADD, gamma=GAMMA, alpha=ALPHA, scoring_seed=scoring_seed)
        seeds = {"noise": noise_seed, "threshold": threshold_seed, "scoring": scoring_seed, "opening_design": derive_seed(root_seed, "opening_design"), "candidate_menu": derive_seed(root_seed, "adaptive_candidate_menu"), "ivr_reference": derive_seed(root_seed, "ivr_reference_grid"), "terminal_grid": derive_seed(scoring_seed, "terminal_rule_p_grid"), "map_grid": derive_seed(scoring_seed, "probability_map_grid"), "certificate_grid": derive_seed(scoring_seed, "certificate_grid"), "certificate_draws": derive_seed(scoring_seed, "certificate_joint_draws")}
        yield build_study_row(score, study_protocol_digest=metadata["protocol_digest"], spec_digest=metadata["spec_digest"], config_digest=metadata["config_digest"], source_commit=metadata["source_commit"], source_dirty=False, command_args=command_args, parent_artifacts={"spec": metadata["spec_digest"], "config": metadata["config_digest"], "generator": metadata["generator_digest"], "generator_manifest": metadata["generator_manifest_sha256"], "selected_protocol": metadata["selected_protocol_sha256"], "power_plan": metadata["power_plan_sha256"]}, family=family, instance_seed=key, campaign_seed=0, root_seed=root_seed, derived_seeds=seeds)


def _publication_targets(destination: Path) -> tuple[Path, Path, Path]:
    return destination, Path(f"{destination}.sha256"), Path(f"{destination}.manifest.json")


def _require_unused_publication_targets(destination: Path) -> None:
    occupied = [path for path in _publication_targets(destination) if path.exists()]
    if occupied:
        raise ValueError(f"immutable lockbox publication target already exists: {occupied[0]}")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _install_new(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except FileExistsError as exc:
        raise ValueError(f"immutable lockbox publication target already exists: {target}") from exc


def _install_staged_completion(
    *, destination: Path, staged_raw: Path, staged_sidecar: Path, staged_manifest: Path
) -> None:
    _require_unused_publication_targets(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw_target, sidecar_target, manifest_target = _publication_targets(destination)
    _install_new(staged_raw, raw_target)
    _install_new(staged_sidecar, sidecar_target)
    _fsync_directory(destination.parent)
    _install_new(staged_manifest, manifest_target)
    _fsync_directory(destination.parent)


def run_lockbox_shard(*, family: str, start: int, stop: int, output: str | Path, limit: int | None = None, smoke: bool = False, repo_root: Path = ROOT, command_args: Sequence[str] = ()) -> dict[str, object]:
    destination = Path(output)
    _require_unused_publication_targets(destination)
    assert_no_development_metric_dependency()
    access = validate_lockbox_access(repo_root=repo_root)
    selected = access["selection"]
    sample_size = access["sample_size"]
    validate_shard_request(family=family, start=start, stop=stop, output=destination, limit=limit, smoke=smoke, repo_root=repo_root, sample_size=sample_size)
    metadata = registered_metadata(repo_root)
    metadata.update({
        "selected_protocol_sha256": _sha256(repo_root / "results/spade-selected-protocol.json"),
        "selection_source_commit": selected["source_commit"],
        "power_plan_sha256": access["power_plan_sha256"],
        "power_source_commit": access["power_plan"]["source_commit"],
    })
    resume_path = Path(f"{destination}.resume.json")
    rows: list[dict[str, object]] = []
    if resume_path.is_file():
        try:
            rows = validate_resume_payload(json.loads(resume_path.read_text()), metadata=metadata, family=family, start=start, stop=stop, sample_size=sample_size, raw_file=destination.name)
        except json.JSONDecodeError as exc:
            raise ValueError("resume checkpoint is invalid JSON") from exc
    runtime_environment_compatibility = environment_compatibility_projection(
        collect_environment_provenance()
    )
    if rows and common_environment_compatibility(rows) != runtime_environment_compatibility:
        raise ValueError("resume row environment compatibility differs from this worker")
    completed_keys = {int(row["instance_seed"]) for row in rows}
    keys = range(start, min(stop, start + limit) if limit is not None else stop)
    for key in keys:
        if key not in completed_keys:
            rows.extend(_campaign_rows(family, key, selected, metadata, command_args))
            _atomic_json(resume_path, make_resume_payload(family=family, start=start, stop=stop, sample_size=sample_size, raw_file=destination.name, rows=rows, metadata=metadata))
    if len(rows) != (stop - start) * len(LOCKBOX_ARMS):
        raise RuntimeError("lockbox shard is incomplete; every requested key needs all three arms")
    environment_compatibility = common_environment_compatibility(rows)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.", dir=destination.parent) as staging_name:
        staged_raw = Path(staging_name) / destination.name
        digest = write_jsonl_gzip(staged_raw, rows, protocol_digest=metadata["protocol_digest"])
        staged_sidecar = Path(f"{staged_raw}.sha256")
        published_metadata = _lockbox_publication_metadata(metadata)
        manifest = {"schema": MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": start, "stop": stop, "sample_size": sample_size, "expected_rows": (stop-start)*3, "row_count": len(rows), "complete": True, "raw_file": destination.name, "raw_sha256": digest, **published_metadata, "environment_compatibility": environment_compatibility, "command_args": list(command_args)}
        if set(manifest) != SHARD_MANIFEST_FIELDS:
            raise RuntimeError("lockbox shard manifest schema drift")
        staged_manifest = Path(f"{staged_raw}.manifest.json")
        _atomic_json(staged_manifest, manifest)
        _install_staged_completion(
            destination=destination,
            staged_raw=staged_raw,
            staged_sidecar=staged_sidecar,
            staged_manifest=staged_manifest,
        )
    return manifest


def merge_lockbox_manifests(
    manifest_paths: Sequence[str | Path],
    *,
    output: str | Path,
    metadata: Mapping[str, object],
    sample_size: int,
    repo_root: Path = ROOT,
) -> dict[str, object]:
    """Hash and merge complete shard sidecars without loading outcome rows."""
    access = validate_lockbox_access(repo_root=repo_root)
    registered_n = _registered_sample_size(access["sample_size"])
    if sample_size != registered_n:
        raise ValueError("lockbox merge caller sample size drift")
    expected_metadata = set(LOCKBOX_PROVENANCE_FIELDS)
    live_metadata = registered_metadata(repo_root)
    trusted_metadata = {
        field: live_metadata[field]
        for field in (
            "protocol_digest", "spec_digest", "config_digest", "generator_digest",
            "generator_manifest_sha256", "source_commit", "source_dirty",
        )
    }
    trusted_metadata.update({
        "selected_protocol_sha256": access["power_plan"]["selected_protocol"]["sha256"],
        "selection_source_commit": access["selection"]["source_commit"],
        "power_plan_sha256": access["power_plan_sha256"],
        "power_source_commit": access["power_plan"]["source_commit"],
    })
    if (
        set(metadata) not in (expected_metadata, expected_metadata | {"command_args"})
        or trusted_metadata["source_dirty"] is not False
        or any(metadata.get(field) != trusted_metadata[field] for field in expected_metadata)
    ):
        raise ValueError("lockbox merge caller metadata drift")
    output_path = Path(output)
    shards: list[dict[str, object]] = []
    ranges: dict[str, list[tuple[int, int]]] = {family: [] for family in LOCKBOX_FAMILIES}
    environment_compatibility: dict[str, object] | None = None
    for manifest_path in manifest_paths:
        try:
            shard = json.loads(Path(manifest_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("lockbox shard manifest is missing or invalid") from exc
        shard = validate_completed_shard_contract(shard, sample_size=registered_n)
        family, start, stop = shard["family"], shard["start"], shard["stop"]
        shard_environment = shard["environment_compatibility"]
        if environment_compatibility is None:
            environment_compatibility = shard_environment
        elif shard_environment != environment_compatibility:
            raise ValueError("lockbox shard environment compatibility drift")
        if any(shard.get(field) != trusted_metadata[field] for field in expected_metadata):
            raise ValueError("lockbox shard provenance drift")
        raw_file = shard.get("raw_file")
        raw_path = Path(manifest_path).parent / raw_file
        sidecar = Path(f"{raw_path}.sha256")
        if not raw_path.is_file() or not sidecar.is_file() or shard.get("raw_sha256") != _sha256(raw_path):
            raise ValueError("lockbox shard raw hash mismatch")
        if sidecar.read_text(encoding="ascii").split() != [shard["raw_sha256"], raw_file]:
            raise ValueError("lockbox shard raw SHA-256 sidecar mismatch")
        ranges[family].append((start, stop))
        shard_entry = {"family": family, "start": start, "stop": stop, "raw_file": raw_file, "raw_sha256": shard["raw_sha256"], "command_args": shard["command_args"], "manifest_file": Path(manifest_path).name, "manifest_sha256": _sha256(Path(manifest_path)), "sha256_file": sidecar.name, "sha256_sha256": _sha256(sidecar)}
        if set(shard_entry) != MERGED_RAW_SHARD_FIELDS:
            raise RuntimeError("lockbox merged raw-shard schema drift")
        shards.append(shard_entry)
    for family, intervals in ranges.items():
        cursor = 0
        for start, stop in sorted(intervals):
            if start != cursor:
                raise ValueError("lockbox manifests have missing or overlapping ranges")
            cursor = stop
        if cursor != registered_n:
            raise ValueError("lockbox manifests are incomplete")
    shards.sort(key=lambda item: (item["family"], item["start"], item["stop"]))
    if environment_compatibility is None:
        raise ValueError("lockbox manifests are incomplete")
    final = {"schema": MERGED_MANIFEST_SCHEMA, "status": "COMPLETE", "sample_size": registered_n, "raw_shards": shards, **trusted_metadata, "environment_compatibility": environment_compatibility}
    if set(final) != MERGED_MANIFEST_FIELDS:
        raise RuntimeError("lockbox merged manifest schema drift")
    _write_once_json(output_path, final)
    return final


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=LOCKBOX_FAMILIES); parser.add_argument("--start", required=True, type=int); parser.add_argument("--stop", required=True, type=int); parser.add_argument("--out", required=True, type=Path); parser.add_argument("--limit", type=int); parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    manifest = run_lockbox_shard(family=args.family, start=args.start, stop=args.stop, output=args.out, limit=args.limit, smoke=args.smoke, command_args=tuple(argv or sys.argv[1:]))
    print(_canonical_json(manifest)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
