# Five-Figure Editorial Redesign

**Date:** 2026-08-25

**Status:** Approved concept; written specification awaiting final review

**Scope:** Reframe the manuscript's main visual argument as five publication figures, add a combined study-architecture figure, and rebuild the existing evidence figures without changing validated estimands or results.

## Goal and Definition of Done

The main figures must explain the study as a coherent scientific argument rather than as a collection of analytical outputs. After reading them in sequence, a reader should understand which response landscapes were studied, how the design strategies differ, what one noisy 48-well campaign produces, why the terminal rule changes conclusions, what SPADE contributes across point and map objectives, and where certification is reliable or deliberately withheld.

The redesign is complete only when all five figures are publication ready, numerically traceable to authoritative repository artifacts, legible at their final physical sizes, visually coherent with the reference paper, and accompanied by captions, accessibility text, machine-readable panel data, and a panel-level provenance ledger. All supported PDF, SVG, PNG, and TIFF exports must pass semantic, typography, geometry, accessibility, and artifact validation.

## Editorial Framing

The five figures form one evidence chain:

1. **Study architecture:** response landscapes, design strategies, campaign observations, and decision outputs are distinct layers of the project.
2. **Benchmark decisions:** the same campaign supports several estimands, and each reported object answers a different scientific question.
3. **Terminal-rule sensitivity:** method rankings depend on whether performance is judged at the best observed well or at the model-recommended input.
4. **SPADE point–map–cost evidence:** SPADE improves acceptable-region mapping while remaining within the registered practical-equivalence margin for point regret and using limited feedback rounds.
5. **Reliability and certification:** calibration, answer rate, and conditional containment must be considered separately because a conservative method may decline to certify.

This sequence makes the central contribution explicit: the project is not only an optimization comparison. It is a decision framework that distinguishes point selection, region estimation, certification, and experimental feedback under noisy finite-well campaigns.

## Reference-Paper Influence

The visual system takes inspiration from the supplied reference paper's restrained scientific hierarchy, modular architecture diagrams, serif typography, compact panel lettering, fine rules, and generous use of white space. The redesign does not reproduce the reference paper's scientific content, topology, or exact layouts.

The reference PDF embeds **Charis SIL** for regular, bold, and italic text and **STIX Math** for equations. Those families replace Arial throughout this figure package.

### Reproducible Font Contract

- Bundle official open-source Charis SIL and STIX Math font files within the repository or a documented build asset location.
- Record the source URL, version, license, file name, and SHA-256 hash for every bundled font.
- Resolve fonts from explicit paths during figure generation; do not depend on a workstation's font registry.
- Fail the publication build if the required font files cannot be resolved.
- Embed non-Type-3 fonts in PDF output and retain live text in SVG output.
- Use STIX Math only for mathematical notation; ordinary labels, titles, captions within artwork, and numbers use Charis SIL.

## Evidence and Claim Lock

Presentation may change, but the underlying scientific evidence may not be silently altered. Authoritative values are obtained through the repository's evidence adapters from:

- `results/fix1-terminal-rule.json`
- `results/fix1-analysis.json`
- `results/step0-oracle-best.json`
- `results/final-spade-regret-pareto.json`
- `results/final-spade-kill-ledger.json`
- `results/p7-murphy.json`
- `results/final-spade-certificate.json`
- `results/p8-predictions.json`
- `results/p8-certificate-families.json`

The redesign retains these locked facts:

- Figure 3 compares the same campaigns under two terminal rules and preserves the identity `Rule A = search loss + identification loss`.
- Figure 4 preserves the registered SPADE contrasts, paired intervals, `n = 25`, and the practical-equivalence region of ±0.02.
- The SPADE-minus-Sobol map contrast is −0.010892 with 95% interval [−0.01566185, −0.0059691125].
- The SPADE-minus-qLogNEI map contrast is −0.0326545 with 95% interval [−0.0372318375, −0.028543325].
- The SPADE-minus-qLogNEI Rule-P regret contrast is +0.0093747607 with 95% interval [0.0025784577, 0.0161511877], which lies inside the registered ±0.02 practical-equivalence region.
- Figure 5 preserves exact family-level campaign answer counts: Ackley 0/50, Hartmann6 11/50, Hill 50/50, Levy 49/50, and Rosenbrock 50/50.
- Figure 5 uses exact Clopper–Pearson intervals, distinguishes empty-certificate exclusions from missing data, and reports containment conditional on answering.
- Hartmann robustness panels remain explicitly descriptive where inferential intervals are unavailable.

