"""Fail-closed runner for the frozen variance-corrected DC2 protocol."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import run_dc_doe_certificate as dc

SPEC = ROOT / "docs" / "SPADE-DOE-CERTIFICATE-CORRECTION-SPEC.md"


@dataclass(frozen=True)
class DC2Protocol:
    families: tuple[str, ...] = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
    seed_start: int = 32
    seed_stop: int = 64
    arms: tuple[tuple[str, int], ...] = (
        ("doe", 3),
        ("doe_unscreened", 3),
        ("spade", 5),
    )
    p_grid: tuple[float, ...] = (0.70, 0.30)
    c_grid: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)

    @property
    def expected_jobs(self) -> int:
        return len(self.families) * (self.seed_stop - self.seed_start)

    @property
    def cells_per_job(self) -> int:
        return len(self.arms) * len(self.p_grid) * len(self.c_grid)

    @property
    def expected_rows(self) -> int:
        return self.expected_jobs * self.cells_per_job

    @property
    def arm_names(self) -> tuple[str, ...]:
        return tuple(arm for arm, _rounds in self.arms)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def new_artifact(protocol: DC2Protocol, *, source_commit: str, source_dirty: bool,
                 spec_sha256: str, runner_sha256: str) -> dict:
    return {
        "status": "PARTIAL",
        "source_commit": source_commit,
        "source_dirty": bool(source_dirty),
        "seed_start": protocol.seed_start,
        "seed_stop": protocol.seed_stop,
        "families": list(protocol.families),
        "arms": [[arm, rounds] for arm, rounds in protocol.arms],
        "p_grid": list(protocol.p_grid),
        "c_grid": list(protocol.c_grid),
        "expected_jobs": protocol.expected_jobs,
        "expected_rows": protocol.expected_rows,
        "spec_sha256": spec_sha256,
        "runner_sha256": runner_sha256,
        "completed_jobs": [],
        "rows": [],
    }


def _cell_key(row: dict) -> tuple[str, int, str, float, float]:
    return (
        str(row["family"]),
        int(row["seed"]),
        str(row["arm"]),
        float(row["p_value"]),
        float(row["inflation_c"]),
    )


def _json_finite(value):
    """Replace non-finite numeric leaves with JSON null before persistence."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_finite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_finite(item) for item in value]
    return value


def _expected_cells(protocol: DC2Protocol) -> set[tuple[str, int, str, float, float]]:
    return {
        (family, seed, arm, float(p_value), float(inflation_c))
        for family in protocol.families
        for seed in range(protocol.seed_start, protocol.seed_stop)
        for arm, _rounds in protocol.arms
        for p_value in protocol.p_grid
        for inflation_c in protocol.c_grid
    }


def complete_job_keys(rows: list[dict], protocol: DC2Protocol) -> set[tuple[str, int]]:
    expected_per_job = {
        (arm, float(p_value), float(inflation_c))
        for arm, _rounds in protocol.arms
        for p_value in protocol.p_grid
        for inflation_c in protocol.c_grid
    }
    cells: dict[tuple[str, int], set[tuple[str, float, float]]] = {}
    for row in rows:
        family, seed, arm, p_value, inflation_c = _cell_key(row)
        cells.setdefault((family, seed), set()).add((arm, p_value, inflation_c))
    return {job for job, observed in cells.items() if observed == expected_per_job}


