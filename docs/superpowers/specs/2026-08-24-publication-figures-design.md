# Design Specification: Publication-Ready Paper Figures

## Objective

Create a reproducible, journal-grade figure package for the estimand-aware experimental-design paper. The figures must communicate the paper's scientific argument rather than decorate it: the terminal decision and reported deliverable determine what constitutes success, point optimization and acceptable-region learning rank workflows differently, and map accuracy does not by itself establish calibration or conservative containment.

The default deliverables will be portable across the paper's realistic target venues. Each main figure will be generated as editable vector PDF and SVG, 600-dpi TIFF, and 450-dpi PNG. The plotting pipeline will produce figures from authoritative committed artifacts, emit the numerical data used in every panel, and fail rather than substitute values when required evidence is absent.

## Scientific Story

The four main figures form one decision-first narrative:

1. **Define the deliverables.** A matched well budget does not define a benchmark until the terminal decision, reported object, and feedback-round cost are specified.
2. **Demonstrate terminal-rule dependence.** The same sampled campaigns produce different method comparisons when the final recommendation rule changes.
3. **Demonstrate point-versus-region dependence.** The registered target study shows a point–map trade-off and different feedback-round requirements.
4. **Audit reliability.** Discrimination, calibration, containment, and non-vacuity are distinct properties and must be displayed separately.

SPADE is the principal prospective region-first case study. It is not presented as a universally superior optimizer or a fundamentally new level-set algorithm. No main or supplementary figure may use the unresolved boundary-targeting comparison until its corrected analysis has been frozen.

## Output Architecture

The implementation will add one figure driver under `scripts/` and a small reusable plotting module under `src/boec/`. The responsibilities will be separated:

- **Data adapters** read and validate authoritative JSON artifacts and return typed panel records.
- **Statistical transforms** compute only quantities already defined by the study, such as paired contrasts or aggregations over explicitly named units. Newly derived values must be written to panel-data JSON.
- **Visual primitives** define the shared palette, markers, typography, panel labels, reference lines, and interval drawing.
- **Figure builders** create Figures 1–4 without reading arbitrary files or recomputing campaigns.
- **Export and QA** write venue presets and verify dimensions, fonts, density, colour mode, and expected panel content.

The pipeline must never fit a model, evaluate an oracle, rerun a campaign, or silently read narrative prose as data.

## Authoritative Evidence Map

| Figure component | Primary source | Evidence status |
|---|---|---|
| Deliverable definitions and workflow | `docs/SPADE-FINAL-SPEC.md`, `docs/SPADE-FOR-RESEARCHERS.md`, implemented method modules | Ready for a new schematic |
| Rule-A versus Rule-P comparison | `results/fix1-terminal-rule.json`, `results/fix1-analysis.json` | Ready |
| Search-versus-identification decomposition | `results/step0-oracle-best.json` and its registered analysis metadata | Ready after consistency checks |
| Confirmation sensitivity | `results/q58-selection-sensitivity.json` | Supplementary only until refreshed against the post-fix terminal-rule artifact |
| Target and Hartmann point–map means | `results/final-spade-regret-pareto.json` | Ready |
| Target inferential contrasts | `results/final-spade-kill-ledger.json` interpreted through current corrections and checked against arm means | Ready only for non-reserved contrasts |
| Hartmann uncertainty intervals | Raw prospective condition artifacts | Blocked because the raw files are absent from the checkout |
| Retrospective calibration and refinement | `results/p7-murphy.json` | Ready; Hill-only and descriptive |
| Prospective Hill containment | `results/final-spade-certificate.json` | Ready after exact filtering by condition, arm, threshold fraction, probability level, and assurance level |
| Cross-family non-vacuity and containment | `results/p8-predictions.json`, `results/p8-certificate-families.json` | Ready for descriptive panels; global adjudication must be persisted before a multiplicity-adjusted claim |
| Feasibility exclusions | `results/final-spade-feasibility.json` | Supplementary |

The missing `final-spade-primary.json` and raw `final-spade-c1.json` through `c4.json` and `s1.json` through `s3.json` are publication-release blockers. The figure code may render panels supported by summary artifacts, but it must mark unavailable interval layers as unavailable rather than fabricate or reverse-engineer them.

## Figure 1: The Deliverable Defines the Benchmark

### Claim

