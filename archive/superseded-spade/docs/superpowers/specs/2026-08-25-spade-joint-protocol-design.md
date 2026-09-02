# SPADE Joint Protocol Design

**Status:** approved implementation design, before outcome-bearing development runs  
**Date:** 2026-08-25  
**Public method name:** SPADE  
**Scope:** computational method and synthetic validation only; no wet-lab, biological-efficacy, GMP-readiness, or manufacturing-validation claim

## 1. Objective

Build one finalized SPADE method that uses exactly 48 evaluations per campaign and is
tested against the two specialist references it is intended to unite:

1. Sobol48 for probability-map accuracy.
2. qLogNEI48 for posterior-mean terminal regret.

SPADE succeeds only when it simultaneously:

- is non-inferior to Sobol48 on the registered map endpoint;
- is non-inferior to qLogNEI48 on the registered regret endpoint;
- issues a non-empty conservative region often enough to be useful; and
- has positive held-out evidence that issued regions are contained in the true reliable
  region.

The old executed 40+8 SPADE protocol remains frozen historical evidence. The public
algorithm is still called SPADE, not “SPADE 2”. New results must carry a protocol digest
and source commit so historical and current rows cannot be mixed.

## 2. Non-goals

- Do not claim universal algorithmic superiority.
- Do not treat the existing Hill, Ackley, Hartmann6, Levy, or Rosenbrock results as new
  hold-out evidence.
- Do not infer biological performance from the synthetic benchmark.
- Do not use oracle truth, comparator outcomes, future observations, or final scores to
  choose campaign points.
- Do not add evaluations beyond 48 to SPADE or any comparator.
- Do not call an adaptively selected evaluation an independent confirmation.
- Do not select the final method by an unregistered weighted average of map, regret, and
  certificate metrics.

## 3. Registered estimands

Let the observation model be

\[
Y(x)=f(x)(1+\epsilon)+\eta,
\quad \epsilon\sim N(0,\sigma_{rel}^2),
\quad \eta\sim N(0,\sigma_{add}^2).
\]

The primary lockbox condition is:

- dimension `d = 6`;
- `sigma_rel = 0.10`;
- `sigma_add = 0.01`;
- reliability level `gamma = 0.95`;
- certificate assurance `alpha = 0.95`;
- controlled-prevalence quantile `q_tau = 0.75`.

### 3.1 Reliable region

The target is the future-observation reliable region

\[
S_{\tau,\gamma}=\{x:P(Y_{new}(x)\geq\tau\mid f(x))\geq\gamma\}.
\]

The benchmark threshold is generated in a sealed oracle-only harness. On a deterministic
65,536-point Sobol calibration grid, compute

\[
m_\gamma(x)=f(x)-z_\gamma
\sqrt{\sigma_{rel}^2 f(x)^2+\sigma_{add}^2}
\]

and set `tau` to the `q_tau` quantile of `m_gamma`. This makes the true primary reliable
region occupy approximately 25% of the calibration grid while retaining each landscape's
topology and signal-to-noise structure. SPADE and all comparators receive only the numeric
`tau`, `gamma`, and assay-noise specification. They never receive prevalence, margin
values, oracle probabilities, or calibration-grid truth.

This is explicitly a controlled-prevalence synthetic estimand, not an operational method
for choosing a real assay threshold.

This incorporates the pre-registered tau-quantile follow-up without copying its remaining
limitation. That follow-up showed that equalising latent superlevel-set prevalence makes
Ackley and Hartmann6 more answerable at `p = 0.30`, but leaves `p = 0.03` and `p = 0.01`
almost entirely unanswerable at 48 evaluations. The primary benchmark therefore uses one
moderate target prevalence and takes the quantile of `m_gamma`, not of `f`: the controlled
quantity is the actual future-response reliability event, including `gamma` and both noise
terms. The threshold is computed separately for every sealed landscape instance so a
randomized family cannot leak instance-to-instance prevalence differences into the method
comparison.

