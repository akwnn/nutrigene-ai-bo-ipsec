from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

import pytest

from boec.spade import SpadeConfig
from boec.spade_power import DEVELOPMENT_FAMILIES, validate_power_plan_payload
from scripts import plan_spade_lockbox_power as planner
from scripts import run_spade_development as development
from scripts import select_spade_protocol as selector


CURRENT = "c" * 40
SOURCE = "1" * 40
PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
GENERATOR_MANIFEST = "b" * 64
POWER_DESIGN = "2" * 64
POWER_ENGINE = "3" * 64
POWER_PLANNER = "4" * 64
SELECTED = "spade-o44-fixed_hybrid"


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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata() -> dict[str, object]:
    return {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "power_design_digest": POWER_DESIGN,
        "power_engine_digest": POWER_ENGINE,
        "power_planner_digest": POWER_PLANNER,
        "source_commit": CURRENT,
        "source_dirty": False,
    }


def _registered_manifest(
    family: str,
    *,
    raw_file: str | None = None,
    resume_file: str | None = None,
) -> dict[str, object]:
    expected_raw = f"spade-development-{family}-000-050.jsonl.gz"
    return development.make_shard_manifest(
        family=family,
        start=0,
        stop=50,
        row_count=50 * len(development.DEVELOPMENT_ARM_IDS),
        raw_file=raw_file or expected_raw,
        raw_sha256=_sha256(f"raw:{family}".encode("ascii")),
        resume_file=resume_file or f"{expected_raw}.resume.json",
        resume_sha256=_sha256(f"resume:{family}".encode("ascii")),
        row_chain_head=_sha256(f"chain:{family}".encode("ascii")),
        metadata={**_metadata(), "source_commit": SOURCE},
        smoke=False,
        complete=True,
        command_args=(),
    )


def _artifacts() -> list[dict[str, object]]:
    artifacts = []
    for family in sorted(DEVELOPMENT_FAMILIES):
        raw_file = f"spade-development-{family}-000-050.jsonl.gz"
        manifest_file = f"{raw_file}.manifest.json"
        resume_file = f"{raw_file}.resume.json"
        artifacts.append(
            {
            "family": family,
            "start": 0,
            "stop": 50,
            "raw_file": raw_file,
            "raw_sha256": _sha256(f"raw:{family}".encode("ascii")),
            "manifest_file": manifest_file,
            "manifest_sha256": _sha256(f"manifest:{family}".encode("ascii")),
            "resume_file": resume_file,
            "resume_sha256": _sha256(f"resume:{family}".encode("ascii")),
            "row_chain_head": _sha256(f"chain:{family}".encode("ascii")),
            }
        )
    return artifacts


def _development_artifact_bytes(
    path: Path, artifacts: list[dict[str, object]]
) -> bytes:
    for artifact in artifacts:
        family = str(artifact["family"])
        if path.name == artifact["raw_file"]:
            return f"raw:{family}".encode("ascii")
        if path.name == artifact["manifest_file"]:
            return f"manifest:{family}".encode("ascii")
        if path.name == artifact["resume_file"]:
            return f"resume:{family}".encode("ascii")
        if path.name == f"{artifact['raw_file']}.sha256":
            return f"{artifact['raw_sha256']}  {artifact['raw_file']}\n".encode("ascii")
    raise AssertionError(f"unexpected committed fixture path {path}")


def _row(family: str, key_index: int, arm_id: str) -> dict[str, object]:
    instance_seed, campaign_seed = development.development_campaign_key(
        family, key_index
    )
    root_seed = 17 + key_index
    if arm_id.startswith("spade-"):
        opening, policy = development.candidate_spec(arm_id)
        arm = "spade"
        protocol = SpadeConfig(
            opening=opening, policy=policy, root_seed=root_seed
        ).protocol_digest
        map_loss = 0.08 + key_index / 100_000
        regret = 0.09 + key_index / 100_000
    else:
        arm = arm_id
        protocol = development.comparator_protocol_digest(
            arm_id, root_seed=root_seed
        )
        map_loss = 0.10 + key_index / 100_000
        regret = 0.10 + key_index / 100_000
    return {
        "family": family,
        "instance_seed": instance_seed,
        "campaign_seed": campaign_seed,
        "root_seed": root_seed,
        "arm": arm,
        "arm_protocol_digest": protocol,
        "scores": {"map_loss": map_loss, "regret_rule_p": regret},
    }


