# HANDOFF — resume point for the next session

**Written 2026-08-22 (evening); §0 and §A1 updated 2026-08-23.**
Read this first, then `docs/FINDINGS-SPADE.md` **Part V (§32 onward)**, then Part IV, then Parts II–III.

> **✅ NOTHING IS RUNNING, AND NOTHING IS BLOCKED.** Verified 2026-08-23: zero runner
> processes alive. Every experimental dependency has landed. **What remains is the draft.**

---

## 0. ✅ COMPLETE — the runs this handoff was written to track

> The text below is preserved as written on 2026-08-22 evening, when both runs were live.
> **Both have since finished.** Do not treat the PIDs or ETAs as current.

| run | state as of 2026-08-23 |
|---|---|
| **P8** — SPADE's certificate off hill | ✅ `COMPLETE` — `results/p8-certificate-families.json`, 24,000 rows, **0 gate failures** |
| **Version C Form 1**, both σ | ✅ `COMPLETE` — 28,800 rows, gate clean, **all eight kills adjudicated, none fired** |
| **P7** — Murphy calibration | ✅ `COMPLETE` — 12,000 rows, 10 arms |

### Historical — the live-run notice as written on 2026-08-22

### P8 — SPADE's certificate off hill (started 2026-08-22 evening, ~10 h)

```
PID 43033   .venv/bin/python -u scripts/run_p8_certificate_families.py   (PPID 1)
```

**The largest remaining gap, and the one Joseph named:** SPADE's *arms* are in 17 committed
files but SPADE's **certificate** — `alpha_star`, `ce_contain_*`, containment — exists on
**`hill` only**. `p6-families.json` has 60 columns across four families and **not one is a
certificate column.** P8 closes it: 5 families × 4 arms × 50 seeds = **1,000 campaigns**,
d=6, σ=0.25, **4,096 draws** (not P2's 512 — F3 registered 512 as insufficient at γ≥0.95, so
hill is re-run here too rather than compared across draw counts).

Writes `results/p8-certificate-families.json`. Gate: hill `regret`/`n_wells` against
`p2-versionb-gamma.json` at \|Δ\| = 0 — **running clean**. Certificate columns are
deliberately **not** gated (the draw count changed; they are meant to move).
Registered at `b281d4b`, runner at `2941a20`. ~36 s/campaign, ETA ~10 h.

### Version C Form 1 — FINISHED



```
PID 74464   .venv/bin/python -u scripts/run_versionc_form1.py --sigma 0.10
PID 74462   sh -c  (parent, PPID 1 — properly detached)
```

Started ~16:53. It **auto-chains to σ=0.25 on success** via `&&`, so one process becomes two
runs. Observed **~180 s per campaign × 50 campaigns ≈ 2.5 h per σ, ≈ 5 h total.**

| writes | state at time of writing |
|---|---|
| `results/versionc-form1-s010.json` | `.partial` present, **[2/50]** |
| `results/versionc-form1-s025.json` | not started; chained |
| `results/versionc-form1-s010.log` / `-s025.log` | live |

**When it lands:** gate is `p3-k6-d6-s010.json` at \|Δ\| = 0 over 20 columns, 12 arms × 50
keys. If the gate fails the run aborts and the `.partial` is the evidence — do not delete it.
**Zero new wells**: this is a re-score of stored Version B campaigns (see §8.5).

To check: `ps -o pid,ppid,etime,args -p 74464` and `tail -3 results/versionc-form1-s010.log`.

---

## 1. Where to start

| read | why |
|---|---|
| `docs/FINDINGS-SPADE.md` §19 | **the headline** — screening is fatal on 3 of 4 families |
| `docs/FINDINGS-SPADE.md` §29 | **§14's kill was an estimator artefact.** Reverses the previous headline |
| `docs/FINDINGS-SPADE.md` §26–27 | Q59 (screening is not the mechanism) and the closed scope gap |
| `docs/FINDINGS-SPADE.md` §32 | **Version C, C0** — the σ=0.10 deficit was an identification artefact |
| `docs/FINDINGS-SPADE.md` §33 | **the RSM toolkit** — the classical arm fails all four of its own diagnostics |
| `docs/FINDINGS-SPADE.md` §34 | **NEW** — the D20 reversal as a rank, and **E7's prediction fails** |
| `docs/FINDINGS-SPADE.md` **§35** | 🔴 **VERSION C: eight kills registered, ZERO adjudicated** — read before touching Version C |
| `docs/OPEN-QUESTIONS.md`, from the Phase 2–4 block | every registration **plus errata 20–30** |
| `docs/OVERNIGHT-LOG.md` **D67–D75** | the decision trail |

