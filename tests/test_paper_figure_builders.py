from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.colors import to_hex
from matplotlib.text import Text
import numpy as np
import pytest

from boec.paper_figures.evidence import build_figure2_data, build_figure3_data, build_figure4_data
from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.figure2 import build_figure2
from boec.paper_figures.figure3 import build_figure3
from boec.paper_figures.figure4 import build_figure4
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
    panel_a_labels = {
        " ".join(text.get_text().split())
        for text in bundle.figure.axes[0].texts
        if text.get_text()
    }
    assert {"Classical DoE", "qLogEI", "qLogNEI", "SPADE"} <= panel_a_labels

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


def test_figure3_separates_point_map_and_cost_without_boundary_evidence():
    data = build_figure3_data(Path("results"))
    bundle = build_figure3(data, get_preset("portable"))

    assert bundle.panel_data["A"]["terminal_rule"] == "P"
    assert bundle.panel_data["B"]["sesoi"] == 0.02
    assert bundle.panel_data["C"]["rounds_are_not_point_size"] is True
    assert all(row["evidence_stage"].startswith("descriptive") for row in bundle.panel_data["D"]["rows"])
    assert "spade_random_plate2" not in str(bundle.panel_data)
    assert "KF-3" not in str(bundle.panel_data)
    assert "KF-4" not in str(bundle.panel_data)
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


