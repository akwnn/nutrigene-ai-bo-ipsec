# PLOS ONE Manuscript Revision Design

**Status:** approved for implementation
**Date:** 2026-09-07
**Target journal:** PLOS ONE

## Objective

Revise the SPADE manuscript into a technically rigorous PLOS ONE submission whose main
contribution is a reproducible comparison of point and region decisions under matched
experimental budgets. Preserve the supported target-regime findings, report the failed
joint-protocol selection as a separate preregistered negative result, and remove any
language that implies universal validation or biological efficacy.

## Editorial position

The paper leads with a general experimental-design result: method rankings depend on the
decision delivered at the end of a campaign. SPADE is the region-first method used to
test that claim, not a universally superior optimizer.

The manuscript will make four contributions explicit:

1. Point selection and acceptable-region mapping are different estimands and can rank
   the same experimental campaigns differently.
2. Under the prespecified six-factor Hill target, SPADE achieved lower map error than
   qLogNEI while retaining practical point-regret parity and using fewer feedback rounds.
3. Map accuracy, calibration, conditional certificate containment, and certificate
   non-vacuity are distinct properties that must be reported together.
4. A separate 2,750-row development study selected none of nine stricter SPADE
   candidates because every candidate missed the registered 0.90 containment floor in
   every leave-one-family-out training fold. The stop rule prevented power planning and
   kept the lockbox unopened.

## Evidence boundaries

The retrospective campaign rescoring, the 99,601-record prospective SPADE benchmark,
and the later joint-protocol development study remain separate evidence bodies. Their
rows, endpoints, and claims are not pooled. The joint-protocol result may support only a
negative selection-stop conclusion; it cannot modify the historical target-regime
estimates or create a lockbox claim.

The paper will continue to state that all landscapes are synthetic proxies. It will not
claim wet-lab validation, biological efficacy, manufacturing validation, universal
certificate validity, or a measured fivefold reduction in elapsed time.

## Manuscript changes

- Keep the current descriptive title and PLOS ONE article structure.
- Rewrite the abstract so the general contribution comes first and the joint-protocol
  stop appears as direct evidence of limited portability.
- Expand the evidence-body and statistical-method sections to describe the separate
  nine-candidate, five-family selection study and its prespecified stop rule.
- Add a results subsection reporting the authenticated `NO_SELECTION` outcome and the
  unopened lockbox.
- Rework the discussion so the null mechanism result and failed cross-family selection
  define the method's boundary instead of reading as late disclaimers.
- Replace the stale statement that the joint protocol was not run.
- Preserve author, affiliation, funding, contribution, competing-interest, and repository
  DOI fields that require author input, while making their pre-submission status clear.

## Source of truth and outputs

`manuscript/SPADE-PLOS-ONE.md` is the canonical text. The existing modified DOCX builder
remains the generation path so its native Word equations, table geometry, and footer
fixes are preserved. The final outputs are the synchronized Markdown manuscript and
`manuscript/SPADE-PLOS-ONE.docx`.

## Verification

Verification will include manuscript-specific tests, a scan for stale joint-protocol
claims and unsupported universal language, confirmation of all reported numbers against
the committed selection artifact at commit `502ea39`, and a complete DOCX render with
visual inspection of every page.
