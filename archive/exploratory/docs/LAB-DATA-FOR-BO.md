# Lab data for the BO project

**What this file is.** A briefing on the wet-lab drop you put in the repo: what it physically is, what is already pulled out of it, what is still sitting in the files unused, and **exactly how it can feed Bayesian optimization**. Written so a later session (or a collaborator) can decide Campaign A vs B vs C without re-opening 300 files.

**Paths as of 2026-08-14.** Raw files live under `data/lab/raw/`. Human judgement lives under `data/lab/overlay/`. Machine tables live under `data/lab/derived/` (regenerate with `python scripts/build_lab_dataset.py`).

---

## Decision card (read this first)

The optimizer only learns from rows of **recipe (`x`) + one locked score (`y`)**. This drop can supply those rows for **your cells**. It cannot rewrite the fake-landscape tests (Phase 1) or the published Hall/Ogle replay (Phase 2).

| Question | Answer |
|---|---|
| Can the optimizer train on this today? | **No.** The official score column `y` is empty until a person signs CytExpert gates. |
| How many BO-shaped flow points exist? | **31** named tubes with a draft CD31% — in **three separate campaigns**, not one pile. |
| Which campaign can enter BO without inventing a keymap? | **Campaign A:** 12 FN/VTN coating tubes, 0.5–20 µg/mL, n = 1. |
| What does BO get after those 12 are signed? | Round 1 on NutriGene cells → software **asks** for round 2 → you run those conditions in **triplicate**. |
| What must stay frozen while Campaign A runs? | Differentiation protocol (CHIR / BMP4 / media) and background culture. Use Campaigns B and C as the freeze list, not as extra coating rows. |
| Can this replay Hall/Ogle? | **No.** Wrong proteins, wrong dose box (below their 22 µg/mL FN floor), wrong score (flow % ≠ photo area/DAPI). |
| Fastest action that actually advances BO | Sign the 12 CD31⁺ % into `data/lab/overlay/bo_primary_conditions.csv`. |

---

## 1. What you handed over

**Source.** Desktop folder `NutrigeneAI Lab Data`. Only `1. Relevant files for the BO project` went into git (~326 MB before de-duplication). School, visa, and personal files were left out on purpose.

**In the repo.** About **300 instrument files, 267 MB**, ingested 2026-08-13, later split:

| Folder | Role | Rule |
|---|---|---|
| `data/lab/raw/` | Instrument output, original names | Never edit. Checksums in `overlay/MANIFEST.sha256`. |
| `data/lab/overlay/` | Human sort: roles, gating record, the 12-row official table | Hand-maintained. Judgement lives here. |
| `data/lab/derived/` | Pipeline output | Disposable. Delete and re-run. |

**What the biology is.** iPSC toward endothelial (blood-vessel) cells, late July through 11 August 2026. Three kinds of experiment were dumped in one folder:

1. **Coating amounts** — fibronectin (FN) vs vitronectin (VTN) at 0.5, 1, 2.5, 5, 10, 20 µg/mL.
2. **Differentiation protocol** — CHIR timing, BMP4 on/off, finishing medium, passaging (two Word calendars).
3. **Culture / media history** — EGM, N2B27, 10% FBS, stem vs induction, T75 flasks, 3D, a culture nicknamed “sunny.”

Plus microscope photos, a June protein plate, and flow **controls** (unstained, isotype, sorted CD31⁺/−).

**Instrument.** All 52 flow files are **CytoFLEX LX** (Beckman Coulter, CytExpert), serial `BG17015`. They were first documented as a NovoCyte because the sidecar `.xit` is CytExpert’s format. The locked metric name is therefore `cytoflexlx-cd31-cd140a-2026-08-06`, not a NovoCyte string.

---

## 2. What is in the drop (inventory)

### 2.1 Flow cytometry — 52 files

Every live file: 38 detectors, **no colour compensation**, stats requested on **B525-A** and **Y585-A**.

**CD31 = B525-A** (measured from the 28 Jul sorted CD31⁺ vs CD31⁻ tubes, 20.8 point gap over the next detector). **CD140a = Y585-A** by elimination. Details: `derived/channel_identity.json` and `overlay/GATE.md`.

