"""Terminal-rule evidence display for the paper's Figure 2."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
import numpy as np

from .core import FigureBundle
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_SEARCH_COLOUR = "#A8C7E0"
_IDENTIFICATION_COLOUR = "#E7A77D"
_LABEL_OFFSETS = {"qlogei": -0.005, "qlognei": 0.005}


def _direct_rule_label(row: dict[str, float | str]) -> float:
    """Separate the two near-overlapping Rule-P endpoint labels."""
    return float(row["rule_p"]) + _LABEL_OFFSETS.get(str(row["arm"]), 0.0)


def build_figure2(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the terminal-rule comparison from validated Figure 2 evidence."""
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure, axes = plt.subplots(
            1,
            3,
            figsize=preset.figsize(74),
            gridspec_kw={"width_ratios": (0.9, 1.05, 1.2)},
            constrained_layout=True,
        )
        axis_a, axis_b, axis_c = axes
        for axis, label in zip(axes, "abc", strict=True):
            apply_axis_style(axis, preset)
            panel_label(axis, label, preset)

        rule_means = data["rule_means"]
        for row in rule_means:
            style = method_style(row["arm"])
            marker_facecolour = "white" if style.fill == "none" else style.colour
            axis_a.plot(
                (0, 1),
                (row["rule_a"], row["rule_p"]),
                color=style.colour,
                marker=style.marker,
                markersize=4.5,
                markerfacecolor=marker_facecolour,
                markeredgewidth=0.9,
            )
            axis_a.text(
                1.08,
                _direct_rule_label(row),
                style.label,
                color=style.colour,
                va="center",
                fontsize=preset.body_pt,
            )
        axis_a.set_xlim(-0.15, 1.78)
        axis_a.margins(y=0.14)
        axis_a.set_xticks((0, 1), ("Rule A", "Rule P"))
        axis_a.set_ylabel("Mean simple regret")
        axis_a.set_title("Same campaigns,\ndifferent terminal rule", loc="left", fontsize=preset.body_pt)

        contrasts = data["paired_rule_contrasts"]
        for y_position, row in enumerate(contrasts):
            style = method_style(row["arm"])
            axis_b.hlines(y_position, row["lo"], row["hi"], color=style.colour, linewidth=1.6)
            axis_b.scatter(
                row["mean"],
                y_position,
                color=style.colour,
                edgecolor=style.colour,
                marker=style.marker,
                s=24,
                zorder=3,
            )
        axis_b.axvline(0, color="#202124", linewidth=0.8, zorder=0)
        axis_b.set_yticks(range(len(contrasts)), [method_style(row["arm"]).label for row in contrasts])
        axis_b.invert_yaxis()
        axis_b.set_xlabel("Paired Rule P − Rule A regret\n← P lower        P higher →")
        axis_b.set_title("Paired terminal-rule\nchange", loc="left", fontsize=preset.body_pt)

        decomposition = data["decomposition"]
        y_positions = np.arange(len(decomposition))
        search_loss = np.array([row["oracle_best"] for row in decomposition])
        identification_loss = np.array([row["identification_gap"] for row in decomposition])
        axis_c.barh(y_positions, search_loss, color=_SEARCH_COLOUR, label="Search loss")
        axis_c.barh(
            y_positions,
            identification_loss,
            left=search_loss,
            color=_IDENTIFICATION_COLOUR,
            label="Identification loss",
        )
        axis_c.set_yticks(y_positions, [method_style(row["arm"]).label for row in decomposition])
        axis_c.invert_yaxis()
        maximum_regret = float(np.max(search_loss + identification_loss))
        axis_c.set_xlim(0, maximum_regret * 1.06)
        axis_c.set_xticks(np.arange(0, maximum_regret, 0.05))
        axis_c.set_xlabel("Rule-A simple regret\nblue: search\norange: identification")
        axis_c.set_title("Rule A = search +\nidentification loss", loc="left", fontsize=preset.body_pt)

    panel_data = {
        "A": {"rows": rule_means, "pairing": "same campaigns"},
        "B": {
            "rows": contrasts,
            "reference": 0.0,
            "interval": "paired bootstrap 95%",
            "direction": "negative means Rule P has lower regret",
        },
        "C": {
            "rows": decomposition,
            "identity": "Rule A = search loss + identification loss",
        },
    }
    alt_text = (
        "The same campaigns change ordering under Rules A and P. Paired intervals show method-specific "
        "terminal-rule changes relative to zero, while Rule-A stacked components show that measured "
        "selection combines search and identification losses for compatible arms."
    )
    return FigureBundle("fig2", figure, panel_data, alt_text)
