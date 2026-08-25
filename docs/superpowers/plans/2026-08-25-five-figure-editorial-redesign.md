# Five-Figure Editorial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a coherent five-figure main-paper sequence with reference-matched typography, a new study-architecture figure, independently reconciled evidence, uncluttered editorial layouts, and complete publication exports.

**Architecture:** Keep scientific evidence extraction independent from rendering, and use semantic evidence-adapter names so figure renumbering cannot change the data selected. Extend the existing Matplotlib system with bundled Charis SIL/STIX fonts and reserved heading geometry, then rebuild one figure per task before integrating provenance, inventory, accessibility, and multi-format export validation.

**Tech Stack:** Python 3.11+, Matplotlib 3.11.1, NumPy, SciPy, Pillow, pytest, Poppler command-line QA, Charis SIL 6.200, and STIX Math 1.1.1.

## Global Constraints

- Use Charis SIL for all ordinary text and STIX Math for mathematical notation; Arial must not appear in production artwork or manifests.
- Bundle official open-source font files, license texts, source versions, release URLs, and SHA-256 hashes; do not depend on workstation font installation.
- Every figure has one declarative headline, panel titles of approximately three to six words, a condition/evidence deck, simple axis labels, and explicit space for legends and status text.
- No analytical row contains more than two panels.
- Native Matplotlib remains the only runtime plotting dependency.
- Colour never carries method identity, warning state, or certification state alone.
- Production export never uses `bbox_inches="tight"`.
- Evidence values, signs, intervals, practical-equivalence boundaries, denominators, estimands, and evidence-stage labels remain unchanged.
- The registered SPADE practical-equivalence region is ±0.02, and every Figure 4 contrast is paired over `n = 25` campaigns.
- Cross-family answer counts remain Ackley 0/50, Hartmann6 11/50, Hill 50/50, Levy 49/50, and Rosenbrock 50/50.
- `spade_random_plate2`, KF-3, KF-4, boundary targeting, and unresolved boundary results remain prohibited everywhere.
- Hartmann robustness results remain descriptive where raw-row intervals are unavailable.
- Preserve unrelated repository changes and do not push the branch.

## File Structure

- `src/boec/paper_figures/fonts/`: versioned font binaries, licenses, and a machine-readable source manifest.
- `src/boec/paper_figures/fonts.py`: explicit font registration, resolution, and provenance.
- `src/boec/paper_figures/layout.py`: content-sized nodes plus reserved figure/panel heading geometry.
- `src/boec/paper_figures/qa.py`: renderer-level containment, collision, typography, and contrast assertions.
- `src/boec/paper_figures/landscape_glyphs.py`: deterministic two-dimensional slices of the five implemented response landscapes.
- `src/boec/paper_figures/evidence.py`: semantic terminal-rule, SPADE, and certification evidence adapters.
- `src/boec/paper_figures/figure1.py` through `figure5.py`: one builder per final manuscript figure.
- `src/boec/paper_figures/provenance.py`: panel-level provenance records and inventory rendering.
- `src/boec/paper_figures/export.py`: deterministic five-figure publication package and review sheets.
- `docs/PAPER-FIGURE-INVENTORY.md`: disposition of main, legacy, generated, supplementary-candidate, obsolete, unsupported, and excluded assets.
- `docs/PAPER-FIGURE-PROVENANCE.md`: panel claims, sources, transforms, units, denominators, intervals, and tests.

---

### Task 1: Bundle the reference typography and reserve editorial heading space

**Files:**
- Create: `src/boec/paper_figures/fonts/CharisSIL-Regular.ttf`
- Create: `src/boec/paper_figures/fonts/CharisSIL-Bold.ttf`
- Create: `src/boec/paper_figures/fonts/CharisSIL-Italic.ttf`
- Create: `src/boec/paper_figures/fonts/CharisSIL-BoldItalic.ttf`
- Create: `src/boec/paper_figures/fonts/STIXMath-Regular.otf`
- Create: `src/boec/paper_figures/fonts/OFL-Charis.txt`
- Create: `src/boec/paper_figures/fonts/OFL-STIX.txt`
- Create: `src/boec/paper_figures/fonts/font-assets.json`
- Create: `src/boec/paper_figures/fonts.py`
- Modify: `src/boec/paper_figures/core.py`
- Modify: `src/boec/paper_figures/paper.mplstyle`
- Modify: `src/boec/paper_figures/style.py`
- Modify: `src/boec/paper_figures/layout.py`
- Modify: `src/boec/paper_figures/qa.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_paper_figure_core.py`
- Modify: `tests/test_paper_figure_layout.py`

**Interfaces:**
- Produces: `FontAssets`, `register_publication_fonts() -> FontAssets`, `font_manifest() -> dict[str, object]`, `editorial_figure(...) -> tuple[Figure, GridSpec]`, `panel_heading(...) -> tuple[Text, Text, Text]`, `assert_no_registered_collisions(Figure)`, `assert_all_text_inside_figure(Figure)`, and `FigureBundle.headline`, `.deck`, and `.layout_rows` metadata.
- Consumes: packaged font resources, `VenuePreset`, and Matplotlib renderer transforms.

