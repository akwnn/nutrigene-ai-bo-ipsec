"""Q50's paired contrast — locked so it cannot go stale unnoticed again.

The original defect was not a wrong number. It was a number with no artefact behind it,
which then quietly went stale when the seed sweep completed and nothing recomputed it.
Both halves need a test: the artefact must exist and match the docs, and the pairing must
be over matching instances.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAIRED = ROOT / "results" / "q50-paired.json"
SWEEP = ROOT / "results" / "q50-qlogei-seedsweep.json"

pytestmark = pytest.mark.skipif(not PAIRED.exists(), reason="q50-paired.json not present")


@pytest.fixture(scope="module")
def paired():
    return json.loads(PAIRED.read_text(encoding="utf-8"))


def test_artefact_covers_the_registered_primary_cell(paired):
    assert paired["cell"] == {"dim": 6, "sigma_rel": 0.25, "budget": 48}


def test_per_instance_vectors_are_stored_not_just_the_summary(paired):
    """The whole point. A stored mean cannot be re-paired; stored vectors can."""
    lhs = paired["lhs"]["per_instance"]
    bo = paired["qlogei"]["per_instance"]
    assert len(lhs) == 25 and len(bo) == 25
    assert len(paired["instance_ids"]) == 25
    assert len(set(paired["instance_ids"])) == 25, "instance ids must be unique"


def test_stored_vectors_reproduce_the_reported_arm_means(paired):
    assert np.mean(paired["lhs"]["per_instance"]) == pytest.approx(
        paired["lhs"]["design_averaged"], abs=1e-12
    )
    assert np.mean(paired["qlogei"]["per_instance"]) == pytest.approx(
        paired["qlogei"]["seed_averaged"], abs=1e-12
    )
    assert paired["lhs"]["design_averaged"] == pytest.approx(0.1752, abs=5e-4)
    assert paired["qlogei"]["seed_averaged"] == pytest.approx(0.1532, abs=5e-4)


def test_stored_vectors_reproduce_the_paired_difference(paired):
    lhs = np.array(paired["lhs"]["per_instance"])
    bo = np.array(paired["qlogei"]["per_instance"])
    diff = lhs - bo
    assert diff.mean() == pytest.approx(paired["paired"]["mean_difference"], abs=1e-12)
    assert int((diff > 0).sum()) == paired["paired"]["bo_ahead_on"]


def test_the_claim_as_written_in_claims_md(paired):
    """These four numbers appear verbatim in docs/CLAIMS.md. If they move, both move."""
    st = paired["paired"]
    assert st["mean_difference"] == pytest.approx(0.0220, abs=5e-5)
    assert st["ci95_bootstrap"][0] == pytest.approx(0.0170, abs=5e-4)
    assert st["ci95_bootstrap"][1] == pytest.approx(0.0272, abs=5e-4)
    assert st["wilcoxon_p"] < 1e-7
    assert st["bo_ahead_on"] == 25
    assert st["n_instances"] == 25


def test_bonferroni_over_q39s_family_still_survives(paired):
    """CLAIMS.md quotes 2.3e-6 for 39 contrasts."""
    assert paired["paired"]["wilcoxon_p"] * 39 == pytest.approx(2.3e-6, rel=0.1)
    assert paired["paired"]["wilcoxon_p"] * 39 < 0.05


def test_the_historical_eight_seed_figures_are_recorded_and_differ(paired):
    """The staleness finding itself is an artefact, not a claim in a commit message.

    Without this, the next person sees only the corrected numbers and has no way to
    know the docs once said something else, or why.
    """
    old = paired["paired_historical_8_seeds"]
    assert old["mean_difference"] == pytest.approx(0.0219, abs=5e-5)
    assert old["bo_ahead_on"] == 21
    assert old["wilcoxon_p"] == pytest.approx(1.8e-5, rel=0.1)
    # The point that made it invisible: the ARM MEAN is stable, only the pairing moved.
    assert old["mean_difference"] == pytest.approx(
        paired["paired"]["mean_difference"], abs=2e-4
    )
    assert old["bo_ahead_on"] != paired["paired"]["bo_ahead_on"]


def test_pairing_is_by_instance_id_and_both_arms_cover_the_same_instances(paired):
    """A paired test on mismatched instances returns a plausible, wrong number."""
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    sweep_ids = {str(r["instance"]) for r in sweep["rows"]}
    assert set(paired["instance_ids"]) == sweep_ids


def test_qlogei_side_is_read_from_the_committed_sweep(paired):
    assert paired["qlogei"]["source"] == "results/q50-qlogei-seedsweep.json"
    assert SWEEP.exists()


def test_lhs_side_records_how_it_was_regenerated(paired):
    assert paired["lhs"]["arm"] == "lhs"
    assert paired["lhs"]["n_designs"] == 60
    assert paired["lhs"]["noise_seeds"] == [0, 1]
    assert paired["lhs"]["source"], "the lhs side must say where it came from"


# --- the underlying repair: q48 no longer throws the per-instance axis away ---------

Q48 = ROOT / "results" / "q48-design-variance.json"

q48_only = pytest.mark.skipif(not Q48.exists(), reason="q48-design-variance.json absent")


@pytest.fixture(scope="module")
def q48():
    return json.loads(Q48.read_text(encoding="utf-8"))


@q48_only
def test_q48_keeps_the_per_instance_axis(q48):
    """`cell_mean` used to collapse this before returning. That was the whole defect."""
    for rec in q48:
        assert "per_instance" in rec, (rec["dim"], rec["sigma"], rec["arm"])
        assert "per_instance_design_averaged" in rec
        assert "instance_ids" in rec
        cube = np.array(rec["per_instance"])
        assert cube.shape == (rec["n_designs"], len(rec["instance_ids"]))


@q48_only
def test_q48_detail_rebuilds_every_summary_it_ships(q48):
    """The added detail must be consistent with the numbers already published."""
    for rec in q48:
        cube = np.array(rec["per_instance"])
        assert np.allclose(cube.mean(axis=1), rec["draws"], atol=1e-12)
        assert cube.mean() == pytest.approx(rec["design_averaged"], abs=1e-12)
        assert np.array(rec["per_instance_design_averaged"]).mean() == pytest.approx(
            rec["design_averaged"], abs=1e-12
        )


@q48_only
def test_q48_instance_ids_are_present_and_unique(q48):
    """Pairing by list position is what makes two arms silently mismatch."""
    for rec in q48:
        ids = rec["instance_ids"]
        assert len(ids) == 25 and len(set(ids)) == 25


@q48_only
def test_q48_and_the_paired_artefact_agree_instance_by_instance(paired, q48):
    """Two independently written code paths over the same cell. Any drift is a bug."""
    rec = next(
        r for r in q48 if r["dim"] == 6 and abs(r["sigma"] - 0.25) < 1e-12 and r["arm"] == "lhs"
    )
    by_id = dict(zip(rec["instance_ids"], rec["per_instance_design_averaged"]))
    assert set(by_id) == set(paired["instance_ids"])
    aligned = np.array([by_id[i] for i in paired["instance_ids"]])
    assert np.allclose(aligned, paired["lhs"]["per_instance"], atol=1e-12)


@q48_only
def test_every_static_arm_cell_can_now_be_paired(q48):
    """The durable part of the fix: not just the one cell the claim happened to need.

    Before the repair only d=6/sigma=0.25 could be rescued, and only by re-running it.
    """
    cells = {(r["dim"], r["sigma"], r["arm"]) for r in q48}
    assert len(cells) == 12
    for rec in q48:
        assert len(rec["per_instance_design_averaged"]) == 25