**The five lines that matter most:**

1. **§35 — Version C registered EIGHT kill conditions and adjudicated NONE.**
   `grep -rno "K-C[1-8]" scripts/` returns four hits, all K-C7, and not one Version C
   artefact carries a verdict field. Three kills (K-C4/5/8) are **moot** — §2 was never
   built and K-C8 would compare an arm to itself. **K-C1, K-C2 (the hard stop) and K-C3 are
   the entire live surface and have no evaluator.** The columns are being produced; the
   verdict has no code.
2. **§29 — the registered kill was an artefact of 512 draws.** "SPADE's certificate fails
   below nominal at high assurance" is **WITHDRAWN**. A 1.5–3.5 pp selection bias survives at
   4,096 draws, concentrated where the quantiles tie; Version C's cross-fit finds the same
   thing by an independent route. **`N_DRAWS = 512` is now a registered insufficiency.**
3. **§19 — screening is fatal for a design-space deliverable on three of four families**, and
   **reproduces at d = 8** (`doe` mean rank 7.78 of 9 vs 7.59 at d = 6). Ackley reverses it
   and is excluded from DoE contrasts by a decision taken before the numbers existed.
4. **§34 — E7's registered prediction FAILS, and so does its kill condition.** Under rule P
   `doe` has no advantage to be above or below SESOI; **it has a deficit.** Its identification
   gap nearly quadruples while every other arm's falls.
5. **§33 — the classical arm fails its own single-well acceptance test in 50 of 50 campaigns**,
   predicts a response above the global maximum in half of them, and lands on a saddle every
   time.

---

## 2. ✅ DONE — committed, gated, and green

**Full suite: `1,317 passed, 0 failed` (4 m 30 s), re-run at the time of writing.**

| file | contents | gate |
|---|---|---|
| **`p6-families.json`** | **cross-family, ALL 16 CELLS, 96,000 rows** | **gate failures 0** |
| **`p7-murphy.json`** | **Murphy decomposition, `complete`, 50/50 keys, 12,000 rows** | **gate failures 0** |
| **`f3-draw-sweep.json`** | **`COMPLETE`, draws 50/50 · seeds 200/200, 3,000 rows** | clean |
| **`p1-kernel-gate.json`** | **verdict `VALIDATED`**, 2,800/2,800 rows re-scored | 0 failures |
| `q59-map-rescore.json` | `COMPLETE`, 50/50, 2,400 rows — **corrected for the `sigma_add` bug** | 0 misses |
| `versionc-gate-s010.json` | C0, `complete`, 50/50, 600 rows | \|Δ\| = 0, double-gated |
| `versionc-gate-analysis.json` | per-arm rule A vs P, Holm, the `n_eff` regression | — |
| `versionc-detector-fit.json` / `-boundary.json` | §3.2 fit set, 150 rows; boundary **`frozen: false`** | — |
| `q59-hartmann-no-screen.json` | the unscreened classical arm | \|Δ\| = 0.0 |
| `p2-versionb-gamma.json` | full 24-cell γ ladder, 4,800 rows | 28,800 comparisons at \|Δ\| = 0.0 |
| `p3-k6-d6-s010.json`, `p3-k6b-d6-s010.json`, `p3-taumax-sensitivity.json` | the (6, 0.10) cell | 0 failures |
| `p4b-alpha-star-anomaly.json` | α\* vs regret and error volumes, 12 arms | 0 failures |
| earlier | `q30-additive`, `d23-doe-subspace`, `f1-dual-n`, `f2-error-volumes`, `f2-ce-error-volumes`, `p4-coord`, `p5-tau-quantile`, `p6-ceiling-census`, `fix1-terminal-rule`, `q52-budget-to-target`, `step0-oracle-best`, `q57-search-vs-id` | all clean |