A matched experimental budget is scientifically incomplete until the terminal decision, reported object, and sequential-feedback cost are specified.

### Panels

**A. Campaign spine.** A restrained vector workflow will show formulation variables, sampled wells, noisy assay responses, and a fitted response model. Repeated stages will use aligned, equal-sized modules; pale fills will encode semantic stage; and nested or repeated operations will use rounded or dashed group containers. The schematic will use geometric shapes and arrows rather than stock illustrations, biological clip art, or generative imagery.

**B. Decision fork.** The same campaign will branch into hidden tested-best, single noisy-readout selection, posterior/model recommendation, confirmation protocol, acceptable-region map, and conservative certificate. Point decisions and set-valued decisions will occupy visibly separate grouped branches, using one primary flow direction and avoiding crossed connectors.

**C. Estimand ledger.** A compact matrix will list, for each branch, the selected object, practical observability, scoring quantity, additional wells, and feedback rounds. The ledger will distinguish simple regret, symmetric-difference error, probability calibration, and joint containment.

### Caption constraint

The caption must state explicitly that this figure defines the benchmark and contains no performance result.

## Figure 2: The Terminal Decision Changes the Comparison

### Claim

On identical primary Hill campaigns, changing the terminal rule changes the estimated comparison among workflows; measured-value selection combines search quality with noisy identification.

### Panels

**A. Same-campaign slope plot.** For the primary six-factor, higher-noise Hill condition, each method will connect its mean regret under Rule A and Rule P. The principal displayed arms will be classical DoE, qLogEI, qLogNEI, and SPADE/versionb. Direct labels will replace a legend where space permits.

**B. Paired contrast forest.** Contrasts will be centered at zero with 95% paired intervals. The direction of benefit will be written on the axis. Bars and significance stars are prohibited.

**C. Search-versus-identification decomposition.** The measured-value contrast will be decomposed into the difference in the best latent response visited and the additional loss from selecting a condition using noisy measurements. The components must sum visibly to the total contrast and retain the original statistical unit.

The top-three confirmation result will be assigned to the supplement until it is refreshed against the current terminal-rule artifact. Its present protocol decides from the new confirmation reading alone and may not be generalized to averaged confirmation workflows.

## Figure 3: Point Quality, Map Quality, and Rounds Are Different Currencies

### Claim

In the registered target regime, the region-first workflow and batch BO occupy different point–map trade-offs, while equal well counts conceal large differences in feedback rounds.

### Panels

**A. Registered target Pareto plane.** The horizontal axis will be symmetric-difference error and the vertical axis Rule-P simple regret, both oriented so the desirable direction is visually consistent. Principal comparators will be directly labelled. Method family will use colour and method identity will use marker shape.

**B. Inferential contrast strip.** Display primary SPADE versus qLogNEI for map error and regret, and primary SPADE versus Sobol for map error. Each contrast will show its interval and the registered ±0.02 practical-effect band. The panel must make clear that the qLogNEI map contrast exceeds the margin, the mean regret gap lies inside it while its interval extends beyond it, and the Sobol map contrast is below it.

**C. Cost ledger.** Aligned method rows will show wells and feedback rounds in separate columns. Point size will not encode rounds. The panel may state two versus ten rounds but may not infer calendar-time or monetary savings.

**D. Hartmann robustness.** Six- and eight-dimensional Hartmann means may be shown as descriptive small multiples. Inferential whiskers will be added only when the authoritative raw prospective rows are restored. Until then the panels will be explicitly labelled descriptive.

The pending matched boundary-control arm is excluded.

## Figure 4: A Good Map Is Not Yet a Certificate

### Claim

Map discrimination, probability calibration, whole-region containment, and willingness to return a non-empty certificate are different properties.

### Panels

**A. Calibration–refinement plane.** Retrospective Hill means from `p7-murphy.json` will show lower calibration error and stronger refinement as distinct directions. The panel will directly label SPADE/versionb, Sobol, qLogNEI, and classical DoE and mute secondary arms. It must be labelled as retrospective Hill evidence, not prospective cross-family calibration.

**B. Prospective Hill containment.** Exact Clopper–Pearson intervals will be plotted relative to nominal assurance. Every point will print or expose `x/n`; empty certificates are excluded from both numerator and denominator. Filtering must include condition, arm, threshold fraction, probability level, and assurance level so different certificate cells cannot collide.

