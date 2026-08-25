#!/usr/bin/env python3
"""Merge one complete registered SPADE development family deterministically."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec import spade_study as study  # noqa: E402
from scripts import run_spade_development as development  # noqa: E402


_PROVENANCE_FIELDS = (
    "study_protocol_digest",
    "spec_digest",
    "config_digest",
    "generator_digest",
    "generator_manifest_sha256",
    "source_commit",
    "source_dirty",
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_canonical_mapping(path: Path, name: str) -> tuple[dict[str, object], bytes]:
    _require_regular_file(path, name)
    data = path.read_bytes()
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    try:
        canonical = _canonical_bytes(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not finite canonical JSON") from exc
    if data != canonical:
        raise ValueError(f"{name} bytes are not canonical JSON")
    return payload, data


def _require_regular_file(path: Path, name: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file: {path}")


def output_paths(output: str | Path) -> tuple[Path, Path, Path, Path]:
    raw = Path(output)
    return (
        raw,
        Path(f"{raw}.sha256"),
        Path(f"{raw}.resume.json"),
        Path(f"{raw}.manifest.json"),
    )


def canonical_gzip_bytes(
    rows: Sequence[Mapping[str, object]], *, protocol_digest: str
) -> bytes:
    """Return the path-independent gzip bytes used by the registered writer."""
    validated = study._validate_rows(rows, protocol_digest)
    uncompressed = b"".join(
        (_canonical_json(row) + "\n").encode("utf-8") for row in validated
    )
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(uncompressed)
    return buffer.getvalue()


def _key_index(family: str, row: Mapping[str, object]) -> int:
    key = (row.get("instance_seed"), row.get("campaign_seed"))
    by_key = {
        development.development_campaign_key(family, index): index
        for index in range(development.CAMPAIGNS_PER_FAMILY)
    }
    if key not in by_key:
        raise ValueError("development row has an unregistered family key")
    return by_key[key]


def _validate_input_shard(
    manifest_path: Path,
    *,
    family: str,
    common_provenance: Mapping[str, object] | None,
) -> tuple[
    dict[str, object],
    list[dict[str, object]],
    dict[str, object],
]:
    parsed, _ = _read_canonical_mapping(manifest_path, "development manifest")
    manifest = development.validate_shard_manifest(parsed)
    if manifest["family"] != family:
        raise ValueError("development manifests mix family identities")
    start = int(manifest["start"])
    stop = int(manifest["stop"])
    raw_name = f"spade-development-{family}-{start:03d}-{stop:03d}.jsonl.gz"
    if manifest_path.name != f"{raw_name}.manifest.json":
        raise ValueError("development manifest path identity drift")
    if manifest["raw_file"] != raw_name:
        raise ValueError("development raw path identity drift")
    if manifest["resume_file"] != f"{raw_name}.resume.json":
        raise ValueError("development resume path identity drift")
    if manifest["execution_mode"] != "REGISTERED" or manifest["source_dirty"] is not False:
        raise ValueError("development merge requires clean REGISTERED shards")

    provenance = {field: manifest[field] for field in _PROVENANCE_FIELDS}
    if common_provenance is not None and provenance != dict(common_provenance):
        raise ValueError("development shards mix clean provenance identities")

    raw_path = manifest_path.parent / raw_name
    sidecar_path = Path(f"{raw_path}.sha256")
    resume_path = Path(f"{raw_path}.resume.json")
    for path, name in (
        (raw_path, "development raw shard"),
        (sidecar_path, "development SHA-256 sidecar"),
        (resume_path, "development resume checkpoint"),
    ):
        _require_regular_file(path, name)
    raw_bytes = raw_path.read_bytes()
    raw_digest = _sha256(raw_bytes)
    if raw_digest != manifest["raw_sha256"]:
        raise ValueError("development raw SHA-256 does not match manifest")
    expected_sidecar = f"{raw_digest}  {raw_name}\n".encode("ascii")
    if sidecar_path.read_bytes() != expected_sidecar:
        raise ValueError("development SHA-256 sidecar path or hash drift")

    resume, resume_bytes = _read_canonical_mapping(
        resume_path, "development resume checkpoint"
    )
    if _sha256(resume_bytes) != manifest["resume_sha256"]:
        raise ValueError("development resume SHA-256 does not match manifest")
    validated_resume = development.read_resume_checkpoint(
        resume_path,
        protocol_digest=str(manifest["study_protocol_digest"]),
    )
    expected_resume = {
        "family": family,
        "start": start,
        "stop": stop,
        "raw_file": raw_name,
        "execution_mode": "REGISTERED",
        **provenance,
        "command_args": manifest["command_args"],
        "row_count": manifest["row_count"],
        "row_chain_head": manifest["row_chain_head"],
        "expected_raw_sha256": raw_digest,
    }
    for field, expected in expected_resume.items():
        if validated_resume.get(field) != expected:
            raise ValueError(f"development resume {field} identity drift")

    rows = development.read_shard_rows(
        raw_path,
        str(manifest["study_protocol_digest"]),
    )
    if len(rows) != manifest["row_count"]:
        raise ValueError("development raw row count disagrees with manifest")
    if _canonical_json(rows) != _canonical_json(resume["rows"]):
        raise ValueError("development raw rows differ from resume checkpoint")
    if any(row.get("command_args") != manifest["command_args"] for row in rows):
        raise ValueError("development row command provenance differs from manifest")
    seen = development._validate_partial_rows(
        rows,
        family=family,
        start=start,
        stop=stop,
        metadata=provenance,
        smoke=False,
    )
    expected_seen = {
        (key_index, arm_id)
        for key_index in range(start, stop)
        for arm_id in development.DEVELOPMENT_ARM_IDS
    }
    if seen != expected_seen:
        raise ValueError("development shard lacks exactly 11 registered arms per key")
    expected_order = [
        (key_index, arm_id)
        for key_index in range(start, stop)
        for arm_id in development.DEVELOPMENT_ARM_IDS
    ]
    actual_order = [
        (_key_index(family, row), development._development_arm_id(row)) for row in rows
    ]
    if actual_order != expected_order:
        raise ValueError("development shard rows are not in canonical key/arm order")
    return manifest, rows, provenance


def _stable_command_args(
    family: str, manifests: Sequence[tuple[int, int, Path]]
) -> tuple[str, ...]:
    values: list[str] = ["--family", family]
    for _, _, path in manifests:
        values.extend(("--manifest", path.name))
    return tuple(values)


def _write_staged(path: Path, data: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def merge_development_shards(
    manifest_paths: Sequence[str | Path],
    *,
    family: str,
    output: str | Path,
    repo_root: str | Path = ROOT,
) -> dict[str, object]:
    """Validate and merge disjoint shards for one registered development family."""
    if family not in development.DEVELOPMENT_FAMILIES:
        raise ValueError(f"family must be one of {development.DEVELOPMENT_FAMILIES}")
    if not manifest_paths:
        raise ValueError("at least one development manifest is required")
    root = Path(os.path.abspath(repo_root))
    destination = Path(os.path.abspath(output))
    expected = Path(
        os.path.abspath(development.expected_registered_output(root, family, 0, 50))
    )
    if destination != expected:
        raise ValueError(f"merged output must be the exact canonical path {expected}")
    targets = output_paths(destination)
    existing = [path for path in targets if path.exists() or path.is_symlink()]
    if existing:
        raise ValueError(f"merged development outputs are write-once; already exists: {existing[0]}")

    records: list[tuple[int, int, Path, list[dict[str, object]]]] = []
    provenance: dict[str, object] | None = None
    environment: str | None = None
    seen_manifest_paths: set[Path] = set()
    for supplied in manifest_paths:
        path = Path(os.path.abspath(supplied))
        if path in seen_manifest_paths:
            raise ValueError("duplicate development manifest path")
        seen_manifest_paths.add(path)
        manifest, rows, shard_provenance = _validate_input_shard(
            path,
            family=family,
            common_provenance=provenance,
        )
        if provenance is None:
            provenance = shard_provenance
        for row in rows:
            encoded_environment = _canonical_json(row.get("environment"))
            if environment is None:
                environment = encoded_environment
            elif environment != encoded_environment:
                raise ValueError("development shards mix execution environments")
        records.append((int(manifest["start"]), int(manifest["stop"]), path, rows))

    records.sort(key=lambda item: (item[0], item[1]))
    cursor = 0
    for start, stop, _, _ in records:
        if start != cursor:
            raise ValueError("development shard ranges contain a gap or overlap")
        cursor = stop
    if cursor != development.CAMPAIGNS_PER_FAMILY:
        raise ValueError("development shard ranges do not cover exact interval [0,50)")
    assert provenance is not None

    merged_rows = [row for _, _, _, rows in records for row in rows]
    expected_identities = {
        (key_index, arm_id)
        for key_index in range(development.CAMPAIGNS_PER_FAMILY)
        for arm_id in development.DEVELOPMENT_ARM_IDS
    }
    identities = [
        (_key_index(family, row), development._development_arm_id(row))
        for row in merged_rows
    ]
    if len(identities) != len(expected_identities) or set(identities) != expected_identities:
        raise ValueError("merged development grid has duplicates, gaps, or missing arms")

    protocol_digest = str(provenance["study_protocol_digest"])
    raw_bytes = canonical_gzip_bytes(merged_rows, protocol_digest=protocol_digest)
    raw_digest = _sha256(raw_bytes)
    ordered_manifests = [(start, stop, path) for start, stop, path, _ in records]
    command_args = _stable_command_args(family, ordered_manifests)
    resume = development._resume_payload(
        family=family,
        start=0,
        stop=development.CAMPAIGNS_PER_FAMILY,
        raw_file=destination.name,
        rows=merged_rows,
        metadata=provenance,
        smoke=False,
        command_args=command_args,
        expected_raw_sha256=raw_digest,
    )
    resume_bytes = _canonical_bytes(resume)
    manifest = development.make_shard_manifest(
        family=family,
        start=0,
        stop=development.CAMPAIGNS_PER_FAMILY,
        row_count=len(merged_rows),
        raw_file=destination.name,
        raw_sha256=raw_digest,
        resume_file=f"{destination.name}.resume.json",
        resume_sha256=_sha256(resume_bytes),
        row_chain_head=str(resume["row_chain_head"]),
        metadata=provenance,
        smoke=False,
        complete=True,
        command_args=command_args,
    )
    payloads = (
        raw_bytes,
        f"{raw_digest}  {destination.name}\n".encode("ascii"),
        resume_bytes,
        _canonical_bytes(manifest),
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    if any(path.exists() or path.is_symlink() for path in targets):
        raise ValueError("merged development outputs are write-once; target appeared during validation")
    staged: list[Path] = []
    installed: list[Path] = []
    try:
        staged = [_write_staged(path, data) for path, data in zip(targets, payloads)]
        for temporary, path in zip(staged, targets):
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise ValueError(
                    "merged development output appeared during write-once promotion"
                ) from exc
            temporary.unlink()
            installed.append(path)
        staged.clear()
    except BaseException:
        for temporary in staged:
            temporary.unlink(missing_ok=True)
        for path in installed:
            path.unlink(missing_ok=True)
        raise
    return manifest


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=development.DEVELOPMENT_FAMILIES)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    output = args.out or development.expected_registered_output(
        ROOT, args.family, 0, development.CAMPAIGNS_PER_FAMILY
    )
    manifest = merge_development_shards(
        args.manifest,
        family=args.family,
        output=output,
        repo_root=ROOT,
    )
    print(_canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