- [ ] **Step 1: Add failing font and heading-contract tests**

Replace the Arial test with explicit package-resolution tests and add a heading test:

```python
def test_publication_fonts_are_packaged_and_hash_verified():
    assets = register_publication_fonts()
    assert assets.text_regular.name == "CharisSIL-Regular.ttf"
    assert assets.text_bold.name == "CharisSIL-Bold.ttf"
    assert assets.math_regular.name == "STIXMath-Regular.otf"
    manifest = font_manifest()
    assert manifest["charis"]["version"] == "6.200"
    assert manifest["stix"]["version"] == "1.1.1"
    for record in manifest["files"]:
        assert sha256_file(assets.text_regular.parent / record["name"]) == record["sha256"]

def test_editorial_heading_has_reserved_non_overlapping_geometry():
    fig, content = editorial_figure(
        get_preset("plos"), 150,
        "The terminal rule changes method rankings",
        "Hill · d=6 · σ=0.25 · n=50 paired campaigns",
        rows=1, cols=1,
    )
    ax = fig.add_subplot(content[0, 0])
    panel_heading(ax, "a", "Paired terminal-rule effect", "95% paired bootstrap interval", get_preset("plos"))
    assert_registered_geometry(fig)

def test_figure_bundle_records_editorial_hierarchy():
    fig = plt.figure()
    bundle = FigureBundle(
        "fig1", fig, {"A": {}}, "alt", "caption", "description",
        headline="Study architecture separates scientific layers",
        deck="Five landscapes · four method families · one campaign protocol",
        layout_rows=(("A",),),
    )
    assert bundle.layout_rows == (("A",),)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py -q
```

Expected: failures because packaged font assets and editorial heading helpers do not exist and the current style still resolves Arial.

- [ ] **Step 3: Import and document the official font releases**

Import Charis SIL 6.200 from the official SIL release and STIX Math 1.1.1 from the official STIX Word release. These names match the embedded font families identified in the reference PDF. Store only the five required font binaries and both OFL texts. Generate `font-assets.json` from the imported bytes so the committed manifest contains the actual digests:

```python
font_names = (
    "CharisSIL-Regular.ttf",
    "CharisSIL-Bold.ttf",
    "CharisSIL-Italic.ttf",
    "CharisSIL-BoldItalic.ttf",
    "STIXMath-Regular.otf",
)
payload = {
    "charis": {
        "family": "Charis SIL",
        "version": "6.200",
        "release_url": "https://github.com/silnrsi/font-charis/releases/tag/v6.200",
        "license": "SIL Open Font License 1.1",
    },
    "stix": {
        "family": "STIX Math",
        "version": "1.1.1",
        "release_url": "https://sourceforge.net/projects/stixfonts/files/Current%20Release/STIXv1.1.1-word.zip/download",
        "license": "SIL Open Font License 1.1",
    },
    "files": [
        {"name": name, "sha256": sha256_file(font_root / name)}
        for name in font_names
    ],
}
manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
```

- [ ] **Step 4: Implement explicit font registration and editorial geometry**

Implement the core font interface:

```python
@dataclass(frozen=True)
class FontAssets:
    text_regular: Path
    text_bold: Path
    text_italic: Path
    text_bold_italic: Path
    math_regular: Path

@lru_cache(maxsize=1)
def register_publication_fonts() -> FontAssets:
    root = Path(str(files("boec.paper_figures").joinpath("fonts")))
    assets = FontAssets(
        root / "CharisSIL-Regular.ttf",
        root / "CharisSIL-Bold.ttf",
        root / "CharisSIL-Italic.ttf",
        root / "CharisSIL-BoldItalic.ttf",
        root / "STIXMath-Regular.otf",
    )
    for path in dataclasses.astuple(assets):
        if not path.is_file():
            raise RuntimeError(f"required publication font is missing: {path}")
        font_manager.fontManager.addfont(path)
    return assets
```

Update `content_box` to use `fontfamily="Charis SIL"`. Add an explicit header axis occupying the first 12–15% of every canvas and give each panel a dedicated title/deck band. Register title, deck, and panel-letter collision pairs in `qa.py`. Update `paper.mplstyle` to Charis SIL and STIX Math, Type 42 PDF text, and live SVG text. Add `fonts/*.ttf`, `fonts/*.otf`, `fonts/*.txt`, and `fonts/*.json` to package data.

Extend `FigureBundle` without breaking intermediate builders:

```python
@dataclass(frozen=True)
class FigureBundle:
    figure_id: str
    figure: Figure
    panel_data: dict[str, Any]
    alt_text: str
    caption: str
    long_description: str
    headline: str = ""
    deck: str = ""
    layout_rows: tuple[tuple[str, ...], ...] = ()
```

