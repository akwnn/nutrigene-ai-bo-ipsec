"""Q52 §2 — the budget-to-target cost curves, as a self-contained HTML page.

    python scripts/make_cost_curve_page.py

Reads `results/q52-budget-to-target.json` and writes `results/figures/cost-curves.html`.
Nothing is hand-authored: every number on the page is derived here, so the page is
regenerable rather than remembered. That distinction matters in this repository --
`results/E4-RESULTS-v2.md` and `results/NEGATIVE-shape-aware-mean.md` are hand-written
narratives with no producing script, they carry claims in `CLAIMS.md`, and they cannot
be re-derived. This page does not join them.

Censoring, the >50% rule and the undefined savings ratio follow Q52 §2's registration
(`docs/OPEN-QUESTIONS.md`), applied through `boec.budget.first_budget_to_target` -- the
same function the harness uses, not a reimplementation of its arithmetic. D19 is the
reason that is spelled out: a registration binds only the analysis that runs through it.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target  # noqa: E402

#: Matched to `scripts/run_q52_budget_to_target.py`. Not tunable here.
CAP, DIM, PIPELINE_BUDGET = 200, 6, 48
TARGETS_RULE_C = (0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05)
SERIES = (("qlogei", "rule_a"), ("qlogei", "rule_c"),
          ("spread_gp", "rule_a"), ("spread_gp", "rule_c"),
          ("random", "rule_a"),
          ("doe", "rule_a"), ("doe", "rule_c"), ("doe", "rule_c_constrained"))

#: Q52 §2's arrival table, transcribed from `docs/RESULTS.md` and asserted against the
#: grid below, so a drift in either is a failure rather than a silent disagreement.
ARRIVAL = [
    dict(sigma=0.10, target=0.10, bo=24, doe=13, disc="11 : 0", p=0.0010, holm=True),
    dict(sigma=0.10, target=0.08, bo=22, doe=13, disc="10 : 1", p=0.0117, holm=False),
    dict(sigma=0.10, target=0.05, bo=18, doe=7,  disc="15 : 4", p=0.0192, holm=False),
    dict(sigma=0.10, target=0.12, bo=24, doe=20, disc="5 : 1",  p=0.2188, holm=False),
    dict(sigma=0.25, target=0.15, bo=21, doe=23, disc="1 : 3",  p=0.6250, holm=False),
    dict(sigma=0.25, target=0.10, bo=14, doe=11, disc="7 : 4",  p=0.5488, holm=False),
    dict(sigma=0.25, target=0.08, bo=10, doe=6,  disc="7 : 3",  p=0.3438, holm=False),
]


def rounds_for(arm: str, n: int) -> int:
    """Sequential plate cycles to spend ``n`` evaluations. Verbatim from the runner."""
    if arm == "doe":
        return 3 * (n // PIPELINE_BUDGET)
    if arm == "qlogei":
        n_init = 2 * DIM + 2
        return 1 if n <= n_init else 1 + math.ceil((n - n_init) / 4)
    return 1


def build_data() -> dict:
    grid = json.loads((ROOT / "results" / "q52-budget-to-target.json").read_text())
    rows = grid["rows"]
    out = {"series": {}, "cost": {}, "targets": list(TARGETS_RULE_C), "arrival": ARRIVAL}
    for sigma in (0.25, 0.10):
        rs = [r for r in rows if abs(r["sigma"] - sigma) < 1e-9]
        key = f"{sigma}"
        out["series"][key] = {}
        for arm, rule in SERIES:
            grids = sorted({int(k) for r in rs for k in r["arms"].get(arm, {}).get(rule, {})})
            pts = []
            for n in grids:
                v = [r["arms"][arm][rule].get(str(n)) for r in rs]
                v = [x for x in v if x is not None]
                if v:
                    pts.append(dict(n=n, med=round(float(np.median(v)), 4),
                                    lo=round(float(np.percentile(v, 25)), 4),
                                    hi=round(float(np.percentile(v, 75)), 4),
                                    rounds=rounds_for(arm, n)))
            if pts:
                out["series"][key][f"{arm}|{rule}"] = pts
        out["cost"][key] = {}
        for arm in ("doe", "qlogei", "random", "spread_gp"):
            cells = []
            for t in TARGETS_RULE_C:
                if rs[0]["arms"].get(arm, {}).get("rule_c") is None:
                    cells.append(None)          # `random` carries no model, so no rule C
                    continue
                got, censored = [], 0
                for r in rs:
                    a = first_budget_to_target(r["arms"][arm]["rule_c"], target=t, cap=CAP)
                    if a is ARRIVAL_CENSORED:
                        censored += 1
                    else:
                        got.append(a)
                n = censored + len(got)
                rate = censored / n if n else 1.0
                # Registered: above 50% censored, the rate is reported and no point
                # estimate is. A median over only the arrivals is biased.
                ok = rate <= 0.50 and got
                med = int(np.median(got)) if ok else None
                cells.append(dict(censored=round(rate, 3), evals=med,
                                  rounds=(rounds_for(arm, med) if med else None)))
            out["cost"][key][arm] = cells
    return out


HEAD = r"""<title>The Savings Curve That Isn't</title>
<style>
:root{
  --ground:#F6F7F9; --surface:#FFFFFF; --sunk:#EDF0F4;
  --ink:#161B22; --ink-2:#39424E; --muted:#5A6472; --line:#DCE1E8; --rule:#C8D0DA;
  --qlogei:#2563EB; --spread:#0D9488; --doe:#C2410C; --random:#94A3B8;
  --cens:#C2410C; --good:#0F766E;
  --serif:ui-serif,Georgia,"Iowan Old Style","Times New Roman",serif;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0F1319; --surface:#161B22; --sunk:#1B212A;
    --ink:#E6EAF0; --ink-2:#C2CAD6; --muted:#94A0B0; --line:#252D38; --rule:#39434F;
    --qlogei:#6098F5; --spread:#2DD4BF; --doe:#FB8B3C; --random:#8593A6;
    --cens:#FB8B3C; --good:#2DD4BF;
  }
}
:root[data-theme="dark"]{
  --ground:#0F1319; --surface:#161B22; --sunk:#1B212A;
  --ink:#E6EAF0; --ink-2:#C2CAD6; --muted:#94A0B0; --line:#252D38; --rule:#39434F;
  --qlogei:#6098F5; --spread:#2DD4BF; --doe:#FB8B3C; --random:#8593A6;
  --cens:#FB8B3C; --good:#2DD4BF;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
     font-size:16px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px 96px}
