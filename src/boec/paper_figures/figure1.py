"""Benchmark-definition schematic for the paper's Figure 1."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch

from .core import FigureBundle
from .layout import content_box
from .qa import register_artist
from .style import VenuePreset, panel_label


_INK = "#243746"
_LINE = "#CBD2D9"
_CAMPAIGN_FILL = "#E8F1F8"
_ASSAY_FILL = "#FDE9DD"
_REGION_FILL = "#DDF3E8"


def _node(
    ax: Axes,
    xy: tuple[float, float],
    text: str,
    facecolour: str,
    preset: VenuePreset,
    label: str,
    *,
    dashed: bool = False,
    fontweight: str = "normal",
):
    """Add and register a renderer-sized semantic module."""
    node = content_box(
        ax,
        xy,
        text,
        preset,
        facecolor=facecolour,
        dashed=dashed,
        fontweight=fontweight,
    )
    register_artist(ax.figure, label, node.text, node.patch, padding_pt=2.0)
    return node


def _arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    """Add a restrained primary-flow connector."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=7,
            linewidth=0.8,
            color=_INK,
            shrinkA=4,
            shrinkB=4,
        )
    )


def _prepare_panel(ax: Axes, label: str, preset: VenuePreset) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    panel_label(ax, label, preset=preset)


