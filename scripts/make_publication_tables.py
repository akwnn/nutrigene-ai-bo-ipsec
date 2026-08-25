"""Build deterministic, evidence-locked tables for ``spade-final-2026-08-23``.

The builder is deliberately an artefact reader, not an analysis runner.  It
only aggregates the committed final-SPADE raw rows and adjudication records,
and refuses inputs that could silently mix registered cells or incomplete
campaigns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


STUDY_ID = "spade-final-2026-08-23"
SOURCE_NAMES = (
    "final-spade-c1.json",
    "final-spade-c2.json",
    "final-spade-c3.json",
    "final-spade-c4.json",
    "final-spade-s1.json",
    "final-spade-s2.json",
    "final-spade-s3.json",
    "final-spade-regret-pareto.json",
    "final-spade-kill-ledger.json",
)
RAW_SOURCE_NAMES = SOURCE_NAMES[:7]
PARETO_SOURCE = "final-spade-regret-pareto.json"
KILL_SOURCE = "final-spade-kill-ledger.json"
TARGET = {
    "condition": "hill-d6-s0.1",
    "family": "hill",
    "dimension": 6,
    "sigma": 0.1,
    "tau_frac": 0.25,
    "gamma": 0.95,
    "alpha": 0.95,
}
TARGET_FIELDS = (
    "arm",
    "instance_seed",
    "campaign_seed",
    "brier",
    "murphy_calibration",
    "murphy_refinement",
    "auc_pred",
    "symmetric_difference_pred",
    "regret_rule_p",
    "total_wells",
    "rounds",
)
CALIBRATION_METRICS = (
    ("brier", "brier"),
    ("murphy_calibration", "murphy_calibration"),
    ("murphy_refinement", "murphy_refinement"),
    ("auc", "auc_pred"),
    ("symmetric_difference", "symmetric_difference_pred"),
    ("regret_rule_p", "regret_rule_p"),
)
PAPER_ARMS = ("doe", "sobol", "qlogei", "qlognei", "spade_cf_m0", "spade_random_plate2")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing required source payload: {path.name}")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load source payload {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected a top-level JSON object")
    if value.get("study_id") != STUDY_ID:
        raise ValueError(f"{path.name}: expected study_id {STUDY_ID!r}")
    if value.get("dirty", False):
        raise ValueError(f"{path.name}: refusing dirty source payload")
    return value


def _require_mapping(row: object, source: str, label: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"{source}: {label} must be an object")
    return row


def _finite_number(value: object, source: str, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{source}: {field} must be finite")
    return float(value)


def _finite_or_none(value: object, source: str, field: str) -> float | None:
    return None if value is None else _finite_number(value, source, field)


def _read_sources(results_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    payloads: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name in SOURCE_NAMES:
        path = Path(results_dir) / name
        payloads[name] = _load_object(path)
        hashes[name] = _sha256(path)
    return payloads, hashes


def _is_target(row: dict[str, Any]) -> bool:
    return (
        row.get("family") == TARGET["family"]
        and row.get("dimension") == TARGET["dimension"]
        and row.get("sigma") == TARGET["sigma"]
        and row.get("tau_frac_or_quantile") == TARGET["tau_frac"]
        and row.get("gamma") == TARGET["gamma"]
        and row.get("alpha") == TARGET["alpha"]
    )


def _target_rows(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for name in RAW_SOURCE_NAMES:
        payload = payloads[name]
        if payload.get("gate_failures") not in (None, []):
            raise ValueError(f"{name}: refusing source with gate failures")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{name}: rows must be a list")
        for index, candidate in enumerate(rows):
            row = _require_mapping(candidate, name, f"rows[{index}]")
            if not _is_target(row):
                continue
            missing = [field for field in TARGET_FIELDS if field not in row]
            if missing:
                raise ValueError(f"{name}: target record missing keys {missing}")
            for field in TARGET_FIELDS[3:]:
                _finite_number(row[field], name, field)
            if not isinstance(row["arm"], str) or not row["arm"]:
                raise ValueError(f"{name}: target arm must be non-empty")
            selected.append({**row, "_source": name})
    if not selected:
        raise ValueError("no rows match the registered target calibration cell")
    return selected


def _science_fingerprint(row: dict[str, Any]) -> tuple[object, ...]:
    """Fields that determine a target-row estimate, excluding run timestamps."""
    return tuple(row[field] for field in TARGET_FIELDS) + (
        row.get("family"), row.get("dimension"), row.get("sigma"),
        row.get("tau_frac_or_quantile"), row.get("gamma"), row.get("alpha"),
    )


def _deduplicate_target_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, object, object], dict[str, Any]] = {}
    for row in rows:
        key = (row["arm"], row["instance_seed"], row["campaign_seed"])
        prior = unique.get(key)
        if prior is None:
            unique[key] = row
        elif _science_fingerprint(prior) != _science_fingerprint(row):
            raise ValueError(f"conflicting duplicate target row for {key!r}")
    return list(unique.values())


def _constant(rows: list[dict[str, Any]], field: str, arm: str) -> int:
    values = {_finite_number(row[field], "target calibration", field) for row in rows}
    if len(values) != 1:
        raise ValueError(f"target calibration: {arm} has inconsistent {field}")
    value = values.pop()
    if not value.is_integer():
        raise ValueError(f"target calibration: {arm} has non-integral {field}")
    return int(value)


def _prospective_calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deduplicated = _deduplicate_target_rows(rows)
    by_arm_instance: dict[tuple[str, object], list[dict[str, Any]]] = defaultdict(list)
    for row in deduplicated:
        by_arm_instance[(row["arm"], row["instance_seed"])].append(row)

    arm_instances: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
    campaigns_per_instance: set[int] = set()
    for (arm, _instance), campaign_rows in by_arm_instance.items():
        campaign_ids = [row["campaign_seed"] for row in campaign_rows]
        if len(set(campaign_ids)) != len(campaign_ids):
            raise ValueError(f"target calibration: duplicate campaign seed for {arm}")
        campaigns_per_instance.add(len(campaign_rows))
        arm_instances[arm].append(campaign_rows)
    if campaigns_per_instance != {4}:
        raise ValueError("target calibration: each landscape instance must have exactly four campaigns")

    output_rows: list[dict[str, Any]] = []
    for arm in sorted(arm_instances):
        instances = arm_instances[arm]
        if len(instances) != 25:
            raise ValueError(f"target calibration: {arm} has {len(instances)} instances; expected 25")
        entry: dict[str, Any] = {
            "arm": arm,
            "n_instances": len(instances),
            "campaigns_per_instance": 4,
            "wells": _constant([row for group in instances for row in group], "total_wells", arm),
            "rounds": _constant([row for group in instances for row in group], "rounds", arm),
        }
        for output_name, source_name in CALIBRATION_METRICS:
            instance_means = [
                sum(_finite_number(row[source_name], "target calibration", source_name) for row in group)
                / len(group)
                for group in instances
            ]
            entry[output_name] = sum(instance_means) / len(instance_means)
        output_rows.append(entry)
    output_rows.sort(key=lambda row: (row["brier"], row["arm"]))
    return {
        **{key: TARGET[key] for key in ("condition", "tau_frac", "gamma", "alpha")},
        "unit": "n25 landscape instances; campaign seeds averaged within instance",
        "lower_is_better": ["brier", "murphy_calibration", "symmetric_difference", "regret_rule_p"],
        "rows": output_rows,
    }


def _spade_comparison(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{PARETO_SOURCE}: rows must be a list")
    if payload.get("primary_terminal_rule") != "P":
        raise ValueError(f"{PARETO_SOURCE}: primary terminal rule must be P")
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, candidate in enumerate(rows):
        row = _require_mapping(candidate, PARETO_SOURCE, f"rows[{index}]")
        arm, condition = row.get("arm"), row.get("condition")
        if arm not in PAPER_ARMS:
            continue
        if not isinstance(condition, str) or not condition:
            raise ValueError(f"{PARETO_SOURCE}: selected record has no condition")
        key = (condition, arm)
        if key in seen:
            raise ValueError(f"{PARETO_SOURCE}: duplicate selected record {key!r}")
        seen.add(key)
        regret = row.get("regret")
        if not isinstance(regret, dict) or "P" not in regret:
            raise ValueError(f"{PARETO_SOURCE}: selected record missing Rule-P regret")
        required = ("symmetric_difference", "wells", "rounds", "certificate_status", "pareto_nondominated")
        missing = [field for field in required if field not in row]
        if missing:
            raise ValueError(f"{PARETO_SOURCE}: selected record missing keys {missing}")
        selected.append({
            "condition": condition,
            "arm": arm,
            "regret_rule_p": _finite_number(regret["P"], PARETO_SOURCE, "regret.P"),
            "symmetric_difference": _finite_number(row["symmetric_difference"], PARETO_SOURCE, "symmetric_difference"),
            "wells": int(_finite_number(row["wells"], PARETO_SOURCE, "wells")),
            "rounds": int(_finite_number(row["rounds"], PARETO_SOURCE, "rounds")),
            "certificate_status": str(row["certificate_status"]),
            "pareto_nondominated": bool(row["pareto_nondominated"]),
            "unit": str(row.get("unit", "n25")),
        })
    conditions = sorted({row["condition"] for row in selected})
    expected = {(condition, arm) for condition in conditions for arm in PAPER_ARMS}
    if set(seen) != expected or len(conditions) != 7:
        raise ValueError(f"{PARETO_SOURCE}: expected six paper arms in each of seven conditions")
    selected.sort(key=lambda row: (row["condition"], PAPER_ARMS.index(row["arm"])))
    return {
        "primary_terminal_rule": "P",
        "arms": list(PAPER_ARMS),
        "lower_is_better": ["regret_rule_p", "symmetric_difference"],
        "rows": selected,
    }


def _kill_ledger(payload: dict[str, Any]) -> dict[str, Any]:
    kills = payload.get("kills")
    if not isinstance(kills, dict):
        raise ValueError(f"{KILL_SOURCE}: kills must be an object")
    expected_ids = [f"KF-{index}" for index in range(1, 11)]
    if set(kills) != set(expected_ids):
        raise ValueError(f"{KILL_SOURCE}: expected KF-1 through KF-10")
    entries: list[dict[str, Any]] = []
    for kill_id in expected_ids:
        raw = _require_mapping(kills[kill_id], KILL_SOURCE, kill_id)
        required = ("id", "status", "effect", "ci", "p", "p_adjusted", "sesoi", "denominator", "interpretation")
        missing = [field for field in required if field not in raw]
        if missing:
            raise ValueError(f"{KILL_SOURCE}: {kill_id} missing keys {missing}")
        if raw["id"] != kill_id or raw["denominator"] in (None, "", 0):
            raise ValueError(f"{KILL_SOURCE}: {kill_id} has an empty denominator or mismatched id")
        ci = raw["ci"]
        if ci is not None and (not isinstance(ci, list) or len(ci) != 2):
            raise ValueError(f"{KILL_SOURCE}: {kill_id} ci must be null or a two-value list")
        entry = dict(raw)
        entry["effect"] = _finite_or_none(raw["effect"], KILL_SOURCE, f"{kill_id}.effect")
        entry["ci"] = (
            None if ci is None
            else [_finite_or_none(value, KILL_SOURCE, f"{kill_id}.ci") for value in ci]
        )
        entry["p"] = _finite_or_none(raw["p"], KILL_SOURCE, f"{kill_id}.p")
        entry["p_adjusted"] = _finite_or_none(raw["p_adjusted"], KILL_SOURCE, f"{kill_id}.p_adjusted")
        entry["sesoi"] = _finite_or_none(raw["sesoi"], KILL_SOURCE, f"{kill_id}.sesoi")
        entries.append(entry)
    return {"rows": entries, "source": KILL_SOURCE}


def build_tables(results_dir: Path) -> dict[str, object]:
    """Return the three evidence-locked publication table payloads.

    Campaign seeds are averaged inside an instance before the n=25 aggregate;
    therefore a repeated raw row cannot change a reported denominator.
    """
    payloads, hashes = _read_sources(Path(results_dir))
    return {
        "study_id": STUDY_ID,
        "source_provenance": {"source_hashes": hashes},
        "prospective_calibration": _prospective_calibration(_target_rows(payloads)),
        "spade_comparison": _spade_comparison(payloads[PARETO_SOURCE]),
        "kill_ledger": _kill_ledger(payloads[KILL_SOURCE]),
    }


def _format(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, list):
        return "[" + ", ".join(_format(item) for item in value) + "]"
    return str(value).replace("\n", " ")


def _csv_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows([[_format(value) for value in row] for row in rows])
    return stream.getvalue().encode("utf-8")


def _markdown_bytes(title: str, note: str, headers: list[str], rows: list[list[object]]) -> bytes:
    def cell(value: object) -> str:
        return _format(value).replace("|", "\\|")

    lines = [f"# {title}", "", note, "", "| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _table_bytes(tables: dict[str, object]) -> dict[str, bytes]:
    calibration = tables["prospective_calibration"]
    comparison = tables["spade_comparison"]
    ledger = tables["kill_ledger"]
    assert isinstance(calibration, dict) and isinstance(comparison, dict) and isinstance(ledger, dict)
    calibration_headers = [
        "Arm", "Brier (lower is better)", "Murphy calibration (lower is better)",
        "Murphy refinement", "AUC", "Symmetric-difference error (lower is better)",
        "Rule-P regret (lower is better)", "Wells (count)", "Rounds (count)",
        "Landscape instances (n)", "Campaigns per instance (n)",
    ]
    calibration_rows = [[
        row["arm"], row["brier"], row["murphy_calibration"], row["murphy_refinement"], row["auc"],
        row["symmetric_difference"], row["regret_rule_p"], row["wells"], row["rounds"],
        row["n_instances"], row["campaigns_per_instance"],
    ] for row in calibration["rows"]]
    comparison_headers = [
        "Condition", "Arm", "Rule-P regret (lower is better)",
        "Symmetric-difference error (lower is better)", "Wells (count)", "Rounds (count)",
        "Certificate status", "Pareto non-dominated",
    ]
    comparison_rows = [[
        row["condition"], row["arm"], row["regret_rule_p"], row["symmetric_difference"],
        row["wells"], row["rounds"], row["certificate_status"], row["pareto_nondominated"],
    ] for row in comparison["rows"]]
    ledger_headers = [
        "ID", "Status", "Effect", "Interval", "p-value", "Adjusted p-value", "SESOI",
        "Denominator (count)", "Interpretation",
    ]
    ledger_rows = [[
        row["id"], row["status"], row["effect"], row["ci"], row["p"], row["p_adjusted"],
        row["sesoi"], row["denominator"], row["interpretation"],
    ] for row in ledger["rows"]]
    return {
        "table-spade-prospective-calibration.csv": _csv_bytes(calibration_headers, calibration_rows),
        "table-spade-prospective-calibration.md": _markdown_bytes(
            "Prospective calibration at the registered target cell",
            "Unit: n=25 landscape instances; four campaign seeds are averaged within each instance. "
            "Brier, Murphy calibration, symmetric-difference error, and Rule-P regret are lower-is-better.",
            calibration_headers, calibration_rows),
        "table-spade-comparison.csv": _csv_bytes(comparison_headers, comparison_rows),
        "table-spade-comparison.md": _markdown_bytes(
            "SPADE comparison across registered conditions",
            "Unit: n=25 landscape instances per condition. Rule-P regret and symmetric-difference error are lower-is-better; all listed arms use 48 wells.",
            comparison_headers, comparison_rows),
        "table-spade-kill-ledger.csv": _csv_bytes(ledger_headers, ledger_rows),
        "table-spade-kill-ledger.md": _markdown_bytes(
            "Registered final-SPADE kill ledger",
            "Denominators are reported as counts; intervals, p-values, and SESOI retain the adjudicated evidence without reinterpretation.",
            ledger_headers, ledger_rows),
    }


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def write_tables(results_dir: Path, output_dir: Path) -> tuple[Path, ...]:
    """Write the JSON manifest and six journal-ready table files deterministically."""
    tables = build_tables(Path(results_dir))
    rendered = _table_bytes(tables)
    output = Path(output_dir)
    ordered_names = (
        "publication-tables.json",
        "table-spade-prospective-calibration.csv",
        "table-spade-prospective-calibration.md",
        "table-spade-comparison.csv",
        "table-spade-comparison.md",
        "table-spade-kill-ledger.csv",
        "table-spade-kill-ledger.md",
    )
    output_hashes = {name: hashlib.sha256(rendered[name]).hexdigest() for name in sorted(rendered)}
    provenance = tables["source_provenance"]
    assert isinstance(provenance, dict)
    manifest = {
        "study_id": STUDY_ID,
        "source_hashes": provenance["source_hashes"],
        "output_hashes": output_hashes,
        "tables": {
            "prospective_calibration": tables["prospective_calibration"],
            "spade_comparison": tables["spade_comparison"],
            "kill_ledger": tables["kill_ledger"],
        },
    }
    rendered["publication-tables.json"] = _canonical_json(manifest)
    for name in ordered_names:
        _atomic_write(output / name, rendered[name])
    return tuple(output / name for name in ordered_names)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final-SPADE publication tables from committed evidence.")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/publication-tables"))
    args = parser.parse_args()
    written = write_tables(args.results_dir, args.output_dir)
    print(f"wrote {len(written)} publication tables to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
