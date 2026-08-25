#!/usr/bin/env python3
"""Validate the frozen development grid and select one auditable SPADE protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec.spade import SpadeConfig  # noqa: E402
from scripts import run_spade_development as development  # noqa: E402


ANALYSIS_SCHEMA = "boec-spade-development-analysis-v1"
SELECTION_SCHEMA = "boec-spade-selected-protocol-v1"
ANSWER_RATE_MINIMUM = 0.50
EMPIRICAL_CONTAINMENT_MINIMUM = 0.90
REGRET_NONINFERIORITY_MARGIN = 0.02
ONE_SIDED_CONFIDENCE = 0.95
TIE_POLICY_ORDER = ("fixed_hybrid", "validity_gated", "staged")
PAIRED_BOUND_METHOD = "one_sided_student_t_mean_difference_df_n_minus_1"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_digest(value: object, name: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"{name} must be a {length}-character hexadecimal digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value.lower()


def _atomic_json(path: Path, payload: Mapping[str, object]) -> str:
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
    return _sha256_bytes(data)


def registered_metadata(repo_root: Path = ROOT) -> dict[str, object]:
    return development.registered_metadata(repo_root)


def git_state(repo_root: Path = ROOT) -> tuple[str, bool]:
    return development.git_state(repo_root)


def development_arm_id(row: Mapping[str, object]) -> str:
    return development._development_arm_id(row)


def _key(row: Mapping[str, object]) -> tuple[int, int]:
    instance_seed = row.get("instance_seed")
    campaign_seed = row.get("campaign_seed")
    if (
        isinstance(instance_seed, bool)
        or not isinstance(instance_seed, int)
        or instance_seed < 0
        or isinstance(campaign_seed, bool)
        or not isinstance(campaign_seed, int)
        or campaign_seed < 0
    ):
        raise ValueError("development row has invalid campaign key")
    return instance_seed, campaign_seed


def validate_development_grid(
    rows: Sequence[Mapping[str, object]], *, protocol_digest: str
) -> dict[str, object]:
    expected_protocol = str(protocol_digest)
    expected_identities = {
        (family, *development.development_campaign_key(family, key_index), arm_id)
        for family in development.DEVELOPMENT_FAMILIES
        for key_index in range(development.CAMPAIGNS_PER_FAMILY)
        for arm_id in development.DEVELOPMENT_ARM_IDS
    }
    seen: set[tuple[str, int, int, str]] = set()
    family_keys: dict[str, set[tuple[int, int]]] = {
        family: set() for family in development.DEVELOPMENT_FAMILIES
    }
    source_commits: set[str] = set()
    spec_digests: set[str] = set()
    config_digests: set[str] = set()
    generator_digests: set[str] = set()
    for index, row in enumerate(rows):
        family = row.get("family")
        if family not in development.DEVELOPMENT_FAMILIES:
            raise ValueError(f"row {index} has an unregistered development family")
        if row.get("protocol_digest") != expected_protocol:
            raise ValueError(f"row {index} has the wrong study protocol digest")
        if row.get("budget") != 48 or row.get("terminal_rule") != "P":
            raise ValueError(f"row {index} violates the exact 48/Rule-P contract")
        if row.get("source_dirty") is not False:
            raise ValueError(f"row {index} was produced from a dirty source tree")
        spec_digest = _require_digest(row.get("spec_digest"), f"row {index} spec digest")
        config_digest = _require_digest(row.get("config_digest"), f"row {index} config digest")
        parent_artifacts = row.get("parent_artifacts")
        if not isinstance(parent_artifacts, Mapping) or set(parent_artifacts) != {
            "spec",
            "config",
            "generator",
        }:
            raise ValueError(f"row {index} parent artifacts drift")
        generator_digest = _require_digest(
            parent_artifacts.get("generator"), f"row {index} generator digest"
        )
        if parent_artifacts.get("spec") != spec_digest or parent_artifacts.get("config") != config_digest:
            raise ValueError(f"row {index} parent spec/config digest mismatch")
        score = row.get("scores")
        if not isinstance(score, Mapping):
            raise ValueError(f"row {index} has no score mapping")
        if (
            score.get("budget") != 48
            or score.get("terminal_rule") != "P"
            or score.get("arm") != row.get("arm")
            or score.get("protocol_digest") != row.get("arm_protocol_digest")
            or score.get("run_digest") != row.get("run_digest")
            or score.get("execution_mode") != "REGISTERED"
        ):
            raise ValueError(f"row {index} score identity or registered mode drift")
        campaign_key = row.get("campaign_key")
        if not isinstance(campaign_key, Mapping):
            raise ValueError(f"row {index} has no campaign_key")
        key = _key(row)
        expected_campaign_key = {
            "family": family,
            "instance_seed": key[0],
            "campaign_seed": key[1],
            "arm": row.get("arm"),
            "arm_protocol_digest": row.get("arm_protocol_digest"),
            "run_digest": row.get("run_digest"),
        }
        if dict(campaign_key) != expected_campaign_key:
            raise ValueError(f"row {index} campaign key identity drift")
        arm_id = development_arm_id(row)
        identity = (family, key[0], key[1], arm_id)
        if identity in seen:
            raise ValueError(f"duplicate development row {identity}")
        seen.add(identity)
        family_keys[family].add(key)
        source_commits.add(str(row.get("source_commit")))
        spec_digests.add(spec_digest)
        config_digests.add(config_digest)
        generator_digests.add(generator_digest)
    unknown = seen - expected_identities
    missing = expected_identities - seen
    if unknown:
        raise ValueError(f"development grid contains unregistered rows: {sorted(unknown)[:3]}")
    if missing:
        raise ValueError(
            f"development grid is incomplete; missing {len(missing)} registered arm rows"
        )
    if len(rows) != len(expected_identities):
        raise ValueError("development grid row count is not exactly 2,750")
    if any(len(keys) != 50 for keys in family_keys.values()):
        raise ValueError("development grid does not have 50 common keys per family")
    if (
        len(source_commits) != 1
        or len(spec_digests) != 1
        or len(config_digests) != 1
        or len(generator_digests) != 1
    ):
        raise ValueError("development grid mixes source/spec/config/generator identities")
    return {
        "row_count": len(rows),
        "families": list(development.DEVELOPMENT_FAMILIES),
        "campaigns_per_family": development.CAMPAIGNS_PER_FAMILY,
        "candidate_count": len(development.CANDIDATE_ARM_IDS),
        "control_count": len(development.CONTROL_ARMS),
        "source_commit": next(iter(source_commits)),
        "spec_digest": next(iter(spec_digests)),
        "config_digest": next(iter(config_digests)),
        "generator_digest": next(iter(generator_digests)),
    }


def paired_upper_confidence(
    differences: Sequence[float], *, confidence: float = ONE_SIDED_CONFIDENCE
) -> float:
    values = np.asarray(differences, dtype=float)
    if values.ndim != 1 or values.size < 2 or not np.isfinite(values).all():
        raise ValueError("paired confidence bound requires at least two finite differences")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    mean = float(values.mean())
    standard_error = float(values.std(ddof=1) / math.sqrt(values.size))
    if standard_error == 0.0:
        return mean
    return mean + float(t.ppf(confidence, values.size - 1)) * standard_error


def _indexed_rows(
    rows: Sequence[Mapping[str, object]],
) -> dict[tuple[str, tuple[int, int], str], Mapping[str, object]]:
    result = {}
    for row in rows:
        identity = (str(row["family"]), _key(row), development_arm_id(row))
        if identity in result:
            raise ValueError(f"duplicate development row {identity}")
        result[identity] = row
    return result


def _candidate_metrics(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    indexed = _indexed_rows(rows)
    output: dict[str, dict[str, object]] = {}
    for candidate in development.CANDIDATE_ARM_IDS:
        opening, policy = development.candidate_spec(candidate)
        family_metrics = {}
        for family in development.DEVELOPMENT_FAMILIES:
            candidate_rows = [
                indexed[(family, development.development_campaign_key(family, key_index), candidate)]
                for key_index in range(development.CAMPAIGNS_PER_FAMILY)
            ]
            sobol_rows = [
                indexed[(family, development.development_campaign_key(family, key_index), "sobol48")]
                for key_index in range(development.CAMPAIGNS_PER_FAMILY)
            ]
            qlognei_rows = [
                indexed[(family, development.development_campaign_key(family, key_index), "qlognei48")]
                for key_index in range(development.CAMPAIGNS_PER_FAMILY)
            ]
            nonempty = [bool(row["scores"]["certificate_nonempty"]) for row in candidate_rows]
            empirical = [
                bool(row["scores"]["certificate_empirical_containment"])
                for row in candidate_rows
                if row["scores"]["certificate_nonempty"]
            ]
            regret_differences = [
                float(candidate_row["scores"]["regret_rule_p"])
                - float(reference_row["scores"]["regret_rule_p"])
                for candidate_row, reference_row in zip(candidate_rows, qlognei_rows)
            ]
            map_differences = [
                float(candidate_row["scores"]["map_loss"])
                - float(reference_row["scores"]["map_loss"])
                for candidate_row, reference_row in zip(candidate_rows, sobol_rows)
            ]
            family_metrics[family] = {
                "n_campaigns": len(candidate_rows),
                "answer_count": sum(nonempty),
                "answer_rate": float(np.mean(nonempty)),
                "containment_denominator": len(empirical),
                "containment_successes": sum(empirical),
                "empirical_containment": float(np.mean(empirical)) if empirical else None,
                "mean_regret_difference_vs_qlognei48": float(np.mean(regret_differences)),
                "regret_upper_95_vs_qlognei48": paired_upper_confidence(regret_differences),
                "mean_map_difference_vs_sobol48": float(np.mean(map_differences)),
            }
        output[candidate] = {
            "opening": opening,
            "policy": policy,
            "rounds": development.rounds_for_opening(opening),
            "families": family_metrics,
        }
    return output


def _step1_failures(
    candidate: Mapping[str, object], families: Sequence[str]
) -> list[str]:
    failures = []
    family_metrics = candidate["families"]
    for family in families:
        metrics = family_metrics[family]
        if metrics["answer_rate"] < ANSWER_RATE_MINIMUM:
            failures.append(
                f"{family}: answer_rate={metrics['answer_rate']:.17g} < {ANSWER_RATE_MINIMUM}"
            )
        containment = metrics["empirical_containment"]
        if containment is None or containment < EMPIRICAL_CONTAINMENT_MINIMUM:
            rendered = "null" if containment is None else f"{containment:.17g}"
            failures.append(
                f"{family}: empirical_containment={rendered} < "
                f"{EMPIRICAL_CONTAINMENT_MINIMUM}"
            )
    return failures


def _step2_failures(
    candidate: Mapping[str, object], families: Sequence[str]
) -> list[str]:
    failures = []
    family_metrics = candidate["families"]
    for family in families:
        upper = family_metrics[family]["regret_upper_95_vs_qlognei48"]
        if upper > REGRET_NONINFERIORITY_MARGIN:
            failures.append(
                f"{family}: regret_upper_95={upper:.17g} > "
                f"{REGRET_NONINFERIORITY_MARGIN}"
            )
    return failures


def _lexicographic_select(
    metrics: Mapping[str, Mapping[str, object]], families: Sequence[str]
) -> dict[str, object]:
    considered = list(development.CANDIDATE_ARM_IDS)
    step1_failures = {
        candidate: _step1_failures(metrics[candidate], families)
        for candidate in considered
    }
    step1_survivors = [candidate for candidate in considered if not step1_failures[candidate]]
    step2_failures = {
        candidate: _step2_failures(metrics[candidate], families)
        for candidate in considered
    }
    step2_survivors = [
        candidate for candidate in step1_survivors if not step2_failures[candidate]
    ]
    trace: dict[str, object] = {
        "step1": {
            "families": list(families),
            "answer_rate_minimum": ANSWER_RATE_MINIMUM,
            "empirical_containment_minimum": EMPIRICAL_CONTAINMENT_MINIMUM,
            "considered": considered,
            "failures": step1_failures,
            "survivors": step1_survivors,
        },
        "step2": {
            "families": list(families),
            "one_sided_confidence": ONE_SIDED_CONFIDENCE,
            "regret_noninferiority_margin": REGRET_NONINFERIORITY_MARGIN,
            "considered": step1_survivors,
            "failures": {candidate: step2_failures[candidate] for candidate in step1_survivors},
            "survivors": step2_survivors,
        },
        "step3": {
            "criterion": "smallest_worst_family_mean_map_loss_relative_to_sobol48",
            "scores": {},
            "minimum": None,
            "survivors": [],
            "skipped_reason": None,
        },
        "step4": {
            "criteria": ["fewer_rounds", "larger_opening", "policy_order"],
            "policy_order": list(TIE_POLICY_ORDER),
            "input": [],
            "after_fewer_rounds": [],
            "after_larger_opening": [],
            "after_policy_order": [],
            "selected": None,
            "skipped_reason": None,
        },
    }
    if not step2_survivors:
        trace["step3"]["skipped_reason"] = "NO_SELECTION: no candidate survived steps 1-2"
        trace["step4"]["skipped_reason"] = "NO_SELECTION: no candidate survived steps 1-2"
        return {
            "status": "NO_SELECTION",
            "selected_candidate": None,
            "trace": trace,
            "step1_failures": step1_failures,
            "step2_failures": step2_failures,
        }
    map_scores = {
        candidate: max(
            metrics[candidate]["families"][family]["mean_map_difference_vs_sobol48"]
            for family in families
        )
        for candidate in step2_survivors
    }
    minimum = min(map_scores.values())
    step3_survivors = [
        candidate for candidate in step2_survivors if map_scores[candidate] == minimum
    ]
    trace["step3"].update(
        scores=map_scores,
        minimum=minimum,
        survivors=step3_survivors,
    )
    minimum_rounds = min(metrics[candidate]["rounds"] for candidate in step3_survivors)
    after_rounds = [
        candidate
        for candidate in step3_survivors
        if metrics[candidate]["rounds"] == minimum_rounds
    ]
    maximum_opening = max(metrics[candidate]["opening"] for candidate in after_rounds)
    after_opening = [
        candidate
        for candidate in after_rounds
        if metrics[candidate]["opening"] == maximum_opening
    ]
    minimum_policy_rank = min(
        TIE_POLICY_ORDER.index(str(metrics[candidate]["policy"]))
        for candidate in after_opening
    )
    after_policy = [
        candidate
        for candidate in after_opening
        if TIE_POLICY_ORDER.index(str(metrics[candidate]["policy"])) == minimum_policy_rank
    ]
    if len(after_policy) != 1:
        raise RuntimeError("prespecified tie-break did not produce exactly one candidate")
    selected = after_policy[0]
    trace["step4"].update(
        input=step3_survivors,
        after_fewer_rounds=after_rounds,
        after_larger_opening=after_opening,
        after_policy_order=after_policy,
        selected=selected,
    )
    return {
        "status": "SELECTED",
        "selected_candidate": selected,
        "trace": trace,
        "step1_failures": step1_failures,
        "step2_failures": step2_failures,
    }


def analyse_development(
    rows: Sequence[Mapping[str, object]], *, protocol_digest: str
) -> dict[str, object]:
    grid = validate_development_grid(rows, protocol_digest=protocol_digest)
    metrics = _candidate_metrics(rows)
    full = _lexicographic_select(metrics, development.DEVELOPMENT_FAMILIES)
    candidates = {}
    for candidate in development.CANDIDATE_ARM_IDS:
        candidate_metrics = dict(metrics[candidate])
        candidate_metrics["step1_failures"] = full["step1_failures"][candidate]
        candidate_metrics["step1_pass"] = not candidate_metrics["step1_failures"]
        candidate_metrics["step2_failures"] = full["step2_failures"][candidate]
        candidate_metrics["step2_pass"] = (
            candidate_metrics["step1_pass"] and not candidate_metrics["step2_failures"]
        )
        candidates[candidate] = candidate_metrics
    lofo_folds = []
    for held_out in development.DEVELOPMENT_FAMILIES:
        training = tuple(
            family for family in development.DEVELOPMENT_FAMILIES if family != held_out
        )
        fold = _lexicographic_select(metrics, training)
        selected = fold["selected_candidate"]
        lofo_folds.append(
            {
                "held_out_family": held_out,
                "training_families": list(training),
                "status": fold["status"],
                "selected_candidate": selected,
                "training_selection_trace": fold["trace"],
                "held_out_metrics": (
                    None if selected is None else metrics[selected]["families"][held_out]
                ),
            }
        )
    payload = {
        "schema": ANALYSIS_SCHEMA,
        "status": full["status"],
        "selected_candidate": full["selected_candidate"],
        "selection_method": "nested_leave_one_family_out_with_frozen_full_grid_rule",
        "paired_upper_bound_method": PAIRED_BOUND_METHOD,
        "grid": grid,
        "candidates": candidates,
        "lofo_folds": lofo_folds,
        "selection_trace": full["trace"],
    }
    _canonical_json(payload)
    return payload


def _load_complete_shards(
    manifest_paths: Sequence[str | Path],
    *,
    metadata: Mapping[str, object],
    source_commit: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not manifest_paths:
        raise ValueError("at least one development shard manifest is required")
    rows: list[dict[str, object]] = []
    artifacts = []
    ranges: dict[str, list[tuple[int, int]]] = {
        family: [] for family in development.DEVELOPMENT_FAMILIES
    }
    for supplied in manifest_paths:
        manifest_path = Path(supplied)
        if not manifest_path.is_file():
            raise ValueError(f"development manifest is missing: {manifest_path}")
        manifest_bytes = manifest_path.read_bytes()
        try:
            parsed = json.loads(manifest_bytes)
        except json.JSONDecodeError as exc:
            raise ValueError(f"development manifest is not JSON: {manifest_path}") from exc
        manifest = development.validate_shard_manifest(parsed)
        expected = {
            "study_protocol_digest": metadata["study_protocol_digest"],
            "spec_digest": metadata["spec_digest"],
            "config_digest": metadata["config_digest"],
            "generator_digest": metadata["generator_digest"],
            "source_commit": source_commit,
            "source_dirty": False,
        }
        for name, value in expected.items():
            if manifest[name] != value:
                label = "protocol digest" if name == "study_protocol_digest" else name
                raise ValueError(f"development manifest {label} mismatch")
        raw_path = manifest_path.parent / str(manifest["raw_file"])
        shard_rows = development.read_shard_rows(
            raw_path, str(metadata["study_protocol_digest"])
        )
        raw_hash = _sha256_bytes(raw_path.read_bytes())
        if raw_hash != manifest["raw_sha256"]:
            raise ValueError("development raw SHA-256 does not match its manifest")
        if len(shard_rows) != manifest["row_count"]:
            raise ValueError("development manifest row count does not match raw shard")
        for row in shard_rows:
            expected_row_identity = {
                "protocol_digest": metadata["study_protocol_digest"],
                "spec_digest": metadata["spec_digest"],
                "config_digest": metadata["config_digest"],
                "source_commit": source_commit,
                "source_dirty": False,
                "family": manifest["family"],
            }
            for name, value in expected_row_identity.items():
                if row.get(name) != value:
                    raise ValueError(f"development row {name} mismatch")
            if row.get("parent_artifacts") != {
                "spec": metadata["spec_digest"],
                "config": metadata["config_digest"],
                "generator": metadata["generator_digest"],
            }:
                raise ValueError("development row parent artifact digest mismatch")
            campaign_seed = row.get("campaign_seed")
            instance_seed = row.get("instance_seed")
            valid_keys = {
                development.development_campaign_key(str(manifest["family"]), key_index)
                for key_index in range(int(manifest["start"]), int(manifest["stop"]))
            }
            if (instance_seed, campaign_seed) not in valid_keys:
                raise ValueError("development row lies outside its manifest key range")
        ranges[str(manifest["family"])].append((int(manifest["start"]), int(manifest["stop"])))
        rows.extend(shard_rows)
        artifacts.append(
            {
                "family": manifest["family"],
                "start": manifest["start"],
                "stop": manifest["stop"],
                "raw_file": raw_path.name,
                "raw_sha256": raw_hash,
                "manifest_file": manifest_path.name,
                "manifest_sha256": _sha256_bytes(manifest_bytes),
            }
        )
    for family, intervals in ranges.items():
        ordered = sorted(intervals)
        cursor = 0
        for start, stop in ordered:
            if start != cursor:
                raise ValueError(f"development manifests are incomplete or overlap for {family}")
            cursor = stop
        if cursor != development.CAMPAIGNS_PER_FAMILY:
            raise ValueError(f"development manifests are incomplete for {family}")
    artifacts.sort(key=lambda item: (item["family"], item["start"], item["stop"]))
    return rows, artifacts


def select_from_shards(
    manifest_paths: Sequence[str | Path],
    *,
    analysis_output: str | Path,
    selected_output: str | Path,
    repo_root: Path = ROOT,
) -> dict[str, object]:
    metadata = registered_metadata(repo_root)
    source_commit, dirty = git_state(repo_root)
    if dirty:
        raise ValueError("protocol selection refuses a dirty source tree")
    if metadata["source_commit"] != source_commit or metadata["source_dirty"]:
        raise ValueError("registered metadata does not describe the current clean source commit")
    rows, artifacts = _load_complete_shards(
        manifest_paths,
        metadata=metadata,
        source_commit=source_commit,
    )
    analysis = analyse_development(
        rows,
        protocol_digest=str(metadata["study_protocol_digest"]),
    )
    analysis_path = Path(analysis_output)
    analysis_sha = _atomic_json(analysis_path, analysis)
    selected_candidate = analysis["selected_candidate"]
    if selected_candidate is None:
        canonical_config = None
        canonical_config_json = None
        template_digest = None
    else:
        opening, policy = development.candidate_spec(str(selected_candidate))
        template = SpadeConfig(opening=opening, policy=policy, root_seed=0)
        canonical_config_json = template.canonical_json
        canonical_config = json.loads(canonical_config_json)
        template_digest = template.protocol_digest
    selected = {
        "schema": SELECTION_SCHEMA,
        "status": analysis["status"],
        "selected_candidate": selected_candidate,
        "source_commit": source_commit,
        "study_protocol_digest": metadata["study_protocol_digest"],
        "spec_digest": metadata["spec_digest"],
        "config_digest": metadata["config_digest"],
        "generator_digest": metadata["generator_digest"],
        "development_artifacts": artifacts,
        "analysis_file": analysis_path.name,
        "analysis_sha256": analysis_sha,
        "selection_trace_digest": _sha256_bytes(
            _canonical_json(analysis["selection_trace"]).encode("utf-8")
        ),
        "selected_canonical_config": canonical_config,
        "selected_canonical_config_json": canonical_config_json,
        "selected_template_protocol_digest": template_digest,
        "campaign_root_seed_binding": "sha256_labelled_derived_per_campaign",
    }
    _atomic_json(Path(selected_output), selected)
    return selected


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument(
        "--analysis-out",
        type=Path,
        default=ROOT / "results" / "spade-development-analysis.json",
    )
    parser.add_argument(
        "--selected-out",
        type=Path,
        default=ROOT / "results" / "spade-selected-protocol.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    selected = select_from_shards(
        args.manifest,
        analysis_output=args.analysis_out,
        selected_output=args.selected_out,
    )
    print(_canonical_json(selected))
    return 0 if selected["status"] == "SELECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