| Date | Folder under `raw/flow/` | Live tubes | Empty | What it is |
|---|---|---:|---:|---|
| 21 Jul | `2026-07-21/` | 16 | 0 | Media / passage / 3D / stem / “sunny” + unstained |
| 28 Jul | `2026-07-28/Exp_20260728_1/` | 7 | 0 | **Gating panel:** unstained, isotype, before-stain, CD31⁺, CD31⁻, CD31⁺ P3 |
| 6 Aug | `2026-08-06/Exp_20260806_1/` | 8 | 0 | Protocol wells 1–5 + leftover `3-1` + two unstained |
| 6 Aug | `2026-08-06/Exp_20260806_2/` | 0 | 8 | Same names, **0 cells** — aborted |
| 6 Aug | `2026-08-06/Exp_20260806_cd31-cd140a/` | 13 | 0 | **FN/VTN dose series + same-day unstained** |

### 2.2 Microscope photos — 121 images + 114 sidecars

Leica DMi8, mostly **phase contrast, 4X**, 27 Jul–11 Aug. EVOS stills `QS_2448`–`QS_2454` on 6 Aug (no well or dose labels).

The only photos that share **dose labels** with Campaign A are the **4 Aug** FN/VTN series. Those 12 frames were shot with the **same** optics (phase, 4X, exposure 19000, gain 1, light 45), so they can be compared to each other. They measure **how much of the field is covered by cells**, not CD31.

Other Leica days are well/FOV pictures, sort leftovers (`fenxuan`), IEC P6, “mia dish,” and a 28 Jul `c1`/`k10`/`con` series whose factor key is **not in the repo**.

### 2.3 Protocols — 2 Word files

`raw/protocols/IPSC分化EC-2.docx` and `IPSC分化EC-3.docx`. Day-by-day calendars: which well got which CHIR dose, BMP4, medium, passaging, sort day. Extracted table: `derived/protocol_wellmap.csv`. The orphan tube `3-1.fcs` is protocol v2 (the file titles itself “3-1”).

### 2.4 Plate reader — 1 Excel file

22 June 2026, absorbance **562 nm**, 96 wells, Multiskan SkyHigh. This is a **total-protein (BCA)** plate. The layout sheet is all `X` (unlabelled). It can never be a CD31 score.

### 2.5 What never entered git

Duplicate zips (`Flow.zip`, `0804.zip`); empty instrument `Backup/` folders; school/personal files; a second identical EVOS copy.

---

## 3. How many points — counted the way BO cares

**Files are not points.** A point is a known recipe (`x`) plus one locked score (`y`).

| Count | What | For the optimizer? |
|---:|---|---|
| **12** | FN/VTN coating tubes | **Campaign A.** Official table exists; `y` still empty. |
| **6** | 6 Aug wells 1–5 + `3-1` | **Campaign B** (protocol knobs). |
| **13** | 21 Jul named cultures | **Campaign C** (media / flask / 3D). Some are two passages of the same recipe. |
| **31** | A + B + C | Draft CD31% exists for all 31. **Do not dump into one model.** |
| **12** | Matching Leica coverage | **Different score.** A coverage campaign, not CD31. |
| **0** | Signed official `y` | Until CytExpert gates are copied into `overlay/bo_primary_conditions.csv`. |
| 10 | Unstained / ISO / Before | Gates only. Not recipes. |
| 8 | Empty exp 2 | Not points. |
| 3 | Sorted CD31⁺ / CD31⁻ / P3 | Already picked cells. Used to **name the detector**, not as experiments. |

### 3.1 Campaign A — draft CD31% (unsigned)

Software scores, **all recorded events**, vs same-day unstained 99th percentile. Source: `derived/candidate_campaign_coating_flow.csv`. Changing the cutoff from 95th to 99.9th percentile moves each number by about **9–14 points**. That is why they are `y_candidate`, not `y`.

