"""Version C §3.3 · **THE ONE-SHOT HELD-OUT SCORING PASS.** Runs exactly once.

The rule was frozen and committed at `b7dcc41` (corrected by Erratum 31 at `ba2e3ec`)
**before this file existed**. This runner scores hartmann6 and ackley against that frozen
rule and emits K-C7's verdict. It cannot be re-run to improve the answer.

WHY THIS IS A SEPARATE FILE FROM `run_versionc_detector.py`
------------------------------------------------------------
That runner's `evaluator_for` raises `HeldOutFamily` **by name** for hartmann6 and ackley,
and its analyser's `_guard` refuses to read such a row. Those guards are load-bearing and
are **not** relaxed here. Adding a `--family` flag to the fitting runner would have made
the single most consequential mistake in the protocol reachable by a typo. The held-out
path therefore gets its own file, and this one refuses the FIT families symmetrically.

WHERE THE BOUNDARY COMES FROM
------------------------------
**The committed document, not the fit file.** A runner that recomputed `min`/`max` from
`results/versionc-detector-fit.*` at run time would re-freeze on whatever that file
happened to contain, which is not what "frozen" means. `assert_freeze_committed` asks
**git** for the committed text and checks both literals appear in it, so a working-tree
edit cannot move the boundary.

WHAT IT DELIBERATELY DOES NOT DO
---------------------------------
No `truth`, no `mu_max`, no oracle-derived column reaches the classification. The decision
path is `additive_share -> classify -> count`, and nothing else. `detector_statistics`
takes no `truth` argument at all, which is the architectural half of the same guarantee.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch
from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.replay import family_evaluator                            # noqa: E402
from boec.surrogate import build_gp                                 # noqa: E402
from boec.versionc import (additive_refit_residual_ratio,           # noqa: E402
                           detector_statistics)

torch.set_num_threads(1)

#: The FROZEN boundary. These two literals are the contract; they are duplicated from the
#: committed freeze block on purpose and checked against it at start-up. They are **not**
#: recomputed from any results file, and this module reads no fit artefact at all.
FROZEN_LO = 0.10542874984223577
FROZEN_HI = 0.8860126525534584
FROZEN_STATISTIC = "additive_share"

#: Scored exactly once, then never again.
HELD_OUT_FAMILIES = ("hartmann6", "ackley")
#: Refused here, symmetrically with the fitting runner refusing the held-out set.
FITTING_FAMILIES = ("hill", "levy", "rosenbrock")

#: Mirrors the fitting run exactly (Erratum 31): same cells, same seeds, same plate.
CELLS = ((6, 0.25), (6, 0.10))
N_SEEDS = 25
N_PER_FAMILY = len(CELLS) * N_SEEDS            # 50
N_PLATE1, GRID_N, GRID_SEED, N_BINS = 40, 20_000, 0, 20

#: K-C7's registered threshold. **Not a round number** -- it is the exact binomial tail.
#: P(X >= 33 | n=50, p=0.5) = 1.6420e-02, Holm x2 = 3.2839e-02 < 0.05; at 32 it is
#: 6.4909e-02 and fails. Erratum 21: exact tails, never a normal approximation.
KC7_MIN_DECEPTIVE = 33
KC7_NULL_P = 0.5

OUT = ROOT / "results" / "versionc-detector-heldout.json"
DOC = "docs/OPEN-QUESTIONS.md"


class FreezeNotCommitted(RuntimeError):
    """The freeze is a commitment. Present-on-disk is not committed."""


class AlreadyScored(RuntimeError):
    """§3.5: the pass cannot be repeated to improve it."""


class WrongFamily(RuntimeError):
    """A fitting family was requested from the held-out runner."""


def assert_freeze_committed() -> str:
    """Ask **git** for the committed document and check both literals are in it."""
    try:
        committed = subprocess.check_output(
            ["git", "show", f"HEAD:{DOC}"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL)
    except Exception as exc:                                        # noqa: BLE001
        raise FreezeNotCommitted(f"cannot read committed {DOC}: {exc}") from exc
    for name, lit in (("lo", FROZEN_LO), ("hi", FROZEN_HI)):
        if repr(lit) not in committed:
            raise FreezeNotCommitted(
                f"frozen {name} {lit!r} does not appear in the COMMITTED {DOC}. The rule "
                f"must be committed before hartmann6 or ackley is touched (§3.3).")
    if "THE DETECTOR RULE IS FROZEN" not in committed:
        raise FreezeNotCommitted(f"the freeze block is not in the committed {DOC}")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   text=True).strip()


def assert_not_already_scored(path: Path = OUT) -> None:
    if Path(path).exists():
        raise AlreadyScored(
            f"{Path(path).name} already exists. §3.5 registers this pass as one-shot: it "
            f"cannot be repeated to improve the answer. Move the existing file aside "
            f"deliberately if you intend to discard a recorded result.")


def classify_family_guard(family: str) -> str:
    if family in FITTING_FAMILIES:
        raise WrongFamily(
            f"{family!r} is a FITTING family. This runner scores the held-out set "
            f"{HELD_OUT_FAMILIES} exactly once; fitting lives in run_versionc_detector.py")
    if family not in HELD_OUT_FAMILIES:
        raise WrongFamily(f"unknown family {family!r}; held-out set is {HELD_OUT_FAMILIES}")
    return family


def classify(additive_share: float) -> str:
    """The FROZEN rule. **Inclusive boundary means UNIMODAL** -- on the fit range is inside."""
    v = float(additive_share)
    return "DECEPTIVE" if (v < FROZEN_LO or v > FROZEN_HI) else "UNIMODAL"


def exact_tail(n_deceptive: int, n: int = N_PER_FAMILY, p: float = KC7_NULL_P) -> float:
    """`P(X >= n_deceptive)`. Exact, never a normal approximation (Erratum 21)."""
    return float(binom.sf(n_deceptive - 1, n, p))


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval. Reported, never part of K-C7's gate."""
    if n == 0:
        return (0.0, 1.0)
    phat, z2 = k / n, z * z
    denom = 1.0 + z2 / n
    centre = (phat + z2 / (2 * n)) / denom
    half = z * ((phat * (1 - phat) / n + z2 / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def kc7_verdict(deceptive_counts: dict) -> str:
    """**BOTH** held-out families must clear the threshold. One family is not separation."""
    if set(deceptive_counts) != set(HELD_OUT_FAMILIES):
        raise ValueError(f"need both of {HELD_OUT_FAMILIES}, got {sorted(deceptive_counts)}")
    ok = all(int(deceptive_counts[f]) >= KC7_MIN_DECEPTIVE for f in HELD_OUT_FAMILIES)
    return "NOT_FIRED" if ok else "FIRED"


def _fit_runner():
    """`plate_one` IMPORTED, never re-implemented. A second copy of plate 1 would be a
    second protocol, and its statistics could not be compared to the fit set's at all."""
    spec = importlib.util.spec_from_file_location(
        "_vc_fit", ROOT / "scripts" / "run_versionc_detector.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def score_one(family: str, dim: int, sigma: float, seed: int, fit_mod,
              n_plate1: int = N_PLATE1, grid_n: int = GRID_N) -> dict:
    """One plate 1, one GP, the frozen statistic, and the frozen call. No oracle column."""
    classify_family_guard(family)
    t0 = time.time()
    ev = family_evaluator(family, dim, sigma, seed)
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])
    X, Y, Yvar = fit_mod.plate_one(ev, bounds, n=n_plate1, seed=seed)
    model = build_gp(X, Y, Yvar, bounds)
    stats = detector_statistics(model, X, bounds, grid_n=grid_n, grid_seed=GRID_SEED,
                                n_bins=N_BINS)
    stats.update({
        "family": family, "dim": dim, "sigma": sigma, "seed": seed, "n_plate1": n_plate1,
        "additive_refit_residual": additive_refit_residual_ratio(X, Y, Yvar, bounds),
        "classification": classify(stats[FROZEN_STATISTIC]),
        "secs": round(time.time() - t0, 2),
    })
    return stats


