"""boec — Bayesian optimization for hiPSC to endothelial-cell differentiation.

Phase 1: synthetic data. See docs/phase1_build.md for the specification.
"""

__all__ = [
    # Person B — model, experiment machinery
    "campaign", "designs", "discrimination", "e4", "metrics", "optimizers",
    "parametric", "rsm", "runner", "surrogate",
    # Person A — search space, landscapes, measurement
    "evaluators", "oracles", "space", "torch_oracle",
]
