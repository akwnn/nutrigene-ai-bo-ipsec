"""The release audit's own audit — spec §9 (publication guards) and §10.1 item 7.

------------------------------------------------------------------------------
WHY THIS FILE EXISTS AT ALL
------------------------------------------------------------------------------

``scripts/validate_final_spade_release.py`` is the thing that stands between this
project and publishing a claim it has already learned it cannot support. A guard
that has never been shown to fire is not a guard — it is a comment. FINDINGS §22
is the case in point: the multiplicity correction *looked* right for a week and
was a normal approximation the whole time, and nothing in the repository was
positioned to say so.

So every check in the validator is exercised here **twice**: once on a synthetic
input that violates it, where it must fire, and once on a clean input, where it
must stay silent. A check that fires on everything is as useless as one that
fires on nothing, and only the pair of tests distinguishes them.

------------------------------------------------------------------------------
WHY EVERYTHING HERE IS SYNTHETIC
------------------------------------------------------------------------------

**The final study has not run.** ``results/final-spade-benchmark.json``,
``-certificates.json``, ``-kill-ledger.json``, ``-manifest.json`` and
``docs/FINDINGS-SPADE-FINAL.md`` do not exist yet. Tests that waited for them
would be written after the results were visible, which is the exact ordering the
registration forbids for everything else in this study and should not be
tolerated for its release gate either.

Every fixture below is therefore hand-built into ``tmp_path``. That has a second
benefit the real artefacts could never give: a fixture can be made to violate a
guard **on purpose**, which is the only way to demonstrate the guard works.

------------------------------------------------------------------------------
THE ONE TEST THAT IS NOT ABOUT THE VALIDATOR
------------------------------------------------------------------------------

``test_figures_never_import_the_campaign_machinery`` is a reproducibility test
wearing a figures test's clothes. A figure script that can call ``build_gp`` can
silently draw a number that is not in any committed artefact, and the reader has
no way to tell. The guard is structural — the module must not be able to reach
the oracle at all — because a guard on intent is not enforceable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_final_spade_release.py"
FIGURES_PATH = ROOT / "scripts" / "make_final_spade_figures.py"


def _load(name: str, path: Path):
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Registered before exec: the modules use forward-referenced dataclass fields,
    # and `dataclasses` resolves those through `sys.modules[cls.__module__]`.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


val = _load("validate_final_spade_release", VALIDATOR_PATH)
figs = _load("make_final_spade_figures", FIGURES_PATH)


# --------------------------------------------------------------------------
# Fixture builders. Kept as functions rather than pytest fixtures so a test can
# mutate one field of an otherwise-clean artefact -- which is how every
# "fires on the violation, silent otherwise" pair below is written.
# --------------------------------------------------------------------------

MANDATORY = ("spade_cf_m0", "spade_cf_m4", "spade_cf_m8", "spade_plate1_only",
             "spade_random_plate2", "sobol", "lhs", "random", "qlognei", "qlogei",
             "doe", "doe_unscreened")

ARM_FAMILY = {"spade_cf_m0": "SPADE", "spade_cf_m4": "SPADE", "spade_cf_m8": "SPADE",
              "spade_plate1_only": "SPADE control", "spade_random_plate2": "SPADE control",
              "sobol": "space-filling", "lhs": "space-filling", "random": "space-filling",
              "qlognei": "BO", "qlogei": "BO", "doe": "classical RSM",
              "doe_unscreened": "classical RSM"}

ARM_ROUNDS = {"spade_cf_m0": 2, "spade_cf_m4": 2, "spade_cf_m8": 2,
              "spade_plate1_only": 1, "spade_random_plate2": 2, "sobol": 1, "lhs": 1,
              "random": 1, "qlognei": 10, "qlogei": 10, "doe": 3, "doe_unscreened": 3}


def clean_ledger() -> dict:
    return {"study_id": "spade-final-2026-08-23", "entries": [
        {"id": f"KF-{i}", "claim": f"registered claim {i}", "status": "PASS",
         "effect": 0.01, "interval": [-0.01, 0.03], "p": 0.4, "p_adjusted": 0.9,
         "sesoi_comparison": "inside SESOI", "denominator": 100,
         "source_artefact": "results/final-spade-benchmark.json", "source_key": "rows"}
        for i in range(1, 11)]}


def clean_feasibility() -> dict:
    rows = []
    for cid, family, dim, sigma, tier, cls in (
            ("C1", "hill", 6, 0.25, "primary", "TARGET"),
            ("C2", "hill", 6, 0.10, "primary", "TARGET"),
            ("C3", "hartmann6", 6, 0.25, "primary", "ROBUSTNESS"),
            ("C4", "hartmann6", 8, 0.25, "primary", "ROBUSTNESS")):
        rows.append({"condition_id": cid, "tier": tier, "family": family,
                     "dimension": dim, "sigma": sigma, "tau_frac": 0.60,
                     "tau_raw": 0.60, "tau_max_worst": 0.9, "worst_gamma": 0.95,
                     "true_prevalence": 0.3, "boundary_frac": 0.2,
                     "expected_nonempty_rate": 0.8, "regime_class": cls,
                     "classification_reason": "synthetic"})
    return {"study_id": "spade-final-2026-08-23", "counts": {"TARGET": 2,
            "ROBUSTNESS": 2}, "rows": rows}


def clean_benchmark() -> dict:
    rows = []
    for cid in ("C1", "C2", "C3", "C4"):
        for i, arm in enumerate(MANDATORY):
            rows.append({
                "condition_id": cid, "arm": arm, "arm_family": ARM_FAMILY[arm],
                "rounds": ARM_ROUNDS[arm], "family": "hill", "dimension": 6,
                "sigma": 0.25, "regime_class": "TARGET", "terminal_rule": "P",
                "gamma": 0.95, "alpha": 0.95, "tau_frac_or_quantile": 0.60,
                "campaign_seed": i, "instance_seed": 0,
                "regret_rule_p": 0.10 + 0.01 * i, "regret_rule_a": 0.12 + 0.01 * i,
                "symmetric_difference_pred": 0.30 - 0.01 * i,
                "type_i_volume_pred": 0.10, "type_ii_volume_pred": 0.20 - 0.01 * i,
                "murphy_calibration": 0.02 + 0.001 * i,
                "murphy_refinement": 0.15 - 0.002 * i,
                "crossfit_containment": 0.96, "same_draw_containment": 0.98,
                "nonempty_certificate": True, "rankable": True,
                "unavailable_reason": None, "exclusion_reason": None,
                "gate_status": "OK"})
    return {"study_id": "spade-final-2026-08-23", "rows": rows}


def clean_certificates() -> dict:
    cells = []
    for cid in ("C1", "C2"):
        for arm in ("spade_cf_m0", "spade_cf_m4", "spade_cf_m8"):
            for alpha in (0.80, 0.95):
                cells.append({
                    "condition_id": cid, "arm": arm, "gamma": 0.95, "alpha": alpha,
                    "tau_frac": 0.60, "terminal_rule": "P",
                    "crossfit_x": 96, "crossfit_n": 100, "crossfit_rate": 0.96,
                    "ci_lo": 0.9007, "ci_hi": 0.9892,
                    "same_draw_x": 98, "same_draw_n": 100, "same_draw_rate": 0.98,
                    "exact_p": 0.63, "holm_p": 1.0, "holm_family": "F-CERT",
                    "nonempty_n": 100, "empty_rate": 0.0, "verdict": "PASS"})
    return {"study_id": "spade-final-2026-08-23", "cells": cells}


def clean_manifest(root: Path, sources: dict[str, str]) -> dict:
    hashes = {}
    for rel, text in sources.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        hashes[rel] = hashlib.sha256(text.encode()).hexdigest()
    return {"study_id": "spade-final-2026-08-23", "registration_commit": "c4f58d3",
            "code_commit": "0" * 40, "generated": "2026-08-23T00:00:00",
            "source_hashes": hashes,
            "config": {"n_draws": 4096, "campaigns": 100},
            "environment": {"python": "3.11.9", "platform": "darwin",
                            "packages": {"torch": "2.4.0", "scipy": "1.14.0"}},
            "seed_policy": "noise stream keyed on (family, d, sigma, instance, campaign)"}


CLEAN_FINDINGS = """\
# FINDINGS — SPADE-FINAL

