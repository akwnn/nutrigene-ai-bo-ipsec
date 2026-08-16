"""Figure 1 — the same campaigns under four terminal decisions, both arms. Workstream 1.

    python scripts/make_scoring_figure.py

Reads the committed artefacts and writes `results/figures/fig1-scoring.html`.

WHY THIS SCRIPT EXISTS AT ALL
-------------------------------
`fig1-scoring.html` was a **hand-authored page carrying twenty hardcoded numbers with no
producing script**, and it was gitignored while the manuscript cited it by path — so a
clone got a paper with a dangling figure reference and no way to re-derive it. That is the
same defect `results/E4-RESULTS-v2.md` and `results/NEGATIVE-shape-aware-mean.md` carry,
and `docs/TRIAGE.md` records it. Every number on the page is now derived here.

THE FOUR TERMINAL DECISIONS
-----------------------------
One target, ``E[1 - f(delta(D_N))]``, and four locators ``delta`` applied to the *same*
48-well campaigns:

1. **tested-best** — the truth at the best well the campaign ran, whether or not the assay
   could tell. What the search achieved, with identification removed.
2. **measured-value argmax** — the truth at the well that read highest. What a single
   noisy readout selects, and the project's published headline.
3. **naïve unconstrained model recommendation** — the model's argmax over the whole box.
   For the classical arm this is a quadratic and it is a **diagnostic of extrapolation**,
   not the classical recommendation; for the adaptive arm it is the GP posterior mean.
4. **in-region / ridge recommendation** — the model's argmax restricted to the region the
   design actually explored. This is the principal classical readout.

ONE CELL IS DELIBERATELY EMPTY
--------------------------------
There is **no stored in-region recommendation for the adaptive arm at N = 48**. Its design
is not confined to a sub-box, so "in-region" has no agreed meaning for it, and no artefact
in this repository carries the column. The bar is omitted rather than filled with the
unconstrained number, which would silently claim the two locators agree for that arm.
`docs/INFORMATION-MATRIX.md`: *empty cells stay empty; do not interpolate, do not
substitute a nearby cell.*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
OUT = ROOT / "results" / "figures" / "fig1-scoring.html"

#: Every number on the page, and the committed file it comes from. Printed in the footer
#: so a reader can check any bar against an artefact without reading this script.
SOURCES = {
    "tested-best": "results/q57-search-vs-id.json",
    "measured-value argmax": "results/q57-search-vs-id.json",
    "naive unconstrained (classical)": "results/q35-constrained-rsm.json",
    "naive unconstrained (adaptive)": "results/q34-factorial.json (cell 4: GP on BO points)",
    "in-region / ridge (classical)": "results/q35-constrained-rsm.json",
    "in-region / ridge (adaptive)": "NOT STORED — bar omitted",
}


def _rows(p: Path) -> list[dict]:
    d = json.loads(p.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


def build() -> dict:
    q57 = _rows(ROOT / "results" / "q57-search-vs-id.json")
    q35 = _rows(ROOT / "results" / "q35-constrained-rsm.json")
    q34 = _rows(ROOT / "results" / "q34-factorial.json")

    def mean_of(rows, key, dim, sigma):
        v = [r[key] for r in rows
             if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12 and r.get(key) is not None]
        return round(float(np.mean(v)), 4) if v else None

    out = {"cells": [], "sources": SOURCES}
    for dim, sigma in CELLS:
        cell = {"dim": dim, "sigma": sigma, "arms": {}}
        cell["arms"]["doe"] = {
            "tested": mean_of(q57, "doe_oracle_best", dim, sigma),
            "measured": mean_of(q57, "doe_rule_a", dim, sigma),
            "unconstrained": mean_of(q35, "unconstrained", dim, sigma),
            "inregion": mean_of(q35, "constrained", dim, sigma),
        }
        for tag, prefix in (("qlogei", "bo"), ("qlognei", "nei")):
            cell["arms"][tag] = {
                "tested": mean_of(q57, f"{prefix}_oracle_best", dim, sigma),
                "measured": mean_of(q57, f"{prefix}_rule_a", dim, sigma),
                # Only qLogEI has a stored model recommendation at N=48 (Q34 predates
                # qLogNEI being co-primary). qLogNEI's is left empty rather than borrowed.
                "unconstrained": (mean_of(q34, "cell4_bo_gp", dim, sigma)
                                  if tag == "qlogei" else None),
                "inregion": None,       # see the module docstring
            }
        out["cells"].append(cell)
    return out


HEAD = r"""<title>Four Terminal Decisions</title>
<style>
:root{
  --ground:#F5F7FA; --surface:#FFFFFF; --sunk:#E9EEF4;
  --ink:#101419; --ink-2:#37414F; --muted:#5D6A7B; --faint:#8996A8;
  --line:#DCE3EC; --rule:#C3CDDA;
  --doe:#C2540A; --qlogei:#2F6BD8; --qlognei:#0E8C7F;
  --serif:ui-serif,Georgia,"Iowan Old Style","Times New Roman",serif;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0D1116; --surface:#151A21; --sunk:#1A212A;
    --ink:#E9EDF3; --ink-2:#C3CCD8; --muted:#93A0B1; --faint:#6D7A8B;
    --line:#242C36; --rule:#3A4553;
    --doe:#F0873A; --qlogei:#6D9CF0; --qlognei:#2FC4B2;
  }
}
:root[data-theme="dark"]{
  --ground:#0D1116; --surface:#151A21; --sunk:#1A212A;
  --ink:#E9EDF3; --ink-2:#C3CCD8; --muted:#93A0B1; --faint:#6D7A8B;
  --line:#242C36; --rule:#3A4553;
  --doe:#F0873A; --qlogei:#6D9CF0; --qlognei:#2FC4B2;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1020px;margin:0 auto;padding:0 24px 96px}
.prose{max-width:70ch}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,5.2vw,3.1rem);
  line-height:1.05;letter-spacing:-.02em;margin:0 0 .55rem;text-wrap:balance}
