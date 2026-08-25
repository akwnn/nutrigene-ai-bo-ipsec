"""Reliability and non-vacuity audit for the paper's Figure 4."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt

from .core import FigureBundle, assert_no_prohibited_content
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_CONTAINMENT_COLOUR = "#009E73"
_UNDERCOVERAGE_WARNING = "#B2182B"
_INK = "#202124"
_MUTED = "#6B7280"


def _marker_facecolour(arm: str) -> str:
    """Use the shared open-marker convention where a method requires it."""
    style = method_style(arm)
    return "white" if style.fill == "none" else style.colour


def _containment_effect(row: dict) -> tuple[float, float, float]:
    """Return containment relative to its nominal assurance for a scored cell."""
    return (
        row["proportion"] - row["alpha"],
        row["ci_lo"] - row["alpha"],
        row["ci_hi"] - row["alpha"],
    )


def _containment_colour(row: dict) -> str:
    """Reserve warning red for an interval wholly below nominal assurance."""
    return _UNDERCOVERAGE_WARNING if row["ci_hi"] < row["alpha"] else _CONTAINMENT_COLOUR


def _effect_limits(rows: list[dict]) -> tuple[float, float]:
    """Leave room for exact-denominator labels while retaining the zero reference."""
    intervals = [_containment_effect(row) for row in rows if row["n"]]
    lower = min([0.0, *(interval[1] for interval in intervals)])
    upper = max([0.0, *(interval[2] for interval in intervals)])
    return lower - 0.04, upper + 0.16


def _keep_ticks_within_view(axis) -> None:
    """Avoid terminal locator labels extending past the final-size figure edge."""
    lower, upper = sorted(axis.get_xlim())
    axis.set_xticks([tick for tick in axis.get_xticks() if lower <= tick <= upper])


def _hill_label(row: dict) -> str:
    """Compactly expose the selected Hill condition and nominal assurance."""
    condition = row["condition"].replace("hill-d", "d=").replace("-s", "; σ=")
    return f"{condition}; γ={row['gamma']:g}; α={row['alpha']:g}"


def build_figure4(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the retrospective calibration and prospective certification audit."""
    assert_no_prohibited_content(data)
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 160 if preset.name == "plos" else 146
        figure = plt.figure(figsize=preset.figsize(height_mm), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, width_ratios=(0.95, 1.05))
        axis_a = figure.add_subplot(grid[0, 0])
        axis_b = figure.add_subplot(grid[0, 1])
        axis_c = figure.add_subplot(grid[1, 0])
        axis_d = figure.add_subplot(grid[1, 1])
        axes = (axis_a, axis_b, axis_c, axis_d)
        for axis, label in zip(axes, "abcd", strict=True):
            apply_axis_style(axis, preset)
            label_text = panel_label(axis, label, preset)
            label_text.set_position((-0.10, 0.99))

        calibration_rows = data["calibration_refinement"]
        for row in calibration_rows:
            style = method_style(row["arm"])
            axis_a.scatter(
                row["calibration"],
                row["refinement"],
                marker=style.marker,
                s=34,
                facecolor=_marker_facecolour(row["arm"]),
                edgecolor=style.colour,
                linewidth=0.9,
                zorder=3,
            )
            axis_a.annotate(
                style.label,
                (row["calibration"], row["refinement"]),
                xytext=(4, 3),
                textcoords="offset points",
                color=style.colour,
                fontsize=preset.body_pt,
            )
        axis_a.margins(0.17)
        axis_a.set_xlabel("Calibration error  ← lower is better")
        axis_a.set_ylabel("Refinement  higher is better →")
        axis_a.set_title("Retrospective Hill evidence: descriptive", loc="left", fontsize=preset.body_pt)

        hill_rows = data["hill_containment"]
        axis_b.axvline(0, color=_INK, linewidth=0.8, zorder=0)
        for y_position, row in enumerate(hill_rows):
            if not row["n"]:
                axis_b.text(
                    0.015,
                    y_position,
                    "no non-empty\ncertificate",
                    color=_MUTED,
                    ha="left",
                    va="center",
                    fontsize=preset.body_pt,
                )
                continue
            effect, lo, hi = _containment_effect(row)
            colour = _containment_colour(row)
            interval = axis_b.hlines(y_position, lo, hi, color=colour, linewidth=1.4, zorder=2)
            interval.set_gid(f"hill-interval:{row['cell_id']}")
            point = axis_b.scatter(effect, y_position, color=colour, s=24, zorder=3)
            point.set_gid(f"hill:{row['cell_id']}")
            axis_b.text(hi + 0.012, y_position, f"{row['x']}/{row['n']}", va="center", fontsize=preset.body_pt)
        axis_b.set_xlim(*_effect_limits(hill_rows))
        axis_b.set_yticks(range(len(hill_rows)), [_hill_label(row) for row in hill_rows])
        axis_b.set_ylim(len(hill_rows) - 0.6, -0.6)
        axis_b.set_xlabel("Cross-fit containment − nominal")
        axis_b.set_title("Prospective Hill\nempties excluded", loc="left", fontsize=preset.body_pt)

        answer_rows = data["cross_family_answer_rate"]
        bars = axis_c.barh(range(len(answer_rows)), [row["answer_rate"] for row in answer_rows], color=_MUTED)
        for y_position, (bar, row) in enumerate(zip(bars, answer_rows, strict=True)):
            bar.set_gid(f"answer-rate:{row['family']}")
            axis_c.text(
                row["answer_rate"] + 0.015,
                y_position,
                f"{row['answered']}/{row['n_campaigns']}",
                va="center",
                fontsize=preset.body_pt,
            )
        axis_c.set_yticks(range(len(answer_rows)), [row["family"] for row in answer_rows])
        axis_c.invert_yaxis()
        axis_c.set_xlim(0, 1)
        axis_c.set_xlabel("Campaigns with any non-empty γ×τ certificate")
        axis_c.set_title(
            "Campaign answer rate (α=0.95)\n0 = declined to certify (not zero containment)",
            loc="left",
            fontsize=preset.body_pt,
        )

        conditional_rows = data["cross_family_conditional_containment"]
        axis_d.axvline(0, color=_INK, linewidth=0.8, zorder=0)
        for y_position, row in enumerate(conditional_rows):
            if not row["n"]:
                axis_d.text(
                    0.015,
                    y_position,
                    "declined\nto certify",
                    color=_MUTED,
                    ha="left",
                    va="center",
                    fontsize=preset.body_pt,
                )
                continue
            effect, lo, hi = _containment_effect(row)
            colour = _containment_colour(row)
            interval = axis_d.hlines(y_position, lo, hi, color=colour, linewidth=1.4, zorder=2)
            interval.set_gid(f"conditional-interval:{row['family']}")
            point = axis_d.scatter(effect, y_position, color=colour, s=24, zorder=3)
            point.set_gid(f"conditional:{row['family']}")
            axis_d.text(hi + 0.012, y_position, f"{row['x']}/{row['n']}", va="center", fontsize=preset.body_pt)
        axis_d.set_xlim(*_effect_limits(conditional_rows))
        axis_d.set_yticks(range(len(conditional_rows)), [row["family"] for row in conditional_rows])
        axis_d.set_ylim(len(conditional_rows) - 0.6, -0.6)
        axis_d.set_xlabel("Containment − nominal")
        axis_d.set_title("Conditional on answering", loc="left", fontsize=preset.body_pt)
        for axis in (axis_b, axis_d):
            _keep_ticks_within_view(axis)

    panel_data = {
        "A": {"rows": calibration_rows, "evidence": "retrospective Hill; descriptive"},
        "B": {
            "rows": hill_rows,
            "reference": 0.0,
            "interval": "Clopper-Pearson 95% exact",
            "empty_policy": "exclude from numerator and denominator",
        },
        "C": {
            "rows": answer_rows,
            "scope": "alpha=0.95 campaigns; any non-empty gamma-by-tau certificate",
            "zero_means": "declined to certify",
        },
        "D": {
            "rows": conditional_rows,
            "effect": "containment minus nominal",
            "interval": "Clopper-Pearson 95% exact",
            "conditioning": "non-empty certificate cell returned an answer",
        },
    }
    assert_no_prohibited_content(panel_data)
    alt_text = (
        "Retrospective Hill calibration and refinement are shown separately. Prospective Hill cross-fit "
        "containment uses exact intervals and non-empty denominators; cross-family answer rates distinguish "
        "declining to certify from containment conditional on answering."
    )
    return FigureBundle("fig4", figure, panel_data, alt_text)