### 3.2 Probability-map endpoint

On a separate deterministic 8,192-point Sobol scoring grid, each fitted model emits

\[
\hat p(x)=P_{model}(Y_{new}(x)\geq\tau\mid data).
\]

The oracle supplies `p_true(x)` only to the scorer. The primary map loss is integrated
squared probability error:

\[
M=\frac{1}{8192}\sum_x (\hat p(x)-p_{true}(x))^2.
\]

Lower is better. Symmetric difference at `gamma`, raw Brier score against the binary
reliable-set label, calibration decomposition, AUC, and IoU are secondary diagnostics.

### 3.3 Regret endpoint

Every arm uses terminal Rule P. Fit its final model on all 48 observations and select the
point with greatest latent posterior mean from the shared locked 16,384-point terminal
Sobol grid. Score that already-selected point at oracle truth:

\[
R=f(x^*)-f(\hat x_P).
\]

The observed-best Rule A result is secondary. Terminal-rule mixing is prohibited.

### 3.4 Certificate endpoints

For each campaign, draw 4,096 joint latent posterior samples on a deterministic
2,048-point certificate grid. For every draw, convert latent values into future-response
probabilities using that fitted model's observation-noise estimate, then threshold at
`gamma`. This produces 4,096 random reliable-set draws. Predictive observation noise for
both the probability map and these set draws uses the sealed assay law
(`sigma_rel`, `sigma_add`) on latent samples, not learned homoskedastic likelihood noise.
The first 2,048 draws select the
smallest non-empty Vorob'ev quantile whose model-conditional containment is at least
`alpha` (manufacturing-honest volume rule; see
`2026-08-26-spade-manufacturing-certificate-recovery-design.md`); the
second 2,048 estimate model-conditional cross-fit containment. The historical largest-
quantile rule and learned-noise predictive margin are retained only as explicit
non-registered options and must not be used for REGISTERED scoring in this protocol.

The two confirmatory endpoints are evaluated across independent lockbox campaigns:

1. `answer_rate = P(certificate is non-empty)`.
2. `empirical_containment = P(C_alpha subset S_true | C_alpha non-empty)`.

Cross-fit containment is a model diagnostic, not confirmatory validation. Empty
certificates contribute zero to the answer-rate numerator and are excluded—not counted
as successes—from the conditional-containment denominator.

## 4. Fairness contract

Every arm receives exactly 48 noisy function evaluations per campaign.

| Arm | Opening | Later evaluations | Rounds |
|---|---:|---:|---:|
| Sobol48 | 48 scrambled Sobol | 0 | 1 |
| qLogNEI48 | `2d+2 = 14` Sobol | q=4 batches plus final q=2 | 10 |
| SPADE | selected from 32, 40, or 44 Sobol | q=4 batches to 48 | 5, 3, or 2 |

All arms share:

- the same landscape instance and standardized observation-noise streams;
- the same numeric threshold and primary estimands;
- the same surrogate family and fitting policy;
- the same discrete adaptive-candidate pool;
- the same terminal grid, scoring grid, and certificate grid;
- the same Rule P terminal recommendation; and
- identical map, regret, and certificate scoring code.

Evaluation count is the primary resource constraint. Rounds and wall-clock time are
reported separately and never collapsed into “same budget”.

## 5. Observation and surrogate model

The current response-dependent plug-in variance derived from each noisy observation is
not used by the new benchmark. It couples a lucky high observation to a larger fixed
variance and was one of the identified certificate risks.

The common primary surrogate for all three arms is:

- BoTorch `SingleTaskGP` with learned Gaussian observation noise;
- Matérn-5/2 ARD covariance with the repository's dimension-scaled prior;
- explicit unit-cube input normalization;
- standardized outcome transform;
- four deterministic hyperparameter restarts;
- bounded positive likelihood noise; and
- raw duplicate rows retained if a policy ever proposes them, though the locked discrete
  pool prevents exact duplicate locations.

