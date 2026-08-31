"""Fail-closed, resumable runner for the prospective synthetic EC benchmark.

Campaign decisions see only scalarized joint-CQA observations. The six-factor,
three-CQA oracle is consulted only after a campaign finishes, when the selected
point and a locked Sobol grid are scored. ``--dry-run`` runs one reduced-settings
campaign per arm and is explicitly TEST_ONLY, never prospective evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from boec.doe import run_doe_arm, run_doe_unscreened_arm
from boec.ec_calibration import ECTrainingCandidate, boundary_candidates, per_cqa_lower_utility
from boec.ec_benchmark import ECConfig, joint_success, make_ec_landscape, registered_ec_families
from boec.optimizers import AcqConfig, propose, sobol_design
from boec.seedbook import derive_seed
from boec.surrogate import build_gp, build_learned_noise_gp

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "SPADE-EC-BENCHMARK.md"
ARMS = ("spade", "doe", "doe_unscreened", "qlognei")
TRAIN_SEEDS = tuple(range(64))
EVAL_SEEDS = tuple(range(64, 96))
FAMILIES = registered_ec_families()
WELLS = 48
# BO is an opening plus two adaptive batches. Screened DoE has three stages;
# full-dimensional CCD has a design and confirmation stage.
ROUNDS = {"spade": 5, "doe": 3, "doe_unscreened": 2, "qlognei": 5}
REQUIRED_COLUMNS = {
    "family", "seed", "arm", "answer_rate", "containment", "containment_wilson_lower",
    "false_certificate_count", "joint_volume", "point_regret", "adaptive_rounds",
    "training_seed_start", "training_seed_stop", "evaluation_seed_start", "evaluation_seed_stop",
    "spec_sha256", "runner_sha256", "source_commit",
}
_BO_OPENING, _BO_BATCH, _BO_GRID = 32, 8, 2_048
# A calibration report chooses this object from training seeds only.  It is
# threaded explicitly so the prospective runner never inspects an evaluation
# result to alter surrogate uncertainty or the candidate menu.
EC_TRAINING_DEFAULT = ECTrainingCandidate((1.5, 1.5, 1.5), candidate_density=4_096)
_BOUNDARY_RECIPES = {"ec_narrow": 2, "ec_multimodal": 2}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    if trials <= 0:
        return 0.0
    p = successes / trials
    den = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    half = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5)
    return (centre - half) / den


def expected_cells(*, seeds: tuple[int, ...] = EVAL_SEEDS, families: tuple[str, ...] = FAMILIES):
    return {(family, seed, arm) for family in families for seed in seeds for arm in ARMS}


def _provenance() -> dict[str, Any]:
    return {
        "training_seed_start": TRAIN_SEEDS[0], "training_seed_stop": TRAIN_SEEDS[-1] + 1,
        "evaluation_seed_start": EVAL_SEEDS[0], "evaluation_seed_stop": EVAL_SEEDS[-1] + 1,
        "spec_sha256": sha256(SPEC), "runner_sha256": sha256(Path(__file__)),
        "source_commit": source_commit(),
    }


@dataclass(frozen=True)
class _Campaign:
    X: torch.Tensor
    Y: torch.Tensor
    rounds: int


class _JointCQAEvaluator:
    """Adapt three CQA outcomes to the scalar SPADE evaluator contract.

    The minimum threshold-normalized endpoint reaches one exactly when every
    CQA reaches its registered threshold, so averaging cannot sacrifice a CQA.
    """

    def __init__(self, family: str, seed: int) -> None:
        self.landscape = make_ec_landscape(family, seed, ECConfig())
        self.thresholds = torch.tensor(self.landscape.config.cqa_thresholds, dtype=torch.double)

    def utility(self, Y: torch.Tensor) -> torch.Tensor:
        return (Y.double() / self.thresholds.to(Y)).amin(dim=1, keepdim=True)

    def evaluate(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        Y, Yvar = self.landscape.evaluate(X)
        return self.utility(Y), (Yvar.double() / self.thresholds.square().to(Yvar)).amax(dim=1, keepdim=True)

    def evaluate_cqas(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return all observed CQAs; SPADE's surrogate must not scalarize them."""
        return self.landscape.evaluate(X)

    def truth(self, X: torch.Tensor) -> torch.Tensor:
        return self.utility(self.landscape.truth(X))


