from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.style import get_preset


def test_figure1_defines_campaign_decisions_and_estimands():
    bundle = build_figure1(get_preset("portable"))

    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["stages"] == ["formulation", "wells", "assay", "model"]
    assert set(bundle.panel_data["B"]["branches"]) == {"point decision", "region decision"}
    assert "contains no performance result" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 3

    plt.close(bundle.figure)
