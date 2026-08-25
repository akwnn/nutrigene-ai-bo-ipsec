# Publication Figure System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and render four reproducible, publication-ready main figures for the estimand-aware experimental-design paper, with SPADE as the region-first prospective case study.

**Architecture:** A new `boec.paper_figures` package will separate frozen-artifact loading, semantic panel-data construction, visual styling, figure composition, and multi-format export. Figure builders consume normalized dictionaries rather than repository paths, return a figure plus panel data and alt text, and never fit models or rerun campaigns. A single CLI writes vector and raster artwork, panel-data sidecars, alt text, a provenance manifest, and a final-size contact sheet.

**Tech Stack:** Python 3.11+, Matplotlib 3.11.1, NumPy 2.4.6, SciPy 1.17.1, Pillow supplied by Matplotlib, pytest 9.1.1, Poppler command-line QA.

## Global Constraints

- Source design: `docs/superpowers/specs/2026-08-24-publication-figures-design.md`.
- Rendering must use committed JSON artifacts only; figure code must not fit a model, evaluate an oracle, rerun a campaign, or read narrative prose as numerical data.
- The current boundary-targeting comparison is prohibited. No output may contain `spade_random_plate2`, `KF-3`, `KF-4`, its estimate, interval, verdict, or interpretation.
- Figure 3 may show Hartmann means descriptively, but no Hartmann interval may be inferred while raw prospective condition files are absent.
- Figure 4 containment must use the cross-fit estimator, exclude empty certificates from numerator and denominator, and preserve exact `x/n` labels.
- Matplotlib is the only required rendering dependency; do not add SciencePlots, LaTeX, or generative-image dependencies.
- Use Arial or Helvetica-compatible sans-serif text, `pdf.fonttype = 42`, and `svg.fonttype = none`.
- Method identity must use both colour and marker shape. Required family colours are SPADE `#009E73`, Bayesian optimization `#0072B2`, classical DoE `#D55E00`, space filling `#6B7280`, warning `#B2182B`, and reference ink `#202124`.
- Export every main figure as editable PDF and SVG, 600-dpi TIFF, and 450-dpi PNG, plus panel-data JSON and plain-text alt text.
- Default portable width is 178 mm. Include 171-mm RSC, 183-mm Nature-style, and larger-text PLOS presets.
- Final-size body text is 7-8 pt and panel labels are 8 pt bold lowercase for the portable, RSC, and Nature-style presets.
- Submission artwork contains no figure-level marketing titles, gradients, drop shadows, 3-D effects, dual axes, rainbow palettes, red-green identity encodings, or significance stars.
- Missing, ambiguous, duplicate, or non-finite evidence must raise an actionable exception rather than being silently omitted.

## File Structure

- Create `src/boec/paper_figures/__init__.py`: stable public API.
- Create `src/boec/paper_figures/core.py`: bundle dataclass, JSON validation, hashing, and constants.
- Create `src/boec/paper_figures/style.py`: venue presets, method styles, panel labels, and axis styling.
- Create `src/boec/paper_figures/paper.mplstyle`: committed Matplotlib visual contract.
- Create `src/boec/paper_figures/evidence.py`: authoritative artifact adapters and panel-data transforms.
- Create `src/boec/paper_figures/figure1.py`: benchmark-definition schematic.
- Create `src/boec/paper_figures/figure2.py`: terminal-rule figure.
- Create `src/boec/paper_figures/figure3.py`: point-map-cost figure.
- Create `src/boec/paper_figures/figure4.py`: calibration-containment-non-vacuity figure.
- Create `src/boec/paper_figures/export.py`: multi-format exports, sidecars, manifest, and contact sheet.
- Create `scripts/make_paper_figures.py`: one-command build entry point.
- Modify `pyproject.toml`: package the `.mplstyle` resource.
- Create `tests/test_paper_figure_core.py`: styles, presets, and validation tests.
- Create `tests/test_paper_figure_evidence.py`: numerical provenance and boundary-exclusion tests.
- Create `tests/test_paper_figure_builders.py`: panel semantics and rendering tests.
- Create `tests/test_paper_figure_export.py`: format, dimension, sidecar, and manifest tests.
- Generate `results/paper-figures/portable/`: final figure files and sidecars.
- Generate `results/paper-figures/build-manifest.json`: source and output hashes.
- Generate `results/paper-figures/paper-figures-contact-sheet.png`: visual-review sheet.

---

### Task 1: Establish the figure core, visual contract, and venue presets

**Files:**
- Create: `src/boec/paper_figures/__init__.py`
- Create: `src/boec/paper_figures/core.py`
- Create: `src/boec/paper_figures/style.py`
- Create: `src/boec/paper_figures/paper.mplstyle`
- Modify: `pyproject.toml`
- Create: `tests/test_paper_figure_core.py`

**Interfaces:**
- Produces: `FigureBundle`, `VenuePreset`, `get_preset(name)`, `method_style(arm)`, `apply_axis_style(ax)`, `panel_label(ax, label)`, `load_json(path)`, and `sha256_file(path)`.
- Consumes: no earlier task.

- [ ] **Step 1: Write failing tests for presets, palette, bundles, and strict JSON loading**

```python
# tests/test_paper_figure_core.py
from __future__ import annotations

import json

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from boec.paper_figures.core import FigureBundle, load_json
from boec.paper_figures.style import METHOD_STYLES, get_preset, panel_label


def test_required_method_families_have_redundant_encodings():
    assert METHOD_STYLES["spade_cf_m0"].colour == "#009E73"
    assert METHOD_STYLES["qlognei"].colour == "#0072B2"
    assert METHOD_STYLES["doe"].colour == "#D55E00"
    assert METHOD_STYLES["sobol"].colour == "#6B7280"
    assert len({METHOD_STYLES[k].marker for k in ("spade_cf_m0", "qlognei", "doe", "sobol")}) == 4


@pytest.mark.parametrize(
    ("name", "width_mm"),
    [("portable", 178.0), ("rsc", 171.0), ("nature", 183.0)],
)
def test_double_column_widths_are_physical(name, width_mm):
    assert get_preset(name).width_mm == width_mm


def test_panel_label_is_lowercase_and_bold():
    fig, ax = plt.subplots()
    artist = panel_label(ax, "a")
    assert artist.get_text() == "a"
    assert artist.get_fontweight() == "bold"
    plt.close(fig)


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError, match="top-level JSON object"):
        load_json(path)


def test_figure_bundle_requires_all_metadata():
    fig, _ = plt.subplots()
    bundle = FigureBundle("fig1", fig, {"A": {"claim": "definition"}}, "A benchmark schematic.")
    assert bundle.figure_id == "fig1"
    plt.close(fig)
```

- [ ] **Step 2: Run the core tests and verify the missing package failure**

Run: `pytest tests/test_paper_figure_core.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'boec.paper_figures'`.

- [ ] **Step 3: Implement the core dataclasses and strict helpers**

```python
# src/boec/paper_figures/core.py
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from matplotlib.figure import Figure


PROHIBITED_TOKENS = ("spade_random_plate2", "KF-3", "KF-4")


@dataclass(frozen=True)
class FigureBundle:
    figure_id: str
    figure: Figure
    panel_data: dict[str, Any]
    alt_text: str


def load_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a top-level JSON object")
    return payload


def require_keys(record: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - record.keys()
    if missing:
        raise ValueError(f"{context}: missing keys {sorted(missing)}")


def assert_no_prohibited_content(value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True)
    found = [token for token in PROHIBITED_TOKENS if token in encoded]
    if found:
        raise ValueError(f"prohibited boundary evidence present: {found}")


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Implement method styling, physical presets, and the committed style sheet**

```python
# src/boec/paper_figures/style.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodStyle:
    label: str
    colour: str
    marker: str
    fill: str = "full"


