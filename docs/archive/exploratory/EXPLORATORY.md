# EXPLORATORY BRANCH — `exploratory/three-factor`

## Nothing on this branch is registered. Nothing on it is a result.

**No number produced here may enter `docs/RESULTS-PERSON-A.md`, `docs/METHODS.md`, or any
paper text without being re-run clean, on fresh instances, under a registration written
before that run.** That applies to every table, every p-value and every figure below,
including ones that look decisive. Especially ones that look decisive.

The reason is not tidiness. Eight of the nine measurement defects logged in this project
were found in code that its author believed was careful, and three of them were tests that
could not have returned the other answer. An unregistered search over eight model
configurations, scored on the outcome, is the single most favourable environment for that
class of error that this project has yet constructed. The branch exists so that the search
can happen somewhere its output cannot be mistaken for a finding.

## What is being asked

At d=6, σ_rel = 0.25 — the pre-registered E2 primary cell — Bayesian optimisation loses to
the sequential-DoE arm, and the surrogate at the point adaptive search begins is
statistically indistinguishable from a model fitted to permuted outcomes.

Two candidate mechanisms are already refuted, both by varied conditions rather than by
readings:

* **prior dominance** — Gamma(3, 6) roughly halves ARD separation in every cell
  (p ≤ 4.3e-06) and does not improve argmax error (Q25);
* **opening design size** — at 18 points d=6 dominates d=8 on every normalisation of
  points-per-dimension and still separates less (1.036× vs 1.199×, p=0.044 at σ=0.25;
  1.241× vs 1.688×, p=0.0008 at σ=0.10) (Q26).

**The question here is mechanism, not rescue.** Not "can BO be made to win" — that is a
search, and a search over enough configurations always succeeds. The question is *what does
the second-order polynomial have that this GP does not*, which has an answer that is true or
false independently of who wins.

| factor | what the polynomial has | 
|---|---|
| **mean function** | a global quadratic trend pooling every observation into ~28 parameters — heavy implicit averaging, which is a regulariser at low signal-to-noise. `ConstantMean` reverts to a constant and pools nothing. |
| **replication** | central composite designs carry replicated centre points by construction, and Binois, Huang, Gramacy & Ludkovski (*Technometrics* 2019) show replication helps GP surrogates at low signal-to-noise. **The source study averaged ≥4 wells × ≥3 replicates ≈ 12 measurements per condition. This benchmark gives one.** |
| **input warping** | nothing directly — but a Kumaraswamy warp lets a GP represent a saturating response from fewer points, and points are the binding constraint here. |

## The outcome that is most likely, and is not "BO wins"

If a quadratic-mean GP closes the gap, the informative diagnostic is not its regret but
**how much the GP component is still contributing**. If its posterior mean agrees closely
with a pure second-order polynomial fitted to the same data, the finding is that *the
polynomial's model was simply the right one for this regime* — which is a stronger and more
publishable statement than "BO can be improved", and it sharpens the existing E2 result
rather than overturning it.

If nothing helps, that is also worth having: it would mean the polynomial's advantage at
high noise and low dimension is neither a modelling artefact nor something a better GP
configuration recovers.

## Standing rules on this branch

1. **Cell 1 of the factorial is the pre-registered configuration and must reproduce its
   stored E2 numbers exactly.** Asserted in code, not eyeballed. If it does not, stop.
2. **The permutation null is recomputed per cell.** Warping changes the input space and a
   quadratic mean changes what the kernel is left to explain, so a null computed once and
   reused would be answering a different question in seven of eight cells.
3. **Instance-level clustering on every test.** n = 25, never 50. Defect 9 was exactly this.
4. **The best of eight cells, selected on the outcome, is an inflated estimate**, and any
   sentence quoting it must say so in the same breath.
5. **Report what did not work in the same detail as what did.**