h2{font-family:var(--serif);font-weight:600;font-size:clamp(1.3rem,3vw,1.75rem);
  line-height:1.2;margin:3.6rem 0 .5rem;text-wrap:balance}
p{margin:0 0 1.05rem;color:var(--ink-2)}
strong{color:var(--ink);font-weight:650}
code,.num{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.89em}
header{padding:78px 0 0}
.eyebrow{font-family:var(--mono);font-size:.71rem;letter-spacing:.15em;text-transform:uppercase;
  color:var(--muted);margin:0 0 1.15rem}
.lede{font-size:1.15rem;line-height:1.55;color:var(--ink-2);max-width:62ch;margin:0 0 2rem}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:24px 24px 14px;margin:1.6rem 0}
.legend{display:flex;flex-wrap:wrap;gap:18px;margin:2px 0 16px}
.legend span{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);
  font-size:.74rem;color:var(--muted)}
.sw{width:13px;height:13px;border-radius:3px;flex:none}
.scroll{overflow-x:auto}
svg{display:block;width:100%;height:auto;min-width:640px}
.cap{font-size:.85rem;color:var(--muted);line-height:1.6;margin:14px 2px 4px;max-width:78ch}
table{border-collapse:collapse;width:100%;font-size:.85rem;margin:.4rem 0}
th,td{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);
  font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
th{font-size:.66rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);
  font-weight:600;border-bottom:1px solid var(--rule)}
th:first-child,td:first-child{text-align:left}
td.empty{color:var(--faint)}
.note{border-left:2px solid var(--rule);padding:3px 0 3px 18px;margin:1.6rem 0;
  color:var(--muted);font-size:.94rem;max-width:70ch}
.note strong{color:var(--ink-2)}
footer{margin-top:4.5rem;padding-top:1.5rem;border-top:1px solid var(--line);
  font-size:.78rem;color:var(--muted);font-family:var(--mono);line-height:1.85}