**C. Cross-family answer rate.** For each external family, show the fraction or count of campaigns returning a non-empty certificate. A method that returns no certificate will be labelled as declining to certify, not assigned zero containment.

**D. Cross-family containment conditional on answering.** Scored cells will display containment minus nominal assurance with exact intervals and aligned non-empty denominators. Multiplicity-adjusted failure labels will appear only after the global adjudication is persisted as an authoritative artifact.

## Supplementary Figure Program

The first implementation pass will reserve stable identifiers for:

1. Full terminal-rule contrasts across dimensions, noise levels, and qLogEI/qLogNEI.
2. Per-campaign search and identification distributions.
3. Confirmation and replication sensitivities after refresh.
4. Quadratic saddle and in-region recommendation diagnostics.
5. Regret and arrival curves against wells and rounds through 200 wells.
6. Complete point–map small multiples across all families.
7. Type-I and type-II components of symmetric-difference error.
8. Full Murphy decomposition and reliability diagrams with bin counts.
9. Complete certificate matrix with exact `x/n`, empty rates, and feasibility exclusions.
10. Posterior-draw sensitivity and Monte Carlo stability.
11. Classical-design diagnostics and unscreened-comparator feasibility.

The unresolved boundary-targeting comparison is prohibited from the main and supplementary packages until corrected and frozen.

## Visual System

### Reference visual benchmark

The visual benchmark supplied during design review is Jiang et al., “A data-driven framework for plant-wide modeling and simulation in biopharmaceutical manufacturing,” *Computers & Chemical Engineering* 215 (2026) 109830, doi:10.1016/j.compchemeng.2026.109830. Its most successful features will inform the visual grammar without reproducing its layouts:

- centered, self-contained scientific schematics with generous white space;
- repeated modules drawn with consistent dimensions, alignment, and border weight;
- pale semantic fills contained by dark outlines, with colour reserved for model or data-flow meaning;
- dashed group boundaries and rounded containers to distinguish hierarchy from sequence;
- predominantly left-to-right or top-to-bottom flow with minimal line crossings;
- compact, aligned small multiples with shared axes, common reference lines, and one figure-level key;
- concise panel labels embedded at the upper-left of each panel and captions kept outside the artwork.

The implementation will exceed the reference where its production choices are unsuitable for this paper. The reference figures are embedded as approximately 300-dpi raster images; the new schematics and statistical plots will remain editable vectors. Final-size labels will be larger, repeated axes will be suppressed where safe, method identity will not rely on the reference's low-separation cyan/blue or red/green combinations, and uncertainty and practical-effect bands will be shown explicitly rather than relying on scatter alone.

### Palette and redundant encodings

- SPADE / region-first: teal `#009E73`, circle.
- Bayesian optimization: blue `#0072B2`, triangle.
- Classical DoE/RSM: vermillion `#D55E00`, square.
- Space-filling: neutral grey `#6B7280`, diamond.
- Undercoverage warning: dark red `#B2182B`, used only for a supported warning state.
- Truth/reference: near-black `#202124`.

Colour will never carry identity or status alone. Marker shape, fill state, line style, direct labels, and panel structure will preserve meaning under grayscale and common colour-vision deficiencies. Rainbow maps and red–green contrasts are prohibited.

### Typography and geometry

- Arial or Helvetica throughout; math rendered with compatible sans-serif glyphs.
- Default portable width approximately 178 mm, with explicit 171-mm RSC and 183-mm Nature presets.
- Final-size body text 7–8 pt, panel labels 8 pt bold lowercase, with a separate PLOS preset using larger text.
- Data strokes approximately 0.6–0.8 pt; reference lines visually recessive.
- Sentence-case panel headings; figure-level titles omitted from submission artwork unless scientifically necessary.
- Captions remain outside the artwork. Short panel subtitles may state the question, not repeat the result as marketing language.
- Minimal grid lines. No drop shadows, gradients, 3-D perspectives, dual axes, or ornamental icons.

## Open-Source Toolchain

Matplotlib is the required rendering core because it is already pinned in the project, supports exact physical sizing, and exports PDF, SVG, and high-resolution raster formats. A committed project `.mplstyle` will encode the shared visual contract.

