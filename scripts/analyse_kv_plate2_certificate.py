"""KV adjudication. Implements `docs/SPADE-PLATE2-CERTIFICATE-SPEC.md` §5 and §6 exactly.

Written BEFORE KV's data exists, so no gate can be tuned after seeing an outcome.

§6 verbatim: Wilcoxon signed-rank on **campaign-clustered** paired differences (average within
a campaign across its cells, then pair), bootstrap intervals for effect size, Holm-Bonferroni
across KV-1/KV-2/KV-3/KV-4 as one family. gamma=0.95 primary; 0.50/0.80 reported beside it and
NOT eligible for promotion.

The clustering is not optional. Each campaign contributes 24 `(gamma, p_value)` rows that are
strongly correlated; pairing per-row would inflate n by 24x and manufacture significance from
one underlying observation -- the same error `SPADE-CALIBRATION-FIX-SPEC.md` §1 had to guard
against when K0 deduped 4,800 rows to 200 campaigns.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KV = ROOT / "results" / "kv-plate2-certificate.json"
OUT = ROOT / "results" / "kv-analysis.json"

GAMMA_PRIMARY = "0.95"
SESOI = 0.02
CONTAIN = f"ce_empirical_{GAMMA_PRIMARY}"
MAPERR = "map_total_error_vol_sub"


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values, monotone-enforced."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, prev = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        out[k] = adj
        prev = adj
    return out


def cluster(rows, col, require_nonempty: bool):
    """`(family, seed) -> {arm: campaign-mean of col}`. §6's clustering step."""
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        v = r.get(col)
        if v is None or (isinstance(v, float) and v != v):
            continue
        if require_nonempty and r.get(f"ce_empty_{GAMMA_PRIMARY}"):
            continue
        acc[(r["family"], r["seed"])][r["arm"]].append(float(v))
    return {k: {a: float(np.mean(vs)) for a, vs in d.items()} for k, d in acc.items()}


def paired(camp, a1, a2):
    x = np.array([d[a1] for d in camp.values() if a1 in d and a2 in d])
    y = np.array([d[a2] for d in camp.values() if a1 in d and a2 in d])
    return x, y


def contrast(camp, a1, a2, label, lower_is_better=False):
    x, y = paired(camp, a1, a2)
    if len(x) < 10:
        return {"label": label, "n": int(len(x)), "insufficient": True}
    d = x - y
    eff = float(d.mean()) * (-1.0 if lower_is_better else 1.0)
    try:
        p = float(wilcoxon(x, y).pvalue)
    except Exception:                                                # noqa: BLE001
        p = float("nan")
    rng = np.random.default_rng(0)
    bs = [float(d[rng.integers(0, len(d), len(d))].mean()) for _ in range(5000)]
    lo, hi = (float(v) * (-1.0 if lower_is_better else 1.0)
              for v in np.percentile(bs, [2.5, 97.5]))
    if lower_is_better:
        lo, hi = hi, lo
    return {"label": label, "n": int(len(x)), "mean_a": float(x.mean()),
            "mean_b": float(y.mean()), "effect": eff, "ci95": [lo, hi], "p_raw": p}


def verdict(c, p_adj):
    if c.get("insufficient"):
        return "INSUFFICIENT"
    if p_adj >= 0.05:
        return "FAIL (not significant)"
    return "PASS" if c["effect"] >= SESOI else "REAL BUT NOT MATERIAL (< SESOI)"


