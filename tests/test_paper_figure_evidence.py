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
    assert contrasts["map_spade_minus_qlognei"]["mean"] == pytest.approx(-0.0330745)
    assert contrasts["regret_spade_minus_qlognei"]["mean"] == pytest.approx(0.0152724734)


def test_figure4_exact_hill_cell_preserves_denominator():
    data = build_figure4_data(RESULTS)
    cells = {row["cell_id"]: row for row in data["hill_containment"]}
    cell = cells["spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"]
    assert (cell["x"], cell["n"]) == (43, 50)
    assert cell["empty_rate"] == pytest.approx(0.50)
    assert cell["estimator"] == "crossfit"


def test_ambiguous_duplicate_certificate_cell_fails(tmp_path):
    source = json.loads((RESULTS / "final-spade-certificate.json").read_text())
    source["cells"].append(source["cells"][0])
    (tmp_path / "final-spade-certificate.json").write_text(json.dumps(source))
    for name in ("p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json"):
        (tmp_path / name).write_bytes((RESULTS / name).read_bytes())
    with pytest.raises(ValueError, match="duplicate cell_id"):
        build_figure4_data(tmp_path)
