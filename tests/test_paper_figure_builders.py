from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.colors import to_hex
from matplotlib.patches import FancyArrowPatch
from matplotlib.text import Text
from matplotlib.transforms import Bbox
import numpy as np
import pytest

from boec.paper_figures.evidence import (
    build_certification_data,
    build_spade_evidence_data,
    build_terminal_rule_data,
)
from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.figure2 import build_figure2
from boec.paper_figures.figure3 import build_figure3
from boec.paper_figures.figure4 import build_figure4
from boec.paper_figures.figure5 import build_figure5
from boec.paper_figures.landscape_glyphs import LANDSCAPE_FAMILIES, landscape_slice
from boec.paper_figures.qa import assert_registered_geometry
from boec.paper_figures.style import get_preset, method_style


def test_figure1_separates_landscapes_methods_campaign_and_outputs():
    bundle = build_figure1(get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["families"] == [
        "hill", "ackley", "hartmann6", "levy", "rosenbrock"
    ]
    assert bundle.panel_data["B"]["method_families"] == [
        "classical experimental design",
        "space-filling design",
        "sequential Bayesian optimization",
        "SPADE",
    ]
    assert bundle.panel_data["C"]["campaign_wells"] == 48
    assert set(bundle.panel_data["C"]["outputs"]) == {
        "point", "region map", "certificate", "experimental cost"
    }

    plt.close(bundle.figure)


@pytest.mark.parametrize("family", LANDSCAPE_FAMILIES)
def test_landscape_glyph_is_deterministic_finite_vector_data(family):
    first = landscape_slice(family, resolution=48)
    second = landscape_slice(family, resolution=48)

    assert np.array_equal(first.z, second.z)
    assert first.z.shape == (48, 48)
    assert np.isfinite(first.z).all()
    assert first.z.min() == pytest.approx(0.0)
    assert first.z.max() == pytest.approx(1.0)


def test_figure5_uses_math_font_for_symbols_missing_from_charis():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bundle = build_figure5(build_certification_data(Path("results")), get_preset("portable"))
        bundle.figure.canvas.draw()

    missing_glyphs = [
        warning for warning in caught if "missing from font(s) Charis SIL" in str(warning.message)
    ]
    assert not missing_glyphs
    plt.close(bundle.figure)


def test_figure2_defines_campaign_decisions_and_estimands():
    bundle = build_figure2(get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.layout_rows == (("A", "B"), ("C",))
    assert bundle.headline == "One 48-well campaign supports distinct scientific decisions"
    assert bundle.deck == (
        "Observation, selection, mapping and certification are different reported objects"
    )
    expected_panel_titles = {
        "a": "Campaign observation loop",
        "b": "Point and region decisions",
        "c": "Estimand ledger",
    }
    visible_figure_text = {text.get_text() for text in bundle.figure.texts}
    panel_titles = {
        label: title
        for label, title in expected_panel_titles.items()
        if title in visible_figure_text
    }
    assert panel_titles == expected_panel_titles
    assert bundle.panel_data["A"]["stages"] == ["formulation", "wells", "assay", "model"]
    assert set(bundle.panel_data["B"]["branches"]) == {"point decision", "region decision"}
    assert "contains no performance result" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


def test_figure2_campaign_observation_path_is_a_closed_loop():
    bundle = build_figure2(get_preset("portable"))

    panel_a_connectors = bundle.figure.axes[1].findobj(match=FancyArrowPatch)
    assert {connector.get_gid() for connector in panel_a_connectors} >= {
        "campaign-return-loop"
    }

    plt.close(bundle.figure)


def test_figure2_panel_b_names_required_point_deliverables():
    bundle = build_figure2(get_preset("portable"))

    point_deliverables = bundle.panel_data["B"]["point deliverables"]
    assert point_deliverables == (
        "tested-best",
        "measured selection",
        "model recommendation",
        "confirmation",
    )
    assert "noisy-readout" not in point_deliverables
    assert "model" not in point_deliverables

    plt.close(bundle.figure)


@pytest.mark.parametrize("name", ["portable", "rsc", "nature"])
def test_figure2_estimand_table_uses_preset_body_typography(name):
    preset = get_preset(name)
    bundle = build_figure2(preset)
    table = bundle.figure.axes[3].tables[0]

    assert all(cell.get_text().get_fontsize() >= preset.body_pt for cell in table.get_celld().values())

    plt.close(bundle.figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure2_text_stays_inside_nodes_and_ledger_cells_for_every_preset(preset_name):
    bundle = build_figure2(get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()

    assert_registered_geometry(figure)
    registrations = figure._paper_geometry
    assert all(item.padding_pt == 2.0 for item in registrations)
    registered_labels = {item.label for item in registrations}
    assert "same-sampled-campaign" in registered_labels
    assert {
        f"ledger-r{row}-c{column}"
        for row in range(7)
        for column in range(6)
    } <= registered_labels

    table = figure.axes[3].tables[0]
    pad = renderer.points_to_pixels(2.0)
    for cell in table.get_celld().values():
        cell_bounds = cell.get_window_extent(renderer)
        text_bounds = cell.get_text().get_window_extent(renderer)
        padded_cell_bounds = Bbox.from_extents(
            cell_bounds.x0 + pad,
            cell_bounds.y0 + pad,
            cell_bounds.x1 - pad,
            cell_bounds.y1 - pad,
        )
        assert padded_cell_bounds.contains(*text_bounds.get_points()[0])
        assert padded_cell_bounds.contains(*text_bounds.get_points()[1])

    connectors = figure.findobj(match=FancyArrowPatch)
    text_extents = [
        text.get_window_extent(renderer)
        for text in figure.findobj(match=Text)
        if text.get_visible() and text.get_text()
    ]
    assert connectors
    for connector in connectors:
        rendered_path = connector.get_path().transformed(connector.get_transform())
        connector_bounds = rendered_path.get_extents()
        sampled_path = rendered_path.interpolated(32)
        assert not any(
            connector_bounds.overlaps(text_extent)
            and any(text_extent.contains(*point) for point in sampled_path.vertices)
            for text_extent in text_extents
        )

    plt.close(figure)


def test_figure2_includes_editorial_caption_and_long_description():
    bundle = build_figure2(get_preset("portable"))

    assert "no performance result" in bundle.caption.lower()
    assert "point" in bundle.long_description.lower()
    assert "region" in bundle.long_description.lower()

    plt.close(bundle.figure)


def test_figure3_encodes_same_campaign_rules_contrasts_and_decomposition():
    data = build_terminal_rule_data(Path("results"))
    bundle = build_figure3(data, get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.layout_rows == (("A",), ("B", "C"))
    assert bundle.headline == "The terminal rule changes method rankings on the same campaigns"
    assert bundle.deck == (
        "Hill · d=6 · σ=0.25 · n=50 paired campaigns · 95% paired-bootstrap intervals"
    )
    assert bundle.panel_data["A"]["pairing"] == "same campaigns"
    assert bundle.panel_data["A"]["reference"] == 0.0
    assert bundle.panel_data["A"]["dominant_panel"] is True
    assert bundle.panel_data["C"]["identity"] == "Rule A = search loss + identification loss"
    assert "same campaigns" in bundle.alt_text.lower()
    expected_panel_titles = {
        "a": "Paired terminal-rule effect",
        "b": "Mean regret by rule",
        "c": "What Rule A combines",
    }
    visible_figure_text = {text.get_text() for text in bundle.figure.texts}
    panel_titles = {
        label: title
        for label, title in expected_panel_titles.items()
        if title in visible_figure_text
    }
    assert panel_titles == expected_panel_titles
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


def test_figure3_preserves_every_terminal_rule_value_and_numerical_mark():
    bundle = build_figure3(build_terminal_rule_data(Path("results")), get_preset("portable"))
    figure = bundle.figure
    figure.canvas.draw()
    _, panel_a, panel_b, panel_c = figure.axes

    expected_contrasts = {
        "doe": (0.10348625913954412, 0.07225003121385253, 0.13667376335054549, 50),
        "qlogei": (-0.03203675680145408, -0.04892103581591358, -0.015074944183211461, 50),
        "qlognei": (-0.02461824959888463, -0.04168010918755903, -0.007641877264361989, 50),
        "versionb": (-0.054323796385480565, -0.06928781070598541, -0.03984640664834545, 50),
    }
    contrast_rows = {row["arm"]: row for row in bundle.panel_data["A"]["rows"]}
    assert set(contrast_rows) == set(expected_contrasts)
    for arm, expected in expected_contrasts.items():
        row = contrast_rows[arm]
        assert (row["mean"], row["lo"], row["hi"], row["n"]) == pytest.approx(expected)
        interval = next(
            collection
            for collection in panel_a.collections
            if collection.get_gid() == f"paired:{arm}"
        )
        segment = interval.get_segments()[0]
        assert segment[:, 0] == pytest.approx((expected[1], expected[2]))
        point = next(
            collection
            for collection in panel_a.collections
            if collection.get_gid() == f"paired-point:{arm}"
        )
        assert point.get_offsets()[0, 0] == pytest.approx(expected[0])

    expected_means = {
        "doe": (0.09580089411672021, 0.19928715325626434, 50),
        "qlogei": (0.15525130489063754, 0.12321454808918345, 50),
        "qlognei": (0.15321199940788324, 0.12859374980899857, 50),
        "versionb": (0.15464098856453284, 0.10031719217905226, 50),
    }
    mean_rows = {row["arm"]: row for row in bundle.panel_data["B"]["rows"]}
    assert set(mean_rows) == set(expected_means)
    for arm, expected in expected_means.items():
        row = mean_rows[arm]
        assert (row["rule_a"], row["rule_p"], row["n"]) == pytest.approx(expected)
        slope = next(line for line in panel_b.lines if line.get_gid() == f"rule-slope:{arm}")
        assert slope.get_xdata() == pytest.approx((0.0, 1.0))
        assert slope.get_ydata() == pytest.approx(expected[:2])

    expected_decomposition = {
        "doe": (0.059666720920255135, 0.03613417319646509, 0.09580089411672021, 50),
        "qlognei": (0.08340172329615139, 0.06981027611173182, 0.15321199940788324, 50),
        "lhs": (0.07951998084532072, 0.04749959230902029, 0.12701957315434098, 50),
        "sobol": (0.09933441983958823, 0.0730215905552549, 0.1723560103948431, 50),
    }
    decomposition_rows = {row["arm"]: row for row in bundle.panel_data["C"]["rows"]}
    assert set(decomposition_rows) == set(expected_decomposition)
    for arm, expected in expected_decomposition.items():
        row = decomposition_rows[arm]
        assert (
            row["oracle_best"],
            row["identification_gap"],
            row["rule_a"],
            row["n"],
        ) == pytest.approx(expected)
        search = next(patch for patch in panel_c.patches if patch.get_gid() == f"decomposition:{arm}:search")
        identification = next(
            patch for patch in panel_c.patches if patch.get_gid() == f"decomposition:{arm}:identification"
        )
        assert search.get_width() == pytest.approx(expected[0])
        assert identification.get_x() == pytest.approx(expected[0])
        assert identification.get_width() == pytest.approx(expected[1])
        assert search.get_width() + identification.get_width() == pytest.approx(expected[2])

    legend = panel_c.get_legend()
    assert legend is not None
    legend_bounds = legend.get_window_extent(figure.canvas.get_renderer())
    assert not any(
        legend_bounds.overlaps(patch.get_window_extent(figure.canvas.get_renderer()))
        for patch in panel_c.patches
    )

    plt.close(figure)


def test_figure3_rendered_text_states_terminal_rule_semantics():
    bundle = build_figure3(build_terminal_rule_data(Path("results")), get_preset("portable"))
    bundle.figure.canvas.draw()
    rendered_text = {
        " ".join(text.get_text().split())
        for text in bundle.figure.findobj(match=Text)
        if text.get_text()
    }

    assert "Rule A = search loss + identification loss" in rendered_text
    assert "Search loss" in rendered_text
    assert "Identification loss" in rendered_text
    assert not any("blue:" in text or "orange:" in text for text in rendered_text)
    assert "no terminal-rule effect" in rendered_text
    assert "Rule P lowers regret" in rendered_text
    assert "Rule P raises regret" in rendered_text
    panel_a_labels = {
        " ".join(text.get_text().split())
        for text in bundle.figure.axes[1].texts
        if text.get_text()
    }
    assert {"Classical DoE", "qLogEI", "qLogNEI", "SPADE"} <= panel_a_labels
    assert all(text.get_color() == "#243746" for text in bundle.figure.axes[1].texts if text.get_text() in panel_a_labels)
    assert all(linewidth <= 1.0 for collection in bundle.figure.axes[1].collections for linewidth in collection.get_linewidths())
    assert {patch.get_hatch() for patch in bundle.figure.axes[3].patches} >= {"////", "...."}

    plt.close(bundle.figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure3_forest_labels_clear_same_row_intervals_and_markers(preset_name):
    # Regression coverage for the reviewed finding: at PLOS's larger body size the
    # "SPADE" row label encroached on its own confidence interval by a few pixels
    # because the label-to-interval gap was a hard-coded data coordinate rather
    # than a physical (points) quantity. Every row's label is registered against
    # its own interval artist via the shared QA collision machinery, with a
    # non-zero point padding, so any regression in the gap is caught at every
    # preset's actual body size rather than relying on a hand-rolled pixel check.
    bundle = build_figure3(build_terminal_rule_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    panel_a = figure.axes[1]

    collisions = getattr(figure, "_paper_collisions", [])
    registered_by_label = {item.label: item for item in collisions}
    expected_registrations = {
        f"paired-label-clears-interval-{arm}" for arm in ("doe", "qlogei", "qlognei", "versionb")
    }
    assert expected_registrations <= set(registered_by_label)
    for label in expected_registrations:
        registration = registered_by_label[label]
        assert registration.padding_pt > 0.0
        assert isinstance(registration.first, Text)
        assert registration.second in panel_a.collections

    # Raises AssertionError if any registered label/interval pair overlaps once
    # rendered at this preset's actual physical point sizes.
    assert_registered_geometry(figure)

    # The marker sits between the interval's own lo/hi, so a label clearing the
    # interval's left edge also clears the marker; confirm that directly too.
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    for arm in ("doe", "qlogei", "qlognei", "versionb"):
        label = next(text for text in panel_a.texts if text.get_text() == method_style(arm).label)
        marker = next(
            collection
            for collection in panel_a.collections
            if collection.get_gid() == f"paired-point:{arm}"
        )
        label_bounds = label.get_window_extent(renderer)
        marker_bounds = marker.get_window_extent(renderer)
        assert label_bounds.x1 <= marker_bounds.x0

    plt.close(figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure3_text_stays_inside_the_rendered_figure_for_every_preset(preset_name):
    bundle = build_figure3(build_terminal_rule_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    figure_bounds = figure.bbox
    _, panel_a, panel_b, panel_c = figure.axes

    for text in figure.findobj(match=Text):
        if text.get_text():
            text_bounds = text.get_window_extent(renderer)
            assert figure_bounds.contains(*text_bounds.get_points()[0])
            assert figure_bounds.contains(*text_bounds.get_points()[1])

    assert_registered_geometry(figure)
    for texts in (
        panel_a.texts,
        [text for text in panel_b.texts if text.get_text()],
    ):
        extents = [text.get_window_extent(renderer) for text in texts]
        assert not any(
            first.overlaps(second)
            for index, first in enumerate(extents)
            for second in extents[index + 1 :]
        )

    slope_labels = [text.get_window_extent(renderer) for text in panel_b.texts if text.get_text()]
    decomposition_labels = [
        text.get_window_extent(renderer)
        for text in panel_c.get_yticklabels()
        if text.get_visible() and text.get_text()
    ]
    assert not any(
        slope.overlaps(decomposition)
        for slope in slope_labels
        for decomposition in decomposition_labels
    )
    legend = panel_c.get_legend()
    legend_bounds = legend.get_window_extent(renderer)
    assert not legend_bounds.overlaps(panel_c.xaxis.label.get_window_extent(renderer))
    assert not any(
        legend_bounds.overlaps(patch.get_window_extent(renderer))
        for patch in panel_c.patches
    )

    plt.close(figure)


def test_figure4_separates_point_map_and_cost_without_boundary_evidence():
    data = build_spade_evidence_data(Path("results"))
    bundle = build_figure4(data, get_preset("portable"))

    assert bundle.panel_data["A"]["terminal_rule"] == "P"
    assert bundle.panel_data["B"]["sesoi"] == 0.02
    assert bundle.panel_data["C"]["rounds_are_not_point_size"] is True
    assert bundle.panel_data["C"]["constant_wells"] == 48
    assert bundle.panel_data["C"]["encoding"] == "rounds lollipop"
    assert bundle.panel_data["D"]["facets"] == ["d=6", "d=8"]
    assert all(row["evidence_stage"].startswith("descriptive") for row in bundle.panel_data["D"]["rows"])
    assert "spade_random_plate2" not in str(bundle.panel_data)
    assert "KF-3" not in str(bundle.panel_data)
    assert "KF-4" not in str(bundle.panel_data)
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


def test_figure4_rendered_panels_preserve_pareto_contrasts_costs_and_descriptive_status():
    data = build_spade_evidence_data(Path("results"))
    bundle = build_figure4(data, get_preset("portable"))
    figure = bundle.figure
    figure.canvas.draw()
    panel_a, panel_b, panel_c, panel_d = figure.axes

    assert "Symmetric-difference error" in panel_a.get_xlabel()
    assert "Rule-P simple regret" in panel_a.get_ylabel()
    assert "better" in panel_a.get_xlabel()
    direct_labels = {text.get_text() for text in panel_a.texts if text.get_text() != "a"}
    assert direct_labels == {"SPADE", "qLogNEI", "Sobol", "Classical DoE"}
    assert all(text.get_color() == "#243746" for text in panel_a.texts)

    expected_contrasts = {
        "map_spade_minus_sobol": ("Map: SPADE − Sobol", -0.010892, -0.01566185, -0.0059691125),
        "map_spade_minus_qlognei": ("Map: SPADE − qLogNEI", -0.0326545, -0.0372318375, -0.028543325),
        "regret_spade_minus_qlognei": ("Regret: SPADE − qLogNEI", 0.0093747607, 0.0025784577, 0.0161511877),
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

    assert not panel_c.tables
    assert "Feedback rounds" in panel_c.get_xlabel()
    assert {tick.get_text() for tick in panel_c.get_yticklabels()} == {
        "Classical DoE", "Latin hypercube", "Sobol", "qLogEI", "qLogNEI", "SPADE"
    }
    assert "All methods use 48 wells" in {text.get_text() for text in panel_c.texts}
    assert sorted(
        float(collection.get_offsets()[0, 0])
        for collection in panel_c.collections
        if isinstance(collection, PathCollection)
    ) == [1, 1, 2, 3, 10, 10]

    assert "descriptive" in panel_d.get_title(loc="left").lower()
    assert "intervals unavailable" in panel_d.get_title(loc="left").lower()
    assert {text.get_text() for text in panel_d.get_legend().get_texts()} == {
        "Classical DoE", "Latin hypercube", "Sobol", "qLogEI", "qLogNEI", "SPADE"
    }
    assert {float(size) for collection in panel_a.collections for size in collection.get_sizes()} == {32.0}

    facet_axes = panel_d.child_axes
    assert [axis.get_title(loc="left") for axis in facet_axes] == ["d=6", "d=8"]
    hartmann_points = {collection.get_gid(): collection for axis in facet_axes for collection in axis.collections}
    arms = ("doe", "lhs", "sobol", "qlogei", "qlognei", "spade_cf_m0")
    conditions = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
    assert set(hartmann_points) == {f"{condition}:{arm}" for condition in conditions for arm in arms}
    for condition in conditions:
        assert to_hex(hartmann_points[f"{condition}:qlogei"].get_facecolors()[0]) == "#ffffff"
        assert to_hex(hartmann_points[f"{condition}:qlognei"].get_facecolors()[0]) == "#0072b2"
        assert to_hex(hartmann_points[f"{condition}:lhs"].get_facecolors()[0]) == "#ffffff"
        assert to_hex(hartmann_points[f"{condition}:sobol"].get_facecolors()[0]) == "#6b7280"
    assert not any(isinstance(collection, LineCollection) for axis in facet_axes for collection in axis.collections)

    plt.close(figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure4_rendered_text_is_contained_in_each_panel_for_every_preset(preset_name):
    bundle = build_figure4(build_spade_evidence_data(Path("results")), get_preset(preset_name))
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

    plt.close(figure)


def test_figure4_contrast_labels_follow_ids_not_input_order():
    data = deepcopy(build_spade_evidence_data(Path("results")))
    data["contrasts"].reverse()
    bundle = build_figure4(data, get_preset("portable"))
    panel_b = bundle.figure.axes[1]
    observed = {
        int(collection.get_offsets()[0, 1]): float(collection.get_offsets()[0, 0])
        for collection in panel_b.collections
        if isinstance(collection, PathCollection) and len(collection.get_offsets()) == 1
    }

    assert observed == pytest.approx({0: -0.010892, 1: -0.0326545, 2: 0.0093747607})

    plt.close(bundle.figure)


def test_figure4_rejects_contrasts_without_expected_ids_or_common_sesoi():
    missing = deepcopy(build_spade_evidence_data(Path("results")))
    missing["contrasts"] = missing["contrasts"][:2]
    with pytest.raises(ValueError, match="expected contrast IDs"):
        build_figure4(missing, get_preset("portable"))

    mismatched_sesoi = deepcopy(build_spade_evidence_data(Path("results")))
    mismatched_sesoi["contrasts"][0]["sesoi"] = 0.01
    with pytest.raises(ValueError, match="common SESOI"):
        build_figure4(mismatched_sesoi, get_preset("portable"))


def test_figure5_keeps_calibration_containment_and_answer_rate_distinct():
    data = build_certification_data(Path("results"))
    bundle = build_figure5(data, get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C", "D"}
    assert all(row["estimator"] == "crossfit" for row in bundle.panel_data["B"]["rows"])
    assert bundle.panel_data["C"]["zero_means"] == "declined to certify"
    assert bundle.panel_data["D"]["effect"] == "containment minus nominal"
    assert bundle.panel_data["A"]["display"] == "aligned dot strips"
    assert bundle.panel_data["B"]["status_gutter"] is True
    assert bundle.panel_data["D"]["warning_encoding"] == "red triangle plus status text"
    assert "non-empty" in bundle.alt_text
    assert len(bundle.figure.axes) == 4

    plt.close(bundle.figure)


@pytest.mark.parametrize("preset_name", ["portable", "rsc", "nature", "plos"])
def test_figure5_rendered_panels_keep_exact_denominators_and_certification_states_distinct(preset_name):
    data = build_certification_data(Path("results"))
    preset = get_preset(preset_name)
    bundle = build_figure5(data, preset)
    figure = bundle.figure
    figure.canvas.draw()
    panel_a, panel_b, panel_c, panel_d = figure.axes

    assert "retrospective hill" in panel_a.get_title(loc="left").lower()
    assert "descriptive" in panel_a.get_title(loc="left").lower()
    assert [axis.get_title(loc="left") for axis in panel_a.child_axes] == [
        "Calibration error ↓", "Refinement ↑"
    ]
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
            assert all(linewidth <= 1.0 for linewidth in interval.get_linewidths())
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
def test_figure5_declined_certification_labels_stay_inside_their_containment_panels(preset_name):
    bundle = build_figure5(build_certification_data(Path("results")), get_preset(preset_name))
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
def test_figure5_rendered_text_stays_inside_the_figure_for_every_preset(preset_name):
    bundle = build_figure5(build_certification_data(Path("results")), get_preset(preset_name))
    figure = bundle.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()

    for text in figure.findobj(match=Text):
        if text.get_text():
            text_bounds = text.get_window_extent(renderer)
            assert figure.bbox.contains(*text_bounds.get_points()[0])
            assert figure.bbox.contains(*text_bounds.get_points()[1])

    plt.close(figure)