**Three items the previous handoff listed as UNFINISHED are finished.** P7 (called "the single
largest outstanding item"), F3, and the P1 kernel re-score are all on disk, tracked, and
gated. **Do not restart them.**

---

## 3. 🔴 NOT FINISHED — the real list

### 3.1 Cheap, no new campaigns, nothing blocking

| task | state | cost |
|---|---|---|
| **`coord` AUPRC re-score** | verified absent: `p4-coord.json.k6_rows` has no `auprc` key | ~20 min |
| ~~Tier 1 document corrections~~ | ✅ **VERIFIED ALREADY APPLIED, 2026-08-23.** B3: `K6-TECHNICAL-REPORT.md:600` already reads *withdrawn*, `:604` *RESOLVED*. Pooled containment: `:929` already reads *"no pooled containment number appears in this document"*, with the withdrawn 0.1546/0.4203/0.5098 listed at `:1816`. AUC: the only surviving mention (`CLAIMS.md:749`, "AUC 0.77–0.84") is **descriptive** — contrasting map quality against `grid_r2 = −6.19` — not a ranking, so §24 does not reach it. **No edit made; editing correct text is not a correction.** | — |

### 3.2 Needs compute

| task | state | cost |
|---|---|---|
| **Version C Form 1 σ=0.25** | chained behind the live σ=0.10 run — **already handled, just wait** | ~2.5 h |
| **C0 at σ=0.25** | `versionc-gate-s025.json` absent. Closes the registered two-σ `n_eff` regression, currently one-σ only | ~1 h |
| **P3 cells 2 and 3** | verified stalled at **[1/50]** in `p3-d8-s025.log` and `p3-d8-s010.log` | ~1.3 h each |

### 3.2b ✅ CLOSED since the evening handoff

| task | outcome |
|---|---|
| `analyse_versionc_form1.py` | **DONE by the other agent** (`8a67741`), with `tests/test_versionc_kills.py` |
| **detector freeze + one-shot score** | **DONE.** Frozen at `b7dcc41` (code-free commit), scored at `debeffb`. **K-C7 FIRED, 0/50 both families** — FINDINGS **§37** |
| **E7 runner** | **DONE** (`bf4526d`). `e7-search-vs-id-rule-p.json` committed, zero new campaigns, both joins checked at run time — FINDINGS **§36** |
| **`qlogei` / σ=0.10 in E7** | **NOT missing — I was wrong.** Both come from `q57-search-vs-id.json`; Erratum 28 is withdrawn by **Erratum 32** |

### 3.3 🔴 BLOCKED ON A DECISION — do not take these unilaterally

| task | why it is blocked |
|---|---|
| **Task 6.1: σ = 0.10 on the γ ladder** | P7's `SIGMA = 0.25` is **deliberately** hardcoded — the source comment reads *"Not parameters — the only cell that carries…"*. This is a registration decision |
| **spread arms in E7 at σ=0.10** | only `doe`/`qlogei`/`qlognei` have a committed `oracle_best` there (q57). Adding the rest is a re-score, but it extends a committed artefact's shape |
| **`versionb` in E7 at 48 wells** | the only Version B row is `versionb_plate1_ceiling` at **40 wells**. A 40-well arm is not comparable to eight 48-well ones, so **SPADE cannot enter E7** until a 48-well row exists |

### 3.4 Open coordination item

Version C's commit **`bba2575`** claims *"the cross-fit cannot move §14's failures."* **§29
finds those failures were a draw-count artefact** with 1.5–3.5 pp residual bias. The two
tracks reached compatible conclusions by independent routes, but the claim as worded in that
commit no longer matches §29. **I offered to read their file; Joseph has not answered.**

---

## 4. Launch form — `setsid` does NOT exist on macOS

```
( nohup env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    .venv/bin/python -u scripts/<runner>.py <flags> > results/<log> 2>&1 < /dev/null & )
```

Verify **PPID 1** with `ps -o pid,ppid,args -p <pid>` before trusting it.
`scripts/drive_p6.sh` is the multi-family driver; it halts the programme on any non-zero exit.

---

## 5. Decisions taken 2026-08-22 — do not reopen without new evidence

1. **Ackley: in for the map, OUT of every DoE contrast**, labelled. Taken **before** the
   cross-family numbers existed — which matters, because ackley turns out to be the only
   family where `doe` wins.
2. **B3 subspace comparison: DROPPED.** It cannot be made from committed files at all.
   `K6-TECHNICAL-REPORT.md` §5.10.2's "B3 made it worse" **comes out entirely**.
   *(Removal still pending — §3.1.)*
3. **The IoU identity bound is DERIVED per row, not a fitted scalar** (§18). This changed a
   registered gate; the evidence is independent of the failure that prompted it.
4. **`N_DRAWS = 512` is a registered insufficiency.** Any containment claim at γ ≥ 0.95
   requires **≥ 1,024 draws**, and the residual bias at 4,096 requires the cross-fit.
5. **Superseded artefacts are kept on disk, not deleted** — `q59-map-rescore.SUPERSEDED-
   sigma_add-bug.json` and its checkpoint prefix. Corrections must stay auditable.

---

## 6. Rules that cost something to learn — do not rediscover these

* **`setsid` is not on macOS.** Use the subshell form in §4.
* **A run tied to an agent's turn dies with it.** The P6 merge was launched as a plain
  background call, the session restarted, and it died leaving no output.
* **Subagent findings die with the session too** — and **they are frequently wrong.** §34 is
  the case study: of the numbers one agent reported, **four did not survive the first check
  against disk** (errata 28–30). Have agents **write to disk as they go**, and **verify every
  number they hand you, including ones you asked for.**
* **A gate that does not cover the quantity the run exists to measure is not a gate for that
  quantity.** The `rule_a`/`oracle_best` gate passed at \|Δ\| = 0 while `sigma_pred` was 30.2%
  too narrow at σ = 0.10, because neither gated quantity touches `Yvar`.
* **A constant derived as `max(observed)` is a MEASUREMENT, never a BOUND** (Erratum 20). It
  gets **stricter** as the study grows — which is how it halted P6 at 120k checks per family.
* **Exact binomial tails, never normal approximations** (Erratum 21). The substitution turned
  §14's "one failure survives Holm" into an artefact: Holm ×72 is **0.2296, not 0.043**.
* **`plate1_only` is `never_rank_separately`** — it IS `lhs` at 48 wells, verified identical
  in 50 of 50 `regret_p` rows. **This trap has now been fallen into twice** (§19, §34.1).
* **Match the arithmetic, never widen a tolerance.** When a bound looks wrong, derive it.
* **Type I error volume read alone ranks silence first.** Use the symmetric difference.
* **Never write incrementally to a registered `results/` path** — write `<name>.partial`,
  promote once, carry `status` / `keys_present` / `keys_expected`.
* **`.gitignore` negations for every new artefact.** This repo has been bitten four times by a
  runner writing a registered file git then declined to track.
* **`kill $VAR` with a multi-line var is a silent no-op in zsh.** And `pkill` does not stop
  launchd-managed agents such as `ReportCrash` — it respawns with the same PID.

---

## 7. What NOT to claim

* **"SPADE's certificate fails at high assurance."** **WITHDRAWN** (§29) — 512-draw artefact.
* **`doe` beats BO.** It needs a specific terminal rule **and** a specific (d, σ) cell — and
  **§34.5 shows it does not even lead throughout at either σ.** At σ = 0.10 the lead is gone
  at budget 48 (p = 0.77) and inverts by 150. The defensible claim is about **terminal rules**.
* **"Screening is always fatal."** Three of four families; ackley reverses it.
* **"E7's gaps converge."** Only **excluding `doe`** (0.0776 → 0.0395). Including it they
  **diverge** (0.0890 → 0.1339).
* **Any E7 number at σ = 0.10, or any E7 `qlogei` number.** Erratum 28 — no committed source.
* **E7 as a committed result.** No file exists; §34.3 is an in-session join.
* **A "consistent ~30%" screening share.** Erratum: it is **19.8–28.4%** and not consistent;
  the apparent agreement was my own `sigma_add` bug (§26).
* **AUC rankings.** Superseded by error volumes wherever a ranking exists.
* **Any pooled containment figure.** Per-cell only, with `n`.
* **α\* as trustworthy or as discredited.** Neither reading resolves (§28, §31).
* **"Seven of eight arms hold."** It is **six**; the B3 comparison is withdrawn entirely.
* **Pooling `q52.doe.rule_c` with `fix1.rule_p`.** Three different non-maximising rules are on
  disk and they are not one estimator (§34.6).
* **Anything on levy or rosenbrock without its denominator.** 10 and 9 rankable cells of 48.

---

## 8. Version C — track status

**Ran as a parallel track under the ownership boundary.** Nothing here edited `replay.py`,
`campaign.py`, `surrogate.py`, `oracles.py`, `torch_oracle.py`, or any committed `results/`
file. Both tracks touched `designspace.py`; the additions are disjoint and every commit states
its insertion counts.

**8.1 — C0 closed §2.** `versionc-gate-s010.json`, 600 rows, gate clean at \|Δ\| = 0,
double-gated against `p3-k6-d6-s010.json` and `e2-grid.json`. Verdict
**`IDENTIFICATION_ARTEFACT`**: `versionb` rule-P regret **0.0792** against a registered branch
at 0.090. **§2 was not built.** Full result in FINDINGS §32.

**8.2 — Library and runners.** `boec/versionc.py`, `vorobev.conservative_estimate_split`,
`designspace.connected_components` / `component_report`; `run_versionc_gate.py`,
`run_versionc_form1.py`, `run_versionc_detector.py`, and the two analysers. All committed.

**8.3 — THE KILL LEDGER: eight registered, EIGHT ADJUDICATED.** ✅ Closed. Full result in
FINDINGS **§38**; verdicts in `results/versionc-kills-s010.json` / `-s025.json`.

Both re-scores are committed: `versionc-form1-s010.json` and `-s025.json`, **14,400 rows
each, gate clean at \|Δ\| = 0** across all 20 committed K6 columns.

| # | verdict | evidence |
|---|---|---|
| **K-C1** | ✅ **PASS — beaten, not merely met** | regret_P **0.0792** vs `r*` **0.0808** (`qlognei`, from `e2-grid.json` alone) → gap **−0.0016** |
| **K-C2** (hard stop) | ✅ **PASS — CLEARS** | {0.50: 0.940, 0.80: 1.000, 0.95: 1.000} against a committed nominal of exactly those three; `invariance_violated` **False** |
| **K-C3** | ✅ **PASS** both σ | 0.21089 / 0.35828, +0.00% against a +10% bar |
| K-C4 / K-C5 / K-C8 | **MOOT** | settled by C0 — no §2, and the other labels name the same campaign |
| K-C6 | **WOULD MISFIRE** | C1.2a |
| **K-C7** | 🔴 **FIRED** | §37 — 0/50 both held-out families. **Ship without Stage 0.** |

**🔴 Read §38.3 before quoting K-C2.** It passes **structurally, not evidentially**: it is
built from columns gated at \|Δ\| = 0 and Version C's selected sets are bit-identical to
Version B's, so it **could not have moved**. A pass is **not** an independent re-test of the
certificate — **F3 (§29) is what re-tested it.**

`analyse_versionc_form1.py` — the file 8.3 previously recorded as missing — **exists and is
what produced the table above.** Both collision risks are closed: one runner chain ran
start to finish, and the `.gitignore` negations are in (plus two more for the verdict files,
which were silently ignored until added).

**8.4 — The Version C commits are on `main`**, following this repository's convention and the
evaluation track's. Flagged because it departs from the global "branch first" rule.

**8.5 — The one thing that would otherwise be rediscovered.**
**Version C Form 1 requires ZERO new campaigns.** §1's three changes are scoring and reporting
changes only. With §2 unbuilt and K-C7 predicted, `versionc` ≡ `versionc_form1` ≡
`versionc_nodetect`, `versionc_fixed_m` is moot, and `versionc_random` ≡ the already-committed
`versionb_random`. **Form 1's design IS Version B's design**, and its regret number already
exists: the 0.0792 above. **Do not budget wells for it.**

---

# 🔴 OUTSTANDING WORK — labelled 2026-08-22, evening

## A. BLOCKED ON JOSEPH — one action, and it gates everything else

### A1. ✅ **RESOLVED 2026-08-23 — the repo is pushed.**

> The purge ran. `results/p6-families.json` is out of history and lives as 8 shards under
> `results/p6-families/` plus `results/p6-families.meta.json`, read via
> `scripts/load_p6_families.py`. 27 SHA citations were repaired at `7b72fef`, and
> `main` now tracks `origin/main` cleanly. **The original problem statement is kept below
> because the SHA-rewrite consequences it lists still explain why citations moved.**

#### Historical — the blocker as written on 2026-08-22

`results/p6-families.json` is **103.8 MB** against GitHub's **100 MB hard limit**, and an
earlier **208.8 MB** version of the same file is also in unpushed history (added at
`d191d69`). **Every push is rejected by the pre-receive hook.** Splitting the working-tree
file — done at `5a5d948`, 8 shards of ~22 MB plus a verified loader — **does not fix this**,
because a push sends the blobs that are in *history*, not the ones in the working tree.

**The only fix is a destructive history rewrite over 49 commits.** It was **blocked by the
permission classifier**, correctly. Joseph must run it or approve it:

```
git branch -f backup-before-blob-purge HEAD          # safety net first
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --index-filter \
  'git rm --cached --ignore-unmatch -q results/p6-families.json' \
  --prune-empty -- d191d69^..HEAD
git push origin main
```

**Consequences, stated before it is run:**

1. **Every commit SHA from `d191d69` onward changes.** ~50 SHAs are cited in
   `FINDINGS-SPADE.md`, `OPEN-QUESTIONS.md`, `CLAIMS.md` and this file — including the
   detector freeze `b7dcc41`, whose whole evidentiary value is *"committed before the
   scoring pass"*. **The ordering survives** (the freeze commit still precedes the scoring
   commit) but **the citations must be rewritten** from the old→new map. `filter-branch`
   preserves commit order and count, so the map is `git rev-list --reverse` before ∥ after.