`spade_random_plate2`, KF-3, KF-4, boundary targeting, and every unresolved boundary result remain prohibited from main figures, captions, accessibility text, sidecars, and headlines until that analysis is repaired and separately approved.

## Terminology Contract

The artwork must not use “model” as an ambiguous synonym for an optimization algorithm. It distinguishes:

- **Response landscapes:** Hill, Ackley, Hartmann6, Levy, and Rosenbrock.
- **Design or decision methods:** classical DoE, unscreened DoE where relevant, Latin hypercube, Sobol, random sampling, qLogEI, qLogNEI, and validated SPADE variants.
- **Fitted response model:** the statistical surrogate learned from campaign observations.
- **Decision outputs:** tested-best selection, model-recommended point, acceptable-region map, conservative certificate, regret, mapping error, and experimental cost.

Only methods supported by a panel's authoritative result artifact may appear as evidence marks in that panel. Figure 1 may present the broader implemented method families as architecture, but it must not imply that every method appears in every benchmark comparison.

## Shared Editorial System

### Hierarchy and Language

Every figure uses four distinct information levels:

1. a single declarative figure-level takeaway;
2. panel titles of approximately three to six words;
3. a concise deck stating conditions, sample size, interval type, or evidence stage;
4. simple axis labels and restrained annotations.

Panel letters align with panel titles. Statistical qualifications belong in the deck, caption, or sidecar rather than being compressed into the plot title. Titles state the inference a reader should take away; axes state only the quantity and direction needed to interpret the marks.

No analytical row may contain more than two panels. Title, deck, legend, annotation, and status areas receive explicit layout space rather than borrowing space from data axes. Legends never obscure observations. Direct labels use near-black text and preserve method identity through adjacent colour and shape rather than coloured prose.

### Colour and Redundant Encoding

- SPADE: teal circle.
- Bayesian optimization: blue triangle, with open and filled states distinguishing qLogEI and qLogNEI.
- Classical DoE: vermillion square.
- Space-filling designs: neutral grey diamonds, with open and filled states distinguishing Latin hypercube and Sobol.
- Search and identification components: distinct luminance and hatch patterns with direct black labels.
- Undercoverage or failed assurance: warning red plus an explicit symbol or status label; never colour alone.

Every method and scientific state must remain identifiable in grayscale and common colour-vision-deficiency simulations. Body text remains near-black on white.

### Geometry and Density

- Use named subplot mosaics or explicit `GridSpec` layouts.
- Use renderer-measured or content-sized schematic nodes, with a minimum of 2 pt internal text padding.
- Use point-based annotation offsets and deterministic leaders.
- Reserve dedicated status gutters for categorical states such as “declined to certify” or “no non-empty certificate.”
- Keep semantic strokes between 0.25 and 1.0 pt.
- Do not use `bbox_inches="tight"` to conceal failed layout geometry or change the specified physical canvas.
- No manually edited production output is permitted; all final artwork is regenerated from committed code.

## Figure Contracts

### Figure 1 — Study architecture separates landscapes, design strategies, and decision outputs

Figure 1 is a full-width architecture diagram inspired by the modular visual grammar of the reference paper. It establishes the project before presenting results.

The first band contains compact response-landscape modules for Hill, Ackley, Hartmann6, Levy, and Rosenbrock. Each module uses a small, consistent surface or contour glyph generated from the implemented benchmark function, not decorative stock artwork. The landscape band is labelled as the source of controlled ground truth for development, stress testing, and cross-family certification evaluation.

The second band groups design strategies by scientific role rather than placing every algorithm in an undifferentiated row:

- classical experimental design;
- space-filling design;
- sequential Bayesian optimization;
- SPADE, combining search, map estimation, and targeted experimental feedback.

The third band shows the common experimental loop: formulation inputs, a 48-well sampled campaign, noisy assay responses, and a fitted response model. It then branches into point outputs, region outputs, certification outputs, and experimental-cost accounting.

Connectors express the direction of information flow. They must not imply that benchmark functions are fitted models or that all methods share identical feedback structure. A compact note distinguishes one-shot designs from methods that can request feedback rounds.

The panel has no numerical performance claims. Its purpose is conceptual orientation and exact project vocabulary.

### Figure 2 — One 48-well campaign supports distinct scientific decisions

The upper half shows a spacious campaign ribbon: formulation variables → 48-well campaign → noisy assay responses → fitted response model. The same sampled campaign then forks into two decision lanes.