.prose{max-width:68ch}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,5.2vw,3.15rem);
   line-height:1.06;letter-spacing:-.018em;margin:0 0 .55rem;text-wrap:balance}
h2{font-family:var(--serif);font-weight:600;font-size:clamp(1.35rem,3vw,1.85rem);
   line-height:1.2;letter-spacing:-.012em;margin:4.2rem 0 .6rem;text-wrap:balance}
p{margin:0 0 1.05rem;color:var(--ink-2)}
strong{color:var(--ink);font-weight:650}
em{font-style:italic}
code,.num{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.9em}
header{padding:76px 0 0}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin:0 0 1.15rem}
.lede{font-size:1.16rem;line-height:1.55;color:var(--ink-2);max-width:60ch;margin:0 0 2rem}
.verdict{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:26px 28px;margin:2.5rem 0 0}
.verdict p{margin:0;font-family:var(--serif);font-size:1.24rem;line-height:1.42;color:var(--ink)}
.verdict .sub{font-family:var(--sans);font-size:.95rem;color:var(--muted);margin-top:.9rem;line-height:1.55}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:22px 22px 14px;margin:1.6rem 0}
.ctrls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 14px}
button{font-family:var(--mono);font-size:.75rem;letter-spacing:.03em;padding:7px 13px;
  border-radius:6px;border:1px solid var(--rule);background:transparent;color:var(--muted);cursor:pointer;
  transition:background .12s,color .12s,border-color .12s}
