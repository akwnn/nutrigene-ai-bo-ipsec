"""Fail-closed validation and summary for EC benchmark artifacts."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from run_ec_benchmark import ARMS, EVAL_SEEDS, FAMILIES, REQUIRED_COLUMNS, TRAIN_SEEDS, expected_cells, sha256, SPEC, source_commit

TRAINING_REPORT_SCHEMA = "spade-ec-training-calibration-v1"
EC_VERDICTS = {
    "PASS_EC_PROSPECTIVE", "FAIL_ANSWER_RATE", "FAIL_CONTAINMENT",
    "FAIL_FALSE_CERTIFICATE", "FAIL_REGRET", "FAIL_ROUNDS", "REFUSED_INCOMPLETE",
}


def _wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    if trials <= 0:
        return 0.0
    p = successes / trials
    den = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return (centre - half) / den


def _summary(rows: list[dict[str, Any]], family: str, arm: str) -> dict[str, Any]:
    selected = [r for r in rows if r.get("family") == family and r.get("arm") == arm]
    answered = [r for r in selected if float(r.get("answer_rate", 0)) > 0]
    contained = [r for r in answered if bool(r.get("contained", float(r.get("containment", 0)) >= 1.0 - 1e-12))]
    return {
        "family": family, "arm": arm, "campaigns": len(selected),
        "answered": len(answered), "answer_rate": len(answered) / len(selected) if selected else 0.0,
        "containment": len(contained) / len(answered) if answered else 0.0,
        "containment_wilson_lower": _wilson_lower(len(contained), len(answered)),
        "false_certificate_count": sum(int(r.get("false_certificate_count", 0)) for r in selected),
        "point_regret": sum(float(r.get("point_regret", 0)) for r in selected) / len(selected) if selected else float("inf"),
        "adaptive_rounds": sum(float(r.get("adaptive_rounds", 0)) for r in selected) / len(selected) if selected else float("inf"),
    }


def adjudicate(path: Path) -> dict[str, Any]:
    """Return one immutable EC verdict; incomplete evidence is never scored."""
    try:
        validate_artifact(path)
    except Exception as exc:
        return {"verdict": "REFUSED_INCOMPLETE", "reason": f"complete unseen-seed artifact required: {exc}"}
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = artifact["rows"]
    summaries = {f: {a: _summary(rows, f, a) for a in ARMS} for f in FAMILIES}
    for family in FAMILIES:
        s = summaries[family]["spade"]
        if s["answered"] < 16 or s["answer_rate"] < 0.50:
            return {"verdict": "FAIL_ANSWER_RATE", "family": family, "summaries": summaries,
                    "reason": "SPADE answered fewer than 16 campaigns or below 0.50 answer rate"}
        if s["containment_wilson_lower"] < 0.90:
            return {"verdict": "FAIL_CONTAINMENT", "family": family, "summaries": summaries,
                    "reason": "SPADE one-sided 95% containment lower bound is below 0.90"}
        if s["false_certificate_count"] != 0:
            return {"verdict": "FAIL_FALSE_CERTIFICATE", "family": family, "summaries": summaries,
                    "reason": "SPADE produced a false certificate"}
        d = summaries[family]["doe"]
        if s["point_regret"] > d["point_regret"] + 0.02:
            return {"verdict": "FAIL_REGRET", "family": family, "summaries": summaries,
                    "reason": "SPADE regret exceeds matched-budget DOE by more than 0.02"}
        if s["adaptive_rounds"] > d["adaptive_rounds"]:
            return {"verdict": "FAIL_ROUNDS", "family": family, "summaries": summaries,
                    "reason": "SPADE uses more adaptive rounds than matched-budget DOE"}
    return {"verdict": "PASS_EC_PROSPECTIVE", "summaries": summaries,
            "reason": "all prospective EC acceptance criteria passed"}


def validate_artifact(path: Path) -> None:
    """Refuse incomplete, duplicated, non-finite, or provenance-drifted artifacts."""
    artifact: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    if artifact.get("status") != "COMPLETE":
        raise ValueError("artifact is not COMPLETE")
    if artifact.get("spec_sha256") != sha256(SPEC):
        raise ValueError("spec digest mismatch")
    runner = Path(__file__).with_name("run_ec_benchmark.py")
    if artifact.get("runner_sha256") != sha256(runner):
        raise ValueError("runner digest mismatch")
    if artifact.get("training_seed_start") != TRAIN_SEEDS[0] or artifact.get("training_seed_stop") != TRAIN_SEEDS[-1] + 1:
        raise ValueError("training seed bounds mismatch")
    if artifact.get("evaluation_seed_start") != EVAL_SEEDS[0] or artifact.get("evaluation_seed_stop") != EVAL_SEEDS[-1] + 1:
        raise ValueError("evaluation seed bounds mismatch")
    if artifact.get("source_commit") != source_commit():
        raise ValueError("source commit mismatch")
    if set(TRAIN_SEEDS) & set(EVAL_SEEDS):
        raise ValueError("training and evaluation seeds overlap")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(expected_cells()):
        raise ValueError("partial or wrong-size grid")
    seen = set()
    for row in rows:
        missing = REQUIRED_COLUMNS - set(row)
        if missing: raise ValueError(f"missing columns: {sorted(missing)}")
        key = (row["family"], int(row["seed"]), row["arm"])
        if key in seen: raise ValueError(f"duplicate cell {key}")
        if key not in expected_cells(): raise ValueError(f"unexpected cell {key}")
        seen.add(key)
        for name in ("answer_rate", "containment", "containment_wilson_lower", "false_certificate_count", "joint_volume", "point_regret", "adaptive_rounds"):
            if not math.isfinite(float(row[name])): raise ValueError(f"non-finite {name}")
        for name in ("spec_sha256", "runner_sha256", "source_commit"):
            if row[name] != artifact[name]: raise ValueError(f"row provenance mismatch: {name}")
    if seen != expected_cells(): raise ValueError("missing grid cells")


def analyse(path: Path) -> dict[str, Any]:
    validate_artifact(path)
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    return artifact


def validate_training_report(path: Path) -> dict[str, Any]:
    """Validate a calibration template without treating it as evaluation evidence.

    Training calibration is allowed to contain proposed/fitted values, but it must
    never contain evaluation seeds or claim a completed benchmark result.
    """
    report: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("schema") != TRAINING_REPORT_SCHEMA:
        raise ValueError("training calibration schema mismatch")
    if report.get("status") != "TRAINING_ONLY_TEMPLATE":
        raise ValueError("training report must remain a template until populated")
    if report.get("evaluation_status") != "NOT_RUN":
        raise ValueError("evaluation status must be NOT_RUN")
    if report.get("evaluation_seeds") not in ([], None):
        raise ValueError("training report must not contain evaluation seeds")
    seeds = report.get("training_seeds")
    if seeds != list(TRAIN_SEEDS):
        raise ValueError("training seed list mismatch")
    if report.get("claims") != []:
        raise ValueError("training report cannot contain outcome claims")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("artifact", type=Path)
    result = adjudicate(parser.parse_args().artifact)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "PASS_EC_PROSPECTIVE" else 2


if __name__ == "__main__": sys.exit(main())
