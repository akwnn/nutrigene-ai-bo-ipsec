"""P8 · **SPADE's CERTIFICATE OFF HILL.** The gap §25 named and nothing closed.

Registered in `docs/OPEN-QUESTIONS.md` at `b281d4b`, **before this file existed**.

WHAT WAS MISSING
----------------
SPADE's *arms* appear in seventeen committed files. SPADE's **certificate** — the
conservative set, ``alpha_star``, containment — appears on **`hill` only**.
``p6-families.json`` carries sixty columns across four families and **not one is a
certificate column**: they are all ``auc*``, ``auprc*``, ``brier*``, ``iou*``, ``box_vol*``.
So every cross-family result in this project tests the **map**, and SPADE's actual claim has
been measured at exactly one family.

WHY THIS EDITS NOTHING
----------------------
``run_p2_versionb_gamma.score_campaign`` is **family-agnostic**: it takes ``orc``, ``grid``
and ``truth`` as arguments, and only ``build_campaign`` is hill-specific. So P2 is imported
**read-only** and fed campaigns from ``run_p6_families.versionb_builder`` — the construction
`p6` already used for these arms. ``p2-versionb-gamma.json`` is committed against P2's
current behaviour and nothing here touches it (D15).

🔴 WHY THE DRAW COUNT IS 4,096 AND WHY HILL IS RE-RUN
-----------------------------------------------------
``run_p2_versionb_gamma.N_DRAWS`` is **512**, and F3 registered that 512 draws **cannot**
estimate ``CE_alpha`` containment at γ ≥ 0.95 — §14's kill was an artefact of it (§29). So
**every committed hill certificate number carries that artefact.**

Running the families at 4,096 and comparing them to committed hill at 512 would confound
*family* with *draw count*, which is the exact confound Part IV spent itself isolating.
**Hill is therefore re-run here at 4,096**, and all five families sit on one draw count.
``p2-versionb-gamma.json`` is left alone as the 512-draw record.

THE GATE IS CAMPAIGN-LEVEL, DELIBERATELY
-----------------------------------------
Hill's ``regret`` and ``n_wells`` must reproduce P2 at ``|delta| = 0`` — the campaigns are
seed-identical and drift means the builder is not P2's. The **certificate columns are not
gated**, because they are *expected* to move: the draw count changed, and that is the point.
Gating them would report the correction as a defect.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path

import torch
from scipy.stats import binom

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "software" / "src"))

from boec.norms import sobol_grid                                    # noqa: E402
from boec.replay import family_evaluator, instance_by_id, regenerate, scored_curve    # noqa: E402

OUT = ROOT / "research" / "results" / "p8-certificate-families.json"
P2_COMMITTED = ROOT / "research" / "results" / "p2-versionb-gamma.json"

#: `hill` is FIRST and is not optional -- it is the comparability anchor and the gate.
FAMILIES = ("hill", "hartmann6", "levy", "rosenbrock", "ackley")
ARMS = ("versionb", "versionb_random", "versionb_predictive", "plate1_only")

DIM, SIGMA, N_SEEDS = 6, 0.25, 50

#: 🔴 NOT P2's 512. F3 registered 512 as insufficient at gamma >= 0.95 (FINDINGS §29).
N_DRAWS = 4096

#: Campaign-level only. Never a certificate column -- see the module docstring.
GATE_COLUMNS = ("regret", "n_wells")

_P2 = _P6 = None


def _mod(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "software" / "scripts" / filename)
    m = importlib.util.module_from_spec(spec)
    sys.modules[alias] = m
    spec.loader.exec_module(m)
    return m


def p2():
    global _P2
    if _P2 is None:
        _P2 = _mod("_p8_p2", "run_p2_versionb_gamma.py")
    return _P2


def p6():
    global _P6
    if _P6 is None:
        _P6 = _mod("_p8_p6", "run_p6_families.py")
    return _P6


def exact_tail(x: int, n: int, p: float) -> float:
    """Lower binomial tail. **Exact, never a normal approximation** (Erratum 21)."""
    return float(binom.cdf(x, n, p))


def committed_hill_index() -> dict:
    """`(instance, seed, arm) -> row` from P2, for the campaign-level gate."""
    if not P2_COMMITTED.exists():
        return {}
    return {(r.get("instance"), r.get("seed"), r.get("arm")): r
            for r in json.loads(P2_COMMITTED.read_text())["rows"]}


def keys_for(family: str, n_seeds: int) -> list[tuple[str, int]]:
    """`(instance, seed)` pairs. **hill is keyed differently and that is not a detail.**

    `hill` is an ENSEMBLE: P2 measured 25 instances x 2 seeds = 50 campaigns, and its
    instance ids are hashes. The synthetic families have no ensemble -- one landscape each --
    so the family name IS the instance and the 50 campaigns come from 50 seeds.

    Using `range(50)` for hill would ask `instance_by_id` for an instance called `"hill"`,
    which is what the first version did and what the smoke run caught.
    """
    if family == "hill":
        ks = sorted({(r["instance"], r["seed"]) for r in
                     json.loads(P2_COMMITTED.read_text())["rows"]})
        return ks[:n_seeds * 2] if n_seeds < N_SEEDS else ks
    return [(family, s) for s in range(n_seeds)]


def instance_optimum(instance: str) -> float:
    """`hill`'s declared optimum. `UnitScaled` puts every other family's at exactly 1.0."""
    return float(instance_by_id(instance, DIM).optimum_value)


def evaluator_for(family: str, instance: str, seed: int):
    """`hill` goes through the ensemble; every other family through `UnitScaled`."""
    if family == "hill":
        from boec.torch_oracle import BiphasicOracle
        return BiphasicOracle(instance_by_id(instance, DIM), sigma_rel=SIGMA, seed=seed)
    return family_evaluator(family, DIM, SIGMA, seed)


def build(family: str, instance: str, arm: str, seed: int):
    """One 48-well campaign. `plate1_only` is `lhs` and needs no builder (D23.1)."""
    fam_kw = {} if family == "hill" else {"family": family}
    if arm == "plate1_only":
        rec = regenerate(instance, DIM, SIGMA, seed, "lhs", **fam_kw)
        return rec, int(rec.X.shape[0])
    rec = regenerate(instance, DIM, SIGMA, seed, arm,
                     builder=p6().versionb_builder(arm), **fam_kw)
    return rec, int(rec.X.shape[0])


def score(family: str, instance: str, arm: str, seed: int, grid, X_sub) -> list[dict]:
    """Every `(gamma, tau_frac)` row for one campaign, through **P2's own scorer**."""
    ev = evaluator_for(family, instance, seed)
    rec, n_wells = build(family, instance, arm, seed)
    with torch.no_grad():
        truth = ev.truth(grid).reshape(-1).double()
        truth_sub = ev.truth(X_sub).reshape(-1).double()
    # 🔴 P2's `regret` is the TERMINAL RULE's regret against the instance's declared
    # optimum -- NOT oracle-best over the grid. The first version used
    # `mu_max - truth(X).max()`, which is the oracle-best ceiling, and the hill gate failed
    # on all 16 campaigns with `versionb` and `versionb_random` returning IDENTICAL values
    # (two different designs share an oracle-best ceiling; they do not share a rule-A pick).
    # The gate existed precisely to catch a scorer that measures a different quantity.
    # `plate1_only` takes `rec.regret` -- the value `regenerate` itself computed -- because
    # that is what P2's `build_campaign` does for its GATED_ARM. Recomputing it as
    # `mu_max - scored_curve(...)` is the same arithmetic in a different ORDER and lands
    # 1-2 ULP away: the smoke run failed the hill gate on exactly three plate1_only
    # campaigns at 3.3e-16, 4.4e-16 and 1.1e-16. **Matched, not tolerated** -- the gate
    # stays at |delta| = 0.
    if arm == "plate1_only":
        regret = float(rec.regret)
    else:
        mu_max = float(instance_optimum(instance)) if family == "hill" else 1.0
        regret = float(mu_max - scored_curve(ev, rec.X, rec.Y)[-1])
    rows = p2().score_campaign(
        X=rec.X, Y=rec.Y, Yvar=rec.Yvar, orc=ev, dim=DIM, grid=grid, truth=truth,
        X_sub=X_sub, truth_sub=truth_sub, seed=seed, instance=instance, arm=arm,
        regret=regret, n_draws=N_DRAWS)
    for r in rows:
        r.update({"family": family, "sigma": SIGMA, "dim": DIM,
                  "n_wells": n_wells, "n_draws": N_DRAWS})
    return rows


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    import botorch, gpytorch, numpy, scipy                           # noqa: E401
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__,
            "botorch": botorch.__version__, "gpytorch": gpytorch.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    ap.add_argument("--families", type=str, default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    final = Path(args.out) if args.out else OUT
    if args.smoke and args.out is None:
        raise SystemExit("--smoke requires --out; it must never write the registered file")
    fams = tuple(args.families.split(",")) if args.families else FAMILIES
    seeds = range(2 if args.smoke else args.seeds)
    n_draws_eff = 512 if args.smoke else N_DRAWS
    grid_n = 2048 if args.smoke else p2().GRID_N
    sub_n = 512 if args.smoke else p2().SUBSET_N

    grid = sobol_grid(DIM, grid_n, seed=p2().GRID_SEED)
    X_sub = sobol_grid(DIM, sub_n, seed=p2().GRID_SEED)
    hill_ref = committed_hill_index()

    n_seeds = len(seeds)
    keys = {f: keys_for(f, n_seeds) for f in fams}
    total = sum(len(keys[f]) for f in fams) * len(ARMS)
    print(f"P8 · SPADE's certificate off hill · d={DIM} sigma={SIGMA}")
    print(f"families {fams} · arms {ARMS} · n_draws={n_draws_eff}")
    print(f"campaigns per family: { {f: len(keys[f]) for f in fams} }")
    print(f"gate: hill {GATE_COLUMNS} against p2-versionb-gamma at |delta| = 0")
    print(f"{total} campaigns\n")

    globals()["N_DRAWS"] = n_draws_eff
    rows, gate_fail, n = [], [], 0
    partial = final.with_suffix(final.suffix + ".partial")
    t0 = time.time()
    for family in fams:
        for instance, seed in keys[family]:
            for arm in ARMS:
                got = score(family, instance, arm, seed, grid, X_sub)
                # CAMPAIGN-LEVEL GATE, hill only. Certificate columns deliberately excluded.
                if family == "hill" and hill_ref:
                    ref = hill_ref.get((instance, seed, arm))
                    if ref is not None:
                        for col in GATE_COLUMNS:
                            if col in ref and col in got[0]:
                                d = abs(float(got[0][col]) - float(ref[col]))
                                if d > 0.0:
                                    gate_fail.append({"family": family, "seed": seed,
                                                      "arm": arm, "column": col,
                                                      "committed": ref[col],
                                                      "regenerated": got[0][col],
                                                      "abs_delta": d})
                rows.extend(got)
                n += 1
            el = time.time() - t0
            print(f"[{n:4d}/{total}] {family:<11} {instance[:8]} seed={seed:<3d} "
                  f"rows={len(rows):>6} gate_fail={len(gate_fail)} "
                  f"({el/60:.1f}m, eta {(total-n)*el/max(n,1)/60:.0f}m)", flush=True)
            partial.write_text(json.dumps(
                {"status": "partial", "keys_present": n, "keys_expected": total,
                 "provenance": _provenance(sys.argv),
                 "config": {"families": list(fams), "arms": list(ARMS), "dim": DIM,
                            "sigma": SIGMA, "n_seeds": len(seeds), "n_draws": n_draws_eff,
                            "grid_n": grid_n, "subset_n": sub_n,
                            "gate_columns": list(GATE_COLUMNS),
                            "gate_note": ("campaign-level only; certificate columns are "
                                          "NOT gated against P2 because the draw count "
                                          "changed from 512 and they are expected to move"),
                            "p2_is_the_512_draw_record": True},
                 "gate_failures": gate_fail, "rows": rows}, indent=1))
    payload = json.loads(partial.read_text())
    payload["status"] = "COMPLETE"
    final.write_text(json.dumps(payload, indent=1))
    partial.unlink(missing_ok=True)
    print(f"\ngate failures: {len(gate_fail)}")
    print(f"wrote {final.name} · {len(rows)} rows")


if __name__ == "__main__":
    main()
