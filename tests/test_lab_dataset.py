"""The assembled derived tables, the plate workbook, and the separation of metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from boec.lab.dataset import (
    CONTROL_STEMS,
    FLOW_METRIC,
    coating_flow_campaign,
    coded_dose,
    find_control,
    flow_positivity_frame,
    is_control,
    protocol_frame,
)
from boec.lab.imaging import METRIC_NAME as COVERAGE_METRIC
from boec.lab.plate import read_plate

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
DERIVED = LAB / "derived"
PANEL = LAB / "flow" / "2026-08-06" / "Exp_20260806_cd31-cd140a"
EXP1 = LAB / "flow" / "2026-08-06" / "Exp_20260806_1"

pytestmark = pytest.mark.skipif(not LAB.exists(), reason="data/lab not present")


def test_coded_dose_maps_this_box_not_the_hall_ogle_cube():
    """0.5 ug/mL is the floor of THIS experiment, so it codes to 0, not to 0.025."""
    assert coded_dose(0.5) == pytest.approx(0.0)
    assert coded_dose(20.0) == pytest.approx(1.0)
    assert coded_dose(1.0) == pytest.approx(0.5 / 19.5)


def test_flow_metric_names_the_instrument_that_actually_acquired_the_data():
    assert FLOW_METRIC[0] == "CD31_pct_flow"
    assert "cytoflexlx" in FLOW_METRIC[2]
    assert "novocyte" not in FLOW_METRIC[2].lower()


def test_flow_and_coverage_metrics_are_different_numbers():
    assert FLOW_METRIC[0] != COVERAGE_METRIC


def test_controls_are_recognised_and_never_become_conditions():
    assert is_control(PANEL / "us.fcs")
    assert not is_control(PANEL / "f5.fcs")
    assert {"us", "iso", "before"} <= CONTROL_STEMS


def test_control_selection_is_recorded_because_the_tie_break_is_arbitrary():
    """Exp_20260806_1 holds US-old and US-new; the choice must not be invisible."""
    chosen = find_control(EXP1)
    assert chosen is not None and chosen.name in {"US-new.fcs", "US-old.fcs"}
    assert find_control(PANEL).name == "us.fcs"


def test_a_directory_with_no_unstained_yields_no_percentages(tmp_path):
    assert find_control(tmp_path) is None


@pytest.mark.slow
def test_every_fcs_file_gets_a_disposition():
    """The 'read everything' guarantee: 52 files, zero silently skipped."""
    from boec.lab.gating import resolve_cd31_channel

    ident = resolve_cd31_channel(LAB / "flow" / "2026-07-28" / "Exp_20260728_1")
    frame = flow_positivity_frame(LAB, ident.cd31_detector, "Y585-A")
    assert len(frame) == 52
    assert frame["status"].isna().sum() == 0
    counts = frame["status"].value_counts().to_dict()
    assert counts["aborted_zero_events"] == 8
    assert counts["gated_candidate"] == 34
    assert counts["control"] == 10


@pytest.mark.slow
def test_the_twelve_coating_rows_carry_candidate_not_final_values():
    from boec.lab.gating import resolve_cd31_channel

    ident = resolve_cd31_channel(LAB / "flow" / "2026-07-28" / "Exp_20260728_1")
    frame = flow_positivity_frame(LAB, ident.cd31_detector, "Y585-A")
    campaign = coating_flow_campaign(frame)
    assert len(campaign) == 12
    assert set(campaign["coating"]) == {"fibronectin", "vitronectin"}
    assert (campaign["status"] == "awaiting_human_signoff").all()
    assert "y_candidate" in campaign.columns and "y" not in campaign.columns
    assert (campaign["n_replicates"] == 1).all()
    assert campaign["y_spread_pp"].min() > 0


def test_protocol_confounding_is_reported_for_v3():
    _wells, confounding = protocol_frame(LAB)
    v3 = confounding["IPSC分化EC-3.docx"]
    assert ["chir_second_dose_day", "terminal_medium"] in v3
    assert not any("bmp4_ng_ml" in pair for pair in v3)


def test_plate_is_identified_as_a_bca_plate_with_an_unlabelled_layout():
    xlsx = next((LAB / "plate-reader").glob("*.xlsx"))
    plate = read_plate(xlsx)
    assert plate.instrument == "Multiskan SkyHigh"
    assert plate.wavelength_nm == 562
    assert plate.n_wells == 96
    assert plate.layout_labelled is False
    assert plate.looks_like_bca
    assert plate.standard_curve.is_monotonic_duplicate_series


def test_plate_layout_headers_are_not_mistaken_for_labels():
    """Row 1 holds column numbers and column A holds row letters on every plate."""
    xlsx = next((LAB / "plate-reader").glob("*.xlsx"))
    assert read_plate(xlsx).layout_labelled is False


@pytest.mark.skipif(not (DERIVED / "RUN.json").exists(), reason="pipeline not run yet")
def test_run_summary_records_the_promotion_rule_and_no_checksum_drift():
    import json

    run = json.loads((DERIVED / "RUN.json").read_text())
    assert run["checksums_mismatched"] == []
    assert run["checksums_verified"] == 300
    assert run["files_indexed"] == 305
    assert run["cd31_detector"] == "B525-A"
    assert "human act" in run["promotion_rule"]


@pytest.mark.skipif(not (DERIVED / "RUN.json").exists(), reason="pipeline not run yet")
def test_derived_campaign_files_never_contain_a_column_named_y():
    """A column called `y` is what an optimizer reads. These tables must not offer one."""
    import pandas as pd

    for name in (
        "candidate_campaign_coating_flow.csv",
        "candidate_campaign_coating_morphology.csv",
    ):
        frame = pd.read_csv(DERIVED / name)
        assert "y" not in frame.columns, name
        assert "y_candidate" in frame.columns, name
