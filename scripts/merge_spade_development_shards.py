#!/usr/bin/env python3
"""Merge one complete registered SPADE development family deterministically."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import stat
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
_PARENT_LEDGER_SCHEMA = "boec-spade-development-parent-ledger-v1"
_PARENT_LEDGER_FLAG = "--parent-shard-ledger-json"
_PARENT_FIELDS = frozenset(
    {
        "start",
        "stop",
        "expected_rows",
        "row_count",
        "manifest_file",
        "manifest_sha256",
        "raw_file",
        "raw_sha256",
        "sidecar_file",
        "sidecar_sha256",
        "resume_file",
        "resume_sha256",
        "row_chain_head",
        "command_args",
        "provenance",
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lower_hex(value: object, name: str, *, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be {length} lowercase hexadecimal characters")
    return value


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


def _lexical_absolute(path: str | Path, *, base: Path, name: str) -> Path:
    supplied = Path(path)
    if ".." in supplied.parts:
        raise ValueError(f"{name} contains lexical traversal")
    candidate = supplied if supplied.is_absolute() else base / supplied
    if not candidate.is_absolute():
        raise ValueError(f"{name} is not an absolute lexical path")
    return candidate


def _reject_symlink_components(
    path: Path, *, name: str, allow_missing_tail: bool = False
) -> None:
    if not path.is_absolute():
        raise ValueError(f"{name} must be absolute before symlink validation")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            status = os.lstat(current)
        except FileNotFoundError:
            if allow_missing_tail:
                return
            raise ValueError(f"{name} is missing: {current}") from None
        if stat.S_ISLNK(status.st_mode):
            raise ValueError(f"{name} contains a symlink component: {current}")


def _require_regular_file(path: Path, name: str) -> None:
    _reject_symlink_components(path, name=name)
    status = os.lstat(path)
    if not stat.S_ISREG(status.st_mode):
        raise ValueError(f"{name} must be a regular file: {path}")


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


def parent_shard_ledger(command_args: object) -> dict[str, object]:
    """Decode and validate the authenticated parent ledger carried by merged rows."""
    if (
        not isinstance(command_args, list)
        or len(command_args) != 4
        or command_args[0] != "--family"
        or not isinstance(command_args[1], str)
        or command_args[1] not in development.DEVELOPMENT_FAMILIES
        or command_args[2] != _PARENT_LEDGER_FLAG
        or not isinstance(command_args[3], str)
    ):
        raise ValueError("merged command_args do not contain an explicit parent ledger")
    try:
        ledger = json.loads(command_args[3])
    except json.JSONDecodeError as exc:
        raise ValueError("parent-shard ledger is not JSON") from exc
    if command_args[3] != _canonical_json(ledger):
        raise ValueError("parent-shard ledger is not canonical JSON")
    if (
        not isinstance(ledger, dict)
        or set(ledger) != {"schema", "family", "parents"}
        or ledger["schema"] != _PARENT_LEDGER_SCHEMA
        or ledger["family"] != command_args[1]
        or not isinstance(ledger["parents"], list)
        or not ledger["parents"]
    ):
        raise ValueError("parent-shard ledger schema or family drift")
    cursor = 0
    common_provenance: dict[str, object] | None = None
    for index, value in enumerate(ledger["parents"]):
        if not isinstance(value, dict) or set(value) != _PARENT_FIELDS:
            raise ValueError(f"parent-shard ledger entry {index} fields drift")
        start = development._strict_int(value["start"], f"parent {index} start")
        stop = development._strict_int(
            value["stop"], f"parent {index} stop", minimum=1
        )
        if start != cursor or not start < stop <= development.CAMPAIGNS_PER_FAMILY:
            raise ValueError("parent-shard ledger ranges contain a gap or overlap")
        expected_rows = (stop - start) * len(development.DEVELOPMENT_ARM_IDS)
        if value["expected_rows"] != expected_rows or value["row_count"] != expected_rows:
            raise ValueError("parent-shard ledger row counts drift")
        raw_name = (
            f"spade-development-{ledger['family']}-{start:03d}-{stop:03d}.jsonl.gz"
        )
        expected_names = {
            "manifest_file": f"{raw_name}.manifest.json",
            "raw_file": raw_name,
            "sidecar_file": f"{raw_name}.sha256",
            "resume_file": f"{raw_name}.resume.json",
        }
        if any(value[field] != expected for field, expected in expected_names.items()):
            raise ValueError("parent-shard ledger filename identity drift")
        for field in (
            "manifest_sha256",
            "raw_sha256",
            "sidecar_sha256",
            "resume_sha256",
            "row_chain_head",
        ):
            _lower_hex(value[field], f"parent {index} {field}")
        if not isinstance(value["command_args"], list) or not all(
            isinstance(argument, str) for argument in value["command_args"]
        ):
            raise ValueError("parent-shard ledger command_args drift")
        provenance = value["provenance"]
        if (
            not isinstance(provenance, dict)
            or set(provenance) != set(_PROVENANCE_FIELDS)
            or provenance["source_dirty"] is not False
        ):
            raise ValueError("parent-shard ledger clean provenance drift")
        for field in _PROVENANCE_FIELDS:
            if field == "source_dirty":
                continue
            _lower_hex(
                provenance[field],
                f"parent {index} provenance {field}",
                length=40 if field == "source_commit" else 64,
            )
        if common_provenance is None:
            common_provenance = provenance
        elif provenance != common_provenance:
            raise ValueError("parent-shard ledger mixes provenance identities")
        cursor = stop
    if cursor != development.CAMPAIGNS_PER_FAMILY:
        raise ValueError("parent-shard ledger does not cover exact interval [0,50)")
    return ledger


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
    dict[str, object],
]:
    parsed, manifest_bytes = _read_canonical_mapping(
        manifest_path, "development manifest"
    )
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
    if _PARENT_LEDGER_FLAG in manifest["command_args"]:
        ledger = parent_shard_ledger(manifest["command_args"])
        if any(parent["provenance"] != provenance for parent in ledger["parents"]):
            raise ValueError("parent-shard ledger provenance differs from merged manifest")

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
    sidecar_bytes = sidecar_path.read_bytes()
    if sidecar_bytes != expected_sidecar:
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
    parent = _parent_record(
        manifest,
        manifest_path,
        manifest_bytes=manifest_bytes,
        raw_bytes=raw_bytes,
        sidecar_bytes=sidecar_bytes,
        resume_bytes=resume_bytes,
    )
    return manifest, rows, provenance, parent


def _parent_record(
    manifest: Mapping[str, object],
    manifest_path: Path,
    *,
    manifest_bytes: bytes,
    raw_bytes: bytes,
    sidecar_bytes: bytes,
    resume_bytes: bytes,
) -> dict[str, object]:
    raw_path = manifest_path.parent / str(manifest["raw_file"])
    sidecar_path = Path(f"{raw_path}.sha256")
    resume_path = manifest_path.parent / str(manifest["resume_file"])
    provenance = {field: manifest[field] for field in _PROVENANCE_FIELDS}
    return {
        "start": manifest["start"],
        "stop": manifest["stop"],
        "expected_rows": manifest["expected_rows"],
        "row_count": manifest["row_count"],
        "manifest_file": manifest_path.name,
        "manifest_sha256": _sha256(manifest_bytes),
        "raw_file": raw_path.name,
        "raw_sha256": _sha256(raw_bytes),
        "sidecar_file": sidecar_path.name,
        "sidecar_sha256": _sha256(sidecar_bytes),
        "resume_file": resume_path.name,
        "resume_sha256": _sha256(resume_bytes),
        "row_chain_head": manifest["row_chain_head"],
        "command_args": manifest["command_args"],
        "provenance": provenance,
    }


def _merged_command_args(
    family: str, parents: Sequence[Mapping[str, object]]
) -> tuple[str, ...]:
    ledger = {
        "schema": _PARENT_LEDGER_SCHEMA,
        "family": family,
        "parents": [dict(parent) for parent in parents],
    }
    return ("--family", family, _PARENT_LEDGER_FLAG, _canonical_json(ledger))


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
    working_directory = Path.cwd()
    root = _lexical_absolute(
        repo_root, base=working_directory, name="repository root"
    )
    _reject_symlink_components(root, name="repository root")
    destination = _lexical_absolute(
        output, base=root, name="merged output"
    )
    expected = root / "results" / (
        f"spade-development-{family}-000-050.jsonl.gz"
    )
    if destination != expected:
        raise ValueError(
            "merged output must remain inside the exact lexical repository/results "
            f"path {expected}"
        )
    _reject_symlink_components(
        destination.parent,
        name="merged output parent",
        allow_missing_tail=True,
    )
    targets = output_paths(destination)
    existing = [path for path in targets if path.exists() or path.is_symlink()]
    if existing:
        raise ValueError(f"merged development outputs are write-once; already exists: {existing[0]}")

    try:
        registered = development.registered_metadata(root)
        current_provenance = {
            field: registered[field] for field in _PROVENANCE_FIELDS
        }
    except KeyError as exc:
        raise ValueError("current registered metadata fields drift") from exc
    if current_provenance["source_dirty"] is not False:
        raise ValueError("development merge requires current clean registered metadata")

    records: list[
        tuple[int, int, Path, dict[str, object], list[dict[str, object]], dict[str, object]]
    ] = []
    environment: str | None = None
    seen_manifest_paths: set[Path] = set()
    for supplied in manifest_paths:
        path = _lexical_absolute(
            supplied, base=working_directory, name="development manifest path"
        )
        _reject_symlink_components(path, name="development manifest path")
        if path in seen_manifest_paths:
            raise ValueError("duplicate development manifest path")
        seen_manifest_paths.add(path)
        manifest, rows, shard_provenance, parent = _validate_input_shard(
            path,
            family=family,
            common_provenance=current_provenance,
        )
        if shard_provenance != current_provenance:
            raise ValueError("development shard provenance differs from current registration")
        for row in rows:
            encoded_environment = _canonical_json(row.get("environment"))
            if environment is None:
                environment = encoded_environment
            elif environment != encoded_environment:
                raise ValueError("development shards mix execution environments")
        records.append(
            (
                int(manifest["start"]),
                int(manifest["stop"]),
                path,
                manifest,
                rows,
                parent,
            )
        )

    records.sort(key=lambda item: (item[0], item[1]))
    cursor = 0
    for start, stop, _, _, _, _ in records:
        if start != cursor:
            raise ValueError("development shard ranges contain a gap or overlap")
        cursor = stop
    if cursor != development.CAMPAIGNS_PER_FAMILY:
        raise ValueError("development shard ranges do not cover exact interval [0,50)")
    parents = [parent for _, _, _, _, _, parent in records]
    command_args = _merged_command_args(family, parents)
    parent_shard_ledger(list(command_args))
    merged_rows = [
        {**row, "command_args": list(command_args)}
        for _, _, _, _, rows, _ in records
        for row in rows
    ]
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

    protocol_digest = str(current_provenance["study_protocol_digest"])
    raw_bytes = canonical_gzip_bytes(merged_rows, protocol_digest=protocol_digest)
    raw_digest = _sha256(raw_bytes)
    resume = development._resume_payload(
        family=family,
        start=0,
        stop=development.CAMPAIGNS_PER_FAMILY,
        raw_file=destination.name,
        rows=merged_rows,
        metadata=current_provenance,
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
        metadata=current_provenance,
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
    _reject_symlink_components(destination.parent, name="merged output parent")
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