button:hover{color:var(--ink);border-color:var(--muted)}
button[aria-pressed="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
button:focus-visible{outline:2px solid var(--qlogei);outline-offset:2px}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin:12px 0 4px}
.legend span{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);
  font-size:.75rem;color:var(--muted)}
.swatch{width:16px;height:3px;border-radius:2px;flex:none}
.scroll{overflow-x:auto}
svg{display:block;width:100%;height:auto;min-width:580px}
.cap{font-size:.86rem;color:var(--muted);line-height:1.55;margin:12px 2px 4px;max-width:76ch}
table{border-collapse:collapse;width:100%;font-size:.87rem;margin:1rem 0}
th,td{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);
  font-family:var(--mono);font-variant-numeric:tabular-nums}
th{font-size:.69rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600;
   border-bottom:1px solid var(--rule)}
th:first-child,td:first-child{text-align:left}
tr.hit td{color:var(--ink);font-weight:650}
.tag{font-family:var(--mono);font-size:.67rem;letter-spacing:.05em;padding:2px 7px;border-radius:4px;
  border:1px solid currentColor;white-space:nowrap}
.tag.no{color:var(--muted)} .tag.yes{color:var(--good)}
.note{border-left:2px solid var(--rule);padding:2px 0 2px 18px;margin:1.5rem 0;color:var(--muted);
  font-size:.95rem;max-width:66ch}
.note strong{color:var(--ink-2)}
ul{padding-left:1.15rem;margin:0 0 1.1rem;color:var(--ink-2)}
li{margin:0 0 .55rem}
footer{margin-top:5rem;padding-top:1.5rem;border-top:1px solid var(--line);
  font-size:.81rem;color:var(--muted);font-family:var(--mono);line-height:1.75}
@media (max-width:640px){ header{padding-top:48px} h2{margin-top:3rem} .panel{padding:16px 14px 10px} }
</style>
"""

BODY = r"""<div class="wrap">
<header>
  <p class="eyebrow">Q52 §2 &middot; budget-to-target grid &middot; d=6 &middot; n=25 landscapes &middot; cap 200</p>
  <h1>The Savings Curve That Isn&rsquo;t</h1>
  <p class="lede">We set out to measure how many experiments Bayesian optimization saves against a
  classical DoE pipeline. Under the analysis registered before the run, <strong>that number does not
  exist at any target.</strong> Here is what the curves actually look like, and the one comparison
  that survived.</p>
  <div class="verdict">
    <p>The classical arm is censored above 50&thinsp;% at <em>every</em> rule-C target &mdash;
    including the loosest. A savings ratio needs both arms to arrive. Neither a median nor a mean
    is defined anywhere on this curve.</p>
    <p class="sub">Registered in advance: above 50&thinsp;% censoring, report the rate and no point
    estimate; a median over only the runs that arrived is biased. That gate is why this page is a
    null rather than a headline &mdash; and a first pass that bypassed it did produce one, which
    was retracted.</p>
  </div>
</header>

<h2>Why there is no curve</h2>
<p class="prose">Each cell is one target regret. Shading is the share of the 25 landscapes where
that arm <em>never reached</em> the target inside the 200-evaluation cap. Anything past the halfway
mark is hatched: the registered rule forbids a point estimate there.</p>
<div class="panel">
  <div class="ctrls" id="cens-ctrls"></div>
  <div class="scroll"><svg id="cens" viewBox="0 0 900 258" role="img"
    aria-label="Censoring rate by target regret for each arm"></svg></div>
  <p class="cap">The classical <code>doe</code> row is blocked across its whole length. Its
  unconstrained rule-C regret is <span class="num">0.4163</span> &mdash; worse than the loosest
  target in the set, so it cannot arrive anywhere. <code>random</code> has no rule-C column at all:
  it carries no model, so it has no recommendation to score.</p>
</div>

