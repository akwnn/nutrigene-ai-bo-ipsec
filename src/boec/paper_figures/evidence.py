from __future__ import annotations

from numbers import Real
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import beta

from .core import assert_no_prohibited_content, load_json, require_keys


FIGURE2_RULE_ARMS = ("doe", "qlogei", "qlognei", "versionb")
FIGURE2_DECOMPOSITION_ARMS = ("doe", "qlognei", "lhs", "sobol")
FIGURE3_ARMS = ("doe", "lhs", "sobol", "qlogei", "qlognei", "spade_cf_m0")
FIGURE3_HARTMANN_CONDITIONS = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
FIGURE4_HILL_CELL_IDS = frozenset(
    {
        "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.5|a0.8",
        "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.5|a0.95",
        "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.8",
        "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95",
        "spade_cf_m0|hill-d6-s0.25|tf0.25|g0.5|a0.8",
        "spade_cf_m0|hill-d6-s0.25|tf0.25|g0.5|a0.95",
    }
)
FIGURE4_HILL_CELL_SPECS = {
    "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.5|a0.8": ("hill-d6-s0.1", 0.25, 0.5, 0.8),
    "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.5|a0.95": ("hill-d6-s0.1", 0.25, 0.5, 0.95),
    "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.8": ("hill-d6-s0.1", 0.25, 0.95, 0.8),
    "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95": ("hill-d6-s0.1", 0.25, 0.95, 0.95),
    "spade_cf_m0|hill-d6-s0.25|tf0.25|g0.5|a0.8": ("hill-d6-s0.25", 0.25, 0.5, 0.8),
    "spade_cf_m0|hill-d6-s0.25|tf0.25|g0.5|a0.95": ("hill-d6-s0.25", 0.25, 0.5, 0.95),
}


def _context(source: str, record: str) -> str:
    return f"{source} {record}"


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: expected an object")
    return value


def _records(payload: dict[str, Any], key: str, source: str) -> list[dict[str, Any]]:
    require_keys(payload, {key}, source)
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"{source}.{key}: expected a list")
    return [_mapping(record, _context(source, f"record {index}")) for index, record in enumerate(value)]


def _record(record: dict[str, Any], keys: set[str], source: str, label: str) -> None:
    require_keys(record, keys, _context(source, label))


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context}: expected a non-empty string")
    return value


def _finite(value: Any, context: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{context}: expected a finite number")
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"{context}: expected a finite number")
    if minimum is not None and number < minimum:
        raise ValueError(f"{context}: expected a value >= {minimum}")
    return number


def _probability(value: Any, context: str) -> float:
    number = _finite(value, context)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{context}: expected a probability in [0, 1]")
    return number


def _count(value: Any, context: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context}: expected an integer count")
    if value < 0 or (positive and value == 0):
        bound = "positive" if positive else "non-negative"
        raise ValueError(f"{context}: expected a {bound} integer count")
    return value


def _exactly_one(
    rows: Iterable[tuple[int, dict[str, Any]]], source: str, description: str
) -> tuple[int, dict[str, Any]]:
    matches = list(rows)
    if len(matches) != 1:
        raise ValueError(f"{source} {description}: expected exactly one record, found {len(matches)}")
    return matches[0]


def _pareto_row(row: dict[str, Any], source: str, index: int) -> None:
    label = f"record {index}"
    _record(row, {"arm", "condition", "symmetric_difference", "regret", "rounds", "wells", "unit"}, source, label)
    context = _context(source, label)
    _string(row["arm"], f"{context}.arm")
    _string(row["condition"], f"{context}.condition")
    _probability(row["symmetric_difference"], f"{context}.symmetric_difference")
    regret = _mapping(row["regret"], f"{context}.regret")
    _record(regret, {"P"}, source, f"{label}.regret")
    _finite(regret["P"], f"{context}.regret.P", minimum=0.0)
    _count(row["rounds"], f"{context}.rounds", positive=True)
    _count(row["wells"], f"{context}.wells", positive=True)
    _string(row["unit"], f"{context}.unit")


