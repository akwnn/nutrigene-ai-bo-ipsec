"""Version C §3.3 · the ONE-SHOT held-out scoring pass, checked without spending it.

Registered in ``docs/OPEN-QUESTIONS.md`` at commit 95fca9c (the freeze) and corrected by
Erratum 31 at 72c2a39 -- **both before this runner existed**.

WHAT THIS FILE PINS, AND WHY EACH ONE COST SOMETHING
-----------------------------------------------------
1. **The frozen literals are READ FROM THE DOCUMENT, never recomputed.** A runner that
   recomputes the boundary from ``versionc-detector-fit.json`` would silently re-freeze on
   whatever that file happened to contain at run time. The freeze is a commitment, so the
   code must depend on the committed text.
2. **The fitting runner's guards are NOT weakened.** Adding a held-out path must not make
   ``run_versionc_detector.py`` capable of touching hartmann6. Checked directly.
3. **The boundary is INCLUSIVE => UNIMODAL.** An off-by-one on a closed interval moves the
   verdict on exactly the campaigns that sit on the boundary, which are the ones the
   one-class rule is most likely to produce.
4. **K-C7's threshold is 33/50 and comes from the EXACT binomial tail** (Erratum 21), not
   from a normal approximation and not from a round number.
5. **The pass runs ONCE.** A second invocation against an existing output must refuse.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
from scipy.stats import binom, norm

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "OPEN-QUESTIONS.md"

#: The two literals, as they appear in the committed freeze block. Duplicated here on
#: purpose: if either the doc or the runner drifts, this file fails rather than agreeing
#: with whichever one moved.
FROZEN_LO = 0.10542874984223577
FROZEN_HI = 0.8860126525534584


@pytest.fixture(scope="module")
def ho():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "ho", ROOT / "scripts" / "run_versionc_detector_heldout.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ho"] = mod
    spec.loader.exec_module(mod)
    return mod


# ======================================================================================
# 1. THE FREEZE IS A COMMITMENT, SO THE CODE MUST DEPEND ON THE COMMITTED TEXT
# ======================================================================================
def test_the_freeze_block_is_committed_and_carries_both_literals():
    """The document half of the contract, independent of any runner."""
    committed = subprocess.check_output(
        ["git", "show", "HEAD:docs/OPEN-QUESTIONS.md"], cwd=ROOT, text=True)
    assert "THE DETECTOR RULE IS FROZEN" in committed
    assert repr(FROZEN_LO) in committed, "lo is not in the committed document"
    assert repr(FROZEN_HI) in committed, "hi is not in the committed document"


def test_runner_reads_the_literals_from_the_document_not_from_the_fit_file(ho):
    """🔴 The defect this exists to prevent.

    Recomputing ``min``/``max`` from ``versionc-detector-fit.json`` at run time would make
    the boundary whatever that file says *now*, which is not what "frozen" means.
    """
    src = (ROOT / "scripts" / "run_versionc_detector_heldout.py").read_text()
    assert "versionc-detector-fit.json" not in src, (
        "the held-out runner must not read the fit file at all -- the boundary comes from "
        "the committed document")
    assert "versionc-detector-boundary.json" not in src, (
        "nor the boundary file; that one carries frozen=false")
    assert ho.FROZEN_LO == FROZEN_LO
    assert ho.FROZEN_HI == FROZEN_HI


def test_the_runner_refuses_to_run_if_the_freeze_is_not_committed(ho):
    """Present-on-disk is not committed. The guard must ask git."""
    assert hasattr(ho, "assert_freeze_committed")
    ho.assert_freeze_committed()          # must not raise at HEAD
    src = (ROOT / "scripts" / "run_versionc_detector_heldout.py").read_text()
    assert "git" in src and "show" in src, (
        "the freeze check must consult git, not merely read the working-tree file")


# ======================================================================================
# 2. THE FITTING PATH MUST NOT BE WEAKENED BY THE EXISTENCE OF A HELD-OUT PATH
# ======================================================================================
def test_the_fitting_runner_still_refuses_held_out_families():
    """Defence in depth stays in depth. This is a regression guard on the OLD file."""
    spec = importlib.util.spec_from_file_location(
        "fitrun", ROOT / "scripts" / "run_versionc_detector.py")
    fit = importlib.util.module_from_spec(spec)
    sys.modules["fitrun"] = fit
    spec.loader.exec_module(fit)

    assert fit.HELD_OUT_FAMILIES == ("hartmann6", "ackley")
    for fam in fit.HELD_OUT_FAMILIES:
        with pytest.raises(fit.HeldOutFamily):
            fit.evaluator_for(fam, 6, 0.25, 0)


def test_held_out_runner_scores_only_held_out_families(ho):
    """The mirror image: the one-shot runner must not be pointable at the fit set."""
    assert ho.HELD_OUT_FAMILIES == ("hartmann6", "ackley")
    for fam in ("hill", "levy", "rosenbrock"):
        with pytest.raises(Exception):
            ho.classify_family_guard(fam)


# ======================================================================================
# 3. THE CLASSIFICATION RULE, INCLUDING ITS BOUNDARY
# ======================================================================================
def test_classification_is_inclusive_at_both_ends(ho):
    """On the boundary is INSIDE, so UNIMODAL. Pinned because it is an off-by-one."""
    assert ho.classify(FROZEN_LO) == "UNIMODAL", "lo itself is inside the fit range"
    assert ho.classify(FROZEN_HI) == "UNIMODAL", "hi itself is inside the fit range"
    assert ho.classify(FROZEN_LO - 1e-12) == "DECEPTIVE"
    assert ho.classify(FROZEN_HI + 1e-12) == "DECEPTIVE"
    assert ho.classify(0.5 * (FROZEN_LO + FROZEN_HI)) == "UNIMODAL"


# ======================================================================================
# 4. K-C7'S THRESHOLD IS THE EXACT TAIL, NOT A ROUND NUMBER (Erratum 21)
# ======================================================================================
def test_kc7_threshold_is_the_exact_binomial_tail(ho):
    assert ho.N_SEEDS == 25
    assert ho.CELLS == ((6, 0.25), (6, 0.10))
    assert ho.N_PER_FAMILY == 50, "2 cells x 25 seeds"
    assert ho.KC7_MIN_DECEPTIVE == 33

    # 33 survives Holm x2; 32 does not. This is the arithmetic the number came from.
    assert binom.sf(32, 50, 0.5) * 2 < 0.05
    assert binom.sf(31, 50, 0.5) * 2 > 0.05
    # and it must not be the normal approximation, which disagrees here
    z = (32.5 - 25) / (50 * 0.25) ** 0.5
    assert abs(binom.sf(32, 50, 0.5) - norm.sf(z)) > 1e-4, (
        "if these agree the test cannot tell an exact tail from an approximation")


def test_kc7_verdict_needs_BOTH_families(ho):
    """'Separates held-out families', plural. One family is not separation."""
    assert ho.kc7_verdict({"hartmann6": 40, "ackley": 40}) == "NOT_FIRED"
    assert ho.kc7_verdict({"hartmann6": 40, "ackley": 32}) == "FIRED"
    assert ho.kc7_verdict({"hartmann6": 32, "ackley": 40}) == "FIRED"
    assert ho.kc7_verdict({"hartmann6": 33, "ackley": 33}) == "NOT_FIRED", "33 is inclusive"
    assert ho.kc7_verdict({"hartmann6": 0, "ackley": 0}) == "FIRED"


# ======================================================================================
# 5. ONE SHOT MEANS ONE SHOT
# ======================================================================================
def test_the_output_path_is_registered_and_negated(ho):
    gi = (ROOT / ".gitignore").read_text()
    assert "!results/versionc-detector-heldout.json" in gi
    assert ho.OUT.name == "versionc-detector-heldout.json"


def test_a_second_invocation_refuses(ho, tmp_path):
    """The pass cannot be repeated to improve it (section 3.5)."""
    existing = tmp_path / "versionc-detector-heldout.json"
    existing.write_text("{}")
    with pytest.raises(Exception):
        ho.assert_not_already_scored(existing)
    ho.assert_not_already_scored(tmp_path / "absent.json")   # must not raise


def test_no_constant_is_fitted_at_run_time(ho):
    """Erratum 20. The boundary is a max(observed) by design; nothing ELSE may be."""
    src = (ROOT / "scripts" / "run_versionc_detector_heldout.py").read_text()
    for banned in ("max(observed", "worst_observed", "np.percentile", "quantile("):
        assert banned not in src, f"{banned!r} suggests a constant fitted at run time"
