"""Stage 6 — the Hall/Ogle replay, against the claim registered in Q31 before it ran.

    python software/scripts/run_replay_hall_ogle.py

REGISTERED CLAIM (OPEN-QUESTIONS Q31, commit b04a900, before any canonical CSV existed):

    Bayesian optimization reaches the pre-specified top-5 condition set in
    significantly fewer evaluations than uniform random selection over the identical
    candidate set.

    k = 5, budget = 8, ranking from the surviving extraction as corrected, comparator
    is uniform random over the same candidates, Wilcoxon governs significance.

WHY BUDGET 8 AND NOT 48
-----------------------
Stage 2 has 25 conditions and stage 1 has 23. A replay proposes only conditions that
exist in the table, so a budget of 48 reaches the top-5 **by exhaustion** — a method
picking alphabetically would "succeed". Q31 §2 registered 8, about a third of the set,
so the comparison is about search rather than enumeration.

TWO DECISIONS TAKEN HERE, both forced rather than chosen
--------------------------------------------------------
**Opening size.** `batch_plan` gives 2d + 2, which is 10 at d=4 and 14 at d=6 — both
exceed the registered budget of 8, so the default opening cannot be used. Set to 4,
leaving 4 adaptive evaluations. Both arms share that opening (Q18), so the comparison
is paired and the difference is attributable to what happens after it.

**Ranking source.** Q31 registered "the reconciled extraction". There is only one
extraction — the digitizer's CSVs were never committed and died with the folder deleted
in `e28c84c` — so the ranking comes from the single surviving extraction as corrected in
`build_published_dataset.py`. This is recorded as an amendment in Q31 rather than passed
over: the registration named a source that does not exist.
"""

from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import csv
import warnings
from pathlib import Path

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

from scipy.stats import wilcoxon

from boec.evaluators import LookupEvaluator
from boec.optimizers import AcqConfig, propose
from boec.space import MetricIdentity
from boec.surrogate import build_gp

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "research" / "data" / "published"

K = 5
BUDGET = 8
N_INIT = 4
N_SEEDS = 40
FACTORS = {"stage1": ["c", "civ", "ln111", "ln411", "ln511", "fn"],
           "stage2": ["c", "civ", "ln411", "fn"]}
METRIC = MetricIdentity("cd31_area_over_dapi_norm_fn", "ratio", "hall_ogle_2025_fig")
RULE = "=" * 84


def load(stage: str):
    rows = list(csv.DictReader((PUB / f"hall_ogle_2025_{stage}.csv").open()))
    X = np.array([[int(r[f]) for f in FACTORS[stage]] for r in rows], dtype=float)
    y = np.array([float(r["response"]) if r["response"] else np.nan for r in rows])
    sd = np.array([float(r["response_sd"]) if r["response_sd"] else np.nan for r in rows])
    ids = np.array([int(r["run_id"]) for r in rows])
    return X, y, sd, ids


def evals_to_first_hit(order: list[int], top: set[int]) -> int:
    """1-indexed evaluation at which a top-k condition first appears; BUDGET+1 if never.

    Censored rather than dropped: a run that never finds one is the informative case and
    discarding it would flatter whichever arm fails more often.
    """
    for t, idx in enumerate(order, start=1):
        if idx in top:
            return t
    return BUDGET + 1


def run_bo(ev: LookupEvaluator, cand_idx: np.ndarray, X: np.ndarray, opening: list[int],
           bounds: torch.Tensor, seed: int) -> list[int]:
    order = list(opening)
    proposals: list[int] = []
    Xtr = torch.tensor(X[order], dtype=torch.double)
    Ytr, Yvar = ev.evaluate(X[order])
    Ytr = torch.tensor(Ytr, dtype=torch.double)
    Yvar_t = torch.tensor(Yvar, dtype=torch.double)
    while len(order) < BUDGET:
        remaining = [i for i in cand_idx if i not in order]
        if not remaining:
            break
        model = build_gp(Xtr, Ytr, Yvar_t, bounds)
        pick = propose(model, bounds, 1, Xtr, Ytr,
                       config=AcqConfig(num_restarts=4, raw_samples=64, mc_samples=32),
                       candidates=torch.tensor(X[remaining], dtype=torch.double))
        # FORWARD-COMPATIBILITY REQUIREMENT 2, verified rather than assumed. Discrete
        # mode is the whole reason the replay is possible -- only conditions the study
        # actually ran have measured outcomes -- and this is its first contact with real
        # data. `optimize_acqf_discrete` returns rows of `choices` by construction, but
        # rounding the proposal before matching would hide it if that ever stopped being
        # true, so the raw proposal is checked against the menu first.
        raw = pick.numpy()[0]
        menu = X[remaining]
        exact = np.flatnonzero((np.abs(menu - raw) < 1e-9).all(axis=1))
        if exact.size != 1:
            raise AssertionError(
                f"proposal {raw.tolist()} matches {exact.size} of {len(remaining)} menu "
                "entries exactly; discrete candidate mode is not being honoured")
        chosen = remaining[int(exact[0])]
        proposals.append(chosen)
        order.append(chosen)
        y1, v1 = ev.evaluate(X[[chosen]])
        Xtr = torch.cat([Xtr, torch.tensor(X[[chosen]], dtype=torch.double)])
        Ytr = torch.cat([Ytr, torch.tensor(y1, dtype=torch.double)])
        Yvar_t = torch.cat([Yvar_t, torch.tensor(v1, dtype=torch.double)])
    return order, proposals


