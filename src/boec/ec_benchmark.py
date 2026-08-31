"""Frozen six-factor, three-CQA EC-differentiation benchmark primitives."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
import torch
from torch import Tensor

CQA_NAMES = ("identity", "viability", "yield")

@dataclass(frozen=True)
class ECConfig:
    n_factors: int = 6
    budget: int = 48
    opening_wells: int = 32
    adaptive_batch: int = 8
    train_seed_start: int = 0
    train_seed_stop: int = 64
    eval_seed_start: int = 64
    eval_seed_stop: int = 96
    min_answered_per_family: int = 16
    cqa_thresholds: tuple[float, float, float] = (0.70, 0.70, 0.60)

    def __post_init__(self) -> None:
        if self.n_factors != 6 or len(self.cqa_thresholds) != 3:
            raise ValueError("EC benchmark requires six factors and three CQAs")
        if self.train_seed_stop > self.eval_seed_start:
            raise ValueError("training and evaluation seeds must be disjoint")

    @property
    def digest(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

@dataclass(frozen=True)
class ECLandscape:
    family: str
    seed: int
    config: ECConfig
    centers: tuple[tuple[float, ...], ...]
    widths: tuple[float, ...]

    def truth(self, X: Tensor) -> Tensor:
        if X.ndim != 2 or X.shape[1] != self.config.n_factors:
            raise ValueError("X must have shape (n, 6)")
        x = X.double(); responses = []
        for cqa in range(3):
            vals = []
            for center, width in zip(self.centers, self.widths):
                c = torch.tensor(center, dtype=torch.double, device=x.device)
                vals.append(torch.exp(-width * (x - c).square().sum(dim=1)))
            base = torch.stack(vals).amax(dim=0)
            offset = 0.02 * torch.sin(torch.tensor(float(self.seed + 13 * cqa)))
            responses.append((base + offset).clamp(0.0, 1.0))
        return torch.stack(responses, dim=1)

    def evaluate(self, X: Tensor) -> tuple[Tensor, Tensor]:
        y = self.truth(X)
        return y, 0.0025 + 0.01 * y.square()

def registered_ec_families(config: ECConfig | None = None) -> tuple[str, ...]:
    return ("ec_broad", "ec_narrow", "ec_multimodal")

def make_ec_landscape(family: str, seed: int, config: ECConfig | None = None) -> ECLandscape:
    cfg = config or ECConfig()
    if family not in registered_ec_families(cfg):
        raise ValueError(f"unknown EC family: {family}")
    centers = {
        "ec_broad": ((0.25, 0.62, 0.42, 0.35, 0.55, 0.48),),
        "ec_narrow": ((0.68, 0.35, 0.55, 0.72, 0.30, 0.62),),
        "ec_multimodal": ((0.25, 0.62, 0.42, 0.35, 0.55, 0.48),
                           (0.72, 0.35, 0.58, 0.64, 0.45, 0.70)),
    }
    widths = {"ec_broad": (7.0,), "ec_narrow": (18.0,), "ec_multimodal": (12.0, 10.0)}
    return ECLandscape(family, int(seed), cfg, centers[family], widths[family])

def joint_success(y: Tensor, thresholds: Tensor | tuple[float, float, float]) -> Tensor:
    if y.ndim != 2 or y.shape[1] != 3:
        raise ValueError("y must have shape (n, 3)")
    t = torch.as_tensor(thresholds, dtype=y.dtype, device=y.device)
    if t.shape != (3,):
        raise ValueError("thresholds must have shape (3,)")
    return (y >= t).all(dim=1)

__all__ = ["CQA_NAMES", "ECConfig", "ECLandscape", "make_ec_landscape", "registered_ec_families", "joint_success"]