Condition C1 (hill, d=6, sigma=0.25), TARGET. Condition C2, TARGET.
Conditions C3 and C4 are ROBUSTNESS cells and are reported as such.

Cross-fit containment is the primary endpoint; same-draw containment is reported
beside it as a non-primary diagnostic only.

Caption: cross-fit containment by arm, condition C1, terminal rule P.

| condition | arm | cross-fit X/n | same-draw X/n | rate |
|---|---|---|---|---|
| C1 | spade_cf_m0 | 96/100 | 98/100 | 0.96 |

Caption: regret by arm, condition C1, terminal rule P, n=100.

| condition | arm | terminal rule | regret | n |
|---|---|---|---|---|
| C1 | spade_cf_m0 | P | 0.10 | 100 |

`alpha_star` is retained as MODEL-INTERNAL: it measures willingness to certify
and is not evidence of certificate quality.

SPADE did not outperform sobol on the map. The certificate is NOT certified in
any wider sense than C1 and C2.
"""


def write_release(root: Path, *, findings: str = CLEAN_FINDINGS, ledger=None,
                  feasibility=None, benchmark=None, certificates=None,
                  manifest=None, analysis: str | None = None) -> Path:
    """A complete synthetic release tree at ``root``. Every argument defaults to the
    clean version, so a test overrides exactly the one artefact it is about."""
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "results").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "FINDINGS-SPADE-FINAL.md").write_text(findings)
    src = analysis if analysis is not None else CLEAN_ANALYSIS
    (root / "scripts" / "analyse_final_spade_benchmark.py").write_text(src)
    for name, obj in (("kill-ledger", ledger or clean_ledger()),
                      ("feasibility", feasibility or clean_feasibility()),
                      ("benchmark", benchmark or clean_benchmark()),
                      ("certificates", certificates or clean_certificates())):
        (root / "results" / f"final-spade-{name}.json").write_text(json.dumps(obj))
    man = manifest if manifest is not None else clean_manifest(
        root, {"scripts/analyse_final_spade_benchmark.py": src})
    (root / "results" / "final-spade-manifest.json").write_text(json.dumps(man))
    return root


CLEAN_ANALYSIS = '''\
"""Certificate inference is EXACT -- never a normal approximation (FINDINGS §22)."""
from scipy.stats import beta, binom


def containment_interval(x, n, level=0.95):
    """Clopper-Pearson, exact."""
    lo = beta.ppf((1 - level) / 2, x, n - x + 1) if x else 0.0
    hi = beta.ppf(1 - (1 - level) / 2, x + 1, n - x) if x < n else 1.0
    return lo, hi


def containment_tail_p(x, n, nominal):
    return float(binom.cdf(x, n, nominal))
'''


def names(vs) -> set[str]:
    return {v.check for v in vs}


# ==========================================================================
# 1. Manifest and regeneration -- spec §10.1 item 7
# ==========================================================================

REQUIRED_MANIFEST_KEYS = ("source_hashes", "code_commit", "config", "environment",
                          "seed_policy")


@pytest.mark.parametrize("missing", REQUIRED_MANIFEST_KEYS)
def test_every_required_manifest_key_is_required(tmp_path, missing):
    """Source hash, commit, config, package environment, seed policy. Drop any one
    and the release stops being reproducible; the validator must say which."""
    man = clean_manifest(tmp_path, {"a.py": "x = 1\n"})
    man.pop(missing)
    out = val.check_manifest_regenerates(man, tmp_path)
    assert names(out) == {"manifest_regeneration"}
    assert missing in " ".join(v.detail for v in out)


def test_a_complete_manifest_over_unmodified_sources_is_silent(tmp_path):
    man = clean_manifest(tmp_path, {"a.py": "x = 1\n", "b/c.py": "y = 2\n"})
    assert val.check_manifest_regenerates(man, tmp_path) == []


def test_a_deliberate_one_character_source_mismatch_fails_the_analysis(tmp_path):
    """The core reproducibility claim. Change one byte of one file the manifest
    covers and the release must not validate -- §10.1 item 7."""
    man = clean_manifest(tmp_path, {"a.py": "x = 1\n", "b/c.py": "y = 2\n"})
    (tmp_path / "b" / "c.py").write_text("y = 3\n")
    out = val.check_manifest_regenerates(man, tmp_path)
    assert names(out) == {"manifest_regeneration"}
    assert "b/c.py" in " ".join(v.location + v.detail for v in out)
    assert len(out) == 1, "only the changed file should be reported"


def test_a_source_named_in_the_manifest_but_absent_is_a_violation(tmp_path):
    man = clean_manifest(tmp_path, {"a.py": "x = 1\n"})
    man["source_hashes"]["gone.py"] = "0" * 64
    out = val.check_manifest_regenerates(man, tmp_path)
    assert names(out) == {"manifest_regeneration"}
    assert "gone.py" in " ".join(v.location for v in out)


def test_an_empty_source_hash_map_is_a_violation(tmp_path):
    """A manifest that hashes nothing hashes nothing honestly, and pins nothing."""
    man = clean_manifest(tmp_path, {})
    assert names(val.check_manifest_regenerates(man, tmp_path)) == {"manifest_regeneration"}


def test_a_package_environment_without_packages_is_a_violation(tmp_path):
    man = clean_manifest(tmp_path, {"a.py": "x = 1\n"})
    man["environment"] = {"python": "3.11.9"}
    out = val.check_manifest_regenerates(man, tmp_path)
    assert names(out) == {"manifest_regeneration"}


# ==========================================================================
# 2. Claim language -- spec §9.1, kill ledger §10
# ==========================================================================

def _claims(text, ledger=None):
    return val.check_claim_language(text, ledger or clean_ledger())


def failing_ledger(*ids, status="FAIL") -> dict:
    led = clean_ledger()
    for e in led["entries"]:
        if e["id"] in ids:
            e["status"] = status
    return led


def test_a_claim_word_whose_kill_did_not_pass_is_a_violation():
    out = _claims("SPADE outperforms sobol on the map (KF-6).", failing_ledger("KF-6"))
    assert names(out) == {"claim_language"}
    assert "KF-6" in out[0].detail


@pytest.mark.parametrize("status", ["FAIL", "INCONCLUSIVE", "NOT_RUN", "MOOT"])
def test_only_pass_licenses_a_claim(status):
    """§10: a ledger item resolves to one of five states and exactly one of them
    licenses the word. INCONCLUSIVE especially -- §7.1, non-significance is not
    proof of validity."""
    text = "The certificate is certified in C1 (KF-1)."
    out = _claims(text, failing_ledger("KF-1", status=status))
    assert names(out) == {"claim_language"}


def test_a_claim_word_whose_kill_passed_is_allowed():
    assert _claims("SPADE outperforms sobol on the map (KF-6).") == []


def test_an_unattributed_claim_word_is_a_violation():
    """A claim with no registered decision behind it cannot be checked against
    one, so it is refused rather than assumed innocent."""
    out = _claims("SPADE outperforms sobol on the map.")
    assert names(out) == {"claim_language"}
    assert "no kill-ledger" in out[0].detail.lower()


def test_a_negated_claim_is_not_a_claim():
    assert _claims("SPADE did not outperform sobol on the map.") == []


def test_negation_is_case_insensitive():
    assert _claims("The region is NOT certified beyond hill.") == []


def test_a_blockquoted_withdrawal_is_not_a_claim():
    """§29.4's form: withdrawals are quoted, and quoting the sentence being
    withdrawn must not itself trip the guard."""
    assert _claims("> Withdrawn: SPADE outperforms every baseline everywhere.") == []


def test_a_backticked_identifier_is_not_a_claim():
    """`murphy_calibration` is a column in ROW_SCHEMA, not an assertion that
    anything is calibrated."""
    assert _claims("We report `murphy_calibration` and `oracle_best_regret`.") == []


def test_a_fenced_code_block_is_not_a_claim():
    text = "```\nverdict = 'certified' if p > 0.05 else 'best'\n```\n"
    assert _claims(text) == []


def test_a_short_quoted_mention_is_not_a_claim():
    """Quoting the guard list itself, as §9 does, must not trip the guard."""
    text = 'The validator hard-fails on "best", "winner", "certified".'
    assert _claims(text) == []


def test_a_long_quoted_sentence_is_still_a_claim():
    """A four-word exemption for mentions is not a licence to launder a claim by
    wrapping it in quotation marks."""
    out = _claims('The abstract says "SPADE outperforms every strong BO baseline here".')
    assert names(out) == {"claim_language"}


def test_negation_does_not_leak_across_a_clause_boundary():
    """THE discriminating case. A negation earlier in the sentence must not
    license a positive claim in the next clause -- that is how a paragraph that
    reads as balanced ships an unsupported headline."""
    text = "SPADE did not win on regret, and m0 outperforms random_plate2."
    out = _claims(text, failing_ledger("KF-3"))
    assert names(out) == {"claim_language"}
    assert "outperforms" in out[0].detail


def test_a_non_prefixed_negation_is_a_negation():
    assert _claims("The difference was non-significant at both units.") == []


def test_oracle_best_is_a_registered_term_not_a_claim():
    assert _claims("Rule P beats the oracle-best ceiling in C2 (KF-8).") == []
    assert _claims("Regret is decomposed against oracle-best.") == []


def test_the_clean_findings_document_passes():
    assert _claims(CLEAN_FINDINGS) == []


# ==========================================================================
# 3. Tables -- spec §9.2
# ==========================================================================

TABLE_OK = """\
Caption: containment by arm, condition C1, terminal rule P.

