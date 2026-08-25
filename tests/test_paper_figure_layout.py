from __future__ import annotations

import importlib
from importlib.resources import files

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from boec.paper_figures.core import sha256_file
from boec.paper_figures.fonts import font_manifest, register_publication_fonts
from boec.paper_figures.layout import editorial_figure, panel_heading
from boec.paper_figures.style import get_preset


def test_publication_fonts_are_packaged_and_hash_verified():
    assets = register_publication_fonts()
    assert assets.text_regular.name == "CharisSIL-Regular.ttf"
    assert assets.text_bold.name == "CharisSIL-Bold.ttf"
    assert assets.math_regular.name == "STIXMath-Regular.otf"
    manifest = font_manifest()
    assert manifest["charis"]["version"] == "6.200"
    assert manifest["stix"]["version"] == "1.1.1"
    for record in manifest["files"]:
        assert sha256_file(assets.text_regular.parent / record["name"]) == record["sha256"]


def test_paper_style_uses_only_packaged_font_faces():
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with matplotlib.rc_context(fname=style_path):
        assert matplotlib.rcParams["font.family"] == ["Charis SIL"]
        assert matplotlib.rcParams["mathtext.rm"] == "STIX Math"
        assert matplotlib.rcParams["mathtext.it"] == "STIX Math"
        assert matplotlib.rcParams["mathtext.bf"] == "STIX Math"


def test_editorial_heading_has_reserved_non_overlapping_geometry():
    qa = importlib.import_module("boec.paper_figures.qa")
    fig, content = editorial_figure(
        get_preset("plos"),
        150,
        "The terminal rule changes method rankings",
        "Hill · d=6 · σ=0.25 · n=50 paired campaigns",
        rows=1,
        cols=1,
    )
    ax = fig.add_subplot(content[0, 0])
    panel_heading(
        ax,
        "a",
        "Paired terminal-rule effect",
        "95% paired bootstrap interval",
        get_preset("plos"),
    )
    qa.assert_registered_geometry(fig)
    plt.close(fig)


def test_editorial_axis_text_stays_inside_short_fixed_canvas():
    qa = importlib.import_module("boec.paper_figures.qa")
    preset = get_preset("plos")
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with matplotlib.rc_context(fname=style_path):
        fig, content = editorial_figure(
            preset,
            90,
            "Publication typography smoke test",
            "Packaged fonts only",
            rows=1,
            cols=1,
        )
        ax = fig.add_subplot(content[0, 0])
        panel_heading(ax, "a", "Text and mathematics", "Embedded PDF text", preset)
        ax.set_xlabel(r"$x^2 + \sigma$")
        ax.set_ylabel("Response")

        qa.assert_all_text_inside_figure(fig)
        plt.close(fig)


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
