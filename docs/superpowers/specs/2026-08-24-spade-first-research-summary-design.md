# Design Specification: Estimand-Aware Research Summary

## Objective

`docs/RESEARCH-SUMMARY.md` will be rewritten as the principal scientific summary for an estimand-aware experimental-design paper. The paper will no longer be organized as a claim that SPADE is a fundamentally new or generally superior optimizer. Its central contribution will be a controlled demonstration that experimental-design methods cannot be ranked independently of the terminal decision, scientific deliverable, and experimental cost unit used to evaluate them.

The revised summary must enable a computational or biological reader to understand the laboratory decision, synthetic benchmark, implemented workflows, statistical estimands, strongest results, negative findings, limitations, and publication requirements without consulting the repository's chronological findings logs.

## Recommended Paper

### Working title

**One Recipe Is Not a Design Space: An Estimand-Aware Benchmark of Experimental Design Under Matched Laboratory Budgets**

### Central thesis

Under identical or explicitly reconciled experimental budgets, point search, noisy identification, terminal recommendation, acceptable-region mapping, probability calibration, conservative containment, and experimental rounds reward different properties of an experimental campaign. Consequently, the apparent winner among Bayesian optimization, classical response-surface workflows, space-filling designs, and region-first strategies changes with the decision the laboratory must make.

### Role of SPADE

SPADE will be the prospectively evaluated region-first case study, not the paper's claimed algorithmic invention. Its implemented components—Latin-hypercube initialization, Gaussian-process modeling, straddle-style level-set sampling, and conservative excursion sets based on Vorob'ev quantiles—must be positioned against their established methodological precedents. The paper may claim that the repository evaluates this combination prospectively in a biological-formulation-style benchmark; it may not claim that those ingredients or their combination are unprecedented.

The name SPADE may appear in the abstract, Methods, Results, figures, and Discussion. It should not dominate the title or turn every result into evidence for SPADE. The terminal-decision program supplies the first demonstration of estimand dependence; the prospective SPADE program extends the argument from choosing one recipe to learning an acceptable region.

## Scientific Narrative

The paper will follow one argument rather than repository chronology.

1. A laboratory campaign is incomplete until its terminal decision and deliverable are specified.
2. On the same sampled campaigns, measured-value selection, hidden tested-best performance, model recommendation, in-region recommendation, and confirmation protocols can produce different BO-versus-RSM conclusions.
3. Point optimization and acceptable-region learning are different tasks and reorder the methods again.
4. SPADE demonstrates a region-first trade-off in the registered Hill target regime: leading map accuracy among the displayed non-control comparators, practically close mean point regret, and two decision rounds rather than ten for batch BO.
5. Map accuracy, probabilistic calibration, and whole-region containment are not interchangeable. Strong discrimination can coexist with mid-field calibration, thin containment evidence, or a method declining to certify.
6. The proper conclusion is an evaluation framework and decision guide, not a universal method hierarchy.

The main text will use the results needed to establish that chain. Classical diagnostics, long-run budget curves, full condition tables, allocation variants, kill ledgers, and secondary sensitivities will be summarized only when they change interpretation and otherwise assigned to the supplementary program.

## Evidence Hierarchy

### Central retrospective evidence

The terminal-rule analysis will establish that matched well counts do not define a unique BO-versus-RSM comparison. At the primary higher-noise Hill cell, measured-value selection favors the implemented classical workflow over qLogEI by approximately 0.0595 and over qLogNEI by approximately 0.0574. Search-versus-identification decomposition shows that much of this contrast arises after sampling, when a single noisy observation is used to identify the condition carried forward.

The top-three confirmation result will be reported with its exact limitation. Deciding from the confirmation reading alone changes the primary contrast to approximately -0.0009 with an interval spanning zero. This does not establish that every confirmation protocol produces a tie because averaging the original and confirmation measurements was not run.

The quadratic-recommendation result will be presented as a warning about extrapolative terminal rules. Unconstrained optimization of the fitted classical quadratic produces saddle behavior and a large BO-favorable reversal; restricting the recommendation to the learned region largely removes that result. This is evidence that terminal model use affects the comparison, not evidence that either surrogate class is universally superior.

### Central prospective evidence