| condition | arm | terminal rule | regret | containment | n |
|---|---|---|---|---|---|
| C1 | spade_cf_m0 | P | 0.10 | 96/100 | 100 |
"""


def test_a_complete_results_table_is_silent():
    assert val.check_table_completeness(TABLE_OK) == []


def test_a_results_table_without_a_condition_label_is_a_violation():
    text = TABLE_OK.replace("| condition | arm", "| arm").replace(
        "| C1 | spade_cf_m0", "| spade_cf_m0").replace(
        "|---|---|---|---|---|---|", "|---|---|---|---|---|").replace(
        "Caption: containment by arm, condition C1, terminal rule P.",
        "Caption: containment by arm, terminal rule P.")
    out = val.check_table_completeness(text)
    assert names(out) == {"table_completeness"}
    assert "condition" in out[0].detail


def test_a_regret_table_without_a_terminal_rule_is_a_violation():
    """§7.4: comparing rule A for one arm against rule P for another is a protocol
    violation, and a table that never names its rule cannot be checked for it."""
    text = """\
Caption: regret by arm, condition C1.

| condition | arm | regret |
|---|---|---|
| C1 | spade_cf_m0 | 0.10 |
"""
    out = val.check_table_completeness(text)
    assert names(out) == {"table_completeness"}
    assert "terminal rule" in out[0].detail


def test_a_containment_table_without_a_denominator_is_a_violation():
    """§11: reporting a certificate rate without its non-empty denominator is a
    prohibited action."""
    text = """\
