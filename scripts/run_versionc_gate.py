"""Version C section 0 -- rule P at sigma_rel = 0.10. THE GATE. Analysis only.

    .venv/bin/python scripts/run_versionc_gate.py --limit 2    # smoke
    .venv/bin/python scripts/run_versionc_gate.py              # all 50 keys, 12 arms
    .venv/bin/python scripts/run_versionc_gate.py --gate-only  # regenerate and gate, stop

Registered in `docs/OPEN-QUESTIONS.md` **before this file existed**.

------------------------------------------------------------------------------
WHAT IS BEING DECIDED, AND WHY IT IS A GATE RATHER THAN A MEASUREMENT
------------------------------------------------------------------------------

Version B ranks 1st-3rd of 12 on the design-space map at (d=6, sigma_rel=0.10) and
**10th-11th of 12 on regret at the same cell**, losing to qLogNEI by 0.045 -- more than
twice the SESOI. Version C's section 2 proposes to spend plate 2's wells on a trust region
to close that. **Section 2 must not be built until this runner returns**, because there
are two different worlds consistent with the same 10th place:

* If the deficit is **identification** -- rule A nominates the best *noisy* reading, and a
  spread design has more mediocre wells that can draw lucky noise -- then a posterior-mean
  terminal rule closes it for free and a trust region is a solution to a problem that does
  not exist.
* If the deficit is **search** -- SPADE genuinely does not look where the optimum is --
  then no terminal rule can repair it and section 2 is required.

THE PRE-REGISTERED PREDICTION, WRITTEN BEFORE LOOKING
-----------------------------------------------------
Under a posterior-mean terminal rule, regret is governed by how well the posterior
localises the argmax. For a peak of local curvature `c`, a posterior mean error of size
`s` displaces the argmax by `r ~ sqrt(s/c)`, giving regret `~ c*r^2 ~ s`, and
`s ~ sigma / sqrt(n_eff)`:

    regret_P  ~  sigma / sqrt(n_eff)

At sigma = 0.10 with the measured `n_eff ~ 1.4` this gives **regret_P ~ 0.085**. Reference
points at that cell, under rule A: qLogNEI 0.0808, qLogEI 0.0874, `doe` 0.0892.

THE BRANCH  (:func:`gate_branch`, so it is applied and not recalled)
--------------------------------------------------------------------
    regret_P <= 0.090   IDENTIFICATION_ARTEFACT   section 2 is NOT built
    regret_P >= 0.110   SEARCH_DEFICIT            trust region required
    between             INCONCLUSIVE              section 2 is built as an ARM

**And validate the model, not just the number.** `n_eff` is emitted per campaign so that
`regret_P` can be regressed on `sigma/sqrt(n_eff)` across all arms and both sigma. If R^2
is high and the slope is near 1, the model behind section 2.2's allocation rule is
validated. If not, section 2.2's well-count formula has no basis and must be replaced by
empirical calibration -- which is a finding about section 2.2 whichever way the branch
above falls.

------------------------------------------------------------------------------
NO NEW CAMPAIGNS, AND A DOUBLE GATE WHERE TWO SOURCES EXIST
------------------------------------------------------------------------------

Every arm is a regeneration, gated at **|delta| = 0 exactly** before any rule-P number is
read. Two committed sources are used and they must agree:

* **`p3-k6-d6-s010.json`** carries `regret` for all twelve arms at exactly this cell. It is
  the primary gate. Its own `gate_policy` recorded the three Version B arms as "ungatable
  in principle -- no committed comparator exists and none ever will"; that was true when
  **no file existed yet**, and this file is now that file. Determinism is what is being
  checked, which is precisely the guarantee that registration says those arms have.
* **`e2-grid.json`** carries seven of them independently. Where both exist, both are
  checked. p3's column was itself gated against e2-grid, so agreement is expected -- which
  is exactly why a disagreement would be worth stopping for rather than absorbing.

WHY NOT `run_fix1_terminal_rule.py`
-----------------------------------
Fix 1 is the same estimand at sigma = 0.25 and would be the obvious thing to parameterise.
It cannot be: it calls `run_versionb._two_plate(orc, DIM, seed, mu_max, True)` and unpacks
three values. That function now takes `mode: str` and returns four, so **fix 1 raises at
HEAD** and can no longer reproduce its own committed file. Its Version B path is not
copied here. This runner builds every arm through `boec.replay.regenerate`, using the
builder hook for the Version B arms exactly as `run_p3_cells.py` does -- so the oracle
construction, the scoring rule and the provenance all stay inside `replay`, which is the
property that makes a gate mean anything.

ONE LOCATOR, ONE SETTING, EVERY ARM
------------------------------------
Q29 shipped a locator asymmetry -- its BO arm screened at `10 / 256` unseeded while its
DoE arm used `20 / 4096` seeded, a 16x gap that flatters whichever arm got the bigger
screen. Every arm here goes through one `grid_screened_argmax` at one setting: the
registered 20,000-point Sobol grid at seed 0, then `constrained_argmax` at
`n_restarts=20, raw_samples=4096`. Those two constants are the ones `boec.spread_gp`
records as load-bearing, so these numbers are commensurable with every rule-C figure
already on disk.

PARTIAL FILES
-------------
Never write incrementally to a registered `results/` path: the `.gitignore` negation makes
a partial stageable and it reads as finished. This writes `<name>.json.partial`, carries
`status` / `keys_present` / `keys_expected`, and :func:`promote` re-reads what it
publishes.
"""

