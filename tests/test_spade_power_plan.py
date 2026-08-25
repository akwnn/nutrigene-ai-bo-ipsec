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
    def committed_bytes(_root, path):
        source = Path(path)
        if source in {analysis_path, selection_path}:
            return source.read_bytes()
        return _development_artifact_bytes(source, artifacts)

    monkeypatch.setattr(planner, "_committed_file_bytes", committed_bytes)
    monkeypatch.setattr(
        selector,
        "_load_complete_shards",
        lambda _paths, *, metadata, source_commit: (rows, artifacts),
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


def test_power_payload_passes_selected_source_to_complete_shard_loader(
    planner_case, monkeypatch
):
    observed: dict[str, object] = {}

    def load(paths, *, metadata, source_commit):
        observed.update(paths=list(paths), metadata=metadata, source_commit=source_commit)
        return planner_case["rows"], planner_case["artifacts"]

    monkeypatch.setattr(selector, "_load_complete_shards", load)
    _payload(planner_case)
    assert observed["source_commit"] == SOURCE
    assert observed["metadata"]["source_commit"] == CURRENT


def test_power_payload_requires_every_development_input_to_be_committed(
    planner_case, monkeypatch
):
    observed: set[str] = set()

    def committed(_root, path):
        source = Path(path)
        observed.add(source.name)
        if source in {
            Path(planner_case["analysis_path"]),
            Path(planner_case["selection_path"]),
        }:
            return source.read_bytes()
        return _development_artifact_bytes(source, planner_case["artifacts"])

    monkeypatch.setattr(planner, "_committed_file_bytes", committed)
    _payload(planner_case)
    for artifact in planner_case["artifacts"]:
        assert artifact["raw_file"] in observed
        assert artifact["manifest_file"] in observed
        assert artifact["resume_file"] in observed
        assert f"{artifact['raw_file']}.sha256" in observed


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
    destination = tmp_path / "artifact.json"
    real_link = os.link

    def racing_link(source, target):
        Path(target).write_bytes(b"racer\n")
        return real_link(source, target)

    monkeypatch.setattr(planner.os, "link", racing_link)
    with pytest.raises(FileExistsError):
        planner._write_once_json(destination, {"value": 1})
    assert destination.read_bytes() == b"racer\n"
