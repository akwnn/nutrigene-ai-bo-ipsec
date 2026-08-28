from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from boec.spade import SpadeConfig
from boec.spade_study import REGISTERED_SCORING_SETTINGS, write_jsonl_gzip
from boec.seedbook import derive_seed
from scripts import run_spade_development as runner
from scripts import select_spade_protocol as selector


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
SOURCE = "1" * 40
GENERATOR_MANIFEST = "b" * 64
POWER_DESIGN = "c" * 64
POWER_ENGINE = "8" * 64
POWER_PLANNER = "9" * 64


def _registered_metadata() -> dict[str, object]:
    return {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "power_design_digest": POWER_DESIGN,
        "power_engine_digest": POWER_ENGINE,
        "power_planner_digest": POWER_PLANNER,
        "source_commit": SOURCE,
        "source_dirty": False,
    }


def _candidate_protocol(arm_id: str, root_seed: int) -> str:
    opening, policy = runner.candidate_spec(arm_id)
    return SpadeConfig(
        opening=opening,
        policy=policy,
        root_seed=root_seed,
    ).protocol_digest


def _identity_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    registered_seed_identity = runner.development_seed_identity(
        family=family,
        instance_seed=instance_seed,
        campaign_seed=campaign_seed,
    )
    root_seed = registered_seed_identity["root"]
    arm = "spade" if arm_id.startswith("spade-") else arm_id
    arm_protocol = (
        _candidate_protocol(arm_id, root_seed)
        if arm == "spade"
        else runner.comparator_protocol_digest(arm, root_seed=root_seed)
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
    scoring_seed = registered_seed_identity["scoring"]
    terminal_grid_seed = derive_seed(scoring_seed, "terminal_rule_p_grid")
    map_grid_seed = derive_seed(scoring_seed, "probability_map_grid")
    certificate_grid_seed = derive_seed(scoring_seed, "certificate_grid")
    certificate_draw_seed = derive_seed(scoring_seed, "certificate_joint_draws")
    terminal_fit_seed = derive_seed(
        scoring_seed,
        "score_terminal_common_gp",
        run_digest,
        settings_digest,
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
        "scoring_seed": scoring_seed,
        "terminal_fit_seed": terminal_fit_seed,
        "terminal_fit_restarts": 4 if registered else 1,
        "terminal_grid_seed": terminal_grid_seed,
        "map_grid_seed": map_grid_seed,
        "certificate_grid_seed": certificate_grid_seed,
        "certificate_draw_seed": certificate_draw_seed,
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
    derived_seeds = {
        "noise": registered_seed_identity["noise"],
        "threshold": registered_seed_identity["threshold"],
        "scoring": scoring_seed,
        "opening_design": derive_seed(root_seed, "opening_design"),
        "candidate_menu": derive_seed(root_seed, "adaptive_candidate_menu"),
        "ivr_reference": derive_seed(root_seed, "ivr_reference_grid"),
        "terminal_grid": terminal_grid_seed,
        "map_grid": map_grid_seed,
        "certificate_grid": certificate_grid_seed,
        "certificate_draws": certificate_draw_seed,
    }
    candidate_menu_contract = {
        "schema": "boec-candidate-menu-contract-v1",
        "design": "scrambled_sobol",
        "dimension": 6,
        "size": 16_384 if registered else 256,
        "seed": derived_seeds["candidate_menu"],
    }
    scorer_contract = {
        "schema": "boec-scorer-contract-v1",
        "scoring_seed": scoring_seed,
        "settings_digest": settings_digest,
        "threshold_record_digest": score["threshold_record_digest"],
        "terminal_grid_seed": terminal_grid_seed,
        "map_grid_seed": map_grid_seed,
        "certificate_grid_seed": certificate_grid_seed,
        "certificate_draw_seed": certificate_draw_seed,
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
            "generator_manifest": GENERATOR_MANIFEST,
            "seed_contract": _identity_digest(derived_seeds),
            "candidate_menu_contract": _identity_digest(candidate_menu_contract),
            "scorer_contract": _identity_digest(scorer_contract),
        },
        "family": family,
        "instance_seed": instance_seed,
        "campaign_seed": campaign_seed,
        "root_seed": root_seed,
        "derived_seeds": derived_seeds,
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


def test_registered_metadata_binds_the_frozen_generator_manifest():
    root = Path(__file__).resolve().parents[1]
    metadata = runner.registered_metadata(root)
    manifest = root / "results" / "spade-lockbox-generator-manifest.json"
    assert metadata["generator_manifest_sha256"] == hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()


def test_registered_metadata_binds_live_power_sources_and_dynamic_rule():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(
        (root / "configs/experiment/spade-joint.yaml").read_text(encoding="utf-8")
    )
    expected_rule = {
        "minimum": 350,
        "maximum": 2000,
        "target_power": 0.80,
        "paired_margin": 0.02,
        "one_sided_alpha": 0.05,
        "sensitivity_replicates": 2000,
        "sensitivity_lower_confidence": 0.95,
        "decision": "first_integer_passing_all_families_and_both_endpoints",
    }
    assert config["protocol"]["lockbox"]["sample_size_rule"] == expected_rule
    assert "selected_instance_prefix" not in config["protocol"]["lockbox"]

    paths = {
        "power_design_sha256": (
            "docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md"
        ),
        "power_engine_sha256": "src/boec/spade_power.py",
        "power_planner_sha256": "scripts/plan_spade_lockbox_power.py",
    }
    metadata = runner.registered_metadata(root)
    for field, relative in paths.items():
        expected = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert config["digests"][field] == expected
        assert metadata[field.removesuffix("_sha256") + "_digest"] == expected

    parent = (
        root / "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md"
    ).read_text(encoding="utf-8")
    assert "2026-08-25-spade-lockbox-power-design.md" in parent
    assert "first integer from 350 through 2,000" in parent
    assert "Run 350 independent paired campaigns" not in parent


@pytest.mark.parametrize(
    "relative",
    [
        ".github/workflows/spade-distributed.yml",
        "scripts/make_spade_actions_matrix.py",
        "scripts/run_spade_actions_worker.py",
        "scripts/merge_spade_development_shards.py",
        "requirements.txt",
    ],
)
def test_registered_metadata_rejects_live_execution_blob_drift(monkeypatch, relative):
    root = Path(__file__).resolve().parents[1]
    original = runner._sha256

    def drift(path):
        if path == root / relative:
            return "0" * 64
        return original(path)

    monkeypatch.setattr(runner, "_sha256", drift)
    with pytest.raises(ValueError, match="execution|source digest"):
        runner.registered_metadata(root)


def test_default_live_metadata_reaches_campaign_boundary_as_development_projection(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[1]
    observed: list[dict[str, object]] = []

    class CampaignBoundaryReached(RuntimeError):
        pass

    def stop_before_campaign(_family, _key_index, _arm_ids, *, metadata, **_kwargs):
        observed.append(dict(metadata))
        raise CampaignBoundaryReached

    monkeypatch.setattr(runner, "_run_campaign_rows", stop_before_campaign)
    with pytest.raises(CampaignBoundaryReached):
        runner.run_development_shard(
            family="ackley",
            start=0,
            stop=1,
            output=tmp_path / "scratch.jsonl.gz",
            smoke=True,
            repo_root=root,
        )

    live = runner.registered_metadata(root)
    assert observed == [
        {
            field: live[field]
            for field in (
                "study_protocol_digest",
                "spec_digest",
                "config_digest",
                "generator_digest",
                "generator_manifest_sha256",
                "source_commit",
                "source_dirty",
            )
        }
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda metadata: metadata.pop("power_design_digest"),
        lambda metadata: metadata.__setitem__("unexpected", "0" * 64),
        lambda metadata: metadata.__setitem__("power_engine_digest", "0" * 63),
    ],
    ids=("missing-power-digest", "extra-field", "malformed-power-digest"),
)
def test_development_entry_rejects_registered_metadata_drift_before_campaign(
    tmp_path, monkeypatch, mutate
):
    metadata = _registered_metadata()
    mutate(metadata)
    monkeypatch.setattr(
        runner,
        "_run_campaign_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("campaign work must not begin")
        ),
    )

    with pytest.raises(ValueError, match="registered metadata|power_engine_digest"):
        runner.run_development_shard(
            family="ackley",
            start=0,
            stop=1,
            output=tmp_path / "scratch.jsonl.gz",
            smoke=True,
            metadata=metadata,
            repo_root=tmp_path / "repo",
        )


def test_generator_manifest_remains_unopened_and_binds_final_protocol_bytes():
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs/experiment/spade-joint.yaml"
    spec_path = root / "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md"
    manifest = json.loads(
        (root / "results/spade-lockbox-generator-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    protocol_digest = hashlib.sha256(
        json.dumps(
            config["protocol"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert manifest["status"] == "FROZEN_UNOPENED"
    assert manifest["digests"]["config_file_sha256"] == hashlib.sha256(
        config_path.read_bytes()
    ).hexdigest()
    assert manifest["digests"]["spec_sha256"] == hashlib.sha256(
        spec_path.read_bytes()
    ).hexdigest()
    assert manifest["digests"]["protocol_payload_sha256"] == protocol_digest


@pytest.mark.parametrize("family", runner.DEVELOPMENT_FAMILIES)
def test_real_development_threshold_path_accepts_every_registered_family(family):
    instance_seed, campaign_seed = runner.development_campaign_key(family, 0)
    seeds = runner.development_seed_identity(
        family=family,
        instance_seed=instance_seed,
        campaign_seed=campaign_seed,
    )
    _, threshold = runner._development_threshold(
        family,
        instance_seed,
        seeds["noise"],
        seeds["threshold"],
        smoke=True,
    )
    assert threshold.reliable_fraction == pytest.approx(0.25, abs=1 / 256)
    assert threshold.truth_range_contract == (
        "strict_unit_interval" if family == "hill" else "legacy_unit_scaled"
    )


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
            "generator_manifest_sha256": GENERATOR_MANIFEST,
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
    metadata = _registered_metadata()
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
    checkpoint = runner.read_resume_checkpoint(
        runner.resume_checkpoint_path(output), protocol_digest=PROTOCOL
    )
    assert checkpoint["row_count"] == 5
    assert not output.exists()

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

    rows = runner.read_shard_rows(output, PROTOCOL)
    rows[0]["scores"]["map_loss"] = 0.123
    write_jsonl_gzip(output, rows, protocol_digest=PROTOCOL)
    with pytest.raises(ValueError, match="expected raw|resume|SHA-256"):
        runner.run_development_shard(
            family="ackley",
            start=0,
            stop=2,
            output=output,
            smoke=True,
            metadata=metadata,
            repo_root=tmp_path / "repo",
        )

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
    assert trace["all_five_refit_diagnostic"]["trace"]["step4"]["policy_order"] == [
        "fixed_hybrid",
        "validity_gated",
        "staged",
    ]
    assert set(analysis["candidates"]) == set(runner.CANDIDATE_ARM_IDS)
    assert analysis["selection_trace"]["rule"] == "unanimous_lofo_consensus"
    assert analysis["selection_trace"]["unanimous"] is True


def test_lofo_disagreement_returns_no_selection_even_when_full_grid_has_winner(complete_rows):
    rows = copy.deepcopy(complete_rows)
    candidate_a = "spade-o44-fixed_hybrid"
    candidate_b = "spade-o44-validity_gated"
    for row in rows:
        arm_id = selector.development_arm_id(row)
        if arm_id == "sobol48":
            row["scores"]["map_loss"] = 0.40
        elif arm_id == candidate_a:
            row["scores"]["map_loss"] = 0.60 if row["family"] == "rosenbrock" else 0.10
        elif arm_id == candidate_b:
            row["scores"]["map_loss"] = 0.40
        elif row["arm"] == "spade":
            row["scores"]["map_loss"] = 0.80
    analysis = selector.analyse_development(rows, protocol_digest=PROTOCOL)
    winners = {fold["selected_candidate"] for fold in analysis["lofo_folds"]}
    assert winners == {candidate_a, candidate_b}
    assert analysis["status"] == "NO_SELECTION"
    assert analysis["selected_candidate"] is None
    assert analysis["selection_trace"]["unanimous"] is False
    assert "unanimous" in analysis["selection_trace"]["rationale"]


def test_all_eleven_arms_must_share_seed_and_scoring_identity(complete_rows):
    for field, value in (
        ("root_seed", 999_999),
        ("noise", 999_998),
        ("candidate_menu", 999_997),
        ("scoring", 999_996),
    ):
        rows = copy.deepcopy(complete_rows)
        target = next(
            row
            for row in rows
            if row["family"] == "ackley"
            and row["campaign_seed"] == 0
            and selector.development_arm_id(row) == "sobol48"
        )
        if field == "root_seed":
            target[field] = value
        else:
            target["derived_seeds"][field] = value
        with pytest.raises(ValueError, match="matched|seed|identity|protocol|comparator"):
            selector.validate_development_grid(rows, protocol_digest=PROTOCOL)

    rows = copy.deepcopy(complete_rows)
    target = next(
        row
        for row in rows
        if row["family"] == "levy"
        and row["campaign_seed"] == 2
        and selector.development_arm_id(row) == "qlognei48"
    )
    target["scores"]["scoring_seed"] += 1
    with pytest.raises(ValueError, match="scor|seed|identity"):
        selector.validate_development_grid(rows, protocol_digest=PROTOCOL)

    rows = copy.deepcopy(complete_rows)
    target = next(
        row for row in rows
        if row["family"] == "ackley"
        and row["campaign_seed"] == 1
        and selector.development_arm_id(row) == "qlognei48"
    )
    target["arm_protocol_digest"] = "0" * 64
    target["scores"]["protocol_digest"] = "0" * 64
    target["campaign_key"]["arm_protocol_digest"] = "0" * 64
    with pytest.raises(ValueError, match="comparator|protocol|identity"):
        selector.validate_development_grid(rows, protocol_digest=PROTOCOL)

    for contract in ("seed_contract", "candidate_menu_contract", "scorer_contract"):
        rows = copy.deepcopy(complete_rows)
        target = next(
            row for row in rows
            if row["family"] == "hartmann6"
            and row["campaign_seed"] == 3
            and selector.development_arm_id(row) == "sobol48"
        )
        target["parent_artifacts"][contract] = "0" * 64
        with pytest.raises(ValueError, match="contract|digest|identity"):
            selector.validate_development_grid(rows, protocol_digest=PROTOCOL)

    rows = copy.deepcopy(complete_rows)
    group = [
        row for row in rows
        if row["family"] == "rosenbrock" and row["campaign_seed"] == 4
    ]
    assert len(group) == 11
    for row in group:
        row["derived_seeds"]["noise"] = 999_995
        row["parent_artifacts"]["seed_contract"] = runner.seed_contract_digest(
            row["derived_seeds"]
        )
    with pytest.raises(ValueError, match="registered|noise|seed identity"):
        selector.validate_development_grid(rows, protocol_digest=PROTOCOL)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("map_loss", -0.1),
        ("map_loss", float("nan")),
        ("regret_rule_p", -0.1),
        ("regret_rule_p", float("inf")),
        ("certificate_nonempty", 1),
        ("certificate_empirical_containment", 1),
    ],
)
def test_direct_selection_metrics_are_finite_typed_and_in_range(complete_rows, field, bad):
    rows = copy.deepcopy(complete_rows)
    rows[0]["scores"][field] = bad
    with pytest.raises(ValueError, match="finite|range|boolean|containment|metric"):
        selector.analyse_development(rows, protocol_digest=PROTOCOL)


def test_git_state_treats_modified_tracked_selected_artifact_as_dirty(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    selected = result_dir / "spade-selected-protocol.json"
    selected.write_text("{}\n")
    subprocess.run(["git", "add", "results/spade-selected-protocol.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    selected.write_text('{"tampered":true}\n')
    _, dirty = runner.git_state(tmp_path)
    assert dirty is True


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
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    for family in runner.DEVELOPMENT_FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        raw = tmp_path / f"spade-development-{family}-000-050.jsonl.gz"
        raw_hash = write_jsonl_gzip(raw, family_rows, protocol_digest=PROTOCOL)
        resume_path = runner.resume_checkpoint_path(raw)
        resume_payload = runner._resume_payload(
            family=family,
            start=0,
            stop=50,
            raw_file=raw.name,
            rows=family_rows,
            metadata=metadata,
            smoke=False,
            command_args=(),
            expected_raw_sha256=raw_hash,
        )
        resume_hash = runner._write_resume_checkpoint(resume_path, resume_payload)
        manifest = runner.make_shard_manifest(
            family=family,
            start=0,
            stop=50,
            row_count=len(family_rows),
            raw_file=raw.name,
            raw_sha256=raw_hash,
            resume_file=resume_path.name,
            resume_sha256=resume_hash,
            row_chain_head=resume_payload["row_chain_head"],
            metadata=metadata,
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
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(selector, "registered_metadata", lambda _root: metadata)
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    analysis_path = tmp_path / "results" / "spade-development-analysis.json"
    selected_path = tmp_path / "results" / "spade-selected-protocol.json"
    with pytest.raises(ValueError, match="exact registered path"):
        selector.select_from_shards(
            manifests,
            analysis_output=tmp_path / "wrong-analysis.json",
            selected_output=selected_path,
            repo_root=tmp_path,
        )
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
    assert selected["generator_manifest_sha256"] == GENERATOR_MANIFEST
    assert len(selected["development_artifacts"]) == 5
    assert selected["selected_canonical_config"]["opening"] == 44
    assert selected["selected_canonical_config"]["policy"] == "fixed_hybrid"
    assert selected["selection_trace"]["rule"] == "unanimous_lofo_consensus"
    assert len(selected["lofo_folds"]) == 5
    assert hashlib.sha256(analysis_path.read_bytes()).hexdigest() == selected["analysis_sha256"]

    with pytest.raises(ValueError, match="write-once|already exists"):
        selector.select_from_shards(
            manifests,
            analysis_output=analysis_path,
            selected_output=selected_path,
            repo_root=tmp_path,
        )

    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, True))
    with pytest.raises(ValueError, match="dirty"):
        selector.selection_payload_from_shards(
            manifests,
            repo_root=tmp_path,
        )

    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    sidecar = Path(str(tmp_path / "spade-development-hill-000-050.jsonl.gz") + ".sha256")
    sidecar.unlink()
    with pytest.raises(ValueError, match="SHA-256|sidecar|hashed"):
        selector.selection_payload_from_shards(
            manifests,
            repo_root=tmp_path,
        )


def test_selection_rejects_preexisting_analysis_without_overwriting_it(
    tmp_path, complete_rows, monkeypatch
):
    manifests = _write_complete_shards(tmp_path, complete_rows)
    monkeypatch.setattr(
        selector, "registered_metadata", lambda _root: _registered_metadata()
    )
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    analysis_path = tmp_path / "results" / "spade-development-analysis.json"
    selected_path = tmp_path / "results" / "spade-selected-protocol.json"
    analysis_path.parent.mkdir()
    analysis_path.write_bytes(b"pre-existing analysis\n")

    with pytest.raises(ValueError, match="write-once|already exists"):
        selector.select_from_shards(
            manifests,
            analysis_output=analysis_path,
            selected_output=selected_path,
            repo_root=tmp_path,
        )

    assert analysis_path.read_bytes() == b"pre-existing analysis\n"
    assert not selected_path.exists()


@pytest.mark.parametrize(
    "racing_name",
    ["spade-development-analysis.json", "spade-selected-protocol.json"],
)
def test_selection_never_overwrites_a_target_that_appears_during_promotion(
    tmp_path, complete_rows, monkeypatch, racing_name
):
    manifests = _write_complete_shards(tmp_path, complete_rows)
    monkeypatch.setattr(
        selector, "registered_metadata", lambda _root: _registered_metadata()
    )
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    analysis_path = tmp_path / "results" / "spade-development-analysis.json"
    selected_path = tmp_path / "results" / "spade-selected-protocol.json"
    racing_path = tmp_path / "results" / racing_name
    real_link = selector.os.link
    raced = False

    def race_link(source, destination):
        nonlocal raced
        if not raced and Path(destination) == racing_path:
            raced = True
            racing_path.write_bytes(b"racing artifact\n")
        real_link(source, destination)

    monkeypatch.setattr(selector.os, "link", race_link)
    with pytest.raises(ValueError, match="write-once|appeared|already exists"):
        selector.select_from_shards(
            manifests,
            analysis_output=analysis_path,
            selected_output=selected_path,
            repo_root=tmp_path,
        )

    assert racing_path.read_bytes() == b"racing artifact\n"
    other_path = selected_path if racing_path == analysis_path else analysis_path
    assert not other_path.exists()
    assert set(racing_path.parent.iterdir()) == {racing_path}


def test_selection_rejects_incomplete_or_wrong_digest_manifest(tmp_path, complete_rows, monkeypatch):
    manifests = _write_complete_shards(tmp_path, complete_rows)
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
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
            analysis_output=tmp_path / "results" / "spade-development-analysis.json",
            selected_output=tmp_path / "results" / "spade-selected-protocol.json",
            repo_root=tmp_path,
        )

    manifests = _write_complete_shards(tmp_path, complete_rows)
    broken = json.loads(manifests[0].read_text())
    broken["study_protocol_digest"] = "0" * 64
    manifests[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="protocol digest"):
        selector.select_from_shards(
            manifests,
            analysis_output=tmp_path / "results" / "spade-development-analysis.json",
            selected_output=tmp_path / "results" / "spade-selected-protocol.json",
            repo_root=tmp_path,
        )


def test_selection_rejects_tampered_development_generator_manifest(tmp_path, complete_rows, monkeypatch):
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(selector, "registered_metadata", lambda _root: metadata)
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))

    manifests = _write_complete_shards(tmp_path / "manifest-drift", complete_rows)
    broken_manifest = json.loads(manifests[0].read_text())
    broken_manifest["generator_manifest_sha256"] = "0" * 64
    manifests[0].write_text(json.dumps(broken_manifest))
    with pytest.raises(ValueError, match="generator.manifest"):
        selector.selection_payload_from_shards(manifests, repo_root=tmp_path)

    tampered_rows = copy.deepcopy(complete_rows)
    tampered_rows[0]["parent_artifacts"]["generator_manifest"] = "0" * 64
    manifests = _write_complete_shards(tmp_path / "row-drift", tampered_rows)
    with pytest.raises(ValueError, match="generator.manifest"):
        selector.selection_payload_from_shards(manifests, repo_root=tmp_path)
