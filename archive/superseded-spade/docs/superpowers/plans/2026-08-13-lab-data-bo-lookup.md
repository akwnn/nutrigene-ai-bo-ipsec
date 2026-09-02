# Lab FN/VTN Lookup Implementation Plan

> ## ⚠️ SUPERSEDED — 2026-08-14. Historical record; do not execute.
>
> Implemented, with corrections, by
> [`docs/superpowers/specs/2026-08-14-lab-data-pipeline-design.md`](../specs/2026-08-14-lab-data-pipeline-design.md).
> **Paths and one fact below are stale by design** — this file is kept as written on
> 2026-08-13 so the reasoning is auditable, not as a current instruction.
>
> | This plan says | Now |
> |---|---|
> | `data/lab/BO-PURPOSE.md`, `bo_*.csv`, `GATE.md` at the root of `data/lab` | moved to `data/lab/overlay/` |
> | `flow/…`, `protocols/…` | moved to `data/lab/raw/` |
> | metric `novocyte-cd31-cd140a-2026-08-06` | **wrong instrument.** All 52 FCS report `$CYT = CytoFLEX LX`; the string is `cytoflexlx-…` |
> | `src/boec/lab.py` (module) | `src/boec/lab/` (package, 8 modules) |
> | CD31 vs CD140a channel "not in the filenames", gating blocked | **resolved by measurement:** CD31 = `B525-A`, 8.39 pp margin over the runner-up |
> | Task 4 `ContinuousLookupEvaluator` with no `truth()` | built, plus `truth()` and a duplicate-row guard |
>
> What survives unchanged: the coded dose `(dose − 0.5)/19.5`, the refusal to invent
> CD31%, and the rule that this box is not the Hall/Ogle cube.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 12 gated-pending fibronectin/vitronectin FCS files into a discrete Phase-3 lookup table the existing `Evaluator` interface can consume, without mixing them into the Hall/Ogle 6-protein cube or inventing CD31%.

**Architecture:** Keep raw files where they are. The overlay (`BO-PURPOSE.md`, `bo_file_roles.csv`, `bo_primary_conditions.csv`) is the sort. A new `boec.lab` loader reads that CSV into coded `(n, 2)` points `{coating ∈ {0,1}, dose ∈ [0,1]}`. A new `ContinuousLookupEvaluator` matches proposals with `np.allclose` (the Phase 2 `LookupEvaluator` uses `np.rint` because Hall/Ogle levels are −1/0/+1; rint would collide every dose below 0.5). Empty `y` raises — gating is a lab step, not a software guess.

**Tech Stack:** Python 3.11, numpy, pyyaml, pytest. No new dependencies. No FlowKit/fcsparser. No Ax.

## Global Constraints

- Python `>=3.11`; pins in `requirements.txt` (`numpy==2.4.6`, `pyyaml==6.0.3`, `pytest==9.1.1`). Do not add packages.
- Outcome tensors are always `(n, m)` with `m = 1`.
- Metric identity travels on every row: `CD31_pct_flow` / `percent_of_parent` / `novocyte-cd31-cd140a-2026-08-06`. Never mix with Hall/Ogle `CD31_area_per_DAPI`.
- This coating box is `[0.5, 20] µg/mL`. It is not the Phase 1/2 ECM cube and not Hall/Ogle’s FN floor of 22 µg/mL. Coded dose is `(dose_ug_mL - 0.5) / 19.5`.
- `n = 1` tube per level. Missing `y_sd` uses `LookupEvaluator`’s `sd_floor` (positive; never 0).
- Do not move the 255 MB of committed FCS/JPEGs. Do not gate-invent CD31% from unstained thresholds in this plan.
- Do not change `LookupEvaluator`’s `np.rint` index. Phase 2 replay depends on it.
- Protocol wells (`Exp_20260806_1`) and the 21 Jul media screen are out of this plan.

## File map

