"""Fix 1 analysis: does a posterior-mean terminal rule help, and does it help ASYMMETRICALLY?

    .venv/bin/python scripts/analyse_fix1.py

Reads `results/fix1-terminal-rule.json`, writes `results/fix1-analysis.json`.

Registered in `docs/OPEN-QUESTIONS.md` (commit 4e14769) before the runner existed.

THE TWO QUESTIONS, AND THEY ARE NOT THE SAME ONE
-------------------------------------------------
1. **Does rule P lower regret at all**, per arm? Paired on `(instance, seed)`, n = 50,
   Holm across the arms.
2. **Is the effect ASYMMETRIC** — does reading the model help the arm with the better
   model more? That is the whole claim, and it is a *difference of differences*. An arm
   list in which everything improves by the same amount would answer question 1 "yes" and
   question 2 "no", and only question 2 is what Fix 1 was proposed for.

The registered kill is question 2, on one pre-declared contrast:

    C = improvement(versionb) - improvement(doe),  improvement = regret_A - regret_P

**If `doe` improves as much as `versionb` — C fails to favour `versionb` by at least the
SESOI of 0.02 with a significant Wilcoxon — the claimed asymmetry is not there.** One
test, deliberately outside the per-arm Holm family so it is not corrected twice.

STATISTICS (Q20 §2, and it is not negotiable here)
----------------------------------------------------
Wilcoxon governs yes/no; the 4,000-resample percentile bootstrap reports magnitude;
**disagreements between them are printed as disagreements and are not resolved.** A
project that silently picks whichever of the two agrees with it has no decision rule.

`plate1_only` is the same 48 wells as `lhs` (worst |delta| 4.44e-16 across the committed
columns). It is reported, and flagged, and must not be counted as independent evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results" / "fix1-terminal-rule.json"
OUT = ROOT / "results" / "fix1-analysis.json"

N_BOOT = 4000
BOOT_SEED = 0
#: Smallest effect this project calls a difference. Registered for K6 and reused here.
SESOI = 0.02
ALPHA = 0.05
#: The registered kill contrast. Named here so it cannot quietly become a different pair.
KILL_BETTER, KILL_WORSE = "versionb", "doe"
#: Not independent evidence -- the same 48 wells as `lhs`. Flagged wherever it prints.
DUPLICATE_OF = {"plate1_only": "lhs"}
RULE = "=" * 104


def _holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down, adjusted p in the original order (Q39)."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def _contrast(a: np.ndarray, b: np.ndarray) -> dict:
    """Mean of ``a - b``, its percentile bootstrap CI, and the two-sided Wilcoxon p.

    The bootstrap resamples the **paired differences**, which is the unit of analysis;
    resampling the two arms independently would break the pairing that makes n = 50
    campaigns worth n = 50 comparisons.
    """
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(BOOT_SEED)
    boots = np.array([rng.choice(d, d.size, replace=True).mean() for _ in range(N_BOOT)])
    try:
        p = float(wilcoxon(a, b).pvalue)
    except ValueError:                       # every difference identically zero
        p = 1.0
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    return {"n": int(d.size), "mean": float(d.mean()), "lo": lo, "hi": hi,
            "wilcoxon_p": p, "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "above_sesoi": bool(abs(float(d.mean())) >= SESOI)}


def _disagrees(c: dict, p_key: str = "wilcoxon_p") -> bool:
    """Bootstrap and Wilcoxon pointing different ways. Reported, never resolved."""
    return c["ci_excludes_zero"] != (c[p_key] < ALPHA)


def _paired(rows: list[dict], arm: str, key: str) -> dict[tuple[str, int], float]:
    return {(r["instance"], r["seed"]): float(r[key]) for r in rows if r["arm"] == arm}


def _align(rows, arms, key) -> tuple[list[tuple[str, int]], dict[str, np.ndarray]]:
    """One vector per arm over the `(instance, seed)` pairs EVERY arm has."""
    cols = {a: _paired(rows, a, key) for a in arms}
    keys = sorted(set.intersection(*(set(c) for c in cols.values())))
    return keys, {a: np.array([cols[a][k] for k in keys]) for a in arms}


def main() -> None:
    data = json.loads(IN.read_text())
    rows, cfg = data["rows"], data["config"]
    gate = data["gate"]
    if gate["failures"]:
        raise SystemExit(f"{len(gate['failures'])} gate failures in {IN.name}; "
                         "the rule-P column describes a different experiment")

    arms = [a for a in cfg["arms"] if any(r["arm"] == a for r in rows)]
    keys, A = _align(rows, arms, "regret_a")
    _, P = _align(rows, arms, "regret_p")
    _, PG = _align(rows, arms, "regret_p_grid")
    n = len(keys)

    print(f"{RULE}\nFIX 1 — the posterior-mean terminal rule, against the committed "
          f"argmax-of-the-noisy-reading\n{RULE}")
    print(f"  d={cfg['dim']} sigma={cfg['sigma']} · n={n} (instance, seed) pairs · "
          f"{len(arms)} arms · gate worst |delta| = {gate['worst_abs_delta']:.3e}")
    print(f"  rule P: {cfg['rule_p']}")
    print(f"  bootstrap {N_BOOT} resamples, default_rng({BOOT_SEED}); Wilcoxon two-sided; "
          f"Holm across {len(arms)} arms; SESOI {SESOI}\n")

    # ---- 1. per arm: does rule P lower regret at all? ------------------------------
    per_arm = []
    for a in arms:
        c = _contrast(P[a], A[a])            # rule P - rule A; negative = P is better
        sub = [r for r in rows if r["arm"] == a]
        per_arm.append({
            "arm": a, "rounds": cfg["rounds"][a], "n": n,
            "duplicate_of": DUPLICATE_OF.get(a),
            "mean_rule_a": float(A[a].mean()), "mean_rule_p": float(P[a].mean()),
            "mean_rule_p_grid_only": float(PG[a].mean()),
            "mean_improvement": float((A[a] - P[a]).mean()),
            "delta_p_minus_a": c,
            "polish_beat_grid_frac": float(np.mean([not r["from_grid"] for r in sub])),
            "wins_frac": float(np.mean(P[a] < A[a])),
        })
    adj = _holm([x["delta_p_minus_a"]["wilcoxon_p"] for x in per_arm])
    for x, p in zip(per_arm, adj, strict=True):
        x["delta_p_minus_a"]["p_holm"] = float(p)
        x["delta_p_minus_a"]["holm_significant"] = bool(p < ALPHA)

    print(f"{RULE}\n  1. PER ARM — mean regret under both rules. "
          f"Delta = rule P - rule A; NEGATIVE means the posterior-mean rule is BETTER."
          f"\n{RULE}")
    print(f"    {'arm':>15}{'rnd':>5}{'rule A':>9}{'rule P':>9}{'P grid':>9}"
          f"{'Delta':>9}{'95% CI':>21}{'p':>9}{'p Holm':>9}{'SESOI':>7}{'P<A':>7}")
    for x in per_arm:
        c = x["delta_p_minus_a"]
        flag = "  <<< DISAGREE" if _disagrees(c) else ""
        dup = "  (= lhs)" if x["duplicate_of"] else ""
        print(f"    {x['arm']:>15}{x['rounds']:>5}{x['mean_rule_a']:>9.4f}"
              f"{x['mean_rule_p']:>9.4f}{x['mean_rule_p_grid_only']:>9.4f}"
              f"{c['mean']:>+9.4f}  [{c['lo']:>+.4f},{c['hi']:>+.4f}]"
              f"{c['wilcoxon_p']:>9.4f}{c['p_holm']:>9.4f}"
              f"{('yes' if c['above_sesoi'] else 'no'):>7}"
              f"{100*x['wins_frac']:>6.0f}%{flag}{dup}")

    # ---- 2. the registered kill ----------------------------------------------------
    imp = {a: A[a] - P[a] for a in arms}
    kill = None
    if KILL_BETTER in imp and KILL_WORSE in imp:
        c = _contrast(imp[KILL_BETTER], imp[KILL_WORSE])
        big_enough = c["mean"] >= SESOI
        significant = c["wilcoxon_p"] < ALPHA
        fired = not (big_enough and significant)
        # WHY it fired is not the same finding twice over. "The two arms improve alike"
        # and "the difference is real but this n cannot see it" are different states of
        # the world, and a kill that reports only its own boolean hides which one holds.
        reason = ("the registered condition is met: the asymmetry survives" if not fired
                  else "; ".join(
                      ([] if big_enough else
                       [f"the difference {c['mean']:+.4f} is below the SESOI {SESOI}"])
                      + ([] if significant else
                         [f"Wilcoxon p={c['wilcoxon_p']:.4f} is not below {ALPHA}"])))
        kill = {"contrast": f"improvement({KILL_BETTER}) - improvement({KILL_WORSE})",
                **c, "sesoi": SESOI, "fired": bool(fired),
                "above_sesoi": bool(big_enough), "significant": bool(significant),
                "reason": reason,
                "bootstrap_wilcoxon_disagree": bool(_disagrees(c))}
        print(f"\n{RULE}\n  2. THE REGISTERED KILL — is the effect ASYMMETRIC?"
              f"\n{RULE}")
        print(f"    improvement = rule A regret - rule P regret  (positive = rule P helps)")
        print(f"      {KILL_BETTER:>15}: {imp[KILL_BETTER].mean():>+9.4f}")
        print(f"      {KILL_WORSE:>15}: {imp[KILL_WORSE].mean():>+9.4f}")
        print(f"      {'difference':>15}: {c['mean']:>+9.4f} "
              f"[{c['lo']:>+.4f},{c['hi']:>+.4f}]  p={c['wilcoxon_p']:.4f}  "
              f"SESOI {SESOI}")
        if kill["bootstrap_wilcoxon_disagree"]:
            print("      <<< BOOTSTRAP AND WILCOXON DISAGREE — reported, not resolved")
        print(f"\n    KILL {'FIRED' if fired else 'DID NOT FIRE'} — {reason}.")
        if fired:
            print(f"    Registered reading: `{KILL_WORSE}` improves as much as "
                  f"`{KILL_BETTER}`; the claimed asymmetry is not there.")
        else:
            print(f"    Registered reading: `{KILL_BETTER}` improves materially more "
                  f"than `{KILL_WORSE}`; the asymmetry survives.")

    # ---- 3. did the ARM ORDER change? ----------------------------------------------
    order_a = sorted(arms, key=lambda a: A[a].mean())
    order_p = sorted(arms, key=lambda a: P[a].mean())
    head_to_head = []
    for a in arms:
        if a == KILL_WORSE:
            continue
        head_to_head.append({"arm": a,
                             "rule_a": _contrast(A[KILL_WORSE], A[a]),
                             "rule_p": _contrast(P[KILL_WORSE], P[a])})
    print(f"\n{RULE}\n  3. DOES THE ARM ORDER CHANGE? Best (lowest regret) first."
          f"\n{RULE}")
    print(f"    rule A: {' > '.join(order_a)}")
    print(f"    rule P: {' > '.join(order_p)}")
    print(f"    order {'UNCHANGED' if order_a == order_p else 'CHANGED'}\n")
    print(f"    `{KILL_WORSE}` minus each arm, under each rule. "
          f"NEGATIVE means `{KILL_WORSE}` is ahead.")
    print(f"    {'arm':>15}{'rule A':>10}{'95% CI':>21}{'p':>9}   "
          f"{'rule P':>10}{'95% CI':>21}{'p':>9}{'':>4}{'sign':>8}")
    for h in head_to_head:
        ca, cp = h["rule_a"], h["rule_p"]
        same = "same" if np.sign(ca["mean"]) == np.sign(cp["mean"]) else "FLIPS"
        print(f"    {h['arm']:>15}{ca['mean']:>+10.4f}  [{ca['lo']:>+.4f},{ca['hi']:>+.4f}]"
              f"{ca['wilcoxon_p']:>9.4f}   {cp['mean']:>+10.4f}  "
              f"[{cp['lo']:>+.4f},{cp['hi']:>+.4f}]{cp['wilcoxon_p']:>9.4f}{'':>4}{same:>8}")

    # ---- 4. disagreements, collected --------------------------------------------
    dis = [x["arm"] for x in per_arm if _disagrees(x["delta_p_minus_a"])]
    print(f"\n{RULE}\n  4. BOOTSTRAP vs WILCOXON\n{RULE}")
    if dis:
        print(f"    {len(dis)} per-arm contrast(s) disagree: {', '.join(dis)}.")
        print("    Reported as disagreements. Not resolved, and not adjudicated by "
              "picking the\n    one that suits the conclusion (Q20 §2).")
    else:
        print("    None. Every per-arm contrast agrees between the two.")

    OUT.write_text(json.dumps({
        "source": IN.name, "provenance": data["provenance"], "config": cfg,
        "gate": {"worst_abs_delta": gate["worst_abs_delta"],
                 "failures": len(gate["failures"])},
        "statistics": {"n_boot": N_BOOT, "boot_seed": BOOT_SEED, "sesoi": SESOI,
                       "alpha": ALPHA, "holm_family": arms,
                       "unit_of_analysis": "(instance, seed)", "n": n},
        "per_arm": per_arm, "kill": kill,
        "order_rule_a": order_a, "order_rule_p": order_p,
        "order_changed": bool(order_a != order_p),
        "head_to_head_vs_" + KILL_WORSE: head_to_head,
        "bootstrap_wilcoxon_disagreements": dis}, indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