This is a deliberately simpler homoskedastic approximation to the simulator's
heteroskedastic noise. It spends no evaluations estimating noise from six residual degrees
of freedom. Its adequacy is judged by held-out probability-map calibration and empirical
certificate containment. A sensitivity analysis may fit the legacy plug-in fixed-noise
model, but it cannot replace the primary model after lockbox outcomes are known.

The K1 oracle-noise study is used narrowly: changing the legacy GP from response-plug-in
variance to oracle pointwise variance improved mean Rule-P regret by `0.00816`, below its
registered `0.01` build bar. That result is enough to reject spending scarce evaluations on
the proposed pooled-replicate estimator in this 48-evaluation protocol. It is not evidence
that noise modelling is irrelevant to map calibration or certificate containment, so those
endpoints remain explicit gates for the learned-noise primary model.

## 6. Deterministic campaign inputs

Each campaign derives independent stateless seeds from a root campaign identity for:

- opening design;
- adaptive candidate pool;
- observation multiplicative noise;
- observation additive noise;
- GP restart initializations;
- qLogNEI QMC samples;
- adaptive tie-breaking;
- terminal grid;
- map scoring grid;
- certificate grid; and
- posterior certificate draws.

Observation noise is indexed by evaluation order and campaign identity, not by mutable
NumPy generator state. Checkpoints persist completed evaluation count, all seed labels,
observations, decisions made before each outcome, protocol digest, and content hashes.
Resume must produce byte-identical rows to uninterrupted execution.

## 7. SPADE campaign architecture

### 7.1 Opening

SPADE begins with one scrambled Sobol opening of size `n0`. Development compares exactly
`n0 in {32, 40, 44}`. No replicate reserve and no additional confirmation budget exist.

OA-LHS is excluded rather than left as an untested alternative. Its strength-2 construction
requires 49 points, violating the common 48-evaluation budget, and the matched Hartmann6 K2
study did not reduce design-lottery SD (`+0.0132` OA-minus-plain, 95% bootstrap CI
`[-0.0196, +0.0450]`). Sobol is therefore the only opening design in development; this
choice is frozen before joint-policy outcomes are inspected.

### 7.2 Adaptive candidate pool

At campaign start, generate a locked 16,384-point scrambled Sobol menu. Opening points
are removed if present. Every adaptive proposal is selected from the remaining menu and
then removed. qLogNEI48 uses the identical menu construction and discrete acquisition
implementation.

### 7.3 Whole-batch objectives

A q=4 batch is assigned to exactly one objective. Raw scores from different objectives
are never added.

1. `qlognei`: discrete qLog noisy expected improvement using the common learned-noise GP.
2. `global_ivr`: greedy integrated latent posterior variance reduction over a locked
   2,048-point reference grid.
3. `boundary_ivr`: the same variance-reduction calculation weighted by
   `p_hat(x)*(1-p_hat(x))` around the predictive reliability boundary at `gamma`.

Greedy IVR accounts for already selected members of the same batch. It uses posterior
covariance and learned observation noise, not predictive variance containing an
irreducible noise term. The exact covariance calculation is evaluated in deterministic
1,024-candidate blocks: it stores the reference-to-candidate block, candidate diagonal,
and at most `q-1` selected-candidate rows, then applies the same rank-one Schur updates.
It must never materialize the full 16,384 by 16,384 candidate covariance matrix.

### 7.4 Development policies

Development compares exactly three policy families:

- `staged`: every post-opening batch uses qLogNEI.
- `fixed_hybrid`: alternate qLogNEI and global IVR, beginning with qLogNEI.
- `validity_gated`: alternate qLogNEI with a map batch. A map batch uses boundary IVR only
  when the current model predicts a non-empty reliable set and boundary weights have
  effective sample size at least 32; otherwise it uses global IVR.

The gate is a validity fallback, not a regime-performance detector. It may use only the
current campaign's observations and locked model diagnostics. It may not use oracle
truth, comparator scores, family identity, final metrics, or future outcomes.

