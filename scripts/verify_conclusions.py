"""Guard: the paper's numbers must reproduce from committed data.

Covers docs/SPADE-PAPER-ARGUMENT.md (the paper's argument) and
docs/SPADE-CONCLUSIONS-2026-08-29.md §1, which quote the same figures.

Run after ANY change to results/, to an analyser, or to the conclusions document. A
MISMATCH means the docs and the data have drifted apart -- which is exactly how a paper
ends up quoting a number no script produces.

    .venv/bin/python scripts/verify_conclusions.py

Exits non-zero if any claim fails to reproduce.
"""
import json, glob, math, random, statistics as st, importlib.util, re
from pathlib import Path
from scipy.stats import beta, spearmanr

ROOT = Path(__file__).resolve().parents[1]

def rows(pat):
    out = []
    for p in glob.glob(str(ROOT / pat)):
        raw = json.load(open(p))
        out += raw['rows'] if isinstance(raw, dict) and 'rows' in raw else raw
    return out

def boot(d, seed=0, n=8000):
    rng = random.Random(seed)
    m = sorted(sum(d[rng.randrange(len(d))] for _ in range(len(d)))/len(d) for _ in range(n))
    le = sum(1 for x in m if x <= 0)/n; ge = sum(1 for x in m if x >= 0)/n
    return st.mean(d), m[int(.025*n)], m[int(.975*n)], min(1.0, 2*min(le, ge))

ok = []
def check(name, got, want, tol):
    good = abs(got - want) <= tol
    ok.append(good)
    print(f"  [{'OK ' if good else 'MISMATCH'}] {name}: doc={want}  recomputed={got:.6f}")

def require(name, condition, detail=""):
    ok.append(bool(condition))
    print(f"  [{'OK ' if condition else 'REFUSED'}] {name}{(': ' + detail) if detail else ''}")

def exact_grid(path, expected):
    raw = json.loads(path.read_text())
    data = raw.get("rows", raw) if isinstance(raw, dict) else raw
    keys = [(r["arm"], r["family"], int(r["seed"]), float(r["p_value"]),
             float(r["inflation_c"])) for r in data]
    return len(keys) == len(set(keys)) and set(keys) == expected

# --- claim 1: SPADE R=5 vs qLogNEI R=10 regret ---
lc = {}
for r in rows('results/lc-*.json'):
    g = r.get('regret')
    if g is not None and not (isinstance(g, float) and g != g):
        lc[(r['arm'], r['rounds'], r['family'], r['seed'])] = float(g)
keys = [(f,s) for (a,rr,f,s) in lc if (a,rr)==("spade",5) and ("qlognei",10,f,s) in lc]
d = [lc[("spade",5,f,s)] - lc[("qlognei",10,f,s)] for f,s in keys]
m1, lo1, hi1, _ = boot(d, seed=7)
print("CLAIM 1 -- SPADE R=5 vs qLogNEI R=10 on regret")
check("mean", m1, 0.0016, 0.0004); check("CI lo", lo1, -0.0184, 0.002)
check("CI hi", hi1, 0.0208, 0.002); check("n", len(d), 160, 0)
print(f"  half-width = {(hi1-lo1)/2:.4f} (doc says 0.0196 < SESOI 0.0200)")

