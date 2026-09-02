#!/usr/bin/env python
"""Q50's paired contrast, recomputed so it exists as an artefact rather than a memory.

    python scripts/q50_paired_recompute.py

WHY THIS SCRIPT EXISTS
----------------------
`docs/CLAIMS.md` and `docs/OPEN-QUESTIONS.md` quote the project's most load-bearing
sentence: at the registered primary cell (d=6, sigma_rel=0.25), design-averaged,

    lhs - qlogei = +0.0219 [+0.0145, +0.0292], Wilcoxon p = 1.8e-5, BO ahead 21/25.

No committed script produced it, and none could. The `qlogei` side is fine --
`results/q50-qlogei-seedsweep.json` keeps all 1000 rows with their instance IDs. The
`lhs` side is not: `run_q48_design_variance.py:82` builds a list of per-instance regrets
and then returns `float(np.mean(out))`, so `q48-design-variance.json` stores 60 design
means per arm-cell and nothing underneath them. A paired test needs the values that line
was throwing away.

This is the D12/D17 family for the third time: a number that is almost certainly right,
resting on nothing a second person can re-run. So the fix is not to re-derive the number
by cleverness, it is to re-run the cheap half and write the pieces down.

WHAT IT COSTS
-------------
Nothing much. The `lhs` arm is a static space-filling design -- no surrogate, no
acquisition optimisation. 60 designs x 25 instances x 2 noise seeds = 3000 campaign
evaluations of 48 points, which is seconds. The BO side is NOT re-run; it is read from
the committed seed sweep.

WHAT IT WRITES
--------------
`results/q50-paired.json`, holding the per-instance vectors for both arms, so the next
person can re-pair without re-running anything at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.diagnostics import reported_best_curve  # noqa: E402
from boec.oracles import load_ensemble  # noqa: E402
from boec.runner import static_design  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402

# The registered primary cell. Not a parameter -- this script reproduces one claim.
DIM, SIGMA = 6, 0.25
BUDGET, N_INSTANCES = 48, 25
NOISE_SEEDS = (0, 1)
N_DESIGNS = 60
ARM = "lhs"
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 0

RESULTS = ROOT / "results"


def lhs_from_artefact() -> dict[str, float] | None:
    """``{instance_id: design-averaged regret}`` read from `q48-design-variance.json`.

    Returns ``None`` when the file predates the 2026-08-14 repair and still holds only
    the 60 design means, in which case :func:`lhs_per_instance` re-runs the arm.

    Preferring the artefact is the point of that repair: the first version of this
    script had to recompute because the per-instance axis had been thrown away. Now it
    is stored, so the default path reads it and the recompute becomes a cross-check
    (``--recompute``) rather than the only option.
    """
    path = RESULTS / "q48-design-variance.json"
    if not path.exists():
        return None
    records = json.loads(path.read_text())
    rec = next(
        (
            r
            for r in records
            if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12 and r["arm"] == ARM
        ),
        None,
    )
    if rec is None or "per_instance_design_averaged" not in rec:
        return None
    return dict(zip(rec["instance_ids"], rec["per_instance_design_averaged"]))


def lhs_per_instance() -> dict[str, float]:
    """``{instance_id: design-averaged regret}`` for the static arm, recomputed.

    This is `run_q48_design_variance.cell_mean` with the collapse removed: it keeps the
    per-instance axis instead of averaging it away, then averages over designs and noise
    seeds only.

    Keyed by ``instance_id`` rather than by position. The two arms were produced by
    different scripts months apart, and pairing them by list order would be silently
    wrong the first time either ensemble is reordered -- which is the same class of
    mistake this whole script exists to repair.
    """
    ens = load_ensemble(dim=DIM)[:N_INSTANCES]
    bounds = torch.stack(
        [torch.zeros(DIM, dtype=torch.double), torch.ones(DIM, dtype=torch.double)]
    )
    # (n_designs, n_instances, n_noise_seeds)
    cube = np.empty((N_DESIGNS, N_INSTANCES, len(NOISE_SEEDS)), dtype=float)
    for d, design_seed in enumerate(range(N_DESIGNS)):
        X = static_design(bounds, ARM, BUDGET, design_seed)
        for i, inst in enumerate(ens):
            for s_idx, s in enumerate(NOISE_SEEDS):
                oracle = BiphasicOracle(inst, sigma_rel=SIGMA, seed=s)
                Y, _ = oracle.evaluate(X)
                cube[d, i, s_idx] = float(inst.optimum_value) - float(
                    reported_best_curve(oracle.truth(X), Y)[-1]
                )
        if (d + 1) % 10 == 0:
            print(f"    {d + 1}/{N_DESIGNS} designs")
    means = cube.mean(axis=(0, 2))
    return {inst.instance_id: float(means[i]) for i, inst in enumerate(ens)}


def qlogei_per_instance(max_seeds: int | None = None) -> dict[str, float]:
    """``{instance_id: campaign-seed-averaged regret}``, read from the committed sweep.

    Args:
        max_seeds: use only campaign seeds ``< max_seeds``. ``None`` uses all 20. This
            exists to reproduce the historical 8-seed figures -- see :func:`main`.
    """
    sweep = json.loads((RESULTS / "q50-qlogei-seedsweep.json").read_text())
    by_instance: dict[str, list[float]] = {}
    for row in sweep["rows"]:
        if max_seeds is not None and int(row["campaign_seed"]) >= max_seeds:
            continue
        by_instance.setdefault(str(row["instance"]), []).append(float(row["regret"]))
    return {k: float(np.mean(v)) for k, v in by_instance.items()}


def align(lhs: dict[str, float], qlogei: dict[str, float]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Match the two arms by ``instance_id``, refusing to proceed if they disagree.

    A paired test on mismatched instances still returns a number, and the number looks
    entirely reasonable. So this is a hard failure, not a warning.
    """
    if set(lhs) != set(qlogei):
        only_lhs = sorted(set(lhs) - set(qlogei))
        only_bo = sorted(set(qlogei) - set(lhs))
        raise SystemExit(
            "the two arms are not over the same instances -- refusing to pair.\n"
            f"  only in {ARM}: {only_lhs}\n  only in qlogei: {only_bo}"
        )
    if len(lhs) != N_INSTANCES:
        raise SystemExit(f"expected {N_INSTANCES} instances, found {len(lhs)}")
    ids = sorted(lhs)
    return ids, np.array([lhs[i] for i in ids]), np.array([qlogei[i] for i in ids])