def _rows() -> list[dict[str, object]]:
    return [
        _row(family, key_index, arm)
        for family in DEVELOPMENT_FAMILIES
        for key_index in range(50)
        for arm in (SELECTED, "sobol48", "qlognei48")
    ]


def _analysis() -> dict[str, object]:
    folds = [
        {
            "held_out_family": family,
            "training_families": [
                other for other in DEVELOPMENT_FAMILIES if other != family
            ],
            "status": "SELECTED",
            "selected_candidate": SELECTED,
            "training_selection_trace": {"selected": SELECTED},
            "held_out_metrics": {"n_campaigns": 50},
            "rationale": "held out",
        }
        for family in DEVELOPMENT_FAMILIES
    ]
    trace = {
        "rule": "unanimous_lofo_consensus",
        "fold_winners": [
            {
                "held_out_family": family,
                "winner": SELECTED,
                "status": "SELECTED",
            }
            for family in DEVELOPMENT_FAMILIES
        ],
        "unanimous": True,
        "selected_candidate": SELECTED,
        "rationale": "unanimous",
        "all_five_refit_diagnostic": {"status": "SELECTED"},
    }
    return {
        "schema": selector.ANALYSIS_SCHEMA,
        "status": "SELECTED",
        "selected_candidate": SELECTED,
        "selection_method": "unanimous_nested_leave_one_family_out_consensus",
        "paired_upper_bound_method": selector.PAIRED_BOUND_METHOD,
        "grid": {"row_count": 2750},
        "candidates": {SELECTED: {}},
        "lofo_folds": folds,
        "selection_trace": trace,
    }