@dataclass(frozen=True)
class VenuePreset:
    name: str
    width_mm: float
    body_pt: float
    panel_pt: float
    png_dpi: int = 450
    tiff_dpi: int = 600

    def figsize(self, height_mm: float) -> tuple[float, float]:
        return self.width_mm / 25.4, height_mm / 25.4


METHOD_STYLES = {
    "spade_cf_m0": MethodStyle("SPADE", "#009E73", "o"),
    "versionb": MethodStyle("SPADE", "#009E73", "o"),
    "qlogei": MethodStyle("qLogEI", "#0072B2", "^", "none"),
    "qlognei": MethodStyle("qLogNEI", "#0072B2", "^"),
    "doe": MethodStyle("Classical DoE", "#D55E00", "s"),
    "lhs": MethodStyle("Latin hypercube", "#6B7280", "D", "none"),
    "sobol": MethodStyle("Sobol", "#6B7280", "D"),
    "random": MethodStyle("Random", "#6B7280", "P", "none"),
}

PRESETS = {
    "portable": VenuePreset("portable", 178.0, 7.5, 8.0),
    "rsc": VenuePreset("rsc", 171.0, 7.5, 8.0),
    "nature": VenuePreset("nature", 183.0, 7.0, 8.0),
    "plos": VenuePreset("plos", 178.0, 9.0, 10.0),
}


def get_preset(name: str) -> VenuePreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"unknown venue preset {name!r}; choose {sorted(PRESETS)}") from exc


def method_style(arm: str) -> MethodStyle:
    if arm.startswith("spade_cf_"):
        return METHOD_STYLES["spade_cf_m0"]
    try:
        return METHOD_STYLES[arm]
    except KeyError as exc:
        raise ValueError(f"no visual encoding registered for arm {arm!r}") from exc


def apply_axis_style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B8BEC5")
    ax.tick_params(width=0.6, length=2.5, color="#6B7280")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.5)
    ax.set_axisbelow(True)


def panel_label(ax, label: str):
    if label not in {"a", "b", "c", "d"}:
        raise ValueError("panel labels must be lowercase a-d")
    return ax.text(-0.10, 1.04, label, transform=ax.transAxes, fontweight="bold", va="bottom")
```

```ini
# src/boec/paper_figures/paper.mplstyle
font.family: sans-serif
font.sans-serif: Arial, Helvetica, DejaVu Sans
mathtext.fontset: dejavusans
pdf.fonttype: 42
ps.fonttype: 42
svg.fonttype: none
axes.linewidth: 0.6
lines.linewidth: 1.0
patch.linewidth: 0.7
xtick.major.width: 0.6
ytick.major.width: 0.6
legend.frameon: False
figure.facecolor: white
axes.facecolor: white
savefig.facecolor: white
savefig.transparent: False
```

Add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"boec.paper_figures" = ["*.mplstyle"]
```

Export the public types from `src/boec/paper_figures/__init__.py`:

```python
from .core import FigureBundle
from .style import VenuePreset, get_preset

__all__ = ["FigureBundle", "VenuePreset", "get_preset"]
```

- [ ] **Step 5: Run the core tests and commit**

Run: `pytest tests/test_paper_figure_core.py -v`

Expected: all tests pass.

```bash
git add pyproject.toml src/boec/paper_figures tests/test_paper_figure_core.py
git commit -m "feat: establish publication figure style system"
```

---

### Task 2: Normalize authoritative evidence into panel-data records

**Files:**
- Create: `src/boec/paper_figures/evidence.py`
- Create: `tests/test_paper_figure_evidence.py`

**Interfaces:**
- Consumes: `load_json`, `require_keys`, and `assert_no_prohibited_content` from Task 1; JSON files under `results/`.
- Produces: `build_figure2_data(results_dir)`, `build_figure3_data(results_dir)`, `build_figure4_data(results_dir)`, and `source_paths(results_dir)`.

- [ ] **Step 1: Write failing numerical-anchor and exclusion tests**

```python
# tests/test_paper_figure_evidence.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from boec.paper_figures.evidence import build_figure2_data, build_figure3_data, build_figure4_data


RESULTS = Path("results")


def test_figure2_uses_current_fix1_values():
    data = build_figure2_data(RESULTS)
    by_arm = {row["arm"]: row for row in data["rule_means"]}
    assert by_arm["doe"]["rule_a"] == pytest.approx(0.0958008941)
    assert by_arm["doe"]["rule_p"] == pytest.approx(0.1992871533)
    assert by_arm["versionb"]["rule_p"] == pytest.approx(0.1003171922)
    for row in data["decomposition"]:
        assert row["rule_a"] == pytest.approx(row["oracle_best"] + row["identification_gap"])


def test_figure3_uses_common_rule_p_and_excludes_boundary_arm():
    data = build_figure3_data(RESULTS)
    encoded = json.dumps(data)
    assert "spade_random_plate2" not in encoded
    assert "KF-3" not in encoded and "KF-4" not in encoded
    target = {row["arm"]: row for row in data["target_points"]}
    assert target["spade_cf_m0"]["regret_p"] == pytest.approx(0.0843635436)
    assert target["spade_cf_m0"]["map_error"] == pytest.approx(0.180414)
    contrasts = {row["contrast_id"]: row for row in data["contrasts"]}
    assert contrasts["map_spade_minus_qlognei"]["mean"] == pytest.approx(-0.0330745)
    assert contrasts["regret_spade_minus_qlognei"]["mean"] == pytest.approx(0.0152724734)


def test_figure4_exact_hill_cell_preserves_denominator():
    data = build_figure4_data(RESULTS)
    cells = {row["cell_id"]: row for row in data["hill_containment"]}
    cell = cells["spade_cf_m0|hill-d6-s0.1|tf0.25|g0.95|a0.95"]
    assert (cell["x"], cell["n"]) == (43, 50)
    assert cell["empty_rate"] == pytest.approx(0.50)
    assert cell["estimator"] == "crossfit"


def test_ambiguous_duplicate_certificate_cell_fails(tmp_path):
    source = json.loads((RESULTS / "final-spade-certificate.json").read_text())
    source["cells"].append(source["cells"][0])
    (tmp_path / "final-spade-certificate.json").write_text(json.dumps(source))
    for name in ("p7-murphy.json", "p8-predictions.json", "p8-certificate-families.json"):
        (tmp_path / name).write_bytes((RESULTS / name).read_bytes())
    with pytest.raises(ValueError, match="duplicate cell_id"):
        build_figure4_data(tmp_path)
```

- [ ] **Step 2: Run the evidence tests and confirm imports fail**

Run: `pytest tests/test_paper_figure_evidence.py -v`

Expected: collection fails because `boec.paper_figures.evidence` does not exist.

- [ ] **Step 3: Implement strict loaders and Figure 2 transforms**