The candidate set is therefore exactly nine complete algorithms: three opening sizes by
three policies. No candidate is added after development outcomes are inspected.

## 8. Development and selection

All previously used families are development-only: Hill, Ackley, Hartmann6, Levy, and
Rosenbrock. Development uses matched campaign keys across all nine SPADE candidates,
Sobol48, and qLogNEI48. Run exactly 50 matched campaigns per family and arm. Hill uses
25 accepted landscape instances with two campaign seeds each; the four deterministic
families use 50 matched design/noise seeds and are interpreted only as within-landscape
development evidence.

The four legacy external-family adapters retain the exact historical `UnitScaled`
transformation without clipping. Its floor is a deterministic Sobol estimate, so an
independent calibration grid can contain finite values slightly below zero. Development
therefore uses the provenance-bound `legacy_unit_scaled` truth contract: finite truth,
an optimum normalized to one, and an enforced upper bound of one, without clipping small
negative tails. This preserves comparability with the existing benchmarks. Hill and the
new lockbox generators use the stricter `strict_unit_interval` [0,1] contract. The range
contract is included in each controlled-threshold record and digest.

Selection uses nested leave-one-family-out evaluation so a gate or schedule is never
trained and judged on the same family fold. The final complete algorithm is chosen by the
following frozen lexicographic rule:

For each of the five folds, apply the rule using only the other four development
families. A final protocol is selected only if all five fold-specific selections name the
same candidate. Any fold returning `NO_SELECTION`, or disagreement among fold winners,
produces overall `NO_SELECTION`. This conservative consensus rule is frozen before any
outcome-bearing development campaign is run; the all-five-family refit is diagnostic only
and cannot override the nested result.

1. Reject any candidate whose worst-family development empirical-containment point
   estimate is below 0.90 or whose answer-rate point estimate is below 0.50.
2. Among remaining candidates, retain those whose one-sided 95% paired upper confidence
   bound for regret minus qLogNEI48 is at most +0.02 in every family.
3. Select the candidate with the smallest worst-family mean map loss relative to
   Sobol48.
4. Tie-break by fewer rounds, then larger opening, then policy order
   `fixed_hybrid`, `validity_gated`, `staged`.

If no candidate survives steps 1-2, development returns `NO_SELECTION`. The lockbox must
not run and the paper must not claim a finalized joint method.

The selected configuration is serialized to `results/spade-selected-protocol.json` with
the specification digest, source commit, development-artifact hashes, complete numerical
configuration, and selection trace. It is committed before any lockbox score is read.

## 9. Untouched lockbox generators

The lockbox contains four new d=6 randomized generator families. Their parameter seeds
create independent landscape instances; repeated observation seeds on one deterministic
function are not treated as independent landscapes.

1. `toroidal_rastrigin`: shifted, rotated multimodal periodic landscapes.
2. `gaussian_basin_mixture`: separated anisotropic peaks with disconnected high regions.
3. `curved_ridge`: correlated narrow ridges with a unique interior optimum.
4. `soft_plateau`: broad flat reliable interiors with sharp but smooth boundaries.

Every generator outputs a finite normalized response in [0,1], records all sampled
parameters, and has an independently verified optimum. Analytic optima are used where
available; otherwise a deterministic multistart optimizer plus a dense Sobol audit must
agree within `1e-6` before an instance is eligible.

Generator definitions, allowed parameter ranges, instance seed keys `0..1999`, and their
source digest are frozen before development selection. The final power decision uses the
prefix `0..n-1`. No map, regret, answer-rate, or containment score from these generators
may be computed until `spade-selected-protocol.json` exists in a clean commit.

## 10. Lockbox sample size and execution

