"""The final study, ADJUDICATED. Certificate, Pareto front, and the ten registered kills.

    .venv/bin/python scripts/analyse_final_spade_benchmark.py \
        --file results/final-spade-primary.json

Writes ``results/final-spade-certificate.json``,
``results/final-spade-regret-pareto.json`` and ``results/final-spade-kill-ledger.json``.

Registered by ``docs/SPADE-FINAL-SPEC.md`` at commit ``c4f58d3``, **before any final-study
number exists**. Nothing in this file is a preference. Every constant, every refusal and
every branch below traces to a numbered section of that spec or to a defect this repository
has already committed once, and the comment beside it says which.

==============================================================================
WHY THIS FILE EXISTS AT ALL
==============================================================================

``docs/FINDINGS-SPADE.md`` §35 is the precedent: *"a registered kill that nothing evaluates
is not a kill -- it is a paragraph."* Version C's runner produced seven megabytes of columns
and **nothing in the repository called K-C1, K-C2 or K-C3.** The run finished, the columns
landed, and the kill ledger stayed empty until an adjudicator was written for it.

So the final study's runner computes columns and this file decides. The separation is not
tidiness: a runner that also adjudicates can be re-run after seeing a verdict, and §11
prohibits exactly that.

==============================================================================
THE SIX FAILURES THIS FILE IS BUILT AROUND
==============================================================================

**1. §22 -- the exact tail.** §14's multiplicity correction was computed with a normal
approximation. `Binom(50, 0.95)` has `np(1-p) = 2.5`, an order of magnitude under the usual
bar, and the far-left tail is where the approximation is worst: the leading cell's raw p was
reported as 0.00058843 and is **0.00318834**, a 5.31x error, and the Holm-adjusted value went
from 0.043 to **0.2296**. *No cell survived Holm at 0.05 across the 72.* The inferential
claim layered on §14 was withdrawn.

Therefore: every tail here is :func:`scipy.stats.binom.cdf` and every interval is
Clopper-Pearson via :func:`scipy.stats.beta.ppf`. Both are exact. There is no closed-form
approximation anywhere in this module, and ``tests/test_final_spade_statistics.py`` **greps
this source file** for the ones that were used before. That test exists because the defect
was invisible in review for a week -- the printed numbers looked entirely reasonable.

**2. §9.5 -- the pooling prohibitions RAISE.** A published containment table pooled four
``tau_frac`` values computed on the same campaign, the same posterior and the same 512 draws
and called them four Bernoulli trials. **Eleven pooling sites were found, not the one
flagged.** Two claims did not survive un-pooling. Every prohibition in spec §8.2 is enforced
here as an exception, not a warning: the eleven sites already had comments.

**3. §29.3 -- cross-fit is primary.** Same-draw and cross-fit containment differ by up to
3.5 points, concentrated exactly where the Vorob'ev quantiles tie -- the corner where the
selection bias lives. Same-draw is the flattering number. It is emitted on every cell, it is
labelled ``diagnostic`` on every cell, the difference is its own column, and §9's publication
guard 3 hard-fails a table that presents it as primary.

**4. §9.4 -- type I volume ranks silence first.** An arm that certifies the empty set has no
false inclusions and therefore scores **exactly 0**. A type-I-only ranking crowns the method
that declines to answer. The primary map scalar is the symmetric difference (type I + type
II), and :func:`rank_arms` **refuses** the type-I ranking rather than printing it under a
footnote -- a footnote is what §9.4 already had.

**5. §9.6 -- both sample-size units.** `K6-TECHNICAL-REPORT` §3.8 used n=50 `(instance,
seed)`; `RESEARCH-SUMMARY` used n=25 with seeds averaged first; **nothing recorded the
switch**, and 137 contrasts had to be recomputed at both. Paired contrasts here report both,
always, and a direction disagreement is a loud boolean rather than a judgement call.

**6. §43.1 -- terminal rules are never mixed.** K-C1's registered bar `r*` is a rule A column
from `e2-grid.json`; the number compared against it was rule P. Against the mixed bar the arm
was below the bar; like-for-like it was +0.0165 above it, inside SESOI, and *"beaten"* became
**parity, not a win**. :func:`compare_regret` raises when the two sides name different rules.

==============================================================================
WHAT ``--allow-partial`` IS FOR, AND WHY IT CANNOT PRODUCE A VERDICT
==============================================================================

Spec §6: *"If compute cannot reach 200 for a high-assurance cell, the sample size is NOT
silently reduced."* The same principle one level up. A run that is missing arms, missing
conditions, or carrying gate failures is still worth **looking at** -- the tables are how you
find out what went wrong. It is not worth concluding from.

So ``--allow-partial`` builds and prints every table, keeps every count and every interval,
and omits the ``verdict`` key from every certificate cell and the ``status`` key from every
kill. Not "PENDING", not "UNKNOWN": absent, so that no downstream reader can mistake a
placeholder for a decision.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

STUDY_ID = "spade-final-2026-08-23"
REGISTRATION_COMMIT = "c4f58d3"

# --------------------------------------------------------------------------
# The registered constants. Every one is quoted from docs/SPADE-FINAL-SPEC.md.
# --------------------------------------------------------------------------

#: Spec §8. Smallest effect this project calls a difference, on regret and on the symmetric
#: difference. Inherited from the project registration, not chosen for this study.
SESOI = 0.02

#: Spec §6's evidence floor. "A cell with < 10 non-empty certificates cannot support a
#: containment claim; appendix only, with denominator." It bars a PASS. It deliberately does
#: **not** bar a FAIL -- see :func:`_verdict`.
NONEMPTY_FLOOR = 10

#: KF-10, spec §10. A PASS cell where more than half the campaigns certified nothing is
#: downgraded to INCONCLUSIVE. Mirrors ``boec.final_spade.MIN_NONEMPTY_RATE`` from the other
#: direction; the two are the same bar read on the two complementary rates.
EMPTY_RATE_CEILING = 0.50

#: The level at which "demonstrably below nominal" is decided, after Holm.
TEST_ALPHA = 0.05
#: Two-sided Clopper-Pearson coverage.
CI_LEVEL = 0.95

#: Spec §2.1. Cross-fit is the primary estimator; same-draw is emitted beside it as a
#: diagnostic and never as evidence (§9 publication guard 3).
PRIMARY_ESTIMATOR = "crossfit"
DIAGNOSTIC_ESTIMATOR = "same_draw"
CROSSFIT_COLUMN = "crossfit_containment"
SAME_DRAW_COLUMN = "same_draw_containment"

#: Spec §7.2. The only honest single scalar: type I alone ranks silence first (§9.4).
PRIMARY_MAP_SCALAR = "symmetric_difference_pred"
#: Superseded but retained. AUC is invariant to monotone transformation and so cannot see
#: calibration, while mean ``grid_r2`` is negative for all eight arms (§9.4); §24 revised the
#: grounds for the supersession without restoring it.
SECONDARY_MAP_SCALARS = ("auc_pred",)

#: Spec §7.4. Rule P is the primary estimand -- the paper asks which campaign produces the
#: strongest final *model-based* recipe decision. Rule A is a REQUIRED robustness outcome.
PRIMARY_TERMINAL_RULE = "P"
REGRET_COLUMN_BY_RULE = {"A": "regret_rule_a", "P": "regret_rule_p"}

#: Spec §8 / §9.6. The default for UNPAIRED quantities -- arm means, prevalence, containment
#: proportions -- because raw per-arm ICC runs -0.226 to +0.581 and the conservative unit is
#: the defensible one there. Paired contrasts report both units regardless.
DEFAULT_UNPAIRED_UNIT = "n25"

#: Spec §8.2.4. The one accepted treatment of an empty certificate: it leaves the numerator
#: AND the denominator. Any other value raises -- see :func:`containment_cell`.
EMPTY_POLICY = "exclude_from_numerator_and_denominator"

#: Spec §4's registry. `qlogei-addonly` is sensitivity-only and is deliberately NOT
#: mandatory: §4 admits it "only if its re-score status is confirmed VALIDATED first".
MANDATORY_ARMS = (
    "spade_cf_m0", "spade_cf_m4", "spade_cf_m8", "spade_plate1_only",
    "spade_random_plate2", "sobol", "lhs", "random", "qlognei", "qlogei",
    "doe", "doe_unscreened",
)
SENSITIVITY_ARMS = ("qlogei-addonly",)

#: Spec §3.2's co-primary design variants. They differ in exactly one registered quantity.
SPADE_ALLOCATION_ARMS = ("spade_cf_m0", "spade_cf_m4", "spade_cf_m8")
#: Spec §3.3's causal controls.
SPADE_CONTROL_ARMS = ("spade_plate1_only", "spade_random_plate2")
#: Spec §8.1's F-MAP comparators.
MAP_COMPARATORS = ("sobol", "qlognei", "doe")
#: The BO family, for KF-8's like-for-like rule-P bar.
BO_ARMS = ("qlognei", "qlogei")

#: Spec §2. gamma=0.99 is registered as DIAGNOSTIC ONLY. A diagnostic corner carrying a
#: confirmatory verdict would be a fifth Holm family invented after the fact.
GAMMAS_PRIMARY = (0.50, 0.95)
GAMMA_DIAGNOSTIC = 0.99

#: Spec §5.2. The four primary conditions, keyed as `family-d{dim}-s{sigma}`. §5.3's
#: secondary conditions are robustness/context and "may not carry a confirmatory endpoint",
#: so they are absent here by construction rather than by a filter someone can relax.
PRIMARY_CONDITIONS = ("hill-d6-s0.25", "hill-d6-s0.1",
                      "hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
#: KF-2's scope: the two conditions that decide whether validity extends beyond hill d=6.
BEYOND_HILL_CONDITIONS = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")

#: Columns that describe a CAMPAIGN, not a certificate cell. The raw row grid is
#: (arm x campaign x tau_frac x gamma x alpha), so a naive mean over rows counts each
#: campaign once per certificate cell and inflates n by the multiplicity -- §9.5's arithmetic
#: wearing a different column's name. These are deduplicated per campaign, and a
#: disagreement between a campaign's own rows raises rather than being averaged away.
CAMPAIGN_INVARIANT_COLUMNS = frozenset({
    "regret_rule_a", "regret_rule_p", "oracle_best_regret",
    "identification_gap_rule_a", "identification_gap_rule_p",
    "total_wells", "rounds", "plate1_wells", "plate2_wells", "confirmation_wells",
    "adaptive_decisions", "model_fits", "m_local", "n_effective",
})

#: Spec §7.2 / §9.4. Refused as a ranking key, with the reason carried so the refusal
#: explains itself at the call site instead of in a docstring nobody opens.
REFUSED_RANKING_KEYS = {
    "type_i_volume_pred": (
        "type I error volume read ALONE ranks silence first: an arm that certifies the "
        "empty set has no false inclusions and scores exactly 0 (FINDINGS §9.4). The "
        "primary map scalar is the symmetric difference, type I + type II"),
}

#: Spec §8.1, frozen before any result. "They are not combined, split, or redefined
#: afterwards." §22 is the cost of getting a family wrong: the one cell that survived Holm
#: reappeared only in an 18-cell subfamily, and choosing that subfamily after seeing the
#: table is not available.
HOLM_FAMILIES = {
    "F-CERT": "all primary SPADE cross-fit certificate cells",
    "F-BOUND": ("spade_cf_m0 vs spade_random_plate2 and spade_cf_m0 vs "
                "spade_plate1_only, across TARGET primary conditions"),
    "F-ALLOC": "all m0/m4/m8 comparisons across TARGET primary conditions",
    "F-MAP": ("spade_cf_m0 vs sobol, qlognei, doe on primary symmetric-difference "
              "outcomes"),
}

#: Paired percentile bootstrap, matching `analyse_fix1`. The bootstrap reports the interval;
#: Wilcoxon governs yes/no (Q20 §2). A disagreement between them is printed as a
#: disagreement and is never resolved by picking whichever suits the conclusion.
N_BOOT = 4000
BOOT_SEED = 0

CERTIFICATE_ARTEFACT = "results/final-spade-certificate.json"
PARETO_ARTEFACT = "results/final-spade-regret-pareto.json"
LEDGER_ARTEFACT = "results/final-spade-kill-ledger.json"


# ==========================================================================
# Refusals. Each one is a prohibition from the spec, given a type.
# ==========================================================================

class InvalidPooling(ValueError):
    """Spec §8.2. A pooling the registration forbids was requested.

    This is an exception and not a warning on purpose. §9.5 found **eleven** pooling sites
    in committed analysis code; every one of them was written by someone who knew the rule.
    A warning is what they already had.
    """


class MixedEstimand(ValueError):
    """Spec §7.4 / §43.1. Two different terminal rules were compared as one estimand."""


class TypeIOnlyRanking(ValueError):
    """Spec §7.2 / §13.5. A ranking on type I volume alone was requested."""


class UnregisteredHolmFamily(ValueError):
    """Spec §8.1. A multiplicity family outside the four frozen ones was named."""


class GateFailure(RuntimeError):
    """The run carries gate failures, so its columns describe a different experiment."""


class RefusedOverwrite(RuntimeError):
    """An output path collided with the input path.

    `analyse_versionc_form1.verdict_path` records this one from experience: a derived output
    name whose substitution was a no-op equalled the input, and the analyser **overwrote the
    run it was asked to read** -- a few kB of verdict destroying hours of compute.
    """


# ==========================================================================
# Exact inference. §22 is the whole reason these are the shapes they are.
# ==========================================================================

def exact_lower_tail(x: int, n: int, p: float) -> float | None:
    """``P(X <= x)`` for ``X ~ Binomial(n, p)``. EXACT, by :func:`scipy.stats.binom.cdf`.

    The one-sided lower tail is the right test because the registered question is whether
    containment falls **below** nominal; a two-sided test would spend half its size on the
    direction the spec does not ask about.

    Returns ``None`` when there is no denominator. That is not a convenience: §7.1's
    INCONCLUSIVE branch exists so that *no evidence* and *evidence of no effect* stay
    distinguishable, and a cell with nothing in it must not emit a p-value at all.
    """
    if n <= 0:
        return None
    return float(binom.cdf(int(x), int(n), float(p)))


def clopper_pearson(x: int, n: int, level: float = CI_LEVEL) -> tuple:
    """The EXACT two-sided binomial interval, by inverting the beta tails.

    Clopper-Pearson rather than Wald, for the same reason the tail is exact. At ``x = n`` the
    Wald interval collapses to the single point ``[1, 1]``: a certificate contained in 50 of
    50 campaigns would be reported as *proven* rather than as bounded below by 0.929. At the
    counts this study runs -- §6 targets 200 campaigns for high-assurance cells and accepts
    100 -- that corner is not hypothetical.
    """
    if n <= 0:
        return (None, None)
    x, n = int(x), int(n)
    a = 1.0 - float(level)
    lo = 0.0 if x == 0 else float(beta.ppf(a / 2.0, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1.0 - a / 2.0, x + 1, n - x))
    return (lo, hi)


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni step-down, adjusted p returned per key. ``None`` passes through.

    The running maximum is what makes the sequence monotone; without it a later, larger raw
    p can receive a smaller adjusted p and the ordering of the family stops meaning anything.
    Identical to `analyse_fix1._holm` and `analyse_p8_certificate.holm` -- one step-down in
    three files is a maintenance cost, but three *different* step-downs is a result.
    """
    live = {k: float(v) for k, v in pvals.items() if v is not None}
    out: dict = {k: None for k in pvals if k not in live}
    order = sorted(live, key=lambda k: live[k])
    m, running = len(order), 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, live[k] * (m - i)))
        out[k] = running
    return out


