# HANDOFF — resume point for the next session

**Written 2026-08-22 (afternoon), superseding the 2026-08-22 morning version.**
Read this first, then `docs/FINDINGS-SPADE.md` **Part IV**, then Parts II–III.

---

## 1. Where to start

| read | why |
|---|---|
| `docs/FINDINGS-SPADE.md` §18–21 | **the cross-family results** — §19 is the headline, §18 is why the programme halted first |
| `docs/FINDINGS-SPADE.md` §13–16 | the overnight results; §14 (the kill fired) still stands |
| `docs/OPEN-QUESTIONS.md`, Phase 2–4 block onward | every registration, **plus the errata** |
| `docs/OPEN-QUESTIONS.md`, **2026-08-22 block at the end** | the four decisions and **errata 20–22** |
| `docs/OVERNIGHT-LOG.md` **D67–D74** | the decision trail for cross-family day |
| `docs/FINDINGS-SPADE.md` **§23** | **what Part IV signifies** — implications, not results |

**The three most important lines:**

1. §19 — **screening is fatal for a design-space deliverable on three of four families.**
   The Hill result was one family and post-hoc; it now reproduces on hartmann6, levy and
   rosenbrock, and **reverses on ackley**, which is excluded from DoE contrasts by a decision
   taken before the numbers existed.
2. §14 — SPADE's certificate fails below nominal at high assurance. **The registered kill
   still fired.** But see §22.
3. §22 — **§14's multiplicity correction used a normal approximation.** With the exact
   binomial tail, Holm ×72 on the leading cell is **0.2296, not 0.043**, and **no cell
   survives at α = 0.05.** "One of the four failures is statistically real" is **withdrawn**.
   Four cells still fall below nominal; none is distinguishable from chance across 72.

---

## 2. Committed results — what exists now

| file | contents | gate |
|---|---|---|
| **`p6-families.json`** | **cross-family, 8 cells, 2,000 campaigns, 48,000 rows** | **gate failures 0 across all 8** |
| `p2-versionb-gamma.json` | SPADE on the full 24-cell γ ladder, 4,800 rows | 28,800 comparisons at \|Δ\| = 0.0 |
| `p3-k6-d6-s010.json` | the (6, 0.10) cell, K6 map, 12 arms, 14,400 rows | 0 failures |
| `p3-k6b-d6-s010.json` | the (6, 0.10) cell, K6b conservative sets | 0 failures |
| `p3-taumax-sensitivity.json` | P3-B2, 28,800 rows, both τ_max definitions | 0 failures |
| `p4b-alpha-star-anomaly.json` | α\* vs regret and error volumes, 12 arms, 650 keys | 0 failures |
| `q30-additive.json` | the comparator that did not exist for eight months | — |
| earlier | `d23-doe-subspace`, `f1-dual-n`, `f2-error-volumes`, `f2-ce-error-volumes`, `p4-coord`, `p5-tau-quantile`, `p6-ceiling-census` | all clean |

`conservative_estimate_split` (cross-fit CE_α) is **now committed** — it was sitting
uncommitted in the working tree at session start. Version C owns it; it is the independent
route against which F3's draw sweep gets cross-checked.

---

## 3. 🔴 UNFINISHED — restart these

**Nothing is running.** All checkpoints intact.

| task | state | resume cost |
|---|---|---|
| **P1 — kernel-arm gate** | Q30 comparator done; the **2,800-row re-score has NOT run**. **Joseph: run it now** (decided: queue after cross-family, which is finished) | decides VALIDATED vs WITHDRAWN |
| **P7 — Murphy calibration** | **8/50**, 10 arms | ~2 h. Primary Phase 2 deliverable (F2d) |
| **P6 — cells 3 and 4** | `(8, 0.25)` and `(8, 0.10)` never started | ~2 h per cell at observed speed, **not** the registered ~7 h |
| **P3 — cells 2 and 3** | (8, 0.25) and (8, 0.10) held at key 1 | ~1.3 h each |
| **`coord` AUPRC re-score** | `p4-coord.json` lacks `auprc` | ~20 min |
| **F3 — draw sweep** | registered, **no runner exists**; `conservative_estimate_split` is now available to cross-check against | Tier 0 of the SPADE evaluation |