The point-decision lane contains tested-best selection, noisy measured selection, model-recommended point, and confirmation. The region-decision lane contains the acceptable-region map and conservative certificate. Each lane states what is observable and what requires additional protocol activity.

The lower half is an estimand ledger sized for exact lookup. It records the deliverable, reported object, observability, score, extra wells, and experimental rounds. Point and region deliverables are visually grouped, numerical fields are aligned, and all cells are content-sized with measured padding.

This figure explains what was estimated and how the study's reported objects differ. It does not report method performance.

### Figure 3 — The terminal rule changes method rankings on the same campaigns

The dominant upper panel is a full-width paired-effect forest plot. It shows Rule-P-minus-Rule-A changes with 95% paired bootstrap intervals for the four same-campaign arms: classical DoE, qLogEI, qLogNEI, and SPADE. The zero line and direction of improvement are labelled directly.

The lower-left panel is an orientation slopegraph showing each method's mean simple regret under Rule A and Rule P. It uses black direct labels next to colour- and shape-coded marks.

The lower-right panel decomposes Rule-A simple regret into search loss and identification loss for the supported methods: classical DoE, qLogNEI, Latin hypercube, and Sobol. Components use both hatch and luminance and close exactly to the source total.

The deck states the Hill condition, `d = 6`, `σ = 0.25`, `n = 50` paired campaigns, and the interval definition. The caption defines both terminal rules and pairing. The figure avoids vague headings such as “Rule A” without a plain-language definition.

### Figure 4 — SPADE improves map recovery within practical point-regret parity

The first row contains two analytical panels. The left panel is the point–map Pareto plane: symmetric-difference error on the horizontal axis and Rule-P simple regret on the vertical axis, both labelled “lower is better.” SPADE, qLogNEI, Sobol, and classical DoE receive deterministic direct labels; the shared method key covers all marks.

The right panel is the registered paired-contrast forest. It shows the two map contrasts and the SPADE-minus-qLogNEI regret contrast with exact 95% paired intervals. A neutral band and labelled boundary lines identify the ±0.02 practical-equivalence region. The interpretation distinguishes evidence of improved mapping from practical parity in regret.

The second row is a full-width operational-cost panel. It displays feedback rounds as a horizontal dot or lollipop plot and states once that all compared campaigns use 48 wells. Rounds are not encoded by marker area.

The third row is a full-width Hartmann robustness section with aligned `d = 6` and `d = 8` facets on shared scales. It presents map error and regret as descriptive means only and explicitly states that intervals are unavailable.

The deck states the primary Hill condition, `d = 6`, `σ = 0.10`, `n = 25`, 95% paired intervals, and the registered ±0.02 margin. It visually separates the inferential Hill evidence from descriptive Hartmann evidence.

### Figure 5 — Reliability and willingness to certify vary across landscapes

The first row contains two aligned cross-family panels. The left panel reports campaign answer rate at `α = 0.95` using exact answered/50 labels. It renders Ackley's 0/50 as “declined to certify,” not as zero containment. The right panel reports conditional containment only for answered certificate cells and uses a dedicated status gutter for declined or empty-certificate states.

The second row is a full-width prospective Hill assurance panel. Conditions are aligned into columns, nominal containment is clearly marked, 95% exact intervals and `x/n` are visible, and “no non-empty certificate” appears as a categorical status outside the data scale.

The third row is a full-width retrospective Hill evidence panel. Calibration error and refinement appear as two aligned ranked dot strips sharing method rows. The deck marks this evidence as retrospective and states `n = 1,200` cells per method. Calibration is labelled “lower is better,” while refinement is labelled “higher is better.”

The figure preserves the separation among calibration, willingness to answer, and containment conditional on answering. It makes no multiplicity or Holm-adjustment claim unless such a result is added through a separately reviewed analysis.

## Figure Inventory and Provenance Deliverables

The repository contains substantially more evidence than can be placed in five main figures. Implementation must therefore produce a documented figure inventory rather than imply that the main set exhausts all available results.

The inventory must enumerate:

- every current main-figure panel and its source artifact;
- all legacy assets under `results/figures`;
- all generated assets under `results/paper-figures`;
- figure-producing scripts and result families relevant to the manuscript;
- the disposition of each item as **main**, **supplementary candidate**, **obsolete**, **unsupported**, or **excluded pending repair**.