- [ ] **Step 5: Run font/layout tests and inspect a PDF font table**

Run the Task 1 pytest command, then render one test page and run:

```bash
pdffonts /private/tmp/boec-font-smoke.pdf
```

Expected: pytest passes; the PDF lists embedded Charis SIL and STIX math fonts, contains no Arial, and contains no Type 3 font.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/boec/paper_figures/fonts src/boec/paper_figures/fonts.py \
  src/boec/paper_figures/core.py \
  src/boec/paper_figures/paper.mplstyle src/boec/paper_figures/style.py \
  src/boec/paper_figures/layout.py src/boec/paper_figures/qa.py \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py
git commit -m "feat: bundle publication typography"
```

### Task 2: Give evidence adapters semantic names and independently pin every main result

**Files:**
- Modify: `src/boec/paper_figures/evidence.py`
- Modify: `src/boec/paper_figures/export.py`
- Modify: `src/boec/paper_figures/figure2.py`
- Modify: `src/boec/paper_figures/figure3.py`
- Modify: `src/boec/paper_figures/figure4.py`
- Modify: `tests/test_paper_figure_evidence.py`
- Modify: `tests/test_paper_figure_builders.py`
- Modify: `tests/test_paper_figure_export.py`

**Interfaces:**
- Produces: `build_terminal_rule_data(Path)`, `build_spade_evidence_data(Path)`, and `build_certification_data(Path)`.
- Consumes: the nine frozen JSON artifacts already returned by `source_paths()`.

- [ ] **Step 1: Write failing tests for semantic adapters and exact reconciliation**

Rename test imports and add exact locks:

```python
def test_spade_registered_contrasts_are_exact():
    rows = {row["contrast_id"]: row for row in build_spade_evidence_data(RESULTS)["contrasts"]}
    numeric = lambda row: (row["mean"], row["lo"], row["hi"], row["sesoi"], row["n"])
    assert numeric(rows["map_spade_minus_sobol"]) == pytest.approx(
        (-0.010892, -0.01566185, -0.0059691125, 0.02, 25)
    )
    assert numeric(rows["map_spade_minus_qlognei"]) == pytest.approx(
        (-0.0326545, -0.0372318375, -0.028543325, 0.02, 25)
    )
    assert numeric(rows["regret_spade_minus_qlognei"]) == pytest.approx(
        (0.0093747607, 0.0025784577, 0.0161511877, 0.02, 25)
    )

def _independent_clopper_pearson(x: int, n: int, level: float = 0.95):
    tail = (1.0 - level) / 2.0
    lo = 0.0 if x == 0 else float(beta.ppf(tail, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1.0 - tail, x + 1, n - x))
    return lo, hi

def test_cross_family_exact_intervals_recompute_from_x_and_n():
    for row in build_certification_data(RESULTS)["cross_family_conditional_containment"]:
        if row["n"]:
            assert (row["ci_lo"], row["ci_hi"]) == pytest.approx(
                _independent_clopper_pearson(row["x"], row["n"])
            )
```

The independent interval helper in the test must call `scipy.stats.beta.ppf` directly rather than the production `_clopper_pearson` function.

- [ ] **Step 2: Run evidence tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_evidence.py -q
```

Expected: import failures because the adapters still use figure-number names.

- [ ] **Step 3: Rename adapters and constants without compatibility aliases**

Rename:

```python
FIGURE2_RULE_ARMS -> TERMINAL_RULE_ARMS
FIGURE2_DECOMPOSITION_ARMS -> TERMINAL_DECOMPOSITION_ARMS
FIGURE3_ARMS -> SPADE_EVIDENCE_ARMS
FIGURE3_HARTMANN_CONDITIONS -> SPADE_HARTMANN_CONDITIONS
FIGURE4_HILL_CELL_IDS -> CERTIFICATION_HILL_CELL_IDS
FIGURE4_HILL_CELL_SPECS -> CERTIFICATION_HILL_CELL_SPECS
build_figure2_data -> build_terminal_rule_data
build_figure3_data -> build_spade_evidence_data
build_figure4_data -> build_certification_data
```

Update all imports and callers in one commit. Preserve every validation and output field. Do not retain numbered aliases because they would allow a future figure reorder to silently select the wrong evidence.

- [ ] **Step 4: Run focused evidence, builder, and export tests**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_export.py -q
```

Expected: all existing four-figure behavior remains green under semantic adapter names.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/evidence.py src/boec/paper_figures/export.py \
  src/boec/paper_figures/figure2.py src/boec/paper_figures/figure3.py \
  src/boec/paper_figures/figure4.py tests/test_paper_figure_evidence.py \
  tests/test_paper_figure_builders.py tests/test_paper_figure_export.py
git commit -m "refactor: name figure evidence by estimand"
```