| Dose µg/mL | 0.5 | 1 | 2.5 | 5 | 10 | 20 |
|---:|---:|---:|---:|---:|---:|---:|
| **FN** | 31.7 | 47.3 | 46.8 | 38.7 | 46.3 | 36.4 |
| **VTN** | 22.6 | 40.1 | 39.6 | 41.3 | 34.3 | 39.8 |

The only pattern that survives every cutoff: **0.5 µg/mL is weakest for both coatings.** Above 1 µg/mL there is **no clean “more coating → more CD31” line.**

### 3.2 Campaign B — draft CD31% (unsigned), same day and machine as A

| Tube | Draft CD31% | Recipe (protocol v3, except `3-1`) |
|---|---:|---|
| well 1 | 7.2 | CHIR day 2, **no BMP4**, finish on 10% FBS+EGM2, passaged |
| well 2 | 1.8 | CHIR day 3, **no BMP4**, stay on EC induction, not passaged |
| well 3 | 8.6 | CHIR day 2, **BMP4 25**, finish on 10% FBS+EGM2, passaged |
| well 4 | 2.2 | CHIR day 3, **BMP4 25**, stay on EC induction, not passaged |
| well 5 | 7.8 | CHIR days 2+3, BMP4 25, finish on 10% FBS+EGM2, passaged |
| `3-1` | 4.8 | Protocol **v2** leftover, not the same map as wells 1–5 |

Protocol wells sit far below the coating panel (1.8–8.6% vs 22–47%). Control choice (US-new vs US-old) explains only ~1.6 points. The gap is real: **different experiment**, not “worse coating data.”

BMP4 only is estimable: well 1→3 **+1.3** points, well 2→4 **+0.4**. Small. CHIR day, finishing medium, and passaging **change together**, so the big ~4× swing (day-2/EGM2/passaged vs day-3/EC-induction/not-passaged) cannot be blamed on one knob.

### 3.3 Campaign C — draft CD31% (unsigned), 21 Jul, that day’s unstained

Do not gate these against 6 Aug unstained.

| Recipe | Tubes | Draft CD31% |
|---|---|---|
| 10% FBS | p1, p2 | 0.57, 0.40 |
| Stem | p1, p2 | 0.41, 0.33 |
| EC induction | p1, p2 | 0.52, 0.22 |
| T75 | p1 | 0.38 |
| N2-3D | P0, p1 | 2.1, 6.4 |
| EGM-3D | p0, p1 | 5.5, 8.7 |
| “sunny” | p3, p3-1 | **55.0, 69.9** |

Most named media sit near zero. EGM-3D is the only named medium with a modest CD31 signal. “Sunny” is an outlier (likely a different line or already-enriched cells) — not a coating level and not a media win to copy blindly.

### 3.4 Coverage on the 12 dose-matched photos (not CD31)

4 Aug, phase contrast. FN 0.5 has the **highest** coverage (0.42) and the **lowest** flow CD31%. Different day, different quantity. Photos **do not confirm** the 12 flow scores.

---

## 4. Three BO campaigns (do not mash)

One optimizer loop. One metric per campaign. Three search spaces.

### Campaign A — coating dose (the one that matches this project’s story)

| | |
|---|---|
| **`x`** | Coating type (FN = 0, VTN = 1) and dose 0.5–20 µg/mL. Coded dose = `(dose − 0.5) / 19.5`. This [0, 1] is **this box**, not Hall/Ogle’s cube. |
| **`y`** | CD31⁺ % of parent. Version `cytoflexlx-cd31-cd140a-2026-08-06`. |
| **Rows** | 12 tubes, n = 1. Empty `y_sd`; the lookup uses an SD floor until you repeat. |
| **Config** | `configs/lab/coating_2026-08-06.yaml` |
| **Loader** | `boec.lab.evaluator.load_lab_evaluator` — **raises** until `y` is filled and `status` is `gated`. |
| **BO contribution** | After sign-off: **round 1** on NutriGene cells. Fit. **Ask round 2.** Run those conditions in triplicate. Also: evidence that this lab already works **below** the published 22 µg/mL FN floor, and that above 1 µg/mL the draft curve is weak/flat — useful before anyone spends a 14-day round on six ECM proteins. |

