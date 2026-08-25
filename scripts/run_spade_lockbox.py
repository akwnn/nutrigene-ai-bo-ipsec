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
from boec.spade_study import SealedOracleHarness, _validate_rows, build_study_row, controlled_tau, score_campaign, write_jsonl_gzip  # noqa: E402
from boec.torch_oracle import TorchEvaluator  # noqa: E402


LOCKBOX_ARMS = ("spade", "sobol48", "qlognei48")
LOCKBOX_SAMPLE_SIZE = 350
STUDY_ROOT_SEED = 2_026_08_25
SIGMA_REL, SIGMA_ADD, GAMMA, ALPHA, Q_TAU = .10, .01, .95, .95, .75
MANIFEST_SCHEMA = "boec-spade-lockbox-shard-v1"
MERGED_MANIFEST_SCHEMA = "boec-spade-lockbox-manifest-v1"
GENERATOR_FREEZE_SHA256 = "2bf6d6d51e22d8d6faa117f6ac701675b929c40b8a034435bb83ae6011493bcd"
GENERATOR_FREEZE_PARENT_COMMIT = "d1fab2c2099926945e399f741ccc79123a539066"
SHARD_MANIFEST_FIELDS = frozenset({
    "schema", "status", "family", "start", "stop", "sample_size", "expected_rows",
    "row_count", "complete", "raw_file", "raw_sha256", "protocol_digest",
    "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256",
    "source_commit", "source_dirty", "selected_protocol_sha256",
    "selection_source_commit", "command_args",
})
MERGED_MANIFEST_FIELDS = frozenset({
    "schema", "status", "sample_size", "raw_shards", "protocol_digest", "spec_digest",
    "config_digest", "generator_digest", "generator_manifest_sha256", "source_commit",
    "source_dirty", "selected_protocol_sha256", "selection_source_commit",
})
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


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _row_chain_head(rows: Sequence[Mapping[str, object]]) -> str:
    head = "0" * 64
    for row in rows:
        digest = hashlib.sha256(_canonical_json(row).encode()).hexdigest()
        head = hashlib.sha256(f"{head}:{digest}".encode()).hexdigest()
    return head


def _validate_resume_rows(rows: Sequence[Mapping[str, object]], *, family: str, start: int, stop: int) -> None:
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


def make_resume_payload(*, family: str, start: int, stop: int, raw_file: str, rows: Sequence[Mapping[str, object]], metadata: Mapping[str, object]) -> dict[str, object]:
    _validate_resume_rows(rows, family=family, start=start, stop=stop)
    return {"schema": "boec-spade-lockbox-resume-v1", "family": family, "start": start, "stop": stop, "raw_file": raw_file, "metadata": dict(metadata), "row_count": len(rows), "row_chain_head": _row_chain_head(rows), "rows": [dict(row) for row in rows]}


def validate_resume_payload(payload: Mapping[str, object], *, metadata: Mapping[str, object], family: str, start: int, stop: int, raw_file: str) -> list[dict[str, object]]:
    expected = {"schema", "family", "start", "stop", "raw_file", "metadata", "row_count", "row_chain_head", "rows"}
    if not isinstance(payload, Mapping) or set(payload) != expected or payload.get("schema") != "boec-spade-lockbox-resume-v1":
        raise ValueError("resume checkpoint schema drift")
    if (payload.get("family"), payload.get("start"), payload.get("stop"), payload.get("raw_file")) != (family, start, stop, raw_file) or payload.get("metadata") != dict(metadata):
        raise ValueError("resume checkpoint identity drift")
    rows = payload.get("rows")
    if not isinstance(rows, list) or payload.get("row_count") != len(rows) or payload.get("row_chain_head") != _row_chain_head(rows):
        raise ValueError("resume checkpoint row hash-chain mismatch")
    _validate_resume_rows(rows, family=family, start=start, stop=stop)
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
        if parents.get("generator") != metadata.get("generator_digest") or parents.get("generator_manifest") != metadata.get("generator_manifest_sha256"):
            raise ValueError("resume row parent provenance drift")
    return [dict(row) for row in validated]


def _allowed_generated_path(path: str) -> bool:
    """Permit only exact registered generated names directly below results/."""
    normalized = path.replace("\\", "/")
    if not normalized.startswith("results/") or "/" in normalized.removeprefix("results/"):
        return False
    name = normalized.removeprefix("results/")
    import re
    return bool(re.fullmatch(r"spade-lockbox-(?:[a-z_]+-\d{3}-\d{3}\.jsonl\.gz(?:\.(?:sha256|manifest\.json|resume\.json))?|manifest\.json|analysis\.json|release\.json)", name) or name == "spade-selected-protocol.json")


def git_state(repo_root: Path = ROOT) -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.splitlines()
    dirty = any(line and (line[:2] != "??" or not _allowed_generated_path(line[3:].split(" -> ")[-1])) for line in status)
    return commit, dirty


