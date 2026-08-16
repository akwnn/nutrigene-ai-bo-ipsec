"""Search versus identification, both classical and Bayesian, under BOTH acquisitions.

    python scripts/rescore_oracle_best.py                  # all four cells
    python scripts/rescore_oracle_best.py --cell 6 0.25    # one cell
    python scripts/rescore_oracle_best.py --gate-only      # reproduce, gate, report nothing
    python scripts/rescore_oracle_best.py --workers 4

Workstreams 1 and 3 of the revision program. Q55 was this file with one acquisition;
qLogNEI is now co-primary, because a result that holds against qLogEI alone is a result
about an acquisition function. Noisy EI exists precisely because the incumbent is itself
uncertain when observations carry noise, and the executed comparison this project is
answering to used it. **qLogNEI is better than qLogEI at all four cells** (0.1532 / 0.0808
/ 0.1105 / 0.0849 against 0.1553 / 0.0874 / 0.1247 / 0.0972), so promoting it is the
harder test for the classical arm's lead, not a friendlier one.

WHAT IS ACTUALLY BEING ASKED
-----------------------------
Every headline in this project reports **rule A**: pick the well with the best *noisy*
reading, then report its noiseless value. That is what a researcher can really select,
and by it the classical pipeline beats BO at d=6 sigma=0.25 (0.0958 against 0.1553).

There is a second, different quantity — **oracle-best**: the noiseless value of the best
well the campaign *ran*, whether or not the assay could tell it apart. The difference
between them is an **identification gap**, and it is a property of the measurement, not
of the search.

The paper's limitations paragraph currently asserts that the best-observed estimand *is*
the true best among evaluated points. That sentence is false: those are the two different
quantities above. It cannot be corrected from stored artefacts, because `e2-grid.json`
keeps one ``regret`` per row and nothing else, so BO's oracle-best does not exist anywhere
on disk. Q49's 61% identification share is LHS at n=192, not the E2 BO campaign, and
subtracting it from E2's rule A would be inventing a number.

WHY THE DoE HALF IS CHEAP AND THE BO HALF IS NOT
--------------------------------------------------
The classical arm runs on its own evaluator at a stored seed, so re-running it reproduces
the same 48 wells in seconds — `rescore_d20.py` already established that. BO has to
regenerate 200 full campaigns. Both are gated the same way: the **published rule-A column
must come back identical** before the new oracle-best column beside it is trusted. A
campaign that does not reproduce is not the campaign the paper reports, and an
oracle-best computed from it would describe a different experiment.

WHAT THIS SCRIPT MAY NOT CONCLUDE
-----------------------------------
Neither direction is pre-written. Prompt 2 fixes the language in advance:

  * *"DoE tested better conditions"* only if the **oracle-best** contrast is negative and
    significant.
  * *"Researchers using DoE selected a better well from the noisy readings"* only if the
    **rule A** contrast is negative and significant — which is already true at sigma=0.25.
  * **If the two disagree in sign, that is the result.** Write both.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig                   # noqa: E402
from boec.diagnostics import instance_bootstrap, reported_best_curve  # noqa: E402
from boec.doe import run_doe_arm                                     # noqa: E402
from boec.optimizers import AcqConfig                                # noqa: E402
from boec.oracles import load_ensemble                               # noqa: E402
from boec.torch_oracle import BiphasicOracle                         # noqa: E402

BUDGET = 48
Q = 4
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))

#: Per-row reproduction tolerance. Both arms are deterministic given (instance, seed):
#: the campaign replays the same acquisition path and the classical pipeline the same 48
#: wells. Anything above this is a different run, not a rounding difference.
GATE_TOL = 1e-12

#: Cell-level means the re-run must land on, from the committed artefacts. Quoted in
#: `docs/PROMPTS-NEXT.md` Prompt 2 and checked here so a silent drift in either source
#: file is caught rather than absorbed.
PUBLISHED_BO_RULE_A = {(6, 0.25): 0.1553, (6, 0.10): 0.0874,
                       (8, 0.25): 0.1247, (8, 0.10): 0.0972}
#: Workstream 3. qLogNEI is **better than qLogEI at all four cells**, so promoting it to
#: co-primary is the *harder* test for the classical arm's lead, not a friendlier one.
#: That is exactly why it has to be here: a reviewer can otherwise dismiss the whole
#: result as "wrong acquisition function", and observations really are noisy — noisy EI
#: exists because the incumbent is itself uncertain, and Rummukainen used it.
PUBLISHED_NEI_RULE_A = {(6, 0.25): 0.1532, (6, 0.10): 0.0808,
                        (8, 0.25): 0.1105, (8, 0.10): 0.0849}
PUBLISHED_DOE_RULE_A = {(6, 0.25): 0.0958, (6, 0.10): 0.0892,
                        (8, 0.25): 0.0963, (8, 0.10): 0.0948}
PUBLISHED_DOE_ORACLE_BEST = {(6, 0.25): 0.0597, (6, 0.10): 0.0544,
                             (8, 0.25): 0.0575, (8, 0.10): 0.0500}
#: The published means carry four decimals, so they can only be checked to half a unit
#: in the last place.
CELL_TOL = 5e-5

N_BOOT = 4000
#: Named for Workstream 1's requested artefact rather than for the run number, because the
#: revision program lists this filename and someone will grep for it. Q55 was this file
#: without the qLogNEI arm; it is extended here, not superseded — its numbers reproduce
#: exactly, which the per-row gate below re-checks.
OUT = ROOT / "results" / "q57-search-vs-id.json"
E2_GRID = ROOT / "results" / "e2-grid.json"
E2_DOE_D8 = ROOT / "results" / "e2-doe-d8.json"
RULE = "=" * 100


def _rows(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    return d if isinstance(d, list) else d.get("rows", d)


def _stored(dim: int, sigma: float, arm: str) -> dict[tuple[str, int], float]:
    """Published regret per (instance, seed) for one arm at one cell.

    The classical arm at d=8 lives in its own file: `e2-doe-d8.json` was produced after
    the main grid, and D17 once recorded it as missing. It is not.
    """
    src = E2_DOE_D8 if (arm == "doe" and dim == 8) else E2_GRID
    return {(r["instance"], int(r["seed"])): float(r["regret"]) for r in _rows(src)
            if r["arm"] == arm and r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12}


def _score(truth_vals: torch.Tensor, Y: torch.Tensor, opt: float) -> tuple[float, float, bool]:
    """``(rule_a, oracle_best, identified)`` from one campaign's visit log.

    ``rule_a`` locates by the **noisy** reading and scores the truth there.
    ``oracle_best`` maximises the truth over the same visited set with no locating to do,
    so it can never be worse. ``identified`` is whether those two picked the same well.
    """
    t = truth_vals.double().reshape(-1)
    rule_a = opt - float(reported_best_curve(truth_vals, Y)[-1])
    oracle_best = opt - float(t.max())
    identified = int(torch.argmax(Y.double().reshape(-1))) == int(torch.argmax(t))
    return rule_a, oracle_best, bool(identified)


def one(job: tuple[int, float, int, int]) -> dict:
    """One (instance, seed) at one cell: both arms, both locators, both gates."""
    dim, sigma, idx, seed = job
    t0 = time.time()
    inst = load_ensemble(dim=dim)[idx]
    opt = float(inst.optimum_value)
    bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                          torch.ones(dim, dtype=torch.double)])

    # --- BO, both acquisitions: regenerate, then check each IS the published one ---
    out = {}
    for tag, kind in (("bo", "qlogei"), ("nei", "qlognei")):
        o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        cfg = AcqConfig(kind=kind)  # type: ignore[arg-type]
        camp = Campaign(o, bounds,
                        CampaignConfig(d=dim, budget=BUDGET, q=Q, seed=seed, acq=cfg))
        camp.run()
        a, ob, ident = _score(o.truth(camp.train_X), camp.train_Y, opt)
        out |= {f"{tag}_rule_a": a, f"{tag}_oracle_best": ob, f"{tag}_identified": ident}

    # --- DoE: same, on its own evaluator ---------------------------------------
    od = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
    r = run_doe_arm(od, bounds, truth=od.truth, budget=BUDGET, seed=seed)
    doe_a, doe_ob, doe_id = _score(od.truth(r.X_visited), r.Y_visited, opt)

    return dict(dim=dim, sigma=sigma, instance=inst.instance_id, instance_index=idx,
                seed=seed, secs=round(time.time() - t0, 1),
                doe_rule_a=doe_a, doe_oracle_best=doe_ob, doe_identified=doe_id,
                **out)


def gate(rows: list[dict]) -> dict:
    """The published rule-A column must come back identical, per row and per cell.

    Raises rather than reporting. Prompt 2 §3: *"If the gate fails, the campaign is not
    reproduced and the new column is worthless."*
    """
    arms = {"bo": "qlogei", "nei": "qlognei", "doe": "doe"}
    worst = {a: 0.0 for a in arms}
    n = {a: 0 for a in arms}
    for arm, published_name in arms.items():
        key_col = f"{arm}_rule_a"
        for r in rows:
            if key_col not in r:
                continue          # a row from before this arm existed
            key = key_col
            want = _stored(r["dim"], r["sigma"], published_name)
            k = (r["instance"], r["seed"])
            if k not in want:
                raise AssertionError(
                    f"{arm} row {k} at d={r['dim']} sigma={r['sigma']} has no published "
                    "counterpart; the re-run is not on the stored grid.")
            delta = abs(r[key] - want[k])
            worst[arm] = max(worst[arm], delta)
            n[arm] += 1
            if delta > GATE_TOL:
                raise AssertionError(
                    f"{arm} rule A does not reproduce at instance {k[0]} seed {k[1]} "
                    f"d={r['dim']} sigma={r['sigma']}: {r[key]:.15f} vs {want[k]:.15f} "
                    f"(|delta|={delta:.3e}). The campaign is not the published one, so "
                    "the oracle-best column beside it would describe a different run.")

    # --- and the cell means must be the numbers the paper prints ----------------
    # Only for cells that are actually complete. A half-finished cell has a mean that is
    # legitimately not the published one, and raising on it would turn every resume into
    # a false alarm — which teaches the reader to ignore this gate.
    cells, skipped = {}, []
    for dim, sigma in CELLS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
        if not sub:
            continue
        expected = len(_stored(dim, sigma, "qlogei"))
        if len(sub) < expected:
            skipped.append(f"d={dim} s={sigma} ({len(sub)}/{expected})")
            continue
        for label, key, published in (
                ("bo_rule_a", "bo_rule_a", PUBLISHED_BO_RULE_A),
                ("nei_rule_a", "nei_rule_a", PUBLISHED_NEI_RULE_A),
                ("doe_rule_a", "doe_rule_a", PUBLISHED_DOE_RULE_A),
                ("doe_oracle_best", "doe_oracle_best", PUBLISHED_DOE_ORACLE_BEST)):
            if key not in sub[0]:
                continue
            got = float(np.mean([r[key] for r in sub]))
            exp = published[(dim, sigma)]
            if abs(got - exp) > CELL_TOL:
                raise AssertionError(
                    f"{label} at d={dim} sigma={sigma} is {got:.4f}, published {exp:.4f} "
                    f"(|delta|={abs(got-exp):.2e} > {CELL_TOL:g}).")
            cells[f"{label}|{dim}|{sigma}"] = got
    return dict(rows_checked=n, worst_abs_delta=worst, tol=GATE_TOL,
                cell_tol=CELL_TOL, cell_means=cells, incomplete_cells=skipped)


def _per_instance(sub: list[dict], key: str) -> np.ndarray:
    """One number per instance, averaged over its seeds. E2's clustering, restated.

    Inference clusters on landscapes, not runs: 25 landscapes x 2 seeds is an effective
    n of 25, and treating it as 50 would halve every interval this script prints.
    """
    by: dict[str, list[float]] = {}
    for r in sub:
        by.setdefault(r["instance"], []).append(r[key])
    return np.array([float(np.mean(v)) for _, v in sorted(by.items())])


def analyse(rows: list[dict]) -> list[dict]:
    from scipy import stats
    out = []
    for dim, sigma in CELLS:
        sub = [r for r in rows if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12]
        if not sub:
            continue
        def contrast(d: np.ndarray) -> dict:
            m, lo, hi = instance_bootstrap(d, n_boot=N_BOOT)
            w = stats.wilcoxon(d) if np.any(d != 0) else None
            return dict(mean=float(m), lo=float(lo), hi=float(hi),
                        wilcoxon_p=float(w.pvalue) if w is not None else 1.0,
                        n=int(d.size))

        doe_a = _per_instance(sub, "doe_rule_a")
        doe_ob = _per_instance(sub, "doe_oracle_best")
        cell = dict(dim=dim, sigma=sigma, n_instances=int(doe_a.size),
                    doe_rule_a=float(doe_a.mean()),
                    doe_oracle_best=float(doe_ob.mean()),
                    doe_gap=float((doe_a - doe_ob).mean()),
                    doe_identified=float(np.mean([r["doe_identified"] for r in sub])),
                    gap_doe=contrast(doe_a - doe_ob), arms={})

        # Workstream 3: every contrast is computed against BOTH acquisitions. A headline
        # that survives only one of them is not a headline about Bayesian optimization,
        # it is a headline about qLogEI.
        for tag in ("bo", "nei"):
            if f"{tag}_rule_a" not in sub[0]:
                continue
            a = _per_instance(sub, f"{tag}_rule_a")
            ob = _per_instance(sub, f"{tag}_oracle_best")
            cell["arms"][tag] = dict(
                rule_a=float(a.mean()), oracle_best=float(ob.mean()),
                gap=float((a - ob).mean()),
                identified=float(np.mean([r[f"{tag}_identified"] for r in sub])),
                contrast_rule_a=contrast(doe_a - a),
                contrast_oracle_best=contrast(doe_ob - ob),
                gap_arm=contrast(a - ob),
                gap_difference=contrast((a - ob) - (doe_a - doe_ob)))

        # Back-compatible top-level keys so anything reading the Q55 shape still works.
        if "bo" in cell["arms"]:
            b = cell["arms"]["bo"]
            cell |= dict(bo_rule_a=b["rule_a"], bo_oracle_best=b["oracle_best"],
                         bo_gap=b["gap"], bo_identified=b["identified"],
                         contrast_rule_a=b["contrast_rule_a"],
                         contrast_oracle_best=b["contrast_oracle_best"],
                         gap_bo=b["gap_arm"], gap_difference=b["gap_difference"])
        out.append(cell)
    return out


NAME = {"bo": "qLogEI", "nei": "qLogNEI"}


def _verdict(c: dict) -> str | None:
    """Which arm the interval favours, or ``None`` if it covers zero."""
    if c["hi"] < 0 or c["lo"] > 0:
        return "DoE" if c["mean"] < 0 else "BO"
    return None


def report(summary: list[dict]) -> None:
    print(f"\n{RULE}\n  THE TWO LOCATORS, BOTH ACQUISITIONS — mean regret, n=25 landscapes"
          f"\n{RULE}")
    print(f"    {'cell':>14}{'arm':>9}{'rule A':>10}{'tested':>10}{'gap':>9}{'id%':>7}"
          f"   |{'DoE rule A':>12}{'DoE tested':>12}{'DoE gap':>9}{'DoE id%':>9}")
    for s in summary:
        for tag, a in sorted(s["arms"].items()):
            cell = f"d={s['dim']} s={s['sigma']}" if tag == "bo" else ""
            print(f"    {cell:>14}{NAME[tag]:>9}{a['rule_a']:>10.4f}"
                  f"{a['oracle_best']:>10.4f}{a['gap']:>+9.4f}{100*a['identified']:>6.0f}%"
                  f"   |{s['doe_rule_a']:>12.4f}{s['doe_oracle_best']:>12.4f}"
                  f"{s['doe_gap']:>+9.4f}{100*s['doe_identified']:>8.0f}%")

    print(f"\n{RULE}\n  THE CONTRAST, ON EACH LOCATOR, AGAINST EACH ACQUISITION. "
          f"Negative = DoE better.\n{RULE}")
    print(f"    {'cell':>14}{'vs':>9}{'rule A (DoE-BO)':>26}{'p':>9}"
          f"{'tested-best (DoE-BO)':>28}{'p':>9}{'sign':>10}")
    for s in summary:
        for tag, arm in sorted(s["arms"].items()):
            a, o = arm["contrast_rule_a"], arm["contrast_oracle_best"]
            same = "same" if np.sign(a["mean"]) == np.sign(o["mean"]) else "FLIPS"
            cell = f"d={s['dim']} s={s['sigma']}" if tag == "bo" else ""
            print(f"    {cell:>14}{NAME[tag]:>9}"
                  f"{a['mean']:>+11.4f} [{a['lo']:>+.4f},{a['hi']:>+.4f}]"
                  f"{a['wilcoxon_p']:>9.4f}"
                  f"{o['mean']:>+13.4f} [{o['lo']:>+.4f},{o['hi']:>+.4f}]"
                  f"{o['wilcoxon_p']:>9.4f}{same:>10}")

    # ---- Workstream 3's actual deliverable -----------------------------------
    print(f"\n{RULE}\n  DOES EVERY QUALITATIVE HEADLINE SURVIVE BOTH ACQUISITIONS?"
          f"\n{RULE}")
    print("    A conclusion that holds against qLogEI but not qLogNEI is a conclusion")
    print("    about an acquisition function, not about Bayesian optimization.\n")
    disagree = []
    for s in summary:
        if len(s["arms"]) < 2:
            continue
        cell = f"d={s['dim']} sigma={s['sigma']}"
        for locator, key in (("measured-value argmax", "contrast_rule_a"),
                             ("tested-best", "contrast_oracle_best")):
            v = {t: _verdict(a[key]) for t, a in s["arms"].items()}
            agree = len(set(v.values())) == 1
            shown = ", ".join(f"{NAME[t]}: {x or 'null'}" for t, x in sorted(v.items()))
            flag = "" if agree else "   <<< DISAGREES"
            print(f"    {cell:>16}  {locator:<22} {shown}{flag}")
            if not agree:
                disagree.append((cell, locator, v))
    print()
    if not disagree:
        print("    Every verdict is IDENTICAL under both acquisitions. No headline in this")
        print("    file depends on the choice of acquisition function.")
    else:
        print(f"    {len(disagree)} verdicts change with the acquisition. Each must be")
        print("    reported as acquisition-dependent, not as a property of BO:")
        for cell, loc, v in disagree:
            print(f"      {cell} / {loc}: "
                  + ", ".join(f"{NAME[t]} says {x or 'null'}" for t, x in sorted(v.items())))


def _provenance(argv) -> dict:
    def _git(*a: str) -> str:
        try:
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except Exception:  # noqa: BLE001
            return "unknown"
    import botorch
    import gpytorch
    import scipy
    return dict(git_sha=_git("rev-parse", "HEAD"),
                git_dirty=bool(_git("status", "--porcelain")),
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), argv=list(argv),
                python=platform.python_version(), torch=torch.__version__,
                botorch=botorch.__version__, gpytorch=gpytorch.__version__,
                numpy=np.__version__, scipy=scipy.__version__,
                config=dict(budget=BUDGET, q=Q, cells=[list(c) for c in CELLS],
                            gate_tol=GATE_TOL, cell_tol=CELL_TOL, n_boot=N_BOOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", nargs=2, metavar=("DIM", "SIGMA"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--gate-only", action="store_true")
    args = ap.parse_args()

    cells = ([(int(args.cell[0]), float(args.cell[1]))] if args.cell else list(CELLS))
    print(f"{RULE}\nQ55 — oracle-best beside rule A, both arms\n{RULE}")
    print(f"  cells {cells}, budget {BUDGET}, q {Q}")
    print(f"  gate: published rule A must reproduce per row at {GATE_TOL:g}\n")

    done = json.loads(OUT.read_text())["rows"] if OUT.exists() else []
    have = {(r["dim"], r["sigma"], r["instance_index"], r["seed"]) for r in done}

    todo = []
    for dim, sigma in cells:
        want = _stored(dim, sigma, "qlogei")
        ids = {i.instance_id: k for k, i in enumerate(load_ensemble(dim=dim))}
        for (iid, seed) in sorted(want):
            idx = ids[iid]
            if (dim, sigma, idx, seed) not in have:
                todo.append((dim, sigma, idx, seed))
    if have:
        print(f"  resuming — {len(have)} rows already on disk")
    print(f"  {len(todo)} rows to run on {args.workers} workers\n")

    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for k, row in enumerate(pool.map(one, todo), 1):
                done.append(row)
                OUT.write_text(json.dumps(
                    dict(provenance=_provenance(sys.argv), rows=done), indent=1))
                if k % 10 == 0 or k == len(todo):
                    el = time.time() - t0
                    print(f"    {k:>4}/{len(todo)}  {el/60:>5.1f} min elapsed, "
                          f"~{el/k*(len(todo)-k)/60:>5.1f} min left", flush=True)

    g = gate(done)
    print(f"\n  GATE PASSED — rule A reproduced for "
          f"{g['rows_checked']['bo']} BO and {g['rows_checked']['doe']} DoE rows")
    print(f"    worst |delta|: BO {g['worst_abs_delta']['bo']:.3e}, "
          f"DoE {g['worst_abs_delta']['doe']:.3e}")
    print(f"    {len(g['cell_means'])} published cell means reproduced to {CELL_TOL:g}")
    if g["incomplete_cells"]:
        print(f"    cell means NOT checked (still incomplete): "
              f"{', '.join(g['incomplete_cells'])}")
    if args.gate_only:
        return

    summary = analyse(done)
    report(summary)
    OUT.write_text(json.dumps(dict(provenance=_provenance(sys.argv), gate=g,
                                   summary=summary, rows=done), indent=1))
    print(f"\n  written to {OUT.relative_to(ROOT)}  ({(time.time()-t0)/60:.0f} min)")


if __name__ == "__main__":
    main()