def holm_within_family(family: str, pvals: dict) -> dict:
    """Holm inside one of the four frozen families, and nowhere else.

    Raises rather than defaulting, because the two ways to cheat a multiplicity correction
    are to widen the family after a result is significant and to narrow it after a result is
    not, and both look like a typo in a string.
    """
    if family not in HOLM_FAMILIES:
        raise UnregisteredHolmFamily(
            f"{family!r} is not one of the four frozen Holm families "
            f"{sorted(HOLM_FAMILIES)} (spec §8.1). Families are not combined, split or "
            "redefined after a result -- §22 records the one surviving cell reappearing "
            "only in a subfamily chosen after seeing the table")
    return holm(pvals)


def family_for_contrast(arm_a: str, arm_b: str) -> str:
    """Which frozen family a two-arm contrast belongs to. Raises if none covers it.

    The routing is registered so that an analyst cannot move a contrast into a larger family
    to soften its correction, or into a smaller one to sharpen it.
    """
    pair = {arm_a, arm_b}
    for control in SPADE_CONTROL_ARMS:
        if pair == {"spade_cf_m0", control}:
            return "F-BOUND"
    if pair <= set(SPADE_ALLOCATION_ARMS) and len(pair) == 2:
        return "F-ALLOC"
    for comparator in MAP_COMPARATORS:
        if pair == {"spade_cf_m0", comparator}:
            return "F-MAP"
    raise UnregisteredHolmFamily(
        f"no frozen Holm family covers the contrast {arm_a!r} vs {arm_b!r} (spec §8.1). "
        "Inventing one after the fact is the failure mode the freeze exists to prevent")


# ==========================================================================
# Row helpers
# ==========================================================================

def is_spade_arm(arm: str) -> bool:
    """SPADE arms are the ones spec §3 names, and they all carry the ``spade_`` prefix.

    Used to decide F-CERT membership: §8.1 says "all primary SPADE cross-fit certificate
    cells", and the two causal controls of §3.3 produce certificates too -- §7.3 requires
    `m0` not to "produce worse cross-fit certificate validity" than they do, which is a
    statement about their certificates.
    """
    return str(arm).startswith("spade_")


def condition_key(row: dict) -> str:
    """``family-d{dim}-s{sigma}``. One condition is one (family, dimension, sigma) cell.

    §9.7 is why sigma is part of the identity and never a pooling axis: `BiphasicOracle`
    seeds on `seed` alone and never on sigma, so sigma=0.25 and sigma=0.10 are **one noise
    realisation at two amplitudes**. Spec §5.4 requires C1 and C2 to be analysed separately
    and never pooled as independent replicates.
    """
    return (f"{row['family']}-d{int(row['dimension'])}"
            f"-s{float(row['sigma']):g}")


def tau_frac_of(row: dict) -> float:
    return float(row["tau_frac_or_quantile"])


def cell_id(arm: str, condition: str, tau_frac, gamma, alpha) -> str:
    return f"{arm}|{condition}|tf{float(tau_frac):g}|g{float(gamma):g}|a{float(alpha):g}"


def regret_key(rule: str) -> str:
    """The regret column for one terminal rule, or a refusal.

    §34.6 records **three different non-maximising rules on disk**, and they are not one
    estimator. A silent default would pick one of them on the reader's behalf.
    """
    if rule not in REGRET_COLUMN_BY_RULE:
        raise MixedEstimand(
            f"{rule!r} is not a registered terminal rule; spec §7.4 registers exactly two, "
            f"{sorted(REGRET_COLUMN_BY_RULE)} -- A is the observed-data terminal choice and "
            "P is the posterior-mean one. §34.6 records three different non-maximising "
            "rules already on disk, which is why this does not default")
    return REGRET_COLUMN_BY_RULE[rule]


def live_rows(rows: list) -> list:
    """Rows that carry a measurement.

    A row with ``unavailable_reason`` set is a **declaration of absence** required by spec
    §4, not a data point. Averaging one in would be `doe_unscreened` fabricated at d=8, which
    §11 names as a prohibited action outright.
    """
    return [r for r in rows if not r.get("unavailable_reason")]


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _require_single(rows: list, getter, label: str, section: str):
    """The pooling guard, in one place. Returns the single distinct value, or raises.

    ``label`` is the axis the registration forbids pooling over, and it appears verbatim in
    the exception so that a stack trace names the prohibition rather than a variable.
    """
    values = sorted({getter(r) for r in rows})
    if len(values) > 1:
        campaigns = [(r.get("instance_seed"), r.get("campaign_seed")) for r in rows]
        repeated = len(campaigns) != len(set(campaigns))
        raise InvalidPooling(
            f"{len(values)} distinct {label} values {values} in one aggregation "
            f"({section}). "
            + ("These rows repeat the same (instance_seed, campaign_seed), so they are "
               "readings of ONE campaign on ONE posterior -- not independent observations. "
               if repeated else "")
            + "FINDINGS §9.5 found ELEVEN sites pooling exactly this way; two published "
              "claims did not survive un-pooling")
    return values[0] if values else None


# ==========================================================================
# Containment -- the primary safety endpoint
# ==========================================================================

def containment_cell(rows: list, *, alpha: float, tau_frac=None, gamma=None,
                     empty_policy: str = EMPTY_POLICY) -> dict:
    """Cross-fit containment for ONE (arm, condition, tau_frac, gamma, alpha) cell.

    ------------------------------------------------------------------------------
    WHAT IS COUNTED, AND WHY IT IS A COUNT AND NOT A MEAN
    ------------------------------------------------------------------------------

    `crossfit_containment` on a row is that campaign's estimate of `P(CE_alpha subset D)`,
    scored on the evaluation half of the draws. The registered claim is a **whole-region
    assurance** -- `alpha` is a statement about the reported set -- so the campaign either
    meets its own assurance or it does not, and the cell's statistic is `X/n` campaigns
    meeting it. That is the same reading `analyse_p8_certificate.containment_rate` uses and
    the same one §29's powered table (186/200, exact tail 1.299e-01) reports.

    Averaging the per-campaign probabilities instead would answer a different question and
    would let a handful of near-certain campaigns carry a cell in which most campaigns sat
    below their own nominal level.

    ------------------------------------------------------------------------------
    THE THREE POOLING REFUSALS, ALL OF THEM SPEC §8.2
    ------------------------------------------------------------------------------

    1. **Two `tau_frac` in one cell** raises. §3.7 pooled four of them computed on the same
       campaign, the same posterior and the same draws.
    2. **Two `gamma` in one cell** raises. gamma is a per-point margin read off the *same*
       posterior; two gammas from one campaign are two readings of one draw.
    3. **Any `empty_policy` but the registered one** raises, and separately, a row that says
       ``nonempty_certificate = False`` while carrying a containment number raises. §2.1: an
       empty mask returns ``None`` and ``conservative_estimate_split`` returns ``nan``, both
       carried through as missing. If empties counted as successes, a cell where 47 of 50
       campaigns certified *nothing* and the other 3 happened to contain the optimum would
       report containment 1.000 -- a perfect score for a method that declined to answer.
    """
    if empty_policy != EMPTY_POLICY:
        raise InvalidPooling(
            f"empty_policy={empty_policy!r} is refused. Spec §8.2.4 permits exactly one "
            f"treatment, {EMPTY_POLICY!r}: an empty certificate leaves the numerator AND "
            "the denominator. Pooling empty with non-empty outcomes without preserving the "
            "denominator is how an arm that certifies nothing posts perfect containment")

    sel = live_rows(rows)
    if tau_frac is not None:
        sel = [r for r in sel if abs(tau_frac_of(r) - float(tau_frac)) < 1e-12]
    if gamma is not None:
        sel = [r for r in sel if abs(float(r["gamma"]) - float(gamma)) < 1e-12]
    sel = [r for r in sel if abs(float(r["alpha"]) - float(alpha)) < 1e-12]

    tau_frac = _require_single(sel, tau_frac_of, "tau_frac", "spec §8.2.1")
    gamma = _require_single(sel, lambda r: float(r["gamma"]), "gamma", "spec §8.2.2")

    n_empty = 0
    cross_scores, same_scores = [], []
    for r in sel:
        nonempty = bool(r.get("nonempty_certificate"))
        cross, same = r.get(CROSSFIT_COLUMN), r.get(SAME_DRAW_COLUMN)
        if not nonempty:
            if not (_is_missing(cross) and _is_missing(same)):
                raise InvalidPooling(
                    "a row with nonempty_certificate=False carries a containment score "
                    f"({CROSSFIT_COLUMN}={cross!r}, {SAME_DRAW_COLUMN}={same!r}). Spec "
                    "§2.1: the empty set is never scored as a success, and an empty mask "
                    "must arrive as None/nan. Scoring it pools empty with non-empty and "
                    "destroys the denominator (§8.2.4)")
            n_empty += 1
            continue
        if not _is_missing(cross):
            cross_scores.append(float(cross))
        if not _is_missing(same):
            same_scores.append(float(same))

    n = len(cross_scores)
    x = sum(1 for v in cross_scores if v >= float(alpha))
    n_same = len(same_scores)
    x_same = sum(1 for v in same_scores if v >= float(alpha))
    n_total = n + n_empty

    proportion = (x / n) if n else None
    same_proportion = (x_same / n_same) if n_same else None
    lo, hi = clopper_pearson(x, n)

    return {
        "alpha": float(alpha), "tau_frac": tau_frac, "gamma": gamma,
        "empty_policy": EMPTY_POLICY,
        "n_total": n_total, "n_nonempty": n, "n_empty": n_empty,
        "empty_rate": (n_empty / n_total) if n_total else None,
        "x": x, "proportion": proportion,
        "ci_lo": lo, "ci_hi": hi, "ci_level": CI_LEVEL,
        "ci_method": "Clopper-Pearson, exact (scipy.stats.beta.ppf)",
        "exact_p": exact_lower_tail(x, n, float(alpha)),
        "tail": "scipy.stats.binom.cdf, one-sided lower, EXACT",
        "same_draw_x": x_same, "same_draw_n": n_same,
        "same_draw_proportion": same_proportion,
        "same_draw_minus_crossfit": (
            None if (same_proportion is None or proportion is None)
            else same_proportion - proportion),
    }


