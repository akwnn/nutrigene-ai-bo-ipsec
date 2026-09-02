from __future__ import annotations

import json
from pathlib import Path

import pytest

from boec.paper_figures.evidence import (
    build_figure2_data,
    build_figure3_data,
    build_figure4_data,
)


RESULTS = Path("results")


def _copy_sources(tmp_path: Path, *names: str) -> None:
    for name in names:
        (tmp_path / name).write_bytes((RESULTS / name).read_bytes())


def test_figure2_uses_current_fix1_values():
    data = build_figure2_data(RESULTS)
    by_arm = {row["arm"]: row for row in data["rule_means"]}
    assert by_arm["doe"]["rule_a"] == pytest.approx(0.0958008941)
    assert by_arm["doe"]["rule_p"] == pytest.approx(0.1992871533)
    assert by_arm["versionb"]["rule_p"] == pytest.approx(0.1003171922)
    for row in data["decomposition"]:
        assert row["rule_a"] == pytest.approx(
            row["oracle_best"] + row["identification_gap"]
        )


def test_figure3_uses_common_rule_p_and_excludes_boundary_arm():
    data = build_figure3_data(RESULTS)
    encoded = json.dumps(data)
    assert "spade_random_plate2" not in encoded
    assert "KF-3" not in encoded and "KF-4" not in encoded
    target = {row["arm"]: row for row in data["target_points"]}
    assert target["spade_cf_m0"]["regret_p"] == pytest.approx(0.0843635436)
    assert target["spade_cf_m0"]["map_error"] == pytest.approx(0.180414)
    contrasts = {row["contrast_id"]: row for row in data["contrasts"]}
    assert contrasts["map_spade_minus_qlognei"]["mean"] == pytest.approx(-0.0326545)
    assert contrasts["regret_spade_minus_qlognei"]["mean"] == pytest.approx(0.0093747607)


def test_figure4_exact_hill_cell_preserves_denominator():
    data = build_figure4_data(RESULTS)
    cells = {row["cell_id"]: row for row in data["hill_containment"]}
    cell = cells["spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"]
    assert (cell["x"], cell["n"]) == (43, 50)
    assert cell["empty_rate"] == pytest.approx(0.50)
    assert cell["estimator"] == "crossfit"


def test_figure4_cross_family_answer_rate_uses_alpha_095_campaigns():
    data = build_figure4_data(RESULTS)
    answer_rows = {row["family"]: row for row in data["cross_family_answer_rate"]}

    assert {
        family: (row["answered"], row["n_campaigns"])
        for family, row in answer_rows.items()
    } == {
        "ackley": (0, 50),
        "hartmann6": (11, 50),
        "hill": (50, 50),
        "levy": (49, 50),
        "rosenbrock": (50, 50),
    }
    assert answer_rows["ackley"]["answer_rate"] == 0.0
    assert all("alpha=0.95" in row["definition"] for row in answer_rows.values())
    assert all("campaign" in row["definition"] for row in answer_rows.values())


def test_ambiguous_duplicate_certificate_cell_fails(tmp_path):
    source = json.loads((RESULTS / "final-spade-certificate.json").read_text())
    source["cells"].append(source["cells"][0])
    (tmp_path / "final-spade-certificate.json").write_text(json.dumps(source))
    for name in ("p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json"):
        (tmp_path / name).write_bytes((RESULTS / name).read_bytes())
    with pytest.raises(ValueError, match="duplicate cell_id"):
        build_figure4_data(tmp_path)


def test_figure2_rejects_duplicate_selected_analysis_arm(tmp_path):
    analysis = json.loads((RESULTS / "fix1-analysis.json").read_text())
    analysis["per_arm"].append(analysis["per_arm"][0])
    (tmp_path / "fix1-analysis.json").write_text(json.dumps(analysis))
    _copy_sources(tmp_path, "fix1-terminal-rule.json", "step0-oracle-best.json")

    with pytest.raises(ValueError, match="fix1-analysis.json.*doe.*exactly one"):
        build_figure2_data(tmp_path)


def test_figure3_rejects_duplicate_target_arm(tmp_path):
    pareto = json.loads((RESULTS / "final-spade-regret-pareto.json").read_text())
    target = next(
        row
        for row in pareto["rows"]
        if row["condition"] == "hill-d6-s0.1" and row["arm"] == "doe"
    )
    pareto["rows"].append(target)
    (tmp_path / "final-spade-regret-pareto.json").write_text(json.dumps(pareto))
    _copy_sources(tmp_path, "final-spade-kill-ledger.json")

    with pytest.raises(ValueError, match="final-spade-regret-pareto.json.*doe.*exactly one"):
        build_figure3_data(tmp_path)


def test_figure3_rejects_missing_target_arm(tmp_path):
    pareto = json.loads((RESULTS / "final-spade-regret-pareto.json").read_text())
    pareto["rows"] = [
        row
        for row in pareto["rows"]
        if not (row["condition"] == "hill-d6-s0.1" and row["arm"] == "doe")
    ]
    (tmp_path / "final-spade-regret-pareto.json").write_text(json.dumps(pareto))
    _copy_sources(tmp_path, "final-spade-kill-ledger.json")

    with pytest.raises(ValueError, match="final-spade-regret-pareto.json.*doe.*exactly one"):
        build_figure3_data(tmp_path)


