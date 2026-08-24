# Design Specification: SPADE-First Research Summary

## Objective

`docs/RESEARCH-SUMMARY.md` will be rewritten from a terminal-rule BO-versus-RSM manuscript into the principal SPADE-first research summary for the paper. It must remain more compact than `docs/PROJECT-UNDERSTANDING-OUTLINE.md`, but it must function as a coherent near-manuscript rather than an append-only experiment log.

The revised summary will answer five questions without requiring the reader to consult historical findings documents: why an operating region is a different deliverable from one optimal recipe; what SPADE does; how the synthetic benchmark and prospective study were implemented; what the current results establish; and which claims remain narrow, incomplete, or reserved.

## Scientific Framing

The headline contribution is design-space learning. The registered target result is that all three SPADE allocation variants have lower mean symmetric-difference error than every non-SPADE comparator reported in the target table. The primary `m0` arm achieves map error 0.1804 and Rule-P regret 0.0844 in two rounds, compared with qLogNEI map error 0.2135 and regret 0.0691 in ten rounds. The 0.0153 mean regret gap is inside the 0.02 practical margin, but its interval extends slightly beyond that margin.

The earlier point-optimization program will be retained as motivation. It will show that terminal selection rules can reverse BO-versus-RSM conclusions and that point regret does not measure acceptable-region quality. Detailed internal experiment chronology will be condensed. Only results that materially support the SPADE paper's argument will remain in the main summary; additional numeric tables will be routed to the outline, findings documents, or supplement.

The summary will distinguish map accuracy, calibration, and certification. SPADE's map and refinement results are strong, but retrospective calibration is mid-field. Prospective Hill containment is not shown below nominal, yet its weakest confirmatory cell has only 13 non-empty certificates and a wide interval. Cross-family certificate validity is not established. Levy and Rosenbrock under-cover at high assurance in the independent five-family analysis, while Ackley and Hartmann often produce no non-empty certificate.

## Boundary-Targeting Reservation

The current targeted-versus-control comparison is undergoing correction. The rewritten summary must not include its current effect, interval, probability value, kill identifier, verdict, or mechanistic interpretation. It may describe the implemented straddle acquisition in Methods and state that the causal value of boundary-focused placement is reserved pending corrected analysis.

The target performance table will omit the matched control while the correction is pending. This omission must be explained explicitly and may not be used to claim that `m0`, `m4`, and `m8` are the top three arms overall. The safe statement is that all three SPADE allocation variants have lower mean map error than every non-SPADE comparator shown.

## Manuscript Architecture

The new summary will retain a conventional scientific structure:

1. Title, compact abstract, and revision status.
2. Introduction centered on one recipe versus an operating region.
3. Methods covering the synthetic Hill generator, observation model, external families, comparators, SPADE's two rounds, map and certificate estimands, target classification, inference, and release provenance.
4. Results organized by scientific claim: terminal-rule motivation; target-condition performance; second-round and allocation results that are currently interpretable; Hartmann robustness; Ackley exception; Levy/Rosenbrock non-discrimination; calibration and refinement; certificate scope; feasibility and empty-set guards; full-dimensional DoE; and experimental rounds.
5. Discussion, laboratory decision guide, limitations, conclusion, data availability, evidence map, and references.

The summary will use polished paragraphs rather than a list of experiment IDs. Internal labels may appear in provenance notes but will not organize the scientific narrative.

## Evidence and Numerical Controls

Current committed decision artifacts govern prospective values. The rewrite will use `results/final-spade-regret-pareto.json`, `results/final-spade-certificate.json`, `results/final-spade-kill-ledger.json`, and `results/final-spade-manifest.json` ahead of stale prose. The reported prospective dataset contains 99,601 rows: 92,400 original rows, 7,200 `doe_unscreened` rows, and one structured d=8 unavailability declaration.

The plate-one comparison will be stated correctly: primary SPADE reduces map error from 0.1921 to 0.1804, an improvement of 0.0117 with adjusted p approximately 0.00013, but the effect is below the 0.02 smallest effect of interest. Positive-`m` allocation will be reported as an unmet conjunction rather than an improvement. `doe_unscreened` will be described as implemented at every d=6 condition and structurally unavailable at d=8.

The summary will report that eight of 44 raw-passing certificate cells were downgraded for more than 50% emptiness and that 4,400 of 23,600 primary-probability rows reached analysis at or above the certifiability ceiling. These are guard or protocol findings, not method-performance failures.

Fresh-clone reproducibility will be described accurately. The repository reports a green nine-check release audit on the generating machine, but the ignored raw condition files and `final-spade-primary.json` are absent from the checkout, so the local validator reports blocking missing-artifact violations. Targeted final-SPADE tests pass 173 of 173 in the configured Python 3.11 environment.

## Formatting

Equations will use `$...$` inline and `$$...$$` for display mathematics. The summary will define simple regret, the acceptable region, exceedance probability, symmetric-difference error, and the cross-fit containment target. Tables will name condition, terminal rule, wells, rounds, and evidence scope. The document will contain no malformed HTML spaces, bracket-style display math, placeholders, or stale `doe_unscreened` statements.

## Completion Criteria

The rewrite is complete when the research summary reads as one SPADE-first paper, contains the current prospective and retrospective evidence needed for that paper, omits the pending boundary-targeting result, removes all statements that `doe_unscreened` is missing, uses the correct 99,601-row provenance, distinguishes target and robustness evidence, and discloses the raw-artifact release limitation.

Every central number must be cross-checked against a committed artifact. Structural verification must confirm a conventional manuscript sequence, balanced display-math delimiters, absence of stale boundary estimates and obsolete status language, and a clean Git diff.