def _selected(analysis: dict[str, object], artifacts: list[dict[str, object]]) -> dict[str, object]:
    canonical_config_json = SpadeConfig(
        opening=44, policy="fixed_hybrid", root_seed=0
    ).canonical_json
    analysis_bytes = _canonical_bytes(analysis)
    trace_json = json.dumps(
        analysis["selection_trace"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return {
        "schema": selector.SELECTION_SCHEMA,
        "status": "SELECTED",
        "selected_candidate": SELECTED,
        "source_commit": SOURCE,
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "development_artifacts": copy.deepcopy(artifacts),
        "analysis_file": "spade-development-analysis.json",
        "analysis_sha256": _sha256(analysis_bytes),
        "selection_trace": analysis["selection_trace"],
        "lofo_folds": analysis["lofo_folds"],
        "selection_trace_digest": _sha256(trace_json),
        "selected_canonical_config": json.loads(canonical_config_json),
        "selected_canonical_config_json": canonical_config_json,
        "selected_template_protocol_digest": SpadeConfig(
            opening=44, policy="fixed_hybrid", root_seed=0
        ).protocol_digest,
        "campaign_root_seed_binding": "sha256_labelled_derived_per_campaign",
    }


@pytest.fixture
def planner_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    results = tmp_path / "results"
    results.mkdir()
    rows = _rows()
    artifacts = _artifacts()
    analysis = _analysis()
    selected = _selected(analysis, artifacts)
    analysis_path = results / "spade-development-analysis.json"
    selection_path = results / "spade-selected-protocol.json"
    analysis_path.write_bytes(_canonical_bytes(analysis))
    selection_path.write_bytes(_canonical_bytes(selected))

    monkeypatch.setattr(planner, "registered_metadata", lambda _root: _metadata())
    monkeypatch.setattr(planner, "git_state", lambda _root: (CURRENT, False))
    monkeypatch.setattr(planner, "_is_ancestor", lambda *_args: True)
    monkeypatch.setattr(
        planner,
        "_validate_frozen_dependency_blobs",
        lambda *_args, **_kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        planner,
        "_preflight_development_inputs",
        lambda _root, paths, **_kwargs: tuple(Path(path) for path in paths),
        raising=False,
    )
    def committed_bytes(_root, path):
        source = Path(path)
        if source in {analysis_path, selection_path}:
            return source.read_bytes()
        return _development_artifact_bytes(source, artifacts)

    monkeypatch.setattr(planner, "_committed_file_bytes", committed_bytes)
    monkeypatch.setattr(
        planner,
        "_load_verified_development_shards",
        lambda _inputs, *, metadata, source_commit: (rows, artifacts),
    )
    monkeypatch.setattr(
        selector,
        "analyse_development",
        lambda _rows, *, protocol_digest: copy.deepcopy(analysis),
    )
    return {
        "repo_root": tmp_path,
        "manifest_paths": [results / str(item["manifest_file"]) for item in artifacts],
        "analysis": analysis,
        "analysis_path": analysis_path,
        "selected": selected,
        "selection_path": selection_path,
        "rows": rows,
        "artifacts": artifacts,
    }


def _write_case_files(case: dict[str, object]) -> None:
    Path(case["analysis_path"]).write_bytes(_canonical_bytes(case["analysis"]))
    Path(case["selection_path"]).write_bytes(_canonical_bytes(case["selected"]))


def _payload(case: dict[str, object]) -> dict[str, object]:
    return planner.power_payload_from_shards(
        case["manifest_paths"],
        selection_path=case["selection_path"],
        repo_root=case["repo_root"],
    )


def test_power_payload_extracts_exact_lofo_differences_and_provenance(planner_case):
    payload = _payload(planner_case)
    assert payload["schema"] == "boec-spade-lockbox-power-v1"
    assert payload["source_commit"] == CURRENT
    assert payload["selected_protocol"]["source_commit"] == SOURCE
    assert payload["held_out_proof"]["unanimous"] is True
    for family in DEVELOPMENT_FAMILIES:
        assert payload["held_out_differences"][family]["map"] == pytest.approx(
            [-0.02] * 50
        )
        assert payload["held_out_differences"][family]["regret"] == pytest.approx(
            [-0.01] * 50
        )
    assert [item["family"] for item in payload["development_artifacts"]] == list(
        DEVELOPMENT_FAMILIES
    )
    assert validate_power_plan_payload(payload) == payload


def test_power_payload_passes_selected_source_to_verified_byte_loader(
    planner_case, monkeypatch
):
    observed: dict[str, object] = {}

    def load(paths, *, metadata, source_commit):
        observed.update(paths=list(paths), metadata=metadata, source_commit=source_commit)
        return planner_case["rows"], planner_case["artifacts"]

    monkeypatch.setattr(planner, "_load_verified_development_shards", load)
    _payload(planner_case)
    assert observed["source_commit"] == SOURCE
    assert observed["metadata"]["source_commit"] == CURRENT


def test_power_payload_never_reopens_paths_after_verified_preflight(
    planner_case, monkeypatch
):
    verified_inputs = object()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        planner,
        "_preflight_development_inputs",
        lambda *_args, **_kwargs: verified_inputs,
    )

    def load_verified(inputs, *, metadata, source_commit):
        observed.update(
            inputs=inputs,
            metadata=metadata,
            source_commit=source_commit,
        )
        return planner_case["rows"], planner_case["artifacts"]

    monkeypatch.setattr(
        planner,
        "_load_verified_development_shards",
        load_verified,
        raising=False,
    )
    monkeypatch.setattr(
        selector,
        "_load_complete_shards",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("verified development paths were reopened")
        ),
    )

    _payload(planner_case)
    assert observed["inputs"] is verified_inputs
    assert observed["source_commit"] == SOURCE
    assert observed["metadata"]["source_commit"] == CURRENT


def test_power_payload_preflights_before_loader_opens_any_development_input(
    planner_case, monkeypatch
):
    loader_called = False

    def refuse_preflight(_root, _paths, **_kwargs):
        raise ValueError("manifest preflight refused before open")

    def load(*_args, **_kwargs):
        nonlocal loader_called
        loader_called = True
        raise AssertionError("loader must not run after failed preflight")

    monkeypatch.setattr(
        planner,
        "_preflight_development_inputs",
        refuse_preflight,
        raising=False,
    )
    monkeypatch.setattr(planner, "_load_verified_development_shards", load)
    with pytest.raises(ValueError, match="preflight"):
        _payload(planner_case)
    assert loader_called is False


