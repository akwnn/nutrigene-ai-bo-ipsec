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

from boec.calibration import error_volumes as canonical_error_volumes  # noqa: E402

from analyse_f2_error_volumes import (  # noqa: E402
    REQUIRED_COLUMNS,
    committed_rows,
    ce_error_volumes,
    error_volumes,
    missing_columns,
)

#: Registered in AMENDMENT F2a, measured before registration. Not derived from the code.
REGISTERED_SCORABLE_ROWS = 2553
REGISTERED_WORST_DELTA = 1e-15


@pytest.fixture(scope="module")
def k6_rows():
    return committed_rows("results/k6-designspace.json")


def test_the_registered_gate_holds_against_the_canonical_implementation(k6_rows):
    """THE registered validation, asserted directly against `boec.calibration`.

    The arithmetic used to live in this script and was deleted in favour of the canonical
    implementation, so that one committed quantity has one home. **The property that made
    the local copy worth keeping was this gate**, and a gate that stays behind in the
    deleted file is a gate that no longer protects anything. So it is re-asserted here
    against the imported function itself, not against this script's adapter.
    """
    committed = np.array([r["iou_pred"] for r in k6_rows], dtype=float)
    fi = np.array([r["fi_pred"] for r in k6_rows], dtype=float)
    scorable = np.isfinite(fi)
    assert int(scorable.sum()) == REGISTERED_SCORABLE_ROWS

    implied, type_ii = [], []
    for r in k6_rows:
        d = canonical_error_volumes(r["vol_pred"], r["fi_pred"],
                                    r["true_frac_above_tau"])
        implied.append(d["implied_iou"])
        type_ii.append(d["type_II_vol"])
    implied, type_ii = np.array(implied), np.array(type_ii)
    delta = np.abs(implied[scorable] - committed[scorable])
    assert float(delta.max()) <= REGISTERED_WORST_DELTA, (
        f"worst |delta| {float(delta.max()):.3e} exceeds the registered "
        f"{REGISTERED_WORST_DELTA:.0e} -- boec.calibration.error_volumes no longer "
        "describes the committed sets. STOP and report; do not patch it here.")
    assert float(type_ii.min()) >= 0.0


def test_this_scripts_adapter_delegates_to_the_canonical_implementation(k6_rows):
    """No second implementation. The adapter vectorises; it does not re-derive."""
    ev = error_volumes(k6_rows, "pred")
    for i in (0, 1, 500, 2000, 5999):
        r = k6_rows[i]
        d = canonical_error_volumes(r["vol_pred"], r["fi_pred"],
                                    r["true_frac_above_tau"])
        assert ev["type_I"][i] == d["type_I_vol"]
        assert ev["type_II"][i] == d["type_II_vol"]
        assert ev["total"][i] == d["total_error_vol"]


def test_derived_iou_reproduces_committed_iou_pred(k6_rows):
    """The same validation through this script's row-level API."""
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


def test_the_two_nan_conditions_are_different_and_counted_separately(k6_rows):
    """`fi` and `iou` do NOT break under the same condition, and F2a said they did.

    * `fi` is nan whenever **`D_est`** is empty  -- 3,447 of 6,000 rows here.
    * `iou` is nan only when the **UNION** is empty, i.e. `D_est` AND `D_true` both empty.
      An empty `D_est` against a non-empty true set gives IoU = **0**, which is correct.

    So the error volumes are strictly better defined than IoU, but on this data the true
    excursion set is never empty (min prevalence 0.0012), so the margin over IoU is
    **zero rows**. The real coverage gain is over `fi`. Asserted rather than assumed,
    because the registration claimed the larger margin.
    """
    fi = np.array([r["fi_pred"] for r in k6_rows], dtype=float)
    iou = np.array([r["iou_pred"] for r in k6_rows], dtype=float)
    prevalence = np.array([r["true_frac_above_tau"] for r in k6_rows], dtype=float)
    assert int(np.isnan(fi).sum()) == 3447, "D_est-empty count moved"
    assert int(np.isnan(iou).sum()) == 0, "committed iou_pred is finite on every row"
    assert (prevalence > 0).all(), "D_true is never empty, so the union is never empty"
    ev = error_volumes(k6_rows, "pred")
    assert np.isfinite(ev["type_I"]).all() and np.isfinite(ev["type_II"]).all()


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