| File | Responsibility |
|---|---|
| `data/lab/BO-PURPOSE.md` | Already written. Human sort: which files BO may use. |
| `data/lab/bo_file_roles.csv` | Already written. One role per file. |
| `data/lab/bo_primary_conditions.csv` | Already written. 12 rows, `y` empty, `status=awaiting_gating`. Recode dose in Task 2. |
| `data/lab/GATE.md` | Lab-facing gating record. Empty `y` until filled by hand. |
| `configs/lab/coating_2026-08-06.yaml` | Search space + metric for this box only. |
| `src/boec/lab.py` | Load roles + conditions; refuse ungated tables; build X/y/sd. |
| `src/boec/evaluators.py` | Add `ContinuousLookupEvaluator`. Leave `LookupEvaluator` alone. |
| `tests/test_lab.py` | Catalog, coding, ungated refusal, float lookup, Hall/Ogle isolation. |

---

### Task 1: Lock the classification overlay

**Files:**
- Create: `tests/test_lab.py`
- Modify: none of the overlay files except to keep them
- Test: `tests/test_lab.py`

**Interfaces:**
- Consumes: `data/lab/bo_file_roles.csv`, `data/lab/bo_primary_conditions.csv`
- Produces: assertions that the 12 primaries and the gating `us.fcs` cannot be confused

- [ ] **Step 1: Write the failing tests**

```python
"""In-house lab table: what BO may see, and what it must not invent."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
ROLES = LAB / "bo_file_roles.csv"
COND = LAB / "bo_primary_conditions.csv"

PRIMARY = [
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f0.5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f1.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f2.5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f10.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/f20.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v0.5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v1.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v2.5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v5.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v10.fcs",
    "flow/2026-08-06/Exp_20260806_cd31-cd140a/v20.fcs",
]


def _roles() -> list[dict]:
    with ROLES.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _cond() -> list[dict]:
    with COND.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_roles_file_exists_and_covers_every_committed_lab_file():
    rows = _roles()
    assert len(rows) >= 300
    on_disk = {
        p.relative_to(LAB).as_posix()
        for p in LAB.rglob("*")
        if p.is_file()
        and p.name not in {"BO-PURPOSE.md", "bo_file_roles.csv", "bo_primary_conditions.csv", "GATE.md"}
    }
    catalogued = {r["path"] for r in rows}
    missing = on_disk - catalogued
    extra = catalogued - on_disk
    assert missing == set(), missing
    assert extra == set(), extra


def test_exactly_twelve_bo_primary_fcs_and_they_are_the_fn_vtn_titration():
    prim = [r["path"] for r in _roles() if r["role"] == "bo_primary"]
    assert sorted(prim) == sorted(PRIMARY)


def test_unstained_in_the_same_folder_is_gating_not_a_thirteenth_condition():
    us = "flow/2026-08-06/Exp_20260806_cd31-cd140a/us.fcs"
    row = next(r for r in _roles() if r["path"] == us)
    assert row["role"] == "bo_gating"
    assert us not in PRIMARY


def test_aborted_exp2_is_not_for_bo():
    rows = [r for r in _roles() if "Exp_20260806_2" in r["path"] and r["path"].endswith(".fcs")]
    assert rows and all(r["role"] == "not_for_bo" for r in rows)


def test_conditions_table_is_the_twelve_primaries_still_awaiting_gating():
    rows = _cond()
    assert [r["file"] for r in rows] == PRIMARY
    assert all(r["status"] == "awaiting_gating" for r in rows)
    assert all(r["y"] == "" for r in rows)
    assert all(r["n_replicates"] == "1" for r in rows)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_lab.py -v`
Expected: FAIL on collection or on `test_roles_file_exists` if overlay files are missing from the worktree. If the overlay from the previous session is present, these four tests PASS and the later loader tests in Task 3 are the first red. If `BO-PURPOSE.md` / CSVs are missing, copy them from the previous session’s `data/lab/` overlay before continuing.

- [ ] **Step 3: Confirm overlay files are present**

Paths that must exist (already written 2026-08-13, not yet committed):