def test_figure3_rendered_panels_preserve_pareto_contrasts_costs_and_descriptive_status():
    data = build_figure3_data(Path("results"))
    bundle = build_figure3(data, get_preset("portable"))
    figure = bundle.figure
    figure.canvas.draw()
    panel_a, panel_b, panel_c, panel_d = figure.axes

    assert "Symmetric-difference error" in panel_a.get_xlabel()
    assert "Rule-P simple regret" in panel_a.get_ylabel()
    assert "better" in panel_a.get_xlabel()
    assert {text.get_text() for text in panel_a.texts} >= {"SPADE", "qLogNEI", "Sobol"}

    expected_contrasts = {
        "map_spade_minus_sobol": ("Map: SPADE − Sobol", -0.010892, -0.01566185, -0.0059691125),
        "map_spade_minus_qlognei": ("Map: SPADE − qLogNEI", -0.0330745, -0.038435375, -0.0281399125),
        "regret_spade_minus_qlognei": ("Regret: SPADE − qLogNEI", 0.0152724734, 0.0081584845, 0.0223052340),
    }
    assert {row["contrast_id"] for row in data["contrasts"]} == set(expected_contrasts)
    assert {row["sesoi"] for row in data["contrasts"]} == {0.02}
    points_by_y = {
        int(collection.get_offsets()[0, 1]): float(collection.get_offsets()[0, 0])
        for collection in panel_b.collections
        if isinstance(collection, PathCollection) and len(collection.get_offsets()) == 1
    }
    intervals_by_y = {
        int(collection.get_segments()[0][0, 1]): tuple(collection.get_segments()[0][:, 0])
        for collection in panel_b.collections
        if collection.__class__.__name__ == "LineCollection"
    }
    for y_position, contrast_id in enumerate(
        ("map_spade_minus_sobol", "map_spade_minus_qlognei", "regret_spade_minus_qlognei")
    ):
        label, mean, lo, hi = expected_contrasts[contrast_id]
        assert panel_b.get_yticklabels()[y_position].get_text() == label
        assert points_by_y[y_position] == pytest.approx(mean)
        assert intervals_by_y[y_position] == pytest.approx((lo, hi))
    assert any(
        np.isclose(patch.get_x(), -0.02)
        and np.isclose(patch.get_x() + patch.get_width(), 0.02)
        for patch in panel_b.patches
    )
    assert tuple(panel_b.get_yticklabels()[index].get_text() for index in range(3)) == (
        "Map: SPADE − Sobol",
        "Map: SPADE − qLogNEI",
        "Regret: SPADE − qLogNEI",
    )
    assert "±0.02" in panel_b.get_title(loc="left")

    table = panel_c.tables[0]
    cell_text = {cell.get_text().get_text() for cell in table.get_celld().values()}
    assert {"Method", "Wells", "Rounds"} <= cell_text
    assert {str(row["wells"]) for row in data["cost_ledger"]} <= cell_text
    assert {str(row["rounds"]) for row in data["cost_ledger"]} <= cell_text
    assert not panel_c.collections

    assert "descriptive" in panel_d.get_title(loc="left").lower()
    assert "intervals unavailable" in panel_d.get_title(loc="left").lower()
    assert not panel_d.lines
    assert {text.get_text() for text in panel_d.get_legend().get_texts()} == {
        "Classical DoE", "Latin hypercube", "Sobol", "qLogEI", "qLogNEI", "SPADE"
    }
    assert "thin border: d=6; thick dashed: d=8" in {text.get_text() for text in panel_d.texts}
    assert {float(size) for collection in panel_a.collections for size in collection.get_sizes()} == {34.0}
    assert {float(size) for collection in panel_d.collections for size in collection.get_sizes()} == {24.0}

    hartmann_points = {collection.get_gid(): collection for collection in panel_d.collections}
    arms = ("doe", "lhs", "sobol", "qlogei", "qlognei", "spade_cf_m0")
    conditions = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
    assert set(hartmann_points) == {f"{condition}:{arm}" for condition in conditions for arm in arms}
    for condition in conditions:
        assert to_hex(hartmann_points[f"{condition}:qlogei"].get_facecolors()[0]) == "#ffffff"
        assert to_hex(hartmann_points[f"{condition}:qlognei"].get_facecolors()[0]) == "#0072b2"
        assert to_hex(hartmann_points[f"{condition}:lhs"].get_facecolors()[0]) == "#ffffff"
        assert to_hex(hartmann_points[f"{condition}:sobol"].get_facecolors()[0]) == "#6b7280"
    assert hartmann_points["hartmann6-d6-s0.25:doe"].get_linewidths()[0] != hartmann_points["hartmann6-d8-s0.25:doe"].get_linewidths()[0]

    plt.close(figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure3_rendered_text_is_contained_in_each_panel_for_every_preset(preset_name):
    bundle = build_figure3(build_figure3_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    figure_bounds = figure.bbox

    for axis in figure.axes:
        for text in axis.findobj(match=Text):
            if text.get_text():
                text_bounds = text.get_window_extent(renderer)
                assert figure_bounds.contains(*text_bounds.get_points()[0])
                assert figure_bounds.contains(*text_bounds.get_points()[1])

    table = figure.axes[2].tables[0]
    for cell in table.get_celld().values():
        cell_bounds = cell.get_window_extent(renderer)
        text_bounds = cell.get_text().get_window_extent(renderer)
        assert cell_bounds.contains(*text_bounds.get_points()[0])
        assert cell_bounds.contains(*text_bounds.get_points()[1])

    plt.close(figure)


def test_figure3_contrast_labels_follow_ids_not_input_order():
    data = deepcopy(build_figure3_data(Path("results")))
    data["contrasts"].reverse()
    bundle = build_figure3(data, get_preset("portable"))
    panel_b = bundle.figure.axes[1]
    observed = {
        int(collection.get_offsets()[0, 1]): float(collection.get_offsets()[0, 0])
        for collection in panel_b.collections
        if isinstance(collection, PathCollection) and len(collection.get_offsets()) == 1
    }

    assert observed == pytest.approx({0: -0.010892, 1: -0.0330745, 2: 0.0152724734})

    plt.close(bundle.figure)


def test_figure3_rejects_contrasts_without_expected_ids_or_common_sesoi():
    missing = deepcopy(build_figure3_data(Path("results")))
    missing["contrasts"] = missing["contrasts"][:2]
    with pytest.raises(ValueError, match="expected contrast IDs"):
        build_figure3(missing, get_preset("portable"))

    mismatched_sesoi = deepcopy(build_figure3_data(Path("results")))
    mismatched_sesoi["contrasts"][0]["sesoi"] = 0.01
    with pytest.raises(ValueError, match="common SESOI"):
        build_figure3(mismatched_sesoi, get_preset("portable"))


def test_figure4_keeps_calibration_containment_and_answer_rate_distinct():
    data = build_figure4_data(Path("results"))
    bundle = build_figure4(data, get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C", "D"}
    assert all(row["estimator"] == "crossfit" for row in bundle.panel_data["B"]["rows"])
    assert bundle.panel_data["C"]["zero_means"] == "declined to certify"
    assert bundle.panel_data["D"]["effect"] == "containment minus nominal"
    assert "non-empty" in bundle.alt_text
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure4_rendered_panels_keep_exact_denominators_and_certification_states_distinct(preset_name):
    data = build_figure4_data(Path("results"))
    preset = get_preset(preset_name)
    bundle = build_figure4(data, preset)
    figure = bundle.figure
    figure.canvas.draw()
    panel_a, panel_b, panel_c, panel_d = figure.axes

    assert "retrospective hill" in panel_a.get_title(loc="left").lower()
    assert "descriptive" in panel_a.get_title(loc="left").lower()
    assert all(row["estimator"] == "crossfit" for row in bundle.panel_data["B"]["rows"])

    hill_points = {
        collection.get_gid(): collection
        for collection in panel_b.collections
        if isinstance(collection, PathCollection)
    }
    hill_intervals = {
        collection.get_gid(): collection
        for collection in panel_b.collections
        if isinstance(collection, LineCollection)
    }
    for row in data["hill_containment"]:
        point_id = f"hill:{row['cell_id']}"
        if row["n"]:
            point = hill_points[point_id]
            assert tuple(point.get_offsets()[0]) == pytest.approx((row["proportion"] - row["alpha"], data["hill_containment"].index(row)))
            interval = hill_intervals[f"hill-interval:{row['cell_id']}"]
            assert tuple(interval.get_segments()[0][:, 0]) == pytest.approx((row["ci_lo"] - row["alpha"], row["ci_hi"] - row["alpha"]))
            assert f"{row['x']}/{row['n']}" in {text.get_text() for text in panel_b.texts}
            expected_colour = "#b2182b" if row["ci_hi"] < row["alpha"] else "#009e73"
            assert to_hex(point.get_facecolors()[0]) == expected_colour
        else:
            assert point_id not in hill_points
            assert any(
                "no non-empty certificate" in " ".join(text.get_text().split()).lower()
                for text in panel_b.texts
            )
            assert "0/0" not in {text.get_text() for text in panel_b.texts}

    answer_bars = {patch.get_gid(): patch for patch in panel_c.patches}
    expected_answer_counts = {
        "ackley": (0, 50),
        "hartmann6": (11, 50),
        "hill": (50, 50),
        "levy": (49, 50),
        "rosenbrock": (50, 50),
    }
    for family, (answered, n_campaigns) in expected_answer_counts.items():
        assert answer_bars[f"answer-rate:{family}"].get_width() == pytest.approx(answered / n_campaigns)
        assert f"{answered}/{n_campaigns}" in {text.get_text() for text in panel_c.texts}
    assert bundle.panel_data["C"]["scope"] == "alpha=0.95 campaigns; any non-empty gamma-by-tau certificate"
    assert "declined to certify" in panel_c.get_title(loc="left").lower()
    assert "not zero containment" in panel_c.get_title(loc="left").lower()

    conditional_points = {
        collection.get_gid(): collection
        for collection in panel_d.collections
        if isinstance(collection, PathCollection)
    }
    conditional_intervals = {
        collection.get_gid(): collection
        for collection in panel_d.collections
        if isinstance(collection, LineCollection)
    }
    for row in data["cross_family_conditional_containment"]:
        point_id = f"conditional:{row['family']}"
        if row["n"]:
            point = conditional_points[point_id]
            assert float(point.get_offsets()[0, 0]) == pytest.approx(row["proportion"] - row["alpha"])
            interval = conditional_intervals[f"conditional-interval:{row['family']}"]
            assert tuple(interval.get_segments()[0][:, 0]) == pytest.approx((row["ci_lo"] - row["alpha"], row["ci_hi"] - row["alpha"]))
            assert f"{row['x']}/{row['n']}" in {text.get_text() for text in panel_d.texts}
            expected_colour = "#b2182b" if row["ci_hi"] < row["alpha"] else "#009e73"
            assert to_hex(point.get_facecolors()[0]) == expected_colour
        else:
            assert point_id not in conditional_points
            assert any(
                "declined to certify" in " ".join(text.get_text().split()).lower()
                for text in panel_d.texts
            )
            assert "0/0" not in {text.get_text() for text in panel_d.texts}

    assert bundle.panel_data["D"]["effect"] == "containment minus nominal"
    assert "holm" not in " ".join(text.get_text().lower() for text in figure.findobj(match=Text))
    for axis in figure.axes:
        assert axis.title.get_size() >= preset.body_pt
        assert axis.xaxis.label.get_size() >= preset.body_pt
        assert axis.yaxis.label.get_size() >= preset.body_pt

    plt.close(figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure4_declined_certification_labels_stay_inside_their_containment_panels(preset_name):
    bundle = build_figure4(build_figure4_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()

    for axis, panel_label_text in zip((figure.axes[1], figure.axes[3]), ("b", "d"), strict=True):
        axis_bounds = axis.get_window_extent(renderer)
        for text in axis.texts:
            if text.get_text() == panel_label_text or "declined" not in text.get_text().lower():
                continue
            text_bounds = text.get_window_extent(renderer)
            assert axis_bounds.contains(*text_bounds.get_points()[0])
            assert axis_bounds.contains(*text_bounds.get_points()[1])

    plt.close(figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure4_rendered_text_stays_inside_the_figure_for_every_preset(preset_name):
    bundle = build_figure4(build_figure4_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()

    for text in figure.findobj(match=Text):
        if text.get_text():
            text_bounds = text.get_window_extent(renderer)
            assert figure.bbox.contains(*text_bounds.get_points()[0])
            assert figure.bbox.contains(*text_bounds.get_points()[1])

    plt.close(figure)
