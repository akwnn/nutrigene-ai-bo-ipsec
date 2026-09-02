# SPADE publication and presentation figure redesign

## Goal

Create one coherent five-figure narrative for SPADE while producing both
PLOS-oriented submission assets and larger, more legible color presentation
assets. The underlying evidence, transformations, thresholds, and negative EC
gate result remain unchanged.

## Figure roles

1. Workflow and estimand ledger.
2. Point-versus-region and terminal-rule trade-offs.
3. Paired contrasts, round cost, and robustness.
4. Calibration and certificate reliability.
5. Prospective EC gate answer rate and containment evidence.

## Visual contract

- SPADE uses a consistent green; comparators use blue/orange/gray.
- Color is redundant with marker, hatch, direct label, or panel separation.
- Numerical axes use honest baselines and common limits where comparisons are
  intended; uncertainty and sample sizes are named in captions/sidecars.
- No data, exclusions, missing values, thresholds, or failures are suppressed.
- Figures use fixed physical dimensions and constrained layout; no accidental
  bounding-box cropping.
- Every figure exports vector PDF/SVG and RGB raster derivatives with alt text,
  long description, caption, data, and provenance.

## Presets

- `plos`: fixed manuscript geometry and 300–600 dpi RGB TIFF suitable for
  submission screening.
- `presentation`: larger canvas and typography for slides/readability, using
  the same data and encodings.

## Verification

- Regenerate all five figures from frozen evidence.
- Inspect color, grayscale, and deuteranopia review sheets.
- Validate raster mode, dimensions, DPI, compression, and file size.
- Run the complete figure and EC test suite.
- Confirm the manuscript continues to state the prospective EC gate failure
  without stronger unsupported claims.
