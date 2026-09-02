"""§9 item 3: `spade_cf_m0` and `spade_random_plate2` must reproduce their already-committed
rows bit-for-bit BEFORE any new KF-3-follow-up arm's data is trusted.

Registered in `docs/SPADE-KF3-FOLLOWUP-SPEC.md` §9. If this fails, nothing built alongside
these two arms (`spade_cf_erroraware`, `spade_cf_diverse_batch`) is meaningful -- the
frozen study's own arms have to still reproduce first.

No new production code is exercised here: this only re-runs `scripts/
run_final_spade_benchmark.py`'s own `build()` against the committed `results/
final-spade-c2.json` and checks regret A matches exactly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_final_spade_benchmark import build, conditions  # noqa: E402

COMMITTED = ROOT / "results" / "final-spade-c2.json"


def _committed_regret_a(arm: str, n: int = 3) -> list[tuple]:
    data = json.loads(COMMITTED.read_text())
    seen: dict[tuple, float] = {}
    for r in data["rows"]:
        if r["arm"] != arm:
            continue
        key = (r["instance_seed"], r["campaign_seed"])
        seen.setdefault(key, r["regret_rule_a"])
    return list(seen.items())[:n]


@pytest.mark.parametrize("arm", ["spade_cf_m0", "spade_random_plate2"])
def test_committed_rows_reproduce_exactly(arm):
    if not COMMITTED.exists():
        pytest.skip(f"{COMMITTED} not present locally")
    cond = conditions()["C2"]
    for (instance, seed), committed_regret_a in _committed_regret_a(arm):
        rec, _ = build(cond, instance, arm, seed)
        assert float(rec.regret) == pytest.approx(committed_regret_a, rel=0, abs=1e-9), (
            f"{arm} {instance} seed={seed}: regenerated {float(rec.regret)!r} != "
            f"committed {committed_regret_a!r}")
