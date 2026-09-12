from __future__ import annotations

import importlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from pathlib import Path

from boec.paper_figures.style import get_preset


def test_publication_font_resolves_to_arial():
    qa = importlib.import_module("boec.paper_figures.qa")

    path = qa.resolved_publication_font()

    assert path.name == "Arial.ttf"


def test_content_box_contains_text_with_two_point_padding():
    layout = importlib.import_module("boec.paper_figures.layout")
    qa = importlib.import_module("boec.paper_figures.qa")
    fig, ax = plt.subplots(figsize=(4, 2))

    editorial_box = layout.content_box(
        ax,
        (0.5, 0.5),
        "Same sampled\ncampaign",
        get_preset("plos"),
    )
    qa.register_artist(
        fig,
        "same-sampled-campaign",
        editorial_box.text,
        editorial_box.patch,
        padding_pt=2.0,
    )

    qa.assert_registered_geometry(fig)
    plt.close(fig)


def test_normal_text_colour_meets_wcag_contrast_contract():
    qa = importlib.import_module("boec.paper_figures.qa")

    assert qa.contrast_ratio("#243746", "#FFFFFF") >= 4.5
    assert qa.contrast_ratio("#009E73", "#FFFFFF") < 4.5


@pytest.mark.parametrize("obstacle", ["text", "point", "line", "edge"])
def test_label_audit_rejects_overlaps_and_clipping(obstacle):
    from boec.paper_figures.qa import assert_label_clearance

    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.text(0.5, 0.5, "Label", ha="center", va="center")
    if obstacle == "text":
        ax.text(0.5, 0.5, "Other")
    elif obstacle == "point":
        ax.scatter([0.5], [0.5], s=36)
    elif obstacle == "line":
        ax.plot([0.2, 0.8], [0.5, 0.5])
    else:
        fig.text(0.999, 0.5, "Outside figure")
    with pytest.raises(AssertionError):
        assert_label_clearance(fig)
    plt.close(fig)


@pytest.mark.parametrize("figure_id", [1, 2, 3, 4])
def test_plos_figures_have_clear_labels(figure_id):
    from boec.paper_figures import evidence
    from boec.paper_figures.qa import assert_label_clearance

    module = importlib.import_module(f"boec.paper_figures.figure{figure_id}")
    builder = getattr(module, f"build_figure{figure_id}")
    preset = get_preset("plos")
    data = None if figure_id == 1 else getattr(evidence, f"build_figure{figure_id}_data")(Path("results"))
    bundle = builder(preset) if data is None else builder(data, preset)
    try:
        assert_label_clearance(bundle.figure)
    finally:
        plt.close(bundle.figure)


def test_repeated_certificate_cells_are_descriptive_not_binomial_trials():
    from boec.paper_figures.evidence import build_figure4_data
    from boec.paper_figures.figure4 import build_figure4

    bundle = build_figure4(build_figure4_data(Path("results")), get_preset("plos"))
    try:
        assert bundle.panel_data["D"]["interval"] == "not computed; repeated cells within campaigns"
        assert not any((artist.get_gid() or "").startswith("conditional-interval:")
                       for artist in bundle.figure.findobj())
        assert "α=0.80" in bundle.figure.axes[3].get_title(loc="left")
    finally:
        plt.close(bundle.figure)
