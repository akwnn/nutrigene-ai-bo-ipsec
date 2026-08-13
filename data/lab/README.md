# In-house lab data (raw)

Raw Nutrigene wet-lab files for the iPSC → endothelial Bayesian-optimization project. This is **Phase 3 source material**, not an analysis-ready table. Filenames are the originals from the instrument / bench so they still match lab notebooks.

Ingested 2026-08-13 from `~/Desktop/NutrigeneAI Lab Data/1. Relevant files for the BO project/`. SHA-256 checksums of every committed file are in `MANIFEST.sha256`.

The repo already holds synthetic oracles under `data/oracles/` and digitized Hall/Ogle tables under `data/published/`. This tree is the first in-house drop.

## Layout

```
data/lab/
├── README.md
├── MANIFEST.sha256
├── protocols/                 iPSC→EC differentiation notes (docx v2, v3)
├── plate-reader/              Multiskan SkyHigh endpoint Abs @ 562 nm, 2026-06-22
├── microscopy/
│   ├── leica/YYYY-MM-DD/      Leica DMi8 JPEGs + .metadata sidecars
│   └── evos/2026-08-06/       EVOS QS_2448–QS_2454
└── flow/YYYY-MM-DD/           NovoCyte FCS + .xit + ExpSummaryForAPI.xml
```

| Path | What it is | Files | Size |
|---|---|---:|---:|
| `microscopy/leica/2026-07-27` | Leica, wells 1–4 / EC wells | 18 | 8.5 MB |
| `microscopy/leica/2026-07-28` | Leica (was `New Folder`) | 52 | 17.6 MB |
| `microscopy/leica/2026-07-30` | Leica (was `New Folder-copy`) | 26 | 9.3 MB |
| `microscopy/leica/2026-07-31` | Leica (was `0731`) | 18 | 5.4 MB |
| `microscopy/leica/2026-08-01` | Leica (was `0801`) | 18 | 6.4 MB |
| `microscopy/leica/2026-08-04` | Leica fibronectin / vitronectin / gel series (was `0804`) | 50 | 10.6 MB |
| `microscopy/leica/2026-08-06` | Leica (was `New Folder-copy-copy/20260806`) | 14 | 4.5 MB |
| `microscopy/leica/2026-08-10` | Leica (was `0810`) | 18 | 5.0 MB |
| `microscopy/leica/2026-08-11` | Leica (was `0811`) | 14 | 4.6 MB |
| `microscopy/evos/2026-08-06` | EVOS stills (byte-identical copy under `20260806/EVOS` dropped) | 7 | 4.0 MB |
| `flow/2026-07-21` | FCS + `20260721.xit` | 18 | 54.3 MB |
| `flow/2026-07-28` | CD31± / ISO / US / Before | 9 | 23.7 MB |
| `flow/2026-08-06/Exp_20260806_1` | Wells 1–5 + US-old/new | 9 | 36.6 MB |
| `flow/2026-08-06/Exp_20260806_2` | Same tube names; **header-only FCS (~13 KB each)** | 9 | 0.1 MB |
| `flow/2026-08-06/Exp_20260806_cd31-cd140a` | Fibronectin vs vitronectin titration (`f*` / `v*` µg/mL) + US | 14 | 75.5 MB |
| `protocols/` | `IPSC分化EC-2.docx`, `IPSC分化EC-3.docx` | 2 | 40 KB |
| `plate-reader/` | `2026-06-22_endpoint-abs-562.xlsx` | 1 | 12 KB |

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
done < MANIFEST.sha256 | shasum -a 256 -c -
```