def comparator_status(rows: list, condition: str) -> dict:
    """Spec §4: every primary condition runs every mandatory arm, or declares why not.

    A missing mandatory comparator is a **hard failure** that blocks any primary conclusion
    for the condition (§13.6). §4.2b's Q57 trap is the concrete reason: a headline that holds
    against `qLogEI` and dies against the noisy acquisition. Running only the weaker arm
    manufactures a win -- and so, identically, does losing the stronger one to a crash and
    saying nothing.

    A **structured declaration** is compliance. Silence is not. `doe_unscreened` at d=8 needs
    45 coefficients against a 48-well budget; when the arithmetic does not close the arm is
    recorded ``unavailable_reason`` before any run and is never approximated into existence.
    """
    sub = [r for r in rows if condition_key(r) == condition]
    present = sorted({r["arm"] for r in sub if not r.get("unavailable_reason")})
    unavailable = {}
    for r in sub:
        if r.get("unavailable_reason") and r["arm"] not in present:
            unavailable[r["arm"]] = str(r["unavailable_reason"])
    missing = [a for a in MANDATORY_ARMS
               if a not in present and a not in unavailable]
    primary = condition in PRIMARY_CONDITIONS

    if not primary:
        reason = ("not a primary condition (spec §5.3): secondary results are "
                  "robustness/context and may not carry a confirmatory endpoint")
    elif missing:
        reason = (f"missing mandatory comparator(s): {', '.join(missing)}. Spec §4 makes a "
                  "missing mandatory arm a hard failure that blocks any primary conclusion "
                  "for this condition")
    else:
        reason = None

    return {
        "condition": condition, "primary": primary,
        "arms_present": present, "unavailable": unavailable,
        "missing_mandatory": missing,
        "sensitivity_present": [a for a in SENSITIVITY_ARMS if a in present],
        "primary_conclusion_available": bool(primary and not missing),
        "unavailable_reason": reason,
        "regime_classes": sorted({str(r.get("regime_class")) for r in sub}),
    }


def _verdict(cell: dict, *, member: bool, cond_ok: bool) -> tuple:
    """PASS / FAIL / INCONCLUSIVE for one cell, plus the reason and any downgrade.

    The order of the branches is the argument:

    1. **Infeasible first.** §4.5: no method certifies above ``tau_max`` at any budget. A
       zero there is a property of the threshold, and reading it as a method failure is the
       error the pre-run feasibility gate exists to stop.
    2. **No denominator next.** An arm that certified nothing has no containment. §2.1
       forbids carrying that through as 1.0.
    3. **Outside the frozen family next.** A diagnostic gamma (§2) or a secondary condition
       (§5.3) is reported descriptively. Giving it a confirmatory verdict would create a
       fifth Holm family after the fact.
    4. **FAIL before the evidence floor.** The floor bars a PASS; it deliberately does not
       bar a FAIL. A cell of 4/8 is not thin enough to be reassuring -- it is demonstrably
       below nominal on the exact tail, and a floor that could suppress a demonstrated
       failure would be a safety guard running backwards.
    5. **PASS, then KF-10.** §7.1's PASS is "not demonstrably below nominal", never "shown
       to be valid" -- see the note in the returned reason.
    """
    if cell["infeasible"]:
        return ("INCONCLUSIVE", None,
                "the cell is above the certifiability ceiling or degenerate; spec §4.5 "
                "makes that a property of the threshold, never a method failure")
    if not cell["crossfit"]["n"]:
        return ("INCONCLUSIVE", None,
                "no non-empty certificate to score; §2.1 forbids scoring the empty set as "
                "a success, so there is no containment number here in either direction")
    if not member:
        return ("INCONCLUSIVE", None,
                "outside the frozen F-CERT family (spec §8.1) -- a diagnostic gamma (§2) "
                "or a non-primary condition (§5.3); reported descriptively and it carries "
                "no confirmatory endpoint")

    p_holm = cell["crossfit"]["p_holm"]
    below = cell["crossfit"]["proportion"] < cell["alpha"]
    if p_holm is not None and p_holm < TEST_ALPHA and below:
        return ("FAIL", None,
                f"demonstrably below nominal: {cell['crossfit']['x']}/"
                f"{cell['crossfit']['n']} = {cell['crossfit']['proportion']:.4f} against "
                f"alpha={cell['alpha']}, exact one-sided p={cell['crossfit']['exact_p']:.3e}"
                f", Holm-adjusted within F-CERT p={p_holm:.3e}")

    if cell["crossfit"]["n"] < NONEMPTY_FLOOR:
        return ("INCONCLUSIVE", None,
                f"non-empty denominator {cell['crossfit']['n']} is below the registered "
                f"evidence floor of {NONEMPTY_FLOOR} (spec §6); non-confirmatory, appendix "
                "only, and reported with its denominator. Non-significance here is an "
                "absence of power, not evidence of validity (§7.1)")

    if not cond_ok:
        pass  # a complete-comparator failure blocks the CONCLUSION, not the measurement

    if cell["empty_rate"] is not None and cell["empty_rate"] > EMPTY_RATE_CEILING:
        return ("INCONCLUSIVE", "KF-10",
                f"reached PASS on containment but {cell['empty_rate']:.1%} of campaigns "
                f"certified nothing, above the KF-10 ceiling of {EMPTY_RATE_CEILING:.0%}. "
                "A method that declines to answer two campaigns in three has not shown a "
                "valid certificate; it has shown that its non-answers are safe")

    return ("PASS", None,
            f"not demonstrably below nominal: {cell['crossfit']['x']}/"
            f"{cell['crossfit']['n']} = {cell['crossfit']['proportion']:.4f} against "
            f"alpha={cell['alpha']}, exact one-sided p={cell['crossfit']['exact_p']:.4f}, "
            f"Holm-adjusted {p_holm:.4f}. This is a failure to reject, not a proof of "
            "validity (§7.1)")


def certificate_report(rows: list, *, allow_partial: bool = False,
                       envelope: dict | None = None) -> dict:
    """The primary safety endpoint, per SPADE arm x condition x tau_frac x gamma x alpha.

    Cross-fit is primary on every cell, same-draw travels beside it as a diagnostic, and the
    difference between them is its own column -- §29.3 measured that difference at up to 3.5
    points and the whole value of the protocol is that it stays visible in every row rather
    than being resolved once in an analysis nobody re-reads.

    Cells are formed by grouping on the full key, so the two containment pooling
    prohibitions cannot be violated here **by construction**: there is never more than one
    ``tau_frac`` or one ``gamma`` inside a cell to pool. :func:`containment_cell` still
    checks, because a guard that only holds while the caller is careful is a convention.
    """
    envelope = envelope or {}
    conditions = sorted({condition_key(r) for r in rows})
    cond_blocks = {c: comparator_status(rows, c) for c in conditions}

    groups: dict = {}
    for r in live_rows(rows):
        if not is_spade_arm(r["arm"]):
            continue
        key = (r["arm"], condition_key(r), tau_frac_of(r),
               float(r["gamma"]), float(r["alpha"]))
        groups.setdefault(key, []).append(r)

    cells = []
    for (arm, cond, tf, gamma, alpha), sub in sorted(groups.items(),
                                                     key=lambda kv: str(kv[0])):
        counts = containment_cell(sub, alpha=alpha, tau_frac=tf, gamma=gamma)
        infeasible = any(bool(r.get("above_ceiling")) for r in sub) or any(
            str(r.get("regime_class")) == "INFEASIBLE" for r in sub)
        gamma_role = "primary" if any(abs(gamma - g) < 1e-12 for g in GAMMAS_PRIMARY) \
            else "diagnostic"
        cells.append({
            "cell_id": cell_id(arm, cond, tf, gamma, alpha),
            "arm": arm, "condition": cond, "tau_frac": tf,
            "gamma": gamma, "gamma_role": gamma_role, "alpha": alpha,
            "regime_class": sorted({str(r.get("regime_class")) for r in sub}),
            "primary_condition": cond in PRIMARY_CONDITIONS,
            "infeasible": infeasible,
            "primary_estimator": PRIMARY_ESTIMATOR,
            "crossfit": {
                "role": "primary", "column": CROSSFIT_COLUMN,
                "x": counts["x"], "n": counts["n_nonempty"],
                "proportion": counts["proportion"],
                "ci_lo": counts["ci_lo"], "ci_hi": counts["ci_hi"],
                "ci_level": counts["ci_level"], "ci_method": counts["ci_method"],
                "exact_p": counts["exact_p"], "tail": counts["tail"],
                "p_holm": None,
            },
            "same_draw": {
                "role": "diagnostic", "column": SAME_DRAW_COLUMN,
                "x": counts["same_draw_x"], "n": counts["same_draw_n"],
                "proportion": counts["same_draw_proportion"],
                "note": ("§9 publication guard 3: same-draw containment is NEVER presented "
                         "as primary. §29.3 measured it up to 3.5 points above cross-fit, "
                         "concentrated where the Vorob'ev quantiles tie"),
            },
            "same_draw_minus_crossfit": counts["same_draw_minus_crossfit"],
            "n_total": counts["n_total"], "n_nonempty": counts["n_nonempty"],
            "n_empty": counts["n_empty"], "empty_rate": counts["empty_rate"],
            "nonempty_floor": NONEMPTY_FLOOR,
            "meets_nonempty_floor": counts["n_nonempty"] >= NONEMPTY_FLOOR,
            "empty_policy": counts["empty_policy"],
        })

    # ---- F-CERT, and only F-CERT -------------------------------------------------------
    members = [c["cell_id"] for c in cells
               if c["primary_condition"] and c["gamma_role"] == "primary"
               and not c["infeasible"] and c["crossfit"]["n"] > 0]
    adjusted = holm_within_family(
        "F-CERT", {c["cell_id"]: c["crossfit"]["exact_p"] for c in cells
                   if c["cell_id"] in members})
    for c in cells:
        c["crossfit"]["p_holm"] = adjusted.get(c["cell_id"])

    for c in cells:
        cond_ok = cond_blocks[c["condition"]]["primary_conclusion_available"]
        member = c["cell_id"] in members
        c["confirmatory"] = bool(member and cond_ok and c["meets_nonempty_floor"])
        verdict, downgrade, reason = _verdict(c, member=member, cond_ok=cond_ok)
        c["downgraded_by"] = downgrade
        c["verdict_reason"] = reason
        if allow_partial:
            c["verdict_withheld"] = True
        else:
            c["verdict"] = verdict

    return {
        "study_id": envelope.get("study_id", STUDY_ID),
        "registration_commit": envelope.get("registration_commit", REGISTRATION_COMMIT),
        "code_commit": envelope.get("code_commit"),
        "artefact": CERTIFICATE_ARTEFACT,
        "primary_estimator": PRIMARY_ESTIMATOR,
        "diagnostic_estimator": DIAGNOSTIC_ESTIMATOR,
        "estimator_note": (
            "Cross-fit containment is the primary safety endpoint (spec §2.1). Same-draw "
            "containment is emitted on every cell, labelled diagnostic, and is never "
            "evidence. §29.3 measured the gap at 1.5-3.5 points at 4,096 draws"),
        "inference": {
            "tail": "scipy.stats.binom.cdf, one-sided lower, EXACT",
            "interval": "Clopper-Pearson, exact",
            "why_exact": (
                "FINDINGS §22: §14's Holm correction was computed with a normal "
                "approximation and did not survive the exact tail -- the leading cell's "
                "adjusted p is 0.2296, not the 0.043 that was published"),
            "test_alpha": TEST_ALPHA, "ci_level": CI_LEVEL,
        },
        "config": {"sesoi": SESOI, "nonempty_floor": NONEMPTY_FLOOR,
                   "empty_rate_ceiling": EMPTY_RATE_CEILING,
                   "empty_policy": EMPTY_POLICY,
                   "gammas_primary": list(GAMMAS_PRIMARY),
                   "gamma_diagnostic": GAMMA_DIAGNOSTIC,
                   "primary_conditions": list(PRIMARY_CONDITIONS)},
        "verdicts_withheld": bool(allow_partial),
        "verdict_withheld_reason": (
            "--allow-partial: the tables are built and printed, but an incomplete run may "
            "not produce a conclusion (spec §6)" if allow_partial else None),
        "conditions": cond_blocks,
        "holm": {"family": "F-CERT", "definition": HOLM_FAMILIES["F-CERT"],
                 "n_members": len(members), "members": members},
        "cells": cells,
    }