def test_figure4_rejects_missing_selected_certificate_cell(tmp_path):
    certificate = json.loads((RESULTS / "final-spade-certificate.json").read_text())
    certificate["cells"] = [
        cell
        for cell in certificate["cells"]
        if cell["cell_id"] != "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"
    ]
    (tmp_path / "final-spade-certificate.json").write_text(json.dumps(certificate))
    _copy_sources(tmp_path, "p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json")

    with pytest.raises(ValueError, match="final-spade-certificate.json.*missing selected cell"):
        build_figure4_data(tmp_path)


def test_figure4_rejects_expected_certificate_id_with_infeasible_status(tmp_path):
    certificate = json.loads((RESULTS / "final-spade-certificate.json").read_text())
    cell = next(
        cell
        for cell in certificate["cells"]
        if cell["cell_id"] == "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"
    )
    cell["infeasible"] = True
    (tmp_path / "final-spade-certificate.json").write_text(json.dumps(certificate))
    _copy_sources(tmp_path, "p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json")

    with pytest.raises(ValueError, match="final-spade-certificate.json.*infeasible"):
        build_figure4_data(tmp_path)


@pytest.mark.parametrize(
    ("source", "mutate", "match"),
    [
        (
            "p8-predictions.json",
            lambda payload: payload["stats"].pop("ackley"),
            "p8-predictions.json.*family set",
        ),
        (
            "p8-certificate-families.json",
            lambda payload: payload.__setitem__("rows", []),
            "p8-certificate-families.json.*family set",
        ),
    ],
)
def test_figure4_rejects_empty_or_mismatched_cross_family_sources(
    tmp_path, source, mutate, match
):
    payload = json.loads((RESULTS / source).read_text())
    mutate(payload)
    (tmp_path / source).write_text(json.dumps(payload))
    _copy_sources(
        tmp_path,
        *(
            name
            for name in (
                "p7-murphy.json",
                "final-spade-certificate.json",
                "p8-predictions.json",
                "p8-certificate-families.json",
            )
            if name != source
        ),
    )

    with pytest.raises(ValueError, match=match):
        build_figure4_data(tmp_path)


def test_figure2_rejects_oracle_raw_count_that_does_not_reconcile(tmp_path):
    oracle = json.loads((RESULTS / "step0-oracle-best.json").read_text())
    for index, row in enumerate(oracle["rows"]):
        if row["arm"] == "doe":
            del oracle["rows"][index]
            break
    (tmp_path / "step0-oracle-best.json").write_text(json.dumps(oracle))
    _copy_sources(tmp_path, "fix1-terminal-rule.json", "fix1-analysis.json")

    with pytest.raises(ValueError, match="step0-oracle-best.json.*doe.*raw-row count"):
        build_figure2_data(tmp_path)


@pytest.mark.parametrize(
    ("source", "mutate", "builder", "required"),
    [
        (
            "fix1-terminal-rule.json",
            lambda payload: payload["rows"][0].__setitem__("regret_a", float("nan")),
            build_figure2_data,
            ("fix1-analysis.json", "step0-oracle-best.json"),
        ),
        (
            "final-spade-regret-pareto.json",
            lambda payload: next(
                row
                for row in payload["rows"]
                if row["condition"] == "hill-d6-s0.1" and row["arm"] == "doe"
            )["regret"].__setitem__("P", float("inf")),
            build_figure3_data,
            ("final-spade-kill-ledger.json",),
        ),
        (
            "final-spade-kill-ledger.json",
            lambda payload: payload["kills"]["KF-6"].__setitem__("effect", float("nan")),
            build_figure3_data,
            ("final-spade-regret-pareto.json",),
        ),
        (
            "p7-murphy.json",
            lambda payload: payload["rows"][0].__setitem__("pred_calibration", float("nan")),
            build_figure4_data,
            ("final-spade-certificate.json", "p8-predictions.json", "p8-certificate-families.json"),
        ),
        (
            "final-spade-certificate.json",
            lambda payload: next(
                cell
                for cell in payload["cells"]
                if cell["cell_id"] == "spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"
            )["crossfit"].__setitem__("ci_hi", float("inf")),
            build_figure4_data,
            ("p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json"),
        ),
        (
            "p8-predictions.json",
            lambda payload: next(iter(payload["stats"].values())).__setitem__("all_empty", float("nan")),
            build_figure4_data,
            ("p7-murphy.json", "final-spade-certificate.json", "p8-certificate-families.json"),
        ),
        (
            "p8-certificate-families.json",
            lambda payload: payload["rows"][0].__setitem__("ce_empirical_0.8", float("nan")),
            build_figure4_data,
            ("p7-murphy.json", "final-spade-certificate.json", "p8-predictions.json"),
        ),
    ],
)
def test_nonfinite_selected_evidence_fails_with_source_context(
    tmp_path, source, mutate, builder, required
):
    payload = json.loads((RESULTS / source).read_text())
    mutate(payload)
    (tmp_path / source).write_text(json.dumps(payload))
    _copy_sources(tmp_path, *required)

    with pytest.raises(ValueError, match=source):
        builder(tmp_path)


def test_selected_malformed_figure3_record_has_contextual_value_error(tmp_path):
    pareto = json.loads((RESULTS / "final-spade-regret-pareto.json").read_text())
    target = next(
        row
        for row in pareto["rows"]
        if row["condition"] == "hill-d6-s0.1" and row["arm"] == "doe"
    )
    del target["regret"]
    (tmp_path / "final-spade-regret-pareto.json").write_text(json.dumps(pareto))
    _copy_sources(tmp_path, "final-spade-kill-ledger.json")

    with pytest.raises(ValueError, match="final-spade-regret-pareto.json.*record.*missing keys"):
        build_figure3_data(tmp_path)