def _provenance(argv, freeze_sha: str) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    return {"git_sha": _git("rev-parse", "HEAD"), "freeze_verified_at_sha": freeze_sha,
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def summarise(rows: list[dict]) -> dict:
    per_family, counts = {}, {}
    for fam in HELD_OUT_FAMILIES:
        fr = [r for r in rows if r["family"] == fam]
        k = sum(1 for r in fr if r["classification"] == "DECEPTIVE")
        counts[fam] = k
        lo, hi = wilson(k, len(fr))
        per_cell = {}
        for dim, sigma in CELLS:
            cr = [r for r in fr if r["dim"] == dim and r["sigma"] == sigma]
            per_cell[f"d{dim}_s{sigma}"] = {
                "n": len(cr),
                "deceptive": sum(1 for r in cr if r["classification"] == "DECEPTIVE")}
        shares = sorted(float(r[FROZEN_STATISTIC]) for r in fr)
        per_family[fam] = {
            "n": len(fr), "deceptive": k,
            "rate": (k / len(fr)) if fr else None,
            "wilson95": [lo, hi],
            "exact_tail_ge_k_vs_p50": exact_tail(k, len(fr)) if fr else None,
            "clears_threshold": k >= KC7_MIN_DECEPTIVE,
            "per_cell": per_cell,
            "additive_share_min": shares[0] if shares else None,
            "additive_share_max": shares[-1] if shares else None,
        }
    verdict = kc7_verdict(counts)
    holm = sorted((per_family[f]["exact_tail_ge_k_vs_p50"], f) for f in HELD_OUT_FAMILIES)
    holm_adj = {f: min(1.0, p * (len(holm) - i)) for i, (p, f) in enumerate(holm)}
    return {
        "k_c7": verdict,
        "k_c7_consequence": ("ship WITHOUT Stage 0 (§3.6)" if verdict == "FIRED"
                             else "the detector separates; Stage 0 is supported"),
        "threshold": KC7_MIN_DECEPTIVE, "n_per_family": N_PER_FAMILY,
        "requires_both_families": True,
        "per_family": per_family, "holm_adjusted_tails": holm_adj,
        "frozen_rule": {"statistic": FROZEN_STATISTIC, "lo": FROZEN_LO, "hi": FROZEN_HI,
                        "boundary_is": "inclusive => UNIMODAL"},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="tiny run to a scratch path; never writes the registered file")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    freeze_sha = assert_freeze_committed()
    final = Path(args.out) if args.out else OUT
    assert_not_already_scored(final)

    cells = ((6, 0.10),) if args.smoke else CELLS
    seeds = range(2 if args.smoke else N_SEEDS)
    n_plate1 = 16 if args.smoke else N_PLATE1
    grid_n = 1024 if args.smoke else GRID_N
    if args.smoke and args.out is None:
        raise SystemExit("--smoke requires --out; it must never write the registered file")

    fit_mod = _fit_runner()
    total = len(HELD_OUT_FAMILIES) * len(cells) * len(seeds)
    print(f"Version C §3.3 · ONE-SHOT HELD-OUT PASS · {HELD_OUT_FAMILIES}")
    print(f"frozen rule verified against committed {DOC} at {freeze_sha[:9]}")
    print(f"DECEPTIVE if {FROZEN_STATISTIC} outside [{FROZEN_LO!r}, {FROZEN_HI!r}]")
    print(f"K-C7 does not fire iff BOTH families >= {KC7_MIN_DECEPTIVE}/{N_PER_FAMILY}")
    print(f"{total} campaigns · plate1={n_plate1} · grid={grid_n}\n")

    rows, n = [], 0
    partial = final.with_suffix(final.suffix + ".partial")
    for family in HELD_OUT_FAMILIES:
        for dim, sigma in cells:
            for seed in seeds:
                rows.append(score_one(family, dim, sigma, seed, fit_mod,
                                      n_plate1=n_plate1, grid_n=grid_n))
                n += 1
                r = rows[-1]
                print(f"[{n:3d}/{total}] {family:<10} d={dim} s={sigma} seed={seed:<2d} "
                      f"add={r[FROZEN_STATISTIC]:.4f} -> {r['classification']:<9} "
                      f"({r['secs']}s)", flush=True)
                partial.write_text(json.dumps(
                    {"status": "complete" if n == total else "partial",
                     "complete": n == total, "keys_present": n, "keys_expected": total,
                     "provenance": _provenance(sys.argv, freeze_sha),
                     "config": {"held_out": list(HELD_OUT_FAMILIES),
                                "cells": [list(c) for c in cells], "n_seeds": len(seeds),
                                "n_plate1": n_plate1, "grid_n": grid_n,
                                "grid_seed": GRID_SEED, "n_bins": N_BINS,
                                "one_shot": True},
                     "summary": summarise(rows) if n == total else None,
                     "rows": rows}, indent=1))
    final.write_text(partial.read_text())
    partial.unlink()

    s = summarise(rows)
    print(f"\n{'='*70}")
    for fam in HELD_OUT_FAMILIES:
        p = s["per_family"][fam]
        print(f"  {fam:<11} {p['deceptive']:>3d}/{p['n']} DECEPTIVE  "
              f"rate {p['rate']:.3f}  Wilson95 [{p['wilson95'][0]:.3f}, "
              f"{p['wilson95'][1]:.3f}]  clears={p['clears_threshold']}")
    print(f"\n  K-C7: {s['k_c7']} -- {s['k_c7_consequence']}")
    print(f"{'='*70}\nwrote {final.name} · {len(rows)} rows")


if __name__ == "__main__":
    main()