In the registered six-factor Hill target condition, primary SPADE has symmetric-difference map error 0.1804 and Rule-P regret 0.0844 in two rounds. qLogNEI has map error 0.2135 and regret 0.0691 in ten rounds. The 0.0331 map difference against qLogNEI is strong target-specific evidence. The 0.0153 regret gap has a mean inside the 0.02 practical margin but an interval extending to approximately 0.0223, so equivalence is not established.

The comparison with Sobol is intentionally more restrained. Primary SPADE's map advantage is approximately 0.0109, below the registered 0.02 smallest effect of interest. Likewise, the map improvement from the 40-well plate-one design to the 48-well primary SPADE workflow is approximately 0.0117, statistically detectable but below the declared meaningful-effect threshold. These results prevent the paper from attributing the target result solely to the second-round policy.

Hartmann at six and eight dimensions provides descriptive robustness of the point-versus-region split: batch BO has lower point regret while SPADE variants have lower map error. Hartmann conditions are not independent confirmatory populations and must not be presented as universal superiority evidence.

### Reliability and negative evidence

The retrospective Murphy decomposition will show that SPADE has strong refinement but not the lowest calibration error. The certificate section will report exact containment numerators, non-empty denominators, intervals, empty rates, and certifiability ceilings. Multiplicity-adjusted failure to reject under-coverage will not be called proof of validity.

Prospective Hill containment will be described as not shown below nominal, with explicit acknowledgement of thin denominators. Cross-family certificate validity is not established. High-assurance under-coverage on Levy and Rosenbrock and frequent empty certificates on Ackley and Hartmann will be retained because they define the boundary of the contribution.

## Boundary-Targeting Reservation

The targeted-versus-control allocation comparison is undergoing correction. The rewritten summary must not include its current effect, interval, probability value, kill identifier, verdict, or mechanistic interpretation.

The implemented acquisition may be described in Methods. However, the code and prose must distinguish the latent-response straddle contour from the predictive acceptable-region boundary, which additionally includes process noise. The final prospective runner invoked the straddle workflow without passing predictive noise to the allocation function. Until a corrected and frozen analysis addresses the intended comparison, the paper may claim performance of the executed two-round workflow but may not claim that boundary targeting caused that performance.

## Manuscript Architecture

1. **Title, abstract, and significance statement.** Lead with the laboratory decision and estimand dependence.
2. **Introduction.** Explain one best recipe versus an acceptable operating region; review BO, RSM, level-set estimation, conservative excursion sets, and quality-by-design precedent; identify the missing integrated evaluation.
3. **Methods.** Define the biological scenario, synthetic generators, observation model, experimental workflows, terminal rules, point and region estimands, calibration and containment measures, budgets, prospective registration, inference, and release provenance.
4. **Results.** Present terminal-decision reversals; search-versus-identification decomposition; confirmation and extrapolation sensitivities; point-versus-region reordering; registered SPADE target performance; Hartmann robustness and declared exceptions; calibration; containment and non-vacuity; classical diagnostics; and rounds.
5. **Discussion.** State what the evidence changes about experimental comparison, interpret SPADE as a region-first trade-off, give a laboratory decision guide, delimit synthetic and certificate claims, and specify the required biological validation.
6. **Data and code availability.** Describe the current release accurately and state what must be archived before submission.

Internal experiment identifiers may appear in provenance notes and the evidence map but must not organize the scientific prose.

## Main Figure Program

### Figure 1: What is the experimental deliverable?

Show one formulation campaign branching into hidden tested-best, noisy measured-value selection, model recommendation, confirmation, acceptable-region mapping, and conservative certification. Distinguish wells from adaptive rounds.

### Figure 2: The terminal decision changes the winner

Use paired estimates or slope plots for the primary Hill condition under measured-value selection, hidden tested-best, unconstrained recommendation, in-region recommendation, posterior-mean-at-visited selection, and top-three confirmation. Include the search-versus-identification decomposition.

### Figure 3: Point and region objectives reorder methods

Plot Rule-P regret against symmetric-difference error for the registered target and Hartmann robustness conditions. Encode wells and feedback rounds separately. The pending matched allocation control must remain absent until its corrected analysis is frozen.

### Figure 4: A good map is not yet a certificate

Combine calibration versus refinement, containment against nominal assurance, empty-certificate rates, non-empty denominators, and certifiability exclusions. The visual conclusion must separate map support from certificate scope.