Do **not** inject these 12 into the Phase 1/2 six-protein cube (no collagens, no laminins).

### Campaign B — differentiation protocol

| | |
|---|---|
| **`x`** | CHIR schedule, BMP4 0 vs 25 ng/mL, finishing medium, passaged yes/no. |
| **`y`** | Same CD31% **only if** stain, machine, and gate version stay the same — still a **separate** campaign because `x` is different. |
| **Rows** | 6 live tubes. |
| **BO contribution** | **Freeze** the protocol so Campaign A is about coating, not CHIR day. Or design a **new** protocol campaign with one change at a time. Do not add these 6 as extra FN/VTN doses. |

### Campaign C — media / vessel / 3D

| | |
|---|---|
| **`x`** | Named recipes (13 tubes, ~7 names). |
| **`y`** | Draft CD31% vs **21 Jul** unstained only. |
| **BO contribution** | **Freeze background culture** before a coating BO. EGM-3D vs near-zero stem/FBS is the briefing. Hold media fixed in Campaign A. |

---

## 5. Already extracted (do not redo)

`python scripts/build_lab_dataset.py` (~31 s) writes `derived/`:

| File | Content |
|---|---|
| `file_index.csv` | Every file, role, checksum |
| `flow_acquisitions.csv` | 52 FCS: time, events, compensation flag, aborted |
| `channel_identity.json` | CD31 = B525-A |
| `flow_positivity_candidate.csv` | Draft CD31% and CD140a% + cutoff sweep |
| `candidate_campaign_coating_flow.csv` | The 12 coating rows as unsigned candidates |
| `candidate_campaign_coating_morphology.csv` | 12 coverage fractions, optics-matched |
| `image_features.csv` | 121 images: coverage, focus, comparability key |
| `protocol_wellmap.csv` | Well → CHIR / BMP4 / medium / passaging |
| `plate_reader.json` | BCA verdict |
| `overlay/GATE.md`, `overlay/BO-PURPOSE.md` | Human-readable sort and what is still unsigned |

Code already **refuses** unsigned tables (`GatingIncompleteError`) and can look up **signed** coating rows without colliding nearby doses (`ContinuousLookupEvaluator`). Phase 2’s integer lookup is untouched.

---

## 6. Still in the files — not extracted yet

None of this creates a six-protein Hall/Ogle table. The largest remaining extract is **human**, not computational.

| Still in the files | What you would get | BO use |
|---|---|---|
| **Live + singlet gates in CytExpert** | The only honest path from draft % → official `y` | **Required** before Campaign A can `tell()` |
| **Single-stain compensation controls** | **Not in the drop.** Two-colour panel was run uncompensated | If you need CD31⁺CD140a⁺ purity, **re-run**; you cannot invent controls |
| **CD140a% as its own campaign** | Drafts already ~6–10% on coating tubes | Second metric, second table, **never** a second column beside CD31 |
| **Well-labelled Leica days (27 Jul–11 Aug)** | Coverage vs protocol well, if photo names are mapped to the Word calendar | Attachment QC, not CD31 `y` |
| **28 Jul `c` / `k` / `con` photos** | Looks designed; **key missing** | Useless until someone writes what c1/k10/con means |
| **EVOS `QS_*`** | Coverage can be computed; **no labels** | No `x` |
| **FIJI CD31 area on photos** | Needs fluorescent CD31 images. These Leicas are **phase contrast** | Cannot extract Hall/Ogle-style CD31/DAPI from this drop |
| **Plate 562 nm** | Absorbance grid exists; layout unlabelled | Protein QC only |
| **Event-level FCS** | Full cell lists are in the files | Re-gate later; never average aborted files to 0% |
| **`fenxuan` / IEC P6 / “mia dish”** | Other line / sort leftover / operator dish | Not experimental arms |

---

## 7. What this drop contributes to the BO project

### It does contribute

1. **Starts Phase 3 — the ask/tell loop on NutriGene cells.** After sign-off, Campaign A is 12 real `(x, y)` rows. The model can propose round 2. That is the first time the project uses *your* cells instead of a formula or a published figure.