Caption: containment by arm, condition C1, terminal rule P.

| condition | arm | containment |
|---|---|---|
| C1 | spade_cf_m0 | 0.96 |
"""
    out = val.check_table_completeness(text)
    assert names(out) == {"table_completeness"}
    assert "denominator" in out[0].detail


def test_a_table_that_reports_no_registered_metric_is_not_subject():
    """The arm registry is a table of definitions. Demanding a denominator of it
    would train the reader to ignore the guard."""
    text = """\
| arm | family | rounds | mandatory |
|---|---|---|---|
| sobol | space-filling | 1 | yes |
"""
    assert val.check_table_completeness(text) == []


def test_the_clean_findings_document_has_complete_tables():
    assert val.check_table_completeness(CLEAN_FINDINGS) == []


# ==========================================================================
# 4. Same-draw containment -- spec §9.3, FINDINGS §29.3
# ==========================================================================

def test_same_draw_presented_as_primary_is_a_violation():
    text = "Our primary containment endpoint is same-draw containment, at 0.98."
    out = val.check_same_draw_not_primary(text)
    assert names(out) == {"same_draw_primacy"}


def test_a_containment_table_with_same_draw_but_no_crossfit_column_is_a_violation():
    """§29.3 measured the two differing by up to 3.5 points. A table showing only
    the flattering one hides exactly that gap."""
    text = """\