SciencePlots may be cited and inspected as an MIT-licensed style reference, especially its `science`, `nature`, and colourblind-safe patterns, but the implementation will not depend on its defaults or require LaTeX. Venue-critical sizes, fonts, colours, and export settings will remain explicit in this repository.

`pytest-mpl` is the preferred optional visual-regression dependency. Semantic tests remain mandatory even if pixel baselines are unavailable: every panel must expose the records, channel mapping, reference lines, labels, and interval types it rendered.

Poppler utilities, ImageMagick, and optional Inkscape will be used for QA where installed. Manual graphical edits are prohibited unless the editable source and deterministic export procedure are committed.

Generative-image systems will not be used for scientific figures. This avoids licensing ambiguity and complies with venues that prohibit generative alteration of submitted scientific images.

## Export Presets

### Portable default

- Editable PDF with `pdf.fonttype = 42` and embedded fonts.
- Editable SVG with `svg.fonttype = "none"` and standard installed fonts.
- RGB PNG at 450 dpi for manuscript preview.
- RGB TIFF at 600 dpi for RSC-compatible submission.

### Venue profiles

- **RSC:** 83-mm and 171-mm widths, ≤233-mm height, 600-dpi TIFF plus PDF.
- **Nature-style:** 89-mm and 183-mm widths, ≤170-mm height, editable vector text, 5–7 pt body labels.
- **Elsevier:** embedded-font PDF/EPS-equivalent vector master and raster derivatives at the resolution required by artwork type.
- **PLOS:** TIFF/EPS-compatible output with larger 8–12 pt text preset.

## Validation

Every completed figure must pass:

1. **Artifact provenance:** all source paths and hashes recorded in a build manifest.
2. **Schema validation:** missing or ambiguous keys fail with an actionable error.
3. **Semantic assertions:** panel channel mappings, statistical units, intervals, reference lines, denominators, and prohibited arms are checked in tests.
4. **Numerical reconciliation:** panel-data JSON is compared with authoritative artifacts and manuscript anchor values.
5. **Boundary exclusion:** no current targeted-versus-control estimate, interval, verdict, or label appears in any export.
6. **Physical-size rendering:** visual inspection at final journal width, not only enlarged on screen.
7. **Accessibility:** grayscale and colour-vision-deficiency checks, plus redundant encodings and alt text.
8. **Vector integrity:** PDF/SVG text remains editable; PDF fonts are embedded and non-Type-3.
9. **Raster integrity:** pixel dimensions and density meet the selected preset without artificial upsampling.
10. **Diff control:** figures are regenerated deterministically from a clean checkout, subject to the disclosed missing raw prospective artifacts.

## Research Basis

The implementation will follow the current official artwork guidance for the intended portable venue profiles:

- [Royal Society of Chemistry, Digital Discovery author guidelines](https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/digital-discovery) for 83-mm and 171-mm column widths, maximum figure height, and high-resolution artwork.
- [Nature Portfolio figure construction guidance](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/) and [figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/) for physical dimensions, typography, editable text, and vector export.
- [Elsevier artwork overview](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-overview) for vector/raster formats and embedded fonts.
- [Matplotlib font documentation](https://matplotlib.org/stable/users/explain/text/fonts.html) for deterministic font embedding and cross-backend behaviour.
- [SciencePlots](https://github.com/garrettj403/SciencePlots), an MIT-licensed collection of Matplotlib styles, as an inspected design reference rather than an uncontrolled runtime dependency.

These sources define export constraints, not the scientific content or visual hierarchy. The repository's committed style, semantic tests, and panel-data records remain authoritative for reproducibility.

## Completion Criteria

The figure package is complete when:

- Figures 1–4 render from a single documented command.
- Every figure has PDF, SVG, TIFF, and PNG outputs plus panel-data JSON and alt text.
- Shared colours, shapes, ordering, typography, and evidence-stage labels are consistent across the set.
- Figures 2–4 trace every plotted number to an authoritative artifact.
- Unsupported interval layers are labelled unavailable rather than inferred.
- The unresolved boundary-targeting result is absent.
- Tests validate semantic meaning in addition to image generation.
- The build manifest records code commit, source artifacts, venue preset, dimensions, and output hashes.
- The final-size contact sheet has been visually inspected for legibility, clipping, overlaps, and misleading emphasis.