# ==========================================================================
# Contrasts -- both units, both rules, never pooled
# ==========================================================================

def _campaign_values(rows: list, key: str) -> dict:
    """``{(arm, instance_seed, campaign_seed): value}`` for a campaign-invariant column.

    Raises when one campaign's own rows disagree. Regret does not depend on ``tau_frac``,
    ``gamma`` or ``alpha``; if two rows of the same campaign carry different regret, the
    column is not what it claims to be, and averaging the disagreement away would hide a
    runner bug behind a plausible number.
    """
    out: dict = {}
    for r in rows:
        k = (r["arm"], r.get("instance_seed"), r.get("campaign_seed"))
        v = r.get(key)
        if _is_missing(v):
            continue
        v = float(v)
        if k in out and abs(out[k] - v) > 1e-12:
            raise InvalidPooling(
                f"campaign {k} carries two different values of {key!r} ({out[k]} and {v}). "
                f"{key!r} is registered as a campaign-level quantity, so its own rows must "
                "agree -- they disagree, which is a defect in the run and not something to "
                "average away")
        out[k] = v
    return out


def _cell_values(rows: list, key: str, *, tau_frac=None, gamma=None, alpha=None) -> dict:
    """``{(arm, instance_seed, campaign_seed): value}`` for a cell-level column.

    A cell-level column -- the map metrics, the calibration scores -- depends on the
    threshold and the margin, so the selection must name exactly one ``(tau_frac, gamma,
    alpha)``. Spanning two is §9.5 in a different column.
    """
    sel = rows
    if tau_frac is not None:
        sel = [r for r in sel if abs(tau_frac_of(r) - float(tau_frac)) < 1e-12]
    if gamma is not None:
        sel = [r for r in sel if abs(float(r["gamma"]) - float(gamma)) < 1e-12]
    if alpha is not None:
        sel = [r for r in sel if abs(float(r["alpha"]) - float(alpha)) < 1e-12]
    sel = [r for r in sel if not _is_missing(r.get(key))]
    _require_single(sel, tau_frac_of, "tau_frac", "spec §8.2.1")
    _require_single(sel, lambda r: float(r["gamma"]), "gamma", "spec §8.2.2")
    _require_single(sel, lambda r: float(r["alpha"]), "alpha", "spec §8.2.2")
    return {(r["arm"], r.get("instance_seed"), r.get("campaign_seed")): float(r[key])
            for r in sel}


def _values(rows: list, key: str, *, tau_frac=None, gamma=None, alpha=None) -> dict:
    rows = live_rows(rows)
    _require_single(rows, condition_key, "condition", "spec §5.4 / §9.7")
    if key in CAMPAIGN_INVARIANT_COLUMNS:
        return _campaign_values(rows, key)
    return _cell_values(rows, key, tau_frac=tau_frac, gamma=gamma, alpha=alpha)


def arm_means(rows: list, key: str, *, tau_frac=None, gamma=None, alpha=None) -> dict:
    """Mean of ``key`` per arm, on the n=25 unit -- seeds averaged within instance first.

    §9.6: the n=25 convention is the default for **unpaired** quantities because raw per-arm
    ICC runs -0.226 to +0.581, and the conservative unit is the defensible one there. It is
    *not* a free choice: `K6-TECHNICAL-REPORT` §3.8 and `RESEARCH-SUMMARY` disagreed on this
    and nothing recorded the switch, so 137 contrasts had to be recomputed at both.
    """
    vals = _values(rows, key, tau_frac=tau_frac, gamma=gamma, alpha=alpha)
    by_instance: dict = {}
    for (arm, inst, _seed), v in vals.items():
        by_instance.setdefault((arm, inst), []).append(v)
    per_arm: dict = {}
    for (arm, _inst), vs in by_instance.items():
        per_arm.setdefault(arm, []).append(sum(vs) / len(vs))
    return {a: sum(vs) / len(vs) for a, vs in per_arm.items()}


def rank_arms(rows: list, key: str, *, tau_frac=None, gamma=None, alpha=None) -> list:
    """Arms ordered on one metric, lower first. Refuses the rankings §9.4 poisoned.

    Type I volume alone is the refused one, and the refusal is a raise rather than a
    footnote because §9.4 already carried the footnote: *"type I volume read alone ranks
    silence first -- an arm certifying the empty set scores exactly 0."*
    """
    if key in REFUSED_RANKING_KEYS:
        raise TypeIOnlyRanking(
            f"a ranking on {key!r} is refused: {REFUSED_RANKING_KEYS[key]}. Rank on "
            f"{PRIMARY_MAP_SCALAR!r} instead, or report the components beside it")
    means = arm_means(rows, key, tau_frac=tau_frac, gamma=gamma, alpha=alpha)
    ordered = sorted(means.items(), key=lambda kv: kv[1])
    return [{"rank": i + 1, "arm": a, "value": v, "key": key,
             "lower_is_better": True}
            for i, (a, v) in enumerate(ordered)]


def _boot_ci(diffs: np.ndarray) -> tuple:
    """Percentile bootstrap on the PAIRED differences -- the unit of analysis.

    Resampling the two arms independently would break the pairing that makes n campaigns
    worth n comparisons, which is the entire reason spec §8 matches oracle instances and
    campaign seeds across arms.
    """
    if diffs.size == 0:
        return (None, None)
    rng = np.random.default_rng(BOOT_SEED)
    boots = np.array([rng.choice(diffs, diffs.size, replace=True).mean()
                      for _ in range(N_BOOT)])
    return (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))


def _wilcoxon_p(diffs: np.ndarray) -> float:
    """Two-sided Wilcoxon on the paired differences. Q20 §2: Wilcoxon governs yes/no.

    The all-zero case is short-circuited rather than handed to scipy. Two arms that are
    bit-identical on every campaign are a real and *expected* state here -- §3.2 registers
    `spade_cf_m0` as bit-identical to the plain boundary rule, and `analyse_fix1` records
    `plate1_only` matching `lhs` to 4.44e-16 -- and scipy's answer for it has changed shape
    across versions (a ValueError in some, a warning and a p of 1.0 in others). A verdict
    that depends on which scipy is installed is not a verdict.
    """
    if diffs.size == 0 or not np.any(diffs):
        return 1.0
    try:
        p = float(wilcoxon(diffs).pvalue)
    except ValueError:
        return 1.0
    return 1.0 if math.isnan(p) else p


def _unit_block(diffs: list) -> dict:
    d = np.asarray(diffs, dtype=float)
    lo, hi = _boot_ci(d)
    return {"n": int(d.size),
            "mean": (float(d.mean()) if d.size else None),
            "ci_lo": lo, "ci_hi": hi,
            "wilcoxon_p": _wilcoxon_p(d),
            "above_sesoi": bool(d.size and abs(float(d.mean())) >= SESOI)}


