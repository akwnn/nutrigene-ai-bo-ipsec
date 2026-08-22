"""Version C section 0 -- the gate that decides whether section 2 gets built at all.

Rule P at sigma_rel = 0.10, every arm. **No new campaigns**: every arm is a regeneration
of a committed campaign, gated against its committed regret column at |delta| = 0 exactly
before any rule-P number is read. A single failure aborts; no tolerance is introduced.

The branch, pre-registered before looking:

    regret_P <~ 0.090   the sigma=0.10 gap is an IDENTIFICATION ARTEFACT of rule A
                        -> section 2 is NOT BUILT, Version C = section 1 + section 3
    regret_P >~ 0.11    a genuine search deficit -> trust region required
    between             inconclusive -> section 2 is built as an ARM, not as the method
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_run_versionc_gate", ROOT / "scripts" / "run_versionc_gate.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


# --- the gate index -------------------------------------------------------------------

def test_every_arm_at_sigma_010_has_a_committed_regret_column():
    """All twelve. p3-k6-d6-s010.json is the committed artefact at this cell and it
    carries `regret` for every arm, including the three the P2 registration called
    ungatable in principle -- ungatable then meant *no file existed yet*, and now one
    does. An arm the runner cannot gate is an arm the runner must refuse to score."""
    idx = G.gate_index(G.SIGMA)
    arms = {a for (_, _, a) in idx}
    assert arms == set(G.ARMS), f"missing {set(G.ARMS) - arms}"
    assert len(idx) == len(G.ARMS) * 50


def test_the_seven_e2_arms_carry_a_second_independent_gate():
    """Double-gated wherever two committed sources exist. p3's own regret column was
    itself gated against e2-grid.json, so agreement is expected -- which is exactly why
    disagreement would be worth stopping for."""
    cross = G.cross_gate_index(G.SIGMA)
    assert {a for (_, _, a) in cross} == set(G.CROSS_GATED_ARMS)
    idx = G.gate_index(G.SIGMA)
    for key, ref in cross.items():
        assert idx[key] == ref, f"the two committed sources disagree at {key}"


def test_plate1_only_is_cross_gated_through_its_lhs_alias():
    """`plate1_only` IS `lhs` -- the same 48 wells, committed columns agreeing to a worst
    |delta| of 4.44e-16. It is kept because it is Version B's label, and it must never be
    counted as an independent arm in a ranking."""
    cross = G.cross_gate_index(G.SIGMA)
    keys = [(i, s) for (i, s, a) in cross if a == "plate1_only"]
    assert len(keys) == 50, f"expected 50 plate1_only keys, got {len(keys)}"
    for inst, seed in keys:
        assert cross[(inst, seed, "plate1_only")] == cross[(inst, seed, "lhs")]


def test_a_missing_gate_key_raises_rather_than_returning_none():
    """The section 3.6 defect, which `run_p3_cells.py` already guards against: the file is
    there, the key is not, and `.get()` hands back `None` which then compares equal to
    nothing and gates nothing."""
    with pytest.raises(G.MissingGateTarget):
        G.gate_index(G.SIGMA, arms=("an_arm_that_was_never_run",))


def test_the_kernel_arms_carry_their_unresolved_provenance_into_every_row():
    """`qlogei-add` / `qlogei-addonly` were ungated in p3 because q30-additive.json was
    absent. It now exists, but the 2,800-row re-score that decides whether the committed
    kernel rows are VALIDATED or WITHDRAWN has not run. They are gated here against p3's
    committed column, which is a reproduction check and NOT a resolution of P1, and the
    row has to say so or a reader will take the gate for the answer."""
    for arm in ("qlogei-add", "qlogei-addonly"):
        assert arm in G.PROVENANCE_CAVEAT
        assert "P1" in G.PROVENANCE_CAVEAT[arm]


# --- the partial-file discipline ------------------------------------------------------

def test_a_partial_is_never_written_to_the_registered_path(tmp_path):
    """`.gitignore`'s negation makes anything at a registered `results/` path stageable,
    so a half-finished file reads as a finished one. Write to `<name>.partial`, promote
    once, and carry status / keys_present / keys_expected."""
    final = tmp_path / "versionc-gate.json"
    G.write_partial(final, rows=[{"arm": "lhs"}], keys_present=1, keys_expected=50,
                    argv=["t"], sigma=0.10)
    assert not final.exists()
    assert final.with_suffix(".json.partial").exists()
    d = json.loads(final.with_suffix(".json.partial").read_text())
    assert d["status"] == "partial" and d["complete"] is False
    assert d["keys_present"] == 1 and d["keys_expected"] == 50


def test_promote_refuses_an_incomplete_partial(tmp_path):
    final = tmp_path / "versionc-gate.json"
    G.write_partial(final, rows=[{"arm": "lhs"}], keys_present=1, keys_expected=50,
                    argv=["t"], sigma=0.10)
    with pytest.raises(ValueError):
        G.promote(final)
    assert not final.exists()


def test_promote_rereads_what_it_publishes(tmp_path):
    """A promote that does not re-read cannot tell you it published what it meant to."""
    final = tmp_path / "versionc-gate.json"
    rows = [{"arm": "lhs", "regret_p": 0.5}]
    G.write_partial(final, rows=rows, keys_present=50, keys_expected=50,
                    argv=["t"], sigma=0.10)
    published = G.promote(final)
    assert final.exists()
    assert not final.with_suffix(".json.partial").exists()
    assert published["status"] == "complete" and published["complete"] is True
    assert published["rows"] == rows


# --- the branch, applied identically every time ---------------------------------------

@pytest.mark.parametrize("regret_p, expected", [
    (0.0850, "IDENTIFICATION_ARTEFACT"),
    (0.0900, "IDENTIFICATION_ARTEFACT"),
    (0.0901, "INCONCLUSIVE"),
    (0.1099, "INCONCLUSIVE"),
    (0.1100, "SEARCH_DEFICIT"),
    (0.1500, "SEARCH_DEFICIT"),
])
def test_the_branch_is_a_function_not_a_reading(regret_p, expected):
    """Written as a function so it is applied to the number identically rather than
    recalled selectively -- the same reason `boec.spread_gp.within_design_noise` is one."""
    assert G.gate_branch(regret_p) == expected