Caption: containment, condition C1, terminal rule P.

| condition | arm | same-draw containment | n |
|---|---|---|---|
| C1 | spade_cf_m0 | 98/100 | 100 |
"""
    out = val.check_same_draw_not_primary(text)
    assert names(out) == {"same_draw_primacy"}
    assert "cross-fit" in out[0].detail


def test_same_draw_labelled_a_diagnostic_is_silent():
    text = ("Cross-fit containment is primary; same-draw containment is reported "
            "beside it as a non-primary diagnostic.")
    assert val.check_same_draw_not_primary(text) == []


def test_the_clean_findings_document_does_not_promote_same_draw():
    assert val.check_same_draw_not_primary(CLEAN_FINDINGS) == []


# ==========================================================================
# 5. Normal approximation in certificate inference -- spec §9.4, FINDINGS §22
# ==========================================================================

def test_the_exact_analysis_source_is_silent():
    assert val.check_no_normal_approximation(CLEAN_ANALYSIS) == []


def test_importing_scipy_stats_norm_is_a_hard_failure():
    src = CLEAN_ANALYSIS.replace("from scipy.stats import beta, binom",
                                 "from scipy.stats import beta, binom, norm")
    out = val.check_no_normal_approximation(src)
    assert names(out) == {"normal_approximation"}


def test_a_z_constant_inside_a_containment_function_is_a_hard_failure():
    src = CLEAN_ANALYSIS + '''

def containment_ci_fast(p, n):
    """A quicker interval for the containment table."""
    return p - 1.96 * (p * (1 - p) / n) ** 0.5, p + 1.96 * (p * (1 - p) / n) ** 0.5
'''
    out = val.check_no_normal_approximation(src)
    assert names(out) == {"normal_approximation"}
    assert "containment_ci_fast" in out[0].location


def test_a_z_constant_outside_certificate_inference_is_not_flagged():
    """1.96 is the straddle band's own constant (§5.1). Flagging it everywhere
    would make the guard noise, and noise gets switched off."""
    src = CLEAN_ANALYSIS + '''

def straddle_fraction(mean, sd, theta):
    """The band plate 2 exists to resolve -- spec §5.1, not an inference."""
    return ((mean - theta).abs() <= 1.96 * sd).double().mean()
'''
    assert val.check_no_normal_approximation(src) == []


def test_proportion_confint_with_a_non_exact_method_is_a_hard_failure():
    src = CLEAN_ANALYSIS + '''

def containment_interval_2(x, n):
    from statsmodels.stats.proportion import proportion_confint
    return proportion_confint(x, n, method="wilson")
'''
    out = val.check_no_normal_approximation(src)
    assert names(out) == {"normal_approximation"}


def test_proportion_confint_with_method_beta_is_clopper_pearson_and_allowed():
    src = CLEAN_ANALYSIS + '''

def containment_interval_2(x, n):
    from statsmodels.stats.proportion import proportion_confint
    return proportion_confint(x, n, method="beta")
'''
    assert val.check_no_normal_approximation(src) == []


def test_a_warning_about_normal_approximations_in_prose_is_not_a_violation():
    """The docstring of the clean source says 'never a normal approximation'. A
    guard that cannot tell a warning from the thing it warns about is useless in
    exactly the file most likely to carry the warning."""
    src = ('"""Holm is computed on the exact tail, never a normal approximation '
           'and never a z of 1.96 -- FINDINGS §22."""\n' + CLEAN_ANALYSIS)
    assert val.check_no_normal_approximation(src) == []


def test_certificate_inference_with_no_exact_tail_anywhere_is_a_violation():
    """§8: containment inference is EXACT. A file that computes containment and
    never touches scipy.stats.binom has computed it some other way."""
    src = '''
def containment_rate(x, n):
    """The certificate containment proportion."""
    return x / n
'''
    out = val.check_no_normal_approximation(src)
    assert names(out) == {"normal_approximation"}
    assert "exact" in out[0].detail.lower()


def test_a_missing_analysis_source_is_not_a_normal_approximation():
    assert val.check_no_normal_approximation(None) == []


# ==========================================================================
# 6. Suppressed failures, exceptions, unrankable cells, unavailable arms -- §9.5
# ==========================================================================

def _suppress(findings, ledger=None, feas=None, bench=None):
    return val.check_no_suppressed_failures(
        findings, ledger or clean_ledger(), feas or clean_feasibility(),
        bench or clean_benchmark())


def test_a_failed_kill_that_the_findings_never_mention_is_suppression():
    out = _suppress(CLEAN_FINDINGS, ledger=failing_ledger("KF-3"))
    assert names(out) == {"suppressed_failure"}
    assert "KF-3" in out[0].detail


