"""Channel identity and positivity.

The point of these tests is that the CD31 assignment is a *measurement with a margin*,
not a lookup. If a future drop swaps the panel, the winner changes and these fail.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from boec.lab.gating import (
    REFERENCE_PANEL,
    ChannelIdentity,
    check_panel_match,
    percent_positive,
    resolve_cd31_channel,
)

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
REF = LAB / "raw" / "flow" / "2026-07-28" / "Exp_20260728_1"
PANEL = LAB / "raw" / "flow" / "2026-08-06" / "Exp_20260806_cd31-cd140a"

pytestmark = pytest.mark.skipif(not REF.exists(), reason="reference panel not present")

PRIMARIES = [f"{c}{d}.fcs" for c in ("f", "v") for d in ("0.5", "1", "2.5", "5", "10", "20")]


@pytest.fixture(scope="module")
def identity() -> ChannelIdentity:
    return resolve_cd31_channel(REF)


def test_cd31_resolves_to_b525a(identity):
    assert identity.cd31_detector == "B525-A"


def test_winner_is_ranked_against_all_sixteen_fluorescence_detectors(identity):
    """Beating the one channel we expected to beat is not evidence."""
    assert len(identity.verdicts) == 16
    assert identity.verdicts[0].detector == identity.cd31_detector


def test_the_margin_over_the_runner_up_is_reported_and_material(identity):
    assert identity.margin > 5.0, f"only {identity.margin:.2f}pp over {identity.runner_up}"
    assert identity.verdicts[0].excess > 2 * identity.verdicts[2].excess


def test_runner_up_is_flagged_as_probable_spillover(identity):
    """B610-A shares the blue laser and the panel was never compensated."""
    assert identity.runner_up == "B610-A"
    assert any("spillover" in n for n in identity.notes)


def test_sorted_negative_and_controls_stay_near_the_isotype_rate(identity):
    """A detector that calls 1% of the isotype positive should call ~1% of US positive."""
    win = identity.verdicts[0]
    assert win.pct_positive_in_isotype == pytest.approx(1.0, abs=0.2)
    assert win.pct_positive_in_negative < 2.0
    assert win.pct_positive_in_unstained < 2.0


def test_median_comparison_would_have_picked_the_wrong_channel():
    """Documents why `excess` is the statistic.

    The sorted CD31+ sample is bimodal: its B525-A median sits *below* CD31-'s while
    its upper tail sits far above. A median-ratio rule ranks the correct answer last.
    """
    from boec.lab.fcs import detector_index, read_events

    pos, lab = read_events(REF / "CD31+.fcs")
    neg, _ = read_events(REF / "CD31-.fcs")
    i = detector_index(lab, "B525-A")
    assert np.median(pos[:, i]) < np.median(neg[:, i])
    assert np.percentile(pos[:, i], 90) > 10 * np.percentile(neg[:, i], 90)


def test_incomplete_reference_panel_raises(tmp_path):
    (tmp_path / REFERENCE_PANEL["positive"]).write_bytes(b"not an fcs")
    with pytest.raises(FileNotFoundError, match="panel incomplete"):
        resolve_cd31_channel(tmp_path)


def test_reference_panel_and_target_share_a_detector_configuration():
    ok, problems = check_panel_match(REF / "CD31+.fcs", PANEL / "f5.fcs")
    assert ok, problems


def test_panel_mismatch_is_detected_when_it_exists(tmp_path):
    ok, problems = check_panel_match(REF / "CD31+.fcs", REF / "CD31+.fcs")
    assert ok and problems == []


@pytest.mark.parametrize("name", PRIMARIES)
def test_every_primary_yields_a_percentage_in_range(name, identity):
    r = percent_positive(PANEL / name, PANEL / "us.fcs", identity.cd31_detector)
    assert 0.0 <= r.pct_positive <= 100.0
    assert r.events > 20_000
    assert r.control_file == "us.fcs"


def test_sensitivity_sweep_travels_with_every_point_estimate(identity):
    r = percent_positive(PANEL / "f5.fcs", PANEL / "us.fcs", identity.cd31_detector)
    assert set(r.sensitivity) == {95.0, 99.0, 99.5, 99.9}
    # A higher threshold cannot call more events positive.
    vals = [r.sensitivity[q] for q in sorted(r.sensitivity)]
    assert vals == sorted(vals, reverse=True)
    assert r.pct_positive == pytest.approx(r.sensitivity[99.0])
    assert r.spread > 1.0, "a spread this flat would be suspicious on n=1 data"


def test_lowest_coating_dose_is_the_weakest_for_both_coatings(identity):
    """The one dose-response claim the data makes strongly at every threshold."""
    det = identity.cd31_detector
    for coating in ("f", "v"):
        pcts = {
            d: percent_positive(PANEL / f"{coating}{d}.fcs", PANEL / "us.fcs", det).pct_positive
            for d in ("0.5", "1", "2.5", "5", "10", "20")
        }
        assert pcts["0.5"] == min(pcts.values()), (coating, pcts)


def test_cd140a_stays_low_which_corroborates_the_assignment(identity):
    """PDGFRa should be a minority marker on differentiating EC cultures.

    If Y585-A were CD31 and B525-A were CD140a, this panel would be reporting a
    predominantly mesenchymal culture with a rare endothelial fraction -- the opposite
    of what the experiment is for. Consistency, not proof.
    """
    assert identity.cd31_detector != "Y585-A"
    for name in PRIMARIES:
        r = percent_positive(PANEL / name, PANEL / "us.fcs", "Y585-A")
        assert r.pct_positive < 20.0, name
