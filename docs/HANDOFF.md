# HANDOFF — resume point for the next session

**Written 2026-08-22.** Read this first, then `docs/FINDINGS-SPADE.md` Parts II–III.

---

## 1. Where to start

| read | why |
|---|---|
| `docs/FINDINGS-SPADE.md` §13–16 | **the overnight results** — the two that matter are §14 (the kill fired) and §13 |
| `docs/OPEN-QUESTIONS.md`, the Phase 2–4 block onward | every registration, **plus 16 errata** |
| `docs/OVERNIGHT-LOG.md` D1–D66 | the decision trail, including which of them were wrong |

**The single most important line:** §14 — **SPADE's certificate fails below nominal in 4 of 72
cells, all at α = 0.95, all at γ ≥ 0.95.** That is a registered kill firing, not a bug.

---

## 2. Committed results — what exists now

| file | contents | gate |
|---|---|---|
| `p2-versionb-gamma.json` | SPADE on the full 24-cell γ ladder, 4,800 rows | **28,800 comparisons at \|Δ\| = 0.0** |
| `p3-k6-d6-s010.json` | the (6, 0.10) cell, K6 map, 12 arms, 14,400 rows | 0 failures |
| `p3-k6b-d6-s010.json` | the (6, 0.10) cell, K6b conservative sets | 0 failures |
| `p3-taumax-sensitivity.json` | P3-B2, 28,800 rows, both τ_max definitions | 0 failures |
| `p4b-alpha-star-anomaly.json` | α\* vs regret and error volumes, 12 arms, 650 keys | 0 failures |
| `q30-additive.json` | **the comparator that did not exist for eight months** | — |
| earlier | `d23-doe-subspace`, `f1-dual-n`, `f2-error-volumes`, `f2-ce-error-volumes`, `p4-coord`, `p5-tau-quantile` | all clean |

---

## 3. 🔴 UNFINISHED — restart these

**Nothing is running. All checkpoints are intact.**

| task | state | resume cost |
|---|---|---|
| **P7 — Murphy calibration** | **8/50**, 10 arms | ~2 h. **Primary Phase 2 deliverable** (F2d) — calibration is the one Brier component AUC cannot see, and SPADE is the only arm making a calibrated claim |
| **P6 — cross-family** | **24 of 250** on hartmann6, then ackley → levy → rosenbrock | ~7 h per cell; **~14 h for cells 1+2**, the registered fallback |
| **P1 — kernel-arm gate** | Q30 comparator **done**; the **2,800-row re-score has NOT run** | decides whether the committed kernel rows are **VALIDATED or WITHDRAWN** |
| **P3 — cells 2 and 3** | (8, 0.25) and (8, 0.10) held at key 1 | ~1.3 h each |
| **`coord` AUPRC re-score** | `p4-coord.json` lacks `auprc` (my omission) | ~20 min |

**Launch form — `setsid` does NOT exist on macOS** (it failed silently for three workers):
```
( nohup env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    .venv/bin/python -u scripts/<runner>.py <flags> > results/<log> 2>&1 < /dev/null & )
```
Verify **PPID 1** with `ps -o pid,ppid,args -p <pid>` before trusting it.

---

## 4. Needs Joseph's decision

1. **How long to run the cross-family programme.** ~14 h (cells 1+2, publishable pair) vs ~20–28 h
   (all four). **The registered cell order — (6,0.25) → (6,0.10) → (8,0.25) → (8,0.10) — is what
   makes an early stop coherent.**
2. **The machine.** ~59 MB free RAM all session; Adobe `CCXProcess` burning ~80% of a core since
   13 Aug. Everything ran at roughly a tenth speed.
3. **Whether to register `versionb_tauq`** — SPADE's plate-2 straddle targets `0.75·mu_max`, which
   is **empty on ackley** (§ the SPADE design-threshold finding). Its kill condition must be
   written against a **map metric**, since the variants are indistinguishable on regret.

---

## 5. Rules that cost something to learn — do not rediscover these

* **`setsid` is not on macOS.** Use the subshell form above or `start_new_session=True`.
* **A run tied to an agent's turn dies with it.** Confirmed once, after I wrongly retracted it.
* **Never write incrementally to a registered `results/` path** — the `.gitignore` negation makes a
  partial stageable and it reads as finished. Write to `<name>.partial`, promote once, and carry
  `status` / `keys_present` / `keys_expected`.
* **Every constant in a registration names the population it was measured on.** Four of mine were
  right for a subset and registered as general.
* **Match the arithmetic, never widen a tolerance.** The `static_curve` 20-ordering artefact has
  now been caught **five** times, twice latent in the obvious implementation.
* **`plate1_only` must be regenerated as `lhs` and relabelled**, and gated against
  **`e2-grid.json`** — `k6-designspace-spread.json` is d=6 σ=0.25 only.
* **Degeneracy needs BOTH flags** — a tie test and a separation check. Neither catches the other's
  case, and a third case (arms agreeing far from the prevalence) needs the tie test specifically.
* **Type I error volume read alone ranks silence first.** Use the symmetric difference.
* **`kill $VAR` with a multi-line var is a silent no-op in zsh**; and after a parent dies its
  orphans reparent to PPID 1, so `ppid == parent` checks read as success.
* **Count processes by executable path, excluding shell wrappers** — a bare `grep` counts its own
  wrapper.

---

## 6. What NOT to claim

* **`doe` beats BO.** It needs a specific terminal rule **and** a specific (d, σ) cell, and 59% of
  its advantage at the primary cell is **identification, not search**. The defensible claim is
  about **terminal rules**.
* **AUC rankings.** Superseded by the error volumes wherever a ranking exists — they disagree in
  **18 of 18 rankable** cells (type II / symmetric difference; **14 for type I**).
* **Any pooled containment figure.** Withdrawn at eleven sites. Per-cell only, with `n`.
* **α\* as trustworthy or as discredited.** It agrees with regret and disagrees with the error
  volumes; **neither reading resolves.**
* **"Seven of eight arms hold."** It is **six**; the B3 comparison is withdrawn entirely.