def paired_contrast(rows: list, arm_a: str, arm_b: str, key: str, *,
                    tau_frac=None, gamma=None, alpha=None) -> dict:
    """Mean of ``arm_a - arm_b`` on ``key``, reported at **both** registered units.

    Every metric in this study is lower-is-better, so a positive mean means ``arm_b`` is
    ahead. The direction is stated in the returned dict rather than left to the reader.

    ------------------------------------------------------------------------------
    WHY BOTH UNITS, ALWAYS
    ------------------------------------------------------------------------------

    §9.6: `K6-TECHNICAL-REPORT` §3.8 used **n=50**, unit `(instance, seed)`;
    `RESEARCH-SUMMARY` used **n=25**, seeds averaged within instance. **Nothing recorded the
    switch.** All 137 reported contrasts had to be recomputed at both, and while no verdict
    moved, the measured ICC ran from +0.199 at (6, 0.10) to **-0.168** at (8, 0.25) -- where
    n=25 is the *more* precise unit, not the more conservative one.

    The two units cannot disagree on a balanced design; averaging within instance and then
    across is the same arithmetic. They disagree exactly when the seeds-per-instance counts
    are unequal, which is what an excluded or crashed campaign produces. That is precisely
    the case where a single reported unit would be a silent choice, so the disagreement is a
    boolean on the output and spec §8 requires the analysis to fail loudly on it.
    """
    vals = _values(rows, key, tau_frac=tau_frac, gamma=gamma, alpha=alpha)
    a_vals = {(i, s): v for (arm, i, s), v in vals.items() if arm == arm_a}
    b_vals = {(i, s): v for (arm, i, s), v in vals.items() if arm == arm_b}
    shared = sorted(set(a_vals) & set(b_vals))

    pair_diffs = [a_vals[k] - b_vals[k] for k in shared]
    by_instance: dict = {}
    for (inst, _seed), d in zip(shared, pair_diffs, strict=True):
        by_instance.setdefault(inst, []).append(d)
    instance_diffs = [sum(v) / len(v) for _, v in sorted(by_instance.items())]

    n50, n25 = _unit_block(pair_diffs), _unit_block(instance_diffs)
    disagree = bool(
        n50["mean"] is not None and n25["mean"] is not None
        and n50["mean"] != 0.0 and n25["mean"] != 0.0
        and (n50["mean"] > 0) != (n25["mean"] > 0))

    return {
        "key": key, "arm_a": arm_a, "arm_b": arm_b,
        "contrast": f"mean({arm_a} - {arm_b})",
        "lower_is_better": True,
        "positive_means": f"{arm_b} is ahead",
        "primary_unit": DEFAULT_UNPAIRED_UNIT,
        "n50": n50, "n25": n25,
        "effect": n25["mean"], "ci": [n25["ci_lo"], n25["ci_hi"]],
        "p": n25["wilcoxon_p"],
        "sesoi": SESOI,
        "units_disagree": disagree,
        "unit_disagreement_note": (
            f"the two registered sample-size units disagree in DIRECTION: n=50 gives "
            f"{n50['mean']:+.5f} and n=25 gives {n25['mean']:+.5f}. FINDINGS §9.6 requires "
            "this to be reported loudly rather than resolved by choosing a unit; it happens "
            "when the seeds-per-instance counts are unequal, so check for excluded or "
            "crashed campaigns before quoting either number" if disagree else None),
        "bootstrap": {"n_boot": N_BOOT, "seed": BOOT_SEED,
                      "note": "percentile bootstrap on the PAIRED differences"},
    }


def compare_regret(rows: list, arm_a: str, arm_b: str, *, rule_a: str,
                   rule_b: str | None = None) -> dict:
    """A regret contrast under ONE terminal rule. Mixing the two raises.

    §43.1 is the whole reason this function has two rule arguments instead of one. K-C1's
    registered bar `r*` is *"the best committed regret at this (d, sigma) cell, read from
    e2-grid.json"* -- **and that column is rule A**. The number compared against it was rule
    P. The repository's own Fix 1 registration already forbade it:

        "A rule-P regret is also not comparable to any published rule-A number: they are
         different estimands, and every table that carries both must say which column is
         which."

    Against the mixed bar the arm read as below it; like-for-like it was **+0.0165 above**,
    inside SESOI, and the headline *"beaten, not merely met"* was withdrawn in favour of
    **parity, not a win**. Two arguments, so the mismatch is expressible and therefore
    catchable, rather than impossible to state and consequently made by accident.
    """
    rule_b = rule_a if rule_b is None else rule_b
    key_a, key_b = regret_key(rule_a), regret_key(rule_b)
    if key_a != key_b:
        raise MixedEstimand(
            f"refusing to compare {arm_a!r} under terminal rule {rule_a!r} against "
            f"{arm_b!r} under rule {rule_b!r}. Spec §7.4: 'Comparing rule A for one arm "
            "against rule P for another is a protocol violation.' §43.1 records this "
            "project doing exactly that and having to withdraw the claim -- like-for-like, "
            "the gap fell inside SESOI and the result was parity, not a win")
    out = paired_contrast(rows, arm_a, arm_b, key_a)
    out["rule"] = rule_a
    out["estimand"] = ("rule P -- the posterior-mean terminal choice, the primary estimand "
                       "(spec §7.4)" if rule_a == "P" else
                       "rule A -- the observed-data terminal choice, required robustness")
    return out


# ==========================================================================
# The Pareto front
# ==========================================================================

def pareto_nondominated(points: dict) -> set:
    """Non-dominated keys on two lower-is-better axes.

    Spec gives two primary scalars in different currencies -- rule-P regret (§7.4) and the
    symmetric difference (§7.2) -- and registers no weighting between them. Collapsing them
    into one score would require inventing that weighting after seeing the numbers, so the
    front is reported instead. §42's reading of SPADE as a "low-variance middling arm" is
    exactly the shape a front makes visible and a scalar hides.
    """
    keys = [k for k, v in points.items()
            if v is not None and all(c is not None for c in v)]
    front = set()
    for k in keys:
        x, y = points[k]
        dominated = any(
            (points[o][0] <= x and points[o][1] <= y)
            and (points[o][0] < x or points[o][1] < y)
            for o in keys if o != k)
        if not dominated:
            front.add(k)
    return front


def _certificate_status(certificate: dict | None, arm: str, condition: str) -> str:
    if certificate is None:
        return "NOT_ASSESSED"
    if certificate.get("verdicts_withheld"):
        return "WITHHELD"
    verdicts = [c.get("verdict") for c in certificate["cells"]
                if c["arm"] == arm and c["condition"] == condition]
    verdicts = [v for v in verdicts if v]
    if not verdicts:
        return "NOT_ASSESSED"
    for worst in ("FAIL", "INCONCLUSIVE", "PASS"):
        # FAIL dominates: an arm with one failing cell has a failing certificate, and
        # letting a PASS elsewhere mask it is how a safety endpoint gets averaged away.
        if worst in verdicts:
            return worst
    return "NOT_ASSESSED"


def _assessable(rows: list) -> list:
    """Rows the map and regret analyses may read.

    Above-ceiling and INFEASIBLE cells are dropped *here* rather than being scored and
    explained: §4.5 and KF-9 make an above-ceiling threshold a property of the threshold, so
    an arm's zero there is not a measurement of the arm. The certificate report keeps them
    -- KF-9 has to be able to see that one reached the analyser at all.
    """
    return [r for r in live_rows(rows)
            if not r.get("above_ceiling")
            and str(r.get("regime_class")) != "INFEASIBLE"]


def _sole_map_cell(rows: list) -> tuple:
    """The single ``(tau_frac, gamma, alpha)`` the map metrics are read at.

    The spec registers no *one* map cell, and this analyser will not pick one. If the run
    spans several, the operator states which with ``--map-cell``; averaging across them
    would pool threshold levels computed on one campaign and one posterior, which is §9.5
    exactly.
    """
    cells = sorted({(tau_frac_of(r), float(r["gamma"]), float(r["alpha"])) for r in rows})
    if len(cells) != 1:
        raise InvalidPooling(
            f"the run spans {len(cells)} (tau_frac, gamma, alpha) map cells {cells} and the "
            "registration names no single primary one. Name it with --map-cell. Averaging "
            "the map metric across thresholds or margins computed on the SAME campaign and "
            "the SAME posterior is the pooling FINDINGS §9.5 found at eleven sites")
    return cells[0]


def regret_pareto_report(rows: list, *, certificate: dict | None = None,
                         map_cell: tuple | None = None,
                         allow_partial: bool = False,
                         envelope: dict | None = None) -> dict:
    """Regret under BOTH rules, the map error, the budget axes, and the front.

    §7.4 requires both terminal rules for every arm -- rule P primary, rule A a **required**
    robustness outcome, never optional -- and every table names its rule.

    §4.1 requires wells and rounds on separate axes and they are carried per row here, not
    folded into a footnote: `spade_plate1_only` is budget-short by 8 wells and is a
    rounds/wells *reference*, not an equal-well comparator. A table without both columns
    invites exactly the comparison the spec forbids.
    """
    envelope = envelope or {}
    usable = _assessable(rows)
    excluded = len(live_rows(rows)) - len(usable)
    conditions = sorted({condition_key(r) for r in usable})

    entries = []
    for cond in conditions:
        sub = [r for r in usable if condition_key(r) == cond]
        tf, gamma, alpha = map_cell or _sole_map_cell(sub)
        arms = sorted({r["arm"] for r in sub})

        regret_a = arm_means(sub, "regret_rule_a")
        regret_p = arm_means(sub, "regret_rule_p")
        sym = arm_means(sub, PRIMARY_MAP_SCALAR, tau_frac=tf, gamma=gamma, alpha=alpha)

        points = {a: (regret_p.get(a), sym.get(a)) for a in arms}
        front = pareto_nondominated(points)

        for arm in arms:
            arm_rows = [r for r in sub if r["arm"] == arm]
            entries.append({
                "arm": arm, "condition": cond,
                "regime_class": sorted({str(r.get("regime_class")) for r in arm_rows}),
                "map_cell": {"tau_frac": tf, "gamma": gamma, "alpha": alpha},
                "regret": {"A": regret_a.get(arm), "P": regret_p.get(arm)},
                "primary_rule": PRIMARY_TERMINAL_RULE,
                "regret_rule_note": ("both rules are reported for every arm; comparing one "
                                     "arm's rule A against another's rule P is a protocol "
                                     "violation (spec §7.4, FINDINGS §43.1)"),
                "symmetric_difference": sym.get(arm),
                "type_i_volume": arm_means(sub, "type_i_volume_pred", tau_frac=tf,
                                           gamma=gamma, alpha=alpha).get(arm),
                "type_ii_volume": arm_means(sub, "type_ii_volume_pred", tau_frac=tf,
                                            gamma=gamma, alpha=alpha).get(arm),
                "rounds": int(arm_means(sub, "rounds").get(arm, 0)),
                "wells": int(arm_means(sub, "total_wells").get(arm, 0)),
                "certificate_status": _certificate_status(certificate, arm, cond),
                "pareto_nondominated": arm in front,
                "unit": DEFAULT_UNPAIRED_UNIT,
            })

    return {
        "study_id": envelope.get("study_id", STUDY_ID),
        "registration_commit": envelope.get("registration_commit", REGISTRATION_COMMIT),
        "code_commit": envelope.get("code_commit"),
        "artefact": PARETO_ARTEFACT,
        "axes": ("regret_rule_p", PRIMARY_MAP_SCALAR),
        "axes_note": (
            "both axes are lower-is-better. The map axis is the SYMMETRIC DIFFERENCE and "
            "never type I alone -- §9.4: type I read alone ranks silence first, because an "
            "arm certifying the empty set scores exactly 0"),
        "primary_terminal_rule": PRIMARY_TERMINAL_RULE,
        "excluded_infeasible_rows": excluded,
        "excluded_note": ("above-ceiling and INFEASIBLE rows are excluded from the map and "
                          "regret analyses: §4.5 makes that a property of the threshold, "
                          "never a method failure. KF-9 still counts them"),
        "verdicts_withheld": bool(allow_partial),
        "rows": entries,
    }


# ==========================================================================
# The kill ledger -- spec §10, all ten
# ==========================================================================

KILL_REGISTRY = {
    "KF-1": ("SPADE's certificate is valid prospectively under cross-fit",
             "any primary F-CERT cell demonstrably below nominal after exact test + Holm"),
    "KF-2": ("Certificate validity extends beyond hill d=6 sigma=0.25",
             "C3/C4 INCONCLUSIVE or FAIL -> the claim narrows to hill"),
    "KF-3": ("Targeted plate 2 earns its complexity",
             "m0 does not beat random_plate2 by >=SESOI on symmetric difference in any "
             "TARGET condition"),
    "KF-4": ("Plate 2 does anything at all",
             "m0 does not beat plate1_only on symmetric difference"),
    "KF-5": ("m>0 lowers regret safely",
             "the §7.5 conjunction is unmet -> trade-off, not an improvement"),
    "KF-6": ("SPADE is competitive with Sobol on the map in TARGET regimes",
             "sobol beats m0 by >SESOI in a TARGET condition"),
    "KF-7": ("SPADE is competitive with qLogNEI on the map in TARGET regimes",
             "qlognei beats m0 by >SESOI in a TARGET condition"),
    "KF-8": ("Regret is at practical parity under a common terminal rule",
             "m0 - best BO regret > SESOI under rule P"),
    "KF-9": ("The study's cells are feasible",
             "any planned cell with tau >= tau_max reached the analysis"),
    "KF-10": ("Empty-set degeneracy does not explain a pass",
              "any PASS cell with empty rate > 0.50"),
}


