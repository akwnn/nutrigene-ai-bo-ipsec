# Which lab files are for Bayesian optimization

Every file under `data/lab/` has a role in `bo_file_roles.csv`. This note is the scientific sort: what the optimizer is allowed to see, what it needs in order to see it, and what must stay out.

> **Update 2026-08-14 — three of the blockers below have been resolved by reading the files.**
> Run `python scripts/build_lab_dataset.py` (~31 s) to regenerate `derived/`.
>
> | Blocker as written below | Status |
> |---|---|
> | "Which detector is CD31 is not in the filenames" | **Resolved.** B525-A, by 8.39 pp over the runner-up, from the 07-28 sorted panel. See [`GATE.md`](GATE.md). |
> | "`blocked_needs_keymap` — not until a well→condition table exists" | **Resolved.** The map was inside `protocols/IPSC分化EC-3.docx`. See `derived/protocol_wellmap.csv`. But CHIR timing, terminal medium and passaging are *mutually confounded* across those five wells — only the BMP4 contrast is estimable. |
> | "`plate-reader/…` — wrong metric" | **Confirmed, and identified.** 562 nm is the BCA readout; it is a total-protein plate, and its layout sheet is verifiably all `X`. It can never be a CD31 outcome. |
>
> Unchanged: **`y` still does not exist.** The pipeline produces `y_candidate` with a
> sensitivity sweep and `status=awaiting_human_signoff`. Promotion is a human act.
> Also corrected: the instrument is a **CytoFLEX LX**, not a NovoCyte.

**The optimizer only eats `(x, y)` rows** — coded factor levels plus one locked metric. Images, protocols, and gating FCS are not `y`. Requirement 7 still holds: CD31% by flow and CD31 area by immunofluorescence are different numbers and must never share a campaign.

Raw paths are unchanged. Moving 255 MB of already-pushed binaries would only rewrite git history. The sort is this overlay.

## The one-screen answer

| Role | Count | Enters the optimizer? |
|---|---:|---|
| **`bo_primary`** | 12 FCS | **Yes, after gating** — the only files that already encode both a numeric coating level and a CD31/CD140a acquisition |
| **`bo_gating`** | 13 FCS | No. Required to extract `%` from the 12 primaries |
| **`bo_morphology_matched`** | 13 JPEGs | No. Same FN/VTN series, morphology QC only |
| **`bo_protocol`** | 2 docx | No. Locks the *other* experiment (CHIR/BMP4/media by well) |
| `blocked_needs_keymap` | 83 | Not until a well→condition table exists |
| `assay_dev` | 29 | No. Media / passage / gel / 1% FBS work. Different search space |
| `not_for_bo` | 24 | No. Empty FCS, unlabeled EVOS, sort leftovers, Abs@562 |
| `instrument_sidecar` | 124 | No. `.metadata`, `.xit`, `.xml` |

## 1. Use for BO — the 12 primary FCS files

These are the only in-house files that can become Phase 3 rows without inventing a condition map. They are a **one-factor-at-a-time coating titration**, acquired 2026-08-06, panel named `cd31-cd140a`, CytoFLEX LX detectors **B525-A** (CD31) and **Y585-A** (CD140a).

Directory: `flow/2026-08-06/Exp_20260806_cd31-cd140a/`

| File | Factor `x` | Physical level | Events | Proposed coded `x` on [0, 20] µg/mL |
|---|---|---:|---:|---:|
| `f0.5.fcs` | fibronectin | 0.5 µg/mL | 25,897 | 0.025 |
| `f1.fcs` | fibronectin | 1 | 40,624 | 0.05 |
| `f2.5.fcs` | fibronectin | 2.5 | 35,434 | 0.125 |
| `f5.fcs` | fibronectin | 5 | 53,458 | 0.25 |
| `f10.fcs` | fibronectin | 10 | 39,548 | 0.50 |
| `f20.fcs` | fibronectin | 20 | 50,920 | 1.00 |
| `v0.5.fcs` | vitronectin | 0.5 µg/mL | 37,657 | 0.025 |
| `v1.fcs` | vitronectin | 1 | 39,077 | 0.05 |
| `v2.5.fcs` | vitronectin | 2.5 | 42,140 | 0.125 |
| `v5.fcs` | vitronectin | 5 | 33,486 | 0.25 |
| `v10.fcs` | vitronectin | 10 | 42,275 | 0.50 |
| `v20.fcs` | vitronectin | 20 | 36,891 | 1.00 |

`us.fcs` in the same folder is **gating**, not a 13th condition.

Skeleton table (empty `y`): `bo_primary_conditions.csv`.

### What this is, and what it is not

- **It is** a 12-point OFAT screen of two mutually exclusive coatings. That can seed a 1-D GP per coating, or a 2-D space `{coating_type categorical, dose continuous}` once `y` exists.
- **It is not** a Hall/Ogle 6-protein factorial. Collagen I/IV and laminins 111/411/511 were not varied. These 12 points cannot replay Phase 2 and cannot skip Phase 3 round 1 for a 6-D ECM campaign.
- **Fibronectin here is 0.5–20 µg/mL.** Hall/Ogle’s attachment floor was 22 µg/mL. This drop sits *below* that floor, which is scientifically the interesting side of the published failure — but it is a different box, so it must not be coded onto the Phase 1/2 `[0,1]` ECM cube.
- **`y` does not exist yet.** Filenames are not CD31%. Someone still has to gate live/singlet → CD31⁺ and (optionally) CD140a⁺ and write percentages into `bo_primary_conditions.csv`. Until that happens, the optimizer has nothing to `tell()`.
- **n = 1 tube per level.** No replicate SD. `Yvar` will have to be imputed (contract requirement 5) until the lab repeats the series.

