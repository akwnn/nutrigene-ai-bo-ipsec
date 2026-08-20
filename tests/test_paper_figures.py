"""Tests for the publication figures.

These check that the figures are written, that they are derived from the
committed JSON, and that Figure 1 still shows the rank reversal it exists to
show. They do not judge layout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from boec.paper_figures import (
    COLOURS,
    PNG_DPI,
    figure_cost,
    figure_saddle,
    figure_terminal_rules,
    hit_series,
    locator_means,
    make_paper_figures,
    saddle_stats,
    winner_reverses,
)


def test_colours_are_fixed():
    assert COLOURS["doe"] == "#D55E00"
    assert COLOURS["qlogei"] == "#0072B2"
    assert COLOURS["qlognei"] == "#009E73"


def test_primary_measured_means_match_the_manuscript():
    m = locator_means(6, 0.25)
    assert round(m["doe"]["measured"][0], 4) == 0.0958
    assert round(m["qlogei"]["measured"][0], 4) == 0.1553
    assert round(m["qlognei"]["measured"][0], 4) == 0.1532
    assert round(m["doe"]["measured"][0] - m["qlogei"]["measured"][0], 4) == -0.0595


def test_inregion_gp_uses_q64_when_present_else_q34_fallback():
    import json

    from boec.paper_figures import ROOT

    m = locator_means(6, 0.25)
    assert m["qlogei"]["unconstrained"] is not None
    assert m["qlogei"]["inregion"] is not None
    q64 = ROOT / "results" / "q64-gp-inregion.json"
    if q64.exists():
        data = json.loads(q64.read_text())
        qlogei = [
            r for r in data["rows"]
            if r["dim"] == 6 and abs(float(r["sigma"]) - 0.25) < 1e-12 and r["acq"] == "qlogei"
        ]
        if len({r["instance"] for r in qlogei}) >= 25:
            return
    assert m["qlogei"]["unconstrained"][0] == m["qlogei"]["inregion"][0]
    assert round(m["qlogei"]["inregion"][0], 4) == 0.1232
    assert round(m["doe"]["inregion"][0], 4) == 0.1169


def test_qlognei_model_recommendation_uses_q64_when_complete():
    import json

    from boec.paper_figures import ROOT

    m = locator_means(6, 0.25)
    q64 = ROOT / "results" / "q64-gp-inregion.json"
    if q64.exists():
        data = json.loads(q64.read_text())
        qlognei = [
            r for r in data["rows"]
            if r["dim"] == 6 and abs(float(r["sigma"]) - 0.25) < 1e-12 and r["acq"] == "qlognei"
        ]
        if len({r["instance"] for r in qlognei}) >= 25:
            assert m["qlognei"]["unconstrained"] is not None
            assert m["qlognei"]["inregion"] is not None
            return
    assert m["qlognei"]["unconstrained"] is None
    assert m["qlognei"]["inregion"] is None


def test_q62_primary_cell_matches_locked_json():
    from boec.paper_figures import q62_locked_payload

    data = q62_locked_payload()
    assert data is not None and data.get("smoke") is False
    s = next(x for x in data["summary"] if abs(float(x["sigma"]) - 0.25) < 1e-12)
    assert s["n"] == 25
    assert round(s["turbo_measured"], 4) == 0.1538
    assert round(s["stored_qlognei"], 4) == 0.1532
    assert round(s["stored_doe"], 4) == 0.0958
    assert round(s["doe_minus_turbo"]["mean"], 4) == -0.0580
    assert s["doe_minus_turbo"]["hi"] < 0
    assert s["turbo_minus_qlognei"]["lo"] < 0 < s["turbo_minus_qlognei"]["hi"]
    assert data["collapse_rate"] == 0.0


def test_q62_n200_arrival_matches_locked_json():
    import json

    from boec.paper_figures import ROOT

    p = ROOT / "results" / "q62-turbo-n200.json"
    data = json.loads(p.read_text())
    assert data.get("smoke") is False
    assert data["budget"] == 200
    by = {float(s["sigma"]): s for s in data["summary"]}
    assert by[0.25]["hit_regret_0_10_both_seeds"] == 11
    assert by[0.10]["hit_regret_0_10_both_seeds"] == 25
    assert by[0.25]["doe_minus_turbo"] is None
    assert by[0.25]["q56_rule_a_0_10"]["hits_doe_ascent"] == 8
    assert by[0.10]["q56_rule_a_0_10"]["hits_doe_ascent"] == 16
    assert round(by[0.25]["turbo_measured"], 4) == 0.1267
    assert round(by[0.10]["turbo_measured"], 4) == 0.0492


def test_winner_reverses_where_the_manuscript_claims_it():
    # Six factors at lower noise does not reverse: qLogEI is already slightly
    # ahead on the measured argmax, and further ahead unconstrained.
    assert winner_reverses() == 3


def test_saddle_count_and_primary_gap():
    s = saddle_stats()
    assert s["n"] == 200
    assert s["n_saddle"] == 200
    assert round(s["gap"], 4) == 0.2995
    assert s["gap_lo"] > 0.27


def test_hit_curves_keep_failures_in_the_denominator():
    high = hit_series(0.25)
    low = hit_series(0.10)
    assert high["qlogei"][-1][1] == pytest.approx(14 / 25)
    assert high["ascent"][-1][1] == pytest.approx(8 / 25)
    assert low["qlogei"][-1][1] == pytest.approx(24 / 25)
    assert low["ascent"][-1][1] == pytest.approx(16 / 25)
    assert low["doe"][-1][1] == pytest.approx(13 / 25)


def test_each_figure_writes_pdf_and_png(tmp_path: Path):
    from PIL import Image

    for fn, stem in (
        (figure_terminal_rules, "fig1"),
        (figure_cost, "fig2"),
        (figure_saddle, "fig3"),
    ):
        out = fn(tmp_path / stem)
        assert out["pdf"].exists() and out["png"].exists()
        assert out["pdf"].stat().st_size > 8_000
        assert out["png"].stat().st_size > 20_000
        image = Image.open(out["png"])
        assert image.size[0] >= 4_800, image.size
        stored_dpi = image.info.get("dpi", (0, 0))[0]
        assert stored_dpi >= PNG_DPI - 1


def test_make_paper_figures_writes_core_stems(tmp_path: Path):
    paths = make_paper_figures(tmp_path)
    assert {"fig1", "fig2", "fig3", "fig4"} <= set(paths)
    for pair in paths.values():
        assert pair["pdf"].exists()
        assert pair["png"].exists()


def test_q62_smoke_json_is_not_treated_as_locked():
    import json

    from boec.paper_figures import ROOT, q62_locked_payload

    p = ROOT / "results" / "q62-turbo.json"
    if not p.exists():
        assert q62_locked_payload() is None
        return
    data = json.loads(p.read_text())
    if data.get("smoke"):
        assert q62_locked_payload() is None
    else:
        locked = q62_locked_payload()
        assert locked is not None
        assert len({r["instance"] for r in locked["rows"]}) >= 25


def test_turbo_figure_uses_only_the_supplied_payload(tmp_path: Path):
    from PIL import Image

    from boec.paper_figures import figure_turbo

    payload = {
        "smoke": False,
        "budget": 48,
        "rows": [{"instance": f"i{k}"} for k in range(25)],
        "summary": [
            dict(sigma=0.25, stored_doe=0.10, stored_qlognei=0.15, turbo_measured=0.14),
            dict(sigma=0.10, stored_doe=0.06, stored_qlognei=0.08, turbo_measured=0.07),
        ],
    }
    out = figure_turbo(tmp_path / "fig4-turbo", payload=payload)
    assert out["pdf"].exists() and out["png"].exists()
    image = Image.open(out["png"])
    assert image.size[0] >= 2000