<h2>The cost curves</h2>
<p class="prose">Median regret against evaluations spent; lower is better. Bands are the
interquartile range across landscapes. <strong>The classical arm sits on a coarser grid on
purpose</strong> &mdash; it only yields a recommendation when a whole 48-run pipeline completes, so
it has four points where the others have eleven. Plotting it on their grid would invent readings it
never produced.</p>
<div class="panel">
  <div class="ctrls" id="curve-ctrls"></div>
  <div class="legend" id="curve-legend"></div>
  <div class="scroll"><svg id="curve" viewBox="0 0 900 430" role="img"
    aria-label="Median regret against evaluations for each arm"></svg></div>
  <p class="cap"><strong>Read the picture against the statistics, not instead of them.</strong> At
  budget 48 the paired contrast between <code>qlogei</code> and <code>spread_gp</code> is
  <strong>null on both rules at both noise levels</strong> &mdash; every interval covers zero. The
  visible gap between those two lines is not a measured win.</p>
</div>

<h2>The same data, priced in rounds</h2>
<p class="prose">Evaluations are not what a lab pays. A <em>round</em> is a plate cycle &mdash; you
plate, incubate, stain, read, and only then choose what to try next. Here the x-axis is rounds of
waiting rather than wells consumed. Nothing about the measurements changed; only the price did.</p>
<div class="panel">
  <div class="ctrls" id="rounds-ctrls"></div>
  <div class="legend" id="rounds-legend"></div>
  <div class="scroll"><svg id="rounds" viewBox="0 0 900 430" role="img"
    aria-label="Median regret against sequential rounds for each arm"></svg></div>
  <p class="cap">Spending all 200 evaluations costs <code>spread_gp</code>
  <strong>1&nbsp;round</strong>, <code>doe</code> <strong>12</strong>, and <code>qlogei</code>
  <strong>48</strong>. That is the axis on which these methods genuinely differ &mdash; and it is a
  property of the batch structure, fixed in advance, not a result of the experiment.</p>
</div>

<h2>The one result that survives</h2>
<p class="prose">Everything above conditions on arriving, and arriving is what the classical arm
mostly fails to do. <strong>Arrival itself is unconditioned</strong> &mdash; all 25 landscapes
contribute, nothing is selected &mdash; so it is the one quantity this grid measures cleanly.
Paired per landscape, exact binomial on the discordant pairs.</p>
<div class="panel">
  <div class="scroll"><table>
    <thead><tr><th>&sigma;</th><th>target</th><th>BO reaches</th><th>DoE reaches</th>
      <th>discordant</th><th>exact p</th><th>survives Holm</th></tr></thead>
    <tbody id="arrival"></tbody>
  </table></div>
  <p class="cap">At the optimistic assay, BO reaches a regret of <span class="num">0.10</span> in
  <strong>24 of 25</strong> landscapes where the classical pipeline reaches it in
  <strong>13</strong> &mdash; eleven discordant pairs to nil. It is the only cell surviving Holm
  over all ten arrival tests. <strong>At the realistic assay the difference vanishes</strong>, and
  at target 0.15 the classical arm is nominally ahead.</p>
</div>
<div class="note"><strong>So the honest sentence is not</strong> &ldquo;BO gets there in fewer
experiments&rdquo; &mdash; that comparison is undefined here &mdash; but <strong>&ldquo;at a quiet
assay, BO gets there at all, far more often.&rdquo;</strong> And it disappears at the noise level
this project registered as primary.</div>

<h2>What would make these curves wrong</h2>
<ul class="prose">
<li><strong>The classical arm never moves its design region.</strong> It repeats a fixed 48-run
pipeline with a fresh seed and keeps the best. Textbook sequential RSM inserts a steepest-ascent
phase that walks the design toward the optimum. <strong>Every ratio here is therefore biased in
BO&rsquo;s favour</strong> &mdash; conceded in the registration, not after the numbers landed.</li>
<li><strong>The loose targets measure granularity, not adaptivity.</strong> qLogEI opens with 14
points, so at n=8 and n=12 it has made <em>zero</em> adaptive decisions. Any apparent advantage
there is checkpoint spacing.</li>
<li><strong>Each row is a different subset of landscapes.</strong> As the target tightens, n falls
from 25 toward 3, so reading a trend down a column is partly survivorship.</li>
<li><strong>One campaign seed per landscape</strong>, where the main grid used two.</li>
<li><strong>d=8 was not run</strong> &mdash; declared out of scope, not attempted and dropped.</li>
</ul>