def rule_c_first_hit(X, y, sd, order, cand_idx, top, bounds) -> int:
    """Evaluations until the MODEL'S RECOMMENDATION is a top-k condition.

    Rule A -- the registered endpoint -- asks when a top-k condition is first *measured*.
    Rule C asks when the fitted model would first *tell you to use* one, which is what a
    practitioner reads off a finished campaign. The two can differ in both directions: a
    method can stumble onto a good condition without knowing it is good, and a method can
    identify one from neighbouring evidence before ever running it.

    Both arms are scored with the SAME model and the SAME recommendation rule -- the
    posterior-mean argmax over the whole candidate menu -- so the only thing that differs
    is where the points were placed. Random has no model of its own; giving it this one
    is what makes the comparison about design rather than about having a surrogate.
    """
    for t in range(N_INIT, len(order) + 1):
        idx = order[:t]
        Xtr = torch.tensor(X[idx], dtype=torch.double)
        Ytr = torch.tensor(y[idx].reshape(-1, 1), dtype=torch.double)
        Yvar = torch.tensor((sd[idx] ** 2).reshape(-1, 1), dtype=torch.double)
        model = build_gp(Xtr, Ytr, Yvar, bounds)
        with torch.no_grad():
            mu = model.posterior(
                torch.tensor(X[cand_idx], dtype=torch.double)).mean.squeeze(-1)
        if int(cand_idx[int(mu.argmax())]) in top:
            return t
    return BUDGET + 1


def run_stage(stage: str) -> None:
    X, y, sd, ids = load(stage)
    valid = np.where(~np.isnan(y))[0]
    top = set(valid[np.argsort(y[valid])[::-1][:K]].tolist())
    d = X.shape[1]
    bounds = torch.stack([torch.full((d,), -1.0, dtype=torch.double),
                          torch.full((d,), 1.0, dtype=torch.double)])

    print(f"\n{RULE}\nREPLAY · {stage} · {len(valid)} usable of {len(y)} conditions · "
          f"budget {BUDGET} · opening {N_INIT} · k={K}\n{RULE}")
    print(f"  top-{K} conditions (run_id): {sorted(ids[sorted(top)].tolist())}")

    bo_hits, rd_hits, bo_rec, rd_rec = [], [], [], []
    n_proposals = [0]
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(seed)
        opening = rng.choice(valid, size=N_INIT, replace=False).tolist()

        ev = LookupEvaluator(X, y, sd, METRIC)
        bo_order, proposals = run_bo(ev, valid, X, opening, bounds, seed)
        assert all(i in valid.tolist() for i in proposals), (
            "a proposal fell outside the candidate set")
        assert len(set(bo_order)) == len(bo_order), "a condition was proposed twice"

        rest = [i for i in valid.tolist() if i not in opening]
        rd_order = opening + rng.permutation(rest).tolist()[: BUDGET - N_INIT]

        bo_hits.append(evals_to_first_hit(bo_order, top))
        rd_hits.append(evals_to_first_hit(rd_order, top))
        bo_rec.append(rule_c_first_hit(X, y, sd, bo_order, valid, top, bounds))
        rd_rec.append(rule_c_first_hit(X, y, sd, rd_order, valid, top, bounds))
        n_proposals[0] += len(proposals)

    bo = np.array(bo_hits, float)
    rd = np.array(rd_hits, float)
    diff = rd - bo                      # >0 means BO got there sooner
    try:
        p = wilcoxon(diff).pvalue
    except ValueError:
        p = float("nan")
    boot = np.array([diff[np.random.default_rng(s).integers(0, len(diff), len(diff))].mean()
                     for s in range(2000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])

    print(f"\n  {'arm':<10}{'median evals to first top-5':>30}{'never found':>14}")
    print(f"  {'qLogEI':<10}{np.median(bo):>30.2f}{int((bo > BUDGET).sum()):>14}")
    print(f"  {'random':<10}{np.median(rd):>30.2f}{int((rd > BUDGET).sum()):>14}")
    print(f"\n  paired difference (random − BO) = {diff.mean():+.3f} "
          f"[{lo:+.3f}, {hi:+.3f}]  wilcoxon p={p:.4f}")
    verdict = ("BO FASTER — claim supported" if lo > 0 and p < 0.05
               else "NULL — BO is not faster than random. Claim REFUTED as registered.")
    print(f"  {verdict}")
    print(f"  [rule A — best observed — is the REGISTERED endpoint; the verdict is this one]")
    print(f"  discrete mode: {n_proposals[0]} proposals, every one verified in the menu")

    bc, rc = np.array(bo_rec, float), np.array(rd_rec, float)
    dc = rc - bc
    try:
        pc = wilcoxon(dc).pvalue
    except ValueError:
        pc = float("nan")
    bootc = np.array([dc[np.random.default_rng(s).integers(0, len(dc), len(dc))].mean()
                      for s in range(2000)])
    loc, hic = np.percentile(bootc, [2.5, 97.5])
    print(f"\n  RULE C — evaluations until the model RECOMMENDS a top-{K} condition")
    print(f"  (secondary, NOT the registered endpoint; same GP and same recommendation "
          f"rule for both arms)")
    print(f"  {'qLogEI':<10}{np.median(bc):>30.2f}{int((bc > BUDGET).sum()):>14}")
    print(f"  {'random':<10}{np.median(rc):>30.2f}{int((rc > BUDGET).sum()):>14}")
    print(f"  paired difference (random − BO) = {dc.mean():+.3f} "
          f"[{loc:+.3f}, {hic:+.3f}]  wilcoxon p={pc:.4f}")


def main() -> None:
    for stage in ("stage2", "stage1"):
        run_stage(stage)
    print(f"\n{RULE}\n  Registered in Q31 before the dataset existed. Reported as it came out.\n{RULE}")


if __name__ == "__main__":
    main()