from __future__ import annotations

import argparse
import dataclasses
import gc
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.designspace import gp_adapter                              # noqa: E402
from boec.metrics import grid_screened_argmax                        # noqa: E402
from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import instance_by_id, regenerate, unit_bounds      # noqa: E402
from boec.surrogate import build_gp                                  # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402
from boec.versionc import ard_lengthscales, n_effective              # noqa: E402

DIM, SIGMA, BUDGET = 6, 0.10, 48
GRID_N, GRID_SEED = 20_000, 0
#: `boec.spread_gp`'s constants. Load-bearing: changing either makes this incomparable
#: with every rule-C number already committed.
N_RESTARTS, RAW_SAMPLES = 20, 4096
LOCATOR_SEED = GRID_SEED

#: The twelve arms `p3-k6-d6-s010.json` scored, in its order.
ARMS = ("doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly", "lhs", "sobol",
        "random", "plate1_only", "versionb", "versionb_random", "versionb_predictive")

ROUNDS = {"doe": 3, "lhs": 1, "sobol": 1, "random": 1, "plate1_only": 1,
          "qlogei": 10, "qlognei": 10, "qlogei-add": 10, "qlogei-addonly": 10,
          "versionb": 2, "versionb_random": 2, "versionb_predictive": 2}

#: `run_versionb._two_plate`'s modes, imported read-only -- never re-expressed here.
VERSIONB_MODE = {"versionb": "lse", "versionb_random": "random",
                 "versionb_predictive": "predictive"}

#: Arms `e2-grid.json` carries independently at this cell. `plate1_only` IS `lhs` -- the
#: same 48 wells, committed columns agreeing to a worst |delta| of 4.44e-16 -- so it is
#: cross-gated through that alias and must never be counted as an independent arm.
CROSS_GATED_ARMS = ("doe", "qlogei", "qlognei", "lhs", "sobol", "random", "plate1_only")
CROSS_GATE_ALIAS = {"plate1_only": "lhs"}

