# Publication Figures Editorial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Figures 1–4 as editorial-quality, venue-compliant scientific artwork without changing validated evidence or scientific claims.

**Architecture:** Keep evidence adapters independent from rendering. Add shared physical-layout, typography, contrast, and collision primitives; rebuild each figure through native Matplotlib mosaics and content-aware artists; then export captions, long descriptions, and reproducible multi-format assets through the existing provenance pipeline.

**Tech Stack:** Python 3.11+, Matplotlib 3.11.1, Pillow, pytest, optional test-only pytest-mpl 0.19.0, Poppler command-line QA.

## Global Constraints

- Native Matplotlib is the only runtime plotting dependency.
- Arial is the canonical publication font; the build fails if it cannot be resolved and records the resolved font path.
- Nature body text is 7 pt, panel labels 8 pt, and semantic strokes are 0.25–1.0 pt.
- RSC output is 171 mm wide with a 600 dpi TIFF derivative.
- PLOS typography is 8–12 pt and its TIFF derivative is 600 dpi.
- Normal text uses near-black and targets at least 4.5:1 contrast; meaningful graphical boundaries target at least 3:1.
- Colour never carries identity or warning status alone.
- Production export never uses `bbox_inches="tight"`.
- Evidence values, signs, intervals, SESOI, `x/n`, estimands, and evidence-stage labels remain unchanged.
- `spade_random_plate2`, KF-3, KF-4, boundary targeting, and unresolved boundary results remain prohibited everywhere.
- Preserve existing uncommitted changes in `docs/FINDINGS-SPADE-FINAL.md`, `docs/FINDINGS-SPADE.md`, `docs/RESEARCH-SUMMARY.md`, and `.worktrees/`.

---

### Task 1: Shared editorial layout, typography, and QA contracts

**Files:**
- Create: `src/boec/paper_figures/layout.py`
- Create: `src/boec/paper_figures/qa.py`
- Modify: `src/boec/paper_figures/core.py`
- Modify: `src/boec/paper_figures/style.py`
- Modify: `src/boec/paper_figures/paper.mplstyle`
- Test: `tests/test_paper_figure_core.py`
- Create: `tests/test_paper_figure_layout.py`

**Interfaces:**
- Produces: `EditorialText`, `content_box(...)`, `register_artist(...)`, `assert_registered_geometry(...)`, `contrast_ratio(...)`, `resolved_publication_font()`, and an extended `FigureBundle` containing `caption` and `long_description`.
- Consumes: existing `VenuePreset`, `MethodStyle`, and Matplotlib renderer transforms.

- [ ] **Step 1: Write failing tests for the shared contract**

Add tests that require:

```python
def test_publication_font_resolves_to_arial():
    path = resolved_publication_font()
    assert path.name == "Arial.ttf"

def test_figure_bundle_requires_caption_and_long_description():
    bundle = FigureBundle("fig1", fig, {"A": {}}, "short", "caption", "long")
    assert bundle.caption == "caption"
    assert bundle.long_description == "long"

def test_content_box_contains_text_with_two_point_padding():
    artist = content_box(ax, (0.5, 0.5), "Same sampled\ncampaign", preset)
    register_artist(fig, "node", artist.text, artist.patch, padding_pt=2)
    fig.canvas.draw()
    assert_registered_geometry(fig)

def test_normal_text_colours_meet_contrast_contract():
    assert contrast_ratio("#243746", "#FFFFFF") >= 4.5
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py -q
```

Expected: failures because the new bundle fields and layout/QA functions do not exist.

- [ ] **Step 3: Implement the minimal shared primitives**

Implement `content_box` with `TextArea` and `AnnotationBbox`, returning a named object exposing the text and frame artists. Store geometry registrations on the figure. Convert point padding to pixels with `renderer.points_to_pixels`. Implement pairwise rectangle intersection and contrast using WCAG relative luminance. Resolve Arial with `matplotlib.font_manager.findfont("Arial", fallback_to_default=False)` and raise a clear `RuntimeError` if unavailable.

Extend the bundle exactly as:

```python
@dataclass(frozen=True)
class FigureBundle:
    figure_id: str
    figure: Figure
    panel_data: dict[str, Any]
    alt_text: str
    caption: str
    long_description: str
```

Update the style context to use Arial, near-black text, 0.8 pt primary strokes, 0.5 pt grids, Type 42 PDF/PS text, and live SVG text.

- [ ] **Step 4: Run shared tests and verify GREEN**