def _remove_rows(menu: torch.Tensor, rows: torch.Tensor) -> torch.Tensor:
    keep = torch.ones(menu.shape[0], dtype=torch.bool)
    for row in rows:
        keep &= ~torch.all(menu == row.to(menu), dim=1)
    return menu[keep]


def _bounds() -> torch.Tensor:
    return torch.stack([torch.zeros(6, dtype=torch.double), torch.ones(6, dtype=torch.double)])


def _per_cqa_batch(models, menu: torch.Tensor, adapter: _JointCQAEvaluator,
                   calibration: ECTrainingCandidate, q: int) -> torch.Tensor:
    scores = per_cqa_lower_utility(
        models, menu, thresholds=tuple(adapter.thresholds.tolist()),
        inflation_by_cqa=calibration.inflation_by_cqa,
    ).flatten()
    order = torch.argsort(scores, descending=True, stable=True)
    return menu[order[:q]].clone()


def _run_bo_arm(adapter: _JointCQAEvaluator, *, seed: int, arm: str, test_only: bool,
                calibration: ECTrainingCandidate = EC_TRAINING_DEFAULT) -> _Campaign:
    """Run the registered 32 + 8 + 8 schedule with repository SPADE APIs."""
    if arm not in {"spade", "qlognei"}:
        raise ValueError(f"not a BO arm: {arm}")
    bounds = _bounds()
    root = derive_seed(seed, "ec-campaign", arm)
    X = sobol_design(bounds, _BO_OPENING, seed=derive_seed(root, "opening"))
    Y, _ = adapter.evaluate(X)
    cqa_Y, cqa_Yvar = adapter.evaluate_cqas(X)
    menu_size = min(calibration.candidate_density, 128) if test_only else calibration.candidate_density
    reference_size = 64 if test_only else _BO_GRID
    fit_restarts, mc_samples = (1, 16) if test_only else (4, 256)
    menu = _remove_rows(sobol_design(bounds, menu_size, seed=derive_seed(root, "candidate-menu")), X)
    reference = sobol_design(bounds, reference_size, seed=derive_seed(root, "ivr-reference"))
    for batch_index in range(2):
        if arm == "spade":
            models = tuple(
                build_gp(X, cqa_Y[:, index:index + 1], cqa_Yvar[:, index:index + 1], bounds,
                         fit_restarts=fit_restarts)
                for index in range(cqa_Y.shape[1])
            )
            n_boundary = _BOUNDARY_RECIPES.get(adapter.landscape.family, 0)
            adaptive = _per_cqa_batch(models, menu, adapter, calibration, _BO_BATCH - n_boundary)
            boundary = boundary_candidates(
                bounds, n=n_boundary, seed=derive_seed(root, "boundary", batch_index)
            ) if n_boundary else menu[:0]
            selected = torch.cat((adaptive, boundary), dim=0)
            selected = _remove_rows(selected, X)
            if selected.shape[0] != _BO_BATCH:
                raise RuntimeError("EC boundary exploration duplicated an observed recipe")
        else:
            model = build_learned_noise_gp(
                X, Y, bounds, fit_restarts=fit_restarts,
                seed=derive_seed(root, "gp-fit", X.shape[0]),
            )
            selected = propose(
                model, bounds, _BO_BATCH, X, Y,
                config=AcqConfig(kind="qlognei", mc_samples=mc_samples,
                                 sampler_seed=derive_seed(root, "qmc", X.shape[0])),
                candidates=menu,
            ).detach().double()
        menu = _remove_rows(menu, selected)
        next_y, _ = adapter.evaluate(selected)
        next_cqa_y, next_cqa_yvar = adapter.evaluate_cqas(selected)
        X, Y = torch.cat([X, selected]), torch.cat([Y, next_y])
        cqa_Y, cqa_Yvar = torch.cat([cqa_Y, next_cqa_y]), torch.cat([cqa_Yvar, next_cqa_yvar])
    if X.shape != (WELLS, 6) or torch.unique(X, dim=0).shape[0] != WELLS:
        raise RuntimeError("EC BO campaign did not preserve the exact unique 48-well budget")
    return _Campaign(X=X, Y=Y, rounds=ROUNDS[arm])