2. **The other agent's clone diverges** and must reset to the rewritten `main`.
3. **`results/p6-families.json` leaves history entirely.** It stays on disk (ignored) and in
   the shards. Nothing else in the repo reads the single file — `scripts/run_p6_families.py`
   writes it; readers should move to `scripts/load_p6_families.py`.

**Do not attempt a partial push.** Only 7 of the 55 commits predate the blob.

### A2. Version C: nothing left blocked

K-C7 is **spent and fired**. The σ=0.10 γ-ladder question (Task 6.1) still needs a
registration decision — P7's `SIGMA = 0.25` is deliberately hardcoded.

## B. ✅ NO RUNS OUTSTANDING

| what | state |
|---|---|
| `run_versionc_form1.py` both σ | **DONE** — 28,800 rows, gate clean |
| `analyse_versionc_form1.py` (`8a67741`) | **DONE** — K-C1, K-C2 (hard stop) and K-C3 all adjudicated, **none fired** |
| P8 certificate off hill | **DONE** — 24,000 rows, 0 gate failures |

**The last data dependency before drafting is discharged.** Carry the two qualifications from
`FINDINGS-SPADE.md` §44.4 with any Version C number: K-C1's registered bar mixes estimands, so
the verdict is **parity and not a win**; K-C2 and K-C3 pass **structurally** rather than
evidentially, because a re-score reproduces its own source by construction.