```python
# src/boec/paper_figures/evidence.py
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta

from .core import assert_no_prohibited_content, load_json, require_keys


FIGURE2_RULE_ARMS = ("doe", "qlogei", "qlognei", "versionb")
FIGURE2_DECOMPOSITION_ARMS = ("doe", "qlognei", "lhs", "sobol")
FIGURE3_ARMS = ("doe", "lhs", "sobol", "qlogei", "qlognei", "spade_cf_m0")


def _unique(rows: list[dict[str, Any]], predicate, context: str) -> dict[str, Any]:
    matches = [row for row in rows if predicate(row)]
    if len(matches) != 1:
        raise ValueError(f"{context}: expected exactly one row, found {len(matches)}")
    return matches[0]


def source_paths(results_dir: Path) -> tuple[Path, ...]:
    names = (
        "fix1-terminal-rule.json", "fix1-analysis.json", "step0-oracle-best.json",
        "final-spade-regret-pareto.json", "final-spade-kill-ledger.json",
        "p7-murphy.json", "final-spade-certificate.json",
        "p8-predictions.json", "p8-certificate-families.json",
    )
    return tuple(Path(results_dir) / name for name in names)


def build_figure2_data(results_dir: Path) -> dict[str, Any]:
    terminal = load_json(Path(results_dir) / "fix1-terminal-rule.json")
    analysis = load_json(Path(results_dir) / "fix1-analysis.json")
    oracle = load_json(Path(results_dir) / "step0-oracle-best.json")
    require_keys(analysis, {"per_arm", "statistics"}, "fix1 analysis")
    per_arm = {row["arm"]: row for row in analysis["per_arm"]}
    terminal_by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in terminal["rows"]:
        if row["arm"] in FIGURE2_RULE_ARMS:
            terminal_by_arm[row["arm"]].append(row)
    for arm in FIGURE2_RULE_ARMS:
        rows = terminal_by_arm[arm]
        if len(rows) != per_arm[arm]["n"]:
            raise ValueError(f"{arm}: raw-row count does not match fix1 analysis")
        raw_a = float(np.mean([r["regret_a"] for r in rows]))
        raw_p = float(np.mean([r["regret_p"] for r in rows]))
        if not (np.isfinite(raw_a) and np.isfinite(raw_p)):
            raise ValueError(f"{arm}: non-finite terminal-rule mean")
        if not np.allclose((raw_a, raw_p), (per_arm[arm]["mean_rule_a"], per_arm[arm]["mean_rule_p"]), atol=1e-12):
            raise ValueError(f"{arm}: fix1 raw rows do not reconcile with analysis")
    means = [{
        "arm": arm,
        "rule_a": per_arm[arm]["mean_rule_a"],
        "rule_p": per_arm[arm]["mean_rule_p"],
        "rounds": per_arm[arm]["rounds"],
        "n": per_arm[arm]["n"],
    } for arm in FIGURE2_RULE_ARMS]
    contrasts = [{
        "arm": arm,
        "mean": per_arm[arm]["delta_p_minus_a"]["mean"],
        "lo": per_arm[arm]["delta_p_minus_a"]["lo"],
        "hi": per_arm[arm]["delta_p_minus_a"]["hi"],
        "n": per_arm[arm]["delta_p_minus_a"]["n"],
    } for arm in FIGURE2_RULE_ARMS]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in oracle["rows"]:
        if row["arm"] in FIGURE2_DECOMPOSITION_ARMS:
            grouped[row["arm"]].append(row)
    decomposition = []
    for arm in FIGURE2_DECOMPOSITION_ARMS:
        rows = grouped[arm]
        rule_a = float(np.mean([r["rule_a"] for r in rows]))
        oracle_best = float(np.mean([r["oracle_best"] for r in rows]))
        identification_gap = float(np.mean([r["identification_gap"] for r in rows]))
        if not np.isclose(rule_a, oracle_best + identification_gap, atol=1e-12):
            raise ValueError(f"{arm}: Rule A decomposition does not close")
        decomposition.append({"arm": arm, "rule_a": rule_a, "oracle_best": oracle_best,
                              "identification_gap": identification_gap, "n": len(rows)})
    output = {"condition": "hill-d6-s0.25", "rule_means": means,
              "paired_rule_contrasts": contrasts, "decomposition": decomposition,
              "unit": analysis["statistics"]["unit_of_analysis"]}
    assert_no_prohibited_content(output)
    return output
```

- [ ] **Step 4: Implement Figure 3 transforms with an explicit contrast allowlist**

Add to `src/boec/paper_figures/evidence.py`:

```python
def build_figure3_data(results_dir: Path) -> dict[str, Any]:
    pareto = load_json(Path(results_dir) / "final-spade-regret-pareto.json")
    ledger = load_json(Path(results_dir) / "final-spade-kill-ledger.json")
    target_rows = [r for r in pareto["rows"] if r["condition"] == "hill-d6-s0.1"
                   and r["arm"] in FIGURE3_ARMS]
    if {r["arm"] for r in target_rows} != set(FIGURE3_ARMS):
        raise ValueError("Figure 3 target rows are incomplete")
    target_points = [{"arm": r["arm"], "map_error": r["symmetric_difference"],
                      "regret_p": r["regret"]["P"], "rounds": r["rounds"],
                      "wells": r["wells"], "unit": r["unit"]} for r in target_rows]

    # Only these non-boundary entries may be read from the ledger.
    k6, k7, k8 = (ledger["kills"][key] for key in ("KF-6", "KF-7", "KF-8"))
    contrasts = [
        {"contrast_id": "map_spade_minus_sobol", "mean": -k6["effect"],
         "lo": -k6["ci"][1], "hi": -k6["ci"][0], "sesoi": k6["sesoi"], "n": k6["denominator"]},
        {"contrast_id": "map_spade_minus_qlognei", "mean": -k7["effect"],
         "lo": -k7["ci"][1], "hi": -k7["ci"][0], "sesoi": k7["sesoi"], "n": k7["denominator"]},
        {"contrast_id": "regret_spade_minus_qlognei", "mean": k8["effect"],
         "lo": k8["ci"][0], "hi": k8["ci"][1], "sesoi": k8["sesoi"], "n": k8["denominator"]},
    ]
    hartmann = [{"arm": r["arm"], "condition": r["condition"],
                 "map_error": r["symmetric_difference"], "regret_p": r["regret"]["P"],
                 "rounds": r["rounds"], "wells": r["wells"],
                 "evidence_stage": "descriptive; raw-row intervals unavailable"}
                for r in pareto["rows"]
                if r["condition"] in {"hartmann6-d6-s0.25", "hartmann6-d8-s0.25"}
                and r["arm"] in FIGURE3_ARMS]
    output = {"target_points": target_points, "contrasts": contrasts,
              "cost_ledger": target_points, "hartmann": hartmann, "terminal_rule": "P"}
    assert_no_prohibited_content(output)
    return output
```

- [ ] **Step 5: Implement Figure 4 transforms with exact certificate filtering**

Add to `src/boec/paper_figures/evidence.py`:

