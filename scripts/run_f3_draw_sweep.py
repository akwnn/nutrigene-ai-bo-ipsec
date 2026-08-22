"""F3 · the winner's curse inside ``CE_alpha``, on BOTH axes.

Registered in ``docs/OPEN-QUESTIONS.md`` at commit 445c028, **before this file existed**.
Tests at ``tests/test_f3_draw_sweep.py`` were written and watched fail first.

------------------------------------------------------------------------------------
THE MECHANISM
------------------------------------------------------------------------------------
``conservative_estimate`` scans ``n_rho`` Vorob'ev quantiles and keeps the **largest**
whose containment -- *measured on the draws* -- reaches ``alpha``. A **maximum over
``n_rho`` noisy estimates**, then reported on the same draws that selected it. It is
anti-conservative by construction: the project's own optimizer's-curse result operating
inside its own safety metric.

The bias should peak where the candidates tie. At ``gamma=0.99, tau_frac=0.60`` the true
set covers **0.99916** of the box, the quantiles collapse onto each other, and that is
exactly where the four sub-nominal cells sit.

------------------------------------------------------------------------------------
WHY THE DRAWS ARE DRAWN ONCE AND SLICED
------------------------------------------------------------------------------------
``torch.randn(N, n_draws)`` fills **row-major**. Calling it at 512 and again at 1024
therefore yields a *completely different* realisation for every grid point after the
first -- only row 0's prefix matches. A sweep built that way would confound "more draws"
with "different draws", which is the confound Part IV spent its length isolating.

:func:`nested_draws` draws once at ``max(DRAW_LEVELS)`` and slices, so every level is a
**prefix** of the largest and the sweep is **paired**. Asserted at every level in
``tests/test_f3_draw_sweep.py::test_draw_levels_are_nested_subsamples``, with the torch
behaviour itself pinned beside it so nobody simplifies the runner back into the trap.

------------------------------------------------------------------------------------
WHY THE SEEDS AXIS EXISTS
------------------------------------------------------------------------------------
Erratum 21. At n=50, p=0.95 the exact tail at 45/50 is **0.1036** -- that cell can never
reach p<0.10 -- and after Holm x72 even 42/50 cannot reach 0.05. A draws-only sweep
returns four uncallable cells at four draw levels. At n=200, 180/200 gives an exact tail
of ~0.007, inside Holm x72. **The seeds axis is what makes the experiment able to answer
its own question.**

Every tail here is ``scipy.stats.binom.cdf``. **Never a normal approximation** -- that
substitution is what made section 14's multiplicity correction wrong.

------------------------------------------------------------------------------------
DESIGN, AND WHY IT IS NOT A FULL FACTORIAL
------------------------------------------------------------------------------------
``4 draw levels x 2 n_rho x 5 cells x 200 seeds`` is not affordable: at 4,096 draws a
single ``conservative_estimate`` scan copies ``draws[:, mask]`` at up to 4096 x 2000
doubles per candidate. The design is therefore a **corner-anchored one-factor-at-a-time**
sweep, which answers both questions without the cross terms:

    DRAWS arm : every draw level x every n_rho x every cell, at the committed 50 pairs
    SEEDS arm : the largest draw level and n_rho=64, at all 200 pairs

The two arms share the corner ``(4096, 64, 50 pairs)``, so they are comparable, and the
seeds arm's first 50 pairs are bit-identical to the draws arm's. **Stated because a
fractional design that is not disclosed reads as a full one.**
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Imported, never reimplemented: a second copy of plate 2's LSE selection would be a
# second campaign, and its columns could not be gated against the committed ones at all.
_P2 = _load("_p2", ROOT / "scripts" / "run_p2_versionb_gamma.py")

from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import instance_by_id, unit_bounds                  # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402
from boec.vorobev import (alpha_star, conservative_estimate,         # noqa: E402
                          conservative_estimate_split,
                          containment_probability, empirical_containment)

OUT = ROOT / "results" / "f3-draw-sweep.json"
CKPT = ROOT / "results" / "f3-draw-sweep.ckpt.jsonl"

#: The four section-14 sub-nominal cells, PLUS a negative control at gamma=0.50.
#: The bias is a maximum over near-tied candidates, so it must be near-absent where the
#: quantiles separate. **A sweep that moves at gamma=0.50 too is measuring something
#: other than selection bias**, and without the control that cannot be distinguished.
CELLS = [(0.99, 0.60), (0.99, 0.75), (0.95, 0.60), (0.99, 0.85), (0.50, 0.60)]

DRAW_LEVELS = (512, 1024, 2048, 4096)
#: The bias is a maximum over `n_rho` candidates, so it must SCALE with `n_rho` if the
#: mechanism is what we think. Swept for that reason, not for robustness.
N_RHO_LEVELS = (16, 64)
N_SEEDS = 200                      # 25 instances x 8 seeds; the first 50 are committed
SEEDS_PER_INSTANCE = 8
ALPHA = 0.95                       # the level every section-14 failure sits at
DIM, SIGMA = 6, 0.25
GRID_N, SUBSET_N, GRID_SEED = _P2.GRID_N, _P2.SUBSET_N, _P2.GRID_SEED
ARM = "versionb"                   # the certificate is SPADE's


def exact_tail(x: int, n: int, p: float = 0.95) -> float:
    """``P(X <= x | Binom(n, p))``, EXACT. Never a normal approximation (Erratum 21).

    At n=50, p=0.95 the continuity-corrected normal is 5.31x off at x=42, and that
    substitution is what turned section 14's "one failure survives Holm" into an
    artefact.
    """
    return float(binom.cdf(x, n, p))


def nested_draws(mean: torch.Tensor, L: torch.Tensor, seed: int,
                 n_draws: int) -> torch.Tensor:
    """``[n_draws, N]`` posterior draws that are a PREFIX of the largest level.

    Draws once at ``max(DRAW_LEVELS)`` and slices. See the module docstring: torch fills
    row-major, so re-drawing at each level would change the realisation rather than
    extend it.
    """
    g = torch.Generator().manual_seed(seed)
    z = torch.randn(L.shape[0], max(DRAW_LEVELS), generator=g, dtype=torch.double)
    draws = (mean.reshape(-1, 1).double() + L @ z).T
    return draws[:n_draws]


def _posterior_pieces(X, Y, V, X_sub, dim):
    """The GP fit and the Cholesky of the subset posterior. Paid once per campaign."""
    model = build_gp(X, Y, V, unit_bounds(dim))
    with torch.no_grad():
        post = model.posterior(X_sub)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        mean = post.mean.reshape(-1).double()
    del model, post, cov
    gc.collect()
    return mean, L


def score_one(draws, truth_sub, tau, n_rho) -> dict:
    """Every F3 column for one (draws, tau, n_rho).

    ``ce_contain`` is the CIRCULAR statistic -- ``conservative_estimate`` selects on it,
    so it cannot fall below alpha. It is carried precisely so the bias it cannot see is
    visible beside the empirical figure that can.
    """
    ce = conservative_estimate(draws, tau, ALPHA, n_rho=n_rho)
    n_ce = int(ce.sum())
    emp = empirical_containment(ce, truth_sub, tau)
    split_mask, split_contain = conservative_estimate_split(draws, tau, ALPHA,
                                                            n_rho=n_rho)
    n_split = int(split_mask.sum())
    split_emp = empirical_containment(split_mask, truth_sub, tau)
    return {
        "alpha_star": alpha_star(draws, tau, n_rho=n_rho),
        "ce_vol": n_ce / ce.numel(),
        "ce_empty": n_ce == 0,
        "ce_contain_circular": (containment_probability(draws, ce, tau)
                                if n_ce else float("nan")),
        "ce_empirical": float("nan") if emp is None else float(emp),
        # Version C owns the split; this track owns the measurement. Same row, so the
        # bias and its cross-fit removal are never compared across files.
        "split_vol": n_split / split_mask.numel(),
        "split_empty": n_split == 0,
        "split_contain_heldout": split_contain,
        "split_empirical": float("nan") if split_emp is None else float(split_emp),
    }


def campaign_rows(inst_id: str, seed: int, arm_draw_levels, n_rho_levels) -> list[dict]:
    """One (instance, seed) campaign, scored across every requested (draws, n_rho, cell)."""
    inst = instance_by_id(inst_id, DIM)
    orc_t = BiphasicOracle(inst, sigma_rel=SIGMA, seed=seed)
    X_sub = sobol_grid(DIM, SUBSET_N, seed=GRID_SEED)
    with torch.no_grad():
        truth_sub = orc_t.truth(X_sub).reshape(-1).double()

    X, Y, V, regret = _P2.build_campaign(ARM, inst_id, DIM, SIGMA, seed, orc_t)
    mean, L = _posterior_pieces(X, Y, V, X_sub, DIM)
    mu_max = float(inst.optimum_value)

    rows = []
    for n_draws in arm_draw_levels:
        draws = nested_draws(mean, L, seed=seed, n_draws=n_draws)
        for n_rho in n_rho_levels:
            for gamma, tau_frac in CELLS:
                tau, _ = _P2.tau_for(gamma, tau_frac, SIGMA)
                rows.append({
                    "instance": inst_id, "seed": seed, "arm": ARM,
                    "dim": DIM, "sigma": SIGMA, "regret": regret, "mu_max": mu_max,
                    "gamma": gamma, "tau_frac": tau_frac, "tau": tau,
                    "n_draws": n_draws, "n_rho": n_rho, "alpha": ALPHA,
                    "true_frac_above_tau": float((truth_sub >= tau).double().mean()),
                    **score_one(draws, truth_sub, tau, n_rho)})
        del draws
        gc.collect()
    del X, Y, V, mean, L, truth_sub
    gc.collect()
    return rows


def _provenance(argv, elapsed: float) -> dict:
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                         text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip())
    return {"git_sha": sha, "git_dirty": dirty, "argv": argv,
            "elapsed_s": round(elapsed, 1),
            "python": sys.version.split()[0], "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__,
            "threads": torch.get_num_threads(),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS")}


def read_ckpt(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def pairs_for(n_pairs: int) -> list[tuple[str, int]]:
    """(instance, seed) in a fixed order whose first 50 are the committed pairs.

    25 instances x seeds 0..7. Seeds 0 and 1 come first across all instances, so a run
    truncated at 50 IS the committed set and the seeds arm nests the draws arm.
    """
    insts = sorted({r["instance"] for r in _P2.committed_rows()
                    if r["dim"] == DIM and r["sigma"] == SIGMA})
    out = [(i, s) for s in range(SEEDS_PER_INSTANCE) for i in insts]
    return out[:n_pairs]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-of-design", choices=("draws", "seeds"), default="draws",
                    help="draws: every level x n_rho x cell at 50 pairs. "
                         "seeds: the largest draw level, n_rho=64, at all 200 pairs.")
    ap.add_argument("--limit", type=int, default=None, help="pairs to score")
    ap.add_argument("--ckpt", type=Path, default=None)
    args = ap.parse_args()

    if args.arm_of_design == "draws":
        draw_levels, n_rho_levels, n_pairs = DRAW_LEVELS, N_RHO_LEVELS, 50
    else:
        draw_levels, n_rho_levels, n_pairs = (max(DRAW_LEVELS),), (64,), N_SEEDS
    if args.limit:
        n_pairs = args.limit
    ckpt = args.ckpt or Path(str(CKPT).replace(".ckpt", f".{args.arm_of_design}.ckpt"))

    pairs = pairs_for(n_pairs)
    done = {(e["instance"], e["seed"]) for e in read_ckpt(ckpt)}
    t0 = time.time()

    print(f"F3 · {args.arm_of_design} arm · arm={ARM} d={DIM} sigma={SIGMA}")
    print(f"  draws={draw_levels}  n_rho={n_rho_levels}  alpha={ALPHA}")
    print(f"  cells={CELLS}  (gamma=0.50 is the NEGATIVE CONTROL)")
    print(f"  pairs={len(pairs)}  already done={len(done)}")
    print(f"  rows per campaign = {len(draw_levels)*len(n_rho_levels)*len(CELLS)}")
    print(f"  threads={torch.get_num_threads()} OMP={os.environ.get('OMP_NUM_THREADS')}",
          flush=True)

    n_new = 0
    with ckpt.open("a") as fh:
        for k, (inst_id, seed) in enumerate(pairs, 1):
            if (inst_id, seed) in done:
                continue
            t = time.time()
            rows = campaign_rows(inst_id, seed, draw_levels, n_rho_levels)
            fh.write(json.dumps({"instance": inst_id, "seed": seed,
                                 "rows": rows}) + "\n")
            fh.flush()
            n_new += 1
            el = time.time() - t0
            print(f"  [{k:3d}/{len(pairs)}] {inst_id} seed={seed} "
                  f"{len(rows)} rows ({time.time()-t:.1f}s) "
                  f"~{el/max(n_new,1)*(len(pairs)-k)/60:.1f} min left", flush=True)

    entries = read_ckpt(ckpt)
    rows = [r for e in entries for r in e["rows"]]
    # PER-ARM partial. Both arms previously wrote `f3-draw-sweep.json.partial`, so
    # whichever finished last silently overwrote the other. No data was lost -- the
    # checkpoints are separate and are the source of truth -- but the partial only
    # ever held one arm, and a reader would not have known which.
    work = Path(str(OUT).replace(".json", f".{args.arm_of_design}.json") + ".partial")
    work.write_text(json.dumps({
        "status": "COMPLETE" if len(entries) >= len(pairs) else "PARTIAL",
        "keys_present": len(entries), "keys_expected": len(pairs),
        "provenance": _provenance(sys.argv, time.time() - t0),
        "config": {"arm_of_design": args.arm_of_design, "cells": CELLS,
                   "negative_control": [0.50, 0.60],
                   "draw_levels": list(draw_levels), "n_rho_levels": list(n_rho_levels),
                   "alpha": ALPHA, "arm": ARM, "dim": DIM, "sigma": SIGMA,
                   "n_pairs": len(pairs), "grid_n": GRID_N, "subset_n": SUBSET_N,
                   "tail": "scipy.stats.binom.cdf, EXACT; never a normal approximation "
                           "(Erratum 21)",
                   "design_note": "corner-anchored one-factor-at-a-time, NOT a full "
                                  "factorial; the two arms share (4096, n_rho=64, 50 "
                                  "pairs) and the seeds arm's first 50 pairs are "
                                  "bit-identical to the draws arm's",
                   "nesting_note": "draws are drawn once at max(DRAW_LEVELS) and "
                                   "sliced, so every level is a PREFIX of the largest "
                                   "and the sweep is paired; torch.randn fills "
                                   "row-major so re-drawing per level would change the "
                                   "realisation rather than extend it"},
        "rows": rows}, indent=1))
    print(f"\n{len(entries)} campaigns · {len(rows)} rows -> {work.name}", flush=True)
    print(f"  promote to {OUT.name} when the arm is complete", flush=True)


if __name__ == "__main__":
    main()