@pytest.mark.parametrize(
    "unregistered",
    [
        "results/spade-lockbox-hill-0000-0050.jsonl.gz.manifest.json",
        "results/../secret.json",
        "/tmp/arbitrary-development-manifest.json",
    ],
)
def test_preflight_rejects_unregistered_manifest_path_before_read(
    tmp_path, monkeypatch, unregistered
):
    observed: list[Path] = []

    def committed(*_args, **_kwargs):
        observed.append(Path(_args[1]))
        raise AssertionError("unregistered path must never be read")

    monkeypatch.setattr(
        planner,
        "_committed_regular_file_bytes",
        committed,
        raising=False,
    )
    manifests = [
        Path("results")
        / f"spade-development-{family}-000-050.jsonl.gz.manifest.json"
        for family in DEVELOPMENT_FAMILIES
    ]
    manifests[0] = Path(unregistered)
    with pytest.raises(ValueError, match="registered|manifest|path"):
        planner._preflight_development_inputs(
            tmp_path,
            manifests,
            metadata=_metadata(),
            selected_source=SOURCE,
        )
    assert observed == []


def test_preflight_rejects_manifest_contained_lockbox_path_before_child_read(
    tmp_path, monkeypatch
):
    manifests = [
        tmp_path
        / "results"
        / f"spade-development-{family}-000-050.jsonl.gz.manifest.json"
        for family in DEVELOPMENT_FAMILIES
    ]
    malicious = _registered_manifest(
        DEVELOPMENT_FAMILIES[0],
        raw_file="spade-lockbox-toroidal_rastrigin-0000-0050.jsonl.gz",
    )
    observed: list[str] = []

    def committed(_root, path, **_kwargs):
        source = Path(path)
        observed.append(source.name)
        family = next(
            family for family in DEVELOPMENT_FAMILIES if family in source.name
        )
        payload = malicious if family == DEVELOPMENT_FAMILIES[0] else _registered_manifest(family)
        return _canonical_bytes(payload)

    monkeypatch.setattr(
        planner,
        "_committed_regular_file_bytes",
        committed,
        raising=False,
    )
    with pytest.raises(ValueError, match="raw|registered|identity"):
        planner._preflight_development_inputs(
            tmp_path,
            manifests,
            metadata=_metadata(),
            selected_source=SOURCE,
        )
    assert all("spade-lockbox" not in name for name in observed)
    assert observed
    assert set(observed) <= {path.name for path in manifests}


def test_dependency_pinning_runs_before_loader(planner_case, monkeypatch):
    loader_called = False

    def reject_dependencies(*_args, **_kwargs):
        raise ValueError("selected source dependency drift")

    def load(*_args, **_kwargs):
        nonlocal loader_called
        loader_called = True
        raise AssertionError("loader must not run after dependency drift")

    monkeypatch.setattr(
        planner,
        "_validate_frozen_dependency_blobs",
        reject_dependencies,
        raising=False,
    )
    monkeypatch.setattr(planner, "_load_verified_development_shards", load)
    with pytest.raises(ValueError, match="dependency drift"):
        _payload(planner_case)
    assert loader_called is False


def test_dependency_pinning_rejects_descendant_selector_reinterpretation(
    tmp_path, monkeypatch
):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, check=True
    )
    relative = Path("scripts/select_spade_protocol.py")
    source = tmp_path / relative
    source.parent.mkdir()
    source.write_text("FROZEN = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", relative.as_posix()], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "frozen selector"], cwd=tmp_path, check=True)
    selected_source = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source.write_text("FROZEN = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", relative.as_posix()], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "reinterpret rows"], cwd=tmp_path, check=True)
    monkeypatch.setattr(
        planner,
        "_FROZEN_POST_DEVELOPMENT_DEPENDENCIES",
        (relative,),
        raising=False,
    )
    with pytest.raises(ValueError, match="dependency|selected source|drift"):
        planner._validate_frozen_dependency_blobs(tmp_path, selected_source)


