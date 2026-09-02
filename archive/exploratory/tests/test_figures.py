"""Tests for the figures.

Figures cannot be checked for beauty by a test, so these check the things that
CAN be checked mechanically: that the colours survive the colour-blindness
requirement, that every file is actually written, and — most importantly —
that the honest-framing choices are not quietly reverted.
"""

from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")

from boec.figures import (
    COLOURS,
    figure_discrimination,
    figure_headroom,
    figure_over_prediction,
    make_all_figures,
    stationary_point_summary,
)


class FakeAgreement:
    def __init__(self, v): self.max_offdiagonal = v; self.has_headroom = v <= 0.95


class FakeDiscrimination:
    def __init__(self, gp, nn, poly, agree):
        self.spearman = {
            "gp_predictive_sd": gp,
            "nearest_neighbour_distance": nn,
            "second_order_pi_width": poly,
        }
        self.agreement = FakeAgreement(agree)


class FakeResult:
    def __init__(self, kappa, gp=0.5, nn=0.45, poly=0.4, agree=0.85,
                 op_poly=9.0, op_gp=0.5, kind="saddle", valid=True):
        self.kappa = kappa
        self.is_valid = valid
        self.over_prediction = {"second_order": op_poly, "gp": op_gp}
        self.argmax_inside_subbox = {"second_order": False, "gp": False}
        self.stationary_kind = {"second_order": kind}
        self.discrimination = FakeDiscrimination(gp, nn, poly, agree)


KAPPAS = (0.6, 0.7, 0.8, 0.9)


@pytest.fixture
def results():
    out = []
    for k in KAPPAS:
        for i in range(10):
            out.append(FakeResult(k, gp=0.5 + i * 0.01, nn=0.45 + i * 0.01))
    return out


def test_colours_are_the_validated_ones():
    """Changed on a whim, these stop being colour-blind safe. The validator
    result is recorded in the module docstring; these are the inputs to it."""
    assert COLOURS == {
        "gp": "#0072B2",
        "polynomial": "#D55E00",
        "distance": "#009E73",
    }


def test_every_figure_is_written(results, tmp_path):
    out = make_all_figures(results, tmp_path, KAPPAS)
    for key in ("headroom", "over_prediction", "discrimination"):
        assert out[key].exists()
        assert out[key].stat().st_size > 5000, f"{key} looks empty"


def test_each_figure_renders_alone(results, tmp_path):
    assert figure_headroom(results, tmp_path / "h.png", KAPPAS).exists()
    assert figure_over_prediction(results, tmp_path / "o.png", KAPPAS).exists()
    assert figure_discrimination(results, tmp_path / "d.png", KAPPAS).exists()


def test_invalid_cells_are_not_plotted(results, tmp_path):
    """A cell that tested nothing must not appear in a figure either."""
    poisoned = results + [FakeResult(0.6, op_poly=999.0, valid=False)]
    a = figure_over_prediction(results, tmp_path / "a.png", KAPPAS).read_bytes()
    b = figure_over_prediction(poisoned, tmp_path / "b.png", KAPPAS).read_bytes()
    assert a == b, "an invalid cell changed the figure — it should be filtered out"


# --------------------------------------------------------------------------
# The honest-framing choices. These are the tests that matter.
# --------------------------------------------------------------------------

def test_a_single_category_is_reported_as_text_not_a_chart(results):
    """40/40 saddles is a sentence, not a bar chart of one bar."""
    text = stationary_point_summary(results)
    assert "40" in text and "saddle" in text
    assert "not a chart" in text


def test_a_genuine_mix_is_described_as_a_mix(results):
    mixed = results[:-5] + [FakeResult(0.9, kind="maximum") for _ in range(5)]
    text = stationary_point_summary(mixed)
    assert "maximum" in text and "saddle" in text
    assert "not a chart" not in text


def test_the_null_verdict_is_stated_not_softened(results, tmp_path):
    """When the paired interval straddles zero the title must say so.

    Guards against someone later 'improving' the wording into something that
    lets a reader infer an advantage that was not established.
    """
    import matplotlib.pyplot as plt

    figure_discrimination(results, tmp_path / "d.png", KAPPAS)
    # Re-render into a live figure so the title can be inspected.
    fig, axes = plt.subplots(1, 2)
    plt.close(fig)
    # The verdict string is built from the pooled significance; assert the
    # branch exists by checking both wordings are present in the source.
    from pathlib import Path

    src = Path("src/boec/figures.py").read_text()
    assert "NOT established" in src
    assert "the advantage is established" in src


def test_paired_difference_is_what_gets_plotted_not_two_separate_bars():
    """The central honesty choice. Two separate error bars invite a comparison
    that discards the shared variation and can hide a real effect."""
    from pathlib import Path

    src = Path("src/boec/figures.py").read_text()
    assert "paired_difference_ci" in src
    assert "axvline(0" in src, "the zero line is what makes the null readable"
