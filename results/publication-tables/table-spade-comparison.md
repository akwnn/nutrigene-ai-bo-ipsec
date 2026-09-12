# SPADE comparison across registered conditions

Units: 25 Hill landscape instances with four campaigns per instance; 100 campaigns on each specified external function, not 100 independent landscapes. Rule-P regret and symmetric-difference error are lower-is-better; all listed arms use 48 wells. Maps use a 0.50 cutoff and a frozen condition-specific threshold. The archived posterior model check does not establish empirical certificate validity. Pareto labels retain the original point/map comparison across all archived arms, not only the six displayed strategies.

| Condition | Arm | Rule-P regret (lower is better) | Symmetric-difference error (lower is better) | Wells (count) | Rounds (count) | Archived posterior model-check status (not empirical validity) | Pareto non-dominated | Replication unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ackley-d6-s0.25 | doe | 0.553876 | 0.459858 | 48 | 3 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| ackley-d6-s0.25 | sobol | 0.732109 | 0.238258 | 48 | 1 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| ackley-d6-s0.25 | qlogei | 0.693968 | 0.235983 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| ackley-d6-s0.25 | qlognei | 0.660229 | 0.223334 | 48 | 10 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| ackley-d6-s0.25 | spade_cf_m0 | 0.760073 | 0.238550 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| ackley-d6-s0.25 | spade_random_plate2 | 0.750770 | 0.238871 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | doe | 0.568174 | 0.224417 | 48 | 3 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | sobol | 0.460809 | 0.189911 | 48 | 1 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | qlogei | 0.299650 | 0.225865 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | qlognei | 0.230487 | 0.224274 | 48 | 10 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | spade_cf_m0 | 0.422068 | 0.184830 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| hartmann6-d6-s0.25 | spade_random_plate2 | 0.468670 | 0.199363 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | doe | 0.639142 | 0.250720 | 48 | 3 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | sobol | 0.479634 | 0.200588 | 48 | 1 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | qlogei | 0.294501 | 0.234784 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | qlognei | 0.262029 | 0.219581 | 48 | 10 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | spade_cf_m0 | 0.445404 | 0.190809 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| hartmann6-d8-s0.25 | spade_random_plate2 | 0.454033 | 0.211682 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| hill-d6-s0.1 | doe | 0.307217 | 0.257978 | 48 | 3 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.1 | sobol | 0.085476 | 0.191306 | 48 | 1 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.1 | qlogei | 0.079799 | 0.206715 | 48 | 10 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.1 | qlognei | 0.074989 | 0.213068 | 48 | 10 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.1 | spade_cf_m0 | 0.084364 | 0.180414 | 48 | 2 | INCONCLUSIVE | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.1 | spade_random_plate2 | 0.082195 | 0.178532 | 48 | 2 | INCONCLUSIVE | yes | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | doe | 0.168367 | 0.258287 | 48 | 3 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | sobol | 0.122117 | 0.250434 | 48 | 1 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | qlogei | 0.136973 | 0.252497 | 48 | 10 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | qlognei | 0.127020 | 0.252015 | 48 | 10 | NOT_ASSESSED | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | spade_cf_m0 | 0.112581 | 0.241537 | 48 | 2 | INCONCLUSIVE | no | 25 Hill instances; four campaigns per instance |
| hill-d6-s0.25 | spade_random_plate2 | 0.119376 | 0.241120 | 48 | 2 | INCONCLUSIVE | no | 25 Hill instances; four campaigns per instance |
| levy-d6-s0.25 | doe | 0.268001 | 0.251056 | 48 | 3 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| levy-d6-s0.25 | sobol | 0.072695 | 0.248136 | 48 | 1 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| levy-d6-s0.25 | qlogei | 0.076795 | 0.247002 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| levy-d6-s0.25 | qlognei | 0.065582 | 0.245337 | 48 | 10 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| levy-d6-s0.25 | spade_cf_m0 | 0.074688 | 0.248193 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| levy-d6-s0.25 | spade_random_plate2 | 0.072643 | 0.248078 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | doe | 0.052595 | 0.249409 | 48 | 3 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | sobol | 0.027767 | 0.246650 | 48 | 1 | NOT_ASSESSED | yes | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | qlogei | 0.034737 | 0.247974 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | qlognei | 0.037430 | 0.246563 | 48 | 10 | NOT_ASSESSED | no | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | spade_cf_m0 | 0.031883 | 0.246421 | 48 | 2 | INCONCLUSIVE | no | 100 campaigns on the specified external function |
| rosenbrock-d6-s0.25 | spade_random_plate2 | 0.027158 | 0.246839 | 48 | 2 | INCONCLUSIVE | yes | 100 campaigns on the specified external function |