def source_paths(results_dir: Path) -> tuple[Path, ...]:
    names = (
        "fix1-terminal-rule.json", "fix1-analysis.json", "step0-oracle-best.json",
        "final-spade-regret-pareto.json", "final-spade-kill-ledger.json", "p7-murphy.json",
        "final-spade-certificate.json", "p8-predictions.json", "p8-certificate-families.json",
    )
    return tuple(Path(results_dir) / name for name in names)


def build_figure2_data(results_dir: Path) -> dict[str, Any]:
    terminal_source, analysis_source, oracle_source = (
        "fix1-terminal-rule.json", "fix1-analysis.json", "step0-oracle-best.json"
    )
    terminal = load_json(Path(results_dir) / terminal_source)
    analysis = load_json(Path(results_dir) / analysis_source)
    oracle = load_json(Path(results_dir) / oracle_source)
    terminal_rows = _records(terminal, "rows", terminal_source)
    analysis_rows = _records(analysis, "per_arm", analysis_source)
    oracle_rows = _records(oracle, "rows", oracle_source)
    require_keys(analysis, {"statistics"}, analysis_source)
    statistics = _mapping(analysis["statistics"], f"{analysis_source}.statistics")
    _record(statistics, {"unit_of_analysis"}, analysis_source, "statistics")
    unit = _string(statistics["unit_of_analysis"], f"{analysis_source}.statistics.unit_of_analysis")

    for index, row in enumerate(analysis_rows):
        _record(row, {"arm"}, analysis_source, f"record {index}")
        _string(row["arm"], f"{_context(analysis_source, f'record {index}')}.arm")
    per_arm: dict[str, dict[str, Any]] = {}
    for arm in FIGURE2_RULE_ARMS:
        index, row = _exactly_one(((i, value) for i, value in enumerate(analysis_rows) if value["arm"] == arm), analysis_source, f"selected arm {arm}")
        label = f"record {index} ({arm})"
        _record(row, {"rounds", "n", "mean_rule_a", "mean_rule_p", "delta_p_minus_a"}, analysis_source, label)
        _count(row["rounds"], f"{_context(analysis_source, label)}.rounds", positive=True)
        _count(row["n"], f"{_context(analysis_source, label)}.n", positive=True)
        _finite(row["mean_rule_a"], f"{_context(analysis_source, label)}.mean_rule_a", minimum=0.0)
        _finite(row["mean_rule_p"], f"{_context(analysis_source, label)}.mean_rule_p", minimum=0.0)
        delta = _mapping(row["delta_p_minus_a"], f"{_context(analysis_source, label)}.delta_p_minus_a")
        _record(delta, {"mean", "lo", "hi", "n"}, analysis_source, f"{label}.delta_p_minus_a")
        _finite(delta["mean"], f"{_context(analysis_source, label)}.delta_p_minus_a.mean")
        lo = _finite(delta["lo"], f"{_context(analysis_source, label)}.delta_p_minus_a.lo")
        hi = _finite(delta["hi"], f"{_context(analysis_source, label)}.delta_p_minus_a.hi")
        if lo > hi:
            raise ValueError(f"{_context(analysis_source, label)}.delta_p_minus_a: lo exceeds hi")
        if _count(delta["n"], f"{_context(analysis_source, label)}.delta_p_minus_a.n", positive=True) != row["n"]:
            raise ValueError(f"{_context(analysis_source, label)}: contrast n does not match arm n")
        per_arm[arm] = row

    decomposition_counts: dict[str, int] = {}
    for arm in FIGURE2_DECOMPOSITION_ARMS:
        index, row = _exactly_one(((i, value) for i, value in enumerate(analysis_rows) if value["arm"] == arm), analysis_source, f"decomposition arm {arm}")
        label = f"record {index} ({arm})"
        _record(row, {"n"}, analysis_source, label)
        decomposition_counts[arm] = _count(row["n"], f"{_context(analysis_source, label)}.n", positive=True)

    selected_terminal: dict[str, list[dict[str, Any]]] = {arm: [] for arm in FIGURE2_RULE_ARMS}
    for index, row in enumerate(terminal_rows):
        _record(row, {"arm"}, terminal_source, f"record {index}")
        arm = _string(row["arm"], f"{_context(terminal_source, f'record {index}')}.arm")
        if arm in selected_terminal:
            label = f"record {index} ({arm})"
            _record(row, {"regret_a", "regret_p"}, terminal_source, label)
            _finite(row["regret_a"], f"{_context(terminal_source, label)}.regret_a", minimum=0.0)
            _finite(row["regret_p"], f"{_context(terminal_source, label)}.regret_p", minimum=0.0)
            selected_terminal[arm].append(row)
    for arm, rows in selected_terminal.items():
        if len(rows) != per_arm[arm]["n"]:
            raise ValueError(f"{terminal_source} selected arm {arm}: raw-row count does not match fix1 analysis")
        raw_a, raw_p = float(np.mean([row["regret_a"] for row in rows])), float(np.mean([row["regret_p"] for row in rows]))
        if not np.allclose((raw_a, raw_p), (per_arm[arm]["mean_rule_a"], per_arm[arm]["mean_rule_p"]), atol=1e-12):
            raise ValueError(f"{terminal_source} selected arm {arm}: raw rows do not reconcile with analysis")

    grouped: dict[str, list[dict[str, Any]]] = {arm: [] for arm in FIGURE2_DECOMPOSITION_ARMS}
    for index, row in enumerate(oracle_rows):
        _record(row, {"arm"}, oracle_source, f"record {index}")
        arm = _string(row["arm"], f"{_context(oracle_source, f'record {index}')}.arm")
        if arm in grouped:
            label = f"record {index} ({arm})"
            _record(row, {"rule_a", "oracle_best", "identification_gap"}, oracle_source, label)
            for key in ("rule_a", "oracle_best", "identification_gap"):
                _finite(row[key], f"{_context(oracle_source, label)}.{key}", minimum=0.0)
            grouped[arm].append(row)
    decomposition = []
    for arm, rows in grouped.items():
        if len(rows) != decomposition_counts[arm]:
            raise ValueError(f"{oracle_source} selected arm {arm}: raw-row count does not match fix1 analysis")
        rule_a = float(np.mean([row["rule_a"] for row in rows]))
        oracle_best = float(np.mean([row["oracle_best"] for row in rows]))
        gap = float(np.mean([row["identification_gap"] for row in rows]))
        if not np.isclose(rule_a, oracle_best + gap, atol=1e-12):
            raise ValueError(f"{oracle_source} selected arm {arm}: Rule A decomposition does not close")
        decomposition.append({"arm": arm, "rule_a": rule_a, "oracle_best": oracle_best, "identification_gap": gap, "n": len(rows)})

    output = {
        "condition": "hill-d6-s0.25",
        "rule_means": [{"arm": arm, "rule_a": per_arm[arm]["mean_rule_a"], "rule_p": per_arm[arm]["mean_rule_p"], "rounds": per_arm[arm]["rounds"], "n": per_arm[arm]["n"]} for arm in FIGURE2_RULE_ARMS],
        "paired_rule_contrasts": [{"arm": arm, "mean": per_arm[arm]["delta_p_minus_a"]["mean"], "lo": per_arm[arm]["delta_p_minus_a"]["lo"], "hi": per_arm[arm]["delta_p_minus_a"]["hi"], "n": per_arm[arm]["delta_p_minus_a"]["n"]} for arm in FIGURE2_RULE_ARMS],
        "decomposition": decomposition, "unit": unit,
    }
    assert_no_prohibited_content(output)
    return output


