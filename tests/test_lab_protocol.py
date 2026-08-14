"""The well -> condition map recovered from the protocol .docx files.

BO-PURPOSE.md blocks 83 files on "a well map exists nowhere in the repo". It exists;
it was inside the docx tables. These tests pin what it says, including the part that
limits what a campaign built on it may claim.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from boec.lab.protocol import (
    confounded_factor_pairs,
    factor_table,
    parse_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / "data" / "lab" / "raw" / "protocols"
V2, V3 = PROTOCOLS / "IPSC分化EC-2.docx", PROTOCOLS / "IPSC分化EC-3.docx"

pytestmark = pytest.mark.skipif(not PROTOCOLS.exists(), reason="protocols not present")


@pytest.fixture(scope="module")
def v3():
    return parse_protocol(V3)


@pytest.fixture(scope="module")
def v2():
    return parse_protocol(V2)


def test_v3_has_five_running_wells_and_well6_never_ran(v3):
    assert [w.well for w in v3.running_wells] == ["Well 1", "Well 2", "Well 3", "Well 4", "Well 5"]
    well6 = v3.well("Well 6")
    assert well6 is not None and not any(e.active for e in well6.entries)


def test_cell_paragraphs_are_separated_not_concatenated(v3):
    """A naive join produces 'CHIR 6μMKODMEM' and then the medium never parses."""
    day1 = [e for e in v3.well("Well 1").entries if e.day == 1][0]
    assert "CHIR" in day1.raw and "KODMEM" in day1.raw
    assert "μMKODMEM" not in day1.raw
    assert day1.chir_uM == 6.0
    assert day1.medium == "kodmem"


def test_v3_bmp4_split_is_the_one_clean_contrast(v3):
    rows = {r["well"]: r for r in factor_table(v3)}
    assert rows["Well 1"]["bmp4_ng_ml"] == 0.0
    assert rows["Well 2"]["bmp4_ng_ml"] == 0.0
    assert rows["Well 3"]["bmp4_ng_ml"] == 25.0
    assert rows["Well 4"]["bmp4_ng_ml"] == 25.0
    assert rows["Well 5"]["bmp4_ng_ml"] == 25.0
    # Wells 1/3 and 2/4 differ in BMP4 and nothing else.
    for a, b in (("Well 1", "Well 3"), ("Well 2", "Well 4")):
        for key in ("chir_schedule", "terminal_medium", "passaged"):
            assert rows[a][key] == rows[b][key], key


def test_chir_timing_medium_and_passaging_are_mutually_confounded(v3):
    """The finding that limits any BO campaign on these five wells.

    Every Day-2 well went to 10%FBS+EGM2 and was passaged; every Day-3 well stayed on
    EC induction and was not. Those three factors cannot be separated by this design.
    """
    conf = confounded_factor_pairs(
        factor_table(v3), ["chir_second_dose_day", "bmp4_ng_ml", "terminal_medium", "passaged"]
    )
    assert ("chir_second_dose_day", "terminal_medium") in conf
    assert ("terminal_medium", "passaged") in conf
    # BMP4 is the factor that is NOT tangled with the others.
    assert not any("bmp4_ng_ml" in pair for pair in conf)


def test_v2_is_the_experiment_named_3_1(v2):
    """Explains the orphan `3-1.fcs` in Exp_20260806_1.

    The v2 document titles itself "3-1"; its Well 3 and T75 were still running on
    06/08/26, the day Exp_20260806_1 was acquired.
    """
    assert "3-1" in v2.title
    assert v2.well("Well 3").active_on(date(2026, 8, 6))
    assert v2.well("T75").active_on(date(2026, 8, 6))


def test_v3_wells_were_all_running_on_the_flow_acquisition_date(v3):
    """Exp_20260806_1 is dated 06-Aug-2026, which is v3 Day 11 -- the day before sort."""
    for w in v3.running_wells:
        assert w.active_on(date(2026, 8, 6)) or w.sort_day == 12


def test_sorting_day_is_recovered_from_the_chinese_marker(v3):
    assert {w.sort_day for w in v3.running_wells} == {12}


def test_factor_table_rows_are_one_per_running_well(v3, v2):
    assert len(factor_table(v3)) == 5
    assert len(factor_table(v2)) == 5


def test_constant_factors_are_not_reported_as_confounded(v2):
    """BMP4 is 25 ng/ml on every v2 well. A constant is not confounded with anything."""
    conf = confounded_factor_pairs(factor_table(v2), ["bmp4_ng_ml", "terminal_medium"])
    assert conf == []
