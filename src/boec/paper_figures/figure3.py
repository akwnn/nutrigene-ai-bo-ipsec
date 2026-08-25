"""Terminal-rule evidence display for the paper's Figure 3."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox
import numpy as np

from .core import FigureBundle
from .layout import editorial_figure, panel_heading
from .qa import register_collision
from .style import VenuePreset, apply_axis_style, method_style


_INK = "#243746"
_SEARCH_COLOUR = "#D6E4EE"
_IDENTIFICATION_COLOUR = "#B6BEC6"
_SLOPE_LABEL_OFFSETS = {"qlogei": 0.0, "qlognei": 14.0, "versionb": -8.0}


def _marker_facecolour(arm: str) -> str:
    style = method_style(arm)
    return "white" if style.fill == "none" else style.colour


def _keep_x_ticks_within_view(axis) -> None:
    lower, upper = sorted(axis.get_xlim())
    axis.set_xticks([tick for tick in axis.get_xticks() if lower <= tick <= upper])


def _forest_gutter_left_limit(
    axis, renderer, *, label_anchor: float, right_limit: float, gutter_px: float
) -> float:
    """Return an xlim left bound that reserves exactly `gutter_px` pixels of data
    space to the left of `label_anchor`, given the axes' fixed physical pixel width.

    The axes' pixel width is set by the GridSpec position, not by the data range,
    so this is solved algebraically rather than guessed: widening xlim leftward
    both grows the reserved gutter and rescales pixels-per-data-unit, so the two
    effects are resolved together instead of iterated.
    """

    axis_width_px = axis.get_window_extent(renderer).width
    target_ratio = gutter_px / axis_width_px
    if target_ratio >= 1.0:
        raise ValueError("row labels do not fit the reserved forest gutter at this preset")
    return (label_anchor - target_ratio * right_limit) / (1.0 - target_ratio)


def _bind_interval_window_extent(interval, axis) -> None:
    """Bind a live, correct `get_window_extent` to an hlines-created LineCollection.

    `Collection.get_window_extent()` returns a null (inf) Bbox for a plain,
    offset-less path collection such as `axis.hlines` produces: its default
    implementation only resolves the paths' data limits when queried against
    an identity transform, which excludes ordinary `axis.transData`-based
    collections. Binding an instance-level override lets the shared QA
    collision machinery (`register_collision` / `assert_no_registered_collisions`,
    which call `get_window_extent` on every registered artist) measure this
    interval correctly. The override recomputes from the live transform and
    renderer on every call, so it stays correct across the export-time figure
    resize in `export.py`, not just at build time.
    """

    def _window_extent(renderer=None, *, _interval=interval, _axis=axis):
        if renderer is None:
            renderer = _axis.figure.canvas.get_renderer()
        segment = _axis.transData.transform(_interval.get_segments()[0])
        half_stroke = renderer.points_to_pixels(_interval.get_linewidths()[0]) / 2.0
        return Bbox.from_extents(
            float(segment[:, 0].min()) - half_stroke,
            float(segment[:, 1].min()) - half_stroke,
            float(segment[:, 0].max()) + half_stroke,
            float(segment[:, 1].max()) + half_stroke,
        )

    interval.get_window_extent = _window_extent


def _draw_paired_forest(axis, contrasts: list[dict], preset: VenuePreset) -> None:
    figure = axis.figure
    label_gap_pt = 6.0
    collision_padding_pt = 2.0
    right_limit = 0.15
    label_anchor = min(row["lo"] for row in contrasts)
    styles = {row["arm"]: method_style(row["arm"]) for row in contrasts}

    # Measure the widest row label at this preset's actual body size so the
    # reserved gutter is a deterministic physical (points) quantity rather than
    # a hard-coded data coordinate tuned for one font size.
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    probes = [axis.text(0, 0, style.label, fontsize=preset.body_pt) for style in styles.values()]
    figure.canvas.draw()
    max_label_width_px = max(probe.get_window_extent(renderer).width for probe in probes)
    for probe in probes:
        probe.remove()
    gap_px = renderer.points_to_pixels(label_gap_pt)
    left_limit = _forest_gutter_left_limit(
        axis,
        renderer,
        label_anchor=label_anchor,
        right_limit=right_limit,
        gutter_px=max_label_width_px + gap_px,
    )

    for y_position, row in enumerate(contrasts):
        style = styles[row["arm"]]
        interval = axis.hlines(
            y_position,
            row["lo"],
            row["hi"],
            color=_INK,
            linewidth=0.9,
            zorder=2,
        )
        interval.set_gid(f"paired:{row['arm']}")
        _bind_interval_window_extent(interval, axis)
        point = axis.scatter(
            row["mean"],
            y_position,
            facecolor=_marker_facecolour(row["arm"]),
            edgecolor=style.colour,
            linewidth=0.8,
            marker=style.marker,
            s=34,
            zorder=3,
        )
        point.set_gid(f"paired-point:{row['arm']}")
        label = axis.annotate(
            style.label,
            (label_anchor, y_position),
            xycoords="data",
            xytext=(-label_gap_pt, 0),
            textcoords="offset points",
            color=_INK,
            ha="right",
            va="center",
            fontsize=preset.body_pt,
        )
        label.set_gid(f"paired-label:{row['arm']}")
        register_collision(
            figure,
            f"paired-label-clears-interval-{row['arm']}",
            label,
            interval,
            padding_pt=collision_padding_pt,
        )

    axis.axvline(0, color=_INK, linewidth=0.8, zorder=0)
    axis.annotate(
        "no terminal-rule effect",
        (0, 0.98),
        xycoords=axis.get_xaxis_transform(),
        xytext=(4, 0),
        textcoords="offset points",
        color=_INK,
        ha="left",
        va="top",
        fontsize=preset.body_pt,
    )
    axis.text(
        0,
        -0.16,
        "Rule P lowers regret",
        transform=axis.transAxes,
        color=_INK,
        ha="left",
        va="top",
        fontsize=preset.body_pt,
    )
    axis.text(
        1,
        -0.16,
        "Rule P raises regret",
        transform=axis.transAxes,
        color=_INK,
        ha="right",
        va="top",
        fontsize=preset.body_pt,
    )
    axis.set_xlim(left_limit, right_limit)
    axis.set_ylim(len(contrasts) - 0.55, -0.55)
    axis.set_yticks(())
    axis.set_xlabel(
        "Paired simple-regret difference (Rule P − Rule A)",
        fontsize=preset.body_pt,
        labelpad=17,
    )
    _keep_x_ticks_within_view(axis)


def _draw_rule_means(axis, rule_means: list[dict], preset: VenuePreset) -> None:
    for row in rule_means:
        style = method_style(row["arm"])
        slope = axis.plot(
            (0, 1),
            (row["rule_a"], row["rule_p"]),
            color=style.colour,
            linewidth=0.8,
            marker=style.marker,
            markersize=4.5,
            markerfacecolor=_marker_facecolour(row["arm"]),
            markeredgewidth=0.8,
        )[0]
        slope.set_gid(f"rule-slope:{row['arm']}")
        axis.annotate(
            style.label,
            (1, row["rule_p"]),
            xytext=(6, _SLOPE_LABEL_OFFSETS.get(str(row["arm"]), 0.0)),
            textcoords="offset points",
            color=_INK,
            ha="left",
            va="center",
            fontsize=preset.body_pt,
        )
    axis.set_xlim(-0.12, 1.60)
    axis.set_ylim(0.075, 0.215)
    axis.set_xticks((0, 1), ("Rule A", "Rule P"))
    axis.set_ylabel("Mean simple regret", fontsize=preset.body_pt)


def _draw_decomposition(axis, decomposition: list[dict], preset: VenuePreset) -> None:
    y_positions = np.arange(len(decomposition))
    search_loss = np.array([row["oracle_best"] for row in decomposition])
    identification_loss = np.array([row["identification_gap"] for row in decomposition])
    search_bars = axis.barh(
        y_positions,
        search_loss,
        color=_SEARCH_COLOUR,
        edgecolor=_INK,
        linewidth=0.5,
        hatch="////",
        label="Search loss",
    )
    identification_bars = axis.barh(
        y_positions,
        identification_loss,
        left=search_loss,
        color=_IDENTIFICATION_COLOUR,
        edgecolor=_INK,
        linewidth=0.5,
        hatch="....",
        label="Identification\nloss",
    )
    for row, search, identification in zip(
        decomposition,
        search_bars.patches,
        identification_bars.patches,
        strict=True,
    ):
        search.set_gid(f"decomposition:{row['arm']}:search")
        identification.set_gid(f"decomposition:{row['arm']}:identification")

    axis.set_yticks(
        y_positions,
        [method_style(row["arm"]).label for row in decomposition],
    )
    axis.invert_yaxis()
    maximum_regret = float(np.max(search_loss + identification_loss))
    axis.set_xlim(0, maximum_regret * 1.08)
    axis.set_xlabel("Rule-A simple regret", fontsize=preset.body_pt)
    position = axis.get_position()
    axis.set_position((position.x0, position.y0, position.width * 0.60, position.height))
    axis.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.50),
        ncol=1,
        frameon=False,
        fontsize=preset.body_pt,
        title="Rule A =\nsearch loss +\nidentification loss",
        title_fontsize=preset.body_pt,
        handlelength=1.1,
        handletextpad=0.4,
        labelspacing=0.7,
    )
    _keep_x_ticks_within_view(axis)


def build_figure3(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the paired terminal-rule comparison from validated evidence."""
    headline = "The terminal rule changes method rankings on the same campaigns"
    deck = "Hill · d=6 · σ=0.25 · n=50 paired campaigns · 95% paired-bootstrap intervals"
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure, content = editorial_figure(
            preset,
            150,
            headline,
            deck,
            rows=2,
            cols=2,
        )
        content.set_height_ratios((1.18, 1.0))
        content.update(hspace=0.58, wspace=0.38)
        axis_a = figure.add_subplot(content[0, :])
        axis_b = figure.add_subplot(content[1, 0])
        axis_c = figure.add_subplot(content[1, 1])
        for axis in (axis_a, axis_b, axis_c):
            apply_axis_style(axis, preset)
        panel_heading(axis_a, "a", "Paired terminal-rule effect", "", preset)
        panel_heading(axis_b, "b", "Mean regret by rule", "", preset)
        panel_heading(axis_c, "c", "What Rule A combines", "", preset)

        rule_means = data["rule_means"]
        contrasts = data["paired_rule_contrasts"]
        decomposition = data["decomposition"]
        _draw_paired_forest(axis_a, contrasts, preset)
        _draw_rule_means(axis_b, rule_means, preset)
        _draw_decomposition(axis_c, decomposition, preset)

    panel_data = {
        "A": {
            "rows": contrasts,
            "pairing": "same campaigns",
            "reference": 0.0,
            "interval": "paired bootstrap 95%",
            "direction": "negative means Rule P has lower regret",
            "dominant_panel": True,
        },
        "B": {"rows": rule_means, "pairing": "same campaigns"},
        "C": {
            "rows": decomposition,
            "identity": "Rule A = search loss + identification loss",
            "redundant_encoding": "luminance and hatch",
        },
    }
    alt_text = (
        "The same campaigns (n=50 per method) change ordering under measured-selection Rule A and "
        "model-recommendation Rule P. SPADE, qLogEI and qLogNEI have negative paired "
        "Rule-P-minus-Rule-A effects, whereas Classical DoE has a positive effect. Rule-A regret is "
        "decomposed into search and identification losses."
    )
    caption = (
        "Figure 3 | The terminal decision rule changes comparative performance on the same campaigns. "
        "Rule A is measured selection: the tested well with the largest noisy assay response. Rule P is "
        "model recommendation: the input recommended by the fitted response model. (a) Paired Rule P − "
        "Rule A simple-regret differences with 95% paired-bootstrap intervals for the Hill d=6, σ=0.25 "
        "benchmark (n=50 paired campaigns per method); negative values favour Rule P. SPADE shows the "
        "largest reduction (−0.0543), while Classical DoE increases regret (+0.1035). (b) Mean simple "
        "regret under both rules orients the paired effects. (c) For compatible arms, Rule-A regret is the "
        "sum of search loss and identification loss."
    )
    long_description = (
        "Panel a is the dominant forest plot. SPADE is −0.0543 with interval −0.0693 to −0.0398; "
        "qLogEI is −0.0320 with interval −0.0489 to −0.0151; qLogNEI is −0.0246 with interval "
        "−0.0417 to −0.0076; and Classical DoE is +0.1035 with interval +0.0723 to +0.1367. Panel b "
        "links each method's mean measured-selection Rule-A regret to its mean model-recommendation "
        "Rule-P regret. Panel c partitions measured-selection regret into search and identification "
        "components using both luminance and hatch."
    )
    return FigureBundle(
        "fig3",
        figure,
        panel_data,
        alt_text,
        caption,
        long_description,
        headline=headline,
        deck=deck,
        layout_rows=(("A",), ("B", "C")),
    )
