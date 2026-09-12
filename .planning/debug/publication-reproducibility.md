---
status: dependency_fix_verified_historical_failures_unresolved
trigger: "Make the codebase ready for publishing; investigate frozen dependency digests and eight historical replay/calibration failures."
created: 2026-09-07
updated: 2026-09-09
---

## Current Focus

2026-09-09 submission pass: fresh two-test run reproduced both historical failures in
11.03 seconds. `test_full_space_rule_p_reproduces_fix1` returned 0.25251124591423746
versus stored 0.2525116337195932 for `033466197eba3ddb`, seed 0. That reference column
feeds Figure 2. The calibration checkpoint test wrote its output successfully, then
intentionally exited on 48 exact-map differences (worst 9.082e-13); regret-gate failures
and changed latent-map cells were zero. This is not a checkpoint-writer crash.
Source tracing also corrected a manuscript error: Fix 1 uses a common GP for every arm,
with twenty restarts / 4,096 raw starts, not an arm-specific quadratic RSM readout.
The manuscript correction changes interpretation only, not stored numerical results.
No underlying replay cause has been established and no equality gate was relaxed.

hypothesis: Adding three document-only dependencies to the digest-bound scientific requirements file invalidates the development and release provenance checks.
test: Run the existing frozen-design digest test before changing dependencies, compare the requirements diff with its committed version, then restore the scientific bytes and move the additions to an optional publication requirements file.
expecting: The existing scientific SHA-256 matches again without modifying any frozen manifest; document builds retain their pinned dependencies.
next_action: Preserve the verified dependency separation. Historical campaign replay remains a distinct unresolved investigation; do not change frozen evidence or relax exact equality checks to make the suite green.

reasoning_checkpoint:
  hypothesis: Three manuscript-only pins alter requirements.txt bytes and therefore invalidate the registered requirements_sha256, although the scientific pins themselves were not changed.
  confirming_evidence:
    - The working diff adds only the three document dependencies and their heading.
    - The existing frozen-design test fails on requirements_sha256 (expected 96a00b1abb366bd48318d7957703608b348393aa280a6808ef91652c28471687; actual 5a372f38df6106e8e26831b023fc875dad7b7b839056fa4cf557d5ef09ecd70e).
  falsification_test: If removing only those added lines does not restore the exact frozen SHA and pass the same test, the additions are not the sole cause.
  fix_rationale: Separate optional publication tooling from the immutable scientific dependency surface while retaining all requested pins and normal installation through -r requirements.txt.
  blind_spots: This addresses dependency-file identity, not clean-environment installation or the unrelated historical replay mismatches.

## Symptoms

expected: Publication preparation retains the registered scientific environment and reports reproducibility faithfully; all manuscript dependencies remain installable.
actual: Latest full suite reports 25 failures, including 17 frozen requirements digest failures and eight previously documented replay/calibration failures.
errors: requirements_sha256 mismatch; exact floating-point replay mismatches; three material adaptive qLogEI/qLogNEI mismatches; P7 map fidelity stop gate.
reproduction: Run the named test cases in tests/test_spade_study.py, test_spade_development.py, test_spade_release.py, test_calibration.py, test_d23_doe_subspace.py, test_p4_coord.py, test_q59_map_rescore.py, test_replay.py, and test_spread_gp.py using .venv/bin/python -m pytest.
started: Requirements digest failures followed manuscript dependency additions; eight historical failures are documented before SPADE implementation.

## Eliminated

## Evidence

- checked: requirements.txt working diff
  found: Only python-docx==1.2.0, latex2mathml==3.79.0, mathml2omml==0.0.2 and their heading/spacing were added.
  implication: Document tooling can be separated without changing the frozen scientific dependency file.
- checked: .planning/STATE.md and .planning/codebase/CONCERNS.md
  found: Eight historical failures were reproduced from pre-SPADE commit 02a6bfa in the same environment, including three large adaptive mismatches and five numerical/stop-gate failures.
  implication: They are not caused by the document dependency additions; never erase them by loosening evidence gates.
- checked: Required GSD reference locations
  found: The four referenced files under /Users/alanakwan/.Codex/gsd-core/references are absent, and filename discovery under .codex/.agents found no copies.
  implication: Use the supplied debugger protocol plus the completely read systematic-debugging and verification-before-completion skills as fallback.
- checked: Existing frozen-design digest test, before fix
  found: One failure at tests/test_spade_study.py:763; the requirements digest is the differing frozen value.
  implication: The dependency hypothesis has a direct failing reproduction.

## Resolution

root_cause: Three document-only dependency additions changed the bytes of the registered scientific requirements file, invalidating 17 provenance checks.
fix: Restored requirements.txt to its committed bytes and moved document-only pins into requirements-publication.txt, which includes the unchanged scientific requirements.
verification: Full suite completed with 2,428 passed and the same eight historical failures (940.40 seconds); all 17 requirements-related failures are resolved. All nine prospective release checks pass. Original SHA-256 96a00b1abb366bd48318d7957703608b348393aa280a6808ef91652c28471687 is restored. Word generation succeeds with the separated toolchain.
files_changed: [requirements.txt, requirements-publication.txt]

Historical failures remain in test_calibration, test_d23_doe_subspace, test_p4_coord,
test_q59_map_rescore, three test_replay cases, and test_spread_gp. They include five
numerical/stop-gate discrepancies and three material adaptive qLogEI/qLogNEI trajectory
mismatches. No tolerance, scientific reference artifact, or frozen manifest was changed.
The manuscript and README distinguish archived-row reanalysis from exact campaign replay.
