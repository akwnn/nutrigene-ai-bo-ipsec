# Lab Data Pipeline — Design

**Status:** built and running. `python scripts/build_lab_dataset.py` (~31 s).
**Supersedes:** `docs/superpowers/plans/2026-08-13-lab-data-bo-lookup.md` — now fully implemented, with corrections (see §8).

## 1. Goal

Use every file in `data/lab` — all 306 — rather than the 12 that can become optimizer
input. "Use" means each file is opened, parsed, and contributes a row to a derived
table: an outcome where one is defensible, provenance or QC where it is not.

The constraint that shapes everything: `BO-PURPOSE.md` is right that only 12 files can
become `(x, y)` rows, and requirement 7 forbids mixing metrics. So the pipeline is
built to *read everything and promote nothing*. Promotion is a human act.

## 2. Architecture

`src/boec/lab/`, seven modules, each independently testable:

| Module | Input | Output | Depends on |
|---|---|---|---|
| `manifest.py` | the tree | file index + checksum verdicts | stdlib |
| `fcs.py` | 52 `.fcs` | acquisition summaries, event arrays, logicle | `flowio`, `flowutils` |
| `gating.py` | reference panel + tubes | channel identity, percent-positive | `fcs` |
| `imaging.py` | 121 images + 114 sidecars | coverage, focus, comparability | `scikit-image` |
| `protocol.py` | 2 `.docx` | well→condition map, confounding | stdlib |
| `plate.py` | 1 `.xlsx` | plate structure, assay identification | stdlib |
| `dataset.py` | all of the above | 10 derived tables + `RUN.json` | `pandas` |

`scripts/build_lab_dataset.py` is the entry point. Output goes to `data/lab/derived/`,
which is excluded from the index so the pipeline is not a function of its own last run.

## 3. Dependency decision

`flowkit` was rejected: it resolves **pandas 3.0.5 → 2.3.3**, and every number in
`docs/RESULTS.md` was produced under 3.0.5. Its engine — `flowio` (reference FCS
reader) and `flowutils` (C compensation and Moore & Parks logicle) — installs with zero
downgrades and is what the pipeline uses. `scikit-image` installs clean. Pillow arrives
transitively with matplotlib. `.docx` and `.xlsx` are zips of XML, so `zipfile` +
`xml.etree` covers both and openpyxl is not needed.

Hand-rolling logicle was the alternative and is the easier thing to get quietly wrong:
a mis-parameterised biexponential moves every gate and fails as a plausible percentage
rather than a crash.

## 4. What reading the files established

Facts that were wrong or unknown in the overlay, now settled by measurement:

1. **Instrument.** All 52 FCS report `$CYT = CytoFLEX LX`, serial BG17015, CytExpert.
   The drop was documented as a NovoCyte — the `.xit` sidecar is CytExpert's format,
   which is what caused the misreading. The metric string named the wrong instrument.
2. **CD31 = B525-A**, by 20.76 pp excess-positive against all 16 fluorescence
   detectors, margin 8.39 pp over B610-A. CD140a = Y585-A by elimination.
3. **No compensation was applied.** `$SPILLOVER` is the exact 32×32 identity,
   `USCOMP = False`. This inflates double positives and explains B610-A's second place.
4. **`$PnR = 2²⁴`**, so logicle `t` must be 16777216, not the flowutils 262144 default.
5. **The well keymap existed** inside `IPSC分化EC-3.docx`, and the orphan `3-1.fcs` is
   protocol v2, which titles itself "3-1".
6. **The plate is a BCA total-protein plate** (562 nm, duplicate standard series), and
   its layout sheet is verifiably all `X`.
7. **"235 microscopy" is 121 images + 114 sidecars**, not 235 images.

## 5. Metric separation

Three distinct measurements, three identities, three campaigns. Enforced in code and
by test, not by README:

| Metric | Unit | Protocol version | Source |
|---|---|---|---|
| `CD31_pct_flow` | `percent_of_parent` | `cytoflexlx-cd31-cd140a-2026-08-06` | 12 FN/VTN tubes |
| `coverage_frac_phase` | `fraction_of_field` | `leica-ph-4x-v1` | 12 dose-matched Leica frames |
| `CD31_area_per_DAPI` | — | Hall/Ogle | published, untouched here |

