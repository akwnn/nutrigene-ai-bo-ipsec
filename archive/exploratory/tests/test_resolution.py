"""Effective resolution: certified volume measured in correlation cells, not box fraction.

The certificate's failure probability is governed by how much volume it claims (measured
this session on `results/p8-certificate-families.json`: model-internal containment is flat
at 0.983-1.000 across volume while truth containment collapses 1.000 -> 0.552). The volume
LAW is universal across families; its SCALE is not -- a volume cap calibrated on
hill/levy/rosenbrock sits at ~0.20 while ackley/hartmann6 need ~0.0025, an 80x gap.

`effective_resolution` is the hypothesis for why: what governs simultaneous containment is
the number of *effectively independent locations* a region spans, k_eff = V / prod(l_i),
not V itself. Lengthscales are read from the campaign's own fitted GP, so k_eff is
observable at run time with no access to truth.
"""



import pytest
import torch

from boec.resolution import effective_resolution


def test_isotropic_unit_cell_gives_one_effective_location():
    """d=2, l=0.5 each -> cell volume 0.25; a region of volume 0.25 spans exactly one."""
    assert effective_resolution(0.25, [0.5, 0.5]) == pytest.approx(1.0)


def test_anisotropic_cell_uses_the_product_of_lengthscales():
    """l=(0.5, 0.25) -> cell volume 0.125, so V=0.125 is one location, V=0.5 is four."""
    assert effective_resolution(0.125, [0.5, 0.25]) == pytest.approx(1.0)
    assert effective_resolution(0.500, [0.5, 0.25]) == pytest.approx(4.0)


def test_lengthscale_longer_than_the_box_is_capped_at_the_box():
    """A lengthscale of 2.0 on a unit box does not make the cell bigger than the box.

    Uncapped, prod(l) = 4.0 would report k_eff = V/4 -- claiming a region is a *fraction*
    of one independent location, which is not a thing. The whole box is one cell, so
    k_eff = V, and a full-box region spans exactly one.
    """
    assert effective_resolution(0.5, [2.0, 2.0]) == pytest.approx(0.5)
    assert effective_resolution(1.0, [2.0, 2.0]) == pytest.approx(1.0)


def test_empty_region_spans_no_locations():
    assert effective_resolution(0.0, [0.3, 0.3]) == 0.0


def test_monotone_increasing_in_volume_and_decreasing_in_lengthscale():
    a = effective_resolution(0.10, [0.3, 0.3])
    b = effective_resolution(0.20, [0.3, 0.3])
    c = effective_resolution(0.10, [0.6, 0.6])
    assert b > a, "more certified volume must span more independent locations"
    assert c < a, "a smoother field packs the same volume into fewer independent locations"


def test_accepts_a_tensor_of_lengthscales():
    """The caller reads ARD lengthscales straight off the fitted GP, which returns a
    Tensor. Requiring a list would put a `.tolist()` at every call site."""
    got = effective_resolution(0.25, torch.tensor([0.5, 0.5], dtype=torch.double))
    assert got == pytest.approx(1.0)


def test_six_dimensional_case_matches_hand_arithmetic():
    """d=6 at the project's own measured median ARD lengthscale (0.5982, n=40 plate 1,
    `src/boec/lse.py`). cell = 0.5982**6; a 5% region spans 0.05/cell locations."""
    cell = 0.5982 ** 6
    assert effective_resolution(0.05, [0.5982] * 6) == pytest.approx(0.05 / cell)


def test_rejects_a_volume_outside_the_unit_interval():
    """Volume is a FRACTION of the box. A value above 1 means the caller passed a count
    of grid points, which would silently inflate k_eff by the grid size."""
    with pytest.raises(ValueError):
        effective_resolution(1.5, [0.5, 0.5])
    with pytest.raises(ValueError):
        effective_resolution(-0.1, [0.5, 0.5])


def test_rejects_a_non_positive_lengthscale():
    """A zero lengthscale divides by zero and reports infinite resolution."""
    with pytest.raises(ValueError):
        effective_resolution(0.5, [0.5, 0.0])
    with pytest.raises(ValueError):
        effective_resolution(0.5, [0.5, -1.0])


def test_rejects_an_empty_lengthscale_vector():
    with pytest.raises(ValueError):
        effective_resolution(0.5, [])