def _kill(name: str, status: str, *, effect=None, ci=None, p=None, p_adjusted=None,
          denominator=None, comparison: str = "", source_key: str = "",
          artefact: str = CERTIFICATE_ARTEFACT, interpretation: str = "") -> dict:
    claim, fires = KILL_REGISTRY[name]
    return {"id": name, "claim": claim, "fires_when": fires, "status": status,
            "effect": effect, "ci": ci, "p": p, "p_adjusted": p_adjusted,
            "sesoi": SESOI,
            "sesoi_comparison": comparison or f"SESOI = {SESOI}; not applicable to this kill",
            "denominator": denominator,
            "source": {"artefact": artefact, "key": source_key},
            "interpretation": interpretation}


def _target_primary_conditions(rows: list) -> list:
    """Conditions classified TARGET **before** any arm ran (spec §5.1).

    The classification is read off the rows because `boec.final_spade.classify_regime`
    stamped it there from oracle geometry and a frozen 20-campaign pilot, and its signature
    takes no arm outcome at all. That is the guard: a cell relabelled TARGET after results
    are known makes TARGET mean "where SPADE won".
    """
    out = []
    for cond in sorted({condition_key(r) for r in rows}):
        if cond not in PRIMARY_CONDITIONS:
            continue
        if any(str(r.get("regime_class")) == "TARGET"
               for r in rows if condition_key(r) == cond):
            out.append(cond)
    return out


#: The membership of the three contrast families, spec §8.1, written out as pairs so the
#: family is a data structure rather than something each kill reconstructs for itself.
#:
#: 🔴 This file's first draft let every kill build its own family and Holm-correct inside
#: it. F-BOUND's two registered contrasts became two families of one, F-MAP's three became
#: two of one, and `doe` fell out of F-MAP entirely -- and a one-member Holm correction is
#: arithmetically no correction at all. §8.1 forbids splitting a family in the same breath
#: as combining one, and this is what splitting looks like when nobody means to do it.
FAMILY_CONTRASTS = {
    "F-BOUND": tuple(("spade_cf_m0", c) for c in SPADE_CONTROL_ARMS),
    "F-MAP": tuple(("spade_cf_m0", c) for c in MAP_COMPARATORS),
    "F-ALLOC": (("spade_cf_m0", "spade_cf_m4"), ("spade_cf_m0", "spade_cf_m8"),
                ("spade_cf_m4", "spade_cf_m8")),
}

#: Which outcome each family's members are tested on. F-BOUND and F-MAP are registered
#: against the symmetric difference by §7.3 and §8.1; F-ALLOC's only hypothesis test is
#: clause 1 of §7.5's conjunction, which is rule-P regret. The other three clauses of §7.5
#: are bars, not tests, and carry no p-value into the family.
FAMILY_METRIC = {"F-BOUND": PRIMARY_MAP_SCALAR, "F-MAP": PRIMARY_MAP_SCALAR,
                 "F-ALLOC": "regret_rule_p"}


def _family_contrasts(rows: list, targets: list, map_cell=None) -> dict:
    """Every member of every frozen contrast family, computed once and Holm-corrected once.

    A family spans **all** its registered contrasts across **all** TARGET primary conditions
    -- F-BOUND is two contrasts, F-MAP is three, F-ALLOC is three, each times however many
    TARGET conditions the pre-run classifier produced. Building them here, together, is the
    only way the correction can be the one §8.1 registered: a kill that assembles its own
    family assembles a smaller one, and a smaller family is a softer correction.

    Missing arms drop out of a family rather than being imputed. That shrinks the family and
    therefore weakens the correction, which is the wrong direction -- so the count of members
    travels with the result and every kill built from a thin family says so.
    """
    out: dict = {}
    for family, pairs in FAMILY_CONTRASTS.items():
        members: dict = {}
        for cond in targets:
            sub = [r for r in _assessable(rows) if condition_key(r) == cond]
            arms = {r["arm"] for r in sub}
            metric = FAMILY_METRIC[family]
            cell_kw = {}
            if metric not in CAMPAIGN_INVARIANT_COLUMNS:
                tf, gamma, alpha = map_cell or _sole_map_cell(sub)
                cell_kw = {"tau_frac": tf, "gamma": gamma, "alpha": alpha}
            for arm, versus in pairs:
                if arm not in arms or versus not in arms:
                    continue
                if family == "F-ALLOC":
                    # Through compare_regret, so the terminal rule is named on both sides
                    # and §43.1's mixed-estimand comparison stays unrepresentable.
                    c = compare_regret(sub, arm, versus, rule_a=PRIMARY_TERMINAL_RULE)
                else:
                    # versus - arm, so a POSITIVE effect is `arm` ahead on a
                    # lower-is-better metric.
                    c = paired_contrast(sub, versus, arm, metric, **cell_kw)
                members[f"{arm} vs {versus} @ {cond}"] = {
                    "condition": cond, "arm": arm, "versus": versus,
                    "metric": metric, "contrast": c}
        adjusted = holm_within_family(
            family, {k: v["contrast"]["p"] for k, v in members.items()})
        for k, v in members.items():
            v["p_adjusted"] = adjusted[k]
        out[family] = members
    return out


def _map_kill(name, arm, versus, conditions, families, *, fires_if_below_sesoi: bool,
              interpretation_fail: str, interpretation_pass: str) -> dict:
    """One kill decided on a family member, with the family's own correction attached.

    "Best across TARGET conditions" is the registered reading, not a selection: every §10
    kill that uses this fires on *"in any TARGET condition"*. The full per-condition list
    travels with the verdict so the best-case reading stays visible beside its siblings.
    """
    family = family_for_contrast(arm, versus)
    if not conditions:
        return _kill(name, "INCONCLUSIVE",
                     artefact=PARETO_ARTEFACT, source_key="rows[].symmetric_difference",
                     interpretation=("no TARGET primary condition exists in this run, and "
                                     "spec §5.1 assigns regime class from oracle geometry "
                                     "and a frozen pilot -- never from arm performance. "
                                     "The kill cannot be answered here"))
    mine = {k: v for k, v in families[family].items()
            if v["arm"] == arm and v["versus"] == versus}
    if not mine:
        return _kill(name, "NOT_RUN", artefact=PARETO_ARTEFACT,
                     source_key="rows[].symmetric_difference",
                     interpretation=(f"{arm!r} and {versus!r} do not both appear in any "
                                     "TARGET primary condition. NOT_RUN is not a pass -- "
                                     "§35.2 records silence being read as one"))
    key, best = max(mine.items(),
                    key=lambda kv: (kv[1]["contrast"]["effect"] is not None,
                                    kv[1]["contrast"]["effect"] or 0.0))
    c, cond = best["contrast"], best["condition"]
    e = c["effect"]
    failed = (e is None or e < SESOI) if fires_if_below_sesoi else (
        e is not None and e < -SESOI)
    entry = _kill(name, "FAIL" if failed else "PASS",
                  effect=e, ci=c["ci"], p=c["p"], p_adjusted=best["p_adjusted"],
                  denominator=c["n25"]["n"],
                  comparison=f"effect {e:+.5f} against SESOI {SESOI} in {cond}",
                  artefact=PARETO_ARTEFACT,
                  source_key=f"rows[arm={arm},condition={cond}].symmetric_difference",
                  interpretation=interpretation_fail if failed else interpretation_pass)
    entry["holm_family"] = family
    entry["holm_family_size"] = len(families[family])
    entry["holm_member"] = key
    entry["per_condition"] = {
        v["condition"]: {"effect": v["contrast"]["effect"], "p": v["contrast"]["p"],
                         "p_adjusted": v["p_adjusted"],
                         "units_disagree": v["contrast"]["units_disagree"]}
        for v in mine.values()}
    entry["units_disagree"] = any(v["contrast"]["units_disagree"] for v in mine.values())
    return entry