## C. DONE THIS SESSION — do not redo

| item | commit | outcome |
|---|---|---|
| Version C kill audit | `7f32d08` | 8 registered, 0 adjudicated → fixed by the other agent at `8a67741` |
| **Detector freeze** | `b7dcc41` | code-free commit, so the ordering is checkable |
| Erratum 31 | `a797afa` | `_instance_seed` was dead code; my own freeze spec was wrong, caught pre-scoring |
| **K-C7 one-shot pass** | `debeffb` | **FIRED — 0/50 both families**, ranges nested inside the fit range |
| Erratum 32 | `9d97f64` | **Erratum 28 was wrong** — q57 had the "sourceless" numbers all along |
| E7 committed | `bf4526d` | zero new campaigns, both joins checked at run time |
| **SPADE into E7** | `7d34e7b` | 700-row fill, **0 gate failures**, all 48 wells |
| p6 shards | `5a5d948` | 8 × 22 MB + verified loader |

## D. EXPLICITLY NOT DOING — Joseph's call, 2026-08-22

Hill completeness (Task 6) · option (b) on α\* · more containment sweeps · a d=8 unscreened
arm (arithmetically impossible: 45 parameters, no CCD lands on 48 wells — **state it as a
permanent limit**).

## E. THEN STOP AND DRAFT

Five results, each survived an attempt to kill it. **The shortage is a draft, not data.**
