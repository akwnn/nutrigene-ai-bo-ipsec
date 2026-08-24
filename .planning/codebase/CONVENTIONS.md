# Coding Conventions

**Analysis Date:** 2026-08-24

## Naming Patterns

**Files:**
- Use lowercase `snake_case.py` for importable modules, for example `src/boec/final_spade.py`, `src/boec/sequential_rsm.py`, and `src/boec/designspace.py`.
- Use `test_<subject>.py` for tests, normally mirroring a module or research workstream: `tests/test_final_spade_statistics.py`, `tests/test_lab_dataset.py`, and `tests/test_q50_paired.py`.
- Use action-prefixed `snake_case.py` for one-off and reproducibility scripts: `scripts/run_*`, `scripts/analyse_*`, `scripts/make_*`, `scripts/preflight_*`, and `scripts/validate_*`.
- Use uppercase kebab-case Markdown names for curated research documents, such as `docs/MAIN-LINE.md`, `docs/RESEARCH-SUMMARY.md`, and `docs/SPADE-FINAL-SPEC.md`. Treat the naming suffixes `EXPLORATORY` and `SUPERSEDED` as evidence-state labels, as in `results/EXPLORATORY-disagreement.md` and `results/e7-search-vs-id-rule-p.SUPERSEDED-no-spade.json`.

**Functions:**
- Use `snake_case` and names that state the scientific operation or invariant: `classify_regime` in `src/boec/final_spade.py`, `set_single_threaded` in `src/boec/runner.py`, and test names such as `test_a_primary_condition_missing_a_mandatory_arm_refuses_a_primary_conclusion` in `tests/test_final_spade_statistics.py`.
- Prefix private helpers with `_`; keep the public surface explicit through `__all__` in modules such as `src/boec/final_spade.py` and `src/boec/runner.py`.
- Name failure paths as refusals rather than silent fallbacks. Functions and tests consistently use language such as `raises`, `refuses`, `missing`, `unavailable`, and `incomplete`.

**Variables:**
- Use short mathematical names only where they match the research notation (`X1`, `tau`, `gamma`, `sigma_rel`, `ls`); otherwise use descriptive `snake_case` such as `nonempty_rate`, `boundary_frac`, and `missing_mandatory_arms` in `src/boec/final_spade.py`.
- Use uppercase constants for frozen protocol values and enumerations: `LOCAL_RADIUS`, `TARGET_PREVALENCE`, and `MIN_NONEMPTY_RATE` in `src/boec/final_spade.py`; `STATIC_METHODS`, `UNWIRED_METHODS`, and `PAIRING_EXEMPT` in `src/boec/runner.py`.
- Preserve the project’s unit-bearing suffixes (`sigma_rel`, `_rate`, `_frac`, `_pp`, `_var`) rather than using unitless generic names.

**Types:**
- Use `PascalCase` for dataclasses and protocol objects (`GridCell`, `Runner`, `Release`, `Violation`, `Check`).
- Add Python type annotations to public and research-critical functions, using built-in generics and PEP 604 unions (`dict`, `list[str]`, `str | None`, `tuple[Tensor, dict]`). Examples are in `src/boec/final_spade.py` and `scripts/validate_final_spade_release.py`.
- Use frozen dataclasses for immutable configuration or audit records (`GridCell` in `src/boec/runner.py`, `Violation` and `Check` in `scripts/validate_final_spade_release.py`).

## Code Style

**Formatting:**
- No automated formatter is configured in `pyproject.toml`; match the existing PEP 8-like, four-space style manually.
- Keep imports at the top, normally preceded by `from __future__ import annotations` in maintained modules such as `src/boec/final_spade.py` and `src/boec/runner.py`.
- Existing research-heavy modules permit long explanatory module docstrings and comments. Preserve that style where a statistical or protocol decision would otherwise be opaque.
- Keep tensors and numerical calculations explicit about precision. Core code repeatedly normalizes inputs with `torch.as_tensor(..., dtype=torch.double)`, for example in `src/boec/final_spade.py`.

**Linting:**
- No Ruff, Flake8, Black, mypy, pre-commit, or equivalent configuration is detected in `pyproject.toml` or the repository root.
- Do not assume static lint or type enforcement. Validate changes with the relevant pytest module and, for release-facing work, `scripts/validate_final_spade_release.py`.

## Import Organization

**Order:**
1. `from __future__ import annotations`.
2. Python standard library imports (`json`, `os`, `pathlib`, `dataclasses`, collections interfaces).
3. Third-party packages (`numpy`, `pandas`, `torch`, `scipy`, `pytest`).
4. Absolute package imports from `boec`, as in `src/boec/runner.py`.

