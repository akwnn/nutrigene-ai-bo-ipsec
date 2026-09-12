---
status: investigating
trigger: "Diagnose the three historical adaptive test_replay.py failures without weakening tests, replacing references, running new study grids, or accessing lockbox outcomes."
created: 2026-09-10
updated: 2026-09-11
---

## Current Focus

hypothesis: A later sampler-seed change is a proven additional divergence; the original historical mismatch remains unidentified. No evidence supports calling it only an environment problem.
test: Completed current/legacy sampler comparisons for all three first-failing campaigns and a one-versus-four-thread legacy Hartmann6 control. Fresh original tests still fail.
expecting: A recovered generating environment, exact dirty source snapshot, or original campaign trace is needed to isolate the remaining historical divergence. Do not search seeds until a reference happens to match.
next_action: If further historical recovery is authorized and original provenance becomes available, compare the first initialization/model/acquisition trace against it. Keep all scientific defaults, tests and reference results unchanged meanwhile.

## Symptoms

expected: Historical family qLogEI/qLogNEI regeneration exactly equals the retained Q42/Q59 Rule A regret columns.
actual: Hartmann6 qLogEI seed 0 differs by 0.033954554533606185, Ackley qLogEI seed 0 by 0.1721093109374322, Hartmann6 qLogNEI seed 0 by 0.02527916780343853 in the existing audit.
errors: Three exact-equality assertions fail in tests/test_replay.py.
reproduction: Run only the three failing small test campaigns or equivalent diagnostic replay under .venv/bin/python; output diagnostics to /private/tmp.
started: Present before SPADE implementation and reproduced in pre-SPADE commit 02a6bfa according to the retained state and audit.

## Eliminated

- hypothesis: Restoring pre-01d2ea5 sampler behavior alone recovers the historical Hartmann6 Q42 reference.
  evidence: Legacy sampler replay at one thread returns 0.19391397009622446, exactly the older audit mismatch, not retained 0.22786852462983065.
  timestamp: 2026-09-10

## Evidence

- checked: `.venv/bin/python /private/tmp/diagnose-adaptive-replay-20260910.py --family hartmann6 --arm qlogei --sampler current --threads 1` and the same command with `--sampler legacy`.
  found: Current regret 0.3038381093602984; legacy 0.19391397009622446; reference 0.22786852462983065. Initial X/Y/Yvar and fitted-model SHA-256 match. The first current sampler seed is 0 with unchanged RNG state; historical semantics draw seed 136044 and advance RNG. First adaptive batch after n=14 has different points and RNG state. Full diagnostics are in /private/tmp/adaptive-hartmann6-qlogei-{current,legacy}-t1.json.
  implication: Commit 01d2ea5 proves a new compatibility divergence at the first acquisition, but the original historical mismatch remains. Existing audit values describe old sampler behavior, not current replay.

- checked: Read-only git history/diffs across 74d0b4d (Q42), 98c043c (Q59), 02a6bfa (pre-SPADE), and 01d2ea5 (2026-08-25).
  found: The relevant historical adaptive modules are identical between 98c043c and 02a6bfa. 01d2ea5 adds sampler_seed=0 and passes it to SobolQMCNormalSampler. The installed sampler previously chose int(torch.randint(0, 1000000, (1,)).item()).
  implication: There is a concrete RNG/configuration change to test, separate from the earlier environment-dependent failures.
- checked: Original Q42/Q59 generators and retained Q59 provenance.
  found: Both generators set OMP_NUM_THREADS=1 and torch.set_num_threads(1); direct .venv Python uses Torch 4 threads / interop 10. Q59 provenance records git_dirty=true at e2b9e7b and matching current package versions, but no platform/BLAS/RNG/trajectory capture. Q42 has rows and summaries without provenance. Neither artifact stores X/Y/model states or first-round traces.
  implication: Thread count is another concrete differentiating variable; matching version strings does not identify the generating numerical binary/environment or dirty source bytes.

- checked: .planning/STATE.md, .planning/ROADMAP.md, .planning/debug/publication-reproducibility.md, tests/test_replay.py and scripts/audit_historical_replay.py
  found: Scientific state is NO_SELECTION and FROZEN_UNOPENED. Adaptive gates use exact Rule A scalar equality, fresh family evaluators, Q42 bo_a and Q59 arms.qlognei.rule_a. Audit observations are recorded values, not a fresh execution.
  implication: Preserve gates and retained references; investigate upstream campaign generation independently of the known fixed-design numerical drifts.