#: Carried into every row of these arms. The gate below is a REPRODUCTION check against
#: p3's committed column; it is not a resolution of P1, and a reader who takes it for one
#: would be reading a determinism check as a provenance answer.
PROVENANCE_CAVEAT = {
    "qlogei-add": ("P1 UNRESOLVED: gated here against p3-k6-d6-s010.json only. "
                   "q30-additive.json now exists but the 2,800-row re-score that decides "
                   "VALIDATED vs WITHDRAWN has not run."),
    "qlogei-addonly": ("P1 UNRESOLVED: gated here against p3-k6-d6-s010.json only. "
                       "q30-additive.json now exists but the 2,800-row re-score that "
                       "decides VALIDATED vs WITHDRAWN has not run."),
}

P3 = ROOT / "results" / "p3-k6-d6-s010.json"
E2_GRID = ROOT / "results" / "e2-grid.json"
OUT = ROOT / "results" / "versionc-gate-s010.json"

#: Exact. K1 measured every gated arm at worst |delta| = 0.0 over 500 rows, so exact is
#: the measured bar rather than an aspiration. A single failure aborts.
GATE_TOL = 0.0

#: The pre-registered branch. Both bounds inclusive on the decisive side.
BRANCH_ARTEFACT, BRANCH_DEFICIT = 0.090, 0.110

_VB = importlib.util.module_from_spec(
    importlib.util.spec_from_file_location("_run_versionb",
                                           ROOT / "scripts" / "run_versionb.py"))
_VB.__spec__.loader.exec_module(_VB)


class MissingGateTarget(RuntimeError):
    """An arm's committed file exists but contributes no rows at this cell.

    Raised rather than skipped. That is the section 3.6 defect: `.get()` hands back
    `None`, `None` compares equal to nothing, and the run reports a gate it never applied.
    """