### Task 3: Add the study-architecture figure and migrate to the five-figure sequence

**Files:**
- Create: `src/boec/paper_figures/landscape_glyphs.py`
- Replace: `src/boec/paper_figures/figure1.py` with the new architecture builder after preserving its old content as Figure 2
- Replace: `src/boec/paper_figures/figure2.py` with the migrated decision-and-estimand builder
- Replace: `src/boec/paper_figures/figure3.py` with the migrated terminal-rule builder
- Replace: `src/boec/paper_figures/figure4.py` with the migrated SPADE evidence builder
- Create: `src/boec/paper_figures/figure5.py` from the migrated certification builder
- Modify: `src/boec/paper_figures/export.py`
- Modify: `tests/test_paper_figure_builders.py`
- Modify: `tests/test_paper_figure_export.py`

**Interfaces:**
- Produces: `LANDSCAPE_FAMILIES`, `landscape_slice(family, resolution=48)`, `build_figure1(preset)`, and final builders `build_figure1` through `build_figure5` with matching `fig1` through `fig5` IDs.
- Consumes: `HillOracle(load_ensemble(6)[0])`, `FAMILY_ORACLE`, shared editorial layout, and semantic evidence adapters.

- [ ] **Step 1: Write failing sequence and landscape tests**

Add:

```python
def test_figure1_separates_landscapes_methods_campaign_and_outputs():
    bundle = build_figure1(get_preset("portable"))
    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["families"] == [
        "hill", "ackley", "hartmann6", "levy", "rosenbrock"
    ]
    assert bundle.panel_data["B"]["method_families"] == [
        "classical experimental design", "space-filling design",
        "sequential Bayesian optimization", "SPADE",
    ]
    assert bundle.panel_data["C"]["campaign_wells"] == 48
    assert set(bundle.panel_data["C"]["outputs"]) == {
        "point", "region map", "certificate", "experimental cost"
    }

@pytest.mark.parametrize("family", LANDSCAPE_FAMILIES)
def test_landscape_glyph_is_deterministic_finite_vector_data(family):
    first = landscape_slice(family, resolution=48)
    second = landscape_slice(family, resolution=48)
    assert np.array_equal(first.z, second.z)
    assert first.z.shape == (48, 48)
    assert np.isfinite(first.z).all()
    assert first.z.min() == pytest.approx(0.0)
    assert first.z.max() == pytest.approx(1.0)

def test_export_sequence_is_exactly_five_figures(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    assert list(manifest["figures"]) == ["fig1", "fig2", "fig3", "fig4", "fig5"]
```

- [ ] **Step 2: Run tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py tests/test_paper_figure_export.py -q
```

Expected: missing `landscape_glyphs`, missing Figure 5, and a four-figure manifest.

- [ ] **Step 3: Implement deterministic landscape slices**

Use the first two coordinates as the displayed plane and fix every other coordinate at the oracle optimum:

```python
@dataclass(frozen=True)
class LandscapeSlice:
    family: str
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray

def landscape_slice(family: str, resolution: int = 48) -> LandscapeSlice:
    oracle = HillOracle(load_ensemble(6)[0]) if family == "hill" else FAMILY_ORACLE[family](6)
    grid = np.linspace(0.0, 1.0, resolution)
    gx, gy = np.meshgrid(grid, grid)
    points = np.repeat(oracle.optimum_x[None, :], resolution * resolution, axis=0)
    points[:, 0], points[:, 1] = gx.ravel(), gy.ravel()
    raw = oracle.f(points).reshape(resolution, resolution)
    scaled = (raw - raw.min()) / (raw.max() - raw.min())
    return LandscapeSlice(family, gx, gy, scaled)
```

Render each glyph with vector contours and the same normalized luminance scale. The normalization is a visual fingerprint, not a cross-family magnitude comparison, and the caption must say so.

- [ ] **Step 4: Migrate builders and implement the new Figure 1**

Preserve each old builder while shifting it one number forward, then update module docstrings, function names, `FigureBundle.figure_id`, caption numbers, test imports, and exporter imports. Build new Figure 1 as three full-width bands:

1. `a  Response landscapes` with five compact vector contour glyphs.
2. `b  Design strategies` with four grouped method-family modules and one-shot/sequential status.
3. `c  Decisions from one campaign` with the 48-well observation loop and four output branches.

Use the headline `Study architecture separates landscapes, design strategies and decision outputs` and the deck `Five controlled response families · common noisy campaigns · point, map and certification objectives`. Do not print performance values in this figure.

- [ ] **Step 5: Update exporter ordering and review sheets**

Build in this exact order:

```python
builders = (
    (build_figure1, None),
    (build_figure2, None),
    (build_figure3, terminal_data),
    (build_figure4, spade_data),
    (build_figure5, certification_data),
)
png_paths = [figure_dir / f"fig{i}.png" for i in range(1, 6)]
```

Update contact-sheet geometry for a two-column layout with a final full-width fifth card. Update deterministic-export tests to compare all five figures.

- [ ] **Step 6: Run the focused sequence tests and inspect Figure 1**

Run the Task 3 tests, export portable and PLOS Figure 1 previews, and inspect both. Expected: five figures build, all glyphs are vector contours, method families are not labelled “models,” and no card text clips.

- [ ] **Step 7: Commit**

```bash
git add src/boec/paper_figures/landscape_glyphs.py src/boec/paper_figures/figure1.py \
  src/boec/paper_figures/figure2.py src/boec/paper_figures/figure3.py \
  src/boec/paper_figures/figure4.py src/boec/paper_figures/figure5.py \
  src/boec/paper_figures/export.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_export.py