`load_lab_evaluator`-style metric checking rejects a space whose metric does not match,
and no derived table ships a column named `y`.

## 6. The honesty mechanisms

Each exists because a specific failure was possible:

- **`y_candidate`, never `y`.** A test asserts no derived table has a `y` column.
- **Sensitivity sweep on every percentage.** CD31% moves 9–14 pp across the p95→p99.9
  threshold range, so a bare point estimate would be false precision.
- **`otsu_separability` on every coverage number.** Otsu assumes a bimodal field; a
  flat frame returns 0.0 with the untrustworthy flag rather than a confident value.
- **Comparability keys checked before cross-image claims.** All 18 FN/VTN frames were
  shot `PH`/4X/19000/gain 1/light 45, so the comparison measures cells not optics.
- **Confounding detected mechanically.** In protocol v3, CHIR timing, terminal medium
  and passaging are mutually confounded; only the BMP4 contrast is estimable.
- **Controls matched within day and directory.** No same-day unstained → no percentage,
  rather than a borrowed threshold. Where the tie-break is arbitrary, the chosen control
  travels in the output row and its cost was measured (1.6 pp).
- **Aborted files raise.** Reading 0 events returns an error, not an empty array that
  would average to 0.0%.

## 7. Findings the data supports

- **0.5 µg/mL is the weakest coating dose for both FN and VTN**, at every threshold.
  No monotonic dose response above 1 µg/mL. (CD31% 22–47% across the 12 tubes.)
- **The protocol wells sit far lower than the coating panel** (1.8–8.6% vs 22–47%) on
  the same day and instrument. Control choice accounts for ~1.6 pp of that, so the gap
  is real.
- **BMP4 effect is small and positive**: +1.34 pp (Well 1→3) and +0.40 pp (Well 2→4).
- **The largest effect in the protocol wells is uninterpretable** — Day-2/EGM2/passaged
  reads ~4× Day-3/EC-induction/not-passaged, but those three factors are confounded.
- **Coverage does not corroborate the flow dose response.** FN 0.5 has the *highest*
  coverage and the *lowest* CD31%. Different timepoints (08-04 vs 08-06) and different
  quantities; recorded as a negative result rather than smoothed over.

## 8. Relationship to the 2026-08-13 plan — now completed

That plan specified a `ContinuousLookupEvaluator` and a loader that refuses ungated
tables. Both are built, against the corrected facts:

- `configs/lab/coating_2026-08-06.yaml` — 2-D `{coating, dose}` on `[0.5, 20] µg/mL`.
- `evaluators.ContinuousLookupEvaluator` — `np.isclose` matching. `LookupEvaluator` is
  untouched; Phase 2 replay depends on its `np.rint` index.
- `boec.lab.evaluator.load_lab_evaluator` — `GatingIncompleteError` on the committed
  table, `MetricMismatchError` on a metric or protocol-version mismatch.

Changes from the plan as written:

- Its `novocyte-…` metric string was wrong; the config uses `cytoflexlx-…`.
- Its coded dose `(dose − 0.5)/19.5` is adopted.
- Its premise that gating is wholly a lab step is softened: the channel identity was
  recoverable from data. The percentages still are not signed off.
- It planned `src/boec/lab.py`; this is `src/boec/lab/` (a package).
- Added beyond the plan: `truth()` for parity with `LookupEvaluator`, and a
  construction-time check rejecting table rows indistinguishable within `atol`.

**Correction to an earlier assessment.** This document previously recorded "lacks
`truth()`, which `baselines.py:131` calls" as a live gap. `baselines.py` needs `truth()`
only inside `coordinate_descent`, which is called exclusively with `TorchEvaluator`
(`tests/test_baselines.py`, `scripts/run_e2*.py`), so a lab evaluator would never have
reached it. `truth()` was added for interface parity, not to fix a crash.

## 9. Testing

105 new tests, `tests/test_lab_*.py`. Full suite: **727 passed**. Coverage includes all
300 committed checksums re-verified, every FCS given a disposition (34 gated, 10
controls, 8 aborted), a test pinning why a median comparison would have picked the
wrong channel, a test demonstrating the `np.rint` dose collision rather than merely
asserting the fix, and — the headline — a test asserting that building an evaluator
from the real committed conditions table **fails**.