def build_figure1(preset: VenuePreset) -> FigureBundle:
    """Build the benchmark schematic using content-aware physical typography."""
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure = plt.figure(figsize=preset.figsize(148), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, height_ratios=(0.88, 1.32), wspace=0.12)
        ax_a = figure.add_subplot(grid[0, 0])
        ax_b = figure.add_subplot(grid[0, 1])
        ax_c = figure.add_subplot(grid[1, :])
        for axis, label in zip((ax_a, ax_b, ax_c), "abc", strict=True):
            _prepare_panel(axis, label, preset)

        ax_a.text(
            0.02,
            0.86,
            "ONE CAMPAIGN",
            transform=ax_a.transAxes,
            fontsize=preset.body_pt,
            fontweight="bold",
            color=_INK,
            va="top",
        )
        stage_specs = (
            ((0.10, 0.49), "Formulation\nvariables", _CAMPAIGN_FILL, "campaign-formulation"),
            ((0.37, 0.49), "48-well\ncampaign", _CAMPAIGN_FILL, "campaign-wells"),
            ((0.64, 0.49), "Noisy assay\nresponses", _ASSAY_FILL, "campaign-assay"),
            ((0.90, 0.49), "Response\nmodel", _REGION_FILL, "campaign-model"),
        )
        for xy, text, facecolour, label in stage_specs:
            _node(ax_a, xy, text, facecolour, preset, label)
        arrow_specs = (
            ((0.20, 0.49), (0.27, 0.49)),
            ((0.47, 0.49), (0.54, 0.49)),
            ((0.74, 0.49), (0.81, 0.49)),
        )
        for start, end in arrow_specs:
            _arrow(ax_a, start, end)

        _node(
            ax_b,
            (0.15, 0.50),
            "Same sampled\ncampaign",
            _CAMPAIGN_FILL,
            preset,
            "same-sampled-campaign",
            fontweight="bold",
        )
        _node(
            ax_b,
            (0.69, 0.70),
            "POINT DECISION\nTested-best · noisy selection\nModel recommendation · confirmation",
            _CAMPAIGN_FILL,
            preset,
            "point-decision-lane",
            dashed=True,
        )
        _node(
            ax_b,
            (0.69, 0.27),
            "REGION DECISION\nAcceptable-region map\nConservative certificate",
            _REGION_FILL,
            preset,
            "region-decision-lane",
            dashed=True,
        )
        _arrow(ax_b, (0.28, 0.52), (0.47, 0.69))
        _arrow(ax_b, (0.28, 0.48), (0.47, 0.29))

        columns = ("Deliverable", "Reported object", "Observable?", "Score", "Extra wells", "Rounds")
        display_columns = ("Deliverable", "Reported\nobject", "Observable?", "Score", "Extra\nwells", "Rounds")
        rows = (
            ("Tested-best", "latent best visited", "no", "simple regret", "0", "campaign"),
            ("Measured selection", "one tested well", "yes", "Rule-A regret", "0", "campaign"),
            ("Model recommendation", "predicted optimum", "yes", "Rule-P regret", "0", "campaign"),
            ("Confirmation protocol", "confirmed tested well", "yes", "confirmed regret", "protocol", "campaign + confirmation"),
            ("Acceptable-region map", "set of acceptable inputs", "yes", "symmetric difference", "0", "campaign"),
            ("Certificate", "conservative subset", "yes", "joint containment", "0", "campaign"),
        )
        display_rows = (
            ("Tested-best", "latent best\nvisited", "no", "simple\nregret", "0", "campaign"),
            ("Measured\nselection", "one tested\nwell", "yes", "Rule-A\nregret", "0", "campaign"),
            ("Model\nrecommendation", "predicted\noptimum", "yes", "Rule-P\nregret", "0", "campaign"),
            ("Confirmation\nprotocol", "confirmed\ntested well", "yes", "confirmed\nregret", "protocol", "campaign +\nconfirmation"),
            ("Acceptable-region\nmap", "acceptable\ninput set", "yes", "symmetric\ndifference", "0", "campaign"),
            ("Certificate", "conservative\nsubset", "yes", "joint\ncontainment", "0", "campaign"),
        )
        ax_c.text(
            0.01,
            0.96,
            "ESTIMAND LEDGER   •   point decisions (blue)   •   region decisions (green)",
            transform=ax_c.transAxes,
            fontsize=preset.body_pt,
            fontweight="bold",
            color=_INK,
            va="top",
        )
        table = ax_c.table(
            cellText=display_rows,
            colLabels=display_columns,
            cellLoc="left",
            colLoc="left",
            bbox=(0.01, 0.02, 0.98, 0.84),
            colWidths=(0.19, 0.18, 0.15, 0.16, 0.13, 0.19),
        )
        table.auto_set_font_size(False)
        table.set_fontsize(preset.body_pt)
        for (row, column), cell in table.get_celld().items():
            cell.set_edgecolor(_LINE)
            cell.set_linewidth(0.5)
            cell.PAD = 0.06
            if row == 0:
                cell.set_facecolor("#F3F6F8")
                cell.get_text().set_fontweight("bold")
            elif column == 0 and row <= 4:
                cell.set_facecolor(_CAMPAIGN_FILL)
            elif column == 0:
                cell.set_facecolor(_REGION_FILL)
            else:
                cell.set_facecolor("white")
            if row == 5:
                cell.set_linewidth(0.9)
            cell.get_text().set_color(_INK)

    panel_data = {
        "A": {"stages": ["formulation", "wells", "assay", "model"]},
        "B": {
            "branches": {"point decision": 4, "region decision": 2},
            "point deliverables": (
                "tested-best",
                "noisy selection",
                "model recommendation",
                "confirmation",
            ),
            "region deliverables": ("acceptable-region map", "conservative certificate"),
        },
        "C": {"columns": columns, "rows": rows},
    }
    alt_text = (
        "Benchmark definition. A campaign flows from formulation variables through wells, assay, and model; "
        "the same data then fork into point or region deliverables, each with a distinct estimand. "
        "This schematic contains no performance result."
    )
    caption = (
        "Figure 1 | Benchmark decisions and estimands. (a) Each method operates within one 48-well "
        "campaign. (b) The same sampled campaign supports point and region decisions. (c) The estimand "
        "ledger distinguishes the reported object, observability, score, additional wells and experimental "
        "rounds for every deliverable. This figure defines the benchmark and contains no performance result."
    )
    long_description = (
        "Panel a presents a left-to-right campaign ribbon from formulation variables to a 48-well campaign, "
        "noisy assay responses and a fitted response model. Panel b shows the same sampled campaign branching "
        "to four point-decision deliverables and two region-decision deliverables. Panel c lists the distinct "
        "reported object and scoring rule for each point and region output, preventing model recommendation, "
        "measured selection, acceptable-region mapping and conservative certification from being conflated."
    )
    return FigureBundle("fig1", figure, panel_data, alt_text, caption, long_description)
