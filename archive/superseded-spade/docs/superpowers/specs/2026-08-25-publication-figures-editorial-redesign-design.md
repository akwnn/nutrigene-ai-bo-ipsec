# Publication Figures Editorial Redesign

**Date:** 2026-08-25  
**Status:** Approved design  
**Scope:** Redesign Figures 1–4 without changing their validated evidence, estimands, or exclusion rules.

## Goal

Replace the technically correct but visually rudimentary first-generation figures with an editorial-quality, reproducible figure system suitable for a high-impact scientific manuscript. The redesign must improve hierarchy, density, legibility, and visual storytelling while preserving every validated numerical value and scientific qualification.

The work is complete only when all four figures render without clipping or unintended collisions at every supported venue preset, remain interpretable without colour, pass semantic and visual regression tests, and export as editable vector artwork plus compliant high-resolution raster derivatives.

## Evidence and Claim Lock

The redesign changes presentation only. Evidence adapters and validated panel data remain authoritative.

- Figure 2 retains the same-campaign terminal-rule comparison and the identity `Rule A = search loss + identification loss`.
- Figure 3 retains the Rule-P target Pareto comparison, exact registered contrasts, the ±0.02 SESOI, separate wells and rounds, and descriptive-only Hartmann means.
- Figure 4 retains the retrospective/prospective separation, cross-fit containment rows, exact `x/n`, empty-certificate exclusions, campaign-level answer rates at alpha 0.95, and containment conditional on answering.
- `spade_random_plate2`, KF-3, KF-4, boundary targeting, and every unresolved boundary result remain prohibited from the main figures, sidecars, captions, and alternative text.

## Research Basis

The design follows current official requirements and maintained open-source implementation guidance:

- Nature: editable text, 5–7 pt body typography, 8 pt lowercase panel labels, and semantic strokes between 0.25 and 1 pt.
- RSC Digital Discovery: 171 mm double-column format and 600 dpi TIFF delivery.
- PLOS: 8–12 pt typography and 300–600 dpi composite TIFF delivery.
- WCAG: colour is never the sole semantic channel; normal text targets 4.5:1 contrast and meaningful graphical boundaries target 3:1.
- Matplotlib: native `GridSpec`, subplot mosaics, constrained layout, transforms, `AnnotationBbox`, and renderer extents provide the maintained implementation path.

Native Matplotlib remains the only runtime plotting dependency. `pytest-mpl` may be added as an exact-pinned test dependency for canonical visual regression. `adjustText` is not added unless a failing deterministic cross-preset collision test proves fixed annotations are insufficient. SciencePlots, seaborn, ProPlot, Pylustrator, FigureFirst, patchworklib, and GUI-authored positioning are excluded from the runtime design.

## Root Cause of the Existing Layout Failure

The first-generation schematic sizes containers in normalized axes coordinates while sizing text in physical points. Venue presets change text metrics without changing those containers. `constrained_layout` manages axes decorations but cannot resize arbitrary patches around their text.

The redesign therefore separates two responsibilities:

1. panel geometry is managed by `GridSpec`, mosaics, and constrained layout;
2. content geometry is managed by content-sized containers or renderer-measured bounds at final size.

No production export may use `bbox_inches="tight"` to hide a failed layout because it changes the physical output dimensions.

## Shared Visual System

### Typography

- Use Arial as the canonical family, fail the publication build if it cannot be resolved, and record the resolved font path in the manifest.
- Keep labels near-black. Method colours identify marks, not body text.
- Preserve venue-specific sizes: Nature 7 pt body/8 pt panels, RSC 7.5 pt body/8 pt panels, and PLOS 9 pt body/10 pt panels.
- Use sentence-case insight titles and concise axis labels. Detailed statistical qualifications belong in captions and sidecars rather than crowded plot titles.

### Colour and Redundancy

- SPADE: teal circle.
- BO: blue triangle, with open/filled state distinguishing qLogEI/qLogNEI.
- Classical DoE: vermillion square.
- Space-filling methods: grey diamonds, with open/filled state distinguishing Latin hypercube/Sobol.
- Undercoverage: dark warning red plus an open/crossed warning symbol and explicit text; never red alone.
- Search and identification components use distinct luminance, hatch, and direct black labels.

All method identities must remain recoverable in grayscale. Coloured direct-label text is removed because the current teal and vermillion fail the 4.5:1 small-text contrast target on white.

### Geometry

- Use named subplot-mosaic keys rather than positional axis indexing where practical.
- Use point-based annotation offsets for data labels and axes-fraction transforms for panel notes.
- Use content-sized `TextArea`/`AnnotationBbox` nodes for schematic cards.
- For fixed regions such as table cells, measure rendered text with the final renderer and require at least 2 pt internal padding.
- Semantic strokes remain within 0.25–1.0 pt.
- Legends must not cover data. Prefer direct labels, a shared figure legend, or a dedicated legend/status gutter.

## Figure Contracts

### Figure 1 — The deliverable defines the comparison

The figure becomes a compact editorial explainer with three aligned layers.

**Panel A: campaign ribbon.** Four content-sized stages—formulation variables, 48-well campaign, noisy assay responses, and response model—sit on one baseline with patch-aware connectors. Nodes expand with text and maintain measured internal padding at every preset.

**Panel B: decision lanes.** The same sampled campaign forks into two horizontally structured lanes. The point lane lists tested-best, noisy selection, model recommendation, and confirmation as aligned compact items. The region lane lists acceptable-region map and conservative certificate. Repeated prose is removed from large multiline boxes.

**Panel C: estimand matrix.** Retain a table because the task is exact categorical lookup. Group point and region deliverables visually, right-align numeric fields, size rows from line count, and use subtle rules instead of heavy boxes. Every cell must pass renderer-level containment with internal padding.

