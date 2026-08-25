"""Study-architecture schematic for the paper's Figure 1."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyArrowPatch

from .core import FigureBundle
from .landscape_glyphs import LANDSCAPE_FAMILIES, landscape_slice
from .layout import EditorialText, content_box, editorial_figure
from .qa import register_artist, register_collision
from .style import VenuePreset, panel_label


_INK = "#243746"
_LANDSCAPE_CMAP = LinearSegmentedColormap.from_list(
    "landscape_luminance",
    ("#F7FAFC", "#C8DCE8", "#5B8FA8", "#173F5F"),
)
_LANDSCAPE_LABELS = {
    "hill": "Hill",
    "ackley": "Ackley",
    "hartmann6": "Hartmann6",
    "levy": "Levy",
    "rosenbrock": "Rosenbrock",
}


def _prepare_panel(axis: Axes, label: str, title: str, deck: str, preset: VenuePreset) -> None:
    axis.set_axis_off()
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    panel_label(axis, label, preset)
    axis.text(
        0.01,
        0.98,
        title,
        transform=axis.transAxes,
        color=_INK,
        fontsize=preset.panel_pt,
        fontweight="bold",
        va="top",
    )
    axis.text(
        0.01,
        0.79,
        deck,
        transform=axis.transAxes,
        color=_INK,
        fontsize=preset.body_pt,
        va="top",
    )


def _card(
    axis: Axes,
    xy: tuple[float, float],
    text: str,
    facecolour: str,
    preset: VenuePreset,
    label: str,
    *,
    dashed: bool = False,
) -> EditorialText:
    card = content_box(
        axis,
        xy,
        text,
        preset,
        facecolor=facecolour,
        dashed=dashed,
    )
    register_artist(axis.figure, label, card.text, card.patch, padding_pt=2.0)
    return card


def _arrow(
    axis: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    connectionstyle: str = "arc3",
) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=axis.transAxes,
            arrowstyle="-|>",
            mutation_scale=7,
            linewidth=0.8,
            color=_INK,
            connectionstyle=connectionstyle,
            shrinkA=4,
            shrinkB=4,
        )
    )


def _draw_landscapes(axis: Axes, preset: VenuePreset) -> None:
    normalizer = Normalize(vmin=0.0, vmax=1.0)
    levels = tuple(index / 8 for index in range(9))
    for index, family in enumerate(LANDSCAPE_FAMILIES):
        left = 0.01 + index * 0.198
        glyph_axis = axis.inset_axes((left, 0.02, 0.176, 0.48))
        glyph = landscape_slice(family)
        glyph_axis.contourf(
            glyph.x,
            glyph.y,
            glyph.z,
            levels=levels,
            cmap=_LANDSCAPE_CMAP,
            norm=normalizer,
            antialiased=True,
        )
        glyph_axis.contour(
            glyph.x,
            glyph.y,
            glyph.z,
            levels=levels[1:-1],
            colors="#243746",
            linewidths=0.35,
            alpha=0.62,
        )
        glyph_axis.set_title(
            _LANDSCAPE_LABELS[family],
            color=_INK,
            fontsize=preset.body_pt,
            pad=2.0,
        )
        glyph_axis.set_xticks(())
        glyph_axis.set_yticks(())
        for spine in glyph_axis.spines.values():
            spine.set_color("#8EA2B1")
            spine.set_linewidth(0.5)


def _draw_methods(axis: Axes, preset: VenuePreset) -> None:
    cards = (
        ((0.12, 0.23), "Classical\nexperimental design\nONE-SHOT", "#FDE9DD", "classical-design"),
        ((0.38, 0.23), "Space-filling\ndesign\nONE-SHOT", "#F3F4F6", "space-filling-design"),
        ((0.66, 0.23), "Sequential Bayesian\noptimization\nSEQUENTIAL", "#E8F1F8", "bayesian-optimization"),
        ((0.90, 0.23), "SPADE\nmap-aware design\nSEQUENTIAL", "#DDF3E8", "spade-design"),
    )
    for xy, text, facecolour, label in cards:
        _card(axis, xy, text, facecolour, preset, label)


def _draw_campaign_and_outputs(axis: Axes, preset: VenuePreset) -> None:
    _card(axis, (0.08, 0.45), "Design\nstrategy", "#F3F4F6", preset, "campaign-design")
    _card(axis, (0.27, 0.45), "48 wells\ntotal", "#E8F1F8", preset, "campaign-wells")
    _card(axis, (0.47, 0.45), "Noisy\nobservations", "#FDE9DD", preset, "campaign-observations")
    _arrow(axis, (0.13, 0.45), (0.21, 0.45))
    _arrow(axis, (0.33, 0.45), (0.40, 0.45))
    _arrow(axis, (0.43, 0.27), (0.12, 0.27), connectionstyle="arc3,rad=-0.38")
    axis.text(
        0.27,
        0.00,
        "sequential update within the fixed campaign",
        transform=axis.transAxes,
        color=_INK,
        fontsize=preset.body_pt,
        ha="center",
        va="bottom",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0},
    )

    output_cards = (
        ((0.70, 0.60), "Point\ndecision", "#E8F1F8", "point-output"),
        ((0.90, 0.60), "Region\nmap", "#DDF3E8", "region-map-output"),
        ((0.70, 0.17), "Conservative\ncertificate", "#DDF3E8", "certificate-output"),
        ((0.90, 0.17), "Experimental\ncost", "#F3F4F6", "cost-output"),
    )
    rendered_cards = []
    for index, (xy, text, facecolour, label) in enumerate(output_cards):
        rendered_cards.append(_card(axis, xy, text, facecolour, preset, label, dashed=True))
        route = "arc3"
        if index == 1:
            route = "angle3,angleA=0,angleB=90"
        elif index == 3:
            route = "angle3,angleA=0,angleB=-90"
        _arrow(axis, (0.54, 0.41), (xy[0] - 0.07, xy[1]), connectionstyle=route)
    for first, second, label in (
        (0, 1, "output-cards-upper-row"),
        (2, 3, "output-cards-lower-row"),
        (0, 2, "output-cards-left-column"),
        (1, 3, "output-cards-right-column"),
    ):
        register_collision(
            axis.figure,
            label,
            rendered_cards[first].patch,
            rendered_cards[second].patch,
            padding_pt=2.0,
        )


def build_figure1(preset: VenuePreset) -> FigureBundle:
    """Build the response-landscape-to-decision study architecture."""
    headline = "Study architecture separates landscapes, design strategies and decision outputs"
    deck = "Five controlled response families · common noisy campaigns · point, map and certification objectives"
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 188 if preset.name == "plos" else 176
        figure, content = editorial_figure(
            preset,
            height_mm,
            headline,
            deck,
            rows=3,
            cols=1,
        )
        header = figure.axes[0]
        header.texts[0].set_fontsize(min(preset.panel_pt, 9.5))
        header.texts[1].set_fontsize(min(preset.body_pt, 8.0))
        content.set_height_ratios((1.22, 0.90, 1.14))
        axis_a = figure.add_subplot(content[0, 0])
        axis_b = figure.add_subplot(content[1, 0])
        axis_c = figure.add_subplot(content[2, 0])
        _prepare_panel(
            axis_a,
            "a",
            "Response landscapes",
            "First two coordinates shown · remaining coordinates held at each optimum",
            preset,
        )
        _prepare_panel(
            axis_b,
            "b",
            "Design strategies",
            "Two one-shot families · two sequential families · one common well budget",
            preset,
        )
        _prepare_panel(
            axis_c,
            "c",
            "Decisions from one campaign",
            "One campaign supports point, map, certification and cost objectives",
            preset,
        )
        _draw_landscapes(axis_a, preset)
        _draw_methods(axis_b, preset)
        _draw_campaign_and_outputs(axis_c, preset)

    panel_data = {
        "A": {
            "families": list(LANDSCAPE_FAMILIES),
            "displayed_coordinates": [0, 1],
            "other_coordinates": "held at oracle optimum",
            "normalization": "independent within-family visual fingerprint",
        },
        "B": {
            "method_families": [
                "classical experimental design",
                "space-filling design",
                "sequential Bayesian optimization",
                "SPADE",
            ],
            "status": {
                "classical experimental design": "one-shot",
                "space-filling design": "one-shot",
                "sequential Bayesian optimization": "sequential",
                "SPADE": "sequential",
            },
        },
        "C": {
            "campaign_wells": 48,
            "observation_loop": ["design strategy", "campaign", "noisy observations"],
            "outputs": ["point", "region map", "certificate", "experimental cost"],
        },
    }
    alt_text = (
        "Study architecture with three bands. Five response-landscape contour glyphs feed four design-strategy "
        "families. One fixed 48-well noisy campaign supports point decisions, region maps, conservative "
        "certificates and experimental-cost summaries. The schematic contains no performance result."
    )
    caption = (
        "Figure 1 | Study architecture separates response landscapes, design strategies and decision outputs. "
        "(a) Deterministic two-coordinate slices of Hill, Ackley, Hartmann6, Levy and Rosenbrock responses; "
        "all remaining coordinates are fixed at each oracle optimum. Each glyph is independently normalized "
        "to a common luminance scale as a visual fingerprint, not a cross-family magnitude comparison. "
        "(b) Classical experimental design and space-filling design are one-shot families, whereas sequential "
        "Bayesian optimization and SPADE update within the campaign. (c) The same 48-well campaign yields "
        "separate point, region-map, conservative-certificate and experimental-cost outputs. No performance "
        "result is displayed."
    )
    long_description = (
        "Panel a shows five vector contour glyphs generated from controlled response families. The displayed "
        "plane varies the first two coordinates while every other coordinate is held at that response's known "
        "optimum; independent normalization communicates geometry only. Panel b groups the design strategies "
        "by experimental cadence: classical experimental design and space-filling design are one-shot, while "
        "sequential Bayesian optimization and SPADE can update from observations. Panel c follows a single "
        "fixed-budget campaign from strategy through 48 wells and noisy observations, then branches to four "
        "distinct objectives: a point decision, a region map, a conservative certificate and experimental cost."
    )
    return FigureBundle(
        "fig1",
        figure,
        panel_data,
        alt_text,
        caption,
        long_description,
        headline=headline,
        deck=deck,
        layout_rows=(("A",), ("B",), ("C",)),
    )
