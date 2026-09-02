"""K1-gate: the measured reproducibility of every committed arm.

Its OUTPUT IS A POLICY, not a verdict. Whatever the per-arm worst ``|delta|`` turns out
to be is what K6, K0, K1 and K3 must gate against. Registered in
``docs/OPEN-QUESTIONS.md`` (commit ``ef118dd``) before this file existed.

The rule, fixed before the numbers:

* ``doe`` has no acquisition optimiser, so **exact equality is the right bar**. A failure
  there is a hard stop -- it would mean the ensemble order or seeding convention has
  drifted and every downstream number is unsafe.
* ``qlogei``/``qlognei`` route through multi-start L-BFGS-B, which Q54 measured at worst
  ``|delta|`` 2.463e-06 with 482/550 exact. If they are not exact they get Q54's
  treatment: gate on whether a **verdict** changes, never on a raised constant.

Checkpointed per row, so a kill costs one campaign rather than the run.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from boec.replay import committed_rows, regenerate

OUT = Path("results/k1-replay-gate.json")
ARMS = ("doe", "qlogei", "qlognei")


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def main() -> None:
    head = _head()
    print(f"K1-gate · replay reproducibility · HEAD={head}")
    print(f"python={platform.python_version()}\n")

    rows = [r for r in committed_rows() if r["arm"] in ARMS]
    print(f"{len(rows)} committed rows in scope: {ARMS}\n")

    out_rows: list[dict] = []
    worst: dict[str, float] = defaultdict(float)
    exact: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    t0 = time.time()

    for i, r in enumerate(rows, 1):
        t = time.time()
        rec = regenerate(r["instance"], r["dim"], r["sigma"], r["seed"], r["arm"])
        delta = abs(rec.regret - r["regret"])
        arm = r["arm"]
        worst[arm] = max(worst[arm], delta)
        exact[arm] += int(delta == 0.0)
        total[arm] += 1
        out_rows.append({
            "instance": r["instance"], "dim": r["dim"], "sigma": r["sigma"],
            "seed": r["seed"], "arm": arm, "committed": r["regret"],
            "regenerated": rec.regret, "abs_delta": delta,
            "secs": round(time.time() - t, 2),
        })
        print(f"[{i:3d}/{len(rows)}] {arm:8s} d={r['dim']} s={r['sigma']:<4} "
              f"seed={r['seed']} {r['instance']} delta={delta:.3e} "
              f"({time.time()-t:.1f}s)", flush=True)

        policy = {
            a: {"rows": total[a], "exact": exact[a], "worst_abs_delta": worst[a],
                "gate": "exact" if worst[a] == 0.0 else "verdict-invariance"}
            for a in ARMS if total[a]
        }
        OUT.write_text(json.dumps(
            {"provenance": {"git_sha": head, "argv": sys.argv,
                            "python": platform.python_version()},
             "policy": policy, "rows": out_rows}, indent=2))

    print(f"\n--- POLICY --- ({time.time()-t0:.0f}s total)")
    for a in ARMS:
        if not total[a]:
            continue
        p = policy[a]
        print(f"{a:8s} {p['exact']:3d}/{p['rows']:3d} exact · worst "
              f"{p['worst_abs_delta']:.3e} -> {p['gate']}")

    if worst["doe"] != 0.0:
        print("\n*** HARD STOP: the DoE arm did not reproduce exactly. ***")
        print("Do not proceed to K6. Seeding or ensemble order has drifted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