# --------------------------------------------------------------------------------- CE
@pytest.fixture(scope="module")
def k6b_rows():
    return (committed_rows("results/k6b-conservative.json")
            + committed_rows("results/k6b-conservative-spread.json"))


def test_ce_error_volumes_produce_no_impossible_volumes(k6b_rows):
    """Extending the primary metric to `CE_alpha` — the object the certificate is about.

    There is **no committed IoU column for the CE sets**, so unlike the K6 map this
    derivation has no independent cross-check to gate against; the gate covers the shared
    function, not this application of it. What can be falsified is that the three columns
    are on the same normalisation: if `ce_vol * (1 - ce_false_in)` ever exceeded the
    prevalence, type II would go negative and the columns would not be comparable.
    """
    assert len(k6b_rows) == 1600
    for alpha in (0.5, 0.8, 0.95):
        ev = ce_error_volumes(k6b_rows, alpha)
        assert float(ev["type_II"].min()) >= 0.0, (
            f"negative type-II volume at alpha={alpha}: the CE columns are not on the "
            "same normalisation as the prevalence -- STOP and report")
        assert np.isfinite(ev["type_I"]).all() and np.isfinite(ev["type_II"]).all()


def test_an_empty_ce_set_scores_zero_type_i_and_the_whole_prevalence(k6b_rows):
    ev = ce_error_volumes(k6b_rows, 0.95)
    empty = ev["empty"]
    assert empty.sum() == 1380, "CE_0.95 emptiness moved"
    prevalence = np.array([r["true_frac_above"] for r in k6b_rows], dtype=float)
    assert np.array_equal(ev["type_I"][empty], np.zeros(int(empty.sum())))
    assert np.array_equal(ev["type_II"][empty], prevalence[empty])


def test_the_six_union_empty_rows_are_where_iou_genuinely_breaks(k6b_rows):
    """The one place in this programme where IoU really is 0/0 — and the volumes are not.

    F2a claimed the error volumes are defined where IoU breaks. On the K6 map that never
    happens (the true set is never empty). Here it happens exactly 6 times: the true
    excursion set is empty AND the certified set is empty, so IoU is 0/0 while both error
    volumes are exactly 0 and exactly right.
    """
    ev = ce_error_volumes(k6b_rows, 0.5)
    union_empty = ev["empty_union"]
    assert int(union_empty.sum()) == 6
    assert np.isnan(ev["iou_derived"][union_empty]).all()
    assert (ev["type_I"][union_empty] == 0).all()
    assert (ev["type_II"][union_empty] == 0).all()


def test_the_ce_prevalence_is_not_like_for_like_across_arms(k6b_rows):
    """Unlike K6, K6b scores `doe` on its own 4-D active subspace (Amendment B3).

    So the CE prevalence differs by arm within a cell and the cross-arm ranking is NOT
    like-for-like — the opposite of the K6 map, where all eight arms share the 6-D grid.
    Asserted so the ranking cannot quietly be read as comparable.
    """
    cells = {}
    for r in k6b_rows:
        cells.setdefault((r["instance"], r["seed"], r["tau_frac"]), {})[r["arm"]] = \
            r["true_frac_above"]
    differing = sum(1 for v in cells.values()
                    if len({round(x, 12) for x in v.values()}) > 1)
    assert differing == 198 and len(cells) == 200


def test_a_fully_empty_cell_ranks_prevalence_not_arms(k6b_rows):
    """The trap that would otherwise produce a wrong cross-family headline.

    When every arm certifies nothing, type I is 0 for all of them and total error volume
    is EXACTLY the prevalence — so the "ranking" is a ranking of prevalences and says
    nothing about the arms. Under Amendment B3 `doe`'s prevalence is higher (0.0046 vs
    0.0029 at `tau_frac = 0.95`, its slice being the easier one), so it is ranked LAST in
    those cells purely mechanically.

    This is the same class of error as "type I read alone ranks silence first", and it
    bites in 4 of the 12 CE cells.
    """
    ev = ce_error_volumes([r for r in k6b_rows if r["tau_frac"] == 0.95], 0.5)
    assert bool(ev["empty"].all()), "every CE_0.50 set at tau_frac=0.95 should be empty"
    assert np.array_equal(ev["total"], ev["prevalence"])