# --- claim 5: TAU-1 rho ---
spec = importlib.util.spec_from_file_location("t", "scripts/analyse_tau_sweep.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
cells, diff = T.load([f"results/tau-{f}.json" for f in T.FAMILIES])
fams = sorted({k[1] for k in cells}); ps = sorted({k[3] for k in cells}, reverse=True)
xs, ys = [], []
for f in fams:
    for p in ps:
        _lb, _n, ar = T.pooled(cells, lambda k, f=f, p=p: k[1]==f and k[3]==p and k[4]==1.0)
        ms = diff.get((f,p), float('nan'))
        if ms == ms: xs.append(ms); ys.append(ar)
rho, _ = spearmanr(xs, ys)
print("\nCLAIM 5 -- margin/sd governs certification")
check("Spearman rho", rho, 0.9801, 0.0005); check("cells", len(xs), 25, 0)

# --- claim 4: hill certifies ---
def cp(k, n): return 0.0 if n==0 or k==0 else float(beta.ppf(0.05,k,n-k+1))
n=k=0
for (a,f,s,p,c),(ne,good,_v) in cells.items():
    if a=="spade" and f=="hill" and p==0.70 and c==1.0 and ne:
        n+=1; k+=good
print("\nCLAIM 4 -- hill certifies at prevalence 0.70")
check("answered", n, 40, 0); check("contained", k, 40, 0); check("LB", cp(k,n), 0.9278, 0.0002)

# --- claim 6: SPADE vs one-shot lhs ---
la = {}
for r in rows('results/la-*.json'):
    g = r.get('regret')
    if g is not None and not (isinstance(g, float) and g != g):
        la[(r['arm'], r['family'], r['seed'])] = float(g)
keys = [(f,s) for (a,rr,f,s) in lc if (a,rr)==("spade",3) and ("lhs",f,s) in la]
d6 = [lc[("spade",3,f,s)] - la[("lhs",f,s)] for f,s in keys]
m6, lo6, hi6, _ = boot(d6, seed=9)
print("\nCLAIM 6 -- SPADE R=3 vs one-shot lhs")
check("mean", m6, -0.0783, 0.004)

paper = (ROOT / "docs" / "SPADE-PAPER-ARGUMENT.md").read_text().lower()
conclusions = (ROOT / "docs" / "SPADE-CONCLUSIONS-2026-08-29.md").read_text().lower()
print("\nCLAIM INTEGRITY -- TT, historical DC, and publication language")
families = {"ackley", "hartmann6", "hill", "levy", "rosenbrock"}
arms = {"spade", "spade_tau", "qlognei"}
expected = {(a, f, s, p, c) for a in arms for f in families for s in range(32)
            for p in (0.3, 0.7) for c in (1.0, 1.5, 2.0, 3.0)}
tt_paths = [ROOT / "results" / f"tt-{f}.json" for f in sorted(families)]
require("TT files present", all(p.exists() for p in tt_paths))
if all(p.exists() for p in tt_paths):
    for path in tt_paths:
        require(f"TT exact grid {path.name}", exact_grid(path, {(a, path.stem[3:], s, p, c)
                for a in arms for s in range(32) for p in (0.3, 0.7)
                for c in (1.0, 1.5, 2.0, 3.0)}))

audit_path = ROOT / "results" / "tt-activation-audit.json"
require("TT activation audit complete", audit_path.exists())
if audit_path.exists():
    audit = json.loads(audit_path.read_text())
    require("TT activation totals", audit.get("status") == "COMPLETE" and
            audit.get("active_rounds") == 206 and audit.get("total_rounds") == 640 and
            audit.get("campaigns_active_all_rounds") == 20 and audit.get("total_campaigns") == 160)
    records = audit.get("records", [])
    require("TT activation records unique", len(records) == len({(r.get("family"), r.get("seed"), r.get("round")) for r in records}))

hist_dir = ROOT / "results" / "historical-dc-constant-yvar"
hist_files = [hist_dir / f"dc-{f}.json" for f in sorted(families)]
readme = (hist_dir / "README.md").read_text().lower() if (hist_dir / "README.md").exists() else ""
require("historical DC artifacts present", all(p.exists() for p in hist_files))
require("historical DC labelled non-confirmatory", "historical" in readme and "non-confirmatory" in readme)
if all(p.exists() for p in hist_files):
    # Historical grid is checked for integrity only; its values are explicitly not inferential.
    h_expected = {(a, f, s, p, c) for a in {"doe", "doe_unscreened", "spade", "qlognei"}
                  for f in families for s in range(32) for p in (0.3, 0.7)
                  for c in (1.0, 1.5, 2.0, 3.0)}
    for path in hist_files:
        family = path.stem[3:]
        require(f"historical DC exact grid {path.name}", exact_grid(path,
                {(a, family, s, p, c) for a in {"doe", "doe_unscreened", "spade", "qlognei"}
                 for s in range(32) for p in (0.3, 0.7) for c in (1.0, 1.5, 2.0, 3.0)}))

dc2 = ROOT / "results" / "dc2-doe-certificate.json"
if dc2.exists():
    try:
        d2 = json.loads(dc2.read_text())
        require("DC2 complete before current conclusions", d2.get("status") == "COMPLETE",
                "incomplete artifact cannot support a conclusion")
        require("DC2 provenance present", bool(d2.get("spec_sha256")) and bool(d2.get("runner_sha256")))
    except (OSError, json.JSONDecodeError):
        require("DC2 valid JSON", False)
else:
    print("  [OK ] no DC2 conclusion: corrected experiment has not been run")

require("bounded regret terminology", "no detectable difference" in paper and
        "matches bo" not in paper and "ties bo" not in paper)
require("no uniqueness claim", "only arm with containment 1.0000" not in paper and
        "only method that returns an operating region you can trust" not in paper)
require("DoE historical caveat", "variance-corrected replication" in paper and
        "historical" in paper)
require("TT mixed activation caveat", "not adopted" in conclusions and "mixed-activation" in conclusions)

print(f"\n===== {sum(ok)}/{len(ok)} checks passed =====")
print("checked against committed LC, TT, historical DC artifacts, and claim documents")

import sys
sys.exit(0 if all(ok) else 1)
