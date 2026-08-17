"""TOST (SESOI = 0.02) on registered contrasts. No new campaigns.

    .venv/bin/python scripts/tost_contrasts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.tost import per_instance, tost_paired, wilcoxon_mde  # noqa: E402

SESOI = 0.02
N_BOOT = 4000
OUT = ROOT / "results" / "tost-contrasts.json"
E2 = ROOT / "results" / "e2-grid.json"
E2_D8 = ROOT / "results" / "e2-doe-d8.json"
Q34 = ROOT / "results" / "q34-factorial.json"
Q35 = ROOT / "results" / "q35-constrained-rsm.json"
Q58 = ROOT / "results" / "q58-selection-sensitivity.json"
Q60 = ROOT / "results" / "q60-top3-average.json"


def _load(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


def _cell(rows: list[dict], dim: int, sigma: float) -> list[dict]:
    return [r for r in rows if int(r["dim"]) == dim and abs(float(r["sigma"]) - sigma) < 1e-12]


def _score(name: str, diffs: np.ndarray) -> dict:
    tost = tost_paired(diffs, sesoi=SESOI, n_boot=N_BOOT)
    sigma = float(np.std(diffs, ddof=1))
    mde = wilcoxon_mde(max(sigma, 1e-12), n=int(diffs.size), n_sim=400, seed=0)
    return dict(name=name, status="ok", sigma=sigma, wilcoxon_mde=mde, **tost)


def _e2_contrast(dim: int, sigma: float) -> np.ndarray:
    doe_src = E2_D8 if dim == 8 else E2
    doe = per_instance(
        [r for r in _cell(_load(doe_src), dim, sigma) if r["arm"] == "doe"],
        "regret")
    bo = per_instance(
        [r for r in _cell(_load(E2), dim, sigma) if r["arm"] == "qlogei"],
        "regret")
    if doe.shape != bo.shape or doe.size != 25:
        raise AssertionError(
            f"E2 pairing failed at d={dim} sigma={sigma}: {doe.shape} vs {bo.shape}")
    return doe - bo


def main() -> None:
    rows_out = []

    q34 = _load(Q34)
    q35 = _load(Q35)
    for dim, sigma in ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10)):
        doe = per_instance(_cell(q35, dim, sigma), "constrained")
        gp = per_instance(_cell(q34, dim, sigma), "cell4_bo_gp")
        if doe.shape != gp.shape:
            raise AssertionError(
                f"in-region pairing failed at d={dim} sigma={sigma}: "
                f"{doe.shape} vs {gp.shape}")
        rows_out.append(_score(f"inregion|d={dim}|sigma={sigma}|doe-gp", doe - gp))

    for dim, sigma in ((6, 0.10), (8, 0.10)):
        d = _e2_contrast(dim, sigma)
        rows_out.append(_score(f"measured-argmax|d={dim}|sigma={sigma}|doe-qlogei", d))

    q58 = _load(Q58)
    for rule in ("posterior", "top3"):
        bo = per_instance([{"instance": r["instance"], rule: r["arms"]["bo"][rule]}
                           for r in q58], rule)
        doe = per_instance([{"instance": r["instance"], rule: r["arms"]["doe"][rule]}
                           for r in q58], rule)
        rows_out.append(_score(f"q58|{rule}|doe-bo", doe - bo))

    if Q60.exists():
        q60 = _load(Q60)
        bo = per_instance([{"instance": r["instance"],
                            "top3_average": r["arms"]["bo"]["top3_average"]}
                           for r in q60], "top3_average")
        doe = per_instance([{"instance": r["instance"],
                             "top3_average": r["arms"]["doe"]["top3_average"]}
                           for r in q60], "top3_average")
        rows_out.append(_score("q60|top3_average|doe-bo", doe - bo))
    else:
        rows_out.append(dict(name="q60|top3_average|doe-bo", status="not_run"))

    OUT.write_text(json.dumps(
        dict(sesoi=SESOI, n_boot=N_BOOT, n_sim_mde=400, rows=rows_out), indent=1))
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in rows_out:
        if r.get("status") != "ok":
            print(f"  {r['name']}: {r['status']}")
            continue
        print(f"  {r['name']}: {r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]  "
              f"{r['verdict']}  MDE={r['wilcoxon_mde']:.4f}")


if __name__ == "__main__":
    main()
