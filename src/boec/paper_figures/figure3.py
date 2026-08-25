"""Terminal-rule evidence display for the paper's Figure 3."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
import numpy as np

from .core import FigureBundle
from .layout import editorial_figure, panel_heading
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


def _draw_paired_forest(axis, contrasts: list[dict], preset: VenuePreset) -> None:
    for y_position, row in enumerate(contrasts):
        style = method_style(row["arm"])
        interval = axis.hlines(
            y_position,
            row["lo"],
            row["hi"],
            color=_INK,
            linewidth=0.9,
            zorder=2,
        )
        interval.set_gid(f"paired:{row['arm']}")
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
        axis.text(
            -0.084,
            y_position,
            style.label,
            color=_INK,
            ha="left",
            va="center",
            fontsize=preset.body_pt,
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
    axis.set_xlim(-0.09, 0.15)
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