def registered_metadata(repo_root: Path = ROOT) -> dict[str, object]:
    config_path, spec_path, generator_path = (repo_root / _CONFIG_PATH, repo_root / _SPEC_PATH, repo_root / _GENERATOR_PATH)
    config = yaml.safe_load(config_path.read_text())
    protocol = config.get("protocol") if isinstance(config, Mapping) else None
    digests = config.get("digests") if isinstance(config, Mapping) else None
    if not isinstance(protocol, Mapping) or not isinstance(digests, Mapping):
        raise ValueError("SPADE config is missing frozen protocol digests")
    protocol_digest = hashlib.sha256(_canonical_json(protocol).encode()).hexdigest()
    if protocol_digest != digests.get("protocol_payload_sha256"):
        raise ValueError("configured study protocol digest mismatch")
    metadata = {"protocol_digest": protocol_digest, "spec_digest": _sha256(spec_path), "config_digest": _sha256(config_path), "generator_digest": _sha256(generator_path)}
    if metadata["spec_digest"] != digests.get("spec_sha256") or metadata["generator_digest"] != digests.get("lockbox_oracles_source_sha256"):
        raise ValueError("frozen source digest mismatch")
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


def validate_lockbox_access(*, repo_root: Path = ROOT, selected_path: Path | None = None) -> dict[str, object]:
    path = selected_path or repo_root / "results/spade-selected-protocol.json"
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
    _, dirty = git_state(repo_root)
    if dirty or metadata.get("source_dirty"):
        raise ValueError("lockbox access refuses a dirty source tree")
    for field in ("protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256"):
        selected_field = "study_protocol_digest" if field == "protocol_digest" else field
        if selected.get(selected_field) != metadata.get(field):
            raise ValueError(f"selected protocol {field} digest mismatch")
    selected_hash = _committed_file_hash(repo_root, "HEAD")
    if selected_hash != _sha256(path):
        raise ValueError("selected protocol must be committed at HEAD before lockbox access")
    freeze = _load_generator_freeze(repo_root)
    selected_commit = str(selected.get("source_commit", ""))
    freeze_commit = str(freeze.get("freeze_parent_commit", ""))
    if freeze_commit != GENERATOR_FREEZE_PARENT_COMMIT or not _is_ancestor(repo_root, freeze_commit, selected_commit):
        raise ValueError("selected protocol is older than the generator freeze commit")
    if not _is_ancestor(repo_root, selected_commit, metadata["source_commit"]):
        raise ValueError("selected protocol commit is not reachable from the clean source")
    return selected


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


def registered_raw_filename(family: object, start: object, stop: object) -> str:
    if (
        family not in LOCKBOX_FAMILIES
        or isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(stop, bool)
        or not isinstance(stop, int)
        or not 0 <= start < stop <= LOCKBOX_SAMPLE_SIZE
    ):
        raise ValueError("lockbox shard has unregistered family/range")
    return f"spade-lockbox-{family}-{start:03d}-{stop:03d}.jsonl.gz"


def validate_completed_shard_contract(
    shard: object,
    *,
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
    expected_name = registered_raw_filename(family, start, stop)
    if result.get("raw_file") != expected_name:
        raise ValueError("lockbox shard exact registered raw filename drift")
    if result.get("complete") is not True:
        raise ValueError("lockbox shard completion drift")
    if result.get("sample_size") != LOCKBOX_SAMPLE_SIZE:
        raise ValueError("lockbox shard sample size drift")
    expected_rows = (stop - start) * len(LOCKBOX_ARMS)
    if result.get("expected_rows") != expected_rows:
        raise ValueError("lockbox shard expected row count drift")
    if result.get("row_count") != expected_rows:
        raise ValueError("lockbox shard row count drift")
    command_args = result.get("command_args")
    if not isinstance(command_args, list) or any(not isinstance(value, str) for value in command_args):
        raise ValueError("lockbox shard command args schema drift")
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
        ):
            if result.get(field) != merged_manifest.get(field):
                raise ValueError(f"lockbox shard {field} identity drift")
    return result


def validate_shard_local_rows(
    rows: object, *, family: object, start: object, stop: object
) -> list[dict[str, object]]:
    """Require the exact registered key/arm grid belonging to this shard."""
    registered_raw_filename(family, start, stop)
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


def expected_registered_output(repo_root: Path, family: str, start: int, stop: int) -> Path:
    return repo_root / "results" / registered_raw_filename(family, start, stop)


