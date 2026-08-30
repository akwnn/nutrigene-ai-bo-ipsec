"""Point–map–cost decision display for the paper's Figure 3."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .core import FigureBundle, assert_no_prohibited_content
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_INK = "#243746"
_SESOI_FILL = "#E5E7EB"
_CONTRAST_SPECS = {
    "map_spade_minus_sobol": "Map: SPADE − Sobol",
    "map_spade_minus_qlognei": "Map: SPADE − qLogNEI",
    "regret_spade_minus_qlognei": "Regret: SPADE − qLogNEI",
}
_HARTMANN_CONDITIONS = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
_KEY_LABELS = {"spade_cf_m0", "qlognei", "sobol", "doe"}
_POINT_LABEL_OFFSETS = {
    "spade_cf_m0": (-6, 7),
    "qlognei": (5, -10),
    "sobol": (6, 12),
    "doe": (-5, 5),
}


def _marker_facecolour(arm: str) -> str:
    style = method_style(arm)
    return "white" if style.fill == "none" else style.colour


def _keep_ticks_within_view(axis) -> None:
    x_lower, x_upper = sorted(axis.get_xlim())
    y_lower, y_upper = sorted(axis.get_ylim())
    axis.set_xticks([tick for tick in axis.get_xticks() if x_lower <= tick <= x_upper])
    axis.set_yticks([tick for tick in axis.get_yticks() if y_lower <= tick <= y_upper])


def _ordered_contrasts(data: dict) -> tuple[list[dict], float]:
    by_id = {row.get("contrast_id"): row for row in data["contrasts"]}
    if set(by_id) != set(_CONTRAST_SPECS) or len(by_id) != len(data["contrasts"]):
        raise ValueError(f"expected contrast IDs {tuple(_CONTRAST_SPECS)}")
    sesois = {row.get("sesoi") for row in by_id.values()}
    if sesois != {0.02}:
        raise ValueError("expected a common SESOI of 0.02")
    return [by_id[contrast_id] for contrast_id in _CONTRAST_SPECS], 0.02


def _legend_handles(arms: list[str]) -> list[Line2D]:
    handles = []
    for arm in arms:
        style = method_style(arm)
        handles.append(
            Line2D(
                [0],
                [0],
                marker=style.marker,
                linestyle="none",
                markersize=4.2,
                markerfacecolor=_marker_facecolour(arm),
                markeredgecolor=style.colour,
                markeredgewidth=0.8,
                label=style.label,
            )
        )
    return handles


def build_figure3(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the registered target point-map-cost display."""
    assert_no_prohibited_content(data)
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 166 if preset.name == "plos" else 150
        figure = plt.figure(figsize=preset.figsize(height_mm), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, width_ratios=(1.03, 0.97), hspace=0.18, wspace=0.12)
        axis_a = figure.add_subplot(grid[0, 0])
        axis_b = figure.add_subplot(grid[0, 1])
        axis_c = figure.add_subplot(grid[1, 0])
        axis_d = figure.add_subplot(grid[1, 1])
        for axis, label in zip((axis_a, axis_b, axis_c, axis_d), "abcd", strict=True):
            apply_axis_style(axis, preset)
            label_text = panel_label(axis, label, preset)
            label_text.set_position((-0.10, 1.01))

        target_points = data["target_points"]
        for row in target_points:
            style = method_style(row["arm"])
            axis_a.scatter(
                row["map_error"],
                row["regret_p"],
                s=32,
                marker=style.marker,
                facecolor=_marker_facecolour(row["arm"]),
                edgecolor=style.colour,
                linewidth=0.8,
                zorder=3,
            )
            if row["arm"] in _KEY_LABELS:
                axis_a.annotate(
                    style.label,
                    (row["map_error"], row["regret_p"]),
                    xytext=_POINT_LABEL_OFFSETS[row["arm"]],
                    textcoords="offset points",
                    ha="right" if row["arm"] in {"doe", "spade_cf_m0"} else "left",
                    fontsize=preset.body_pt,
                    color=_INK,
                )
        axis_a.margins(0.20)
        axis_a.set_xlabel("Symmetric-difference error  ← lower is better", fontsize=preset.body_pt)
        axis_a.set_ylabel("Rule-P simple regret  ← lower is better", fontsize=preset.body_pt)
        axis_a.set_title("Registered point–map trade-off", loc="left", fontsize=preset.body_pt)

        contrast_rows, sesoi = _ordered_contrasts(data)
        axis_b.axvspan(-sesoi, sesoi, color=_SESOI_FILL, zorder=0)
        axis_b.axvline(0, color=_INK, linewidth=0.8, zorder=1)
        for y_position, row in enumerate(contrast_rows):
            axis_b.hlines(y_position, row["lo"], row["hi"], color=_INK, linewidth=0.9, zorder=2)
            axis_b.scatter(row["mean"], y_position, color="#009E73", edgecolor=_INK, linewidth=0.5, s=28, zorder=3)
        axis_b.set_yticks(range(len(contrast_rows)), tuple(_CONTRAST_SPECS.values()))
        axis_b.invert_yaxis()
        axis_b.set_xlabel("Paired difference (SPADE − comparator)", fontsize=preset.body_pt)
        axis_b.set_title("Paired contrasts and ±0.02 margin", loc="left", fontsize=preset.body_pt)

        costs = data["cost_ledger"]
        for y_position, row in enumerate(costs):
            style = method_style(row["arm"])
            axis_c.hlines(y_position, 0, row["rounds"], color="#AAB4BE", linewidth=0.8, zorder=1)
            axis_c.scatter(
                row["rounds"],
                y_position,
                marker=style.marker,
                s=28,
                facecolor=_marker_facecolour(row["arm"]),
                edgecolor=style.colour,
                linewidth=0.8,
                zorder=2,
            )
        axis_c.set_yticks(range(len(costs)), [method_style(row["arm"]).label for row in costs])
        axis_c.set_ylim(len(costs) - 0.6, -0.6)
        axis_c.set_xlim(0, 10.8)
        axis_c.set_xticks((0, 2, 4, 6, 8, 10))
        axis_c.set_xlabel("Feedback rounds", fontsize=preset.body_pt)
        axis_c.set_title("Equal wells, unequal experimental feedback", loc="left", fontsize=preset.body_pt)
        axis_c.text(
            0.98,
            0.04,
            "All methods use 48 wells",
            transform=axis_c.transAxes,
            ha="right",
            va="bottom",
            fontsize=preset.body_pt,
            color=_INK,
            fontweight="bold",
        )

        axis_d.set_axis_off()
        axis_d.set_title(
            "Hartmann robustness\ndescriptive means\nintervals unavailable",
            loc="left",
            fontsize=preset.body_pt,
        )
        facet_axes = (
            axis_d.inset_axes((0.02, 0.20, 0.45, 0.62)),
            axis_d.inset_axes((0.53, 0.20, 0.45, 0.62)),
        )
        all_hartmann = data["hartmann"]
        map_limits = (
            min(row["map_error"] for row in all_hartmann) - 0.008,
            max(row["map_error"] for row in all_hartmann) + 0.008,
        )
        regret_limits = (
            min(row["regret_p"] for row in all_hartmann) - 0.04,
            max(row["regret_p"] for row in all_hartmann) + 0.04,
        )
        for facet, condition, title in zip(facet_axes, _HARTMANN_CONDITIONS, ("d=6", "d=8"), strict=True):
            apply_axis_style(facet, preset)
            rows = [row for row in all_hartmann if row["condition"] == condition]
            for row in rows:
                style = method_style(row["arm"])
                point = facet.scatter(
                    row["map_error"],
                    row["regret_p"],
                    marker=style.marker,
                    s=22,
                    facecolor=_marker_facecolour(row["arm"]),
                    edgecolor=style.colour,
                    linewidth=0.8,
                )
                point.set_gid(f"{condition}:{row['arm']}")
            facet.set_xlim(*map_limits)
            facet.set_ylim(*regret_limits)
            facet.set_title(title, loc="left", fontsize=preset.body_pt)
            facet.set_xlabel("Map error", fontsize=preset.body_pt)
            if facet is facet_axes[0]:
                facet.set_ylabel("Rule-P regret", fontsize=preset.body_pt)
            else:
                facet.set_yticklabels([])
            _keep_ticks_within_view(facet)
        arms = [row["arm"] for row in costs]
        axis_d.legend(
            handles=_legend_handles(arms),
            loc="lower center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=3,
            fontsize=preset.body_pt,
            columnspacing=0.8,
            handletextpad=0.3,
        )

        for axis in (axis_a, axis_b, axis_c):
            _keep_ticks_within_view(axis)

    panel_data = {
        "A": {"rows": target_points, "terminal_rule": data["terminal_rule"]},
        "B": {"rows": contrast_rows, "sesoi": sesoi, "reference": 0.0},
        "C": {
            "rows": costs,
            "rounds_are_not_point_size": True,
            "constant_wells": 48,
            "encoding": "rounds lollipop",
        },
        "D": {
            "rows": all_hartmann,
            "intervals": "unavailable",
            "summary": "descriptive means",
            "facets": ["d=6", "d=8"],
        },
    }
    assert_no_prohibited_content(panel_data)
    alt_text = (
        "On the registered target, SPADE has the lowest map error and competitive Rule-P regret. "
        "Paired contrasts show lower SPADE map error than Sobol and qLogNEI, while its regret is slightly "
        "higher than qLogNEI. All methods use 48 wells but require one to ten feedback rounds. Hartmann "
        "d=6 and d=8 panels report descriptive means only."
    )
    caption = (
        "Figure 3 | Point, map and experimental-cost evidence for SPADE. (a) Registered Hill-target means "
        "for symmetric-difference map error and Rule-P simple regret (n=25 campaigns per method); lower is "
        "better on both axes. (b) Paired SPADE-minus-comparator contrasts with 95% intervals and the prespecified "
        "±0.02 smallest effect size of interest. SPADE reduces map error relative to Sobol (−0.0109) and qLogNEI "
        "(−0.0327), while Rule-P regret is +0.0094 relative to qLogNEI. (c) Every method consumes 48 wells, but "
        "feedback ranges from one to ten rounds. (d) Hartmann d=6 and d=8 robustness values are descriptive means; "
        "intervals are unavailable."
    )
    long_description = (
        "Panel a places six methods in the map-error versus Rule-P-regret plane and directly labels SPADE, qLogNEI, "
        "Sobol and Classical DoE. Panel b shows three paired estimates: SPADE minus Sobol map error is −0.010892 "
        "(−0.015662, −0.005969); SPADE minus qLogNEI map error is −0.032655 (−0.037232, −0.028543); and SPADE "
        "minus qLogNEI regret is +0.009375 (+0.002578, +0.016151). Panel c is a rounds lollipop: Latin hypercube "
        "and Sobol use one round, SPADE two, Classical DoE three, and qLogEI/qLogNEI ten. Panel d separates "
        "Hartmann d=6 and d=8 into two small multiples without inferential intervals."
    )
    return FigureBundle("fig3", figure, panel_data, alt_text, caption, long_description)