def _rows(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


@lru_cache(maxsize=4)
def gate_index(sigma: float, arms: tuple[str, ...] = ARMS
               ) -> dict[tuple[str, int, str], float]:
    """``(instance, seed, arm) -> committed rule-A regret`` from `p3-k6-d6-s010.json`.

    p3 carries 24 (gamma, tau_frac) rows per campaign and `regret` is constant across
    them -- measured, not assumed: all 600 keys carry exactly one distinct value.
    """
    out: dict[tuple[str, int, str], float] = {}
    for r in _rows(P3):
        if r["dim"] != DIM or abs(r["sigma"] - sigma) > 1e-12 or r["arm"] not in arms:
            continue
        key = (r["instance"], int(r["seed"]), r["arm"])
        val = float(r["regret"])
        if key in out and out[key] != val:
            raise MissingGateTarget(
                f"{key} carries two different committed regrets, {out[key]} and {val}")
        out[key] = val
    missing = [a for a in arms if not any(k[2] == a for k in out)]
    if missing:
        raise MissingGateTarget(
            f"{P3.name} exists but contributes no rows at (d={DIM}, sigma={sigma}) for "
            f"{missing} -- refusing to run ungated")
    return out


@lru_cache(maxsize=4)
def cross_gate_index(sigma: float) -> dict[tuple[str, int, str], float]:
    """``(instance, seed, arm) -> committed regret`` from the independent `e2-grid.json`.

    Seven arms only. `plate1_only` is read through its `lhs` alias, because it is not a
    separate campaign and gating it against a column of its own would be gating it
    against itself.
    """
    by_arm: dict[tuple[str, int, str], float] = {}
    for r in _rows(E2_GRID):
        if r["dim"] != DIM or abs(r["sigma"] - sigma) > 1e-12:
            continue
        by_arm[(r["instance"], int(r["seed"]), r["arm"])] = float(r["regret"])

    out: dict[tuple[str, int, str], float] = {}
    for arm in CROSS_GATED_ARMS:
        source = CROSS_GATE_ALIAS.get(arm, arm)
        hits = {(i, s, arm): v for (i, s, a), v in by_arm.items() if a == source}
        if not hits:
            raise MissingGateTarget(
                f"{E2_GRID.name} carries no `{source}` rows at (d={DIM}, sigma={sigma})")
        out.update(hits)
    return out


def gate_branch(regret_p: float) -> str:
    """The registered branch, as a function so it is applied identically every time.

    Written as a function for the same reason `boec.spread_gp.within_design_noise` is one:
    a rule recalled at reading time is a rule applied selectively.
    """
    if regret_p <= BRANCH_ARTEFACT:
        return "IDENTIFICATION_ARTEFACT"
    if regret_p >= BRANCH_DEFICIT:
        return "SEARCH_DEFICIT"
    return "INCONCLUSIVE"


def regenerate_arm(instance: str, dim: int, sigma: float, seed: int, arm: str):
    """One campaign for any of the twelve arms, always through `replay.regenerate`.

    `run_p3_cells.regenerate_arm`'s construction exactly. The Version B arms go through
    `regenerate`'s builder hook so this module never learns to fit GPs: the builder
    supplies `(X, Y, Yvar)` and `replay` keeps the oracle construction, the scoring rule
    and the provenance -- the property that makes a gate mean anything.

    `plate1_only` IS `lhs` and is regenerated as `lhs`, then relabelled, so it is built by
    the arithmetic its committed column was built by, including `run_e2.static_curve`'s
    20-ordering mean. Building it as a fresh 48-well LHS instead misses that column by
    ~1e-16 and fires the gate on an arithmetic artefact of this script.
    """
    if arm == "plate1_only":
        return dataclasses.replace(regenerate(instance, dim, sigma, seed, "lhs"),
                                   arm="plate1_only")
    if arm in VERSIONB_MODE:
        mu_max = float(instance_by_id(instance, dim).optimum_value)
        mode = VERSIONB_MODE[arm]

        def _builder(orc, d, sd):
            X, Y, V, _diag = _VB._two_plate(orc, d, sd, mu_max, mode)
            return X, Y, V, None, None

        return regenerate(instance, dim, sigma, seed, arm, builder=_builder)
    return regenerate(instance, dim, sigma, seed, arm)


def score_one(inst_id: str, seed: int, arms=ARMS, sigma: float = SIGMA) -> list[dict]:
    """Every arm for one ``(instance, seed)``. The grid and the truth are built once."""
    inst = instance_by_id(inst_id, DIM)
    mu_max = float(inst.optimum_value)
    bounds = unit_bounds(DIM)
    grid = sobol_grid(DIM, GRID_N, seed=GRID_SEED)
    #: A separate oracle for scoring, so `truth` is never read off an oracle whose noise
    #: stream a regeneration is still consuming.
    orc_t = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    primary, cross = gate_index(sigma), cross_gate_index(sigma)

    rows = []
    for arm in arms:
        t0 = time.time()
        rec = regenerate_arm(inst_id, DIM, sigma, seed, arm)

        # --- rule A: the gate, not a new number ---------------------------------------
        ref = primary[(inst_id, seed, arm)]
        delta = abs(float(rec.regret) - ref)
        cross_ref = cross.get((inst_id, seed, arm))
        cross_delta = None if cross_ref is None else abs(float(rec.regret) - cross_ref)

        # --- rule P: one model, one locator, every arm --------------------------------
        model = build_gp(rec.X, rec.Y, rec.Yvar, bounds)

        def predict(Z: torch.Tensor, _m=model) -> torch.Tensor:
            with torch.no_grad():
                return _m.posterior(Z).mean

        # CHUNKED. 20k points through `model.posterior` in one call is 100.6s and a
        # 3.2 GB joint covariance whose off-diagonal is never used.
        grid_mean, _ = gp_adapter(model).posterior_mean_and_sd(grid)
        r = grid_screened_argmax(predict, grid, grid_mean, bounds,
                                 n_restarts=N_RESTARTS, raw_samples=RAW_SAMPLES,
                                 seed=LOCATOR_SEED)
        with torch.no_grad():
            regret_p = float(mu_max - orc_t.truth(r.x.reshape(1, -1)))
            regret_p_grid = float(mu_max - orc_t.truth(r.x_grid.reshape(1, -1)))

        # --- the section 0 regression's independent variable --------------------------
        ls = ard_lengthscales(model)
        n_eff = n_effective(rec.X, r.x.reshape(-1), ls)

        rows.append({
            "instance": inst_id, "seed": seed, "arm": arm, "dim": DIM, "sigma": sigma,
            "rounds": ROUNDS[arm], "n_wells": int(rec.X.shape[0]),
            "optimum_value": mu_max,
            "regret_a": float(rec.regret),
            "regret_a_committed": ref, "gate_source": P3.name, "gate_abs_delta": delta,
            "regret_a_cross": cross_ref, "cross_gate_source": (
                E2_GRID.name if cross_ref is not None else None),
            "cross_gate_abs_delta": cross_delta,
            "cross_gate_alias": CROSS_GATE_ALIAS.get(arm),
            "provenance_caveat": PROVENANCE_CAVEAT.get(arm),
            "regret_p": regret_p, "regret_p_grid": regret_p_grid,
            "improvement": float(rec.regret) - regret_p,
            "post_mean_at_x_p": r.value, "post_mean_at_x_grid": r.value_grid,
            "from_grid": bool(r.from_grid),
            "n_starts_converged": int(r.n_starts_converged),
            "x_p": [float(v) for v in r.x],
            "n_eff": n_eff,
            "lengthscales": [float(v) for v in ls],
            "sigma_over_sqrt_n_eff": sigma / (n_eff ** 0.5),
            "secs": round(time.time() - t0, 2),
        })
        del model, grid_mean
        gc.collect()
    return rows


# --- provenance and the partial-file discipline ---------------------------------------

def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import numpy
    import scipy
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__,
            "torch_num_threads": str(torch.get_num_threads()),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "unset")}