def paired_stats(lhs: np.ndarray, qlogei: np.ndarray) -> dict:
    diff = lhs - qlogei
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot = np.array(
        [rng.choice(diff, size=diff.size, replace=True).mean() for _ in range(BOOTSTRAP)]
    )
    lo, hi = np.percentile(boot, [2.5, 97.5])
    wilcoxon = stats.wilcoxon(lhs, qlogei)
    return {
        "mean_difference": float(diff.mean()),
        "ci95_bootstrap": [float(lo), float(hi)],
        "wilcoxon_statistic": float(wilcoxon.statistic),
        "wilcoxon_p": float(wilcoxon.pvalue),
        "bo_ahead_on": int((diff > 0).sum()),
        "n_instances": int(diff.size),
    }


def main() -> int:
    force_recompute = "--recompute" in sys.argv
    print("=" * 78)
    print(f"Q50 paired contrast | d={DIM} sigma_rel={SIGMA} budget={BUDGET}")
    print("=" * 78)

    lhs_map = None if force_recompute else lhs_from_artefact()
    if lhs_map is not None:
        source = "results/q48-design-variance.json (per-instance axis)"
        print(f"  {ARM} arm read from {source}")
    else:
        source = f"recomputed: {N_DESIGNS} designs x {N_INSTANCES} instances"
        print(f"  re-running the {ARM} arm, keeping the per-instance axis:")
        lhs_map = lhs_per_instance()
    ids, lhs, qlogei = align(lhs_map, qlogei_per_instance())
    print(f"  paired on {len(ids)} matching instance_ids")

    print(f"\n  {ARM} design-averaged     {lhs.mean():.4f}")
    print(f"  qlogei seed-averaged  {qlogei.mean():.4f}")
    print(f"  difference            {lhs.mean() - qlogei.mean():+.4f}")

    st = paired_stats(lhs, qlogei)
    print(f"\n  PAIRED AT INSTANCE LEVEL (n={st['n_instances']}), all 20 campaign seeds")
    print(f"    mean lhs - qlogei   {st['mean_difference']:+.4f}")
    print(f"    95% CI (bootstrap)  [{st['ci95_bootstrap'][0]:+.4f}, {st['ci95_bootstrap'][1]:+.4f}]")
    print(f"    Wilcoxon p          {st['wilcoxon_p']:.3g}")
    print(f"    BO ahead on         {st['bo_ahead_on']} of {st['n_instances']} instances")

    # The figures in CLAIMS.md/OPEN-QUESTIONS.md were computed before the sweep finished.
    # Reproducing them here is what identifies the discrepancy as "stale", rather than
    # leaving two different sets of numbers in the record with no account of the gap.
    _ids8, lhs8, q8 = align(lhs_map, qlogei_per_instance(max_seeds=8))
    st8 = paired_stats(lhs8, q8)
    print(f"\n  HISTORICAL, first 8 campaign seeds only -- what the docs quoted:")
    print(f"    mean lhs - qlogei   {st8['mean_difference']:+.4f}")
    print(f"    Wilcoxon p          {st8['wilcoxon_p']:.3g}")
    print(f"    BO ahead on         {st8['bo_ahead_on']} of {st8['n_instances']} instances")
    print(f"    -> the arm mean is 0.1532 either way, which is why the staleness hid.")

    payload = {
        "cell": {"dim": DIM, "sigma_rel": SIGMA, "budget": BUDGET},
        "instance_ids": ids,
        "lhs": {
            "arm": ARM,
            "source": source,
            "n_designs": N_DESIGNS,
            "noise_seeds": list(NOISE_SEEDS),
            "design_averaged": float(lhs.mean()),
            "per_instance": [float(v) for v in lhs],
        },
        "qlogei": {
            "source": "results/q50-qlogei-seedsweep.json",
            "seed_averaged": float(qlogei.mean()),
            "per_instance": [float(v) for v in qlogei],
        },
        "paired": st,
        "paired_historical_8_seeds": st8,
        "note": (
            "Per-instance vectors are stored so the pairing can be redone without "
            "re-running anything. run_q48_design_variance.py collapses these to a mean "
            "before returning, which is why this claim had no artefact behind it."
        ),
        "staleness_finding": (
            "The paired figures previously in CLAIMS.md and OPEN-QUESTIONS.md "
            "(+0.0219, p=1.8e-5, 21/25) are reproduced exactly by restricting qlogei to "
            "its first 8 campaign seeds. They were computed before the 20-seed sweep "
            "finished and were never refreshed, because no script existed to refresh "
            "them. The arm mean is 0.1532 to four decimals at 8 seeds and at 20, so the "
            "staleness was invisible in the headline number."
        ),
    }
    out = RESULTS / "q50-paired.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n  written to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