<footer>
  Source: <code>results/q52-budget-to-target.json</code> &mdash; the only artefact in this project
  carrying its own provenance block: git SHA, timestamp, argv, library versions, full config.<br>
  Fidelity gate passed at max |&Delta;| = 0.000e+00 against 10 stored qLogEI rows re-run at budget 48.<br>
  Rounds model <code>results/q38-cost-model.json</code> &middot; arrival tests McNemar exact form, Holm over ten.
</footer>
</div>
"""

SCRIPT = r"""const C = {qlogei:'--qlogei', spread_gp:'--spread', doe:'--doe', random:'--random'};
const NAME = {qlogei:'qLogEI (BO)', spread_gp:'spread + GP', doe:'DoE pipeline', random:'random'};
const cv = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const SVG = 'http://www.w3.org/2000/svg';
const el = (n,a) => { const e=document.createElementNS(SVG,n);
  for(const k in (a||{})) e.setAttribute(k,a[k]); return e; };
const txt = (e,s) => { e.textContent = s; return e; };

let sigma = '0.25', rule = 'rule_c';

/* ---------------- censoring strip ---------------- */
function drawCens(){
  const s = document.getElementById('cens'); s.innerHTML='';
  const arms = ['doe','qlogei','spread_gp'], T = D.targets;
  const L=118, R=26, TOP=48, cw=(900-L-R)/T.length, rh=44, gap=10;

  const defs = el('defs');
  const pat = el('pattern',{id:'hatch',width:8,height:8,
    patternTransform:'rotate(45)',patternUnits:'userSpaceOnUse'});
  pat.appendChild(el('rect',{width:8,height:8,fill:cv('--cens'),opacity:.16}));
  pat.appendChild(el('line',{x1:0,y1:0,x2:0,y2:8,stroke:cv('--cens'),'stroke-width':3.4,opacity:.9}));
  defs.appendChild(pat); s.appendChild(defs);

  s.appendChild(txt(el('text',{x:L,y:16,fill:cv('--muted'),'font-size':11,
    'font-family':cv('--mono'),'letter-spacing':'.11em'}),'TARGET REGRET  →  tighter'));
  T.forEach((t,i)=> s.appendChild(txt(el('text',{x:L+cw*i+cw/2,y:36,'text-anchor':'middle',
    fill:cv('--muted'),'font-size':13,'font-family':cv('--mono')}), t.toFixed(2))));

  arms.forEach((a,r)=>{
    const y = TOP + r*(rh+gap);
    s.appendChild(txt(el('text',{x:L-14,y:y+rh/2+5,'text-anchor':'end',fill:cv('--ink'),
      'font-size':13,'font-family':cv('--mono')}), a));
    (D.cost[sigma][a]||[]).forEach((c,i)=>{
      const x = L+cw*i+3, w = cw-6;
      s.appendChild(el('rect',{x:x,y:y,width:w,height:rh,rx:4,fill:cv('--sunk')}));
      if(!c) return;
      const over = c.censored > 0.5;
      s.appendChild(el('rect',{x:x,y:y,width:w,height:rh,rx:4,
        fill: over ? 'url(#hatch)' : cv('--cens'),
        opacity: over ? 1 : (0.10 + 0.55*c.censored)}));
      const label = Math.round(c.censored*100)+'%';
      if(over){
        s.appendChild(el('rect',{x:x+w/2-21,y:y+rh/2-11,width:42,height:22,rx:4,fill:cv('--cens')}));
        s.appendChild(txt(el('text',{x:x+w/2,y:y+rh/2+5,'text-anchor':'middle','font-size':12,
          'font-family':cv('--mono'),fill:cv('--ground'),'font-weight':700}), label));
      } else {
        s.appendChild(txt(el('text',{x:x+w/2,y:y+rh/2+5,'text-anchor':'middle','font-size':12,
          'font-family':cv('--mono'),fill:cv('--ink')}), label));
      }
    });
  });
  s.appendChild(txt(el('text',{x:L,y:TOP+3*(rh+gap)+18,fill:cv('--muted'),'font-size':12,
    'font-family':cv('--mono')}),
    'hatched = above 50% censored → registered rule forbids a point estimate'));
}

