"""Q52 §2 — rounds-to-arrival from the committed grid. No campaign.

    python scripts/report_q52_rounds_to_arrival.py

Reads `results/q52-budget-to-target.json`. Writes
`results/q52-rounds-to-arrival.json` and prints the arrival table with rounds.

Rounds were NOT stored per landscape. The runner recorded regret at evaluation
checkpoints only. This script reconstructs rounds from those evaluation indices
using the same `rounds_for` that `scripts/run_q52_budget_to_target.py` used at
report time (git 633e74d, the SHA stamped on the artifact). That conversion was
applied there to the *median evaluation count*. Here it is applied per landscape,
then summarised as a median over the landscapes that arrived — the quantity the
arrival table needs, and not the same as rounds-of-the-median.

Arrival itself uses `boec.budget.first_budget_to_target`, the same reduction the
harness used. D19: a registration binds only the analysis that runs through it.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target  # noqa: E402

SRC = ROOT / "results" / "q52-budget-to-target.json"
OUT = ROOT / "results" / "q52-rounds-to-arrival.json"

CAP, DIM, PIPELINE_BUDGET = 200, 6, 48
QLOGEI_N_INIT = 2 * DIM + 2  # 14; CampaignConfig.n_init is None → batch_plan default
QLOGEI_Q = 4                 # CampaignConfig(d=6, budget=200, q=4) at run_q52:176

# Same rows as docs/RESULTS.md Q52 §2 arrival table (rule A, appendix targets).
ARRIVAL_ROWS = [
    (0.10, 0.10),
    (0.10, 0.08),
    (0.10, 0.05),
    (0.10, 0.12),
    (0.25, 0.10),
    (0.25, 0.08),
    (0.25, 0.15),
]


def rounds_for(arm: str, n: int) -> int:
    """Verbatim from scripts/run_q52_budget_to_target.py:96-103 (commit 633e74d).

    Partial-batch convention, applied consistently:
    - qlogei: a prefix inside the opening (n ≤ 14) still costs 1 round — the
      opening plate is paid for as a whole. After that, ceil((n-14)/4) adaptive
      plates: arriving mid-batch pays for the whole batch of 4.
    - doe: checkpoints are multiples of 48 only (a partial pipeline is not the
      method). 3 * (n // 48) = 3 rounds per completed pipeline. An arrival that
      would have occurred at evaluation 30 is stored as 48, which is when that
      pipeline completes.
    - spread_gp / random: one-shot. 1 round at any n.
    """
    if arm == "doe":
        return 3 * (n // PIPELINE_BUDGET)
    if arm == "qlogei":
        n_init = QLOGEI_N_INIT
        return 1 if n <= n_init else 1 + math.ceil((n - n_init) / QLOGEI_Q)
    return 1


def _median(xs: list[int]) -> float | None:
    return None if not xs else float(np.median(xs))


def _arrivals(rows, arm: str, rule: str, target: float) -> list:
    out = []
    for r in rows:
        curve = r["arms"].get(arm, {}).get(rule)
        if curve is None:
            continue
        out.append(first_budget_to_target(curve, target=target, cap=CAP))
    return out


def _arm_summary(arrivals, arm: str) -> dict:
    n = len(arrivals)
    got_n, got_r = [], []
    for a in arrivals:
        if a is ARRIVAL_CENSORED:
            continue
        got_n.append(int(a))
        got_r.append(rounds_for(arm, int(a)))
    return dict(
        n=n,
        n_arrived=len(got_n),
        evals=got_n,
        rounds=got_r,
        median_evals=_median(got_n),
        median_rounds=_median(got_r),
        rounds_histogram=dict(sorted(Counter(got_r).items())),
        evals_histogram=dict(sorted(Counter(got_n).items())),
    )


def _mcnemar(bo, doe) -> dict:
    bo_only = doe_only = both = neither = 0
    for b, d in zip(bo, doe):
        b_ok = b is not ARRIVAL_CENSORED
        d_ok = d is not ARRIVAL_CENSORED
        if b_ok and d_ok:
            both += 1
        elif b_ok:
            bo_only += 1
        elif d_ok:
            doe_only += 1
        else:
            neither += 1
    disc = bo_only + doe_only
    p = float(binomtest(bo_only, disc, 0.5, alternative="two-sided").pvalue) if disc else 1.0
    return dict(bo_only=bo_only, doe_only=doe_only, both=both, neither=neither,
                discordant=f"{bo_only} : {doe_only}", exact_p=round(p, 4), exact_p_raw=p)


def _paired(bo, doe) -> dict | None:
    """Cost (wells) and time (rounds) on instances where both arrived. Not the headline."""
    pairs = []
    for b, d in zip(bo, doe):
        if b is ARRIVAL_CENSORED or d is ARRIVAL_CENSORED:
            continue
        pairs.append((int(b), int(d),
                      rounds_for("qlogei", int(b)), rounds_for("doe", int(d))))
    if not pairs:
        return None
    return dict(
        n_both=len(pairs),
        bo_fewer_wells=sum(1 for b, d, _, _ in pairs if b < d),
        doe_fewer_wells=sum(1 for b, d, _, _ in pairs if d < b),
        ties_wells=sum(1 for b, d, _, _ in pairs if b == d),
        bo_fewer_rounds=sum(1 for _, _, br, dr in pairs if br < dr),
        doe_fewer_rounds=sum(1 for _, _, br, dr in pairs if dr < br),
        ties_rounds=sum(1 for _, _, br, dr in pairs if br == dr),
        median_bo_wells=float(np.median([p[0] for p in pairs])),
        median_doe_wells=float(np.median([p[1] for p in pairs])),
        median_bo_rounds=float(np.median([p[2] for p in pairs])),
        median_doe_rounds=float(np.median([p[3] for p in pairs])),
    )


def main() -> None:
    grid = json.loads(SRC.read_text())
    rows = grid["rows"]
    prov = grid["provenance"]

    structure = {
        "logged_or_reconstructed": "reconstructed",
        "why": (
            "Per-landscape rows store regret at evaluation checkpoints only. "
            "No rounds-to-arrival, batch index, or round_index field exists on "
            "the curves. The runner's rounds_for was applied at print time to "
            "the median evaluation count, not per landscape."
        ),
        "source": str(SRC.relative_to(ROOT)),
        "artifact_git_sha": prov["git_sha"],
        "batch_structure": {
            "qlogei": {
                "opening": QLOGEI_N_INIT,
                "batch_thereafter": QLOGEI_Q,
                "source": (
                    "scripts/run_q52_budget_to_target.py:176 "
                    "CampaignConfig(d=6, budget=200, q=4); "
                    "src/boec/campaign.py:batch_plan n_init=2*d+2"
                ),
                "partial_batch": "ceil; mid-batch pays for the whole plate of 4. "
                                 "Prefix n≤14 still costs 1 round (the opening).",
                "formula": "1 if n<=14 else 1+ceil((n-14)/4)",
            },
            "doe": {
                "opening": 20,
                "batch_thereafter": "27 (CCD) then 1 (confirm) = 3 sequential stages",
                "pipeline_evals": PIPELINE_BUDGET,
                "source": (
                    "src/boec/doe.py header (20+27+1); "
                    "src/boec/doe_repeat.py PIPELINE_BUDGET=48; "
                    "checkpoints 48,96,144,192 only"
                ),
                "partial_batch": (
                    "A partial pipeline is not the method. Stored arrival is the "
                    "completed pipeline that contains the crossing (48/96/144/192). "
                    "Rounds = 3 per completed pipeline."
                ),
                "formula": "3 * (n // 48)",
            },
            "spread_gp": {
                "opening": "n (fresh LHS of size n at each checkpoint)",
                "batch_thereafter": "none — one-shot",
                "source": "scripts/run_q52_budget_to_target.py:200-211",
                "partial_batch": "not applicable; 1 round at any n",
                "formula": "1",
            },
            "random": {
                "opening": "n (fresh random design of size n)",
                "batch_thereafter": "none — one-shot",
                "source": "scripts/run_q52_budget_to_target.py:200-211",
                "partial_batch": "not applicable; 1 round at any n",
                "formula": "1",
            },
        },
        "batch_structure_changed_between_runs": False,
        "note": (
            "One Q52 §2 grid. Artifact SHA 633e74d is the harness commit. "
            "rounds_for in that file is identical to current main."
        ),
    }

    table = []
    spread_table = []
    print("ROUNDS WERE RECONSTRUCTED — not logged per landscape.")
    print("Source:", SRC.relative_to(ROOT), "  SHA", prov["git_sha"])
    print()
    print("COST = wells (evaluations).  TIME = rounds (plate cycles).")
    print("Medians are over the landscapes that arrived; n is in the cell.")
    print()
    hdr = (f"{'σ':>5} {'T':>5} {'BO':>7} {'wells':>7} {'rounds':>7} "
           f"{'DoE':>7} {'wells':>7} {'rounds':>7} {'disc':>10} {'p':>8}")
    print(hdr)
    print("-" * len(hdr))

    headline = None
    for sigma, target in ARRIVAL_ROWS:
        rs = [r for r in rows if abs(r["sigma"] - sigma) < 1e-9]
        bo_a = _arrivals(rs, "qlogei", "rule_a", target)
        doe_a = _arrivals(rs, "doe", "rule_a", target)
        sp_a = _arrivals(rs, "spread_gp", "rule_a", target)
        bo = _arm_summary(bo_a, "qlogei")
        doe = _arm_summary(doe_a, "doe")
        sp = _arm_summary(sp_a, "spread_gp")
        mc = _mcnemar(bo_a, doe_a)
        mc_sp = _mcnemar(sp_a, doe_a)
        paired = _paired(bo_a, doe_a)
        row = dict(sigma=sigma, target=target, rule="rule_a",
                   bo=bo, doe=doe, spread_gp=sp,
                   discordant=mc, discordant_spread_vs_doe=mc_sp,
                   paired_both_arrived=paired)
        table.append(row)
        spread_table.append(row)
        def cell(s, key):
            med = s[key]
            return "—" if med is None else f"{med:g}"
        print(f"{sigma:>5.2f} {target:>5.2f} "
              f"{bo['n_arrived']:>2}/{bo['n']:<4} {cell(bo,'median_evals'):>7} {cell(bo,'median_rounds'):>7} "
              f"{doe['n_arrived']:>2}/{doe['n']:<4} {cell(doe,'median_evals'):>7} {cell(doe,'median_rounds'):>7} "
              f"{mc['discordant']:>10} {mc['exact_p']:>8.4f}")
        if abs(sigma - 0.10) < 1e-9 and abs(target - 0.10) < 1e-9:
            headline = row

    print()
    print("spread_gp — 1 round by construction. Wells still vary with the design size that first hit.")
    print(f"{'σ':>5} {'T':>5} {'sGP':>7} {'wells':>7} {'rounds':>7} "
          f"{'DoE':>7} {'wells':>7} {'rounds':>7} {'disc vs DoE':>12} {'p':>8}")
    print("-" * 88)
    for row in spread_table:
        sp, doe, mc = row["spread_gp"], row["doe"], row["discordant_spread_vs_doe"]
        def cell(s, key):
            med = s[key]
            return "—" if med is None else f"{med:g}"
        print(f"{row['sigma']:>5.2f} {row['target']:>5.2f} "
              f"{sp['n_arrived']:>2}/{sp['n']:<4} {cell(sp,'median_evals'):>7} {cell(sp,'median_rounds'):>7} "
              f"{doe['n_arrived']:>2}/{doe['n']:<4} {cell(doe,'median_evals'):>7} {cell(doe,'median_rounds'):>7} "
              f"{mc['discordant']:>12} {mc['exact_p']:>8.4f}")

    assert headline is not None
    h = headline
    print("\n" + "=" * 72)
    print("HEADLINE  σ=0.10  target=0.10  rule A")
    print(f"  BO  {h['bo']['n_arrived']}/{h['bo']['n']}  "
          f"COST {h['bo']['median_evals']:g} wells   TIME {h['bo']['median_rounds']:g} rounds")
    print(f"  DoE {h['doe']['n_arrived']}/{h['doe']['n']}  "
          f"COST {h['doe']['median_evals']:g} wells   TIME {h['doe']['median_rounds']:g} rounds")
    print(f"  spread_gp {h['spread_gp']['n_arrived']}/{h['spread_gp']['n']}  "
          f"COST {h['spread_gp']['median_evals']:g} wells   TIME {h['spread_gp']['median_rounds']:g} round")
    print(f"  BO wells histogram:  {h['bo']['evals_histogram']}")
    print(f"  BO rounds histogram: {h['bo']['rounds_histogram']}")
    print(f"  DoE wells histogram: {h['doe']['evals_histogram']}")
    print(f"  DoE rounds histogram:{h['doe']['rounds_histogram']}")
    pr = h["paired_both_arrived"]
    if pr:
        print(f"  among both-arrived (n={pr['n_both']}):")
        print(f"    COST  BO fewer wells {pr['bo_fewer_wells']}, DoE fewer {pr['doe_fewer_wells']}, ties {pr['ties_wells']}")
        print(f"    TIME  BO fewer rounds {pr['bo_fewer_rounds']}, DoE fewer {pr['doe_fewer_rounds']}, ties {pr['ties_rounds']}")

    # Guard: published arrival counts must regenerate.
    assert h["bo"]["n_arrived"] == 24 and h["doe"]["n_arrived"] == 13, h
    assert h["discordant"]["discordant"] == "11 : 0", h["discordant"]

    payload = dict(
        reconstruction=structure,
        rule="rule_a",
        table=table,
        headline=dict(sigma=0.10, target=0.10, **{k: h[k] for k in
                      ("bo", "doe", "spread_gp", "discordant",
                       "paired_both_arrived")}),
    )
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\nwritten {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
