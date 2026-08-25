from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from boec.spade import SpadeConfig
from boec.spade_study import REGISTERED_SCORING_SETTINGS, write_jsonl_gzip
from scripts import run_spade_development as runner
from scripts import select_spade_protocol as selector


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
SOURCE = "1" * 40


def _candidate_protocol(arm_id: str, root_seed: int) -> str:
    opening, policy = runner.candidate_spec(arm_id)
    return SpadeConfig(
        opening=opening,
        policy=policy,
        root_seed=root_seed,
    ).protocol_digest


def _row(
    family: str,
    key_index: int,
    arm_id: str,
    *,
    answer: bool = True,
    contained: bool = True,
    regret: float = 0.10,
    map_loss: float = 0.10,
    registered: bool = True,
) -> dict:
    instance_seed, campaign_seed = runner.development_campaign_key(family, key_index)
    root_seed = 10_000 + key_index
    arm = "spade" if arm_id.startswith("spade-") else arm_id
    arm_protocol = (
        _candidate_protocol(arm_id, root_seed)
        if arm == "spade"
        else ("b" if arm == "sobol48" else "c") * 64
    )
    run_digest = hashlib.sha256(
        f"{family}|{key_index}|{arm_id}|{root_seed}".encode()
    ).hexdigest()
    rounds = (
        runner.rounds_for_opening(runner.candidate_spec(arm_id)[0])
        if arm == "spade"
        else (1 if arm == "sobol48" else 10)
    )
    selection_draws = 2048 if registered else 16
    evaluation_draws = 2048 if registered else 16
    settings_digest = (
        REGISTERED_SCORING_SETTINGS.digest if registered else "0" * 64
    )
    execution_mode = "REGISTERED" if registered else "TEST_ONLY"
    score = {
        "schema": "boec-spade-score-v1",
        "arm": arm,
        "protocol_digest": arm_protocol,
        "run_digest": run_digest,
        "terminal_rule": "P",
        "budget": 48,
        "rounds": rounds,
        "execution_mode": execution_mode,
        "scoring_settings_digest": settings_digest,
        "threshold_record_digest": "2" * 64,
        "scoring_seed": 4,
        "terminal_fit_seed": 5,
        "terminal_fit_restarts": 4 if registered else 1,
        "terminal_grid_seed": 6,
        "map_grid_seed": 7,
        "certificate_grid_seed": 8,
        "certificate_draw_seed": 9,
        "decision_digest": "3" * 64,
        "tau": 0.5,
        "sigma_rel": 0.1,
        "sigma_add": 0.01,
        "gamma": 0.95,
        "alpha": 0.95,
        "q_tau": 0.75,
        "terminal_x": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        "terminal_truth": 1.0 - regret,
        "regret_rule_p": regret,
        "map_loss": map_loss,
        "map_brier": map_loss,
        "map_auc": 0.75,
        "map_iou": 0.6,
        "map_symmetric_difference": 0.2,
        "certificate_nonempty": answer,
        "certificate_volume": 0.1 if answer else 0.0,
        "certificate_selection_containment": 0.96 if answer else None,
        "certificate_crossfit_containment": 0.94 if answer else None,
        "certificate_empirical_containment": contained if answer else None,
        "certificate_selection_draws": selection_draws,
        "certificate_evaluation_draws": evaluation_draws,
    }
    return {
        "schema": "boec-spade-study-row-v1",
        "campaign_key": {
            "family": family,
            "instance_seed": instance_seed,
            "campaign_seed": campaign_seed,
            "arm": arm,
            "arm_protocol_digest": arm_protocol,
            "run_digest": run_digest,
        },
        "protocol_digest": PROTOCOL,
        "arm_protocol_digest": arm_protocol,
        "run_digest": run_digest,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "source_commit": SOURCE,
        "source_dirty": False,
        "environment": {
            "python": "3.11",
            "platform": "test",
            "packages": {
                "numpy": "1",
                "scipy": "1",
                "torch": "1",
                "gpytorch": "1",
                "botorch": "1",
            },
            "threads": {
                "torch": 1,
                "torch_interop": 1,
                "omp_num_threads": None,
                "mkl_num_threads": None,
            },
            "executable": "/python",
            "boec_distribution": "0.1.0",
        },
        "command_args": ["--family", family],
        "parent_artifacts": {
            "spec": SPEC,
            "config": CONFIG,
            "generator": GENERATOR,
        },
        "family": family,
        "instance_seed": instance_seed,
        "campaign_seed": campaign_seed,
        "root_seed": root_seed,
        "derived_seeds": {"noise": 2, "threshold": 3, "scoring": 4},
        "arm": arm,
        "budget": 48,
        "rounds": rounds,
        "terminal_rule": "P",
        "estimands": {
            "target": "future_response_reliability",
            "tau": 0.5,
            "sigma_rel": 0.1,
            "sigma_add": 0.01,
            "gamma": 0.95,
            "alpha": 0.95,
            "q_tau": 0.75,
            "map_metric": "integrated_squared_probability_error",
            "terminal_rule": "P",
            "certificate_draws": {
                "total": selection_draws + evaluation_draws,
                "selection": selection_draws,
                "evaluation": evaluation_draws,
            },
        },
        "scores": score,
    }


