"""Terminal-rule evidence display for the paper's Figure 2."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
import numpy as np

from .core import FigureBundle
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_INK = "#243746"
_SEARCH_COLOUR = "#D6E4EE"
_IDENTIFICATION_COLOUR = "#B6BEC6"
_LABEL_OFFSETS = {"qlogei": -0.005, "qlognei": 0.005}


def _direct_rule_label(row: dict[str, float | str]) -> float:
    return float(row["rule_p"]) + _LABEL_OFFSETS.get(str(row["arm"]), 0.0)


def build_figure2(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the paired terminal-rule comparison from validated evidence."""
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 164 if preset.name == "plos" else 150
        figure = plt.figure(figsize=preset.figsize(height_mm), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, hspace=0.14, wspace=0.14)
        axis_a = figure.add_subplot(grid[0, 0])
        axis_b = figure.add_subplot(grid[0, 1])
        axis_c = figure.add_subplot(grid[1, :])
        axes = (axis_a, axis_b, axis_c)
        for axis, label in zip(axes, "abc", strict=True):
            apply_axis_style(axis, preset)
            panel_label(axis, label, preset).set_position((-0.16, 1.03))

        rule_means = data["rule_means"]
        for row in rule_means:
            style = method_style(row["arm"])
            marker_facecolour = "white" if style.fill == "none" else style.colour
            axis_a.plot(
                (0, 1),
                (row["rule_a"], row["rule_p"]),
                color=style.colour,
                linewidth=0.8,
                marker=style.marker,
                markersize=4.5,
                markerfacecolor=marker_facecolour,
                markeredgewidth=0.8,
            )
            axis_a.text(
                1.07,
                _direct_rule_label(row),
                style.label,
                color=_INK,
                va="center",
                fontsize=preset.body_pt,
            )
        axis_a.set_xlim(-0.12, 2.0)
        axis_a.margins(y=0.16)
        axis_a.set_xticks((0, 1), ("Rule A", "Rule P"))
        axis_a.set_ylabel("Mean simple regret", fontsize=preset.body_pt)
        axis_a.set_title("Same campaigns\ndifferent terminal rules", loc="left", fontsize=preset.body_pt)

        contrasts = data["paired_rule_contrasts"]
        for y_position, row in enumerate(contrasts):
            style = method_style(row["arm"])
            interval = axis_b.hlines(
                y_position,
                row["lo"],
                row["hi"],
                color=_INK,
                linewidth=0.9,
                zorder=2,
            )
            interval.set_gid(f"paired:{row['arm']}")
            axis_b.scatter(
                row["mean"],
                y_position,
                facecolor="white" if style.fill == "none" else style.colour,
                edgecolor=style.colour,
                linewidth=0.8,
                marker=style.marker,
                s=28,
                zorder=3,
            )
        axis_b.axvline(0, color=_INK, linewidth=0.8, zorder=0)
        axis_b.set_yticks(range(len(contrasts)), [method_style(row["arm"]).label for row in contrasts])
        axis_b.invert_yaxis()
        axis_b.set_xlabel(
            "Paired Rule P − Rule A regret\n← P lower          P higher →",
            fontsize=preset.body_pt,
        )
        axis_b.set_title("Paired terminal-rule effect\n95% bootstrap interval", loc="left", fontsize=preset.body_pt)
        axis_b.set_xticks([tick for tick in axis_b.get_xticks() if axis_b.get_xlim()[0] <= tick <= axis_b.get_xlim()[1]])

        decomposition = data["decomposition"]
        y_positions = np.arange(len(decomposition))
        search_loss = np.array([row["oracle_best"] for row in decomposition])
        identification_loss = np.array([row["identification_gap"] for row in decomposition])
        axis_c.barh(
            y_positions,
            search_loss,
            color=_SEARCH_COLOUR,
            edgecolor=_INK,
            linewidth=0.5,
            hatch="////",
            label="Search loss",
        )
        axis_c.barh(
            y_positions,
            identification_loss,
            left=search_loss,
            color=_IDENTIFICATION_COLOUR,
            edgecolor=_INK,
            linewidth=0.5,
            hatch="....",
            label="Identification loss",
        )
        axis_c.set_yticks(y_positions, [method_style(row["arm"]).label for row in decomposition])
        axis_c.invert_yaxis()
        maximum_regret = float(np.max(search_loss + identification_loss))
        axis_c.set_xlim(0, maximum_regret * 1.08)
        axis_c.set_xticks([tick for tick in axis_c.get_xticks() if tick <= axis_c.get_xlim()[1]])
        axis_c.set_xlabel("Rule-A simple regret", fontsize=preset.body_pt)
        axis_c.set_title(
            "Rule A = search loss + identification loss",
            loc="left",
            fontsize=preset.body_pt,
        )
        axis_c.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, -0.40),
            ncol=2,
            fontsize=preset.body_pt,
            handlelength=1.1,
            columnspacing=0.8,
        )

    panel_data = {
        "A": {"rows": rule_means, "pairing": "same campaigns"},
        "B": {
            "rows": contrasts,
            "reference": 0.0,
            "interval": "paired bootstrap 95%",
            "direction": "negative means Rule P has lower regret",
            "dominant_panel": True,
        },
        "C": {
            "rows": decomposition,
            "identity": "Rule A = search loss + identification loss",
            "redundant_encoding": "luminance and hatch",
        },
    }
    alt_text = (
        "The same campaigns (n=50 per method) change ordering under Rules A and P. SPADE, qLogEI and qLogNEI have "
        "negative paired Rule-P-minus-Rule-A effects, whereas Classical DoE has a positive effect. "
        "Rule-A regret is decomposed into search and identification losses."
    )
    caption = (
        "Figure 2 | The terminal decision rule changes comparative performance on the same campaigns. "
        "(a) Mean simple regret under measured-selection Rule A and model-recommendation Rule P for the "
        "Hill d=6, σ=0.25 benchmark (n=50 paired campaigns per method). (b) Paired Rule P − Rule A "
        "differences with 95% paired-bootstrap intervals; negative values favour Rule P. SPADE shows the "
        "largest reduction (−0.0543), while Classical DoE increases regret (+0.1035). (c) For compatible "
        "arms, Rule-A regret is the sum of search loss and identification loss."
    )
    long_description = (
        "Panel a is a slopegraph linking each method's mean Rule-A and Rule-P regret. Panel b is the "
        "principal forest plot: SPADE is −0.0543 with interval −0.0693 to −0.0398; qLogEI is −0.0320 "
        "with interval −0.0489 to −0.0151; qLogNEI is −0.0246 with interval −0.0417 to −0.0076; and "
        "Classical DoE is +0.1035 with interval +0.0723 to +0.1367. Panel c partitions measured-selection "
        "regret into search and identification components using both luminance and hatch."
    )
    return FigureBundle("fig2", figure, panel_data, alt_text, caption, long_description)