Run the Task 1 test command again. Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/layout.py src/boec/paper_figures/qa.py \
  src/boec/paper_figures/core.py src/boec/paper_figures/style.py \
  src/boec/paper_figures/paper.mplstyle tests/test_paper_figure_core.py \
  tests/test_paper_figure_layout.py
git commit -m "feat: add editorial figure layout contracts"
```

### Task 2: Redesign Figure 1 with content-sized campaign and decision lanes

**Files:**
- Modify: `src/boec/paper_figures/figure1.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `content_box`, geometry registration, Arial venue presets, and extended `FigureBundle`.
- Produces: Figure 1 campaign ribbon, decision lanes, grouped estimand matrix, caption, and long description.

- [ ] **Step 1: Replace the portable-only regression with all-preset failing tests**

Parameterize over `portable`, `rsc`, `nature`, and `plos`. Require every campaign/decision label to be registered inside its content box with 2 pt padding; every table text artist to remain inside its cell; and no panel label/title collision. Explicitly assert that the old failing label is covered:

```python
assert "Same sampled\ncampaign" in registered_text
assert_registered_geometry(bundle.figure)
```

- [ ] **Step 2: Run Figure 1 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure1 -q
```

Expected: the current fixed patches fail for every preset and additional PLOS nodes fail.

- [ ] **Step 3: Implement the campaign ribbon and decision lanes**

Use a 2×2 outer GridSpec. Build Panel A from four content-sized cards connected to their actual frames. Build Panel B as two aligned lane cards whose individual deliverables are separate short text rows, not one multiline paragraph. Keep Panel C as a grouped table with subtle rules, point/region group labels, numeric alignment, and row heights determined from line counts.

Use black text throughout; fills retain semantic grouping. Register every node and cell for geometry QA. Add the approved caption and a long description that states the figure contains no performance result.

- [ ] **Step 4: Verify all Figure 1 presets**

Run the Figure 1 tests. Expected: all pass, including the screenshot regression.

- [ ] **Step 5: Render and inspect Figure 1 only**

Export a temporary portable and PLOS PNG, inspect both with the image tool, and verify there is no text overflow, excessive empty space, or connector crossing.

- [ ] **Step 6: Commit**

```bash
git add src/boec/paper_figures/figure1.py tests/test_paper_figure_builders.py
git commit -m "feat: redesign benchmark definition figure"
```

### Task 3: Redesign Figure 2 around the paired terminal-rule effect

**Files:**
- Modify: `src/boec/paper_figures/figure2.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: unchanged `build_figure2_data`, shared layout/QA primitives, and extended bundle metadata.
- Produces: orientation slopegraph, dominant paired-effect forest, redundant decomposition, caption, and long description.

- [ ] **Step 1: Write failing editorial and accessibility tests**

Require Panel B to receive the largest width ratio, every direct label to use near-black text, all semantic line widths to be ≤1 pt, decomposition components to have distinct hatch/luminance encodings, and rendered labels to avoid registered mark/label collisions across all presets. Preserve exact Rule A/Rule P values, contrast signs, and identity tests.

- [ ] **Step 2: Run Figure 2 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure2 -q
```

Expected: current coloured labels, >1 pt intervals, and colour-only decomposition fail.

- [ ] **Step 3: Implement the editorial mosaic**

Use a one-row named mosaic with width ratios approximately 0.9:1.25:1.0. Keep coloured/shape-coded endpoints but render label text in near-black with point offsets. Draw paired intervals at 0.8–1.0 pt. Draw search and identification segments with direct black labels, distinct grayscale luminance, and hatch. Remove “blue/orange” prose from the axis.

Add a caption defining same campaigns, Rule A and Rule P, paired effect direction, exact campaign count, and the 95% interval; add a long description with the principal numerical contrasts.

- [ ] **Step 4: Verify Figure 2 tests and render all presets**

Expected: all tests pass and no text or interval exceeds venue contracts.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure2.py tests/test_paper_figure_builders.py
git commit -m "feat: redesign terminal rule evidence figure"
```

### Task 4: Redesign Figure 3 point-map-cost evidence