```python
def _clopper_pearson(x: int, n: int, level: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("Clopper-Pearson interval requires n > 0")
    tail = (1.0 - level) / 2.0
    lo = 0.0 if x == 0 else float(beta.ppf(tail, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1.0 - tail, x + 1, n - x))
    return lo, hi


def build_figure4_data(results_dir: Path) -> dict[str, Any]:
    murphy = load_json(Path(results_dir) / "p7-murphy.json")
    certificate = load_json(Path(results_dir) / "final-spade-certificate.json")
    predictions = load_json(Path(results_dir) / "p8-predictions.json")
    families = load_json(Path(results_dir) / "p8-certificate-families.json")

    ids = [cell["cell_id"] for cell in certificate["cells"]]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate cell_id values: {duplicates[:5]}")

    calibration = []
    for arm in ("doe", "sobol", "qlognei", "versionb"):
        rows = [r for r in murphy["rows"] if r["arm"] == arm]
        calibration.append({"arm": arm, "n": len(rows),
                            "calibration": float(np.mean([r["pred_calibration"] for r in rows])),
                            "refinement": float(np.mean([r["pred_refinement"] for r in rows])),
                            "evidence_stage": "retrospective Hill"})

    hill_containment = []
    for cell in certificate["cells"]:
        if (cell["arm"] == "spade_cf_m0" and cell["condition"].startswith("hill-")
                and cell["tau_frac"] == 0.25 and cell["gamma"] in {0.5, 0.95}
                and cell["alpha"] in {0.8, 0.95} and not cell["infeasible"]):
            crossfit = cell["crossfit"]
            if crossfit["n"] != cell["n_nonempty"]:
                raise ValueError(f"{cell['cell_id']}: cross-fit n does not match non-empty count")
            hill_containment.append({"cell_id": cell["cell_id"], "condition": cell["condition"],
                                     "tau_frac": cell["tau_frac"], "gamma": cell["gamma"],
                                     "alpha": cell["alpha"], "x": crossfit["x"], "n": crossfit["n"],
                                     "proportion": crossfit["proportion"], "ci_lo": crossfit["ci_lo"],
                                     "ci_hi": crossfit["ci_hi"], "empty_rate": cell["empty_rate"],
                                     "estimator": "crossfit"})

    answer_rate = []
    for family, stats in predictions["stats"].items():
        n = stats["n_campaigns"]
        answer_rate.append({"family": family, "answered": n - stats["all_empty"],
                            "n_campaigns": n, "answer_rate": 1.0 - stats["all_empty"] / n,
                            "definition": "campaign returned at least one non-empty certificate"})

    conditional = []
    for family in sorted({row["family"] for row in families["rows"]}):
        rows = [r for r in families["rows"] if r["family"] == family and r["arm"] == "versionb"
                and r["ce_empty_0.8"] is False]
        x = sum(r["ce_empirical_0.8"] == 1.0 for r in rows)
        n = len(rows)
        if n:
            lo, hi = _clopper_pearson(x, n)
            conditional.append({"family": family, "alpha": 0.8, "x": x, "n": n,
                                "proportion": x / n, "ci_lo": lo, "ci_hi": hi,
                                "definition": "containment conditional on a non-empty certificate cell"})
        else:
            conditional.append({"family": family, "alpha": 0.8, "x": 0, "n": 0,
                                "proportion": None, "ci_lo": None, "ci_hi": None,
                                "definition": "no certificate cell returned an answer"})

    output = {"calibration_refinement": calibration, "hill_containment": hill_containment,
              "cross_family_answer_rate": answer_rate,
              "cross_family_conditional_containment": conditional}
    assert_no_prohibited_content(output)
    return output
```

- [ ] **Step 6: Run evidence tests and commit**

Run: `pytest tests/test_paper_figure_evidence.py -v`

Expected: all tests pass and no prohibited token is serialized.

```bash
git add src/boec/paper_figures/evidence.py tests/test_paper_figure_evidence.py
git commit -m "feat: normalize paper figure evidence"
```

---

### Task 3: Build Figure 1 as a journal-grade vector schematic

**Files:**
- Create: `src/boec/paper_figures/figure1.py`
- Create: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `FigureBundle`, `VenuePreset`, `panel_label`, and the committed style sheet.
- Produces: `build_figure1(preset) -> FigureBundle`.

- [ ] **Step 1: Write the Figure 1 semantic test**

```python
# tests/test_paper_figure_builders.py
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.style import get_preset


def test_figure1_defines_campaign_decisions_and_estimands():
    bundle = build_figure1(get_preset("portable"))
    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["A"]["stages"] == ["formulation", "wells", "assay", "model"]
    assert set(bundle.panel_data["B"]["branches"]) == {"point decision", "region decision"}
    assert "contains no performance result" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 3
    plt.close(bundle.figure)
```

- [ ] **Step 2: Run the test and confirm the missing builder failure**

Run: `pytest tests/test_paper_figure_builders.py::test_figure1_defines_campaign_decisions_and_estimands -v`

Expected: import fails because `figure1.py` does not exist.

- [ ] **Step 3: Implement aligned modules, grouped branches, and the estimand ledger**

```python
# src/boec/paper_figures/figure1.py
from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from .core import FigureBundle
from .style import VenuePreset, panel_label


def _node(ax, x, y, w, h, text, face, dashed=False):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                           facecolor=face, edgecolor="#243746", linewidth=0.8,
                           linestyle="--" if dashed else "-")
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7)
    return patch


def _arrow(ax, start, end, colour="#243746"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8,
                                 linewidth=0.8, color=colour))


def build_figure1(preset: VenuePreset) -> FigureBundle:
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        fig = plt.figure(figsize=preset.figsize(142), constrained_layout=True)
        grid = fig.add_gridspec(2, 2, height_ratios=(0.9, 1.25))
        ax_a, ax_b, ax_c = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])
        for ax, label in zip((ax_a, ax_b, ax_c), "abc", strict=True):
            ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1); panel_label(ax, label)

        stages = ((0.02, "Formulation\nvariables", "#E8F1F8"), (0.27, "48-well\ncampaign", "#E8F1F8"),
                  (0.52, "Noisy assay\nresponses", "#FDE9DD"), (0.77, "Response\nmodel", "#DDF3E8"))
        for x, text, face in stages:
            _node(ax_a, x, 0.40, 0.19, 0.22, text, face)
        for x in (0.21, 0.46, 0.71): _arrow(ax_a, (x, 0.51), (x + 0.05, 0.51))
        ax_a.text(0.02, 0.84, "One campaign", fontsize=8, fontweight="bold")

        _node(ax_b, 0.03, 0.40, 0.20, 0.22, "Same sampled\ncampaign", "#E8F1F8")
        _node(ax_b, 0.38, 0.60, 0.56, 0.25, "Point decision\ntested-best | noisy-readout | model | confirmation", "#E8F1F8", True)
        _node(ax_b, 0.38, 0.15, 0.56, 0.25, "Region decision\nacceptable-region map | conservative certificate", "#DDF3E8", True)
        _arrow(ax_b, (0.23, 0.51), (0.38, 0.72)); _arrow(ax_b, (0.23, 0.51), (0.38, 0.27))

        columns = ("Deliverable", "Reported object", "Observable?", "Score", "Extra wells", "Rounds")
        rows = (
            ("Tested-best", "latent best visited", "no", "simple regret", "0", "campaign"),
            ("Measured selection", "one tested well", "yes", "Rule-A regret", "0", "campaign"),
            ("Model recommendation", "predicted optimum", "yes", "Rule-P regret", "0", "campaign"),
            ("Confirmation protocol", "confirmed tested well", "yes", "confirmed regret", "protocol", "campaign + confirmation"),
            ("Acceptable-region map", "set of acceptable inputs", "yes", "symmetric difference", "0", "campaign"),
            ("Certificate", "conservative subset", "yes", "joint containment", "0", "campaign"),
        )
        table = ax_c.table(cellText=rows, colLabels=columns, cellLoc="left", colLoc="left",
                           bbox=(0.01, 0.04, 0.98, 0.86))
        table.auto_set_font_size(False); table.set_fontsize(6.5)
        for (row, _), cell in table.get_celld().items():
            cell.set_edgecolor("#CBD2D9"); cell.set_linewidth(0.5)
            cell.set_facecolor("#F3F6F8" if row == 0 else "white")

    panel_data = {"A": {"stages": ["formulation", "wells", "assay", "model"]},
                  "B": {"branches": {"point decision": 4, "region decision": 2}},
                  "C": {"columns": columns, "rows": rows}}
    alt = ("Benchmark definition. A campaign flows from formulation variables through wells, assay, and model; "
           "the same data then fork into point or region deliverables, each with a distinct estimand. "
           "This schematic contains no performance result.")
    return FigureBundle("fig1", fig, panel_data, alt)
```