def test_a_failed_kill_that_the_findings_do_mention_is_disclosed():
    text = CLEAN_FINDINGS + "\nKF-3 FAILED: targeted plate 2 did not earn its complexity.\n"
    assert _suppress(text, ledger=failing_ledger("KF-3")) == []


def test_an_infeasible_condition_that_is_never_mentioned_is_suppression():
    feas = clean_feasibility()
    feas["rows"].append({"condition_id": "S2", "tier": "secondary", "family": "levy",
                         "dimension": 6, "sigma": 0.25, "regime_class": "INFEASIBLE",
                         "classification_reason": "tau above ceiling"})
    out = _suppress(CLEAN_FINDINGS, feas=feas)
    assert names(out) == {"suppressed_failure"}
    assert "S2" in out[0].detail


def test_an_exception_condition_that_is_never_mentioned_is_suppression():
    """§5.3/§41: ackley is the pre-declared exception and is reported plainly."""
    feas = clean_feasibility()
    feas["rows"].append({"condition_id": "S1", "tier": "secondary", "family": "ackley",
                         "dimension": 6, "sigma": 0.25, "regime_class": "EXCEPTION",
                         "classification_reason": "centre-point optimum"})
    out = _suppress(CLEAN_FINDINGS, feas=feas)
    assert names(out) == {"suppressed_failure"}
    assert "S1" in out[0].detail


def test_an_unavailable_arm_that_is_never_mentioned_is_suppression():
    """§4: doe_unscreened at d=8 is recorded unavailable, never approximated into
    existence -- and never dropped from the write-up either."""
    bench = clean_benchmark()
    for r in bench["rows"]:
        if r["arm"] == "doe_unscreened" and r["condition_id"] == "C4":
            r["unavailable_reason"] = "second-order RSM infeasible at shared budget"
    out = _suppress(CLEAN_FINDINGS, bench=bench)
    assert names(out) == {"suppressed_failure"}
    assert "doe_unscreened" in out[0].detail


def test_an_unrankable_cell_that_is_never_mentioned_is_suppression():
    """§9.4: 18 of 18 *rankable* cells, not 24 of 24 -- six had no ranking, and
    the difference is the whole claim."""
    bench = clean_benchmark()
    bench["rows"][0]["rankable"] = False
    out = _suppress(CLEAN_FINDINGS, bench=bench)
    assert names(out) == {"suppressed_failure"}
    assert "rankable" in out[0].detail.lower()


def test_a_fully_disclosed_release_is_silent():
    assert _suppress(CLEAN_FINDINGS) == []


# ==========================================================================
# 7. Universal claims -- spec §9.6
# ==========================================================================

@pytest.mark.parametrize("phrase", ["always", "in all settings", "universally",
                                    "everywhere", "any landscape"])
def test_a_universal_claim_on_target_only_evidence_is_a_violation(phrase):
    text = f"SPADE {phrase} produces a valid certificate."
    out = val.check_no_universal_claims(text, clean_feasibility())
    assert names(out) == {"universal_claim"}


def test_a_target_scoped_claim_is_not_universal():
    text = "In TARGET regimes SPADE always produced a non-empty certificate."
    assert val.check_no_universal_claims(text, clean_feasibility()) == []


def test_a_negated_universal_is_allowed():
    """§1: the claim this study may never support is that SPADE beats Sobol
    everywhere. Saying so is the opposite of claiming it."""
    text = "This study does not show that SPADE wins everywhere."
    assert val.check_no_universal_claims(text, clean_feasibility()) == []


def test_a_blockquoted_universal_is_allowed():
    assert val.check_no_universal_claims(
        "> The claim this study may never support: SPADE wins in all settings.",
        clean_feasibility()) == []


def test_the_clean_findings_document_makes_no_universal_claim():
    assert val.check_no_universal_claims(CLEAN_FINDINGS, clean_feasibility()) == []


# ==========================================================================
# 8. alpha_star -- spec §9.7, FINDINGS §28 and §31
# ==========================================================================

def test_alpha_star_offered_as_certificate_quality_is_a_violation():
    text = "SPADE's alpha_star of 0.79 shows the quality of its certificate."
    out = val.check_alpha_star_not_quality_evidence(text)
    assert names(out) == {"alpha_star_misuse"}
    assert "§28" in out[0].section or "28" in out[0].section


def test_alpha_star_ranking_arms_is_a_violation():
    """§28: no ranking, no claim, and no kill condition may rest on it."""
    text = "Ranking the arms by α* puts spade_cf_m0 first on certificate validity."
    assert names(val.check_alpha_star_not_quality_evidence(text)) == {"alpha_star_misuse"}


def test_alpha_star_labelled_willingness_to_certify_is_silent():
    text = ("`alpha_star` is MODEL-INTERNAL: it measures willingness to certify, "
            "not certificate quality.")
    assert val.check_alpha_star_not_quality_evidence(text) == []


def test_a_document_that_never_mentions_alpha_star_is_silent():
    assert val.check_alpha_star_not_quality_evidence("No such statistic here.") == []


