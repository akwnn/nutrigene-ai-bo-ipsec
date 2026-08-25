# Registered final-SPADE kill ledger

Denominators are reported as counts; intervals, p-values, and SESOI retain the adjudicated evidence without reinterpretation.

| ID | Status | Effect | Interval | p-value | Adjusted p-value | SESOI | Denominator (count) | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KF-1 | PASS | -0.167391 | [0.562969, 0.925397] | 0.004930 | 0.389497 | 0.020000 | 23 | no confirmatory cell is demonstrably below nominal across 64 cells. This is a failure to reject, not a proof of validity (§7.1) -- §22 measured what this design can and cannot detect |
| KF-2 | FAIL | 0.097436 | [0.807873, 0.954669] | 0.993056 | 1.000000 | 0.020000 | 78 | cross-family evidence is not clean, so the certificate claim narrows to hill and says so (§10.1 item 2). §37/§42 predicted SPADE would struggle off hill; a narrowing here is the registered outcome, not a surprise |
| KF-3 | FAIL | -0.001882 | [-0.006238, 0.002608] | 0.410765 | 0.410765 | 0.020000 | 25 | targeted plate-2 SUR did not demonstrate value beyond random second-plate wells. Spec §7.3's registered consequence applies: the mechanistic claim comes out of the paper. This is THE load-bearing causal comparison of the study |
| KF-4 | FAIL | 0.011714 | [0.007430, 0.015644] | 0.000064 | 0.000127 | 0.020000 | 25 | plate 2 does not improve the map over plate 1 alone. Note the asymmetry spec §4.1 requires: plate1_only is budget-short by 8 wells, so it is a rounds/wells reference and NOT an equal-well comparator -- this failure is the stronger reading of the two, not the weaker one |
| KF-5 | FAIL | -0.002776 | [-0.007611, 0.002125] | 0.312333 | 0.312333 | 0.020000 | 25 | spade_cf_m4 does not meet the full §7.5 conjunction in hill-d6-s0.1, so m>0 is reported as a TRADE-OFF and not as an improvement. A regret reduction that damages the certificate is not a SPADE improvement |
| KF-6 | PASS | 0.010892 | [0.005969, 0.015662] | 0.000287 | 0.000287 | 0.020000 | 25 | SPADE is within SESOI of Sobol on the symmetric difference in the TARGET regime, which is competitiveness and is never phrased as a win (§9 publication guard 1) |
| KF-7 | PASS | 0.032655 | [0.028543, 0.037232] | 0.000000 | 0.000000 | 0.020000 | 25 | SPADE is within SESOI of qLogNEI on the symmetric difference in the TARGET regime, which is competitiveness and is never phrased as a win (§9 publication guard 1) |
| KF-8 | PASS | 0.009375 | [0.002578, 0.016151] | 0.014722 | NA | 0.020000 | 25 | SPADE is within SESOI of qlognei under a common terminal rule. That is PARITY and §11 prohibits calling practical parity a superiority win -- §43.1 is this project doing it once already |
| KF-9 | PASS | 0.000000 | NA | NA | NA | 0.020000 | 23600 | every analysed primary-gamma cell sits below the certifiability ceiling, as the pre-run feasibility gate requires |
| KF-10 | FAIL | 18.000000 | NA | NA | NA | 0.020000 | 64 | 18 cell(s) reached PASS on containment while certifying nothing in more than half their campaigns, and were downgraded to INCONCLUSIVE. §41.3 records the same failure mode off hill: the problem is emptiness, not miscoverage -- and an empty certificate is vacuously contained |