- [ ] **Step 4: Run the Figure 1 test and commit**

Run: `pytest tests/test_paper_figure_builders.py::test_figure1_defines_campaign_decisions_and_estimands -v`

Expected: pass.

```bash
git add src/boec/paper_figures/figure1.py tests/test_paper_figure_builders.py
git commit -m "feat: add benchmark definition figure"
```

---

### Task 4: Build Figure 2 from the corrected terminal-rule evidence

**Files:**
- Create: `src/boec/paper_figures/figure2.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_figure2_data(results_dir)` and Task 1 style helpers.
- Produces: `build_figure2(data, preset) -> FigureBundle`.

- [ ] **Step 1: Add tests for the three panel semantics**

```python
from pathlib import Path

from boec.paper_figures.evidence import build_figure2_data
from boec.paper_figures.figure2 import build_figure2


def test_figure2_encodes_same_campaign_rules_contrasts_and_decomposition():
    data = build_figure2_data(Path("results"))
    bundle = build_figure2(data, get_preset("portable"))
    assert set(bundle.panel_data) == {"A", "B", "C"}
    assert bundle.panel_data["B"]["reference"] == 0.0
    assert bundle.panel_data["C"]["identity"] == "Rule A = search loss + identification loss"
    assert "same campaigns" in bundle.alt_text.lower()
    assert len(bundle.figure.axes) == 3
    plt.close(bundle.figure)
```

- [ ] **Step 2: Run the focused test and verify it fails on the absent module**

Run: `pytest tests/test_paper_figure_builders.py::test_figure2_encodes_same_campaign_rules_contrasts_and_decomposition -v`

Expected: import failure for `boec.paper_figures.figure2`.

- [ ] **Step 3: Implement the slope, paired-contrast, and decomposition panels**

```python
# src/boec/paper_figures/figure2.py
from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
import numpy as np

from .core import FigureBundle
from .style import VenuePreset, apply_axis_style, method_style, panel_label


def build_figure2(data: dict, preset: VenuePreset) -> FigureBundle:
    with plt.style.context(str(files("boec.paper_figures").joinpath("paper.mplstyle"))):
        fig, axes = plt.subplots(1, 3, figsize=preset.figsize(74),
                                 gridspec_kw={"width_ratios": (0.9, 1.05, 1.2)}, constrained_layout=True)
        ax_a, ax_b, ax_c = axes
        for ax, label in zip(axes, "abc", strict=True): apply_axis_style(ax); panel_label(ax, label)

        for row in data["rule_means"]:
            style = method_style(row["arm"])
            ax_a.plot((0, 1), (row["rule_a"], row["rule_p"]), color=style.colour, marker=style.marker,
                      markersize=4.5, markerfacecolor="white" if style.fill == "none" else style.colour)
            ax_a.text(1.04, row["rule_p"], style.label, color=style.colour, va="center", fontsize=6.5)
        ax_a.set_xticks((0, 1), ("Rule A", "Rule P")); ax_a.set_ylabel("Mean simple regret")
        ax_a.set_title("Same campaigns, different terminal rule", loc="left", fontsize=8)

        contrasts = data["paired_rule_contrasts"]
        for y, row in enumerate(contrasts):
            style = method_style(row["arm"])
            ax_b.plot((row["lo"], row["hi"]), (y, y), color=style.colour, linewidth=1.6)
            ax_b.scatter(row["mean"], y, color=style.colour, marker=style.marker, s=24, zorder=3)
        ax_b.axvline(0, color="#202124", linewidth=0.8)
        ax_b.set_yticks(range(len(contrasts)), [method_style(r["arm"]).label for r in contrasts])
        ax_b.set_xlabel("Rule P - Rule A regret"); ax_b.set_title("Paired change in the estimand", loc="left", fontsize=8)

        rows = data["decomposition"]
        y = np.arange(len(rows))
        search = np.array([r["oracle_best"] for r in rows])
        identify = np.array([r["identification_gap"] for r in rows])
        ax_c.barh(y, search, color="#A8C7E0", label="Search loss")
        ax_c.barh(y, identify, left=search, color="#E7A77D", label="Identification loss")
        ax_c.set_yticks(y, [method_style(r["arm"]).label for r in rows]); ax_c.invert_yaxis()
        ax_c.set_xlabel("Rule-A simple regret"); ax_c.legend(loc="lower right", fontsize=6.5)
        ax_c.set_title("Measured selection mixes two losses", loc="left", fontsize=8)

    panel_data = {"A": {"rows": data["rule_means"], "pairing": "same campaigns"},
                  "B": {"rows": contrasts, "reference": 0.0, "interval": "paired bootstrap 95%"},
                  "C": {"rows": rows, "identity": "Rule A = search loss + identification loss"}}
    alt = ("The same campaigns change ordering under Rules A and P. Paired intervals show method-specific "
           "terminal-rule changes, while stacked components show that measured selection combines search and identification losses.")
    return FigureBundle("fig2", fig, panel_data, alt)
```

- [ ] **Step 4: Run Figure 2 and evidence tests, then commit**

Run: `pytest tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py -v`

Expected: all tests pass.

```bash
git add src/boec/paper_figures/figure2.py tests/test_paper_figure_builders.py
git commit -m "feat: add terminal rule figure"
```

---

### Task 5: Build Figure 3 as a point-map-cost decision display

**Files:**
- Create: `src/boec/paper_figures/figure3.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_figure3_data(results_dir)` and Task 1 style helpers.
- Produces: `build_figure3(data, preset) -> FigureBundle`.

- [ ] **Step 1: Add tests for common terminal rule, SESOI bands, and descriptive Hartmann status**

```python
from boec.paper_figures.evidence import build_figure3_data
from boec.paper_figures.figure3 import build_figure3


def test_figure3_separates_point_map_and_cost_without_boundary_evidence():
    data = build_figure3_data(Path("results"))
    bundle = build_figure3(data, get_preset("portable"))
    assert bundle.panel_data["A"]["terminal_rule"] == "P"
    assert bundle.panel_data["B"]["sesoi"] == 0.02
    assert bundle.panel_data["C"]["rounds_are_not_point_size"] is True
    assert all(row["evidence_stage"].startswith("descriptive") for row in bundle.panel_data["D"]["rows"])
    assert "spade_random_plate2" not in str(bundle.panel_data)
    assert len(bundle.figure.axes) == 4
    plt.close(bundle.figure)
```

- [ ] **Step 2: Run the focused test and confirm the missing builder failure**

Run: `pytest tests/test_paper_figure_builders.py::test_figure3_separates_point_map_and_cost_without_boundary_evidence -v`

Expected: import failure for `boec.paper_figures.figure3`.

- [ ] **Step 3: Implement the Pareto plane, contrast strip, cost ledger, and Hartmann small multiples**