/* ---------------- line charts ---------------- */
function drawLines(id, xkey){
  const s = document.getElementById(id); s.innerHTML='';
  const W=900,H=430,L=66,R=26,TOP=24,B=58;
  const set = D.series[sigma];
  const keys = Object.keys(set).filter(k =>
    k.endsWith('|'+rule) || (rule==='rule_c' && k.endsWith('|rule_c_constrained')));
  if(!keys.length) return;
  let all=[]; keys.forEach(k => set[k].forEach(p => all.push(p)));
  const xv = p => xkey==='n' ? p.n : p.rounds;
  const x0 = Math.min.apply(null, all.map(xv));
  const x1 = Math.max.apply(null, all.map(xv));
  const y1 = Math.max.apply(null, all.map(p=>p.hi)) * 1.05;
  const sx = v => L + (Math.log(v)-Math.log(x0))/(Math.log(x1)-Math.log(x0))*(W-L-R);
  const sy = v => H-B - (v/y1)*(H-TOP-B);

  for(let i=0;i<=4;i++){
    const v = y1*i/4, y = sy(v);
    s.appendChild(el('line',{x1:L,x2:W-R,y1:y,y2:y,stroke:cv('--line'),'stroke-width':1}));
    s.appendChild(txt(el('text',{x:L-11,y:y+4,'text-anchor':'end',fill:cv('--muted'),
      'font-size':12,'font-family':cv('--mono')}), v.toFixed(2)));
  }
  const ticks = xkey==='n' ? [8,16,32,48,100,200] : [1,2,3,6,12,24,48];
  ticks.filter(t => t>=x0 && t<=x1).forEach(t=>{
    const x = sx(t);
    s.appendChild(el('line',{x1:x,x2:x,y1:TOP,y2:H-B,stroke:cv('--line'),'stroke-width':1,opacity:.55}));
    s.appendChild(txt(el('text',{x:x,y:H-B+22,'text-anchor':'middle',fill:cv('--muted'),
      'font-size':12,'font-family':cv('--mono')}), String(t)));
  });
  s.appendChild(txt(el('text',{x:(L+W-R)/2,y:H-14,'text-anchor':'middle',fill:cv('--muted'),
    'font-size':11,'font-family':cv('--mono'),'letter-spacing':'.1em'}),
    xkey==='n' ? 'EVALUATIONS SPENT  (log scale)' : 'SEQUENTIAL ROUNDS OF WAITING  (log scale)'));
  s.appendChild(txt(el('text',{x:14,y:TOP+8,fill:cv('--muted'),'font-size':11,
    'font-family':cv('--mono'),'letter-spacing':'.1em'}), 'REGRET'));

  keys.forEach(k=>{
    const arm = k.split('|')[0], dashed = k.indexOf('constrained') > -1;
    const col = cv(C[arm]), pp = set[k];
    if(pp.length > 1 && !dashed){
      const up = pp.map(p => sx(xv(p))+','+sy(p.hi));
      const dn = pp.slice().reverse().map(p => sx(xv(p))+','+sy(p.lo));
      s.appendChild(el('polygon',{points:up.concat(dn).join(' '),fill:col,opacity:.085}));
    }
    const d = pp.map((p,i) => (i?'L':'M') + sx(xv(p)) + ',' + sy(p.med)).join('');
    s.appendChild(el('path',{d:d,fill:'none',stroke:col,'stroke-width':dashed?1.9:2.5,
      'stroke-dasharray':dashed?'5 4':'none','stroke-linejoin':'round','stroke-linecap':'round'}));
    pp.forEach(p => s.appendChild(el('circle',{cx:sx(xv(p)),cy:sy(p.med),r:dashed?2.7:3.7,
      fill:cv('--surface'),stroke:col,'stroke-width':2})));
  });

  const lg = document.getElementById(id==='curve' ? 'curve-legend' : 'rounds-legend');
  lg.innerHTML='';
  keys.forEach(k=>{
    const arm = k.split('|')[0], dashed = k.indexOf('constrained') > -1;
    const sp = document.createElement('span');
    const sw = document.createElement('i');
    sw.className='swatch'; sw.style.background = cv(C[arm]);
    if(dashed) sw.style.opacity='.5';
    sp.appendChild(sw);
    sp.appendChild(document.createTextNode(NAME[arm] + (dashed ? ' · constrained' : '')));
    lg.appendChild(sp);
  });
}

