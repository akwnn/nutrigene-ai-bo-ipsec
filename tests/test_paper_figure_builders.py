from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.style import get_preset


def test_figure1_defines_campaign_decisions_and_estimands():
    bundle = build_figure1(get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["stages"] == ["formulation", "wells", "assay", "model"]
    assert set(bundle.panel_data["B"]["branches"]) == {"point decision", "region decision"}
    assert "contains no performance result" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 3

    plt.close(bundle.figure)


def test_figure1_panel_b_names_required_point_deliverables():
    bundle = build_figure1(get_preset("portable"))

    point_deliverables = bundle.panel_data["B"]["point deliverables"]
    assert "noisy selection" in point_deliverables
    assert "model recommendation" in point_deliverables
    assert "noisy-readout" not in point_deliverables
    assert "model" not in point_deliverables

    plt.close(bundle.figure)


@pytest.mark.parametrize("name", ["portable", "rsc", "nature"])
def test_figure1_estimand_table_uses_preset_body_typography(name):
    preset = get_preset(name)
    bundle = build_figure1(preset)
    table = bundle.figure.axes[2].tables[0]

    assert all(cell.get_text().get_fontsize() >= preset.body_pt for cell in table.get_celld().values())

    plt.close(bundle.figure)
