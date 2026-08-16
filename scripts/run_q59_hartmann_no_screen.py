"""Q59 — is BO's Hartmann6 win about optimization, or about the screen? Workstream 5.

    python scripts/run_q59_hartmann_no_screen.py [n_seeds] [--workers 3]

THE CONFOUND
------------
Hartmann6 has **six active coordinates**. The classical pipeline this project runs screens
6 factors down to 4 before building its response surface, because that is what the
published study did and what the shared 48-well budget affords at d=6 and d=8 alike.

On the Hill oracle that cut is nearly free — the landscape has inactive directions to
throw away. **On Hartmann6 it throws away two coordinates that genuinely matter.** So the
stored result *"BO wins on Hartmann6 under every rule"* bundles two different failures:
the optimizer's, and the screen's. It cannot currently distinguish them, and a reviewer
will say so.

THE TWO PROTOCOLS
-----------------
Same landscapes, same seeds, same budget of 48, same locators. Only the classical arm's
design changes:

* **screened** — the published pipeline: 20-run screen, keep 4, 27-run CCD on the
  survivors, 1 confirmation. Gated against the committed D20-corrected column.
* **unscreened** — no screen at all: a half-fraction face-centred CCD on **all six**
  coordinates, 47 runs, plus 1 confirmation. Exactly 48.

WHY THIS ONLY EXISTS AT d = 6, AND THAT IS ITSELF THE ANSWER TO PART OF THE QUESTION
--------------------------------------------------------------------------------------
A full second-order model needs ``C(d+2, 2)`` terms: 28 at d=6, **45 at d=8**. The
face-centred CCDs available inside a 48-well budget are:

===== ========== ======= ============ =============
d     n_derived  runs    +confirm     residual df
===== ========== ======= ============ =============
6     1          47      **48**       19
8     2          83      84           38
8     4          35      36           **cannot fit**
===== ========== ======= ============ =============

At d=8 nothing lands on 48, and the only design small enough carries 35 runs for a 45-term
model — fewer observations than parameters. **An unscreened classical pipeline is not
merely worse at d=8, it is arithmetically impossible within the shared budget.** That is
not a limitation of this script; it is the reason the 6→4 screen exists, and it is
reported rather than worked around.

A SECOND CONSEQUENCE, WORTH STATING BEFORE THE NUMBERS
--------------------------------------------------------
The screened pipeline's CCD sits in a **sub-box** centred on the best screening run, so its
fitted quadratic can recommend a point outside the region it was fitted on — the
extrapolation failure mode that produces the 0.27–0.36 gap elsewhere in this project. The
unscreened CCD spans the **whole box**, so that failure mode cannot occur by construction:
its constrained and unconstrained recommendations are the same search. If the giant gap
shrinks under this protocol, that is evidence the gap is about the screen's sub-box, not
about quadratics.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig                    # noqa: E402
from boec.designs import central_composite, scale_to_box              # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                      # noqa: E402
from boec.metrics import constrained_argmax                           # noqa: E402
from boec.optimizers import AcqConfig                                 # noqa: E402
from boec.oracles import Hartmann6, UnitScaled                        # noqa: E402
from boec.rsm import fit_second_order, second_order_n_terms           # noqa: E402
from boec.torch_oracle import TorchEvaluator                          # noqa: E402

DIM, BUDGET, Q = 6, 48, 4
SIGMAS = (0.25, 0.10)
N_SEEDS = 25
N_RESTARTS, RAW_SAMPLES = 20, 4096
N_BOOT = 4000
GATE_TOL = 1e-12

#: The unscreened design. `n_derived=1` is the only fraction that lands on 47 runs, which
#: with one confirmation is exactly the shared budget. Not a tuning choice — the table in
#: the module docstring shows it is the only option at d=6.
CCD_N_DERIVED, CCD_N_CENTRE = 1, 3

OUT = ROOT / "results" / "q59-hartmann-no-screen.json"
D20 = ROOT / "results" / "d20-rescore.json"
RULE = "=" * 100


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(DIM, dtype=torch.double),
                        torch.ones(DIM, dtype=torch.double)])


def _oracle():
    return UnitScaled(Hartmann6())


def run_unscreened_ccd(evaluator, bounds, *, truth, optimum_value: float, seed: int) -> dict:
    """The classical pipeline with the screen removed. 47-run CCD + 1 confirmation.

    Deliberately parallel to :func:`boec.doe.run_doe_arm` and deliberately **not** a
    modification of it — the stored arm is locked, and a variant that shared its code path
    could not be gated against it.
    """
    ccd = central_composite(DIM, n_centre=CCD_N_CENTRE, n_derived=CCD_N_DERIVED,
                            face_centred=True)
    n = int(ccd.coded.shape[0])
    if n + 1 != BUDGET:
        raise ValueError(
            f"unscreened design is {n} runs + 1 confirmation = {n + 1}, not the shared "
            f"{BUDGET}. A budget that does not match makes this arm incomparable.")
    p = second_order_n_terms(DIM)
    if n <= p:
        raise ValueError(f"{n} runs cannot fit {p} second-order terms at d={DIM}.")

    X = scale_to_box(ccd.coded, bounds)
    Y, _ = evaluator.evaluate(X)
    fit = fit_second_order(X, Y)

    # The design spans the whole box, so there is no sub-box to escape: the constrained
    # and unconstrained searches are the same search. Recorded as one number, with that
    # equality stated rather than two identical columns implying independent evidence.
    x_star, _, _ = constrained_argmax(fit.predict, bounds, n_restarts=N_RESTARTS,
                                      raw_samples=RAW_SAMPLES, seed=seed)
    x_star = x_star.reshape(1, -1)
    Yc, _ = evaluator.evaluate(x_star)

    X_all = torch.cat([X, x_star])
    Y_all = torch.cat([Y, Yc])
    t_all = truth(X_all).double()
    return dict(
        rule_a=optimum_value - float(reported_best_curve(t_all, Y_all)[-1]),
        oracle_best=optimum_value - float(t_all.max()),
        rule_c=optimum_value - float(truth(x_star)),
        n_design=n, residual_df=n - p)


def one(job: tuple[float, int]) -> dict:
    """One noise level x one seed: both classical protocols and both acquisitions."""
    sigma, seed = job
    t0 = time.time()
    oracle = _oracle()
    opt = float(oracle.optimum_value)
    b = _bounds()
    out: dict = {}

    for tag, kind in (("qlogei", "qlogei"), ("qlognei", "qlognei")):
        ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
        cfg = AcqConfig(kind=kind)  # type: ignore[arg-type]
        c = Campaign(ev, b, CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=seed, acq=cfg))
        c.run()
        t = ev.truth(c.train_X).double()
        out[tag] = dict(rule_a=opt - float(reported_best_curve(t, c.train_Y)[-1]),
                        oracle_best=opt - float(t.max()))

    # --- classical, screened: the published pipeline -----------------------------
    ev = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(ev, b, truth=ev.truth, budget=BUDGET, seed=seed)
    t = ev.truth(r.X_visited).double()
    out["doe_screened"] = dict(
        rule_a=opt - float(reported_best_curve(t, r.Y_visited)[-1]),
        oracle_best=opt - float(t.max()),
        rule_c=opt - float(ev.truth(r.confirmation_x.unsqueeze(0))),
        kept_factors=list(r.kept_factors))

    # --- classical, unscreened: all six coordinates ------------------------------
    ev2 = TorchEvaluator(oracle, sigma_rel=sigma, seed=seed)
    out["doe_unscreened"] = run_unscreened_ccd(
        ev2, b, truth=ev2.truth, optimum_value=opt, seed=seed)

    return dict(sigma=sigma, seed=seed, secs=round(time.time() - t0, 1), arms=out)


def gate(rows: list[dict]) -> dict:
    """The screened arm must reproduce the committed D20-corrected Hartmann6 column.

    Without this, the unscreened arm beside it could be measuring a different landscape,
    a different noise stream, or a different budget, and nothing would say so.
    """
    want = {}
    for r in json.loads(D20.read_text())["rows"]:
        if r["family"] == "hartmann6" and r["dim"] == DIM:
            want[(r["sigma"], int(r["seed"]))] = float(r["doe_a_new"])
    worst, n = 0.0, 0
    for row in rows:
        k = (row["sigma"], row["seed"])
        if k not in want:
            continue
        d = abs(row["arms"]["doe_screened"]["rule_a"] - want[k])
        worst, n = max(worst, d), n + 1
        if d > GATE_TOL:
            raise AssertionError(
                f"screened arm does not reproduce D20's Hartmann6 rule A at sigma="
                f"{k[0]} seed={k[1]}: {row['arms']['doe_screened']['rule_a']:.15f} vs "
                f"{want[k]:.15f} (|delta|={d:.3e}). The unscreened arm beside it would "
                "describe a different experiment.")
    return dict(n=n, worst_abs_delta=worst, tol=GATE_TOL, source=D20.name)


def analyse(rows: list[dict]) -> list[dict]:
    from scipy import stats
    out = []
    for sigma in SIGMAS:
        sub = [r for r in rows if abs(r["sigma"] - sigma) < 1e-12]
        if not sub:
            continue

        def col(arm, key):
            return np.array([r["arms"][arm][key] for r in sub])

        def contrast(d):
            m, lo, hi = instance_bootstrap(d, n_boot=N_BOOT)
            w = stats.wilcoxon(d) if np.any(d != 0) else None
            return dict(mean=float(m), lo=float(lo), hi=float(hi),
                        wilcoxon_p=float(w.pvalue) if w is not None else 1.0)

        cell = dict(sigma=sigma, n=len(sub),
                    means={a: {k: float(col(a, k).mean())
                               for k in ("rule_a", "oracle_best")}
                           for a in ("qlogei", "qlognei", "doe_screened",
                                     "doe_unscreened")},
                    residual_df=int(sub[0]["arms"]["doe_unscreened"]["residual_df"]))
        cell["means"]["doe_screened"]["rule_c"] = float(col("doe_screened", "rule_c").mean())
        cell["means"]["doe_unscreened"]["rule_c"] = float(col("doe_unscreened", "rule_c").mean())
        # the question: does removing the screen close BO's lead?
        for bo in ("qlogei", "qlognei"):
            cell[f"screened_vs_{bo}"] = contrast(col("doe_screened", "rule_a") - col(bo, "rule_a"))
            cell[f"unscreened_vs_{bo}"] = contrast(col("doe_unscreened", "rule_a") - col(bo, "rule_a"))
        cell["screen_effect"] = contrast(
            col("doe_unscreened", "rule_a") - col("doe_screened", "rule_a"))
        out.append(cell)
    return out


def report(summary: list[dict], g: dict) -> None:
    print(f"\n  GATE PASSED — screened arm reproduces {g['source']} on {g['n']} rows, "
          f"worst |delta| = {g['worst_abs_delta']:.3e}")

    print(f"\n{RULE}\n  HARTMANN6 AT d=6, WITH AND WITHOUT THE 6→4 SCREEN "
          f"(measured-value argmax)\n{RULE}")
    print(f"    {'sigma':>7}{'qLogEI':>10}{'qLogNEI':>10}{'DoE screened':>15}"
          f"{'DoE unscreened':>17}{'screen costs':>15}")
    for s in summary:
        m = s["means"]
        se = s["screen_effect"]
        print(f"    {s['sigma']:>7.2f}{m['qlogei']['rule_a']:>10.4f}"
              f"{m['qlognei']['rule_a']:>10.4f}{m['doe_screened']['rule_a']:>15.4f}"
              f"{m['doe_unscreened']['rule_a']:>17.4f}{se['mean']:>+15.4f}")
    print("\n    'screen costs' = unscreened − screened. Negative means removing the "
          "screen HELPED.")

    print(f"\n{RULE}\n  DOES REMOVING THE SCREEN CLOSE BO'S LEAD?\n{RULE}")
    for s in summary:
        print(f"\n    sigma = {s['sigma']}   (unscreened CCD: "
              f"{s['residual_df']} residual df)")
        for bo in ("qlogei", "qlognei"):
            a, b = s[f"screened_vs_{bo}"], s[f"unscreened_vs_{bo}"]
            shrink = (b["mean"] / a["mean"]) if a["mean"] else float("nan")
            print(f"      vs {bo:>8}:  screened {a['mean']:+.4f} "
                  f"[{a['lo']:+.4f},{a['hi']:+.4f}] p={a['wilcoxon_p']:.4f}"
                  f"   →  unscreened {b['mean']:+.4f} "
                  f"[{b['lo']:+.4f},{b['hi']:+.4f}] p={b['wilcoxon_p']:.4f}"
                  f"   ({shrink:.2f}x)")

    print(f"\n{RULE}\n  AND THE EXTRAPOLATION FAILURE MODE\n{RULE}")
    print(f"    {'sigma':>7}{'screened rule C':>18}{'unscreened rule C':>20}"
          f"{'difference':>13}")
    for s in summary:
        a = s["means"]["doe_screened"]["rule_c"]
        b = s["means"]["doe_unscreened"]["rule_c"]
        print(f"    {s['sigma']:>7.2f}{a:>18.4f}{b:>20.4f}{b - a:>+13.4f}")
    print("\n    The unscreened CCD spans the whole box, so its recommendation cannot")
    print("    fall outside the region it was fitted on. If rule C improves here, the")
    print("    giant unconstrained gap is about the screen's sub-box, not about")
    print("    quadratics being unable to recommend.")


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(git_sha=_git("rev-parse", "HEAD"),
                git_dirty=bool(_git("status", "--porcelain")),
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=list(argv),
                python=platform.python_version(), torch=torch.__version__,
                botorch=botorch.__version__, gpytorch=gpytorch.__version__,
                numpy=np.__version__, scipy=scipy.__version__,
                config=dict(dim=DIM, budget=BUDGET, q=Q, sigmas=list(SIGMAS),
                            n_seeds=N_SEEDS, ccd_n_derived=CCD_N_DERIVED,
                            ccd_n_centre=CCD_N_CENTRE, gate_tol=GATE_TOL,
                            n_boot=N_BOOT, family="hartmann6",
                            d8_unscreened="impossible within 48 wells; see docstring"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_seeds", nargs="?", type=int, default=N_SEEDS)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    print(f"{RULE}\nQ59 — Hartmann6 with and without the 6→4 screen\n{RULE}")
    print(f"  d={DIM}, sigma in {SIGMAS}, {args.n_seeds} seeds, budget {BUDGET}")
    print(f"  unscreened design: face-centred CCD, n_derived={CCD_N_DERIVED}, "
          f"{CCD_N_CENTRE} centre points")
    print(f"  d=8 is not run: no CCD lands on {BUDGET} wells and the only one that fits "
          "cannot support 45 terms\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["sigma"], r["seed"]) for r in done}
    todo = [(s, k) for s in SIGMAS for k in range(args.n_seeds) if (s, k) not in have]
    if have:
        print(f"  resuming — {len(have)} on disk")
    print(f"  {len(todo)} to run on {args.workers} workers\n")

    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(
                    dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 5 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min, "
                          f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    g = gate(done)
    summary = analyse(done)
    report(summary, g)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), gate=g,
                                   summary=summary, rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.0f} min)")


if __name__ == "__main__":
    main()