def build_figure3_data(results_dir: Path) -> dict[str, Any]:
    pareto_source, ledger_source = "final-spade-regret-pareto.json", "final-spade-kill-ledger.json"
    pareto = load_json(Path(results_dir) / pareto_source)
    ledger = load_json(Path(results_dir) / ledger_source)
    rows = _records(pareto, "rows", pareto_source)
    for index, row in enumerate(rows):
        _record(row, {"arm", "condition"}, pareto_source, f"record {index}")
        _string(row["arm"], f"{_context(pareto_source, f'record {index}')}.arm")
        _string(row["condition"], f"{_context(pareto_source, f'record {index}')}.condition")

    targets: list[dict[str, Any]] = []
    for arm in FIGURE3_ARMS:
        index, row = _exactly_one(((i, value) for i, value in enumerate(rows) if value["condition"] == "hill-d6-s0.1" and value["arm"] == arm), pareto_source, f"target arm {arm}")
        _pareto_row(row, pareto_source, index)
        targets.append(row)

    require_keys(ledger, {"kills"}, ledger_source)
    kills = _mapping(ledger["kills"], f"{ledger_source}.kills")
    ledger_rows: dict[str, dict[str, Any]] = {}
    for key in ("KF-6", "KF-7", "KF-8"):
        if key not in kills:
            raise ValueError(f"{ledger_source}.kills: missing key {key}")
        row = _mapping(kills[key], f"{ledger_source}.kills.{key}")
        _record(row, {"effect", "ci", "sesoi", "denominator"}, ledger_source, f"kills.{key}")
        _finite(row["effect"], f"{ledger_source}.kills.{key}.effect")
        ci = row["ci"]
        if not isinstance(ci, list) or len(ci) != 2:
            raise ValueError(f"{ledger_source}.kills.{key}.ci: expected a two-value interval")
        lo, hi = _finite(ci[0], f"{ledger_source}.kills.{key}.ci[0]"), _finite(ci[1], f"{ledger_source}.kills.{key}.ci[1]")
        if lo > hi:
            raise ValueError(f"{ledger_source}.kills.{key}.ci: lo exceeds hi")
        _finite(row["sesoi"], f"{ledger_source}.kills.{key}.sesoi", minimum=0.0)
        _count(row["denominator"], f"{ledger_source}.kills.{key}.denominator", positive=True)
        ledger_rows[key] = row

    hartmann = []
    for condition in FIGURE3_HARTMANN_CONDITIONS:
        for arm in FIGURE3_ARMS:
            index, row = _exactly_one(((i, value) for i, value in enumerate(rows) if value["condition"] == condition and value["arm"] == arm), pareto_source, f"Hartmann condition {condition} arm {arm}")
            _pareto_row(row, pareto_source, index)
            hartmann.append({"arm": row["arm"], "condition": row["condition"], "map_error": row["symmetric_difference"], "regret_p": row["regret"]["P"], "rounds": row["rounds"], "wells": row["wells"], "evidence_stage": "descriptive; raw-row intervals unavailable"})

    k6, k7, k8 = (ledger_rows[key] for key in ("KF-6", "KF-7", "KF-8"))
    target_points = [{"arm": row["arm"], "map_error": row["symmetric_difference"], "regret_p": row["regret"]["P"], "rounds": row["rounds"], "wells": row["wells"], "unit": row["unit"]} for row in targets]
    output = {
        "target_points": target_points,
        "contrasts": [
            {"contrast_id": "map_spade_minus_sobol", "mean": -k6["effect"], "lo": -k6["ci"][1], "hi": -k6["ci"][0], "sesoi": k6["sesoi"], "n": k6["denominator"]},
            {"contrast_id": "map_spade_minus_qlognei", "mean": -k7["effect"], "lo": -k7["ci"][1], "hi": -k7["ci"][0], "sesoi": k7["sesoi"], "n": k7["denominator"]},
            {"contrast_id": "regret_spade_minus_qlognei", "mean": k8["effect"], "lo": k8["ci"][0], "hi": k8["ci"][1], "sesoi": k8["sesoi"], "n": k8["denominator"]},
        ],
        "cost_ledger": target_points, "hartmann": hartmann, "terminal_rule": "P",
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
    murphy_source, certificate_source = "p7-murphy.json", "final-spade-certificate.json"
    predictions_source, families_source = "p8-predictions.json", "p8-certificate-families.json"
    murphy = load_json(Path(results_dir) / murphy_source)
    certificate = load_json(Path(results_dir) / certificate_source)
    predictions = load_json(Path(results_dir) / predictions_source)
    families = load_json(Path(results_dir) / families_source)
    murphy_rows = _records(murphy, "rows", murphy_source)

    calibration = []
    for arm in ("doe", "sobol", "qlognei", "versionb"):
        selected: list[dict[str, Any]] = []
        for index, row in enumerate(murphy_rows):
            _record(row, {"arm"}, murphy_source, f"record {index}")
            if _string(row["arm"], f"{_context(murphy_source, f'record {index}')}.arm") != arm:
                continue
            label = f"record {index} ({arm})"
            _record(row, {"pred_calibration", "pred_refinement"}, murphy_source, label)
            _finite(row["pred_calibration"], f"{_context(murphy_source, label)}.pred_calibration", minimum=0.0)
            _finite(row["pred_refinement"], f"{_context(murphy_source, label)}.pred_refinement", minimum=0.0)
            selected.append(row)
        if not selected:
            raise ValueError(f"{murphy_source} selected arm {arm}: expected at least one record")
        calibration.append({"arm": arm, "n": len(selected), "calibration": float(np.mean([row["pred_calibration"] for row in selected])), "refinement": float(np.mean([row["pred_refinement"] for row in selected])), "evidence_stage": "retrospective Hill"})

    cells = _records(certificate, "cells", certificate_source)
    by_id: dict[str, dict[str, Any]] = {}
    for index, cell in enumerate(cells):
        label = f"record {index}"
        _record(cell, {"cell_id", "arm", "condition", "tau_frac", "gamma", "alpha", "infeasible"}, certificate_source, label)
        cell_id = _string(cell["cell_id"], f"{_context(certificate_source, label)}.cell_id")
        if cell_id in by_id:
            raise ValueError(f"{certificate_source}: duplicate cell_id {cell_id}")
        by_id[cell_id] = cell
        _string(cell["arm"], f"{_context(certificate_source, label)}.arm")
        _string(cell["condition"], f"{_context(certificate_source, label)}.condition")
        _probability(cell["tau_frac"], f"{_context(certificate_source, label)}.tau_frac")
        _probability(cell["gamma"], f"{_context(certificate_source, label)}.gamma")
        _probability(cell["alpha"], f"{_context(certificate_source, label)}.alpha")
        if not isinstance(cell["infeasible"], bool):
            raise ValueError(f"{_context(certificate_source, label)}.infeasible: expected a boolean")
    missing = sorted(FIGURE4_HILL_CELL_IDS - set(by_id))
    if missing:
        raise ValueError(f"{certificate_source}: missing selected cell IDs {missing}")
    unexpected = [cell_id for cell_id, cell in by_id.items() if cell["arm"] == "spade_cf_m0" and cell["condition"].startswith("hill-") and cell["tau_frac"] == 0.25 and cell["gamma"] in {0.5, 0.95} and cell["alpha"] in {0.8, 0.95} and not cell["infeasible"] and cell_id not in FIGURE4_HILL_CELL_IDS]
    if unexpected:
        raise ValueError(f"{certificate_source}: unexpected selected cell IDs {sorted(unexpected)}")

    hill_containment = []
    for cell_id in sorted(FIGURE4_HILL_CELL_IDS):
        cell = by_id[cell_id]
        label = f"cell {cell_id}"
        expected_condition, expected_tau_frac, expected_gamma, expected_alpha = FIGURE4_HILL_CELL_SPECS[cell_id]
        expected_fields = {
            "arm": "spade_cf_m0",
            "condition": expected_condition,
            "tau_frac": expected_tau_frac,
            "gamma": expected_gamma,
            "alpha": expected_alpha,
            "infeasible": False,
        }
        for field, expected in expected_fields.items():
            if cell[field] != expected:
                raise ValueError(f"{certificate_source} {label}.{field}: expected {expected!r}")
        _record(cell, {"n_nonempty", "empty_rate", "crossfit"}, certificate_source, label)
        n_nonempty = _count(cell["n_nonempty"], f"{_context(certificate_source, label)}.n_nonempty")
        empty_rate = _probability(cell["empty_rate"], f"{_context(certificate_source, label)}.empty_rate")
        crossfit = _mapping(cell["crossfit"], f"{_context(certificate_source, label)}.crossfit")
        _record(crossfit, {"x", "n", "proportion", "ci_lo", "ci_hi"}, certificate_source, f"{label}.crossfit")
        x = _count(crossfit["x"], f"{_context(certificate_source, label)}.crossfit.x")
        n = _count(crossfit["n"], f"{_context(certificate_source, label)}.crossfit.n")
        if x > n:
            raise ValueError(f"{_context(certificate_source, label)}.crossfit: x exceeds n")
        if n != n_nonempty:
            raise ValueError(f"{certificate_source} {label}: cross-fit n does not match non-empty count")
        if n == 0:
            if any(crossfit[key] is not None for key in ("proportion", "ci_lo", "ci_hi")):
                raise ValueError(f"{_context(certificate_source, label)}.crossfit: zero-n evidence must have null estimates")
            proportion = ci_lo = ci_hi = None
        else:
            proportion = _probability(crossfit["proportion"], f"{_context(certificate_source, label)}.crossfit.proportion")
            ci_lo, ci_hi = _probability(crossfit["ci_lo"], f"{_context(certificate_source, label)}.crossfit.ci_lo"), _probability(crossfit["ci_hi"], f"{_context(certificate_source, label)}.crossfit.ci_hi")
            if ci_lo > ci_hi:
                raise ValueError(f"{_context(certificate_source, label)}.crossfit: ci_lo exceeds ci_hi")
            if not np.isclose(proportion, x / n, atol=1e-12):
                raise ValueError(f"{_context(certificate_source, label)}.crossfit: proportion does not match x/n")
        hill_containment.append({"cell_id": cell_id, "condition": cell["condition"], "tau_frac": cell["tau_frac"], "gamma": cell["gamma"], "alpha": cell["alpha"], "x": x, "n": n, "proportion": proportion, "ci_lo": ci_lo, "ci_hi": ci_hi, "empty_rate": empty_rate, "estimator": "crossfit"})

    require_keys(predictions, {"stats"}, predictions_source)
    stats_by_family = _mapping(predictions["stats"], f"{predictions_source}.stats")
    family_stats: dict[str, tuple[int, int, int]] = {}
    for family, value in stats_by_family.items():
        _string(family, f"{predictions_source}.stats family")
        stats = _mapping(value, f"{predictions_source}.stats.{family}")
        _record(stats, {"n_campaigns", "n_cells", "all_empty"}, predictions_source, f"stats.{family}")
        n_campaigns = _count(stats["n_campaigns"], f"{predictions_source}.stats.{family}.n_campaigns", positive=True)
        n_cells = _count(stats["n_cells"], f"{predictions_source}.stats.{family}.n_cells", positive=True)
        all_empty = _count(stats["all_empty"], f"{predictions_source}.stats.{family}.all_empty")
        if all_empty > n_cells:
            raise ValueError(f"{predictions_source}.stats.{family}: all_empty exceeds n_cells")
        family_stats[family] = (n_campaigns, n_cells, all_empty)

    family_rows = _records(families, "rows", families_source)
    family_names: set[str] = set()
    selected_by_family: dict[str, list[dict[str, Any]]] = {}
    campaign_cells_by_family: dict[str, dict[tuple[str, str, int], list[dict[str, Any]]]] = {}
    for index, row in enumerate(family_rows):
        label = f"record {index}"
        _record(row, {"family", "arm", "ce_empty_0.8"}, families_source, label)
        family = _string(row["family"], f"{_context(families_source, label)}.family")
        family_names.add(family)
        arm = _string(row["arm"], f"{_context(families_source, label)}.arm")
        if not isinstance(row["ce_empty_0.8"], bool):
            raise ValueError(f"{_context(families_source, label)}.ce_empty_0.8: expected a boolean")
        if arm != "versionb":
            continue
        _record(row, {"instance", "seed", "gamma", "tau_frac", "ce_empty_0.95"}, families_source, label)
        instance = _string(row["instance"], f"{_context(families_source, label)}.instance")
        seed = _count(row["seed"], f"{_context(families_source, label)}.seed")
        _probability(row["gamma"], f"{_context(families_source, label)}.gamma")
        _probability(row["tau_frac"], f"{_context(families_source, label)}.tau_frac")
        if not isinstance(row["ce_empty_0.95"], bool):
            raise ValueError(f"{_context(families_source, label)}.ce_empty_0.95: expected a boolean")
        campaign_id = (family, instance, seed)
        campaign_cells_by_family.setdefault(family, {}).setdefault(campaign_id, []).append(row)
        if not row["ce_empty_0.8"]:
            _record(row, {"ce_empirical_0.8"}, families_source, label)
            _probability(row["ce_empirical_0.8"], f"{_context(families_source, label)}.ce_empirical_0.8")
            selected_by_family.setdefault(family, []).append(row)

    if not family_stats:
        raise ValueError(f"{predictions_source} family set: expected at least one family")
    if not family_names:
        raise ValueError(f"{families_source} family set: expected at least one family")
    if set(family_stats) != family_names:
        raise ValueError(
            f"{predictions_source} family set does not match {families_source}: "
            f"stats={sorted(family_stats)}, certificate_rows={sorted(family_names)}"
        )

    answer_rate = []
    for family in sorted(family_names):
        n_campaigns, n_cells, expected_all_empty = family_stats[family]
        campaigns = campaign_cells_by_family.get(family, {})
        if len(campaigns) != n_campaigns:
            raise ValueError(
                f"{families_source} {family}: expected {n_campaigns} versionb campaigns, found {len(campaigns)}"
            )
        cells_by_configuration: dict[tuple[float, float], list[dict[str, Any]]] = {}
        for campaign_id, cells in campaigns.items():
            if len(cells) != n_cells:
                raise ValueError(
                    f"{families_source} {family} campaign {campaign_id}: expected {n_cells} gamma-by-tau cells, found {len(cells)}"
                )
            configurations = [(row["gamma"], row["tau_frac"]) for row in cells]
            if len(set(configurations)) != n_cells:
                raise ValueError(f"{families_source} {family} campaign {campaign_id}: duplicate gamma-by-tau cell")
            for configuration, row in zip(configurations, cells, strict=True):
                cells_by_configuration.setdefault(configuration, []).append(row)
        if len(cells_by_configuration) != n_cells or any(
            len(cells) != n_campaigns for cells in cells_by_configuration.values()
        ):
            raise ValueError(f"{families_source} {family}: inconsistent gamma-by-tau campaign grid")
        all_empty = sum(
            all(row["ce_empty_0.95"] for row in cells)
            for cells in cells_by_configuration.values()
        )
        if all_empty != expected_all_empty:
            raise ValueError(
                f"{predictions_source} {family}: all_empty does not match alpha=0.95 certificate rows"
            )
        answered = sum(any(not row["ce_empty_0.95"] for row in cells) for cells in campaigns.values())
        answer_rate.append(
            {
                "family": family,
                "answered": answered,
                "n_campaigns": n_campaigns,
                "answer_rate": answered / n_campaigns,
                "definition": "alpha=0.95 campaign returned any non-empty gamma-by-tau certificate",
            }
        )

    conditional = []
    for family in sorted(family_names):
        selected = selected_by_family.get(family, [])
        x, n = sum(row["ce_empirical_0.8"] == 1.0 for row in selected), len(selected)
        if n:
            # Multiple gamma-by-tau cells share each sampled campaign. Pooling
            # them yields a descriptive proportion, not independent Bernoulli trials.
            conditional.append({"family": family, "alpha": 0.8, "x": x, "n": n, "proportion": x / n, "ci_lo": None, "ci_hi": None, "definition": "descriptive containment across dependent non-empty certificate cells"})
        else:
            conditional.append({"family": family, "alpha": 0.8, "x": 0, "n": 0, "proportion": None, "ci_lo": None, "ci_hi": None, "definition": "no certificate cell returned an answer"})

    output = {"calibration_refinement": calibration, "hill_containment": hill_containment, "cross_family_answer_rate": answer_rate, "cross_family_conditional_containment": conditional}
    assert_no_prohibited_content(output)
    return output