@media (max-width:640px){ header{padding-top:48px} .wrap{padding:0 16px 72px} }
</style>
"""

BODY = r"""<div class="wrap">
<header>
  <p class="eyebrow">Figure 1 &middot; matched budget of 48 &middot; n = 25 landscapes &times; 2 seeds</p>
  <h1>Four Terminal Decisions</h1>
  <p class="lede">One target, four ways of naming the answer, applied to the
  <strong>same campaigns</strong>. Nothing about the search changes between these bars
  &mdash; only which well gets reported.</p>
</header>

<div class="panel">
  <div class="legend" id="legend"></div>
  <div class="scroll"><svg id="fig" viewBox="0 0 900 620" role="img"
    aria-label="Regret under four terminal decisions, by arm and cell"></svg></div>
  <p class="cap">Lower is better. <strong>The ordering of the arms changes with the
  decision rule</strong> &mdash; that reversal, on identical campaigns, is the result.
  The naïve unconstrained bar for the classical arm is an extrapolation diagnostic, not
  its recommendation; the in-region bar is.</p>
</div>

<h2>The numbers</h2>
<div class="scroll"><table id="tbl">
  <thead><tr><th>cell</th><th>arm</th><th>tested-best</th><th>measured argmax</th>
    <th>naïve unconstrained</th><th>in-region / ridge</th></tr></thead>
  <tbody></tbody>
</table></div>

<div class="note"><strong>One cell is deliberately empty.</strong> No artefact in this
project stores an in-region recommendation for the adaptive arm at 48 wells: its design is
not confined to a sub-box, so &ldquo;in-region&rdquo; has no agreed meaning for it.
Filling that bar with the unconstrained number would quietly assert the two locators agree
for that arm. Empty cells stay empty.</div>

<div class="note">qLogNEI has no stored model recommendation either &mdash; the
design&times;surrogate factorial predates its promotion to co-primary. Its two locators
that <em>are</em> stored are shown; the others are blank for the same reason.</div>

<footer id="src"></footer>
</div>
"""

SCRIPT = r"""const NS='http://www.w3.org/2000/svg';
const el=(n,a)=>{const e=document.createElementNS(NS,n);
  for(const k in (a||{}))e.setAttribute(k,a[k]);return e;};
const tx=(e,s)=>{e.textContent=s;return e;};
const cv=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const ARMS=[['doe','--doe','classical DoE'],['qlogei','--qlogei','qLogEI'],
            ['qlognei','--qlognei','qLogNEI']];
const LOC=[['tested','tested-best'],['measured','measured argmax'],
           ['unconstrained','naïve unconstrained'],['inregion','in-region / ridge']];

