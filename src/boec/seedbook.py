"""Stateless labelled seeds and evaluation-indexed observation noise."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import torch
from torch import Tensor

__all__ = ["IndexedGaussianNoise", "derive_seed"]


def derive_seed(root_seed: int, label: str, *parts: object) -> int:
    """Derive a stable independent seed from a root seed and labelled identity."""
    payload = json.dumps(
        [int(root_seed), label, *parts],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63 - 1)


@dataclass(frozen=True)
class IndexedGaussianNoise:
    """Gaussian observation noise keyed by evaluation index rather than call order."""

    root_seed: int
    sigma_rel: float
    sigma_add: float

    def draw(self, indices: Tensor, latent: Tensor) -> tuple[Tensor, Tensor]:
        """Public alias for indexed observation-noise draws."""
        return self.observe(indices, latent)

    def observe(self, indices: Tensor, latent: Tensor) -> tuple[Tensor, Tensor]:
        """Observe latent values with draws determined independently for each index."""
        eps, eta = [], []
        for index in indices.reshape(-1).tolist():
            g_rel = torch.Generator().manual_seed(
                derive_seed(self.root_seed, "rel", index)
            )
            g_add = torch.Generator().manual_seed(
                derive_seed(self.root_seed, "add", index)
            )
            eps.append(torch.randn((), generator=g_rel, dtype=torch.double))
            eta.append(torch.randn((), generator=g_add, dtype=torch.double))
        eps_t = torch.stack(eps).reshape_as(latent) * self.sigma_rel
        eta_t = torch.stack(eta).reshape_as(latent) * self.sigma_add
        y = latent * (1 + eps_t) + eta_t
        yvar = (
            y.square() * self.sigma_rel**2 + self.sigma_add**2
        ).clamp_min(self.sigma_add**2)
        return y, yvar
