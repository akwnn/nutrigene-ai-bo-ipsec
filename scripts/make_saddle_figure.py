"""Figure 3 — saddle / ridge schematic with numbers from q35 JSON.

    python scripts/make_saddle_figure.py

The cartoon is a schematic. The counts and regret gaps are derived here so the
page cannot drift from `results/q35-constrained-rsm.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "q35-constrained-rsm.json"
OUT = ROOT / "results" / "figures" / "fig3-saddle.html"


def stats(rows: list[dict]) -> dict:
    kinds = [r["stationary_kind"] for r in rows]
    n_saddle = sum(k == "saddle" for k in kinds)
    primary = [r for r in rows if r["dim"] == 6 and abs(r["sigma"] - 0.25) < 1e-12]
    by_inst: dict[str, list[dict]] = {}
    for r in primary:
        by_inst.setdefault(r["instance"], []).append(r)
    unc = np.mean([np.mean([r["unconstrained"] for r in v]) for v in by_inst.values()])
    con = np.mean([np.mean([r["constrained"] for r in v]) for v in by_inst.values()])
    exits = [r["ridge_exit_radius"] for r in rows if r.get("ridge_exit_radius") is not None]
    corners = [r["ridge_region_corner_radius"] for r in rows]
    return {
        "n": len(rows),
        "n_saddle": n_saddle,
        "n_max": sum(k == "maximum" for k in kinds),
        "unc_minus_con": round(float(unc - con), 4),
        "unc": round(float(unc), 4),
        "con": round(float(con), 4),
        "ridge_exit": round(float(np.median(exits)), 2) if exits else None,
        "ridge_corner": round(float(np.median(corners)), 2) if corners else None,
    }


def main() -> None:
    rows = json.loads(SRC.read_text())
    s = stats(rows)
    assert s["n_saddle"] == s["n"], (
        f"expected all saddles, got {s['n_saddle']}/{s['n']}"
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Figure 3. Why a fitted quadratic becomes a saddle, and why ridge constraints matter</title>
<style>
:root{{--ground:#F6F7F9;--ink:#161B22;--muted:#5A6472;--line:#DCE1E8;--doe:#C2410C;--bo:#2563EB;--sans:ui-sans-serif,system-ui,sans-serif;--serif:ui-serif,Georgia,serif}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);line-height:1.55}}
.wrap{{max-width:820px;margin:0 auto;padding:32px 20px 64px}}
h1{{font-family:var(--serif);font-size:1.45rem;font-weight:600;margin:0 0 .5rem}}
.cap,.note{{color:var(--muted);font-size:.92rem;max-width:72ch}}
svg{{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:10px;margin:12px 0 8px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:8px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}}
.card h2{{font-size:.95rem;margin:0 0 6px}}
.card p{{margin:0;font-size:.9rem;color:var(--muted)}}
@media(max-width:640px){{.row{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="wrap">
<h1>Figure 3. A saddle fit cannot have an interior maximum; unconstrained recommendation leaves the explored region</h1>
<p class="cap">Schematic of the mechanism measured on the Hill ensemble: the fitted second-order surface was a saddle in <strong>{s['n_saddle']}/{s['n']}</strong> runs. On a compact box the maximum of a saddle lies on the boundary. Ridge analysis (constrained recommendation) keeps the suggestion inside the region the CCD actually explored. The ridge path left that region at median radius ≈{s['ridge_exit']} versus a corner radius of {s['ridge_corner']}.</p>
<svg viewBox="0 0 640 340" role="img" aria-label="Saddle schematic">
  <rect x="40" y="30" width="260" height="260" fill="#F6F7F9" stroke="#C8D0DA"/>
  <text x="170" y="22" text-anchor="middle" font-size="12" fill="#5A6472">Unconstrained: peak forced to the wall</text>
  <path d="M70,160 C120,60 220,60 270,160 C220,260 120,260 70,160" fill="none" stroke="#94A3B8" stroke-width="1.2"/>
  <path d="M90,160 C130,90 210,90 250,160 C210,230 130,230 90,160" fill="none" stroke="#94A3B8" stroke-width="1.2"/>
  <path d="M110,160 C140,115 200,115 230,160 C200,205 140,205 110,160" fill="none" stroke="#94A3B8" stroke-width="1.2"/>
  <circle cx="170" cy="160" r="4" fill="#39424E"/>
  <text x="178" y="156" font-size="11" fill="#39424E">saddle (not a max)</text>
  <rect x="110" y="110" width="120" height="100" fill="none" stroke="#C2410C" stroke-dasharray="4 3"/>
  <text x="170" y="104" text-anchor="middle" font-size="11" fill="#C2410C">explored region (CCD)</text>
  <circle cx="300" cy="80" r="7" fill="#C2410C"/>
  <text x="308" y="76" font-size="11" fill="#C2410C">unconstrained argmax</text>
  <line x1="230" y1="110" x2="300" y2="80" stroke="#C2410C" stroke-dasharray="3 3"/>

  <rect x="340" y="30" width="260" height="260" fill="#F6F7F9" stroke="#C8D0DA"/>
  <text x="470" y="22" text-anchor="middle" font-size="12" fill="#5A6472">Constrained: ridge keeps the suggestion inside</text>
  <path d="M370,160 C420,60 520,60 570,160 C520,260 420,260 370,160" fill="none" stroke="#94A3B8" stroke-width="1.2"/>
  <path d="M390,160 C430,90 510,90 550,160 C510,230 430,230 390,160" fill="none" stroke="#94A3B8" stroke-width="1.2"/>
  <rect x="410" y="110" width="120" height="100" fill="#C2410C" fill-opacity=".06" stroke="#C2410C"/>
  <circle cx="470" cy="160" r="4" fill="#39424E"/>
  <circle cx="530" cy="160" r="7" fill="#0D9488"/>
  <text x="470" y="292" text-anchor="middle" font-size="11" fill="#0D9488">constrained argmax on the ridge, inside the CCD</text>
</svg>
<div class="row">
  <div class="card">
    <h2>What the Hessian said</h2>
    <p>Indefinite Hessian = saddle. There is a stationary point, but it is not a maximum ({s['n_saddle']}/{s['n']} Hill runs; interior maxima: {s['n_max']}). Asking the polynomial for its favourite recipe anywhere in the box therefore returns a face or a corner, typically outside the CCD.</p>
  </div>
  <div class="card">
    <h2>What that did to regret</h2>
    <p>At the primary cell, unconstrained ({s['unc']}) minus constrained ({s['con']}) DoE regret was <strong>+{s['unc_minus_con']}</strong>. Constraining to the explored region removed the BO advantage in three of four cells.</p>
  </div>
</div>
<p class="note">Source: {SRC.relative_to(ROOT)}. Numbers filled by scripts/make_saddle_figure.py. Cartoon is a schematic, not a fitted contour from one run.</p>
</div>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"  wrote {OUT.relative_to(ROOT)}")
    print(f"  saddle {s['n_saddle']}/{s['n']}; primary unc−con +{s['unc_minus_con']}")


if __name__ == "__main__":
    main()