git commit -m "feat: add five-figure study architecture"
```

### Task 4: Rebuild Figure 2 as the decision-and-estimand definition

**Files:**
- Modify: `src/boec/paper_figures/figure2.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `editorial_figure`, `content_box`, `panel_heading`, and geometry registration.
- Produces: spacious observation loop, point/region decision lanes, estimand ledger, caption, long description, and `FigureBundle("fig2", ...)`.

- [ ] **Step 1: Write failing hierarchy and geometry tests**

Require these exact headings and rows:

```python
assert bundle.layout_rows == (("A", "B"), ("C",))
assert bundle.headline == "One 48-well campaign supports distinct scientific decisions"
assert panel_titles == {
    "a": "Campaign observation loop",
    "b": "Point and region decisions",
    "c": "Estimand ledger",
}
assert bundle.panel_data["B"]["point deliverables"] == (
    "tested-best", "measured selection", "model recommendation", "confirmation"
)
```

Parameterize portable, RSC, Nature, and PLOS. Assert registered node and table-cell containment with 2 pt padding and no connector intersects a text extent.

- [ ] **Step 2: Run Figure 2 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure2 -q
```

Expected: the migrated first-generation layout lacks the headline/deck contract and uses compressed multiline decision cards.

- [ ] **Step 3: Implement the spacious two-row composition**

Use a 154 mm portable canvas. Allocate the first analytical row to two equal-width panels and the lower row to a full-width ledger. In Panel A, keep four short content-sized nodes on one baseline. In Panel B, give each point and region deliverable its own row within two clearly titled lanes. In Panel C, retain the exact six-column lookup table but size each row from rendered line count and align numerical fields.

Use the deck `Observation, selection, mapping and certification are different reported objects`. Remove colour names from visible prose. The caption must state that this figure contains no performance result.

- [ ] **Step 4: Verify all presets and inspect final-size previews**

Run Figure 2 tests. Render the portable preview at manuscript reading size and the PLOS preview at 100%. Expected: no wrapped word is split awkwardly, arrows terminate at card boundaries, and every ledger row is readable without zooming.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure2.py tests/test_paper_figure_builders.py
git commit -m "feat: clarify benchmark decisions figure"
```

### Task 5: Rebuild Figure 3 around the dominant paired terminal-rule result

**Files:**
- Modify: `src/boec/paper_figures/figure3.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_terminal_rule_data`, shared method encodings, and editorial heading geometry.
- Produces: full-width paired-effect forest, lower slopegraph, lower decomposition panel, and `FigureBundle("fig3", ...)`.

- [ ] **Step 1: Write failing layout, title, and numerical-mark tests**

Add:

```python
assert bundle.layout_rows == (("A",), ("B", "C"))
assert bundle.panel_data["A"]["dominant_panel"] is True
assert panel_titles == {
    "a": "Paired terminal-rule effect",
    "b": "Mean regret by rule",
    "c": "What Rule A combines",
}
assert bundle.deck == (
    "Hill · d=6 · σ=0.25 · n=50 paired campaigns · 95% paired-bootstrap intervals"
)
```

Retain exact tests for every mean and interval, the identity `Rule A = search loss + identification loss`, near-black direct labels, and hatch/luminance decomposition.

- [ ] **Step 2: Run Figure 3 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure3 -q
```

Expected: the migrated one-row three-panel layout fails the new row hierarchy.

- [ ] **Step 3: Implement the 150 mm two-row composition**

Place the paired Rule-P-minus-Rule-A forest across the full first row. Label the reference line `no terminal-rule effect` and place `Rule P lowers regret` and `Rule P raises regret` at the appropriate ends of the axis. Put the slopegraph and additive decomposition below with equal widths. Keep each panel title under six words; move all condition and interval language into the deck.

The headline is `The terminal rule changes method rankings on the same campaigns`. The caption defines Rule A as measured selection and Rule P as model recommendation before reporting any contrasts.

- [ ] **Step 4: Verify and inspect all presets**

Run Figure 3 tests, render all four presets, and inspect the forest at final physical size. Expected: the forest is visually dominant, method names do not collide, and the decomposition legend occupies reserved space below or beside the data rather than covering it.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure3.py tests/test_paper_figure_builders.py
git commit -m "feat: prioritize terminal rule evidence"
```