def test_committed_reader_rejects_worktree_and_head_symlinks_and_wrong_mode(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, check=True
    )
    results = tmp_path / "results"
    results.mkdir()
    path = results / "spade-selected-protocol.json"
    path.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "results/spade-selected-protocol.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "regular"], cwd=tmp_path, check=True)
    assert planner._committed_regular_file_bytes(tmp_path, path) == b"{}\n"

    target = results / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    path.unlink()
    path.symlink_to(target.name)
    with pytest.raises(ValueError, match="symlink"):
        planner._committed_regular_file_bytes(tmp_path, path)

    path.unlink()
    path.write_text("{}\n", encoding="utf-8")
    path.chmod(0o755)
    subprocess.run(["git", "add", "results/spade-selected-protocol.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "executable"], cwd=tmp_path, check=True)
    with pytest.raises(ValueError, match="mode|100644"):
        planner._committed_regular_file_bytes(tmp_path, path)

    path.unlink()
    path.symlink_to(target.name)
    subprocess.run(["git", "add", "results/spade-selected-protocol.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "tracked symlink"], cwd=tmp_path, check=True)
    with pytest.raises(ValueError, match="symlink|mode|regular"):
        planner._committed_regular_file_bytes(tmp_path, path)


def test_power_payload_refuses_dirty_tree(planner_case, monkeypatch):
    monkeypatch.setattr(planner, "git_state", lambda _root: (CURRENT, True))
    with pytest.raises(ValueError, match="dirty"):
        _payload(planner_case)


def test_power_payload_refuses_uncommitted_or_modified_selection(
    planner_case, monkeypatch
):
    def uncommitted(*_args):
        raise ValueError("selected protocol is not committed")

    monkeypatch.setattr(planner, "_committed_file_bytes", uncommitted)
    with pytest.raises(ValueError, match="committed"):
        _payload(planner_case)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda c: c["selected"].__setitem__("status", "NO_SELECTION"), "SELECTED"),
        (
            lambda c: c["selected"]["selection_trace"].__setitem__(
                "unanimous", False
            ),
            "unanimous|analysis|trace",
        ),
        (
            lambda c: c["selected"]["lofo_folds"][0].__setitem__(
                "selected_candidate", "spade-o32-staged"
            ),
            "fold|candidate|analysis",
        ),
        (
            lambda c: c["selected"]["development_artifacts"][0].__setitem__(
                "raw_sha256", "f" * 64
            ),
            "artifact",
        ),
        (
            lambda c: c["selected"].__setitem__("analysis_sha256", "0" * 64),
            "analysis",
        ),
        (
            lambda c: c["selected"].__setitem__("spec_digest", "0" * 64),
            "spec",
        ),
        (
            lambda c: c["selected"].__setitem__("config_digest", "0" * 64),
            "config",
        ),
        (
            lambda c: c["selected"].__setitem__("generator_digest", "0" * 64),
            "generator",
        ),
        (
            lambda c: c["selected"].__setitem__(
                "generator_manifest_sha256", "0" * 64
            ),
            "manifest",
        ),
    ],
)
def test_power_payload_refuses_selection_and_provenance_drift(
    planner_case, mutation, message
):
    mutation(planner_case)
    _write_case_files(planner_case)
    with pytest.raises(ValueError, match=message):
        _payload(planner_case)


def test_power_payload_refuses_nonancestor_development_source(
    planner_case, monkeypatch
):
    monkeypatch.setattr(planner, "_is_ancestor", lambda *_args: False)
    with pytest.raises(ValueError, match="ancestor|source commit"):
        _payload(planner_case)


def test_power_payload_refuses_selection_analysis_byte_mismatch(planner_case):
    planner_case["analysis"]["grid"] = {"row_count": 999}
    _write_case_files(planner_case)
    with pytest.raises(ValueError, match="analysis"):
        _payload(planner_case)


def test_power_payload_refuses_49_pairs(planner_case):
    planner_case["rows"].pop()
    with pytest.raises(ValueError, match="50|missing|complete"):
        _payload(planner_case)


def test_power_payload_refuses_wrong_comparator(planner_case):
    target = next(row for row in planner_case["rows"] if row["arm"] == "qlognei48")
    target["arm"] = "wrong-comparator"
    with pytest.raises(ValueError, match="comparator|arm|missing"):
        _payload(planner_case)


@pytest.mark.parametrize("bad", [math.nan, math.inf, True, "0.1"])
def test_power_payload_refuses_nonfinite_or_nonnumeric_score(planner_case, bad):
    planner_case["rows"][0]["scores"]["map_loss"] = bad
    with pytest.raises((TypeError, ValueError), match="finite|real|score"):
        _payload(planner_case)


def test_write_power_plan_is_exact_path_and_write_once(planner_case):
    wrong = Path(planner_case["repo_root"]) / "power.json"
    with pytest.raises(ValueError, match="registered path"):
        planner.write_power_plan(
            planner_case["manifest_paths"],
            selection_path=planner_case["selection_path"],
            output_path=wrong,
            repo_root=planner_case["repo_root"],
        )
    output = Path(planner_case["repo_root"]) / "results/spade-lockbox-power.json"
    payload = planner.write_power_plan(
        planner_case["manifest_paths"],
        selection_path=planner_case["selection_path"],
        output_path=output,
        repo_root=planner_case["repo_root"],
    )
    assert output.read_bytes() == _canonical_bytes(payload)
    with pytest.raises(ValueError, match="write-once|exists"):
        planner.write_power_plan(
            planner_case["manifest_paths"],
            selection_path=planner_case["selection_path"],
            output_path=output,
            repo_root=planner_case["repo_root"],
        )


def test_write_power_plan_returns_insufficient_artifact_and_status_2(
    planner_case, monkeypatch
):
    real_plan = planner.plan_lockbox_sample_size
    weak = {
        family: {"map": [0.03] * 50, "regret": [0.03] * 50}
        for family in DEVELOPMENT_FAMILIES
    }
    monkeypatch.setattr(
        planner,
        "_extract_held_out_differences",
        lambda *_args, **_kwargs: weak,
    )
    output = Path(planner_case["repo_root"]) / "results/spade-lockbox-power.json"
    payload = planner.write_power_plan(
        planner_case["manifest_paths"],
        selection_path=planner_case["selection_path"],
        output_path=output,
        repo_root=planner_case["repo_root"],
    )
    assert planner.plan_lockbox_sample_size is real_plan
    assert payload["status"] == "INSUFFICIENT_POWER"
    assert output.is_file()


def test_committed_bytes_require_head_blob_identity(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, check=True
    )
    path = tmp_path / "results/spade-selected-protocol.json"
    path.parent.mkdir()
    path.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", str(path.relative_to(tmp_path))], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "selection"], cwd=tmp_path, check=True)
    assert planner._committed_file_bytes(tmp_path, path) == b"{}\n"
    path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="committed|bytes|modified"):
        planner._committed_file_bytes(tmp_path, path)


