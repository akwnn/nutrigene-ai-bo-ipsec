from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import beta

from .core import assert_no_prohibited_content, load_json, require_keys


FIGURE2_RULE_ARMS = ("doe", "qlogei", "qlognei", "versionb")
FIGURE2_DECOMPOSITION_ARMS = ("doe", "qlognei", "lhs", "sobol")
FIGURE3_ARMS = ("doe", "lhs", "sobol", "qlogei", "qlognei", "spade_cf_m0")


def _unique(
    rows: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    context: str,
) -> dict[str, Any]:
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise ValueError(f"{context}: expected exactly one row, found {len(matches)}")
    return matches[0]


def source_paths(results_dir: Path) -> tuple[Path, ...]:
    names = (
        "fix1-terminal-rule.json",
        "fix1-analysis.json",
        "step0-oracle-best.json",
        "final-spade-regret-pareto.json",
        "final-spade-kill-ledger.json",
        "p7-murphy.json",
        "final-spade-certificate.json",
        "p8-predictions.json",
        "p8-certificate-families.json",
    )
    return tuple(Path(results_dir) / name for name in names)


def build_figure2_data(results_dir: Path) -> dict[str, Any]:
    terminal = load_json(Path(results_dir) / "fix1-terminal-rule.json")
    analysis = load_json(Path(results_dir) / "fix1-analysis.json")
    oracle = load_json(Path(results_dir) / "step0-oracle-best.json")
    require_keys(analysis, {"per_arm", "statistics"}, "fix1 analysis")
    per_arm = {row["arm"]: row for row in analysis["per_arm"]}
    terminal_by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in terminal["rows"]:
        if row["arm"] in FIGURE2_RULE_ARMS:
            terminal_by_arm[row["arm"]].append(row)
    for arm in FIGURE2_RULE_ARMS:
        rows = terminal_by_arm[arm]
        if len(rows) != per_arm[arm]["n"]:
            raise ValueError(f"{arm}: raw-row count does not match fix1 analysis")
        raw_a = float(np.mean([row["regret_a"] for row in rows]))
        raw_p = float(np.mean([row["regret_p"] for row in rows]))
        if not (np.isfinite(raw_a) and np.isfinite(raw_p)):
            raise ValueError(f"{arm}: non-finite terminal-rule mean")
        if not np.allclose(
            (raw_a, raw_p),
            (per_arm[arm]["mean_rule_a"], per_arm[arm]["mean_rule_p"]),
            atol=1e-12,
        ):
            raise ValueError(f"{arm}: fix1 raw rows do not reconcile with analysis")
    means = [
        {
            "arm": arm,
            "rule_a": per_arm[arm]["mean_rule_a"],
            "rule_p": per_arm[arm]["mean_rule_p"],
            "rounds": per_arm[arm]["rounds"],
            "n": per_arm[arm]["n"],
        }
        for arm in FIGURE2_RULE_ARMS
    ]
    contrasts = [
        {
            "arm": arm,
            "mean": per_arm[arm]["delta_p_minus_a"]["mean"],
            "lo": per_arm[arm]["delta_p_minus_a"]["lo"],
            "hi": per_arm[arm]["delta_p_minus_a"]["hi"],
            "n": per_arm[arm]["delta_p_minus_a"]["n"],
        }
        for arm in FIGURE2_RULE_ARMS
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in oracle["rows"]:
        if row["arm"] in FIGURE2_DECOMPOSITION_ARMS:
            grouped[row["arm"]].append(row)
    decomposition = []
    for arm in FIGURE2_DECOMPOSITION_ARMS:
        rows = grouped[arm]
        rule_a = float(np.mean([row["rule_a"] for row in rows]))
        oracle_best = float(np.mean([row["oracle_best"] for row in rows]))
        identification_gap = float(np.mean([row["identification_gap"] for row in rows]))
        if not np.isclose(rule_a, oracle_best + identification_gap, atol=1e-12):
            raise ValueError(f"{arm}: Rule A decomposition does not close")
        decomposition.append(
            {
                "arm": arm,
                "rule_a": rule_a,
                "oracle_best": oracle_best,
                "identification_gap": identification_gap,
                "n": len(rows),
            }
        )
    output = {
        "condition": "hill-d6-s0.25",
        "rule_means": means,
        "paired_rule_contrasts": contrasts,
        "decomposition": decomposition,
        "unit": analysis["statistics"]["unit_of_analysis"],
    }
    assert_no_prohibited_content(output)
    return output


def build_figure3_data(results_dir: Path) -> dict[str, Any]:
    pareto = load_json(Path(results_dir) / "final-spade-regret-pareto.json")
    ledger = load_json(Path(results_dir) / "final-spade-kill-ledger.json")
    target_rows = [
        row
        for row in pareto["rows"]
        if row["condition"] == "hill-d6-s0.1" and row["arm"] in FIGURE3_ARMS
    ]
    if {row["arm"] for row in target_rows} != set(FIGURE3_ARMS):
        raise ValueError("Figure 3 target rows are incomplete")
    target_points = [
        {
            "arm": row["arm"],
            "map_error": row["symmetric_difference"],
            "regret_p": row["regret"]["P"],
            "rounds": row["rounds"],
            "wells": row["wells"],
            "unit": row["unit"],
        }
        for row in target_rows
    ]

    # Only these non-boundary entries may be read from the ledger.
    k6, k7, k8 = (ledger["kills"][key] for key in ("KF-6", "KF-7", "KF-8"))
    contrasts = [
        {
            "contrast_id": "map_spade_minus_sobol",
            "mean": -k6["effect"],
            "lo": -k6["ci"][1],
            "hi": -k6["ci"][0],
            "sesoi": k6["sesoi"],
            "n": k6["denominator"],
        },
        {
            "contrast_id": "map_spade_minus_qlognei",
            "mean": -k7["effect"],
            "lo": -k7["ci"][1],
            "hi": -k7["ci"][0],
            "sesoi": k7["sesoi"],
            "n": k7["denominator"],
        },
        {
            "contrast_id": "regret_spade_minus_qlognei",
            "mean": k8["effect"],
            "lo": k8["ci"][0],
            "hi": k8["ci"][1],
            "sesoi": k8["sesoi"],
            "n": k8["denominator"],
        },
    ]
    hartmann = [
        {
            "arm": row["arm"],
            "condition": row["condition"],
            "map_error": row["symmetric_difference"],
            "regret_p": row["regret"]["P"],
            "rounds": row["rounds"],
            "wells": row["wells"],
            "evidence_stage": "descriptive; raw-row intervals unavailable",
        }
        for row in pareto["rows"]
        if row["condition"] in {"hartmann6-d6-s0.25", "hartmann6-d8-s0.25"}
        and row["arm"] in FIGURE3_ARMS
    ]
    output = {
        "target_points": target_points,
        "contrasts": contrasts,
        "cost_ledger": target_points,
        "hartmann": hartmann,
        "terminal_rule": "P",
    }
    assert_no_prohibited_content(output)
    return output


def _clopper_pearson(x: int, n: int, level: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("Clopper-Pearson interval requires n > 0")
    tail = (1.0 - level) / 2.0
    lo = 0.0 if x == 0 else float(beta.ppf(tail, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1.0 - tail, x + 1, n - x))
    return lo, hi


def build_figure4_data(results_dir: Path) -> dict[str, Any]:
    murphy = load_json(Path(results_dir) / "p7-murphy.json")
    certificate = load_json(Path(results_dir) / "final-spade-certificate.json")
    predictions = load_json(Path(results_dir) / "p8-predictions.json")
    families = load_json(Path(results_dir) / "p8-certificate-families.json")

    ids = [cell["cell_id"] for cell in certificate["cells"]]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate cell_id values: {duplicates[:5]}")

    calibration = []
    for arm in ("doe", "sobol", "qlognei", "versionb"):
        rows = [row for row in murphy["rows"] if row["arm"] == arm]
        calibration.append(
            {
                "arm": arm,
                "n": len(rows),
                "calibration": float(np.mean([row["pred_calibration"] for row in rows])),
                "refinement": float(np.mean([row["pred_refinement"] for row in rows])),
                "evidence_stage": "retrospective Hill",
            }
        )

    hill_containment = []
    for cell in certificate["cells"]:
        if (
            cell["arm"] == "spade_cf_m0"
            and cell["condition"].startswith("hill-")
            and cell["tau_frac"] == 0.25
            and cell["gamma"] in {0.5, 0.95}
            and cell["alpha"] in {0.8, 0.95}
            and not cell["infeasible"]
        ):
            crossfit = cell["crossfit"]
            if crossfit["n"] != cell["n_nonempty"]:
                raise ValueError(
                    f"{cell['cell_id']}: cross-fit n does not match non-empty count"
                )
            hill_containment.append(
                {
                    "cell_id": cell["cell_id"],
                    "condition": cell["condition"],
                    "tau_frac": cell["tau_frac"],
                    "gamma": cell["gamma"],
                    "alpha": cell["alpha"],
                    "x": crossfit["x"],
                    "n": crossfit["n"],
                    "proportion": crossfit["proportion"],
                    "ci_lo": crossfit["ci_lo"],
                    "ci_hi": crossfit["ci_hi"],
                    "empty_rate": cell["empty_rate"],
                    "estimator": "crossfit",
                }
            )

    answer_rate = []
    for family, stats in predictions["stats"].items():
        n = stats["n_campaigns"]
        answer_rate.append(
            {
                "family": family,
                "answered": n - stats["all_empty"],
                "n_campaigns": n,
                "answer_rate": 1.0 - stats["all_empty"] / n,
                "definition": "campaign returned at least one non-empty certificate",
            }
        )

    conditional = []
    for family in sorted({row["family"] for row in families["rows"]}):
        rows = [
            row
            for row in families["rows"]
            if row["family"] == family
            and row["arm"] == "versionb"
            and row["ce_empty_0.8"] is False
        ]
        x = sum(row["ce_empirical_0.8"] == 1.0 for row in rows)
        n = len(rows)
        if n:
            lo, hi = _clopper_pearson(x, n)
            conditional.append(
                {
                    "family": family,
                    "alpha": 0.8,
                    "x": x,
                    "n": n,
                    "proportion": x / n,
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "definition": "containment conditional on a non-empty certificate cell",
                }
            )
        else:
            conditional.append(
                {
                    "family": family,
                    "alpha": 0.8,
                    "x": 0,
                    "n": 0,
                    "proportion": None,
                    "ci_lo": None,
                    "ci_hi": None,
                    "definition": "no certificate cell returned an answer",
                }
            )

    output = {
        "calibration_refinement": calibration,
        "hill_containment": hill_containment,
        "cross_family_answer_rate": answer_rate,
        "cross_family_conditional_containment": conditional,
    }
    assert_no_prohibited_content(output)
    return output