Locked metric, when gated:

```
metric_name: CD31_pct_flow
metric_unit: percent_of_parent
metric_protocol_version: cytoflexlx-cd31-cd140a-2026-08-06
```

Do not later mix that column with a FIJI CD31-area/DAPI number from the Leica JPEGs.

## 2. Needed for BO — gating and matched morphology

**Gating (not conditions).** Use these to set the CD31/CD140a gates on the 12 primaries. They must not appear as `x` rows.

| File | Use |
|---|---|
| `flow/2026-08-06/Exp_20260806_cd31-cd140a/us.fcs` | Unstained, same day and panel as the primaries |
| `flow/2026-07-28/Exp_20260728_1/US.fcs` | Unstained |
| `flow/2026-07-28/Exp_20260728_1/ISO.fcs` | Isotype |
| `flow/2026-07-28/Exp_20260728_1/CD31+.fcs` | Positive reference |
| `flow/2026-07-28/Exp_20260728_1/CD31-.fcs` | Negative reference |
| `flow/2026-07-28/Exp_20260728_1/CD31+P3.fcs` | CD31⁺ P3 |
| `flow/2026-07-28/Exp_20260728_1/Before.fcs`, `BEFORE2.fcs` | Pre-stain |
| `flow/2026-08-06/Exp_20260806_1/US-old.fcs`, `US-new.fcs` | Unstained, same cytometer day as Exp_1 |
| `flow/2026-07-21/US.fcs`, `us-2.fcs`, `us-23.fcs` | Unstained for the media screen only |

**Matched morphology (not `y`).** Same µg/mL labels as the primaries, Leica 2026-08-04:

- FN: `fib 0-5`, `fib 1`, `fib 2-5`, `fib5`, `fib10` / `Fib 10%`, `fib20`
- VTN: `vtn 0-5`, `vtn 1`, `vtn 2-5`, `vtn5`, `vtn 10`, `vtn 20`

These can corroborate attachment vs concentration. They become BO data only if someone scores a *different*, versioned metric (e.g. confluence). That would be a second campaign, not a second column on the flow campaign.

## 3. Not for this BO campaign

**Protocol / induction screen (blocked until a well map is locked).**  
`flow/2026-08-06/Exp_20260806_1/well 1.fcs` … `well 5.fcs` and `3-1.fcs` have 22k–39k events, so they are real acquisitions. Filenames are well IDs. `protocols/IPSC分化EC-3.docx` assigns those wells CHIR µM, BMP4 on/off, and terminal media (10% FBS + EGM2 vs staying on EC induction). That is a **protocol** search space, not the ECM cube. Eligible for a later Phase 3 campaign if the well map is written down; not mixable with the 12 coating tubes.

**Media / passage development.**  
`flow/2026-07-21/` (`10%FBS`, `EGM-3D`, `N2-3D`, `stem`, `ec indu`, `T75`, `sunny-p3`) and the 08-04 `stem` / `gel` / `1%fbs` / `mia` images. Useful lab history. Wrong factors for the Hall/Ogle-calibrated optimizer.

**Empty.**  
`flow/2026-08-06/Exp_20260806_2/*.fcs` — 0 events.

**Unlabeled or key-missing morphology.**  
Leica 07-27 through 08-11 well/FOV images, the 07-28 `c1`/`c10`/`k1`/`k10`/`con` series (looks designed; the factor key is not in the repo), EVOS `QS_*`, `fenxuan` / IEC P6 dishes.

**Wrong metric.**  
`plate-reader/2026-06-22_endpoint-abs-562.xlsx` — absorbance at 562 nm, 22 June, no condition labels. Not CD31.

## 4. Plan to turn the 12 files into optimizer input

1. Gate the 12 primaries against `us.fcs` (same folder) and the 07-28 CD31±/ISO panel. Record the gate geometry (FSC/SSC live, singlets, CD31, CD140a) in one paragraph next to the CSV so the metric can be versioned.
2. Fill `y` = CD31⁺ % of parent (and optionally CD140a⁺ % as a *separate* metric, not a second column of the same campaign) into `bo_primary_conditions.csv`.
3. Declare the search space as either:
   - two 1-D problems (FN-only, VTN-only), or
   - `{coating: categorical {FN, VTN}, dose_ug_mL: continuous 0.5–20}`.
   Do **not** inject these points into the 6-D Hall/Ogle cube.
4. Impute `Yvar` (n = 1). Do not pretend tubes are replicates.
5. Only then can `HumanEvaluator` / a lookup table `tell()` the campaign. Twelve OFAT points are a seed, not a finished Phase 3 round 1.

If the lab wants the CHIR/BMP4 wells in BO as well, that is a second spec: lock the protocol-v3 well map, pick one metric, keep it out of the coating campaign.