```python
# src/boec/paper_figures/figure3.py
from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt
import numpy as np

from .core import FigureBundle, assert_no_prohibited_content
from .style import VenuePreset, apply_axis_style, method_style, panel_label


def build_figure3(data: dict, preset: VenuePreset) -> FigureBundle:
    assert_no_prohibited_content(data)
    with plt.style.context(str(files("boec.paper_figures").joinpath("paper.mplstyle"))):
        fig = plt.figure(figsize=preset.figsize(142), constrained_layout=True)
        grid = fig.add_gridspec(2, 2, width_ratios=(1.05, 0.95))
        axes = [fig.add_subplot(grid[i, j]) for i in range(2) for j in range(2)]
        ax_a, ax_b, ax_c, ax_d = axes
        for ax, label in zip(axes, "abcd", strict=True): apply_axis_style(ax); panel_label(ax, label)

        for row in data["target_points"]:
            style = method_style(row["arm"])
            face = "none" if style.fill == "none" else style.colour
            ax_a.scatter(row["map_error"], row["regret_p"], s=38, marker=style.marker,
                         facecolor=face, edgecolor=style.colour, linewidth=1.0)
            ax_a.annotate(style.label, (row["map_error"], row["regret_p"]), xytext=(4, 3),
                          textcoords="offset points", fontsize=6.5, color=style.colour)
        ax_a.set_xlabel("Symmetric-difference error  <- better")
        ax_a.set_ylabel("Rule-P simple regret  <- better")
        ax_a.set_title("Registered target: point-map trade-off", loc="left", fontsize=8)

        contrast_rows = data["contrasts"]
        sesoi = contrast_rows[0]["sesoi"]
        ax_b.axvspan(-sesoi, sesoi, color="#E5E7EB", zorder=0)
        ax_b.axvline(0, color="#202124", linewidth=0.8)
        labels = ("Map: SPADE - Sobol", "Map: SPADE - qLogNEI", "Regret: SPADE - qLogNEI")
        for y, (row, label) in enumerate(zip(contrast_rows, labels, strict=True)):
            ax_b.plot((row["lo"], row["hi"]), (y, y), color="#202124", linewidth=1.5)
            ax_b.scatter(row["mean"], y, color="#009E73", s=26, zorder=3)
        ax_b.set_yticks(range(3), labels); ax_b.invert_yaxis(); ax_b.set_xlabel("Paired difference")
        ax_b.set_title("Effects relative to the +/-0.02 margin", loc="left", fontsize=8)

        costs = data["cost_ledger"]
        ax_c.set_axis_off()
        table_rows = [[method_style(r["arm"]).label, str(r["wells"]), str(r["rounds"])] for r in costs]
        table = ax_c.table(cellText=table_rows, colLabels=("Method", "Wells", "Rounds"),
                           cellLoc="left", colLoc="left", bbox=(0.02, 0.02, 0.96, 0.88))
        table.auto_set_font_size(False); table.set_fontsize(7)
        for (row, _), cell in table.get_celld().items():
            cell.set_edgecolor("#CBD2D9"); cell.set_linewidth(0.5)
            cell.set_facecolor("#F3F6F8" if row == 0 else "white")
        ax_c.set_title("Equal wells do not mean equal feedback rounds", loc="left", fontsize=8)

        conditions = ("hartmann6-d6-s0.25", "hartmann6-d8-s0.25")
        for condition, marker in zip(conditions, ("o", "s"), strict=True):
            rows = [r for r in data["hartmann"] if r["condition"] == condition]
            ax_d.scatter([r["map_error"] for r in rows], [r["regret_p"] for r in rows],
                         marker=marker, s=25, facecolor="none", edgecolor="#6B7280",
                         label=condition.replace("hartmann6-", ""))
        ax_d.set_xlabel("Symmetric-difference error"); ax_d.set_ylabel("Rule-P simple regret")
        ax_d.legend(title="Descriptive means", fontsize=6.5, title_fontsize=6.5)
        ax_d.set_title("Hartmann robustness: intervals unavailable", loc="left", fontsize=8)

    panel_data = {"A": {"rows": data["target_points"], "terminal_rule": data["terminal_rule"]},
                  "B": {"rows": contrast_rows, "sesoi": sesoi},
                  "C": {"rows": costs, "rounds_are_not_point_size": True},
                  "D": {"rows": data["hartmann"], "intervals": "unavailable"}}
    assert_no_prohibited_content(panel_data)
    alt = ("SPADE and batch BO occupy different locations in the target point-map plane. Paired contrasts are "
           "shown against a practical margin, a separate ledger reports wells and rounds, and Hartmann means are descriptive only.")
    return FigureBundle("fig3", fig, panel_data, alt)
```

- [ ] **Step 4: Run all evidence and builder tests, then commit**

Run: `pytest tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py -v`

Expected: all tests pass, including boundary exclusion.

```bash
git add src/boec/paper_figures/figure3.py tests/test_paper_figure_builders.py
git commit -m "feat: add point map and cost figure"
```

---

### Task 6: Build Figure 4 as a reliability and non-vacuity audit

**Files:**
- Create: `src/boec/paper_figures/figure4.py`
- Modify: `tests/test_paper_figure_builders.py`

**Interfaces:**
- Consumes: `build_figure4_data(results_dir)` and Task 1 style helpers.
- Produces: `build_figure4(data, preset) -> FigureBundle`.

- [ ] **Step 1: Add tests for denominators, nominal references, and declined certification**

```python
from boec.paper_figures.evidence import build_figure4_data
from boec.paper_figures.figure4 import build_figure4


def test_figure4_keeps_calibration_containment_and_answer_rate_distinct():
    data = build_figure4_data(Path("results"))
    bundle = build_figure4(data, get_preset("portable"))
    assert set(bundle.panel_data) == {"A", "B", "C", "D"}
    assert all(row["estimator"] == "crossfit" for row in bundle.panel_data["B"]["rows"])
    assert bundle.panel_data["C"]["zero_means"] == "declined to certify"
    assert bundle.panel_data["D"]["effect"] == "containment minus nominal"
    assert "non-empty" in bundle.alt_text
    assert len(bundle.figure.axes) == 4
    plt.close(bundle.figure)
```

- [ ] **Step 2: Run the focused test and confirm the missing builder failure**

Run: `pytest tests/test_paper_figure_builders.py::test_figure4_keeps_calibration_containment_and_answer_rate_distinct -v`

Expected: import failure for `boec.paper_figures.figure4`.

- [ ] **Step 3: Implement calibration-refinement, exact containment, answer-rate, and conditional-containment panels**

