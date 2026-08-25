"""Decision-and-estimand definition for the paper's Figure 2."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.path import Path
from matplotlib.patches import FancyArrowPatch

from .core import FigureBundle
from .layout import EditorialText, content_box, editorial_figure, panel_heading
from .qa import register_artist, register_collision
from .style import VenuePreset


_INK = "#243746"
_LINE = "#CBD2D9"
_CAMPAIGN_FILL = "#E8F1F8"
_ASSAY_FILL = "#FDE9DD"
_REGION_FILL = "#DDF3E8"
_NEUTRAL_FILL = "#F3F4F6"


def _node(
    axis: Axes,
    xy: tuple[float, float],
    text: str,
    facecolour: str,
    preset: VenuePreset,
    label: str,
    *,
    dashed: bool = False,
    fontweight: str = "normal",
    compact: bool = False,
    box_alignment: tuple[float, float] = (0.5, 0.5),
) -> EditorialText:
    """Add and register a renderer-sized semantic module."""
    node = content_box(
        axis,
        xy,
        text,
        preset,
        facecolor=facecolour,
        dashed=dashed,
        fontweight=fontweight,
        box_alignment=box_alignment,
    )
    if compact:
        node.patch.set_boxstyle("round,pad=0.21,rounding_size=0.08")
    if xy[0] < 0:
        node.annotation.set_clip_on(False)
    register_artist(axis.figure, label, node.text, node.patch, padding_pt=2.0)
    return node


def _arrow(
    axis: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    source: EditorialText,
    target: EditorialText,
    *,
    connectionstyle: str = "arc3",
) -> FancyArrowPatch:
    """Connect two content-sized cards and clip the route at their frames."""
    connector = FancyArrowPatch(
        start,
        end,
        transform=axis.transAxes,
        patchA=source.patch,
        patchB=target.patch,
        arrowstyle="-|>",
        mutation_scale=7,
        linewidth=0.8,
        color=_INK,
        connectionstyle=connectionstyle,
        shrinkA=2,
        shrinkB=2,
        zorder=4,
    )
    axis.add_patch(connector)
    return connector


def _prepare_panel(
    axis: Axes,
    label: str,
    title: str,
    deck: str,
    preset: VenuePreset,
) -> None:
    axis.set_axis_off()
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    panel_heading(axis, label, title, deck, preset)
    if not deck:
        position = axis.get_position()
        figure_height_pt = axis.figure.get_figheight() * 72.0
        reclaimed = (preset.body_pt * 1.6 + 3.0) / figure_height_pt
        axis.set_position((position.x0, position.y0, position.width, position.height + reclaimed))


def _routed_arrow(
    axis: Axes,
    source: EditorialText,
    target: EditorialText,
    *,
    corridor_y: float,
) -> FancyArrowPatch:
    """Route a fork connector through the measured gap between decision rows."""
    axis.figure.canvas.draw()
    renderer = axis.figure.canvas.get_renderer()
    inverse = axis.transAxes.inverted()
    source_bounds = source.patch.get_window_extent(renderer)
    target_bounds = target.patch.get_window_extent(renderer)
    start = inverse.transform((source_bounds.x1, (source_bounds.y0 + source_bounds.y1) / 2))
    end = inverse.transform(
        (
            target_bounds.x0 - renderer.points_to_pixels(3.0),
            (target_bounds.y0 + target_bounds.y1) / 2,
        )
    )
    route = Path(
        (start, (start[0] + 0.015, corridor_y), (end[0] - 0.02, corridor_y), end),
        (Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO),
    )
    connector = FancyArrowPatch(
        path=route,
        transform=axis.transAxes,
        arrowstyle="-|>",
        mutation_scale=7,
        linewidth=0.8,
        color=_INK,
        zorder=4,
    )
    axis.add_patch(connector)
    return connector


def _boundary_arrow(axis: Axes, source: EditorialText, target: EditorialText) -> FancyArrowPatch:
    """Draw a straight connector from one rendered card boundary to another."""
    axis.figure.canvas.draw()
    renderer = axis.figure.canvas.get_renderer()
    inverse = axis.transAxes.inverted()
    source_bounds = source.patch.get_window_extent(renderer)
    target_bounds = target.patch.get_window_extent(renderer)
    start = inverse.transform((source_bounds.x1, (source_bounds.y0 + source_bounds.y1) / 2))
    end = inverse.transform(
        (
            target_bounds.x0 - renderer.points_to_pixels(3.0),
            (target_bounds.y0 + target_bounds.y1) / 2,
        )
    )
    connector = FancyArrowPatch(
        start,
        end,
        transform=axis.transAxes,
        arrowstyle="-|>",
        mutation_scale=7,
        linewidth=0.8,
        color=_INK,
        shrinkA=0,
        shrinkB=0,
        zorder=4,
    )
    axis.add_patch(connector)
    return connector


def _campaign_return_arrow(
    axis: Axes,
    source: EditorialText,
    target: EditorialText,
) -> FancyArrowPatch:
    """Close the experimental loop below the forward observation path."""
    axis.figure.canvas.draw()
    renderer = axis.figure.canvas.get_renderer()
    inverse = axis.transAxes.inverted()
    source_bounds = source.patch.get_window_extent(renderer)
    target_bounds = target.patch.get_window_extent(renderer)
    start = inverse.transform(((source_bounds.x0 + source_bounds.x1) / 2, source_bounds.y0))
    end = inverse.transform(
        (
            (target_bounds.x0 + target_bounds.x1) / 2,
            target_bounds.y0 - renderer.points_to_pixels(3.0),
        )
    )
    corridor_y = 0.08
    route = Path(
        (start, (start[0], corridor_y), (end[0], corridor_y), end),
        (Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO),
    )
    connector = FancyArrowPatch(
        path=route,
        transform=axis.transAxes,
        arrowstyle="-|>",
        mutation_scale=7,
        linewidth=0.8,
        color=_INK,
        zorder=4,
    )
    connector.set_gid("campaign-return-loop")
    axis.add_patch(connector)
    return connector


def _draw_campaign_loop(axis: Axes, preset: VenuePreset) -> None:
    specs = (
        ((0.11, 0.49), "Formulation\nvariables", _NEUTRAL_FILL, "campaign-formulation"),
        ((0.38, 0.49), "48-well\ncampaign", _CAMPAIGN_FILL, "campaign-wells"),
        ((0.65, 0.49), "Noisy assay\nresponses", _ASSAY_FILL, "campaign-assay"),
        ((0.90, 0.49), "Response\nmodel", _REGION_FILL, "campaign-model"),
    )
    nodes = [
        _node(axis, xy, text, facecolour, preset, label, compact=True)
        for xy, text, facecolour, label in specs
    ]
    for index in range(len(nodes) - 1):
        _arrow(axis, specs[index][0], specs[index + 1][0], nodes[index], nodes[index + 1])
        register_collision(
            axis.figure,
            f"campaign-node-gap-{index}",
            nodes[index].patch,
            nodes[index + 1].patch,
            padding_pt=0.0,
        )
    _campaign_return_arrow(axis, nodes[-1], nodes[0])


def _draw_decision_lanes(axis: Axes, preset: VenuePreset) -> None:
    axis.text(
        0.37,
        0.99,
        "Point decisions",
        transform=axis.transAxes,
        color=_INK,
        fontsize=preset.body_pt,
        fontweight="bold",
        ha="center",
        va="top",
    )
    axis.text(
        0.81,
        0.99,
        "Region decisions",
        transform=axis.transAxes,
        color=_INK,
        fontsize=preset.body_pt,
        fontweight="bold",
        ha="center",
        va="top",
    )
    source_xy = (-0.08, 0.50)
    source = _node(
        axis,
        source_xy,
        "Same\ncampaign",
        _CAMPAIGN_FILL,
        preset,
        "same-sampled-campaign",
        fontweight="bold",
        compact=True,
        box_alignment=(0.0, 0.5),
    )
    point_specs = (
        ((0.37, 0.75), "Tested-best", "point-tested-best"),
        ((0.37, 0.53), "Measured selection", "point-measured-selection"),
        ((0.37, 0.31), "Model recommendation", "point-model-recommendation"),
        ((0.37, 0.09), "Confirmation", "point-confirmation"),
    )
    region_specs = (
        ((0.81, 0.67), "Acceptable-region\nmap", "region-map"),
        ((0.81, 0.27), "Conservative\ncertificate", "region-certificate"),
    )
    point_nodes = [
        _node(axis, xy, text, _CAMPAIGN_FILL, preset, label, dashed=True, compact=True)
        for xy, text, label in point_specs
    ]
    region_nodes = [
        _node(axis, xy, text, _REGION_FILL, preset, label, dashed=True, compact=True)
        for xy, text, label in region_specs
    ]
    _boundary_arrow(axis, source, point_nodes[1])
    _routed_arrow(axis, source, region_nodes[0], corridor_y=0.43)
    for lane_name, nodes in (("point", point_nodes), ("region", region_nodes)):
        for index in range(len(nodes) - 1):
            register_collision(
                axis.figure,
                f"{lane_name}-decision-row-{index}",
                nodes[index].patch,
                nodes[index + 1].patch,
                padding_pt=0.0,
            )


def _draw_estimand_ledger(axis: Axes, preset: VenuePreset):
    display_columns = (
        "Deliverable",
        "Reported object",
        "Observable?",
        "Score",
        "Extra\nwells",
        "Rounds",
    )
    display_rows = (
        ("Tested-best", "latent best visited", "no", "simple regret", "0", "campaign"),
        ("Measured\nselection", "one tested well", "yes", "Rule-A regret", "0", "campaign"),
        ("Model\nrecommendation", "predicted optimum", "yes", "Rule-P regret", "0", "campaign"),
        (
            "Confirmation\nprotocol",
            "confirmed\ntested well",
            "yes",
            "confirmed regret",
            "protocol",
            "campaign +\nconfirmation",
        ),
        (
            "Acceptable-region\nmap",
            "acceptable input set",
            "yes",
            "symmetric\ndifference",
            "0",
            "campaign",
        ),
        ("Certificate", "conservative subset", "yes", "joint containment", "0", "campaign"),
    )
    table = axis.table(
        cellText=display_rows,
        colLabels=display_columns,
        cellLoc="left",
        colLoc="left",
        bbox=(0.0, 0.01, 1.0, 0.98),
        colWidths=(0.20, 0.205, 0.145, 0.19, 0.105, 0.155),
    )
    table.auto_set_font_size(False)
    table.set_fontsize(preset.body_pt)

    line_counts = (
        max(text.count("\n") + 1 for text in display_columns),
        *(max(text.count("\n") + 1 for text in row) for row in display_rows),
    )
    row_weights = tuple(1.0 + 0.385 * (lines - 1) for lines in line_counts)
    total_weight = sum(row_weights)
    for (row, column), cell in table.get_celld().items():
        cell.set_height(0.98 * row_weights[row] / total_weight)
        cell.set_edgecolor(_LINE)
        cell.set_linewidth(0.5)
        cell.PAD = 0.07
        if row == 0:
            cell.set_facecolor(_NEUTRAL_FILL)
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
        cell.get_text().set_linespacing(0.70)
        if column in {2, 4}:
            cell.get_text().set_ha("center")
        register_artist(
            axis.figure,
            f"ledger-r{row}-c{column}",
            cell.get_text(),
            cell,
            padding_pt=2.0,
        )
    return table


def build_figure2(preset: VenuePreset) -> FigureBundle:
    """Build the campaign decision and estimand definition."""
    headline = "One 48-well campaign supports distinct scientific decisions"
    deck = "Observation, selection, mapping and certification are different reported objects"
    columns = ("Deliverable", "Reported object", "Observable?", "Score", "Extra wells", "Rounds")
    rows = (
        ("Tested-best", "latent best visited", "no", "simple regret", "0", "campaign"),
        ("Measured selection", "one tested well", "yes", "Rule-A regret", "0", "campaign"),
        ("Model recommendation", "predicted optimum", "yes", "Rule-P regret", "0", "campaign"),
        (
            "Confirmation protocol",
            "confirmed tested well",
            "yes",
            "confirmed regret",
            "protocol",
            "campaign + confirmation",
        ),
        (
            "Acceptable-region map",
            "set of acceptable inputs",
            "yes",
            "symmetric difference",
            "0",
            "campaign",
        ),
        ("Certificate", "conservative subset", "yes", "joint containment", "0", "campaign"),
    )
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 178 if preset.name == "plos" else 154
        figure, content = editorial_figure(
            preset,
            height_mm,
            headline,
            deck,
            rows=2,
            cols=2,
        )
        content.set_height_ratios((1.0, 1.55))
        axis_a = figure.add_subplot(content[0, 0])
        axis_b = figure.add_subplot(content[0, 1])
        axis_c = figure.add_subplot(content[1, :])
        _prepare_panel(
            axis_a,
            "a",
            "Campaign observation loop",
            "",
            preset,
        )
        _prepare_panel(
            axis_b,
            "b",
            "Point and region decisions",
            "",
            preset,
        )
        _prepare_panel(
            axis_c,
            "c",
            "Estimand ledger",
            "",
            preset,
        )
        _draw_campaign_loop(axis_a, preset)
        _draw_decision_lanes(axis_b, preset)
        _draw_estimand_ledger(axis_c, preset)

    panel_data = {
        "A": {"stages": ["formulation", "wells", "assay", "model"]},
        "B": {
            "branches": {"point decision": 4, "region decision": 2},
            "point deliverables": (
                "tested-best",
                "measured selection",
                "model recommendation",
                "confirmation",
            ),
            "region deliverables": ("acceptable-region map", "conservative certificate"),
        },
        "C": {"columns": columns, "rows": rows},
    }
    alt_text = (
        "Benchmark definition. A 48-well campaign flows from formulation variables through noisy assay "
        "responses and a response model. The same observations support four point deliverables and two "
        "region deliverables, each tied to a distinct reported object and score. This figure contains no "
        "performance result."
    )
    caption = (
        "Figure 2 | One 48-well campaign supports distinct scientific decisions. (a) Formulation variables, "
        "the fixed campaign, noisy assay responses and the response model form one observation loop. "
        "(b) The same sampled campaign supports four point decisions and two region decisions. (c) The "
        "estimand ledger distinguishes each reported object, its observability, score, additional wells and "
        "experimental rounds. This figure defines the benchmark and contains no performance result."
    )
    long_description = (
        "Panel a presents four content-sized nodes on one baseline: formulation variables, a 48-well "
        "campaign, noisy assay responses and the response model. Panel b separates tested-best, measured "
        "selection, model recommendation and confirmation as four point deliverables, separate from "
        "acceptable-region mapping and conservative "
        "certification. Panel c provides a six-column lookup table for the reported object, observability, "
        "score, extra wells and experimental rounds associated with each deliverable."
    )
    return FigureBundle(
        "fig2",
        figure,
        panel_data,
        alt_text,
        caption,
        long_description,
        headline=headline,
        deck=deck,
        layout_rows=(("A", "B"), ("C",)),
    )
