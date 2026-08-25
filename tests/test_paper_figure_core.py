from __future__ import annotations

import json

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from boec.paper_figures.core import FigureBundle, load_json
from boec.paper_figures.style import METHOD_STYLES, get_preset, panel_label


def test_required_method_families_have_redundant_encodings():
    assert METHOD_STYLES["spade_cf_m0"].colour == "#009E73"
    assert METHOD_STYLES["qlognei"].colour == "#0072B2"
    assert METHOD_STYLES["doe"].colour == "#D55E00"
    assert METHOD_STYLES["sobol"].colour == "#6B7280"
    assert len({METHOD_STYLES[k].marker for k in ("spade_cf_m0", "qlognei", "doe", "sobol")}) == 4


@pytest.mark.parametrize(
    ("name", "width_mm"),
    [("portable", 178.0), ("rsc", 171.0), ("nature", 183.0)],
)
def test_double_column_widths_are_physical(name, width_mm):
    assert get_preset(name).width_mm == width_mm


def test_panel_label_is_lowercase_and_bold():
    fig, ax = plt.subplots()
    artist = panel_label(ax, "a")
    assert artist.get_text() == "a"
    assert artist.get_fontweight() == "bold"
    plt.close(fig)


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError, match="top-level JSON object"):
        load_json(path)


def test_figure_bundle_requires_all_metadata():
    fig, _ = plt.subplots()
    bundle = FigureBundle("fig1", fig, {"A": {"claim": "definition"}}, "A benchmark schematic.")
    assert bundle.figure_id == "fig1"
    plt.close(fig)