### Task 6: Rebuild Figure 4 as the central SPADE point–map–cost result

**Files:**
- Modify: `src/boec/paper_figures/figure4.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_spade_evidence_data`, exact contrast IDs, shared method encodings, and the ±0.02 practical-equivalence contract.
- Produces: Pareto panel, registered contrast forest, full-width feedback-round panel, full-width Hartmann robustness facets, and `FigureBundle("fig4", ...)`.

- [ ] **Step 1: Write failing row, deck, and claim-safety tests**

Add:

```python
assert bundle.layout_rows == (("A", "B"), ("C",), ("D",))
assert bundle.deck == (
    "Primary Hill evidence: d=6 · σ=0.10 · n=25 paired campaigns · "
    "95% paired intervals · practical-equivalence region ±0.02"
)
assert panel_titles == {
    "a": "Map–point trade-off",
    "b": "Registered paired contrasts",
    "c": "Experimental feedback",
    "d": "Hartmann robustness",
}
assert bundle.panel_data["B"]["interpretation"] == (
    "map error improves; regret remains within the registered practical-equivalence region"
)
```

Pin all three exact contrasts, the 48-well constant, rounds `[1, 1, 2, 3, 10, 10]`, direct-label subset, shared Hartmann scales, and descriptive-only status. Assert no headline or caption says SPADE has lower point regret than qLogNEI.

- [ ] **Step 2: Run Figure 4 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure4 -q
```

Expected: the migrated 2×2 layout and old headline fail.

- [ ] **Step 3: Implement the 190 mm three-row composition**

Allocate two panels only in the first row. Give both axes at least 70 mm width. Use deterministic leader offsets for SPADE, qLogNEI, Sobol, and classical DoE. In the contrast forest, render the ±0.02 region as a low-luminance band with labelled boundaries and keep map and regret rows visually distinct.

Give feedback rounds a full-width row with one statement that all methods use 48 wells. Give Hartmann a full-width final section containing aligned `d = 6` and `d = 8` map/regret facets with shared scales and a visible `descriptive means; intervals unavailable` deck.

Use the headline `SPADE improves map recovery within practical point-regret parity`. The long description must report all three exact effects and intervals.

- [ ] **Step 4: Verify scientific and visual contracts**

Run Figure 4 tests plus `tests/test_paper_figure_evidence.py`. Render every preset and inspect the portable and PLOS versions. Expected: no panel is narrower than its labels require, the practical-equivalence region is unambiguous in grayscale, and Hartmann evidence is not visually merged with the primary Hill inference.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure4.py tests/test_paper_figure_builders.py
git commit -m "feat: rebuild central spade evidence figure"
```

### Task 7: Rebuild Figure 5 as a spacious reliability-and-certification argument

**Files:**
- Modify: `src/boec/paper_figures/figure5.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_certification_data`, exact answer counts, exact Clopper–Pearson intervals, and status-gutter layout.
- Produces: cross-family answer/containment row, full-width prospective Hill panel, full-width retrospective reliability panel, and `FigureBundle("fig5", ...)`.

- [ ] **Step 1: Write failing row, status, and denominator tests**

Require:

```python
assert bundle.layout_rows == (("A", "B"), ("C",), ("D",))
assert panel_titles == {
    "a": "Campaign answer rate",
    "b": "Conditional containment",
    "c": "Prospective Hill assurance",
    "d": "Retrospective reliability",
}
assert bundle.panel_data["A"]["counts"] == {
    "ackley": "0/50", "hartmann6": "11/50", "hill": "50/50",
    "levy": "49/50", "rosenbrock": "50/50",
}
assert bundle.panel_data["A"]["ackley_status"] == "declined to certify"
assert bundle.panel_data["B"]["zero_denominator_is_not_zero_containment"] is True
```

Assert all prospective Hill `x/n` labels, conditional family denominators, exact intervals, undercoverage symbol-plus-text encoding, and absence of Holm/multiplicity claims.