```python
# src/boec/paper_figures/figure4.py
from __future__ import annotations

from importlib.resources import files

import matplotlib.pyplot as plt

from .core import FigureBundle
from .style import VenuePreset, apply_axis_style, method_style, panel_label


def build_figure4(data: dict, preset: VenuePreset) -> FigureBundle:
    with plt.style.context(str(files("boec.paper_figures").joinpath("paper.mplstyle"))):
        fig = plt.figure(figsize=preset.figsize(142), constrained_layout=True)
        axes = fig.subplots(2, 2).ravel()
        ax_a, ax_b, ax_c, ax_d = axes
        for ax, label in zip(axes, "abcd", strict=True): apply_axis_style(ax); panel_label(ax, label)

        for row in data["calibration_refinement"]:
            style = method_style(row["arm"])
            ax_a.scatter(row["calibration"], row["refinement"], marker=style.marker, s=36,
                         facecolor="none" if style.fill == "none" else style.colour,
                         edgecolor=style.colour)
            ax_a.annotate(style.label, (row["calibration"], row["refinement"]),
                          xytext=(4, 3), textcoords="offset points", fontsize=6.5)
        ax_a.set_xlabel("Calibration error  <- better"); ax_a.set_ylabel("Refinement  better ->")
        ax_a.set_title("Retrospective Hill evidence", loc="left", fontsize=8)

        cells = data["hill_containment"]
        plotted_cells = []
        ax_b.axvline(0, color="#202124", linewidth=0.8)
        for y, row in enumerate(cells):
            plotted = {**row, "effect": row["proportion"] - row["alpha"],
                       "effect_lo": row["ci_lo"] - row["alpha"],
                       "effect_hi": row["ci_hi"] - row["alpha"]}
            plotted_cells.append(plotted)
            ax_b.plot((plotted["effect_lo"], plotted["effect_hi"]), (y, y), color="#009E73", linewidth=1.4)
            ax_b.scatter(plotted["effect"], y, color="#009E73", s=24)
            ax_b.text(max(plotted["effect_hi"], 0.0) + 0.015, y, f"{row['x']}/{row['n']}",
                      va="center", fontsize=6.3)
        ax_b.set_yticks(range(len(cells)), [f"{r['condition'].replace('hill-', '')}; g={r['gamma']}; a={r['alpha']}" for r in cells])
        ax_b.set_xlabel("Cross-fit containment - nominal (95% exact CI)")
        ax_b.set_title("Prospective Hill: empty certificates excluded", loc="left", fontsize=8)

        answers = data["cross_family_answer_rate"]
        ax_c.barh(range(len(answers)), [r["answer_rate"] for r in answers], color="#6B7280")
        ax_c.set_yticks(range(len(answers)), [r["family"] for r in answers]); ax_c.invert_yaxis()
        ax_c.set_xlim(0, 1); ax_c.set_xlabel("Campaigns returning any non-empty certificate")
        ax_c.set_title("Answer rate", loc="left", fontsize=8)

        conditional = data["cross_family_conditional_containment"]
        for y, row in enumerate(conditional):
            if row["n"] == 0:
                ax_d.text(-0.02, y, "declined", ha="right", va="center", color="#6B7280", fontsize=6.5)
                continue
            effect, lo, hi = row["proportion"] - row["alpha"], row["ci_lo"] - row["alpha"], row["ci_hi"] - row["alpha"]
            ax_d.plot((lo, hi), (y, y), color="#202124", linewidth=1.4)
            ax_d.scatter(effect, y, color="#009E73" if effect >= 0 else "#B2182B", s=24)
            ax_d.text(max(hi, 0.0) + 0.015, y, f"{row['x']}/{row['n']}", va="center", fontsize=6.3)
        ax_d.axvline(0, color="#202124", linewidth=0.8)
        ax_d.set_yticks(range(len(conditional)), [r["family"] for r in conditional]); ax_d.invert_yaxis()
        ax_d.set_xlabel("Containment - nominal assurance")
        ax_d.set_title("Conditional on answering", loc="left", fontsize=8)

    panel_data = {"A": {"rows": data["calibration_refinement"], "evidence": "retrospective Hill"},
                  "B": {"rows": plotted_cells, "reference": 0.0,
                        "empty_policy": "exclude from numerator and denominator"},
                  "C": {"rows": answers, "zero_means": "declined to certify"},
                  "D": {"rows": conditional, "effect": "containment minus nominal"}}
    alt = ("Calibration and refinement differ across methods. Prospective Hill cross-fit containment is shown with "
           "exact intervals and non-empty denominators, while cross-family answer rates are separated from containment conditional on answering.")
    return FigureBundle("fig4", fig, panel_data, alt)
```

- [ ] **Step 4: Run all focused figure tests and commit**

Run: `pytest tests/test_paper_figure_core.py tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py -v`

Expected: all tests pass.

```bash
git add src/boec/paper_figures/figure4.py tests/test_paper_figure_builders.py
git commit -m "feat: add reliability audit figure"
```

---

### Task 7: Add deterministic multi-format export and the one-command build

**Files:**
- Create: `src/boec/paper_figures/export.py`
- Create: `scripts/make_paper_figures.py`
- Create: `tests/test_paper_figure_export.py`

**Interfaces:**
- Consumes: all four builders, all three evidence transforms, `source_paths`, `sha256_file`, and `VenuePreset`.
- Produces: `export_bundle(bundle, output_dir, preset)`, `write_manifest(...)`, `make_contact_sheet(...)`, and CLI `main()`.

- [ ] **Step 1: Write failing export and CLI tests**

```python
# tests/test_paper_figure_export.py
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from boec.paper_figures.export import build_all


def test_build_all_writes_every_required_format_and_sidecar(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    for figure_id in ("fig1", "fig2", "fig3", "fig4"):
        for suffix in ("pdf", "svg", "tiff", "png", "data.json", "alt.txt"):
            path = tmp_path / "portable" / f"{figure_id}.{suffix}"
            assert path.exists() and path.stat().st_size > 100
    assert manifest["preset"]["width_mm"] == 178.0
    assert set(manifest["figures"]) == {"fig1", "fig2", "fig3", "fig4"}
    assert set(manifest["supplementary_reservations"]) == {f"S{i}" for i in range(1, 12)}
    assert (tmp_path / "build-manifest.json").exists()
    assert (tmp_path / "paper-figures-contact-sheet.png").exists()


def test_raster_dimensions_match_dpi(tmp_path):
    build_all(Path("results"), tmp_path, "portable")
    png = Image.open(tmp_path / "portable" / "fig2.png")
    tiff = Image.open(tmp_path / "portable" / "fig2.tiff")
    expected_png_width = round(178.0 / 25.4 * 450)
    expected_tiff_width = round(178.0 / 25.4 * 600)
    assert abs(png.width - expected_png_width) <= 3
    assert abs(tiff.width - expected_tiff_width) <= 3


def test_panel_data_and_alt_text_are_human_readable(tmp_path):
    build_all(Path("results"), tmp_path, "portable")
    data = json.loads((tmp_path / "portable" / "fig3.data.json").read_text())
    assert set(data) == {"A", "B", "C", "D"}
    assert len((tmp_path / "portable" / "fig3.alt.txt").read_text().split()) >= 25
```

- [ ] **Step 2: Run export tests and verify the absent exporter failure**

Run: `pytest tests/test_paper_figure_export.py -v`

Expected: import failure for `boec.paper_figures.export`.

- [ ] **Step 3: Implement lossless sidecars, format exports, hashes, and the contact sheet**