- `data/lab/BO-PURPOSE.md`
- `data/lab/bo_file_roles.csv`
- `data/lab/bo_primary_conditions.csv`
- `data/lab/README.md` (points at the three files above)

Do not regenerate `bo_file_roles.csv` unless a test names a missing path.

- [ ] **Step 4: Re-run Task 1 tests**

Run: `python -m pytest tests/test_lab.py -v`
Expected: the five tests above PASS.

- [ ] **Step 5: Commit**

```bash
git add data/lab/BO-PURPOSE.md data/lab/bo_file_roles.csv data/lab/bo_primary_conditions.csv data/lab/README.md tests/test_lab.py
git commit -m "$(cat <<'EOF'
Lab overlay: which files BO may use, and the 12-point FN/VTN table still ungated.

EOF
)"
```

---

### Task 2: Coating search space, separate from Hall/Ogle

**Files:**
- Create: `configs/lab/coating_2026-08-06.yaml`
- Modify: `data/lab/bo_primary_conditions.csv` (recode dose against `[0.5, 20]`)
- Modify: `tests/test_lab.py`
- Test: `tests/test_lab.py`

**Interfaces:**
- Consumes: `SearchSpace.from_config`
- Produces: space with `parameters[0].name == "coating"`, `parameters[1].name == "dose"`, metric `CD31_pct_flow`; `coded_dose = (dose_ug_mL - 0.5) / 19.5`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lab.py` (add `import numpy as np` and `import yaml` at the top):

```python
import yaml
from boec.space import SearchSpace

CFG = ROOT / "configs" / "lab" / "coating_2026-08-06.yaml"


def test_coating_space_is_two_d_and_not_the_hall_ogle_cube():
    cfg = yaml.safe_load(CFG.read_text())
    space = SearchSpace.from_config(cfg)
    assert space.dim == 2
    assert space.names == ("coating", "dose")
    assert space.metric.name == "CD31_pct_flow"
    assert space.metric.unit == "percent_of_parent"
    assert space.metric.protocol_version == "novocyte-cd31-cd140a-2026-08-06"
    assert space.parameters[1].physical_low == 0.5
    assert space.parameters[1].physical_high == 20.0


