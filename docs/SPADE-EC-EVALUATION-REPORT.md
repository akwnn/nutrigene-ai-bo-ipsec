# Prospective EC benchmark evaluation

This report records the frozen unseen-seed evaluation (`64..95`) on the synthetic
three-CQA EC benchmark. It is computational evidence only, not biological validation.

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