- [ ] **Step 2: Run Figure 5 tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_builders.py -k figure5 -q
```

Expected: the migrated 2×2 layout fails the three-row hierarchy and deck contract.

- [ ] **Step 3: Implement the 200 mm three-row composition**

Use two aligned family panels in the first row. Replace filled answer-rate bars with low-ink lollipops or dots and print exact counts. In both panels, place `declined to certify` in a dedicated categorical gutter.

Use the full second row for prospective Hill assurance. Align condition, gamma, alpha, interval, `x/n`, and status fields; keep status text outside the numerical axis. Use the full third row for retrospective calibration/refinement strips with shared method rows and independent horizontal scales.

Use the headline `Reliability and willingness to certify vary across landscapes`. Use the deck `Cross-family α=0.95 campaigns · exact intervals · containment is conditional on answering`. Add `Retrospective Hill · n=1,200 cells per method` only to Panel D.

- [ ] **Step 4: Verify and inspect every certification state**

Run Figure 5 tests and evidence tests. Render all presets. Expected: 0/50 is never plotted as zero containment, empty-certificate rows have no numerical point, warning states remain visible in grayscale, and every denominator can be read at final size.

- [ ] **Step 5: Commit**

```bash
git add src/boec/paper_figures/figure5.py tests/test_paper_figure_builders.py
git commit -m "feat: clarify reliability and certification figure"
```

### Task 8: Generate the panel provenance ledger and complete figure inventory

**Files:**
- Create: `src/boec/paper_figures/provenance.py`
- Create: `docs/PAPER-FIGURE-INVENTORY.md`
- Create: `docs/PAPER-FIGURE-PROVENANCE.md`
- Create: `tests/test_paper_figure_provenance.py`
- Modify: `src/boec/paper_figures/core.py`
- Modify: `src/boec/paper_figures/export.py`
- Modify: `tests/test_paper_figure_export.py`

**Interfaces:**
- Produces: `PanelProvenance`, `provenance_records() -> tuple[PanelProvenance, ...]`, `render_provenance_markdown(...)`, `build_figure_inventory(...)`, `paper-figure-provenance.json`, and documented asset dispositions.
- Consumes: final five-figure panel IDs, `source_paths()`, `results/figures`, `results/paper-figures`, figure-producing scripts, and validation-test node IDs.

- [ ] **Step 1: Write failing coverage and disposition tests**

Add:

```python
def test_every_main_panel_has_exactly_one_provenance_record():
    expected = {
        "fig1": {"A", "B", "C"}, "fig2": {"A", "B", "C"},
        "fig3": {"A", "B", "C"}, "fig4": {"A", "B", "C", "D"},
        "fig5": {"A", "B", "C", "D"},
    }
    observed = {}
    for record in provenance_records():
        if record.disposition != "excluded":
            observed.setdefault(record.figure_id, set()).add(record.panel_id)
    assert observed == expected

def test_every_legacy_asset_has_a_documented_disposition():
    inventory = build_figure_inventory(Path("results"), Path("scripts"))
    legacy = {path.name for path in Path("results/figures").iterdir() if path.is_file()}
    assert legacy == {
        Path(row.path).name for row in inventory if row.collection == "legacy"
    }
    assert all(row.disposition in {
        "main", "supplementary candidate", "obsolete", "unsupported", "excluded pending repair"
    } for row in inventory)

def test_provenance_sources_exist_and_numbers_are_recoverable():
    for record in provenance_records():
        assert all(Path(path).exists() for path in record.source_files)
        assert record.validation_test.startswith("tests/")
        assert record.claim and record.transform and record.evidence_stage
```

- [ ] **Step 2: Run provenance tests and verify RED**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_provenance.py -q
```

Expected: missing provenance module and undocumented inventory.

- [ ] **Step 3: Implement a typed provenance record**

Use:

```python
@dataclass(frozen=True)
class PanelProvenance:
    figure_id: str
    panel_id: str
    claim: str
    evidence_stage: str
    source_files: tuple[str, ...]
    source_keys: tuple[str, ...]
    transform: str
    unit: str
    denominator: str
    interval: str | None
    validation_test: str
    disposition: Literal["main", "supplementary", "descriptive", "excluded"]
```

Conceptual Figure 1 and Figure 2 panels cite implemented source modules or estimand documentation rather than result JSON. Numerical Figures 3–5 cite the exact authoritative JSON files and keys. Figure 4D is `descriptive`; unresolved boundary material is `excluded` and must not share a main-panel identifier.

- [ ] **Step 4: Inventory every existing asset and producing script**

Document all ten files currently under `results/figures`: four critical-difference PNGs, three E4 diagnostic PNGs, and `cost-curves.html`, `fig1-scoring.html`, and `fig3-saddle.html`. Also enumerate generated `results/paper-figures` assets, the five final builders, and manuscript-relevant figure scripts. Give every row one disposition and a one-sentence rationale tied to claim readiness.

Render the same structured records to `docs/PAPER-FIGURE-INVENTORY.md` and `docs/PAPER-FIGURE-PROVENANCE.md`; tests compare generated text with committed text so the documents cannot drift.

- [ ] **Step 5: Integrate provenance into the export manifest**

Write `paper-figure-provenance.json`, hash it in `build-manifest.json`, and include each panel's source-file hashes. Reject a build when a provenance source is missing, a final panel lacks a record, or a displayed source changes during rendering.