def _complete_rows() -> list[dict]:
    rows = []
    for family in runner.DEVELOPMENT_FAMILIES:
        for key_index in range(runner.CAMPAIGNS_PER_FAMILY):
            for arm_id in runner.DEVELOPMENT_ARM_IDS:
                opening = runner.candidate_spec(arm_id)[0] if arm_id.startswith("spade-") else 0
                candidate_offset = (44 - opening) * 0.0001
                regret = 0.10 if arm_id == "qlognei48" else 0.095 + candidate_offset
                map_loss = 0.10 if arm_id == "sobol48" else 0.08 + candidate_offset
                rows.append(
                    _row(
                        family,
                        key_index,
                        arm_id,
                        regret=regret,
                        map_loss=map_loss,
                    )
                )
    return rows


@pytest.fixture(scope="module")
def complete_rows():
    return _complete_rows()


def test_frozen_development_grid_is_exact_and_common_keyed():
    assert runner.DEVELOPMENT_FAMILIES == (
        "hill",
        "ackley",
        "hartmann6",
        "levy",
        "rosenbrock",
    )
    assert runner.OPENINGS == (32, 40, 44)
    assert runner.POLICIES == ("staged", "fixed_hybrid", "validity_gated")
    assert len(runner.CANDIDATE_ARM_IDS) == 9
    assert runner.CONTROL_ARMS == ("sobol48", "qlognei48")
    assert len(runner.DEVELOPMENT_ARM_IDS) == 11
    assert runner.development_campaign_key("hill", 0) == (0, 0)
    assert runner.development_campaign_key("hill", 49) == (24, 1)
    assert runner.development_campaign_key("ackley", 49) == (0, 49)
    committed = json.loads(
        (Path(__file__).resolve().parents[1] / "results" / "p2-versionb-gamma.json").read_text()
    )
    assert len(runner.HILL_DEVELOPMENT_INSTANCE_IDS) == 25
    assert set(runner.HILL_DEVELOPMENT_INSTANCE_IDS) == {
        row["instance"] for row in committed["rows"]
    }


def test_complete_grid_accepts_exactly_2750_rows(complete_rows):
    grid = selector.validate_development_grid(complete_rows, protocol_digest=PROTOCOL)
    assert grid["row_count"] == 5 * 50 * 11 == 2750
    assert grid["campaigns_per_family"] == 50
    assert grid["candidate_count"] == 9
    assert grid["control_count"] == 2


def test_grid_rejects_tenth_candidate_missing_arm_and_heldout_role(complete_rows):
    extra = copy.deepcopy(complete_rows[0])
    extra["arm_protocol_digest"] = "9" * 64
    extra["scores"]["protocol_digest"] = "9" * 64
    extra["campaign_key"]["arm_protocol_digest"] = "9" * 64
    extra["run_digest"] = "8" * 64
    extra["scores"]["run_digest"] = "8" * 64
    extra["campaign_key"]["run_digest"] = "8" * 64
    with pytest.raises(ValueError, match="unregistered SPADE candidate"):
        selector.validate_development_grid([*complete_rows, extra], protocol_digest=PROTOCOL)

    with pytest.raises(ValueError, match="missing|incomplete"):
        selector.validate_development_grid(complete_rows[:-1], protocol_digest=PROTOCOL)

    wrong_parent = copy.deepcopy(complete_rows)
    wrong_parent[0]["parent_artifacts"]["generator"] = "0" * 64
    with pytest.raises(ValueError, match="parent|generator"):
        selector.validate_development_grid(wrong_parent, protocol_digest=PROTOCOL)

    manifest = runner.make_shard_manifest(
        family="hill",
        start=0,
        stop=1,
        row_count=11,
        raw_file="x.jsonl.gz",
        raw_sha256="4" * 64,
        metadata={
            "study_protocol_digest": PROTOCOL,
            "spec_digest": SPEC,
            "config_digest": CONFIG,
            "generator_digest": GENERATOR,
            "source_commit": SOURCE,
            "source_dirty": False,
        },
        smoke=False,
        complete=True,
        command_args=(),
    )
    manifest["dataset_role"] = "HELD_OUT"
    with pytest.raises(ValueError, match="DEVELOPMENT"):
        runner.validate_shard_manifest(manifest)


