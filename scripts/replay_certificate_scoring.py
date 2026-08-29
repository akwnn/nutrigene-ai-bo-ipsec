#!/usr/bin/env python3
"""Re-score archived development shards with alternate certificate settings.

Deterministically re-executes each stored campaign from its sealed seeds, then scores
with the requested :class:`ScoringExecutionSettings`. Used for B3 bagged-certificate
offline gate analysis without mutating archived shard digests.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from boec.replay import unit_bounds  # noqa: E402
from boec.spade import SpadeConfig, run_qlognei48, run_sobol48, run_spade  # noqa: E402
from boec.spade_study import (  # noqa: E402
    REGISTERED_SCORING_SETTINGS,
    ScoringExecutionSettings,
    score_campaign,
)

import run_spade_development as development  # noqa: E402


def _load_rows(path: Path) -> list[dict]:
    if path.suffix == ".gz":
        from boec.spade_study import read_jsonl_gzip

        return list(read_jsonl_gzip(path))
    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and "rows" in payload:
        return payload["rows"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"unsupported shard format: {path}")


# Archived shards may predate the unified 5-arm product grid.
_HISTORICAL_ARM_LAYOUTS = (
    # Pre-B3: 9 SPADE + 2 controls
    tuple(
        f"spade-o{opening}-{policy}"
        for opening in (32, 40, 44)
        for policy in ("staged", "fixed_hybrid", "validity_gated")
    )
    + ("sobol48", "qlognei48"),
    # B3/B4: 10 SPADE (cert_targeted on o32) + 2 controls
    tuple(
        f"spade-o{opening}-{policy}"
        for opening in (32, 40, 44)
        for policy in (
            ("staged", "fixed_hybrid", "validity_gated", "certificate_targeted")
            if opening == 32
            else ("staged", "fixed_hybrid", "validity_gated")
        )
    )
    + ("sobol48", "qlognei48"),
)


def _resolve_arm_id(row: dict, all_rows: list[dict]) -> str:
    family = row["family"]
    instance_seed = int(row["instance_seed"])
    campaign_seed = int(row["campaign_seed"])
    group = [
        item
        for item in all_rows
        if item["family"] == family
        and int(item["instance_seed"]) == instance_seed
        and int(item["campaign_seed"]) == campaign_seed
    ]
    group.sort(key=lambda item: item["run_digest"])
    layouts = (*_HISTORICAL_ARM_LAYOUTS, development.DEVELOPMENT_ARM_IDS)
    for arm_ids in layouts:
        if len(group) == len(arm_ids):
            index = group.index(row)
            return arm_ids[index]
    raise ValueError(
        f"unexpected campaign arm count {len(group)} for "
        f"{family}/{instance_seed}/{campaign_seed}"
    )


def _rescore_row(
    row: dict,
    *,
    all_rows: list[dict],
    settings: ScoringExecutionSettings,
    alpha: float,
    execution_mode: str,
    fast: bool,
) -> dict:
    family = row["family"]
    instance_seed = int(row["instance_seed"])
    campaign_seed = int(row["campaign_seed"])
    arm_id = _resolve_arm_id(row, all_rows)
    registered_seeds = development.development_seed_identity(
        family=family,
        instance_seed=instance_seed,
        campaign_seed=campaign_seed,
    )
    harness, threshold = development._development_threshold(
        family,
        instance_seed,
        registered_seeds["noise"],
        registered_seeds["threshold"],
        smoke=fast,
        settings=settings if execution_mode == "TEST_ONLY" else None,
    )
    _, evaluator, _ = development._development_oracle(
        family, instance_seed, registered_seeds["noise"]
    )
    bounds = unit_bounds(6)
    campaign_root = registered_seeds["root"]
    if arm_id in development.CANDIDATE_ARM_IDS:
        opening, policy = development.candidate_spec(arm_id)
        campaign = run_spade(
            evaluator,
            bounds,
            SpadeConfig(opening=opening, policy=policy, root_seed=campaign_root),
            tau=threshold.tau,
            fast=fast,
        )
    elif arm_id == "sobol48":
        campaign = run_sobol48(
            evaluator, bounds, root_seed=campaign_root, tau=threshold.tau, fast=fast
        )
    elif arm_id == "qlognei48":
        campaign = run_qlognei48(
            evaluator, bounds, root_seed=campaign_root, tau=threshold.tau, fast=fast
        )
    else:
        raise ValueError(f"unsupported arm {arm_id!r}")
    score = score_campaign(
        campaign,
        threshold.tau,
        harness.scorer(),
        sigma_rel=development._SIGMA_REL,
        sigma_add=development._SIGMA_ADD,
        gamma=development._GAMMA,
        alpha=alpha,
        scoring_seed=registered_seeds["scoring"],
        execution_mode=execution_mode,
        settings=settings,
    )
    return {
        "arm": arm_id,
        "family": family,
        "instance_seed": instance_seed,
        "campaign_seed": campaign_seed,
        "certificate_nonempty": score.certificate_nonempty,
        "certificate_empirical_containment": score.certificate_empirical_containment,
        "certificate_abstention_reason": score.certificate_abstention_reason,
        "latent_inflation_factor": score.latent_inflation_factor,
        "scoring_settings_digest": score.scoring_settings_digest,
    }


def summarize(
    rescored: list[dict],
    *,
    families: tuple[str, ...],
) -> dict[str, object]:
  by_family: dict[str, dict[str, dict[str, object]]] = {family: {} for family in families}
  arms = sorted({row["arm"] for row in rescored})
  for family in families:
      subset = [row for row in rescored if row["family"] == family]
      for arm in arms:
          arm_rows = [row for row in subset if row["arm"] == arm]
          answered = [row for row in arm_rows if row["certificate_nonempty"]]
          contained = [
              row
              for row in answered
              if row["certificate_empirical_containment"] is True
          ]
          n = len(arm_rows)
          by_family[family][arm] = {
              "n": n,
              "ans": (len(answered) / n if n else 0.0),
              "emp": (len(contained) / len(answered) if answered else float("nan")),
          }
  survivors = [
      arm
      for arm in arms
      if all(
          by_family.get(family, {}).get(arm, {}).get("ans", 0.0) >= 0.5
          and by_family.get(family, {}).get(arm, {}).get("emp", 0.0) >= 0.9
          for family in families
      )
  ]
  return {"families": by_family, "survivors": survivors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shards", nargs="+", type=Path)
    parser.add_argument(
        "--families",
        nargs="+",
        default=["hill", "levy"],
        help="families that must jointly pass (default: hill levy)",
    )
    parser.add_argument(
        "--bootstrap-bags",
        type=int,
        default=5,
        help="certificate_bootstrap_bags for rescoring (default: 5)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=development._ALPHA,
        help="reliability alpha for rescoring",
    )
    parser.add_argument("--smoke", action="store_true", help="use reduced grids")
    parser.add_argument("--max-rows", type=int, help="limit rows per shard (debug)")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    base = development._SMOKE_SCORING_SETTINGS if args.smoke else REGISTERED_SCORING_SETTINGS
    settings = ScoringExecutionSettings(
        **{
            **asdict(base),
            "certificate_bootstrap_bags": int(args.bootstrap_bags),
        }
    )
    execution_mode = "TEST_ONLY"

    rows: list[dict] = []
    for shard in args.shards:
        rows.extend(_load_rows(shard))
    if args.max_rows is not None:
        subset = rows[: args.max_rows]
    else:
        subset = rows

    rescored = [
        _rescore_row(
            row,
            all_rows=rows,
            settings=settings,
            alpha=float(args.alpha),
            execution_mode=execution_mode,
            fast=bool(args.smoke),
        )
        for row in subset
    ]
    report = summarize(rescored, families=tuple(args.families))
    report["settings"] = asdict(settings)
    report["alpha"] = float(args.alpha)
    report["row_count"] = len(rescored)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0 if report["survivors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