function draw(){
  const s=document.getElementById('fig'); s.innerHTML='';
  const W=900,L=118,R=24,TOP=30;
  const cellH=140, groupGap=10;
  let vmax=0;
  D.cells.forEach(c=>ARMS.forEach(([a])=>LOC.forEach(([k])=>{
    const v=c.arms[a][k]; if(v!==null&&v>vmax) vmax=v;})));
  vmax=Math.ceil(vmax*10)/10;
  const sx=v=>L+(v/vmax)*(W-L-R);

  D.cells.forEach((c,ci)=>{
    const y0=TOP+ci*cellH;
    s.appendChild(tx(el('text',{x:0,y:y0+10,fill:cv('--ink'),'font-size':12.5,
      'font-family':cv('--mono'),'font-weight':600}),
      'd='+c.dim+'  σ='+c.sigma.toFixed(2)));
    LOC.forEach(([k,label],li)=>{
      const yy=y0+20+li*28;
      s.appendChild(tx(el('text',{x:L-10,y:yy+13,'text-anchor':'end',fill:cv('--muted'),
        'font-size':10.5,'font-family':cv('--mono')}), label));
      ARMS.forEach(([a,col],ai)=>{
        const v=c.arms[a][k], yb=yy+ai*6;
        if(v===null||v===undefined){
          if(ai===0) s.appendChild(tx(el('text',{x:L+6,y:yb+6,fill:cv('--faint'),
            'font-size':9.5,'font-family':cv('--mono')}),'not stored'));
          return;
        }
        s.appendChild(el('rect',{x:L,y:yb,width:Math.max(1,sx(v)-L),height:5,rx:1.5,
          fill:cv(col)}));
        s.appendChild(tx(el('text',{x:sx(v)+6,y:yb+5,fill:cv('--muted'),
          'font-size':9,'font-family':cv('--mono')}), v.toFixed(4)));
      });
    });
    if(ci<D.cells.length-1)
      s.appendChild(el('line',{x1:0,x2:W,y1:y0+cellH-groupGap,y2:y0+cellH-groupGap,
        stroke:cv('--line'),'stroke-width':1}));
  });
  for(let g=0;g<=vmax+1e-9;g+=0.1){
    const x=sx(g);
    s.appendChild(el('line',{x1:x,x2:x,y1:TOP-14,y2:TOP+D.cells.length*cellH-20,
      stroke:cv('--line'),'stroke-width':1,opacity:.6}));
    s.appendChild(tx(el('text',{x:x,y:TOP-20,'text-anchor':'middle',fill:cv('--faint'),
      'font-size':10,'font-family':cv('--mono')}), g.toFixed(1)));
  }
  s.appendChild(tx(el('text',{x:L,y:TOP+D.cells.length*cellH,fill:cv('--muted'),
    'font-size':10.5,'font-family':cv('--mono'),'letter-spacing':'.1em'}),
    'REGRET  →  worse'));

  const lg=document.getElementById('legend'); lg.innerHTML='';
  ARMS.forEach(([a,col,name])=>{
    const sp=document.createElement('span'), sw=document.createElement('i');
    sw.className='sw'; sw.style.background=cv(col);
    sp.appendChild(sw); sp.appendChild(document.createTextNode(name)); lg.appendChild(sp);
  });

  const tb=document.querySelector('#tbl tbody'); tb.innerHTML='';
  D.cells.forEach(c=>ARMS.forEach(([a,,name],ai)=>{
    const tr=document.createElement('tr');
    const vals=[ai===0?('d='+c.dim+' σ='+c.sigma.toFixed(2)):'', name]
      .concat(LOC.map(([k])=>{
        const v=c.arms[a][k]; return v===null||v===undefined?'—':v.toFixed(4);}));
    vals.forEach((v,i)=>{const td=document.createElement('td');
      td.textContent=v; if(v==='—') td.className='empty'; tr.appendChild(td);});
    tb.appendChild(tr);
  }));

  const f=document.getElementById('src');
  f.innerHTML='';
  f.appendChild(document.createTextNode('Every bar is derived by scripts/make_scoring_figure.py. Sources:'));
  f.appendChild(document.createElement('br'));
  Object.entries(D.sources).forEach(([k,v])=>{
    f.appendChild(document.createTextNode(k+' — '+v));
    f.appendChild(document.createElement('br'));
  });
}
draw();
if(window.matchMedia) matchMedia('(prefers-color-scheme:dark)').addEventListener('change', draw);
"""


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEAD + BODY + "\n<script>\nconst D = "
                   + json.dumps(data, indent=1) + ";\n" + SCRIPT + "\n</script>\n")

    # The figure's whole point is that the ordering changes with the locator. If it ever
    # stops changing, the figure is making a claim the data no longer supports.
    flips = 0
    for c in data["cells"]:
        m, u = c["arms"]["doe"]["measured"], c["arms"]["doe"]["unconstrained"]
        bm, bu = c["arms"]["qlogei"]["measured"], c["arms"]["qlogei"]["unconstrained"]
        if None in (m, u, bm, bu):
            continue
        if (m < bm) != (u < bu):
            flips += 1
    if not flips:
        raise AssertionError(
            "the winner no longer reverses between measured argmax and the unconstrained "
            "recommendation in any cell — this figure exists to show that reversal and "
            "would now be asserting something the data does not show.")

    print(f"  wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")
    print(f"  the winner reverses between locators in {flips} of {len(data['cells'])} cells")
    empty = sum(1 for c in data["cells"] for a in c["arms"].values()
                for v in a.values() if v is None)
    print(f"  {empty} cells left empty rather than interpolated")


if __name__ == "__main__":
    main()
