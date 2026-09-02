from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from boec.spade_study import write_jsonl_gzip
from scripts import plan_spade_lockbox_power as planner
from scripts import run_spade_development as development
from scripts import select_spade_protocol as selector
from tests.test_spade_development import _row


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
GENERATOR_MANIFEST = "b" * 64
SOURCE = "1" * 40
POWER_DESIGN = "2" * 64
POWER_ENGINE = "3" * 64
POWER_PLANNER = "4" * 64


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _metadata() -> dict[str, object]:
    return {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE,
        "source_dirty": False,
    }


def _registered_metadata() -> dict[str, object]:
    return {
        **_metadata(),
        "power_design_digest": POWER_DESIGN,
        "power_engine_digest": POWER_ENGINE,
        "power_planner_digest": POWER_PLANNER,
    }


def _family_rows(family: str) -> list[dict[str, object]]:
    return [
        _row(family, key_index, arm_id)
        for key_index in range(development.CAMPAIGNS_PER_FAMILY)
        for arm_id in development.DEVELOPMENT_ARM_IDS
    ]


def _write_shard(
    directory: Path,
    family: str,
    start: int,
    stop: int,
    rows: list[dict[str, object]],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / (
        f"spade-development-{family}-{start:03d}-{stop:03d}.jsonl.gz"
    )
    raw_hash = write_jsonl_gzip(raw, rows, protocol_digest=PROTOCOL)
    resume = development._resume_payload(
        family=family,
        start=start,
        stop=stop,
        raw_file=raw.name,
        rows=rows,
        metadata=_metadata(),
        smoke=False,
        command_args=("--family", family),
        expected_raw_sha256=raw_hash,
    )
    resume_path = development.resume_checkpoint_path(raw)
    resume_hash = development._write_resume_checkpoint(resume_path, resume)
    manifest = development.make_shard_manifest(
        family=family,
        start=start,
        stop=stop,
        row_count=len(rows),
        raw_file=raw.name,
        raw_sha256=raw_hash,
        resume_file=resume_path.name,
        resume_sha256=resume_hash,
        row_chain_head=str(resume["row_chain_head"]),
        metadata=_metadata(),
        smoke=False,
        complete=True,
        command_args=("--family", family),
    )
    manifest_path = Path(f"{raw}.manifest.json")
    manifest_path.write_bytes(_canonical_bytes(manifest))
    return manifest_path


def _split_family(tmp_path: Path, family: str) -> list[Path]:
    rows = _family_rows(family)
    return [
        _write_shard(tmp_path, family, 25, 50, rows[25 * 11 :]),
        _write_shard(tmp_path, family, 0, 25, rows[: 25 * 11]),
    ]


def _import_merger():
    from scripts import merge_spade_development_shards as merger

    return merger


@pytest.fixture(autouse=True)
def _freeze_current_registered_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    merger = _import_merger()
    monkeypatch.setattr(
        merger.development,
        "registered_metadata",
        lambda _root: _registered_metadata(),
    )


def test_merge_emits_deterministic_canonical_artifacts_accepted_unchanged(
    tmp_path: Path,
) -> None:
    merger = _import_merger()
    results = tmp_path / "results"
    results.mkdir()
    verified: list[planner._VerifiedDevelopmentShard] = []
    selector_manifests: list[Path] = []

    for family in development.DEVELOPMENT_FAMILIES:
        inputs = _split_family(tmp_path / family, family)
        output = results / f"spade-development-{family}-000-050.jsonl.gz"
        manifest = merger.merge_development_shards(
            inputs,
            family=family,
            output=output,
            repo_root=tmp_path,
        )
        manifest_path = Path(f"{output}.manifest.json")
        selector_manifests.append(manifest_path)
        assert manifest["status"] == "COMPLETE"
        assert manifest["row_count"] == 550
        resume = json.loads(Path(f"{output}.resume.json").read_bytes())
        output_rows = development.read_shard_rows(output, PROTOCOL)
        assert resume["command_args"] == manifest["command_args"]
        assert all(row["command_args"] == manifest["command_args"] for row in output_rows)
        ledger = merger.parent_shard_ledger(manifest["command_args"])
        assert ledger["schema"] == "boec-spade-development-parent-ledger-v1"
        assert [(item["start"], item["stop"]) for item in ledger["parents"]] == [
            (0, 25),
            (25, 50),
        ]
        for parent in ledger["parents"]:
            parent_manifest = next(
                path for path in inputs if path.name == parent["manifest_file"]
            )
            raw = Path(str(parent_manifest).removesuffix(".manifest.json"))
            assert parent["manifest_sha256"] == hashlib.sha256(
                parent_manifest.read_bytes()
            ).hexdigest()
            assert parent["raw_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
            assert parent["sidecar_sha256"] == hashlib.sha256(
                Path(f"{raw}.sha256").read_bytes()
            ).hexdigest()
            assert parent["resume_sha256"] == hashlib.sha256(
                Path(f"{raw}.resume.json").read_bytes()
            ).hexdigest()
            assert parent["command_args"] == ["--family", family]
            assert parent["provenance"] == _metadata()
        revalidated, revalidated_rows, _, _ = merger._validate_input_shard(
            manifest_path,
            family=family,
            common_provenance=_metadata(),
        )
        assert revalidated == manifest
        assert revalidated_rows == output_rows
        expected_rows = [
            {**row, "command_args": manifest["command_args"]}
            for row in _family_rows(family)
        ]
        assert output.read_bytes() == merger.canonical_gzip_bytes(
            expected_rows, protocol_digest=PROTOCOL
        )
        assert output.with_suffix(output.suffix + ".sha256").read_bytes() == (
            f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}\n"
        ).encode("ascii")
        verified.append(
            planner._VerifiedDevelopmentShard(
                family=family,
                manifest_name=manifest_path.name,
                manifest_bytes=manifest_path.read_bytes(),
                raw_name=output.name,
                raw_bytes=output.read_bytes(),
                resume_name=f"{output.name}.resume.json",
                resume_bytes=Path(f"{output}.resume.json").read_bytes(),
                sidecar_name=f"{output.name}.sha256",
                sidecar_bytes=Path(f"{output}.sha256").read_bytes(),
            )
        )

    rows, _ = selector._load_complete_shards(
        selector_manifests,
        metadata=_metadata(),
        source_commit=SOURCE,
    )
    assert len(rows) == 2_750
    powered_rows, artifacts = planner._load_verified_development_shards(
        verified,
        metadata=_metadata(),
        source_commit=SOURCE,
    )
    assert len(powered_rows) == 2_750
    assert len(artifacts) == 5


@pytest.mark.parametrize("failure", ["gap", "overlap", "duplicate", "environment"])
def test_merge_rejects_invalid_grids_before_writing(
    tmp_path: Path, failure: str
) -> None:
    merger = _import_merger()
    family = "ackley"
    rows = _family_rows(family)
    first = _write_shard(tmp_path, family, 0, 25, rows[: 25 * 11])
    if failure == "gap":
        second = _write_shard(tmp_path, family, 26, 50, rows[26 * 11 :])
    elif failure == "overlap":
        second = _write_shard(tmp_path, family, 24, 50, rows[24 * 11 :])
    elif failure == "duplicate":
        second = _write_shard(tmp_path, family, 25, 50, rows[25 * 11 :])
    else:
        changed = copy.deepcopy(rows[25 * 11 :])
        changed[0]["environment"]["platform"] = "drifted"
        second = _write_shard(tmp_path, family, 25, 50, changed)

    output = tmp_path / "results" / "spade-development-ackley-000-050.jsonl.gz"
    supplied = [second, first, first] if failure == "duplicate" else [second, first]
    with pytest.raises(ValueError):
        merger.merge_development_shards(
            supplied,
            family=family,
            output=output,
            repo_root=tmp_path,
        )
    assert not output.exists()
    assert not Path(f"{output}.sha256").exists()
    assert not Path(f"{output}.resume.json").exists()
    assert not Path(f"{output}.manifest.json").exists()


def test_merge_rejects_hash_path_or_resume_drift_and_is_write_once(
    tmp_path: Path,
) -> None:
    merger = _import_merger()
    family = "ackley"
    inputs = _split_family(tmp_path, family)
    output = tmp_path / "results" / "spade-development-ackley-000-050.jsonl.gz"

    sidecar = Path(str(inputs[0]).removesuffix(".manifest.json") + ".sha256")
    sidecar.write_text("0" * 64 + "  wrong.jsonl.gz\n", encoding="ascii")
    with pytest.raises(ValueError, match="SHA-256|sidecar"):
        merger.merge_development_shards(
            inputs, family=family, output=output, repo_root=tmp_path
        )
    assert not output.exists()

    inputs = _split_family(tmp_path / "fresh", family)
    merger.merge_development_shards(
        inputs, family=family, output=output, repo_root=tmp_path
    )
    before = {path: path.read_bytes() for path in merger.output_paths(output)}
    with pytest.raises(ValueError, match="write-once|already exists"):
        merger.merge_development_shards(
            inputs, family=family, output=output, repo_root=tmp_path
        )
    assert before == {path: path.read_bytes() for path in merger.output_paths(output)}


def test_merge_never_overwrites_a_target_that_appears_during_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    merger = _import_merger()
    inputs = _split_family(tmp_path, "ackley")
    output = tmp_path / "results" / "spade-development-ackley-000-050.jsonl.gz"
    real_link = merger.os.link
    raced = False

    def race_link(source: str | Path, destination: str | Path) -> None:
        nonlocal raced
        if not raced:
            raced = True
            Path(destination).write_bytes(b"pre-existing")
        real_link(source, destination)

    monkeypatch.setattr(merger.os, "link", race_link)
    with pytest.raises(ValueError, match="appeared|write-once"):
        merger.merge_development_shards(
            inputs,
            family="ackley",
            output=output,
            repo_root=tmp_path,
        )
    assert output.read_bytes() == b"pre-existing"
    assert not Path(f"{output}.sha256").exists()
    assert not Path(f"{output}.resume.json").exists()
    assert not Path(f"{output}.manifest.json").exists()


def test_merge_rejects_symlinked_input_parent_and_lexical_output_escape(
    tmp_path: Path,
) -> None:
    merger = _import_merger()
    real_inputs = tmp_path / "real-inputs"
    inputs = _split_family(real_inputs, "ackley")
    linked_inputs = tmp_path / "linked-inputs"
    linked_inputs.symlink_to(real_inputs, target_is_directory=True)
    supplied = [linked_inputs / path.name for path in inputs]
    output = tmp_path / "results" / "spade-development-ackley-000-050.jsonl.gz"

    with pytest.raises(ValueError, match="symlink"):
        merger.merge_development_shards(
            supplied,
            family="ackley",
            output=output,
            repo_root=tmp_path,
        )
    assert not output.exists()

    escaped_lexically = (
        tmp_path
        / "results"
        / "not-a-real-directory"
        / ".."
        / "spade-development-ackley-000-050.jsonl.gz"
    )
    with pytest.raises(ValueError, match="lexical|traversal|results"):
        merger.merge_development_shards(
            inputs,
            family="ackley",
            output=escaped_lexically,
            repo_root=tmp_path,
        )
    assert not output.exists()


def test_merge_rejects_symlinked_repo_component_before_writing(
    tmp_path: Path,
) -> None:
    merger = _import_merger()
    real_repo = tmp_path / "real-repo"
    inputs = _split_family(tmp_path / "inputs", "ackley")
    real_repo.mkdir()
    linked_repo = tmp_path / "linked-repo"
    linked_repo.symlink_to(real_repo, target_is_directory=True)
    output = linked_repo / "results" / "spade-development-ackley-000-050.jsonl.gz"

    with pytest.raises(ValueError, match="symlink"):
        merger.merge_development_shards(
            inputs,
            family="ackley",
            output=output,
            repo_root=linked_repo,
        )
    assert not (real_repo / "results").exists()


@pytest.mark.parametrize("drift", ["source_commit", "source_dirty", "config_digest"])
def test_merge_preflights_current_clean_registered_metadata_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    merger = _import_merger()
    inputs = _split_family(tmp_path / "inputs", "ackley")
    current = _registered_metadata()
    if drift == "source_dirty":
        current[drift] = True
    else:
        current[drift] = ("9" * 40) if drift == "source_commit" else ("9" * 64)
    monkeypatch.setattr(
        merger.development,
        "registered_metadata",
        lambda _root: current,
    )
    output = tmp_path / "results" / "spade-development-ackley-000-050.jsonl.gz"

    with pytest.raises(ValueError, match="current|registered|clean|provenance"):
        merger.merge_development_shards(
            inputs,
            family="ackley",
            output=output,
            repo_root=tmp_path,
        )
    assert not (tmp_path / "results").exists()


def test_parent_ledger_rejects_noncanonical_or_malformed_authentication(
    tmp_path: Path,
) -> None:
    merger = _import_merger()
    parents = []
    for path in sorted(_split_family(tmp_path / "inputs", "ackley")):
        _, _, _, parent = merger._validate_input_shard(
            path,
            family="ackley",
            common_provenance=_metadata(),
        )
        parents.append(parent)
    parents.sort(key=lambda item: item["start"])
    valid = list(merger._merged_command_args("ackley", parents))
    assert merger.parent_shard_ledger(valid)["parents"] == parents

    malformed = json.loads(valid[3])
    malformed["parents"][0]["raw_sha256"] = "0" * 63
    with pytest.raises(ValueError, match="hexadecimal"):
        merger.parent_shard_ledger([*valid[:3], merger._canonical_json(malformed)])

    noncanonical = json.dumps(json.loads(valid[3]), indent=2)
    with pytest.raises(ValueError, match="canonical"):
        merger.parent_shard_ledger([*valid[:3], noncanonical])