The executable rule is frozen in
`2026-08-25-spade-lockbox-power-design.md`. After unanimous leave-one-family-out
development selection, choose the first integer from 350 through 2,000 for which both
the analytic paired-normal power and the exact lower confidence bound on nonparametric
sensitivity power are at least 0.80 for map and regret in every development family. The
selected lockbox keys are exactly `0..n-1`. If no registered integer passes, publish an
immutable `INSUFFICIENT_POWER` decision and do not open the lockbox.

The 350-instance minimum still provides about 82.5% joint planning power for the two
exact lower-bound certificate criteria in Section 11 at true answer rate 0.60 and true
conditional containment 0.95. Any larger map/regret-powered prefix only increases that
nominal binomial planning power. The 48-evaluation budget per arm never changes.

Execution is sharded by generator and the committed powered instance range. Shards write
deterministic gzip JSONL raw rows and a sidecar manifest. The merge refuses missing,
duplicate, mismatched, dirty-tree, wrong-protocol, wrong-power-plan, or wrong-environment
shards.

### 10.1 Registered execution logistics

The machine-readable config has a top-level `execution` mapping outside `protocol`.
This is an execution-only amendment: it does not change the scientific design or the
canonical `protocol_payload_sha256`, which remains
`6e6dec2a1671e602833be195d51b6b3f13fa443a56a3780de28db3312ed2d75b`
after the manufacturing certificate recovery
(`certificate_volume_rule: smallest`,
`predictive_observation_noise: assay_relative_additive`,
`latent_draw_inflation: loo_calibration`,
`certificate_max_volume: 0.001`).
The execution mapping has its own canonical sorted compact-JSON SHA-256, and the config
also records live SHA-256 hashes for the workflow, matrix builder, worker, development
merger, and frozen requirements file. Both registered runners authenticate those bytes
before campaign work begins.

Each phase uses one manual `workflow_dispatch` at an exact lowercase 40-character source
commit. The event SHA, workflow SHA, checkout ref, checked-out HEAD, and requested source
SHA must all be identical, and the checkout must be clean. GitHub permissions are
read-only. The runner is `ubuntu-24.04` with Linux/AMD64 Python 3.11.15 in the pinned
`python@sha256:eaeffb6e8511935426934aac863940fbd004ef31dab0d7fc27a129bb7c19d9a8`
container. Checkout and upload-artifact actions are pinned respectively to commits
`11bd71901bbe5b1630ceea73d27597364c9af683` and
`ea165f8d65b6e75b540449e92b4886f43607fa02`. CUDA is disabled; Python hashing, OpenMP,
MKL, OpenBLAS, NumExpr, and Torch intra/inter-op thread settings are fixed to the values
in the execution mapping.

The Actions matrix uses `max-parallel: 40`, while each job runs at most two worker
processes concurrently. Development has 65 logical width-4 shards packed into 33 jobs.
Lockbox shards have width 10 and produce 35 jobs at `n=350` through 200 jobs at `n=2000`;
each job runs the four families in the two frozen pairs
`(toroidal_rastrigin, gaussian_basin_mixture)` and
`(curved_ridge, soft_plateau)`. Every enabled slot is uploaded separately as an immutable
four-file contract: gzip JSONL, SHA-256 sidecar, resume JSON, and manifest JSON, with no
overwrite and no result inspection in the workflow.

## 11. Confirmatory success rule

All conditions below must pass separately in every one of the four lockbox families.
This is an intersection-union claim; success cannot be rescued by pooling families or by
one strong family compensating for another.

1. **Map non-inferiority:** the one-sided 95% paired-bootstrap upper confidence bound for
   `M_SPADE - M_Sobol48` is below `+0.02`.
2. **Regret non-inferiority:** the one-sided 95% paired-bootstrap upper confidence bound
   for `R_SPADE - R_qLogNEI48` is below `+0.02`.
3. **Certificate willingness:** the one-sided 95% Clopper-Pearson lower bound for SPADE's
   non-empty answer rate is above `0.50`.
