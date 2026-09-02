# Supplementary tables

Headline results, the three figures, and the laboratory decision guide live in `docs/RESEARCH-SUMMARY.md`.

This file marks what is **not** a headline result. The long tables still sit in the main file at the sections below until a journal split; they are supporting, not the argument.

| Content | Main-file section | Why it is supplementary |
|---|---|---|
| Control arms vs qLogEI (LHS, Sobol', random, qLogNEI, coordinate descent) | §5.2 | Sanity checks, not the DoE–BO claim |
| Design × surrogate factorial raw grid | §5.4 | Mechanism for Figure 1’s recommendation panel |
| Levy, Rosenbrock, Hartmann6, Ackley full cells | §5.5 | Generality; Ackley is void |
| Internal run names (E2, Q34, Q35, Q42, Q52, Q53) | §2.4 and §4.4 | Reproducibility tags |

## Figures (main text)

| Figure | File |
|---|---|
| 1. Winner by scoring rule and noise | `results/figures/fig1-scoring.html` |
| 2. Cost in wells and in rounds | `results/figures/cost-curves.html` |
| 3. Saddle and ridge constraint | `results/figures/fig3-saddle.html` |

## Runs that are not in any table yet

`docs/PROMPTS-NEXT.md`: sequential RSM with steepest ascent; BO hidden-true-best column; Hill one-shot GP at five design draws.