def validate_shard_request(*, family: str, start: int, stop: int, output: Path, limit: int | None, smoke: bool, repo_root: Path) -> None:
    if family not in LOCKBOX_FAMILIES or isinstance(start, bool) or isinstance(stop, bool) or not isinstance(start, int) or not isinstance(stop, int) or not 0 <= start < stop <= LOCKBOX_SAMPLE_SIZE:
        raise ValueError("lockbox shard must use a registered family and exactly the 0..350 prefix")
    in_results = (repo_root / "results").resolve() in output.resolve().parents
    if smoke and in_results:
        raise ValueError("TEST_ONLY output cannot be under registered results")
    if not smoke:
        if limit is not None:
            raise ValueError("--limit is forbidden at a registered lockbox output")
        expected = expected_registered_output(repo_root, family, start, stop)
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
        yield build_study_row(score, study_protocol_digest=metadata["protocol_digest"], spec_digest=metadata["spec_digest"], config_digest=metadata["config_digest"], source_commit=metadata["source_commit"], source_dirty=False, command_args=command_args, parent_artifacts={"spec": metadata["spec_digest"], "config": metadata["config_digest"], "generator": metadata["generator_digest"], "generator_manifest": metadata["generator_manifest_sha256"], "selected_protocol": metadata["selected_protocol_sha256"]}, family=family, instance_seed=key, campaign_seed=0, root_seed=root_seed, derived_seeds=seeds)


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
    validate_shard_request(family=family, start=start, stop=stop, output=destination, limit=limit, smoke=smoke, repo_root=repo_root)
    _require_unused_publication_targets(destination)
    assert_no_development_metric_dependency()
    selected = validate_lockbox_access(repo_root=repo_root)
    metadata = registered_metadata(repo_root)
    metadata.update({
        "selected_protocol_sha256": _sha256(repo_root / "results/spade-selected-protocol.json"),
        "selection_source_commit": selected["source_commit"],
    })
    resume_path = Path(f"{destination}.resume.json")
    rows: list[dict[str, object]] = []
    if resume_path.is_file():
        try:
            rows = validate_resume_payload(json.loads(resume_path.read_text()), metadata=metadata, family=family, start=start, stop=stop, raw_file=destination.name)
        except json.JSONDecodeError as exc:
            raise ValueError("resume checkpoint is invalid JSON") from exc
    completed_keys = {int(row["instance_seed"]) for row in rows}
    keys = range(start, min(stop, start + limit) if limit is not None else stop)
    for key in keys:
        if key not in completed_keys:
            rows.extend(_campaign_rows(family, key, selected, metadata, command_args))
            _atomic_json(resume_path, make_resume_payload(family=family, start=start, stop=stop, raw_file=destination.name, rows=rows, metadata=metadata))
    if len(rows) != (stop - start) * len(LOCKBOX_ARMS):
        raise RuntimeError("lockbox shard is incomplete; every requested key needs all three arms")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.", dir=destination.parent) as staging_name:
        staged_raw = Path(staging_name) / destination.name
        digest = write_jsonl_gzip(staged_raw, rows, protocol_digest=metadata["protocol_digest"])
        staged_sidecar = Path(f"{staged_raw}.sha256")
        manifest = {"schema": MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": start, "stop": stop, "sample_size": LOCKBOX_SAMPLE_SIZE, "expected_rows": (stop-start)*3, "row_count": len(rows), "complete": True, "raw_file": destination.name, "raw_sha256": digest, **metadata, "command_args": list(command_args)}
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


def merge_lockbox_manifests(manifest_paths: Sequence[str | Path], *, output: str | Path, metadata: Mapping[str, object]) -> dict[str, object]:
    """Hash and merge complete shard sidecars without loading outcome rows."""
    expected_metadata = {"protocol_digest", "spec_digest", "config_digest", "generator_digest", "generator_manifest_sha256", "source_commit", "source_dirty", "selected_protocol_sha256", "selection_source_commit"}
    if set(metadata) not in (expected_metadata, expected_metadata | {"command_args"}) or metadata["source_dirty"] is not False:
        raise ValueError("final lockbox manifest requires clean complete metadata")
    output_path = Path(output)
    shards: list[dict[str, object]] = []
    ranges: dict[str, list[tuple[int, int]]] = {family: [] for family in LOCKBOX_FAMILIES}
    for manifest_path in manifest_paths:
        try:
            shard = json.loads(Path(manifest_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("lockbox shard manifest is missing or invalid") from exc
        shard = validate_completed_shard_contract(shard)
        family, start, stop = shard["family"], shard["start"], shard["stop"]
        if any(shard.get(field) != metadata[field] for field in expected_metadata):
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
        if cursor != LOCKBOX_SAMPLE_SIZE:
            raise ValueError("lockbox manifests are incomplete")
    shards.sort(key=lambda item: (item["family"], item["start"], item["stop"]))
    final = {"schema": MERGED_MANIFEST_SCHEMA, "status": "COMPLETE", "sample_size": LOCKBOX_SAMPLE_SIZE, "raw_shards": shards, **{field: metadata[field] for field in expected_metadata}}
    if set(final) != MERGED_MANIFEST_FIELDS:
        raise RuntimeError("lockbox merged manifest schema drift")
    _atomic_json(output_path, final)
    return final


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=LOCKBOX_FAMILIES); parser.add_argument("--start", required=True, type=int); parser.add_argument("--stop", required=True, type=int); parser.add_argument("--out", required=True, type=Path); parser.add_argument("--limit", type=int); parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    manifest = run_lockbox_shard(family=args.family, start=args.start, stop=args.stop, output=args.out, limit=args.limit, smoke=args.smoke, command_args=tuple(argv or sys.argv[1:]))
    print(_canonical_json(manifest)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