def test_power_planner_source_has_no_lockbox_outcome_dependency():
    source = Path(planner.__file__).read_text(encoding="utf-8")
    compact = source.lower()
    for forbidden in (
        "spade-lockbox-*.jsonl",
        "spade-lockbox-analysis",
        "analyse_spade_lockbox",
    ):
        assert forbidden not in compact
    assert "run_spade_lockbox" not in compact
    assert "boec.lockbox_oracles" not in compact


def test_atomic_install_does_not_replace_racing_destination(tmp_path, monkeypatch):
    results = tmp_path / "results"
    results.mkdir()
    destination = results / "artifact.json"
    real_link = os.link

    def racing_link(
        source,
        target,
        *,
        src_dir_fd=None,
        dst_dir_fd=None,
        follow_symlinks=True,
    ):
        racer = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
            dir_fd=dst_dir_fd,
        )
        try:
            os.write(racer, b"racer\n")
        finally:
            os.close(racer)
        return real_link(
            source,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(planner.os, "link", racing_link)
    directory_descriptor = planner._open_registered_results_directory(tmp_path)
    try:
        with pytest.raises(FileExistsError):
            planner._write_once_json_at(
                directory_descriptor,
                destination.name,
                {"value": 1},
            )
    finally:
        os.close(directory_descriptor)
    assert destination.read_bytes() == b"racer\n"


def test_write_power_plan_parent_swap_cannot_redirect_publication(
    tmp_path, monkeypatch
):
    results = tmp_path / "results"
    results.mkdir()
    stable_results = tmp_path / "registered-results"
    attacker_results = tmp_path / "attacker-results"
    attacker_results.mkdir()
    output = results / "spade-lockbox-power.json"
    payload = {"status": "POWERED"}

    def swap_parent(*_args, **_kwargs):
        results.rename(stable_results)
        results.symlink_to(attacker_results, target_is_directory=True)
        return payload

    monkeypatch.setattr(planner, "power_payload_from_shards", swap_parent)

    assert planner.write_power_plan(
        [],
        selection_path=tmp_path / "results/spade-selected-protocol.json",
        output_path=output,
        repo_root=tmp_path,
    ) == payload
    assert (stable_results / output.name).read_bytes() == _canonical_bytes(payload)
    assert not (attacker_results / output.name).exists()
