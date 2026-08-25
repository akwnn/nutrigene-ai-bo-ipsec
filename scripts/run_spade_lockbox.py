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
from boec.spade_study import SealedOracleHarness, build_study_row, controlled_tau, score_campaign, write_jsonl_gzip  # noqa: E402
from boec.torch_oracle import TorchEvaluator  # noqa: E402


LOCKBOX_ARMS = ("spade", "sobol48", "qlognei48")
LOCKBOX_SAMPLE_SIZE = 350
STUDY_ROOT_SEED = 2_026_08_25
SIGMA_REL, SIGMA_ADD, GAMMA, ALPHA, Q_TAU = .10, .01, .95, .95, .75
MANIFEST_SCHEMA = "boec-spade-lockbox-shard-v1"
_CONFIG_PATH = Path("configs/experiment/spade-joint.yaml")
_SPEC_PATH = Path("docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md")
_GENERATOR_PATH = Path("src/boec/lockbox_oracles.py")
_GENERATOR_MANIFEST = Path("results/spade-lockbox-generator-manifest.json")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return [dict(row) for row in rows]


def _allowed_generated_path(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return name.startswith("spade-lockbox-") or name == "spade-selected-protocol.json"


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
    metadata = {"study_protocol_digest": protocol_digest, "spec_digest": _sha256(spec_path), "config_digest": _sha256(config_path), "generator_digest": _sha256(generator_path)}
    if metadata["spec_digest"] != digests.get("spec_sha256") or metadata["generator_digest"] != digests.get("lockbox_oracles_source_sha256"):
        raise ValueError("frozen source digest mismatch")
    metadata["source_commit"], metadata["source_dirty"] = git_state(repo_root)
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


def _load_generator_freeze(repo_root: Path) -> dict[str, object]:
    path = repo_root / _GENERATOR_MANIFEST
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("frozen lockbox generator manifest is missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("status") != "FROZEN_UNOPENED" or tuple(manifest.get("families", ())) != LOCKBOX_FAMILIES:
        raise ValueError("lockbox generator manifest must remain FROZEN_UNOPENED")
    return manifest


def validate_lockbox_access(*, repo_root: Path = ROOT, selected_path: Path | None = None) -> dict[str, object]:
    path = selected_path or repo_root / "results/spade-selected-protocol.json"
    if not path.is_file():
        raise ValueError("selected protocol artifact is missing")
    try:
        selected = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError("selected protocol artifact is invalid JSON") from exc
    if not isinstance(selected, dict) or selected.get("status") != "SELECTED":
        raise ValueError("lockbox requires a SELECTED protocol, never NO_SELECTION")
    metadata = registered_metadata(repo_root)
    _, dirty = git_state(repo_root)
    if dirty or metadata.get("source_dirty"):
        raise ValueError("lockbox access refuses a dirty source tree")
    for field in ("study_protocol_digest", "spec_digest", "config_digest", "generator_digest"):
        if selected.get(field) != metadata.get(field):
            raise ValueError(f"selected protocol {field} digest mismatch")
    if selected.get("selected_template_protocol_digest") != _selected_template_digest(selected):
        raise ValueError("selected protocol canonical configuration digest mismatch")
    selected_hash = _committed_file_hash(repo_root, "HEAD")
    if selected_hash != _sha256(path):
        raise ValueError("selected protocol must be committed at HEAD before lockbox access")
    freeze = _load_generator_freeze(repo_root)
    selected_commit = str(selected.get("source_commit", ""))
    freeze_commit = str(freeze.get("freeze_parent_commit", ""))
    if not _is_ancestor(repo_root, freeze_commit, selected_commit):
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


def expected_registered_output(repo_root: Path, family: str, start: int, stop: int) -> Path:
    return repo_root / "results" / f"spade-lockbox-{family}-{start:03d}-{stop:03d}.jsonl.gz"


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
        yield build_study_row(score, study_protocol_digest=metadata["study_protocol_digest"], spec_digest=metadata["spec_digest"], config_digest=metadata["config_digest"], source_commit=metadata["source_commit"], source_dirty=False, command_args=command_args, parent_artifacts={"spec": metadata["spec_digest"], "config": metadata["config_digest"], "generator": metadata["generator_digest"]}, family=family, instance_seed=key, campaign_seed=0, root_seed=root_seed, derived_seeds=seeds)


def run_lockbox_shard(*, family: str, start: int, stop: int, output: str | Path, limit: int | None = None, smoke: bool = False, repo_root: Path = ROOT, command_args: Sequence[str] = ()) -> dict[str, object]:
    destination = Path(output)
    validate_shard_request(family=family, start=start, stop=stop, output=destination, limit=limit, smoke=smoke, repo_root=repo_root)
    assert_no_development_metric_dependency()
    selected = validate_lockbox_access(repo_root=repo_root)
    metadata = registered_metadata(repo_root)
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
    staging = destination.with_name(f".{destination.name}.promotion")
    digest = write_jsonl_gzip(staging, rows, protocol_digest=metadata["study_protocol_digest"])
    destination.parent.mkdir(parents=True, exist_ok=True); os.replace(staging, destination)
    Path(f"{staging}.sha256").unlink(missing_ok=True)
    Path(f"{destination}.sha256").write_text(f"{digest}  {destination.name}\n")
    manifest = {"schema": MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": start, "stop": stop, "sample_size": LOCKBOX_SAMPLE_SIZE, "expected_rows": (stop-start)*3, "row_count": len(rows), "complete": True, "raw_file": destination.name, "raw_sha256": digest, **metadata, "selected_protocol_sha256": _sha256(repo_root / "results/spade-selected-protocol.json"), "command_args": list(command_args)}
    _atomic_json(Path(f"{destination}.manifest.json"), manifest)
    return manifest


def merge_lockbox_manifests(manifest_paths: Sequence[str | Path], *, output: str | Path, metadata: Mapping[str, object]) -> dict[str, object]:
    """Hash and merge complete shard sidecars without loading outcome rows."""
    expected_metadata = {"study_protocol_digest", "spec_digest", "config_digest", "generator_digest", "source_commit", "source_dirty"}
    if set(metadata) != expected_metadata or metadata["source_dirty"] is not False:
        raise ValueError("final lockbox manifest requires clean complete metadata")
    output_path = Path(output)
    shards: list[dict[str, object]] = []
    ranges: dict[str, list[tuple[int, int]]] = {family: [] for family in LOCKBOX_FAMILIES}
    for manifest_path in manifest_paths:
        try:
            shard = json.loads(Path(manifest_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("lockbox shard manifest is missing or invalid") from exc
        required = {"schema", "status", "family", "start", "stop", "sample_size", "expected_rows", "row_count", "complete", "raw_file", "raw_sha256", *expected_metadata}
        if not isinstance(shard, dict) or set(shard) != required or shard.get("schema") != MANIFEST_SCHEMA or shard.get("status") != "COMPLETE" or shard.get("complete") is not True:
            raise ValueError("lockbox shard manifest schema or completion drift")
        family, start, stop = shard.get("family"), shard.get("start"), shard.get("stop")
        if family not in LOCKBOX_FAMILIES or isinstance(start, bool) or isinstance(stop, bool) or not isinstance(start, int) or not isinstance(stop, int) or not 0 <= start < stop <= LOCKBOX_SAMPLE_SIZE:
            raise ValueError("lockbox shard has unregistered range")
        if shard.get("sample_size") != LOCKBOX_SAMPLE_SIZE or shard.get("expected_rows") != (stop - start) * len(LOCKBOX_ARMS) or shard.get("row_count") != shard.get("expected_rows"):
            raise ValueError("lockbox shard row count or sample size drift")
        if any(shard.get(field) != metadata[field] for field in expected_metadata):
            raise ValueError("lockbox shard provenance drift")
        raw_file = shard.get("raw_file")
        if not isinstance(raw_file, str) or Path(raw_file).name != raw_file:
            raise ValueError("lockbox shard raw filename drift")
        raw_path = Path(manifest_path).parent / raw_file
        sidecar = Path(f"{raw_path}.sha256")
        if not raw_path.is_file() or not sidecar.is_file() or shard.get("raw_sha256") != _sha256(raw_path):
            raise ValueError("lockbox shard raw hash mismatch")
        if sidecar.read_text(encoding="ascii").split() != [shard["raw_sha256"], raw_file]:
            raise ValueError("lockbox shard raw SHA-256 sidecar mismatch")
        ranges[family].append((start, stop))
        shards.append({"family": family, "start": start, "stop": stop, "raw_file": raw_file, "raw_sha256": shard["raw_sha256"], "manifest_file": Path(manifest_path).name, "manifest_sha256": _sha256(Path(manifest_path))})
    for family, intervals in ranges.items():
        cursor = 0
        for start, stop in sorted(intervals):
            if start != cursor:
                raise ValueError("lockbox manifests have missing or overlapping ranges")
            cursor = stop
        if cursor != LOCKBOX_SAMPLE_SIZE:
            raise ValueError("lockbox manifests are incomplete")
    shards.sort(key=lambda item: (item["family"], item["start"], item["stop"]))
    final = {"schema": "boec-spade-lockbox-manifest-v1", "status": "COMPLETE", "sample_size": LOCKBOX_SAMPLE_SIZE, "raw_shards": shards, **dict(metadata)}
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
