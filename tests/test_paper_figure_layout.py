from __future__ import annotations

import importlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
