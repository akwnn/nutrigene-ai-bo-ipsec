"""Point–map–cost decision display for the paper's Figure 3."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt

from .core import FigureBundle, assert_no_prohibited_content
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_INK = "#202124"
_TABLE_LINE = "#CBD2D9"
_SESOI_FILL = "#E5E7EB"
_POINT_LABEL_OFFSETS = {
    "spade_cf_m0": (5, 5),
    "sobol": (5, 9),
    "lhs": (5, -6),
    "qlogei": (5, 5),
    "qlognei": (5, -8),
    "doe": (5, 3),
}


def _marker_facecolour(arm: str) -> str:
    """Return the shared fill treatment for a method marker."""
    style = method_style(arm)
    return "white" if style.fill == "none" else style.colour


def _keep_ticks_within_view(axis) -> None:
    """Prevent locator overhang from clipping terminal tick labels at final size."""
    x_lower, x_upper = sorted(axis.get_xlim())
    y_lower, y_upper = sorted(axis.get_ylim())
    axis.set_xticks([tick for tick in axis.get_xticks() if x_lower <= tick <= x_upper])
    axis.set_yticks([tick for tick in axis.get_yticks() if y_lower <= tick <= y_upper])


def build_figure3(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the registered target point-map-cost display from validated evidence."""
    assert_no_prohibited_content(data)
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure = plt.figure(figsize=preset.figsize(142), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, width_ratios=(1.05, 0.95))
        axis_a = figure.add_subplot(grid[0, 0])
        axis_b = figure.add_subplot(grid[0, 1])
        axis_c = figure.add_subplot(grid[1, 0])
        axis_d = figure.add_subplot(grid[1, 1])
        axes = (axis_a, axis_b, axis_c, axis_d)
        for axis, label in zip(axes, "abcd", strict=True):
            apply_axis_style(axis, preset)
            label_text = panel_label(axis, label, preset)
            label_text.set_position((-0.10, 0.99))

        target_points = data["target_points"]
        for row in target_points:
            style = method_style(row["arm"])
            axis_a.scatter(
                row["map_error"],
                row["regret_p"],
                s=34,
                marker=style.marker,
                facecolor=_marker_facecolour(row["arm"]),
                edgecolor=style.colour,
                linewidth=0.9,
                zorder=3,
            )
            axis_a.annotate(
                style.label,
                (row["map_error"], row["regret_p"]),
                xytext=_POINT_LABEL_OFFSETS[row["arm"]],
                textcoords="offset points",
                fontsize=preset.body_pt,
                color=style.colour,
            )
        axis_a.margins(0.18)
        axis_a.set_xlabel("Symmetric-difference error  ← lower is better")
        axis_a.set_ylabel("Rule-P simple regret  ← lower is better")
        axis_a.set_title("Registered target: point–map trade-off", loc="left", fontsize=preset.body_pt)

        contrast_rows = data["contrasts"]
        sesoi = contrast_rows[0]["sesoi"]
        axis_b.axvspan(-sesoi, sesoi, color=_SESOI_FILL, zorder=0)
        axis_b.axvline(0, color=_INK, linewidth=0.8, zorder=1)
        contrast_labels = (
            "Map: SPADE − Sobol",
            "Map: SPADE − qLogNEI",
            "Regret: SPADE − qLogNEI",
        )
        for y_position, row in enumerate(contrast_rows):
            axis_b.hlines(y_position, row["lo"], row["hi"], color=_INK, linewidth=1.3, zorder=2)
            axis_b.scatter(row["mean"], y_position, color="#009E73", s=24, zorder=3)
        axis_b.set_yticks(range(len(contrast_rows)), contrast_labels)
        axis_b.invert_yaxis()
        axis_b.set_xlabel("Paired difference (SPADE − comparator)")
        axis_b.set_title("Paired contrasts and ±0.02 margin", loc="left", fontsize=preset.body_pt)

        costs = data["cost_ledger"]
        axis_c.set_axis_off()
        cost_rows = [
            [method_style(row["arm"]).label, str(row["wells"]), str(row["rounds"])]
            for row in costs
        ]
        table = axis_c.table(
            cellText=cost_rows,
            colLabels=("Method", "Wells", "Rounds"),
            cellLoc="left",
            colLoc="left",
            bbox=(0.02, 0.02, 0.96, 0.82),
            colWidths=(0.54, 0.23, 0.23),
        )
        table.auto_set_font_size(False)
        table.set_fontsize(preset.body_pt)
        for (row_index, _), cell in table.get_celld().items():
            cell.set_edgecolor(_TABLE_LINE)
            cell.set_linewidth(0.5)
            cell.set_facecolor("#F3F6F8" if row_index == 0 else "white")
            cell.get_text().set_color(_INK)
            if row_index == 0:
                cell.get_text().set_fontweight("bold")
        axis_c.set_title("Equal wells do not mean equal feedback rounds", loc="left", fontsize=preset.body_pt)

        for condition, marker in zip(
            ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25"), ("o", "s"), strict=True
        ):
            rows = [row for row in data["hartmann"] if row["condition"] == condition]
            axis_d.scatter(
                [row["map_error"] for row in rows],
                [row["regret_p"] for row in rows],
                marker=marker,
                s=24,
                facecolor="none",
                edgecolor="#6B7280",
                linewidth=0.9,
                label=condition.replace("hartmann6-", ""),
            )
        axis_d.set_xlabel("Symmetric-difference error")
        axis_d.set_ylabel("Rule-P simple regret")
        axis_d.legend(
            title="Descriptive means",
            fontsize=preset.body_pt,
            title_fontsize=preset.body_pt,
            loc="best",
        )
        axis_d.set_title(
            "Hartmann robustness: descriptive means; intervals unavailable",
            loc="left",
            fontsize=preset.body_pt,
            wrap=True,
        )
        for axis in (axis_a, axis_b, axis_d):
            _keep_ticks_within_view(axis)

    panel_data = {
        "A": {"rows": target_points, "terminal_rule": data["terminal_rule"]},
        "B": {"rows": contrast_rows, "sesoi": sesoi, "reference": 0.0},
        "C": {"rows": costs, "rounds_are_not_point_size": True},
        "D": {"rows": data["hartmann"], "intervals": "unavailable", "summary": "descriptive means"},
    }
    assert_no_prohibited_content(panel_data)
    alt_text = (
        "The registered target displays distinct point-map trade-offs for SPADE and batch BO. "
        "Paired contrasts are shown against a practical margin, wells and feedback rounds are "
        "reported separately, and Hartmann means are descriptive because intervals are unavailable."
    )
    return FigureBundle("fig3", figure, panel_data, alt_text)
