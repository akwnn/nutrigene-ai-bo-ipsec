# Prospective EC benchmark evaluation

This report records the frozen unseen-seed evaluation (`64..95`) on the synthetic
three-CQA EC benchmark. It is computational evidence only, not biological validation.

## Current-commit rerun (authoritative)

The complete artifact `results/ec-evaluation-current.json` was regenerated under the
current checkout and contains 384 rows (three families × 32 seeds × four arms). The
fail-closed analyzer returns `FAIL_CONTAINMENT`.

| Family | SPADE answer rate | SPADE containment | 95% lower bound | False certificates | Mean regret | Verdict |
|---|---:|---:|---:|---:|---:|---|
| ec_broad | 17/32 (0.5313) | 17/17 (1.0000) | 0.8157 | 0 | 0.1315 | fail containment bound |
| ec_narrow | 0/32 (0.0000) | 0/0 | 0.0000 | 0 | 0.2879 | fail answer rate |
| ec_multimodal | 12/32 (0.3750) | 12/12 (1.0000) | 0.7575 | 0 | 0.2377 | fail answer rate |

The current artifact passes provenance validation. The 48-well gate therefore remains
negative despite zero observed false certificates. Containment is not treated as a
success claim when the answer-rate requirement is unmet.

The table below is retained as an earlier evaluation artifact for provenance and is not
the authoritative current-commit result.

| Family | SPADE answer rate | SPADE containment | 95% lower bound | False certificates | Mean regret | Verdict |
|---|---:|---:|---:|---:|---:|---|
| ec_broad | 10/32 (0.3125) | 10/10 (1.0000) | 0.7225 | 0 | 0.2309 | fail answer rate |
| ec_narrow | 0/32 (0.0000) | 0/0 | 0.0000 | 0 | 0.4407 | fail answer rate |
| ec_multimodal | 3/32 (0.0938) | 3/3 (1.0000) | 0.4385 | 0 | 0.3746 | fail answer rate |

## Final adjudication

`FAIL_ANSWER_RATE`.

SPADE produced no false certificates in this run, but it did not meet the required
minimum of 16 answered campaigns and answer rate 0.50 in any family. Containment is
therefore not interpretable as a success claim; perfect containment on very few answered
campaigns is explicitly non-vacuous only when the minimum-answer rule is met.

The original registered benchmark conclusion remains unchanged. These results identify
abstention/answer rate—not false certification—as the current limiting failure mode.

## Fresh policy checks (not pooled with the frozen result)

Two separately checkpointed fresh-seed blocks were run after training-only policy
development. They are reported as sensitivity evidence, not as replacements for the
frozen evaluation above.

| Seed block | Family | SPADE answers | Empirical containment | 95% lower bound | False certificates | Mean regret | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| 96–127 | ec_broad | 25/32 (0.7813) | 1.0000 | 0.8668 | 0 | 0.0885 | fail containment bound |
| 96–127 | ec_narrow | 2/32 (0.0625) | 1.0000 | 0.3424 | 0 | 0.2491 | fail answer rate |
| 96–127 | ec_multimodal | 7/32 (0.2188) | 1.0000 | 0.6457 | 0 | 0.2822 | fail answer rate |
| 160–191 | ec_broad | 22/32 (0.6875) | 1.0000 | 0.8513 | 0 | 0.0745 | fail containment bound |
| 160–191 | ec_narrow | 0/32 (0.0000) | 0/0 | 0.0000 | 0 | 0.3384 | fail answer rate |
| 160–191 | ec_multimodal | 3/32 (0.0938) | 1.0000 | 0.4385 | 0 | 0.3351 | fail answer rate |

The defensible positive claim is therefore bounded: SPADE can improve point selection and
answer rate on the broad synthetic family at this budget, with no observed false
certificates. The data do **not** support a general claim of superior certified-region
recovery or superiority on narrow/multimodal families.

The training-only sweep tested six predeclared inflation/density settings across all three
families and seeds 0–63. No setting achieved the required one-sided 90% containment lower
bound, so no unsafe calibration was promoted. The narrow-family result is consistent with
an estimability limit of the 48-well design, not evidence that a certificate exists but was
hidden by a reporting choice.
