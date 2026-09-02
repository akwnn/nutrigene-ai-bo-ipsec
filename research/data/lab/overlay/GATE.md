# Gating record — 2026-08-06 CD31 / CD140a

**Status: channel identity RESOLVED by measurement. Percentages are CANDIDATE and
unsigned.** `bo_primary_conditions.csv` `y` is still empty on purpose.

Everything below was produced by `python software/scripts/build_lab_dataset.py` and lands in
`derived/`. Regenerating is cheap (~31 s); nothing here is hand-typed.

---

## 1. Which detector is CD31 — answered

The earlier draft of this file recorded CD31 and CD140a as `_ungated_`, because neither
the filenames nor the FCS `$PnS` keywords name an antibody: they carry detector names
(`B525-A`, `Y585-A`) and nothing else.

That was solvable from data already in the drop. `raw/flow/2026-07-28/Exp_20260728_1/`
holds a **sorted reference panel** — `CD31+.fcs`, `CD31-.fcs`, `ISO.fcs`, `US.fcs`.
Whichever detector separates CD31+ from CD31− *is* CD31.

| | |
|---|---|
| **CD31** | **B525-A** |
| **CD140a** | **Y585-A** (by elimination; it is the other stat channel of the panel) |
| Statistic | percent-positive above the isotype 99th percentile, CD31+ minus CD31− |
| Winner | B525-A, **20.76 pp** excess |
| Runner-up | B610-A, 12.37 pp — **margin 8.39 pp** |
| Scanned against | all 16 fluorescence area detectors, not just the two expected |

Full table: `derived/channel_identity.json`.

**Why the runner-up does not threaten the call.** B610-A sits on the same blue laser as
B525-A, and `$SPILLOVER` on every file is the exact identity with `USCOMP = False` —
*no compensation was applied at acquisition*. Uncompensated spillover flows out of the
bright channel into its neighbours, so B610-A's signal is evidence **for** B525-A being
the real stain, not evidence against it. Y585-A places 7th at 4.64 pp.

**Why the statistic is excess-positive and not a median comparison.** The sorted
`CD31+` sample is bimodal: its B525-A median sits *below* `CD31-`'s while its 90th
percentile sits ~17× above. Any central-tendency rule ranks the correct answer last.
`software/tests/test_lab_gating.py::test_median_comparison_would_have_picked_the_wrong_channel`
pins this so nobody "simplifies" it later.

**Corroboration.** CD140a (PDGFRα, mesenchymal) reads 6–10% across all 12 coating
tubes. If the assignment were reversed, this panel would describe a predominantly
mesenchymal culture with a rare endothelial fraction — the opposite of the experiment's
purpose. Consistency, not proof.

**Panel match.** The 07-28 reference and the 08-06 primaries share instrument, serial,
detector list and parameter count, so the identity transfers between the two days.

---

## 2. Instrument — corrected

Every one of the 52 FCS files reports:

```
$CYT   = CytoFLEX LX          (Beckman Coulter, CytExpert; .xit is CytExpert's format)
$CYTSN = BG17015
$PAR   = 38,  $PnR = 16777216
```

**This drop was documented as a NovoCyte.** It is not. The metric string has been
corrected to `cytoflexlx-cd31-cd140a-2026-08-06` in `bo_primary_conditions.csv` and
`BO-PURPOSE.md`. `metric_protocol_version` is meant to be the immutable name of a
measurement, so naming the wrong instrument in it is a data-integrity problem rather
than a typo.

---

## 3. Candidate percentages — what they are and are not

`derived/candidate_campaign_coating_flow.csv`, CD31⁺ % of **all recorded events**:

| dose µg/mL | 0.5 | 1 | 2.5 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| **fibronectin** | 31.69 | 47.35 | 46.85 | 38.66 | 46.33 | 36.45 |
| **vitronectin** | 22.56 | 40.11 | 39.61 | 41.27 | 34.25 | 39.85 |

The one claim that survives every threshold choice: **0.5 µg/mL is the weakest dose for
both coatings.** There is no monotonic dose response above 1 µg/mL.

### Three judgement calls that arithmetic cannot settle

1. **No compensation.** `$SPILLOVER` is identity. A two-colour panel run uncompensated
   inflates double positives. Correcting this needs single-stain controls that are not
   in the drop.
2. **No live/singlet gate.** These percentages are over *all recorded events*. The
   FSC-H/FSC-A ratio has MAD 0.24 here, so a ±3 MAD singlet gate keeps 99.5% of events
   — that is not a gate. A human drawing FSC/SSC live and singlet gates in CytExpert
   will get different, and probably better, numbers.
3. **The threshold is a convention.** Positive means "above the same-day unstained
   99th percentile". On `f5.fcs`, CD31% runs 47.1 → 33.5 as that percentile goes
   95 → 99.9. Every candidate row therefore carries `y_candidate_p95`,
   `y_candidate_p99_9` and `y_spread_pp`; spreads here are 9–14 pp.

Control choice matters less: gating `well 3` against `US-new` gives 8.56% and against
`US-old` 10.14%, ≈1.6 pp.

---

## 4. To finalise — the human steps

1. Open the 12 primaries in CytExpert against `us.fcs` (same folder, same day).
2. Draw and **record here** the FSC/SSC live gate and the singlet gate.
3. Decide whether uncompensated B525/Y585 is acceptable for the CD31 number, or whether
   the series must be re-run with single-stain controls.
4. Copy the agreed CD31⁺ % of parent into `bo_primary_conditions.csv` column `y`.
5. Leave `y_sd` empty — n = 1 per level; `LookupEvaluator`'s `sd_floor` imputes.
6. Set `status` to `gated`, and update
   `software/tests/test_lab_manifest.py` / any test asserting `y` is empty **in the same commit**.
   Do not leave a test demanding emptiness after gating.

Gate geometry, to be filled by hand when step 2 happens:

- Live (FSC-A × SSC-A): _not drawn_
- Singlet (FSC-H × FSC-A): _not drawn_
- CD31 gate on B525-A: _not drawn_ (software used unstained p99 = 16332.9)
- CD140a gate on Y585-A: _not drawn_

CD140a⁺ % is a **second metric**. If scored, it is a second campaign with its own
`metric_protocol_version`, never a second column beside CD31.

---

## 5. Do not

- Do not paste `y_candidate` into `y` without doing §4. The column names differ on
  purpose, and `software/tests/test_lab_dataset.py` enforces that no derived table ships a
  column called `y`.
- Do not mix these percentages with the Leica coverage numbers
  (`coverage_frac_phase`) or with Hall/Ogle's `CD31_area_per_DAPI`. Three different
  measurements, three metric identities. Requirement 7.
- Do not gate a tube against an unstained control from another day.
