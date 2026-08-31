# SPADE EC calibration freeze policy

This policy governs the transition from development calibration to the prospective
EC benchmark. The calibration report is training-only: it may use seeds 0–63 and
the registered synthetic families, but it must not read, score, or summarize seeds
64–95. Evaluation seeds remain unopened until the calibration parameters and this
policy are committed.

The frozen report records the fitting method, parameter values, training seed list,
family list, code/spec digests, and a timestamp/commit identifier. After freeze,
calibration parameters are immutable. Any change creates a new version and requires
discarding any evaluation output made under the old version.

The template at `results/ec-training-calibration-template.json` is deliberately
`TRAINING_ONLY_TEMPLATE`, has `evaluation_status: NOT_RUN`, and contains no claims.
It is not an evaluation result and must not be cited as one. At this revision no
evaluation seeds were run; consequently no evaluation result exists.

Before evaluation, the operator must verify that training and evaluation seed sets
are disjoint, validate the report with `validate_training_report`, and record the
freeze commit. The evaluation analyzer remains fail-closed and requires a complete
grid with evaluation provenance.
