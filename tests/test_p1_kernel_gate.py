"""P1 — the gate that `run_k6_designspace.py` never applied to the kernel arms.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION", before `scripts/run_p1_kernel_gate.py` existed.

THE DEFECT THESE TESTS EXIST TO MAKE IMPOSSIBLE
-----------------------------------------------
`scripts/run_k6_designspace.py:161-162` builds its `committed` dict from
`results/e2-grid.json`, which carries seven arms and **no kernel arms**. Line 181's
`ref = committed.get(...)`/`if ref is not None` therefore skipped 100 campaigns in
silence, and `run_k6b_conservative.py:135-136` skipped the same 100 (COVERAGE-MATRIX
§3.6). The gate did not fail; it did not run, and nothing said so.

So the property under test is not "the deltas are small". It is:

* a comparator that is **absent raises**, and is never quietly treated as a pass;
* **every** non-key column of the committed row is compared, so a re-score cannot pass
  by checking a hand-picked subset of the metrics it happens to reproduce;
* the bar is **exact**. One ULP is a failure. The registration's stop condition 4 is
  "wanting to raise a tolerance", so there is no tolerance to raise.

The row counts are asserted against the registration's own number (2,800) rather than
against a regeneration of themselves — D12 applies to the shape of the data too.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_p1_kernel_gate.py"
K6 = Path("results/k6-designspace.json")
K6B = Path("results/k6b-conservative.json")


def _mod():
    spec = importlib.util.spec_from_file_location("p1_kernel_gate", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    assert SCRIPT.exists(), f"{SCRIPT} does not exist yet"
    return _mod()


# --------------------------------------------------------------------------- shape


def test_the_committed_kernel_rows_are_the_registered_2800(mod):
    """1,200 per arm in K6 and 200 per arm in K6b — the number A1 rests on."""
    k6 = mod.committed_index(K6, mod.K6_KEYS)
    k6b = mod.committed_index(K6B, mod.K6B_KEYS)
    per_arm_k6 = {a: sum(1 for k in k6 if k[4] == a) for a in mod.KERNEL_ARMS}
    per_arm_k6b = {a: sum(1 for k in k6b if k[4] == a) for a in mod.KERNEL_ARMS}
    assert per_arm_k6 == {"qlogei-add": 1200, "qlogei-addonly": 1200}
    assert per_arm_k6b == {"qlogei-add": 200, "qlogei-addonly": 200}
    assert len(k6) + len(k6b) == 2800


def test_the_index_refuses_a_duplicate_key(mod):
    """A duplicated key would let one re-scored row silently shadow another."""
    rows = [{"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0,
             "arm": "qlogei-add", "tau_frac": 0.6, "x": 1.0}] * 2
    with pytest.raises(ValueError, match="duplicate"):
        mod.index_rows(rows, mod.K6B_KEYS)


# ------------------------------------------------------------ nothing hand-picked


def test_every_non_key_column_is_compared(mod):
    """A re-score that checks a subset of columns is how a bad row passes a gate."""
    k6_row = next(iter(mod.committed_index(K6, mod.K6_KEYS).values()))
    k6b_row = next(iter(mod.committed_index(K6B, mod.K6B_KEYS).values()))
    assert set(mod.metric_columns(k6_row, mod.K6_KEYS)) == set(k6_row) - set(mod.K6_KEYS)
    assert set(mod.metric_columns(k6b_row, mod.K6B_KEYS)) == set(k6b_row) - set(mod.K6B_KEYS)
    # The committed schema, pinned so a re-score against a narrower one is caught.
    assert len(mod.metric_columns(k6_row, mod.K6_KEYS)) == 20
    assert len(mod.metric_columns(k6b_row, mod.K6B_KEYS)) == 24
    assert "regret" in mod.metric_columns(k6_row, mod.K6_KEYS)


def test_comparing_a_row_that_is_missing_a_committed_column_is_a_failure(mod):
    committed = {"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0,
                 "arm": "qlogei-add", "tau_frac": 0.6, "alpha_star": 0.5, "max_p": 0.1}
    rescored = dict(committed)
    del rescored["max_p"]
    fails = mod.compare_row(committed, rescored, mod.K6B_KEYS)
    assert [f["metric"] for f in fails] == ["max_p"]
    assert fails[0]["abs_delta"] == math.inf


# ------------------------------------------------------------------- exactness


def test_one_ulp_is_a_failure(mod):
    """Stop condition 4: there is no tolerance here to raise."""
    v = 0.14830000000000001
    assert mod.abs_delta(v, math.nextafter(v, math.inf)) > 0.0
    committed = {"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0,
                 "arm": "qlogei-add", "tau_frac": 0.6, "regret": v}
    rescored = dict(committed, regret=math.nextafter(v, math.inf))
    fails = mod.compare_row(committed, rescored, mod.K6B_KEYS)
    assert len(fails) == 1 and fails[0]["metric"] == "regret"
    assert 0.0 < fails[0]["abs_delta"] < 1e-15


def test_identical_rows_produce_no_failures(mod):
    row = {"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0, "arm": "qlogei-add",
           "tau_frac": 0.6, "regret": 0.1483, "empty_pred": True, "n_active": 6}
    assert mod.compare_row(row, dict(row), mod.K6B_KEYS) == []


def test_nan_equals_nan_but_never_equals_a_number(mod):
    """`fi_pred` is NaN in 1,398 committed kernel rows; NaN != NaN would fire on all."""
    assert mod.abs_delta(float("nan"), float("nan")) == 0.0
    assert mod.abs_delta(float("nan"), 0.0) == math.inf
    assert mod.abs_delta(0.0, float("nan")) == math.inf


def test_bools_compare_as_themselves_not_as_floats(mod):
    assert mod.abs_delta(True, True) == 0.0
    assert mod.abs_delta(True, False) == math.inf


# ------------------------------------------------- the §3.6 defect, made impossible


def test_a_missing_comparator_raises_rather_than_skipping(mod):
    """`committed.get(...) is not None` is exactly how 100 campaigns skipped the gate."""
    comparator = mod.index_rows(
        [{"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0,
          "arm": "qlogei-add", "regret": 0.1}], mod.Q30_KEYS)
    with pytest.raises(KeyError):
        mod.gate_regret(comparator, instance="b", dim=6, sigma=0.25, seed=0,
                        arm="qlogei-add", regenerated=0.1)


def test_gate_regret_reports_the_delta_it_measured(mod):
    comparator = mod.index_rows(
        [{"instance": "a", "dim": 6, "sigma": 0.25, "seed": 0,
          "arm": "qlogei-add", "regret": 0.1}], mod.Q30_KEYS)
    ok = mod.gate_regret(comparator, instance="a", dim=6, sigma=0.25, seed=0,
                         arm="qlogei-add", regenerated=0.1)
    assert ok["abs_delta"] == 0.0 and ok["passed"] is True
    bad = mod.gate_regret(comparator, instance="a", dim=6, sigma=0.25, seed=0,
                          arm="qlogei-add", regenerated=0.2)
    assert bad["passed"] is False and bad["abs_delta"] == pytest.approx(0.1)


# ------------------------------------------------------------------- the verdict


def test_verdict_is_validated_only_when_everything_is_zero(mod):
    assert mod.verdict([], []) == "VALIDATED"


def test_any_nonzero_delta_withdraws_the_committed_rows(mod):
    assert mod.verdict([{"abs_delta": 1e-17}], []) == "WITHDRAWN"
    assert mod.verdict([], [{"abs_delta": 1e-17}]) == "WITHDRAWN"


def test_an_incomplete_rescore_cannot_be_reported_as_validated(mod):
    """Fewer re-scored rows than committed rows is the §3.6 silence, not a pass."""
    with pytest.raises(ValueError, match="2800|coverage|expected"):
        mod.assert_full_coverage(rescored_k6=2399, rescored_k6b=400)


def test_provenance_block_matches_the_q52_model(mod):
    """`results/q52-budget-to-target.json` is the registered model for this block."""
    model = set(json.loads(Path("results/q52-budget-to-target.json").read_text())
                ["provenance"]) - {"config"}
    prov = mod.provenance()
    assert model <= set(prov), f"provenance missing {sorted(model - set(prov))}"