### Figure 2 — The terminal rule changes the result

**Panel A: orientation slopegraph.** Retain the Rule-A-to-Rule-P mean comparison for the four same-campaign arms. Use black direct labels adjacent to colour/shape-coded endpoints and deterministic leader offsets.

**Panel B: dominant paired-effect forest.** Allocate the most visual area to the paired Rule-P-minus-Rule-A contrasts and their 95% intervals. State the reference direction concisely; exact pairing and interval definitions live in the caption/sidecar.

**Panel C: decomposition.** Retain the additive search-plus-identification view. Label each component directly in black and encode components with both luminance and hatch. Remove prose that requires the reader to identify components only by colour.

### Figure 3 — Point quality, map quality, and rounds are different currencies

**Panel A: target Pareto plane.** Retain map error versus Rule-P regret. Directly label SPADE, qLogNEI, Sobol, and Classical DoE with deterministic leader lines; identify all methods through a shared non-overlapping legend and unambiguous marker encodings.

**Panel B: paired contrast forest.** Retain the three registered contrasts and exact intervals. Represent ±0.02 with labelled boundary lines and a faint neutral band that remains distinguishable in grayscale, and define the interval in the caption/sidecar.

**Panel C: operational cost.** Replace the lookup table with a horizontal rounds dot/lollipop plot. State once that all displayed methods use 48 wells. Rounds are never encoded as point size.

**Panel D: Hartmann robustness.** Replace thin-versus-dashed marker borders with aligned d=6 and d=8 small multiples sharing scales and method encodings. Label these as descriptive means with intervals unavailable.

### Figure 4 — A good map is not a guarantee

**Panel A: calibration and refinement.** Replace the compressed bivariate plane with two aligned ranked dot strips: calibration error, where lower is better, and refinement, where higher is better. Use the same method rows and colour/shape-coded marks in both strips. This preserves the retrospective Hill comparison without a broken axis or outlier-compressed scale.

**Panel B: prospective containment.** Use a structured forest layout with condition fields aligned into columns or assurance facets. Show containment minus nominal, exact intervals, and `x/n`. Put `no non-empty certificate` in a dedicated status gutter rather than at an arbitrary data coordinate.

**Panel C: campaign answer count.** Replace filled bars with a low-ink dot/lollipop display aligned by family. Show exact answered/50 counts. Render `0/50 — declined to certify` as a categorical state, not as zero containment.

**Panel D: conditional containment.** Align families with Panel C. Plot containment minus nominal only among answered certificate cells and place declined states in the same dedicated status gutter. Do not add multiplicity or Holm claims.

## Captions and Accessibility

Each figure receives a publication-ready caption outside the artwork. Captions must define:

- the estimand and direction of better performance;
- the experimental or simulation unit;
- exact `n` or `x/n` and denominator exclusions;
- interval type and confidence level;
- pairing where applicable;
- all abbreviations and practical-effect margins;
- descriptive versus inferential evidence status.

Each export retains concise alternative text, machine-readable panel data, and a human-readable long description sufficient to recover scales, major values, relationships, and trends.

## Automated Acceptance Tests

### Semantic tests

- Pin all critical values, signs, intervals, SESOI, `x/n`, and evidence-stage labels.
- Assert prohibited boundary identifiers and claims are absent from panel data, rendered text, captions, and alt text.
- Assert each method has a unique non-colour encoding tuple.

### Geometry tests

- Build all four figures under portable, Nature, RSC, and PLOS presets.
- At final renderer size, require every registered text box to lie inside its assigned figure, panel, node, status gutter, or table cell with at least 2 pt padding.
- Reject unintended label-label, label-marker, legend-data, and panel-title/panel-letter intersections.
- Reject constrained-layout collapse warnings.
- Confirm exact physical canvas dimensions without `bbox_inches="tight"`.

### Typography and accessibility tests

- Enforce venue minimum/maximum text sizes and 0.25–1.0 pt semantic strokes.
- Record and validate the resolved font family/path.
- Enforce 4.5:1 contrast for normal text and 3:1 for meaningful graphical boundaries where applicable.
- Produce normal, grayscale, protan, deutan, and tritan review sheets; verify method identity remains recoverable.

### Visual and artifact tests

- Add one canonical `pytest-mpl` PNG baseline per portable figure in a pinned rendering environment; semantic tests remain authoritative.
- Require embedded non-Type-3 PDF fonts and extractable text.
- Require live SVG `<text>` and no unexpected raster `<image>` elements.
- Validate raster dimensions, DPI, RGB mode, and TIFF compression.
- Rebuild deterministically and compare sidecars, manifests, and canonical rasters.

## Implementation Boundaries

- Do not change evidence generation, statistical calculations, or adjudication logic unless a redesign test exposes an existing evidence defect; any such defect pauses visual work for separate review.
- Do not introduce new scientific claims, new result panels, or supplementary analyses.
- Do not manually edit exported SVG/PDF/TIFF/PNG files.
- Do not add a runtime plotting dependency without a failing test that native Matplotlib cannot satisfy and explicit approval.
- Preserve unrelated uncommitted document changes and `.worktrees/` exactly as found.

## Completion Criteria

1. Every figure conforms to its panel contract and the shared visual system.
2. No text clips, escapes its semantic container, or collides unintentionally at any venue preset.
3. Main conclusions remain legible in grayscale and common CVD simulations.
4. All focused semantic, geometry, accessibility, visual-regression, and artifact tests pass.
5. Final PDF, SVG, 450 dpi PNG, and 600 dpi TIFF outputs are regenerated from committed code and independently reviewed.
6. Publication-ready captions and long descriptions accompany the final package.