- [ ] **Step 6: Run provenance and export tests**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_provenance.py tests/test_paper_figure_export.py -q
```

Expected: every main panel is traceable, all legacy assets are classified, documents reproduce byte-for-byte, and manifests include provenance hashes.

- [ ] **Step 7: Commit**

```bash
git add src/boec/paper_figures/provenance.py src/boec/paper_figures/core.py \
  src/boec/paper_figures/export.py tests/test_paper_figure_provenance.py \
  tests/test_paper_figure_export.py docs/PAPER-FIGURE-INVENTORY.md \
  docs/PAPER-FIGURE-PROVENANCE.md
git commit -m "docs: trace every paper figure result"
```

### Task 9: Validate all presets, accessibility modes, exports, and final assets

**Files:**
- Modify: `src/boec/paper_figures/export.py`
- Modify: `tests/test_paper_figure_layout.py`
- Modify: `tests/test_paper_figure_export.py`
- Regenerate: `results/paper-figures/**`

**Interfaces:**
- Consumes: all five final builders, font/provenance manifests, geometry registrations, and frozen evidence.
- Produces: PDF, SVG, 450 dpi PNG, 600 dpi TIFF, panel data, alt text, captions, long descriptions, provenance, manifests, and normal/grayscale/protan/deutan/tritan review sheets.

- [ ] **Step 1: Expand failing cross-preset and accessibility tests**

Parameterize all five builders over portable, RSC, Nature, and PLOS. Require:

```python
assert_registered_geometry(figure)
assert_no_registered_collisions(figure)
assert_all_text_inside_figure(figure)
assert max(len(row) for row in bundle.layout_rows) <= 2
canonical_methods = ("spade_cf_m0", "qlogei", "qlognei", "doe", "lhs", "sobol", "random")
encodings = {(METHOD_STYLES[key].marker, METHOD_STYLES[key].fill) for key in canonical_methods}
assert len(encodings) == len(canonical_methods)
assert_no_prohibited_content(bundle.panel_data)
assert_no_prohibited_content(bundle.alt_text)
assert_no_prohibited_content(bundle.caption)
assert_no_prohibited_content(bundle.long_description)
```

Update review-mode tests to require `colour`, `grayscale`, `protanopia`, `deuteranopia`, and `tritanopia`. Require the five-figure contact sheet to place Figure 5 full width on its final row.

- [ ] **Step 2: Run focused tests and verify any new failures**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py \
  tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_provenance.py tests/test_paper_figure_export.py -q
```

Expected before final fixes: failures identify exact presets, artists, or review modes that still violate the final contracts.

- [ ] **Step 3: Fix only test-proven defects and finalize review sheets**

Use renderer-measured point offsets or allocated layout ratios to correct each failure. Do not reduce type below the preset minimum and do not expand canvases with tight cropping. Add deterministic colour-vision transforms in Pillow for review artifacts only; canonical figures remain unchanged.

- [ ] **Step 4: Build and mechanically validate every preset**

Run:

```bash
for preset in portable rsc nature plos; do
  MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python \
    scripts/make_paper_figures.py --results-dir results \
    --output-dir "results/paper-figures-${preset}" --preset "$preset"
done
```

Expected: five figures per preset with all eight per-figure representations, provenance JSON, build manifest, contact sheet, and five accessibility review sheets.

- [ ] **Step 5: Validate physical artifacts**

For every PDF/SVG/PNG/TIFF, verify exact width, declared DPI, RGB raster mode, LZW TIFF compression, live SVG text, no unexpected SVG raster images, embedded Charis SIL/STIX fonts, no Type 3 fonts, deterministic hashes, and absence of prohibited content. Run:

```bash
git diff --check
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest \
  tests/test_paper_figure_core.py tests/test_paper_figure_layout.py \
  tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_provenance.py tests/test_paper_figure_export.py -q
```

Expected: all focused tests pass and `git diff --check` reports no errors.

- [ ] **Step 6: Perform final visual review at manuscript scale**

Inspect all five portable PNGs, the five-figure contact sheet, and all accessibility sheets. Check headline clarity, panel hierarchy, word wrapping, labels, leader lines, legends, practical-equivalence band, denominators, categorical states, grayscale identity, and whitespace. Any defect returns to its figure task with a failing regression test before correction.

- [ ] **Step 7: Run the repository suite**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest -q
```

Expected: all paper-figure tests pass. Classify any unrelated pre-existing scientific replay failure without changing unrelated evidence code.

- [ ] **Step 8: Regenerate the canonical package and commit**

```bash
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python \
  scripts/make_paper_figures.py --results-dir results \
  --output-dir results/paper-figures --preset portable
git add results/paper-figures src/boec/paper_figures/export.py \
  tests/test_paper_figure_layout.py tests/test_paper_figure_export.py
git commit -m "figures: publish five-figure paper package"
```

- [ ] **Step 9: Independent final review**

Review the complete implementation range against `docs/superpowers/specs/2026-08-25-five-figure-editorial-redesign-design.md`. Delivery requires no Critical or Important scientific, visual, typography, accessibility, provenance, or reproducibility finding. Do not push; report the branch and final commit SHA to the coordinating task.