def _config(sigma: float) -> dict:
    return {"dim": DIM, "sigma": sigma, "budget": BUDGET, "arms": list(ARMS),
            "rounds": ROUNDS, "grid_n": GRID_N, "grid_seed": GRID_SEED,
            "n_restarts": N_RESTARTS, "raw_samples": RAW_SAMPLES,
            "locator_seed": LOCATOR_SEED, "gate_tol": GATE_TOL,
            "gate_primary": P3.name, "gate_cross": E2_GRID.name,
            "cross_gated_arms": list(CROSS_GATED_ARMS),
            "branch_artefact_at_or_below": BRANCH_ARTEFACT,
            "branch_deficit_at_or_above": BRANCH_DEFICIT,
            "rule_a": "optimum_value - truth(argmax observed Y)",
            "rule_p": ("optimum_value - truth(argmax posterior mean), located on the "
                       f"{GRID_N}-point Sobol grid at seed {GRID_SEED} and polished with "
                       f"constrained_argmax(n_restarts={N_RESTARTS}, "
                       f"raw_samples={RAW_SAMPLES}, seed={LOCATOR_SEED})"),
            "n_eff": "1 + |{x_i : ||x_i - x_hat||_ARD <= 1}|, boec.versionc.n_effective"}


def _partial_path(final: Path) -> Path:
    return final.with_suffix(final.suffix + ".partial")