# ==========================================================================
# 9. Mandatory comparators -- spec §4, §13.6
# ==========================================================================

def test_a_missing_mandatory_arm_in_a_primary_condition_is_a_violation():
    bench = clean_benchmark()
    bench["rows"] = [r for r in bench["rows"]
                     if not (r["arm"] == "qlognei" and r["condition_id"] == "C2")]
    out = val.check_mandatory_comparators(bench, clean_feasibility())
    assert names(out) == {"mandatory_comparator"}
    assert "qlognei" in out[0].detail and "C2" in out[0].location


def test_the_q57_trap_arm_is_mandatory():
    """§4.2b: a headline that holds against qLogEI and dies against the noisy
    acquisition. Running only the weaker one manufactures a win."""
    bench = clean_benchmark()
    bench["rows"] = [r for r in bench["rows"] if r["arm"] != "qlognei"]
    out = val.check_mandatory_comparators(bench, clean_feasibility())
    assert len(out) == 4, "one violation per primary condition"


def test_a_missing_arm_with_a_structured_unavailable_reason_is_allowed():
    bench = clean_benchmark()
    for r in bench["rows"]:
        if r["arm"] == "doe_unscreened" and r["condition_id"] == "C4":
            r["unavailable_reason"] = "second-order RSM infeasible at shared budget"
    assert val.check_mandatory_comparators(bench, clean_feasibility()) == []


def test_an_infeasible_condition_requires_no_arms():
    """§10 KF-9: an above-ceiling cell is excluded pre-run and is never a method
    failure -- so it is not a missing-comparator failure either."""
    feas = clean_feasibility()
    feas["rows"][0]["regime_class"] = "INFEASIBLE"
    bench = clean_benchmark()
    bench["rows"] = [r for r in bench["rows"] if r["condition_id"] != "C1"]
    assert val.check_mandatory_comparators(bench, feas) == []


def test_a_complete_arm_registry_is_silent():
    assert val.check_mandatory_comparators(clean_benchmark(), clean_feasibility()) == []


# ==========================================================================
# 10. The validator as a program
# ==========================================================================

