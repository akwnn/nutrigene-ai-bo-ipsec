"""Budget-to-target reduction — Q52 §2.

A budget-to-target curve reports *"evaluations needed to reach regret T"*
(METHODS 2.14). This module holds the one reduction that turns a regret-versus-budget
curve into a single arrival budget, and the censoring bookkeeping the registration
demands around it.

**Why censoring is a distinct outcome rather than a missing value.** Q52 registers a
cap of 200 and records, before the run, that the cap *"is a compute limit, not a
scientific one"* — §1.2 shows qLogEI's regret still descending at 500. So a target the
cap forbids an arm from trying for must be reported as CENSORED beside the cap, and
**no arm may be described as "unable to reach" a target it was never allowed to spend
enough to reach.** Collapsing that into ``None`` or ``inf`` would let a compute
decision read downstream as a property of the method, which is exactly the error the
registration exists to prevent.

**Why the first crossing, not the last.** Rule A's identification error *worsens with
budget* on space-filling designs (§1.1: 0.0432 → 0.0746 from n=24 to n=384 at
σ_rel=0.10), so these curves are **not monotone** and a curve may cross a target and
then rise back above it. The quantity the brief asks for is how many evaluations a lab
must spend before it first holds an answer that good, so the arrival is the smallest
qualifying budget. A method that later loses the target again is a finding about rule
A, recorded elsewhere, not a reason to move the arrival.
"""

from __future__ import annotations

from typing import Final, Mapping, Union

__all__ = ["ARRIVAL_CENSORED", "Censored", "first_budget_to_target"]


class Censored:
    """The arm did not reach the target at any budget the cap permitted.

    A singleton rather than ``None`` so that "never got there within 200" cannot be
    confused with a missing measurement, and so that ``is`` comparisons read as the
    verdict they are.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - display only
        return "ARRIVAL_CENSORED"


#: The single censoring verdict. Compare with ``is``.
ARRIVAL_CENSORED: Final[Censored] = Censored()


def first_budget_to_target(
    curve: Mapping[Union[int, str], float],
    *,
    target: float,
    cap: int,
) -> Union[int, Censored]:
    """The smallest budget at or below ``cap`` whose regret meets ``target``.

    Args:
        curve: budget -> regret. Keys may be ``int`` or ``str`` — ``results/*.json``
            stores prefixes as JSON object keys, which are strings, and sorting those
            lexicographically would put 100 before 24. Keys are coerced to ``int``
            and ordered numerically.
        target: the regret to reach. Meeting it exactly counts: the brief asks for
            *"evaluations needed to reach regret T"*, and a curve that lands on T has
            reached it.
        cap: the registered evaluation cap. Checkpoints above it are not consulted,
            because crediting an arm with an arrival it was forbidden to spend for
            would report a compute limit as a method difference.

    Returns:
        The arrival budget, or :data:`ARRIVAL_CENSORED` if no permitted checkpoint
        meets the target.

    Raises:
        ValueError: if ``cap`` is not positive. A non-positive cap admits no
            checkpoint at all, so every arm would come back censored and the grid
            would look like a uniform null rather than a misconfiguration.
    """
    if cap <= 0:
        raise ValueError(
            f"cap={cap!r} admits no checkpoints, so every arm would report "
            "ARRIVAL_CENSORED and a misconfigured run would be indistinguishable "
            "from a universal null. Pass the registered cap (Q52: 200)."
        )

    for budget in sorted(int(b) for b in curve):
        if budget > cap:
            break
        if curve_value(curve, budget) <= target:
            return budget
    return ARRIVAL_CENSORED


def curve_value(curve: Mapping[Union[int, str], float], budget: int) -> float:
    """Read ``curve`` at ``budget`` whichever key type it was stored under."""
    if budget in curve:
        return float(curve[budget])
    return float(curve[str(budget)])
