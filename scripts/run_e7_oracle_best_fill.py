"""E7 · `oracle_best` for the arms no committed file carries -- **SPADE first**.

WHY THIS EXISTS
---------------
SPADE was missing from E7's headline table, and the reason was mundane rather than
principled: `step0-oracle-best.json` carries only `versionb_plate1_ceiling` at **40 wells**,
and a 40-well ceiling cannot be compared to eight 48-well arms. **The object under test was
absent from the result that matters most.** This fills that column at the shared budget.

ZERO NEW EXPERIMENTS, BUT NOT ZERO COMPUTE. Campaigns are **regenerated** deterministically
through `replay.regenerate` -- the same designs, the same seeds, the same oracle. Nothing
new is measured; the wells are the wells the committed campaigns already visited.

THE GATE IS THE WHOLE POINT
----------------------------
Every arm a committed file already carries is regenerated here too and must return
`oracle_best` at **|Δ| = 0**. A new column from a construction that cannot reproduce the
committed one is not a comparison (D12). SPADE itself has no committed column -- that is
why it is being filled -- so it is deliberately **not** in `GATE_ARMS`, and the gate arms
carry the credibility for it.
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

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.replay import instance_by_id                              # noqa: E402
from boec.torch_oracle import BiphasicOracle                        # noqa: E402

R = ROOT / "results"
OUT = R / "e7-oracle-best-fill.json"
STEP0 = R / "step0-oracle-best.json"
Q57 = R / "q57-search-vs-id.json"
VC010 = R / "versionc-gate-s010.json"

DIM, BUDGET = 6, 48

#: **SPADE and its two ablations.** The reason this file exists.
SPADE_ARMS = ("versionb", "versionb_random", "versionb_predictive")
#: Free to regenerate (static designs) and they complete the sigma=0.10 comparison.
SPREAD_ARMS = ("lhs", "sobol", "random", "plate1_only")
FILL_ARMS = SPADE_ARMS + SPREAD_ARMS
#: Carried by `step0-oracle-best.json`; regenerated here purely to gate the construction.
GATE_ARMS = ("lhs", "sobol", "random", "plate1_only")
#: DELIBERATELY OMITTED: `qlogei-add` / `qlogei-addonly` cost ~14s and ~10s per campaign
#: (measured) and are kernel variants, not the contrast this file exists for. `doe`,
#: `qlogei`, `qlognei` already have a committed `oracle_best` in q57 at BOTH sigmas.
OMITTED = {"qlogei-add": "14s/campaign, kernel variant, not the SPADE contrast",
           "qlogei-addonly": "10s/campaign, kernel variant, not the SPADE contrast",
           "doe": "committed in q57 at both sigmas",
           "qlogei": "committed in q57 at both sigmas (bo_*)",
           "qlognei": "committed in q57 at both sigmas (nei_*)"}

SIGMAS = (0.25, 0.10)

_GATE_MOD = None


def _gate_module():
    """`run_versionc_gate.regenerate_arm` IMPORTED, never re-expressed. It is the only
    construction that has been gated clean at |Δ| = 0 over 600 rows, and a second copy of
    the Version B builder would be a second campaign."""
    global _GATE_MOD
    if _GATE_MOD is None:
        spec = importlib.util.spec_from_file_location(
            "_vc_gate", ROOT / "scripts" / "run_versionc_gate.py")
        _GATE_MOD = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_GATE_MOD)
    return _GATE_MOD


def oracle_best_from(mu_max: float, truth_values) -> float:
    """Regret of the genuinely best VISITED well -- the ceiling any terminal rule could hit."""
    return float(mu_max) - float(max(truth_values))


def keys_for(sigma: float) -> list:
    """The (instance, seed) pairs the rule-P source carries at this sigma."""
    if sigma == 0.10:
        return sorted({(r["instance"], r["seed"]) for r in
                       json.loads(VC010.read_text())["rows"]})
    return sorted({(r["instance"], r["seed"]) for r in
                   json.loads(STEP0.read_text())["rows"]})


def committed_gate_table() -> dict:
    """`(instance, seed, arm) -> oracle_best` at sigma = 0.25, from step0."""
    return {(r["instance"], r["seed"], r["arm"]): r["oracle_best"]
            for r in json.loads(STEP0.read_text())["rows"]}


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:                                            # noqa: BLE001
            return "unknown"
    return {"git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(argv),
            "python": platform.python_version(), "torch": torch.__version__}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--limit", type=int, default=None, help="smoke: first N keys")
    args = ap.parse_args()
    final = Path(args.out) if args.out else OUT

    g = _gate_module()
    gate_ref = committed_gate_table()
    rows, gate_fail, n = [], [], 0
    total = sum(len(keys_for(s)) for s in SIGMAS) * len(FILL_ARMS)
    if args.limit:
        total = args.limit * len(SIGMAS) * len(FILL_ARMS)

    print(f"E7 · oracle_best fill · SPADE {SPADE_ARMS} at {BUDGET} wells")
    print(f"gate arms {GATE_ARMS} must reproduce step0 at |delta| = 0")
    print(f"{total} campaigns\n")

    partial = final.with_suffix(final.suffix + ".partial")
    for sigma in SIGMAS:
        keys = keys_for(sigma)
        if args.limit:
            keys = keys[:args.limit]
        for inst_id, seed in keys:
            inst = instance_by_id(inst_id, DIM)
            mu_max = float(inst.optimum_value)
            orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
            for arm in FILL_ARMS:
                t0 = time.time()
                rec = g.regenerate_arm(inst_id, DIM, sigma, seed, arm)
                with torch.no_grad():
                    ob = oracle_best_from(mu_max, [float(orc.truth(rec.X).max())])
                nw = int(rec.X.shape[0])
                row = {"instance": inst_id, "seed": seed, "arm": arm, "sigma": sigma,
                       "dim": DIM, "oracle_best": ob, "n_wells": nw,
                       "secs": round(time.time() - t0, 2)}
                # THE GATE. sigma=0.25 only -- step0 is a sigma=0.25 file.
                if sigma == 0.25 and arm in GATE_ARMS:
                    ref = gate_ref.get((inst_id, seed, arm))
                    if ref is not None:
                        row["committed_oracle_best"] = ref
                        row["gate_abs_delta"] = abs(ob - ref)
                        if abs(ob - ref) > 0.0:
                            gate_fail.append(dict(row))
                if nw != BUDGET:
                    row["budget_warning"] = f"{nw} wells, expected {BUDGET}"
                rows.append(row)
                n += 1
            print(f"[{n:4d}/{total}] s={sigma} {inst_id[:8]} seed={seed} "
                  f"versionb={[r for r in rows if r['arm']=='versionb'][-1]['oracle_best']:+.4f} "
                  f"gate_fail={len(gate_fail)}", flush=True)
            partial.write_text(json.dumps(
                {"status": "partial", "keys_present": n, "keys_expected": total,
                 "provenance": _provenance(sys.argv),
                 "config": {"fill_arms": list(FILL_ARMS), "gate_arms": list(GATE_ARMS),
                            "spade_arms": list(SPADE_ARMS), "omitted": OMITTED,
                            "budget": BUDGET, "sigmas": list(SIGMAS)},
                 "gate_failures": gate_fail, "rows": rows}, indent=1))

    payload = {"status": "COMPLETE", "keys_present": n, "keys_expected": total,
               "provenance": _provenance(sys.argv),
               "config": {"fill_arms": list(FILL_ARMS), "gate_arms": list(GATE_ARMS),
                          "spade_arms": list(SPADE_ARMS), "omitted": OMITTED,
                          "budget": BUDGET, "sigmas": list(SIGMAS)},
               "gate_failures": gate_fail, "rows": rows}
    final.write_text(json.dumps(payload, indent=1))
    partial.unlink(missing_ok=True)
    print(f"\ngate failures: {len(gate_fail)}")
    print(f"wrote {final.name} · {len(rows)} rows")


if __name__ == "__main__":
    main()
