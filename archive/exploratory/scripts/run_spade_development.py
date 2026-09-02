#!/usr/bin/env python3
"""Run resumable, identity-bound shards of the frozen SPADE development grid."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec.oracles import UnitScaled, load_ensemble  # noqa: E402
from boec.replay import FAMILY_ORACLE, unit_bounds  # noqa: E402
from boec.seedbook import IndexedGaussianNoise, derive_seed  # noqa: E402
from boec.spade import (  # noqa: E402
    SpadeConfig,
    _common_protocol_digest,
    run_qlognei48,
    run_sobol48,
    run_spade,
)
from boec.spade_study import (  # noqa: E402
    ControlledThreshold,
    ScoringExecutionSettings,
    SealedOracleHarness,
    build_study_row,
    controlled_tau,
    read_jsonl_gzip,
    score_campaign,
    write_jsonl_gzip,
)
from boec.torch_oracle import BiphasicOracle, TorchEvaluator  # noqa: E402


DEVELOPMENT_FAMILIES = ("hill", "ackley", "hartmann6", "levy", "rosenbrock")
OPENINGS = (32, 40, 44)
POLICIES = ("staged", "fixed_hybrid", "validity_gated")
CANDIDATE_ARM_IDS = tuple(
    f"spade-o{opening}-{policy}" for opening in OPENINGS for policy in POLICIES
)
CONTROL_ARMS = ("sobol48", "qlognei48")
DEVELOPMENT_ARM_IDS = CANDIDATE_ARM_IDS + CONTROL_ARMS
CAMPAIGNS_PER_FAMILY = 50
# Exact historical d=6 development subset, frozen in sorted instance-id order. These are
# the 25 instances in p2-versionb-gamma; hard-coding the identities prevents a later
# ensemble extension or file reordering from silently changing the development sample.
HILL_DEVELOPMENT_INSTANCE_IDS = (
    "033466197eba3ddb",
    "0a6e0788538a7c52",
    "0ed87c75239d73f8",
    "32bb966a18f1d863",
    "443c180247c17191",
    "48b1324dd0461cd9",
    "4d4f7158b65b52ba",
    "51cf489c521a6911",
    "578e5d8768359f0f",
    "59e420274f4385d9",
    "5b3926ef2c5fe4b6",
    "763e0f58925816ca",
    "7b6071e568a98779",
    "7ef3fc89acece49c",
    "7f5c7431c0530e74",
    "8abe35e93ddfcad1",
    "9414bc879284eef0",
    "9f3cdb4d835c6909",
    "c75f6d6f50fe2434",
    "ce7334da318bc5e5",
    "da5ec2fbb20c9f9b",
    "e402c32907f27534",
    "e946207e9dfe1876",
    "ef2815cdafff288c",
    "f79c5cf175034acd",
)
STUDY_ROOT_SEED = 2_026_08_25
MANIFEST_SCHEMA = "boec-spade-development-shard-v1"
RESUME_SCHEMA = "boec-spade-development-resume-v1"
DATASET_ROLE = "DEVELOPMENT"
_CONFIG_PATH = Path("configs/experiment/spade-joint.yaml")
_SPEC_PATH = Path("docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md")
_GENERATOR_PATH = Path("src/boec/lockbox_oracles.py")
_GENERATOR_MANIFEST_PATH = Path("results/spade-lockbox-generator-manifest.json")
_POWER_DESIGN_PATH = Path(
    "docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md"
)
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
_REGISTERED_METADATA_FIELDS = frozenset(
    {
        "study_protocol_digest",
        "spec_digest",
        "config_digest",
        "generator_digest",
        "generator_manifest_sha256",
        "power_design_digest",
        "power_engine_digest",
        "power_planner_digest",
        "source_commit",
        "source_dirty",
    }
)
_DEVELOPMENT_ARTIFACT_METADATA_FIELDS = (
    "study_protocol_digest",
    "spec_digest",
    "config_digest",
    "generator_digest",
    "generator_manifest_sha256",
    "source_commit",
    "source_dirty",
)
_SIGMA_REL = 0.10
_SIGMA_ADD = 0.01
_GAMMA = 0.95
_ALPHA = 0.95
_Q_TAU = 0.75
_SMOKE_SCORING_SETTINGS = ScoringExecutionSettings(
    calibration_grid_size=256,
    terminal_grid_size=64,
    map_grid_size=48,
    certificate_grid_size=24,
    certificate_draws=32,
    certificate_rho_grid_size=8,
    fit_restarts=1,
)

_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "status",
        "dataset_role",
        "family",
        "start",
        "stop",
        "expected_rows",
        "row_count",
        "complete",
        "execution_mode",
        "study_protocol_digest",
        "spec_digest",
        "config_digest",
        "generator_digest",
        "generator_manifest_sha256",
        "source_commit",
        "source_dirty",
        "raw_file",
        "raw_sha256",
        "resume_file",
        "resume_sha256",
        "row_chain_head",
        "command_args",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex_digest(value: object, name: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"{name} must be a {length}-character hexadecimal digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value.lower()


def _strict_int(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical_json(payload) + "\n").encode("utf-8")
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


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def candidate_spec(arm_id: str) -> tuple[int, str]:
    if arm_id not in CANDIDATE_ARM_IDS:
        raise ValueError(f"unknown SPADE candidate {arm_id!r}")
    prefix, policy = arm_id.removeprefix("spade-o").split("-", 1)
    opening = int(prefix)
    if opening not in OPENINGS or policy not in POLICIES:
        raise ValueError(f"unregistered SPADE candidate {arm_id!r}")
    return opening, policy


def rounds_for_opening(opening: int) -> int:
    if opening not in OPENINGS:
        raise ValueError(f"opening must be one of {OPENINGS}")
    return 1 + (48 - opening) // 4


def comparator_protocol_digest(arm: str, *, root_seed: int) -> str:
    if arm == "sobol48":
        return _common_protocol_digest(arm, root_seed, 48, (48,))
    if arm == "qlognei48":
        return _common_protocol_digest(arm, root_seed, 14, (14, *([4] * 8), 2))
    raise ValueError(f"unknown development comparator {arm!r}")


def development_campaign_key(family: str, key_index: int) -> tuple[int, int]:
    if family not in DEVELOPMENT_FAMILIES:
        raise ValueError(f"unknown development family {family!r}")
    index = _strict_int(key_index, "key_index")
    if index >= CAMPAIGNS_PER_FAMILY:
        raise ValueError(f"key_index must be below {CAMPAIGNS_PER_FAMILY}")
    if family == "hill":
        return index // 2, index % 2
    return 0, index


def development_seed_identity(
    *, family: str, instance_seed: int, campaign_seed: int
) -> dict[str, int]:
    registered_keys = {
        development_campaign_key(family, key_index)
        for key_index in range(CAMPAIGNS_PER_FAMILY)
    }
    if (instance_seed, campaign_seed) not in registered_keys:
        raise ValueError("instance/campaign seed is not a registered development key")
    root_seed = derive_seed(
        STUDY_ROOT_SEED,
        "development_campaign",
        family,
        instance_seed,
        campaign_seed,
    )
    return {
        "root": root_seed,
        "noise": derive_seed(
            STUDY_ROOT_SEED,
            "development_noise",
            family,
            instance_seed,
            campaign_seed,
        ),
        "threshold": derive_seed(
            STUDY_ROOT_SEED,
            "development_threshold",
            family,
            instance_seed,
        ),
        "scoring": derive_seed(
            STUDY_ROOT_SEED,
            "development_scoring",
            family,
            instance_seed,
            campaign_seed,
        ),
    }


def matched_seed_identity(
    *, root_seed: int, noise_seed: int, threshold_seed: int, scoring_seed: int
) -> dict[str, int]:
    return {
        "noise": noise_seed,
        "threshold": threshold_seed,
        "scoring": scoring_seed,
        "opening_design": derive_seed(root_seed, "opening_design"),
        "candidate_menu": derive_seed(root_seed, "adaptive_candidate_menu"),
        "ivr_reference": derive_seed(root_seed, "ivr_reference_grid"),
        "terminal_grid": derive_seed(scoring_seed, "terminal_rule_p_grid"),
        "map_grid": derive_seed(scoring_seed, "probability_map_grid"),
        "certificate_grid": derive_seed(scoring_seed, "certificate_grid"),
        "certificate_draws": derive_seed(scoring_seed, "certificate_joint_draws"),
    }


def _identity_contract_digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def seed_contract_digest(seeds: Mapping[str, int]) -> str:
    return _identity_contract_digest(dict(seeds))


def candidate_menu_contract_digest(*, root_seed: int, size: int) -> str:
    return _identity_contract_digest(
        {
            "schema": "boec-candidate-menu-contract-v1",
            "design": "scrambled_sobol",
            "dimension": 6,
            "size": size,
            "seed": derive_seed(root_seed, "adaptive_candidate_menu"),
        }
    )


def scorer_contract_digest(score: Mapping[str, object]) -> str:
    return _identity_contract_digest(
        {
            "schema": "boec-scorer-contract-v1",
            "scoring_seed": score["scoring_seed"],
            "settings_digest": score["scoring_settings_digest"],
            "threshold_record_digest": score["threshold_record_digest"],
            "terminal_grid_seed": score["terminal_grid_seed"],
            "map_grid_seed": score["map_grid_seed"],
            "certificate_grid_seed": score["certificate_grid_seed"],
            "certificate_draw_seed": score["certificate_draw_seed"],
        }
    )


def _allowed_generated_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    return normalized.startswith("results/") and (
        name.startswith("spade-development-")
        or name == "spade-selected-protocol.json"
    )


def git_state(repo_root: Path = ROOT) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _hex_digest(commit, "source commit", length=40)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    dirty = False
    for line in status:
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        status_code = line[:2]
        if status_code != "??" or not _allowed_generated_path(path):
            dirty = True
            break
    return commit, dirty


def _validate_registered_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(metadata, Mapping) or set(metadata) != _REGISTERED_METADATA_FIELDS:
        raise ValueError("registered metadata fields drift")
    result = dict(metadata)
    for field in _REGISTERED_METADATA_FIELDS - {"source_commit", "source_dirty"}:
        _hex_digest(result[field], field)
    _hex_digest(result["source_commit"], "source_commit", length=40)
    if not isinstance(result["source_dirty"], bool):
        raise ValueError("registered metadata source_dirty must be boolean")
    return result


def _development_artifact_metadata(
    metadata: Mapping[str, object],
) -> dict[str, object]:
    return {
        field: metadata[field]
        for field in _DEVELOPMENT_ARTIFACT_METADATA_FIELDS
    }


def registered_metadata(repo_root: Path = ROOT) -> dict[str, object]:
    config_path = repo_root / _CONFIG_PATH
    spec_path = repo_root / _SPEC_PATH
    generator_path = repo_root / _GENERATOR_PATH
    generator_manifest_path = repo_root / _GENERATOR_MANIFEST_PATH
    power_design_path = repo_root / _POWER_DESIGN_PATH
    power_engine_path = repo_root / _POWER_ENGINE_PATH
    power_planner_path = repo_root / _POWER_PLANNER_PATH
    for path in (
        config_path,
        spec_path,
        generator_path,
        generator_manifest_path,
        power_design_path,
        power_engine_path,
        power_planner_path,
    ):
        if not path.is_file():
            raise ValueError(f"required frozen artifact is missing: {path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    protocol = config.get("protocol")
    execution = config.get("execution")
    digests = config.get("digests")
    if (
        not isinstance(protocol, Mapping)
        or not isinstance(execution, Mapping)
        or not isinstance(digests, Mapping)
    ):
        raise ValueError("SPADE config is missing protocol/execution/digests mappings")
    protocol_digest = hashlib.sha256(_canonical_json(protocol).encode("utf-8")).hexdigest()
    if protocol_digest != digests.get("protocol_payload_sha256"):
        raise ValueError("configured study protocol digest does not match canonical protocol")
    execution_digest = hashlib.sha256(
        _canonical_json(execution).encode("utf-8")
    ).hexdigest()
    if (
        execution_digest != _EXECUTION_PAYLOAD_SHA256
        or digests.get("execution_payload_sha256") != _EXECUTION_PAYLOAD_SHA256
    ):
        raise ValueError("configured execution payload digest mismatch")
    spec_digest = _sha256(spec_path)
    generator_digest = _sha256(generator_path)
    power_design_digest = _sha256(power_design_path)
    power_engine_digest = _sha256(power_engine_path)
    power_planner_digest = _sha256(power_planner_path)
    if spec_digest != digests.get("spec_sha256"):
        raise ValueError("frozen specification digest mismatch")
    if generator_digest != digests.get("lockbox_oracles_source_sha256"):
        raise ValueError("frozen generator digest mismatch")
    for field, actual in (
        ("power_design_sha256", power_design_digest),
        ("power_engine_sha256", power_engine_digest),
        ("power_planner_sha256", power_planner_digest),
    ):
        if actual != digests.get(field):
            raise ValueError(f"frozen {field.removesuffix('_sha256')} digest mismatch")
    for field, relative in _EXECUTION_SOURCE_PATHS.items():
        if _sha256(repo_root / relative) != digests.get(field):
            raise ValueError(f"frozen execution source digest mismatch: {field}")
    try:
        generator_manifest = json.loads(
            generator_manifest_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError("frozen generator manifest is not valid JSON") from exc
    if (
        not isinstance(generator_manifest, Mapping)
        or generator_manifest.get("status") != "FROZEN_UNOPENED"
        or not isinstance(generator_manifest.get("digests"), Mapping)
    ):
        raise ValueError("generator manifest must remain FROZEN_UNOPENED")
    manifest_digests = generator_manifest["digests"]
    expected_manifest_digests = {
        "lockbox_oracles_source_sha256": generator_digest,
        "spade_study_source_sha256": _sha256(repo_root / "src/boec/spade_study.py"),
        "spec_sha256": spec_digest,
        "config_file_sha256": _sha256(config_path),
        "protocol_payload_sha256": protocol_digest,
    }
    if any(
        manifest_digests.get(field) != expected
        for field, expected in expected_manifest_digests.items()
    ):
        raise ValueError("frozen generator manifest digest mismatch")
    source_commit, source_dirty = git_state(repo_root)
    return _validate_registered_metadata({
        "study_protocol_digest": protocol_digest,
        "spec_digest": spec_digest,
        "config_digest": _sha256(config_path),
        "generator_digest": generator_digest,
        "generator_manifest_sha256": _sha256(generator_manifest_path),
        "power_design_digest": power_design_digest,
        "power_engine_digest": power_engine_digest,
        "power_planner_digest": power_planner_digest,
        "source_commit": source_commit,
        "source_dirty": source_dirty,
    })


def expected_registered_output(
    repo_root: Path, family: str, start: int, stop: int
) -> Path:
    return repo_root / "results" / (
        f"spade-development-{family}-{start:03d}-{stop:03d}.jsonl.gz"
    )


def validate_shard_request(
    *,
    family: str,
    start: int,
    stop: int,
    output: Path,
    smoke: bool,
    repo_root: Path,
) -> None:
    if family not in DEVELOPMENT_FAMILIES:
        raise ValueError(f"family must be one of {DEVELOPMENT_FAMILIES}")
    start_i = _strict_int(start, "start")
    stop_i = _strict_int(stop, "stop", minimum=1)
    if not start_i < stop_i <= CAMPAIGNS_PER_FAMILY:
        raise ValueError("range must satisfy 0 <= start < stop <= 50")
    destination = output.resolve()
    registered_results = (repo_root / "results").resolve()
    in_results = destination == registered_results or registered_results in destination.parents
    if smoke and in_results:
        raise ValueError("SMOKE output cannot be written under registered results")
    if not smoke:
        expected = expected_registered_output(repo_root, family, start_i, stop_i).resolve()
        if destination != expected:
            raise ValueError(f"registered shard output must be exactly {expected}")


def make_shard_manifest(
    *,
    family: str,
    start: int,
    stop: int,
    row_count: int,
    raw_file: str,
    raw_sha256: str,
    resume_file: str | None = None,
    resume_sha256: str = "0" * 64,
    row_chain_head: str = "0" * 64,
    metadata: Mapping[str, object],
    smoke: bool,
    complete: bool,
    command_args: Sequence[str],
    dataset_role: str = DATASET_ROLE,
) -> dict[str, object]:
    expected_rows = (stop - start) * len(DEVELOPMENT_ARM_IDS)
    status = "SMOKE" if smoke else ("COMPLETE" if complete else "RUNNING")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": status,
        "dataset_role": dataset_role,
        "family": family,
        "start": start,
        "stop": stop,
        "expected_rows": expected_rows,
        "row_count": row_count,
        "complete": complete,
        "execution_mode": "TEST_ONLY" if smoke else "REGISTERED",
        "study_protocol_digest": metadata["study_protocol_digest"],
        "spec_digest": metadata["spec_digest"],
        "config_digest": metadata["config_digest"],
        "generator_digest": metadata["generator_digest"],
        "generator_manifest_sha256": metadata["generator_manifest_sha256"],
        "source_commit": metadata["source_commit"],
        "source_dirty": metadata["source_dirty"],
        "raw_file": raw_file,
        "raw_sha256": raw_sha256,
        "resume_file": resume_file or f"{raw_file}.resume.json",
        "resume_sha256": resume_sha256,
        "row_chain_head": row_chain_head,
        "command_args": list(command_args),
    }
    validate_shard_manifest(manifest, allow_incomplete=True)
    return manifest


def validate_shard_manifest(
    manifest: Mapping[str, object], *, allow_incomplete: bool = False
) -> dict[str, object]:
    if not isinstance(manifest, Mapping) or set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("development shard manifest has schema fields drift")
    result = dict(manifest)
    if result["schema"] != MANIFEST_SCHEMA:
        raise ValueError("development shard manifest schema drift")
    if result["dataset_role"] != DATASET_ROLE:
        raise ValueError("development shard dataset_role must be DEVELOPMENT, never held out")
    family = result["family"]
    if family not in DEVELOPMENT_FAMILIES:
        raise ValueError("development shard family is not registered")
    start = _strict_int(result["start"], "manifest start")
    stop = _strict_int(result["stop"], "manifest stop", minimum=1)
    if not start < stop <= CAMPAIGNS_PER_FAMILY:
        raise ValueError("development shard range is invalid")
    expected = (stop - start) * len(DEVELOPMENT_ARM_IDS)
    if result["expected_rows"] != expected:
        raise ValueError("development shard expected_rows drift")
    row_count = _strict_int(result["row_count"], "manifest row_count")
    if row_count > expected:
        raise ValueError("development shard has more than the registered rows")
    if not isinstance(result["complete"], bool):
        raise ValueError("development shard complete must be boolean")
    if result["status"] not in {"RUNNING", "COMPLETE", "SMOKE"}:
        raise ValueError("development shard status is invalid")
    if result["status"] == "SMOKE":
        if result["execution_mode"] != "TEST_ONLY":
            raise ValueError("SMOKE shard must use TEST_ONLY execution")
    elif result["execution_mode"] != "REGISTERED":
        raise ValueError("registered development shard must use REGISTERED execution")
    if result["complete"] != (row_count == expected):
        raise ValueError("development shard complete flag disagrees with row count")
    if result["status"] == "COMPLETE" and not result["complete"]:
        raise ValueError("COMPLETE development shard is incomplete")
    if not allow_incomplete and (result["status"] != "COMPLETE" or not result["complete"]):
        raise ValueError("selection requires a complete COMPLETE development shard")
    for name in (
        "study_protocol_digest",
        "spec_digest",
        "config_digest",
        "generator_digest",
        "generator_manifest_sha256",
        "raw_sha256",
        "resume_sha256",
        "row_chain_head",
    ):
        _hex_digest(result[name], name)
    _hex_digest(result["source_commit"], "source_commit", length=40)
    if not isinstance(result["source_dirty"], bool):
        raise ValueError("source_dirty must be boolean")
    if not isinstance(result["raw_file"], str) or Path(result["raw_file"]).name != result["raw_file"]:
        raise ValueError("raw_file must be a basename")
    if (
        not isinstance(result["resume_file"], str)
        or Path(result["resume_file"]).name != result["resume_file"]
    ):
        raise ValueError("resume_file must be a basename")
    if not isinstance(result["command_args"], list) or not all(
        isinstance(value, str) for value in result["command_args"]
    ):
        raise ValueError("command_args must be a list of strings")
    return result


def read_shard_rows(path: str | Path, protocol_digest: str) -> list[dict[str, object]]:
    return read_jsonl_gzip(path, protocol_digest=protocol_digest)


def resume_checkpoint_path(output: str | Path) -> Path:
    return Path(f"{Path(output)}.resume.json")


def _row_chain_head(rows: Sequence[Mapping[str, object]]) -> str:
    head = "0" * 64
    for row in rows:
        row_digest = hashlib.sha256(_canonical_json(row).encode("utf-8")).hexdigest()
        head = hashlib.sha256(f"{head}:{row_digest}".encode("ascii")).hexdigest()
    return head


def _resume_payload(
    *,
    family: str,
    start: int,
    stop: int,
    raw_file: str,
    rows: Sequence[Mapping[str, object]],
    metadata: Mapping[str, object],
    smoke: bool,
    command_args: Sequence[str],
    expected_raw_sha256: str | None,
) -> dict[str, object]:
    payload = {
        "schema": RESUME_SCHEMA,
        "family": family,
        "start": start,
        "stop": stop,
        "raw_file": raw_file,
        "execution_mode": "TEST_ONLY" if smoke else "REGISTERED",
        "study_protocol_digest": metadata["study_protocol_digest"],
        "spec_digest": metadata["spec_digest"],
        "config_digest": metadata["config_digest"],
        "generator_digest": metadata["generator_digest"],
        "generator_manifest_sha256": metadata["generator_manifest_sha256"],
        "source_commit": metadata["source_commit"],
        "source_dirty": metadata["source_dirty"],
        "command_args": list(command_args),
        "row_count": len(rows),
        "row_chain_head": _row_chain_head(rows),
        "expected_raw_sha256": expected_raw_sha256,
        "rows": [dict(row) for row in rows],
    }
    _canonical_json(payload)
    return payload


def _write_resume_checkpoint(path: Path, payload: Mapping[str, object]) -> str:
    _atomic_json(path, payload)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_resume_checkpoint(
    path: str | Path, *, protocol_digest: str
) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise ValueError("independent resume checkpoint is missing")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("resume checkpoint is not valid JSON") from exc
    required = {
        "schema", "family", "start", "stop", "raw_file", "execution_mode",
        "study_protocol_digest", "spec_digest", "config_digest", "generator_digest",
        "generator_manifest_sha256", "source_commit", "source_dirty", "command_args", "row_count",
        "row_chain_head", "expected_raw_sha256", "rows",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("resume checkpoint schema fields drift")
    if payload["schema"] != RESUME_SCHEMA:
        raise ValueError("resume checkpoint schema drift")
    if payload["study_protocol_digest"] != protocol_digest:
        raise ValueError("resume checkpoint protocol digest mismatch")
    rows = payload["rows"]
    if not isinstance(rows, list) or payload["row_count"] != len(rows):
        raise ValueError("resume checkpoint row count mismatch")
    if payload["row_chain_head"] != _row_chain_head(rows):
        raise ValueError("resume checkpoint row hash-chain mismatch")
    expected_raw = payload["expected_raw_sha256"]
    if expected_raw is not None:
        _hex_digest(expected_raw, "resume expected raw SHA-256")
    return payload


def _development_oracle(
    family: str,
    instance_seed: int,
    noise_seed: int,
) -> tuple[object, object, str]:
    noise = IndexedGaussianNoise(noise_seed, _SIGMA_REL, _SIGMA_ADD)
    if family == "hill":
        ensemble = load_ensemble(6)
        by_id = {instance.instance_id: instance for instance in ensemble}
        missing = set(HILL_DEVELOPMENT_INSTANCE_IDS) - set(by_id)
        if missing:
            raise RuntimeError(
                "registered Hill development instances are missing from the committed "
                f"ensemble: {sorted(missing)}"
            )
        instance = by_id[HILL_DEVELOPMENT_INSTANCE_IDS[instance_seed]]
        truth_oracle = BiphasicOracle(instance, sigma_rel=_SIGMA_REL, sigma_add=_SIGMA_ADD)
        evaluator = BiphasicOracle(
            instance,
            sigma_rel=_SIGMA_REL,
            sigma_add=_SIGMA_ADD,
            noise_source=noise,
        )
        identity = f"hill:{instance.instance_id}"
        return truth_oracle, evaluator, identity
    if family not in FAMILY_ORACLE:
        raise ValueError(f"unknown development family {family!r}")
    truth_core = UnitScaled(FAMILY_ORACLE[family](6))
    truth_oracle = TorchEvaluator(truth_core, sigma_rel=_SIGMA_REL, sigma_add=_SIGMA_ADD)
    evaluator = TorchEvaluator(
        UnitScaled(FAMILY_ORACLE[family](6)),
        sigma_rel=_SIGMA_REL,
        sigma_add=_SIGMA_ADD,
        noise_source=noise,
    )
    return truth_oracle, evaluator, f"{family}:d6:fixed"


def _development_threshold(
    family: str,
    instance_seed: int,
    noise_seed: int,
    threshold_seed: int,
    *,
    smoke: bool,
) -> tuple[SealedOracleHarness, ControlledThreshold]:
    truth_oracle, _, oracle_identity = _development_oracle(
        family, instance_seed, noise_seed
    )
    harness = SealedOracleHarness(
        truth_oracle,
        optimum_value=1.0,
        oracle_identity=oracle_identity,
        truth_range_contract=(
            "strict_unit_interval" if family == "hill" else "legacy_unit_scaled"
        ),
    )
    mode = "TEST_ONLY" if smoke else "REGISTERED"
    settings = _SMOKE_SCORING_SETTINGS if smoke else None
    threshold = controlled_tau(
        harness,
        sigma_rel=_SIGMA_REL,
        sigma_add=_SIGMA_ADD,
        gamma=_GAMMA,
        q_tau=_Q_TAU,
        root_seed=threshold_seed,
        execution_mode=mode,
        settings=settings,
    )
    return harness, threshold


def _run_campaign_rows(
    family: str,
    key_index: int,
    arm_ids: Sequence[str],
    *,
    metadata: Mapping[str, object],
    smoke: bool,
    command_args: Sequence[str],
) -> Iterable[dict[str, object]]:
    instance_seed, campaign_seed = development_campaign_key(family, key_index)
    registered_seeds = development_seed_identity(
        family=family,
        instance_seed=instance_seed,
        campaign_seed=campaign_seed,
    )
    campaign_root = registered_seeds["root"]
    noise_seed = registered_seeds["noise"]
    threshold_seed = registered_seeds["threshold"]
    scoring_seed = registered_seeds["scoring"]
    mode = "TEST_ONLY" if smoke else "REGISTERED"
    settings = _SMOKE_SCORING_SETTINGS if smoke else None
    harness, threshold = _development_threshold(
        family,
        instance_seed,
        noise_seed,
        threshold_seed,
        smoke=smoke,
    )
    bounds = unit_bounds(6)
    for arm_id in arm_ids:
        _, evaluator, _ = _development_oracle(family, instance_seed, noise_seed)
        if arm_id in CANDIDATE_ARM_IDS:
            opening, policy = candidate_spec(arm_id)
            campaign = run_spade(
                evaluator,
                bounds,
                SpadeConfig(
                    opening=opening,
                    policy=policy,
                    root_seed=campaign_root,
                ),
                tau=threshold.tau,
                fast=smoke,
            )
        elif arm_id == "sobol48":
            campaign = run_sobol48(
                evaluator,
                bounds,
                root_seed=campaign_root,
                tau=threshold.tau,
                fast=smoke,
            )
        elif arm_id == "qlognei48":
            campaign = run_qlognei48(
                evaluator,
                bounds,
                root_seed=campaign_root,
                tau=threshold.tau,
                fast=smoke,
            )
        else:
            raise ValueError(f"unknown development arm {arm_id!r}")
        score = score_campaign(
            campaign,
            threshold.tau,
            harness.scorer(),
            sigma_rel=_SIGMA_REL,
            sigma_add=_SIGMA_ADD,
            gamma=_GAMMA,
            alpha=_ALPHA,
            scoring_seed=scoring_seed,
            execution_mode=mode,
            settings=settings,
        )
        derived_seeds = matched_seed_identity(
            root_seed=campaign_root,
            noise_seed=noise_seed,
            threshold_seed=threshold_seed,
            scoring_seed=scoring_seed,
        )
        score_payload = score.as_dict()
        yield build_study_row(
            score,
            study_protocol_digest=str(metadata["study_protocol_digest"]),
            spec_digest=str(metadata["spec_digest"]),
            config_digest=str(metadata["config_digest"]),
            source_commit=str(metadata["source_commit"]),
            source_dirty=bool(metadata["source_dirty"]),
            command_args=command_args,
            parent_artifacts={
                "spec": str(metadata["spec_digest"]),
                "config": str(metadata["config_digest"]),
                "generator": str(metadata["generator_digest"]),
                "generator_manifest": str(metadata["generator_manifest_sha256"]),
                "seed_contract": seed_contract_digest(derived_seeds),
                "candidate_menu_contract": candidate_menu_contract_digest(
                    root_seed=campaign_root,
                    size=campaign.effective_settings.candidate_menu_size,
                ),
                "scorer_contract": scorer_contract_digest(score_payload),
            },
            family=family,
            instance_seed=instance_seed,
            campaign_seed=campaign_seed,
            root_seed=campaign_root,
            derived_seeds=derived_seeds,
        )


def _development_arm_id(row: Mapping[str, object]) -> str:
    arm = row.get("arm")
    if arm in CONTROL_ARMS:
        root_seed = row.get("root_seed")
        if isinstance(root_seed, bool) or not isinstance(root_seed, int):
            raise ValueError("comparator row root_seed is invalid")
        expected = comparator_protocol_digest(str(arm), root_seed=root_seed)
        if row.get("arm_protocol_digest") != expected:
            raise ValueError("row has an unregistered comparator protocol digest")
        return str(arm)
    if arm != "spade":
        raise ValueError(f"unregistered development arm {arm!r}")
    root_seed = row.get("root_seed")
    if isinstance(root_seed, bool) or not isinstance(root_seed, int):
        raise ValueError("SPADE row root_seed is invalid")
    digest = row.get("arm_protocol_digest")
    matches = []
    for candidate in CANDIDATE_ARM_IDS:
        opening, policy = candidate_spec(candidate)
        if SpadeConfig(opening=opening, policy=policy, root_seed=root_seed).protocol_digest == digest:
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError("row has an unregistered SPADE candidate protocol digest")
    return matches[0]


def _validate_partial_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    family: str,
    start: int,
    stop: int,
    metadata: Mapping[str, object],
    smoke: bool,
) -> set[tuple[int, str]]:
    seen: set[tuple[int, str]] = set()
    expected_keys = {
        development_campaign_key(family, index): index for index in range(start, stop)
    }
    expected_mode = "TEST_ONLY" if smoke else "REGISTERED"
    for row in rows:
        if row["family"] != family:
            raise ValueError("resumed shard contains another family")
        key = (row["instance_seed"], row["campaign_seed"])
        if key not in expected_keys:
            raise ValueError("resumed shard contains a key outside its range")
        for field, metadata_name in (
            ("protocol_digest", "study_protocol_digest"),
            ("spec_digest", "spec_digest"),
            ("config_digest", "config_digest"),
            ("source_commit", "source_commit"),
        ):
            if row[field] != metadata[metadata_name]:
                raise ValueError(f"resumed shard {field} mismatch")
        if row["source_dirty"] != metadata["source_dirty"]:
            raise ValueError("resumed shard source_dirty mismatch")
        parents = row.get("parent_artifacts")
        if (
            not isinstance(parents, Mapping)
            or parents.get("generator") != metadata["generator_digest"]
            or parents.get("generator_manifest") != metadata["generator_manifest_sha256"]
        ):
            raise ValueError("resumed shard generator parent mismatch")
        if row["scores"]["execution_mode"] != expected_mode:
            raise ValueError("resumed shard execution mode mismatch")
        arm_id = _development_arm_id(row)
        identity = (expected_keys[key], arm_id)
        if identity in seen:
            raise ValueError("resumed shard contains a duplicate development arm")
        seen.add(identity)
    return seen


def run_development_shard(
    *,
    family: str,
    start: int,
    stop: int,
    output: str | Path,
    smoke: bool = False,
    metadata: Mapping[str, object] | None = None,
    repo_root: Path = ROOT,
    command_args: Sequence[str] = (),
) -> dict[str, object]:
    destination = Path(output)
    validate_shard_request(
        family=family,
        start=start,
        stop=stop,
        output=destination,
        smoke=smoke,
        repo_root=repo_root,
    )
    registered = _validate_registered_metadata(
        registered_metadata(repo_root) if metadata is None else metadata
    )
    frozen = _development_artifact_metadata(registered)
    if not smoke and frozen["source_dirty"]:
        raise ValueError("registered development campaigns require a clean source tree")
    manifest_path = Path(str(destination) + ".manifest.json")
    resume_path = resume_checkpoint_path(destination)
    rows: list[dict[str, object]] = []
    prior_resume: dict[str, object] | None = None
    if resume_path.exists():
        prior_resume = read_resume_checkpoint(
            resume_path,
            protocol_digest=str(frozen["study_protocol_digest"]),
        )
        expected_resume_identity = {
            "family": family,
            "start": start,
            "stop": stop,
            "raw_file": destination.name,
            "execution_mode": "TEST_ONLY" if smoke else "REGISTERED",
            "study_protocol_digest": frozen["study_protocol_digest"],
            "spec_digest": frozen["spec_digest"],
            "config_digest": frozen["config_digest"],
            "generator_digest": frozen["generator_digest"],
            "generator_manifest_sha256": frozen["generator_manifest_sha256"],
            "source_commit": frozen["source_commit"],
            "source_dirty": frozen["source_dirty"],
        }
        for name, expected in expected_resume_identity.items():
            if prior_resume[name] != expected:
                raise ValueError(f"resume checkpoint {name} mismatch")
        rows = list(prior_resume["rows"])
    elif destination.exists() or manifest_path.exists():
        raise ValueError(
            "raw shard/manifest exists without its independent resume checkpoint"
        )

    if destination.exists():
        if prior_resume is None or prior_resume["expected_raw_sha256"] is None:
            raise ValueError("raw shard exists without a persisted expected raw SHA-256")
        actual_raw_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual_raw_digest != prior_resume["expected_raw_sha256"]:
            raise ValueError("raw shard differs from the independent resume expected raw SHA-256")
    if manifest_path.exists():
        if not destination.exists() or prior_resume is None:
            raise ValueError("complete manifest requires raw shard and resume checkpoint")
        prior_manifest = validate_shard_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            allow_incomplete=True,
        )
        expected_invocation = {
            "family": family,
            "start": start,
            "stop": stop,
            "execution_mode": "TEST_ONLY" if smoke else "REGISTERED",
            "study_protocol_digest": frozen["study_protocol_digest"],
            "spec_digest": frozen["spec_digest"],
            "config_digest": frozen["config_digest"],
            "generator_digest": frozen["generator_digest"],
            "generator_manifest_sha256": frozen["generator_manifest_sha256"],
            "source_commit": frozen["source_commit"],
            "source_dirty": frozen["source_dirty"],
            "raw_file": destination.name,
            "resume_file": resume_path.name,
        }
        for name, expected in expected_invocation.items():
            if prior_manifest[name] != expected:
                raise ValueError(f"resumed shard manifest {name} mismatch")
        resume_digest = hashlib.sha256(resume_path.read_bytes()).hexdigest()
        if prior_manifest["resume_sha256"] != resume_digest:
            raise ValueError("complete manifest resume checkpoint SHA-256 mismatch")
        if prior_manifest["row_chain_head"] != prior_resume["row_chain_head"]:
            raise ValueError("complete manifest row hash-chain mismatch")
        if prior_manifest["raw_sha256"] != prior_resume["expected_raw_sha256"]:
            raise ValueError("complete manifest expected raw SHA-256 mismatch")
        raw_rows = read_shard_rows(destination, str(frozen["study_protocol_digest"]))
        if _canonical_json(raw_rows) != _canonical_json(rows):
            raise ValueError("raw shard rows differ from independent resume checkpoint")
        if prior_manifest["row_count"] != len(rows):
            raise ValueError("resumed shard manifest row count mismatch")
        if prior_manifest["complete"]:
            return prior_manifest
    seen = _validate_partial_rows(
        rows,
        family=family,
        start=start,
        stop=stop,
        metadata=frozen,
        smoke=smoke,
    )

    def checkpoint(expected_raw_sha256: str | None = None) -> tuple[dict[str, object], str]:
        payload = _resume_payload(
            family=family,
            start=start,
            stop=stop,
            raw_file=destination.name,
            rows=rows,
            metadata=frozen,
            smoke=smoke,
            command_args=command_args,
            expected_raw_sha256=expected_raw_sha256,
        )
        return payload, _write_resume_checkpoint(resume_path, payload)

    for key_index in range(start, stop):
        missing = [
            arm_id
            for arm_id in DEVELOPMENT_ARM_IDS
            if (key_index, arm_id) not in seen
        ]
        for row in _run_campaign_rows(
            family,
            key_index,
            missing,
            metadata=frozen,
            smoke=smoke,
            command_args=command_args,
        ):
            arm_id = _development_arm_id(row)
            identity = (key_index, arm_id)
            if identity in seen:
                raise ValueError("campaign runner emitted a duplicate development arm")
            rows.append(row)
            seen.add(identity)
            checkpoint()
    if not rows:
        raise RuntimeError("development shard produced no rows")
    complete = len(rows) == (stop - start) * len(DEVELOPMENT_ARM_IDS)
    if not complete:
        raise RuntimeError("development shard stopped before every requested arm completed")
    staging = destination.with_name(f".{destination.name}.promotion")
    raw_digest = write_jsonl_gzip(
        staging,
        rows,
        protocol_digest=str(frozen["study_protocol_digest"]),
    )
    if (
        prior_resume is not None
        and prior_resume["expected_raw_sha256"] is not None
        and prior_resume["expected_raw_sha256"] != raw_digest
    ):
        raise ValueError("deterministic promotion differs from persisted expected raw SHA-256")
    final_resume, resume_digest = checkpoint(raw_digest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, destination)
    Path(f"{staging}.sha256").unlink(missing_ok=True)
    _atomic_text(
        Path(f"{destination}.sha256"),
        f"{raw_digest}  {destination.name}\n",
    )
    manifest = make_shard_manifest(
        family=family,
        start=start,
        stop=stop,
        row_count=len(rows),
        raw_file=destination.name,
        raw_sha256=raw_digest,
        resume_file=resume_path.name,
        resume_sha256=resume_digest,
        row_chain_head=str(final_resume["row_chain_head"]),
        metadata=frozen,
        smoke=smoke,
        complete=True,
        command_args=command_args,
    )
    _atomic_json(manifest_path, manifest)
    return manifest


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=DEVELOPMENT_FAMILIES)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--stop", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run reduced TEST_ONLY numerics; output must be outside results/",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    command_args = tuple(sys.argv[1:] if argv is None else argv)
    manifest = run_development_shard(
        family=args.family,
        start=args.start,
        stop=args.stop,
        output=args.out,
        smoke=args.smoke,
        command_args=command_args,
    )
    print(_canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
