# Cover letter

Dear Editors,

Please consider our research article, “SPADE improves operating-region decisions under fixed experimental budgets: a synthetic comparison with Bayesian optimization and response-surface design,” for PLOS ONE.

Cell-manufacturing and formulation campaigns often treat “find the best recipe” and “define a trustworthy operating region” as if they were the same decision. They are not. We evaluate SPADE, an assay-oriented integration of established Gaussian-process level-set and conservative-set methods, against noisy Bayesian optimization (qLogNEI) and response-surface design of experiments under matched 48-well budgets on synthetic landscapes.

The contribution is decision guidance for operating-region use cases, not universal method superiority. At matched five rounds, SPADE returned greater certified volume than qLogNEI (`+0.000855`, 95% CI `[+0.000691,+0.001028]`, `p<0.0001`, `n=320` dependent cells). Five-round SPADE showed no detectable point-regret difference from ten-round qLogNEI (`-0.0005`, 95% CI `[-0.0221,+0.0207]`, `p=0.96`, `n=160`), without claiming equivalence. Screened three-round DoE found the better point recipe (`+0.1026` SPADE-minus-DoE regret, 95% CI `[+0.0486,+0.1578]`, `p=0.0003`), while five-round SPADE’s answered regional decisions showed stronger observed truth containment (66/160 answered, 66/66 contained) than screened DoE (122/160, 85/122) or unscreened DoE (134/160, 77/134). We retain the real-noise ceiling, the later `NO_SELECTION` development stop, the unopened lockbox, and the absence of prospective wet-lab validation so “better for the region” cannot be misread as manufacturing qualification. The original posterior certificate checks do not establish empirical or calibration validity.

Reviewer-access materials are at https://github.com/akwnn/nutrigene-ai-bo-ipsec. An archival DOI will be minted upon acceptance or at submission if a Zenodo deposit is completed first.

This manuscript is not under consideration elsewhere. The authors have had no prior interactions with PLOS regarding this work, and there are no related manuscripts or preprints currently under review.

Suggested Academic Editor expertise: Bayesian optimization / Gaussian processes, design of experiments and response-surface methodology, computational statistics or simulation methodology, and bioprocess / formulation development. We have no opposed reviewers.

Both authors will have reviewed the manuscript, agreed to the listed CRediT contributions, and approved this submission before it is filed (Joseph Yung confirmation pending).

Sincerely,

Alana Wai Han Kwan  
Department of Chemical Engineering, Columbia University  
11281128alana@gmail.com