**Launch form — `setsid` does NOT exist on macOS:**
```
( nohup env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    .venv/bin/python -u scripts/<runner>.py <flags> > results/<log> 2>&1 < /dev/null & )
```
Verify **PPID 1** with `ps -o pid,ppid,args -p <pid>` before trusting it.
`scripts/drive_p6.sh` is the multi-family driver; it halts the whole programme on any
non-zero exit.

---

## 4. Decisions taken 2026-08-22 — do not reopen without new evidence

1. **Ackley: in for the map, OUT of every DoE contrast**, labelled. The screen evaluates the
   box centre as well as the CCD and hits ackley's exact optimum 7 times. **Taken before the
   cross-family numbers existed** — which matters, because ackley turns out to be the only
   family where `doe` wins. Also fixes Version C §3.3's scoring set.
2. **B3 subspace comparison: DROPPED.** It cannot be made from committed files at all — both
   sides pooled, unrestricted run never broken out per cell. `K6-TECHNICAL-REPORT.md` §5.10.2's
   "B3 made it worse" **comes out entirely**. *(Removal still pending — see §6.)*
3. **Kernel-arm re-score: queued after cross-family.** Cross-family is now done, so this is
   next in the queue.
4. **The IoU identity bound is now DERIVED per row, not a fitted scalar.** See §18. This
   changed a registered gate; the justification is in the commit and in §18, and the evidence
   is independent of the failure that prompted it.

---

## 5. Rules that cost something to learn — do not rediscover these

* **`setsid` is not on macOS.** Use the subshell form above.
* **A run tied to an agent's turn dies with it.** **Re-confirmed the hard way this session:**
  the P6 merge was launched as a plain background call, the session restarted, and it died
  leaving no output. The checkpoints survived; only the merge had to be redone.
* **Subagent findings die with the session too.** Five verification agents were lost to the
  same restart. Have them **write to disk as they go**, not only at the end.
* **Never write incrementally to a registered `results/` path** — write `<name>.partial`,
  promote once, carry `status` / `keys_present` / `keys_expected`.
* **Every constant in a registration names the population it was measured on** — *and the
  sample size it was measured at.* §18 is that rule failing one level down: a `max(observed)`
  masquerading as a bound gets **stricter** as the study grows.
* **Match the arithmetic, never widen a tolerance.** When a bound looks wrong, derive it.
* **Type I error volume read alone ranks silence first.** Use the symmetric difference.
* **`plate1_only` is `never_rank_separately`** — it IS `lhs` at 48 wells. Including it in a
  ranking makes `lhs` a second arm. It was included in the first cut of §19 and had to be
  redone.
* **`kill $VAR` with a multi-line var is a silent no-op in zsh.** Also: `pkill` does not stop
  launchd-managed agents such as `ReportCrash` — it respawns with the same PID.
* **Count processes by executable path, excluding shell wrappers.**

---

## 6. What NOT to claim

* **`doe` beats BO.** It needs a specific terminal rule **and** a specific (d, σ) cell.
  The defensible claim is about **terminal rules**. Note §19: on hartmann6 `doe` *does* beat
  both BO arms on the map while losing to every spread arm.
* **"Screening is always fatal."** Three of four families; ackley reverses it.
* **AUC rankings.** Superseded by error volumes wherever a ranking exists.
* **Any pooled containment figure.** Per-cell only, with `n`.
* **α\* as trustworthy or as discredited.** Neither reading resolves — but §19 adds a third
  independent measurement calling `sobol` best while α\* ranks it last.
* **"Seven of eight arms hold."** It is **six**; the B3 comparison is withdrawn entirely.
* **Anything on levy or rosenbrock without its denominator.** 10 and 9 rankable cells of 48.

---

## 7. Outstanding, carried from the SPADE evaluation queue

Tier 0 items still open: **F3 draw sweep** (no runner) and **the §10 scope gap**. The
**multiplicity correction is DONE** — and it contradicts the queue's own version of it (§22):
the queue's instruction to "restate §14 as one failure, not four" is itself wrong; the exact
tail gives **zero**. Tier 1 document corrections are inventoried but **not yet
applied** — including B3 removal (decision 2 above), the AUC "superseded" marks, and the
pooled-containment restatements. An audit found several of the queue's own claims are
**already corrected in the repo**, so verify each against the current text before editing.
