"""Reliability and non-vacuity audit for the paper's Figure 4."""

from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt

from .core import FigureBundle, assert_no_prohibited_content
from .style import VenuePreset, apply_axis_style, method_style, panel_label


_CONTAINMENT_COLOUR = "#009E73"
_UNDERCOVERAGE_WARNING = "#B2182B"
_INK = "#243746"
_MUTED = "#6B7280"


def _marker_facecolour(arm: str) -> str:
    style = method_style(arm)
    return "white" if style.fill == "none" else style.colour


def _containment_effect(row: dict) -> tuple[float, float, float]:
    return (
        row["proportion"] - row["alpha"],
        row["ci_lo"] - row["alpha"],
        row["ci_hi"] - row["alpha"],
    )


def _undercoverage(row: dict) -> bool:
    return row["ci_hi"] < row["alpha"]


def _containment_colour(row: dict) -> str:
    return _UNDERCOVERAGE_WARNING if _undercoverage(row) else _CONTAINMENT_COLOUR


def _effect_limits(rows: list[dict]) -> tuple[float, float]:
    intervals = [_containment_effect(row) for row in rows if row["n"]]
    lower = min([0.0, *(interval[1] for interval in intervals)])
    upper = max([0.0, *(interval[2] for interval in intervals)])
    return lower - 0.04, upper + 0.16


def _keep_ticks_within_view(axis) -> None:
    lower, upper = sorted(axis.get_xlim())
    axis.set_xticks([tick for tick in axis.get_xticks() if lower <= tick <= upper])


def _hill_label(row: dict) -> str:
    condition = row["condition"].replace("hill-d", "d=").replace("-s", "; σ=")
    return f"{condition}; γ={row['gamma']:g}; α={row['alpha']:g}"


def _draw_containment_forest(
    axis,
    rows: list[dict],
    *,
    id_prefix: str,
    labels: list[str],
    preset: VenuePreset,
    declined_text: str,
) -> None:
    """Draw a zero-centred exact-interval forest plus a right status gutter."""
    axis.axvline(0, color=_INK, linewidth=0.8, zorder=0)
    limits = _effect_limits(rows)
    axis.set_xlim(*limits)
    for y_position, row in enumerate(rows):
        if not row["n"]:
            axis.text(
                0.04,
                y_position,
                declined_text,
                color=_MUTED,
                ha="left",
                va="center",
                fontsize=preset.body_pt,
            )
            continue
        effect, lo, hi = _containment_effect(row)
        colour = _containment_colour(row)
        interval = axis.hlines(y_position, lo, hi, color=colour, linewidth=0.9, zorder=2)
        interval.set_gid(f"{id_prefix}-interval:{row.get('cell_id', row.get('family'))}")
        point = axis.scatter(
            effect,
            y_position,
            color=colour,
            edgecolor=_INK,
            linewidth=0.5,
            marker="v" if _undercoverage(row) else "o",
            s=30,
            zorder=3,
        )
        point.set_gid(f"{id_prefix}:{row.get('cell_id', row.get('family'))}")
        axis.text(hi + 0.012, y_position, f"{row['x']}/{row['n']}", va="center", fontsize=preset.body_pt, color=_INK)
    axis.set_yticks(range(len(rows)), labels)
    # A declined row carries a two-line label centred on its baseline. On the
    # last row half that label falls below the default 0.6-row margin and
    # crosses the bottom spine, so reserve a full row of space beneath it.
    trailing_declined = bool(rows) and not rows[-1]["n"]
    axis.set_ylim(len(rows) - (0.1 if trailing_declined else 0.6), -0.6)
    _keep_ticks_within_view(axis)