- checked: Required GSD reference files under /Users/alanakwan/.Codex/gsd-core/references
  found: All five referenced files are absent. The installed systematic-debugging/SKILL.md was read completely and used as fallback.
  implication: Follow scientific hypothesis testing and persist findings in this owned debug file; no implementation changes are authorized.

## Resolution

root_cause: Additional compatibility cause confirmed at the first acquisition (01d2ea5 sampler seed). Original historical discrepancy unconfirmed.
fix: None; diagnose-only.
verification: Three original adaptive tests fail in 22.78 seconds; current and legacy single-key diagnostics completed without edits to scientific source or references.
files_changed: [.planning/debug/replay-adaptive-2026-09-10.md]

## Completed probes — 2026-09-11

All rows below are the **same existing failing seed-0 cases**, d=6 and sigma_rel=0.25.
They are diagnostic reruns, not new study evidence. Lower regret is not a license to
replace the reference with a favorable rerun.

| Existing case | Retained reference | Current sampler seed 0 | Legacy ambient sampler |
|---|---:|---:|---:|
| Hartmann6 qLogEI | 0.22786852462983065 | 0.3038381093602984 | 0.19391397009622446 |
| Ackley qLogEI | 0.5928006956256192 | 0.9140845131035267 | 0.7649100065630514 |
| Hartmann6 qLogNEI | 0.1699699208688239 | 0.11127587899761282 | 0.19524908867226243 |

For every current/legacy pair, the initial X, Y, Yvar and fitted-model hashes match.
The first current sampler uses seed 0 and does not advance the ambient Torch RNG;
legacy behavior draws seed 136044 and advances it. First adaptive proposal hashes
then differ. This isolates a concrete mechanism, not merely a final scalar difference.
The legacy values exactly recover the **earlier failed replay values**, not the frozen
scientific references. Hartmann6 qLogEI legacy replay has identical final X/Y hashes
and regret at Torch 1 and 4 threads. Thread count therefore does not explain this case.
No `set_default_dtype` call was found in src/scripts/tests; default-dtype speculation
was not elevated to a finding.

Fresh command (no monkeypatch, original tests and references):

```text
.venv/bin/python -m pytest -q
  tests/test_replay.py::test_family_qlogei_reproduces_the_committed_q42_column_exactly
  tests/test_replay.py::test_family_qlogei_reproduces_on_every_family_and_at_d8
  tests/test_replay.py::test_family_qlognei_reproduces_the_q59_hartmann_column --tb=short
3 failed, 2 Torch deprecation warnings in 22.78s
```

The temporary instrumentation is `/private/tmp/diagnose-adaptive-replay-20260910.py`.
Its `--family {hartmann6,ackley} --arm {qlogei,qlognei} --sampler {current,legacy}
--threads {1,4}` switches patch only the diagnostic process, not production files.
Detailed X/Y/model/RNG/proposal traces are in `/private/tmp/adaptive-*.json` for these
seven probes. Do not turn this patch into a production change under a diagnose-only request.

The reference artifacts lack stored initial X/Y/model/trajectory traces. Q59's recorded
`git_dirty=true` means its HEAD alone does not identify the generating source. Matching
package version strings do not recover wheel hashes, BLAS binaries, or platform state.
These missing provenance items prevent an honest claim that the original cause is fixed.

Fresh-install control on 2026-09-11: all pinned dependencies were downloaded uncached
from public PyPI into a new virtual environment. All three original adaptive tests
still return exactly the current-sampler values in the table above. This reproduces
the failure with freshly installed packages and extracted archive source; it does not
recover the original platform, dirty source or campaign traces. No production fix was
applied. User was asked whether the original generating environment is available.

User reports the original research may be on this computer or Joseph Yung's computer.
A read-only inventory of this project's `.venv` and existing worktree `.venv` paths
found one local environment; all six existing worktree environments are symlinks to
it, not independent historical installations. No other project directories, backup
volumes, or Joseph's computer were searched. Need an exact alternate checkout/backup
location before claiming the original environment has been recovered.