2. **Locks the in-house score.** CD31% on CytoFLEX LX, B525-A, version `cytoflexlx-cd31-cd140a-2026-08-06`. Every later round must keep that identity. Photos and BCA stay out.

3. **Informs the box.** You already measured **below** the published 22 µg/mL FN floor. Draft curves are weak/non-monotonic above 1 µg/mL. That is evidence for “what range is worth optimizing” before a 14-day six-protein round.

4. **Gating SOP.** 28 Jul sorted panel + 6 Aug unstained are the reference for every later coating tube.

5. **Freeze list.** Campaigns B and C tell you what to **hold fixed** so Campaign A is about coating.

6. **Honesty machinery.** Checksums, aborted-file errors, `y_candidate` vs `y`, metric mismatch errors — unsigned software % cannot silently become a paper claim.

### It does not contribute

| Tempting claim | Why it is false |
|---|---|
| “We validated BO on lab data” | No model-proposed batch, n = 1, unsigned `y`. |
| “We can replay Hall/Ogle cheaper with this folder” | Wrong proteins, wrong box, wrong score. Phase 2 already used the published table. |
| “31 points train one GP” | Three different `x` spaces. Mixing them attributes CD31 to the wrong knob. |
| “12 photos confirm the 12 flow scores” | Coverage vs CD31% **disagree**. |
| “Phase 1 numbers should change” | Phase 1 is a planted math test. Lab data does not rewrite E1–E4. |

### Where it sits in the repo

```
data/oracles/     Phase 1  — fake landscapes (done)
data/published/   Phase 2  — Hall/Ogle digitized figures (replay already run; BO not faster than random on that table)
data/lab/         Phase 3  — this drop: round-1 seed *after* human sign-off, then ask round 2
```

The paper’s current strength is Phase 1 (how you score DoE vs BO) plus a null Phase 2 replay. This lab drop is **not** that paper’s dataset. It is the start of **proof on your system**, which the original 14-day plan called out of scope.

---

## 8. Recommended path (order matters)

1. **Sign the 12.** CytExpert: live + singlet + CD31 on B525-A vs `us.fcs` in the same folder. Paste % into `overlay/bo_primary_conditions.csv`. Update any test that currently requires empty `y` in the **same** commit.
2. **Freeze protocol and media** using Campaigns B and C as the briefing, not as extra rows in the coating table.
3. **Load Campaign A** with `load_lab_evaluator`. Confirm it no longer raises.
4. **Ask round 2** — software proposes the next FN/VTN conditions; a scientist approves; run **triplicate**.
5. **Compare** best of the original 12 vs best of the model batch. That comparison is the first in-house BO result.
6. Only then consider a larger ECM list or a clean protocol factorial. **This drop does not contain that design.**

Until step 1, the contribution is **understanding and plumbing**, not training data.

---

## 9. Where to look next

| File | Open it for |
|---|---|
| `data/lab/README.md` | Tree: raw / overlay / derived |
| `data/lab/overlay/BO-PURPOSE.md` | Which files may become `x` |
| `data/lab/overlay/GATE.md` | Channel ID, draft %, what a human must still draw |
| `data/lab/overlay/bo_primary_conditions.csv` | Official 12 rows (`y` empty) |
| `data/lab/derived/candidate_campaign_coating_flow.csv` | Draft % for those 12 |
| `data/lab/derived/flow_positivity_candidate.csv` | All scored tubes (the 31 + controls) |
| `data/lab/derived/protocol_wellmap.csv` | Well → CHIR/BMP4/media |
| `configs/lab/coating_2026-08-06.yaml` | Campaign A search space |
| `docs/superpowers/specs/2026-08-14-lab-data-pipeline-design.md` | How the pipeline was built |
| `docs/archive/build-phase/project_plan.md` Part E | What a real Phase 3 round was specified to look like (§E.1–E.5). ⚠️ **Moved 2026-08-14** by the documentation triage, which labelled the file build-phase scaffolding. Part E is **not** scaffolding — it is the live Phase 3 specification, and the archive index now says so. |