def kill_ledger(rows: list, certificate: dict, pareto: dict, *,
                allow_partial: bool = False, envelope: dict | None = None,
                map_cell: tuple | None = None) -> dict:
    """Every registered kill of spec §10, adjudicated, with its evidence attached.

    §35 is the standard this has to meet: *"a registered kill that nothing evaluates is not a
    kill -- it is a paragraph"*, and *"a kill that quietly disappears is indistinguishable
    from one that passed"*. So all ten appear, always, and **NOT_RUN is a distinct status
    from PASS**. §35.2 records this project's Version C artefacts carrying no kill verdict at
    all and the absence reading as success.

    ``status`` here means *the claim's* fate: **PASS** = the registered claim survives;
    **FAIL** = it does not and the registered consequence applies (which for KF-3 is removing
    the mechanistic claim from the paper, and for KF-5 is calling the result a trade-off).
    """
    envelope = envelope or {}
    cells = certificate["cells"]
    withheld = bool(allow_partial or certificate.get("verdicts_withheld"))
    targets = _target_primary_conditions(_assessable(rows))
    # Every frozen family, built whole and corrected once, BEFORE any kill reads from it.
    families = _family_contrasts(rows, targets, map_cell=map_cell)
    kills: dict = {}

    # ---- KF-1 --------------------------------------------------------------------------
    confirmatory = [c for c in cells if c["confirmatory"]]
    failing = [c for c in confirmatory if c.get("verdict") == "FAIL"]
    if not cells:
        kills["KF-1"] = _kill("KF-1", "NOT_RUN", source_key="cells",
                              interpretation="no certificate cell exists in this run")
    elif not confirmatory:
        kills["KF-1"] = _kill(
            "KF-1", "INCONCLUSIVE", denominator=len(cells), source_key="cells[].confirmatory",
            interpretation=("no cell is confirmatory: every one is below the evidence floor "
                            "of 10, outside the frozen F-CERT family, or sits in a condition "
                            "missing a mandatory comparator (spec §4)"))
    else:
        worst = (min(failing, key=lambda c: c["crossfit"]["proportion"]) if failing
                 else min(confirmatory, key=lambda c: c["crossfit"]["proportion"]))
        eff = worst["crossfit"]["proportion"] - worst["alpha"]
        kills["KF-1"] = _kill(
            "KF-1", "FAIL" if failing else "PASS",
            effect=eff, ci=[worst["crossfit"]["ci_lo"], worst["crossfit"]["ci_hi"]],
            p=worst["crossfit"]["exact_p"], p_adjusted=worst["crossfit"]["p_holm"],
            denominator=worst["crossfit"]["n"],
            comparison=("SESOI does not govern a containment proportion; the registered bar "
                        f"is the nominal alpha={worst['alpha']}, and the worst confirmatory "
                        f"cell sits {eff:+.4f} from it"),
            source_key=f"cells[cell_id={worst['cell_id']}]",
            interpretation=(
                f"{len(failing)} confirmatory cell(s) are demonstrably below nominal after "
                "the exact one-sided test and Holm within F-CERT; the prospective "
                "cross-fit validity claim does not hold as registered" if failing else
                f"no confirmatory cell is demonstrably below nominal across "
                f"{len(confirmatory)} cells. This is a failure to reject, not a proof of "
                "validity (§7.1) -- §22 measured what this design can and cannot detect"))

    # ---- KF-2 --------------------------------------------------------------------------
    beyond = [c for c in cells if c["condition"] in BEYOND_HILL_CONDITIONS
              and c["confirmatory"]]
    if not beyond:
        kills["KF-2"] = _kill(
            "KF-2", "NOT_RUN", source_key="cells[condition in hartmann6]",
            interpretation=("no confirmatory cell in hartmann6 d=6 or d=8, so the study "
                            "carries no evidence beyond the single historical hill "
                            "condition and the claim narrows to hill (§10.1 item 2)"))
    else:
        bad = [c for c in beyond if c.get("verdict") != "PASS"]
        worst = min(beyond, key=lambda c: c["crossfit"]["proportion"])
        kills["KF-2"] = _kill(
            "KF-2", "FAIL" if bad else "PASS",
            effect=worst["crossfit"]["proportion"] - worst["alpha"],
            ci=[worst["crossfit"]["ci_lo"], worst["crossfit"]["ci_hi"]],
            p=worst["crossfit"]["exact_p"], p_adjusted=worst["crossfit"]["p_holm"],
            denominator=worst["crossfit"]["n"],
            comparison=f"nominal alpha={worst['alpha']}; SESOI does not apply",
            source_key=f"cells[cell_id={worst['cell_id']}]",
            interpretation=("cross-family evidence is not clean, so the certificate claim "
                            "narrows to hill and says so (§10.1 item 2). §37/§42 predicted "
                            "SPADE would struggle off hill; a narrowing here is the "
                            "registered outcome, not a surprise" if bad else
                            "certificate validity is supported off hill as well as on it"))

    # ---- KF-3 / KF-4 -------------------------------------------------------------------
    kills["KF-3"] = _map_kill(
        "KF-3", "spade_cf_m0", "spade_random_plate2", targets, families,
        fires_if_below_sesoi=True,
        interpretation_fail=(
            "targeted plate-2 SUR did not demonstrate value beyond random second-plate "
            "wells. Spec §7.3's registered consequence applies: the mechanistic claim comes "
            "out of the paper. This is THE load-bearing causal comparison of the study"),
        interpretation_pass=(
            "boundary-targeted plate 2 beats an equal-well random second plate by at least "
            "SESOI, so the mechanistic claim survives its own strongest control"))
    kills["KF-4"] = _map_kill(
        "KF-4", "spade_cf_m0", "spade_plate1_only", targets, families,
        fires_if_below_sesoi=True,
        interpretation_fail=(
            "plate 2 does not improve the map over plate 1 alone. Note the asymmetry spec "
            "§4.1 requires: plate1_only is budget-short by 8 wells, so it is a rounds/wells "
            "reference and NOT an equal-well comparator -- this failure is the stronger "
            "reading of the two, not the weaker one"),
        interpretation_pass=(
            "plate 2 improves the map over plate 1 alone, against a comparator that is 8 "
            "wells short and therefore favourable to plate 2"))

    # ---- KF-5, the §7.5 conjunction ----------------------------------------------------
    kills["KF-5"] = _kf5(rows, certificate, targets, families, map_cell=map_cell)

    # ---- KF-6 / KF-7 -------------------------------------------------------------------
    for name, comparator, label in (("KF-6", "sobol", "Sobol"),
                                    ("KF-7", "qlognei", "qLogNEI")):
        kills[name] = _map_kill(
            name, "spade_cf_m0", comparator, targets, families,
            fires_if_below_sesoi=False,
            interpretation_fail=(
                f"{label} beats SPADE on the map by more than SESOI in a TARGET condition, "
                "and the paper says so plainly (§10.1 item 3). §19/§13 already record "
                "`sobol` as the best arm on three of four families"),
            interpretation_pass=(
                f"SPADE is within SESOI of {label} on the symmetric difference in the "
                "TARGET regime, which is competitiveness and is never phrased as a win "
                "(§9 publication guard 1)"))

    # ---- KF-8 --------------------------------------------------------------------------
    kills["KF-8"] = _kf8(rows, targets)

    # ---- KF-9 --------------------------------------------------------------------------
    primary_rows = [r for r in live_rows(rows) if condition_key(r) in PRIMARY_CONDITIONS]
    breached = [r for r in primary_rows if r.get("above_ceiling")]
    kills["KF-9"] = _kill(
        "KF-9", "FAIL" if breached else ("PASS" if primary_rows else "NOT_RUN"),
        effect=len(breached), denominator=len(primary_rows),
        comparison="a count, not an effect size; SESOI does not apply",
        artefact=CERTIFICATE_ARTEFACT, source_key="cells[].infeasible",
        interpretation=(
            f"{len(breached)} primary row(s) sit at or above the certifiability ceiling and "
            "reached the analyser. §4.5: no method certifies above tau_max at any budget, "
            "so these cells must be excluded BEFORE campaigns run. A zero scored there is a "
            "property of the threshold and reading it as a method failure is precisely the "
            "error the pre-run feasibility gate exists to stop" if breached else
            "every analysed primary cell sits below the certifiability ceiling, as the "
            "pre-run feasibility gate requires"))

    # ---- KF-10 -------------------------------------------------------------------------
    downgraded = [c for c in cells if c.get("downgraded_by") == "KF-10"]
    pass_eligible = [c for c in cells
                     if c.get("verdict") == "PASS" or c.get("downgraded_by") == "KF-10"]
    kills["KF-10"] = _kill(
        "KF-10", "FAIL" if downgraded else ("PASS" if cells else "NOT_RUN"),
        effect=len(downgraded), denominator=len(pass_eligible) or len(cells),
        comparison=(f"empty-rate ceiling {EMPTY_RATE_CEILING:.0%}; SESOI does not apply to "
                    "a degeneracy guard"),
        source_key="cells[].downgraded_by",
        interpretation=(
            f"{len(downgraded)} cell(s) reached PASS on containment while certifying "
            "nothing in more than half their campaigns, and were downgraded to "
            "INCONCLUSIVE. §41.3 records the same failure mode off hill: the problem is "
            "emptiness, not miscoverage -- and an empty certificate is vacuously contained"
            if downgraded else
            "no PASS rests on a mostly-empty cell; the containment records that passed were "
            "earned on campaigns that actually certified something"))

    for kill in kills.values():
        if withheld:
            kill.pop("status", None)
            kill["status_withheld"] = True

    return {
        "study_id": envelope.get("study_id", STUDY_ID),
        "registration_commit": envelope.get("registration_commit", REGISTRATION_COMMIT),
        "code_commit": envelope.get("code_commit"),
        "artefact": LEDGER_ARTEFACT,
        "verdicts_withheld": withheld,
        "status_semantics": {
            "PASS": "the registered claim survives",
            "FAIL": "the claim does not survive; the registered consequence applies",
            "INCONCLUSIVE": "the design cannot answer it here",
            "NOT_RUN": "the arms or cells it needs are absent -- NOT a pass (§35.2)",
            "MOOT": "settled elsewhere; the contrast is not defined",
        },
        "target_primary_conditions": targets,
        "broad_paper_condition": (
            "spec §10.1: the broad SPADE-method paper is supportable only if ALL of the "
            "seven conditions hold. If any fails the paper claim NARROWS -- it is never "
            "hidden"),
        "kills": kills,
    }


def _kf5(rows: list, certificate: dict, targets: list, families: dict,
         map_cell: tuple | None = None) -> dict:
    """The §7.5 allocation conjunction: regret, map, calibration, certificate -- all four.

    §7.5 is deliberately a conjunction and not a headline number: *"A regret reduction that
    damages the certificate is not a SPADE improvement. It is reported as a trade-off."*
    Each clause is evaluated and reported separately below, so a near-miss says which clause
    it missed rather than collapsing to a boolean.
    """
    variants = [a for a in ("spade_cf_m4", "spade_cf_m8")
                if any(r["arm"] == a for r in _assessable(rows))]
    if not targets or not variants:
        return _kill("KF-5", "NOT_RUN" if not variants else "INCONCLUSIVE",
                     artefact=PARETO_ARTEFACT, source_key="rows[arm=spade_cf_m{4,8}]",
                     interpretation=("the m>0 arms or a TARGET primary condition are absent, "
                                     "so the allocation question the study was built to ask "
                                     "prospectively (§1.1) cannot be answered here"))
    best = None
    for cond in targets:
        sub = [r for r in _assessable(rows) if condition_key(r) == cond]
        # 🔴 REGRESSION, fixed alongside the write_reports/main() wiring bug: this
        # function's OWN signature already accepted `map_cell` but never read it, calling
        # `_sole_map_cell(sub)` unconditionally. On a multi-cell run that raises
        # InvalidPooling even after `kill_ledger` was fixed to forward `map_cell` in --
        # the fix at the caller was necessary but not sufficient.
        tf, gamma, alpha = map_cell or _sole_map_cell(sub)
        for arm in variants:
            if arm not in {r["arm"] for r in sub}:
                continue
            regret = compare_regret(sub, "spade_cf_m0", arm, rule_a=PRIMARY_TERMINAL_RULE)
            map_c = paired_contrast(sub, arm, "spade_cf_m0", PRIMARY_MAP_SCALAR,
                                    tau_frac=tf, gamma=gamma, alpha=alpha)
            cal = paired_contrast(sub, arm, "spade_cf_m0", "murphy_calibration",
                                  tau_frac=tf, gamma=gamma, alpha=alpha)
            cert_ok = _certificate_status(certificate, arm, cond) in ("PASS", "WITHHELD",
                                                                     "NOT_ASSESSED")
            clauses = {
                "regret_reduced_by_sesoi": bool(regret["effect"] is not None
                                                and regret["effect"] >= SESOI),
                "map_not_worse_by_more_than_0.02": bool(map_c["effect"] is not None
                                                        and map_c["effect"] <= 0.02),
                "calibration_not_worse_by_more_than_0.005": bool(
                    cal["effect"] is not None and cal["effect"] <= 0.005),
                "certificate_retained": cert_ok,
            }
            cand = (cond, arm, regret, clauses)
            if best is None or (all(clauses.values()) and not all(best[3].values())):
                best = cand
    cond, arm, regret, clauses = best
    met = all(clauses.values())
    adj = holm_within_family("F-ALLOC", {f"{arm}@{cond}": regret["p"]})
    entry = _kill("KF-5", "PASS" if met else "FAIL",
                  effect=regret["effect"], ci=regret["ci"], p=regret["p"],
                  p_adjusted=adj[f"{arm}@{cond}"], denominator=regret["n25"]["n"],
                  comparison=(f"rule-{PRIMARY_TERMINAL_RULE} regret reduction "
                              f"{regret['effect']:+.5f} against SESOI {SESOI}"),
                  artefact=PARETO_ARTEFACT,
                  source_key=f"rows[arm={arm},condition={cond}].regret.P",
                  interpretation=(
                      f"{arm} meets every clause of the §7.5 conjunction in {cond}: it "
                      "lowers rule-P regret by at least SESOI without costing the map, the "
                      "calibration or the certificate" if met else
                      f"{arm} does not meet the full §7.5 conjunction in {cond}, so m>0 is "
                      "reported as a TRADE-OFF and not as an improvement. A regret "
                      "reduction that damages the certificate is not a SPADE improvement"))
    entry["clauses"] = clauses
    entry["holm_family"] = "F-ALLOC"
    entry["terminal_rule"] = PRIMARY_TERMINAL_RULE
    return entry


