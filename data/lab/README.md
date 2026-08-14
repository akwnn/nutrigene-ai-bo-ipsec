# In-house lab data

Nutrigene wet-lab files for the iPSC → endothelial Bayesian-optimization project. **Phase 3 source material**, not an analysis-ready table.

The directory is split three ways, and the split is load-bearing:

| | What | Rule |
|---|---|---|
| [`raw/`](raw/) | Instrument output, original filenames | **Never edited, never generated.** A change here is corruption. Checksummed in `overlay/MANIFEST.sha256`. |
| [`overlay/`](overlay/) | The human sort + the signed conditions table | Hand-maintained. This is where judgement lives. |
| [`derived/`](derived/) | Everything the pipeline writes | **Disposable.** Delete it and re-run; a change here is just a rerun. |

Before the split, a regenerated table and a corrupted instrument file were the same kind of event — a modified file in `data/lab`. Now they are not.

**BO sort (which files the optimizer may use):** [`overlay/BO-PURPOSE.md`](overlay/BO-PURPOSE.md) · [`overlay/bo_file_roles.csv`](overlay/bo_file_roles.csv) · [`overlay/bo_primary_conditions.csv`](overlay/bo_primary_conditions.csv). Twelve FCS files in `raw/flow/2026-08-06/Exp_20260806_cd31-cd140a/` are the only ones that already encode both a coating level and a CD31/CD140a acquisition. They still need sign-off before `y` exists.

**Derived tables:** `python scripts/build_lab_dataset.py` (~31 s) reads all 306 files and writes [`derived/`](derived/) — file index with checksum verification, flow acquisition provenance, channel identity, candidate percentages with sensitivity sweeps, image features, the protocol well map, and the plate-reader verdict. Gating status and the open judgement calls live in [`overlay/GATE.md`](overlay/GATE.md). Nothing in `derived/` is optimizer input; see the promotion rule in `derived/RUN.json`.

Ingested 2026-08-13 from `~/Desktop/NutrigeneAI Lab Data/1. Relevant files for the BO project/`. SHA-256 checksums of every committed raw file are in `overlay/MANIFEST.sha256`.

The repo already holds synthetic oracles under `data/oracles/` and digitized Hall/Ogle tables under `data/published/`. This tree is the first in-house drop.

## Layout

```
data/lab/
├── README.md                       this file
├── raw/                            INSTRUMENT OUTPUT -- never edit
│   ├── flow/YYYY-MM-DD/            CytoFLEX LX FCS + CytExpert .xit + ExpSummaryForAPI.xml
│   ├── microscopy/
│   │   ├── leica/YYYY-MM-DD/       Leica DMi8 JPEGs + .metadata sidecars
│   │   └── evos/2026-08-06/        EVOS QS_2448–QS_2454
│   ├── plate-reader/               Multiskan SkyHigh endpoint Abs @ 562 nm, 2026-06-22
│   └── protocols/                  iPSC→EC differentiation notes (docx v2, v3)
├── overlay/                        HUMAN SORT -- hand-maintained
│   ├── BO-PURPOSE.md               which files the optimizer may use, and why
│   ├── GATE.md                     gating record; channel identity and what is unsettled
│   ├── MANIFEST.sha256             SHA-256 of every file under raw/
│   ├── bo_file_roles.csv           one role per raw file
│   └── bo_primary_conditions.csv   the 12-point campaign table; `y` filled by a human
└── derived/                        GENERATED -- rm -rf and re-run at will
    ├── RUN.json                    run summary + the promotion rule
    ├── file_index.csv              all 306 files, role, modality, checksum verdict
    ├── flow_acquisitions.csv       52 FCS: instrument, date, events, spillover
    ├── channel_identity.json       CD31 = B525-A, with the full 16-detector ranking
    ├── flow_positivity_candidate.csv   CD31%/CD140a% per tube + sensitivity sweep
    ├── image_features.csv          121 images: coverage, focus, comparability key
    ├── protocol_wellmap.csv        well → CHIR/BMP4/media, from the docx
    ├── plate_reader.json           BCA plate verdict
    └── candidate_campaign_*.csv    the two campaigns, awaiting_human_signoff
```