4. **Certificate validity:** among non-empty SPADE certificates, the one-sided 95%
   Clopper-Pearson lower bound for empirical containment is above `0.90`. This is a
   predeclared 0.05 non-inferiority margin below nominal `alpha=0.95`.

“SPADE beats Sobol on map” is allowed only where the map-difference upper bound is below
zero. “SPADE beats qLogNEI on regret” is allowed only where the regret-difference upper
bound is below zero. Otherwise the valid claim is non-inferiority within the registered
SESOI.

Secondary endpoints and sensitivities use Holm adjustment within explicitly named
families. They cannot change the primary verdict.

## 12. Artifacts and provenance

The new pipeline produces:

- `configs/experiment/spade-joint.yaml`: frozen machine-readable protocol.
- `results/spade-development.json.gz`: complete development rows.
- `results/spade-development-analysis.json`: candidate selection evidence.
- `results/spade-selected-protocol.json`: the only configuration allowed into lockbox.
- `results/spade-lockbox-*.jsonl.gz`: raw lockbox shards.
- `results/spade-lockbox-manifest.json`: shard hashes and completeness.
- `results/spade-lockbox-analysis.json`: confirmatory endpoint estimates and verdict.
- `results/spade-lockbox-release.json`: release-gate report.

Every artifact records:

- specification SHA-256;
- protocol/configuration SHA-256;
- source commit and dirty state;
- Python, platform, NumPy, SciPy, Torch, GPyTorch, and BoTorch versions;
- thread settings;
- exact command arguments;
- generator, instance, arm, root seed, and derived seed labels;
- evaluation budget and round count;
- terminal rule and every primary estimand; and
- parent artifact hashes.

The release validator authenticates the committed configuration and every registered
execution blob from the lockbox execution source commit before it may read stored
analysis or raw outcome rows.

The release validator fails closed on absent raw shards, dirty source, mismatched hashes,
duplicate/missing campaign keys, a lockbox run before the selection commit, mixed
terminal rules, budgets other than 48, invalid certificate denominators, or prose claims
stronger than the computed verdict.

## 13. Historical compatibility

`src/boec/final_spade.py` and the old result artifacts remain historical replay material.
The current method is implemented through a new focused `boec.spade` orchestration path
and is the only SPADE used in the new development and lockbox runners. This internal
separation is provenance, not public algorithm versioning.

Historical exact-replay failures must not be hidden. Future campaigns use explicit
stateless seeds and discrete candidate pools so the new evidence is reproducible. Old
artifacts that cannot be regenerated are labelled historical/non-regenerable and cannot
serve as the new confirmatory result.

## 14. Required implementation tests

Before an outcome-bearing run:

- every new behavior follows a red-green TDD cycle;
- budget arithmetic proves exactly 48 observations for every arm and dimension;
- no-oracle decision signatures and deliberate leak traps are tested;
- gamma changes predictive reliable-set draws and certificates;
- empty certificates are never counted as containment successes;
- exact lower-bound PASS requires positive evidence;
- IVR is invariant to output rescaling after model standardization and decreases reference
  posterior variance on a toy GP;
- resume and uninterrupted runs are byte-identical;
- every random stream is independent and reproducible;
- shuffled shard order produces the same merged artifact;
- selection returns `NO_SELECTION` when any mandatory gate fails;
- lockbox access is refused before a clean selection commit;
- all three arms are scored through identical endpoint functions; and
- release validation catches every registered corruption with a synthetic failing fixture.

## 15. Paper contribution and stopping rule

If the complete lockbox conjunction passes, the paper may state:

> After prespecified selection on development families, the frozen 48-evaluation SPADE
> protocol matched the specialist Sobol map and qLogNEI optimizer within registered
> practical margins while issuing empirically calibrated conservative regions on four
> untouched randomized synthetic generator families.

If any primary condition fails, the paper must report the failed conjunction and retain
the estimand-dependent ranking result as the main contribution. No further policy,
opening, threshold, sample-size reduction, gate, or statistic may be tried against the
same lockbox and called confirmatory.
