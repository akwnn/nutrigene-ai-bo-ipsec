"""FCS reading against the real CytoFLEX LX drop.

These tests double as the record of what the instrument actually wrote, which is how
the NovoCyte misattribution in README.md/BO-PURPOSE.md was caught.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from boec.lab.fcs import (
    LOGICLE_T,
    detector_index,
    logicle,
    parse_spillover,
    read_events,
    read_summary,
)

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
FLOW = LAB / "flow"
PANEL = FLOW / "2026-08-06" / "Exp_20260806_cd31-cd140a"
ABORTED = FLOW / "2026-08-06" / "Exp_20260806_2"

pytestmark = pytest.mark.skipif(not FLOW.exists(), reason="data/lab/flow not present")


@pytest.fixture(scope="module")
def all_summaries():
    return [read_summary(p) for p in sorted(FLOW.rglob("*.fcs"))]


def test_every_fcs_parses(all_summaries):
    assert len(all_summaries) == 52


def test_every_acquisition_is_a_cytoflex_lx_not_a_novocyte(all_summaries):
    """The drop was documented as NovoCyte. All 52 files say otherwise.

    The metric identity string is supposed to be the immutable name of the
    measurement, so an instrument error there is not cosmetic.
    """
    cyts = {s.cytometer for s in all_summaries}
    assert cyts == {"CytoFLEX LX"}, cyts
    assert {s.serial for s in all_summaries} == {"BG17015"}


def test_panel_is_uniform_38_parameters(all_summaries):
    assert {s.parameters for s in all_summaries} == {38}
    assert {len(s.fluorescence_detectors) for s in all_summaries} == {16}


def test_the_eight_exp2_tubes_are_the_only_zero_event_files(all_summaries):
    aborted = sorted(s.path for s in all_summaries if s.aborted)
    on_disk = sorted(p.name for p in ABORTED.glob("*.fcs"))
    assert aborted == on_disk
    assert len(aborted) == 8


def test_no_compensation_was_applied_at_acquisition(all_summaries):
    """$SPILLOVER is the identity on every file.

    This is a scientific caveat, not a parsing detail: an uncompensated two-colour
    panel inflates double positives, and it explains why the adjacent blue detector
    B610-A trails B525-A in the channel-identity scan.
    """
    stained = [s for s in all_summaries if s.spillover_is_identity is not None]
    assert stained, "no file carried a $SPILLOVER keyword"
    assert all(s.spillover_is_identity for s in stained)
    assert {s.spillover_n for s in stained} == {32}


def test_event_counts_match_the_conditions_csv():
    import csv

    cond = LAB / "bo_primary_conditions.csv"
    if not cond.exists():
        pytest.skip("conditions CSV not present")
    with cond.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            summary = read_summary(LAB / row["file"])
            assert summary.events == int(row["events"]), row["file"]


def test_reading_events_of_an_aborted_file_raises_rather_than_returning_empty():
    with pytest.raises(ValueError, match="0 events"):
        read_events(ABORTED / "well 1.fcs")


def test_events_shape_matches_summary():
    summary = read_summary(PANEL / "f5.fcs")
    events, labels = read_events(PANEL / "f5.fcs")
    assert events.shape == (summary.events, summary.parameters)
    assert labels == list(summary.detectors)


def test_spillover_parses_to_identity():
    import flowio

    fd = flowio.FlowData(str(PANEL / "f5.fcs"), only_text=True)
    matrix, labels = parse_spillover(fd.text)
    assert matrix.shape == (32, 32)
    assert len(labels) == 32
    assert np.allclose(matrix, np.eye(32))


def test_detector_index_finds_the_two_panel_channels():
    _, labels = read_events(PANEL / "us.fcs")
    assert labels[detector_index(labels, "B525-A")] == "B525-A"
    assert labels[detector_index(labels, "Y585-A")] == "Y585-A"
    with pytest.raises(KeyError):
        detector_index(labels, "NOT-A-DETECTOR")


def test_logicle_t_is_the_instrument_range_not_the_flowutils_default():
    """$PnR is 2^24 on this cytometer. flowutils defaults to 262144 (2^18).

    Using the default folds the top ~6 decades of a bright FITC sample into the
    asymptote, which moves any gate placed on it.
    """
    assert LOGICLE_T == 16_777_216.0
    import flowio

    fd = flowio.FlowData(str(PANEL / "f5.fcs"), only_text=True)
    idx = list(fd.pns_labels).index("B525-A") + 1
    assert fd.channels[idx]["pnr"] == LOGICLE_T


def test_logicle_is_monotonic_and_bounded():
    events, labels = read_events(PANEL / "f5.fcs")
    i = detector_index(labels, "B525-A")
    sub = events[:2000]
    out = logicle(sub, [i])
    col_in, col_out = sub[:, i], out[:, i]
    order = np.argsort(col_in)
    assert np.all(np.diff(col_out[order]) >= -1e-9), "logicle must preserve order"
    assert np.isfinite(col_out).all()
    assert col_out.min() >= 0.0 - 1e-9 and col_out.max() <= 1.0 + 1e-9