**Files:**
- Modify: `src/boec/paper_figures/figure3.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: unchanged `build_figure3_data`, registered contrast IDs, and shared method styles.
- Produces: decluttered Pareto plane, SESOI forest, rounds lollipop, Hartmann small multiples, caption, and long description.

- [ ] **Step 1: Write failing tests for the new panel contracts**

Require:

```python
assert bundle.panel_data["C"]["constant_wells"] == 48
assert bundle.panel_data["C"]["encoding"] == "rounds lollipop"
assert bundle.panel_data["D"]["facets"] == ["d=6", "d=8"]
```

Assert direct labels exist only for SPADE, qLogNEI, Sobol, and Classical DoE; the shared legend identifies all six methods without overlapping data; SESOI boundaries equal ±0.02; rounds are not marker size; and the Hartmann facets contain only descriptive means with no intervals. Parameterize collision/containment tests across all presets.

- [ ] **Step 2: Run Figure 3 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure3 -q
```

Expected: current cost table and combined Hartmann panel fail the new contracts.

- [ ] **Step 3: Implement the new 2×2 mosaic**

Retain exact Pareto coordinates and registered intervals. Use deterministic point-offset leader lines for the four direct labels and a shared legend outside the data region. Replace Panel C with a horizontal lollipop plot of rounds and one annotation that all methods use 48 wells. Split Panel D into nested d=6/d=8 axes with shared limits and method encodings. Use labelled ±0.02 lines plus a faint neutral band in Panel B.

Add a caption defining Rule-P regret, symmetric-difference error, paired intervals, SESOI, wells versus rounds, and Hartmann’s descriptive-only status. Add a long description with exact SPADE/qLogNEI/Sobol comparisons.

- [ ] **Step 4: Verify Figure 3 tests and inspect crowded presets**

Render portable and PLOS previews. Expected: no lower-left label collision, no legend-data overlap, and distinct Hartmann facets.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure3.py tests/test_paper_figure_builders.py
git commit -m "feat: redesign point map and cost figure"
```

### Task 5: Redesign Figure 4 reliability and certifiability audit

**Files:**
- Modify: `src/boec/paper_figures/figure4.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: unchanged `build_figure4_data`, authoritative campaign answer counts, and exact conditional-containment rows.
- Produces: aligned calibration/refinement strips, structured Hill forest, campaign answer lollipop, conditional forest/status gutter, caption, and long description.

- [ ] **Step 1: Write failing tests for scientific state separation**

Require Panel A to expose aligned `calibration error` and `refinement` strips with common method order. Require Panel B to place `no non-empty certificate` in a non-data status gutter. Require Panel C to render the pinned counts `0/50`, `11/50`, `50/50`, `49/50`, `50/50` and explicitly attach “declined to certify” to Ackley. Require Panel D to place Ackley in the status gutter and never at an estimate coordinate. Require undercoverage to use warning symbol plus text, not red alone. Preserve exact x/n and cross-fit filtering tests.

- [ ] **Step 2: Run Figure 4 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure4 -q
```

Expected: current scatter, bars, and in-axis declined labels fail.

- [ ] **Step 3: Implement the structured audit layout**

Build a 2×2 outer mosaic with nested subgrids. Panel A uses two ranked dot strips with shared rows. Panel B separates condition columns, estimate/CI axis, and status gutter. Panel C uses a low-ink lollipop/count display with all five families aligned. Panel D uses the same family order and a status gutter. Keep exact confidence intervals at ≤1 pt and use a redundant warning marker for evidence-supported undercoverage.

Add a caption defining retrospective versus prospective evidence, calibration/refinement directions, cross-fit containment minus nominal, exact interval type, empty-certificate exclusion, campaign answer scope, and conditional denominators. Add a long description distinguishing decline from undercoverage.

- [ ] **Step 4: Verify Figure 4 tests and inspect all presets**

Expected: all tests pass with aligned families and unambiguous categorical states.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure4.py tests/test_paper_figure_builders.py
git commit -m "feat: redesign reliability audit figure"
```

### Task 6: Export captions, long descriptions, and resolved-font provenance

**Files:**
- Modify: `src/boec/paper_figures/export.py`
- Modify: `tests/test_paper_figure_export.py`

**Interfaces:**
- Consumes: extended `FigureBundle` metadata and `resolved_publication_font()`.
- Produces: `figN.caption.txt`, `figN.description.txt`, font provenance in the manifest, and the existing PDF/SVG/PNG/TIFF/data/alt outputs.

- [ ] **Step 1: Write failing export tests**

Require eight outputs per figure: PDF, SVG, PNG, TIFF, data JSON, short alt text, caption, and long description. Assert captions include panel labels and statistical definitions; long descriptions contain at least 75 words; manifest font path hashes to the resolved Arial file; prohibited tokens are absent; and PDF page dimensions remain exact without tight cropping.