def test_smoke_shard_is_scratch_only_marked_and_resumable(tmp_path, monkeypatch):
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    output = tmp_path / "smoke.jsonl.gz"
    calls = []

    def fake_rows(family, key_index, arm_ids, **_):
        for arm_id in arm_ids:
            calls.append((key_index, arm_id))
            if len(calls) == 6:
                raise RuntimeError("interrupt")
            yield _row(family, key_index, arm_id, registered=False)

    monkeypatch.setattr(runner, "_run_campaign_rows", fake_rows)
    with pytest.raises(RuntimeError, match="interrupt"):
        runner.run_development_shard(
            family="ackley",
            start=0,
            stop=2,
            output=output,
            smoke=True,
            metadata=metadata,
            repo_root=tmp_path / "repo",
        )
    assert len(runner.read_shard_rows(output, PROTOCOL)) == 5

    monkeypatch.setattr(
        runner,
        "_run_campaign_rows",
        lambda family, key_index, arm_ids, **_: (
            _row(family, key_index, arm_id, registered=False) for arm_id in arm_ids
        ),
    )
    manifest = runner.run_development_shard(
        family="ackley",
        start=0,
        stop=2,
        output=output,
        smoke=True,
        metadata=metadata,
        repo_root=tmp_path / "repo",
    )
    assert manifest["status"] == "SMOKE"
    assert manifest["complete"] is True
    assert manifest["row_count"] == 22

    results = tmp_path / "repo" / "results"
    results.mkdir(parents=True)
    with pytest.raises(ValueError, match="SMOKE.*results"):
        runner.run_development_shard(
            family="ackley",
            start=0,
            stop=1,
            output=results / "spade-development-ackley-000-001.jsonl.gz",
            smoke=True,
            metadata=metadata,
            repo_root=tmp_path / "repo",
        )


def test_nested_lofo_selection_records_every_gate_and_tie(complete_rows):
    analysis = selector.analyse_development(complete_rows, protocol_digest=PROTOCOL)
    assert analysis["status"] == "SELECTED"
    assert analysis["selected_candidate"] == "spade-o44-fixed_hybrid"
    assert len(analysis["lofo_folds"]) == 5
    assert {fold["held_out_family"] for fold in analysis["lofo_folds"]} == set(
        runner.DEVELOPMENT_FAMILIES
    )
    assert all(len(fold["training_families"]) == 4 for fold in analysis["lofo_folds"])
    trace = analysis["selection_trace"]
    assert set(trace) == {"step1", "step2", "step3", "step4"}
    assert trace["step4"]["policy_order"] == [
        "fixed_hybrid",
        "validity_gated",
        "staged",
    ]
    assert set(analysis["candidates"]) == set(runner.CANDIDATE_ARM_IDS)


def test_each_mandatory_gate_and_no_selection_are_independently_exercised(complete_rows):
    answer_fail = copy.deepcopy(complete_rows)
    target = "spade-o32-staged"
    changed = 0
    for row in answer_fail:
        if selector.development_arm_id(row) == target and row["family"] == "ackley" and changed < 26:
            row["scores"].update(
                certificate_nonempty=False,
                certificate_volume=0.0,
                certificate_selection_containment=None,
                certificate_crossfit_containment=None,
                certificate_empirical_containment=None,
            )
            changed += 1
    a = selector.analyse_development(answer_fail, protocol_digest=PROTOCOL)
    assert any("answer_rate" in reason for reason in a["candidates"][target]["step1_failures"])

    containment_fail = copy.deepcopy(complete_rows)
    changed = 0
    for row in containment_fail:
        if selector.development_arm_id(row) == target and row["family"] == "levy" and changed < 6:
            row["scores"]["certificate_empirical_containment"] = False
            changed += 1
    a = selector.analyse_development(containment_fail, protocol_digest=PROTOCOL)
    assert any("containment" in reason for reason in a["candidates"][target]["step1_failures"])

    regret_fail = copy.deepcopy(complete_rows)
    for row in regret_fail:
        if selector.development_arm_id(row) == target and row["family"] == "rosenbrock":
            row["scores"]["regret_rule_p"] = 0.14
            row["scores"]["terminal_truth"] = 0.86
    a = selector.analyse_development(regret_fail, protocol_digest=PROTOCOL)
    assert any("regret_upper" in reason for reason in a["candidates"][target]["step2_failures"])

    none = copy.deepcopy(complete_rows)
    for row in none:
        if row["arm"] == "spade":
            row["scores"].update(
                certificate_nonempty=False,
                certificate_volume=0.0,
                certificate_selection_containment=None,
                certificate_crossfit_containment=None,
                certificate_empirical_containment=None,
            )
    a = selector.analyse_development(none, protocol_digest=PROTOCOL)
    assert a["status"] == "NO_SELECTION"
    assert a["selected_candidate"] is None