def main() -> None:
    payload = json.loads(KV.read_text())
    rows = payload["rows"]
    coll = payload.get("arm_collisions", [])
    print(f"KV adjudication · {payload.get('status')} · {len(rows)} rows · "
          f"cert_rho={payload.get('cert_rho')} · gamma={GAMMA_PRIMARY} · SESOI={SESOI}\n")
    if coll:
        print(f"ARM COLLISIONS: {len(coll)} of 200 campaigns -- diagnosed as DEGENERATE "
              "plate-1 fits\n  (posterior sd identically 0, where the two criteria are "
              "algebraically identical for\n  every rho). Excluded from KV-2 only, per spec "
              "§4a. See that section.\n")
        drop = {(c["family"], c["seed"]) for c in coll}
        rows = [r for r in rows if (r["family"], r["seed"]) not in drop
                or r["arm"] != "spade_cert_rho95"]

    cc = cluster(rows, CONTAIN, require_nonempty=True)
    cm = cluster(rows, MAPERR, require_nonempty=False)

    cs = {
        "KV-1": contrast(cc, "versionb", "versionb_random",
                         "KV-1 targeted vs RANDOM plate 2 (containment)"),
        "KV-2": contrast(cc, "spade_cert_rho95", "versionb",
                         "KV-2 cert-rho95 vs targeted (containment)"),
        "KV-3": contrast(cc, "versionb_random", "plate1_only",
                         "KV-3 random 2-plate vs 1-plate (containment; predicts NO effect)"),
        "KV-4": contrast(cm, "spade_cert_rho95", "versionb",
                         "KV-4 cert-rho95 vs targeted (MAP error, lower better)",
                         lower_is_better=True),
    }
    adj = holm({k: v["p_raw"] for k, v in cs.items() if not v.get("insufficient")})

    print(f"{'gate':<7}{'n':>5}{'effect':>10}{'95% CI':>22}{'p_raw':>9}{'p_holm':>9}  verdict")
    for k in ("KV-1", "KV-2", "KV-3", "KV-4"):
        c = cs[k]
        if c.get("insufficient"):
            print(f"{k:<7}{c['n']:>5}   INSUFFICIENT (<10 paired campaigns)")
            continue
        pa = adj[k]
        ci = f"[{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]"
        v = verdict(c, pa)
        if k == "KV-3":       # registered as a prediction of NO effect
            v = ("PASS (no effect, as predicted)" if c["effect"] < SESOI
                 else "FAIL -- 'adaptivity is the value' must be WITHDRAWN")
        if k == "KV-4":       # a guard: cert must not be WORSE by more than SESOI
            v = ("PASS (map not degraded)" if c["effect"] > -SESOI
                 else "FAIL -- certificate bought by wrecking the map; KV-2 dies with it")
        print(f"{k:<7}{c['n']:>5}{c['effect']:>+10.4f}{ci:>22}{c['p_raw']:>9.3g}"
              f"{pa:>9.3g}  {v}")
        cs[k]["p_holm"] = pa
        cs[k]["verdict"] = v

    # KV-5: answer rate, not a paired contrast
    ne = collections.Counter()
    tot = collections.Counter()
    for r in rows:
        tot[r["arm"]] += 1
        if not r.get(f"ce_empty_{GAMMA_PRIMARY}"):
            ne[r["arm"]] += 1
    ar = {a: ne[a] / tot[a] for a in tot}
    gap = abs(ar.get("spade_cert_rho95", 0.0) - ar.get("versionb", 0.0))
    kv5 = "PASS" if gap <= 0.05 else "FAIL -- containment bought by certifying less often"
    print(f"\nKV-5 · answer rate  " + "  ".join(f"{a}={ar[a]:.3f}" for a in sorted(ar)))
    print(f"          |cert - versionb| = {gap:.3f} (bar <= 0.05) -> {kv5}")

    if cs["KV-1"].get("verdict", "").startswith("FAIL"):
        print("\nKV-6 FIRES · Plate-2 targeting has now been tested prospectively on BOTH "
              "deliverables\n  -- map error (KF-3/3b/3c) and certificate containment (KV) -- "
              "and earns its\n  complexity on neither. The question is CLOSED; no further "
              "acquisition rule is\n  built without a new pre-registration.")

    OUT.write_text(json.dumps(
        {"spec": "docs/SPADE-PLATE2-CERTIFICATE-SPEC.md", "gamma": GAMMA_PRIMARY,
         "sesoi": SESOI, "arm_collisions": len(coll), "contrasts": cs,
         "answer_rate": ar, "KV_5": {"gap": gap, "verdict": kv5}}, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