def write_partial(final: Path, rows: list[dict], keys_present: int, keys_expected: int,
                  argv, sigma: float, gate_failures: list[dict] | None = None) -> Path:
    """Write to ``<name>.partial``. **Never** to the registered path.

    `.gitignore`'s negation makes anything at a registered `results/` path stageable, so a
    half-finished file there reads as a finished one. `status`, `keys_present` and
    `keys_expected` travel with the rows so an interrupted run is legible as interrupted.
    """
    complete = keys_present == keys_expected
    path = _partial_path(final)
    path.write_text(json.dumps({
        "status": "complete" if complete else "partial",
        "complete": complete,
        "keys_present": keys_present, "keys_expected": keys_expected,
        "provenance": _provenance(argv), "config": _config(sigma),
        "gate": {"tol": GATE_TOL, "rows_checked": len(rows),
                 "worst_abs_delta": max((r.get("gate_abs_delta", 0.0) for r in rows),
                                        default=0.0),
                 "worst_cross_abs_delta": max(
                     (r["cross_gate_abs_delta"] for r in rows
                      if r.get("cross_gate_abs_delta") is not None), default=0.0),
                 "failures": gate_failures or []},
        "rows": rows}, indent=1))
    return path


def promote(final: Path) -> dict:
    """Move a **complete** partial onto the registered path, then re-read what it wrote.

    Re-reads rather than trusting the write: a promote that does not re-read cannot tell
    you it published what it meant to.

    Raises:
        ValueError: if the partial is not complete. Promoting a partial is precisely the
            failure the `.partial` convention exists to prevent.
    """
    path = _partial_path(final)
    payload = json.loads(path.read_text())
    if not payload.get("complete"):
        raise ValueError(
            f"refusing to promote an incomplete partial: "
            f"{payload.get('keys_present')} of {payload.get('keys_expected')} keys")
    final.write_text(path.read_text())
    republished = json.loads(final.read_text())
    if republished != payload:
        raise ValueError("promoted file does not re-read as what was written")
    path.unlink()
    return republished


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="(instance, seed) pairs to run; default all 50")
    ap.add_argument("--arms", type=str, default=None, help="comma-separated subset")
    ap.add_argument("--gate-only", action="store_true",
                    help="regenerate and gate; write nothing")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else ARMS
    final = Path(args.out) if args.out else OUT
    primary = gate_index(SIGMA, arms)
    keys = sorted({(i, s) for (i, s, a) in primary if a == arms[0]})
    if args.limit:
        keys = keys[:args.limit]

    print(f"Version C section 0 · rule P at sigma={SIGMA} · "
          f"HEAD={_provenance(sys.argv)['git_sha'][:8]}")
    print(f"{len(arms)} arms x {len(keys)} keys · gate {P3.name} "
          f"+ cross {E2_GRID.name} at |delta| = {GATE_TOL}")

    rows: list[dict] = []
    failures: list[dict] = []
    for n, (inst_id, seed) in enumerate(keys, start=1):
        t0 = time.time()
        got = score_one(inst_id, seed, arms)
        for r in got:
            if r["gate_abs_delta"] > GATE_TOL:
                failures.append({k: r[k] for k in
                                 ("instance", "seed", "arm", "regret_a",
                                  "regret_a_committed", "gate_abs_delta")})
            if (r["cross_gate_abs_delta"] or 0.0) > GATE_TOL:
                failures.append({k: r[k] for k in
                                 ("instance", "seed", "arm", "regret_a",
                                  "regret_a_cross", "cross_gate_abs_delta")})
        if failures:
            print(f"\nGATE FAILED on {len(failures)} rows, first: {failures[0]}")
            raise SystemExit(1)
        rows.extend(got)
        print(f"[{n:3d}/{len(keys)}] {inst_id} seed={seed} "
              f"regret_p {min(r['regret_p'] for r in got):.4f}"
              f"..{max(r['regret_p'] for r in got):.4f} "
              f"n_eff {min(r['n_eff'] for r in got)}..{max(r['n_eff'] for r in got)} "
              f"({time.time()-t0:.1f}s)", flush=True)
        if not args.gate_only:
            write_partial(final, rows, n, len(keys), sys.argv, SIGMA, failures)

    if args.gate_only:
        print(f"\ngate clean over {len(rows)} rows; nothing written")
        return
    payload = promote(final)
    print(f"\npromoted {final.name} · {len(payload['rows'])} rows · gate clean")


if __name__ == "__main__":
    main()