def validate_artifact(payload: dict, protocol: DC2Protocol, *, require_complete: bool,
                      expected_spec_sha256: str | None = None,
                      expected_runner_sha256: str | None = None) -> None:
    expected_metadata = {
        "seed_start": protocol.seed_start,
        "seed_stop": protocol.seed_stop,
        "families": list(protocol.families),
        "arms": [[arm, rounds] for arm, rounds in protocol.arms],
        "p_grid": list(protocol.p_grid),
        "c_grid": list(protocol.c_grid),
        "expected_jobs": protocol.expected_jobs,
        "expected_rows": protocol.expected_rows,
    }
    for key, expected in expected_metadata.items():
        if payload.get(key) != expected:
            raise ValueError(f"{key} mismatch: expected {expected!r}, got {payload.get(key)!r}")
    if payload.get("source_dirty") is not False:
        raise ValueError("source_dirty must be false")
    if expected_spec_sha256 is not None and payload.get("spec_sha256") != expected_spec_sha256:
        raise ValueError("spec_sha256 mismatch")
    if (expected_runner_sha256 is not None
            and payload.get("runner_sha256") != expected_runner_sha256):
        raise ValueError("runner_sha256 mismatch")
    if require_complete and payload.get("status") != "COMPLETE":
        raise ValueError("artifact status must be COMPLETE")
    if payload.get("status") not in {"PARTIAL", "COMPLETE"}:
        raise ValueError(f"invalid status: {payload.get('status')!r}")

    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    seen: set[tuple[str, int, str, float, float]] = set()
    for row in rows:
        key = _cell_key(row)
        if key in seen:
            raise ValueError(f"duplicate DC2 cell: {key}")
        seen.add(key)
        for field in ("regret", "p_value", "inflation_c"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"non-finite {field} in {key}")
        for field, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"non-finite {field} in {key}")
    expected_cells = _expected_cells(protocol)
    extra = seen - expected_cells
    if extra:
        raise ValueError(f"unexpected DC2 cells: {sorted(extra)[:3]}")
    if require_complete:
        missing = expected_cells - seen
        if missing:
            raise ValueError(f"missing DC2 grid cells: {sorted(missing)[:3]}")
        if len(rows) != protocol.expected_rows:
            raise ValueError(
                f"row count mismatch: expected {protocol.expected_rows}, got {len(rows)}"
            )
    completed = complete_job_keys(rows, protocol)
    declared = {tuple(item) for item in payload.get("completed_jobs", [])}
    if declared != completed:
        raise ValueError(
            f"completed_jobs mismatch: declared {sorted(declared)}, derived {sorted(completed)}"
        )
    if require_complete and len(completed) != protocol.expected_jobs:
        raise ValueError("complete artifact does not contain every expected job")


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _run_job(protocol: DC2Protocol, family: str, seed: int, *, grid, X_sub,
             tau_cache: dict) -> list[dict]:
    from boec.designspace import tau_quantile
    from boec.replay import scored_curve, unit_bounds
    from boec.surrogate import build_gp

    legacy = dc.lc()
    registered = legacy.kv().p8()
    p2 = registered.p2()
    instance = legacy.instance_for(family, seed)
    if instance not in tau_cache:
        with torch.no_grad():
            truth_grid = registered.evaluator_for(family, instance, 0).truth(grid)
        tau_cache[instance] = {
            p_value: float(tau_quantile(truth_grid.reshape(-1).double(), p_value))
            for p_value in protocol.p_grid
        }

    job_rows: list[dict] = []
    for arm, rounds in protocol.arms:
        (X, Y, Yvar), oracle = dc.build(family, arm, seed, rounds)
        with torch.no_grad():
            truth = oracle.truth(X_sub).reshape(-1).double()
        regret = float(1.0 - scored_curve(oracle, X, Y)[-1])
        model = build_gp(X, Y, Yvar, unit_bounds(registered.DIM))
        with torch.no_grad():
            posterior = model.posterior(X_sub)
            mean = posterior.mean.reshape(-1, 1).double()
            covariance = posterior.mvn.covariance_matrix.double()
            covariance += 1e-8 * torch.eye(covariance.shape[0], dtype=torch.double)
            factor = torch.linalg.cholesky(covariance)
            draws_z = torch.randn(
                covariance.shape[0],
                registered.N_DRAWS,
                generator=torch.Generator().manual_seed(seed),
                dtype=torch.double,
            )
            for inflation_c in protocol.c_grid:
                draws = (mean + inflation_c * factor @ draws_z).T
                for p_value in protocol.p_grid:
                    job_rows.append(_json_finite({
                        "family": family,
                        "seed": seed,
                        "arm": arm,
                        "rounds": rounds,
                        "regret": regret,
                        "p_value": p_value,
                        "inflation_c": inflation_c,
                        "n_wells": int(X.shape[0]),
                        **p2.vorobev_columns(
                            draws,
                            truth,
                            tau_cache[instance][p_value],
                            p2.ALPHAS,
                        ),
                    }))
        del model
        gc.collect()
    if len(job_rows) != protocol.cells_per_job:
        raise RuntimeError(
            f"{family} seed {seed}: expected {protocol.cells_per_job} rows, "
            f"produced {len(job_rows)}"
        )
    return job_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=32)
    parser.add_argument("--seed-stop", type=int, default=64)
    parser.add_argument("--families", default="ackley,hartmann6,hill,levy,rosenbrock")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "dc2-sweep.json")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    protocol = DC2Protocol(
        families=tuple(part.strip() for part in args.families.split(",") if part.strip()),
        seed_start=args.seed_start,
        seed_stop=args.seed_stop,
    )
    source_commit = _git("rev-parse", "HEAD")
    source_dirty = bool(_git("status", "--porcelain"))
    if source_dirty:
        raise RuntimeError("DC2 refuses a dirty source tree")
    spec_sha256 = _sha256(SPEC)
    runner_sha256 = _sha256(Path(__file__))

    if args.resume:
        payload = json.loads(args.out.read_text())
        validate_artifact(
            payload,
            protocol,
            require_complete=False,
            expected_spec_sha256=spec_sha256,
            expected_runner_sha256=runner_sha256,
        )
        if payload.get("source_commit") != source_commit:
            raise ValueError("resume source_commit mismatch")
    else:
        if args.out.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {args.out}")
        payload = new_artifact(
            protocol,
            source_commit=source_commit,
            source_dirty=False,
            spec_sha256=spec_sha256,
            runner_sha256=runner_sha256,
        )
        atomic_write(args.out, payload)

    from boec.norms import sobol_grid

    legacy = dc.lc()
    registered = legacy.kv().p8()
    p2 = registered.p2()
    grid = sobol_grid(registered.DIM, p2.GRID_N, seed=p2.GRID_SEED)
    X_sub = sobol_grid(registered.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
    tau_cache: dict = {}
    completed = complete_job_keys(payload["rows"], protocol)
    started = time.time()

    for family in protocol.families:
        for seed in range(protocol.seed_start, protocol.seed_stop):
            if (family, seed) in completed:
                continue
            job_rows = _run_job(
                protocol,
                family,
                seed,
                grid=grid,
                X_sub=X_sub,
                tau_cache=tau_cache,
            )
            payload["rows"].extend(job_rows)
            completed.add((family, seed))
            payload["completed_jobs"] = [list(job) for job in sorted(completed)]
            validate_artifact(
                payload,
                protocol,
                require_complete=False,
                expected_spec_sha256=spec_sha256,
                expected_runner_sha256=runner_sha256,
            )
            atomic_write(args.out, payload)
            elapsed = (time.time() - started) / 60
            print(
                f"[{len(completed)}/{protocol.expected_jobs}] {family} seed={seed} "
                f"rows={len(payload['rows'])} elapsed={elapsed:.1f}m",
                flush=True,
            )

    payload["status"] = "COMPLETE"
    validate_artifact(
        payload,
        protocol,
        require_complete=True,
        expected_spec_sha256=spec_sha256,
        expected_runner_sha256=runner_sha256,
    )
    atomic_write(args.out, payload)
    print(f"WROTE COMPLETE {args.out} rows={len(payload['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
