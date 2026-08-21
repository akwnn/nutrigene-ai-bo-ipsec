"""Amendment F2a — expected type I / type II error volumes, derived from committed columns.

The registration (docs/OPEN-QUESTIONS.md, AMENDMENT F, commit 07e98df) states the
derivation and then states the check that decides whether the derivation is right:

    type_I_vol  = vol_pred * fi_pred                      # |D_est \\ D_true| / |grid|
    intersect   = vol_pred * (1 - fi_pred)
    type_II_vol = true_frac_above_tau - intersect         # |D_true \\ D_est| / |grid|

    `intersect / (vol_pred + true_frac_above_tau - intersect)` reproduces the committed
    `iou_pred` to a worst |delta| of 2.220e-16 over 2,553 rows, and produces zero
    impossible negative type-II volumes.

**That is the whole point of this file.** If the reproduction does not hold, the algebra
is wrong and the error volumes are not the sets the registration says they are; the
registered instruction is to stop and report rather than to patch the derivation until it
agrees. So the row count and the tolerance are both asserted as written, not recomputed
from whatever the code happens to produce.

Committed blobs are read through `git show HEAD:<path>`, not from the working tree. Six
other agents are writing into `results/` concurrently and a previous worker compared
against a file another process had already replaced.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyse_f2_error_volumes import (  # noqa: E402
    REQUIRED_COLUMNS,
    committed_rows,
    error_volumes,
    missing_columns,
)

#: Registered in AMENDMENT F2a, measured before registration. Not derived from the code.
REGISTERED_SCORABLE_ROWS = 2553
REGISTERED_WORST_DELTA = 1e-15


@pytest.fixture(scope="module")
def k6_rows():
    return committed_rows("results/k6-designspace.json")


def test_derived_iou_reproduces_committed_iou_pred(k6_rows):
    """THE registered validation. Worst |delta| <= 1e-15 over exactly 2,553 rows."""
    ev = error_volumes(k6_rows, "pred")
    scorable = ev["fi_defined"]
    assert int(scorable.sum()) == REGISTERED_SCORABLE_ROWS, (
        f"the registration measured {REGISTERED_SCORABLE_ROWS} rows with a defined "
        f"false-inclusion rate; this file has {int(scorable.sum())}")
    committed = np.array([r["iou_pred"] for r in k6_rows], dtype=float)
    delta = np.abs(ev["iou_derived"][scorable] - committed[scorable])
    assert float(delta.max()) <= REGISTERED_WORST_DELTA, (
        f"worst |delta| {float(delta.max()):.3e} exceeds the registered {REGISTERED_WORST_DELTA:.0e}; "
        "the derivation does not describe the committed sets -- STOP and report")


def test_no_impossible_negative_type_ii_volumes(k6_rows):
    """|D_true \\ D_est| is a volume. A negative one falsifies the derivation."""
    for suffix in ("pred", "latent"):
        ev = error_volumes(k6_rows, suffix)
        assert float(ev["type_II"].min()) >= 0.0, (
            f"negative type-II volume at suffix {suffix!r}: min {ev['type_II'].min():.3e}")


def test_error_volumes_are_defined_where_the_false_inclusion_rate_is_not(k6_rows):
    """The claim that makes the error volumes worth computing at all.

    Where `D_est` is empty the false-inclusion rate is 0/0. The two error volumes are
    not: nothing was claimed, so type I is exactly 0 and the whole true excursion set was
    missed, so type II is exactly the prevalence.
    """
    ev = error_volumes(k6_rows, "pred")
    empty = ~ev["fi_defined"]
    assert empty.any(), "no empty predictive regions -- the fixture is not the K6 file"
    assert np.isfinite(ev["type_I"]).all() and np.isfinite(ev["type_II"]).all()
    assert np.array_equal(ev["type_I"][empty], np.zeros(int(empty.sum())))
    prevalence = np.array([r["true_frac_above_tau"] for r in k6_rows], dtype=float)
    assert np.array_equal(ev["type_II"][empty], prevalence[empty])
    assert int(ev["type_I"].size) == len(k6_rows), "every row must score"


def test_versionb_error_volumes_are_reported_as_not_computable():
    """`versionb.json` does not carry the columns. It is a finding, not a hole to fill.

    The registration is explicit that the prevalence must not be imputed from another
    file, so the contract is that `missing_columns` names what is absent and no volume is
    produced for that file.
    """
    rows = committed_rows("results/versionb.json")
    missing = missing_columns(rows)
    assert missing, "expected versionb.json to be missing design-space columns"
    assert "true_frac_above_tau" in missing
    with pytest.raises(KeyError):
        error_volumes(rows, "pred")


def test_required_columns_are_the_three_the_registration_names():
    assert REQUIRED_COLUMNS == ("vol_{suffix}", "fi_{suffix}", "true_frac_above_tau")
