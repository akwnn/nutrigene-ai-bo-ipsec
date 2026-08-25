"""Benchmark-definition schematic for the paper's Figure 1."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from .core import FigureBundle
from .style import VenuePreset, panel_label


_INK = "#243746"
_LINE = "#CBD2D9"
_CAMPAIGN_FILL = "#E8F1F8"
_ASSAY_FILL = "#FDE9DD"
_REGION_FILL = "#DDF3E8"


def _node(
    ax: Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    facecolour: str,
    preset: VenuePreset,
    *,
    dashed: bool = False,
) -> FancyBboxPatch:
    """Add a consistently sized semantic module to a schematic panel."""
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=facecolour,
        edgecolor=_INK,
        linewidth=0.8,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=preset.body_pt,
        color=_INK,
    )
    return patch


def _arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    """Add a primary-flow connector without introducing a new visual encoding."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=0.8,
            color=_INK,
        )
    )


def _prepare_panel(ax: Axes, label: str, preset: VenuePreset) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    panel_label(ax, label, preset=preset)


def build_figure1(preset: VenuePreset) -> FigureBundle:
    """Build the non-result benchmark schematic using ``preset`` dimensions."""
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure = plt.figure(figsize=preset.figsize(142), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, height_ratios=(0.9, 1.25))
        ax_a = figure.add_subplot(grid[0, 0])
        ax_b = figure.add_subplot(grid[0, 1])
        ax_c = figure.add_subplot(grid[1, :])
        for axis, label in zip((ax_a, ax_b, ax_c), "abc", strict=True):
            _prepare_panel(axis, label, preset)

        stages = (
            (0.02, "Formulation\nvariables", _CAMPAIGN_FILL),
            (0.27, "48-well\ncampaign", _CAMPAIGN_FILL),
            (0.52, "Noisy assay\nresponses", _ASSAY_FILL),
            (0.77, "Response\nmodel", _REGION_FILL),
        )
        for x, text, facecolour in stages:
            _node(ax_a, x, 0.40, 0.19, 0.22, text, facecolour, preset)
        for x in (0.21, 0.46, 0.71):
            _arrow(ax_a, (x, 0.51), (x + 0.05, 0.51))
        ax_a.text(
            0.02,
            0.84,
            "One campaign",
            fontsize=preset.body_pt,
            fontweight="bold",
            color=_INK,
        )

        _node(ax_b, 0.03, 0.40, 0.20, 0.22, "Same sampled\ncampaign", _CAMPAIGN_FILL, preset)
        _node(
            ax_b,
            0.38,
            0.60,
            0.56,
            0.25,
            "Point decision\ntested-best | noisy selection\nmodel recommendation | confirmation",
            _CAMPAIGN_FILL,
            preset,
            dashed=True,
        )
        _node(
            ax_b,
            0.38,
            0.15,
            0.56,
            0.25,
            "Region decision\nacceptable-region map\nconservative certificate",
            _REGION_FILL,
            preset,
            dashed=True,
        )
        _arrow(ax_b, (0.23, 0.51), (0.38, 0.72))
        _arrow(ax_b, (0.23, 0.51), (0.38, 0.27))

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
            ("Acceptable-region\nmap", "set of\nacceptable inputs", "yes", "symmetric\ndifference", "0", "campaign"),
            ("Certificate", "conservative\nsubset", "yes", "joint\ncontainment", "0", "campaign"),
        )
        table = ax_c.table(
            cellText=display_rows,
            colLabels=display_columns,
            cellLoc="left",
            colLoc="left",
            bbox=(0.01, 0.04, 0.98, 0.86),
        )
        table.auto_set_font_size(False)
        table.set_fontsize(preset.body_pt)
        for (row, _), cell in table.get_celld().items():
            cell.set_edgecolor(_LINE)
            cell.set_linewidth(0.5)
            cell.set_facecolor("#F3F6F8" if row == 0 else "white")
            cell.get_text().set_color(_INK)
            if row == 0:
                cell.get_text().set_fontweight("bold")

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
    return FigureBundle("fig1", figure, panel_data, alt_text)