## Claim Controls

The paper may claim:

- Terminal decisions and scientific deliverables can reorder methods on the same campaigns.
- Point optimization and acceptable-region learning reward different sampling behavior in this benchmark.
- Primary SPADE has lower target-regime map error than the named BO and classical comparators and a mean point-regret gap inside the declared practical margin.
- SPADE uses two decision rounds at 48 wells, whereas the batch-BO comparators use ten.
- Strong map discrimination does not establish calibration or conservative containment.
- Empty certificates, infeasible thresholds, negative ablations, and structurally biased benchmarks must be reported rather than silently converted into successes or ranks.

The paper may not claim:

- SPADE is a fundamentally new level-set or conservative-excursion-set algorithm.
- SPADE is the best optimizer or universally beats BO, Sobol, or DoE.
- Regret equivalence is proven.
- Boundary targeting caused the observed map performance.
- The second round produced a practically meaningful gain under the registered threshold.
- The certificate is validated, calibrated, guaranteed, or portable beyond Hill.
- Empty certificates are conservative successes.
- Two versus ten rounds means fivefold lower calendar time or cost.
- The synthetic Hill surfaces are fitted endothelial biology or constitute wet-lab validation.
- The current checkout is a complete reproducible release.

## Literature Positioning

The Introduction must cite primary sources for each methodological boundary. Box and Wilson motivate sequential RSM; Jones, Schonlau, and Welch motivate efficient global optimization; Gotovos and colleagues establish batched GP level-set estimation; Azzimonti and colleagues establish adaptive conservative excursion-set estimation; Gneiting and co-workers motivate sharpness subject to calibration; ICH Q8 motivates multidimensional design spaces; and current biological BO studies establish that media optimization by BO is already an active experimental field.

The novelty statement will therefore be the integrated, matched-budget, claim-separated evaluation—not the existence of BO, DoE, level-set sampling, design spaces, or probabilistic certificates.

## Evidence and Numerical Controls

Current committed decision artifacts govern prospective values: `results/final-spade-regret-pareto.json`, `results/final-spade-certificate.json`, `results/final-spade-kill-ledger.json`, `results/final-spade-manifest.json`, and `results/final-spade-feasibility.json`. The reported prospective dataset contains 99,601 rows: 92,400 original rows, 7,200 `doe_unscreened` rows, and one structured eight-dimensional unavailability declaration.

The rewritten summary must state that eight of 44 raw-passing certificate cells were downgraded for more than 50% emptiness and that 4,400 of 23,600 primary-probability rows reached analysis at or above the certifiability ceiling. These are protocol and guard findings, not direct method-performance outcomes.

The repository reports a green nine-check release audit on the generating machine, but the raw prospective condition files and `final-spade-primary.json` are absent from the checkout. A fresh local release validation therefore has blocking missing-artifact violations. Targeted final-SPADE tests pass 173 of 173 in the configured Python 3.11 environment, but passing implementation tests must not be presented as a self-contained reproducible release.

## Formatting

The document will use polished scientific prose rather than line-by-line notes. Equations will use `$...$` inline and `$$...$$` for display mathematics. Every symbol will be defined immediately. Tables will state condition, terminal rule, wells, rounds, uncertainty interval, and evidence scope where relevant. The rewrite will contain no malformed HTML spaces, bracket-style display mathematics, placeholders, stale boundary estimates, or obsolete `doe_unscreened` statements.

## Completion Criteria

The rewrite is complete when:

1. The title, abstract, Results, and Discussion express one estimand-aware thesis.
2. SPADE is a major prospective case study but not an unsupported algorithmic novelty claim.
3. Terminal-decision, point-versus-region, calibration, containment, non-vacuity, and round-count evidence are connected in one causal and interpretive chain.
4. The pending boundary-targeting result is fully withheld.
5. All central prospective numbers trace to committed authoritative artifacts.
6. Retrospective findings state their protocol-specific limitations.
7. The 99,601-row provenance and incomplete raw-artifact release are accurate.
8. The main text distinguishes confirmatory, robustness, exploratory, diagnostic, and reserved evidence.
9. Mathematical delimiters, headings, tables, references, and internal links pass structural checks.
10. The Git diff contains only the intended documentation changes.