```python
# src/boec/paper_figures/export.py
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import matplotlib.pyplot as plt
from PIL import Image, ImageOps, ImageDraw

from .core import FigureBundle, assert_no_prohibited_content, sha256_file
from .evidence import build_figure2_data, build_figure3_data, build_figure4_data, source_paths
from .figure1 import build_figure1
from .figure2 import build_figure2
from .figure3 import build_figure3
from .figure4 import build_figure4
from .style import get_preset


SUPPLEMENTARY_RESERVATIONS = {
    "S1": "terminal-rule contrasts across dimensions and noise",
    "S2": "per-campaign search and identification distributions",
    "S3": "confirmation and replication sensitivities after refresh",
    "S4": "quadratic saddle and in-region recommendation diagnostics",
    "S5": "regret and arrival curves against wells and rounds",
    "S6": "point-map small multiples across families",
    "S7": "type-I and type-II map-error components",
    "S8": "Murphy decomposition and reliability diagrams",
    "S9": "certificate matrix, empty rates, and feasibility exclusions",
    "S10": "posterior-draw and Monte Carlo sensitivity",
    "S11": "classical-design and unscreened-comparator diagnostics",
}


def _git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def export_bundle(bundle: FigureBundle, output_dir: Path, preset) -> dict:
    assert_no_prohibited_content(bundle.panel_data)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {suffix: output_dir / f"{bundle.figure_id}.{suffix}"
             for suffix in ("pdf", "svg", "png", "tiff", "data.json", "alt.txt")}
    bundle.figure.savefig(paths["pdf"], format="pdf")
    bundle.figure.savefig(paths["svg"], format="svg")
    bundle.figure.savefig(paths["png"], format="png", dpi=preset.png_dpi)
    bundle.figure.savefig(paths["tiff"], format="tiff", dpi=preset.tiff_dpi,
                          pil_kwargs={"compression": "tiff_lzw"})
    paths["data.json"].write_text(json.dumps(bundle.panel_data, indent=2, sort_keys=True) + "\n")
    paths["alt.txt"].write_text(bundle.alt_text.strip() + "\n")
    plt.close(bundle.figure)
    return {name: {"path": str(path), "sha256": sha256_file(path)} for name, path in paths.items()}


def make_contact_sheet(png_paths: list[Path], path: Path) -> None:
    cards = []
    for png_path in png_paths:
        image = Image.open(png_path).convert("RGB")
        image.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
        card = ImageOps.expand(image, border=(30, 80, 30, 30), fill="white")
        ImageDraw.Draw(card).text((30, 25), png_path.stem, fill="#202124")
        cards.append(card)
    width = max(card.width for card in cards) * 2
    row_heights = [max(cards[i].height for i in range(start, min(start + 2, len(cards))))
                   for start in range(0, len(cards), 2)]
    sheet = Image.new("RGB", (width, sum(row_heights)), "#E5E7EB")
    y = 0
    for start, height in zip(range(0, len(cards), 2), row_heights, strict=True):
        for offset, card in enumerate(cards[start:start + 2]): sheet.paste(card, (offset * width // 2, y))
        y += height
    sheet.save(path, dpi=(150, 150))


def build_all(results_dir: Path, output_dir: Path, preset_name: str = "portable") -> dict:
    preset = get_preset(preset_name)
    figure_dir = Path(output_dir) / preset.name
    data2, data3, data4 = (build_figure2_data(results_dir), build_figure3_data(results_dir),
                           build_figure4_data(results_dir))
    bundles = (build_figure1(preset), build_figure2(data2, preset),
               build_figure3(data3, preset), build_figure4(data4, preset))
    figures = {bundle.figure_id: export_bundle(bundle, figure_dir, preset) for bundle in bundles}
    make_contact_sheet([figure_dir / f"fig{i}.png" for i in range(1, 5)],
                       Path(output_dir) / "paper-figures-contact-sheet.png")
    manifest = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "preset": preset.__dict__,
        "sources": {str(path): sha256_file(path) for path in source_paths(results_dir)},
        "figures": figures,
        "supplementary_reservations": SUPPLEMENTARY_RESERVATIONS,
    }
    (Path(output_dir) / "build-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
```

- [ ] **Step 4: Implement the CLI and make the public build API explicit**

```python
# scripts/make_paper_figures.py
from __future__ import annotations

import argparse
from pathlib import Path

from boec.paper_figures.export import build_all


def main() -> int:
    parser = argparse.ArgumentParser(description="Build publication-ready main figures from frozen artifacts.")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/paper-figures"))
    parser.add_argument("--preset", choices=("portable", "rsc", "nature", "plos"), default="portable")
    args = parser.parse_args()
    manifest = build_all(args.results_dir, args.output_dir, args.preset)
    print(f"built {len(manifest['figures'])} figures for {args.preset} at {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to `src/boec/paper_figures/__init__.py`:

```python
from .export import build_all

__all__ = ["FigureBundle", "VenuePreset", "get_preset", "build_all"]
```

- [ ] **Step 5: Run the export tests and commit the complete pipeline**

Run: `pytest tests/test_paper_figure_export.py -v`

Expected: all tests pass and write all 24 figure-specific files plus the manifest and contact sheet in the temporary directory.

```bash
git add src/boec/paper_figures scripts/make_paper_figures.py tests/test_paper_figure_export.py
git commit -m "feat: add reproducible paper figure build"
```

---

### Task 8: Render, mechanically validate, visually inspect, and commit the final package

**Files:**
- Generate: `results/paper-figures/portable/fig1.*`
- Generate: `results/paper-figures/portable/fig2.*`
- Generate: `results/paper-figures/portable/fig3.*`
- Generate: `results/paper-figures/portable/fig4.*`
- Generate: `results/paper-figures/build-manifest.json`
- Generate: `results/paper-figures/paper-figures-contact-sheet.png`

**Interfaces:**
- Consumes: committed code from Tasks 1-7 and frozen files under `results/`.
- Produces: publication-ready portable artwork and a verified provenance record.

- [ ] **Step 1: Run the complete focused test suite**

Run:

```bash
pytest tests/test_paper_figure_core.py tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py tests/test_paper_figure_export.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Build the portable figure package from the committed code revision**

Run:

```bash
python scripts/make_paper_figures.py --results-dir results --output-dir results/paper-figures --preset portable
```

Expected: `built 4 figures for portable at results/paper-figures`.

- [ ] **Step 3: Validate prohibited-content exclusion and sidecar completeness**

Run:

```bash
rg -n 'spade_random_plate2|KF-3|KF-4|targeted plate 2|boundary targeting' results/paper-figures
find results/paper-figures/portable -type f | sort
```

Expected: the prohibited-content scan returns no matches; the file listing contains six files for each of Figures 1-4.

- [ ] **Step 4: Validate embedded fonts, vector text, physical raster size, and TIFF compression**

Run:

```bash
for f in results/paper-figures/portable/*.pdf; do pdffonts "$f"; done
for f in results/paper-figures/portable/*.svg; do rg -q '<text' "$f"; done
python -c 'from pathlib import Path; from PIL import Image; expected={"png":round(178/25.4*450),"tiff":round(178/25.4*600)}; [(lambda im,s: (_ for _ in ()).throw(AssertionError((p,im.width,expected[s]))) if abs(im.width-expected[s])>3 else None)(Image.open(p),p.suffix[1:]) for p in Path("results/paper-figures/portable").glob("fig*.*") if p.suffix[1:] in expected]'
```

Expected: no PDF reports a Type 3 font; every SVG contains editable `<text>` nodes; each raster is within three pixels of the selected physical-width calculation.

- [ ] **Step 5: Inspect every figure at final size and correct any visible defect**

Open `results/paper-figures/paper-figures-contact-sheet.png` and each portable PNG with the image inspection tool. Check all four figures for clipped labels, overlaps, line crossings, unreadably small text, ambiguous encodings, misleading axis direction, missing `x/n`, and disproportionate visual emphasis. If a defect is found, change the responsible builder or style file, add a regression assertion where mechanical detection is possible, rerun Steps 1-4, and re-inspect all four images.

Expected: zero visible defects at the 178-mm final width.

- [ ] **Step 6: Run repository checks and verify deterministic numerical sidecars**

Run:

```bash
git diff --check
cp results/paper-figures/portable/fig3.data.json /tmp/fig3.data.before.json
cp results/paper-figures/portable/fig3.png /tmp/fig3.before.png
python scripts/make_paper_figures.py --results-dir results --output-dir results/paper-figures --preset portable
cmp /tmp/fig3.data.before.json results/paper-figures/portable/fig3.data.json
cmp /tmp/fig3.before.png results/paper-figures/portable/fig3.png
pytest -q
```

Expected: formatting, panel-data, and raster comparisons pass; the full repository test suite passes.

- [ ] **Step 7: Commit the verified publication assets**

```bash
git add results/paper-figures src/boec/paper_figures scripts/make_paper_figures.py tests pyproject.toml
git commit -m "figures: publish estimand-aware paper artwork"
```

Expected: the commit contains four figures in six representations each, the contact sheet, and the build manifest; no unrelated file is staged.
