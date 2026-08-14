"""Microscopy provenance, focus QC, and phase-contrast coverage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from boec.lab.imaging import (
    METRIC_NAME,
    METRIC_PROTOCOL,
    METRIC_UNIT,
    analyse_image,
    comparability_groups,
    focus_score,
    load_gray,
    read_sidecar,
    sidecar_for,
    texture_coverage,
)

ROOT = Path(__file__).resolve().parents[1]
MICRO = ROOT / "data" / "lab" / "raw" / "microscopy"
LEICA_0804 = MICRO / "leica" / "2026-08-04"

pytestmark = pytest.mark.skipif(not MICRO.exists(), reason="microscopy not present")

FN_VTN = {
    "fib 0-5": ("fibronectin", 0.5),
    "fib 1": ("fibronectin", 1.0),
    "fib 2-5": ("fibronectin", 2.5),
    "fib5": ("fibronectin", 5.0),
    "fib10": ("fibronectin", 10.0),
    "fib20": ("fibronectin", 20.0),
    "vtn 0-5": ("vitronectin", 0.5),
    "vtn 1": ("vitronectin", 1.0),
    "vtn 2-5": ("vitronectin", 2.5),
    "vtn5": ("vitronectin", 5.0),
    "vtn 10": ("vitronectin", 10.0),
    "vtn 20": ("vitronectin", 20.0),
}


def _path(stem: str) -> Path:
    return LEICA_0804 / f"Leica_2026-08-04 {stem}.jpeg"


def test_the_twelve_dose_matched_images_all_exist():
    missing = [s for s in FN_VTN if not _path(s).exists()]
    assert missing == [], missing


def test_sidecar_parses_to_phase_contrast_at_4x():
    meta = read_sidecar(sidecar_for(_path("fib5")))
    assert meta.contrast == "PH"
    assert meta.objective == "4X"
    assert (meta.width, meta.height) == (3072, 2048)
    assert meta.created is not None and meta.created.date().isoformat() == "2026-08-04"


def test_the_dose_series_is_acquisition_comparable():
    """The precondition for comparing coverage across these images at all.

    Different exposure or objective would mean any coverage difference measures the
    microscope, not the culture.
    """
    metas = {s: read_sidecar(sidecar_for(_path(s))) for s in FN_VTN}
    groups = comparability_groups(metas)
    assert len(groups) == 1, groups.keys()
    assert next(iter(groups)) == ("PH", "4X", 19000, 1, 45)


def test_evos_images_have_no_sidecar_and_that_is_not_an_error():
    evos = sorted((MICRO / "evos" / "2026-08-06").glob("*.jpg"))
    assert evos, "no EVOS images found"
    assert sidecar_for(evos[0]) is None
    feats = analyse_image(evos[0])
    assert feats.comparability_key is None
    assert 0.0 <= feats.coverage <= 1.0


def test_coverage_is_a_fraction_and_otsu_reports_a_real_split():
    for stem in FN_VTN:
        f = analyse_image(_path(stem))
        assert 0.0 <= f.coverage <= 1.0, stem
        assert f.otsu_separability > 0.3, f"{stem} Otsu split is weak: {f.otsu_separability}"
        assert f.coverage_is_trustworthy, stem


def test_flat_field_yields_near_zero_coverage_and_untrustworthy_flag():
    """A featureless frame has no bimodal split; the number must not be believed."""
    flat = np.full((256, 256), 0.5)
    coverage, _thr, sep = texture_coverage(flat)
    assert coverage == pytest.approx(0.0, abs=1e-6)
    assert sep < 0.05


def test_focus_score_ranks_a_blurred_copy_below_the_original():
    from skimage import filters

    gray = load_gray(_path("fib5"))
    assert focus_score(gray) > focus_score(filters.gaussian(gray, sigma=4.0))


def test_coverage_is_stable_under_downsampling():
    """Coverage is a field fraction, so the analysis resolution must not drive it."""
    a = analyse_image(_path("fib5"), long_edge=1024).coverage
    b = analyse_image(_path("fib5"), long_edge=768).coverage
    assert a == pytest.approx(b, abs=0.06)


def test_metric_identity_is_distinct_from_the_flow_metric():
    """Requirement 7. Coverage from unstained phase contrast is not CD31%."""
    assert METRIC_NAME == "coverage_frac_phase"
    assert METRIC_UNIT == "fraction_of_field"
    assert METRIC_PROTOCOL == "leica-ph-4x-v1"
    assert METRIC_NAME != "CD31_pct_flow"