- [ ] **Step 2: Run focused export tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_export.py -q
```

Expected: caption/description files and font provenance are absent.

- [ ] **Step 3: Implement export metadata**

Validate and write `caption.txt` and `description.txt`, include their hashes in figure records, add resolved font family/path/SHA-256 to the manifest, and preserve existing staging/failure safety and deterministic metadata.

- [ ] **Step 4: Verify export tests and deterministic rebuild**

Expected: all export tests pass and manifests compare byte-for-byte across output roots.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/export.py tests/test_paper_figure_export.py
git commit -m "feat: export paper figure captions and descriptions"
```

### Task 7: Visual regression, collision, grayscale, and CVD review artifacts

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_paper_figure_layout.py`
- Create: `tests/test_paper_figure_visual.py`
- Create: `tests/baseline/paper_figures/fig1.png`
- Create: `tests/baseline/paper_figures/fig2.png`
- Create: `tests/baseline/paper_figures/fig3.png`
- Create: `tests/baseline/paper_figures/fig4.png`
- Modify: `src/boec/paper_figures/export.py`

**Interfaces:**
- Consumes: all redesigned portable figures and shared QA registrations.
- Produces: canonical portable visual baselines and normal/grayscale/protan/deutan/tritan review sheets.

- [ ] **Step 1: Add exact-pinned test dependency and failing visual tests**

Add:

```toml
[project.optional-dependencies]
test = ["pytest-mpl==0.19.0"]
```

Create one `@pytest.mark.mpl_image_compare` test per portable figure with deterministic metadata and a pinned baseline directory. Add programmatic tests that every method retains a unique marker/fill signature in grayscale and the registered geometry checker reports zero unintended collisions.

- [ ] **Step 2: Install the test extra and verify RED**

```bash
.venv/bin/python -m pip install -e '.[test]'
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_visual.py --mpl -q
```

Expected: missing baselines fail and produce candidate images.

- [ ] **Step 3: Review and commit canonical baselines**

Generate baselines only after inspecting each candidate PNG at final composition. Add deterministic review-sheet generation that stores normal, grayscale, protan, deutan, and tritan variants under the final output directory; do not add a runtime colour-simulation dependency.

- [ ] **Step 4: Verify visual and geometry suites GREEN**

Run visual tests with `--mpl`, then core/layout/evidence/builder tests without it. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/boec/paper_figures/export.py \
  tests/test_paper_figure_layout.py tests/test_paper_figure_visual.py \
  tests/baseline/paper_figures
git commit -m "test: add publication figure visual contracts"
```

### Task 8: Regenerate, inspect, validate, and publish the redesigned package

**Files:**
- Regenerate: `results/paper-figures/**`
- Test: all paper-figure tests

**Interfaces:**
- Consumes: committed Tasks 1–7 and frozen evidence under `results/`.
- Produces: final reviewed publication package and provenance manifest.

- [ ] **Step 1: Run the complete focused suite**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py \
  tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_export.py -q
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_visual.py --mpl -q
```

Expected: all focused and visual tests pass.

- [ ] **Step 2: Build the final portable package**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python \
  scripts/make_paper_figures.py --results-dir results \
  --output-dir results/paper-figures --preset portable
```

Expected: four figures, eight per-figure representations, manifest, contact sheet, and accessibility review sheets.

- [ ] **Step 3: Run mechanical artifact QA**

Verify PDF page dimensions/fonts, SVG live text, raster dimensions/DPI/RGB/TIFF compression, source/output hashes, Arial provenance, caption schemas, and prohibited-content exclusion. Require `git diff --check` to pass.

- [ ] **Step 4: Inspect every figure and review sheet visually**

Open the contact sheet, four portable PNGs, and all grayscale/CVD review sheets. Check hierarchy, clipping, label/legend collisions, line crossings, state ambiguity, and final-size readability. Any defect returns to the responsible task with a failing regression test.

- [ ] **Step 5: Run repository tests once and classify unrelated baselines**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest -q
```

Expected: paper-figure tests pass. Record any pre-existing exact-numerical replay/calibration failures without altering unrelated scientific code.

- [ ] **Step 6: Commit final assets**

```bash
git add results/paper-figures
git commit -m "figures: publish editorial paper artwork"
```

- [ ] **Step 7: Independent final review**

Review the complete implementation range against the approved specification. Require no Critical or Important scientific, visual, accessibility, provenance, or reproducibility findings before delivery.