**Path Aliases:**
- No path alias is used. Import package code as `boec.<module>` after `pip install -e .`; `pyproject.toml` exposes packages from `src/`.
- Pytest alone adds `src` through `[tool.pytest.ini_options].pythonpath`. Do not rely on that behavior for scripts; `pyproject.toml` documents that the editable install is required for `python scripts/run_*.py`.
- Scripts that import sibling scripts may insert `scripts/` or the repository root into `sys.path`; follow the nearest existing script only when an importable `src/boec/` module is not appropriate.

## Error Handling

**Patterns:**
- Fail loudly on schema, dimension, missing-data, and invalid-state errors. Use `ValueError`, `KeyError`, or a domain-specific exception with a diagnostic containing the offending value; `local_wells` in `src/boec/final_spade.py` rejects shape and lengthscale mismatches rather than broadcasting.
- Represent scientifically undefined quantities as `None`/`NaN` with an accompanying status, not as a flattering zero. This behavior is enforced across `tests/test_calibration.py`, `tests/test_designspace.py`, and `tests/test_vorobev.py`.
- Treat missing mandatory comparators, mixed estimands, invalid pooling, incomplete shards, and overwrites as hard errors. The canonical examples are `tests/test_final_spade_statistics.py` and `tests/test_final_spade_protocol.py`.
- Record intentionally unavailable methods explicitly. `UNWIRED_METHODS` in `src/boec/runner.py` prevents a `doe` label from silently running the adaptive BO branch.
- Collect all release violations before exiting rather than stopping at the first; follow `scripts/validate_final_spade_release.py` for publication gates.

## Logging

**Framework:** `print`/stdout plus structured JSON artefacts; no logging framework is configured.

**Patterns:**
- Write long-running run output to named `.log` files under `results/`, and write machine-checkable records to `.json`. A result cited by the paper should have a committed artefact and a producing script.
- Store provenance with results: command arguments, configuration, seed, library versions, timestamp, and git SHA where the runner supports it. `src/boec/runner.py`, `results/e2-grid.json`, and `results/q52-budget-to-target.json` establish this pattern.
- Use temporary/partial paths during long runs, validate completeness, then promote. Tests such as `tests/test_versionc_gate.py` and `tests/test_final_spade_reproducibility.py` enforce that partial output is not written to the registered final path.
- Print explicit status and reasons (`PASS`, `FAIL`, `NOT_RUN`, `INCONCLUSIVE`, `unavailable_reason`) so absence cannot be mistaken for success.

## Comments

**When to Comment:**
- Explain why a constraint exists, the historical failure it prevents, and the governing spec section. This is a core repository convention, visible in `src/boec/final_spade.py`, `src/boec/runner.py`, and `scripts/validate_final_spade_release.py`.
- State which constants are frozen and where they were registered. Do not introduce a tunable value without identifying whether it is registered, inherited, or a sensitivity parameter.
- Mark circular, oracle-leaking, structurally impossible, exploratory, or superseded analysis explicitly at the point of use.
- Avoid comments that only restate syntax; comments should carry scientific intent, provenance, unit, or failure-mode information.

**JSDoc/TSDoc:**
- Not applicable. Use Python module, class, and function docstrings.
- Public and research-critical functions should document inputs, outputs, units/shape, statistical meaning, registered source, and raised errors. `local_wells` in `src/boec/final_spade.py` is the strongest model.

## Function Design

**Size:** Prefer small computational functions with independently testable invariants. Larger orchestration and analysis scripts are accepted when they retain named checks and helper functions, as in `scripts/validate_final_spade_release.py`.

**Parameters:**
- Pass seeds and scientific choices explicitly; do not depend on ambient global RNG state.
- Use keyword-only parameters for choices whose meaning could be confused positionally, such as `radius` in `src/boec/final_spade.py`.
- Keep oracle/truth access out of decision-rule signatures. `local_wells` in `src/boec/final_spade.py` accepts arrays rather than a model or oracle specifically to make leakage structurally harder.

**Return Values:**
- Return the scientific result together with diagnostics needed to audit it. For example, `local_wells` returns points plus `n_in_ball`, requested/placed counts, radius, and shortfall status.
- Preserve row schemas and explicit status fields in result dictionaries; avoid returning a bare scalar for an inferential result.

## Module Design

**Exports:** Use explicit `__all__` in core modules with a stable public surface (`src/boec/final_spade.py`, `src/boec/runner.py`). Keep experiment-specific orchestration in `scripts/`; move reusable scientific calculations into `src/boec/`.

**Barrel Files:** `src/boec/__init__.py` is minimal; barrel-style re-exporting is not a repository pattern. Import from the defining module.

---

*Convention analysis: 2026-08-24*