def _kf8(rows: list, targets: list) -> dict:
    """Regret parity against the best BO arm, under ONE rule on both sides.

    The bar is the best BO arm's **rule-P** regret computed on this same run -- the
    like-for-like bar §43.1 had to construct after the fact when the registered one turned
    out to be a rule-A column. Choosing the best arm from the run is legitimate *here* only
    because the direction is against SPADE: a bar chosen to be as strong as possible cannot
    manufacture a parity claim.
    """
    conditions = targets or [c for c in sorted({condition_key(r) for r in _assessable(rows)})
                             if c in PRIMARY_CONDITIONS]
    for cond in conditions:
        sub = [r for r in _assessable(rows) if condition_key(r) == cond]
        arms = {r["arm"] for r in sub}
        bo = [a for a in BO_ARMS if a in arms]
        if "spade_cf_m0" not in arms or not bo:
            continue
        means = arm_means(sub, regret_key(PRIMARY_TERMINAL_RULE))
        best_bo = min(bo, key=lambda a: means[a])
        c = compare_regret(sub, "spade_cf_m0", best_bo, rule_a=PRIMARY_TERMINAL_RULE)
        failed = c["effect"] is not None and c["effect"] > SESOI
        entry = _kill("KF-8", "FAIL" if failed else "PASS",
                      effect=c["effect"], ci=c["ci"], p=c["p"],
                      denominator=c["n25"]["n"],
                      comparison=f"gap {c['effect']:+.5f} against SESOI {SESOI}",
                      artefact=PARETO_ARTEFACT,
                      source_key=f"rows[arm=spade_cf_m0,condition={cond}].regret.P",
                      interpretation=(
                          f"SPADE's rule-P regret exceeds {best_bo}'s by more than SESOI, so "
                          "SPADE is a CERTIFICATION-FIRST TRADE-OFF and is stated as such "
                          "(§10.1 item 6), never as a search win" if failed else
                          f"SPADE is within SESOI of {best_bo} under a common terminal rule. "
                          "That is PARITY and §11 prohibits calling practical parity a "
                          "superiority win -- §43.1 is this project doing it once already"))
        entry["bar_arm"] = best_bo
        entry["terminal_rule"] = PRIMARY_TERMINAL_RULE
        entry["estimand_note"] = ("both sides are rule P. §43.1: the registered r* bar was a "
                                  "rule A column and the mixed comparison had to be "
                                  "withdrawn")
        entry["units_disagree"] = c["units_disagree"]
        return entry
    return _kill("KF-8", "NOT_RUN", artefact=PARETO_ARTEFACT,
                 source_key="rows[arm in qlognei,qlogei].regret.P",
                 interpretation=("no primary condition carries both spade_cf_m0 and a BO "
                                 "arm. §4 makes both BO arms mandatory precisely so this "
                                 "cannot be answered against the weaker one alone"))


# ==========================================================================
# I/O
# ==========================================================================

def assert_gate_clean(payload: dict, *, allow_partial: bool = False) -> None:
    """Refuse a run that failed its own gates, unless partial reading is explicit.

    `analyse_fix1` sets the precedent and states the reason in one line: a run with gate
    failures means *"the rule-P column describes a different experiment"*. The escape hatch
    exists because looking at a broken run is how you find out what broke, and it cannot
    produce a verdict.
    """
    failures = payload.get("gate_failures") or []
    if failures and not allow_partial:
        raise GateFailure(
            f"{len(failures)} gate failure(s) in the run: {failures[:3]}. Its columns do "
            "not describe the registered experiment. Re-run, or pass --allow-partial to "
            "read the tables without producing any verdict")


def load(path: Path) -> dict:
    payload = json.loads(Path(path).read_text())
    if "rows" not in payload:
        raise ValueError(f"{path} carries no 'rows'; this analyser reads the raw-row "
                         "envelope defined by boec.final_spade.ROW_SCHEMA")
    return payload


def write_reports(rows: list, *, out_dir: Path, envelope: dict | None = None,
                  source: Path | None = None, allow_partial: bool = False,
                  map_cell: tuple | None = None) -> list:
    """Build and write the three artefacts. Refuses to write over its own input.

    `analyse_versionc_form1.verdict_path` earned this guard: a derived output name collided
    with the input path and the analyser **overwrote the run it was asked to read** -- a few
    kB of verdict destroying hours of compute. The check is explicit rather than relying on
    every future filename happening not to collide.
    """
    out_dir = Path(out_dir)
    paths = [out_dir / Path(a).name
             for a in (CERTIFICATE_ARTEFACT, PARETO_ARTEFACT, LEDGER_ARTEFACT)]
    if source is not None:
        src = Path(source).resolve()
        for p in paths:
            if p.resolve() == src:
                raise RefusedOverwrite(
                    f"the output path {p} is the file this analyser was asked to read. "
                    "Refusing to write: a few kB of verdict must never destroy a campaign")

    cert = certificate_report(rows, allow_partial=allow_partial, envelope=envelope)
    pareto = regret_pareto_report(rows, certificate=cert, map_cell=map_cell,
                                  allow_partial=allow_partial, envelope=envelope)
    # 🔴 REGRESSION, fixed: `map_cell` was silently dropped here. `kill_ledger` accepts
    # it and needs it for `_family_contrasts`'s own `_sole_map_cell` fallback, so a run
    # spanning more than one (tau_frac, gamma, alpha) cell raised InvalidPooling even
    # after the caller had named the cell explicitly via --map-cell. See
    # tests/test_final_spade_statistics.py::test_write_reports_honours_an_explicit_map_cell_on_a_multi_cell_run.
    ledger = kill_ledger(rows, cert, pareto, allow_partial=allow_partial,
                         envelope=envelope, map_cell=map_cell)

    out_dir.mkdir(parents=True, exist_ok=True)
    for p, payload in zip(paths, (cert, pareto, ledger), strict=True):
        p.write_text(json.dumps(payload, indent=1, default=list))
    return [str(p) for p in paths]


# ==========================================================================
# Printing -- the tables, which --allow-partial still produces
# ==========================================================================

RULE = "=" * 104


def print_certificate(cert: dict) -> None:
    print(f"{RULE}\n  CERTIFICATE VALIDITY -- cross-fit PRIMARY, same-draw diagnostic "
          f"(spec §2.1, §7.1)\n{RULE}")
    print(f"    {'arm':>20}{'condition':>20}{'tf':>6}{'gam':>6}{'a':>6}"
          f"{'X/n':>10}{'rate':>8}{'95% CI':>19}{'p exact':>10}{'p Holm':>10}"
          f"{'empty':>8}{'sd-cf':>8}  verdict")
    for c in cert["cells"]:
        cf = c["crossfit"]
        rate = "  --" if cf["proportion"] is None else f"{cf['proportion']:.4f}"
        ci = ("        --         " if cf["ci_lo"] is None
              else f"[{cf['ci_lo']:.4f},{cf['ci_hi']:.4f}]")
        pe = "  --" if cf["exact_p"] is None else f"{cf['exact_p']:.3e}"
        ph = "  --" if cf["p_holm"] is None else f"{cf['p_holm']:.3e}"
        er = "  --" if c["empty_rate"] is None else f"{c['empty_rate']:.2f}"
        gap = ("  --" if c["same_draw_minus_crossfit"] is None
               else f"{c['same_draw_minus_crossfit']:+.4f}")
        verdict = c.get("verdict", "WITHHELD")
        flag = "  <<<" if verdict == "FAIL" else ""
        counts = f"{cf['x']}/{cf['n']}"
        print(f"    {c['arm']:>20}{c['condition']:>20}{c['tau_frac']:>6.2f}"
              f"{c['gamma']:>6.2f}{c['alpha']:>6.2f}{counts:>10}"
              f"{rate:>8}{ci:>19}{pe:>10}{ph:>10}{er:>8}{gap:>8}  {verdict}{flag}")
        if c.get("downgraded_by"):
            print(f"{'':>26}! downgraded by {c['downgraded_by']}: {c['verdict_reason']}")
    for cond, block in cert["conditions"].items():
        if block["unavailable_reason"]:
            print(f"\n    ! {cond}: {block['unavailable_reason']}")


def print_pareto(pareto: dict) -> None:
    print(f"\n{RULE}\n  REGRET AND MAP -- BOTH terminal rules, symmetric difference as the "
          f"map scalar (spec §7.2, §7.4)\n{RULE}")
    print(f"    {'arm':>20}{'condition':>20}{'rnd':>5}{'wells':>7}"
          f"{'regret A':>11}{'regret P*':>11}{'sym diff':>11}{'cert':>15}{'pareto':>8}")
    for e in pareto["rows"]:
        ra = "   --" if e["regret"]["A"] is None else f"{e['regret']['A']:.4f}"
        rp = "   --" if e["regret"]["P"] is None else f"{e['regret']['P']:.4f}"
        sd = "   --" if e["symmetric_difference"] is None \
            else f"{e['symmetric_difference']:.4f}"
        print(f"    {e['arm']:>20}{e['condition']:>20}{e['rounds']:>5}{e['wells']:>7}"
              f"{ra:>11}{rp:>11}{sd:>11}{e['certificate_status']:>15}"
              f"{('yes' if e['pareto_nondominated'] else ''):>8}")
    print("    * rule P is the primary estimand (§7.4). Comparing one arm's rule A against "
          "another's rule P is a protocol violation.")


def print_ledger(ledger: dict) -> None:
    print(f"\n{RULE}\n  KILL LEDGER -- spec §10, all ten, NOT_RUN is not a pass\n{RULE}")
    for name in sorted(ledger["kills"], key=lambda k: int(k.split("-")[1])):
        k = ledger["kills"][name]
        status = k.get("status", "WITHHELD")
        mark = "🔴 " if status == "FAIL" else "   "
        eff = "" if k["effect"] is None else f"  effect {k['effect']:+.5f}"
        den = "" if k["denominator"] is None else f"  n={k['denominator']}"
        padj = "" if k["p_adjusted"] is None else f"  p_holm={k['p_adjusted']:.3e}"
        print(f"  {mark}{name:<6} {status:<13}{eff}{den}{padj}")
        print(f"        {k['claim']}")
        print(f"        {k['interpretation']}")
        print(f"        source: {k['source']['artefact']} :: {k['source']['key']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=str(ROOT / "results" / "final-spade-primary.json"))
    ap.add_argument("--out-dir", default=str(ROOT / "results"))
    ap.add_argument("--allow-partial", action="store_true",
                    help="print the tables but emit NO verdict of any kind (spec §6)")
    ap.add_argument("--map-cell", default=None,
                    help="tau_frac,gamma,alpha for the map metrics when the run spans "
                         "several; the registration names no single one, so this analyser "
                         "refuses to choose")
    args = ap.parse_args()

    src = Path(args.file)
    payload = load(src)
    assert_gate_clean(payload, allow_partial=args.allow_partial)
    rows = payload["rows"]
    envelope = {k: payload.get(k) for k in ("study_id", "registration_commit",
                                            "code_commit")}
    map_cell = None
    if args.map_cell:
        tf, g, a = (float(v) for v in args.map_cell.split(","))
        map_cell = (tf, g, a)

    cert = certificate_report(rows, allow_partial=args.allow_partial, envelope=envelope)
    pareto = regret_pareto_report(rows, certificate=cert, map_cell=map_cell,
                                  allow_partial=args.allow_partial, envelope=envelope)
    ledger = kill_ledger(rows, cert, pareto, allow_partial=args.allow_partial,
                         envelope=envelope, map_cell=map_cell)

    print(f"{RULE}\n  {payload.get('study_id', STUDY_ID)} · registration "
          f"{payload.get('registration_commit', REGISTRATION_COMMIT)} · code "
          f"{payload.get('code_commit')} · {len(rows)} rows\n{RULE}")
    if args.allow_partial:
        print("  ! --allow-partial: tables only. NO verdict, NO kill status, NO "
              "conclusion.\n")
    print_certificate(cert)
    print_pareto(pareto)
    print_ledger(ledger)

    paths = write_reports(rows, out_dir=Path(args.out_dir), envelope=envelope,
                          source=src, allow_partial=args.allow_partial,
                          map_cell=map_cell)
    print()
    for p in paths:
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
