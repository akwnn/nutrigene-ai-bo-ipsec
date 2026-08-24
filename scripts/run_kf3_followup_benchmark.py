"""The KF-3 follow-up benchmark for `spade-kf3-followup-2026-08-24`.

    .venv/bin/python scripts/run_kf3_followup_benchmark.py --pilot
    .venv/bin/python scripts/run_kf3_followup_benchmark.py --condition C2 --arm spade_cf_erroraware --limit 100
    .venv/bin/python scripts/run_kf3_followup_benchmark.py --condition C3 --arm spade_cf_diverse_batch --limit 100

Registered in ``docs/SPADE-KF3-FOLLOWUP-SPEC.md``. Does not modify, overwrite, or import
anything into `scripts/run_final_spade_benchmark.py` on disk -- the frozen spec's own
namespace rule ("no file of spade-final-2026-08-23 is modified") forbids editing it, so this
script extends its behaviour **at runtime**, on the imported module object, rather than on
the file: it adds two new arm names to the module's ``ARMS`` dict and replaces the module's
``build`` name with a dispatcher that recognises them and calls through to the *original*
``build`` unchanged for every other arm name. `scripts/run_final_spade_benchmark.py`'s own
text is never touched, and every arm it already knows about behaves identically to before
this script imports it.

------------------------------------------------------------------------------
THE FIREWALLED PILOT (spec §3)
------------------------------------------------------------------------------

``--pilot`` runs `spade_cf_erroraware`'s full pipeline for 5 campaigns on C2 (Hill) only,
reusing the first 5 ``(instance, seed)`` keys already spent on `spade_random_plate2`'s
committed data. It writes **only** a wall-clock elapsed-seconds line per campaign to
``results/kf3-followup-pilot-timing.log``. Every other output -- rows, certificates,
symmetric-difference numbers -- goes to ``results/kf3-followup-pilot-DISCARD.json``, a
filename chosen to make the taboo visible in a directory listing. Nothing from that file is
printed, loaded, or inspected here or anywhere else; §3.2's decision rule reads only the
timing log.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from boec.kf3_followup import (  # noqa: E402
    EV_SCORING_N, select_diverse_batch, select_erroraware_batch)
from boec.norms import sobol_grid  # noqa: E402
from boec.replay import unit_bounds  # noqa: E402
from boec.runner import static_design  # noqa: E402
from boec.surrogate import build_gp  # noqa: E402

import run_final_spade_benchmark as rfsb  # noqa: E402

STUDY_ID = "spade-kf3-followup-2026-08-24"
REGISTRATION_COMMIT = "6c5e860"  # errata at 4326de1, 4a23175

NEW_ARMS = ("spade_cf_erroraware", "spade_cf_diverse_batch")

# --- extend the imported module's registry at runtime, never on disk -------------------
rfsb.ARMS["spade_cf_erroraware"] = {
    "fam": "SPADE-kf3-followup", "rounds": 2, "m": None, "wells": 48}
rfsb.ARMS["spade_cf_diverse_batch"] = {
    "fam": "SPADE-kf3-followup", "rounds": 2, "m": None, "wells": 48}

_original_build = rfsb.build


def kf3_followup_builder(mechanism: str, design_theta: float):
    """``builder(orc, dim, seed) -> (X, Y, Yvar, kept, held)`` -- mirrors
    `run_final_spade_benchmark.spade_builder`'s shape exactly: identical plate 1, identical
    GP, so the two new arms differ from `spade_cf_m0` in exactly the registered mechanism
    (spec §2.1/§2.2) and nothing else.
    """

    def builder(orc, dim: int, seed: int):
        bounds = unit_bounds(dim)
        X1 = static_design(bounds, "lhs", rfsb.N_PLATE1, seed)
        Y1, V1 = orc.evaluate(X1)
        model = build_gp(X1, Y1, V1, bounds)
        cand = sobol_grid(dim, rfsb.CAND_N, seed=seed)

        if mechanism == "erroraware":
            X_er = sobol_grid(dim, EV_SCORING_N, seed=rfsb.GRID_SEED)
            # Erratum 3 (spec §12): K_ERR 64->32, K_FANTASY 8->4 -- a 4x refit-count cut
            # after the firewalled pilot's real timing (346.3s/campaign) put every
            # automatic ladder rung over 2 hours. n=100 and SESOI=0.02 are unchanged.
            X2 = select_erroraware_batch(
                model, X1, Y1, V1, bounds, cand, design_theta, X_er, rfsb.N_PLATE2,
                sigma_rel=orc.sigma_rel, sigma_add=orc.sigma_add,
                k_err=32, k_fantasy=4, seed=seed)
        elif mechanism == "diverse_batch":
            X2 = select_diverse_batch(model, cand, design_theta, rfsb.N_PLATE2)
        else:
            raise ValueError(f"unknown kf3-followup mechanism {mechanism!r}")

        Y2, V2 = orc.evaluate(X2)
        del model
        gc.collect()
        return (torch.cat([X1, X2]), torch.cat([Y1, Y2]), torch.cat([V1, V2]), None, None)

    return builder


def _patched_build(cond: dict, instance: str, arm: str, seed: int):
    if arm in NEW_ARMS:
        mechanism = "erroraware" if arm == "spade_cf_erroraware" else "diverse_batch"
        theta = float(cond["by_tau"][rfsb.DESIGN_TAU_Q]["tau_raw"])
        b = kf3_followup_builder(mechanism, theta)
        rec = rfsb.regenerate(instance, cond["dim"], cond["sigma"], seed, arm, builder=b,
                              **({} if cond["family"] == "hill" else {"family": cond["family"]}))
        return rec, {}
    return _original_build(cond, instance, arm, seed)


rfsb.build = _patched_build


def _first_n_committed_keys(condition: str, arm: str, n: int) -> list[tuple]:
    """The first ``n`` ``(instance, seed)`` keys already spent on ``arm``'s committed data
    for ``condition`` -- reused, never freshly drawn, per spec §3.1."""
    path = ROOT / "results" / f"final-spade-{condition.lower()}.json"
    data = json.loads(path.read_text())
    seen: list[tuple] = []
    for r in data["rows"]:
        if r["arm"] != arm:
            continue
        key = (r["instance_seed"], r["campaign_seed"])
        if key not in seen:
            seen.append(key)
        if len(seen) >= n:
            break
    return seen


def run_pilot() -> None:
    """spec §3: wall-clock only, to its own log; every outcome to a file never opened."""
    cond = rfsb.conditions()["C2"]
    keys = _first_n_committed_keys("C2", "spade_random_plate2", 5)
    grid = sobol_grid(cond["dim"], rfsb.GRID_N, seed=rfsb.GRID_SEED)
    X_sub = sobol_grid(cond["dim"], rfsb.SUBSET_N, seed=rfsb.GRID_SEED)
    head = rfsb._head()

    timing_log = ROOT / "results" / "kf3-followup-pilot-timing.log"
    discard = ROOT / "results" / "kf3-followup-pilot-DISCARD.json"
    all_rows = []

    print(f"PILOT: spade_cf_erroraware x {len(keys)} campaigns, C2 only. "
          f"Timing -> {timing_log.name}. Outcomes -> {discard.name} (never read).")

    with timing_log.open("a") as fh:
        for instance, seed in keys:
            t0 = time.time()
            orc_t = rfsb._oracle(cond["family"], instance, cond["dim"], cond["sigma"], seed)
            with torch.no_grad():
                truth = orc_t.truth(grid).reshape(-1).double()
                truth_sub = orc_t.truth(X_sub).reshape(-1).double()
            rows = rfsb.score(cond, instance, "spade_cf_erroraware", seed, grid, X_sub,
                              truth, truth_sub, cond["by_tau"], head)
            elapsed = time.time() - t0
            all_rows.extend(rows)
            fh.write(f"{elapsed:.3f}\n")
            fh.flush()
            print(f"  campaign {instance} seed={seed}: {elapsed:.1f}s "
                  f"(outcome discarded, not shown)")

    discard.write_text(json.dumps({"rows": all_rows}))
    print(f"\nPilot done. Read ONLY {timing_log.name} to apply spec §3.2's decision rule.")


def run_real(condition: str, arm: str, limit: int, out: Path | None) -> None:
    if arm not in NEW_ARMS:
        raise SystemExit(f"arm must be one of {NEW_ARMS}, got {arm!r}")
    cond = rfsb.conditions()[condition]
    keys = rfsb._keys(cond["family"], limit)
    grid = sobol_grid(cond["dim"], rfsb.GRID_N, seed=rfsb.GRID_SEED)
    X_sub = sobol_grid(cond["dim"], rfsb.SUBSET_N, seed=rfsb.GRID_SEED)
    head, dirty = rfsb._head(), rfsb._dirty()

    out = out or (ROOT / "results" / f"kf3-followup-{condition.lower()}-{arm}.json")
    ckpt = out.with_suffix(".ckpt.jsonl")
    done = set()
    if ckpt.exists():
        for line in ckpt.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["instance_seed"], r["campaign_seed"]))

    print(f"{STUDY_ID} · {condition} · {arm} · {len(keys)} campaigns")
    if dirty:
        print("warning: working tree dirty; code_commit is not a faithful fingerprint")

    t0 = time.time()
    with ckpt.open("a") as fh:
        for n, (instance, seed) in enumerate(keys, 1):
            if (instance, seed) in done:
                continue
            orc_t = rfsb._oracle(cond["family"], instance, cond["dim"], cond["sigma"], seed)
            with torch.no_grad():
                truth = orc_t.truth(grid).reshape(-1).double()
                truth_sub = orc_t.truth(X_sub).reshape(-1).double()
            rows = rfsb.score(cond, instance, arm, seed, grid, X_sub, truth, truth_sub,
                              cond["by_tau"], head)
            for r in rows:
                fh.write(json.dumps(r) + "\n")
            fh.flush()
            el = time.time() - t0
            print(f"[{n:4d}/{len(keys)}] {instance} seed={seed} "
                  f"({el/60:.1f}m, eta {(el/n)*(len(keys)-n)/60:.0f}m)")

    rows = [json.loads(l) for l in ckpt.read_text().splitlines() if l.strip()]
    out.write_text(json.dumps({
        "study_id": STUDY_ID, "registration_commit": REGISTRATION_COMMIT,
        "code_commit": head, "dirty": dirty, "condition": condition, "arm": arm,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_campaigns": len(keys), "rows": rows,
    }, indent=1))
    print(f"\nwrote {out.name} · {len(rows)} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="run the firewalled timing pilot")
    ap.add_argument("--condition")
    ap.add_argument("--arm", choices=NEW_ARMS)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.pilot:
        run_pilot()
        return
    if not args.condition or not args.arm:
        raise SystemExit("--condition and --arm are required outside --pilot")
    run_real(args.condition, args.arm, args.limit, args.out)


if __name__ == "__main__":
    main()