def test_coded_dose_puts_half_ug_at_zero_and_twenty_at_one():
    cfg = yaml.safe_load(CFG.read_text())
    space = SearchSpace.from_config(cfg)
    phys = space.to_physical(np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert phys[0, 1] == pytest.approx(0.5)
    assert phys[1, 1] == pytest.approx(20.0)


def test_conditions_csv_coded_dose_matches_the_declared_box():
    for r in _cond():
        dose = float(r["dose_ug_mL"])
        coded = (dose - 0.5) / 19.5
        assert float(r["coded_dose"]) == pytest.approx(coded)
```

Delete the `X = space.to_physical.__wrapped__...` placeholder line when pasting. The real test is `to_physical` plus the CSV recode.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lab.py::test_coating_space_is_two_d_and_not_the_hall_ogle_cube tests/test_lab.py::test_coded_dose_puts_half_ug_at_zero_and_twenty_at_one tests/test_lab.py::test_conditions_csv_coded_dose_matches_the_declared_box -v`
Expected: FAIL with `FileNotFoundError` for the YAML, and CSV `coded_dose_0_to_20` / old `/20` values not matching `(dose-0.5)/19.5`.

- [ ] **Step 3: Write the config**

Create `configs/lab/coating_2026-08-06.yaml`:

```yaml
# In-house FN/VTN OFAT, 2026-08-06. NOT the Hall/Ogle 6-protein cube.
# Coded dose = (ug/mL - 0.5) / 19.5. Coating: 0 = fibronectin, 1 = vitronectin.
parameters:
  - name: coating
    unit: coded
    ptype: continuous
    physical_low: 0.0
    physical_high: 1.0
  - name: dose
    unit: ug/mL
    ptype: continuous
    physical_low: 0.5
    physical_high: 20.0
metric:
  name: CD31_pct_flow
  unit: percent_of_parent
  protocol_version: novocyte-cd31-cd140a-2026-08-06
constraints:
  equality: []
  inequality: []
  nonlinear_inequality: []
```

`ptype: continuous` for coating (0 or 1) on purpose. `integer` / `categorical` are in the schema but unused by Phase 1 optimizers; discrete candidate mode will only propose the 12 measured rows, so coating never takes an intermediate value.

- [ ] **Step 4: Recode the conditions CSV**

Replace header `coded_dose_0_to_20` with `coded_dose`. Values:

| dose_ug_mL | coded_dose |
|---:|---:|
| 0.5 | 0.0 |
| 1.0 | 0.02564102564102564 |
| 2.5 | 0.10256410256410256 |
| 5.0 | 0.23076923076923078 |
| 10.0 | 0.48717948717948717 |
| 20.0 | 1.0 |

Keep `y` empty and `status=awaiting_gating`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_lab.py -v`
Expected: PASS, including the three new tests.

- [ ] **Step 6: Commit**

```bash
git add configs/lab/coating_2026-08-06.yaml data/lab/bo_primary_conditions.csv tests/test_lab.py
git commit -m "$(cat <<'EOF'
Lab coating space is 2-D FN/VTN on [0.5, 20] ug/mL, not the Hall/Ogle cube.

EOF
)"
```

---

### Task 3: Loader that refuses ungated rows

**Files:**
- Create: `src/boec/lab.py`
- Modify: `tests/test_lab.py`
- Test: `tests/test_lab.py`

**Interfaces:**
- Consumes: `bo_primary_conditions.csv`, `coating_2026-08-06.yaml`
- Produces:
  - `class GatingIncompleteError(ValueError)`
  - `load_conditions(path: Path) -> list[dict]`
  - `conditions_to_arrays(rows) -> tuple[np.ndarray, np.ndarray, np.ndarray]` returning `X (n, 2)`, `y (n,)`, `sd (n,)` with `nan` where empty
  - `load_lab_evaluator(path, space) -> ContinuousLookupEvaluator` — **raises `GatingIncompleteError` if any `y` is empty** (implemented in Task 4 once the class exists; this task stops at arrays + the error class)

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np
from boec.lab import GatingIncompleteError, conditions_to_arrays, load_conditions


def test_loader_reads_twelve_rows_with_nan_y_while_ungated():
    rows = load_conditions(COND)
    X, y, sd = conditions_to_arrays(rows)
    assert X.shape == (12, 2)
    assert set(X[:, 0].tolist()) == {0.0, 1.0}
    assert np.all(np.isnan(y))
    assert np.all(np.isnan(sd))
    # FN 0.5 ug/mL is coating 0, coded dose 0
    assert X[0].tolist() == pytest.approx([0.0, 0.0])
    # VTN 20 ug/mL is the last row: coating 1, coded dose 1
    assert X[-1].tolist() == pytest.approx([1.0, 1.0])


def test_us_fcs_is_not_a_row_in_the_condition_table():
    files = [r["file"] for r in load_conditions(COND)]
    assert "flow/2026-08-06/Exp_20260806_cd31-cd140a/us.fcs" not in files


def test_building_an_evaluator_from_the_committed_csv_raises_until_gated():
    from boec.lab import load_lab_evaluator
    from boec.space import SearchSpace
    import yaml
    space = SearchSpace.from_config(yaml.safe_load(CFG.read_text()))
    with pytest.raises(GatingIncompleteError, match="awaiting_gating"):
        load_lab_evaluator(COND, space)
```

Keep `test_building_an_evaluator...` skipped until Task 4 if `load_lab_evaluator` is not introduced yet. Prefer introducing the function in Task 3 as:

```python
def load_lab_evaluator(path, space):
    raise GatingIncompleteError("awaiting_gating")  # replaced in Task 4
```

