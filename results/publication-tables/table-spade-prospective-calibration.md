# Prospective calibration at the registered target cell

Unit: n=25 landscape instances; four campaign seeds are averaged within each instance. Brier, Murphy calibration, symmetric-difference error, and Rule-P regret are lower-is-better.

| Arm | Brier (lower is better) | Murphy calibration (lower is better) | Murphy refinement | AUC | Symmetric-difference error (lower is better) | Rule-P regret (lower is better) | Wells (count) | Rounds (count) | Landscape instances (n) | Campaigns per instance (n) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spade_cf_m4 | 0.127530 | 0.003992 | 0.065231 | 0.850172 | 0.177045 | 0.087140 | 48 | 2 | 25 | 4 |
| spade_random_plate2 | 0.128336 | 0.003439 | 0.063878 | 0.848822 | 0.178532 | 0.082195 | 48 | 2 | 25 | 4 |
| spade_cf_m0 | 0.129053 | 0.003851 | 0.063549 | 0.845496 | 0.180414 | 0.084364 | 48 | 2 | 25 | 4 |
| spade_cf_m8 | 0.129523 | 0.004055 | 0.063315 | 0.844670 | 0.179674 | 0.083501 | 48 | 2 | 25 | 4 |
| lhs | 0.132453 | 0.004189 | 0.060520 | 0.839356 | 0.186703 | 0.074739 | 48 | 1 | 25 | 4 |
| sobol | 0.135133 | 0.004639 | 0.058338 | 0.834193 | 0.191306 | 0.085476 | 48 | 1 | 25 | 4 |
| spade_plate1_only | 0.136691 | 0.003541 | 0.055690 | 0.826579 | 0.192128 | 0.086318 | 40 | 1 | 25 | 4 |
| random | 0.146415 | 0.006823 | 0.049254 | 0.798752 | 0.205029 | 0.090463 | 48 | 1 | 25 | 4 |
| qlogei | 0.148773 | 0.012983 | 0.052726 | 0.802016 | 0.206715 | 0.079799 | 48 | 10 | 25 | 4 |
| qlognei | 0.154572 | 0.012131 | 0.045979 | 0.771543 | 0.213068 | 0.074989 | 48 | 10 | 25 | 4 |
| doe_unscreened | 0.177263 | 0.014582 | 0.027626 | 0.737940 | 0.250226 | 0.286635 | 48 | 1 | 25 | 4 |
| doe | 0.216097 | 0.032985 | 0.007302 | 0.598652 | 0.257978 | 0.307217 | 48 | 3 | 25 | 4 |