The ten currently identified legacy assets—four critical-difference PNGs, three E4 diagnostic PNGs, and the three HTML assets `cost-curves.html`, `fig1-scoring.html`, and `fig3-saddle.html`—must receive an explicit disposition. The inventory is not a license to add unsupported analyses to the main paper.

A separate panel-level provenance ledger must record:

- figure and panel identifier;
- scientific claim and evidence stage;
- authoritative source file and source keys;
- transformation or aggregation performed;
- denominator, exclusions, and pairing unit;
- interval method and confidence level;
- validation test that pins the displayed values;
- main, supplementary, descriptive, or excluded status.

Every number printed in artwork or a caption must be recoverable through this ledger.

## Captions, Alternative Text, and Sidecars

Each figure receives a publication-ready caption outside the artwork. Captions define the estimand, direction of better performance, experimental or simulation unit, exact `n` or `x/n`, denominator exclusions, interval type, confidence level, pairing, abbreviations, practical-effect margins, and descriptive versus inferential status.

Each export also includes:

- concise alternative text;
- a human-readable long description sufficient to recover scales, major values, and relationships;
- machine-readable panel data with stable field names;
- a manifest containing build version, source hashes, font hashes, dimensions, DPI, and output hashes.

## Verification and Acceptance Tests

### Numerical and provenance validation

- Independently reconcile every plotted value against the authoritative JSON artifact rather than trusting only the plotting dataframe.
- Pin all critical values, signs, confidence intervals, practical-equivalence boundaries, `x/n`, denominators, and evidence-stage labels.
- Recompute additive decompositions and exact Clopper–Pearson intervals in tests.
- Assert that each panel's methods and conditions match the source artifact's supported subset.
- Assert prohibited boundary identifiers and claims are absent from panel data, artwork text, captions, alternative text, long descriptions, and manifests.

### Geometry and editorial validation

- Build all five figures under portable, Nature, RSC, and PLOS presets.
- At final renderer size, require every registered text object to remain within its figure, panel, node, table cell, or status gutter with at least 2 pt padding.
- Reject unintended title-letter, label-label, label-marker, legend-data, and annotation-axis collisions.
- Reject any analytical row containing more than two panels.
- Reject constrained-layout collapse warnings and unexpected canvas resizing.
- Review each figure both individually and as a five-figure contact sheet at manuscript reading scale.

### Typography and accessibility validation

- Verify that Charis SIL and STIX Math resolve from the documented build assets and are embedded without Type 3 glyphs.
- Enforce venue text-size and semantic-stroke limits.
- Require near-black normal text to meet a 4.5:1 contrast target and meaningful graphical boundaries to meet a 3:1 target where applicable.
- Generate normal, grayscale, protan, deutan, and tritan review sheets.
- Assert that each method has a unique non-colour encoding tuple and remains identifiable without hue.

### Artifact validation

- Export editable PDF and SVG plus 450 dpi PNG and 600 dpi TIFF derivatives at exact physical dimensions.
- Require live SVG `<text>` and vector response-landscape glyphs; reject unexpected embedded raster `<image>` elements.
- Validate raster dimensions, DPI, RGB mode, and TIFF compression.
- Rebuild deterministically and compare panel data, manifests, captions, long descriptions, and canonical raster hashes or approved visual baselines.

## Implementation Boundaries

- Do not change evidence generation, statistical calculations, or adjudication logic as part of a visual redesign. If validation exposes an evidence defect, pause that panel and document the discrepancy for separate scientific review.
- Do not introduce a new claim merely because a result file exists.
- Do not place unresolved boundary-targeting results into a main or supplementary figure.
- Do not add plotting dependencies unless native Matplotlib demonstrably cannot satisfy a tested requirement and the addition is separately approved.
- Do not manually reposition elements in exported files or use a GUI-only production step.
- Preserve unrelated repository changes and do not push this branch.

## Completion Criteria

1. The five-figure sequence communicates the approved scientific narrative without cramming or ambiguous terminology.
2. Every displayed result and denominator is independently reconciled, documented, and pinned by tests.
3. All legacy and generated figure assets receive a documented disposition.
4. Charis SIL and STIX Math are resolved reproducibly, embedded correctly, and used consistently.
5. No text clips, escapes its semantic container, or collides unintentionally at any supported preset.
6. Main conclusions remain interpretable in grayscale and common colour-vision-deficiency simulations.
7. PDF, SVG, PNG, and TIFF packages, captions, accessibility text, panel data, manifests, and provenance records regenerate from committed code.
8. Focused semantic, geometry, accessibility, artifact, and visual-regression tests pass, followed by an independent final review.