def test_a_clean_release_tree_exits_zero(tmp_path):
    write_release(tmp_path)
    r = subprocess.run([sys.executable, str(VALIDATOR_PATH), "--root", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_violating_release_exits_non_zero_and_prints_every_violation(tmp_path):
    """Not the first violation. All of them -- a validator that stops at the first
    turns one review pass into nine."""
    findings = CLEAN_FINDINGS + (
        "\nSPADE outperforms every baseline and is always calibrated.\n"
        "Its alpha_star establishes the quality of the certificate.\n")
    write_release(tmp_path, findings=findings, ledger=failing_ledger("KF-6"))
    r = subprocess.run([sys.executable, str(VALIDATOR_PATH), "--root", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    for check in ("claim_language", "universal_claim", "alpha_star_misuse"):
        assert check in r.stdout, f"{check} missing from output:\n{r.stdout}"


def test_a_missing_artefact_is_itself_a_violation(tmp_path):
    write_release(tmp_path)
    (tmp_path / "results" / "final-spade-kill-ledger.json").unlink()
    r = subprocess.run([sys.executable, str(VALIDATOR_PATH), "--root", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "kill-ledger" in r.stdout


def test_pre_release_mode_skips_absent_artefacts_without_passing_them(tmp_path):
    """The study has not run. The validator has to be runnable before it can be
    satisfied, or it gets written after the results exist -- which is the failure
    mode the whole registration is built against."""
    write_release(tmp_path)
    (tmp_path / "results" / "final-spade-benchmark.json").unlink()
    r = subprocess.run([sys.executable, str(VALIDATOR_PATH), "--root", str(tmp_path),
                        "--pre-release"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "SKIP" in r.stdout


def test_every_registered_check_is_wired_into_the_run():
    """A check function nobody calls is a check nobody runs."""
    assert set(val.CHECKS) == {
        "claim_language", "table_completeness", "same_draw_primacy",
        "normal_approximation", "suppressed_failure", "universal_claim",
        "alpha_star_misuse", "mandatory_comparator", "manifest_regeneration"}


def test_every_check_names_the_spec_section_it_enforces():
    for name, spec in val.CHECKS.items():
        assert "§" in spec.section, f"{name} does not cite a section"


# ==========================================================================
# 11. Figures -- read committed artefacts, never recompute
# ==========================================================================

def artefact_dir(tmp_path: Path) -> Path:
    d = tmp_path / "results"
    d.mkdir(parents=True, exist_ok=True)
    for name, obj in (("kill-ledger", clean_ledger()),
                      ("feasibility", clean_feasibility()),
                      ("benchmark", clean_benchmark()),
                      ("certificates", clean_certificates())):
        (d / f"final-spade-{name}.json").write_text(json.dumps(obj))
    return d


def test_figures_never_import_the_campaign_machinery():
    """A figure module that can reach the oracle can draw a number that is in no
    committed artefact, and nothing downstream can tell."""
    src = FIGURES_PATH.read_text()
    for forbidden in ("BiphasicOracle", "build_gp", "boec.runner", "boec.lse",
                      "boec.vorobev", "conservative_estimate", "import torch",
                      "batch_lse", "family_evaluator"):
        assert forbidden not in src, f"figures reach {forbidden} -- they must not"


def test_figures_read_only_committed_final_spade_artefacts(tmp_path):
    """Every path the module opens is a results/final-spade-*.json."""
    for key in figs.ARTEFACTS.values():
        assert key.startswith("final-spade-") and key.endswith(".json"), key


def test_every_figure_is_written_from_synthetic_artefacts(tmp_path):
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    assert set(out) == set(figs.FIGURES)
    for name, rendered in out.items():
        assert rendered is not None, f"{name} skipped on complete inputs"
        assert rendered.path.exists() and rendered.path.stat().st_size > 5000, name


def test_a_missing_artefact_skips_the_figure_with_a_message(tmp_path, capsys):
    d = artefact_dir(tmp_path)
    (d / "final-spade-certificates.json").unlink()
    out = figs.make_all_figures(d, tmp_path / "fig")
    assert out["crossfit_containment"] is None
    assert out["same_draw_vs_crossfit"] is None
    assert out["pareto"] is not None, "the pareto figure does not need certificates"
    printed = capsys.readouterr().out
    assert "SKIP" in printed and "final-spade-certificates.json" in printed


def test_no_figure_invents_data_when_its_artefact_is_absent(tmp_path):
    for name in ("benchmark", "certificates", "feasibility"):
        d = artefact_dir(tmp_path / name)
        (d / f"final-spade-{name}.json").unlink()
        figs.make_all_figures(d, tmp_path / name / "fig")  # must not raise


def test_every_figure_caption_names_its_condition_terminal_rule_and_n(tmp_path):
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    for name, r in out.items():
        cap = r.caption
        assert "n=" in cap, f"{name} caption has no n: {cap}"
        assert ("condition" in cap.lower() or "C1" in cap or "TARGET" in cap), cap
        assert ("rule" in cap.lower() or "n/a" in cap.lower()), \
            f"{name} caption does not name a terminal rule: {cap}"


def test_the_pareto_figure_encodes_all_four_channels(tmp_path):
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    enc = out["pareto"].encoding
    assert enc["x"] == "regret_rule_p"
    assert enc["y"] == "symmetric_difference_pred"
    assert enc["shape"] == "rounds"
    assert enc["colour"] == "arm_family"
    assert enc["fill"] == "certificate_status_alpha_0.95"
    assert enc["label"] == "arm"


def test_the_pareto_caption_states_the_regret_map_disagreement(tmp_path):
    """The paper's central figure exists to make visible that the lowest-regret
    arm need not be the best-map arm. The synthetic fixture is built so those are
    different arms; the caption must say which two."""
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    cap = out["pareto"].caption
    assert "spade_cf_m0" in cap and "doe_unscreened" in cap, cap


def test_the_containment_figure_carries_denominators_and_the_nominal_line(tmp_path):
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    r = out["crossfit_containment"]
    assert "/100" in " ".join(r.annotations), r.annotations
    assert r.reference_lines, "nominal assurance must be drawn as a reference line"
    assert 0.95 in r.reference_lines and 0.80 in r.reference_lines


def test_the_same_draw_diagnostic_draws_the_identity_line(tmp_path):
    out = figs.make_all_figures(artefact_dir(tmp_path), tmp_path / "fig")
    assert out["same_draw_vs_crossfit"].encoding["identity_line"] is True


def test_the_condition_figure_separates_the_three_regime_classes(tmp_path):
    d = artefact_dir(tmp_path)
    feas = clean_feasibility()
    feas["rows"].append({"condition_id": "S1", "tier": "secondary", "family": "ackley",
                         "dimension": 6, "sigma": 0.25, "regime_class": "EXCEPTION",
                         "tau_frac": 0.60, "tau_raw": 0.6, "tau_max_worst": 0.9,
                         "worst_gamma": 0.95, "true_prevalence": 0.2,
                         "boundary_frac": 0.1, "expected_nonempty_rate": 0.1,
                         "classification_reason": "centre-point optimum"})
    (d / "final-spade-feasibility.json").write_text(json.dumps(feas))
    out = figs.make_all_figures(d, tmp_path / "fig")
    assert set(out["cross_condition"].encoding["groups"]) == {
        "TARGET", "ROBUSTNESS", "EXCEPTION"}


def test_the_tau_max_figure_shows_excluded_cells_rather_than_dropping_them(tmp_path):
    """§10 KF-9: an above-ceiling cell is excluded pre-run. Excluding it from the
    figure too would make the exclusion invisible, which is what §4.5 punished."""
    d = artefact_dir(tmp_path)
    feas = clean_feasibility()
    feas["rows"][3]["regime_class"] = "INFEASIBLE"
    feas["rows"][3]["tau_raw"] = 0.95
    (d / "final-spade-feasibility.json").write_text(json.dumps(feas))
    out = figs.make_all_figures(d, tmp_path / "fig")
    assert out["threshold_feasibility"].encoding["excluded_shown"] is True
    assert out["threshold_feasibility"].encoding["n_excluded"] == 1
