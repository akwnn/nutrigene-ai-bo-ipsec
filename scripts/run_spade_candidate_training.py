#!/usr/bin/env python3
"""Run a separately identified, TEST_ONLY SPADE candidate training shard.

This runner exists for protocol sensitivity work after a frozen registered protocol has
failed.  It deliberately uses the registered campaign generator and seed contracts, but
changes only the explicitly supplied scoring settings.  Its output can inform a new
registration; it is never accepted as a registered B5 or lockbox artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from boec.replay import unit_bounds  # noqa: E402
from boec.spade import SpadeConfig, run_qlognei48, run_sobol48, run_spade  # noqa: E402
from boec.spade_study import (  # noqa: E402
    REGISTERED_SCORING_SETTINGS,
    ScoringExecutionSettings,
    build_study_row,
    score_campaign,
)
import run_spade_development as development  # noqa: E402


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _candidate_metadata() -> dict[str, object]:
    """Read protocol metadata without pretending the frozen manifest is current.

    The registered runner intentionally rejects a stale frozen manifest.  Candidate
    training is a TEST_ONLY experiment, so it records the current source digest and
    dirty state instead of weakening that registered-artifact guard.
    """
    try:
        return development.registered_metadata(ROOT)
    except ValueError as exc:
        if "generator manifest digest mismatch" not in str(exc):
            raise
        config = development.yaml.safe_load((ROOT / development._CONFIG_PATH).read_text(encoding="utf-8"))
        protocol = config["protocol"]
        protocol_digest = hashlib.sha256(development._canonical_json(protocol).encode("utf-8")).hexdigest()
        commit, dirty = development.git_state(ROOT)
        return {
            "study_protocol_digest": protocol_digest,
            "spec_digest": development._sha256(ROOT / development._SPEC_PATH),
            "config_digest": development._sha256(ROOT / development._CONFIG_PATH),
            "generator_digest": development._sha256(ROOT / development._GENERATOR_PATH),
            "generator_manifest_sha256": development._sha256(ROOT / development._GENERATOR_MANIFEST_PATH),
            "power_design_digest": development._sha256(ROOT / development._POWER_DESIGN_PATH),
            "power_engine_digest": development._sha256(ROOT / development._POWER_ENGINE_PATH),
            "power_planner_digest": development._sha256(ROOT / development._POWER_PLANNER_PATH),
            "source_commit": commit,
            "source_dirty": dirty,
        }


def _relabel_test_only(campaign: object) -> object:
    """Make the in-memory campaign agree with the TEST_ONLY scoring mode."""
    if getattr(campaign, "execution_mode", None) == "TEST_ONLY":
        return campaign
    import copy

    result = copy.copy(campaign)
    object.__setattr__(result, "execution_mode", "TEST_ONLY")
    object.__setattr__(result, "registered", False)
    return result


def _rows_for_key(
    family: str,
    key_index: int,
    *,
    metadata: Mapping[str, object],
    settings: ScoringExecutionSettings,
    command_args: Sequence[str],
) -> list[dict[str, object]]:
    instance_seed, campaign_seed = development.development_campaign_key(family, key_index)
    seeds = development.development_seed_identity(
        family=family, instance_seed=instance_seed, campaign_seed=campaign_seed
    )
    harness, threshold = development._development_threshold(
        family,
        instance_seed,
        seeds["noise"],
        seeds["threshold"],
        smoke=False,
        settings=settings,
    )
    _, evaluator, _ = development._development_oracle(family, instance_seed, seeds["noise"])
    rows: list[dict[str, object]] = []
    for arm_id in development.DEVELOPMENT_ARM_IDS:
        if arm_id in development.CANDIDATE_ARM_IDS:
            opening, policy = development.candidate_spec(arm_id)
            campaign = run_spade(
                evaluator,
                unit_bounds(6),
                SpadeConfig(opening=opening, policy=policy, root_seed=seeds["root"]),
                tau=threshold.tau,
                fast=False,
            )
        elif arm_id == "sobol48":
            campaign = run_sobol48(
                evaluator, unit_bounds(6), root_seed=seeds["root"], tau=threshold.tau, fast=False
            )
        elif arm_id == "qlognei48":
            campaign = run_qlognei48(
                evaluator, unit_bounds(6), root_seed=seeds["root"], tau=threshold.tau, fast=False
            )
        else:  # pragma: no cover - guarded by DEVELOPMENT_ARM_IDS
            raise ValueError(f"unsupported arm {arm_id!r}")
        score = score_campaign(
            _relabel_test_only(campaign),
            threshold.tau,
            harness.scorer(),
            sigma_rel=development._SIGMA_REL,
            sigma_add=development._SIGMA_ADD,
            gamma=development._GAMMA,
            alpha=development._ALPHA,
            scoring_seed=seeds["scoring"],
            execution_mode="TEST_ONLY",
            settings=settings,
        )
        score_payload = score.as_dict()
        rows.append(
            build_study_row(
                score,
                study_protocol_digest=str(metadata["study_protocol_digest"]),
                spec_digest=str(metadata["spec_digest"]),
                config_digest=str(metadata["config_digest"]),
                source_commit=str(metadata["source_commit"]),
                source_dirty=bool(metadata["source_dirty"]),
                command_args=command_args,
                parent_artifacts={
                    "spec": str(metadata["spec_digest"]),
                    "config": str(metadata["config_digest"]),
                    "generator": str(metadata["generator_digest"]),
                    "generator_manifest": str(metadata["generator_manifest_sha256"]),
                    "seed_contract": development.seed_contract_digest(seeds),
                    "candidate_menu_contract": development.candidate_menu_contract_digest(
                        root_seed=seeds["root"], size=campaign.effective_settings.candidate_menu_size
                    ),
                    "scorer_contract": development.scorer_contract_digest(score_payload),
                },
                family=family,
                instance_seed=instance_seed,
                campaign_seed=campaign_seed,
                root_seed=seeds["root"],
                derived_seeds=development.matched_seed_identity(
                    root_seed=seeds["root"],
                    noise_seed=seeds["noise"],
                    threshold_seed=seeds["threshold"],
                    scoring_seed=seeds["scoring"],
                ),
            )
        )
    return rows


def _summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    by_family: dict[str, dict[str, dict[str, object]]] = {}
    for family in sorted({str(row["family"]) for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        by_family[family] = {}
        for arm in development.DEVELOPMENT_ARM_IDS:
            arm_rows = [row for row in family_rows if development._development_arm_id(row) == arm]
            answered = [row for row in arm_rows if row["scores"]["certificate_nonempty"]]
            contained = [
                row for row in answered if row["scores"]["certificate_empirical_containment"] is True
            ]
            by_family[family][arm] = {
                "n": len(arm_rows),
                "ans": len(answered) / len(arm_rows) if arm_rows else 0.0,
                "emp": len(contained) / len(answered) if answered else None,
            }
    survivors = [
        arm
        for arm in development.CANDIDATE_ARM_IDS
        if all(
            by_family[family][arm]["ans"] >= 0.5
            and by_family[family][arm]["emp"] is not None
            and by_family[family][arm]["emp"] >= 0.9
            for family in by_family
        )
    ]
    return {"families": by_family, "survivors": survivors, "row_count": len(rows)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", nargs="+", choices=("hill", "levy"), required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=50)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args(argv)
    if not 0 <= args.start < args.stop <= 50:
        raise ValueError("range must satisfy 0 <= start < stop <= 50")
    if args.out.resolve().is_relative_to((ROOT / "results").resolve()):
        raise ValueError("TEST_ONLY output cannot be written under registered results/")

    metadata = _candidate_metadata()
    settings = replace(
        REGISTERED_SCORING_SETTINGS,
        certificate_bootstrap_bags=1,
        conformal_lower_calibration=True,
    )
    command_args = tuple(sys.argv[1:] if argv is None else argv)
    checkpoint = args.checkpoint or Path(str(args.out) + ".checkpoint.json")
    rows: list[dict[str, object]] = []
    if checkpoint.is_file():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        if payload.get("settings_digest") != settings.digest or payload.get("families") != args.family:
            raise ValueError("candidate checkpoint settings or family mismatch")
        rows = list(payload.get("rows", []))
    done = {
        (row["family"], row["instance_seed"], development._development_arm_id(row))
        for row in rows
    }
    for family in args.family:
        for key_index in range(args.start, args.stop):
            generated = _rows_for_key(
                family,
                key_index,
                metadata=metadata,
                settings=settings,
                command_args=command_args,
            )
            for row in generated:
                identity = (
                    row["family"],
                    row["instance_seed"],
                    development._development_arm_id(row),
                )
                if identity not in done:
                    rows.append(row)
                    done.add(identity)
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            tmp = checkpoint.with_suffix(checkpoint.suffix + ".tmp")
            tmp.write_text(
                _canonical(
                    {
                        "schema": "boec-spade-candidate-training-checkpoint-v1",
                        "execution_mode": "TEST_ONLY",
                        "settings_digest": settings.digest,
                        "families": list(args.family),
                        "start": args.start,
                        "stop": args.stop,
                        "rows": rows,
                    }
                )
            )
            os.replace(tmp, checkpoint)
    report = {
        "schema": "boec-spade-candidate-training-v1",
        "execution_mode": "TEST_ONLY",
        "settings": asdict(settings),
        "settings_digest": settings.digest,
        "protocol_digest": metadata["study_protocol_digest"],
        "source_commit": metadata["source_commit"],
        "families": list(args.family),
        "start": args.start,
        "stop": args.stop,
        **_summarize(rows),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ("schema", "execution_mode", "settings_digest", "survivors", "row_count")}, indent=2))
    return 0 if report["survivors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