def _write_complete_shards(tmp_path: Path, rows: list[dict]) -> list[Path]:
    manifests = []
    for family in runner.DEVELOPMENT_FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        raw = tmp_path / f"spade-development-{family}-000-050.jsonl.gz"
        raw_hash = write_jsonl_gzip(raw, family_rows, protocol_digest=PROTOCOL)
        manifest = runner.make_shard_manifest(
            family=family,
            start=0,
            stop=50,
            row_count=len(family_rows),
            raw_file=raw.name,
            raw_sha256=raw_hash,
            metadata={
                "study_protocol_digest": PROTOCOL,
                "spec_digest": SPEC,
                "config_digest": CONFIG,
                "generator_digest": GENERATOR,
                "source_commit": SOURCE,
                "source_dirty": False,
            },
            smoke=False,
            complete=True,
            command_args=(),
        )
        manifest_path = Path(str(raw) + ".manifest.json")
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
        )
        manifests.append(manifest_path)
    return manifests


def test_selected_artifact_is_hash_bound_and_fail_closed(tmp_path, complete_rows, monkeypatch):
    manifests = _write_complete_shards(tmp_path, complete_rows)
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(selector, "registered_metadata", lambda _root: metadata)
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    analysis_path = tmp_path / "spade-development-analysis.json"
    selected_path = tmp_path / "spade-selected-protocol.json"
    selected = selector.select_from_shards(
        manifests,
        analysis_output=analysis_path,
        selected_output=selected_path,
        repo_root=tmp_path,
    )
    assert selected["status"] == "SELECTED"
    assert selected["source_commit"] == SOURCE
    assert selected["spec_digest"] == SPEC
    assert selected["config_digest"] == CONFIG
    assert selected["generator_digest"] == GENERATOR
    assert len(selected["development_artifacts"]) == 5
    assert selected["selected_canonical_config"]["opening"] == 44
    assert selected["selected_canonical_config"]["policy"] == "fixed_hybrid"
    assert hashlib.sha256(analysis_path.read_bytes()).hexdigest() == selected["analysis_sha256"]

    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, True))
    with pytest.raises(ValueError, match="dirty"):
        selector.select_from_shards(
            manifests,
            analysis_output=analysis_path,
            selected_output=selected_path,
            repo_root=tmp_path,
        )

    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    sidecar = Path(str(tmp_path / "spade-development-hill-000-050.jsonl.gz") + ".sha256")
    sidecar.unlink()
    with pytest.raises(ValueError, match="SHA-256|sidecar|hashed"):
        selector.select_from_shards(
            manifests,
            analysis_output=analysis_path,
            selected_output=selected_path,
            repo_root=tmp_path,
        )


def test_selection_rejects_incomplete_or_wrong_digest_manifest(tmp_path, complete_rows, monkeypatch):
    manifests = _write_complete_shards(tmp_path, complete_rows)
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(selector, "registered_metadata", lambda _root: metadata)
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))

    broken = json.loads(manifests[0].read_text())
    broken["complete"] = False
    broken["status"] = "RUNNING"
    manifests[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="complete|COMPLETE"):
        selector.select_from_shards(
            manifests,
            analysis_output=tmp_path / "a.json",
            selected_output=tmp_path / "s.json",
            repo_root=tmp_path,
        )

    manifests = _write_complete_shards(tmp_path, complete_rows)
    broken = json.loads(manifests[0].read_text())
    broken["study_protocol_digest"] = "0" * 64
    manifests[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="protocol digest"):
        selector.select_from_shards(
            manifests,
            analysis_output=tmp_path / "a.json",
            selected_output=tmp_path / "s.json",
            repo_root=tmp_path,
        )
