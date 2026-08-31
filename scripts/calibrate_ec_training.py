"""Training-only EC policy sweep with a fail-closed containment selector."""
from __future__ import annotations

import argparse, json, os, tempfile
from pathlib import Path
import torch

import diagnose_ec_abstentions as diagnostics
import run_ec_benchmark as runner
from boec.ec_calibration import ECTrainingCandidate, TrainingContainmentRecord, choose_training_candidate
from boec.ec_benchmark import CQA_NAMES, ECConfig, make_ec_landscape
from boec.manufacturing_qualification import qualify_multi_cqa
from boec.optimizers import sobol_design
from boec.seedbook import derive_seed

ROOT = Path(__file__).resolve().parents[1]
TRAIN = tuple(range(64))
# The first sweep used only uniform inflation and could not identify which CQA
# was driving empty joint certificates.  Keep those baselines, then test a
# small predeclared menu that expands the limiting identity/yield tails more
# aggressively.  This remains training-only: no evaluation result can select
# or alter these settings.
_INFLATION_MENU = (
    (1.0, 1.0, 1.0),
    (1.2, 1.2, 1.2),
    (1.5, 1.5, 1.5),
    (2.0, 1.5, 2.0),
    (3.0, 2.0, 3.0),
    (4.0, 3.0, 4.0),
)
CANDIDATES = tuple(
    ECTrainingCandidate(inflation, density)
    for inflation in _INFLATION_MENU
    for density in (4096, 8192)
)


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def assess(family: str, seed: int, candidate: ECTrainingCandidate) -> TrainingContainmentRecord:
    campaign = runner._run_arm(family, seed, "spade", test_only=True, calibration=candidate)
    landscape = make_ec_landscape(family, seed, ECConfig())
    y, yvar = landscape.evaluate(campaign.X)
    bounds = torch.stack((torch.zeros(6), torch.ones(6)))
    grid = sobol_design(bounds, 256, seed=derive_seed(seed, "ec-training-cal-grid", family))
    truth = landscape.truth(grid)
    thresholds = torch.tensor((.70, .70, .60))
    result = qualify_multi_cqa(
        campaign.X, y, yvar, bounds, diagnostics._definitions(), grid=grid,
        alpha=.95, n_draws=32, n_rho=8,
        base_seed=derive_seed(seed, "ec-training-cal-fit", family),
        latent_inflation=candidate.inflation_by_cqa, mean_marginalisation=True,
        volume_rule="smallest", truth_masks=tuple((truth[:, i] >= thresholds[i]) for i in range(3)),
    )
    contained = bool(result.joint_truth_containment) if result.joint_volume > 0 else False
    return TrainingContainmentRecord(family, seed, (contained, contained, contained))


def run(out: Path) -> dict:
    observations = {}
    details = []
    for candidate in CANDIDATES:
        records = []
        for family in runner.FAMILIES:
            for seed in TRAIN:
                record = assess(family, seed, candidate)
                records.append(record)
                details.append({"family": family, "seed": seed, "inflation_by_cqa": list(candidate.inflation_by_cqa),
                                "candidate_density": candidate.candidate_density,
                                "joint_contained": record.joint_contained})
                atomic_write(out, {"schema": "spade-ec-training-calibration-v2", "status": "PARTIAL",
                                   "training_seeds": list(TRAIN), "evaluation_seeds": [], "details": details})
        observations[candidate] = records
    try:
        selected = choose_training_candidate(observations)
        selection = {"inflation_by_cqa": list(selected.candidate.inflation_by_cqa),
                     "candidate_density": selected.candidate.candidate_density,
                     "joint_lower_bound": selected.joint_lower_bound,
                     "per_family_lower_bounds": selected.per_family_lower_bounds,
                     "status": "SELECTED"}
    except ValueError as exc:
        selection = {"status": "NO_ELIGIBLE_CANDIDATE", "reason": str(exc)}
    result = {"schema": "spade-ec-training-calibration-v2", "status": "COMPLETE",
              "execution_mode": "TRAINING_ONLY", "training_seeds": list(TRAIN),
              "evaluation_seeds": [], "selection": selection, "details": details}
    atomic_write(out, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path,
        default=ROOT / "results" / "ec-training-calibration.json")
    result = run(parser.parse_args().out); print(json.dumps(result["selection"], sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
