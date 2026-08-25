from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
import pytest

from boec.paper_figures.evidence import build_figure2_data
from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.figure2 import build_figure2
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


def test_figure1_portable_text_stays_inside_decision_boxes_and_ledger_cells():
    bundle = build_figure1(get_preset("portable"))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()

    panel_b = figure.axes[1]
    decision_boxes = [patch for patch in panel_b.patches if patch.get_linestyle() == "--"]
    assert len(decision_boxes) == 2
    for box in decision_boxes:
        box_bounds = box.get_window_extent(renderer)
        text = next(
            text for text in panel_b.texts if text.get_text().startswith(
                "Point decision" if box is decision_boxes[0] else "Region decision"
            )
        )
        text_bounds = text.get_window_extent(renderer)
        assert box_bounds.contains(*text_bounds.get_points()[0])
        assert box_bounds.contains(*text_bounds.get_points()[1])

    table = figure.axes[2].tables[0]
    for cell in table.get_celld().values():
        cell_bounds = cell.get_window_extent(renderer)
        text_bounds = cell.get_text().get_window_extent(renderer)
        assert cell_bounds.contains(*text_bounds.get_points()[0])
        assert cell_bounds.contains(*text_bounds.get_points()[1])

    plt.close(figure)


def test_figure2_encodes_same_campaign_rules_contrasts_and_decomposition():
    data = build_figure2_data(Path("results"))
    bundle = build_figure2(data, get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["pairing"] == "same campaigns"
    assert bundle.panel_data["B"]["reference"] == 0.0
    assert bundle.panel_data["C"]["identity"] == "Rule A = search loss + identification loss"
    assert "same campaigns" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 3

    plt.close(bundle.figure)


def test_figure2_rendered_text_states_terminal_rule_semantics():
    bundle = build_figure2(build_figure2_data(Path("results")), get_preset("portable"))
    bundle.figure.canvas.draw()
    rendered_text = {
        " ".join(text.get_text().split())
        for text in bundle.figure.findobj(match=Text)
        if text.get_text()
    }

    assert "Rule A = search loss + identification loss" in rendered_text
    assert any(
        "blue: search loss" in text and "orange: identification loss" in text
        for text in rendered_text
    )
    assert any("← P lower" in text and "P higher →" in text for text in rendered_text)
    assert {"Classical DoE", "qLogEI", "qLogNEI", "SPADE"} <= rendered_text

    plt.close(bundle.figure)


def test_figure2_portable_text_stays_inside_the_rendered_figure():
    bundle = build_figure2(build_figure2_data(Path("results")), get_preset("portable"))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    figure_bounds = figure.bbox

    for text in figure.findobj(match=Text):
        if text.get_text():
            text_bounds = text.get_window_extent(renderer)
            assert figure_bounds.contains(*text_bounds.get_points()[0])
            assert figure_bounds.contains(*text_bounds.get_points()[1])

    plt.close(figure)