def build_figure4(data: dict, preset: VenuePreset) -> FigureBundle:
    """Build the retrospective calibration and prospective certification audit."""
    assert_no_prohibited_content(data)
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        height_mm = 168 if preset.name == "plos" else 154
        figure = plt.figure(figsize=preset.figsize(height_mm), constrained_layout=True)
        grid = figure.add_gridspec(2, 2, width_ratios=(0.95, 1.05), hspace=0.18, wspace=0.12)
        axis_a = figure.add_subplot(grid[0, 0])
        axis_b = figure.add_subplot(grid[0, 1])
        axis_c = figure.add_subplot(grid[1, 0])
        axis_d = figure.add_subplot(grid[1, 1])
        for axis, label in zip((axis_a, axis_b, axis_c, axis_d), "abcd", strict=True):
            apply_axis_style(axis, preset)
            label_text = panel_label(axis, label, preset)
            label_text.set_position((-0.17, 1.04))

        calibration_rows = data["calibration_refinement"]
        axis_a.set_axis_off()
        axis_a.set_title("Retrospective Hill evidence: descriptive", loc="left", fontsize=preset.body_pt)
        metric_axes = (
            axis_a.inset_axes((0.02, 0.14, 0.46, 0.72)),
            axis_a.inset_axes((0.54, 0.14, 0.44, 0.72)),
        )
        for metric_axis, metric, title in zip(
            metric_axes,
            ("calibration", "refinement"),
            ("Calibration\nerror ↓", "Refinement ↑"),
            strict=True,
        ):
            apply_axis_style(metric_axis, preset)
            for y_position, row in enumerate(calibration_rows):
                style = method_style(row["arm"])
                metric_axis.scatter(
                    row[metric],
                    y_position,
                    marker=style.marker,
                    s=30,
                    facecolor=_marker_facecolour(row["arm"]),
                    edgecolor=style.colour,
                    linewidth=0.8,
                    zorder=3,
                )
            metric_axis.set_yticks(
                range(len(calibration_rows)),
                [method_style(row["arm"]).label for row in calibration_rows] if metric == "calibration" else [],
            )
            metric_axis.set_ylim(len(calibration_rows) - 0.6, -0.6)
            metric_axis.set_title(title, loc="left", fontsize=preset.body_pt)
            metric_axis.tick_params(axis="x", labelsize=preset.body_pt)
            _keep_ticks_within_view(metric_axis)
            if metric == "refinement":
                metric_axis.set_xticks((0, 0.01))

        hill_rows = data["hill_containment"]
        _draw_containment_forest(
            axis_b,
            hill_rows,
            id_prefix="hill",
            labels=[_hill_label(row) for row in hill_rows],
            preset=preset,
            declined_text="no non-empty\ncertificate",
        )
        axis_b.set_xlabel("Model-check pass fraction − α", fontsize=preset.body_pt)
        axis_b.set_title("Hill posterior check\nnon-empty denominators", loc="left", fontsize=preset.body_pt)

        answer_rows = data["cross_family_answer_rate"]
        bars = axis_c.barh(
            range(len(answer_rows)),
            [row["answer_rate"] for row in answer_rows],
            color="#D6DEE5",
            edgecolor=_INK,
            linewidth=0.6,
        )
        for y_position, (bar, row) in enumerate(zip(bars, answer_rows, strict=True)):
            bar.set_gid(f"answer-rate:{row['family']}")
            axis_c.text(
                row["answer_rate"] + 0.025,
                y_position,
                f"{row['answered']}/{row['n_campaigns']}",
                va="center",
                fontsize=preset.body_pt,
                color=_INK,
            )
        axis_c.set_yticks(range(len(answer_rows)), [row["family"] for row in answer_rows])
        axis_c.invert_yaxis()
        axis_c.set_xlim(0, 1.16)
        axis_c.set_xticks((0, 0.25, 0.50, 0.75, 1.00))
        axis_c.set_xlabel("Campaigns with any non-empty γ×τ certificate", fontsize=preset.body_pt)
        axis_c.set_title(
            "Campaign answer rate (α=0.95)\n0 = declined to certify\nnot zero containment",
            loc="left",
            fontsize=preset.body_pt,
        )

        conditional_rows = data["cross_family_conditional_containment"]
        axis_d.axvline(0, color=_INK, linewidth=0.8, zorder=0)
        axis_d.set(xlim=(-0.4, 0.5), ylim=(len(conditional_rows) - 0.6, -0.6))
        for y_position, row in enumerate(conditional_rows):
            if not row["n"]:
                axis_d.text(0.02, y_position, "declined\nto certify", va="center", fontsize=preset.body_pt, color=_MUTED)
                continue
            point = axis_d.scatter(row["proportion"] - row["alpha"], y_position,
                                   color=_INK, s=30, zorder=3)
            point.set_gid(f"conditional:{row['family']}")
            axis_d.text(0.48, y_position, f"{row['x']}/{row['n']}",
                        ha="right", va="center", fontsize=preset.body_pt, color=_INK)
        axis_d.set_yticks(range(len(conditional_rows)), [row["family"] for row in conditional_rows])
        axis_d.set_xticks((-0.4, -0.2, 0, 0.2, 0.4))
        axis_d.set_xlabel("Containment − nominal", fontsize=preset.body_pt)
        axis_d.set_title("Retrospective containment\nα=0.80; repeated cells\nDescriptive only", loc="left", fontsize=preset.body_pt)

    panel_data = {
        "A": {
            "rows": calibration_rows,
            "evidence": "retrospective Hill; descriptive",
            "display": "aligned dot strips",
        },
        "B": {
            "rows": hill_rows,
            "reference": 0.0,
            "interval": "Original Clopper-Pearson 95%; no instance-cluster adjustment",
            "estimand": "fraction whose held-out posterior containment probability meets alpha; not empirical oracle containment",
            "empty_policy": "exclude from numerator and denominator",
            "status_gutter": True,
        },
        "C": {
            "rows": answer_rows,
            "scope": "alpha=0.95 campaigns; any non-empty gamma-by-tau certificate",
            "zero_means": "declined to certify",
        },
        "D": {
            "rows": conditional_rows,
            "effect": "containment minus nominal",
            "interval": "not computed; repeated cells within campaigns",
            "conditioning": "non-empty certificate cell returned an answer",
            "warning_encoding": "none; descriptive proportions only",
        },
    }
    assert_no_prohibited_content(panel_data)
    alt_text = (
        "Retrospective Hill calibration and refinement are shown as aligned dot strips. Prospective Hill "
        "model-check pass fractions use original binomial intervals and non-empty denominators, not oracle containment. Cross-family answer rates "
        "distinguish declining to certify from containment conditional on answering. Retrospective pooled "
        "certificate-cell counts are descriptive because cells repeat within campaigns."
    )
    caption = (
        "Figure 4 | Calibration, posterior checks, and empirical containment are different outcomes. (a) Retrospective "
        "Hill calibration error and refinement are descriptive summaries (n=1,200 cells per method). "
        "(b) Prospective Hill model-check pass fraction minus alpha: posterior self-consistency, not empirical containment. "
        "Original 95% binomial intervals do not adjust for repeated Hill instances. Empty certificates are excluded "
        "from each denominator. A downward triangle marks an unadjusted interval below alpha, not a Holm-adjusted decision. "
        "Stored gamma labels do not change the latent certificates. (c) In the separate retrospective "
        "five-family study at α=0.95, campaigns returning "
        "any non-empty certificate were 0/50 for Ackley, 11/50 for Hartmann6, 50/50 for Hill, 49/50 for Levy "
        "and 50/50 for Rosenbrock; zero denotes refusal to certify, not zero containment. (d) Conditional "
        "containment at α=0.80 pools non-empty γ×τ cells within those campaigns. These dependent cell counts "
        "are descriptive, with no binomial intervals or cross-family validity test. Panels c and d use different assurance levels."
    )
    long_description = (
        "Panel a separates calibration error from refinement so the two reliability properties are not collapsed "
        "into one score. Panel b reports six prospective Hill posterior-check cells, not oracle containment; one α=0.95, σ=0.25 cell returns no non-empty "
        "certificate and is explicitly marked as such. Panel c shows answer counts of 0, 11, 50, 49 and 50 out "
        "of 50 campaigns for Ackley, Hartmann6, Hill, Levy and Rosenbrock. Panel d conditions containment on an "
        "answer at α=0.80: Ackley declines to certify; Hartmann6 contains 16/32; Hill contains 802/808, "
        "Levy 697/747 and Rosenbrock 778/845. These are dependent cell counts without inferential intervals."
    )
    return FigureBundle("fig4", figure, panel_data, alt_text, caption, long_description)