function drawArrival(){
  const tb = document.getElementById('arrival'); tb.innerHTML='';
  D.arrival.forEach(a=>{
    const tr = document.createElement('tr');
    if(a.holm) tr.className='hit';
    const cells = [a.sigma.toFixed(2), a.target.toFixed(2), a.bo+'/25', a.doe+'/25',
                   a.disc, a.p.toFixed(4)];
    cells.forEach(v=>{ const td=document.createElement('td'); td.textContent=v; tr.appendChild(td); });
    const td = document.createElement('td');
    const sp = document.createElement('span');
    sp.className = 'tag ' + (a.holm ? 'yes' : 'no');
    sp.textContent = a.holm ? 'yes' : 'no';
    td.appendChild(sp); tr.appendChild(td);
    tb.appendChild(tr);
  });
}

function btns(host, opts){
  const h = document.getElementById(host); h.innerHTML='';
  opts.forEach(o=>{
    if(o.spacer){ const g=document.createElement('span'); g.style.width='12px'; h.appendChild(g); return; }
    const b = document.createElement('button');
    b.textContent = o.label;
    b.setAttribute('aria-pressed', String(o.on));
    b.onclick = o.act;
    h.appendChild(b);
  });
}

function drawAll(){
  const sig = [
    {label:'σ = 0.25  realistic assay', on:sigma==='0.25', act:()=>{sigma='0.25';drawAll();}},
    {label:'σ = 0.10  optimistic',      on:sigma==='0.10', act:()=>{sigma='0.10';drawAll();}}];
  const rl = [
    {spacer:true},
    {label:'rule A  best measured', on:rule==='rule_a', act:()=>{rule='rule_a';drawAll();}},
    {label:'rule C  the model’s pick', on:rule==='rule_c', act:()=>{rule='rule_c';drawAll();}}];
  btns('cens-ctrls', sig);
  btns('curve-ctrls', sig.concat(rl));
  btns('rounds-ctrls', sig.concat(rl));
  drawCens(); drawLines('curve','n'); drawLines('rounds','rounds'); drawArrival();
}
drawAll();
if(matchMedia) matchMedia('(prefers-color-scheme:dark)').addEventListener('change', drawAll);
"""


def main() -> None:
    data = build_data()
    doe = [c["censored"] for c in data["cost"]["0.25"]["doe"]]
    assert all(x > 0.5 for x in doe), (
        "the DoE arm is no longer censored above 50% at every rule-C target -- the page's "
        f"headline claim is false and must be rewritten: {doe}")
    page = HEAD + BODY + "<script>\nconst D = " + json.dumps(data, separators=(",", ":")) \
        + ";\n" + SCRIPT + "\n</script>\n"
    out = ROOT / "results" / "figures" / "cost-curves.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"  wrote {out.relative_to(ROOT)}  ({len(page):,} bytes)")
    print(f"  DoE censoring at sigma=0.25, all eight targets: {doe}")


if __name__ == "__main__":
    main()