so the test is red then green inside this task’s “raises until gated” contract.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lab.py::test_loader_reads_twelve_rows_with_nan_y_while_ungated tests/test_lab.py::test_us_fcs_is_not_a_row_in_the_condition_table tests/test_lab.py::test_building_an_evaluator_from_the_committed_csv_raises_until_gated -v`
Expected: FAIL `ModuleNotFoundError: No module named 'boec.lab'`

- [ ] **Step 3: Write `src/boec/lab.py`**

```python
"""In-house lab table for the 2026-08-06 FN/VTN OFAT.

This is not the Hall/Ogle cube. Rows with empty y are not evaluator input.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import yaml

from .evaluators import ContinuousLookupEvaluator
from .space import SearchSpace

COATING = {"fibronectin": 0.0, "vitronectin": 1.0}
DOSE_LOW = 0.5
DOSE_HIGH = 20.0


class GatingIncompleteError(ValueError):
    """Committed table still has awaiting_gating rows. Do not invent CD31%."""


def load_conditions(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _float_or_nan(s: str) -> float:
    s = (s or "").strip()
    return float("nan") if s == "" else float(s)


def conditions_to_arrays(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.empty((len(rows), 2), dtype=float)
    y = np.empty(len(rows), dtype=float)
    sd = np.empty(len(rows), dtype=float)
    for i, r in enumerate(rows):
        X[i, 0] = COATING[r["coating"]]
        dose = float(r["dose_ug_mL"])
        X[i, 1] = (dose - DOSE_LOW) / (DOSE_HIGH - DOSE_LOW)
        y[i] = _float_or_nan(r["y"])
        sd[i] = _float_or_nan(r["y_sd"])
    return X, y, sd


def load_lab_evaluator(path: Path, space: SearchSpace) -> ContinuousLookupEvaluator:
    rows = load_conditions(path)
    if any((r.get("status") == "awaiting_gating") or (r.get("y", "").strip() == "") for r in rows):
        raise GatingIncompleteError(
            f"{path} still has awaiting_gating rows; CD31% has not been gated. "
            "Fill y in bo_primary_conditions.csv. Do not invent percentages."
        )
    if space.metric.name != "CD31_pct_flow":
        raise ValueError(
            f"lab table metric is CD31_pct_flow; got {space.metric.name!r}. "
            "Do not mix with Hall/Ogle CD31_area_per_DAPI."
        )
    X, y, sd = conditions_to_arrays(rows)
    return ContinuousLookupEvaluator(
        X_table=X, y_table=y, sd_table=sd, metric=space.metric
    )
```

If `ContinuousLookupEvaluator` does not exist yet, import it only in `load_lab_evaluator` after Task 4, and in this task raise `GatingIncompleteError` before that import is needed (the raise happens first on the committed CSV). Split the import to the bottom of `load_lab_evaluator` after the ungated check so Task 3 tests pass without Task 4:

```python
    if any(...):
        raise GatingIncompleteError(...)
    from .evaluators import ContinuousLookupEvaluator  # Task 4
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lab.py -v`
Expected: PASS. `test_building_an_evaluator_from_the_committed_csv_raises_until_gated` raises `GatingIncompleteError`.

- [ ] **Step 5: Commit**

```bash
git add src/boec/lab.py tests/test_lab.py
git commit -m "$(cat <<'EOF'
Lab loader reads the 12-point table and refuses to evaluate until gating fills y.

EOF
)"
```

---

### Task 4: `ContinuousLookupEvaluator` (float match, not rint)

**Files:**
- Modify: `src/boec/evaluators.py`
- Modify: `src/boec/lab.py` (wire the class in `load_lab_evaluator`)
- Modify: `tests/test_lab.py`
- Test: `tests/test_lab.py`

**Interfaces:**
- Consumes: `X_table (n, d)`, `y_table (n,)`, `sd_table (n,)`, `metric`, `sd_floor=0.05` (same contract as `LookupEvaluator`)
- Produces: `evaluate(X) -> (Y, Yvar)` both `(n, 1)`; `candidates`; `KeyError` on a point not in the table; does **not** use `np.rint`

- [ ] **Step 1: Write the failing tests**

```python
from boec.evaluators import ContinuousLookupEvaluator, LookupEvaluator
from boec.space import MetricIdentity


def _metric():
    return MetricIdentity("CD31_pct_flow", "percent_of_parent", "novocyte-cd31-cd140a-2026-08-06")


def test_continuous_lookup_distinguishes_doses_that_rint_would_collide():
    """LookupEvaluator rints 0.025 and 0.05 both to 0. That is fatal for this OFAT."""
    X = np.array([[0.0, 0.0], [0.0, 0.02564102564102564], [0.0, 1.0]])
    y = np.array([10.0, 20.0, 30.0])
    sd = np.array([np.nan, np.nan, np.nan])
    ev = ContinuousLookupEvaluator(X, y, sd, _metric())
    Y, Yvar = ev.evaluate(np.array([[0.0, 0.02564102564102564]]))
    assert Y.shape == (1, 1) and Yvar.shape == (1, 1)
    assert Y[0, 0] == pytest.approx(20.0)
    assert Yvar[0, 0] == pytest.approx(0.05**2)


def test_phase2_lookup_evaluator_still_rints_and_is_untouched():
    X = np.array([[-1.0, 1.0], [1.0, -1.0]])
    y = np.array([1.0, 2.0])
    sd = np.array([0.1, 0.1])
    ev = LookupEvaluator(X, y, sd, _metric())
    Y, _ = ev.evaluate(np.array([[-1.0, 1.0]]))
    assert Y[0, 0] == pytest.approx(1.0)


def test_unknown_proposal_is_a_keyerror_not_an_interpolation():
    X = np.array([[0.0, 0.0], [1.0, 1.0]])
    ev = ContinuousLookupEvaluator(X, np.array([1.0, 2.0]), np.array([np.nan, np.nan]), _metric())
    with pytest.raises(KeyError, match="not in the lab table"):
        ev.evaluate(np.array([[0.0, 0.5]]))


def test_load_lab_evaluator_serves_filled_y_from_a_temp_csv(tmp_path):
    import yaml
    from boec.lab import load_lab_evaluator
    src = COND.read_text(encoding="utf-8")
    lines = src.splitlines()
    header, *body = lines
    filled = [header]
    for i, line in enumerate(body):
        parts = line.split(",")
        # y is field 8 (0-based 8) in the recoded header:
        # file,coating,dose_ug_mL,coded_dose,metric_name,metric_unit,metric_protocol_version,events,y,y_sd,n_replicates,batch_id,date,status
        parts[8] = str(10.0 + i)
        parts[13] = "gated"
        filled.append(",".join(parts))
    path = tmp_path / "filled.csv"
    path.write_text("\n".join(filled) + "\n", encoding="utf-8")
    space = SearchSpace.from_config(yaml.safe_load(CFG.read_text()))
    ev = load_lab_evaluator(path, space)
    assert ev.candidates.shape == (12, 2)
    Y, _ = ev.evaluate(ev.candidates[:1])
    assert Y[0, 0] == pytest.approx(10.0)


def test_wrong_metric_space_is_rejected(tmp_path):
    import yaml
    from boec.lab import load_lab_evaluator
    cfg = yaml.safe_load(CFG.read_text())
    cfg["metric"]["name"] = "CD31_area_per_DAPI"
    space = SearchSpace.from_config(cfg)
    # even a filled table must not mix metrics
    src = COND.read_text(encoding="utf-8").replace("awaiting_gating", "gated")
    # still empty y — loader should fail on gating first; force y
    rows = []
    for i, line in enumerate(src.splitlines()):
        if i == 0:
            rows.append(line)
            continue
        parts = line.split(",")
        parts[8] = "1.0"
        rows.append(",".join(parts))
    path = tmp_path / "mixed.csv"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CD31_pct_flow"):
        load_lab_evaluator(path, space)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lab.py::test_continuous_lookup_distinguishes_doses_that_rint_would_collide -v`
Expected: FAIL `ImportError` / `cannot import name ContinuousLookupEvaluator`

- [ ] **Step 3: Add the class to `src/boec/evaluators.py`**

Place immediately after `LookupEvaluator.evaluate`. Do not edit `LookupEvaluator`.

```python
@dataclass
class ContinuousLookupEvaluator(Evaluator):
    """Lab replay: discrete candidates with continuous coded levels.

    Phase 2's :class:`LookupEvaluator` indexes by ``np.rint`` because Hall/Ogle
    levels are -1/0/+1. Rint collides every OFAT dose below 0.5 ug/mL. Match
    here with ``np.allclose``. A miss is a KeyError, not the nearest neighbour.
    """

    X_table: np.ndarray
    y_table: np.ndarray
    sd_table: np.ndarray
    metric: MetricIdentity
    sd_floor: float = 0.05
    _n_eval: int = 0

    def __post_init__(self) -> None:
        self.X_table = np.asarray(self.X_table, dtype=float)
        self.y_table = np.asarray(self.y_table, dtype=float).ravel()
        self.sd_table = np.asarray(self.sd_table, dtype=float).ravel()
        if not (len(self.X_table) == len(self.y_table) == len(self.sd_table)):
            raise ValueError("table lengths disagree")
        if self.sd_floor <= 0:
            raise ValueError(f"sd_floor must be positive, got {self.sd_floor}")

    @property
    def n_evaluations(self) -> int:
        return self._n_eval

    @property
    def candidates(self) -> np.ndarray:
        ok = ~np.isnan(self.y_table)
        return self.X_table[ok]

    def _row(self, x: np.ndarray, who: str) -> int:
        hits = np.where(np.all(np.isclose(self.X_table, x, rtol=0.0, atol=1e-10), axis=1))[0]
        if len(hits) == 0:
            raise KeyError(
                f"{who}: condition {x.tolist()} is not in the lab table. "
                "A replay may only propose measured tubes; interpolating would "
                "claim a coating nobody ran."
            )
        i = int(hits[0])
        if np.isnan(self.y_table[i]):
            raise ValueError(f"{who}: condition {x.tolist()} is ungated")
        return i

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got shape {X.shape}")
        y = np.empty(len(X))
        sd = np.empty(len(X))
        for k, row in enumerate(X):
            i = self._row(row, "evaluate")
            y[k] = self.y_table[i]
            s = self.sd_table[i]
            sd[k] = self.sd_floor if np.isnan(s) else max(float(s), self.sd_floor)
        self._n_eval += len(X)
        return y.reshape(-1, 1), (sd**2).reshape(-1, 1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lab.py tests/test_published.py tests/test_published_dataset.py -v`
Expected: PASS. Phase 2 tests still pass because `LookupEvaluator` is unchanged.

- [ ] **Step 5: Commit**

```bash
git add src/boec/evaluators.py src/boec/lab.py tests/test_lab.py
git commit -m "$(cat <<'EOF'
Continuous lab lookup matches OFAT doses; rint lookup stays Hall/Ogle-only.

EOF
)"
```

---

### Task 5: Gating record — fill `y` by hand, never in code

**Files:**
- Create: `data/lab/GATE.md`
- Modify: `data/lab/BO-PURPOSE.md` (point at GATE.md and this plan)
- Test: `tests/test_lab.py` (already asserts committed CSV `y` is empty)

**Interfaces:**
- Consumes: 12 primary FCS + `us.fcs` + 2026-07-28 CD31±/ISO panel
- Produces: a filled `y` column in `bo_primary_conditions.csv` **only after a human gates**. This task does not write percentages.

- [ ] **Step 1: Write `data/lab/GATE.md`**

```markdown
# Gating record — 2026-08-06 CD31 / CD140a

**Status: not gated.** `bo_primary_conditions.csv` `y` is empty on purpose.
`boec.lab.load_lab_evaluator` raises `GatingIncompleteError` until this file
records a gate and the CSV is filled.

## Files

- Conditions: `flow/2026-08-06/Exp_20260806_cd31-cd140a/f*.fcs`, `v*.fcs` (12 tubes)
- Same-day unstained: `flow/2026-08-06/Exp_20260806_cd31-cd140a/us.fcs`
- CD31± / ISO: `flow/2026-07-28/Exp_20260728_1/`

## Channels (from FCS TEXT + ExpSummaryForAPI.xml)

NovoCyte, 38 parameters. Stats were requested on **B525-A** and **Y585-A**.
Which fluorochrome is CD31 and which is CD140a is **not** in the filenames.
Record it here before anyone fills `y`:

- CD31 → channel: _ungated_
- CD140a → channel: _ungated_
- Live/FSC-SSC gate: _ungated_
- Singlet gate: _ungated_

## Metric

One campaign, one number:

- `metric_name`: CD31_pct_flow
- `metric_unit`: percent_of_parent
- `metric_protocol_version`: novocyte-cd31-cd140a-2026-08-06

CD140a% is a second metric. If scored, it is a second CSV / second campaign.

## How to fill the table

1. Gate the 12 tubes against `us.fcs` with the geometry recorded above.
2. Write CD31⁺ % of parent into `bo_primary_conditions.csv` column `y`.
3. Leave `y_sd` empty (n = 1). The evaluator imputes `sd_floor = 0.05`.
4. Set `status` to `gated`.
5. Re-run `python -m pytest tests/test_lab.py -v`.
   `test_conditions_table_is_the_twelve_primaries_still_awaiting_gating` must
   be updated in the same commit that fills `y` — do not leave a test that
   demands emptiness after gating.

Do not commit a software-invented CD31% from an unstained threshold.
```

- [ ] **Step 2: Point BO-PURPOSE at the plan and GATE.md**

At the top of `data/lab/BO-PURPOSE.md`, after the first paragraph, add:

```markdown
Implementation plan: `docs/superpowers/plans/2026-08-13-lab-data-bo-lookup.md`.
Gating record: `GATE.md`. The optimizer cannot `tell()` until `y` is filled.
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_lab.py -v`
Expected: PASS. Committed CSV still `awaiting_gating`.

- [ ] **Step 4: Commit**

```bash
git add data/lab/GATE.md data/lab/BO-PURPOSE.md
git commit -m "$(cat <<'EOF'
Gating record: CD31% is a lab fill, not a software guess.

EOF
)"
```

---

## Spec coverage

| Spec item (`BO-PURPOSE.md`) | Task |
|---|---|
| 12 FN/VTN FCS are the only primaries | Task 1 |
| `us.fcs` is gating, not a condition | Task 1, 3 |
| Separate box from Hall/Ogle 6-D cube | Task 2, 4 (wrong-metric reject) |
| Coded dose on `[0.5, 20]` | Task 2 |
| `y` empty until gated | Task 3, 5 |
| n = 1, impute `Yvar` | Task 4 `sd_floor` |
| Do not rint-collide OFAT doses | Task 4 |
| Exp_2 / media screen / protocol wells out | Task 1 roles; no loader path |
| Do not invent CD31% in code | Task 5 |

## Placeholder scan

No TBD. Gating percentages are explicitly *not* produced by this plan; the failure mode is `GatingIncompleteError`, which is implemented and tested.

## Type consistency

- `GatingIncompleteError` raised in `load_lab_evaluator`, asserted in Task 3 and 4 tests.
- `ContinuousLookupEvaluator.evaluate` → `(n, 1), (n, 1)`.
- Metric fields: `name`, `unit`, `protocol_version` match `MetricIdentity` (`src/boec/space.py`).
- CSV column after Task 2 is `coded_dose`, not `coded_dose_0_to_20`. Task 4’s temp-CSV splitter uses 0-based field 8 for `y` and 13 for `status` against header `file,coating,dose_ug_mL,coded_dose,metric_name,metric_unit,metric_protocol_version,events,y,y_sd,n_replicates,batch_id,date,status`.
