"""Q62 runner bookkeeping — gate, collapse, Q56 lookup — without a BO loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_stored_qlognei_gate_matches_the_locked_means():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    # Import after path: the runner is a script, not a package.
    import run_q62_turbo as q62

    q62.check_stored_gate()
    _, mu25 = q62.stored_arm_instance_means("qlognei", 6, 0.25)
    _, mu10 = q62.stored_arm_instance_means("qlognei", 6, 0.10)
    assert round(float(mu25.mean()), 4) == 0.1532
    assert round(float(mu10.mean()), 4) == 0.0808


def test_q56_path_argmax_cell_is_readable():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import run_q62_turbo as q62

    cell = q62.q56_path_argmax_hits(0.25, 0.10)
    assert cell["n"] == 25
    assert 0 <= cell["hits_doe_ascent"] <= 25


def test_summarise_pairs_a_subset_of_e2_instances():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import run_q62_turbo as q62

    e2 = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    inst = next(
        r["instance"] for r in e2
        if r["arm"] == "qlognei" and r["dim"] == 6 and abs(r["sigma"] - 0.25) < 1e-12
    )
    fake = [
        dict(
            instance=inst, sigma=0.25, seed=0,
            R_measured=0.2, R_search=0.1, R_gp_box=0.15, R_gp_tr=0.16,
            arrivals={"0.10": 40}, n_unique=48, n_restarts=0,
        ),
        dict(
            instance=inst, sigma=0.25, seed=1,
            R_measured=0.22, R_search=0.11, R_gp_box=0.15, R_gp_tr=0.16,
            arrivals={"0.10": None}, n_unique=47, n_restarts=1,
        ),
    ]
    summary = q62._summarise(fake, budget=48)
    assert len(summary) == 1
    s = summary[0]
    assert s["n"] == 1
    assert s["hit_regret_0_10_both_seeds"] == 0  # seed 1 censored
    assert s["turbo_id"] == pytest.approx(0.105)
    assert s["q56_rule_a_0_10"]["n"] == 25
    assert s["doe_minus_turbo"] is not None


def test_n200_summary_does_not_subtract_48_well_doe():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import run_q62_turbo as q62

    e2 = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    inst = next(
        r["instance"] for r in e2
        if r["arm"] == "qlognei" and r["dim"] == 6 and abs(r["sigma"] - 0.25) < 1e-12
    )
    fake = [
        dict(
            instance=inst, sigma=0.25, seed=0,
            R_measured=0.12, R_search=0.04, R_gp_box=0.10, R_gp_tr=0.10,
            arrivals={"0.10": 80}, n_unique=198, n_restarts=2,
        ),
        dict(
            instance=inst, sigma=0.25, seed=1,
            R_measured=0.11, R_search=0.05, R_gp_box=0.09, R_gp_tr=0.09,
            arrivals={"0.10": 90}, n_unique=199, n_restarts=1,
        ),
    ]
    s = q62._summarise(fake, budget=200)[0]
    assert s["doe_minus_turbo"] is None
    assert s["stored_doe"] is None
    assert s["hit_regret_0_10_both_seeds"] == 1
    assert "48-well" in s["budget_note"]