| Path | What it is | Files | Size |
|---|---|---:|---:|
| `raw/microscopy/leica/2026-07-27` | Leica, wells 1–4 / EC wells | 18 | 8.5 MB |
| `raw/microscopy/leica/2026-07-28` | Leica (was `New Folder`) | 52 | 17.6 MB |
| `raw/microscopy/leica/2026-07-30` | Leica (was `New Folder-copy`) | 26 | 9.3 MB |
| `raw/microscopy/leica/2026-07-31` | Leica (was `0731`) | 18 | 5.4 MB |
| `raw/microscopy/leica/2026-08-01` | Leica (was `0801`) | 18 | 6.4 MB |
| `raw/microscopy/leica/2026-08-04` | Leica fibronectin / vitronectin / gel series (was `0804`) | 50 | 10.6 MB |
| `raw/microscopy/leica/2026-08-06` | Leica (was `New Folder-copy-copy/20260806`) | 14 | 4.5 MB |
| `raw/microscopy/leica/2026-08-10` | Leica (was `0810`) | 18 | 5.0 MB |
| `raw/microscopy/leica/2026-08-11` | Leica (was `0811`) | 14 | 4.6 MB |
| `raw/microscopy/evos/2026-08-06` | EVOS stills (byte-identical copy under `20260806/EVOS` dropped) | 7 | 4.0 MB |
| `raw/flow/2026-07-21` | FCS + `20260721.xit` | 18 | 54.3 MB |
| `raw/flow/2026-07-28` | CD31± / ISO / US / Before | 9 | 23.7 MB |
| `raw/flow/2026-08-06/Exp_20260806_1` | Wells 1–5 + US-old/new | 9 | 36.6 MB |
| `raw/flow/2026-08-06/Exp_20260806_2` | Same tube names; **header-only FCS (~13 KB each)** | 9 | 0.1 MB |
| `raw/flow/2026-08-06/Exp_20260806_cd31-cd140a` | Fibronectin vs vitronectin titration (`f*` / `v*` µg/mL) + US | 14 | 75.5 MB |
| `raw/protocols/` | `IPSC分化EC-2.docx`, `IPSC分化EC-3.docx` | 2 | 40 KB |
| `raw/plate-reader/` | `2026-06-22_endpoint-abs-562.xlsx` | 1 | 12 KB |

**300 data files, 267 MB.** Original names (spaces, mixed case, Chinese protocol titles) are kept on purpose.

## What was left out

| Left out | Why |
|---|---|
| `2. Irrelevant files for the BO project/` | School work, personal/employment PDFs. Not project data. |
| `Flow.zip`, `0804.zip` | Unpacked copies of folders that are already here. |
| Empty `Backup/` directories | Instrument placeholders, no files. |
| Duplicate `20260806/EVOS/` | SHA-256 identical to `EVOS/`. |
| `.DS_Store` | Finder noise. |

`*-copy.jpeg` files are **kept**. They are not byte-identical to the non-copy siblings.

## Caveats (read before analysing)

1. **This is not a coded design matrix.** Well labels, `f5`/`v2.5` filenames, and notebook names still need a condition map before anything here can enter the optimizer.
2. **`Exp_20260806_2` FCS files are stubs.** Valid FCS 3.0 headers, ~13 KB, essentially no events. `Exp_20260806_1` holds the real acquisitions under the same tube names. The two `.xit` files and the identical `ExpSummaryForAPI.xml` were kept so the abort is auditable.
3. **Metric identity is not yet stamped.** CD31/CD140a flow, Leica phase-contrast, EVOS, and Abs@562 are different readouts. Do not mix them into one `y`.
4. **Leica `.metadata` JSON** records objective (typically 4X), exposure, gain, and capture time. Pair it with the JPEG of the same stem.

## Verify

```bash
cd data/lab
while read -r hash _size path; do
  printf '%s  %s\n' "$hash" "$path"
done < overlay/MANIFEST.sha256 | shasum -a 256 -c -
```

Or let the pipeline do it — `derived/RUN.json` carries `checksums_verified` and
`checksums_mismatched` from the last run.