def _run_arm(family: str, seed: int, arm: str, *, test_only: bool,
             calibration: ECTrainingCandidate = EC_TRAINING_DEFAULT) -> _Campaign:
    adapter = _JointCQAEvaluator(family, seed)
    if arm in {"spade", "qlognei"}:
        return _run_bo_arm(adapter, seed=seed, arm=arm, test_only=test_only, calibration=calibration)
    campaign_seed = derive_seed(seed, "ec-campaign", arm)
    if arm == "doe":
        result = run_doe_arm(adapter, _bounds(), truth=adapter.truth, budget=WELLS, seed=campaign_seed)
    elif arm == "doe_unscreened":
        result = run_doe_unscreened_arm(adapter, _bounds(), truth=adapter.truth, budget=WELLS, seed=campaign_seed)
    else:
        raise ValueError(f"unknown EC arm: {arm}")
    # Classical CCDs deliberately include centre replicates; matched *budget*,
    # not uniqueness, is the fairness condition for those comparator arms.
    if result.X_visited.shape != (WELLS, 6):
        raise RuntimeError(f"{arm} did not preserve the exact 48-well budget")
    return _Campaign(X=result.X_visited.double(), Y=result.Y_visited.double(), rounds=ROUNDS[arm])


def _campaign_row(family: str, seed: int, arm: str, *, test_only: bool) -> dict[str, Any]:
    campaign = _run_arm(family, seed, arm, test_only=test_only)
    # All experimental choices are finished before the truth-only scoring boundary.
    selected = int(torch.argmax(campaign.Y.reshape(-1)))
    adapter = _JointCQAEvaluator(family, seed)
    selected_truth = adapter.landscape.truth(campaign.X[selected:selected + 1])
    answered = bool(float(campaign.Y[selected]) >= 1.0)
    contained = bool(joint_success(selected_truth, adapter.thresholds)[0])
    grid = sobol_design(_bounds(), 256 if test_only else _BO_GRID,
                        seed=derive_seed(seed, "ec-score-grid", family))
    grid_truth = adapter.landscape.truth(grid)
    grid_utility = adapter.utility(grid_truth)
    regret = max(0.0, float(grid_utility.max() - adapter.truth(campaign.X[selected:selected + 1]).max()))
    return {
        "family": family, "seed": seed, "arm": arm,
        "answer_rate": 1.0 if answered else 0.0,
        "containment": 1.0 if answered and contained else 0.0,
        "contained": answered and contained,
        "containment_wilson_lower": _wilson_lower(int(answered and contained), int(answered)),
        "false_certificate_count": int(answered and not contained),
        "joint_volume": float(joint_success(grid_truth, adapter.thresholds).double().mean()),
        "point_regret": regret,
        "adaptive_rounds": campaign.rounds,
        "budget": WELLS,
        "execution_mode": "TEST_ONLY" if test_only else "REGISTERED",
        "endpoint": "min_threshold_normalized_cqa",
        **_provenance(),
    }


def _mock_row(family: str, seed: int, arm: str) -> dict[str, Any]:
    """Compatibility fixture for validator tests; never used by registered runs."""
    return _campaign_row(family, seed, arm, test_only=True)


def atomic_write(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(artifact, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def empty_artifact() -> dict[str, Any]:
    return {"status": "PARTIAL", "config": {"wells": WELLS, "spade_rounds": 5, "doe_rounds": 3},
            **_provenance(), "rows": []}


def run(*, out: Path, resume: bool = False, dry_run: bool = False) -> dict[str, Any]:
    artifact = empty_artifact()
    if resume and out.exists():
        artifact = json.loads(out.read_text(encoding="utf-8"))
        for key, value in _provenance().items():
            if artifact.get(key) != value:
                raise ValueError(f"cannot resume: provenance mismatch for {key}")
    rows = list(artifact.get("rows", []))
    seen = {(r.get("family"), int(r.get("seed", -1)), r.get("arm")) for r in rows}
    cells = {(FAMILIES[0], EVAL_SEEDS[0], arm) for arm in ARMS} if dry_run else expected_cells()
    for family, seed, arm in sorted(cells):
        if (family, seed, arm) not in seen:
            rows.append(_campaign_row(family, seed, arm, test_only=dry_run))
            artifact["rows"] = rows
            atomic_write(out, artifact)
    artifact["rows"] = rows
    artifact["status"] = "PARTIAL" if dry_run or len(rows) != len(expected_cells()) else "COMPLETE"
    atomic_write(out, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "ec-evaluation.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        run(out=args.out, resume=args.resume, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
